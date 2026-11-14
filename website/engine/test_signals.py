from __future__ import annotations

import csv
import hashlib
import http.client
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from website.engine import signals
from website.engine.runtime import Runtime
from website.engine.server import RequestError, make_server
from website.engine.test_state import MemoryState

NOW = 1_800_000_005
REQUEST = {"coin": "SOL", "strategy": "buy_and_hold", "interval": "1h"}


def history(root, *, partial=None, stale=False, gap=False):
    path = Path(root) / "data" / "SOL_1h.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(("timestamp", "open", "high", "low", "close", "volume"))
    end = NOW // 3600 * 3600
    for i in range(100):
        if (gap and i == 50) or (stale and i == 99):
            continue
        price = 100 + i
        writer.writerow(
            (end - (100 - i) * 3600, price, price + 2, price - 1, price + 1, 1000)
        )
    if partial is not None:
        writer.writerow((end, partial, partial + 2, partial - 1, partial + 1, 1000))
    raw = buffer.getvalue().encode()
    path.write_bytes(raw)
    path.with_suffix(".json").write_text(
        json.dumps(
            {
                "provider": "https://api.exchange.coinbase.com",
                "product": "SOL-USD",
                "interval": "1h",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bars": 99 if stale or gap else 100,
                "lastBar": end - (7200 if stale else 3600),
                "contiguous": not gap,
            }
        )
    )
    return path


def observation(now=NOW, *, bootstrap=False):
    item = {
        "source": "coinbase_exchange_public",
        "instrument": "SOL/USD",
        "venue": "coinbase",
        "kind": "public_reference",
        "event_id": "SOL:trade:123",
        "observed_at": now,
        "received_at": now,
        "price": 200,
        "timestamp_semantics": "exchange_trade_time",
        "provider": "api.exchange.coinbase.com",
        "upstream_recency_verified": True,
    }
    if bootstrap:
        item.update(
            timestamp_semantics="closed_candle_start_index",
            upstream_recency_verified=False,
        )
    return item


class Fractional:
    name, params = "fractional", {}

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return 0.5


class Invalid(Fractional):
    def on_bar(self, history):
        return float("nan")


class Peeking(Fractional):
    def on_bar(self, history):
        return history.closes[history.i + 1]


class Stateful(Fractional):
    def __init__(self):
        self.calls = 0

    def warmup_bars(self):
        return 7

    def on_bar(self, history):
        self.calls += 1
        return 1.0 if self.calls % 3 else -1.0


class SignalsTests(unittest.TestCase):
    def runtime(self, root, *, item=None, public=None):
        runtime = Runtime(root, MemoryState(), clock=lambda: NOW, public=public)
        runtime.initialize()
        runtime.engines["SOL"].ingest(item or observation(), now=NOW)
        runtime.save()
        return runtime

    def test_latest_closed_bar_target_matches_canonical_next_bar_pending_target(self):
        from backtester.core.data import frame_to_arrays
        from backtester.core.engine import EngineConfig, run_backtest
        from backtester.core.strategies import REGISTRY, build
        from backtester.core.types import Mode

        with (
            tempfile.TemporaryDirectory() as temp,
            mock.patch.dict(REGISTRY, {"buy_and_hold": Stateful}),
        ):
            runtime = self.runtime(temp)
            history(temp, partial=100_000)
            result = runtime.signal(REQUEST)
            frame, _, _ = signals.closed_history(Path(temp) / "data", REQUEST, NOW)
            expected = run_backtest(
                build("buy_and_hold"),
                frame_to_arrays(frame),
                EngineConfig(mode=Mode.SPOT, interval="1h", fill_delay=1),
                close_at_end=False,
            )
            self.assertEqual(result["status"], "available")
            self.assertEqual(
                result["desiredExposure"], expected.account.pending_targets[len(frame)]
            )
            self.assertEqual(result["barEnd"], NOW // 3600 * 3600)
            self.assertEqual(result["barStart"], result["barEnd"] - 3600)
            self.assertEqual(result["fillDelay"], 1)
            self.assertFalse(result["executionQuote"])
            self.assertNotIn("price", result["marketObservation"])
            self.assertEqual(result["expiresAt"], NOW + 15)

    def test_future_partial_values_cannot_change_target_input_hash_or_signal_identity(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp, partial=100_000)
            first = runtime.signal(REQUEST)
            history(temp, partial=0.5)
            runtime.save()
            changed = runtime.signal(REQUEST)
            for key in (
                "desiredExposure",
                "inputHash",
                "signalId",
                "barStart",
                "barEnd",
                "strategyRevision",
            ):
                self.assertEqual(first[key], changed[key], key)
            self.assertNotEqual(first["sourceHash"], changed["sourceHash"])
            self.assertEqual(len(first["inputHash"]), 64)

    def test_fractional_nan_and_future_peek_are_refused_without_rounding(self):
        from backtester.core.strategies import REGISTRY

        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp)
            for factory, reason in (
                (Fractional, "unsupported_fractional_target"),
                (Invalid, "strategy_not_usable"),
                (Peeking, "strategy_not_usable"),
            ):
                with (
                    self.subTest(factory=factory),
                    mock.patch.dict(REGISTRY, {"buy_and_hold": factory}),
                ):
                    result = runtime.signal(REQUEST)
                    self.assertEqual(result["status"], "unavailable")
                    self.assertEqual(result["reason"], reason)
                    self.assertNotIn("desiredExposure", result)

    def test_fresh_closed_history_cannot_substitute_for_a_genuine_current_event(self):
        with tempfile.TemporaryDirectory() as temp:
            history(temp)
            for item in (observation(NOW - 16), observation(bootstrap=True)):
                runtime = self.runtime(
                    Path(temp) / str(item["observed_at"]) / item["timestamp_semantics"],
                    item=item,
                )
                runtime.root.joinpath("data").mkdir(exist_ok=True)
                history(runtime.root)
                result = runtime.signal(REQUEST)
                self.assertEqual(result["status"], "unavailable")
                self.assertEqual(result["reason"], "fresh_market_observation_required")

    def test_gapped_history_and_untrusted_provenance_are_not_signals(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            path = history(temp, gap=True)
            self.assertEqual(runtime.signal(REQUEST)["reason"], "history_not_usable")
            history(temp)
            path.with_suffix(".json").write_text("{}")
            self.assertEqual(
                runtime.signal(REQUEST)["reason"], "public_provenance_unavailable"
            )

    def test_stale_closed_history_requires_explicit_public_refresh_and_durable_commit(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp, stale=True)
            with (
                mock.patch.object(
                    runtime.public, "refresh", side_effect=lambda *_: history(temp)
                ) as refresh,
                mock.patch.object(runtime, "save", wraps=runtime.save) as save,
            ):
                self.assertEqual(runtime.signal(REQUEST)["status"], "available")
                refresh.assert_called_once_with("SOL", "1h")
                self.assertEqual(save.call_count, 1)
            history(temp, stale=True)
            with mock.patch.object(runtime.public, "refresh"):
                self.assertEqual(runtime.signal(REQUEST)["reason"], "stale_history")

    def test_checkpoint_failure_and_expiry_during_calculation_never_publish_a_target(
        self,
    ):
        from website.engine.state import StateError

        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp, stale=True)
            runtime.checkpoint.remote.fail = True
            with (
                mock.patch.object(
                    runtime.public, "refresh", side_effect=lambda *_: history(temp)
                ),
                self.assertRaises(StateError),
            ):
                runtime.signal(REQUEST)
            with self.assertRaisesRegex(RequestError, "not_ready"):
                runtime.signal(REQUEST)
            runtime.checkpoint.remote.fail = False
            runtime.save()
            original = signals.calculate

            def expire(*args):
                result = original(*args)
                runtime.clock = lambda: NOW + 16
                return result

            with mock.patch("website.engine.signals.calculate", side_effect=expire):
                self.assertEqual(
                    runtime.signal(REQUEST)["reason"],
                    "signal_expired_during_calculation",
                )

    def test_compute_budget_is_bounded_and_semantic_errors_are_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp)
            selected = signals.closed_history(runtime.root / "data", REQUEST, NOW)
            market = runtime.engines["SOL"].market(now=NOW)
            with self.assertRaisesRegex(signals.SignalUnavailable, "compute_budget"):
                signals.calculate(
                    REQUEST,
                    selected,
                    market,
                    runtime.identity,
                    NOW,
                    monotonic=iter((0, 6)).__next__,
                )
            self.assertEqual(
                runtime.signal({**REQUEST, "strategy": "unknown"})["reason"],
                "unsupported_market_or_strategy",
            )
            with self.assertRaises(RequestError):
                runtime.signal({**REQUEST, "wallet": "caller_cannot_select_owner"})

    def test_actual_http_signal_catalogue_revisions_and_private_gateway(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = self.runtime(temp)
            history(temp)
            server = make_server(runtime.analysis, "x" * 32, port=0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def call(method, path, body=None, *, auth=True):
                connection = http.client.HTTPConnection(
                    "127.0.0.1", server.server_port, timeout=5
                )
                headers = {"Content-Type": "application/json"}
                if auth:
                    headers["Authorization"] = "Bearer " + "x" * 32
                connection.request(
                    method,
                    path,
                    json.dumps(body) if body is not None else None,
                    headers,
                )
                response = connection.getresponse()
                value = response.status, json.loads(response.read())
                connection.close()
                return value

            try:
                self.assertEqual(
                    call("POST", "/v1/signals", REQUEST, auth=False)[0], 401
                )
                status, result = call("POST", "/v1/signals", REQUEST)
                self.assertEqual(status, 200)
                self.assertEqual(result["status"], "available")
                status, catalogue = call("GET", "/v1/strategies")
                self.assertEqual(status, 200)
                row = next(
                    row
                    for row in catalogue["strategies"]
                    if row["id"] == REQUEST["strategy"]
                )
                self.assertEqual(row["strategyRevision"], result["strategyRevision"])
                self.assertEqual(catalogue["sourceIdentity"], result["sourceIdentity"])
                self.assertTrue(
                    call("GET", "/health")[1]["capabilities"]["strategySignals"]
                )
                self.assertEqual(
                    call("POST", "/v1/signals", {**REQUEST, "wallet": "x"})[0], 400
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(2)


if __name__ == "__main__":
    unittest.main()

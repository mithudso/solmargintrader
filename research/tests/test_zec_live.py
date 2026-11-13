"""Selection completeness, causal signals, real HTTP parsing and stale displays."""

from __future__ import annotations

import json
import math
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import numpy as np

from oracle.feeds import FeedUnavailable
from research import zec_live as live
from research.zec_expanded import contexts


def candles(count=100, step=60):
    rows = {}
    for i in range(count):
        price = 100 + 2 * math.sin(i / 4) + i / 100
        rows[i * step] = {
            "ts": i * step,
            "open": price,
            "close": price,
            "high": price + 1,
            "low": price - 1,
            "volume": i + 1.0,
        }
    return rows


def winner(mode="baseline", config=None):
    return {
        "interval": "1m",
        "candidate_id": "test",
        "mode": mode,
        "market": "spot_reference",
        "family": "single",
        "config": config
        or {
            "members": [
                {
                    "strategy": "rsi",
                    "params": {"period": 3, "oversold": 45, "exit_level": 60},
                }
            ],
            "mode": "single",
            "persistence": 1,
        },
        "historical": {"15": {"return_pct": 1, "fills": 2, "replay_id": "evidence"}},
        "winning_fee_bps": [15],
    }


class Selection(unittest.TestCase):
    def test_every_frozen_positive_fee_row_is_retained(self):
        selected = live.load_winners()
        self.assertEqual(len(selected), 908)
        self.assertEqual(sum(len(w["winning_fee_bps"]) for w in selected), 1566)
        self.assertEqual({w["interval"] for w in selected}, set(live.STEPS))
        self.assertEqual({w["mode"] for w in selected}, set(live.MODES))
        self.assertTrue(
            all(w["config"] for w in selected if w["market"] == "spot_reference")
        )

    def test_nonpositive_and_inactive_rows_do_not_qualify(self):
        base = {
            "interval": "1m",
            "candidate_id": "a",
            "mode": "baseline",
            "fee_bps": "25",
            "status": "completed",
            "return_pct": "-1",
            "fills": "2",
            "market": "spot_reference",
            "family": "single",
            "replay_id": "a",
        }
        rows = [
            base,
            {**base, "fee_bps": "15", "return_pct": "1"},
            {**base, "candidate_id": "inactive", "return_pct": "1", "fills": "0"},
            {
                **base,
                "candidate_id": "missing",
                "status": "insufficient_contiguous_history",
                "return_pct": "",
            },
        ]
        selected = live.select_winners(rows, {"a": winner()["config"]})
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["winning_fee_bps"], [15])
        self.assertEqual(selected[0]["historical"]["25"]["return_pct"], -1)

    def test_tampered_study_is_refused(self):
        with (
            patch.object(live, "CSV_HASH", "0" * 64),
            self.assertRaisesRegex(ValueError, "accepted_study_hash_mismatch"),
        ):
            live.load_winners()


class Input(unittest.TestCase):
    def test_provider_order_and_incomplete_future_bar(self):
        bars = live.parse_candles(
            [[60, 9, 13, 10, 12, 7], [120, 8, 14, 9, 13, 5]], 60, 60, 120
        )
        self.assertEqual(
            bars[60],
            {"ts": 60, "low": 9, "high": 13, "open": 10, "close": 12, "volume": 7},
        )
        self.assertNotIn(120, bars)

    def test_bad_volume_nan_crossed_prices_and_conflicting_duplicates_refuse(self):
        for row in [
            [60, 9, 13, 10, 12, -1],
            [60, 9, 13, 10, np.nan, 1],
            [60, 9, 11, 10, 12, 1],
            [True, 9, 13, 10, 12, 1],
            [61, 9, 13, 10, 12, 1],
        ]:
            with self.subTest(row=row), self.assertRaises(FeedUnavailable):
                live.parse_candles([row], 60, 0, 120)
        with self.assertRaisesRegex(FeedUnavailable, "duplicate_conflict"):
            live.parse_candles(
                [[60, 9, 13, 10, 12, 1], [60, 9, 13, 10, 12, 2]], 60, 0, 120
            )

    def test_ten_minute_aggregation_requires_both_real_volume_candles(self):
        rows = candles(4, 300)
        merged = live.aggregate(rows, 300, 600)
        self.assertEqual(merged[0]["volume"], 3)
        self.assertEqual(merged[0]["close"], rows[300]["close"])
        del rows[300]
        self.assertNotIn(0, live.aggregate(rows, 300, 600))

    def test_real_http_client_paginates_and_sanitizes_rate_limit(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            status = 200

            def do_GET(self):
                requests.append(self.path)
                query = parse_qs(urlparse(self.path).query)
                stamp = int(
                    live.datetime.fromisoformat(
                        query["start"][0].replace("Z", "+00:00")
                    ).timestamp()
                )
                self.send_response(type(self).status)
                self.end_headers()
                self.wfile.write(json.dumps([[stamp, 9, 13, 10, 12, 7]]).encode())

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with patch.object(live, "BASE", f"http://127.0.0.1:{server.server_port}"):
                result = live.Candles(pause=0).fetch(60, 0, 600 * 60)
                self.assertEqual(len(requests), 3)
                self.assertEqual(len(result), 3)
                self.assertTrue(
                    all(p.startswith("/products/ZEC-USD/candles?") for p in requests)
                )
                Handler.status = 429
                with self.assertRaisesRegex(FeedUnavailable, "^candle_rate_limited$"):
                    live.Candles(pause=0).fetch(60, 0, 60)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)


class Signals(unittest.TestCase):
    def test_shape_keeps_the_real_return_before_its_window(self):
        prices = np.exp(np.cumsum(np.random.default_rng(569).normal(0.0003, 0.01, 200)))
        bars = {
            "ts": np.arange(200) * 60,
            "close": prices,
            "high": prices * 1.001,
            "low": prices * 0.999,
        }
        result = live.latest_shape(bars, np.ones(200, dtype=bool), 60)
        self.assertEqual(result["shape"], "range")
        # A final48-only slice invents a zero first return and mislabels this V.
        truncated = {k: v[-48:] for k, v in bars.items()}
        self.assertEqual(
            live.latest_shape(truncated, np.ones(48, dtype=bool), 60)["shape"],
            "v_rebound",
        )

    def test_future_prices_cannot_change_issued_signal_or_shape(self):
        rows = candles(120)
        first = live.evaluate("1m", [winner()], rows, 100 * 60)[0]
        for stamp, bar in rows.items():
            if stamp >= 100 * 60:
                bar.update(open=1e8, high=1e9, low=1, close=1e8, volume=1e9)
        after = live.evaluate("1m", [winner()], rows, 100 * 60)[0]
        self.assertEqual(first, after)
        self.assertEqual(first["bar_close_at"], 6000)
        self.assertEqual(first["target_at"], 6060)

    def test_flat_exit_is_not_down_and_missing_history_is_not_flat(self):
        rows = {
            i * 60: {
                "ts": i * 60,
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100 + i,
                "volume": 1,
            }
            for i in range(100)
        }
        result = live.evaluate("1m", [winner()], rows, 6000)[0]
        self.assertEqual(result["direction"], "FLAT")
        del rows[98 * 60]
        result = live.evaluate("1m", [winner()], rows, 6000)[0]
        self.assertEqual(result["status"], "warming")
        self.assertIsNone(result["direction"])
        self.assertEqual(result["shape"]["shape"], "unknown")

    def test_same_causal_frozen_frequency_as_accepted_contexts(self):
        bars, valid = live.arrays_for(candles(97), 60, 97 * 60)
        expected, fits, _ = contexts(bars, valid, 60, replicates=99)
        actual = live.latest_cycle(bars, valid, 60)
        self.assertEqual(actual["cycle"], expected["cycle"][-1])
        self.assertEqual(actual["linear"], expected["linear"][-1])
        self.assertEqual(actual["period_seconds"], fits[-1]["period_seconds"])
        self.assertEqual(actual["fit_available_at"], fits[-1]["available_at"])
        self.assertFalse(actual["qualified"])

    def test_lifecycle_policy_never_gets_invented_direction(self):
        item = {
            **winner(),
            "market": "observed_cross_limit_guard_reference",
            "config": None,
        }
        row = live.evaluate("1m", [item], candles(), 6000)[0]
        self.assertEqual(row["status"], "unavailable")
        self.assertIsNone(row["direction"])

    def test_late_training_revision_cannot_refit_inside_frozen_block(self):
        bars, valid = live.arrays_for(candles(97), 60, 97 * 60)
        frozen = {}
        first = live.latest_cycle(bars, valid, 60, frozen)
        bars["close"][:96] = 100 + np.arange(96) * 2
        revised = live.latest_cycle(bars, valid, 60, frozen)
        self.assertEqual(first, revised)
        self.assertNotEqual(
            first["training_sha256"],
            live.latest_cycle(bars, valid, 60)["training_sha256"],
        )

    def test_unavailable_cycle_is_frozen_until_next_decision(self):
        bars, valid = live.arrays_for(candles(80), 60, 80 * 60)
        frozen = {}
        valid[-1] = False
        self.assertIsNone(live.latest_cycle(bars, valid, 60, frozen))
        valid[-1] = True
        self.assertIsNone(live.latest_cycle(bars, valid, 60, frozen))
        self.assertIsNotNone(live.latest_cycle(bars, valid, 60))

    def test_quote_staleness_and_bar_expiry_clear_current_direction(self):
        display = live.LiveDisplay([winner()])
        ready = live.evaluate("1m", [winner()], candles(), 6000)
        display.views["1m"] = ready
        quote = {"price": 100, "observed_at": 6001}
        self.assertEqual(display.frame(6001, quote)["rows"][0]["status"], "ready")
        stale = display.frame(6020, quote)["rows"][0]
        self.assertEqual(stale["status"], "stale")
        self.assertIsNone(stale["direction"])
        expired = display.frame(6060, {**quote, "observed_at": 6060})["rows"][0]
        self.assertEqual(expired["reason"], "completed_bar_prediction_expired")
        self.assertEqual(expired["target_at"], 6060)
        self.assertEqual(
            ready[0]["status"], "ready"
        )  # Rendering cannot mutate saved signals.

    def test_failed_refresh_surfaces_error_and_cannot_keep_previous_signal_green(self):
        class Client:
            def fetch(self, *args):
                raise FeedUnavailable("candle_provider_unavailable")

        display = live.LiveDisplay([winner()], client=Client())
        display.views["1m"] = live.evaluate("1m", [winner()], candles(), 6000)
        display.refresh(6065)
        row = display.frame(6065, {"observed_at": 6065, "price": 100})["rows"][0]
        self.assertEqual(row["status"], "unavailable")
        self.assertIsNone(row["direction"])
        self.assertEqual(row["reason"], "candle_provider_unavailable")

    def test_late_internal_candle_recovers_on_next_boundary(self):
        class Client:
            calls = 0

            def fetch(self, step, start, end):
                self.calls += 1
                rows = candles(101)
                if self.calls == 1:
                    del rows[98 * 60]
                return {t: b for t, b in rows.items() if start <= t < end}

        display = live.LiveDisplay([winner()], client=Client())
        display.refresh(6005)
        self.assertEqual(display.views["1m"][0]["status"], "warming")
        display.refresh(6065)
        self.assertEqual(display.views["1m"][0]["status"], "ready")

    def test_missing_latest_candle_retries_within_same_boundary(self):
        class Client:
            calls = 0

            def fetch(self, step, start, end):
                self.calls += 1
                rows = candles(100)
                if self.calls == 1:
                    del rows[99 * 60]
                return {t: b for t, b in rows.items() if start <= t < end}

        client = Client()
        display = live.LiveDisplay([winner()], client=client)
        display.refresh(6005)
        self.assertNotIn("1m", display.ends)
        display.refresh(6020)
        self.assertEqual(client.calls, 2)
        self.assertEqual(display.views["1m"][0]["status"], "ready")

    def test_render_never_hides_rows_without_explicit_limit(self):
        display = live.LiveDisplay([winner()])
        frame = display.frame(6000, None, "quote_stale")
        self.assertIn("test", live.render(frame))
        self.assertIn("rsi", live.render(frame))
        self.assertIn("N/A", live.render(frame))


if __name__ == "__main__":
    unittest.main()

"""Causal paper decisions and exact-path evidence, using public-wire loopbacks."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import threading
import time
import unittest
import urllib.parse
import urllib.request
import zlib
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from oracle_leverage import mtf_forward as mtf

NOW = 1_800_000_000


def bundle():
    models = {}
    for asset in ("BTC", "ZEC"):
        models[asset] = {
            "schema": "mtf-reversal-model/v1",
            "asset": asset,
            "trained_through": NOW - 86400,
            "alpha": 20,
            "min_cell_n": 20,
            "min_components": 2,
            "base_models": {
                str(n): {
                    "n": 100,
                    "down": 60,
                    "contexts": {str(m): {} for m in mtf.INTERVALS},
                }
                for n in mtf.INTERVALS
            },
            "selected": {"minutes": 5, "threshold": 0.7, "id": "fixture-5m"}
            if asset == "BTC"
            else None,
        }
    return {"schema": "mtf-reversal-live-bundle/v1", "models": models}


class Analysis:
    def __init__(self):
        self.supported = 4
        self.pair = "UU"
        self.seen = []

    def live_context(self, rows, at):
        assert rows and all(row[0] + 60 <= at for row in rows)
        self.seen.append(copy.deepcopy(rows))
        return {
            "at": at,
            "frames": {
                str(n): {
                    "shape": "rising",
                    "pair": self.pair,
                    "closed_at": int(at // (n * 60)) * n * 60,
                }
                for n in mtf.INTERVALS
            },
        }

    def score_context(self, model, base_minutes, context):
        return {
            "status": "ready",
            "score_down": 0.8,
            "components": [
                {
                    "minutes": n,
                    "shape": "rising",
                    "n": 40 if i < self.supported else 0,
                    "down": 32,
                    "posterior_down": 0.8,
                    "weight": 1 if i < self.supported else 0,
                    "wilson": [0.6, 0.9],
                }
                for i, n in enumerate(mtf.INTERVALS)
            ],
            "base_down_rate": 0.6,
        }

    def classify(self, score_down, threshold):
        return (
            "DOWN"
            if score_down >= threshold
            else "UP"
            if score_down <= 1 - threshold
            else None
        )


def raw_samples(asset, first, last, *, peak=None, missing=False):
    data = []
    for index, stamp in enumerate(range(first, last + mtf.GRID_US, mtf.GRID_US)):
        if missing and index == 2:
            continue
        price = Decimal(str(peak)) if peak is not None and index == 3 else Decimal(100)
        data.append(
            {
                "price_feed_id": mtf.FEEDS[asset],
                "publish_time": stamp,
                "feed_update_timestamp": stamp,
                "price": int(price * 100_000_000),
                "exponent": -8,
            }
        )
    return mtf.canonical({"data": data}).encode()


class Public:
    def __init__(self, clock):
        self.clock = clock
        self.peak = None
        self.missing = False
        self.future_history = False
        self.gate = None
        self.history_calls = []
        self.path_calls = []
        self.before_path = None

    def history(self, asset, start, last, *, cancelled):
        self.history_calls.append((asset, start, last))
        if self.gate is not None:
            while not self.gate.wait(0.01):
                if cancelled():
                    raise mtf.MtfError("public_request_cancelled")
        if cancelled():
            raise mtf.MtfError("public_request_cancelled")
        rows = [
            [stamp, 100.0, 101.0, 99.0, 100.5, 0]
            for stamp in range(start, last + 60, 60)
        ]
        if self.future_history:
            rows.append([last + 60, 100.0, 101.0, 99.0, 100.5, 0])
        return {"rows": rows, "proof": {"fixture": True}}

    def path(self, asset, entry_at, exit_at, *, cancelled):
        if self.before_path:
            self.before_path()
        self.path_calls.append((asset, entry_at, exit_at))
        first, last = mtf.path_grid(entry_at, exit_at)
        raw = raw_samples(asset, first, last, peak=self.peak, missing=self.missing)
        url = (
            mtf.PRICES_URL
            + "?"
            + urllib.parse.urlencode(
                {
                    "feedId": mtf.FEEDS[asset],
                    "fromMs": first // 1000,
                    "toMs": last // 1000,
                }
            )
        )
        return {
            "status": "complete",
            "points": [],
            "proof": {
                "url": url,
                "received_at": self.clock(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "first_us": first,
                "last_us": last,
            },
            "raw": raw,
        }


class Observer(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / "home"
        self.now = float(NOW + 5)
        self.analysis = Analysis()
        self.public = Public(lambda: self.now)
        self.workers = []

    def worker(self, models=None):
        worker = mtf.MtfForward(
            self.home,
            models or bundle(),
            public=self.public,
            analysis=self.analysis,
            clock=lambda: self.now,
        )
        self.workers.append(worker)
        self.addCleanup(worker.close)
        return worker

    def publish(self, worker, price=100.0, **changes):
        quote = {
            "asset": "BTC",
            "feed_id": 1,
            "endpoint": mtf.STREAM_URL,
            "quote_currency": "USD",
            "price": price,
            "exchange_at": self.now - 0.4,
            "received_at": self.now - 0.1,
        }
        quote.update(changes)
        metadata = {
            "at": self.now,
            "status": "streaming",
            "connected": {"jupiter": True},
            "feeds": {"jupiter": {"BTC": quote}},
        }
        worker.parent.put_meta("dual_quotes", metadata)
        return metadata

    def pump(self, worker, condition, seconds=3):
        deadline = time.monotonic() + seconds
        while not condition():
            self.assertLess(time.monotonic(), deadline)
            worker.tick()
            time.sleep(0.005)

    def ready(self, worker):
        self.pump(worker, lambda: "BTC" in worker._contexts)

    def enter(self, worker):
        self.ready(worker)
        self.publish(worker)
        worker.tick()
        self.assertEqual(len(worker.ledger.rows()), 1)
        return worker.ledger.rows()[0]

    def test_commit_uses_wall_time_before_outcome_with_all_shapes_scores_and_zero_volume(
        self,
    ):
        worker = self.worker()
        row = self.enter(worker)
        self.assertEqual(row["decision_at"], NOW + 5)
        self.assertEqual(row["committed_at"], NOW + 5)
        self.assertEqual((row["target_start"], row["target_end"]), (NOW, NOW + 300))
        quote = json.loads(row["entry_quote_json"])
        self.assertNotEqual(row["decision_at"], quote["exchange_at"])
        self.assertAlmostEqual(quote["exchange_age_seconds"], 0.4, places=5)
        self.assertAlmostEqual(quote["received_age_seconds"], 0.1, places=5)
        self.assertEqual(
            set(json.loads(row["context_json"])["frames"]), {"5", "10", "15", "20"}
        )
        self.assertEqual(set(json.loads(row["scores_json"])), {"5", "10", "15", "20"})
        self.assertEqual(row["model_sha"], worker.model_sha)
        self.assertTrue(
            all(row[-1] == 0 for rows in self.analysis.seen for row in rows)
        )
        self.assertEqual(self.public.path_calls, [])

        def committed():
            independent = worker.ledger.rows()[0]
            self.assertEqual(independent["status"], "pending")
            self.assertIsNotNone(independent["committed_at"])

        self.public.before_path = committed
        self.now = NOW + 300.5
        self.publish(worker, 99.5)
        self.pump(
            worker,
            lambda: any(
                value["id"] == row["id"] and value["status"] == "settled"
                for value in worker.ledger.rows()
            ),
        )
        self.assertEqual(self.public.path_calls[0][1], row["decision_at"])
        self.assertEqual(worker.parent.intents(), [])
        self.assertEqual(worker.parent.predictions(), [])

    def test_path_touch_at_exact_9_8bps_fails_despite_correct_close(self):
        worker = self.worker()
        initial = self.enter(worker)
        self.public.peak = 100.098
        self.now = NOW + 300.5
        self.publish(worker, 99.5)
        self.pump(
            worker,
            lambda: any(
                value["id"] == initial["id"] and value["status"] == "settled"
                for value in worker.ledger.rows()
            ),
        )
        row = next(
            value for value in worker.ledger.rows() if value["id"] == initial["id"]
        )
        self.assertEqual(row["direction_correct"], 1)
        self.assertEqual(row["survived"], 0)
        self.assertEqual(row["paper_win"], 0)
        with worker.ledger.connect() as db:
            evidence = db.execute(
                "SELECT proof_json,raw_zlib FROM path_attempts"
            ).fetchone()
        raw = zlib.decompress(evidence["raw_zlib"])
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            json.loads(evidence["proof_json"])["sha256"],
        )

    def test_raw_oracle_units_prevent_float_rounding_from_hiding_exact_liquidation(
        self,
    ):
        worker = self.worker()
        self.ready(worker)
        self.publish(
            worker, 100.00000000000001, raw_price="100000000000000", exponent=-12
        )
        worker.tick()
        initial = worker.ledger.rows()[0]
        quote = json.loads(initial["entry_quote_json"])
        self.assertEqual(Decimal(quote["price_decimal"]), Decimal(100))
        self.assertEqual(quote["price_precision"], "raw_oracle_units")
        self.public.peak = 100.098
        self.now = NOW + 331
        self.publish(worker, 99.5)
        self.pump(
            worker,
            lambda: any(
                value["id"] == initial["id"] and value["status"] == "settled"
                for value in worker.ledger.rows()
            ),
        )
        row = next(
            value for value in worker.ledger.rows() if value["id"] == initial["id"]
        )
        self.assertEqual(row["direction_correct"], 1)
        self.assertEqual(row["survived"], 0)
        self.assertEqual(row["paper_win"], 0)
        performance = worker.ledger.performance()
        self.assertEqual(performance["by_asset"]["BTC"]["direction_correct"], 1)
        self.assertEqual(performance["by_asset"]["BTC"]["paper_wins"], 0)
        self.assertEqual(performance["by_asset"]["BTC"]["hit_rate"], 0)
        self.assertIsNone(performance["by_asset"]["BTC"]["mean_net_bps"])
        self.assertEqual(performance["by_asset"]["ZEC"]["settled"], 0)
        self.assertIsNone(performance["by_asset"]["ZEC"]["hit_rate"])

    def test_missing_grid_stays_unscored_blocks_entries_and_retries_once_per_minute_across_restart(
        self,
    ):
        worker = self.worker()
        self.enter(worker)
        self.public.missing = True
        self.now = NOW + 300.5
        self.publish(worker, 99.5)
        self.pump(worker, lambda: bool(worker.ledger.rows()[0]["last_error"]))
        self.assertEqual(worker.ledger.rows()[0]["status"], "pending")
        self.assertIsNone(worker.ledger.rows()[0]["survived"])
        self.assertEqual(len(self.public.path_calls), 1)
        for _ in range(5):
            worker.tick()
        worker.close()
        restarted = self.worker()
        self.ready(restarted)
        self.assertEqual(len(self.public.path_calls), 1)
        self.now += 60
        self.publish(restarted, 99.5)
        self.pump(restarted, lambda: len(self.public.path_calls) == 2)
        self.now = NOW + 605
        self.publish(restarted)
        for _ in range(3):
            restarted.tick()
        self.assertEqual(len(restarted.ledger.rows()), 1)
        self.assertEqual(restarted.ledger.performance()["paper_wins"], 0)

    def test_restart_does_not_duplicate_or_change_the_frozen_model(self):
        worker = self.worker()
        self.enter(worker)
        worker.close()
        restarted = self.worker()
        self.ready(restarted)
        self.publish(restarted)
        restarted.tick()
        self.assertEqual(len(restarted.ledger.rows()), 1)
        restarted.close()
        changed = bundle()
        changed["models"]["BTC"]["selected"]["threshold"] = 0.8
        with self.assertRaisesRegex(mtf.MtfError, "model_change_refused"):
            self.worker(changed).start()

    def test_late_start_and_preboundary_or_stale_quotes_never_backfill_entries(self):
        worker = self.worker()
        self.now = NOW + 31
        self.ready(worker)
        self.publish(worker)
        worker.tick()
        self.assertEqual(worker.ledger.rows(), [])
        self.now = NOW + 5
        for changes in (
            {"exchange_at": NOW - 0.1},
            {"exchange_at": self.now - 1.01},
            {"received_at": self.now - 1.01},
            {"exchange_at": self.now + 0.01},
            {"asset": "ZEC"},
            {"feed_id": True},
            {"quote_currency": "USDC"},
            {"endpoint": "https://untrusted.invalid"},
        ):
            with self.subTest(changes=changes):
                self.publish(worker, **changes)
                worker.tick()
                self.assertEqual(worker.ledger.rows(), [])

    def test_minimum_two_supported_contexts_and_uu_pair_are_required(self):
        worker = self.worker()
        self.analysis.supported = 1
        self.ready(worker)
        self.publish(worker)
        worker.tick()
        self.assertEqual(worker.ledger.rows(), [])
        self.assertEqual(self.analysis.supported, 1)

    def test_first_fresh_exit_is_recorded_after_boundary_and_observed_touch_is_immediate(
        self,
    ):
        worker = self.worker()
        self.enter(worker)
        self.now = NOW + 6
        self.publish(worker, 100.098)
        worker.tick()
        self.assertEqual(worker.ledger.rows()[0]["observed_liquidation"], 1)
        self.assertEqual(worker.ledger.rows()[0]["status"], "open")
        self.now = NOW + 300.2
        self.publish(worker, 99.5, exchange_at=NOW + 299.9)
        worker.tick()
        self.assertIsNone(worker.ledger.rows()[0]["exit_decision_at"])
        self.now = NOW + 300.8
        self.publish(worker, 99.4, exchange_at=NOW + 300.6)
        worker.tick()
        row = worker.ledger.rows()[0]
        self.assertEqual(row["exit_decision_at"], self.now)
        self.assertEqual(row["exit_price"], 99.4)
        self.assertEqual(
            json.loads(row["exit_quote_json"])["boundary_delay_seconds"],
            self.now - (NOW + 300),
        )

    def test_future_or_incomplete_history_never_reaches_the_scorer(self):
        worker = self.worker()
        self.public.future_history = True
        self.publish(worker)
        self.pump(
            worker,
            lambda: (
                worker._state["assets"].get("BTC", {}).get("status")
                == "history-unavailable"
            ),
        )
        self.assertEqual(worker.ledger.rows(), [])
        self.assertEqual(self.analysis.seen, [])

    def test_owned_lock_and_shutdown_leave_parent_worker_heartbeat_untouched(self):
        worker = self.worker()
        worker.start()
        other = self.worker()
        with self.assertRaisesRegex(mtf.MtfError, "already_running"):
            other.start()
        worker.parent.put_meta("heartbeat", {"status": "frozen-paper-sentinel"})
        self.public.gate = threading.Event()
        runner = threading.Thread(target=worker.run)
        runner.start()
        deadline = time.monotonic() + 3
        while not worker.parent.meta("mtf_forward"):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        worker.stop_event.set()
        runner.join(3)
        self.assertFalse(runner.is_alive())
        self.assertFalse(worker._publisher.is_alive())
        self.assertEqual(
            worker.parent.meta("heartbeat"), {"status": "frozen-paper-sentinel"}
        )
        self.assertEqual(worker.parent.meta("mtf_forward")["status"], "stopped")
        other.start()
        other.close()


class PublicWire(unittest.TestCase):
    def setUp(self):
        self.path_mode = "complete"
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                outer.requests.append(self.path)
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                if self.path.startswith("/history"):
                    first, last = int(query["from"][0]), int(query["to"][0])
                    times = list(range(first, last + 60, 60))
                    body = mtf.canonical(
                        {
                            "s": "ok",
                            "t": times,
                            "o": [100] * len(times),
                            "h": [101] * len(times),
                            "l": [99] * len(times),
                            "c": [100.5] * len(times),
                            "v": [0] * len(times),
                        }
                    ).encode()
                else:
                    first, last = (
                        int(query["fromMs"][0]) * 1000,
                        int(query["toMs"][0]) * 1000,
                    )
                    body = raw_samples(
                        "BTC", first, last, missing=outer.path_mode == "missing"
                    )
                if outer.path_mode == "redirect":
                    self.send_response(302)
                    self.send_header("Location", "http://untrusted.invalid/fake-secret")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header(
                    "Content-Length",
                    str(
                        mtf.MAX_PATH_BYTES + 1
                        if outer.path_mode == "oversize"
                        else len(body)
                    ),
                )
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        self.addCleanup(self.stop)
        base = f"http://127.0.0.1:{self.server.server_port}"
        underlying = urllib.request.build_opener(mtf.NoRedirect())

        class LocalOpener:
            def open(self, request, timeout):
                parts = urllib.parse.urlsplit(request.full_url)
                tail = "/history" if parts.path.endswith("/history") else "/prices"
                return underlying.open(base + tail + "?" + parts.query, timeout=timeout)

        self.public = mtf.OraclePublic(
            opener=LocalOpener(), clock=lambda: NOW + 400, timeout=1
        )

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def test_real_http_history_keeps_zero_volume_and_raw_samples_verify_exact_grid(
        self,
    ):
        history = self.public.history(
            "BTC", NOW - 120, NOW - 60, cancelled=lambda: False
        )
        self.assertEqual(len(history["rows"]), 2)
        self.assertEqual([r[-1] for r in history["rows"]], [0, 0])
        result = self.public.path(
            "BTC", NOW + 0.21, NOW + 1.01, cancelled=lambda: False
        )
        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            [p["publish_time_us"] for p in result["points"]],
            [(NOW * 1000000) + x for x in (400000, 600000, 800000, 1000000)],
        )
        self.assertEqual(
            result["proof"]["sha256"], hashlib.sha256(result["raw"]).hexdigest()
        )

    def test_missing_grid_caps_redirects_and_cancellation_are_explicit(self):
        self.path_mode = "missing"
        self.assertEqual(
            self.public.path("BTC", NOW, NOW + 1, cancelled=lambda: False)["status"],
            "pending",
        )
        for mode in ("oversize", "redirect"):
            self.path_mode = mode
            with self.subTest(mode=mode), self.assertRaises(mtf.MtfError) as caught:
                self.public.path("BTC", NOW, NOW + 1, cancelled=lambda: False)
            self.assertNotIn("fake-secret", str(caught.exception))
        before = len(self.requests)
        with self.assertRaisesRegex(mtf.MtfError, "cancelled"):
            self.public.path("BTC", NOW, NOW + 1, cancelled=lambda: True)
        self.assertEqual(len(self.requests), before)

    def test_source_has_no_execution_imports_and_grid_boundaries_use_decision_time(
        self,
    ):
        source = Path(mtf.__file__).read_text()
        imports = [
            node.module
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom)
        ]
        self.assertFalse(
            any(
                name
                and any(
                    token in name
                    for token in (
                        "sdkbridge",
                        "oracle_leverage.cli",
                        "console",
                        "engine",
                        "wallet",
                    )
                )
                for name in imports
            )
        )
        first, last = mtf.path_grid(NOW + 0.21, NOW + 1.01)
        self.assertEqual(
            (first, last), (NOW * 1000000 + 400000, NOW * 1000000 + 1000000)
        )
        self.assertTrue(mtf.adverse_touch("UP", 100, 99.902))
        self.assertFalse(mtf.adverse_touch("UP", 100, 99.90200001))


if __name__ == "__main__":
    unittest.main()

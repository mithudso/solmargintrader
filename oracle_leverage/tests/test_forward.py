"""Durability, causal timing, restart and paper-only worker regressions."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import forward
from oracle_leverage.market import MarketError

NOW = 1_800_000_000


def selection():
    return {
        "schema": "reversal-shape-selection/v1",
        "run_id": "run:fixture",
        "rules": [
            {
                "asset": "BTC",
                "id": "5m:UU:reversal:all",
                "interval_minutes": 5,
                "pair": "UU",
                "shape_group": "all",
                "direction": "DOWN",
                "evidence": "fixture only",
            }
        ],
    }


class FakeMarket:
    def __init__(self, clock):
        self.clock = clock
        self.rows = []
        for i in range(-400, 30):
            opening = 100 + (i + 400) * 0.01
            self.rows.append(
                [
                    NOW + i * 60,
                    opening,
                    opening + 0.02,
                    opening - 0.01,
                    opening + 0.01,
                    1,
                ]
            )
        self.price = 104.1
        self.event_offset = -1
        self.history_calls = []
        self.quote_error = False
        self.on_quote = None
        self.visible_start = None
        self.recoveries = []

    def history(self, asset, interval_minutes, *, cancelled):
        self.history_calls.append((asset, interval_minutes))
        if cancelled():
            raise MarketError("market_cancelled")
        # Deliberately include later fixture candles. The signal must remove them.
        return copy.deepcopy(
            [
                row
                for row in self.rows
                if self.visible_start is None or row[0] >= self.visible_start
            ]
        )

    def fetch(self, asset, start, end, *, cancelled):
        self.recoveries.append((asset, start, end))
        return {
            row[0]: copy.deepcopy(row) for row in self.rows if start <= row[0] < end
        }

    def quote(self, asset):
        if self.quote_error:
            raise MarketError("ticker_stale")
        if self.on_quote is not None:
            self.on_quote()
        now = self.clock()
        return {
            "asset": asset,
            "price": self.price,
            "event_at": now + self.event_offset,
            "observed_at": now,
            "venue": "fixture",
            "product": f"{asset}-USD",
            "quote_currency": "USD",
        }

    def cache_status(self, asset):
        return {
            "venue": "fixture",
            "product": f"{asset}-USD",
            "cached_minutes": len(self.rows),
        }


class ForwardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / "forward"
        self.now = [float(NOW + 5)]
        self.market = FakeMarket(lambda: self.now[0])

    def worker(self, config=None, **kwargs):
        return forward.ForwardWorker(
            self.home,
            config or selection(),
            market=self.market,
            clock=lambda: self.now[0],
            **kwargs,
        )

    def test_current_boundary_uses_exact_causal_helpers_and_commits_first(self):
        with self.worker() as worker:
            original_add = worker.store.add_prediction
            order = []

            def add(value):
                original_add(value)
                # Independent connection sees a committed decision before settlement.
                self.assertEqual(len(worker.store.predictions("open")), 1)
                order.append("committed")

            original_settle = worker._settle

            def settle(*args):
                self.assertEqual(order, ["committed"])
                order.append("settlement-inspection")
                return original_settle(*args)

            with (
                patch.object(worker.store, "add_prediction", add),
                patch.object(worker, "_settle", settle),
                patch.object(
                    forward.strategy, "candles", wraps=forward.strategy.candles
                ) as candles,
                patch.object(
                    forward.strategy,
                    "shape_labels",
                    wraps=forward.strategy.shape_labels,
                ) as labels,
                patch.object(
                    forward.strategy, "setup", wraps=forward.strategy.setup
                ) as setup,
                patch.object(
                    forward.strategy, "matches", wraps=forward.strategy.matches
                ) as matches,
            ):
                worker.tick()
            self.assertTrue(
                all(mock.called for mock in (candles, labels, setup, matches))
            )
            self.assertLess(
                max(row[0] for row in candles.call_args_list[0].args[0]), NOW
            )
            prediction = worker.store.predictions()[0]
            self.assertEqual(prediction["target_start"], NOW)
            self.assertEqual(prediction["target_end"], NOW + 300)
            self.assertEqual(prediction["decision_at"], NOW + 5)
            self.assertEqual(prediction["entry_price"], self.market.price)
            self.assertEqual(prediction["entry_time"], NOW + 4)
            self.assertEqual(prediction["status"], "open")
            self.assertIsNone(prediction["correct"])
            proof = json.loads(prediction["rule_json"])
            self.assertEqual(proof["setup"]["signal_available_at"], NOW)
            self.assertEqual(proof["selection_sha256"], worker.selection_sha256)

    def test_repeated_tick_and_restart_never_duplicate_prediction(self):
        with self.worker() as worker:
            worker.tick()
            worker.tick()
            self.assertEqual(len(worker.store.predictions()), 1)
        with self.worker() as restarted:
            restarted.tick()
            self.assertEqual(len(restarted.store.predictions()), 1)

    def test_late_start_and_restart_do_not_backfill_missed_targets(self):
        self.now[0] = NOW + 31
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(worker.store.predictions(), [])
        self.now[0] = NOW + 299
        with self.worker() as restarted:
            restarted.tick()
            self.assertEqual(restarted.store.predictions(), [])

    def test_last_allowed_second_is_30_and_not_a_historical_fill(self):
        self.now[0] = NOW + 30
        self.market.price = 123.45
        with self.worker() as worker:
            worker.tick()
            row = worker.store.predictions()[0]
            self.assertEqual(row["decision_at"], NOW + 30)
            self.assertEqual(row["entry_price"], 123.45)

    def test_missing_or_zero_volume_outcome_waits_instead_of_fabricating_close(self):
        with self.worker() as worker:
            worker.tick()
            missing = next(row for row in self.market.rows if row[0] == NOW + 240)
            self.market.rows.remove(missing)
            self.now[0] = NOW + 340
            heartbeat = worker.tick()
            self.assertEqual(worker.store.predictions()[0]["status"], "open")
            self.assertEqual(
                heartbeat["assets"]["BTC"]["status"], "waiting-outcome-data"
            )
            self.market.rows.append([*missing[:5], 0])
            worker.tick()
            self.assertEqual(worker.store.predictions()[0]["status"], "open")
            self.market.rows[-1] = missing
            worker.tick()
            self.assertEqual(worker.store.predictions()[0]["status"], "settled")

    def test_settlement_compares_actual_entry_quote_and_subtracts_cost_scenario(self):
        self.market.price = 200
        with self.worker() as worker:
            worker.tick()
            self.now[0] = NOW + 340
            worker.tick()
            row = worker.store.predictions()[0]
            expected_close = next(r[4] for r in self.market.rows if r[0] == NOW + 240)
            self.assertEqual(row["exit_price"], expected_close)
            self.assertEqual(row["correct"], 1)
            gross = (expected_close / 200 - 1) * -10000
            self.assertAlmostEqual(row["gross_bps"], gross)
            self.assertAlmostEqual(row["net_bps"], gross - 16)
            # The target body rises; the forecast relative to actual entry falls.
            self.assertGreater(
                expected_close, next(r[1] for r in self.market.rows if r[0] == NOW)
            )

    def test_stale_future_or_cross_asset_quote_cannot_create_a_decision(self):
        for offset in (-16, 1):
            with self.subTest(offset=offset), self.worker() as worker:
                self.market.event_offset = offset
                heartbeat = worker.tick()
                self.assertEqual(worker.store.predictions(), [])
                self.assertEqual(heartbeat["assets"]["BTC"]["status"], "unavailable")
        self.market.event_offset = -1
        original = self.market.quote
        self.market.quote = lambda asset: {**original(asset), "asset": "ZEC"}
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(worker.store.predictions(), [])

    def test_selection_change_is_refused_after_quote_observation_even_without_trades(
        self,
    ):
        self.now[0] = NOW + 31
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(worker.store.predictions(), [])
            self.assertEqual(worker.store.meta("observation_count"), 1)
        changed = selection()
        changed["run_id"] = "run:changed"
        with (
            self.assertRaisesRegex(forward.ForwardError, "selection_change_refused"),
            self.worker(changed),
        ):
            pass

    def test_selection_hash_is_canonical_and_corrupt_binding_is_refused(self):
        config = selection()
        path = Path(self.directory.name) / "selection.json"
        path.write_text(json.dumps(config, indent=4))
        with self.worker(path) as worker:
            expected = hashlib.sha256(forward.canonical(config).encode()).hexdigest()
            self.assertEqual(worker.store.meta("selection_sha256"), expected)
            worker.tick()
        path.write_text(json.dumps(config, separators=(",", ":")))
        with self.worker(path) as restarted:
            self.assertEqual(restarted.selection_sha256, expected)
            restarted.store.put_meta("selection", {**config, "run_id": "corrupt"})
        with (
            self.assertRaisesRegex(
                forward.ForwardError, "stored_selection_hash_mismatch"
            ),
            self.worker(path),
        ):
            pass

    def test_rule_identity_and_ambiguous_same_target_policies_are_refused(self):
        wrong = selection()
        wrong["rules"][0]["direction"] = "UP"
        with self.assertRaisesRegex(forward.ForwardError, "identity_mismatch"):
            forward.load_selection(wrong)
        duplicated = selection()
        duplicated["rules"].append(
            {
                **duplicated["rules"][0],
                "id": "5m:UU:continuation:all",
                "direction": "UP",
            }
        )
        with self.assertRaisesRegex(forward.ForwardError, "target_rule_ambiguous"):
            forward.load_selection(duplicated)

    def test_single_instance_lock_lasts_until_owned_close(self):
        first, second = self.worker(), self.worker()
        first.start()
        try:
            with self.assertRaisesRegex(forward.ForwardError, "already_running"):
                second.start()
        finally:
            first.close()
        second.start()
        second.close()

    def test_stop_during_quote_does_not_publish_another_decision(self):
        stop = threading.Event()
        self.market.on_quote = stop.set
        worker = self.worker(stop_event=stop)
        worker.run(once=True)
        self.assertEqual(worker.store.predictions(), [])
        self.assertEqual(worker.store.meta("heartbeat")["status"], "stopped")
        replacement = self.worker()
        replacement.start()
        replacement.close()

    def test_unavailable_quote_heartbeat_is_explicit_and_recovers(self):
        self.market.quote_error = True
        with self.worker() as worker:
            heartbeat = worker.tick()
            self.assertTrue(heartbeat["paper_only"])
            self.assertEqual(heartbeat["assets"]["BTC"]["error"], "ticker_stale")
            self.assertEqual(worker.store.predictions(), [])
            self.market.quote_error = False
            worker.tick()
            self.assertEqual(len(worker.store.predictions()), 1)

    def test_old_pending_outcome_is_recovered_after_restart_without_backfill(self):
        with self.worker() as worker:
            worker.tick()
        self.now[0] = NOW + 12 * 3600 + 40
        self.market.visible_start = int(self.now[0]) - 260 * 60
        with self.worker() as restarted:
            restarted.tick()
            rows = restarted.store.predictions()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "settled")
            self.assertEqual(self.market.recoveries, [("BTC", NOW, NOW + 300)])

    def test_current_quote_outage_does_not_prevent_settling_complete_old_target(self):
        with self.worker() as worker:
            worker.tick()
            self.now[0] = NOW + 340
            self.market.quote_error = True
            heartbeat = worker.tick()
            self.assertEqual(worker.store.predictions()[0]["status"], "settled")
            self.assertEqual(heartbeat["assets"]["BTC"]["error"], "ticker_stale")

    def test_missing_outcome_recovery_is_limited_to_once_per_asset_minute(self):
        with self.worker() as worker:
            worker.tick()
            self.market.rows = [row for row in self.market.rows if row[0] != NOW + 240]
            self.now[0] = NOW + 340
            worker.tick()
            self.assertEqual(len(self.market.recoveries), 1)
            self.now[0] += 5
            worker.tick()
            self.assertEqual(len(self.market.recoveries), 1)
            self.assertEqual(worker.store.predictions()[0]["status"], "open")

    def test_missing_setup_minute_cannot_cross_a_shape_warmup_gap(self):
        self.market.rows = [r for r in self.market.rows if r[0] != NOW - 120]
        with self.worker() as worker:
            worker.tick()
            self.assertEqual(worker.store.predictions(), [])

    def test_no_execution_module_or_process_launch_is_imported(self):
        source = Path(forward.__file__).read_text()
        tree = ast.parse(source)
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                modules.append(node.module or "")
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
        for forbidden in (
            "oracle_leverage.cli",
            "oracle_leverage.sdkbridge",
            "oracle_leverage.console",
            "subprocess",
            "solana",
        ):
            self.assertNotIn(forbidden, modules)

    def test_actual_loopback_source_runs_through_durable_decision_and_settlement(self):
        from oracle_leverage.market import LiveMarket
        from oracle_leverage.tests.test_market import Server, iso

        server = Server()
        self.addCleanup(server.close)
        server.payload = {"bid": "100", "ask": "102", "time": iso(self.now[0] - 1)}
        market = LiveMarket(base_url=server.base, clock=lambda: self.now[0])
        with forward.ForwardWorker(
            self.home, selection(), market=market, clock=lambda: self.now[0]
        ) as worker:
            worker.tick()
            first = worker.store.predictions()[0]
            self.assertEqual(first["status"], "open")
            self.assertEqual(first["entry_price"], 101)
            self.assertEqual(first["target_start"], NOW)
            self.now[0] = NOW + 340
            server.payload["time"] = iso(self.now[0] - 1)
            worker.tick()
            settled = worker.store.predictions()[0]
            self.assertEqual(settled["status"], "settled")
            self.assertEqual(settled["exit_price"], 101)
            self.assertEqual(settled["net_bps"], -16)
            self.assertTrue(
                all(call.startswith("/products/BTC-USD/") for call in server.calls)
            )


if __name__ == "__main__":
    unittest.main()

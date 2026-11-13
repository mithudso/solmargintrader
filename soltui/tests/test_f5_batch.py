"""Bounded F5 orchestration tests: no production jobs, network or shared data."""
from __future__ import annotations

import json
import os
import sqlite3
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import numpy as np

from soltui import bgqueue, coinbase_account, config, f5_batch, forwardtest
from soltui.tests.test_bgworker import _ok


class BatchTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.settings = config.default_settings()
        self.settings.data_dir = str(self.data)
        self.settings.start = "2024-01-01"  # F5 must not use the UI's truncated start.
        self.enterContext(mock.patch.object(f5_batch, "_code_id", return_value="fixture-code"))
        card = mock.Mock(buildable=True, data_available=True)
        self.enterContext(mock.patch.object(f5_batch, "_card_map", return_value={"buy_and_hold": card}))
        def jobs(card, horizon, asset, interval, **kwargs):
            return [bgqueue.Job("buy_and_hold", horizon, asset, interval, {})]
        self.enterContext(mock.patch.object(bgqueue, "jobs_for_card", side_effect=jobs))
        self.enterContext(mock.patch("backtester.core.types.validate_bar_arrays", return_value={}))
        self.enterContext(mock.patch.object(f5_batch.bgworker, "ArrayCache", return_value=mock.Mock()))
        self.evaluator = self.enterContext(mock.patch.object(f5_batch.bgworker, "evaluate", side_effect=_ok))

    def plan(self, coins=("SOL",), intervals=("1m",), horizons=("medium",)):
        return f5_batch.create(self.settings, coins, root=self.root, intervals=intervals,
                               strategies=("buy_and_hold",), horizons=horizons)

    def test_resume_preserves_completed_cells_and_hands_off_only_at_terminal_boundary(self):
        (self.data / "SOL_1m.csv").write_text("original history")
        item = self.plan(horizons=("medium", "long"))
        run = item["run_id"]
        tick = mock.Mock(return_value={"recorded": 1, "message": "ok"})
        f5_batch.run(run, root=self.root, max_cells=1, tick=tick, forward_cycles=1)
        self.assertEqual(f5_batch.status(run, root=self.root)["counts"], {"completed": 1, "pending": 1})
        self.assertEqual(self.evaluator.call_count, 1)
        tick.assert_not_called()
        f5_batch.run(run, root=self.root, tick=tick, forward_cycles=1)
        rows = f5_batch.cells(run, root=self.root)
        self.assertEqual([r["state"] for r in rows], ["completed", "completed"])
        self.assertEqual(self.evaluator.call_count, 2)
        self.assertEqual(tick.call_count, 1)
        args, kwargs = tick.call_args
        self.assertEqual(args[2], (1,))
        self.assertEqual(kwargs["signal_interval"], "1m")
        self.assertEqual(kwargs["history"], 1442)
        self.assertEqual(kwargs["db_path"], (self.root / run / "forward.sqlite3").resolve())
        self.assertFalse(kwargs["tune"])
        self.assertEqual(len(f5_batch.attempts(run, rows[0]["id"], root=self.root)), 1)
        with __import__("contextlib").closing(sqlite3.connect(self.root / run / "batch.sqlite3")) as db:
            frozen = json.loads(db.execute("SELECT value FROM meta WHERE key='settings'").fetchone()[0])
        self.assertEqual(frozen["start"], "")
        self.assertEqual(frozen["end"], "")

    def test_missing_data_is_reported_and_eligible_others_forward_as_partial(self):
        (self.data / "SOL_1m.csv").write_text("price")
        run = self.plan(coins=("SOL", "BTC"))["run_id"]
        def fake_tick(asset, trials, horizons, *args, **kwargs):
            return {"recorded": len(trials), "message": "ok", "rows": [
                {"label": trial["label"], "minutes": horizons[0], "last_issued": 1} for trial in trials]}
        tick = mock.Mock(side_effect=fake_tick)
        f5_batch.run(run, root=self.root, tick=tick, forward_cycles=1)
        status = f5_batch.status(run, root=self.root)
        self.assertEqual(status["counts"], {"completed": 1, "missing": 1})
        self.assertEqual(status["problems"][0]["asset"], "BTC")
        self.assertEqual(tick.call_args.args[0], "SOL")
        with __import__("contextlib").closing(sqlite3.connect(self.root / run / "batch.sqlite3")) as db:
            self.assertEqual(json.loads(db.execute("SELECT value FROM meta WHERE key='phase'").fetchone()[0]),
                             "forward_partial")

    def test_changed_series_is_not_mixed_into_prior_results(self):
        path = self.data / "SOL_1m.csv"
        path.write_text("first")
        run = self.plan(horizons=("medium", "long"))["run_id"]
        f5_batch.run(run, root=self.root, max_cells=1)
        path.write_text("different")
        tick = mock.Mock(return_value={"recorded": 0, "message": "waiting"})
        f5_batch.run(run, root=self.root, tick=tick, forward_cycles=1)
        states = f5_batch.status(run, root=self.root)
        self.assertEqual(states["counts"], {"completed": 1, "failed": 1})
        self.assertIn("changed", states["problems"][0]["reason"])
        self.assertEqual(self.evaluator.call_count, 1)

    def test_unrecorded_trials_are_reported_as_partial_forward_coverage(self):
        (self.data / "SOL_1m.csv").write_text("history")
        run = self.plan(horizons=("medium", "long"))["run_id"]
        def fake_tick(asset, trials, horizons, *args, **kwargs):
            return {"recorded": 1, "message": "one trial waiting for warm-up", "rows": [
                {"label": trials[0]["label"], "minutes": horizons[0], "last_issued": 1},
                {"label": trials[1]["label"], "minutes": horizons[0], "last_issued": None}]}
        f5_batch.run(run, root=self.root, tick=fake_tick, forward_cycles=1)
        check = f5_batch.status(run, root=self.root)["forward_checks"][0]
        self.assertEqual((check["trials_recorded"], check["trials_expected"]), (1, 2))
        with __import__("contextlib").closing(sqlite3.connect(self.root / run / "batch.sqlite3")) as db:
            self.assertEqual(json.loads(db.execute("SELECT value FROM meta WHERE key='phase'").fetchone()[0]),
                             "forward_partial")

    def test_leverage_tier_is_not_mislabeled_as_a_leveraged_spot_test(self):
        item = f5_batch.create(self.settings, ["SOL"], root=self.root, intervals=["1m"],
                               strategies=["lev_high"], horizons=["medium"])
        tick = mock.Mock()
        f5_batch.run(item["run_id"], root=self.root, tick=tick, forward_cycles=1)
        result = f5_batch.status(item["run_id"], root=self.root)
        self.assertEqual(result["counts"], {"unsupported": 1})
        self.assertIn("perp-aware", result["problems"][0]["reason"])
        tick.assert_not_called()

    def test_incompatible_code_cannot_resume_or_start_forward(self):
        (self.data / "SOL_1m.csv").write_text("history")
        run = self.plan()["run_id"]
        with mock.patch.object(f5_batch, "_code_id", return_value="changed"):
            tick = mock.Mock()
            f5_batch.run(run, root=self.root, tick=tick, forward_cycles=1)
        self.assertIn("code changed", f5_batch.status(run, root=self.root)["error"])
        tick.assert_not_called()
        self.evaluator.assert_not_called()

    def test_f5_lock_does_not_permit_a_second_batch(self):
        a = self.plan()["run_id"]
        b = self.plan()["run_id"]
        fd = f5_batch._global_lock(self.root)
        try:
            with mock.patch.object(f5_batch.subprocess, "Popen") as spawn:
                with self.assertRaisesRegex(RuntimeError, "another F5"):
                    f5_batch.start(b, root=self.root)
                spawn.assert_not_called()
        finally:
            os.close(fd)
        self.assertEqual(f5_batch.status(a, root=self.root)["phase"], "planned")

    def test_complete_catalog_is_required_and_full_eligible_usd_set_is_used(self):
        path = self.root / "spot.json"
        rows = [{"product_type": "SPOT", "product_id": p + "-USD", "base_currency_id": p,
                 "quote_currency_id": "USD", "status": "online", "trading_disabled": False}
                for p in ("SOL", "BTC", "DOGE")]
        rows += [{"product_type": "SPOT", "product_id": "AAA-USDC", "base_currency_id": "AAA",
                  "quote_currency_id": "USDC", "status": "online"}]
        with mock.patch.object(coinbase_account, "spot_pairs_path", return_value=path):
            path.write_text(json.dumps({"complete": False, "products": rows}))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                f5_batch.catalog_coins()
            path.write_text(json.dumps({"complete": True, "products": rows, "fetched_at": 123}))
            assets, proof = f5_batch.catalog_coins()
        self.assertEqual(assets, ["BTC", "DOGE", "SOL"])
        self.assertEqual(proof["eligible"], 3)
        self.assertEqual(len(proof["sha256"]), 64)


class CandidatePlanTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.settings = config.default_settings()
        self.settings.data_dir = str(self.root)
        self.enterContext(mock.patch.object(f5_batch, "_code_id", return_value="candidate-fixture"))

    def plan(self, **kwargs):
        return f5_batch.create(self.settings, ["SOL"], root=self.root, intervals=["1d"],
                               strategies=["rsi"], horizons=["medium"], **kwargs)

    def test_new_plan_freezes_exact_exclusions_and_evaluates_only_valid_neighbours(self):
        (self.root / "SOL_1d.csv").write_text("fixture history")
        plan = self.plan()
        self.assertEqual(plan["candidates"], {"requested": 13, "eligible": 11, "excluded": 2})
        before = f5_batch.proof(plan["run_id"], "SOL", "1d", root=self.root)["candidate_plans"]
        self.assertEqual({e["job_id"] for e in before[0]["exclusions"]},
                         {"cb9b5d612027b69d", "3873501191efbebb"})
        self.assertTrue(all(e["reason"] == "invalid_parameters" for e in before[0]["exclusions"]))

        def evaluate(job, arrays, engine, settings):
            return replace(_ok(job, arrays, engine, settings), median_sharpe=float(job.params["period"]))

        with mock.patch.object(bgqueue, "jobs_for_card", side_effect=AssertionError("must use frozen candidates")), \
                mock.patch("backtester.core.types.validate_bar_arrays", return_value={}), \
                mock.patch.object(f5_batch.bgworker, "ArrayCache", return_value=mock.Mock()), \
                mock.patch.object(f5_batch.bgworker, "evaluate", side_effect=evaluate) as evaluator:
            f5_batch.run(plan["run_id"], root=self.root, forward_cycles=1,
                         tick=lambda *a, **k: {"recorded": 0, "message": "fixture"})
        rows = f5_batch.cells(plan["run_id"], root=self.root)
        self.assertEqual(rows[0]["state"], "completed")
        self.assertIn("2 of 13 requested candidates excluded before evaluation", rows[0]["reason"])
        self.assertEqual(rows[0]["selected"]["params"]["period"], 28)
        self.assertEqual(rows[0]["candidates"]["excluded"], 2)
        self.assertEqual(evaluator.call_count, 11)
        attempts = f5_batch.attempts(plan["run_id"], rows[0]["id"], root=self.root)
        self.assertEqual(len(attempts), 11)
        self.assertTrue(all(a["state"] == "evaluated" for a in attempts))
        self.assertEqual(f5_batch.status(plan["run_id"], root=self.root)["candidates"], plan["candidates"])
        self.assertEqual(f5_batch.proof(plan["run_id"], "SOL", "1d", root=self.root)["candidate_plans"], before)

    def test_universe_expansion_validates_once_per_template(self):
        original = bgqueue.jobs_for_card
        with mock.patch.object(bgqueue, "jobs_for_card", wraps=original) as generate:
            plan = f5_batch.create(self.settings, ["SOL", "BTC"], root=self.root,
                                   intervals=["1h", "1d"], strategies=["rsi"], horizons=["medium"])
        self.assertEqual(generate.call_count, 1)
        self.assertEqual(plan["candidates"], {"requested": 52, "eligible": 44, "excluded": 8})
        rows = f5_batch.cells(plan["run_id"], root=self.root)
        self.assertEqual(len(rows), 4)
        self.assertEqual(len({e["job_id"] for row in rows for e in row["candidates"]["exclusions"]}), 8)

    def test_proof_does_not_fabricate_candidates_for_an_unplanned_series(self):
        plan = self.plan()
        path = self.root / plan["run_id"] / "batch.sqlite3"
        before = path.read_bytes()
        for asset, interval in (("BTC", "1d"), ("SOL", "1h")):
            with self.subTest(asset=asset, interval=interval):
                proof = f5_batch.proof(plan["run_id"], asset, interval, root=self.root)
                self.assertIsNone(proof["series"])
                self.assertIsNone(proof["candidate_plans"])
        self.assertEqual(path.read_bytes(), before)

    def test_legacy_readers_keep_original_partial_cell_selection_and_attempts(self):
        plan = self.plan()
        path = self.root / plan["run_id"] / "batch.sqlite3"
        original = {"params": {"period": 14, "oversold": 30, "exit_level": 25},
                    "reason": "ValueError: require 0 < oversold < exit_level <= 100"}
        selected = {"name": "rsi", "params": {"period": 28, "oversold": 30, "exit_level": 50}}
        with sqlite3.connect(path) as db:
            db.execute("DELETE FROM meta WHERE key IN ('candidate_templates','candidate_counts')")
            db.execute("UPDATE cell SET state='partial',reason='2 of 13 variants not evaluable',selected=?",
                       (json.dumps(selected),))
            db.execute("INSERT INTO attempt VALUES(1,?,'not_evaluable',?)",
                       ("cb9b5d612027b69d", json.dumps(original)))
        before = path.read_bytes()
        self.assertIsNone(f5_batch.status(plan["run_id"], root=self.root)["candidates"])
        cell = f5_batch.cells(plan["run_id"], root=self.root)[0]
        self.assertEqual(cell["state"], "partial")
        self.assertEqual(cell["selected"], selected)
        self.assertIsNone(cell["candidates"])
        self.assertEqual(f5_batch.attempts(plan["run_id"], 1, root=self.root)[0]["result"], original)
        self.assertIsNone(f5_batch.proof(plan["run_id"], "SOL", "1d", root=self.root)["candidate_plans"])
        self.assertEqual(path.read_bytes(), before)


class GapWindowTests(unittest.TestCase):
    def exercise(self, enabled):
        with TemporaryDirectory() as d:
            root = Path(d)
            settings = config.default_settings()
            settings.data_dir = d
            (root / "SOL_1m.csv").write_text("frozen fixture source")
            ts = np.array([0, 60, 120, 600, 660, 720, 780], dtype="int64")
            arrays = {"ts": ts, **{k: np.full(7, 100.0) for k in ("open", "high", "low", "close")},
                      "volume": np.ones(7)}
            card = mock.Mock(buildable=True, data_available=True)
            job = bgqueue.Job("buy_and_hold", "medium", "SOL", "1m", {})
            with mock.patch.object(f5_batch, "_code_id", return_value="fixture"), \
                 mock.patch.object(f5_batch, "_card_map", return_value={"buy_and_hold": card}), \
                 mock.patch.object(bgqueue, "jobs_for_card", return_value=[job]), \
                 mock.patch.object(f5_batch.bgworker, "ArrayCache", return_value=mock.Mock(get=mock.Mock(return_value=arrays))), \
                 mock.patch.object(f5_batch.bgworker, "evaluate", side_effect=_ok) as evaluate:
                plan = f5_batch.create(settings, ["SOL"], root=root, intervals=["1m"],
                                       strategies=["buy_and_hold"], horizons=["medium"],
                                       longest_contiguous=enabled)
                f5_batch.run(plan["run_id"], root=root, forward_cycles=1,
                             tick=lambda *a, **k: {"recorded": 0, "message": "fixture"})
                cells = f5_batch.cells(plan["run_id"], root=root)
                proof = f5_batch.proof(plan["run_id"], "SOL", "1m", root=root)
                if enabled:
                    self.assertEqual(cells[0]["state"], "completed")
                    np.testing.assert_array_equal(evaluate.call_args.args[1]["ts"], ts[3:])
                    self.assertEqual(proof["data_selection"], {"policy": "longest_contiguous",
                        "gaps_excluded": 1, "source_bars": 7, "selected_bars": 4,
                        "first_ts": 600, "last_ts": 780})
                    self.assertEqual(len(proof["series"]["sha256"]), 64)
                    self.assertIn("4 of 7 original bars", cells[0]["reason"])
                    np.testing.assert_array_equal(arrays["ts"], ts)
                else:
                    self.assertEqual(cells[0]["state"], "failed")
                    self.assertIn("timestamp cadence must equal 1m", cells[0]["reason"])
                    evaluate.assert_not_called()

    def test_start_all_policy_uses_original_contiguous_bars_with_proof(self):
        self.exercise(True)

    def test_existing_batch_policy_keeps_refusing_gaps(self):
        self.exercise(False)


class SignalIntervalTests(unittest.TestCase):
    def test_forward_signal_uses_matching_closed_day_candles(self):
        with TemporaryDirectory() as d, mock.patch.object(config, "CONFIG_DIR", Path(d)):
            now = (1_800_000_000 // 86400 + 3) * 86400 + 4
            def bars(seconds, count):
                last = (now // seconds - 1) * seconds
                ts = np.arange(last - (count - 1) * seconds, last + 1, seconds, dtype="int64")
                values = np.full(count, 100.0)
                return {"ts": ts, "open": values, "high": values, "low": values,
                        "close": values, "volume": np.ones(count)}
            minute = bars(60, 1500)
            daily = bars(86400, 200)
            observed = []
            def predict(spec, mode, values):
                observed.append(values["ts"].copy())
                return 1
            trial = {"label": "daily", "mode": "all", "members": [forwardtest.member("buy_and_hold", {})]}
            with mock.patch.object(forwardtest, "_predict", side_effect=predict):
                result = forwardtest.tick("SOL", [trial], (1440,), 16.0, fetch=lambda *a, **k: minute,
                                          signal_interval="1d", signal_fetch=lambda *a, **k: daily,
                                          db_path=Path(d) / "isolated.sqlite3", history=1442,
                                          clock=lambda: now, code="fixture", tune=False)
            self.assertEqual(result["recorded"], 1)
            self.assertTrue(np.all(np.diff(observed[0]) == 86400))
            self.assertLessEqual(int(observed[0][-1]) + 86400, now)
            self.assertFalse((Path(d) / "forwardtest" / "trials.sqlite3").exists())


class ProcessTests(unittest.TestCase):
    def test_one_missing_cell_uses_detached_worker_and_preserves_other_runners(self):
        import time
        with TemporaryDirectory() as d:
            root = Path(d)
            settings = config.default_settings()
            settings.data_dir = str(root / "empty")
            item = f5_batch.create(settings, ["SOL"], root=root, intervals=["1m"],
                                   strategies=["buy_and_hold"], horizons=["medium"])
            launched = f5_batch.start(item["run_id"], root=root)
            self.assertGreater(launched["pid"], 0)
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                current = f5_batch.status(item["run_id"], root=root)
                if not current["running"]:
                    break
                time.sleep(0.1)
            self.assertFalse(current["running"])
            self.assertEqual(current["counts"], {"missing": 1})
            self.assertEqual(current["phase"], "failed")
            self.assertIn("forward testing did not start", current["error"])

    def test_stop_request_targets_only_observed_instance(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            settings = config.default_settings()
            item = f5_batch.create(settings, ["SOL"], root=root, intervals=["1m"],
                                   strategies=["buy_and_hold"], horizons=["medium"])
            directory = Path(item["directory"])
            old, new = "a" * 32, "b" * 32
            (directory / "worker-token").write_text(old)
            lock = f5_batch._lock(directory)
            try:
                self.assertTrue(f5_batch.stop(item["run_id"], root=root)["stopping"])
                self.assertTrue(f5_batch._StopEvent(directory / ("stop-" + old)).is_set())
                (directory / "worker-token").write_text(new)
                self.assertFalse(f5_batch._StopEvent(directory / ("stop-" + new)).is_set())
            finally:
                os.close(lock)

    def test_old_daily_outcome_stays_pending_until_matching_minutes_are_available(self):
        with TemporaryDirectory() as d, mock.patch.object(config, "CONFIG_DIR", Path(d)):
            now = [(1_800_000_000 // 86400 + 3) * 86400 + 4]
            coverage = [1500]
            def bars(seconds, count):
                last = (now[0] // seconds - 1) * seconds
                ts = np.arange(last - (count - 1) * seconds, last + 1, seconds, dtype="int64")
                values = np.full(count, 100.0)
                return {"ts": ts, "open": values, "high": values, "low": values,
                        "close": values, "volume": np.ones(count)}
            trial = {"label": "daily", "mode": "all", "members": [forwardtest.member("buy_and_hold", {})]}
            opts = dict(fetch=lambda *a, **k: bars(60, coverage[0]), signal_interval="1d",
                        signal_fetch=lambda *a, **k: bars(86400, 200), db_path=Path(d) / "f5.sqlite3",
                        history=1442, clock=lambda: now[0], code="fixture", tune=False, expire_missing=False)
            with mock.patch.object(forwardtest, "_predict", return_value=1):
                first = forwardtest.tick("SOL", [trial], (1440,), 16.0, **opts)
                self.assertEqual(first["recorded"], 1)
                now[0] += 86400 + 120
                coverage[0] = 600
                second = forwardtest.tick("SOL", [trial], (1440,), 16.0, **opts)
                self.assertEqual(second["rows"][0]["expired"], 0)
                self.assertGreaterEqual(second["rows"][0]["pending"], 1)
                coverage[0] = 1500
                third = forwardtest.tick("SOL", [trial], (1440,), 16.0, **opts)
                self.assertGreaterEqual(third["rows"][0]["resolved"], 1)

    def test_each_supported_interval_uses_matching_signal_cadence(self):
        with TemporaryDirectory() as d, mock.patch.object(config, "CONFIG_DIR", Path(d)):
            now = 1_800_000_004
            def bars(seconds, count=200):
                last = (now // seconds - 1) * seconds
                ts = np.arange(last - (count - 1) * seconds, last + 1, seconds, dtype="int64")
                v = np.full(count, 100.0)
                return {"ts": ts, "open": v, "high": v, "low": v, "close": v, "volume": np.ones(count)}
            trial = {"label": "chosen", "mode": "all", "members": [forwardtest.member("buy_and_hold", {})]}
            for interval, minutes in f5_batch.INTERVAL_MINUTES.items():
                with self.subTest(interval=interval):
                    captured = []
                    def predict(spec, mode, values):
                        captured.append(values["ts"].copy())
                        return 1
                    def fetch(symbol, **kwargs):
                        return bars(kwargs["seconds"])
                    with mock.patch.object(forwardtest, "_predict", side_effect=predict):
                        result = forwardtest.tick("SOL", [trial], (minutes,), 16.0,
                            fetch=fetch, signal_interval=interval, signal_fetch=fetch,
                            db_path=Path(d) / f"{interval}.sqlite3", history=1442,
                            clock=lambda: now, code="fixture", tune=False)
                    self.assertEqual(result["recorded"], 1)
                    self.assertTrue(np.all(np.diff(captured[0]) == minutes * 60))
                    self.assertLessEqual(int(captured[0][-1]) + minutes * 60, now)

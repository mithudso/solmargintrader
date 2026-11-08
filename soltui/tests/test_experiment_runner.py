"""Native evidence boundaries, replay control and promotion recovery (no network)."""
from __future__ import annotations

import csv
import io
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from backtester.core.data import SyntheticLoader
from soltui import bots, config, pricefeed
from soltui import experiment_runner as runner
from soltui.config import Settings
from soltui.experiments import ExperimentError, ExperimentStore
from soltui.tests.test_bots import tri_quotes, write_hourly, write_snapshots

SPACE = {"range_pct": {"kind": "enum", "values": [5.0]}}


class NativeExperiments(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        patch = mock.patch.object(config, "CONFIG_DIR", self.root / "config")
        patch.start()
        self.addCleanup(patch.stop)
        # Other implementation workers may still be writing source. Dedicated
        # context-mutation tests below exercise changed code explicitly.
        patch = mock.patch.object(runner, "_code_fingerprint", return_value="test-code-v1")
        patch.start()
        self.addCleanup(patch.stop)
        self.store = ExperimentStore()
        self.settings = Settings(data_dir=str(self.data))
        self.ts = write_hourly(self.data, "SOL", n=24 * 12)
        bots._HOURLY_CACHE.clear()

    def prepare(self, **kwargs):
        return runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"],
                                         windows=4, window_days=3, store=self.store, **kwargs)

    def fake(self, bot, cfg, data, interval, costs):
        return {"results": {"total_return": 0.03 if cfg["range_pct"] == 5 else 0.01,
                            "trades": 4, "costs_usd": 2.0, "max_drawdown": -0.04, "sharpe": 1.2}}

    def execute(self, run, **kwargs):
        with mock.patch.object(bots, "run_bars", side_effect=self.fake):
            return runner.run_experiment(run["id"], self.settings, store=self.store, **kwargs)

    def reset(self, run):
        self.store.update_run(run["id"], status="queued")

    def test_preview_never_simulates_and_actual_workload_includes_only_frozen_pair_on_final(self):
        with mock.patch.object(bots, "run_bars") as simulator:
            preview = runner.preview_experiment("grid", self.settings, space=SPACE, coins=["SOL"],
                                                windows=4, window_days=3)
        simulator.assert_not_called()
        self.assertEqual((preview["candidate_count"], preview["exploration_cells"], preview["holdout_cells"]), (2, 4, 4))
        self.assertEqual(preview["evaluations"], 8)
        with self.assertRaisesRegex(ExperimentError, "budget"):
            runner.preview_experiment("grid", self.settings, space=SPACE, windows=4, window_days=3, max_evaluations=7)
        with self.assertRaises(ExperimentError):
            runner.preview_experiment("grid", self.settings, windows=True)

    def test_exploration_preserves_rich_cells_and_never_evaluates_holdout(self):
        run = self.prepare()
        report = self.execute(run)
        cells = self.store.cells(run["id"], include_holdout=True)
        self.assertEqual(report["status"], "explored")
        self.assertEqual(len(cells), 4)
        self.assertEqual({c["split"] for c in cells}, {"train", "validation"})
        self.assertEqual(cells[0]["metrics"]["costs_usd"], 2.0)
        self.assertIn("data_fingerprint", cells[0])
        self.assertFalse(report["verdict"]["adopted"])
        self.assertTrue(all(r["test_median"] is None for r in report["table"]))

    def test_final_freezes_candidate_before_testing_and_keeps_evidence_floor(self):
        run = self.prepare()
        result = self.execute(run, final=True, adopt=True)
        self.assertEqual(self.store.get_run(run["id"])["frozen_candidate"], "1")
        self.assertEqual(result["verdict"]["wins"], 2)
        self.assertFalse(result["verdict"]["reliable"])
        self.assertFalse(result["verdict"]["adopted"])
        self.assertEqual(len(self.store.cells(run["id"], include_holdout=True)), 8)

    def test_pause_acknowledges_after_one_committed_cell_and_resume_reuses_it(self):
        run = self.prepare()
        def pause(frac, message):
            self.store.request_control(run["id"], "pause")
        result = self.execute(run, progress=pause)
        self.assertEqual(result["status"], "paused")
        self.assertEqual(len(self.store.cells(run["id"])), 1)
        self.reset(run)
        with mock.patch.object(bots, "run_bars", side_effect=self.fake) as simulator:
            result = runner.run_experiment(run["id"], self.settings, store=self.store)
        self.assertEqual(result["status"], "explored")
        self.assertEqual(simulator.call_count, 3)

    def test_cancel_during_evaluation_finishes_cell_without_adopting(self):
        run = self.prepare()
        def cancel(*args):
            self.store.request_control(run["id"], "cancel")
            return self.fake(*args)
        with mock.patch.object(bots, "run_bars", side_effect=cancel):
            result = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        self.assertEqual(result["status"], "cancelled")
        self.assertEqual(len(self.store.cells(run["id"], include_holdout=True)), 1)
        self.assertIsNone(self.store.get_run(run["id"])["frozen_candidate"])

    def test_partial_final_metrics_stay_sealed_on_pause(self):
        run = self.prepare()
        def pause_final(frac, message):
            if "holdout" in message:
                self.store.request_control(run["id"], "pause")
        result = self.execute(run, final=True, progress=pause_final)
        self.assertEqual(result["status"], "paused")
        self.assertEqual(result["verdict"]["test_cells"], 0)
        self.assertTrue(all(row["test_median"] is None for row in result["table"]))
        self.assertTrue(all(row["current_test_median"] is None and row["pick_wins"] == 0 for row in result["per_coin"]))
        self.assertEqual(len(self.store.cells(run["id"], split="holdout", include_holdout=True)), 1)
        self.assertFalse(self.store.cells(run["id"], split="holdout"))

    def test_changed_historical_bytes_with_preserved_stat_metadata_refuse_cached_resume(self):
        run = self.prepare()
        self.execute(run)
        path = self.data / "SOL_1h.csv"
        stat = path.stat()
        rows = list(csv.reader(io.StringIO(path.read_text())))
        old = rows[1][1]
        rows[1][1] = old[:-1] + ("1" if old[-1] != "1" else "2")
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerows(rows)
        path.write_text(stream.getvalue())
        self.assertEqual(path.stat().st_size, stat.st_size)
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaisesRegex(ExperimentError, "historical evidence changed"):
            self.execute(run)

    def test_append_only_data_does_not_shift_frozen_windows_or_repeat_cells(self):
        run = self.prepare()
        self.execute(run)
        more = SyntheticLoader(n_bars=24, seed=5, start_ts=int(self.ts[-1]) + 3600).load("SOL", None, None, "1h")
        more.to_csv(self.data / "SOL_1h.csv", mode="a", index=False, header=False)
        with mock.patch.object(bots, "run_bars") as simulator:
            result = runner.run_experiment(run["id"], self.settings, store=self.store)
        simulator.assert_not_called()
        self.assertEqual(result["status"], "explored")
        self.assertEqual(self.store.get_run(run["id"])["spec"]["windows"], run["spec"]["windows"])

    def test_changed_cost_or_code_context_refuses_resume(self):
        run = self.prepare()
        self.execute(run)
        changed = Settings(data_dir=str(self.data), fee_bps=8.0)
        with self.assertRaisesRegex(ExperimentError, "cost fingerprint"):
            runner.run_experiment(run["id"], changed, store=self.store)
        with mock.patch.object(runner, "_code_fingerprint", return_value="different-code"), self.assertRaisesRegex(ExperimentError, "code fingerprint"):
            runner.run_experiment(run["id"], self.settings, store=self.store)

    def test_runtime_provenance_is_frozen_and_version_change_refuses_reuse(self):
        run = self.prepare()
        runtime = runner._runtime_descriptor()
        self.assertEqual(run["spec"]["runtime"], runtime)
        self.assertEqual(set(runtime), {"python", "implementation", "machine", "system", "numpy", "pandas"})
        self.execute(run)
        changed = {**runtime, "numpy": runtime["numpy"] + "-different"}
        with mock.patch.object(runner, "_runtime_descriptor", return_value=changed), mock.patch.object(bots, "run_bars") as simulator, self.assertRaisesRegex(ExperimentError, "runtime fingerprint changed"):
            runner.run_experiment(run["id"], self.settings, store=self.store)
        simulator.assert_not_called()
        self.assertEqual(run["spec"]["runtime"], self.store.get_run(run["id"])["spec"]["runtime"])

    def test_repeat_final_with_changed_costs_cannot_reopen_spent_dates(self):
        first = self.prepare()
        self.execute(first, final=True)
        changed = Settings(data_dir=str(self.data), fee_bps=8.0)
        second = runner.prepare_experiment("grid", changed, space=SPACE, coins=["SOL"], windows=4, window_days=3, store=self.store)
        with mock.patch.object(bots, "run_bars", side_effect=self.fake):
            result = runner.run_experiment(second["id"], changed, final=True, adopt=True, store=self.store)
        self.assertIn("spent dates", result["verdict"]["reason"])
        self.assertFalse(result["verdict"]["adopted"])
        self.assertFalse(self.store.cells(second["id"], split="holdout", include_holdout=True))

    def test_wider_window_cannot_reclassify_prior_exploration_as_untouched_final(self):
        first = runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"], windows=2, window_days=3, store=self.store)
        self.execute(first)
        second = runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"], windows=2, window_days=6, store=self.store)
        result = self.execute(second, final=True)
        self.assertIn("exposed to exploration", result["verdict"]["reason"])
        self.assertEqual(result["verdict"]["test_cells"], 0)

    def test_failure_is_explicit_and_cannot_promote(self):
        run = self.prepare()
        with mock.patch.object(bots, "run_bars", side_effect=ValueError("fixture invalid prices")):
            report = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        cells = self.store.cells(run["id"], include_holdout=True)
        self.assertTrue(cells)
        self.assertTrue(all(c["status"] == "failed" and "invalid prices" in c["error"] for c in cells))
        self.assertFalse(report["verdict"]["adopted"])
        self.assertTrue(all(c["metrics"] == {} for c in cells))

    def test_nonfinite_primary_metric_is_failure_and_optional_risk_stays_unknown(self):
        run = self.prepare()
        with mock.patch.object(bots, "run_bars", return_value={"results": {"total_return": float("nan")}}):
            runner.run_experiment(run["id"], self.settings, store=self.store)
        self.assertTrue(all(c["status"] == "failed" for c in self.store.cells(run["id"])))
        second = self.prepare()
        with mock.patch.object(bots, "run_bars", return_value={"results": {"total_return": 0.0, "sharpe": float("nan")}}):
            runner.run_experiment(second["id"], self.settings, store=self.store)
        self.assertTrue(all(c["metrics"]["sharpe"] is None for c in self.store.cells(second["id"])))

    def test_no_data_returns_honest_report(self):
        run = runner.prepare_experiment("grid", self.settings, coins=["NOPE"], windows=4, window_days=3, store=self.store)
        result = runner.run_experiment(run["id"], self.settings, store=self.store, final=True)
        self.assertIn("NOPE", result["skipped"])
        self.assertFalse(result["verdict"]["adopted"])
        self.assertEqual(result["completed_cells"], 0)

    def test_legacy_history_fences_old_dates_and_fresh_install_has_no_fence(self):
        self.assertIsNone(self.prepare()["spec"]["legacy_cutoff"])
        at = time.time()
        bots._write_json(bots.history_path("grid"), {"runs": 1, "tried": [], "log": [{"run": 1, "at": at}]})
        bots._write_json(bots.optimize_path("grid"), {"bot": "grid", "at": at, "per_coin": []})
        run = self.prepare()
        self.assertEqual(run["spec"]["legacy_cutoff"], at)
        result = self.execute(run, final=True)
        self.assertIn("legacy optimization", result["verdict"]["reason"])
        self.assertFalse(self.store.cells(run["id"], split="holdout", include_holdout=True))

    def test_legacy_exposure_recorded_after_prepare_still_blocks_final(self):
        run = self.prepare()
        self.assertIsNone(run["spec"]["legacy_cutoff"])
        at = time.time()
        bots._write_json(bots.optimize_path("grid"), {"bot": "grid", "at": at, "per_coin": []})
        result = self.execute(run, final=True)
        self.assertIn("legacy optimization", result["verdict"]["reason"])
        self.assertFalse(self.store.cells(run["id"], split="holdout", include_holdout=True))

    def test_active_lock_refuses_duplicate_execution_and_releases_on_exit(self):
        run = self.prepare()
        with runner._lock(self.store, "run:" + run["id"]):
            self.assertTrue(runner.run_active(run["id"], self.store))
            with self.assertRaisesRegex(ExperimentError, "active worker"):
                self.execute(run)
        self.assertFalse(runner.run_active(run["id"], self.store))

    def test_import_cannot_run_or_change_its_lifecycle(self):
        run_id = self.store.create_run({"bot": "grid", "source": "tradingview", "candidates": [bots.GRID_DEFAULTS]})
        self.store.update_run(run_id, status="imported")
        with self.assertRaisesRegex(ExperimentError, "imports cannot promote"):
            runner.run_experiment(run_id, self.settings, final=True, adopt=True, store=self.store)
        self.assertEqual(self.store.get_run(run_id)["status"], "imported")

    def _reliable_run(self):
        coins = ["SOL", "AAA", "BBB", "CCC", "DDD"]
        for seed, coin in enumerate(coins[1:], 5):
            write_hourly(self.data, coin, n=24 * 12, seed=seed)
        return runner.prepare_experiment("grid", self.settings, space=SPACE, coins=coins, windows=4, window_days=3, store=self.store)

    def test_completed_final_can_be_reviewed_then_adopted_without_reevaluation(self):
        run = self._reliable_run()
        report = self.execute(run, final=True, adopt=False)
        self.assertTrue(report["verdict"]["reliable"])
        self.assertFalse(report["verdict"]["adopted"])
        with mock.patch.object(bots, "run_bars") as simulator:
            report = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        simulator.assert_not_called()
        self.assertTrue(report["verdict"]["adopted"])
        self.assertEqual(bots.get_config("grid")["range_pct"], 5.0)

    def test_manual_baseline_edit_cannot_be_overwritten_by_promotion(self):
        run = self._reliable_run()
        self.execute(run)
        bots.save_config("grid", {"range_pct": 20.0})
        report = self.execute(run, final=True, adopt=True)
        self.assertFalse(report["verdict"]["adopted"])
        self.assertIn("baseline changed", report["verdict"]["reason"])
        self.assertEqual(bots.get_config("grid")["range_pct"], 20.0)
        with self.assertRaisesRegex(bots.BotError, "baseline changed"):
            bots.save_config("grid", {"range_pct": 5.0}, expected=bots.GRID_DEFAULTS)

    def test_config_saved_before_report_crash_recovers_own_adoption_receipt(self):
        run = self._reliable_run()
        original = bots.save_config
        def crash_after_save(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError("fixture died after atomic config save")
        with mock.patch.object(bots, "run_bars", side_effect=self.fake), mock.patch.object(bots, "save_config", side_effect=crash_after_save), self.assertRaisesRegex(OSError, "died after atomic"):
            runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        self.assertEqual(bots.get_config("grid")["range_pct"], 5.0)
        with mock.patch.object(bots, "run_bars") as simulator:
            report = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        simulator.assert_not_called()
        self.assertTrue(report["verdict"]["adopted"])
        self.assertTrue(report["verdict"]["recovered"])
        matches = [r for r in bots._all_configs()["history"] if run["id"] in r["reason"]]
        self.assertEqual(len(matches), 1)

    def test_failed_cells_retry_on_explicit_resume_before_candidate_is_frozen(self):
        run = self.prepare()
        with mock.patch.object(bots, "run_bars", side_effect=ValueError("transient fixture failure")):
            result = runner.run_experiment(run["id"], self.settings, final=True, store=self.store)
        self.assertEqual(result["status"], "explored")
        self.assertIsNone(self.store.get_run(run["id"])["frozen_candidate"])
        result = self.execute(run, final=True)
        self.assertEqual(result["failed_cells"], 0)
        self.assertEqual(self.store.get_run(run["id"])["frozen_candidate"], "1")

    def test_unrelated_failed_candidate_does_not_veto_a_matched_winner(self):
        coins = ["SOL", "AAA", "BBB", "CCC", "DDD"]
        for seed, coin in enumerate(coins[1:], 5):
            write_hourly(self.data, coin, n=24 * 12, seed=seed)
        run = runner.prepare_experiment("grid", self.settings,
            space={"range_pct": {"kind": "enum", "values": [5.0, 25.0]}},
            coins=coins, windows=4, window_days=3, store=self.store)
        def some_fail(bot, cfg, data, interval, costs):
            if cfg["range_pct"] == 25:
                raise ValueError("unrelated candidate failed")
            return self.fake(bot, cfg, data, interval, costs)
        with mock.patch.object(bots, "run_bars", side_effect=some_fail):
            result = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        self.assertGreater(result["failed_cells"], 0)
        self.assertTrue(result["verdict"]["adopted"])
        self.assertEqual(bots.get_config("grid")["range_pct"], 5)

    def test_failed_baseline_cannot_promote(self):
        run = self.prepare()
        def fail_baseline(bot, cfg, data, interval, costs):
            if cfg["range_pct"] == 15:
                raise ValueError("baseline failed")
            return self.fake(bot, cfg, data, interval, costs)
        with mock.patch.object(bots, "run_bars", side_effect=fail_baseline):
            result = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        self.assertFalse(result["verdict"]["adopted"])
        self.assertIsNone(self.store.get_run(run["id"])["frozen_candidate"])

    def test_coin_can_adopt_a_labeled_incremental_improvement_with_three_holdouts(self):
        write_hourly(self.data, "SOL", n=24 * 18)
        run = runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"],
                                        config_coin="SOL", windows=6, window_days=3, store=self.store)
        result = self.execute(run, final=True, adopt=True)
        self.assertTrue(result["verdict"]["adopted"])
        self.assertFalse(result["verdict"]["reliable"])
        self.assertEqual(result["verdict"]["confidence"], "tentative")
        self.assertIn("not statistically confirmed", result["verdict"]["reason"])
        self.assertEqual(bots.get_config("grid", "SOL")["range_pct"], 5)
        self.assertEqual(bots.get_config("grid")["range_pct"], 15)

    def test_coin_manual_mode_blocks_automatic_promotion(self):
        write_hourly(self.data, "SOL", n=24 * 18)
        run = runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"],
                                        config_coin="SOL", windows=6, window_days=3, store=self.store)
        bots.save_config("grid", {}, coin="SOL", mode="manual")
        result = self.execute(run, final=True, adopt=True)
        self.assertFalse(result["verdict"]["adopted"])
        self.assertIn("manual mode", result["verdict"]["reason"])
        self.assertEqual(bots.get_config("grid", "SOL")["range_pct"], 15)

    def test_ledger_backed_per_coin_summary_is_not_mistaken_for_legacy_exposure(self):
        bots._write_json(bots.optimize_path("grid"), {"at": time.time(), "skipped": {},
                         "reports": {"SOL": {"experiment_id": "known-run"}}})
        self.assertIsNone(runner._legacy_cutoff(self.store, "grid"))

    def test_incremental_winner_can_survive_one_missing_holdout_with_coverage_disclosed(self):
        write_hourly(self.data, "SOL", n=24 * 60)
        run = runner.prepare_experiment("grid", self.settings, space=SPACE, coins=["SOL"],
                                        config_coin="SOL", windows=20, window_days=3, store=self.store)
        missing_start = next(w["start"] for w in run["spec"]["windows"] if w["split"] == "holdout")
        def one_failure(bot, cfg, data, interval, costs):
            if cfg["range_pct"] == 5 and int(data["ts"][0]) == missing_start:
                raise ValueError("one failed holdout")
            return self.fake(bot, cfg, data, interval, costs)
        with mock.patch.object(bots, "run_bars", side_effect=one_failure):
            result = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        self.assertTrue(result["verdict"]["adopted"])
        self.assertEqual(result["verdict"]["confidence"], "tentative")
        self.assertIn("9/10 matched", result["verdict"]["reason"])

    def test_last_boundary_pause_wins_over_adoption_and_seals_report(self):
        run = self._reliable_run()
        finalize = self.store.finalize_run
        def pause_before_commit(run_id, report, **kwargs):
            self.store.request_control(run_id, "pause")
            return finalize(run_id, report, **kwargs)
        with mock.patch.object(self.store, "finalize_run", side_effect=pause_before_commit):
            result = self.execute(run, final=True, adopt=True)
        self.assertEqual(result["status"], "paused")
        self.assertFalse(result["verdict"]["adopted"])
        self.assertEqual(result["verdict"]["test_cells"], 0)
        self.assertEqual(bots.get_config("grid"), bots.GRID_DEFAULTS)
        self.reset(run)
        with mock.patch.object(bots, "run_bars") as simulator:
            result = runner.run_experiment(run["id"], self.settings, final=True, adopt=True, store=self.store)
        simulator.assert_not_called()
        self.assertTrue(result["verdict"]["adopted"])

    def test_manual_save_matching_winner_does_not_forge_own_adoption_receipt(self):
        run = self._reliable_run()
        self.execute(run)
        bots.save_config("grid", {"range_pct": 5.0}, reason="manual edit")
        result = self.execute(run, final=True, adopt=True)
        self.assertFalse(result["verdict"]["adopted"])
        self.assertIn("baseline changed", result["verdict"]["reason"])

    def test_process_death_releases_lock_and_preserves_only_committed_cells(self):
        run = self.prepare()
        marker = self.root / "second-cell-started"
        script = """
import sys, time
from pathlib import Path
from soltui import bots, config, experiment_runner as runner
from soltui.config import Settings
from soltui.experiments import ExperimentStore
run_id, root, data, marker, config_dir = sys.argv[1:]
config.CONFIG_DIR = Path(config_dir)
runner._code_fingerprint = lambda: "test-code-v1"
calls = 0
def evaluate(bot, cfg, arrays, interval, costs):
    global calls
    calls += 1
    if calls == 2:
        Path(marker).write_text("inside uncommitted second evaluation")
        time.sleep(30)
    return {"results": {"total_return": .03 if cfg["range_pct"] == 5 else .01}}
bots.run_bars = evaluate
runner.run_experiment(run_id, Settings(data_dir=data), store=ExperimentStore(root))
"""
        child = subprocess.Popen([sys.executable, "-c", script, run["id"], str(self.store.root),
                                  str(self.data), str(marker), str(config.CONFIG_DIR)],
                                 cwd=Path(__file__).resolve().parents[2], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 8
            while not marker.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(marker.exists(), "child did not reach the controlled evaluation boundary")
            self.assertTrue(runner.run_active(run["id"], self.store))
            child.kill()
            child.communicate(timeout=5)
            self.assertFalse(runner.run_active(run["id"], self.store))
            self.assertEqual(len(self.store.cells(run["id"])), 1)
            with mock.patch.object(bots, "run_bars", side_effect=self.fake) as simulator:
                result = runner.run_experiment(run["id"], self.settings, store=self.store)
            self.assertEqual(result["status"], "explored")
            self.assertEqual(simulator.call_count, 3)
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

    def test_triangle_uses_recorded_hours_and_checkpoints_each_triangle_candidate(self):
        t0 = 1_794_000_000 // 3600 * 3600
        rows = [(t0 + hour * 3600 + k, tri_quotes(t0 + hour * 3600 + k, 0.0505))
                for hour in range(4) for k in range(65)]
        write_snapshots(pricefeed.prices_dir(), rows)
        products = ["ETH-USD", "BTC-USD", "ETH-BTC"]
        with mock.patch.object(bots, "_triangle_products", return_value=products):
            run = runner.prepare_experiment("triangle", self.settings, space={}, windows=4, store=self.store)
        report = runner.run_experiment(run["id"], self.settings, store=self.store)
        cells = self.store.cells(run["id"], include_holdout=True)
        self.assertEqual(len(cells), 2)
        self.assertEqual({c["split"] for c in cells}, {"train", "validation"})
        self.assertEqual(cells[0]["data_source"], "recorded")
        self.assertIsNotNone(cells[0]["metrics"]["pnl_usd"])
        self.assertIsNone(cells[0]["metrics"]["max_drawdown"])
        self.assertEqual(report["metric_units"], "USD")
        final = runner.run_experiment(run["id"], self.settings, store=self.store, final=True)
        self.assertEqual(len(self.store.cells(run["id"], include_holdout=True)), 4)
        self.assertFalse(final["verdict"]["adopted"])


if __name__ == "__main__":
    unittest.main()

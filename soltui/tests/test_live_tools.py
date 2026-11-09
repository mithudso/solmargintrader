"""The rail reads bounded caches and never turns a poll into a paper/live job."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

import soltui
from soltui import bots, config, council, live_tools as rail, paper_workflow


class LiveRail(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.enterContext(patch.object(config, "CONFIG_DIR", self.directory))
        self.enterContext(patch.dict(os.environ, {"SOLTUI_SUPPORT_DIR": str(self.directory / "support"),
            "SOLMARGINTRADER_STORAGE": str(self.directory / "storage")}))
        self.settings = config.Settings(data_dir=str(self.directory / "data"))
        self.session = {"id": "actual-ada-session", "asset": "ADA", "bot": "grid", "started_at": 100., "stopped_at": None,
            "fee_bps": 6., "slippage_bps": 2., "config": {"range_pct": 1.5, "rungs": 5, "capital_usd": 1000., "spacing": "geom", "deadband_bps": 25.}}

    def save_session(self):
        rail.write(bots.forward_path(), {"grid": self.session})

    def replay(self):
        return {"forward": self.session, "bars": 922, "snapshots": 52984, "bridged_minutes": 1, "stopped_at_gap": None,
                "last_snapshot": "2026-11-09 14:31 UTC", "results": {"final_equity": 1002.37,
                    "realized_pnl_usd": 2.37, "total_return": .00237, "gross_captured_usd": 3.01,
                    "costs_usd": .64, "round_trips": 2, "hold_return": .0152, "excess_return": -.01283}}

    def test_empty_rail_and_workflow_status_are_read_only(self):
        with patch.object(bots, "forward_status", side_effect=AssertionError("No replay in polling")), patch.object(
                rail.subprocess, "Popen", side_effect=AssertionError("No job starts in polling")):
            result = rail.rail("SOL")
            workflow = paper_workflow.status("SOL")
        self.assertIsNone(result["observed_at"])
        self.assertIsNone(result["grid"]["pnl"])
        self.assertFalse(workflow["running"])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_saved_grid_pnl_is_session_matched_and_not_a_historical_winner(self):
        self.save_session()
        with patch.object(bots, "forward_status", return_value=self.replay()) as replay:
            cached = rail.grid_snapshot(now=200., refresh=True)
            result = rail.rail("SOL", now=210.)
        self.assertEqual(replay.call_count, 1)
        self.assertEqual(result["grid"]["asset"], "ADA")
        self.assertAlmostEqual(result["grid"]["pnl"]["net_usd"], 2.37)
        self.assertEqual(result["grid"]["pnl"]["mode"], "paper")
        self.assertEqual(cached["coverage"]["bridged_minutes"], 1)
        self.assertLess(cached["pnl"]["excess_return"], 0)
        self.session["id"] = "new-session"
        self.save_session()
        changed = rail.rail("SOL", now=211.)
        self.assertIsNone(changed["grid"]["pnl"])
        self.assertFalse(changed["grid"]["available"])

    def test_stale_and_gap_coverage_remain_visible(self):
        self.save_session()
        replay = self.replay()
        replay["stopped_at_gap"] = "2026-11-09 02:00 UTC"
        with patch.object(bots, "forward_status", return_value=replay):
            result = rail.grid_snapshot(now=200., refresh=True)
        self.assertEqual(result["state"], "waiting")
        self.assertTrue(result["running"])
        self.assertIn("Coverage ended", result["message"])
        self.assertTrue(rail.grid_snapshot(now=400.)["stale"])

    def test_saved_running_grid_reports_waiting_when_recorder_is_stale(self):
        self.save_session()
        replay = {**self.replay(), "recorder": {"running": False, "live": False, "snapshot_age_s": 70.}}
        with patch.object(bots, "forward_status", return_value=replay):
            result = rail.grid_snapshot(now=200., refresh=True)
        self.assertTrue(result["running"])
        self.assertEqual(result["state"], "waiting")
        self.assertIn("fresh recorded stream", result["message"])
        self.assertTrue(result["available"])

    def test_update_separates_wallet_paper_and_activity_and_caches_public_reads(self):
        state = council._initial(council.config())
        state.update(position={"initial_equity": 9900.}, equity=9950.)
        state.update(mode="paper", state="waiting", running=True, config=council.config(), fills=[])
        external = Mock(return_value={"items": [{"id": "external", "at": 190., "mode": "wallet", "chain": "base", "summary": "Observed transaction"}],
            "coverage": [{"chain": "base", "complete": False}], "gaps": ["Only configured/indexed accounts covered"]})
        module = SimpleNamespace(snapshot=external)
        with patch.object(soltui, "wallet_activity", module, create=True), patch.dict(sys.modules, {"soltui.wallet_activity": module}), patch.object(
                rail.live_score, "prediction_snapshot", return_value={"aggregate": {"available": False}, "rows": []}), patch.object(
                rail.prediction_recovery, "health", return_value={"state": "running", "running": True}), patch.object(
                council, "status", return_value=state), patch.object(rail, "optimizer_snapshot", return_value={"state": "waiting"}), patch.object(
                rail.portfolio, "load_last_scan", return_value={"saved_at": 180., "result": {"total_usd": 123., "partial": False}}), patch.object(
                rail, "_local_actions", return_value=[]):
            first = rail.update("SOL", self.settings, now=200.)
            rail.update("ETH", self.settings, now=210.)
        self.assertEqual(external.call_count, 1)
        self.assertEqual(first["wallet"]["total_usd"], 123.)
        self.assertIsNone(first["wallet"]["pnl"])
        self.assertEqual(first["council"]["pnl"]["realized_usd"], -100.)
        self.assertEqual(first["council"]["pnl"]["unrealized_usd"], 50.)
        self.assertEqual(first["activity"]["items"][0]["mode"], "wallet")
        self.assertTrue(first["activity"]["gaps"])

    def test_parallel_refreshes_launch_one_worker_and_bound_requested_assets(self):
        inherited = []
        class Child:
            def wait(self):
                return 0
        def spawn(*args, **kwargs):
            inherited.append(os.dup(kwargs["pass_fds"][0]))
            return Child()
        try:
            with patch.object(rail.subprocess, "Popen", side_effect=spawn) as start:
                with ThreadPoolExecutor(max_workers=6) as pool:
                    results = list(pool.map(lambda i: rail.refresh(f"COIN{i}"), range(12)))
            self.assertEqual(start.call_count, 1)
            self.assertTrue(all(r["running"] for r in results))
            self.assertEqual(len(rail.read(rail.root() / "requests.json")), 8)
        finally:
            for descriptor in inherited:
                os.close(descriptor)

    def test_oversized_snapshot_is_unavailable_instead_of_unbounded_read(self):
        rail.root().mkdir()
        (rail.root() / "rail-SOL.json").write_text("x" * (rail.MAX_JSON + 100))
        result = rail.rail("SOL")
        self.assertIsNone(result["observed_at"])

    def test_whole_aggregate_rechecks_expiry_before_capping_current_voters(self):
        rows = [{"label": str(i), "accuracy": 90., "resolved": 30, "pred_1m": "UP" if i < 9 else "DOWN",
                 "acc_1m": 90., "resolved_1m": 30, "issued_1m": 100., "expires_1m": 200.} for i in range(10)]
        rows.append({**rows[0], "label": "expired", "expires_1m": 140.})
        rail.write(rail.root() / "rail-SOL.json", {"asset": "SOL", "observed_at": 130.,
            "voting": {"raw_rows": rows, "voting": {"min_accuracy": 60., "min_resolved": 20}}, "activity": {"items": []}})
        result = rail.rail("SOL", limit=2, now=150.)
        self.assertEqual(result["voting"]["aggregate"]["score"], 80.)
        self.assertEqual(result["voting"]["eligible_count"], 10)
        self.assertEqual(len(result["voting"]["rows"]), 2)
        self.assertTrue(result["voting"]["rows_truncated"])
        self.assertNotIn("raw_rows", result["voting"])
        stricter = rail.rail("SOL", limit=2, now=150., min_resolved=31)
        self.assertFalse(stricter["voting"]["aggregate"]["available"])
        self.assertEqual(stricter["voting"]["voting"]["min_resolved"], 31)
        expired = rail.rail("SOL", limit=2, now=200.)
        self.assertFalse(expired["voting"]["aggregate"]["available"])
        self.assertEqual(expired["voting"]["rows"], [])
        self.assertEqual(len(rail.read(rail.root() / "rail-SOL.json")["voting"]["raw_rows"]), 11)

    def test_actual_read_model_survives_short_lived_client_and_stops_cooperatively(self):
        fixture = self.directory / "python-fixture"
        fixture.mkdir()
        # The module worker has a separate __main__ namespace. Replace only the
        # market/wallet boundaries there via the shared imported modules.
        (fixture / "sitecustomize.py").write_text('''\
from soltui import live_score, prediction_recovery, portfolio, wallet_activity
live_score.prediction_snapshot=lambda *a,**k: {'aggregate':{'available':False},'rows':[]}
prediction_recovery.health=lambda *a,**k: {'state':'stopped','running':False}
portfolio.load_last_scan=lambda: None
wallet_activity.snapshot=lambda *a,**k: {'items':[],'coverage':[],'gaps':['offline lifecycle fixture']}
''', encoding="utf-8")
        environment = {**os.environ, "SOLTUI_CONFIG_DIR": str(self.directory),
            "PYTHONPATH": os.pathsep.join([str(fixture), str(rail.REPO)])}
        command = [sys.executable, "-c", "import json; from soltui import live_tools; print(json.dumps(live_tools.refresh('SOL')))"]
        try:
            caller = subprocess.run(command, env=environment, cwd=rail.REPO, capture_output=True, text=True, timeout=10, check=True)
            self.assertTrue(json.loads(caller.stdout)["running"])
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                result = rail.rail("SOL")
                if result.get("observed_at") and result["read_model"]["running"]:
                    break
                time.sleep(.05)
            else:
                self.fail(f"The detached read-model did not survive its short-lived client: {rail.read(rail.root() / 'worker.json')}")
        finally:
            rail.stop_refresh()
            deadline = time.monotonic() + 10
            while rail.locked(rail.root() / "worker.lock") and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(rail.locked(rail.root() / "worker.lock"))


if __name__ == "__main__":
    unittest.main()

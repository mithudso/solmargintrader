"""One explicit paper action reuses saved sessions and frozen assessment inputs."""
from __future__ import annotations

import os
import json
import subprocess
import sys
import time
import sqlite3
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from contextlib import closing
from tempfile import TemporaryDirectory
from unittest.mock import patch

from soltui import bots, bot_scheduler, commands, config, council, f5_batch, live_tools, paper_workflow as workflow
ORIGINAL_FORWARD_START = bots.forward_start


class PaperWorkflow(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.enterContext(patch.object(config, "CONFIG_DIR", self.directory))
        self.settings = config.Settings(data_dir=str(self.directory / "data"))
        Path(self.settings.data_dir).mkdir()
        (Path(self.settings.data_dir) / "ADA_1h.csv").write_text("first frozen data")
        self.grid = {"id": "retained-ada", "asset": "ADA", "bot": "grid", "started_at": 100., "stopped_at": None,
            "fee_bps": 6., "slippage_bps": 2., "config": {"range_pct": 1.5, "rungs": 5, "capital_usd": 1000., "spacing": "geom", "deadband_bps": 25.}}
        live_tools.write(bots.forward_path(), {"grid": self.grid})
        self.state = {"state": "starting", "mode": "paper", "asset": "SOL", "scope": "all", "stages": {}}
        self.batch_list = self.enterContext(patch.object(f5_batch, "list_runs", return_value=[{"run_id": "b" * 32, "running": True, "phase": "backtesting", "assets": ["ADA", "SOL"]}]))
        self.batch_create = self.enterContext(patch.object(f5_batch, "create"))
        self.batch_start = self.enterContext(patch.object(f5_batch, "start"))
        self.prediction = self.enterContext(patch.object(commands, "dispatch", return_value={"ok": True, "result": {"state": "running", "running": True}}))
        self.grid_start = self.enterContext(patch.object(bots, "forward_start"))
        self.assess = self.enterContext(patch.object(bots, "backtest", return_value={"id": "assessment", "bot": "grid", "asset": "ADA", "results": {"total_return": -.01}}))
        self.council_status = self.enterContext(patch.object(council, "status", return_value={"running": True, "state": "waiting", "config": {"asset": "SOL", "execution": {"min_confidence": .8}}}))
        self.council_start = self.enterContext(patch.object(council, "start"))
        self.optimizer_status = self.enterContext(patch.object(bot_scheduler, "status", return_value={"running": True, "phase": "waiting"}))
        self.optimizer_start = self.enterContext(patch.object(bot_scheduler, "start"))

    def test_existing_global_jobs_and_grid_are_preserved(self):
        original = bots.forward_path().read_bytes()
        workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.state["state"], "ready")
        self.assertEqual(bots.forward_path().read_bytes(), original)
        self.grid_start.assert_not_called()
        self.batch_create.assert_not_called()
        self.batch_start.assert_not_called()
        self.council_start.assert_not_called()
        self.optimizer_start.assert_not_called()
        self.assertEqual(self.assess.call_args.args[:2], ("grid", "ADA"))
        self.assertEqual(self.assess.call_args.kwargs["config"], self.grid["config"])
        self.assertEqual(self.state["stages"]["council_paper"]["result"]["execution"]["min_confidence"], .8)

    def test_real_grid_creation_race_preserves_the_winning_ada_session(self):
        bots.forward_path().unlink()
        read, written = threading.Event(), threading.Event()
        original_read = live_tools.grid_metadata
        first = True
        def optimistic_read():
            nonlocal first
            result = original_read()
            if first:
                first = False
                self.assertIsNone(result)
                read.set()
                if not written.wait(5):
                    self.fail("Concurrent grid creation must finish")
            return result
        def writer():
            if not read.wait(5):
                return
            with bots.runtime().lock, bots._forward_lock():
                live_tools.write(bots.forward_path(), {"grid": self.grid})
            written.set()
        concurrent = threading.Thread(target=writer)
        concurrent.start()
        with patch.object(live_tools, "grid_metadata", side_effect=optimistic_read), patch.object(
                bots, "forward_start", ORIGINAL_FORWARD_START), patch.object(bots.pricefeed, "ensure_recorder") as recorder:
            try:
                workflow.run(self.settings, self.state, threading.Event())
            finally:
                read.set()
                concurrent.join(5)
        self.assertFalse(concurrent.is_alive())
        self.assertEqual(original_read(), self.grid)
        saved = self.state["stages"]["grid_forward"]["result"]
        self.assertTrue(saved["reused"])
        self.assertEqual(saved["session_id"], "retained-ada")
        self.assertEqual(saved["asset"], "ADA")
        recorder.assert_not_called()

    def test_repeated_assessment_reuses_identical_proof_but_changed_data_retests(self):
        workflow.run(self.settings, self.state, threading.Event())
        workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.assess.call_count, 1)
        (Path(self.settings.data_dir) / "ADA_1h.csv").write_text("changed data must not reuse the old assessment")
        workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.assess.call_count, 2)
        self.assertEqual(self.state["grid_assessment"]["result"]["results"]["total_return"], -.01)

    def test_fallback_assessment_binds_the_directory_actually_consumed(self):
        # CDO-0bdfbd9a80: a missing configured path must not produce a reusable
        # proof for absent files while the simulator reads a fallback cache.
        actual = Path(self.settings.data_dir)
        self.settings.data_dir = str(self.directory / "missing")
        with patch.object(bots, "data_dir", return_value=actual):
            workflow.run(self.settings, self.state, threading.Event())
            (actual / "ADA_1h.csv").write_text("changed fallback source")
            workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.assess.call_count, 2)
        self.assertEqual(Path(self.assess.call_args.args[2].data_dir), actual.resolve())
        self.assertEqual(self.state["grid_assessment"]["proof"]["data_dir"], str(actual.resolve()))

    def test_one_failed_stage_does_not_hide_other_stage_outcomes_or_relax_gates(self):
        self.assess.side_effect = ValueError("missing historical bars")
        workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.state["state"], "partial")
        self.assertEqual(self.state["stages"]["grid_historical_assessment"]["state"], "failed")
        self.assertEqual(self.state["stages"]["council_paper"]["state"], "completed")
        gates = self.state["stages"]["validated_optimizer"]["result"]["gates"]
        self.assertTrue(gates["manual_mode_blocks_adoption"])
        self.assertEqual(gates["confirmed_sign_test_p"], .05)

    def test_input_changed_during_assessment_is_not_cached_as_proven(self):
        def changed(*args, **kwargs):
            (Path(self.settings.data_dir) / "ADA_1h.csv").write_text("concurrent replacement")
            return {"id": "unbound-result"}
        self.assess.side_effect = changed
        workflow.run(self.settings, self.state, threading.Event())
        self.assertEqual(self.state["stages"]["grid_historical_assessment"]["state"], "failed")
        self.assertNotIn("grid_assessment", self.state)

    def test_cancel_during_assessment_prevents_later_starts(self):
        entered, release, stopped = threading.Event(), threading.Event(), threading.Event()
        def assessment(*args, **kwargs):
            entered.set()
            if not release.wait(5):
                self.fail("Held assessment must be released")
            return {"id": "assessment"}
        self.assess.side_effect = assessment
        worker = threading.Thread(target=workflow.run, args=(self.settings, self.state, stopped))
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            stopped.set()
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.state["state"], "stopped")
        self.assertNotIn("council_paper", self.state["stages"])
        self.assertNotIn("validated_optimizer", self.state["stages"])

    def test_stopped_existing_grid_is_not_reset_by_primary_workflow(self):
        self.grid["stopped_at"] = 200.
        live_tools.write(bots.forward_path(), {"grid": self.grid})
        workflow.run(self.settings, self.state, threading.Event())
        self.grid_start.assert_not_called()
        self.assertEqual(self.state["stages"]["grid_forward"]["state"], "waiting")
        self.assertEqual(live_tools.grid_metadata()["id"], "retained-ada")

    def test_parallel_primary_requests_start_one_coordinator(self):
        inherited = []
        class Child:
            def wait(self):
                return 0
        def spawn(*args, **kwargs):
            inherited.append(os.dup(kwargs["pass_fds"][0]))
            return Child()
        try:
            with patch.object(workflow.subprocess, "Popen", side_effect=spawn) as start:
                with ThreadPoolExecutor(max_workers=6) as pool:
                    results = list(pool.map(lambda _: workflow.ensure(self.settings, "SOL", "all"), range(6)))
            self.assertEqual(start.call_count, 1)
            self.assertTrue(all(result["running"] for result in results))
        finally:
            for descriptor in inherited:
                os.close(descriptor)

    def test_stop_only_marks_coordinator_and_does_not_stop_shared_owners(self):
        with patch.object(council, "stop") as council_stop, patch.object(bot_scheduler, "stop") as optimizer_stop, patch.object(f5_batch, "stop") as batch_stop:
            result = workflow.stop()
        council_stop.assert_not_called()
        optimizer_stop.assert_not_called()
        batch_stop.assert_not_called()
        self.assertTrue(live_tools.read(workflow.root() / "control.json")["stop"])
        self.assertIn("independent shared workers continue", result["message"])

    def test_batch_progress_uses_real_bounded_read_without_starting_a_batch(self):
        run_id = "c" * 32
        directory = f5_batch._root() / run_id
        directory.mkdir(parents=True)
        with closing(sqlite3.connect(directory / "batch.sqlite3")) as db, db:
            db.executescript("CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE cell(state TEXT); CREATE TABLE forward_check(asset TEXT,interval TEXT,at REAL,recorded INTEGER,error TEXT,message TEXT);")
            db.execute("INSERT INTO meta VALUES('phase',?)", (json.dumps("backtesting"),))
            db.executemany("INSERT INTO cell VALUES(?)", [("completed",), ("failed",)])
        live_tools.write(workflow.root() / "state.json", {"state": "ready", "stages": {"backtests_and_forward_batch": {"result": {"run_id": run_id}}}})
        result = workflow.refresh_progress("SOL")
        self.assertEqual(result["batch"]["counts"], {"completed": 1, "failed": 1})
        self.assertEqual(result["batch"]["phase"], "interrupted")
        self.assertFalse(result["batch"]["running"])
        self.assertFalse((directory / "worker.lock").exists())
        self.batch_start.assert_not_called()

    def test_real_detached_coordinator_survives_caller_and_stops_at_job_boundary(self):
        fixture = self.directory / "python-fixture"
        fixture.mkdir()
        (fixture / "sitecustomize.py").write_text('''\
import os,time
from pathlib import Path
from contextlib import closing
from soltui import f5_batch,bots,council,bot_scheduler,commands
root=Path(os.environ['SOLTUI_CONFIG_DIR'])
f5_batch.list_runs=lambda: [{'run_id':'b'*32,'running':True,'assets':['SOL','ADA']}]
commands.dispatch=lambda *a,**k: {'ok':True,'result':{'state':'running','running':True}}
council.status=lambda: {'running':True,'state':'waiting','config':{'asset':'SOL','execution':{'min_confidence':.8}}}
bot_scheduler.status=lambda: {'running':True,'phase':'waiting'}
def assess(*a,**k):
    (root/'assessment-entered').write_text('entered')
    until=time.monotonic()+10
    while not (root/'assessment-release').exists() and time.monotonic()<until:
        time.sleep(.02)
    return {'id':'offline-assessment','asset':'ADA'}
bots.backtest=assess
''', encoding="utf-8")
        environment = {**os.environ, "SOLTUI_CONFIG_DIR": str(self.directory),
            "PYTHONPATH": os.pathsep.join([str(fixture), str(workflow.REPO)])}
        command = [sys.executable, "-c", "import json; from soltui import config,paper_workflow; print(json.dumps(paper_workflow.ensure(config.Settings(),'SOL','all')))"]
        try:
            # Undo this test class's fake Popen only in the launcher process;
            # all spawned worker boundaries are replaced by the offline fixture.
            caller = subprocess.run(command, env=environment, cwd=workflow.REPO, capture_output=True, text=True, timeout=10, check=True)
            self.assertTrue(json.loads(caller.stdout)["running"])
            deadline = time.monotonic() + 10
            while not (self.directory / "assessment-entered").exists() and time.monotonic() < deadline:
                time.sleep(.03)
            self.assertTrue((self.directory / "assessment-entered").exists())
            self.assertTrue(workflow.status()["running"])
            workflow.stop()
        finally:
            (self.directory / "assessment-release").write_text("released")
            deadline = time.monotonic() + 10
            while workflow.status()["running"] and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(workflow.status()["running"])
        self.assertEqual(workflow.status()["state"], "stopped")
        self.assertNotIn("council_paper", workflow.status()["stages"])


if __name__ == "__main__":
    unittest.main()

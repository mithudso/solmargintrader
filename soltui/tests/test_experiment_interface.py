"""The workbench's lifecycle and presentation, isolated from personal evidence."""
from __future__ import annotations

import fcntl
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from soltui import commands, config
from soltui import experiment_jobs as jobs
from soltui.config import Settings
from soltui.experiments import ExperimentError, ExperimentStore


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patch = mock.patch.object(config, "CONFIG_DIR", self.root / "config")
        patch.start()
        self.addCleanup(patch.stop)
        self.store = ExperimentStore()
        self.settings = Settings(data_dir=str(self.root / "data"))
        self.id = self.store.create_run({"source": "native", "bot": "grid", "candidates": [{"range_pct": 10}]})

    def wait(self, predicate, timeout=5):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if predicate():
                return
            time.sleep(.01)
        self.fail("worker did not reach expected lifecycle state")


class JobLifecycle(Isolated):
    def fake_launch(self, body):
        real = subprocess.Popen
        processes = []
        prefix = "import sys,time; from pathlib import Path; from soltui.experiments import ExperimentStore; "
        prefix += f"store=ExperimentStore(Path({str(self.store.root)!r})); rid={self.id!r}; "
        def start(argv, **kwargs):
            self.assertEqual(kwargs["env"]["SOLTUI_CONFIG_DIR"], str(config.CONFIG_DIR.resolve()))
            self.assertEqual(argv[0], __import__("sys").executable)
            self.assertTrue(kwargs["pass_fds"])
            proc = real([argv[0], "-c", prefix + body], **kwargs)
            processes.append(proc)
            return proc
        return mock.patch.object(jobs.subprocess, "Popen", side_effect=start), processes

    def test_durable_cancel_reaps_worker_and_keeps_cells(self):
        body = '''store.update_run(rid,status="running")
while True:
 state=store.get_run(rid)["status"]
 if state in ("cancel_requested","pause_requested"):
  store.update_run(rid,status="cancelled" if state=="cancel_requested" else "paused")
  break
 time.sleep(.01)
'''
        patch, processes = self.fake_launch(body)
        with patch:
            started = jobs.launch(self.store, self.id, self.settings)
        self.assertTrue(started["worker_active"])
        self.wait(lambda: self.store.get_run(self.id)["status"] == "running")
        with self.assertRaisesRegex(ExperimentError, "active worker"):
            jobs.launch(self.store, self.id, self.settings)
        response = jobs.request(self.store, self.id, "cancel")
        self.assertIn(response["status"], ("cancel_requested", "cancelled"))
        self.wait(lambda: not jobs.active(self.store, self.id))
        self.wait(lambda: processes[0].returncode is not None)
        self.assertEqual(jobs.status(self.store, self.id)["status"], "cancelled")
        self.assertEqual(processes[0].returncode, 0)

    def test_pause_resume_and_stdout_message_cannot_complete_a_run(self):
        body = '''store.update_run(rid,status="running")
while True:
 state=store.get_run(rid)["status"]
 if state in ("cancel_requested","pause_requested"):
  store.update_run(rid,status="cancelled" if state=="cancel_requested" else "paused")
  break
 time.sleep(.01)
'''
        patch, processes = self.fake_launch(body)
        with patch:
            jobs.launch(self.store, self.id, self.settings)
        self.wait(lambda: self.store.get_run(self.id)["status"] == "running")
        jobs.request(self.store, self.id, "pause")
        self.wait(lambda: processes[0].returncode is not None)
        self.assertEqual(jobs.status(self.store, self.id)["status"], "paused")
        with patch:
            jobs.launch(self.store, self.id, self.settings)
        self.wait(lambda: self.store.get_run(self.id)["status"] == "running")
        jobs.request(self.store, self.id, "cancel")
        self.wait(lambda: processes[1].returncode is not None)
        self.assertEqual(jobs.status(self.store, self.id)["status"], "cancelled")
        # A printed success event is diagnostic text, not a committed result.
        patch, processes = self.fake_launch('store.update_run(rid,status="running"); print("completed")')
        with patch:
            jobs.launch(self.store, self.id, self.settings)
        self.wait(lambda: processes[0].returncode is not None)
        self.assertNotEqual(jobs.status(self.store, self.id)["status"], "completed")

    def test_nonzero_exit_keeps_stderr_and_recovers_interrupted(self):
        patch, processes = self.fake_launch('store.update_run(rid,status="running"); sys.stderr.write("deterministic crash evidence\\n"); sys.stderr.flush(); sys.exit(7)')
        with patch:
            jobs.launch(self.store, self.id, self.settings)
        self.wait(lambda: processes[0].returncode is not None)
        report = jobs.status(self.store, self.id)
        self.assertEqual(report["status"], "interrupted")
        self.assertIn("deterministic crash evidence", report["log_tail"])
        self.assertIn("deterministic crash evidence", report["error"])

    def test_reaper_cannot_overwrite_a_later_live_worker(self):
        lease, _, _ = jobs._paths(self.store, self.id)
        self.store.update_run(self.id, status="running")
        with lease.open("a+b") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            old = mock.Mock()
            old.wait.return_value = 7
            jobs._reap(old, self.store, self.id)
            self.assertEqual(self.store.get_run(self.id)["status"], "running")
            self.assertTrue(jobs.status(self.store, self.id)["worker_active"])

    def test_stale_reconciliation_holds_lease_through_mutation(self):
        lease, _, _ = jobs._paths(self.store, self.id)
        self.store.update_run(self.id, status="running")
        original = self.store.update_run
        def update(*args, **kwargs):
            with lease.open("a+b") as contender, self.assertRaises(BlockingIOError):
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return original(*args, **kwargs)
        with mock.patch.object(self.store, "update_run", side_effect=update):
            self.assertEqual(jobs.status(self.store, self.id)["status"], "interrupted")

    def test_launch_and_start_failure_preserve_racing_control_requests(self):
        original = self.store.transition_run
        def racing_transition(run_id, state, **kwargs):
            if state == "created":
                self.store.request_control(run_id, "cancel")
            return original(run_id, state, **kwargs)
        with mock.patch.object(self.store, "transition_run", side_effect=racing_transition), \
                mock.patch.object(jobs.subprocess, "Popen") as spawn:
            with self.assertRaisesRegex(ExperimentError, "superseded"):
                jobs.launch(self.store, self.id, self.settings)
            spawn.assert_not_called()
        self.assertEqual(jobs.status(self.store, self.id)["status"], "cancelled")
        self.store.update_run(self.id, status="paused")
        def fail(argv, **kwargs):
            self.store.request_control(self.id, "cancel")
            raise OSError("deterministic spawn failure")
        with mock.patch.object(jobs.subprocess, "Popen", side_effect=fail), self.assertRaisesRegex(ExperimentError, "could not start"):
            jobs.launch(self.store, self.id, self.settings)
        self.assertEqual(jobs.status(self.store, self.id)["status"], "cancelled")

    def test_control_never_reopens_completed_and_import_never_executes(self):
        self.store.update_run(self.id, status="completed")
        self.assertEqual(jobs.request(self.store, self.id, "pause")["status"], "completed")
        imported = self.store.create_run({"source": "tradingview", "bot": "grid", "candidates": [{"rungs": 3}]})
        with self.assertRaisesRegex(ExperimentError, "cannot execute"):
            jobs.launch(self.store, imported, self.settings, final=True, adopt=True)


class Registry(Isolated):
    def test_bad_budgets_and_import_arguments_are_refused(self):
        ctx = commands.Context.from_settings(self.settings)
        for value in (True, 2.5, float("inf")):
            env = commands.dispatch("experiments.preview", {"bot": "grid", "windows": value}, ctx=ctx, quiet=True)
            self.assertFalse(env["ok"])
            self.assertEqual(env["error"]["code"], "bad_params")
        env = commands.dispatch("experiments.import", {"path": "x", "csv": "x"}, ctx=ctx, quiet=True)
        self.assertFalse(env["ok"])
        for name in ("preview", "create", "start", "pause", "cancel", "finalize", "import", "compare", "heatmap", "cells"):
            self.assertIn(f"experiments.{name}", commands.COMMANDS)


class Screen(unittest.IsolatedAsyncioTestCase):
    async def test_typed_preview_browse_heatmap_import_and_safe_dismissal(self):
        from textual.app import App
        from textual.widgets import (
            Button,
            DataTable,
            Input,
            Select,
            Static,
            TabbedContent,
        )

        from soltui.experiment_screens import ExperimentScreen
        calls = []
        config = {"range_pct": 10.0, "rungs": 3, "spacing": "geom"}
        run = {"id": "saved", "status": "explored", "spec": {"source": "native", "bot": "grid", "candidates": [config]},
               "summary": {}, "progress": {}, "worker_active": False}
        def call(name, params):
            calls.append((name, params))
            result = None
            if name == "experiments.schema":
                result = {"baseline": config, "domains": {"range_pct": ("float", 2., 60., "log"), "rungs": ("int", 3, 40, "log")}}
            elif name == "experiments.list":
                result = [run]
            elif name == "experiments.preview":
                result = {"candidate_count": 2, "candidates": [config, {**config, "rungs": 5}], "evaluations": 12,
                          "window_count": 6, "ready": True}
            elif name in {"experiments.create", "experiments.start", "experiments.get", "experiments.pause", "experiments.cancel"}:
                result = run
            elif name == "experiments.candidates":
                result = [{"candidate_id": "0", "config": config, "completed": 2, "failed": 0, "metrics": {
                    "total_return": {"median": .1, "min": -.1, "max": .3, "observations": 2, "stdev": .2}},
                    "coins": ["SOL"], "splits": ["train", "validation"]}]
            elif name == "experiments.heatmap":
                result = {"split": "train", "x": "range_pct", "y": "rungs", "metric": "total_return", "groups": [
                    {"fixed": {"spacing": "geom"}, "x_values": [10, 20], "y_values": [3, 5],
                     "observed_points": 1, "possible_points": 4, "coverage": .25,
                     "points": [{"x": 10, "y": 3, "value": .1, "observations": 2, "stdev": .2, "failed": 0}]}]}
            elif name == "experiments.import":
                result = {**run, "id": "imported", "spec": {**run["spec"], "source": "tradingview"}}
            return {"ok": True, "result": result}
        class Harness(App):
            def compose(self):
                yield Static("Harness")
            def on_mount(self):
                self.push_screen(ExperimentScreen("grid", call, ["SOL"]))
        app = Harness()
        async with app.run_test(size=(160, 55)) as pilot:
            await pilot.pause(.1)
            await app.workers.wait_for_complete()
            screen = app.screen
            screen.query_one("#exp-param", Select).value = "rungs"
            screen.query_one("#exp-kind", Select).value = "enum"
            screen.query_one("#exp-values", Input).value = "3,5"
            screen.query_one("#exp-add", Button).press()
            await pilot.pause()
            self.assertEqual(screen.space["rungs"]["values"], [3, 5])
            screen.query_one("#exp-preview", Button).press()
            await pilot.pause(.05)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertFalse(screen.query_one("#exp-create", Button).disabled)
            self.assertIn("12 evaluations", str(screen.query_one("#exp-preview-summary", Static).render()))
            screen.query_one("#exp-max-evaluations", Input).value = "10"
            await pilot.pause()
            self.assertTrue(screen.query_one("#exp-create", Button).disabled)
            screen.run_id = "saved"
            screen._loaded_run(run)
            await pilot.pause(.05)
            await app.workers.wait_for_complete()
            screen.query_one("#exp-sort", Select).value = "max_drawdown"
            screen.candidate_rows = [{"candidate_id": cid, "config": config, "completed": 1, "failed": 0,
                                     "metrics": {"max_drawdown": {"median": loss}}}
                                    for cid, loss in (("native-worse", .5), ("TV-better", .1))]
            screen.render_candidates()
            self.assertEqual(screen.query_one("#exp-candidate-table", DataTable).get_row_at(0)[0], "TV-better")
            screen.query_one("#exp-tabs", TabbedContent).active = "exp-stability"
            screen.heatmap()
            await pilot.pause(.05)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertIn("25% coverage", str(screen.query_one("#exp-map-summary", Static).render()))
            self.assertEqual(screen.query_one("#exp-map-table", DataTable).row_count, 2)
            self.assertEqual(str(screen.query_one("#exp-map-table", DataTable).get_cell_at((1, 2))), "·")
            screen.query_one("#exp-tabs", TabbedContent).active = "exp-import-tab"
            screen.query_one("#exp-import-path", Input).value = "/tmp/example.csv"
            screen.import_csv()
            await pilot.pause(.05)
            await app.workers.wait_for_complete()
            await pilot.pause()
            self.assertTrue(any(name == "experiments.import" for name, _ in calls))
            screen.action_close()
            await pilot.pause()
            self.assertTrue(screen._workbench_closed)
            # Any delayed worker result after dismissal becomes a no-op.
            screen._received("late", {"ok": True, "result": run}, screen._loaded_run, False)

"""Fresh sweeps preserve evidence and never combine leaderboard histories."""
import os
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import bgcontrol, bgqueue, commands
from soltui.config import default_settings
from soltui.tests.test_strategy_history import row


class FreshResultsTest(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.old = self.root / "results.jsonl"
        self.old.write_text("historical data\n")
        self.proof = self.root / "results.jsonl.proof.json"
        self.proof.write_text("historical proof\n")
        for module, name, value in (
            (bgqueue, "RESULTS_PATH", self.old),
            (bgqueue, "STATE_PATH", self.root / "state.json"),
            (bgcontrol, "BG_DIR", self.root),
            (bgcontrol, "LOCK_PATH", self.root / "worker.lock"),
            (bgcontrol, "PID_PATH", self.root / "worker.pid"),
        ):
            self.enterContext(mock.patch.object(module, name, value))

    def test_fresh_selection_preserves_old_and_resume_uses_same_path(self):
        with mock.patch.object(bgcontrol.subprocess, "Popen") as popen:
            popen.return_value.pid = 42
            bgcontrol.start("SOL", fresh=True)
            chosen = bgqueue.active_results_path()
            self.assertNotEqual(chosen, self.old)
            self.assertEqual(chosen.read_text(), "")
            self.assertEqual(self.old.read_text(), "historical data\n")
            self.assertEqual(self.proof.read_text(), "historical proof\n")
            self.assertIn(str(chosen), popen.call_args.args[0])
            bgcontrol.start("SOL")
            self.assertIn(str(chosen), popen.call_args.args[0])

    def test_running_worker_prevents_selection_change(self):
        fd = bgcontrol.acquire_lock()
        try:
            with self.assertRaises(RuntimeError):
                bgcontrol.start("SOL", fresh=True)
            self.assertEqual(bgqueue.active_results_path(), self.old)
            self.assertFalse((self.root / "active-results").exists())
        finally:
            os.close(fd)

    def test_failed_spawn_keeps_both_old_evidence_and_new_selection(self):
        with mock.patch.object(bgcontrol.subprocess, "Popen", side_effect=OSError("no process")):
            with self.assertRaises(OSError):
                bgcontrol.start("SOL", fresh=True)
        self.assertEqual(self.old.read_text(), "historical data\n")
        self.assertEqual(self.proof.read_text(), "historical proof\n")
        self.assertTrue(bgqueue.active_results_path().exists())

    def test_bad_selection_fails_closed(self):
        (self.root / "active-results").write_text("../../other\n")
        with self.assertRaises(ValueError):
            bgqueue.active_results_path()

    def test_switch_replaces_cached_history_instead_of_combining_rows(self):
        self.old.write_text(row("old").to_json() + "\n")
        context = commands.Context.from_settings(default_settings(), commands.Runtime())
        self.assertEqual([r.job_id for r in commands._queue_results(context)], ["old"])
        with mock.patch.object(bgcontrol.subprocess, "Popen") as popen:
            popen.return_value.pid = 42
            bgcontrol.start("SOL", fresh=True)
        self.assertEqual(commands._queue_results(context), [])
        bgqueue.append_result(row("new"), bgqueue.active_results_path())
        self.assertEqual([r.job_id for r in commands._queue_results(context)], ["new"])

    def test_fresh_selection_hides_old_worker_error_even_if_spawn_fails(self):
        bgqueue.write_state(bgqueue.QueueState(phase="error", error="old proof mismatch"))
        with mock.patch.object(bgcontrol.subprocess, "Popen", side_effect=OSError("no process")):
            with self.assertRaises(OSError):
                bgcontrol.start("SOL", fresh=True)
        self.assertEqual(commands._queue_state().phase, "idle")
        chosen = bgqueue.active_results_path()
        bgqueue.write_state(bgqueue.QueueState(phase="error", error="new error", results_path=str(chosen)))
        self.assertEqual(commands._queue_state().error, "new error")

    def test_simultaneous_starts_do_not_replace_the_selected_sweep(self):
        inside_spawn, release = threading.Event(), threading.Event()
        errors = []
        def spawn(*args, **kwargs):
            inside_spawn.set()
            if not release.wait(5):
                raise RuntimeError("test timed out")
            return mock.Mock(pid=42)
        def first():
            try:
                bgcontrol.start("SOL", fresh=True)
            except Exception as exc:
                errors.append(exc)
        with mock.patch.object(bgcontrol.subprocess, "Popen", side_effect=spawn):
            thread = threading.Thread(target=first)
            thread.start()
            try:
                self.assertTrue(inside_spawn.wait(5))
                selected = bgqueue.active_results_path()
                with self.assertRaises(RuntimeError):
                    bgcontrol.start("SOL", fresh=True)
                self.assertEqual(bgqueue.active_results_path(), selected)
            finally:
                release.set()
                thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors, [])

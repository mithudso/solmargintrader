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


class AutomaticRecoveryTest(unittest.TestCase):
    setUp = FreshResultsTest.setUp
    def test_inherited_worker_rotates_proof_mismatch_without_mixing_results(self):
        from soltui import bgworker
        old = self.old.read_bytes()
        proof = self.proof.read_bytes()
        control = mock.Mock()
        finished = bgqueue.QueueState(phase="done", done=1, total=1)
        with mock.patch.object(bgworker.bgcontrol, "inherited_lock", return_value=11), \
                mock.patch.object(bgworker.bgcontrol, "inherited_control", return_value=control), \
                mock.patch.object(bgworker, "PID_PATH", self.root / "worker.pid"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker, "ensure_dir"), \
                mock.patch.object(bgworker._Stop, "install"), \
                mock.patch.object(bgworker, "run", side_effect=[bgworker.EvaluationProofMismatch("changed"), finished]) as run:
            self.assertEqual(bgworker.main(["--asset", "SOL", "--results-path", str(self.old)]), 0)
        chosen = bgqueue.active_results_path()
        self.assertNotEqual(chosen, self.old)
        self.assertEqual(self.old.read_bytes(), old)
        self.assertEqual(self.proof.read_bytes(), proof)
        self.assertEqual(run.call_args_list[1].kwargs["results_path"], chosen)
        self.assertEqual(run.call_args_list[1].kwargs["recovered_from"], str(self.old))
        self.assertEqual(chosen.with_name(chosen.name + ".recovery.json").exists(), True)
        self.assertIn("previous results preserved", bgqueue.summarise(
            bgqueue.QueueState(phase="running", recovered_from=str(self.old)), [], worker_alive=True))

    def test_unselected_explicit_file_is_not_rotated(self):
        from soltui import bgworker
        other = self.root / "other.jsonl"
        with mock.patch.object(bgworker.bgcontrol, "inherited_lock", return_value=11), \
                mock.patch.object(bgworker.bgcontrol, "inherited_control", return_value=mock.Mock()), \
                mock.patch.object(bgworker, "PID_PATH", self.root / "worker.pid"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker, "ensure_dir"), \
                mock.patch.object(bgworker._Stop, "install"), \
                mock.patch.object(bgworker, "write_state"), \
                mock.patch.object(bgworker, "run", side_effect=bgworker.EvaluationProofMismatch("changed")) as run:
            self.assertEqual(bgworker.main(["--results-path", str(other)]), 1)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(bgqueue.active_results_path(), self.old)

    def test_restart_retains_recovery_explanation(self):
        from soltui import bgworker
        chosen = bgcontrol.select_fresh_results(recovered_from=self.old)
        with mock.patch.object(bgworker.bgcontrol, "inherited_lock", return_value=11), \
                mock.patch.object(bgworker.bgcontrol, "inherited_control", return_value=mock.Mock()), \
                mock.patch.object(bgworker, "PID_PATH", self.root / "worker.pid"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker, "ensure_dir"), \
                mock.patch.object(bgworker._Stop, "install"), \
                mock.patch.object(bgworker, "run", return_value=bgqueue.QueueState(phase="done")) as run:
            self.assertEqual(bgworker.main(["--results-path", str(chosen)]), 0)
        self.assertEqual(run.call_args.kwargs["recovered_from"], str(self.old))
        self.assertEqual(bgqueue.active_results_path(), chosen)

    def test_strategy_cards_are_included_in_evaluation_fingerprint(self):
        from soltui import bgworker
        cards = self.root / "backtester" / "strategy_cards"
        cards.mkdir(parents=True)
        card = cards / "strategy.md"
        card.write_text("first preset")
        with mock.patch.object(bgworker, "REPO", self.root):
            first = bgworker.evaluation_code_fingerprint()
            card.write_text("changed preset")
            second = bgworker.evaluation_code_fingerprint()
        self.assertIn("backtester/strategy_cards/strategy.md", first)
        self.assertNotEqual(first, second)

    def test_changed_proof_rotates_then_restarts_compatible_new_segment(self):
        from soltui import bgworker
        from soltui.tests.test_bgworker import _jobs, _ok
        settings = default_settings()
        settings.data_dir = str(self.root)
        (self.root / "SOL_1d.csv").write_text("price input")
        jobs = _jobs(1)
        state_path = self.root / "state.json"
        code = {"engine.py": "old"}
        real_run = bgworker.run
        evaluator = mock.Mock(side_effect=_ok)
        control = mock.Mock()
        control.stop_requested.return_value = False
        with mock.patch.object(bgworker, "build_queue", return_value=jobs), \
                mock.patch.object(bgworker, "ArrayCache", return_value=mock.Mock()), \
                mock.patch.object(bgworker, "evaluate", evaluator), \
                mock.patch.object(bgworker, "evaluation_code_fingerprint", side_effect=lambda: dict(code)), \
                mock.patch.object(bgworker, "load_settings", return_value=settings), \
                mock.patch.object(bgworker.bgcontrol, "inherited_lock", return_value=11), \
                mock.patch.object(bgworker.bgcontrol, "inherited_control", return_value=control), \
                mock.patch.object(bgworker, "PID_PATH", self.root / "worker.pid"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker._Stop, "install"):
            # Create a real old proof/result pair in this isolated directory.
            self.old.unlink()
            self.proof.unlink()
            real_run("SOL", settings=settings, results_path=self.old, state_path=state_path)
            old_bytes = self.old.read_bytes()
            proof_bytes = self.proof.read_bytes()
            code["engine.py"] = "new"
            def isolated_run(*args, **kwargs):
                return real_run(*args, state_path=state_path, **kwargs)
            with mock.patch.object(bgworker, "run", side_effect=isolated_run):
                self.assertEqual(bgworker.main(["--asset", "SOL", "--results-path", str(self.old)]), 0)
                chosen = bgqueue.active_results_path()
                self.assertNotEqual(chosen, self.old)
                self.assertEqual(len(bgqueue.read_results(chosen)), 1)
                self.assertEqual(bgworker.main(["--asset", "SOL", "--results-path", str(chosen)]), 0)
            self.assertEqual(bgqueue.active_results_path(), chosen)
            self.assertEqual(len(bgqueue.read_results(chosen)), 1)
            self.assertEqual(evaluator.call_count, 2)  # old context once, new context once
            self.assertEqual(self.old.read_bytes(), old_bytes)
            self.assertEqual(self.proof.read_bytes(), proof_bytes)
            self.assertEqual(bgqueue.read_state(state_path).recovered_from, str(self.old))

    def test_recovery_note_identifies_only_the_labeled_input_path(self):
        import json
        from soltui import bgworker
        name = "/tmp/sol-hourly-synthetic/SOL_1h.csv"
        self.proof.write_text(json.dumps({"assets": {"SOL": {"proof": {"data": {name: "hash"}}}}}))
        note = bgworker._prior_input_note(self.old, "SOL")
        self.assertIn(name, note)
        self.assertIn("input path labeled synthetic", note)
        self.assertEqual(bgworker._prior_input_note(self.old, "BTC"), "")
        chosen = bgcontrol.select_fresh_results(recovered_from=self.old, source_note=note)
        metadata = json.loads(chosen.with_name(chosen.name + ".recovery.json").read_text())
        self.assertEqual(metadata["source_note"], note)

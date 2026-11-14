"""Offline regression cases for provenance, lock handoff, and job budgets."""
from __future__ import annotations

import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import bgcontrol, bgqueue, bgworker
from soltui.config import default_settings
from soltui.tests.test_bgworker import _jobs, _ok


class TestEvaluationProof(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.results = self.root / "results.jsonl"
        self.settings = default_settings()
        self.settings.data_dir = str(self.root)
        self.data = self.root / "SOL_1d.csv"
        self.data.write_text("first input", encoding="utf-8")
        self.code = {"backtester/core/engine.py": "first-code-hash"}
        self.jobs = _jobs(2)
        self.evaluator = self.enterContext(mock.patch.object(bgworker, "evaluate", side_effect=_ok))
        self.enterContext(mock.patch.object(bgworker, "build_queue", return_value=self.jobs))
        self.enterContext(mock.patch.object(bgworker, "ArrayCache", return_value=mock.Mock()))
        self.enterContext(mock.patch.object(bgworker, "evaluation_code_fingerprint", side_effect=lambda: dict(self.code), create=True))

    def run_worker(self, **kw):
        return bgworker.run("SOL", settings=self.settings, results_path=self.results,
                            state_path=self.root / "state.json", **kw)

    def assert_refuses_changed_proof(self):
        before = self.results.read_bytes()
        with self.assertRaisesRegex(ValueError, "evaluation proof|evaluation context"):
            self.run_worker()
        self.assertEqual(self.results.read_bytes(), before)
        self.assertEqual(self.evaluator.call_count, 2)

    def test_unchanged_proof_resumes_and_persists_readable_inputs(self):
        self.run_worker()
        self.assertEqual(self.run_worker().total, 0)
        proof = json.loads(self.results.with_name("results.jsonl.proof.json").read_text())
        self.assertIn("SOL", proof["assets"])
        self.assertIn("settings", proof["assets"]["SOL"]["proof"])
        self.assertIn("data", proof["assets"]["SOL"]["proof"])
        self.assertIn("code", proof["assets"]["SOL"]["proof"])
        self.assertEqual(self.evaluator.call_count, 2)

    def test_changed_settings_refuse_and_preserve_history(self):
        self.run_worker()
        self.settings.fee_bps = 999
        self.assert_refuses_changed_proof()

    def test_changed_data_refuse_and_preserve_history(self):
        self.run_worker()
        self.data.write_text("changed input", encoding="utf-8")
        self.assert_refuses_changed_proof()

    def test_changed_code_refuses_and_preserves_history(self):
        self.run_worker()
        self.code["backtester/core/engine.py"] = "changed-code-hash"
        self.assert_refuses_changed_proof()

    def test_lost_proof_refuses_and_preserves_history(self):
        self.run_worker()
        self.results.with_name("results.jsonl.proof.json").unlink()
        self.assert_refuses_changed_proof()

    def test_legacy_results_without_proof_refuse(self):
        bgqueue.append_result(_ok(self.jobs[0], None, None, None), self.results)
        before = self.results.read_bytes()
        with self.assertRaisesRegex(ValueError, "evaluation proof"):
            self.run_worker()
        self.assertEqual(self.results.read_bytes(), before)
        self.evaluator.assert_not_called()

    def test_fresh_output_is_allowed_without_changing_prior_history(self):
        self.run_worker()
        before = self.results.read_bytes()
        self.settings.fee_bps = 999
        fresh = self.root / "fresh.jsonl"
        bgworker.run("SOL", settings=self.settings, results_path=fresh,
                     state_path=self.root / "fresh-state.json")
        self.assertEqual(len(bgqueue.read_results(fresh)), 2)
        self.assertEqual(self.results.read_bytes(), before)

    def test_input_changed_during_array_load_is_not_evaluated(self):
        cache = mock.Mock()
        cache.get.side_effect = lambda *args: self.data.write_text("changed during load")
        with mock.patch.object(bgworker, "ArrayCache", return_value=cache):
            with self.assertRaisesRegex(ValueError, "evaluation context changed"):
                self.run_worker()
        self.evaluator.assert_not_called()
        self.assertFalse(self.results.exists())

    def test_corrupt_proof_cannot_be_replaced_with_a_guess(self):
        self.run_worker()
        sidecar = self.results.with_name("results.jsonl.proof.json")
        sidecar.write_text("broken proof", encoding="utf-8")
        self.assert_refuses_changed_proof()
        self.assertEqual(sidecar.read_text(), "broken proof")

    def test_invalid_budgets_fail_before_evaluation(self):
        for limit in (-1, 1.5, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.run_worker(limit=limit)
        self.evaluator.assert_not_called()

    def test_plan_honors_selected_result_path(self):
        with mock.patch.object(bgworker, "read_results", return_value=[]) as read, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bgworker.main(["--plan", "--results-path", str(self.results)]), 0)
        read.assert_called_once_with(self.results)

    def test_rsi_exclusions_are_bound_to_proof_and_status_without_attempts(self):
        with mock.patch.object(bgworker, "build_queue", side_effect=bgqueue.build_queue):
            state = self.run_worker(horizons=["medium"], strategies=["rsi"])
        self.assertEqual(state.phase, "done")
        self.assertEqual(state.total, 11)
        self.assertEqual({key: state.candidates[key] for key in ("requested", "eligible", "excluded")},
                         {"requested": 13, "eligible": 11, "excluded": 2})
        rows = bgqueue.read_results(self.results)
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(row.evaluable for row in rows))
        manifest = json.loads(self.results.with_name("results.jsonl.proof.json").read_text())
        self.assertEqual(manifest["assets"]["SOL"]["candidates"], state.candidates)
        self.assertEqual({e["job_id"] for e in state.candidates["exclusions"]},
                         {"cb9b5d612027b69d", "3873501191efbebb"})

    def test_plan_prints_exact_exclusions_without_writing_results(self):
        output = io.StringIO()
        with mock.patch.object(bgworker, "build_queue", side_effect=bgqueue.build_queue), \
                mock.patch.object(bgworker, "load_settings", return_value=self.settings), \
                contextlib.redirect_stdout(output):
            code = bgworker.main(["--plan", "--asset", "SOL", "--horizons", "medium",
                                  "--strategies", "rsi", "--results-path", str(self.results)])
        self.assertEqual(code, 0)
        self.assertIn("13 requested, 11 eligible, 2 excluded before evaluation", output.getvalue())
        self.assertIn("cb9b5d612027b69d", output.getvalue())
        self.assertIn("3873501191efbebb", output.getvalue())
        self.assertFalse(self.results.exists())
        self.assertFalse(self.results.with_name("results.jsonl.proof.json").exists())


class TestInheritedLock(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "worker.lock"
        self.enterContext(mock.patch.object(bgcontrol, "LOCK_PATH", self.path))

    def test_unrelated_descriptor_is_not_adopted_or_closed(self):
        other = Path(self.tmp.name) / "other"
        fd = os.open(other, os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, fd)
        self.assertIsNone(bgcontrol.inherited_lock(str(fd)))
        os.fstat(fd)

    def test_unlocked_descriptor_cannot_bypass_another_owner(self):
        owner = bgcontrol.acquire_lock()
        self.addCleanup(os.close, owner)
        fd = os.open(self.path, os.O_RDWR)
        self.addCleanup(os.close, fd)
        self.assertIsNone(bgcontrol.inherited_lock(str(fd)))
        self.assertTrue(bgcontrol.is_running())
        os.fstat(fd)

    def test_held_descriptor_is_adopted_without_releasing_lock(self):
        fd = bgcontrol.acquire_lock()
        self.addCleanup(os.close, fd)
        self.assertEqual(bgcontrol.inherited_lock(str(fd)), fd)
        self.assertTrue(bgcontrol.is_running())

    def test_false_marker_cannot_bypass_second_worker_refusal(self):
        with mock.patch.dict(os.environ, {bgcontrol.LOCK_FD_ENV: "invalid"}), \
                mock.patch.object(bgcontrol, "acquire_lock", return_value=None) as acquire, \
                mock.patch.object(bgworker, "run") as run, \
                mock.patch.object(bgworker, "PID_PATH", Path(self.tmp.name) / "worker.pid"), \
                mock.patch.object(bgworker, "ensure_dir"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker._Stop, "install"), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bgworker.main([]), 1)
        acquire.assert_called_once()
        run.assert_not_called()

    def test_setup_failure_releases_only_the_newly_acquired_lock(self):
        fd = bgcontrol.acquire_lock()
        with mock.patch.dict(os.environ, {bgcontrol.LOCK_FD_ENV: "invalid"}), \
                mock.patch.object(bgcontrol, "acquire_lock", return_value=fd), \
                mock.patch.object(bgworker, "PID_PATH", Path(self.tmp.name) / "worker.pid"), \
                mock.patch.object(bgworker, "ensure_dir", side_effect=OSError("no directory")), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker._Stop, "install"), \
                mock.patch.object(bgworker, "write_state"), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bgworker.main([]), 1)
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_main_does_not_close_a_valid_inherited_owner_descriptor(self):
        fd = bgcontrol.acquire_lock()
        self.addCleanup(os.close, fd)
        with mock.patch.dict(os.environ, {bgcontrol.LOCK_FD_ENV: str(fd)}), \
                mock.patch.object(bgworker, "PID_PATH", Path(self.tmp.name) / "worker.pid"), \
                mock.patch.object(bgworker, "ensure_dir"), \
                mock.patch.object(bgworker, "lower_priority", return_value=19), \
                mock.patch.object(bgworker._Stop, "install"), \
                mock.patch.object(bgworker, "run", return_value=bgqueue.QueueState(phase="done")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bgworker.main([]), 0)
        os.fstat(fd)
        self.assertTrue(bgcontrol.is_running())


class TestCLI(unittest.TestCase):
    def test_invalid_limits_are_parser_errors(self):
        for limit in ("-1", "1.5"):
            with self.subTest(limit=limit):
                with contextlib.redirect_stderr(io.StringIO()), \
                        self.assertRaises(SystemExit) as failure:
                    bgworker.build_parser().parse_args(["--limit", limit])
                self.assertEqual(failure.exception.code, 2)

    def test_tier_help_matches_near_then_far_order(self):
        help_text = " ".join(bgworker.build_parser().format_help().split())
        self.assertIn("1 = +near", help_text)
        self.assertIn("2 = +half/double", help_text)

    def test_code_fingerprint_hashes_execution_files_without_running_them(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = root / "backtester" / "core" / "engine.py"
            code.parent.mkdir(parents=True)
            code.write_text("raise RuntimeError('must not execute')")
            test = root / "backtester" / "tests" / "test_engine.py"
            test.parent.mkdir()
            test.write_text("test-only")
            with mock.patch.object(bgworker, "REPO", root):
                first = bgworker.evaluation_code_fingerprint()
                code.write_text("changed execution code")
                second = bgworker.evaluation_code_fingerprint()
            self.assertNotEqual(first, second)
            self.assertEqual(set(first), {"backtester/core/engine.py"})


if __name__ == "__main__":
    unittest.main()

"""Tests for the background worker's process lifecycle.

Two of these exist because the bug they describe actually shipped in an earlier
draft of this module and only turned up when the worker was spawned for real:
`taskpolicy` lives in /usr/sbin rather than /usr/bin, and the pidfile was written
by the child late enough that Stop-after-Start found nothing to signal.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import bgcontrol


class TestTaskpolicyLookup(unittest.TestCase):
    def test_resolved_path_is_the_one_that_gets_executed(self) -> None:
        """The launcher must exec the path it found, not a hardcoded guess.

        The first draft checked /usr/sbin via PATH but spawned /usr/bin, which
        raised ENOENT on exactly the hosts that HAD the tool.
        """
        launcher = bgcontrol.taskpolicy_path()
        cmd = bgcontrol.worker_command("SOL")
        if launcher is None:
            self.assertNotIn("taskpolicy", cmd[0])
        else:
            self.assertEqual(cmd[0], launcher)
            self.assertTrue(os.path.exists(cmd[0]))
            self.assertEqual(cmd[1], "-b")

    def test_availability_agrees_with_the_path(self) -> None:
        self.assertEqual(
            bgcontrol.taskpolicy_available(), bgcontrol.taskpolicy_path() is not None
        )

    def test_non_darwin_never_claims_taskpolicy(self) -> None:
        if sys.platform == "darwin":
            self.skipTest("darwin host")
        self.assertIsNone(bgcontrol.taskpolicy_path())

    def test_describe_priority_matches_availability(self) -> None:
        """The pane must not claim a QoS demotion this host cannot perform."""
        text = bgcontrol.describe_priority()
        if bgcontrol.taskpolicy_available():
            self.assertIn("background QoS", text)
        else:
            self.assertNotIn("background QoS", text)


class TestStartReleasesTheLockOnFailure(unittest.TestCase):
    """A lock leaked into the long-lived TUI process wedges the whole feature:
    every later Start refuses as "already running" and no Stop can find a worker
    to signal, until the console is restarted."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        for name, value in (
            ("BG_DIR", self.dir),
            ("LOCK_PATH", self.dir / "worker.lock"),
            ("PID_PATH", self.dir / "worker.pid"),
        ):
            p = mock.patch.object(bgcontrol, name, value)
            p.start()
            self.addCleanup(p.stop)

    def test_an_unopenable_log_does_not_leave_the_lock_held(self) -> None:
        undirectory = self.dir / "nope" / "worker.log"
        with self.assertRaises(OSError):
            bgcontrol.start("SOL", log_path=undirectory)
        self.assertFalse(bgcontrol.is_running())

    def test_a_failed_spawn_does_not_leave_the_lock_held(self) -> None:
        with mock.patch.object(bgcontrol.subprocess, "Popen",
                               side_effect=OSError("no exec")):
            with self.assertRaises(OSError):
                bgcontrol.start("SOL", log_path=self.dir / "worker.log")
        self.assertFalse(bgcontrol.is_running())

    def test_a_refused_second_start_does_not_close_the_first_lock(self) -> None:
        held = bgcontrol.acquire_lock()
        self.addCleanup(os.close, held)
        with self.assertRaises(RuntimeError):
            bgcontrol.start("SOL", log_path=self.dir / "worker.log")
        self.assertTrue(bgcontrol.is_running())


class TestWorkerCommand(unittest.TestCase):
    def test_runs_the_current_interpreter(self) -> None:
        """`python3` off PATH would be a different environment, and the failure
        surfaces as a missing numpy rather than as a wrong interpreter."""
        self.assertIn(sys.executable, bgcontrol.worker_command("SOL"))

    def test_carries_every_option(self) -> None:
        cmd = bgcontrol.worker_command(
            "BTC", horizons=["short", "medium"], max_tier=1, limit=25
        )
        self.assertIn("--asset", cmd)
        self.assertIn("BTC", cmd)
        self.assertIn("short", cmd)
        self.assertEqual(cmd[cmd.index("--max-tier") + 1], "1")
        self.assertEqual(cmd[cmd.index("--limit") + 1], "25")

    def test_limit_is_omitted_when_unset(self) -> None:
        self.assertNotIn("--limit", bgcontrol.worker_command("SOL"))

    def test_no_shell_metacharacters_are_interpreted(self) -> None:
        """argv list, never a shell string: an asset name is not a command."""
        cmd = bgcontrol.worker_command("SOL; rm -rf /")
        self.assertIn("SOL; rm -rf /", cmd)


class TestPidfile(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.pid_path = Path(self._tmp.name) / "worker.pid"
        self.lock_path = Path(self._tmp.name) / "worker.lock"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_absent_pidfile_reads_none(self) -> None:
        self.assertIsNone(bgcontrol.read_pid(self.pid_path))

    def test_garbage_pidfile_reads_none(self) -> None:
        self.pid_path.write_text("not a pid", encoding="utf-8")
        self.assertIsNone(bgcontrol.read_pid(self.pid_path))

    def test_nonpositive_pid_is_rejected(self) -> None:
        """kill(0, ...) signals the whole process group and kill(-1, ...) every
        process the user owns -- neither may ever be reachable from a pidfile."""
        for raw in ("0", "-1"):
            self.pid_path.write_text(raw, encoding="utf-8")
            self.assertIsNone(bgcontrol.read_pid(self.pid_path))

    def test_stop_without_a_live_worker_reports_false(self) -> None:
        """Even with a plausible pidfile: liveness is the lock, not the number."""
        self.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        self.assertFalse(bgcontrol.stop(self.pid_path, self.lock_path))


class TestLivenessLock(unittest.TestCase):
    """Liveness is an flock, so it cannot outlive its holder or be faked by a
    recycled pid — the defect this replaced."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.lock_path = Path(self._tmp.name) / "worker.lock"
        self._held: list[int] = []

    def tearDown(self) -> None:
        for fd in self._held:
            os.close(fd)
        self._tmp.cleanup()

    def test_unheld_lock_is_not_running(self) -> None:
        self.assertFalse(bgcontrol.is_running(self.lock_path))

    def test_held_lock_is_running(self) -> None:
        fd = bgcontrol.acquire_lock(self.lock_path)
        self.assertIsNotNone(fd)
        self._held.append(fd)
        self.assertTrue(bgcontrol.is_running(self.lock_path))

    def test_second_acquire_is_refused(self) -> None:
        """This is what stops two sweeps appending to one results file."""
        fd = bgcontrol.acquire_lock(self.lock_path)
        self._held.append(fd)
        self.assertIsNone(bgcontrol.acquire_lock(self.lock_path))

    def test_releasing_frees_the_lock(self) -> None:
        fd = bgcontrol.acquire_lock(self.lock_path)
        os.close(fd)
        self.assertFalse(bgcontrol.is_running(self.lock_path))
        again = bgcontrol.acquire_lock(self.lock_path)
        self.assertIsNotNone(again)
        self._held.append(again)

    def test_probing_does_not_leave_the_lock_held(self) -> None:
        """`is_running` takes the lock to test it; failing to release would make
        the very next Start refuse with 'already running'."""
        self.assertFalse(bgcontrol.is_running(self.lock_path))
        fd = bgcontrol.acquire_lock(self.lock_path)
        self.assertIsNotNone(fd)
        self._held.append(fd)

    def test_a_stale_file_alone_is_not_liveness(self) -> None:
        """A crashed worker leaves the file behind; the kernel drops its lock."""
        self.lock_path.write_text("", encoding="utf-8")
        self.assertFalse(bgcontrol.is_running(self.lock_path))


if __name__ == "__main__":
    unittest.main()

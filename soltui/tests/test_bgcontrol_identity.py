"""Stop addresses a temporary worker instance, never a recorded process id."""
from __future__ import annotations

import json
import os
import socket
import stat
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import bgcontrol, bgworker, bgqueue
from soltui.config import default_settings
from soltui.tests.test_bgworker import _jobs, _ok


class TestStopIdentity(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock = self.root / "worker.lock"
        self.pid = self.root / "worker.pid"
        for name, value in (("BG_DIR", self.root), ("LOCK_PATH", self.lock), ("PID_PATH", self.pid)):
            self.enterContext(mock.patch.object(bgcontrol, name, value))
        self.kill = self.enterContext(mock.patch.object(os, "kill"))
        self.addCleanup(self.kill.assert_not_called)

    def hold(self):
        fd = bgcontrol.acquire_lock(self.lock)
        self.addCleanup(lambda: self.close_fd(fd))
        return fd

    @staticmethod
    def close_fd(fd):
        try:
            os.close(fd)
        except OSError:
            pass

    def control(self, fd):
        control = bgcontrol.create_control(fd)
        self.addCleanup(control.close)
        return control

    def test_recycled_pid_with_newly_held_lock_is_never_signalled(self):
        self.hold()
        self.pid.write_text("424242", encoding="utf-8")
        self.assertFalse(bgcontrol.stop(self.pid, self.lock))

    def test_startup_stop_queues_before_pid_publication(self):
        control = self.control(self.hold())
        self.pid.write_text("424242", encoding="utf-8")
        self.assertTrue(bgcontrol.stop(self.pid, self.lock))
        self.assertTrue(control.stop_requested())

    def test_stop_is_refused_after_lock_owner_exits(self):
        fd = self.hold()
        control = self.control(fd)
        self.close_fd(fd)
        self.assertFalse(bgcontrol.stop(self.pid, self.lock))
        self.assertFalse(control.stop_requested())

    def test_exit_between_metadata_read_and_delivery_cannot_signal_recycled_pid(self):
        control = self.control(self.hold())
        original = bgcontrol.read_control_owner
        def owner_exits(fd):
            value = original(fd)
            control.close()
            self.pid.write_text("424242", encoding="utf-8")
            return value
        with mock.patch.object(bgcontrol, "read_control_owner", side_effect=owner_exits):
            self.assertFalse(bgcontrol.stop(self.pid, self.lock))

    def test_delayed_request_for_old_instance_cannot_stop_replacement(self):
        fd = self.hold()
        old = self.control(fd)
        stale_owner = bgcontrol.read_control_owner(fd)
        old.close()
        self.close_fd(fd)
        replacement = self.control(self.hold())
        with mock.patch.object(bgcontrol, "read_control_owner", return_value=stale_owner):
            self.assertFalse(bgcontrol.stop(self.pid, self.lock))
        self.assertFalse(replacement.stop_requested())
        self.assertTrue(bgcontrol.stop(self.pid, self.lock))
        self.assertTrue(replacement.stop_requested())

    def test_wrong_instance_token_is_ignored(self):
        control = self.control(self.hold())
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            sender.sendto(b'{"command":"stop","nonce":"wrong"}', str(control.path))
        self.assertFalse(control.stop_requested())
        self.assertTrue(bgcontrol.stop(self.pid, self.lock))
        self.assertTrue(control.stop_requested())

    def test_invalid_inherited_control_does_not_close_foreign_descriptor(self):
        fd = self.hold()
        self.control(fd)
        other = os.open(self.root / "unrelated", os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(self.close_fd, other)
        self.assertIsNone(bgcontrol.inherited_control(fd, str(other)))
        os.fstat(other)

    def test_control_cleanup_is_idempotent_and_removes_endpoint(self):
        control = self.control(self.hold())
        control.close()
        control.close()
        self.assertFalse(control.path.exists())
        self.assertFalse(bgcontrol.stop(self.pid, self.lock))

    def test_owner_metadata_and_endpoint_are_owner_only(self):
        control = self.control(self.hold())
        self.assertEqual(stat.S_IMODE(self.lock.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(control.path.stat().st_mode), 0o600)

    def test_child_adoption_closes_only_its_transferred_receiver_copy(self):
        fd = self.hold()
        parent = self.control(fd)
        inherited = os.dup(parent.fileno())
        child = bgcontrol.inherited_control(fd, str(inherited), consume=True)
        self.assertIsNotNone(child)
        self.addCleanup(child.close)
        with self.assertRaises(OSError):
            os.fstat(inherited)
        os.fstat(parent.fileno())
        parent.close(remove_endpoint=False)
        self.assertTrue(child.path.exists())
        self.assertTrue(bgcontrol.stop(self.pid, self.lock))
        self.assertTrue(child.stop_requested())

    def test_long_endpoint_path_refuses_and_launcher_releases_resources(self):
        long_dir = self.root / ("long-" * 18)
        long_dir.mkdir()
        lock = long_dir / "worker.lock"
        with mock.patch.object(bgcontrol, "LOCK_PATH", lock), \
                mock.patch.object(bgcontrol.subprocess, "Popen") as popen:
            with self.assertRaises(OSError):
                bgcontrol.start("SOL", log_path=self.root / "worker.log")
            self.assertFalse(bgcontrol.is_running(lock))
        popen.assert_not_called()
        self.assertEqual(lock.read_bytes(), b"")
        self.assertEqual(list(long_dir.iterdir()), [lock])

    def test_failed_pid_publication_releases_control_even_if_child_cleanup_fails(self):
        child = mock.Mock(pid=123456)
        child.kill.side_effect = OSError("child already exited")
        with mock.patch.object(bgcontrol, "PID_PATH", self.root / "missing" / "worker.pid"), \
                mock.patch.object(bgcontrol.subprocess, "Popen", return_value=child):
            with self.assertRaises(OSError):
                bgcontrol.start("SOL", log_path=self.root / "worker.log")
        self.assertFalse(bgcontrol.is_running(self.lock))
        self.assertEqual(list(self.root.glob(".s-*")), [])

    def test_launcher_hands_queued_request_to_inherited_receiver(self):
        child_controls = []
        def fake_spawn(*args, **kw):
            self.assertTrue(bgcontrol.stop(self.pid, self.lock))
            lock_fd = int(kw["env"][bgcontrol.LOCK_FD_ENV])
            marker = kw["env"][bgcontrol.CONTROL_FD_ENV]
            self.assertIn(int(marker), kw["pass_fds"])
            receiver = bgcontrol.inherited_control(lock_fd, marker)
            self.assertIsNotNone(receiver)
            child_controls.append(receiver)
            self.addCleanup(receiver.close)
            return mock.Mock(pid=123456)
        with mock.patch.object(bgcontrol.subprocess, "Popen", side_effect=fake_spawn):
            bgcontrol.start("SOL", log_path=self.root / "worker.log")
        self.assertTrue(child_controls[0].stop_requested())

    def test_cooperative_request_stops_only_at_next_job_boundary(self):
        control = self.control(self.hold())
        stop = bgworker._Stop(control=control)
        settings = default_settings()
        settings.data_dir = str(self.root)
        def evaluate(job, arrays, cfg, settings):
            self.assertTrue(bgcontrol.stop(self.pid, self.lock))
            return _ok(job, arrays, cfg, settings)
        with mock.patch.object(bgworker, "build_queue", return_value=_jobs(3)), \
                mock.patch.object(bgworker, "ArrayCache", return_value=mock.Mock()), \
                mock.patch.object(bgworker, "evaluate", side_effect=evaluate):
            state = bgworker.run("SOL", settings=settings, stop=stop,
                                 results_path=self.root / "results.jsonl", state_path=self.root / "state.json")
        self.assertEqual(state.phase, "stopped")
        self.assertEqual(len(bgqueue.read_results(self.root / "results.jsonl")), 1)


if __name__ == "__main__":
    unittest.main()

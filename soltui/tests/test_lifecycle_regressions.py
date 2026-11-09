"""Control identities, feed silence and experiment races, isolated from owner state."""
from __future__ import annotations

import gzip
import json
import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backtester.core.trianglesim import read_snapshot_files
from soltui import experiment_jobs as jobs
from soltui import experiment_runner as runner
from soltui import pricefeed as pf
from soltui.bots import SnapshotCursor
from soltui.experiments import ExperimentStore
from soltui.tests.test_pricefeed import FakeSock, connected, server_frame


class RecorderRegressions(unittest.TestCase):
    def test_restart_repairs_only_the_incomplete_gzip_tail_before_appending(self):
        t = 1_800_000_000.0
        def line(at):
            return json.dumps({"t": at, "q": {"ETH-USD": [10, 11, 10.5, 1, 2, at]}}) + "\n"
        prefix = gzip.compress(line(t).encode()) + gzip.compress(line(t + 60).encode())
        final_member = gzip.compress(line(t + 120).encode())
        for tail in (final_member[:len(final_member) // 2], final_member[:-4], b"corrupt gzip tail"):
            with self.subTest(tail_bytes=len(tail)), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = pf.day_path(t, root)
                path.write_bytes(prefix + tail)
                cursor = SnapshotCursor(t, root)
                self.assertEqual([at for at, _ in cursor.read_new()], [t, t + 60])
                rec = pf.Recorder(["ETH-USD"], root=root)
                rec.pending = [line(t + 180).rstrip("\n")]
                lock = pf._try_lock(pf.paths(root)["lock"])
                self.assertIsNotNone(lock)
                try:
                    with mock.patch("builtins.print") as diagnostic:
                        rec.flush(t + 181)
                finally:
                    os.close(lock)
                self.assertTrue(path.read_bytes().startswith(prefix), "preserve every complete member byte")
                self.assertEqual([at for at, _ in cursor.read_new()], [t + 180])
                self.assertEqual([at for at, _ in read_snapshot_files([path])], [t, t + 60, t + 180])
                self.assertEqual(cursor.read_new(), [])
                self.assertEqual(rec.pending, [])
                tails = list(root.glob("*.damaged-tail"))
                self.assertEqual(len(tails), 1)
                self.assertEqual(tails[0].read_bytes(), tail)
                self.assertEqual(tails[0].stat().st_mode & 0o777, 0o600)
                self.assertEqual(pf.recorded_files(root), [path])
                self.assertIn(str(len(tail)), rec.last_error)
                diagnostic.assert_called_once()

    def test_failed_append_repairs_again_without_replaying_completed_members(self):
        t = 1_800_000_000.0
        def line(at):
            return json.dumps({"t": at, "q": {"ETH-USD": [10, 11, 10.5, 1, 2, at]}})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = pf.Recorder(["ETH-USD"], root=root)
            path = pf.day_path(t, root)
            rec.pending = [line(t)]
            with mock.patch.object(pf, "_repair_gzip_tail", wraps=pf._repair_gzip_tail) as repair:
                rec.flush(t)
                prefix = path.read_bytes()
                rec.pending = [line(t + 60)]
                class FailedAppend:
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return False
                    def write(self, text):
                        with path.open("ab") as partial:
                            partial.write(gzip.compress(text.encode())[:15])
                        raise OSError("fixture disk fault")
                with mock.patch.object(pf.gzip, "open", return_value=FailedAppend()):
                    with self.assertRaisesRegex(OSError, "fixture disk fault"):
                        rec.flush(t + 60)
                self.assertEqual(rec.pending, [line(t + 60)])
                with mock.patch("builtins.print"):
                    rec.flush(t + 61)
                self.assertEqual(repair.call_count, 2, "one startup scan and one failed-append recovery")
                self.assertTrue(path.read_bytes().startswith(prefix))
                self.assertEqual([at for at, _ in read_snapshot_files([path])], [t, t + 60])
                rec.pending = [line(t + 120)]
                rec.flush(t + 121)
                self.assertEqual(repair.call_count, 2, "successful flushes do not rescan a whole day")
                self.assertEqual([at for at, _ in read_snapshot_files([path])], [t, t + 60, t + 120])

    def test_quarantine_failure_leaves_the_original_stream_and_pending_batch_intact(self):
        t = 1_800_000_000.0
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = pf.day_path(t, root)
            original = gzip.compress(b'{"t":1800000000,"q":{}}\n') + b"damaged tail"
            path.write_bytes(original)
            rec = pf.Recorder(["ETH-USD"], root=root)
            rec.pending = ['{"t":1800000060,"q":{}}']
            for failure in (mock.patch.object(pf.tempfile, "mkstemp", side_effect=OSError("fixture full disk")),
                            mock.patch.object(pf.os, "fsync", side_effect=OSError("fixture full disk"))):
                with failure, mock.patch.object(pf.gzip, "open") as append:
                    with self.assertRaisesRegex(OSError, "fixture full disk"):
                        rec.flush(t + 61)
                append.assert_not_called()
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(root.glob("*.damaged-tail")), [])
                self.assertEqual(rec.pending, ['{"t":1800000060,"q":{}}'])

    def test_repair_handles_chunk_boundaries_and_large_compression_ratios(self):
        import random
        t = 1_800_000_000.0
        random_bytes = random.Random(7).randbytes(140_000)
        for payload in (b"x" * 300_000, random_bytes):
            with self.subTest(size=len(payload)), tempfile.TemporaryDirectory() as tmp:
                path = pf.day_path(t, Path(tmp))
                prefix = gzip.compress(payload) + gzip.compress(b"second member\n")
                tail = gzip.compress(b"incomplete member\n")[:-3]
                path.write_bytes(prefix + tail)
                removed, quarantine = pf._repair_gzip_tail(path)
                self.assertEqual(removed, len(tail))
                self.assertEqual(quarantine.read_bytes(), tail)
                self.assertEqual(path.read_bytes(), prefix)
                self.assertEqual(gzip.decompress(path.read_bytes()), payload + b"second member\n")

    def test_stop_targets_only_the_current_recorder_instance_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_request = root / (".stop-" + "a" * 32)
            old_request.write_text("stale instance")
            def record(rec, **kwargs):
                self.assertFalse(rec._should_stop(), "an earlier instance cannot stop this recorder")
                result = pf.stop_recorder(root)
                self.assertTrue(result["stopping"])
                self.assertTrue(rec._should_stop())
                return 0
            with mock.patch.object(pf, "stream_products", return_value=["ETH-USD"]), \
                    mock.patch.object(pf.Recorder, "run", autospec=True, side_effect=record), \
                    mock.patch("signal.signal"), mock.patch.object(pf.os, "kill") as kill:
                self.assertEqual(pf.record_main(root), 0)
            kill.assert_not_called()
            self.assertFalse(pf.recorder_running(root))
            self.assertFalse(pf.paths(root)["pid"].exists())
            self.assertEqual(list(root.glob(".stop-*")), [old_request])

    def test_busy_lock_with_stale_pid_never_signals_an_unrelated_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pf.paths(root)["pid"].write_text("424242\n")
            fd = pf._try_lock(pf.paths(root)["lock"])
            try:
                with mock.patch.object(pf.os, "kill") as kill:
                    result = pf.stop_recorder(root)
                kill.assert_not_called()
                self.assertFalse(result["stopping"], "a busy lock does not identify its owner")
            finally:
                os.close(fd)

    def test_missing_or_timed_out_launchctl_uses_detached_fallback(self):
        for error in (FileNotFoundError("launchctl"), subprocess.TimeoutExpired("launchctl", 30)):
            with self.subTest(error=type(error).__name__):
                state = {"running": False}
                def start(root=None):
                    state["running"] = True
                    return {"started": True}
                with mock.patch.object(pf, "recorder_running", side_effect=lambda root=None: state["running"]), \
                        mock.patch.object(pf, "agent_status", return_value={"installed": False, "loaded": False}), \
                        mock.patch.object(pf, "install_agent", side_effect=error), \
                        mock.patch.object(pf, "start_recorder", side_effect=start) as fallback:
                    result = pf.ensure_recorder()
                fallback.assert_called_once()
                self.assertTrue(result["running"])
                self.assertTrue(result["agent_error"])

    def test_silence_cannot_renew_a_synced_book(self):
        with tempfile.TemporaryDirectory() as tmp:
            rec = pf.Recorder(["ETH-USD"], root=Path(tmp))
            rec.handle(json.dumps({"type": "snapshot", "product_id": "ETH-USD",
                                   "bids": [["10", "1"]], "asks": [["11", "2"]]}), 100)
            rec.refresh_from_books(100)
            rec.refresh_from_books(1000)
            self.assertEqual(rec.state["ETH-USD"][5], 100)
            # A heartbeat proves the quiet connection is live without changing its book.
            rec.handle(json.dumps({"type": "heartbeat", "product_id": "ETH-USD"}), 1000)
            rec.refresh_from_books(1001)
            self.assertEqual(rec.state["ETH-USD"][5], 1001)

    def test_receive_idle_closes_connection_before_another_fresh_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = [100.0]
            ws = mock.Mock()
            snapshot = json.dumps({"type": "snapshot", "product_id": "ETH-USD",
                                   "bids": [["10", "1"]], "asks": [["11", "2"]]})
            calls = [0]
            def receive():
                calls[0] += 1
                if calls[0] == 1:
                    return snapshot
                now[0] += 100
                raise socket.timeout()
            ws.recv_text.side_effect = receive
            rec = pf.Recorder(["ETH-USD"], root=Path(tmp), clock=lambda: now[0], ws_factory=lambda: ws)
            with self.assertRaisesRegex(pf.PriceFeedError, "idle|silent"):
                rec.run_once(max_seconds=250)
            ws.close.assert_called_once()
            self.assertEqual(rec.state["ETH-USD"][5], 100)

    def test_ping_only_receive_returns_to_the_control_boundary(self):
        frames = [server_frame(pf.OP_PING, b"p") for _ in range(10)]
        ws, _ = connected(frames + [server_frame(pf.OP_TEXT, b"late")])
        ws.settimeout(1.0)
        ticks = iter(i / 4 for i in range(100))
        with mock.patch.object(pf.time, "monotonic", side_effect=lambda: next(ticks)):
            with self.assertRaises(socket.timeout):
                ws.recv_text()

    def test_slow_handshake_has_an_overall_deadline_and_closes_the_socket(self):
        sock = FakeSock([b"H"] * 100)
        ws = pf.WebSocket("ws://example.test/", timeout=1, connect=lambda *args, **kwargs: sock)
        ticks = iter(i / 4 for i in range(100))
        with mock.patch.object(pf.time, "monotonic", side_effect=lambda: next(ticks)):
            with self.assertRaises(socket.timeout):
                ws.open()
        self.assertTrue(sock.closed)


class ExperimentControlRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = ExperimentStore(self.root)
        self.rid = self.store.create_run({"source": "native", "bot": "grid", "candidates": [{}]})
        self.store.update_run(self.rid, status="running")

    def cancel_after_snapshot(self):
        original = self.store.get_run
        fired = [False]
        def fetch(rid):
            row = original(rid)
            if not fired[0]:
                fired[0] = True
                self.store.request_control(rid, "cancel")
            return row
        return mock.patch.object(self.store, "get_run", side_effect=fetch)

    def test_cancel_wins_over_stale_pause_acknowledgement(self):
        self.store.request_control(self.rid, "pause")
        with self.cancel_after_snapshot():
            self.assertTrue(runner._halt(self.store, self.rid))
        self.assertEqual(self.store.get_run(self.rid)["status"], "cancelled")

    def test_worker_exception_preserves_cancel_and_emits_diagnostics(self):
        settings = self.root / "settings.json"
        settings.write_text("{}")
        def fail(*args, **kwargs):
            self.store.request_control(self.rid, "cancel")
            raise ValueError("fixture evaluation failed after cancellation")
        with settings.open("rb") as lease, \
                mock.patch.object(jobs.signal, "signal"), \
                mock.patch.object(runner, "run_experiment", side_effect=fail), \
                mock.patch.object(jobs.traceback, "print_exc") as diagnostic:
            code = jobs.main(["--worker", self.rid, "--root", str(self.root), "--settings", str(settings),
                              "--lease-fd", str(lease.fileno())])
        self.assertEqual(code, 1)
        diagnostic.assert_called_once()
        self.assertEqual(self.store.get_run(self.rid)["status"], "cancelled")

    def test_reconciliation_preserves_a_newer_cancel_request(self):
        with self.cancel_after_snapshot():
            jobs.status(self.store, self.rid)
        self.assertEqual(self.store.get_run(self.rid)["status"], "cancelled")

    def test_reaper_preserves_a_newer_cancel_request(self):
        with self.cancel_after_snapshot():
            jobs._reap(mock.Mock(wait=mock.Mock(return_value=7)), self.store, self.rid)
        self.assertEqual(self.store.get_run(self.rid)["status"], "cancelled")

    def test_runner_error_keeps_requested_cancel_and_failure_diagnostics(self):
        def fail(*args):
            self.store.request_control(self.rid, "cancel")
            raise ValueError("fixture context failure")
        with mock.patch.object(runner, "_check_context", side_effect=fail):
            with self.assertRaisesRegex(ValueError, "fixture context failure"):
                runner.run_experiment(self.rid, object(), store=self.store)
        result = self.store.get_run(self.rid)
        self.assertEqual(result["status"], "cancelled")
        self.assertIn("fixture context failure", result["error"])

    def test_failed_exit_cannot_overwrite_completed_or_cancelled_states(self):
        for state in ("completed", "cancelled", "paused"):
            with self.subTest(state=state):
                self.store.update_run(self.rid, status=state)
                result = self.store.settle_run(self.rid, status="failed", expected=["running"], error="late failure")
                self.assertEqual(result["status"], state)


if __name__ == "__main__":
    unittest.main()

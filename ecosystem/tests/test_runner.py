from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ecosystem import runner
from soltui import f5_batch


class RunnerTests(unittest.TestCase):
    def plan(self, home, *, offline=False):
        return runner.plan(
            home,
            coins=["BTC", "SOL"],
            intervals=["1d"],
            horizons=["medium"],
            strategies=["rsi"],
            start="2025-01-01",
            end="2025-02-01",
            offline=offline,
            recorder=False,
            manager_home=str(home / "manager"),
        )

    def test_foreground_recovers_failed_generation_without_rewriting_batch(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = self.plan(home)
            state.update(
                phase="failed",
                error="supervisor_failed",
                batch_id="a" * 32,
                supervisor_pid=1234,
            )
            runner.save(home / "state.json", state)
            with patch("ecosystem.runner.os.getpid", return_value=5678):
                token = runner.prepare_foreground(home)
            self.assertEqual(len(token), 32)
            current = runner.load(home)
            self.assertEqual(current["batch_id"], "a" * 32)
            self.assertEqual(current["config"], state["config"])
            self.assertEqual(current["phase"], "starting")
            self.assertEqual(current["supervisor_pid"], 5678)
            self.assertNotIn("error", current)

    def test_foreground_honors_explicit_stop_and_live_owner(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = self.plan(home)
            state.update(phase="stopped", supervisor_token="b" * 32)
            runner.save(home / "state.json", state)
            marker = home / ("stop-" + "b" * 32)
            marker.touch()
            before = (home / "state.json").read_bytes()
            self.assertIsNone(runner.prepare_foreground(home))
            self.assertEqual((home / "state.json").read_bytes(), before)
            marker.unlink()
            with runner.lock(home):
                self.assertIsNone(runner.prepare_foreground(home))
            self.assertIsNotNone(runner.prepare_foreground(home))
            self.assertIsNone(runner.prepare_foreground(home))

    def test_resume_preserves_frozen_matrix_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            initial = self.plan(home)
            self.assertEqual(self.plan(home)["run_id"], initial["run_id"])
            with self.assertRaises(ValueError):
                runner.plan(
                    home,
                    coins=["ETH"],
                    intervals=["1d"],
                    horizons=["medium"],
                    strategies=["rsi"],
                    start="2025-01-01",
                    end="2025-02-01",
                )

    def test_offline_blocks_unknown_data_and_never_starts_workers(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = self.plan(home, offline=True)
            state["supervisor_token"] = "a" * 32
            runner.save(home / "state.json", state)
            with (
                patch(
                    "ecosystem.data.acquire",
                    return_value={"status": "blocked", "reason": "missing"},
                ),
                patch("soltui.f5_batch.create", wraps=f5_batch.create) as create,
                patch("soltui.f5_batch.start") as start,
                patch(
                    "ecosystem.registration.sync_registrations",
                    return_value={"total": 2},
                ),
            ):
                self.assertEqual(runner.supervise(home, "a" * 32), 0)
            self.assertEqual(create.call_args.args[1], ["BTC", "SOL"])
            self.assertEqual(list((home / "accepted").glob("*.csv")), [])
            start.assert_not_called()
            self.assertEqual(runner.load(home)["phase"], "offline_prepared")

    def test_resume_does_not_redownload_or_duplicate_batch_owner(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = self.plan(home)
            state.update(batch_id="a" * 32, supervisor_token="a" * 32)
            runner.save(home / "state.json", state)
            feed = Mock()
            feed.poll.return_value = None
            with (
                patch("ecosystem.data.acquire") as acquire,
                patch(
                    "soltui.f5_batch.status",
                    return_value={"running": True, "phase": "forward_partial"},
                ),
                patch("soltui.f5_batch.start") as start,
                patch("oracle.feeds.RecorderFeed", return_value=feed),
                patch(
                    "ecosystem.registration.sync_registrations",
                    return_value={"total": 2},
                ),
            ):
                self.assertEqual(runner.supervise(home, "a" * 32, max_cycles=1), 0)
            acquire.assert_not_called()
            start.assert_not_called()
            self.assertEqual(runner.load(home)["phase"], "forward_partial")
            self.assertEqual(
                runner.load(home)["oracle"]["BTC"]["prediction"], "unavailable"
            )

    def test_stop_only_addresses_this_batch_and_keeps_recorder(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = self.plan(home)
            state.update(batch_id="a" * 32, supervisor_token="a" * 32)
            runner.save(home / "state.json", state)
            with patch("soltui.f5_batch.stop") as stop:
                result = runner.stop(home)
            stop.assert_called_once_with("a" * 32, root=home / "batches")
            self.assertFalse(result["stops_shared_recorder"])
            self.assertTrue((home / ("stop-" + "a" * 32)).exists())

    def test_publication_refuses_mutated_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            source = home / "source.csv"
            source.write_text("changed")
            with self.assertRaises(ValueError):
                runner.publish(
                    {"path": str(source), "sha256": "0" * 64}, home, "BTC", "1d"
                )
            self.assertFalse((home / "accepted" / "BTC_1d.csv").exists())


if __name__ == "__main__":
    unittest.main()


class RecoveryTests(unittest.TestCase):
    def test_concurrent_start_retains_first_reservation(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            RunnerTests().plan(home)
            with patch("ecosystem.runner.subprocess.Popen") as popen:
                popen.return_value.pid = 123
                first = runner.start(home)
                token = runner.load(home)["supervisor_token"]
                second = runner.start(home)
            self.assertEqual(first["status"], "start_requested")
            self.assertEqual(second["status"], "start_in_progress")
            self.assertEqual(runner.load(home)["supervisor_token"], token)
            self.assertEqual(popen.call_count, 1)
            self.assertIn("-I", popen.call_args.args[0])
            self.assertNotIn("PYTHONPATH", popen.call_args.kwargs["env"])
            self.assertNotIn("PYTHONHOME", popen.call_args.kwargs["env"])

    def test_stale_child_does_not_mark_new_generation_failed(self):
        import io
        from contextlib import redirect_stdout

        from ecosystem.cli import main

        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            state = RunnerTests().plan(home)
            state.update(supervisor_token="b" * 32, phase="backtesting")
            runner.save(home / "state.json", state)
            with (
                patch(
                    "ecosystem.runner.supervise", side_effect=ValueError("old child")
                ),
                redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(
                    main(["supervise", "--home", str(home), "--token", "c" * 32]), 3
                )
            self.assertEqual(runner.load(home)["phase"], "backtesting")

    def test_failed_atomic_publication_leaves_no_partial_name(self):
        import hashlib

        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            source = home / "source.csv"
            source.write_bytes(b"valid input")
            receipt = {
                "path": str(source),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
            with (
                patch("ecosystem.runner.os.link", side_effect=OSError("interrupted")),
                self.assertRaises(OSError),
            ):
                runner.publish(receipt, home, "BTC", "1d")
            self.assertFalse((home / "accepted" / "BTC_1d.csv").exists())
            self.assertEqual(list((home / "accepted").iterdir()), [])

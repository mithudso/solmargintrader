from __future__ import annotations

import tempfile
import threading
import types
import unittest
from contextlib import contextmanager, nullcontext
from pathlib import Path
from unittest.mock import Mock, patch

from ecosystem import pipeline_service as service
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

    def test_acknowledged_stop_targets_the_claimed_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = {
                "coins": ["SOL"],
                "intervals": ["1d"],
                "horizons": ["medium"],
                "strategies": ["rsi"],
                "start": "2025-01-01",
                "end": "2025-02-01",
                "offline": True,
                "recorder": False,
                "mode": "paper",
                "market_venue": "coinbase_exchange",
                "quote": "USD",
            }
            original = {
                "schema_version": 1,
                "run_id": "c" * 32,
                "phase": "failed",
                "supervisor_token": "a" * 32,
                "batch_id": None,
                "config": config,
            }
            runner.save(home / "state.json", original)
            condition = threading.Condition()
            done = threading.Event()
            waiting = threading.Event()
            errors = []
            old_guard = getattr(
                runner, "_generation_guard", lambda home, **kw: nullcontext()
            )

            @contextmanager
            def observed_guard(home, **kwargs):
                if threading.current_thread().name == "explicit-stop":
                    with condition:
                        waiting.set()
                        condition.notify_all()
                with old_guard(home, **kwargs):
                    yield

            def stop():
                try:
                    runner.stop(home)
                except Exception as error:  # noqa: BLE001 - report owned fixture thread failures on the test thread
                    errors.append(error)
                finally:
                    with condition:
                        done.set()
                        condition.notify_all()

            thread = threading.Thread(target=stop, name="explicit-stop")
            old_uuid = runner.uuid.uuid4
            first = [True]

            def next_uuid():
                if not first[0]:
                    return old_uuid()
                first[0] = False
                thread.start()
                with condition:
                    if not condition.wait_for(
                        lambda: done.is_set() or waiting.is_set(), timeout=2
                    ):
                        raise AssertionError(
                            "stop did not reach its observed coordination boundary"
                        )
                return types.SimpleNamespace(hex="b" * 32)

            try:
                with (
                    patch.object(
                        runner, "_generation_guard", observed_guard, create=True
                    ),
                    patch.object(runner.uuid, "uuid4", side_effect=next_uuid),
                ):
                    token = runner.prepare_foreground(home)
                    thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertTrue(done.is_set())
                current = runner.load(home)
                self.assertEqual(current["supervisor_token"], token)
                self.assertEqual(current["config"], original["config"])
                self.assertTrue(
                    (home / ("stop-" + current["supervisor_token"])).exists(),
                    "acknowledged stop must fence the committed generation",
                )
            finally:
                if thread.ident is not None:
                    thread.join(5)

    def test_disposable_installed_prefix_cannot_become_persistent_service(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "disposable-venv"
            module = (
                prefix / "lib/python3.13/site-packages/ecosystem/pipeline_service.py"
            )
            module.parent.mkdir(parents=True)
            module.write_text('"""Synthetic normal-wheel path fixture."""')
            home = Path(directory) / "planned"
            home.mkdir()
            user = Path(directory) / "synthetic-user"
            user.mkdir()
            with (
                patch.object(service.sys, "platform", "darwin"),
                patch.object(service.sys, "prefix", str(prefix)),
                patch.object(service.sys, "executable", str(prefix / "bin/python")),
                patch.object(service, "__file__", str(module)),
                patch.object(Path, "home", return_value=user),
                patch.object(
                    service.runner,
                    "load",
                    return_value={"phase": "planned", "config": {"mode": "paper"}},
                ),
                patch.object(service, "registered", side_effect=[False, True]),
                patch.object(
                    service.subprocess,
                    "run",
                    return_value=types.SimpleNamespace(returncode=0),
                ) as launch,
            ):
                with self.assertRaisesRegex(
                    ValueError, "stable_installed_pipeline_required"
                ):
                    service.operate("install", home)
                launch.assert_not_called()

    def test_pipeline_service_status_accepts_a_stable_normal_install(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "planned"
            home.mkdir()
            user = Path(directory) / "synthetic-user"
            user.mkdir()
            prefix = Path("/opt/oraclebot-fixture/stable-env")
            module = (
                prefix / "lib/python3.13/site-packages/ecosystem/pipeline_service.py"
            )
            with (
                patch.object(service.sys, "platform", "darwin"),
                patch.object(service.sys, "prefix", str(prefix)),
                patch.object(service.sys, "executable", str(prefix / "bin/python")),
                patch.object(service, "__file__", str(module)),
                patch.object(Path, "home", return_value=user),
                patch.object(
                    service.runner,
                    "load",
                    return_value={"phase": "planned", "config": {"mode": "paper"}},
                ),
                patch.object(service, "registered", return_value=False),
                patch.object(service.subprocess, "run") as launch,
            ):
                result = service.operate("status", home)
            self.assertFalse(result["registered"])
            self.assertFalse(result["definition_present"])
            launch.assert_not_called()

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

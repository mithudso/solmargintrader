"""Isolated HTTP identity and simulated process-launch checks; no production start."""

from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

from ecosystem import __version__, runner, ui_service


class UiServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "paper"
        self.instance = "a" * 32
        self.server = None

    def http(self):
        if self.server is not None:
            return

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass

            def do_GET(self):
                self.server.requests += 1
                if self.server.redirect:
                    self.send_response(302)
                    self.send_header("Location", self.server.url + "/other")
                    self.end_headers()
                    return
                raw = json.dumps(self.server.body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.url = f"http://127.0.0.1:{self.server.server_port}"
        self.server.redirect = False
        self.server.requests = 0
        self.server.body = {
            "schema_version": 1,
            "ok": True,
            "data": {
                "control_instance": self.instance,
                "control_home": str(self.home),
                    "manager_home": str(ui_service._manager_home()),
                "ecosystem_version": __version__,
            },
        }
        thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True
        )
        thread.start()

        def close():
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())

        self.addCleanup(close)

    def publish(self, manager_home=None):
        self.http()
        self.server.body["data"]["manager_home"] = str(ui_service._manager_home(manager_home))
        return ui_service.checkpoint(
            self.home, self.instance, self.server.url, pid=321, manager_home=manager_home
        )

    def test_status_without_data_is_inert(self):
        self.assertFalse(ui_service.status(self.home)["running"])
        self.assertFalse(self.home.exists())

    def test_real_identity_and_distinct_pipeline_lock(self):
        with runner.lock(self.home), ui_service.lock(self.home):
            self.publish()
            result = ui_service.status(self.home)
            self.assertTrue(result["running"])
            self.assertEqual(result["pid"], 321)
            self.assertEqual(result["version"], __version__)
            self.assertEqual(result["url"], self.server.url)
            self.assertTrue((self.home / "supervisor.lock").is_file())
            self.assertTrue((self.home / ui_service.LOCK_NAME).is_file())
            mode = stat.S_IMODE((self.home / ui_service.CHECKPOINT_NAME).stat().st_mode)
            self.assertEqual(mode, 0o600)

    def test_manager_home_is_bound_to_checkpoint_and_http_identity(self):
        selected = self.home / "manager-a"
        other = self.home / "manager-b"
        with ui_service.lock(self.home):
            self.publish(selected)
            self.assertTrue(ui_service.status(self.home, selected)["running"])
            with patch("ecosystem.ui_service.subprocess.Popen") as spawn:
                refused = ui_service.ensure(self.home, other)
            self.assertFalse(refused["running"])
            self.assertEqual(refused["reason"], "control_manager_home_mismatch")
            spawn.assert_not_called()
            self.server.body["data"]["manager_home"] = str(other)
            self.assertFalse(ui_service.status(self.home, selected)["running"])

    def test_checkpoint_requires_owner_and_cleanup_is_generation_scoped(self):
        with self.assertRaises(RuntimeError):
            ui_service.checkpoint(self.home, self.instance, "http://127.0.0.1:1")
        with ui_service.lock(self.home):
            self.publish()
            ui_service.clear_checkpoint(self.home, "b" * 32)
            self.assertTrue((self.home / ui_service.CHECKPOINT_NAME).is_file())
            ui_service.clear_checkpoint(self.home, self.instance)
            self.assertFalse((self.home / ui_service.CHECKPOINT_NAME).exists())

    def test_stale_pid_or_http_without_owner_never_establishes_running(self):
        with ui_service.lock(self.home):
            self.publish()
        with patch("ecosystem.ui_service.subprocess.Popen") as spawn:
            result = ui_service.ensure(self.home)
        self.assertFalse(result["running"])
        self.assertEqual(result["reason"], "control_server_owner_unverified")
        spawn.assert_not_called()

    def test_replaced_lock_inode_does_not_create_competing_server(self):
        with ui_service.lock(self.home):
            self.publish()
            (self.home / ui_service.LOCK_NAME).rename(self.home / "old-owner.lock")
            with patch("ecosystem.ui_service.subprocess.Popen") as spawn:
                result = ui_service.ensure(self.home)
            self.assertEqual(result["reason"], "control_server_owner_unverified")
            spawn.assert_not_called()

    def test_proxy_ignored_and_redirect_refused(self):
        with ui_service.lock(self.home):
            self.publish()
            with patch.dict(
                os.environ,
                {
                    "HTTP_PROXY": "http://127.0.0.1:1",
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                    "ALL_PROXY": "http://127.0.0.1:1",
                    "NO_PROXY": "",
                    "no_proxy": "",
                },
            ):
                self.assertTrue(ui_service.status(self.home)["running"])
            before = self.server.requests
            self.server.redirect = True
            self.assertFalse(ui_service.status(self.home)["running"])
            self.assertEqual(self.server.requests - before, 1)

    def test_bad_http_bodies_wrong_generation_and_version_fail_closed(self):
        with ui_service.lock(self.home):
            record = self.publish()
            original = self.server.body
            for body in (
                [],
                {"schema_version": 1, "ok": True, "data": {}},
                {"padding": "x" * (ui_service.MAX_BYTES + 1)},
            ):
                self.server.body = body
                self.assertFalse(ui_service.status(self.home)["running"])
            self.server.body = original
            self.server.body["data"]["control_instance"] = "b" * 32
            self.assertFalse(ui_service.status(self.home)["running"])
            self.server.body["data"]["control_instance"] = self.instance
            record["version"] = "0.0.0"
            runner.save(self.home / ui_service.CHECKPOINT_NAME, record)
            with patch("ecosystem.ui_service.subprocess.Popen") as spawn:
                result = ui_service.ensure(self.home)
            self.assertEqual(result["reason"], "control_server_version_mismatch")
            spawn.assert_not_called()

    def test_corrupt_private_or_foreign_pointer_is_not_followed(self):
        with ui_service.lock(self.home):
            record = self.publish()
            record["url"] = "http://example.invalid:8080"
            runner.save(self.home / ui_service.CHECKPOINT_NAME, record)
            with patch("ecosystem.ui_service._health") as probe:
                self.assertFalse(ui_service.status(self.home)["running"])
                probe.assert_not_called()
            self.publish()
            (self.home / ui_service.CHECKPOINT_NAME).chmod(0o644)
            self.assertFalse(ui_service.status(self.home)["running"])

    def test_launch_uses_installed_python_and_observes_actual_health(self):
        self.http()
        created = []
        observer = Mock()
        with ExitStack() as child:

            def spawned(*args, **kwargs):
                child.enter_context(ui_service.lock(self.home))
                self.publish(self.home / "manager")
                process = Mock(poll=Mock(return_value=None))
                created.append(process)
                return process

            with (
                patch(
                    "ecosystem.ui_service.subprocess.Popen", side_effect=spawned
                ) as spawn,
                patch.dict(
                    os.environ,
                    {
                        "PYTHONPATH": "/untrusted",
                        "PYTHONHOME": "/untrusted",
                        "PYTHONINSPECT": "1",
                    },
                ),
            ):
                result = ui_service.ensure(
                    self.home, self.home / "manager", on_spawn=observer
                )
            self.assertTrue(result["running"])
            observer.assert_called_once_with(created[0])
            command = spawn.call_args.args[0]
            self.assertEqual(command[1:4], ["-I", "-m", "ecosystem.web"])
            self.assertIn("--persistent", command)
            self.assertIn("--manager-home", command)
            kwargs = spawn.call_args.kwargs
            self.assertEqual(kwargs["cwd"], "/tmp")
            self.assertTrue(kwargs["start_new_session"])
            self.assertEqual(kwargs["env"]["PYTHONNOUSERSITE"], "1")
            self.assertFalse(
                {"PYTHONPATH", "PYTHONHOME", "PYTHONINSPECT"} & kwargs["env"].keys()
            )
            self.assertEqual(
                stat.S_IMODE((self.home / "control-room.log").stat().st_mode), 0o600
            )

    def test_existing_owner_is_not_transferred_to_spawn_observer(self):
        observer = Mock()
        with ui_service.lock(self.home):
            self.publish()
            with patch("ecosystem.ui_service.subprocess.Popen") as spawn:
                result = ui_service.ensure(self.home, on_spawn=observer)
            self.assertTrue(result["running"])
            spawn.assert_not_called()
            observer.assert_not_called()

    def test_concurrent_launches_spawn_only_once(self):
        ready = threading.Event()
        healthy = {
            "running": True,
            "url": "http://127.0.0.1:12345",
            "pid": 12,
            "version": __version__,
        }
        absent = {"running": False, "occupied": False, "owner_lock_held": False}
        timer = None

        def spawned(*args, **kwargs):
            nonlocal timer
            timer = threading.Timer(0.05, ready.set)
            timer.start()
            return Mock(poll=Mock(return_value=None))

        with (
            patch(
                "ecosystem.ui_service.status",
                side_effect=lambda home, manager_home=None: healthy if ready.is_set() else absent,
            ),
            patch(
                "ecosystem.ui_service.subprocess.Popen", side_effect=spawned
            ) as spawn,
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = list(pool.map(lambda _: ui_service.ensure(self.home), range(2)))
        if timer:
            timer.join(timeout=1)
        self.assertTrue(all(result["running"] for result in results))
        self.assertEqual(spawn.call_count, 1)

    def test_exited_child_is_not_retried_and_slow_start_is_unavailable(self):
        with patch(
            "ecosystem.ui_service.subprocess.Popen",
            return_value=Mock(poll=Mock(return_value=2)),
        ) as spawn:
            self.assertEqual(
                ui_service.ensure(self.home)["reason"], "control_server_exited"
            )
            self.assertEqual(spawn.call_count, 1)
        with (
            patch(
                "ecosystem.ui_service.subprocess.Popen",
                return_value=Mock(poll=Mock(return_value=None)),
            ) as spawn,
            patch.object(ui_service, "STARTUP_SECONDS", 0.06),
        ):
            self.assertEqual(
                ui_service.ensure(self.home)["reason"], "control_server_start_timeout"
            )
            self.assertEqual(spawn.call_count, 1)

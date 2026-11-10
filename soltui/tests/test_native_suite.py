"""The browser can request fixed availability actions, never paths or execution settings."""
from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from soltui import native_host as host, native_host_install as installer

ORIGIN = "chrome-extension://" + "a" * 32 + "/"


class NativeSuiteTests(unittest.TestCase):
    def setUp(self):
        host._suite_replies.clear()
        host._suite_pending.clear()
        self.env = patch.dict(os.environ, {"SOLTUI_EXTRA_EXTENSION_IDS": "a" * 32, "INDEX_NO_AUTO": "1"})
        self.env.start()
        self.argv = patch.object(host.sys, "argv", ["native-host", ORIGIN])
        self.argv.start()

    def tearDown(self):
        self.argv.stop()
        self.env.stop()

    def request(self, action="status", **fields):
        value = {"id": str(uuid4()), "op": "suite", "action": action, **fields}
        return json.loads(host.handle_request(json.dumps(value).encode()))["response"]

    def test_fixed_actions_only_and_unknown_fields_never_reach_controller(self):
        with patch.object(host, "suite_control", return_value={"fixture": True}) as control:
            for action in ("status", "health", "start"):
                self.assertTrue(self.request(action)["ok"])
            self.assertEqual([call.args[0] for call in control.call_args_list], ["status", "health", "start"])
            control.reset_mock()
            for key in ("home", "ecosystem_home", "argv", "url", "env", "origin", "command", "armed"):
                reply = self.request(**{key: "secret-canary"})
                self.assertFalse(reply["ok"])
                self.assertNotIn("secret-canary", json.dumps(reply))
            for action in ("install", "run", "stop", "restart", "uninstall", [], {}, None):
                self.assertFalse(self.request(action)["ok"])
            self.assertFalse(self.request(id="secret-canary")["ok"])
            control.assert_not_called()

    def test_missing_forged_and_hostile_chrome_origins_fail_before_any_home_is_created(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"SOLBOT_HOME": str(Path(tmp) / "absent")}), patch.object(host, "suite_control") as control:
            for argv in (["host"], ["host", ORIGIN + "?x"], ["host", "chrome-extension://" + "b" * 32], ["host", "https://127.0.0.1"]):
                with patch.object(host.sys, "argv", argv):
                    self.assertEqual(self.request("start")["error"]["code"], "forbidden")
            self.assertFalse((Path(tmp) / "absent").exists())
            control.assert_not_called()

    def test_request_identity_deduplicates_start_and_rejects_conflicting_reuse(self):
        identity = str(uuid4())
        with patch.object(host, "suite_control", return_value={"fixture": True}) as control:
            first = self.request("start", id=identity)
            self.assertEqual(self.request("start", id=identity), first)
            self.assertEqual(self.request("status", id=identity)["error"]["code"], "bad_params")
            control.assert_called_once_with("start")

    def test_concurrent_start_is_bounded_and_status_stays_available(self):
        entered, release = threading.Event(), threading.Event()
        def operation(action):
            if action == "start":
                entered.set()
                self.assertTrue(release.wait(3))
            return {"action": action}
        with patch.object(host, "suite_control", side_effect=operation):
            thread = threading.Thread(target=lambda: self.request("start"))
            thread.start()
            self.assertTrue(entered.wait(3))
            try:
                self.assertEqual(self.request("start")["error"]["code"], "busy")
                self.assertTrue(self.request("health")["ok"])
            finally:
                release.set()
                thread.join(3)
            self.assertFalse(thread.is_alive())

    def test_controller_failures_are_sanitized_and_missing_runtime_is_incompatible(self):
        for error, code in ((RuntimeError("secret-canary"), "suite_failed"), (ImportError("secret-canary"), "incompatible_helper")):
            with patch.object(host, "suite_control", side_effect=error):
                response = self.request("start")
                self.assertEqual(response["error"]["code"], code)
                self.assertNotIn("secret-canary", json.dumps(response))
                if code == 'suite_failed':
                    self.assertIn('solbot stack status', response['error']['message'])

    def test_real_status_and_health_do_not_create_homes_or_start_owners(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'SOLBOT_HOME': str(Path(tmp) / 'manager'), 'SOLBOT_ECOSYSTEM_HOME': str(Path(tmp) / 'ecosystem')}):
            for action in ('status', 'health'):
                response = self.request(action)
                self.assertTrue(response['ok'], response)
                self.assertEqual(response['result']['health']['overall'], 'down')
                self.assertIsNone(response['result']['status']['ui_url'])
            self.assertFalse((Path(tmp) / 'manager').exists())
            self.assertFalse((Path(tmp) / 'ecosystem').exists())

    def test_corrupt_checkpoint_url_does_not_cross_native_boundary(self):
        from botmanager import machine_health, suite
        with patch.object(suite, 'operation', return_value={'state': 'running', 'ui_url': 'http://secret-canary.example/'}), patch.object(
                machine_health, 'check', return_value={'schema_version': 1, 'ui_url': 'http://secret-canary.example/'}):
            response = self.request('health')
            self.assertTrue(response['ok'])
            self.assertIsNone(response['result']['status']['ui_url'])
            self.assertNotIn('secret-canary', json.dumps(response))

    def test_local_installer_pins_homes_preserves_chrome_origin_and_supports_linux_paths(self):
        wrapper = installer.wrapper_text(Path("/tmp/source"), Path("/tmp/python"),
            manager_home=Path("/tmp/manager space"), ecosystem_home=Path("/tmp/ecosystem"))
        self.assertIn('soltui.native_host "$@"', wrapper)
        self.assertIn("export INDEX_NO_AUTO=1", wrapper)
        self.assertIn(f"export SOLTUI_EXTENSION_DIR={Path('/tmp/source').resolve() / 'extension'}", wrapper)
        self.assertIn("a" * 32, wrapper)
        self.assertIn(f"export SOLBOT_HOME='{Path('/tmp/manager space').resolve()}'", wrapper)
        with tempfile.TemporaryDirectory() as tmp, patch.object(installer.sys, "platform", "linux"):
            root = Path(tmp)
            (root / "google-chrome").mkdir()
            self.assertEqual(installer.browser_host_dirs(root), [root / "google-chrome/NativeMessagingHosts"])
        with tempfile.TemporaryDirectory() as tmp, patch.object(installer.sys, "platform", "win32"):
            wrapper_path = Path(tmp) / "host"
            with self.assertRaisesRegex(ValueError, "Windows requires an explicit native port"):
                installer.install(wrapper=wrapper_path)
            self.assertFalse(wrapper_path.exists())

    def test_installer_extra_origin_is_pinned_in_the_process_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = installer.install(repo=root, python=Path('/tmp/python'), extra_ids=['b' * 32],
                dirs=[root / 'NativeMessagingHosts'], wrapper=root / 'host')
            text = (root / 'host').read_text()
            self.assertIn('b' * 32, text)
            self.assertIn('chrome-extension://' + 'b' * 32 + '/', result['allowed_origins'])
            with self.assertRaisesRegex(ValueError, 'extension ids'):
                installer.allowed_origins(['secret-canary'])

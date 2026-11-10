"""Browser owner registration trusts Chrome process origin, never a JSON claim."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from soltui import native_host
from soltui.native_host_install import wrapper_text

ORIGIN = 'chrome-extension://' + 'a' * 32


class BrowserNativeTests(unittest.TestCase):
    def message(self):
        return {"id": str(uuid4()), "op": "browserManager", "message": {
            "schema_version": 1, "receipts": [], "snapshot": {
                "installation_id": str(uuid4()), "native_id": "grid", "generation": 0,
                "config_revision": 1, "config_hash": "1" * 64, "source_hash": "2" * 64,
                "runtime_id": None, "running": False, "mode": "dry-run", "armed": False,
                "kill_switch": False, "extension_version": "0.6.4"}}}

    def test_actual_origin_and_strict_protocol(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                "SOLBOT_HOME": tmp, "SOLTUI_EXTRA_EXTENSION_IDS": "a" * 32}), patch.object(native_host.sys, "argv", ["native-host", ORIGIN]):
            request = self.message()
            reply = json.loads(native_host.handle_request(json.dumps(request).encode()))
            self.assertTrue(reply['response']['ok'])
            self.assertEqual(reply['response']['result']['origin'], ORIGIN)
            self.assertTrue((Path(tmp) / 'browser.sqlite3').exists())
            for hostile in ({**request, "origin": "secret-canary"}, {**request, "id": "secret-canary"},
                            {**request, "message": {**request["message"], "secret": "secret-canary"}}):
                response = native_host.handle_request(json.dumps(hostile).encode())
                self.assertFalse(json.loads(response)['response']['ok'])
                self.assertNotIn(b'secret-canary', response)

    def test_unknown_or_missing_process_origin_does_not_initialize_manager(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                "SOLBOT_HOME": tmp, "SOLTUI_EXTRA_EXTENSION_IDS": "a" * 32}):
            for argv in (["native-host"], ["native-host", 'chrome-extension://' + 'b' * 32]):
                with patch.object(native_host.sys, "argv", argv):
                    reply = json.loads(native_host.handle_request(json.dumps(self.message()).encode()))
                self.assertFalse(reply['response']['ok'])
                self.assertFalse((Path(tmp) / 'browser.sqlite3').exists())

    def test_generated_wrapper_forwards_chrome_origin_without_installing(self):
        text = wrapper_text(Path('/tmp/test-source'), Path('/tmp/test-python'))
        self.assertIn('soltui.native_host "$@"', text)

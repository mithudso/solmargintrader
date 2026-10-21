"""The LaunchAgent plist soltui-service renders must not change.

`soltui-service` used to build the plist itself; it now renders it through
macos-launchd-supervisor. GOLDEN below is the dict the hand-written
`agent_plist()` returned before that migration (captured from the old code with
HOME=/home/u), so this fails if the library ever renders something different
-- in particular a RunAtLoad key, or a KeepAlive that is not PathState-gated.
Only XML key order may differ (the old code sorted keys, the library does not).

No launchctl call is made: only the pure render runs.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import plistlib
import unittest
from pathlib import Path
from unittest import mock

SERVICE = Path(__file__).resolve().parent.parent / "soltui-service"

GOLDEN = {
    "Label": "com.mitchhudson.soltui",
    "ProgramArguments": ["/home/u/Applications/SolTUI.app/Contents/MacOS/SolTUI"],
    "KeepAlive": {
        "PathState": {"/home/u/Library/Application Support/soltui/supervise.enabled": True}
    },
    "ThrottleInterval": 15,
    "ProcessType": "Interactive",
    "EnvironmentVariables": {"LANG": "en_US.UTF-8", "PYTHONUTF8": "1"},
    "StandardOutPath": "/home/u/Library/Logs/soltui.launchd.log",
    "StandardErrorPath": "/home/u/Library/Logs/soltui.launchd.log",
}


def load_service():
    with mock.patch.dict(os.environ, {"HOME": "/home/u"}):
        loader = importlib.machinery.SourceFileLoader("soltui_service_parity", str(SERVICE))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
    return module


class PlistParity(unittest.TestCase):
    def test_agent_plist_equals_the_pre_migration_plist(self) -> None:
        self.assertEqual(load_service().agent_plist(), GOLDEN)

    def test_written_bytes_parse_to_the_same_plist(self) -> None:
        svc = load_service()
        self.assertEqual(plistlib.loads(svc.render_plist(svc.service_spec())), GOLDEN)

    def test_no_run_at_load(self) -> None:
        self.assertNotIn("RunAtLoad", load_service().agent_plist())


if __name__ == "__main__":
    unittest.main()

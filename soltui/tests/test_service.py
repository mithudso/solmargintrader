"""Tests for `soltui-service`, the LaunchAgent manager.

The script is dash-named so that it reads as a command rather than a module,
which means it cannot be imported normally; it is loaded by path below.

What these cover is one failure that cost a debugging session: the agent plist
sitting on disk while launchd knows nothing about it. `launchctl kickstart`
against a job that does not exist fails, `start` ignored that return code, and so
it printed "started" while nothing ran -- no menu-bar item, no console window,
and an empty launchd log offering no hint. Every assertion here exists to keep
`start`'s printed success honest.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock

REPO = Path(__file__).resolve().parent.parent.parent
SERVICE = REPO / "soltui" / "soltui-service"


def load_service() -> ModuleType:
    """Import the dash-named script as a module.

    Importing it is safe: everything at module scope is path arithmetic, and the
    subcommands only run under `__name__ == "__main__"`.
    """
    loader = importlib.machinery.SourceFileLoader("soltui_service", str(SERVICE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def ok(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, 0, "", "")


def fail(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, 1, "", "No such process")


class ServiceTestCase(unittest.TestCase):
    """Base: a loaded module and a scratch directory for its state paths."""

    def setUp(self) -> None:
        self.svc = load_service()
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

        self.agent = self.tmp / "com.mitchhudson.soltui.plist"
        self.support = self.tmp / "support"
        self.flag = self.support / "supervise.enabled"

        self.patches = [
            mock.patch.object(self.svc, "AGENT", self.agent),
            mock.patch.object(self.svc, "SUPPORT", self.support),
            mock.patch.object(self.svc, "FLAG", self.flag),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)


class StartLoadsTheAgent(ServiceTestCase):
    """`start` must ensure the agent is loaded, not assume it."""

    def test_bootstraps_when_the_agent_is_not_loaded(self) -> None:
        self.agent.write_text("<plist/>")
        with mock.patch.object(self.svc, "is_loaded", return_value=False), \
             mock.patch.object(self.svc, "reload_agent",
                               return_value=True) as reload_agent, \
             mock.patch.object(self.svc, "run", side_effect=ok):
            rc = self.svc.start()

        reload_agent.assert_called_once()
        self.assertEqual(rc, 0)
        self.assertTrue(self.flag.exists(), "the supervise flag must be created")

    def test_does_not_rebootstrap_when_already_loaded(self) -> None:
        """Booting out a healthy job would kill a running app for nothing."""
        self.agent.write_text("<plist/>")
        with mock.patch.object(self.svc, "is_loaded", return_value=True), \
             mock.patch.object(self.svc, "reload_agent") as reload_agent, \
             mock.patch.object(self.svc, "run", side_effect=ok):
            rc = self.svc.start()

        reload_agent.assert_not_called()
        self.assertEqual(rc, 0)

    def test_fails_when_the_agent_cannot_be_loaded(self) -> None:
        """A start that could not load the agent must not report success."""
        self.agent.write_text("<plist/>")
        with mock.patch.object(self.svc, "is_loaded", return_value=False), \
             mock.patch.object(self.svc, "reload_agent", return_value=False), \
             mock.patch.object(self.svc, "run", side_effect=ok):
            rc = self.svc.start()

        self.assertEqual(rc, 1)

    def test_fails_when_there_is_no_agent_plist(self) -> None:
        """Nothing to load: point at `install` rather than kickstart nothing."""
        with mock.patch.object(self.svc, "is_loaded", return_value=False), \
             mock.patch.object(self.svc, "reload_agent") as reload_agent, \
             mock.patch.object(self.svc, "run", side_effect=ok):
            rc = self.svc.start()

        reload_agent.assert_not_called()
        self.assertEqual(rc, 1)

    def test_fails_when_kickstart_fails(self) -> None:
        """The exact silent failure: kickstart returned non-zero, start said OK."""
        self.agent.write_text("<plist/>")
        with mock.patch.object(self.svc, "is_loaded", return_value=True), \
             mock.patch.object(self.svc, "run", side_effect=fail):
            rc = self.svc.start()

        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

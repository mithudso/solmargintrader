"""Service fixtures never call the machine's actual user service manager."""

import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.worker import lifetime_lock

from botmanager import suite_service as service


class ServiceManager:
    def __init__(self, platform="darwin", fail=False):
        self.platform, self.fail = platform, fail
        self.active = False
        self.enabled = False
        self.fail_command = None
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:2] == ["launchctl", "print"]:
            return subprocess.CompletedProcess(
                argv, 0 if self.active else 113, b"", b""
            )
        if argv[:3] == ["systemctl", "--user", "show"]:
            return subprocess.CompletedProcess(
                argv,
                0,
                b"loaded\nactive\n" if self.active else b"not-found\ninactive\n",
                b"",
            )
        if argv[:3] == ["systemctl", "--user", "is-enabled"]:
            return subprocess.CompletedProcess(argv, 0 if self.enabled else 1, b"", b"")
        if argv[0] == "systemctl" and argv[2] == self.fail_command:
            return subprocess.CompletedProcess(argv, 1, b"", b"")
        if argv[0] == "launchctl":
            if argv[1] == "bootstrap" and not self.fail:
                self.active = True
            if argv[1] == "bootout":
                self.active = False
        elif argv[2:4] == ["enable", "--now"] and not self.fail:
            self.active = True
            self.enabled = True
        elif argv[2:4] == ["disable", "--now"]:
            self.active = False
            if not self.fail:
                self.enabled = False
        return subprocess.CompletedProcess(argv, 1 if self.fail else 0, b"", b"")


class SuiteServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home, self.ecosystem = self.root / "manager", self.root / "ecosystem"
        self.directory = self.root / "services"
        self.executable = self.root / "stable/bin/solbot"
        self.fixture = ServiceManager()
        self.addCleanup(patch.stopall)
        patch(
            "botmanager.suite_service.installed_executable",
            return_value=self.executable,
        ).start()
        patch("botmanager.suite_service._invoke", side_effect=self.fixture).start()

    def operation(self, action, platform="darwin"):
        return service.operation(
            action,
            self.home,
            self.ecosystem,
            directory=self.directory,
            platform_name=platform,
        )

    def test_status_queries_registration_without_creating_files(self):
        value = self.operation("status")
        self.assertFalse(value["installed"])
        self.assertFalse(value["registered"])
        self.assertFalse(self.home.exists())
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.fixture.calls[0][1], "print")

    def test_mac_install_fixed_homes_keepalive_and_stop_then_reenable(self):
        value = self.operation("install")
        self.assertTrue(value["registered"])
        path = Path(value["definition_path"])
        definition = plistlib.loads(path.read_bytes())
        self.assertEqual(
            definition["ProgramArguments"],
            [
                str(self.executable),
                "--ecosystem-home",
                str(self.ecosystem),
                "stack",
                "run",
            ],
        )
        self.assertEqual(
            definition["EnvironmentVariables"]["SOLBOT_HOME"], str(self.home)
        )
        self.assertEqual(definition["EnvironmentVariables"]["INDEX_NO_AUTO"], "1")
        self.assertTrue(definition["KeepAlive"])
        self.assertTrue(definition["RunAtLoad"])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.operation("stop")
        self.assertFalse(self.fixture.active)
        self.assertTrue(path.exists())
        self.assertIn(
            ["launchctl", "disable", f"gui/{os.getuid()}/{service.label(self.home)}"],
            self.fixture.calls,
        )
        self.operation("start")
        self.assertTrue(self.fixture.active)
        self.operation("uninstall")
        self.assertFalse(path.exists())
        self.assertFalse(self.fixture.active)

    def test_stale_definition_and_registered_missing_definition_are_retained(self):
        self.directory.mkdir()
        path = service._path(self.home, "darwin", self.directory)
        path.write_bytes(b"stale")
        path.chmod(0o600)
        with self.assertRaises(ManagerError) as raised:
            self.operation("uninstall")
        self.assertEqual(raised.exception.code, "identity_conflict")
        self.assertEqual(path.read_bytes(), b"stale")
        path.unlink()
        self.fixture.active = True
        with self.assertRaises(ManagerError):
            self.operation("install")
        self.assertTrue(self.fixture.active)
        self.assertFalse(path.exists())

    def test_unsafe_or_oversized_definitions_cannot_authorize_unloading(self):
        self.directory.mkdir()
        path = service._path(self.home, "darwin", self.directory)
        path.write_bytes(b"x" * 65_537)
        path.chmod(0o600)
        with self.assertRaises(ManagerError):
            self.operation("uninstall")
        self.assertFalse(any(call[1] == "bootout" for call in self.fixture.calls))

    def test_independent_manager_refuses_install_and_preserves_owner(self):
        with (
            lifetime_lock(self.home / "supervisor.lock"),
            self.assertRaises(ManagerError) as raised,
        ):
            self.operation("install")
        self.assertEqual(raised.exception.code, "suite_owner_conflict")
        self.assertFalse(self.directory.exists())

    def test_unconfirmed_activation_keeps_definition_for_recovery(self):
        self.fixture.fail = True
        with self.assertRaises(ManagerError):
            self.operation("install")
        self.assertTrue(service._path(self.home, "darwin", self.directory).exists())
        self.fixture.fail = False
        self.assertTrue(self.operation("install")["registered"])

    def test_linux_unit_has_fixed_argv_and_user_enablement(self):
        value = self.operation("install", "linux")
        self.assertTrue(value["registered"])
        text = Path(value["definition_path"]).read_text()
        self.assertIn("Restart=always", text)
        self.assertIn("KillMode=control-group", text)
        self.assertIn("WantedBy=default.target", text)
        self.assertIn("INDEX_NO_AUTO=1", text)
        self.assertIn(
            [
                "systemctl",
                "--user",
                "enable",
                "--now",
                Path(value["definition_path"]).name,
            ],
            self.fixture.calls,
        )
        self.operation("stop", "linux")
        self.assertFalse(self.fixture.active)
        self.operation("uninstall", "linux")

    def test_linux_quotes_percent_and_refuses_control_characters(self):
        self.assertEqual(service._quote('a%b"c'), '"a%%b\\"c"')
        with self.assertRaises(ManagerError):
            service._quote("new\nline")

    def test_linux_failed_enable_or_disable_is_not_inferred_from_activity(self):
        self.operation("install", "linux")
        self.fixture.fail_command = "enable"
        with self.assertRaises(ManagerError):
            self.operation("start", "linux")
        self.assertTrue(self.fixture.active)
        self.fixture.active = False
        self.fixture.fail_command = "disable"
        with self.assertRaises(ManagerError):
            self.operation("stop", "linux")
        self.assertTrue(self.fixture.enabled)

    def test_native_windows_is_explicitly_unsupported(self):
        self.assertIsNone(self.operation("status", "win32")["registered"])
        with self.assertRaises(ManagerError) as raised:
            self.operation("install", "win32")
        self.assertEqual(raised.exception.code, "capability_unavailable")
        self.assertEqual(self.fixture.calls, [])


if __name__ == "__main__":
    unittest.main()

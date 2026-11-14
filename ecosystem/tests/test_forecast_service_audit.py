"""Isolated lifecycle regressions; no test may call the owner's launchd service."""

from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import plistlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ecosystem import forecast_service


class ForecastServiceAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="forecast-service-audit-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.user = self.root / "user"
        self.user.mkdir(mode=0o700)
        self.home = self.user / "state"
        self.home.mkdir(mode=0o700)
        self.prices = self.user / "prices"
        self.prices.mkdir(mode=0o700)
        self.prefix = Path("/opt/oraclebot-owner/.venv")
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(mock.patch.object(Path, "home", return_value=self.user))
        stack.enter_context(
            mock.patch.object(forecast_service.sys, "platform", "darwin")
        )
        stack.enter_context(
            mock.patch.object(forecast_service.sys, "prefix", str(self.prefix))
        )
        stack.enter_context(
            mock.patch.object(
                forecast_service.sys, "executable", str(self.prefix / "bin/python")
            )
        )
        stack.enter_context(
            mock.patch.object(
                forecast_service,
                "__file__",
                str(
                    self.prefix
                    / "lib/python3.13/site-packages/ecosystem/forecast_service.py"
                ),
            )
        )
        self.registered = stack.enter_context(
            mock.patch.object(forecast_service, "registered", return_value=False)
        )
        self.run = stack.enter_context(
            mock.patch.object(
                forecast_service.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, "", ""),
            )
        )

    def invoke(self, action="install", home=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = forecast_service.main(
                [action, "--home", str(home or self.home), "--prices", str(self.prices)]
            )
        return code, json.loads(output.getvalue())

    def definition_path(self):
        expected = forecast_service.definition(
            self.home.resolve(), self.prefix / "bin/python", self.prices
        )
        return self.user / "Library/LaunchAgents" / (expected["Label"] + ".plist")

    def test_rejects_temporary_and_worktree_prefixes_before_service_lookup(self):
        prefixes = (
            "/tmp/forecast-env",
            "/private/tmp/forecast-env",
            "/var/folders/fixture/forecast-env",
            "/private/var/folders/fixture/forecast-env",
            "/Users/fixture/dev/worktrees/review/.venv",
            "/Users/fixture/dev/.worktrees/review/.venv",
            "/Users/fixture/dev/solmargintrader-wt-review/.venv",
        )
        for prefix in prefixes:
            with self.subTest(prefix=prefix), mock.patch.object(
                forecast_service.sys, "prefix", prefix
            ), mock.patch.object(
                forecast_service,
                "__file__",
                prefix + "/lib/python3.13/site-packages/ecosystem/forecast_service.py",
            ):
                code, result = self.invoke()
                self.assertEqual(code, 3)
                self.assertFalse(result["ok"])
                self.assertEqual(
                    result["reason"], "stable_installed_evaluator_required"
                )
        self.registered.assert_not_called()
        self.run.assert_not_called()
        self.assertFalse((self.user / "Library").exists())

    def test_rejects_module_outside_installed_prefix(self):
        with mock.patch.object(
            forecast_service,
            "__file__",
            "/opt/other/lib/python3.13/site-packages/ecosystem/forecast_service.py",
        ):
            code, result = self.invoke()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "immutable_installed_evaluator_required")
        self.registered.assert_not_called()
        self.run.assert_not_called()

    def test_parent_and_symlink_aliases_share_one_service_identity(self):
        self.registered.side_effect = [False, True, True, True, True, True]
        first = forecast_service.operate("install", self.home, self.prices)
        parent_alias = self.home / ".." / self.home.name
        link = self.root / "user-alias"
        link.symlink_to(self.user, target_is_directory=True)
        for alias in (parent_alias, link / self.home.name):
            with self.subTest(alias=str(alias)):
                result = forecast_service.operate("install", alias, self.prices)
                self.assertEqual(result, first)
        self.run.assert_called_once()
        definition = plistlib.loads(self.definition_path().read_bytes())
        self.assertIn(str(self.home.resolve()), definition["ProgramArguments"])
        self.assertEqual(len(list(self.definition_path().parent.glob("*.plist"))), 1)

    def test_final_component_home_symlink_remains_refused(self):
        alias = self.user / "state-alias"
        alias.symlink_to(self.home, target_is_directory=True)
        code, result = self.invoke(home=alias)
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "owned_macos_home_required")
        self.registered.assert_not_called()
        self.run.assert_not_called()

    def test_unconfirmed_start_is_failure_and_retains_definition(self):
        self.registered.side_effect = [False, False]
        code, result = self.invoke()
        self.assertEqual(code, 3)
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "forecast_start_unconfirmed")
        self.assertTrue(self.definition_path().is_file())
        self.assertEqual(self.definition_path().stat().st_mode & 0o777, 0o600)
        self.run.assert_called_once_with(
            [
                "launchctl",
                "bootstrap",
                f"gui/{os.getuid()}",
                str(self.definition_path()),
            ],
            capture_output=True,
            timeout=10,
            check=True,
        )

    def test_confirmed_start_reports_success(self):
        self.registered.side_effect = [False, True]
        code, result = self.invoke()
        self.assertEqual(code, 0)
        self.assertTrue(result["ok"])
        self.assertIs(result["data"]["installed"], True)
        self.assertEqual(result["data"]["definition"], str(self.definition_path()))
        self.run.assert_called_once()

    def test_status_does_not_bootstrap_or_write(self):
        code, result = self.invoke("status")
        self.assertEqual(code, 0)
        self.assertFalse(result["data"]["registered"])
        self.assertFalse(result["data"]["definition_present"])
        self.assertFalse((self.user / "Library").exists())
        self.run.assert_not_called()

    def test_identity_conflict_diagnostic_preserves_existing_definition(self):
        path = self.definition_path()
        path.parent.mkdir(parents=True)
        original = plistlib.dumps({"Label": "other-owned-service"})
        path.write_bytes(original)
        code, result = self.invoke()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "forecast_service_identity_conflict")
        self.assertIn("Inspect", result["remediation"])
        self.assertEqual(path.read_bytes(), original)
        self.registered.assert_not_called()
        self.run.assert_not_called()

    def test_non_macos_diagnostic_precedes_launchctl(self):
        with mock.patch.object(forecast_service.sys, "platform", "linux"):
            code, result = self.invoke()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "macos_forecast_service_required")
        self.assertIn("macOS", result["remediation"])
        self.registered.assert_not_called()
        self.run.assert_not_called()

    def test_known_failures_have_only_allowlisted_diagnostics(self):
        for reason, remediation in forecast_service._FAILURE_REMEDIATION.items():
            with self.subTest(reason=reason), mock.patch.object(
                forecast_service, "operate", side_effect=ValueError(reason)
            ):
                code, result = self.invoke()
                self.assertEqual(code, 3)
                self.assertEqual(
                    result,
                    {
                        "ok": False,
                        "error": "forecast_service_unavailable",
                        "reason": reason,
                        "remediation": remediation,
                    },
                )
        self.run.assert_not_called()

    def test_unknown_and_subprocess_errors_do_not_leak_details(self):
        secret = "synthetic-private-error-detail"
        cases = (
            (ValueError(secret), None),
            (OSError(secret), "forecast_service_io_failed"),
            (
                subprocess.CalledProcessError(
                    1, ["launchctl", secret], output=secret, stderr=secret
                ),
                "forecast_launchctl_failed",
            ),
        )
        for error, reason in cases:
            with self.subTest(error=type(error).__name__), mock.patch.object(
                forecast_service, "operate", side_effect=error
            ):
                code, result = self.invoke()
                self.assertEqual(code, 3)
                self.assertFalse(result["ok"])
                self.assertNotIn(secret, json.dumps(result))
                self.assertEqual(result.get("reason"), reason)
        self.run.assert_not_called()

    def test_missing_launchctl_has_safe_prerequisite_diagnostic(self):
        error = FileNotFoundError(errno.ENOENT, "missing", "launchctl")
        with mock.patch.object(forecast_service, "operate", side_effect=error):
            code, result = self.invoke()
        self.assertEqual(code, 3)
        self.assertEqual(result["reason"], "launchctl_required")
        self.assertIn("launchctl", result["remediation"])
        self.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.cli import main, parser
from botmanager.operations_commands import (
    component_alerts_command,
    health_check_command,
    stack_command,
    ui_command,
)
from botmanager.registry import CommandContext, dispatch


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "absent-manager"
        self.ecosystem = Path(self.temp.name) / "absent-ecosystem"
        self.context = CommandContext(home=self.home, ecosystem_home=self.ecosystem)

    def test_new_commands_share_registry_and_parser(self):
        for command in ("health-check", "metrics", "component-alerts", "ui"):
            self.assertEqual(parser().parse_args([command]).command, command)
        self.assertEqual(parser().parse_args(["ui"]).action, "status")

    def test_health_reads_missing_homes_without_initializing_them(self):
        data = health_check_command({}, self.context)
        self.assertEqual(data["schema_version"], 1)
        self.assertFalse(data["ready"])
        self.assertEqual(
            set(data["components"]), {"suite", "manager", "control_room", "market_data"}
        )
        self.assertFalse(self.home.exists())
        self.assertFalse(self.ecosystem.exists())

    def test_ui_status_is_inert_and_does_not_guess_url(self):
        result = ui_command({}, self.context)
        self.assertFalse(result["running"])
        self.assertIsNone(result.get("url"))
        self.assertEqual(result["action"], "status")
        self.assertFalse(self.home.exists())
        self.assertFalse(self.ecosystem.exists())

    def test_missing_optional_ui_package_is_a_structured_capability_refusal(self):
        with patch.dict("sys.modules", {"ecosystem.ui_service": None}):
            result = dispatch("ui", {}, self.context)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "capability_unavailable")

    def test_browser_launch_exception_retains_verified_url(self):
        with (
            patch("botmanager.suite.operation"),
            patch(
                "ecosystem.ui_service.status",
                return_value={
                    "running": True,
                    "url": "http://127.0.0.1:57927",
                    "reason": None,
                },
            ),
            patch("webbrowser.open", side_effect=OSError("unavailable opener")),
        ):
            result = ui_command({"action": "open"}, self.context)
        self.assertFalse(result["opened"])
        self.assertEqual(result["url"], "http://127.0.0.1:57927")
        self.assertEqual(result["reason"], "browser_launch_unavailable")

    def test_ui_open_requires_actual_verified_readiness(self):
        with (
            patch("botmanager.suite.operation") as operation,
            patch(
                "ecosystem.ui_service.status",
                return_value={
                    "running": False,
                    "url": None,
                    "reason": "control_checkpoint_pending",
                },
            ),
            patch("webbrowser.open") as open_browser,
        ):
            result = ui_command({"action": "open"}, self.context)
        operation.assert_called_once_with(
            "start", home=self.home, ecosystem_home=self.ecosystem
        )
        open_browser.assert_not_called()
        self.assertFalse(result["opened"])

    def test_ui_open_uses_verified_url_and_exposes_launch_failure(self):
        with (
            patch("botmanager.suite.operation"),
            patch(
                "ecosystem.ui_service.status",
                return_value={
                    "running": True,
                    "url": "http://127.0.0.1:57927",
                    "reason": None,
                },
            ),
            patch("webbrowser.open", return_value=False) as open_browser,
        ):
            result = ui_command({"action": "open"}, self.context)
        open_browser.assert_called_once_with("http://127.0.0.1:57927", new=2)
        self.assertEqual(result["url"], "http://127.0.0.1:57927")
        self.assertEqual(result["reason"], "browser_launch_unavailable")

    def test_stack_and_alerts_pass_only_fixed_context_and_bounded_cursor(self):
        with patch(
            "botmanager.suite.operation", return_value={"running": True}
        ) as operation:
            self.assertTrue(
                stack_command({"action": "status"}, self.context)["running"]
            )
        operation.assert_called_once_with(
            "status", home=self.home, ecosystem_home=self.ecosystem
        )
        with patch("botmanager.suite.alerts", return_value={"items": []}) as alerts:
            self.assertEqual(
                component_alerts_command({"after": 2, "limit": 5}, self.context),
                {"items": []},
            )
        alerts.assert_called_once_with(home=self.home, after=2, limit=5)

    def test_metrics_success_prints_only_prometheus_text(self):
        envelope = {
            "ok": True,
            "data": {
                "format": "prometheus",
                "rendered": 'solbot_component_ready{component="suite"} 0\n',
            },
        }
        output = io.StringIO()
        with (
            patch("botmanager.cli.dispatch", return_value=envelope),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["metrics"]), 0)
        self.assertTrue(output.getvalue().startswith("solbot_component_ready{"))
        self.assertNotIn('"ok"', output.getvalue())

    def test_metrics_failure_preserves_sanitized_json_and_exit_code(self):
        envelope = {
            "schema_version": 1,
            "request_id": "receipt",
            "ok": False,
            "data": None,
            "error": {"code": "suite_config_unavailable", "message": "Unavailable."},
        }
        output = io.StringIO()
        with (
            patch("botmanager.cli.dispatch", return_value=envelope),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["metrics"]), 3)
        self.assertEqual(json.loads(output.getvalue()), envelope)

    def test_structured_help_contains_same_workflow_without_writes(self):
        result = dispatch("help", {}, self.context)
        self.assertTrue(result["ok"])
        self.assertIn("stages", result["data"]["workflow"])
        self.assertFalse(self.home.exists())
        self.assertFalse(self.ecosystem.exists())

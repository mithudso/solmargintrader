"""CLI home selection and observed UI readiness; never starts a real service."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ecosystem import cli


class CliTests(unittest.TestCase):
    def test_restart_preserves_frozen_provider_and_accounting_inputs(self):
        existing = {
            "research_capital": 2500,
            "swap_provider": "jupiter",
            "cost_model": {"source": "configured_scenario"},
            "embedded_ui": False,
        }
        with (
            patch("ecosystem.runner.running", side_effect=[False, True]),
            patch(
                "ecosystem.runner.load",
                return_value={"phase": "forward_partial", "config": existing},
            ),
            patch("ecosystem.runner.plan") as plan,
            patch("ecosystem.runner.start", return_value={"status": "start_requested"}),
            patch("ecosystem.ui_service.ensure", return_value={"running": True}),
        ):
            code, _ = self.invoke(["start", "--home", "/isolated/paper"])
        self.assertEqual(code, 0)
        for key, value in existing.items():
            self.assertEqual(plan.call_args.kwargs[key], value)

    def invoke(self, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(argv)
        return code, json.loads(output.getvalue())["data"]

    def test_default_home_and_parser_use_new_paper_scope(self):
        with patch("ecosystem.cli.Path.home", return_value=Path("/isolated")):
            expected = Path("/isolated/.local/share/solmargintrader/ecosystem-paper-v2")
            self.assertEqual(cli.default_home(), expected)
            self.assertEqual(cli.build_parser().parse_args(["status"]).home, expected)

    def test_status_observes_ui_health_in_same_explicit_home_without_start(self):
        home = Path("/isolated/paper")
        interface = {"running": True, "url": "http://127.0.0.1:12345", "pid": 123}
        with (
            patch(
                "ecosystem.runner.status", return_value={"phase": "stopped"}
            ) as pipeline,
            patch("ecosystem.ui_service.status", return_value=interface) as observed,
            patch("ecosystem.ui_service.ensure") as ensure,
            patch("ecosystem.runner.start") as start,
        ):
            code, data = self.invoke(["status", "--home", str(home)])
        self.assertEqual(code, 0)
        self.assertEqual(data["home"], str(home))
        self.assertEqual(data["control_server"], interface)
        self.assertEqual(data["ui_url"], interface["url"])
        pipeline.assert_called_once_with(home)
        observed.assert_called_once_with(home, None)
        ensure.assert_not_called()
        start.assert_not_called()

    def test_status_preserves_recorded_url_without_presenting_it_as_running(self):
        with (
            patch(
                "ecosystem.runner.status",
                return_value={"phase": "stopped", "ui_url": "http://127.0.0.1:9999"},
            ),
            patch("ecosystem.ui_service.status", return_value={"running": False}),
        ):
            code, data = self.invoke(["status", "--home", "/isolated/paper"])
        self.assertEqual(code, 0)
        self.assertIsNone(data["ui_url"])
        self.assertEqual(data["recorded_ui_url"], "http://127.0.0.1:9999")

    def test_already_running_start_ensures_ui_in_same_default_home(self):
        home = Path("/isolated/.local/share/solmargintrader/ecosystem-paper-v2")
        with (
            patch("ecosystem.cli.Path.home", return_value=Path("/isolated")),
            patch("ecosystem.runner.running", return_value=True) as running,
            patch(
                "ecosystem.ui_service.ensure", return_value={"running": True}
            ) as ensure,
            patch("ecosystem.runner.plan") as plan,
        ):
            code, data = self.invoke(["start"])
        self.assertEqual(code, 0)
        self.assertEqual(data["home"], str(home))
        running.assert_called_once_with(home)
        ensure.assert_called_once_with(home, None)
        plan.assert_not_called()

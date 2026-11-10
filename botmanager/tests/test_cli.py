from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from botmanager.registry import CommandContext, dispatch


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "manager"
        self.env = dict(
            os.environ,
            SOLBOT_HOME=str(self.home),
            SOLBOT_API_KEY="credential-canary-98",
        )

    def cli(self, *args, expected=0):
        run = subprocess.run(
            [sys.executable, "-m", "botmanager", *args],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(run.returncode, expected, (run.stdout, run.stderr))
        self.assertNotIn("credential-canary-98", run.stdout + run.stderr)
        return json.loads(run.stdout)

    def test_empty_reads_and_help_leave_no_home(self):
        self.assertEqual(self.cli("list")["data"]["bots"], [])
        self.assertEqual(self.cli("status")["data"]["initialized"], False)
        self.assertTrue(self.cli("help")["ok"])
        self.assertFalse(self.home.exists())

    def test_no_arguments_shows_next_steps_without_creating_state(self):
        run = subprocess.run(
            [sys.executable, "-m", "botmanager"],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
        self.assertIn("usage: solbot", run.stdout)
        self.assertIn("solbot create grid --name my-grid", run.stdout)
        self.assertIn("recorded", run.stdout)
        self.assertIn("No edit command", run.stdout)
        self.assertIn("bot-manager-quickstart.md", run.stdout)
        self.assertEqual(run.stderr, "")
        self.assertNotIn("credential-canary-98", run.stdout)
        self.assertFalse(self.home.exists())

    def test_two_instances_survive_fresh_processes_and_runtime_refuses(self):
        first = self.cli("create", "grid", "--name", "low", "--set", "range_pct=8")[
            "data"
        ]
        second = self.cli("create", "grid", "--name", "high", "--set", "range_pct=24")[
            "data"
        ]
        self.assertNotEqual(first["bot_id"], second["bot_id"])
        self.assertEqual(len(self.cli("list")["data"]["bots"]), 2)
        for spec in (first, second):
            identity = spec["bot_id"]
            self.assertEqual(
                self.cli("start", identity, expected=3)["error"]["code"],
                "runtime_not_available",
            )
            self.assertEqual(
                self.cli("stop", identity, expected=3)["error"]["code"],
                "runtime_not_available",
            )
            self.assertEqual(self.cli("config", identity)["data"], spec)
            status = self.cli("status", identity)["data"]
            self.assertEqual(status["observed_state"], "not_running")
            self.assertEqual(status["capabilities"], ["inspect"])
        self.assertEqual(
            self.cli("config", "low")["data"]["config_hash"], first["config_hash"]
        )

    def test_input_errors_do_not_reflect_secret_values(self):
        for args in (
            ("create", "grid", "--name", "x", "--set", "api_key=credential-canary-98"),
            ("create", "grid", "--name", "x", "--set", "range_pct=NaN"),
            ("create", "grid", "--name", "x", "--wat", "credential-canary-98"),
        ):
            self.assertFalse(self.cli(*args, expected=2)["ok"])
        self.assertFalse(self.home.exists())

    def test_dispatch_invalid_command_is_structured(self):
        result = dispatch("no-such-command", {}, CommandContext(home=self.home))
        self.assertFalse(result["ok"])
        self.assertEqual(result["schema_version"], 1)
        self.assertTrue(result["request_id"])
        self.assertEqual(result["error"]["code"], "invalid_input")

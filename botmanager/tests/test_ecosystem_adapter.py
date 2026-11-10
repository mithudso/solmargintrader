from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from botmanager.adapters.ecosystem import discover_ecosystem


class EcosystemAdapterTests(unittest.TestCase):
    def test_absent_configuration_is_explicit_and_inert(self):
        result = discover_ecosystem()
        self.assertEqual(result["reason"], "ecosystem_not_connected")
        self.assertFalse(result["controls_available"])
        self.assertFalse(result["ownership_transfer"])

    def test_missing_configured_home_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root) / "missing"
            result = discover_ecosystem(home)
            self.assertEqual(result["status"], "unavailable")
            self.assertFalse(home.exists())
            self.assertTrue(result["read_only"])


if __name__ == "__main__":
    unittest.main()


class EcosystemEditingCliTests(unittest.TestCase):
    def test_explicit_ecosystem_flag_coexists_with_editing_commands(self):
        import json
        import os
        import subprocess
        import sys

        with tempfile.TemporaryDirectory() as root:
            manager = Path(root) / "manager"
            ecosystem = Path(root) / "missing-ecosystem"
            env = dict(os.environ, SOLBOT_HOME=str(manager))

            def cli(*args):
                run = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "botmanager",
                        "--ecosystem-home",
                        str(ecosystem),
                        *args,
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10,
                )
                self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
                return json.loads(run.stdout)["data"]

            for command in ("status", "list"):
                result = cli(command)
                self.assertEqual(result["ecosystem"]["status"], "unavailable")
                self.assertTrue(result["ecosystem"]["read_only"])
                self.assertFalse(result["ecosystem"]["ownership_transfer"])
            self.assertFalse(manager.exists())
            self.assertFalse(ecosystem.exists())
            cli("create", "grid", "--name", "example")
            edited = cli("edit", "example", "--set", "range_pct=20")
            self.assertEqual(edited["spec"]["config_revision"], 2)
            self.assertEqual(len(cli("history", "example")["versions"]), 2)
            self.assertEqual(
                cli("apply", "example")["receipt"]["reason"],
                "draft_uses_saved_revision",
            )
            self.assertFalse(ecosystem.exists())

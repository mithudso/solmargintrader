from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from ecosystem import installation as setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        for name in setup.PROJECTS:
            directory = self.repo / name
            directory.mkdir()
            (directory / "pyproject.toml").write_text(
                f'[project]\nname="test-{name}"\nversion="0.1.0"\n'
            )
            (directory / "__init__.py").write_text('"""Fixture package."""\n')
        self.venv = self.root / "venv"

    def fake_health(self, *, valid=True):
        prefix = self.venv.resolve()
        result = {
            "schema_version": 1,
            "status": "complete",
            "python_prefix": str(prefix),
            "python_version": [3, 13, 0],
            "backtest_strategies": 34,
            "oracle_strategies": 14,
            "packages": {
                f"test-{name}": {
                    "version": "0.1.0",
                    "module_path": str(prefix / "lib" / name / "__init__.py"),
                }
                for name in setup.PROJECTS
            },
            "mcp": {
                "tools": 8,
                "resources": 3,
                "subscriptions": True,
                "no_data_abstention": True,
                "stdio_closed": valid,
            },
        }
        return result

    def fake_run(self, commands, *, fail_pip=False):
        def run(command, **kwargs):
            commands.append((command, kwargs))
            if command[1:3] == ["-m", "venv"]:
                (self.venv / "bin").mkdir(exist_ok=True)
                (self.venv / "pyvenv.cfg").write_text("home = fixture\n")
                (self.venv / "bin" / "python").write_text("fixture")
                return 0, ""
            return (1, "secret-pip-error") if fail_pip else (0, "")

        return run

    def test_install_is_local_dedicated_and_exact_receipt_reuses_verified_env(self):
        commands = []
        with (
            patch.object(setup, "_run", side_effect=self.fake_run(commands)),
            patch.object(
                setup, "verify_environment", return_value=self.fake_health()
            ) as health,
        ):
            first = setup.install_environment(self.repo, self.venv)
            second = setup.install_environment(self.repo, self.venv)
        self.assertEqual(first["status"], "complete")
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(health.call_count, 2)
        self.assertEqual(len(commands), 2)
        install = commands[1][0]
        self.assertEqual(
            install[:4], [str(self.venv / "bin" / "python"), "-m", "pip", "install"]
        )
        self.assertEqual(
            install[4:], [str(self.repo.resolve() / name) for name in setup.PROJECTS]
        )
        self.assertNotIn("--upgrade", install)
        self.assertTrue((self.venv / setup.RECEIPT_NAME).is_file())

    def test_failed_first_install_resumes_owned_environment_without_recreating_it(self):
        commands = []
        with patch.object(
            setup, "_run", side_effect=self.fake_run(commands, fail_pip=True)
        ):
            first = setup.install_environment(self.repo, self.venv)
        self.assertEqual(first["reason"], "package_install_failed")
        self.assertNotIn("secret-pip-error", json.dumps(first))
        self.assertFalse((self.venv / setup.RECEIPT_NAME).exists())
        self.assertTrue((self.venv / setup.OWNER_NAME).exists())
        commands.clear()
        with (
            patch.object(setup, "_run", side_effect=self.fake_run(commands)),
            patch.object(setup, "verify_environment", return_value=self.fake_health()),
        ):
            second = setup.install_environment(self.repo, self.venv)
        self.assertEqual(second["status"], "complete")
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0][0][1:4], ["-m", "pip", "install"])

    def test_source_change_during_install_never_issues_completed_receipt(self):
        def changing_health(*_):
            (self.repo / "oracle" / "__init__.py").write_text(
                "CHANGED_DURING_INSTALL = True\n"
            )
            return self.fake_health()

        with (
            patch.object(setup, "_run", side_effect=self.fake_run([])),
            patch.object(setup, "verify_environment", side_effect=changing_health),
        ):
            result = setup.install_environment(self.repo, self.venv)
        self.assertEqual(result["reason"], "source_changed_during_install")
        self.assertFalse((self.venv / setup.RECEIPT_NAME).exists())

    def test_source_change_never_reinstalls_completed_environment(self):
        with (
            patch.object(setup, "_run", side_effect=self.fake_run([])),
            patch.object(setup, "verify_environment", return_value=self.fake_health()),
        ):
            self.assertEqual(
                setup.install_environment(self.repo, self.venv)["status"], "complete"
            )
        (self.repo / "oracle" / "__init__.py").write_text("CHANGED = True\n")
        with patch.object(setup, "_run") as run:
            result = setup.install_environment(self.repo, self.venv)
        self.assertEqual(result["reason"], "environment_source_changed_use_new_venv")
        run.assert_not_called()

    def test_foreign_existing_environment_is_preserved(self):
        self.venv.mkdir()
        original = self.venv / "pyvenv.cfg"
        original.write_text("foreign environment")
        with patch.object(setup, "_run") as run:
            result = setup.install_environment(self.repo, self.venv)
        self.assertEqual(result["reason"], "environment_receipt_missing_use_new_venv")
        self.assertEqual(original.read_text(), "foreign environment")
        self.assertEqual(list(self.venv.iterdir()), [original])
        run.assert_not_called()

    def test_invalid_receipt_does_not_crash_or_echo_contents(self):
        self.venv.mkdir()
        (self.venv / setup.RECEIPT_NAME).write_text('["secret"]')
        result = setup.install_environment(self.repo, self.venv)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("secret", json.dumps(result))

    def test_verification_proves_venv_imports_and_mcp_contract(self):
        (self.venv / "bin").mkdir(parents=True)
        python = self.venv / "bin" / "python"
        python.write_text("fixture")
        commands = []

        def run(command, **kwargs):
            commands.append((command, kwargs))
            return 0, json.dumps(self.fake_health())

        with patch.object(setup, "_run", side_effect=run):
            result = setup.verify_environment(python, self.repo)
        self.assertEqual(result["status"], "complete")
        command, options = commands[0]
        self.assertEqual(command[:3], [str(python), "-I", "-c"])
        self.assertNotEqual(options["cwd"], self.repo)
        self.assertEqual(options["timeout"], 60)
        for invalid in (
            self.fake_health(valid=False),
            {**self.fake_health(), "python_prefix": "/usr"},
            {**self.fake_health(), "oracle_strategies": 0},
        ):
            with patch.object(setup, "_run", return_value=(0, json.dumps(invalid))):
                self.assertEqual(
                    setup.verify_environment(python, self.repo)["status"], "failed"
                )

    def test_failed_health_is_sanitized_and_prevents_install_receipt(self):
        with (
            patch.object(setup, "_run", side_effect=self.fake_run([])),
            patch.object(
                setup,
                "verify_environment",
                return_value={
                    "status": "failed",
                    "reason": "environment_health_failed",
                },
            ),
        ):
            result = setup.install_environment(self.repo, self.venv)
        self.assertEqual(result["status"], "failed")
        self.assertFalse((self.venv / setup.RECEIPT_NAME).exists())
        python = self.venv / "bin" / "python"
        with patch.object(setup, "_run", return_value=(1, "private-token")):
            result = setup.verify_environment(python, self.repo)
        self.assertEqual(result["reason"], "environment_health_failed")
        self.assertNotIn("private-token", json.dumps(result))

    def test_source_fingerprint_ignores_build_outputs_but_binds_runtime_and_cards(self):
        before = setup.source_fingerprint(self.repo)
        build = self.repo / "oracle" / "build"
        build.mkdir()
        (build / "scratch.py").write_text("ignored")
        self.assertEqual(setup.source_fingerprint(self.repo), before)
        card = self.repo / "backtester" / "card.md"
        card.write_text("new card")
        self.assertNotEqual(setup.source_fingerprint(self.repo), before)

    def test_source_fingerprint_binds_each_shipped_web_asset_type(self):
        web = self.repo / "ecosystem" / "web"
        web.mkdir()
        for suffix in (".html", ".css", ".js"):
            with self.subTest(suffix=suffix):
                asset = web / f"dashboard{suffix}"
                asset.write_text("original shipped content")
                before = setup.source_fingerprint(self.repo)
                asset.write_text("changed shipped content")
                self.assertNotEqual(setup.source_fingerprint(self.repo), before)

    def test_health_stdout_flood_is_bounded_before_child_finishes(self):
        started = time.monotonic()
        code, output = setup._run(
            [
                sys.executable,
                "-c",
                "import sys,time; sys.stdout.write('x'*500000); sys.stdout.flush(); time.sleep(60)",
            ],
            cwd=self.root,
            timeout=10,
            output=True,
        )
        self.assertEqual(code, 125)
        self.assertEqual(output, "")
        self.assertLess(time.monotonic() - started, 5)

    def test_subprocess_timeout_is_bounded_and_logs_are_not_returned(self):
        started = time.monotonic()
        code, out = setup._run(
            [sys.executable, "-c", "import time; print('private'); time.sleep(60)"],
            cwd=self.root,
            timeout=0.05,
        )
        self.assertEqual(code, 124)
        self.assertEqual(out, "")
        self.assertLess(time.monotonic() - started, 5)


if __name__ == "__main__":
    unittest.main()

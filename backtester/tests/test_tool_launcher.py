"""The canonical launcher provisions only a private marked environment."""

from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backtester import run


class ToolLauncherTests(unittest.TestCase):
    def test_help_and_no_arguments_do_not_provision(self):
        with patch.object(run, "ensure_environment") as ensure, redirect_stdout(io.StringIO()) as output:
            self.assertEqual(run.main([]), 0)
            with self.assertRaises(SystemExit) as result:
                run.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("Example:", output.getvalue())
        ensure.assert_not_called()

    def test_bad_tool_exits_two_without_provisioning(self):
        with patch.object(run, "ensure_environment") as ensure, redirect_stderr(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as result:
                run.main(["not-a-tool"])
        self.assertEqual(result.exception.code, 2)
        self.assertIn("usage:", output.getvalue())
        ensure.assert_not_called()

    def test_setup_failure_is_safe_actionable_exit_three(self):
        with patch.object(run, "ensure_environment", side_effect=run.PrerequisiteError("missing numpy; private repair command")), redirect_stderr(io.StringIO()) as output:
            self.assertEqual(run.main(["fetch", "--help"]), 3)
        self.assertIn("missing numpy", output.getvalue())
        self.assertNotIn("Traceback", output.getvalue())

    def test_only_selected_allowlisted_module_is_dispatched(self):
        python = Path("/private/fixture/.venv/bin/python")
        with patch.object(run, "ensure_environment", return_value=python), patch.object(run.subprocess, "run", return_value=SimpleNamespace(returncode=2)) as execute:
            self.assertEqual(run.main(["fetch", "--invalid-option"]), 2)
        self.assertEqual(execute.call_args.args[0], [str(python), "-m", "backtester.core.fetch", "--invalid-option"])

    def test_stdlib_fallback_installs_only_into_owned_environment_and_reuses_it(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            (project / "pyproject.toml").write_text('[project]\nname="fixture"\n')
            def create(environment):
                python = run._python(environment)
                python.parent.mkdir()
                python.touch()
            with patch.object(run.venv.EnvBuilder, "create", side_effect=create) as build, \
                 patch.object(run.shutil, "which", return_value=None), \
                 patch.object(run, "_missing_modules", return_value=[]), \
                 patch.object(run.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as execute:
                python = run.ensure_environment(project)
                self.assertEqual(run.ensure_environment(project), python)
            build.assert_called_once()
            execute.assert_called_once_with([str(python), "-m", "pip", "install", "-e", str(project)], capture_output=True, text=True, timeout=300, check=False)
            marker = json.loads((python.parent.parent / ".oraclebot-tools.json").read_text())
            self.assertEqual(marker["owner"], run.OWNER)
            self.assertFalse((project / ".tools/bootstrap.lock").exists())

    def test_unowned_environment_and_symlink_are_never_modified(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            environment = project / ".tools/.venv"
            environment.mkdir(parents=True)
            sentinel = environment / "sentinel"
            sentinel.write_bytes(b"preserve")
            with self.assertRaisesRegex(run.PrerequisiteError, "ownership marker"):
                run.ensure_environment(project)
            self.assertEqual(sentinel.read_bytes(), b"preserve")
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            (project / "outside").mkdir()
            (project / ".tools").symlink_to(project / "outside", target_is_directory=True)
            with self.assertRaisesRegex(run.PrerequisiteError, "symlink"):
                run.ensure_environment(project)
            self.assertEqual(list((project / "outside").iterdir()), [])

    def test_missing_declared_modules_names_exact_private_repair(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            (project / "pyproject.toml").write_text('[project]\nname="fixture"\n')
            def create(environment):
                python = run._python(environment)
                python.parent.mkdir()
                python.touch()
            with patch.object(run.venv.EnvBuilder, "create", side_effect=create), patch.object(run.shutil, "which", return_value=None), \
                 patch.object(run, "_missing_modules", return_value=["numpy"]), patch.object(run.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                with self.assertRaises(run.PrerequisiteError) as error:
                    run.ensure_environment(project)
            self.assertIn("missing Python module(s): numpy", str(error.exception))
            self.assertIn(str(run._python(project / ".tools/.venv")), str(error.exception))

    def test_foreign_setup_lock_and_marker_symlink_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp).resolve()
            lock = project / ".tools/bootstrap.lock"
            lock.mkdir(parents=True)
            with self.assertRaisesRegex(run.PrerequisiteError, "owned or interrupted"):
                run.ensure_environment(project)
            self.assertTrue(lock.is_dir())
            lock.rmdir()
            environment = project / ".tools/.venv"
            environment.mkdir()
            outside = project / "outside.json"
            outside.write_bytes(b"preserve outside")
            (environment / ".oraclebot-tools.json").symlink_to(outside)
            with self.assertRaisesRegex(run.PrerequisiteError, "marker must not be a symlink"):
                run.ensure_environment(project)
            self.assertEqual(outside.read_bytes(), b"preserve outside")


if __name__ == "__main__":
    unittest.main()

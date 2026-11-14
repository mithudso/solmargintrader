"""Optional design tools provision only an explicitly owned private environment."""
from __future__ import annotations

import ast
import json
import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backtester import run


class OptionalEnvironmentTests(unittest.TestCase):
    def test_icon_missing_pillow_reexec_uses_its_owned_private_environment(self):
        script = Path(__file__).resolve().parents[2] / "soltui/make_icon.py"
        class Replaced(BaseException):
            pass
        with tempfile.TemporaryDirectory() as directory:
            python = Path(directory) / "private-python"
            with patch.object(run, "ensure_environment", return_value=python) as ensure, \
                    patch.object(os, "execve", side_effect=Replaced) as replace, \
                    patch("shutil.which", return_value="/inert/iconutil"), \
                    patch.dict(sys.modules, {"PIL": None}), \
                    patch.dict(os.environ, {"TOOL_NO_VENV": "0", "ORACLEBOT_ICON_REEXEC": ""}), \
                    patch.object(sys, "argv", [str(script), "--preview"]), \
                    self.assertRaises(Replaced):
                runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(ensure.call_args.args[0], script.parent)
            self.assertEqual(ensure.call_args.kwargs["requirements"], ("Pillow",))
            self.assertEqual(ensure.call_args.kwargs["owner"], "oraclebot-icon-generator/v1")
            self.assertEqual(replace.call_args.args[:2],
                             (str(python), [str(python), str(script), "--preview"]))

    def test_prototype_reexec_uses_its_owned_private_environment_and_validated_args(self):
        script = Path(__file__).resolve().parents[2] / "design/soltui-v2/mockup.py"
        tree = ast.parse(script.read_text())
        nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                 and node.name in ("PrototypeSetupError", "_bootstrap_and_reexec")]
        namespace = {"__file__": str(script), "Path": Path, "sys": sys, "os": os}
        # Only the two audited stdlib bootstrap definitions execute. UI classes
        # and optional imports remain outside this isolated test namespace.
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(script), "exec"), namespace)  # noqa: S102
        class Replaced(BaseException):
            pass
        with tempfile.TemporaryDirectory() as directory:
            python = Path(directory) / "private-python"
            with patch.object(run, "ensure_environment", return_value=python) as ensure, \
                    patch.object(os, "execve", side_effect=Replaced) as replace, \
                    patch.object(sys, "argv", [str(script), "--shots", "example"]), \
                    self.assertRaises(Replaced):
                namespace["_bootstrap_and_reexec"]()
            self.assertEqual(ensure.call_args.args[0], script.parent)
            self.assertEqual(ensure.call_args.kwargs["owner"], "oraclebot-design-prototype/v1")
            self.assertEqual(replace.call_args.args[:2],
                             (str(python), [str(python), str(script), "--shots", "example"]))
            self.assertEqual(replace.call_args.args[2]["ORACLEBOT_PROTOTYPE_REEXEC"], str(script))

    def test_declared_packages_install_only_in_private_environment_and_reuse_it(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            def create(environment):
                python = run._python(environment)
                python.parent.mkdir(parents=True)
                python.write_text("mock private interpreter")
            with patch.object(run.venv.EnvBuilder, "create", side_effect=create), \
                    patch.object(run, "_missing_modules", return_value=[]), \
                    patch.object(run.shutil, "which", return_value=None), \
                    patch.object(run.subprocess, "run", return_value=SimpleNamespace(returncode=0)) as install:
                kwargs = {"requirements": ("textual==8.2.8", "textual-plotext"),
                          "required_modules": ("rich", "textual", "textual_plotext"),
                          "owner": "oraclebot-design-prototype/v1"}
                python = run.ensure_environment(project, **kwargs)
                self.assertEqual(run.ensure_environment(project, **kwargs), python)
                self.assertEqual(install.call_count, 1)
                self.assertEqual(install.call_args.args[0],
                                 [str(python), "-m", "pip", "install", "textual==8.2.8", "textual-plotext"])
                self.assertEqual(install.call_args.kwargs["timeout"], 300)
                marker = json.loads((project / ".tools/.venv/.oraclebot-tools.json").read_text())
                self.assertEqual(marker["owner"], kwargs["owner"])
                self.assertEqual(marker["project"], str(project.resolve()))

    def test_another_tool_cannot_take_over_an_existing_owned_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            environment = project / ".tools/.venv"
            environment.mkdir(parents=True)
            marker = environment / ".oraclebot-tools.json"
            marker.write_text(json.dumps({"owner": "other-tool", "project": str(project)}))
            with self.assertRaisesRegex(run.PrerequisiteError, "another source"), \
                    patch.object(run.venv.EnvBuilder, "create") as create:
                run.ensure_environment(project, requirements=("textual",), owner="prototype")
            create.assert_not_called()
            self.assertEqual(json.loads(marker.read_text())["owner"], "other-tool")

    def test_package_arguments_cannot_be_pip_options(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(run.PrerequisiteError):
                run.ensure_environment(Path(directory), requirements=("--index-url",))
            self.assertFalse((Path(directory) / ".tools").exists())

    def test_package_and_module_collections_cannot_be_scalar_strings(self):
        for kwargs in ({"requirements": "Pillow"}, {"required_modules": "PIL"}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(run.PrerequisiteError):
                    run.ensure_environment(Path(directory), **kwargs)
                self.assertFalse((Path(directory) / ".tools").exists())


if __name__ == "__main__":
    unittest.main()

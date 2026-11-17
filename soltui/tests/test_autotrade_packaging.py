"""The monorepo runtime wheel must own the same auto-session package as its bridge."""

import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Packaging(unittest.TestCase):
    def test_runtime_contains_owner_and_consumers_pin_same_version(self):
        def read(component):
            return tomllib.loads((ROOT / component / "pyproject.toml").read_text())

        runtime = read("soltui")
        self.assertEqual(runtime["project"]["version"], "0.4.4")
        self.assertEqual(runtime["build-system"]["build-backend"], "soltui_build")
        self.assertEqual(runtime["build-system"]["backend-path"], ["."])
        self.assertIn("include soltui_build.py", (ROOT / "soltui/MANIFEST.in").read_text())
        self.assertIn("oracle_leverage", runtime["tool"]["setuptools"]["packages"])
        self.assertEqual(
            runtime["tool"]["setuptools"]["package-dir"]["oracle_leverage"],
            "../oracle_leverage",
        )
        for package in ("botmanager", "ecosystem"):
            self.assertIn(
                "solmargintrader-research-runtime==0.4.4",
                read(package)["project"]["dependencies"],
            )
        for module in (
            "autotrade",
            "autotrade_worker",
            "autotrade_engine",
            "autotrade_feed",
            "autotrade_advice",
            "exit50",
            "quotes",
            "store",
        ):
            self.assertTrue((ROOT / "oracle_leverage" / f"{module}.py").is_file())

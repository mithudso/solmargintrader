"""The `soltui` shell launcher (soltui/bin/soltui).

A fake interpreter stands in for Python, so these tests check the launcher's own
job — find the repo through a symlink, cd there, pick the module, pass arguments
through — without starting Textual.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / "soltui" / "bin" / "soltui"

FAKE_PY = """#!/bin/sh
if [ "$1" = "-c" ]; then exit 0; fi
echo "cwd=$PWD"
echo "args=$*"
"""


@unittest.skipUnless(shutil.which("zsh"), "launcher is a zsh script")
class LauncherTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.fake = self.tmp / "python"
        self.fake.write_text(FAKE_PY)
        self.fake.chmod(0o755)
        self.link = self.tmp / "bin" / "soltui"
        self.link.parent.mkdir()
        self.link.symlink_to(LAUNCHER)

    def run_launcher(self, *args):
        env = dict(os.environ, SOLTUI_PYTHON=str(self.fake))
        return subprocess.run(
            [str(self.link), *args], cwd=self.tmp, env=env,
            capture_output=True, text=True, timeout=30,
        )

    def test_is_executable_and_parses(self):
        self.assertTrue(os.access(LAUNCHER, os.X_OK))
        check = subprocess.run(["zsh", "-n", str(LAUNCHER)], capture_output=True, text=True)
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_default_opens_console_from_repo_root(self):
        out = self.run_launcher()
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn(f"cwd={REPO}", out.stdout)
        self.assertIn("args=-m soltui.tui", out.stdout)

    def test_flags_pass_through_to_console(self):
        out = self.run_launcher("--dark")
        self.assertIn("args=-m soltui.tui --dark", out.stdout)

    def test_first_word_selects_module(self):
        out = self.run_launcher("app")
        self.assertIn("args=-m soltui.app", out.stdout)
        out = self.run_launcher("bgworker", "--asset", "SOL")
        self.assertIn("args=-m soltui.bgworker --asset SOL", out.stdout)

    def test_unknown_module_fails_clearly(self):
        out = self.run_launcher("nosuchmodule")
        self.assertEqual(out.returncode, 2)
        self.assertIn("no module soltui.nosuchmodule", out.stderr)


if __name__ == "__main__":
    unittest.main()

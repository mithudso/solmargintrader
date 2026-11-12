"""Repository hooks run only against disposable Git fixtures with inert gates."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class HookSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.template = self.root / "empty-template"
        self.template.mkdir()
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                        GIT_TEMPLATE_DIR=str(self.template))
        self.git("init", "--template=" + str(self.template), "-q", "-b", "master")
        self.git("config", "core.hooksPath", os.devnull)
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        for rel in ("index/build.py", "index/search.py", "index/INDEX.json", "index/TEXT-INDEX.json", "index/CONCEPT-INDEX.json", "source.txt"):
            target = self.root / rel
            target.parent.mkdir(exist_ok=True, parents=True)
            target.write_text("baseline\n")
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        bindir = self.root / "fake-bin"
        bindir.mkdir()
        python = bindir / "python3"
        python.write_text('#!/bin/sh\nif [ "$1" = index/build.py ]; then\n for name in INDEX TEXT-INDEX CONCEPT-INDEX; do echo generated > "index/$name.json"; done\nfi\nexit 0\n')
        python.chmod(0o700)
        (self.root / ".gitignore").write_text("fake-bin/\nempty-template/\n.gitignore\n")
        self.env["PATH"] = str(bindir) + os.pathsep + self.env["PATH"]

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], env=self.env, text=True, capture_output=True, check=True).stdout

    def hook(self):
        return subprocess.run(["bash", str(REPO / ".githooks/pre-commit")], cwd=self.root, env=self.env, text=True, capture_output=True)

    def test_unrelated_private_and_partial_edits_remain_unstaged(self):
        (self.root / "source.txt").write_text("intended\n")
        self.git("add", "source.txt")
        (self.root / "index/search.py").write_text("unrelated edit\n")
        (self.root / "index/private.txt").write_text("SYNTHETIC-PRIVATE-CANARY")
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("diff", "--cached", "--name-only").splitlines(), ["source.txt"])
        self.assertEqual((self.root / "index/private.txt").read_text(), "SYNTHETIC-PRIVATE-CANARY")

    def test_clean_staged_tree_adds_only_declared_generated_artifacts(self):
        (self.root / "source.txt").write_text("intended\n")
        self.git("add", "source.txt")
        result = self.hook()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git("diff", "--cached", "--name-only").splitlines(), ["index/CONCEPT-INDEX.json", "index/INDEX.json", "index/TEXT-INDEX.json", "source.txt"])

    def test_partially_staged_source_is_refused_without_changing_the_index(self):
        (self.root / "source.txt").write_text("staged\n")
        self.git("add", "source.txt")
        (self.root / "source.txt").write_text("later unstaged\n")
        result = self.hook()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("show", ":source.txt"), "staged\n")

    def landing_fixture(self):
        tools = self.root / "tools"
        tools.mkdir()
        shutil.copyfile(REPO / "tools/land.sh", tools / "land.sh")
        gate = tools / "gate.sh"
        gate.write_text('#!/bin/sh\nif [ -n "${LAND_TEST_ADVANCE_TO:-}" ]; then git -C "$LAND_TEST_ROOT" update-ref refs/heads/candidate "$LAND_TEST_ADVANCE_TO"; fi\nexit 0\n')
        gate.chmod(0o700)
        self.git("add", "tools")
        self.git("commit", "-qm", "fixture gate")
        master = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-qb", "candidate")
        (self.root / "source.txt").write_text("candidate\n")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "candidate")
        candidate = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "master")
        return master, candidate

    def land(self, *flags):
        return subprocess.run(["bash", str(self.root / "tools/land.sh"), "candidate", *flags], cwd=self.root, env=self.env, capture_output=True, text=True)

    def test_land_refuses_flags_that_skip_the_full_gate(self):
        master, _ = self.landing_fixture()
        for flag in ("--quick", "--help"):
            with self.subTest(flag=flag):
                result = self.land(flag)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.git("rev-parse", "HEAD").strip(), master)

    def test_land_refuses_a_branch_that_moves_after_verification(self):
        master, candidate = self.landing_fixture()
        self.git("checkout", "-q", "candidate")
        (self.root / "source.txt").write_text("unverified later commit\n")
        self.git("add", "source.txt")
        self.git("commit", "-qm", "later")
        advanced = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "master")
        self.git("update-ref", "refs/heads/candidate", candidate)
        self.env.update(LAND_TEST_ADVANCE_TO=advanced, LAND_TEST_ROOT=str(self.root))
        result = self.land()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), master)

    def test_hook_installation_reports_chmod_and_git_config_failures(self):
        bindir = self.root / "fake-bin"
        git = bindir / "git"
        chmod = bindir / "chmod"
        for mode in ("chmod", "config"):
            with self.subTest(failure=mode):
                git.write_text('#!/bin/sh\nif [ "$1" = rev-parse ]; then printf "%s\\n" "$INSTALL_TEST_ROOT"; exit 0; fi\nif [ "$INSTALL_TEST_FAILURE" = config ]; then exit 8; fi\necho .githooks\n')
                chmod.write_text('#!/bin/sh\nif [ "$INSTALL_TEST_FAILURE" = chmod ]; then exit 7; fi\nexit 0\n')
                git.chmod(0o700)
                chmod.chmod(0o700)
                env = {**self.env, "INSTALL_TEST_ROOT": str(self.root), "INSTALL_TEST_FAILURE": mode}
                result = subprocess.run(["bash", str(REPO / "tools/install-hooks.sh")], cwd=self.root, env=env, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("hooks installed", result.stdout)


if __name__ == "__main__":
    unittest.main()

"""Disposable application staging and inert launchctl results only."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from soltui.tests import test_service as fixture


class ServiceResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # The private renderer is outside this maintenance contract. Inert
        # render/write seams keep lifecycle tests runnable without installing it.
        supervisor = ModuleType("launchd_supervisor")
        supervisor.ServiceSpec = lambda **values: SimpleNamespace(**values)
        supervisor.atomic_write = lambda path, data: path.write_bytes(data)
        supervisor.render_plist = lambda _: b"replacement-agent"
        supervisor.manage = SimpleNamespace(
            reload_agent=lambda _: False, is_loaded=lambda _: False
        )
        plist = ModuleType("launchd_supervisor.plist")
        plist.plist_dict = lambda spec: vars(spec)
        with patch.dict(
            sys.modules,
            {"launchd_supervisor": supervisor, "launchd_supervisor.plist": plist},
        ):
            self.svc = fixture.load_service()
        self.apps = self.root / "Applications"
        self.apps.mkdir()
        self.bundle = self.apps / "SolTUI.app"
        self.dist = self.root / "dist.app"
        for path, text in ((self.bundle, "working"), (self.dist, "replacement")):
            exe = path / "Contents/MacOS/SolTUI"
            exe.parent.mkdir(parents=True)
            exe.write_text(text)
            exe.chmod(0o755)
        self.agent = self.root / "agent.plist"
        self.agent.write_bytes(b"original-agent")
        for name, value in {
            "REPO": self.root,
            "APPS_DIR": self.apps,
            "BUNDLE": self.bundle,
            "BUNDLE_EXE": self.bundle / "Contents/MacOS/SolTUI",
            "DIST_BUNDLE": self.dist,
            "AGENT": self.agent,
            "SUPPORT": self.root / "support",
            "FLAG": self.root / "support/enabled",
            "LOG": self.root / "logs/app.log",
        }.items():
            self.enterContext(patch.object(self.svc, name, value))
        self.enterContext(patch.object(self.svc, "runtime_problem", return_value=None))
        self.output = io.StringIO()
        self.enterContext(redirect_stdout(self.output))
        self.enterContext(redirect_stderr(self.output))
        self.enterContext(
            patch.object(
                self.svc, "run", side_effect=AssertionError("no real launchctl")
            )
        )

    def assert_original(self):
        self.assertEqual((self.bundle / "Contents/MacOS/SolTUI").read_text(), "working")
        self.assertEqual(self.agent.read_bytes(), b"original-agent")

    def test_copy_failure_preserves_prior_application_and_agent(self):
        with (
            patch.object(
                self.svc.shutil, "copytree", side_effect=OSError("synthetic disk full")
            ),
            patch.object(self.svc, "reload_agent") as reload,
        ):
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()
        reload.assert_not_called()

    def test_resource_failure_preserves_prior_application(self):
        with (
            patch.object(
                self.svc,
                "dereference_resources",
                side_effect=OSError("synthetic resource copy failure"),
            ),
            patch.object(self.svc, "reload_agent") as reload,
        ):
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()
        reload.assert_not_called()

    def test_activation_failure_restores_prior_bundle_and_agent(self):
        with patch.object(self.svc, "reload_agent", return_value=False):
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()

    def test_success_installs_complete_staged_bundle(self):
        with patch.object(self.svc, "reload_agent", return_value=True):
            self.assertEqual(self.svc.install(), 0)
        self.assertEqual(
            (self.bundle / "Contents/MacOS/SolTUI").read_text(), "replacement"
        )
        self.assertFalse(list(self.apps.glob(".soltui-install-*")))

    def test_denied_termination_is_failure_but_absent_job_is_controlled(self):
        self.svc.SUPPORT.mkdir()
        self.svc.FLAG.touch()
        with patch.object(
            self.svc,
            "run",
            return_value=subprocess.CompletedProcess([], 1, "", "Not privileged"),
        ):
            self.assertNotEqual(self.svc.stop(), 0)
        self.assertIn("Not privileged", self.output.getvalue())
        self.assertFalse(self.svc.FLAG.exists())
        with patch.object(
            self.svc,
            "run",
            return_value=subprocess.CompletedProcess([], 3, "", "No such process"),
        ):
            self.assertEqual(self.svc.stop(), 0)

    def test_absent_process_does_not_hide_a_loaded_job(self):
        with (
            patch.object(self.svc, "run", return_value=subprocess.CompletedProcess([], 3, "", "No such process")),
            patch.object(self.svc, "is_loaded", return_value=True),
        ):
            self.assertNotEqual(self.svc.stop(), 0)

    def test_alias_worktree_is_refused_before_replacing_application(self):
        (self.root / ".git").write_text("gitdir: /inert/fixture")
        with patch.object(self.svc, "reload_agent") as reload:
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()
        reload.assert_not_called()

    def test_uninstall_does_not_remove_application_after_failed_stop(self):
        with patch.object(self.svc, "stop", return_value=1):
            self.assertNotEqual(self.svc.uninstall(), 0)
        self.assert_original()

    def test_staged_runtime_validation_preserves_prior_bundle(self):
        with (
            patch.object(
                self.svc, "runtime_problem", return_value="fixture runtime missing"
            ),
            patch.object(self.svc, "reload_agent") as reload,
        ):
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()
        reload.assert_not_called()

    def test_activation_rename_failure_restores_prior_bundle(self):
        original = Path.rename

        def rename(path, target):
            if path.name == "candidate.app":
                raise OSError("fixture activation rename failed")
            return original(path, target)

        with (
            patch.object(Path, "rename", rename),
            patch.object(self.svc, "reload_agent") as reload,
        ):
            self.assertNotEqual(self.svc.install(), 0)
        self.assert_original()
        reload.assert_not_called()

    def test_interrupted_activation_restores_previous_bundle_and_agent(self):
        with (
            patch.object(self.svc, "reload_agent", side_effect=KeyboardInterrupt),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.svc.install()
        self.assert_original()

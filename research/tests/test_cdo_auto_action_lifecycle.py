"""Accepted auto actions survive a panel close; all bridges are test doubles."""

import threading
import time
import unittest

from research.zec_leverage_panel import LeveragePanel
from research.zec_tui_workers import LatestWorker


class AutoActionLifecycleTests(unittest.TestCase):
    def test_failed_mount_releases_non_daemon_action_worker(self):
        from unittest.mock import MagicMock, PropertyMock, patch

        panel = LeveragePanel(console=object())
        with (
            patch.object(panel, "query_one", return_value=MagicMock()),
            patch.object(panel, "set_class"),
            patch.object(
                LeveragePanel,
                "size",
                new_callable=PropertyMock,
                return_value=MagicMock(height=42),
            ),
            patch.object(panel, "set_interval", return_value=MagicMock()),
            patch.object(
                panel,
                "_apply_feed_visibility",
                side_effect=RuntimeError("fixture mount failure"),
            ),
            self.assertRaisesRegex(RuntimeError, "fixture mount failure"),
        ):
            panel.on_mount()
        self.assertFalse(panel._auto_action_worker.alive)

    def test_orderly_process_exit_waits_for_draining_action(self):
        import subprocess
        import sys
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "completed"
            script = """
import sys, threading
from pathlib import Path
from research.zec_tui_workers import LatestWorker
started = threading.Event()
def loader(request, cancelled):
    started.set()
    threading.Event().wait(0.2)
    Path(sys.argv[1]).write_text(request)
worker = LatestWorker(loader, daemon=False)
worker.submit('accepted')
assert started.wait(1)
worker.close(0.01, drain=True)
"""
            completed = subprocess.run(
                [sys.executable, "-c", script, str(marker)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(marker.read_text(), "accepted")

    def test_close_drains_start_and_stop_once_while_status_is_blocked(self):
        for command in ("autotrade.start_paper", "autotrade.stop"):
            for phase in ("queued", "inflight"):
                with self.subTest(command=command, phase=phase):
                    status_started, status_release = (
                        threading.Event(),
                        threading.Event(),
                    )
                    action_started, action_release = (
                        threading.Event(),
                        threading.Event(),
                    )
                    blocker_started, blocker_release = (
                        threading.Event(),
                        threading.Event(),
                    )
                    calls = []
                    cancellation_states = []

                    def loader(request, cancelled):
                        name, params = request
                        calls.append((name, params.copy()))  # noqa: B023 - joined before next case
                        if name == "autotrade.status":
                            status_started.set()  # noqa: B023
                            status_release.wait(2)  # noqa: B023
                        elif name == "fixture.block":
                            blocker_started.set()  # noqa: B023
                            blocker_release.wait(2)  # noqa: B023
                        else:
                            action_started.set()  # noqa: B023
                            action_release.wait(2)  # noqa: B023
                            cancellation_states.append(cancelled())  # noqa: B023
                        return {"ok": True, "result": {"state": "stopped"}}

                    panel = LeveragePanel(console=object())
                    panel._auto_worker = LatestWorker(loader, name="test-auto-read")
                    panel._auto_action_worker = LatestWorker(
                        loader, name="test-auto-action", daemon=False
                    )
                    try:
                        self.assertTrue(panel._auto_worker._thread.daemon)
                        self.assertFalse(panel._auto_action_worker._thread.daemon)
                        panel._auto_worker.submit(("autotrade.status", {}))
                        self.assertTrue(status_started.wait(1))
                        if phase == "queued":
                            panel._auto_action_worker.submit(("fixture.block", {}))
                            self.assertTrue(blocker_started.wait(1))
                        panel._auto_submit(
                            command,
                            {"config": {"mode": "paper"}}
                            if command.endswith("paper")
                            else {},
                        )
                        request_id = panel._auto_retry[1]
                        panel._auto_submit(command, {})
                        if phase == "inflight":
                            self.assertTrue(action_started.wait(1))
                        before = time.monotonic()
                        panel.stop_owned()
                        self.assertLess(time.monotonic() - before, 1.0)
                        action_release.set()
                        status_release.set()
                        blocker_release.set()
                        self.assertTrue(action_started.wait(1))
                        panel._auto_action_worker._thread.join(1)
                        panel._auto_worker._thread.join(1)
                        self.assertFalse(panel._auto_action_worker.alive)
                        self.assertFalse(panel._auto_worker.alive)
                        actions = [params for name, params in calls if name == command]
                        self.assertEqual(len(actions), 1)
                        self.assertEqual(actions[0]["request_id"], request_id)
                        self.assertEqual(cancellation_states, [False])
                    finally:
                        status_release.set()
                        action_release.set()
                        blocker_release.set()
                        panel._auto_worker.close(1)
                        panel._auto_action_worker.close(1)


class AutoActionDisplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_old_status_cannot_acknowledge_pending_action(self):
        import asyncio
        from unittest.mock import patch

        from research.tests.test_zec_leverage_panel import (
            ConsoleFixture,
            PanelHost,
            static_text,
        )

        status_started, status_release = threading.Event(), threading.Event()
        action_started, action_release = threading.Event(), threading.Event()
        calls = []

        def call(request, cancelled):
            name, params = request
            calls.append((name, params.copy()))
            if name == "autotrade.status":
                status_started.set()
                status_release.wait(2)
                return {"ok": True, "result": {"state": "old_status", "mode": "paper"}}
            action_started.set()
            action_release.wait(2)
            return {"ok": True, "result": {"state": "acknowledged", "mode": "paper"}}

        with patch.object(LeveragePanel, "_auto_call", staticmethod(call)):
            panel = LeveragePanel(console=ConsoleFixture())
            try:
                async with PanelHost(panel).run_test(size=(120, 42)) as pilot:
                    self.assertTrue(await asyncio.to_thread(status_started.wait, 1))
                    panel._auto_submit("autotrade.stop", {})
                    self.assertTrue(await asyncio.to_thread(action_started.wait, 1))
                    status_release.set()
                    await pilot.pause(0.25)
                    self.assertIn("pending", static_text(panel, "#auto-status"))
                    self.assertTrue(panel._auto_busy)
                    action_release.set()
                    await pilot.pause(0.25)
                    self.assertIn("acknowledged", static_text(panel, "#auto-status"))
                    self.assertFalse(panel._auto_busy)
                    self.assertEqual(
                        sum(name == "autotrade.stop" for name, _ in calls), 1
                    )
            finally:
                status_release.set()
                action_release.set()

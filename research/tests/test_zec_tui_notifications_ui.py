"""Actual Header, sound modal, main-thread bell and quiet view persistence."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from textual.widgets import Header, Select, Static

from research.tests.test_zec_tui import Client, FixtureStream
from research.tests.test_zec_tui_alerts import START
from research.tests.test_zec_tui_model import original
from research.tests.test_zec_tui_notifications import ENABLED, raw_context
from research.zec_tui import OracleWinnersApp, SoundsDialog
from research.zec_tui_model import WorkingSet
from research.zec_tui_source import DataSession


class Player:
    def __init__(self):
        self.calls = 0
        self.closed = False
        self.result = None

    def play(self):
        self.calls += 1
        return True

    def poll(self):
        result, self.result = self.result, None
        return result

    def close(self):
        self.closed = True


class HeaderAndSounds(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "view.json"
        self.now = [START + 100.0]
        self.uu = False
        self.clock = lambda: self.now[0]
        self.stream = FixtureStream(self.clock)
        self.player = Player()
        self.state = WorkingSet([original(i, f"test-{i}") for i in ("1m", "1h")])

    def app(self):
        return OracleWinnersApp(
            self.state,
            settings_path=self.path,
            data_loader=DataSession(Client(), clock=self.clock),
            quote_loader=lambda r, c: {"quote": None, "error": "fixture"},
            signal_loader=lambda request, cancelled: {"assets": {}},
            stream=self.stream,
            alert_loader=lambda r, c: raw_context(self.now[0], uu=self.uu),
            sound_player=self.player,
            clock=self.clock,
        )

    async def wait_for(self, pilot, predicate):
        deadline = time.monotonic() + 5
        while not predicate():
            self.assertLess(time.monotonic(), deadline)
            await pilot.pause(0.03)
        await pilot.pause(0.03)

    async def ready(self, app, pilot):
        await self.wait_for(
            pilot,
            lambda: app.current_alert and app.current_alert["closed_up_count"] == 1,
        )

    async def test_actual_top_header_preserves_stage_and_detection_at_narrow_width(
        self,
    ):
        app = self.app()
        async with app.run_test(size=(90, 40)) as pilot:
            await self.ready(app, pilot)
            header = app.query_one("#oracle-header", Header)
            title = header.query_one("HeaderTitle", Static)
            self.assertEqual(header.region.y, 0)
            self.assertIn("1 closed UP confirmed → bar 2", title.render_line(0).text)
            self.assertIn("WATCHING", title.render_line(0).text)
            self.now[0] = START + 303
            self.stream.update(99)
            app.request_alerts(force=True)
            await self.wait_for(pilot, lambda: app.current_alert["reversal_detected"])
            self.assertEqual(app.title, app.current_alert["text"].splitlines()[0])
            self.assertIn("REVERSAL DETECTED", title.render_line(0).text)
            self.assertIn("bar 2", title.render_line(0).text)
            self.assertIn("TRUE open", str(header.tooltip))
            self.stream.connected = False
            app.paint()
            await pilot.pause(0.05)
            self.assertIn("DATA UNAVAILABLE", title.render_line(0).text)
            self.assertIn("bar 2", title.render_line(0).text)
            self.assertEqual(app.sub_title, "")
            self.assertEqual(self.player.calls, 0)
        self.assertTrue(self.player.closed)

    async def test_modal_preview_cancel_apply_and_explicit_save_at_narrow_width(self):
        app = self.app()
        async with app.run_test(size=(90, 40)) as pilot:
            await self.ready(app, pilot)
            self.assertLessEqual(app.query_one("#show-sounds").region.right, 90)
            await pilot.click("#show-sounds")
            self.assertIsInstance(app.screen, SoundsDialog)
            await pilot.click("#sound-reversal")
            await pilot.press("escape")
            self.assertFalse(self.state.sounds["reversal"])
            await pilot.press("a")
            await pilot.click("#sound-reversal")
            await pilot.click("#sound-two-up")
            await pilot.click("#sound-backend")
            await pilot.press("down", "enter")
            self.assertEqual(
                app.screen.query_one("#sound-backend", Select).value, "macos"
            )
            self.assertLessEqual(
                app.screen.query_one("#test-sound").region.bottom,
                app.screen.query_one("#sounds-dialog").content_region.bottom,
            )
            seen_before = set(app.notification_events.seen)
            await pilot.click("#test-sound")
            self.assertEqual(self.player.calls, 1)
            self.assertEqual(app.notification_events.seen, seen_before)
            self.assertFalse(self.state.sounds["reversal"])
            self.assertFalse(self.path.exists())
            await pilot.click("#apply-sounds")
            self.assertEqual(self.state.sounds, {**ENABLED, "backend": "macos"})
            self.assertFalse(self.path.exists())
            await pilot.click("#save-view")
            restored = WorkingSet(list(self.state.originals.values()))
            restored.load(self.path)
            self.assertEqual(restored.sounds, self.state.sounds)

    async def test_real_bell_path_is_main_thread_once_and_coalesces_simultaneous_events(
        self,
    ):
        self.state.sounds = dict(ENABLED)
        app = self.app()
        bell_threads = []
        app.bell = Mock(side_effect=lambda: bell_threads.append(threading.get_ident()))
        async with app.run_test(size=(168, 60)) as pilot:
            await self.ready(app, pilot)
            self.assertEqual(app.bell.call_count, 0)
            self.now[0] = START + 903
            self.uu = True
            self.stream.update(99)
            app.request_alerts(force=True)
            await self.wait_for(
                pilot,
                lambda: (
                    app.current_alert["current_start"] == START + 600
                    and app.current_alert["reversal_detected"]
                ),
            )
            self.assertEqual(app.bell.call_count, 1)
            for price, connected in ((101, True), (99, False), (99, True)):
                self.stream.update(price)
                self.stream.connected = connected
                app.paint()
            app.action_refresh_now()
            app.query_one("#timeframe", Select).value = "1h"
            await pilot.pause(0.3)
            self.assertEqual(app.bell.call_count, 1)
            self.assertEqual(bell_threads, [threading.get_ident()])

    async def test_failed_sound_is_visible_once_and_exit_makes_callbacks_inert(self):
        app = self.app()
        async with app.run_test(size=(90, 40)) as pilot:
            await self.ready(app, pilot)
            await pilot.click("#show-sounds")
            self.player.result = {
                "error": "Sound playback failed (exit 7)",
                "stderr": b"private child detail",
            }
            app.paint()
            status = str(app.screen.query_one("#sound-status", Static).content)
            self.assertIn("exit 7", status)
            self.assertIn("Test sound", status)
            self.assertNotIn("private child detail", status)
            for _ in range(3):
                app.paint()
            self.assertEqual(self.player.calls, 0)
            app.bell = Mock(side_effect=OSError("private driver detail"))
            app.play_sound("bell", preview=True)
            status = str(app.screen.query_one("#sound-status", Static).content)
            self.assertIn("Terminal bell unavailable", status)
            self.assertNotIn("private driver detail", status)
            app.paint()
            self.assertEqual(app.bell.call_count, 1)
            await pilot.press("escape")
            app.exit()
            app.play_sound("macos", preview=True)
            app.sounds_changed(ENABLED)
            app.paint()
        self.assertTrue(self.player.closed)
        self.assertEqual(self.player.calls, 0)


if __name__ == "__main__":
    unittest.main()

"""Real Textual keyboard/mouse, background lifecycle and layout regressions."""

from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from textual.widgets import DataTable, Input, Select, Sparkline, Static, TextArea

from research.tests.test_zec_tui_model import original
from research.zec_tui import ConfigEditor, OracleWinnersApp, StrategyPicker
from research.zec_tui_model import WorkingSet
from research.zec_tui_source import DataSession


class Client:
    def fetch(self, step, start, end):
        return {
            t: {
                "ts": t,
                "open": 100,
                "high": 102,
                "low": 99,
                "close": 100.5 + (t // step % 10) / 100,
                "volume": 10,
            }
            for t in range(start, end, step)
        }


class Interface(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = [100_005.0]
        self.settings = Path(self.directory.name) / "view.json"
        self.state = WorkingSet(
            [
                original(candidate="alpha"),
                original(candidate="beta"),
                original("5m", "five-minute"),
            ]
        )

    def app(self, loader=None):
        return OracleWinnersApp(
            self.state,
            settings_path=self.settings,
            data_loader=loader or DataSession(Client(), clock=lambda: self.now[0]),
            quote_loader=lambda r, c: {
                "quote": {"price": 100.5, "observed_at": self.now[0] - 1},
                "error": None,
            },
            clock=lambda: self.now[0],
        )

    async def ready(self, app, pilot):
        deadline = time.monotonic() + 5
        while app.current_frame is None:
            self.assertLess(time.monotonic(), deadline)
            await pilot.pause(0.04)
        await pilot.pause(0.05)

    async def test_initial_view_has_shape_numeric_right_panel_and_focused_rows(self):
        app = self.app()
        async with app.run_test(size=(140, 44)) as pilot:
            await self.ready(app, pilot)
            self.assertEqual(app.query_one("#watchlist", DataTable).row_count, 2)
            indicators = app.query_one("#indicators", DataTable)
            self.assertGreater(indicators.row_count, 15)
            self.assertIn("Balance of power", str(indicators.get_row_at(0)[0]))
            self.assertIn(
                "observed 48-bar range", str(app.query_one("#shape", Static).content)
            )
            self.assertGreater(
                app.query_one("#right").region.x, app.query_one("#left").region.x
            )
            self.assertTrue(app.query_one("#choose-strategies").region.width > 0)
        self.assertFalse(app.data_worker.alive)
        self.assertFalse(app.quote_worker.alive)

    async def test_time_window_dropdown_changes_rows_and_horizon(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            await pilot.click("#timeframe")
            await pilot.press("down", "enter")
            await pilot.pause(0.15)
            await self.ready(app, pilot)
            self.assertEqual(self.state.interval, "5m")
            self.assertEqual(app.query_one("#watchlist", DataTable).row_count, 1)
            self.assertEqual(app.current_frame["rows"][0]["horizon_seconds"], 300)
            self.assertEqual(self.state.refresh, 10)

    async def test_picker_search_clear_and_keyboard_toggle_preserve_other_windows(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            await pilot.click("#choose-strategies")
            await pilot.pause(0.1)
            self.assertIsInstance(app.screen, StrategyPicker)
            app.screen.query_one("#strategy-search", Input).value = "beta"
            await pilot.pause(0.1)
            self.assertEqual(
                app.screen.query_one("#strategy-options", DataTable).row_count, 1
            )
            await pilot.click("#clear-visible")
            await pilot.click("#apply-selection")
            await pilot.pause(0.1)
            self.assertIn("5m:five-minute:baseline", self.state.selected)
            self.assertIn("1m:alpha:baseline", self.state.selected)
            self.assertNotIn("1m:beta:baseline", self.state.selected)
            await self.ready(app, pilot)
            self.assertEqual(app.query_one("#watchlist", DataTable).row_count, 1)
            await pilot.click("#choose-strategies")
            await pilot.pause(0.1)
            options = app.screen.query_one("#strategy-options", DataTable)
            options.focus()
            options.move_cursor(row=1)
            await pilot.press("space")
            await pilot.click("#apply-selection")
            self.assertIn("1m:beta:baseline", self.state.selected)

    async def test_editor_validates_and_marks_variant_without_inherited_return(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            identity = app.focused_key
            await pilot.click("#edit-focused")
            await pilot.pause(0.1)
            self.assertIsInstance(app.screen, ConfigEditor)
            editor = app.screen.query_one("#config-json", TextArea)
            editor.load_text("{invalid")
            await pilot.click("#apply-config")
            self.assertIsInstance(app.screen, ConfigEditor)
            self.assertFalse(self.state.overrides)
            cfg = self.state.editor_config(identity)
            cfg["members"][0]["params"]["period"] = 5
            editor.load_text(json.dumps(cfg))
            await pilot.pause(
                0.3
            )  # Let the previous invalid-click button effect finish.
            await pilot.click("#apply-config")
            await pilot.pause(0.1)
            await self.ready(app, pilot)
            row = self.state.effective(identity)
            self.assertTrue(row["edited"])
            self.assertEqual(row["historical"], {})
            self.assertIn(
                "UNTESTED", str(app.query_one("#focus-detail", Static).content)
            )
            table = app.query_one("#watchlist", DataTable)
            self.assertEqual(table.get_row(identity)[3], "—")
            await pilot.click("#reset-focused")
            self.assertFalse(self.state.overrides)

    async def test_refresh_controls_and_private_save_keep_window_identity(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            await pilot.click("#faster")
            self.assertEqual(self.state.refresh, 9)
            await pilot.click("#slower")
            self.assertEqual(self.state.refresh, 10)
            app.query_one("#refresh-seconds", Input).value = "2"
            await pilot.click("#apply-refresh")
            self.assertEqual(self.state.refresh, 2)
            self.assertEqual(self.state.interval, "1m")
            await pilot.click("#save-view")
            loaded = WorkingSet(list(self.state.originals.values()))
            loaded.load(self.settings)
            self.assertEqual(loaded.refresh, 2)

    async def test_modal_escape_and_navigation_stay_responsive_during_slow_loader(self):
        started = threading.Event()

        def slow(request, cancelled):
            started.set()
            while not cancelled():
                time.sleep(0.01)
            return {}

        app = self.app(slow)
        async with app.run_test(size=(130, 44)) as pilot:
            await pilot.pause(0.1)
            self.assertTrue(started.is_set())
            await pilot.click("#choose-strategies")
            await pilot.press("escape")
            await pilot.click("#slower")
            self.assertEqual(self.state.refresh, 11)
        self.assertFalse(app.data_worker.alive)
        self.assertFalse(app.quote_worker.alive)

    async def test_fast_refresh_does_not_discard_each_completed_slow_result(self):
        source = DataSession(Client(), clock=lambda: self.now[0])

        def slow(request, cancelled):
            time.sleep(0.12)
            return source(request, cancelled)

        self.state.refresh = 0.2
        app = self.app(slow)
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            self.assertIsNotNone(app.current_frame["details"])
            await pilot.pause(0.6)
            self.assertGreater(app.data_worker.generation, 1)
            self.assertIsNotNone(app.current_frame)

    async def test_queued_poll_after_child_detach_before_app_unmount_is_inert(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            app._poll_timer.pause()
            # Textual 8.2.8 _shutdown marks the pump stopped before awaiting
            # child closure, and only then dispatches the app's Unmount event.
            app._running = False
            await app.screen.remove_children()
            self.assertFalse(app._display_stopping)
            self.assertFalse(app.query("#market"))
            app.poll_workers()  # Reproduce an already queued timer callback.
            app.paint()  # Other already queued rendering must also be inert.
            app.request_data(clear=True)
            self.assertTrue(app._display_stopping)
        self.assertFalse(app.data_worker.alive)
        self.assertFalse(app.quote_worker.alive)

    async def test_public_exit_stops_display_before_child_unmount(self):
        app = self.app()
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            market = app.query_one("#market", Static)
            app.exit()
            self.assertTrue(app._display_stopping)
            # is_attached becomes false as soon as App.exit sets its flag,
            # even though the child still has its DOM parent at this point.
            self.assertIs(market.parent, app.screen)
            app.poll_workers()
        self.assertFalse(app.data_worker.alive)
        self.assertFalse(app.quote_worker.alive)

    async def test_worker_failure_clears_all_previous_indicator_and_chart_labels(self):
        source = DataSession(Client(), clock=lambda: self.now[0])
        fail = [False]

        def loader(request, cancelled):
            if fail[0]:
                raise ValueError("private source text")
            return source(request, cancelled)

        app = self.app(loader)
        async with app.run_test(size=(130, 44)) as pilot:
            await self.ready(app, pilot)
            self.assertGreater(app.query_one("#indicators", DataTable).row_count, 0)
            fail[0] = True
            app.action_refresh_now()
            deadline = time.monotonic() + 5
            while not app.current_frame.get("error"):
                self.assertLess(time.monotonic(), deadline)
                await pilot.pause(0.05)
            self.assertEqual(app.query_one("#indicators", DataTable).row_count, 0)
            self.assertIn(
                "unavailable", str(app.query_one("#indicator-clock", Static).content)
            )
            self.assertIn(
                "unavailable", str(app.query_one("#chart-clock", Static).content)
            )
            self.assertFalse(app.query_one("#price-chart", Sparkline).data)

    async def test_indicator_cursor_survives_live_painting(self):
        app = self.app()
        async with app.run_test(size=(130, 40)) as pilot:
            await self.ready(app, pilot)
            table = app.query_one("#indicators", DataTable)
            table.focus()
            table.move_cursor(row=18)
            await pilot.pause(0.6)
            self.assertEqual(table.cursor_row, 18)

    async def test_narrow_terminal_and_chart_window_remain_usable(self):
        app = self.app()
        async with app.run_test(size=(80, 28)) as pilot:
            await self.ready(app, pilot)
            self.assertTrue(app.has_class("compact"))
            self.assertGreater(app.query_one("#choose-strategies").region.width, 0)
            app.query_one("#lookback", Select).value = 48
            await pilot.pause(0.1)
            await self.ready(app, pilot)
            self.assertEqual(len(app.current_frame["details"]["chart"]), 48)
            await pilot.click("#choose-strategies")
            await pilot.press("escape")


if __name__ == "__main__":
    unittest.main()

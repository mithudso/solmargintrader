"""Tests for Signal tab Live page: live graph, real-time streaming price, and forward test predictions."""

from __future__ import annotations

import unittest
from unittest import mock

from soltui import commands, forwardtest, pricefeed
from soltui.config import Settings
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp


class SignalLiveLogicTests(unittest.TestCase):
    def test_top_forward_predictions_returns_ranked_strategies(self) -> None:
        rows = forwardtest.top_forward_predictions("SOL", limit=10)
        self.assertIsInstance(rows, list)
        if rows:
            r = rows[0]
            self.assertIn("label", r)
            self.assertEqual(r["asset"], "SOL")
            self.assertIn("accuracy", r)
            self.assertIn("resolved", r)
            self.assertIn("hits", r)
            self.assertIn("pred_1m", r)
            self.assertIn("pred_5m", r)
            self.assertIn("pred_10m", r)
            self.assertIn("pred_30m", r)
            self.assertIn(r["pred_1m"], {"UP", "DOWN", "FLAT", "-"})
            self.assertIn(r["pred_5m"], {"UP", "DOWN", "FLAT", "-"})
            self.assertIn(r["pred_10m"], {"UP", "DOWN", "FLAT", "-"})
            self.assertIn(r["pred_30m"], {"UP", "DOWN", "FLAT", "-"})

    def test_top_forward_predictions_missing_asset(self) -> None:
        rows = forwardtest.top_forward_predictions("NONEXISTENT_COIN_XYZ")
        self.assertEqual(rows, [])

    def test_command_forwardtest_predictions(self) -> None:
        ctx = commands.Context.from_settings(make_settings(), commands.Runtime())
        env = commands.dispatch("forwardtest.predictions", {"asset": "SOL", "limit": 5}, surface="tui")
        self.assertTrue(env["ok"])
        self.assertEqual(env["command"], "forwardtest.predictions")
        self.assertEqual(env["result"]["asset"], "SOL")
        self.assertIsInstance(env["result"]["rows"], list)


class SignalLiveUITests(unittest.IsolatedAsyncioTestCase):
    async def test_live_pane_renders_chart_stream_and_predictions(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-compound", classic=False)
        async with app.run_test(size=TEST_SIZE) as pilot:
            self.assertTrue(app.query("#signal-live-stream"))
            self.assertTrue(app.query("#signal-live-chart"))
            self.assertTrue(app.query("#signal-live-predictions-table"))
            self.assertTrue(app.query("#signal-live-detail"))

            app._signal_live_tick()
            app._signal_live_refresh_predictions(force=True)
            await pilot.pause(0.1)

            stream_text = text_of(app, "#signal-live-stream")
            self.assertTrue(len(stream_text) > 0)

            tbl = app.query_one("#signal-live-predictions-table")
            self.assertTrue(tbl.is_mounted)

    async def test_goto_signal_live_button(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-signals", classic=True)
        async with app.run_test(size=TEST_SIZE) as pilot:
            btn = app.query_one("#btn-goto-signal-live")
            self.assertTrue(btn.is_mounted)
            btn.press()
            await pilot.pause(0.1)
            from textual.widgets import TabbedContent
            tabs = app.query_one("#main-tabs", TabbedContent)
            self.assertEqual(tabs.active, "tab-compound")
            sections = app.query_one("#compound-sections", TabbedContent)
            self.assertEqual(sections.active, "cmp-live")


if __name__ == "__main__":
    unittest.main()

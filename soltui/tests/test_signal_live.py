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
            self.assertTrue(app.query("#signal-live-chart-yaxis"))
            self.assertTrue(app.query("#signal-live-chart-xaxis"))
            self.assertTrue(app.query("#signal-live-predictions-table"))
            self.assertTrue(app.query("#signal-live-predictions-title"))
            self.assertTrue(app.query("#signal-live-detail"))

            app._signal_live_tick()
            app._signal_live_refresh_predictions(force=True)
            await pilot.pause(0.1)

            stream_text = text_of(app, "#signal-live-stream")
            self.assertTrue(len(stream_text) > 0)

            tbl = app.query_one("#signal-live-predictions-table")
            self.assertTrue(tbl.is_mounted)

    async def test_live_chart_price_numbers_and_timestamps(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-compound", classic=False)
        async with app.run_test(size=TEST_SIZE) as pilot:
            mock_latest = {
                "q": {
                    "SOL-USD": [180.0, 180.5, 180.25, 10.0, 12.0, 1700000000.0]
                }
            }
            mock_status = {
                "live": True,
                "prices": {
                    "SOL-USD": {
                        "bid": 180.0, "ask": 180.5, "last": 180.25, "mid": 180.25,
                        "bid_size": 10.0, "ask_size": 12.0, "spread_bps": 2.5, "quote_age_s": 0.5,
                    }
                },
                "messages": 100,
                "reconnects": 0,
            }
            with mock.patch("soltui.pricefeed.read_latest", return_value=mock_latest), \
                 mock.patch("soltui.pricefeed.status", return_value=mock_status):
                app._signal_live_tick()
                await pilot.pause(0.1)

                yaxis_text = text_of(app, "#signal-live-chart-yaxis")
                self.assertIn("$", yaxis_text)
                self.assertIn("180", yaxis_text)

                xaxis_text = text_of(app, "#signal-live-chart-xaxis")
                self.assertIn("UTC", xaxis_text)

    async def test_strategy_predictions_1m_scheduling(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-compound", classic=False)
        async with app.run_test(size=TEST_SIZE) as pilot:
            app._signal_live_refresh_predictions(force=True)
            await pilot.pause(0.1)

            old_update = app._signal_live_last_pred_update
            self.assertGreater(old_update, 0.0)

            # Fast forward last update to 65 seconds ago
            app._signal_live_last_pred_update = old_update - 65.0
            app._signal_live_last_pred_minute = int(app._signal_live_last_pred_update) // 60

            refreshed = False
            orig_refresh = app._signal_live_refresh_predictions

            def tracking_refresh(force: bool = False):
                nonlocal refreshed
                refreshed = True
                return orig_refresh(force=force)

            app._signal_live_refresh_predictions = tracking_refresh
            app._signal_live_tick()
            self.assertTrue(refreshed)
            self.assertGreater(app._signal_live_last_pred_update, old_update - 65.0)

            title_text = text_of(app, "#signal-live-predictions-title")
            self.assertIn("1m schedule", title_text)

    async def test_goto_signal_live_button(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-signals", classic=True)
        async with app.run_test(size=TEST_SIZE) as pilot:
            btn = app.query_one("#btn-goto-signal-live")
            self.assertTrue(btn.is_mounted)
            btn.press()
            await pilot.pause(0.2)
            from textual.widgets import TabbedContent
            tabs = app.query_one("#main-tabs", TabbedContent)
            self.assertEqual(tabs.active, "tab-compound")
            sections = app.query_one("#compound-sections", TabbedContent)
            self.assertEqual(sections.active, "cmp-live")


if __name__ == "__main__":
    unittest.main()

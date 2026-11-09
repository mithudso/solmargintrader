"""Tests for Signal tab Live page: live graph, real-time streaming price, and forward test predictions."""

from __future__ import annotations

import asyncio
import tempfile
import threading
import unittest
import time
from pathlib import Path
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
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patch = mock.patch("soltui.config.CONFIG_DIR", Path(temporary.name))
        patch.start()
        self.addCleanup(patch.stop)

    async def wait_predictions(self, app: SolTuiApp, pilot) -> None:
        for _ in range(100):
            await pilot.pause(0.01)
            if not app._signal_live_busy:
                return
        self.fail("Prediction read did not finish")

    @staticmethod
    def prediction_rows(direction: str = "UP", label: str = "fixture") -> list[dict]:
        now = time.time()
        return [{"label": label, "asset": "SOL", "hits": 32, "accuracy": 80, "resolved": 40, "settings": [],
                 **{f"pred_{h}m": direction for h in (1, 5, 10, 30)},
                 **{f"acc_{h}m": 80 for h in (1, 5, 10, 30)},
                 **{f"resolved_{h}m": 40 for h in (1, 5, 10, 30)},
                 **{f"issued_{h}m": now - 30 for h in (1, 5, 10, 30)},
                 **{f"expires_{h}m": now + 300 for h in (1, 5, 10, 30)}}]

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

    async def test_strategy_predictions_replace_rows_every_10s_including_empty_reads(self) -> None:
        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        snapshot = {"rows": self.prediction_rows()}
        with mock.patch("soltui.live_score.prediction_snapshot", side_effect=lambda *a, **kw: snapshot) as read, \
             mock.patch.object(app, "set_interval", wraps=app.set_interval) as scheduled:
            async with app.run_test(size=TEST_SIZE) as pilot:
                await self.wait_predictions(app, pilot)
                interval, poll = next(c.args[:2] for c in scheduled.call_args_list
                                      if len(c.args) > 1 and c.args[1] == app._signal_live_poll_predictions)
                self.assertEqual(interval, 10, "prediction polling has its own exact ten-second timer")
                app._signal_live_prediction_timer.pause()
                table = app.query_one("#signal-live-predictions-table")
                self.assertIn("UP", str(table.get_row_at(0)[4]))
                initial_reads = read.call_count
                with mock.patch("soltui.tui.time.time", return_value=app._signal_live_last_pred_update + 9.999):
                    app._signal_live_tick()
                self.assertEqual(read.call_count, initial_reads, "no read before ten seconds")
                for rows in (self.prediction_rows("DOWN"), [], self.prediction_rows("FLAT")):
                    snapshot = {"rows": rows}
                    with mock.patch("soltui.tui.time.time", return_value=app._signal_live_last_pred_update + 10):
                        app._signal_live_tick()
                        self.assertEqual(read.call_count, initial_reads, "chart ticks never drive the periodic read")
                        poll()
                    await self.wait_predictions(app, pilot)
                    initial_reads += 1
                    self.assertEqual(read.call_count, initial_reads)
                    self.assertEqual(table.row_count, len(rows))
                    if rows:
                        self.assertIn(rows[0]["pred_1m"], str(table.get_row_at(0)[4]))
                self.assertGreater(app._signal_live_last_pred_update, 0)
                self.assertIn("10s refresh", text_of(app, "#signal-live-predictions-title"))

    async def test_failed_prediction_read_is_visible_and_retries_after_10s(self) -> None:
        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        with mock.patch("soltui.live_score.prediction_snapshot", return_value={"rows": self.prediction_rows()}) as read:
            async with app.run_test(size=TEST_SIZE) as pilot:
                await self.wait_predictions(app, pilot)
                app._signal_live_prediction_timer.pause()
                last_success = app._signal_live_last_pred_update
                read.side_effect = RuntimeError("database is locked")
                app._signal_live_poll_predictions()
                await self.wait_predictions(app, pilot)
                self.assertEqual(app._signal_live_last_pred_update, last_success)
                self.assertEqual(app.query_one("#signal-live-predictions-table").row_count, 0)
                self.assertIn("Refresh failed; retrying", text_of(app, "#signal-live-predictions-title"))
                self.assertIn("database is locked", text_of(app, "#signal-live-detail"))
                self.assertIn("No qualifying", text_of(app, "#signal-live-predictions-score"))
                attempts = read.call_count
                app._signal_live_tick()
                self.assertEqual(read.call_count, attempts, "failed reads do not retry each chart tick")
                read.side_effect = None
                read.return_value = {"rows": self.prediction_rows("DOWN")}
                app._signal_live_poll_predictions()
                await self.wait_predictions(app, pilot)
                self.assertGreater(app._signal_live_last_pred_update, last_success)
                self.assertIn("DOWN", str(app.query_one("#signal-live-predictions-table").get_row_at(0)[4]))
                self.assertNotIn("failed", text_of(app, "#signal-live-predictions-title"))

    async def test_slow_read_keeps_chart_responsive_and_discards_old_coin_and_floor_results(self) -> None:
        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        started, release = threading.Event(), threading.Event()
        reads = []
        active = 0
        peak_active = 0
        hold = {"next": True, "error": False}
        def read(asset, **policy):
            nonlocal active, peak_active
            reads.append((asset, policy["min_accuracy"]))
            active += 1
            peak_active = max(peak_active, active)
            try:
                if hold["next"]:
                    hold["next"] = False
                    started.set()
                    if not release.wait(3):
                        raise RuntimeError("test did not release prediction read")
                    if hold["error"]:
                        raise RuntimeError("obsolete prediction read failed")
                    return {"rows": self.prediction_rows("UP", "obsolete-success")}
                return {"rows": self.prediction_rows("DOWN", f"{asset}-{policy['min_accuracy']}")}
            finally:
                active -= 1
        with mock.patch("soltui.live_score.prediction_snapshot", return_value={"rows": []}) as snapshot:
            async with app.run_test(size=TEST_SIZE) as pilot:
                await self.wait_predictions(app, pilot)
                app._signal_live_prediction_timer.pause()
                snapshot.side_effect = read
                try:
                    app._signal_live_refresh_predictions(force=True)
                    self.assertTrue(await asyncio.to_thread(started.wait, 1))
                    with mock.patch("soltui.pricefeed.read_latest", return_value={}), \
                         mock.patch("soltui.pricefeed.status", return_value={"live": True, "prices": {
                             "SOL-USD": {"mid": 100, "quote_age_s": 1, "quote_ts": time.time() - 1}}}):
                        app._signal_live_tick()
                        self.assertIn("$100", text_of(app, "#signal-live-stream"))
                    timer_ran = []
                    app.set_timer(0.01, lambda: timer_ran.append(True))
                    for _ in range(3):
                        app._signal_live_poll_predictions()
                    self.assertFalse(app._signal_live_refresh_requested,
                                     "busy periodic polls must not queue a catch-up read")
                    for _ in range(3):
                        app._signal_live_refresh_predictions(force=True)
                    await pilot.pause(0.05)
                    self.assertTrue(timer_ran, "the UI loop must run while SQLite is blocked")
                    self.assertEqual(len(reads), 1, "only one snapshot read can be in flight")
                    app._compound_coin = "ETH"
                    app._signal_live_refresh_predictions(force=True)
                    app.settings.live_vote_min_accuracy = 95
                    app._signal_live_refresh_predictions(force=True)
                    published = []
                    original_render = app._signal_live_render_predictions
                    def render(**kwargs):
                        published.extend(row["label"] for row in app._signal_live_prediction_rows)
                        original_render(**kwargs)
                    with mock.patch.object(app, "_signal_live_render_predictions", side_effect=render):
                        release.set()
                        await self.wait_predictions(app, pilot)
                    self.assertNotIn("obsolete-success", published)
                    self.assertEqual(reads, [("SOL", 60.0), ("ETH", 95)])
                    self.assertEqual(peak_active, 1)
                    self.assertEqual(app._signal_live_prediction_rows[0]["label"], "ETH-95")
                    self.assertIn("No qualifying", text_of(app, "#signal-live-predictions-score"))
                    started.clear()
                    release.clear()
                    hold.update(next=True, error=True)
                    app._signal_live_refresh_predictions(force=True)
                    self.assertTrue(await asyncio.to_thread(started.wait, 1))
                    app.settings.live_vote_min_accuracy = 70
                    app._signal_live_refresh_predictions(force=True)
                    with mock.patch.object(app, "_signal_live_render_predictions", wraps=original_render) as render_call:
                        release.set()
                        await self.wait_predictions(app, pilot)
                        self.assertFalse(any(c.kwargs.get("error") for c in render_call.call_args_list),
                                         "obsolete failures cannot replace the current view")
                    self.assertEqual(reads[-2:], [("ETH", 95), ("ETH", 70)])
                    self.assertEqual(peak_active, 1)
                    self.assertEqual(app._signal_live_prediction_rows[0]["label"], "ETH-70")
                    started.clear()
                    release.clear()
                    hold.update(next=True, error=False)
                    previous_reads = len(reads)
                    app._signal_live_poll_predictions()
                    self.assertTrue(await asyncio.to_thread(started.wait, 1))
                    for _ in range(3):
                        app._signal_live_poll_predictions()
                    self.assertFalse(app._signal_live_refresh_requested)
                    release.set()
                    await self.wait_predictions(app, pilot)
                    self.assertEqual(len(reads), previous_reads + 1, "skipped periods do not produce a catch-up burst")
                finally:
                    release.set()

    async def test_prediction_worker_drains_without_callback_after_unmount(self) -> None:
        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        started, release = threading.Event(), threading.Event()
        def held_read(*a, **kw):
            started.set()
            release.wait(3)
            return {"rows": self.prediction_rows()}
        with mock.patch("soltui.live_score.prediction_snapshot", return_value={"rows": []}) as read:
            async with app.run_test(size=TEST_SIZE) as pilot:
                await self.wait_predictions(app, pilot)
                read.side_effect = held_read
                app._signal_live_refresh_predictions(force=True)
                self.assertTrue(await asyncio.to_thread(started.wait, 1))
                # Let teardown begin before the database operation returns.
                asyncio.get_running_loop().call_later(0.05, release.set)
            self.assertFalse(app._signal_live_alive.is_set())
            self.assertTrue(app._signal_live_drained.is_set())
            self.assertIsNone(app._signal_live_prediction_timer)

    async def test_aggregate_headers_and_observed_tick_scores(self) -> None:
        from textual.widgets import Static

        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        async with app.run_test(size=TEST_SIZE) as pilot:
            app._signal_live_prediction_timer.pause()
            now = time.time()
            def rows(direction):
                return [{"label": "qualified", "accuracy": 80, "resolved": 40,
                         "pred_1m": direction, "acc_1m": 80, "resolved_1m": 40,
                         "issued_1m": now - 30, "expires_1m": now + 300}]
            app._signal_live_last_coin = "SOL"
            app._signal_live_last_pred_update = now
            app._signal_live_prediction_key = ("SOL", 60.0, 20)
            app._signal_live_prediction_rows = rows("UP")
            app._signal_live_price_history = {"SOL": []}
            app._signal_live_score_history = {}
            quote = {"mid": 100, "bid": 99, "ask": 101, "quote_age_s": 2, "quote_ts": now - 2}
            with mock.patch("soltui.pricefeed.read_latest", return_value={}), \
                 mock.patch("soltui.pricefeed.status", side_effect=lambda: {"live": True, "prices": {"SOL-USD": quote}}), \
                 mock.patch("soltui.compound._load_candle_cache", return_value={}):
                app._signal_live_tick()
                await pilot.pause(0.05)
                self.assertIn("Strong Buy", text_of(app, "#signal-live-price-score"))
                self.assertIn("+100.0", text_of(app, "#signal-live-predictions-score"))
                before = app.query_one("#signal-live-score-tape", Static).content.plain
                app._signal_live_prediction_rows = rows("DOWN")
                quote.update(mid=101, quote_ts=now-1, quote_age_s=1)
                app._signal_live_tick()
                await pilot.pause(0.05)
                after = app.query_one("#signal-live-score-tape", Static).content.plain
                self.assertIn("Strong Sell", text_of(app, "#signal-live-price-score"))
                self.assertLess(after.index("+100.0"), before.index("+100.0"))
                self.assertIn("-100.0", after)
                self.assertEqual(app._signal_live_score_history["SOL"][now-2], 100)
                app._signal_live_tick()
                self.assertEqual(len(app._signal_live_score_history["SOL"]), 2, "same source quote is not a new tick")
                app._compound_coin = "ETH"
                app._signal_live_tick()
                self.assertEqual(list(app.query_one("#signal-live-chart").data), [])
                self.assertEqual(text_of(app, "#signal-live-score-tape"), "")
                self.assertIn("ETH-USD", text_of(app, "#signal-live-chart-context"))

    async def test_live_voting_floor_saves_through_registry(self) -> None:
        from textual.widgets import Input
        app = SolTuiApp(settings=make_settings(), start="tab-compound", classic=False)
        async with app.run_test(size=TEST_SIZE):
            app.query_one("#signal-live-vote-min-score", Input).value = "75"
            app.query_one("#signal-live-vote-min-resolved", Input).value = "30"
            with mock.patch("soltui.commands.save_settings", return_value=Path("fixture.json")) as save:
                app._signal_live_save_vote_floor()
            self.assertEqual(save.call_args.args[0].live_vote_min_accuracy, 75)
            self.assertEqual(app.settings.live_vote_min_resolved, 30)
            self.assertIn("Saved", text_of(app, "#signal-live-vote-status"))

    async def test_goto_signal_live_button(self) -> None:
        settings = make_settings()
        app = SolTuiApp(settings=settings, start="tab-signals", classic=True)
        async with app.run_test(size=TEST_SIZE) as pilot:
            btn = app.query_one("#btn-goto-signal-live")
            self.assertTrue(btn.is_mounted)
            btn.press()
            from textual.widgets import TabbedContent
            tabs = app.query_one("#main-tabs", TabbedContent)
            sections = app.query_one("#compound-sections", TabbedContent)
            # Button events are queued; busy CI runners may need more than one frame.
            for _ in range(20):
                await pilot.pause(0.2)
                if tabs.active == "tab-compound" and sections.active == "cmp-live":
                    break
            self.assertEqual(tabs.active, "tab-compound")
            self.assertEqual(sections.active, "cmp-live")


if __name__ == "__main__":
    unittest.main()

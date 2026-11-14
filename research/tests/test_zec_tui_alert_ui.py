"""Real Textual fixed-window alert delivery, freshness, refresh and teardown."""

from __future__ import annotations

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Select, Static

from research.tests.test_zec_tui import Client, FixtureStream
from research.tests.test_zec_tui_alerts import START, AlertClient, bar
from research.tests.test_zec_tui_model import original
from research.zec_tui import OracleWinnersApp, StrategyPicker
from research.zec_tui_model import WorkingSet
from research.zec_tui_source import AlertSession, Cancelled, DataSession


class AlertStream(FixtureStream):
    def __init__(self, clock):
        super().__init__(clock)
        self.price = 99
        self.receipt_age = self.event_age = 0
        self.gap = False

    def snapshot(self, interval):
        current = super().snapshot(interval)
        current["bar"]["open"] = 200  # Explicitly incorrect partial-since-attach open.
        current["observed_at"] -= self.receipt_age
        current["event_at"] -= self.event_age
        current["gap"] = self.gap
        return current


class TenMinuteAlertsUI(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = [START + 303.0]
        self.clock = lambda: self.now[0]
        self.state = WorkingSet(
            [original(i, f"test-{i}") for i in ("1m", "5m", "10m", "1h")]
        )
        self.state.refresh = 300
        self.stream = AlertStream(self.clock)
        self.alert_client = AlertClient()
        self.alert_source = AlertSession(self.alert_client, clock=self.clock)

    def app(self, **overrides):
        options = {
            "settings_path": Path(self.directory.name) / "view.json",
            "data_loader": DataSession(Client(), clock=self.clock),
            "quote_loader": lambda r, c: {
                "quote": {"price": 99, "observed_at": self.now[0]},
                "error": None,
            },
            "stream": self.stream,
            "alert_loader": self.alert_source,
            "clock": self.clock,
        }
        options.update(overrides)
        return OracleWinnersApp(self.state, **options)

    async def wait_for(self, pilot, condition):
        deadline = time.monotonic() + 5
        while not condition():
            self.assertLess(
                time.monotonic(), deadline, "UI did not deliver expected state"
            )
            await pilot.pause(0.03)
        await pilot.pause(0.03)

    def assert_stopped(self, app):
        for worker in (
            app.data_worker,
            app.quote_worker,
            app.indicator_worker,
            app.alert_worker,
        ):
            self.assertFalse(worker.alive)
        self.assertFalse(self.stream.alive)

    async def test_alert_is_fixed_ten_minutes_across_all_chart_windows(self):
        app = self.app()
        async with app.run_test(size=(168, 60)) as pilot:
            await self.wait_for(
                pilot,
                lambda: (
                    app.current_alert
                    and app.current_alert["state"] == "observed_reversal"
                ),
            )
            for interval in ("5m", "10m", "1h", "1m"):
                app.query_one("#timeframe", Select).value = interval
                await self.wait_for(
                    pilot,
                    lambda interval=interval: (
                        app.current_frame and app.current_frame["interval"] == interval
                    ),
                )
                self.assertEqual(app.current_alert["state"], "observed_reversal")
                self.assertEqual(app.current_alert["target_at"], START + 600)
                self.assertEqual(app.current_alert["true_open"], 100)
                self.assertTrue(
                    app.query_one("#bearish-alert", Static).has_class(
                        "bearish-observed"
                    )
                )
            self.assertEqual(
                self.alert_client.calls, [(300, START - 1500, START + 300)]
            )
        self.assert_stopped(app)

    async def test_midpoint_fetch_advances_with_hour_chart_and_max_refresh_300(self):
        self.now[0] = START + 299
        self.state.interval = "1h"
        chart_calls = []
        source = DataSession(Client(), clock=self.clock)

        def charts(request, cancelled):
            chart_calls.append(request)
            return source(request, cancelled)

        app = self.app(data_loader=charts)
        async with app.run_test(size=(168, 60)) as pilot:
            await self.wait_for(
                pilot,
                lambda: (
                    app.current_alert
                    and app.current_alert["state"] == "uu_watch"
                    and app.current_frame
                ),
            )
            fixed_chart_end = app.current_frame["end"]
            self.assertNotIn(START, app.alert_context["rows"])
            self.now[0] = START + 302.9
            app.poll_workers()
            self.assertEqual(len(self.alert_client.calls), 1)
            self.now[0] = START + 303
            app.poll_workers()
            await self.wait_for(
                pilot, lambda: app.current_alert["state"] == "observed_reversal"
            )
            self.assertEqual(
                self.alert_client.calls[-1], (300, START - 1500, START + 300)
            )
            self.assertIn(START, app.alert_context["rows"])
            self.assertEqual(app.current_alert["true_open"], 100)
            self.assertEqual(app.current_frame["end"], fixed_chart_end)
            self.assertEqual(len(chart_calls), 1)
            self.assertEqual(self.state.refresh, 300)
        self.assert_stopped(app)

    async def test_alert_runs_while_main_history_bootstrap_is_slow(self):
        started, cancelled_seen = threading.Event(), threading.Event()

        def slow_chart(request, cancelled):
            started.set()
            while not cancelled():
                time.sleep(0.005)
            cancelled_seen.set()
            raise Cancelled()

        app = self.app(data_loader=slow_chart)
        async with app.run_test(size=(90, 40)) as pilot:
            await self.wait_for(
                pilot,
                lambda: (
                    started.is_set()
                    and app.current_alert
                    and app.current_alert["state"] == "observed_reversal"
                ),
            )
            self.assertIsNone(app.current_frame)
            self.assertIn(
                "REVERSAL OBSERVED",
                str(app.query_one("#bearish-alert", Static).content),
            )
            await pilot.click("#choose-strategies")
            self.assertIsInstance(app.screen, StrategyPicker)
            await pilot.press("escape")
            await pilot.click("#faster")
            self.assertEqual(self.state.refresh, 299)
        self.assertTrue(cancelled_seen.is_set())
        self.assert_stopped(app)

    async def test_three_line_banner_visible_above_workspace_at_narrow_and_wide_sizes(
        self,
    ):
        for size in ((90, 40), (168, 60)):
            with self.subTest(size=size):
                app = self.app()
                async with app.run_test(size=size) as pilot:
                    await self.wait_for(
                        pilot,
                        lambda app=app: (
                            app.current_alert
                            and app.current_alert["state"] == "observed_reversal"
                        ),
                    )
                    banner = app.query_one("#bearish-alert", Static)
                    self.assertEqual(banner.content_region.height, 3)
                    self.assertLess(
                        banner.region.bottom, app.query_one("#workspace").region.y
                    )
                    self.assertGreaterEqual(banner.region.y, 0)
                    self.assertLessEqual(banner.region.bottom, size[1])
                    lines = [
                        banner.render_line(i).crop(0, banner.content_region.width).text
                        for i in range(3)
                    ]
                    self.assertIn("REVERSAL OBSERVED", lines[0])
                    self.assertIn("TRUE open", lines[0])
                    self.assertIn("ends 03:30:00 UTC", lines[1])
                    self.assertIn("NOT calibrated live odds", lines[2])
                self.assert_stopped(app)

    async def test_trade_changes_stale_disconnect_gap_and_rollover_clear_banner_immediately(
        self,
    ):
        app = self.app()
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(
                pilot,
                lambda: (
                    app.current_alert
                    and app.current_alert["state"] == "observed_reversal"
                ),
            )
            initial_calls = len(self.alert_client.calls)
            self.stream.update(101)
            app.paint()
            self.assertEqual(app.current_alert["state"], "uu_watch")
            self.assertFalse(
                app.query_one("#bearish-alert", Static).has_class("bearish-observed")
            )
            for field, value, restored in (
                ("receipt_age", 16, 0),
                ("event_age", 16, 0),
                ("receipt_age", -1, 0),
                ("connected", False, True),
                ("gap", True, False),
            ):
                with self.subTest(field=field, value=value):
                    setattr(self.stream, field, value)
                    app.paint()
                    self.assertEqual(app.current_alert["state"], "unavailable")
                    self.assertIsNone(app.current_alert["direction"])
                    banner = app.query_one("#bearish-alert", Static)
                    self.assertFalse(banner.has_class("bearish-observed"))
                    self.assertFalse(banner.has_class("bearish-watch"))
                    setattr(self.stream, field, restored)
            self.assertEqual(len(self.alert_client.calls), initial_calls)
            self.stream.update(99)
            app.paint()
            self.assertEqual(app.current_alert["state"], "observed_reversal")
            self.now[0] = START + 600
            app.paint()
            self.assertNotEqual(app.current_alert["state"], "observed_reversal")
            self.assertEqual(app.current_alert["target_at"], START + 1200)
            self.assertIsNone(app.current_alert["direction"])
        self.assert_stopped(app)

    async def test_refresh_now_forces_alert_fetch_and_busy_clicks_coalesce(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)
        calls = []
        main_thread = threading.get_ident()
        loader_threads = []

        def slow(request, cancelled):
            calls.append(request.get("force"))
            loader_threads.append(threading.get_ident())
            if len(calls) == 1:
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test release did not arrive")
            return self.alert_source(request, cancelled)

        app = self.app(alert_loader=slow)
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(pilot, entered.is_set)
            await pilot.click("#refresh-now")
            for _ in range(4):
                app.action_refresh_now()
            self.assertEqual(calls, [False])
            self.assertEqual(self.stream.refreshes, 5)
            release.set()
            await self.wait_for(
                pilot,
                lambda: (
                    len(calls) == 2
                    and not app.alert_worker.busy
                    and app.current_alert["state"] == "observed_reversal"
                ),
            )
            self.assertEqual(calls, [False, True])
            self.assertEqual(len(self.alert_client.calls), 2)
            self.assertTrue(
                all(identifier != main_thread for identifier in loader_threads)
            )
        self.assert_stopped(app)

    async def test_refresh_now_keeps_alert_source_failure_backoff(self):
        self.alert_client.error = "coinbase_http_429"
        app = self.app()
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(
                pilot, lambda: app.alert_context and app.alert_context.get("error")
            )
            retry_at = self.alert_source.retry_at
            for _ in range(4):
                await pilot.click("#refresh-now")
            await self.wait_for(pilot, lambda: not app.alert_worker.busy)
            self.assertEqual(len(self.alert_client.calls), 1)
            self.assertEqual(self.alert_source.retry_at, retry_at)
            self.assertEqual(app.current_alert["state"], "unavailable")
            self.now[0] = retry_at
            self.alert_client.error = None
            # A keyboard refresh also bypasses the button's brief pressed-effect
            # debounce after the rapid sequence of real mouse clicks above.
            await pilot.press("r")
            await self.wait_for(
                pilot, lambda: app.current_alert["state"] == "observed_reversal"
            )
            self.assertEqual(len(self.alert_client.calls), 2)
        self.assert_stopped(app)

    async def test_hour_chart_change_cannot_publish_expired_slow_alert_context(self):
        entered, release = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def delayed(request, cancelled):
            result = self.alert_source(request, cancelled)
            if not entered.is_set():
                entered.set()
                if not release.wait(3):
                    raise TimeoutError("test release did not arrive")
            return result

        app = self.app(alert_loader=delayed)
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(pilot, entered.is_set)
            app.query_one("#timeframe", Select).value = "1h"
            self.now[0] = START + 603
            release.set()
            await self.wait_for(
                pilot,
                lambda: app.alert_context and app.alert_context["end"] == START + 600,
            )
            self.assertEqual(app.current_alert["target_at"], START + 1200)
            self.assertNotEqual(app.current_alert["state"], "observed_reversal")
            self.assertEqual(app.current_alert["state"], "uu_watch")
            self.assertEqual(len(self.alert_client.calls), 2)
        self.assert_stopped(app)

    async def test_no_dd_up_alert_or_attention_style_in_bearish_banner(self):
        class DownClient(AlertClient):
            def fetch(self, step, start, end):
                self.calls.append((step, start, end))
                return {t: bar(t, 102, 100) for t in range(start, end, step)}

        app = self.app(alert_loader=AlertSession(DownClient(), clock=self.clock))
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(
                pilot,
                lambda: app.current_alert and app.current_alert["state"] == "none",
            )
            banner = app.query_one("#bearish-alert", Static)
            self.assertIsNone(app.current_alert["direction"])
            self.assertFalse(banner.has_class("bearish-observed"))
            self.assertFalse(banner.has_class("bearish-watch"))
            self.assertIn(
                "Previous full ten-minute candle is not UP", str(banner.content)
            )
        self.assert_stopped(app)

    async def test_busy_alert_cancel_and_repeated_modal_exit_leave_no_worker(self):
        started, cancelled_seen = threading.Event(), threading.Event()

        def slow(request, cancelled):
            started.set()
            while not cancelled():
                time.sleep(0.005)
            cancelled_seen.set()
            raise Cancelled()

        for _ in range(2):
            started.clear()
            cancelled_seen.clear()
            app = self.app(alert_loader=slow)
            async with app.run_test(size=(90, 40)) as pilot:
                await self.wait_for(pilot, started.is_set)
                await pilot.click("#choose-strategies")
                self.assertIsInstance(app.screen, StrategyPicker)
                await pilot.press("escape")
                await pilot.click("#faster")
                app.exit()
                app.poll_workers()  # Already queued timer becomes inert.
                app.paint()
            self.assertTrue(cancelled_seen.is_set())
            self.assert_stopped(app)

    async def test_injected_loaders_never_construct_hidden_real_alert_source(self):
        with patch(
            "research.zec_tui.AlertSession",
            side_effect=AssertionError("hidden network"),
        ):
            app = self.app(alert_loader=None)
            async with app.run_test(size=(90, 40)) as pilot:
                await self.wait_for(pilot, lambda: app.alert_context)
                self.assertEqual(
                    app.alert_context["error"], "alert_source_not_attached"
                )
                self.assertEqual(app.current_alert["state"], "unavailable")
        self.assert_stopped(app)


if __name__ == "__main__":
    unittest.main()

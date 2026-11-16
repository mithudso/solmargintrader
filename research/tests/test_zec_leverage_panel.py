"""Real Textual controls, single-flight actions and owned worker teardown."""

from __future__ import annotations

import asyncio
import copy
import threading
import time
import unittest

from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Input, Select, Static

from research.zec_leverage_panel import LeveragePanel


class ConsoleFixture:
    def __init__(self):
        self.reads = self.previews = self.executes = self.closes = 0
        self.preview_args = self.close_args = None
        self.read_gate = self.action_gate = None
        self.read_error = self.action_error = False
        self.data = {
            "status": "running",
            "updated_at": 1000.0,
            "assets": [
                {
                    "asset": "ZEC",
                    "venues": [
                        {"venue": "jupiter-cli-10x", "status": "unsupported"},
                        {
                            "venue": "jupiter-sdk-1000x",
                            "status": "official service ready; manual arming required",
                        },
                    ],
                },
                {
                    "asset": "BTC",
                    "venues": [{"venue": "jupiter-cli-10x", "status": "preview ready"}],
                },
            ],
            "strategies": [
                {
                    "asset": "ZEC",
                    "interval_minutes": 10,
                    "shape": "rising",
                    "direction": "UP",
                    "evidence": "holdout 20/30",
                },
                {
                    "asset": "BTC",
                    "interval_minutes": 20,
                    "shape": "falling",
                    "direction": "DOWN",
                    "evidence": "holdout 18/30",
                },
            ],
            "performance": {"predictions": 4, "settled": 3, "paper_pnl_usd": -1.2},
            "positions": [
                {
                    "id": "position-1",
                    "asset": "ZEC",
                    "venue": "paper",
                    "side": "short",
                    "status": "open",
                    "pnl_usd": -0.4,
                }
            ],
            "events": [
                {
                    "at": 999,
                    "asset": "ZEC",
                    "status": "paper",
                    "message": "Future-only prediction saved",
                }
            ],
        }

    def snapshot(self):
        self.reads += 1
        if self.read_gate is not None:
            self.read_gate.wait(2)
        if self.read_error:
            raise RuntimeError("private material must never appear")
        return copy.deepcopy(self.data)

    def preview(self, *args):
        self.previews += 1
        self.preview_args = args
        if self.action_gate is not None:
            self.action_gate.wait(2)
        if self.action_error:
            raise RuntimeError("private material must never appear")
        return {
            "status": "ready",
            "preview_id": "preview-1",
            "asset": args[0],
            "venue": args[1],
            "side": args[2],
            "collateral_usd": args[3],
            "message": "Unsigned preview only",
        }

    def execute(self, identity):
        self.executes += 1
        if self.action_gate is not None:
            self.action_gate.wait(2)
        if self.action_error:
            raise RuntimeError("private material must never appear")
        return {
            "status": "blocked",
            "message": "Live configuration disarmed",
            "preview_id": identity,
        }

    def close(self, identity):
        self.closes += 1
        self.close_args = identity
        return {"status": "closed", "message": "Paper close recorded"}


class PanelHost(App):
    def __init__(self, panel):
        super().__init__()
        self.panel = panel
        self.ticks = 0

    def compose(self) -> ComposeResult:
        yield Static("Underlying Oracle remains alive")

    def on_mount(self):
        self.set_interval(0.02, self.tick)
        self.push_screen(self.panel)

    def tick(self):
        self.ticks += 1

    def on_unmount(self):
        self.panel.stop_owned()


def static_text(panel, identity):
    return str(panel.query_one(identity, Static).render())


class Interface(unittest.IsolatedAsyncioTestCase):
    async def test_current_select_labels_fit_on_one_line_at_wide_and_narrow_sizes(self):
        for size in ((168, 60), (90, 40)):
            with self.subTest(size=size):
                panel = self.panel()
                async with PanelHost(panel).run_test(size=size) as pilot:
                    await self.wait_for(
                        pilot, lambda panel=panel: panel.snapshot_data is not None
                    )
                    for identity, value, expected in (
                        ("#leverage-asset", "ZEC", "ZEC"),
                        ("#leverage-asset", "BTC", "BTC"),
                        ("#leverage-side", "short", "Short"),
                        ("#leverage-side", "long", "Long"),
                        ("#leverage-interval", 0, "All bars"),
                    ):
                        control = panel.query_one(identity, Select)
                        control.value = value
                        await pilot.pause(0.05)
                        rendered = control.query_one("#label", Static)
                        self.assertEqual(str(rendered.render()), expected)
                        self.assertGreaterEqual(rendered.region.width, len(expected))
                        self.assertEqual(rendered.region.height, 1)
                        self.assertEqual(rendered.content_size.height, 1)
                        self.assertLessEqual(control.region.right, size[0])
                    for identity in (
                        "#leverage-venue",
                        "#leverage-collateral",
                        "#leverage-preview",
                        "#leverage-submit",
                        "#leverage-close-position",
                        "#leverage-return",
                    ):
                        control = panel.query_one(identity)
                        self.assertGreater(control.region.width, 0)
                        self.assertLessEqual(control.region.right, size[0])
                        self.assertLessEqual(control.region.bottom, size[1])

    async def test_selected_live_quote_source_ages_and_waiting_match_render_literally(
        self,
    ):
        console = ConsoleFixture()
        console.data["events"] = []
        console.data["heartbeat"] = {
            "assets": {
                "BTC": {
                    "status": "observing",
                    "cached_minutes": 1040,
                    "error": None,
                    "quote": {
                        "asset": "BTC",
                        "product": "BTC-USD",
                        "price": 100123.125,
                        "quote_currency": "USD",
                        "venue": "Coinbase Exchange",
                        "event_at": 999.0,
                        "observed_at": 1000.0,
                    },
                },
                "ZEC": {
                    "status": "unavailable",
                    "cached_minutes": 2,
                    "error": "ticker_stale [red]literal[/red]",
                },
            }
        }
        now = [1001.0]
        panel = LeveragePanel(console=console, clock=lambda: now[0])
        async with PanelHost(panel).run_test(size=(90, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            panel.query_one("#leverage-asset", Select).value = "BTC"
            await pilot.pause(0.06)
            text = static_text(panel, "#leverage-live-market")
            self.assertIn("BTC-USD: 100,123.125 USD", text)
            self.assertIn("Coinbase Exchange", text)
            self.assertIn("Exchange quote age: 2s", text)
            self.assertIn("cached completed minutes: 1040", text)
            self.assertIn("Waiting for a new matching setup", text)
            self.assertNotIn("DOWN", text)
            self.assertNotIn("UP", text)
            now[0] = 1017.0
            await self.wait_for(
                pilot,
                lambda: "STALE QUOTE" in static_text(panel, "#leverage-live-market"),
            )
            self.assertIn(
                "18s · STALE QUOTE", static_text(panel, "#leverage-live-market")
            )
            panel.query_one("#leverage-asset", Select).value = "ZEC"
            await pilot.pause(0.06)
            self.assertIn(
                "ticker_stale [red]literal[/red]",
                static_text(panel, "#leverage-live-market"),
            )
            self.assertTrue(
                panel.query_one("#leverage-live-market", Static).region.width > 0
            )
            for identity in (
                "#leverage-preview",
                "#leverage-submit",
                "#leverage-close-position",
                "#leverage-return",
            ):
                self.assertLessEqual(
                    panel.query_one(identity, Button).region.bottom, 40
                )

    async def test_all_bars_default_shows_frozen_rules_before_interval_selection(self):
        console = ConsoleFixture()
        console.data["strategies"].append(
            {
                "asset": "ZEC",
                "interval_minutes": 15,
                "shape": "falling",
                "direction": "DOWN",
                "evidence": "frozen15m",
            }
        )
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertEqual(panel.query_one("#leverage-interval", Select).value, 0)
            table = panel.query_one("#leverage-strategies", DataTable)
            self.assertEqual(table.row_count, 2)
            panel.query_one("#leverage-interval", Select).value = 15
            await pilot.pause(0.05)
            self.assertEqual(table.row_count, 1)
            self.assertIn("frozen15m", str(table.get_row_at(0)))
            panel.query_one("#leverage-asset", Select).value = "BTC"
            panel.query_one("#leverage-interval", Select).value = 0
            await pilot.pause(0.05)
            self.assertEqual(table.row_count, 1)
            self.assertIn("20", str(table.get_row_at(0)))

    async def wait_for(self, pilot, condition):
        deadline = time.monotonic() + 4
        while not condition():
            self.assertLess(time.monotonic(), deadline)
            await pilot.pause(0.02)
        await pilot.pause(0.03)

    def panel(self, console=None, **kwargs):
        return LeveragePanel(
            console=console or ConsoleFixture(), clock=lambda: 1001.0, **kwargs
        )

    async def test_capabilities_strategy_filters_and_paper_metrics(self):
        panel = self.panel()
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertIn(
                "Paper forward: running", static_text(panel, "#leverage-status")
            )
            self.assertIn("unsupported", static_text(panel, "#leverage-capabilities"))
            self.assertIn(
                "official service ready; manual arming required",
                static_text(panel, "#leverage-capabilities"),
            )
            self.assertIn(
                "paper pnl usd: -1.2", static_text(panel, "#leverage-performance")
            )
            table = panel.query_one("#leverage-strategies", DataTable)
            self.assertEqual(table.row_count, 1)
            self.assertIn("rising", str(table.get_row_at(0)))
            panel.query_one("#leverage-asset", Select).value = "BTC"
            panel.query_one("#leverage-interval", Select).value = 20
            await pilot.pause(0.1)
            self.assertEqual(table.row_count, 1)
            self.assertIn("falling", str(table.get_row_at(0)))
            self.assertIn("preview ready", static_text(panel, "#leverage-capabilities"))

    async def test_constructor_and_snapshot_do_not_block_ui(self):
        console = ConsoleFixture()
        console.read_gate = threading.Event()
        thread_ids = []

        def factory(home):
            thread_ids.append(threading.get_ident())
            return console

        panel = LeveragePanel(console_factory=factory)
        app = PanelHost(panel)
        async with app.run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: console.reads == 1)
            await pilot.pause(0.12)
            self.assertGreater(app.ticks, 2)
            self.assertNotEqual(thread_ids[0], threading.get_ident())
            console.read_gate.set()
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)

    async def test_preview_is_unsigned_and_submit_is_explicit_single_flight(self):
        console = ConsoleFixture()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(pilot, lambda: panel.preview_id == "preview-1")
            self.assertEqual(console.executes, 0)
            self.assertEqual(
                console.preview_args, ("ZEC", "jupiter-cli-10x", "short", 10.0)
            )
            console.action_gate = threading.Event()
            panel.query_one("#leverage-submit", Button).press()
            await self.wait_for(pilot, lambda: console.executes == 1)
            self.assertTrue(panel.query_one("#leverage-submit", Button).disabled)
            panel._dispatch("execute", ("preview-1",))
            await pilot.pause(0.08)
            self.assertEqual(console.executes, 1)
            console.action_gate.set()
            await self.wait_for(pilot, lambda: panel._operation is None)
            self.assertIn("disarmed", static_text(panel, "#leverage-result"))
            self.assertIsNone(panel.preview_id)

    async def test_changed_selection_invalidates_preview(self):
        panel = self.panel()
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(pilot, lambda: panel.preview_id is not None)
            panel.query_one("#leverage-collateral", Input).value = "15"
            await pilot.pause(0.08)
            self.assertIsNone(panel.preview_id)
            self.assertTrue(panel.query_one("#leverage-submit", Button).disabled)

    async def test_inflight_preview_cannot_be_submitted_after_programmatic_change(self):
        console = ConsoleFixture()
        console.action_gate = threading.Event()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(pilot, lambda: console.previews == 1)
            panel.query_one("#leverage-asset", Select).value = "BTC"
            await pilot.pause(0.04)
            console.action_gate.set()
            await self.wait_for(pilot, lambda: panel._operation is None)
            self.assertIsNone(panel.preview_id)
            self.assertIn("Selection changed", static_text(panel, "#leverage-result"))

    async def test_return_waits_for_inflight_operation(self):
        console = ConsoleFixture()
        console.action_gate = threading.Event()
        panel = self.panel(console)
        app = PanelHost(panel)
        async with app.run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(pilot, lambda: console.previews == 1)
            await pilot.press("escape")
            self.assertIs(app.screen, panel)
            self.assertIn("still in flight", static_text(panel, "#leverage-result"))
            console.action_gate.set()
            await self.wait_for(pilot, lambda: panel._operation is None)
            await pilot.press("escape")
            await self.wait_for(pilot, lambda: app.screen is not panel)
            self.assertFalse(panel._read_worker.alive)
            self.assertFalse(panel._action_worker.alive)

    async def test_action_failure_does_not_retry_or_leak_exception(self):
        console = ConsoleFixture()
        console.action_error = True
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(
                pilot, lambda: panel._operation is None and console.previews == 1
            )
            message = static_text(panel, "#leverage-result")
            self.assertIn("no retry was sent", message)
            self.assertNotIn("private material", message)
            await pilot.pause(0.2)
            self.assertEqual(console.previews, 1)
            self.assertIsNone(panel.preview_id)

    async def test_malformed_refresh_keeps_previous_data_and_surfaces_failure(self):
        console = ConsoleFixture()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            console.data["positions"] = None
            before = console.reads
            panel.action_refresh()
            await self.wait_for(
                pilot,
                lambda: (
                    console.reads > before
                    and "Status unavailable" in static_text(panel, "#leverage-status")
                ),
            )
            self.assertIsNotNone(panel.snapshot_data)
            self.assertEqual(
                panel.query_one("#leverage-positions", DataTable).row_count, 1
            )

    async def test_close_uses_explicitly_selected_position(self):
        console = ConsoleFixture()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 44)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertIsNone(panel.selected_position)
            table = panel.query_one("#leverage-positions", DataTable)
            table.focus()
            await pilot.press("enter")
            self.assertEqual(panel.selected_position, "position-1")
            await pilot.click("#leverage-close-position")
            await self.wait_for(
                pilot, lambda: console.closes == 1 and panel._operation is None
            )
            self.assertEqual(console.close_args, "position-1")
            self.assertEqual(console.executes, 0)

    async def test_sdk_position_venue_and_prefixed_identity_survive_explicit_close(
        self,
    ):
        console = ConsoleFixture()
        identity = "1000x:11111111111111111111111111111111"
        console.data["positions"].append(
            {
                "id": identity,
                "asset": "ZEC",
                "venue": "jupiter-sdk-1000x",
                "side": "long",
                "status": "open",
                "pnl_usd": 1.25,
            }
        )
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(90, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            explanation = static_text(panel, "#leverage-result")
            self.assertIn("fresh unsigned build", explanation)
            self.assertIn("arming and revalidation", explanation)
            self.assertIn("1000× collateral: JupUSD", explanation)
            table = panel.query_one("#leverage-positions", DataTable)
            self.assertIn("jupiter-sdk-1000x", str(table.get_row(identity)))
            self.assertIn(identity, str(table.get_row(identity)))
            table.focus()
            table.move_cursor(row=1)
            await pilot.press("enter")
            self.assertEqual(panel.selected_position, identity)
            # Venue routing comes from the selected position, even if the new
            # open-order form is still set to the CLI venue.
            self.assertEqual(
                panel.query_one("#leverage-venue", Select).value, "jupiter-cli-10x"
            )
            await pilot.click("#leverage-close-position")
            await self.wait_for(
                pilot, lambda: console.closes == 1 and panel._operation is None
            )
            self.assertEqual(console.close_args, identity)
            self.assertEqual(console.executes, 0)

    async def test_periodic_reads_do_not_starve_slow_snapshot(self):
        console = ConsoleFixture()
        console.read_gate = threading.Event()
        panel = self.panel(console)
        app = PanelHost(panel)
        async with app.run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: console.reads == 1)
            for _ in range(8):
                panel.action_refresh()
            await pilot.pause(0.12)
            self.assertEqual(console.reads, 1)
            self.assertGreater(app.ticks, 2)
            console.read_gate.set()
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)

    async def test_invalid_collateral_never_calls_backend(self):
        console = ConsoleFixture()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            for value in ("0", "-1", "nan", "inf", ""):
                panel.query_one("#leverage-collateral", Input).value = value
                await pilot.click("#leverage-preview")
                self.assertIn(
                    "greater than zero", static_text(panel, "#leverage-result")
                )
            self.assertEqual(console.previews, 0)

    async def test_shutdown_discards_owned_read_and_never_stops_forward_service(self):
        console = ConsoleFixture()
        console.read_gate = threading.Event()
        panel = self.panel(console)
        app = PanelHost(panel)
        async with app.run_test(size=(90, 40)) as pilot:
            await self.wait_for(pilot, lambda: console.reads == 1)
            panel.stop_owned()
            self.assertTrue(panel._read_worker.alive)
            console.read_gate.set()
            deadline = time.monotonic() + 2
            while panel._read_worker.alive:
                self.assertLess(time.monotonic(), deadline)
                await asyncio.sleep(0.01)
            self.assertIsNone(panel._read_worker.poll())
            self.assertFalse(panel._action_worker.alive)
            self.assertIsNone(panel.snapshot_data)
            self.assertFalse(hasattr(console, "stop"))

    async def test_stale_timestamp_is_visible_in_narrow_layout(self):
        console = ConsoleFixture()
        console.data["updated_at"] = 800
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(90, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertIn("STALE", static_text(panel, "#leverage-status"))
            for identity in (
                "#leverage-preview",
                "#leverage-submit",
                "#leverage-close-position",
                "#leverage-return",
            ):
                button = panel.query_one(identity, Button)
                self.assertGreater(button.region.width, 0)
                self.assertLessEqual(button.region.bottom, 40)

    async def test_canonical_app_opens_panel_by_flag_and_returns_to_existing_view(self):
        from research.tests.test_zec_tui import Client
        from research.tests.test_zec_tui_model import original
        from research.zec_tui import OracleWinnersApp
        from research.zec_tui_model import WorkingSet
        from research.zec_tui_source import DataSession

        console = ConsoleFixture()
        app = OracleWinnersApp(
            WorkingSet([original()]),
            data_loader=DataSession(Client(), clock=lambda: 100_005.0),
            quote_loader=lambda request, cancelled: {"quote": None, "error": "fixture"},
            leverage_console=console,
            show_leverage=True,
            clock=lambda: 100_005.0,
        )
        async with app.run_test(size=(150, 52)) as pilot:
            await self.wait_for(
                pilot,
                lambda: (
                    app._leverage_panel is not None
                    and app._leverage_panel.snapshot_data is not None
                ),
            )
            first = app._leverage_panel
            await pilot.press("escape")
            await self.wait_for(pilot, lambda: app.screen is not first)
            self.assertTrue(app.is_running)
            self.assertFalse(app._display_stopping)
            await pilot.press("l")
            await self.wait_for(
                pilot,
                lambda: (
                    app._leverage_panel is not first
                    and app._leverage_panel.snapshot_data is not None
                ),
            )
            second = app._leverage_panel
        self.assertFalse(first._read_worker.alive)
        self.assertFalse(first._action_worker.alive)
        self.assertFalse(second._read_worker.alive)
        self.assertFalse(second._action_worker.alive)
        self.assertFalse(app.data_worker.alive)


if __name__ == "__main__":
    unittest.main()

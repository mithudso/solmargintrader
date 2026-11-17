"""Real Textual controls, single-flight actions and owned worker teardown."""

from __future__ import annotations

import asyncio
import copy
import threading
import time
import unittest
from unittest.mock import patch
from xml.etree import ElementTree

from textual.app import App, ComposeResult
from textual.widgets import Button, DataTable, Input, Select, Static

from research.zec_leverage_panel import (
    LeveragePanel,
    bar_view,
    comparison_text,
    emphasized,
    mtf_tilt_text,
    tilt_text,
)


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
            self.action_gate.wait(10)
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
            self.action_gate.wait(10)
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
    def setUp(self):
        # Never connect to or spawn the owner's real session in UI tests.
        bridge = patch.object(
            LeveragePanel,
            "_auto_call",
            staticmethod(
                lambda request, cancelled: {
                    "ok": True,
                    "result": {"state": "stopped", "mode": "paper"},
                }
            ),
        )
        bridge.start()
        self.addCleanup(bridge.stop)

    async def test_auto_summary_uses_active_policy_not_local_selection(self):
        panel = LeveragePanel(console=ConsoleFixture())
        async with PanelHost(panel).run_test(size=(160, 42)) as pilot:
            await pilot.pause(0.1)
            panel.query_one("#leverage-asset", Select).value = "ZEC"
            panel.query_one("#leverage-venue", Select).value = "jupiter-cli-10x"
            panel._paint_auto(
                {
                    "state": "running",
                    "mode": "paper",
                    "policy": {"asset": "BTC", "venue": "jupiter-sdk-1000x"},
                    "position": {
                        "state": "open",
                        "plan": {
                            "direction": "long",
                            "leverage": 1000,
                            "entry_fill": 100,
                            "target_price": 110,
                            "stop_price": 95,
                            "liquidation_price": 90,
                        },
                    },
                    "net_pnl_usd": 2.5,
                    "learner": {
                        "wins": 1,
                        "losses": 2,
                        "liquidations": 0,
                        "samples": 3,
                        "availability_failures": 4,
                    },
                }
            )
            lines = static_text(panel, "#auto-status").splitlines()
            for item in ("BTC", "1000x", "long", "open", "2.5"):
                self.assertIn(item, lines[0])
            for item in ("100", "110", "95", "90"):
                self.assertIn(item, lines[1])
            for item in ("1", "2", "3", "4"):
                self.assertIn(item, lines[2])
            panel._paint_auto({"state": "stopped", "mode": "paper"})
            self.assertNotIn("ZEC", static_text(panel, "#auto-status").splitlines()[0])

    async def test_auto_paper_product_and_unknown_stop_are_explicit(self):
        from types import SimpleNamespace

        panel = LeveragePanel(console=ConsoleFixture())
        async with PanelHost(panel).run_test(size=(120, 42)) as pilot:
            await pilot.pause(0.2)
            panel.query_one("#leverage-venue", Select).value = "jupiter-sdk-1000x"
            for field, value in (("base", "10"), ("max", "15"), ("loss", "50")):
                panel.query_one(f"#auto-{field}", Input).value = value
            await pilot.pause(0.1)

            def press(identity):
                button = panel.query_one(f"#{identity}", Button)
                panel.button_pressed(SimpleNamespace(button=button, stop=lambda: None))

            with patch.object(panel, "_auto_submit") as submit:
                press("auto-paper")
                command, params = submit.call_args.args
                self.assertEqual(command, "autotrade.start_paper")
                self.assertEqual(params["config"]["venue"], "jupiter-sdk-1000x")
                self.assertFalse(params["config"]["advice_enabled"])
                submit.reset_mock()
                panel._auto_unknown = True
                press("auto-stop")
                submit.assert_not_called()
                press("auto-stop")
                submit.assert_called_once_with(
                    "autotrade.stop", {"acknowledge_unknown": True}
                )

    async def test_both_real_quote_sources_basis_primary_and_staleness_render_at_narrow_size(
        self,
    ):
        console = ConsoleFixture()
        console.data["price_comparison"] = {
            "at": 1000.9,
            "status": "streaming",
            "connected": {"jupiter": True, "coinbase": True},
            "errors": {"jupiter": None, "coinbase": None},
            "feeds": {
                "jupiter": {
                    "ZEC": {
                        "asset": "ZEC",
                        "price": 101.0,
                        "exchange_at": 1000.7,
                        "received_at": 1000.8,
                    }
                },
                "coinbase": {
                    "ZEC": {
                        "asset": "ZEC",
                        "price": 100.0,
                        "exchange_at": 1000.6,
                        "received_at": 1000.9,
                    }
                },
            },
        }
        now = [1001.0]
        panel = LeveragePanel(console=console, clock=lambda: now[0])
        app = PanelHost(panel)
        async with app.run_test(size=(90, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            panel.query_one("#leverage-venue", Select).value = "jupiter-sdk-1000x"
            await pilot.pause(0.05)
            rendered = static_text(panel, "#leverage-price-comparison")
            self.assertIn("primary display: Jupiter oracle", rendered)
            self.assertIn(
                "Jupiter oracle · PRIMARY: 101 USD · ● · exchange 0.30s · received 0.20s",
                rendered,
            )
            self.assertIn(
                "Coinbase synced book midpoint: 100 USD · ● · exchange 0.40s · received 0.10s",
                rendered,
            )
            self.assertIn("+100.000 bps", rendered)
            svg = app.export_screenshot()
            self.assertIn("Jupiter", svg)
            self.assertIn("Coinbase", svg)
            for button in panel.query(Button):
                self.assertTrue(button.styles.text_style.bold)
                self.assertLessEqual(button.region.bottom, 42)
            now[0] = 1001.8
            await self.wait_for(
                pilot,
                lambda: any(
                    getattr(getattr(span.style, "foreground", None), "ansi", None) == 3
                    for span in panel.query_one("#leverage-price-comparison", Static)
                    .render()
                    .spans
                ),
            )
            rendered = static_text(panel, "#leverage-price-comparison")
            self.assertIn(
                "Jupiter oracle · PRIMARY: 101 USD · ● · exchange 1.10s · received 1.00s",
                rendered,
            )
            self.assertIn(
                "Coinbase synced book midpoint: 100 USD · ● · exchange 1.20s · received 0.90s",
                rendered,
            )
            self.assertIn("+100.000 bps", rendered)
            self.assertEqual(console.executes + console.closes, 0)

    def test_published_model_components_report_signed_uplift(self):
        value = mtf_tilt_text(
            {
                "10": {
                    "base_down_rate": 0.5,
                    "components": [
                        {"minutes": 5, "posterior_down": 0.4, "n": 50},
                        {"minutes": 10, "posterior_down": 0.6, "n": 40},
                    ],
                }
            }
        )
        self.assertIn("5m +10.0pp n=50", value)
        self.assertIn("10m -10.0pp n=40", value)
        self.assertIn("15m ?", value)

    def test_unsupported_component_displays_its_actual_shape(self):
        model = {"10": {"status": "ready", "base_down_rate": 0.5, "components": []}}
        value = mtf_tilt_text(model, {"5": {"shape": "cap"}})
        self.assertIn("5m cap unsupported", value)
        self.assertIn("10m ?", value)

    def test_bar_intensity_and_empirical_tilts_have_neutral_missing_states(self):
        small = {"open": 100, "close": 100.01, "baseline_range": 2, "progress": 0.5}
        large = {**small, "close": 102}
        self.assertNotEqual(bar_view(small, True)[1], bar_view(large, True)[1])
        self.assertIn("↑", bar_view(large)[0])
        self.assertIn("↓", bar_view({**large, "close": 98})[0])
        self.assertEqual(bar_view({**large, "close": 100})[1], "#555b60")
        rendered = tilt_text(
            {
                "5": {"uplift_pp": 3.2, "n": 30},
                "10": {"uplift_pp": -2, "n": 21},
                "15": {"uplift_pp": 9, "n": 3},
            },
            True,
        )
        self.assertIn("tentative", rendered)
        self.assertIn("5m ↑ +3.2pp n=30", rendered)
        self.assertIn("10m ↓ -2.0pp n=21", rendered)
        self.assertIn("15m ?", rendered)

    def test_links_are_underlined_and_untrusted_markup_stays_literal(self):
        value = "https://jup.ag/perps/1000x [red]literal[/red] STALE LIVE"
        rendered = emphasized(value)
        self.assertEqual(rendered.plain, value)
        self.assertTrue(any("underline" in str(span.style) for span in rendered.spans))
        self.assertTrue(
            any("bright_green" in str(span.style) for span in rendered.spans)
        )

    def test_basis_requires_heartbeat_readtime_fresh_and_synchronized_exchange_times(
        self,
    ):
        base = {
            "price_comparison": {
                "at": 1000.0,
                "status": "streaming",
                "connected": {"jupiter": True, "coinbase": True},
                "feeds": {
                    "jupiter": {
                        "BTC": {
                            "asset": "BTC",
                            "price": 101.0,
                            "exchange_at": 999.8,
                            "received_at": 999.9,
                            "fresh": True,
                        }
                    },
                    "coinbase": {
                        "BTC": {
                            "asset": "BTC",
                            "price": 100.0,
                            "exchange_at": 999.5,
                            "received_at": 999.9,
                            "fresh": True,
                        }
                    },
                },
            }
        }
        self.assertIn(
            "+100.000 bps",
            comparison_text(base, "BTC", "jupiter-sdk-1000x", 1000.0).plain,
        )
        for condition in ("heartbeat", "fresh", "skew", "backend"):
            data = copy.deepcopy(base)
            state = data["price_comparison"]
            if condition == "heartbeat":
                state["at"] = 997.9
            elif condition == "fresh":
                state["feeds"]["jupiter"]["BTC"]["fresh"] = False
            elif condition == "skew":
                state["feeds"]["coinbase"]["BTC"]["exchange_at"] = 998.0
            else:
                state["pairs"] = {
                    "BTC": {"comparable": False, "timestamp_skew_seconds": 0.3}
                }
            with self.subTest(condition=condition):
                text = comparison_text(data, "BTC", "jupiter-sdk-1000x", 1000.0).plain
                self.assertIn("Basis: —", text)
                self.assertNotIn("+100.000 bps", text)
                self.assertIn("Jupiter oracle · PRIMARY", text)

    async def test_full_public_wallet_and_configured_mismatch_appear_in_actual_render(
        self,
    ):
        public = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        configured = "So11111111111111111111111111111111111111112"
        for size in ((168, 58), (90, 42)):
            with self.subTest(size=size):
                console = ConsoleFixture()
                console.data["wallet"] = {
                    "address": public,
                    "name": "owner",
                    "configured_address": configured,
                    "armed": False,
                    "status": "mismatch",
                    "message": "Public identity only; [red]literal[/red]",
                    "privateKey": "fake-secret-never-display",
                }
                panel = self.panel(console)
                app = PanelHost(panel)
                async with app.run_test(size=size) as pilot:
                    await self.wait_for(
                        pilot, lambda panel=panel: panel.snapshot_data is not None
                    )
                    widget = panel.query_one("#leverage-wallet", Static)
                    value = static_text(panel, "#leverage-wallet")
                    self.assertIn(f"Transaction wallet: {public}", value)
                    self.assertIn(f"Configured wallet mismatch: {configured}", value)
                    self.assertIn("DISARMED", value)
                    self.assertIn("[red]literal[/red]", value)
                    self.assertNotIn("fake-secret", value)
                    self.assertNotIn("…", value)
                    self.assertGreater(widget.region.width, len(public))
                    self.assertGreaterEqual(
                        widget.region.height, widget.content_size.height
                    )
                    self.assertLessEqual(
                        widget.region.bottom,
                        panel.query_one("#leverage-asset", Select).region.y,
                    )
                    svg = app.export_screenshot()
                    self.assertIn(public, svg)
                    self.assertIn(configured, svg)
                    for identity in (
                        "#leverage-preview",
                        "#leverage-submit",
                        "#leverage-close-position",
                        "#leverage-return",
                    ):
                        self.assertLessEqual(
                            panel.query_one(identity).region.bottom, size[1]
                        )

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
            console=console or ConsoleFixture(),
            clock=lambda: 1001.0,
            home="/nonexistent",
            **kwargs,
        )

    async def test_capabilities_strategy_filters_and_paper_metrics(self):
        panel = self.panel()
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertIn(
                "Coinbase ZEC paper running", static_text(panel, "#leverage-status")
            )
            self.assertIn("unsupported", static_text(panel, "#leverage-capabilities"))
            self.assertIn(
                "official service ready; manual arming required",
                static_text(panel, "#leverage-capabilities"),
            )
            self.assertIn("settled 3", static_text(panel, "#leverage-status"))
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

    async def test_simulation_only_preview_does_not_enable_submit(self):
        console = ConsoleFixture()

        def inspect(*args):
            console.previews += 1
            return {
                "status": "inspection",
                "message": "Unsigned simulation passed. Inspection only; Submit is unavailable.",
            }

        console.preview = inspect
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(100, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            await pilot.click("#leverage-preview")
            await self.wait_for(
                pilot, lambda: console.previews == 1 and panel._operation is None
            )
            self.assertIn("Inspection only", static_text(panel, "#leverage-result"))
            self.assertIsNone(panel.preview_id)
            self.assertTrue(panel.query_one("#leverage-submit", Button).disabled)
            self.assertEqual(console.executes, 0)

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

    async def test_forward_results_are_next_to_their_status_and_contexts_show_support(
        self,
    ):
        console = ConsoleFixture()
        console.data["performance"] = {
            "by_asset": {
                "ZEC": {
                    "settled": 2,
                    "open": 1,
                    "correct": 1,
                    "hit_rate": 0.5,
                    "mean_net_bps": -2.0,
                }
            }
        }
        console.data["mtf_forward"] = {
            "status": "observing",
            "performance": {
                "settled": 4,
                "open": 1,
                "pending_unscored": 2,
                "direction_correct": 3,
                "paper_wins": 2,
                "hit_rate": 0.5,
                "verified_liquidations": 1,
                "mean_unlevered_gross_bps": 2.0,
            },
            "assets": {
                "ZEC": {
                    "frames": {"5": {"shape": "up"}},
                    "scores": {
                        "5": {
                            "score_down": 0.7,
                            "components": [{"minutes": 5, "n": 42}],
                        }
                    },
                }
            },
        }
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            status = static_text(panel, "#leverage-status")
            self.assertIn("Coinbase ZEC paper running: settled 2", status)
            self.assertIn("net bps -2.000", status)
            self.assertIn("MTF Jupiter ALL-ASSETS observing: settled 4", status)
            self.assertIn("correct 3 · wins 2", status)
            self.assertIn("gross underlying bps 2.000", status)
            self.assertIn("5m n=42", static_text(panel, "#leverage-performance"))

    async def test_missing_quote_retains_price_and_identical_tables_keep_selection(
        self,
    ):
        console = ConsoleFixture()
        console.data["price_comparison"] = {
            "at": 1000,
            "status": "running",
            "connected": {"jupiter": True, "coinbase": True},
            "feeds": {
                "jupiter": {
                    "ZEC": {
                        "asset": "ZEC",
                        "price": 101,
                        "exchange_at": 1000,
                        "received_at": 1000,
                    }
                },
                "coinbase": {
                    "ZEC": {
                        "asset": "ZEC",
                        "price": 100,
                        "exchange_at": 1000,
                        "received_at": 1000,
                    }
                },
            },
        }
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            table = panel.query_one("#leverage-positions", DataTable)
            table.focus()
            panel.selected_position = "position-1"
            console.data["price_comparison"]["feeds"]["jupiter"] = {}
            before = console.reads
            with patch.object(table, "clear", wraps=table.clear) as clear:
                panel.action_refresh()
                await self.wait_for(
                    pilot,
                    lambda: (
                        console.reads > before
                        and panel.snapshot_data["price_comparison"]["feeds"]["jupiter"]
                        .get("ZEC", {})
                        .get("fresh")
                        is False
                    ),
                )
                self.assertIn(
                    "101 USD", static_text(panel, "#leverage-price-comparison")
                )
                self.assertIn(
                    "+100.000 bps", static_text(panel, "#leverage-price-comparison")
                )
                self.assertEqual(clear.call_count, 0)
                self.assertEqual(panel.selected_position, "position-1")
                self.assertTrue(table.has_focus)

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
                    and "Backend read failed"
                    in str(
                        panel.query_one("#leverage-price-comparison", Static).tooltip
                    )
                ),
            )
            self.assertIsNotNone(panel.snapshot_data)
            self.assertEqual(
                panel.query_one("#leverage-positions", DataTable).row_count, 1
            )

    async def test_paper_row_is_visible_but_never_closes_live_position(self):
        console = ConsoleFixture()
        console.data["exit50_forward"] = {
            "positions": [
                {
                    "id": "position-1",
                    "asset": "ZEC",
                    "side": "short",
                    "status": "close_pending",
                    "roe": 0.52,
                }
            ],
            "assets": {},
            "performance": {},
        }
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            table = panel.query_one("#leverage-positions", DataTable)
            self.assertIn("PAPER", str(table.get_row("paper:position-1")))
            self.assertIn("+52.00% / +50%", str(table.get_row("paper:position-1")))
            self.assertIn("paper", str(table.get_row("venue:position-1")))
            table.focus()
            table.move_cursor(row=table.get_row_index("paper:position-1"))
            await pilot.press("enter")
            self.assertIsNone(panel.selected_position)
            self.assertTrue(
                panel.query_one("#leverage-close-position", Button).disabled
            )
            self.assertEqual(console.closes, 0)
            table.move_cursor(row=table.get_row_index("venue:position-1"))
            await pilot.press("enter")
            self.assertEqual(panel.selected_position, "position-1")
            self.assertFalse(
                panel.query_one("#leverage-close-position", Button).disabled
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
            self.assertIn("jupiter-sdk-1000x", str(table.get_row(f"venue:{identity}")))
            self.assertIn(identity, str(table.get_row(f"venue:{identity}")))
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

    async def test_arm_control_requires_known_state_and_failed_read_disables_it(self):
        console = ConsoleFixture()
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(110, 42)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            arm = panel.query_one("#leverage-arm", Button)
            self.assertTrue(arm.disabled)
            self.assertIn("unknown", str(arm.label))
            console.data["enabled_venues"] = ["jupiter-cli-10x"]
            console.data["armed"] = False
            panel.action_refresh()
            await self.wait_for(pilot, lambda: not arm.disabled)
            self.assertIn("Arm", str(arm.label))
            self.assertNotIn("Disarm", str(arm.label))
            console.read_error = True
            panel.action_refresh()
            await self.wait_for(pilot, lambda: panel._read_failed)
            self.assertTrue(arm.disabled)

    async def test_stale_timestamp_is_visible_in_narrow_layout(self):
        console = ConsoleFixture()
        console.data["updated_at"] = 800
        panel = self.panel(console)
        async with PanelHost(panel).run_test(size=(90, 40)) as pilot:
            await self.wait_for(pilot, lambda: panel.snapshot_data is not None)
            self.assertIn("●", static_text(panel, "#leverage-status"))
            self.assertIn(
                "STALE", str(panel.query_one("#leverage-status", Static).tooltip)
            )
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
            signal_loader=lambda request, cancelled: {"assets": {}},
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

    async def test_actual_app_screen_stack_preserves_full_venue_labels_and_quote_view(
        self,
    ):
        from research.tests.test_zec_tui import Client
        from research.tests.test_zec_tui_model import original
        from research.zec_tui import OracleWinnersApp
        from research.zec_tui_model import WorkingSet
        from research.zec_tui_source import DataSession

        public = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
        for size in ((168, 58), (90, 42)):
            with self.subTest(size=size):
                console = ConsoleFixture()
                console.data["wallet"] = {
                    "address": public,
                    "name": "owner",
                    "armed": False,
                    "status": "ready",
                }
                console.data["price_comparison"] = {
                    "at": 100005.0,
                    "status": "streaming",
                    "connected": {"jupiter": True, "coinbase": True},
                    "errors": {"jupiter": None, "coinbase": None},
                    "feeds": {
                        "jupiter": {
                            "ZEC": {
                                "asset": "ZEC",
                                "price": 101.0,
                                "exchange_at": 100004.9,
                                "received_at": 100004.9,
                                "fresh": True,
                            }
                        },
                        "coinbase": {
                            "ZEC": {
                                "asset": "ZEC",
                                "price": 100.0,
                                "exchange_at": 100004.8,
                                "received_at": 100004.9,
                                "fresh": True,
                            }
                        },
                    },
                }
                now = [100005.0]
                app = OracleWinnersApp(
                    WorkingSet([original()]),
                    data_loader=DataSession(Client(), clock=lambda: 100005.0),
                    quote_loader=lambda request, cancelled: {
                        "quote": None,
                        "error": "fixture",
                    },
                    signal_loader=lambda request, cancelled: {"assets": {}},
                    leverage_console=console,
                    show_leverage=True,
                    clock=lambda now=now: now[0],
                )
                async with app.run_test(size=size) as pilot:
                    await self.wait_for(
                        pilot,
                        lambda app=app: (
                            app._leverage_panel is not None
                            and app._leverage_panel.snapshot_data is not None
                        ),
                    )
                    panel = app._leverage_panel
                    positions = panel.query_one("#leverage-positions", DataTable)
                    calls = panel.query_one("#leverage-strategies", DataTable)
                    left = panel.query_one("#leverage-contents")
                    self.assertGreaterEqual(positions.region.x, left.region.right)
                    self.assertGreaterEqual(calls.region.x, left.region.right)
                    self.assertLessEqual(positions.region.bottom, size[1])
                    self.assertLessEqual(calls.region.bottom, size[1])
                    for identity in (
                        "#leverage-previous-bar",
                        "#leverage-current-bar",
                        "#leverage-arm",
                    ):
                        button = panel.query_one(identity, Button)
                        self.assertGreater(button.region.width, 0)
                        self.assertLessEqual(button.region.bottom, size[1])
                    table = positions
                    table.focus()
                    await pilot.pause(0.05)
                    self.assertTrue(table.has_focus)
                    panel.selected_position = "position-1"
                    original_basis = static_text(panel, "#leverage-price-comparison")
                    self.assertIn("+100.000 bps", original_basis)
                    now[0] = 100006.0
                    panel.paint_live_market()
                    comparison = panel.query_one(
                        "#leverage-price-comparison", Static
                    ).render()
                    self.assertIn("+100.000 bps", comparison.plain)
                    self.assertTrue(
                        any(
                            getattr(
                                getattr(span.style, "foreground", None), "ansi", None
                            )
                            == 3
                            for span in comparison.spans
                        )
                    )
                    self.assertIn(
                        "jupiter: connected, exchange",
                        str(
                            panel.query_one(
                                "#leverage-price-comparison", Static
                            ).tooltip
                        ),
                    )
                    self.assertEqual(panel.selected_position, "position-1")
                    self.assertTrue(table.has_focus)
                    panel.query_one(
                        "#leverage-venue", Select
                    ).value = "jupiter-sdk-1000x"
                    panel.paint_live_market()
                    self.assertNotIn(
                        "+100.000 bps", static_text(panel, "#leverage-price-comparison")
                    )
                    panel.query_one("#leverage-venue", Select).value = "jupiter-cli-10x"
                    now[0] = 100005.0
                    panel.paint_live_market()
                    comparison = panel.query_one(
                        "#leverage-price-comparison", Static
                    ).render()
                    self.assertIn("+100.000 bps", comparison.plain)
                    self.assertFalse(
                        any(
                            getattr(
                                getattr(span.style, "foreground", None), "ansi", None
                            )
                            == 3
                            for span in comparison.spans
                        )
                    )
                    panel.query_one("#leverage-asset", Select).value = "BTC"
                    await pilot.pause(0.05)
                    self.assertNotIn(
                        "+100.000 bps", static_text(panel, "#leverage-price-comparison")
                    )
                    panel.query_one("#leverage-asset", Select).value = "ZEC"
                    await pilot.pause(0.05)
                    for venue, label in (
                        ("jupiter-cli-10x", "Jupiter CLI · 10×"),
                        ("jupiter-sdk-1000x", "Jupiter SDK · 1000×"),
                    ):
                        panel.query_one("#leverage-venue", Select).value = venue
                        await pilot.pause(0.05)
                        control = panel.query_one("#leverage-venue", Select)
                        current = control.query_one("#label", Static)
                        self.assertEqual(str(current.render()), label)
                        self.assertGreaterEqual(current.region.width, len(label))
                        self.assertEqual(current.content_size.height, 1)
                        self.assertEqual(current.region.height, 1)
                        self.assertGreaterEqual(control.region.width, 31)
                    panel.query_one("#leverage-contents").scroll_home(animate=False)
                    await pilot.pause(0.05)
                    svg = app.export_screenshot()
                    rendered_text = "".join(
                        ElementTree.fromstring(svg).itertext()
                    ).replace("\u00a0", " ")
                    self.assertIn(public, rendered_text)
                    self.assertIn("Jupiter SDK", rendered_text)
                    self.assertIn("1000×", rendered_text)
                    self.assertIn("Jupiter oracle", rendered_text)
                    self.assertIn("Coinbase", rendered_text)
                    for button in panel.query(Button):
                        self.assertTrue(button.styles.text_style.bold)
                        self.assertLessEqual(button.region.right, size[0])
                        self.assertLessEqual(button.region.bottom, size[1])
                    wallet = panel.query_one("#leverage-wallet", Static)
                    comparison = panel.query_one("#leverage-price-comparison", Static)
                    self.assertGreater(wallet.region.height, 0)
                    self.assertGreater(comparison.region.height, 0)
                    self.assertLess(
                        comparison.region.y,
                        panel.query_one("#leverage-contents").region.bottom,
                    )
                self.assertFalse(app.data_worker.alive)


if __name__ == "__main__":
    unittest.main()

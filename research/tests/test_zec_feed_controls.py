"""Observable provider visibility, preference isolation and foreground lifecycle."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from textual.widgets import Checkbox, Select, Static

from research.tests.test_zec_leverage_panel import ConsoleFixture, PanelHost
from research.zec_leverage_panel import LeveragePanel


class FeedControls(unittest.IsolatedAsyncioTestCase):
    async def test_coinbase_toggle_hides_all_of_its_surfaces_and_basis(self):
        console = ConsoleFixture()
        panel = LeveragePanel(console=console)
        app = PanelHost(panel)
        async with app.run_test(size=(120, 42)) as pilot:
            for _ in range(100):
                if panel.snapshot_data is not None:
                    break
                await pilot.pause(0.02)
            coinbase = panel.query_one("#leverage-feed-coinbase", Checkbox)
            self.assertTrue(coinbase.value)
            await pilot.click("#leverage-feed-coinbase")
            await pilot.pause(0.1)
            self.assertFalse(coinbase.value)
            for identity in (
                "leverage-live-market",
                "leverage-strategies",
                "leverage-events",
            ):
                self.assertFalse(panel.query_one("#" + identity).display, identity)
            visible = "\n".join(
                str(w.render())
                for w in panel.query(Static)
                if w.display
                and w.visible
                and not (w.id or "").startswith("leverage-feed")
                and not any(
                    (a.id or "").startswith("leverage-feed") for a in w.ancestors
                )
            )
            self.assertNotIn("Coinbase", visible)
            self.assertNotIn("Basis", visible)
            self.assertNotIn("BOP", visible)
            self.assertNotIn("EMA", visible)
            self.assertEqual(console.executes + console.closes, 0)

    async def test_both_hidden_restore_without_changing_asset_or_arming(self):
        console = ConsoleFixture()
        panel = LeveragePanel(console=console)
        async with PanelHost(panel).run_test(size=(120, 42)) as pilot:
            await pilot.pause(0.15)
            panel.query_one("#leverage-asset", Select).value = "BTC"
            for source in ("coinbase", "jupiter"):
                panel.query_one("#leverage-feed-" + source, Checkbox).value = False
            await pilot.pause(0.15)
            self.assertIn(
                "Both feeds hidden",
                str(panel.query_one("#leverage-feed-notice", Static).render()),
            )
            self.assertFalse(panel.query_one("#leverage-workspace").display)
            self.assertFalse(panel.query_one("#leverage-trading").display)
            self.assertTrue(panel.query_one("#leverage-feed-jupiter", Checkbox).display)
            panel.query_one("#leverage-feed-coinbase", Checkbox).value = True
            await pilot.pause(0.1)
            self.assertEqual(panel.query_one("#leverage-asset", Select).value, "BTC")
            self.assertTrue(panel.query_one("#leverage-live-market").display)
            self.assertFalse(panel.query_one("#leverage-trading").display)
            self.assertEqual(console.executes + console.closes + console.previews, 0)

    async def test_preferences_survive_panel_reopen_and_preserve_execution_config(self):
        with tempfile.TemporaryDirectory() as name:
            home = Path(name)
            private = home / "config.json"
            original = b'{"armed":true,"sdk":{"enabled":true}}\n'
            private.write_bytes(original)
            panel = LeveragePanel(home, console=ConsoleFixture())
            async with PanelHost(panel).run_test(size=(120, 42)) as pilot:
                await pilot.pause(0.15)
                await pilot.click("#leverage-feed-coinbase")
                await pilot.pause(0.1)
            self.assertEqual(private.read_bytes(), original)
            reopened = LeveragePanel(home, console=ConsoleFixture())
            self.assertEqual(
                reopened.feed_enabled, {"jupiter": True, "coinbase": False}
            )
            self.assertEqual(private.read_bytes(), original)

    async def test_snapshot_error_is_visible_and_refresh_recovers(self):
        console = ConsoleFixture()
        console.read_error = True
        panel = LeveragePanel(console=console)
        async with PanelHost(panel).run_test(size=(80, 24)) as pilot:
            for _ in range(100):
                if panel._read_failed:
                    break
                await pilot.pause(0.02)
            notice = panel.query_one("#leverage-feed-notice", Static)
            self.assertIn("Snapshot unavailable", str(notice.render()))
            self.assertIn("Refresh", str(notice.render()))
            self.assertLessEqual(notice.region.bottom, 24)
            console.read_error = False
            panel.action_refresh()
            for _ in range(100):
                if panel.snapshot_data is not None:
                    break
                await pilot.pause(0.02)
            self.assertNotIn("Snapshot unavailable", str(notice.render()))

    async def test_short_terminal_can_focus_preview_with_feed_controls_visible(self):
        from textual.widgets import Button

        panel = LeveragePanel(console=ConsoleFixture())
        async with PanelHost(panel).run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.15)
            button = panel.query_one("#leverage-preview", Button)
            button.focus()
            for _ in range(50):
                if 0 <= button.region.y and button.region.bottom <= 24:
                    break
                await pilot.pause(0.02)
            self.assertGreaterEqual(button.region.y, 0)
            self.assertLessEqual(button.region.bottom, 24)
            for source in ("jupiter", "coinbase"):
                box = panel.query_one("#leverage-feed-" + source, Checkbox)
                self.assertGreaterEqual(box.region.y, 0)
                self.assertLessEqual(box.region.bottom, 24)
            await pilot.click("#leverage-preview")
            await pilot.pause(0.15)
            self.assertEqual(panel.console.previews, 1)
            self.assertEqual(panel.console.executes, 0)


class BarReadability(unittest.TestCase):
    def test_all_bar_intensities_keep_label_contrast_at_least_four_point_five(self):
        from research.zec_leverage_panel import bar_text_color, bar_view

        def luminance(color):
            values = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
            linear = [
                v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
                for v in values
            ]
            return sum(
                a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
            )

        for n in range(-100, 101):
            _, background = bar_view(
                {"open": 100, "close": 100 + n / 10, "baseline_range": 10}
            )
            foreground = bar_text_color(background)
            a, b = sorted((luminance(background), luminance(foreground)))
            self.assertGreaterEqual(
                (b + 0.05) / (a + 0.05), 4.5, (n, background, foreground)
            )


class KeyboardFeeds(unittest.IsolatedAsyncioTestCase):
    async def test_tab_space_and_shift_tab_keep_controls_reachable(self):
        panel = LeveragePanel(console=ConsoleFixture())
        async with PanelHost(panel).run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.15)
            jupiter = panel.query_one("#leverage-feed-jupiter", Checkbox)
            coinbase = panel.query_one("#leverage-feed-coinbase", Checkbox)
            jupiter.focus()
            await pilot.press("tab")
            self.assertTrue(coinbase.has_focus)
            await pilot.press("space")
            await pilot.pause(0.05)
            self.assertFalse(panel.feed_enabled["coinbase"])
            self.assertTrue(coinbase.has_focus)
            await pilot.press("shift+tab")
            self.assertTrue(jupiter.has_focus)
            await pilot.press("space")
            await pilot.pause(0.05)
            self.assertEqual(panel.feed_enabled, {"jupiter": False, "coinbase": False})
            await pilot.press("tab", "space")
            await pilot.pause(0.05)
            self.assertTrue(panel.feed_enabled["coinbase"])
            self.assertFalse(panel.feed_enabled["jupiter"])

    async def test_partial_nested_provider_sections_remain_a_recoverable_view(self):
        console = ConsoleFixture()
        console.data["performance"] = {"by_asset": {"ZEC": None}}
        console.data["mtf_forward"] = {"assets": {"ZEC": None}}
        panel = LeveragePanel(console=console)
        async with PanelHost(panel).run_test(size=(120, 42)) as pilot:
            await pilot.pause(0.2)
            self.assertIsNotNone(panel.snapshot_data)
            self.assertIn(
                "settled —", str(panel.query_one("#leverage-status", Static).render())
            )
            self.assertIn(
                "observer age unknown",
                str(panel.query_one("#leverage-bar-tilts", Static).render()).lower(),
            )
            await pilot.click("#leverage-feed-coinbase")
            await pilot.pause(0.05)
            self.assertFalse(panel.feed_enabled["coinbase"])
            console.data["mtf_forward"] = {
                "assets": {
                    "ZEC": {
                        "frames": {"5": None},
                        "scores": {"5": {"components": None}, "10": None},
                    }
                }
            }
            panel.snapshot_data = console.data
            panel.paint_snapshot()
            self.assertIn(
                "waiting",
                str(panel.query_one("#leverage-performance", Static).render()),
            )

    async def test_long_preview_keeps_live_comparison_and_controls_reachable(self):
        for size in ((80, 24), (120, 42)):
            with self.subTest(size=size):
                console = ConsoleFixture()
                preview = console.preview

                def long_preview(*args, preview=preview):
                    result = preview(*args)
                    result["message"] = (
                        "Market order; indicative entry. Current-format close is unavailable. "
                        * 12
                    )
                    result["preview"] = {
                        "checked": {"verification": "current_observed_subset"}
                    }
                    return result

                console.preview = long_preview
                panel = LeveragePanel(console=console)
                async with PanelHost(panel).run_test(size=size) as pilot:
                    await pilot.pause(0.15)
                    button = panel.query_one("#leverage-preview")
                    button.focus()
                    await pilot.press("enter")
                    for _ in range(100):
                        if panel.preview_id is not None:
                            break
                        await pilot.pause(0.02)
                    result = panel.query_one("#leverage-result")
                    self.assertLessEqual(
                        panel.query_one("#leverage-result-region").region.height, 6
                    )
                    self.assertGreaterEqual(
                        panel.query_one("#leverage-workspace").region.height, 5
                    )
                    panel.query_one("#leverage-preview").focus()
                    for _ in range(50):
                        if button.region.bottom <= size[1]:
                            break
                        await pilot.pause(0.02)
                    self.assertLessEqual(button.region.bottom, size[1])
                    self.assertIn(
                        "Current-format close is unavailable", str(result.render())
                    )
                    self.assertTrue(
                        str(result.render()).startswith(
                            "1000x MARKET · entry indicative · close unavailable"
                        )
                    )
                    self.assertEqual(console.executes, 0)

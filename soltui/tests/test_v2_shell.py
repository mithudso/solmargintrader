"""The v2 shell: every classic pane stays reachable, and the new chrome reads without writing.

The redesign (docs/design/soltui-v2/DESIGN.md) regroups the classic tabs into destinations. Its one
non-negotiable is that no function is lost, so the coverage test asserts every pane of `#main-tabs`
against the live navigation, including a pane added after the map was written.
"""

from __future__ import annotations

import time
import unittest
from tempfile import TemporaryDirectory
from unittest import mock

from textual.widgets import Static, TabbedContent, TabPane

from soltui import shell
from soltui.commands import COMMANDS
from soltui.config import Settings
from soltui.tui import SolTuiApp

SIZE = (170, 50)


def ok(result):
    return {"ok": True, "result": result}


class PureBuilderTests(unittest.TestCase):
    def test_every_classic_tab_has_a_home(self) -> None:
        classic = {"tab-settings", "tab-strategies", "tab-signals", "tab-compound", "tab-forwardtest",
                   "tab-bots", "tab-backtest", "tab-top5", "tab-liverun", "tab-execute", "tab-analyze",
                   "tab-cumulative", "tab-queue", "tab-liquidity", "tab-pnl", "tab-wallet", "tab-research",
                   "tab-docs"}
        self.assertEqual(classic - shell.COVERED_TABS, set())
        self.assertEqual(shell.locate("tab-liquidity")[0].key, "archive")
        self.assertNotIn("tab-liquidity", {view.tab for view in shell.DEST_BY_KEY["money"].views})
        self.assertEqual(shell.DEST_BY_KEY["archive"].hotkey, "6")
        # Each Compound section is its own Signal view, in the classic order.
        signal = shell.DEST_BY_KEY["signal"]
        self.assertEqual([v.inner for v in signal.views], ["cmp-call", "cmp-backtest", "cmp-forward", "cmp-coins"])

    def test_a_pane_added_later_lands_in_research(self) -> None:
        dests = shell.with_extra_views([("tab-backtest", "Backtest"), ("tab-coins", "Coins")])
        research = next(d for d in dests if d.key == "research")
        self.assertEqual(research.views[-1], shell.View("tab-coins", "Coins", was="Coins"))
        self.assertEqual(shell.locate("tab-coins", None, dests)[0].key, "research")
        self.assertIs(shell.with_extra_views([("tab-backtest", "Backtest")]), shell.DESTINATIONS)

    def test_locate_prefers_the_exact_section(self) -> None:
        dest, index = shell.locate("tab-compound", "cmp-forward")
        self.assertEqual((dest.key, dest.views[index].label), ("signal", "Forward test"))
        dest, index = shell.locate("tab-compound")
        self.assertEqual(dest.views[index].inner, "cmp-call")

    def test_narrow_navigation_keeps_the_active_view_and_clickable_neighbors(self) -> None:
        from rich.text import Text

        dest = shell.DEST_BY_KEY["research"]
        for width in (80, 100, 160):
            for index, view in enumerate(dest.views):
                segments = shell.subnav_segments(dest, index, width)
                line = Text.assemble(*(piece for piece, _ in segments))
                self.assertLessEqual(line.cell_len, width)
                self.assertIn(view.label, line.plain)
                targets = {target for _, target in segments}
                self.assertIn(f"view:{index}", targets)
                self.assertIn(f"view:{(index - 1) % len(dest.views)}", targets)
                self.assertIn(f"view:{(index + 1) % len(dest.views)}", targets)

    def test_narrow_topbar_keeps_the_no_order_path_badge(self) -> None:
        from rich.text import Text

        for width in (80, 100, 160):
            segments = shell.topbar_segments("research", "SOL $90.00", "dry-run only · no live order path", "12:00", width)
            line = Text.assemble(*(piece for piece, _ in segments))
            self.assertLessEqual(line.cell_len, width)
            self.assertIn("dry-run", line.plain)
            self.assertIn("order path", line.plain)
            self.assertIn("no live order path" if width == 160 else "no order path", line.plain)
            self.assertTrue({f"dest:{d.key}" for d in shell.DESTINATIONS} <= {t for _, t in segments})

    def test_needs_lists_failures_worst_first(self) -> None:
        reads = {
            "queue.progress": ok({"state": {"phase": "error", "error": "ValueError: proof differs"}, "alive": False}),
            "liquidity.status": ok({"status_ok": True, "killed": True, "mode_badge": "LIVE"}),
            "prices.status": ok({"running": False}),
            "portfolio.last": ok({"saved_at": time.time() - 60, "result": {"partial": True}}),
        }
        autopilot = {"autopilot": True, "live_coins": ["SOL", "BTC"], "running": ["BTC"],
                     "agent": {"loaded": True}}
        items = shell.needs(reads, autopilot=autopilot, notice={"changed": True, "line": "SOL +0.42"})
        kinds = [n.kind for n in items]
        self.assertEqual(kinds, sorted(kinds, key=lambda k: shell._SEVERITY[k]))
        titles = " | ".join(n.title for n in items)
        for expected in ("Background sweep stopped with an error", "Trainer stopped: SOL",
                         "Price recorder is not running", "Last wallet scan was partial", "Wallet changed"):
            self.assertIn(expected, titles)
        self.assertEqual(items[0].kind, "err")
        self.assertEqual(shell.needs({}), [])

    def test_health_strip_reads_glyphs_not_colour_alone(self) -> None:
        reads = {
            "queue.progress": ok({"state": {"phase": "running", "done": 3, "total": 10}, "alive": False}),
            "liquidity.status": ok({"status_ok": False, "status_reason": "STALE: daemon may be down"}),
        }
        items = shell.health_items(reads, forward_running=True)
        by_label = {i.label: i for i in items}
        self.assertEqual(by_label["Sweep"].kind, "warn")
        self.assertEqual(by_label["Sweep"].detail, "stopped unexpectedly")
        self.assertNotIn("LP daemon", by_label)
        self.assertEqual(by_label["Fwd test"].kind, "run")
        text = shell.health_text(items).plain
        self.assertIn("▲ Sweep stopped unexpectedly", text)

    def test_archived_lp_never_appears_on_home(self) -> None:
        for state in ({"status_ok": True, "killed": True, "mode_badge": "LIVE"},
                      {"status_ok": False, "status_reason": "STALE"},
                      {"status_ok": True, "killed": False}):
            with self.subTest(state=state):
                reads = {"liquidity.status": ok(state)}
                self.assertFalse(any("LP" in item.title for item in shell.needs(reads)))
                self.assertFalse(any("LP" in item.label for item in shell.health_items(reads)))
                self.assertFalse(any("LP" in label for label, _, _ in shell.tiles(reads)))
        self.assertTrue(any(view.tab == "tab-liquidity" for dest in shell.DESTINATIONS
                            if dest.key == "archive" for view in dest.views))

    def test_signal_hero_leads_with_the_call(self) -> None:
        hero = shell.signal_hero({
            "call": "DOWN", "composite": -0.31, "blocked_by": [], "coverage": 0.92, "agreement": 0.64,
            "regime": "trend", "round_trip_bps": 13,
            "components": [{"kind": "gate", "enabled": True, "blocked": False},
                           {"kind": "gate", "enabled": True, "blocked": False}],
        }).plain
        self.assertLess(hero.index("DOWN"), hero.index("composite"))
        self.assertIn("gates 2/2 pass", hero)
        self.assertIn("round trip 13 bps", hero)

    def test_summarise_never_dumps_a_whole_result(self) -> None:
        self.assertEqual(shell.summarise({"summary": "idle"}), "idle")
        self.assertLessEqual(len(shell.summarise({f"k{i}": "x" * 40 for i in range(50)})), 220)


class ShellAppTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def app(self, **kwargs) -> SolTuiApp:
        return SolTuiApp(Settings(data_dir=self.tmp.name, poll_interval_seconds=60), **kwargs)

    async def test_every_pane_is_reachable_from_the_navigation(self) -> None:
        app = self.app(start="tab-now")
        async with app.run_test(size=SIZE) as pilot:
            tabs = app.query_one("#main-tabs", TabbedContent)
            panes = {p.id for p in tabs.query(TabPane)
                     if next(a for a in p.ancestors if isinstance(a, TabbedContent)) is tabs}
            reached = set()
            for dest in app._v2_dests:
                for i, view in enumerate(dest.views):
                    app._v2_show(dest.key, i)
                    await pilot.pause()
                    self.assertEqual(tabs.active, view.tab, (dest.key, view.label))
                    reached.add(tabs.active)
            self.assertEqual(panes - reached, set())

    async def test_opens_on_now_with_the_classic_bar_hidden(self) -> None:
        app = self.app(start="tab-now")
        async with app.run_test(size=SIZE) as pilot:
            await pilot.pause()
            self.assertTrue(app.screen.has_class("v2"))
            self.assertEqual(app.query_one("#main-tabs", TabbedContent).active, "tab-now")
            self.assertFalse(app.query_one("#main-tabs > ContentTabs").display)
            self.assertIn("Now", str(app.query_one("#v2-topbar", Static).render()))
            # The shared editor would take half of Now; it is hidden there, and back elsewhere.
            self.assertFalse(app.query_one("#editor-panel").display)
            await pilot.press("3")
            self.assertTrue(app.query_one("#editor-panel").display)

    async def test_keys_move_between_destinations_and_views(self) -> None:
        app = self.app(start="tab-now")
        async with app.run_test(size=SIZE) as pilot:
            tabs = app.query_one("#main-tabs", TabbedContent)
            await pilot.press("2")
            self.assertEqual(tabs.active, "tab-compound")
            await pilot.press("right_square_bracket")
            self.assertEqual(app.query_one("#compound-sections", TabbedContent).active, "cmp-backtest")
            await pilot.press("3")
            self.assertEqual(tabs.active, "tab-backtest")
            await pilot.press("4")
            self.assertTrue(app.query_one("#v2-live-banner").has_class("on"))
            await pilot.press("6")
            self.assertEqual(tabs.active, "tab-liquidity")
            self.assertEqual(app._v2_dest, "archive")
            self.assertTrue(app.query_one("#liq-positions"))
            self.assertTrue(app.query_one("#liq-scout"))
            await pilot.press("comma")
            self.assertEqual(tabs.active, "tab-settings")
            self.assertFalse(app.query_one("#v2-live-banner").has_class("on"))
            # A tab switched by anything else (the classic bar, a test, a link) moves the chrome too.
            tabs.active = "tab-wallet"
            await pilot.pause()
            self.assertEqual((app._v2_dest, app._v2_destination("money").views[app._v2_index].tab),
                             ("money", "tab-wallet"))

    async def test_explain_shows_the_f1_text_without_a_new_screen(self) -> None:
        app = self.app(start="tab-now")
        async with app.run_test(size=SIZE) as pilot:
            await pilot.press("question_mark")
            panel = app.query_one("#v2-explain", Static)
            self.assertTrue(panel.has_class("open"))
            self.assertIn("EXPLAIN", str(panel.render()))
            self.assertIs(app.screen, app.screen_stack[0])
            await pilot.press("question_mark")
            self.assertFalse(panel.has_class("open"))

    async def test_palette_lists_every_command_and_never_runs_a_write(self) -> None:
        app = self.app(start="tab-now")
        async with app.run_test(size=SIZE) as pilot:
            entries = {e.name: e for e in app.v2_palette_entries()}
            self.assertEqual({n for n in COMMANDS} - set(entries), set())
            self.assertIn("opens its view", entries["liquidity.resume"].help)
            self.assertIn("opens its view", entries["liquidity.kill"].help)
            self.assertIn("runs now", entries["queue.progress"].help)
            calls: list[str] = []
            real = app._call

            def spy(name, params=None, *, quiet=False):
                calls.append(name)
                return real(name, params, quiet=quiet)

            with mock.patch.object(app, "_call", side_effect=spy):
                entries["liquidity.resume"].run()
                entries["liquidity.kill"].run()
                await pilot.pause()
                self.assertNotIn("liquidity.resume", calls)
                self.assertNotIn("liquidity.kill", calls)
                self.assertEqual(app.query_one("#main-tabs", TabbedContent).active, "tab-liquidity")
                for name in COMMANDS:
                    if name.startswith("experiments.") and not COMMANDS[name].read_only:
                        entries[name].run()
                        self.assertNotIn(name, calls)
                        self.assertEqual(app._v2_command_home(name), ("tab-bots", "bots-workbench"))
                await pilot.pause()
                self.assertEqual(app.query_one("#main-tabs", TabbedContent).active, "tab-bots")
                entries["queue.progress"].run()
                self.assertIn("queue.progress", calls)

    async def test_classic_mode_keeps_the_original_bar(self) -> None:
        app = self.app(classic=True)
        async with app.run_test(size=SIZE) as pilot:
            await pilot.pause()
            self.assertTrue(app.screen.has_class("classic"))
            self.assertEqual(app.query_one("#main-tabs", TabbedContent).active, "tab-backtest")
            self.assertTrue(app.query_one("#main-tabs > ContentTabs").display)
            self.assertFalse(app.query_one("#v2-topbar").display)

    def test_main_opens_now_unless_classic(self) -> None:
        from soltui import tui

        seen = []
        with mock.patch.object(tui.SolTuiApp, "run", lambda self: seen.append((self._start, self._v2))):
            tui.main([])
            tui.main(["--classic"])
        self.assertEqual(seen, [("tab-now", True), ("tab-backtest", False)])


if __name__ == "__main__":
    unittest.main()

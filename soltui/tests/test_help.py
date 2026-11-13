"""Exercise help discovery and keyboard/mouse access without invoking actions."""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from textual.containers import VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Input,
    OptionList,
    Select,
    Static,
    Tab,
    TabbedContent,
    TabPane,
    TextArea,
)

from soltui import liquidity
from soltui.config import Settings
from soltui.help import SIGNAL_HELP, column_help, row_help
from soltui.help_screen import HelpScreen
from soltui.signals import SIGNAL_GROUPS
from soltui.tui import GlossaryTable, SolTuiApp


class HelpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        from soltui.tests.test_tui import offline_console_reads
        self.enterContext(offline_console_reads())
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = SolTuiApp(Settings(data_dir=self.tmp.name, poll_interval_seconds=60))

    async def test_all_tabs_and_controls_have_explanations(self) -> None:
        async with self.app.run_test(size=(150, 45)) as pilot:
            for pane in self.app.query(TabPane):
                # Activate every tab set on the way down: the Compound tab has its own sections.
                for owner in reversed([a for a in pane.ancestors_with_self if isinstance(a, TabPane)]):
                    tabs = next(a for a in owner.ancestors if isinstance(a, TabbedContent))
                    tabs.active = owner.id
                await pilot.pause()
                self.assertTrue(pane.tooltip, pane.id)
            controls = (Button, Input, Select, OptionList, TextArea)
            missing = [w.id for w in self.app.query("*")
                       if isinstance(w, controls) and not w.tooltip]
            self.assertEqual(missing, [])
            self.assertEqual([w.id for w in self.app.query(DataTable)
                              if not isinstance(w, GlossaryTable)], [])
            self.assertEqual([w.id for w in self.app.query(Tab) if not w.tooltip], [])
            self.assertEqual([(w.id, str(c.label)) for w in self.app.query(GlossaryTable)
                              for i, c in enumerate(w.ordered_columns)
                              if not w.header_tooltip(i)], [])

    def test_every_signal_parameter_and_liquidity_column_is_explained(self) -> None:
        from backtester.core.strategies import REGISTRY
        self.assertEqual([name for name in REGISTRY if not row_help(name)], [])
        self.assertEqual([n for _, names in SIGNAL_GROUPS for n in names if n not in SIGNAL_HELP], [])
        for mode in ("live", "dry-run", "unknown"):
            for maker in (liquidity.positions_table, liquidity.experiments_table,
                          liquidity.scout_table, liquidity.actions_table):
                for label in maker({"mode": mode}).headers:
                    self.assertIsNotNone(column_help(label, "liq-actions"), label)

    def test_overloaded_kind_has_the_correct_context(self) -> None:
        self.assertIn("token mint", column_help("kind", "wallet-contracts"))
        self.assertIn("file classification", column_help("kind", "docs-table"))
        self.assertIn("action", column_help("kind", "liq-actions"))

    def test_parameterized_strategy_row_preserves_its_mechanism_help(self) -> None:
        self.assertEqual(row_help(" GRID (levels=4) "), row_help("grid"))
        self.assertIsNone(row_help("unknown_strategy (x=1)"))

    async def test_real_cell_hover_explains_value_and_clears_on_leave(self) -> None:
        async with self.app.run_test(size=(150, 45)) as pilot:
            table = self.app.query_one("#results-table", GlossaryTable)
            table.add_row("grid", "mean-reversion", "+0.2", "0.4", "60%", "backtest +2%", "12")
            await pilot.pause()
            table.scroll_visible(immediate=True)
            await pilot.pause()
            self.assertIs(self.app.get_widget_at(table.region.x + 2, table.region.y + 1)[0], table)
            await pilot.hover(table, offset=(2, 1))
            await pilot.pause()
            self.assertIn("exposure", str(table.tooltip))
            self.assertIn("strategy", str(table.tooltip).lower())
            await pilot.hover("#help-hint")
            self.assertIsNone(table.tooltip)
            self.assertIsNone(table.header_tooltip(-1))

    async def test_f1_works_from_input_and_returns_focus_without_changing_text(self) -> None:
        async with self.app.run_test(size=(100, 30)) as pilot:
            self.app.query_one(TabbedContent).active = "tab-settings"
            await pilot.pause()
            field = self.app.query_one("#set-fee_bps", Input)
            field.focus()
            before = field.value
            await pilot.press("f1")
            self.assertIsInstance(self.app.screen, HelpScreen)
            body = str(self.app.screen.query_one("#help-body", Static).content)
            self.assertIn("$0.60", body)
            self.assertIn("Current control", body)
            await pilot.press("escape")
            self.assertIs(self.app.focused, field)
            self.assertEqual(field.value, before)

    async def test_help_search_and_keyboard_scroll_on_small_terminal(self) -> None:
        async with self.app.run_test(size=(80, 24)) as pilot:
            await pilot.press("f1")
            screen = self.app.screen
            screen.query_one("#help-search", Input).value = "grid"
            await pilot.pause()
            body = str(screen.query_one("#help-body", Static).content)
            self.assertIn("resting ladder", body)
            self.assertNotIn("wallet secret", body)
            screen.query_one("#help-search", Input).value = "no-such-term-xyz"
            await pilot.pause()
            self.assertIn("No matching term", str(screen.query_one("#help-body", Static).content))
            screen.query_one("#help-search", Input).value = ""
            await pilot.pause()
            scroll = screen.query_one("#help-scroll", VerticalScroll)
            scroll.focus()
            await pilot.press("pagedown")
            await pilot.pause()
            self.assertGreater(scroll.scroll_y, 0)
            await pilot.press("escape")
            self.assertNotIsInstance(self.app.screen, HelpScreen)

    async def test_f1_from_table_includes_selected_metric(self) -> None:
        async with self.app.run_test(size=(120, 35)) as pilot:
            table = self.app.query_one("#results-table", GlossaryTable)
            table.add_row("grid", "mean-reversion", "+0.2", "0.4", "60%", "backtest +2%", "12")
            table.focus()
            table.move_cursor(column=2)
            await pilot.press("f1")
            body = str(self.app.screen.query_one("#help-body", Static).content)
            self.assertIn("risk-adjusted", self.app.screen.context)
            self.assertIn("not a forecast", body)

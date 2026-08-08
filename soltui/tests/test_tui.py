"""Smoke tests for the Textual app, driven through Textual's own test harness.

An app that imports cleanly but explodes on mount is not working, so these
actually mount it, click things, and assert on widget state. `run_test()` runs a
headless terminal, so no TTY is required and this is safe in CI.

The load-bearing test here is `test_execute_tab_declares_dry_run`: the Execute tab
must state its mode unmistakably, because that banner is the user's only in-app
signal that nothing is reaching a venue.
"""

from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static

from soltui.config import Settings
from soltui.tui import FAMILY_NOTES, SIGNAL_REFERENCE, SolTuiApp


# Terminal big enough that every button is on-screen; Pilot.click() raises
# OutOfBounds for widgets outside the visible region, and the default 80x24 is
# too small for these forms.
TEST_SIZE = (180, 55)


def text_of(app, selector: str) -> str:
    """Visible text of a Static.

    Centralised because the accessor is version-dependent: Textual 8.x exposes
    `.content`, older versions used `.renderable`. One edit here beats twenty.
    """
    widget = app.query_one(selector, Static)
    for attr in ("content", "renderable"):
        if hasattr(widget, attr):
            return str(getattr(widget, attr))
    return str(widget)


def make_settings() -> Settings:
    """Settings pointing at the repo's real data dir, with a fast poll."""
    return Settings(poll_interval_seconds=0.01)


class TestSortKey(unittest.TestCase):
    """`sort_key` decides how header-click sorting ranks cell text."""

    def test_numeric_strings_rank_numerically_not_lexically(self) -> None:
        from soltui.tui import sort_key
        # Lexically "10" < "9" and "-0.9" < "-3.7"; numerically neither is.
        self.assertLess(sort_key("9"), sort_key("10"))
        self.assertLess(sort_key("-3.736213"), sort_key("-0.9"))

    def test_decorated_numbers_parse(self) -> None:
        from soltui.tui import sort_key
        self.assertLess(sort_key("+0.128"), sort_key("+0.534"))
        self.assertLess(sort_key("33%"), sort_key("85%"))
        self.assertLess(sort_key("680"), sort_key("4,304"))

    def test_text_sorts_case_insensitively_after_numbers(self) -> None:
        from soltui.tui import sort_key
        self.assertLess(sort_key("apple"), sort_key("Banana"))
        self.assertLess(sort_key("99999"), sort_key("aardvark"))

    def test_placeholder_cells_rank_last(self) -> None:
        from soltui.tui import sort_key
        self.assertLess(sort_key("zebra"), sort_key("-"))
        self.assertLess(sort_key("zebra"), sort_key(""))


class TestSortableTables(unittest.IsolatedAsyncioTestCase):
    """Clicking a column header sorts the table; clicking again flips it.

    Driven by posting `DataTable.HeaderSelected` from the table (what a real
    header click emits, bubbling to the app-level handler) rather than
    `pilot.click` at a pixel coordinate, which would couple the test to
    column widths.
    """

    @staticmethod
    def _column_values(table, column_index: int) -> list[str]:
        return [str(table.get_row_at(i)[column_index])
                for i in range(table.row_count)]

    @staticmethod
    def _click_header(table, column_index: int) -> None:
        """Post exactly what DataTable emits for a header click."""
        from rich.text import Text

        column = table.ordered_columns[column_index]
        table.post_message(DataTable.HeaderSelected(
            table, column.key, column_index, Text(str(column.label))))

    async def test_header_click_sorts_then_reverses(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            table = app.query_one("#signals-table", DataTable)

            self._click_header(table, 0)  # the "signal" column
            await pilot.pause()
            ascending = self._column_values(table, 0)
            self.assertEqual(ascending, sorted(ascending, key=str.casefold))

            self._click_header(table, 0)
            await pilot.pause()
            self.assertEqual(self._column_values(table, 0), ascending[::-1])

    async def test_numeric_column_sorts_by_value(self) -> None:
        """The Strategies roster's warm-up column is numeric text -- the
        column type someone actually sorts to rank."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            table = app.query_one("#roster-table", DataTable)

            self._click_header(table, 2)  # "warm-up"
            await pilot.pause()

            warmups = [int(v) for v in self._column_values(table, 2)]
            self.assertEqual(warmups, sorted(warmups))


class TestAppMounts(unittest.IsolatedAsyncioTestCase):
    """The app composes and every tab is reachable."""

    async def test_mounts_and_has_five_tabs(self) -> None:
        """All five requested tabs exist."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            for tab in ("settings", "strategies", "signals", "backtest", "execute"):
                with self.subTest(tab=tab):
                    self.assertTrue(app.query(f"#tab-{tab}"), f"missing #tab-{tab}")
            await pilot.pause()

    async def test_indicator_line_is_present_and_labelled(self) -> None:
        """The in-app indicator mirrors the menu-bar title."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            text = text_of(app, "#indicator")
            self.assertIn("SOL", text)

    async def test_every_tab_can_be_activated(self) -> None:
        """Switching tabs must not raise."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import TabbedContent

            tabs = app.query_one(TabbedContent)
            for tab in ("tab-settings", "tab-strategies", "tab-signals",
                        "tab-backtest", "tab-execute"):
                tabs.active = tab
                await pilot.pause()
            self.assertEqual(tabs.active, "tab-execute")


class TestExecuteTabSafety(unittest.IsolatedAsyncioTestCase):
    """The Execute tab's mode must be unmistakable."""

    async def test_execute_tab_declares_dry_run(self) -> None:
        """The banner is the user's only in-app signal that nothing reaches a venue."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            banner = text_of(app, "#execute-banner")
            self.assertIn("DRY RUN", banner)
            self.assertIn("no orders", banner.lower())

    async def test_stepping_without_a_session_is_refused_not_crashed(self) -> None:
        """Clicking Step before starting must produce a message, not a traceback."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import TabbedContent

            app.query_one(TabbedContent).active = "tab-execute"
            await pilot.pause()
            await pilot.click("#btn-step1")
            await pilot.pause()
            summary = text_of(app, "#exec-summary")
            self.assertIn("start a dry run first", summary)


class TestStrategiesTab(unittest.IsolatedAsyncioTestCase):
    """Add/remove wiring."""

    async def test_roster_table_starts_populated(self) -> None:
        """The default roster is visible on open."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            table = app.query_one("#roster-table", DataTable)
            self.assertEqual(table.row_count, len(app.roster))
            self.assertGreater(table.row_count, 0)

    async def test_available_table_lists_every_registered_strategy(self) -> None:
        """The picker must not hide options."""
        from backtester.core.strategies import REGISTRY

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertEqual(
                app.query_one("#available-table", DataTable).row_count, len(REGISTRY)
            )

    async def test_reset_restores_the_default_roster(self) -> None:
        """Reset is a recovery path from a mangled roster."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import TabbedContent

            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            app.roster.clear()
            await pilot.click("#btn-reset-roster")
            await pilot.pause()
            self.assertEqual(len(app.roster), 4)

    async def test_bad_params_surface_as_a_message(self) -> None:
        """An invalid param string must not crash the app."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import Input, TabbedContent

            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            app.query_one("#strategy-params", Input).value = "notakeyvalue"
            await pilot.click("#btn-add")
            await pilot.pause()
            status = text_of(app, "#roster-status")
            self.assertIn("expected key=value", status)

    async def test_clicking_an_available_strategy_opens_its_source_file(self) -> None:
        """The strategy list is a shortcut into the code that defines it."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            table = app.query_one("#available-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]) == "rsi")
            table.move_cursor(row=row)
            await pilot.pause()

            self.assertEqual(app._docs_current_path,
                              "backtester/core/strategies/rsi.py")
            self.assertIn("RSI mean-reversion",
                          app.query_one("#docs-view", TextArea).text)

    async def test_unknown_strategy_name_reports_instead_of_crashing(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app._open_strategy_file("not_a_real_strategy")
            await pilot.pause()
            self.assertIn("not in the Docs catalogue",
                          text_of(app, "#docs-view-status"))

    async def test_clicking_a_roster_entry_opens_its_source_file(self) -> None:
        """The roster table's first column is a label, not a REGISTRY name --
        this pins that the lookup goes through the roster entry, not the
        display text, to find the right file."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            table = app.query_one("#roster-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]) == "rsi_14_30_50")
            table.move_cursor(row=row)
            await pilot.pause()

            self.assertEqual(app._docs_current_path,
                              "backtester/core/strategies/rsi.py")
            self.assertIn("RSI mean-reversion",
                          app.query_one("#docs-view", TextArea).text)


class TestSignalsTab(unittest.IsolatedAsyncioTestCase):
    """The reference tables."""

    async def test_signal_and_family_tables_are_populated(self) -> None:
        """Both reference tables render their full content."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            self.assertEqual(
                app.query_one("#signals-table", DataTable).row_count,
                len(SIGNAL_REFERENCE),
            )
            self.assertEqual(
                app.query_one("#families-table", DataTable).row_count,
                len(FAMILY_NOTES),
            )

    def test_family_notes_cover_every_registry_family(self) -> None:
        """A strategy whose family has no note would render a blank row."""
        from backtester.core.strategies import FAMILY

        missing = set(FAMILY.values()) - set(FAMILY_NOTES)
        self.assertEqual(missing, set(), f"families with no note: {missing}")


class TestSettingsTab(unittest.IsolatedAsyncioTestCase):
    """The settings form."""

    async def test_form_is_prefilled_from_settings(self) -> None:
        """Open state reflects the loaded config."""
        app = SolTuiApp(Settings(capital=12_345.0, poll_interval_seconds=0.01))
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import Input, TabbedContent

            app.query_one(TabbedContent).active = "tab-settings"
            await pilot.pause()
            self.assertEqual(
                app.query_one("#set-capital", Input).value, "12345.0"
            )

    async def test_invalid_setting_reports_instead_of_crashing(self) -> None:
        """A negative fill delay is refused with a message."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            from textual.widgets import Input, TabbedContent

            app.query_one(TabbedContent).active = "tab-settings"
            await pilot.pause()
            app.query_one("#set-fill_delay", Input).value = "-1"
            await pilot.click("#btn-save")
            await pilot.pause()
            status = text_of(app, "#settings-status")
            self.assertIn("look-ahead", status)


class TestSignalsTabEditable(unittest.IsolatedAsyncioTestCase):
    """The Signals tab edits values, not just displays them."""

    async def test_inputs_exist_for_every_tunable(self) -> None:
        """Every signal field must have an editable input."""
        from soltui.signals import SIGNAL_GROUPS
        from textual.widgets import Input, TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-signals"
            await pilot.pause()
            for _, names in SIGNAL_GROUPS:
                for name in names:
                    with self.subTest(field=name):
                        self.assertIsNotNone(app.query_one(f"#sig-{name}", Input))

    async def test_editing_and_saving_updates_the_live_defaults(self) -> None:
        """A saved edit changes what new roster entries will use."""
        from textual.widgets import Input, TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-signals"
            await pilot.pause()
            app.query_one("#sig-rsi_period", Input).value = "9"
            await pilot.click("#btn-save-signals")
            await pilot.pause()
            self.assertEqual(app.signals.rsi_period, 9)

    async def test_invalid_edit_is_refused_with_a_message(self) -> None:
        """An inverted fast/slow pair must not be saved."""
        from textual.widgets import Input, TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-signals"
            await pilot.pause()
            app.query_one("#sig-sma_fast", Input).value = "200"
            await pilot.click("#btn-save-signals")
            await pilot.pause()
            status = text_of(app, "#signals-status")
            self.assertIn("shorter than", status)
            self.assertNotEqual(app.signals.sma_fast, 200)

    async def test_reset_restores_shipped_values(self) -> None:
        """Reset is the recovery path from a mangled signal set."""
        from textual.widgets import Input, TabbedContent
        from soltui.signals import SignalDefaults

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-signals"
            await pilot.pause()
            app.query_one("#sig-rsi_period", Input).value = "3"
            await pilot.click("#btn-reset-signals")
            await pilot.pause()
            self.assertEqual(
                app.query_one("#sig-rsi_period", Input).value,
                str(SignalDefaults().rsi_period),
            )

    async def test_added_strategy_picks_up_edited_signal_defaults(self) -> None:
        """The whole point: editing a signal changes the strategy that uses it."""
        from textual.widgets import TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.signals.rsi_period = 9
            app.roster.clear()
            from soltui.signals import merged_params

            entry = app.roster.add("rsi", **merged_params("rsi", app.signals))
            self.assertEqual(entry.params["period"], 9)
            self.assertIn("rsi_9", entry.label)


class TestDocsTab(unittest.IsolatedAsyncioTestCase):
    """The click-to-open bug: a row cursor move must load the viewer.

    `DataTable.RowSelected` (Enter) was previously the only wired event, and
    the table never set `cursor_type = "row"` -- so a mouse click moved a
    *cell* cursor and nothing opened. `move_cursor` is used here rather than
    `pilot.click` on a table cell because it is what a click, an arrow key,
    and the "o" binding all ultimately act on: the row cursor position.
    """

    async def test_table_uses_row_cursor_not_cell(self) -> None:
        """Without this, a click never fires RowHighlighted at all."""
        from textual.widgets import DataTable, TabbedContent

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            self.assertEqual(
                app.query_one("#docs-table", DataTable).cursor_type, "row")

    async def test_moving_the_row_cursor_opens_an_editable_file(self) -> None:
        """A click (which moves the cursor) must load the file, not just
        highlight a row and wait for a separate Enter press."""
        from textual.widgets import Button, DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]) == "soltui/config.py")
            table.move_cursor(row=row)
            await pilot.pause()

            self.assertEqual(app._docs_current_path, "soltui/config.py")
            view = app.query_one("#docs-view", TextArea)
            self.assertFalse(view.read_only)
            self.assertIn("Settings", view.text)
            self.assertFalse(app.query_one("#docs-save", Button).disabled)
            self.assertIn("editable", text_of(app, "#docs-view-status"))

    async def test_a_results_file_opens_read_only_with_save_disabled(self) -> None:
        """research/results/ is evidence; opening one must never look editable."""
        from textual.widgets import Button, DataTable, Input, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            app.query_one("#docs-filter", Input).value = "research/results/"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            self.assertGreater(table.row_count, 0)
            # The filter also matches a summary that merely *mentions* the
            # path, so pick the row that is actually under the prefix rather
            # than trusting row 0.
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]).startswith("research/results/"))
            table.move_cursor(row=row)
            await pilot.pause()

            self.assertTrue(app.query_one("#docs-view", TextArea).read_only)
            self.assertTrue(app.query_one("#docs-save", Button).disabled)
            self.assertIn("read-only", text_of(app, "#docs-view-status"))

    async def test_o_binding_opens_the_highlighted_row(self) -> None:
        """The explicit fallback for when a click's RowHighlighted doesn't
        land through the browser-rendered terminal (textual-serve)."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]) == "soltui/config.py")
            table.move_cursor(row=row)
            await pilot.pause()
            app.query_one("#docs-view", TextArea).text = ""  # prove "o" reloads it

            await pilot.press("o")
            await pilot.pause()

            self.assertIn("Settings", app.query_one("#docs-view", TextArea).text)

    async def test_read_only_file_rejects_keystrokes(self) -> None:
        """`read_only` is the actual policy enforcement for research/results/
        -- a widget that accepted the flag but ignored it would still pass
        the "looks read-only" assertions above, so this checks behavior."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]).startswith("research/results/"))
            table.move_cursor(row=row)
            await pilot.pause()
            view = app.query_one("#docs-view", TextArea)
            before = view.text

            view.focus()
            await pilot.press("x")
            await pilot.pause()

            self.assertEqual(view.text, before)

    async def test_passive_navigation_never_discards_an_unsaved_edit(self) -> None:
        """The bug report: editing, then moving to another row, silently lost
        the edit. Navigating (RowHighlighted) must refuse; an explicit Enter
        on the new row is what is allowed to discard it."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            row_a = next(i for i in range(table.row_count)
                         if str(table.get_row_at(i)[0]) == "soltui/config.py")
            row_b = next(i for i in range(table.row_count)
                         if str(table.get_row_at(i)[0]) == "soltui/roster.py")
            table.focus()  # Enter later must route to the table, not elsewhere
            table.move_cursor(row=row_a)
            await pilot.pause()
            view = app.query_one("#docs-view", TextArea)
            view.text = "EDITED, NOT SAVED\n" + view.text
            await pilot.pause()
            self.assertIn("unsaved", text_of(app, "#docs-view-status"))

            table.move_cursor(row=row_b)
            await pilot.pause()

            self.assertEqual(app._docs_current_path, "soltui/config.py")
            self.assertIn("EDITED, NOT SAVED", view.text)
            self.assertIn("unsaved changes", text_of(app, "#docs-view-status"))

            # Cursor is already on row_b; Enter is the deliberate-open action
            # and may discard where the RowHighlighted move just refused to.
            await pilot.press("enter")
            await pilot.pause()

            self.assertEqual(app._docs_current_path, "soltui/roster.py")
            self.assertNotIn("EDITED, NOT SAVED", view.text)

    async def test_editor_panel_is_visible_from_a_different_tab(self) -> None:
        """The whole point of moving it out of _docs_pane: it must still be
        on screen after switching away from Docs."""
        from textual.widgets import DataTable, TabbedContent, TextArea

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-docs"
            await pilot.pause()
            table = app.query_one("#docs-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[0]) == "soltui/config.py")
            table.move_cursor(row=row)
            await pilot.pause()

            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()

            view = app.query_one("#docs-view", TextArea)
            self.assertIn("Settings", view.text)
            self.assertTrue(app.query_one("#editor-panel").display)

    async def test_ctrl_s_saves_from_any_tab(self) -> None:
        """`ctrl+s` is an App-level binding precisely so it works without
        switching to Docs first. Uses a temp-repo fixture (see
        `test_docs_browser.py`'s `WriteDocumentTests`) rather than a real
        tracked file, so a save actually lands on disk somewhere throwaway.
        """
        from pathlib import Path
        from unittest import mock
        from tempfile import TemporaryDirectory
        from textual.widgets import TabbedContent, TextArea

        from soltui import docs_browser

        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            target = repo / "scratch.py"
            target.write_text("original\n", encoding="utf-8")
            entries = [docs_browser.DocEntry(
                path="scratch.py", name="scratch.py", directory="",
                kind="code-python", summary="", summary_source="none",
                lines=1, size=9,
            )]

            app = SolTuiApp(make_settings())
            async with app.run_test(size=TEST_SIZE) as pilot:
                # Let the real Docs-tab table's mount-time RowHighlighted
                # (against the real catalogue) drain before swapping
                # `self._docs` out from under it below.
                await pilot.pause()
                with mock.patch.object(docs_browser, "REPO", repo):
                    app._docs = entries
                    app._open_doc("scratch.py")
                    await pilot.pause()

                    app.query_one(TabbedContent).active = "tab-strategies"
                    await pilot.pause()
                    view = app.query_one("#docs-view", TextArea)
                    view.text = "edited\n"
                    await pilot.pause()

                    await pilot.press("ctrl+s")
                    await pilot.pause()

                    self.assertIn("saved", text_of(app, "#docs-view-status"))
                    self.assertEqual(target.read_text(encoding="utf-8"), "edited\n")

    async def test_ctrl_e_toggles_the_editor_panel(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            panel = app.query_one("#editor-panel")
            self.assertTrue(panel.display)

            await pilot.press("ctrl+e")
            await pilot.pause()
            self.assertFalse(panel.display)

            await pilot.press("ctrl+e")
            await pilot.pause()
            self.assertTrue(panel.display)


class TestTop5Tab(unittest.IsolatedAsyncioTestCase):
    """The recommended-configurations tab: evidence shown, re-test wired."""

    async def _open(self, app, pilot):
        from textual.widgets import TabbedContent
        app.query_one(TabbedContent).active = "tab-top5"
        await pilot.pause()

    async def test_shows_five_configs_and_their_transfers(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await self._open(app, pilot)
            table = app.query_one("#top5-table", DataTable)
            self.assertEqual(table.row_count, 5)
            # Rank 1's published SOL Sharpe, straight from the evidence file.
            self.assertEqual(str(table.get_row_at(0)[4]), "+1.345")
            transfers = app.query_one("#top5-transfers", DataTable)
            self.assertEqual(transfers.row_count, 10)  # 5 configs x DOGE, ZEC

    async def test_warning_names_the_pbo_finding_not_sharpe_rank(self) -> None:
        """The tab must carry the study's own caveat: selection is by
        robustness checks, because ranking by Sharpe selects noise."""
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await self._open(app, pilot)
            hints = " ".join(str(getattr(w, "content", "") or
                                 getattr(w, "renderable", ""))
                             for w in app.query(".hint"))
            self.assertIn("0.700", hints)
            self.assertIn("NOT by Sharpe", hints)
            self.assertIn("buy_and_hold", hints)

    async def test_add_all_puts_the_five_member_signals_in_the_roster(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await self._open(app, pilot)
            app.roster.clear()
            await pilot.click("#top5-add-all")
            await pilot.pause()
            names = {e.name for e in app.roster}
            self.assertEqual(names, {"dual_momentum", "vol_regime",
                                     "hurst_switch", "ou_reversion",
                                     "obv_trend"})
            self.assertIn("added", text_of(app, "#top5-status"))

    async def test_add_all_twice_reports_instead_of_erroring(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await self._open(app, pilot)
            app.roster.clear()
            await pilot.click("#top5-add-all")
            await pilot.pause()
            await pilot.click("#top5-add-all")
            await pilot.pause()
            self.assertIn("already in roster", text_of(app, "#top5-status"))

    async def test_add_selected_adds_only_that_configs_members(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await self._open(app, pilot)
            app.roster.clear()
            table = app.query_one("#top5-table", DataTable)
            row = next(i for i in range(table.row_count)
                       if str(table.get_row_at(i)[1]) == "obv_trend_60")
            table.move_cursor(row=row)
            await pilot.click("#top5-add-selected")
            await pilot.pause()
            self.assertEqual({e.name for e in app.roster}, {"obv_trend"})

    async def test_missing_evidence_file_reports_the_command(self) -> None:
        from unittest import mock
        from pathlib import Path

        from soltui import top5 as top5_mod

        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            with mock.patch.object(top5_mod, "TOP5_CSV",
                                   Path("/nonexistent/top5.csv")):
                await self._open(app, pilot)
            headline = text_of(app, "#top5-headline")
            self.assertIn("--top5", headline)
            self.assertEqual(
                app.query_one("#top5-table", DataTable).row_count, 0)


class _VimHarness(App):
    """A bare app around one `VimTextArea` -- exercising the widget directly
    is both faster and more precise than mounting the full `SolTuiApp` (nine
    tabs, the ~270-row Docs catalogue) for every motion/mode assertion."""

    def __init__(self, text: str = "", *, read_only: bool = False,
                 on_save=None) -> None:
        super().__init__()
        self._text = text
        self._read_only = read_only
        self._on_save = on_save

    def compose(self) -> ComposeResult:
        from soltui.tui import VimTextArea
        yield VimTextArea(self._text, id="ta", read_only=self._read_only,
                          on_save=self._on_save)


class TestVimTextArea(unittest.IsolatedAsyncioTestCase):
    """The subset documented on `VimTextArea` itself."""

    async def test_starts_in_normal_mode(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("hello")
        async with app.run_test() as pilot:
            await pilot.pause()
            ta = app.query_one("#ta", VimTextArea)
            self.assertIs(ta.vim_mode, VimTextArea.Mode.NORMAL)

    async def test_unbound_key_in_normal_mode_types_nothing(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("hello")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            await pilot.press("z")  # not bound to anything below
            await pilot.pause()
            self.assertEqual(ta.text, "hello")

    async def test_hjkl_move_the_cursor(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("ab\ncd")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 0))
            await pilot.press("l")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (0, 1))
            await pilot.press("j")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (1, 1))
            await pilot.press("h")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (1, 0))
            await pilot.press("k")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (0, 0))

    async def test_0_and_dollar_move_to_line_start_and_end(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("hello")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 2))
            await pilot.press("dollar_sign")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (0, 5))
            await pilot.press("0")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (0, 0))

    async def test_gg_and_G_move_to_document_start_and_end(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("one\ntwo\nthree")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            await pilot.press("G")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, ta.document.end)
            await pilot.press("g")
            await pilot.press("g")
            await pilot.pause()
            self.assertEqual(ta.cursor_location, (0, 0))

    async def test_i_enters_insert_and_types_before_cursor(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("bc")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 0))
            await pilot.press("i")
            await pilot.pause()
            self.assertIs(ta.vim_mode, VimTextArea.Mode.INSERT)
            await pilot.press("a")  # a literal "a", not the vim command now
            await pilot.pause()
            self.assertEqual(ta.text, "abc")

    async def test_a_enters_insert_after_cursor(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("ac")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 0))
            await pilot.press("a")
            await pilot.press("b")
            await pilot.pause()
            self.assertEqual(ta.text, "abc")

    async def test_o_opens_a_line_below_and_enters_insert(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("first")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            await pilot.press("o")
            await pilot.pause()
            self.assertIs(ta.vim_mode, VimTextArea.Mode.INSERT)
            await pilot.press("s", "e", "c", "o", "n", "d")
            await pilot.pause()
            self.assertEqual(ta.text, "first\nsecond")

    async def test_escape_returns_to_normal_mode(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("x")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            await pilot.press("i")
            await pilot.pause()
            self.assertIs(ta.vim_mode, VimTextArea.Mode.INSERT)
            await pilot.press("escape")
            await pilot.pause()
            self.assertIs(ta.vim_mode, VimTextArea.Mode.NORMAL)
            # Back in NORMAL, "x" is delete-char-under-cursor, not a letter.
            await pilot.press("x")
            await pilot.pause()
            self.assertEqual(ta.text, "")

    async def test_x_deletes_the_character_under_the_cursor(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("abc")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 0))
            await pilot.press("x")
            await pilot.pause()
            self.assertEqual(ta.text, "bc")

    async def test_dd_deletes_the_current_line(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("one\ntwo\nthree")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((1, 0))  # "two"
            await pilot.press("d")
            await pilot.press("d")
            await pilot.pause()
            self.assertEqual(ta.text, "one\nthree")

    async def test_mismatched_pending_key_is_dropped_not_misapplied(self) -> None:
        """"g" then "x" (not "gg") must not delete or move unexpectedly --
        the documented simplification is to drop it, never guess."""
        from soltui.tui import VimTextArea

        app = _VimHarness("abc")
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            ta.move_cursor((0, 0))
            await pilot.press("g")
            await pilot.press("x")
            await pilot.pause()
            self.assertEqual(ta.text, "abc")

    async def test_colon_w_calls_the_save_callback(self) -> None:
        from soltui.tui import VimTextArea

        saved = []
        app = _VimHarness("abc", on_save=lambda: saved.append(True))
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            await pilot.press("colon")
            await pilot.press("w")
            await pilot.press("enter")
            await pilot.pause()
            self.assertEqual(saved, [True])

    async def test_read_only_refuses_to_enter_insert_mode(self) -> None:
        from soltui.tui import VimTextArea

        app = _VimHarness("abc", read_only=True)
        async with app.run_test() as pilot:
            ta = app.query_one("#ta", VimTextArea)
            ta.focus()
            for key in ("i", "a", "o"):
                await pilot.press(key)
                await pilot.pause()
                self.assertIs(ta.vim_mode, VimTextArea.Mode.NORMAL)
            self.assertEqual(ta.text, "abc")


if __name__ == "__main__":
    unittest.main(verbosity=2)

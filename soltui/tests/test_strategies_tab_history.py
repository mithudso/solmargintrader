"""The Strategies tab as a user sees it: history columns and the three Backtest buttons."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from textual.widgets import DataTable, TabbedContent

from soltui import bgcontrol, bgqueue
from soltui.tests.test_strategy_history import row
from soltui.tests.test_tui import TEST_SIZE, make_settings, offline_console_reads, text_of
from soltui.tui import SolTuiApp


def cells(app, name: str) -> dict[str, str]:
    table = app.query_one("#available-table", DataTable)
    index = table.get_row_index(name)
    return {str(c.label): str(table.get_row_at(index)[i]) for i, c in enumerate(table.ordered_columns)}


class StrategiesTabHistory(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.enterContext(offline_console_reads())
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.results = Path(tmp.name) / "results.jsonl"
        for target, value in (("RESULTS_PATH", self.results), ("STATE_PATH", Path(tmp.name) / "s.json")):
            patcher = mock.patch.object(bgqueue, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_history_columns_show_tested_untested_count_date_and_result(self) -> None:
        bgqueue.append_result(row("a", strategy="rsi", sharpe=0.42, finished_at=1_700_000_000.0), self.results)
        bgqueue.append_result(row("b", strategy="rsi", horizon="long"), self.results)
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            rsi, dca = cells(app, "rsi"), cells(app, "dca")
        self.assertEqual(rsi["tested"], "yes")
        self.assertEqual(rsi["times tested"], "2")
        self.assertRegex(rsi["last tested"], r"^\d{4}-\d\d-\d\d \d\d:\d\d$")
        self.assertIn("Sharpe +0.42", rsi["card-preset result"])
        self.assertEqual(dca["tested"], "no")
        self.assertEqual(dca["card-preset result"], "not tested")

    async def test_backtest_selected_runs_only_the_highlighted_strategy(self) -> None:
        app = SolTuiApp(make_settings())
        with mock.patch.object(bgcontrol, "start") as start:
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-strategies"
                await pilot.pause()
                table = app.query_one("#available-table", DataTable)
                table.move_cursor(row=table.get_row_index("dca"))
                await pilot.pause()
                await pilot.click("#btn-bt-selected")
                await pilot.pause()
                status = text_of(app, "#history-status")
        self.assertEqual(start.call_args.kwargs["strategies"], ["dca"])
        self.assertIn("started", status)

    async def test_backtest_untested_and_all_pass_their_scope(self) -> None:
        bgqueue.append_result(row("a", strategy="rsi"), self.results)
        app = SolTuiApp(make_settings())
        with mock.patch.object(bgcontrol, "start") as start:
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-strategies"
                await pilot.pause()
                await pilot.click("#btn-bt-untested")
                await pilot.pause()
                untested = start.call_args.kwargs["strategies"]
                await pilot.click("#btn-bt-all")
                await pilot.pause()
                everything = start.call_args.kwargs["strategies"]
        self.assertNotIn("rsi", untested)
        self.assertIn("rsi", everything)
        self.assertGreater(len(everything), len(untested))

    async def test_a_running_sweep_shows_the_reason_on_the_tab(self) -> None:
        app = SolTuiApp(make_settings())
        with mock.patch.object(bgcontrol, "start", side_effect=RuntimeError("a background sweep is already running")):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-strategies"
                await pilot.pause()
                await pilot.click("#btn-bt-all")
                await pilot.pause()
                status = text_of(app, "#history-status")
        self.assertIn("already running", status)

    async def test_new_results_appear_without_reopening_the_tab(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-strategies"
            await pilot.pause()
            self.assertEqual(cells(app, "rsi")["tested"], "no")
            bgqueue.append_result(row("a", strategy="rsi"), self.results)
            await pilot.pause(0.5)
            self.assertEqual(cells(app, "rsi")["tested"], "yes")


if __name__ == "__main__":
    unittest.main()

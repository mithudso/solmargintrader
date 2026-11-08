"""The Top 5 presets in three tabs, the P&L tab, and the "every percentage names its source" rule
across every table in the app. Driven through Textual's headless harness."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backtester.core.data import SyntheticLoader, frame_to_arrays
from textual.widgets import DataTable, Input, OptionList, Select, TabbedContent

from soltui import analyze as analyze_mod
from soltui import commands, presets
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp

SOURCE_WORDS = ("backtest", "paper", "dry-run", "live", "modelled", "reported", "wallet")


class Isolated(unittest.IsolatedAsyncioTestCase):
    """Temp state for everything the app reads outside the repo, and a synthetic price series."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="soltui-tui-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        df = SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d")
        env = {"AERO_LP_HOME": str(self.tmp / "aero"), "SOLTUI_LOG_DIR": str(self.tmp / "logs"),
               commands.JOURNAL_ENV: str(self.tmp / "none.json"),
               "SOLTUI_CONFIG_DIR": str(self.tmp / "config")}
        for patch in (mock.patch.dict(os.environ, env),
                      mock.patch.object(commands, "load_arrays", lambda s: frame_to_arrays(df)),
                      mock.patch.object(analyze_mod, "available_assets", lambda *a: [("SOL", "1d")])):
            patch.start()
            self.addCleanup(patch.stop)


class TestPresets(Isolated):
    async def test_all_three_tabs_list_the_five_presets(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            for tab in ("analyze", "live", "exec"):
                lst = app.query_one(f"#preset-{tab}", OptionList)
                self.assertEqual([lst.get_option_at_index(i).id for i in range(lst.option_count)],
                                 [f"top5:{r}" for r in range(1, 6)], tab)

    async def test_live_run_click_fills_the_strategy(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            lst = app.query_one("#preset-live", OptionList)
            lst.highlighted = 3
            lst.action_select()
            await pilot.pause()
            self.assertEqual(app.query_one("#live-run-strategy", Input).value, "obv_trend_60")
            self.assertIn("backtest median net", text_of(app, "#live-run-status"))

    async def test_execute_click_selects_the_preset_and_it_is_a_real_option(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            lst = app.query_one("#preset-exec", OptionList)
            lst.highlighted = 0
            lst.action_select()
            await pilot.pause()
            self.assertEqual(app.query_one("#exec-strategy", Select).value, "top5:1")
            self.assertIn("all(dual_momentum+vol_regime)", text_of(app, "#exec-summary"))

    async def test_execute_runs_a_preset_through_paper_start(self) -> None:
        app = SolTuiApp(make_settings())
        df = SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d")
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-execute"
            await pilot.pause()
            lst = app.query_one("#preset-exec", OptionList)
            lst.highlighted = 3
            lst.action_select()
            with mock.patch.object(presets, "load_preset_arrays", lambda p, d="data": frame_to_arrays(df)):
                await pilot.click("#btn-paper-start")
                await pilot.pause(1.0)
            self.assertRegex(text_of(app, "#exec-summary"), r"paper net [+-]\d")

    async def test_analyze_click_selects_the_coin_and_marks_the_preset(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            lst = app.query_one("#preset-analyze", OptionList)
            lst.highlighted = 1
            lst.action_select()
            await pilot.pause()
            self.assertEqual(app._analyze_preset, "top5:2")
            self.assertEqual(app.query_one("#analyze-asset", Select).value, "SOL|1d")
            self.assertIn("any(hurst_switch+ou_reversion)", text_of(app, "#analyze-preset-note"))

    async def test_a_preset_whose_series_is_not_cached_says_so(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app._analyze_values = {"ETH|1d"}
            lst = app.query_one("#preset-analyze", OptionList)
            lst.highlighted = 0
            lst.action_select()
            await pilot.pause()
            self.assertEqual(app._analyze_preset, "")
            self.assertIn("not cached", text_of(app, "#analyze-preset-note"))

    async def test_no_evidence_file_leaves_a_reason_not_a_blank(self) -> None:
        from soltui import top5
        with mock.patch.object(top5, "TOP5_CSV", Path("/nonexistent/top5.csv")):
            app = SolTuiApp(make_settings())
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                self.assertIn("--top5", text_of(app, "#preset-live-empty"))


class TestPnlTab(Isolated):
    async def _compute(self, app, pilot, window="all"):
        app.query_one(TabbedContent).active = "tab-pnl"
        await pilot.pause(2.0)   # first open computes; the roster backtests run in a worker thread
        return app

    async def test_first_open_computes_and_fills_every_table(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one("#pnl-window", Select).value = "all"
            await self._compute(app, pilot)
            self.assertEqual(app.query_one("#pnl-strategies", DataTable).row_count, 4)
            self.assertEqual(app.query_one("#pnl-assets", DataTable).row_count, 1)
            self.assertGreater(app.query_one("#pnl-daily", DataTable).row_count, 100)
            summary = text_of(app, "#pnl-summary")
            self.assertIn("backtest (simulated)", summary)
            self.assertIn("never summed", summary)
            self.assertRegex(summary, r"backtest net [+-]\d")

    async def test_window_with_no_backtest_data_explains_itself(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one("#pnl-window", Select).value = "24h"
            await self._compute(app, pilot)
            self.assertIn("its data covers", text_of(app, "#pnl-summary"))
            self.assertEqual(app.query_one("#pnl-strategies", DataTable).row_count, 0)

    async def test_a_bad_custom_date_is_reported_in_the_status_line(self) -> None:
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one("#pnl-start", Input).value = "not-a-date"
            app._pnl_loaded = True
            app.query_one(TabbedContent).active = "tab-pnl"
            await pilot.pause()
            app._pnl_run()
            await pilot.pause(1.0)
            self.assertIn("could not read", text_of(app, "#pnl-status"))


class TestEveryPercentageNamesItsSource(Isolated):
    """A bare percentage reads as real money. Walk every table in every opened tab."""

    async def test_no_table_renders_an_unlabelled_percentage(self) -> None:
        home = self.tmp / "aero"
        home.mkdir()
        (home / "status.json").write_text(json.dumps({
            "schema": "aero-lp-status/1", "mode": "dry-run", "generated_at": 1_790_000_000,
            "positions": [{"pair": "A/B", "pnl_usd": 1.0, "deposited_usd": 40.0, "apr_realized": 3.0}]}))
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one("#pnl-window", Select).value = "all"
            for tab in ("tab-top5", "tab-cumulative", "tab-queue", "tab-liquidity", "tab-pnl"):
                app.query_one(TabbedContent).active = tab
                await pilot.pause(1.5 if tab == "tab-pnl" else 0.3)
            checked = 0
            for table in app.query(DataTable):
                if table.id in ("signals-table", "families-table", "docs-table") or str(table.id).startswith("research"):
                    continue    # reference text, not results
                for i, col in enumerate(table.ordered_columns):
                    header = str(col.label).casefold()
                    cells = [str(table.get_row_at(r)[i]) for r in range(table.row_count)]
                    if table.id == "available-table" and header == "strategy":
                        # Titles such as "1 Year Active Supply %" name indicators,
                        # rather than report a return. Pin them to actual card
                        # labels; every result column still needs its source label.
                        from backtester.core.strategy_cards import load_all

                        labels = {card.registry_key or card.name for card in load_all().values()}
                        self.assertTrue(set(cells) <= labels)
                        continue
                    if not any("%" in c for c in cells) or header == "% paths +":
                        continue
                    checked += 1
                    for cell in cells:
                        if "%" in cell:
                            self.assertTrue(
                                any(w in header or w in cell.casefold() for w in SOURCE_WORDS),
                                f"{table.id}: column {header!r} shows {cell!r} with no source word")
            self.assertGreaterEqual(checked, 5)
            text = text_of(app, "#pnl-summary")
            for line in text.splitlines():
                if "%" in line and not line.strip().startswith("note"):
                    self.assertRegex(line, r"backtest|paper|dry-run|live LP", line)


if __name__ == "__main__":
    unittest.main()

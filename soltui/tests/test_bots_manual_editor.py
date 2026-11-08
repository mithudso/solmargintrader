"""Manual bot settings remain scoped, editable and unsaved until Apply."""
import unittest
from unittest import mock

from textual.widgets import Input, Select, TabbedContent

from soltui import bots
from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import BotSettingsScreen, SolTuiApp


def envelope(value):
    return {"ok": True, "result": value, "error": None}


class BotManualEditorTests(unittest.IsolatedAsyncioTestCase):
    async def test_scope_edits_defaults_and_cancel_are_not_saved(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_selected, app._bots_coins = ["SOL"], ["SOL", "BTC"]
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "bots.config":
                    values = dict(bots.DEFAULTS[params["bot"]])
                    if params.get("asset") == "BTC":
                        values["range_pct"] = 23.0
                    return envelope({"bot": params["bot"], "config": values,
                                     "defaults": dict(bots.DEFAULTS[params["bot"]])})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call), mock.patch.object(app, "_bots_job") as job:
                app._bots_edit_settings()
                await pilot.pause()
                screen = app.screen
                self.assertIsInstance(screen, BotSettingsScreen)
                self.assertEqual(screen.query_one("#bot-settings-asset", Select).value, "SOL")
                self.assertEqual(screen.query_one("#bot-setting-spacing", Select).value, "geom")
                self.assertEqual(set(screen.current), set(bots.DEFAULTS["grid"]))
                screen.query_one("#bot-setting-rungs", Input).value = "11"
                screen.query_one("#bot-settings-asset", Select).value = "BTC"
                await pilot.pause()
                self.assertEqual(screen.query_one("#bot-setting-range_pct", Input).value, "23.0")
                screen._defaults()
                self.assertEqual(screen.query_one("#bot-setting-range_pct", Input).value, "15.0")
                screen.query_one("#bot-settings-asset", Select).value = "SOL"
                await pilot.pause()
                self.assertEqual(screen.query_one("#bot-setting-rungs", Input).value, "11")
                screen.action_cancel()
                await pilot.pause()
                job.assert_not_called()

    async def test_apply_only_changed_fields_to_selected_coin_and_switch_bot(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_selected, app._bots_coins = ["SOL"], ["SOL", "BTC"]
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "bots.config":
                    values = dict(bots.DEFAULTS[params["bot"]])
                    return envelope({"bot": params["bot"], "config": values, "defaults": dict(values)})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call), mock.patch.object(app, "_bots_job") as job:
                app._bots_edit_settings()
                await pilot.pause()
                screen = app.screen
                screen.query_one("#bot-setting-spacing", Select).value = "arith"
                screen.query_one("#bot-setting-rungs", Input).value = "9"
                screen._apply()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "grid", "asset": "SOL",
                                            "values": {"rungs": 9, "spacing": "arith"}}, "saving settings")
                job.reset_mock()
                app._bots_bot = "dca"
                app._bots_edit_settings()
                await pilot.pause()
                screen = app.screen
                self.assertEqual(set(screen.current), set(bots.DEFAULTS["dca"]))
                screen._apply()
                await pilot.pause()
                job.assert_not_called()

    async def test_defaults_apply_to_coin_and_triangle_fields_are_exposed(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_selected, app._bots_coins = ["BTC"], ["BTC"]
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "bots.config":
                    defaults = dict(bots.DEFAULTS[params["bot"]])
                    values = dict(defaults)
                    if params["bot"] == "grid":
                        values["range_pct"] = 23.0
                    return envelope({"bot": params["bot"], "config": values, "defaults": defaults})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call), mock.patch.object(app, "_bots_job") as job:
                app._bots_edit_settings()
                await pilot.pause()
                app.screen._defaults()
                app.screen._apply()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "grid", "asset": "BTC",
                                            "values": {"range_pct": 15.0}}, "saving settings")
                job.reset_mock()
                app._bots_bot = "triangle"
                app._bots_edit_settings()
                await pilot.pause()
                self.assertEqual(set(app.screen.current), set(bots.DEFAULTS["triangle"]))
                self.assertTrue(app.screen.query_one("#bot-setting-use_displayed_size", Select).value)
                self.assertEqual(app.screen.query_one("#bot-settings-asset", Select).value, "")
                app.screen.query_one("#bot-setting-use_displayed_size", Select).value = False
                app.screen._apply()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "triangle",
                                            "values": {"use_displayed_size": False}}, "saving settings")

    async def test_inherit_global_resets_only_selected_coin(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_selected, app._bots_coins = ["SOL"], ["SOL"]
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "bots.config":
                    return envelope({"bot": "grid", "config": dict(bots.DEFAULTS["grid"]),
                                     "defaults": dict(bots.DEFAULTS["grid"])})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call), mock.patch.object(app, "_bots_job") as job:
                app._bots_edit_settings()
                await pilot.pause()
                app.screen._inherit()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "grid", "asset": "SOL", "reset": True},
                                            "restoring global inheritance", "inherit-global")

    async def test_coin_optimize_results_show_decision_and_failure(self):
        from textual.widgets import DataTable, Static
        from soltui.bots_screens import OptimizeScreen
        from soltui.tui import GlossaryTable
        app = SolTuiApp(make_settings())
        verdict = {"saved": True, "changes": [{"setting": "rungs", "before": 7, "after": 9}],
                   "reason": "Passed holdout"}
        row = {"coin": "SOL", "data_source": "cached", "train_windows": 2, "test_windows": 1,
               "current_test_median": 0.01, "pick_test_median": 0.02, "pick_wins": 1, "pick_losses": 0,
               "verdict": verdict}
        report = {"bot": "grid", "run": 1, "candidates": 2, "train_cells": 2, "test_cells": 1,
                  "seconds": 1, "universe": "per coin", "coins_used": ["SOL"], "skipped": {"BTC": "no data"},
                  "verdict": {"saved": True, "changes": [], "reason": "1 coin-specific setting saved"},
                  "reports": {"SOL": {"verdict": verdict}}, "per_coin": [row], "table": []}
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_render_optimize(report)
            text = str(app.query_one("#bots-opt-verdict", Static).render())
            self.assertIn("global defaults unchanged", text)
            self.assertIn("BTC: no data", text)
            self.assertIn("rungs 7 → 9", str(app.query_one("#bots-opt-coins", DataTable).get_row_at(0)[7]))
            screen = OptimizeScreen("Grid", lambda: None, GlossaryTable)
            app.push_screen(screen)
            await pilot.pause()
            screen.show_result(report)
            text = str(screen.query_one("#opt-result", Static).render())
            self.assertIn("SOL: saved rungs 7 -> 9", text)
            self.assertIn("BTC (no data)", text)

    async def test_mode_only_changes_preserve_values_and_can_return_to_auto(self):
        app = SolTuiApp(make_settings())
        modes = {"SOL": "auto"}
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-bots"
            await pilot.pause()
            app._bots_selected, app._bots_coins = ["SOL"], ["SOL"]
            original = app._call
            def call(name, params=None, **kwargs):
                if name == "bots.config":
                    cfg = dict(bots.DEFAULTS["grid"])
                    cfg["rungs"] = 9
                    return envelope({"bot": "grid", "config": cfg, "defaults": dict(bots.DEFAULTS["grid"]),
                                     "mode": modes["SOL"]})
                return original(name, params, **kwargs)
            with mock.patch.object(app, "_call", side_effect=call), mock.patch.object(app, "_bots_job") as job:
                app._bots_edit_settings()
                await pilot.pause()
                self.assertEqual(app.screen.query_one("#bot-settings-mode", Select).value, "auto")
                app.screen.query_one("#bot-settings-mode", Select).value = "manual"
                app.screen._apply()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "grid", "asset": "SOL", "mode": "manual"},
                                            "saving settings")
                job.reset_mock()
                modes["SOL"] = "manual"
                app._bots_edit_settings()
                await pilot.pause()
                self.assertEqual(app.screen.query_one("#bot-setting-rungs", Input).value, "9")
                app.screen.query_one("#bot-settings-mode", Select).value = "auto"
                app.screen._apply()
                await pilot.pause()
                job.assert_called_once_with("bots.save", {"bot": "grid", "asset": "SOL", "mode": "auto"},
                                            "saving settings")

    async def test_real_registry_persists_coin_values_and_manual_mode(self):
        import tempfile
        from pathlib import Path
        from soltui import config
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, "CONFIG_DIR", Path(tmp)):
            app = SolTuiApp(make_settings())
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one(TabbedContent).active = "tab-bots"
                await pilot.pause()
                app._bots_selected, app._bots_coins = ["SOL"], ["SOL"]
                app._bots_edit_settings()
                await pilot.pause()
                app.screen.query_one("#bot-setting-rungs", Input).value = "9"
                app.screen.query_one("#bot-settings-mode", Select).value = "manual"
                app.screen._apply()
                for _ in range(20):
                    await pilot.pause(.1)
                    if bots.get_config("grid", "SOL")["rungs"] == 9:
                        break
                self.assertEqual(bots.get_config("grid", "SOL")["rungs"], 9)
                self.assertEqual(bots.get_config("grid")["rungs"], bots.DEFAULTS["grid"]["rungs"])
                self.assertEqual(app._call("bots.config", {"bot": "grid", "asset": "SOL"})["result"]["mode"], "manual")

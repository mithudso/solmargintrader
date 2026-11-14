"""Dry Run executes the selected registered strategy, not the extension grid."""
from __future__ import annotations

import unittest
from unittest import mock

from backtester.core.data import SyntheticLoader, frame_to_arrays
from backtester.core.strategies import build
from soltui import live_run
from soltui.tests.test_tui import make_settings, offline_console_reads


class DryRunStrategyTests(unittest.TestCase):
    def test_chosen_strategy_runs_in_simulation_without_node(self):
        arrays = frame_to_arrays(SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d"))
        progress = []
        with mock.patch("soltui.runner.load_arrays", return_value=arrays), \
                mock.patch("backtester.core.strategies.build", wraps=build) as factory, \
                mock.patch("subprocess.run", side_effect=AssertionError("unexpected subprocess")):
            result = live_run.run_dryrun("rsi", settings=make_settings(), progress=progress.append)
        factory.assert_called_once_with("rsi")
        self.assertEqual(result["strategy"], "rsi")
        self.assertEqual(result["mode"], "historical simulation")
        self.assertIn("No live prices or orders", result["stdout"])
        self.assertTrue(any("Running rsi" in line for line in progress))

    def test_top5_preset_runs_the_composite_configuration(self):
        from soltui import presets
        arrays = frame_to_arrays(SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d"))
        with mock.patch.object(presets, "load_preset_arrays", return_value=arrays), \
                mock.patch.object(presets, "build_strategy", wraps=presets.build_strategy) as factory:
            result = live_run.run_dryrun("top5:1", settings=make_settings())
        self.assertEqual(factory.call_args.args[0]["value"], "top5:1")
        self.assertIn("Historical dry run: top5:1", result["stdout"])

    def test_gaps_use_only_latest_real_segment_and_explain_excluded_bars(self):
        arrays = frame_to_arrays(SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d"))
        arrays["ts"] = arrays["ts"].copy()
        arrays["ts"][100:] += 86400
        progress = []
        with mock.patch("soltui.runner.load_arrays", return_value=arrays):
            result = live_run.run_dryrun("rsi", settings=make_settings(), progress=progress.append)
        self.assertEqual(result["input_bars_total"], 300)
        self.assertEqual(result["bars_excluded_for_gaps"], 100)
        self.assertIn("excluded 100 earlier bars", result["stdout"])
        self.assertTrue(any("Price history has gaps" in line for line in progress))

    def test_unknown_name_fails_before_running(self):
        with self.assertRaisesRegex(ValueError, "Unknown strategy"):
            live_run.run_dryrun("definitely_unknown", settings=make_settings())

    def test_default_is_neutral_not_claimed_profitable(self):
        choice = live_run.get_best_strategy()
        self.assertEqual(choice["strategy"], "buy_and_hold")
        self.assertIn("not a recommendation", choice["details"])


class DryRunUiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(offline_console_reads())

    async def test_selected_strategy_runs_and_status_reopens(self):
        from textual.widgets import Select, TabbedContent, TextArea

        from soltui.tests.test_tui import TEST_SIZE
        from soltui.tui import SolTuiApp
        arrays = frame_to_arrays(SyntheticLoader(n_bars=300, seed=4).load("SOL", None, None, "1d"))
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-liverun"
            app.query_one("#live-run-choice", Select).value = "rsi"
            await pilot.pause()
            with mock.patch("soltui.runner.load_arrays", return_value=arrays):
                await pilot.click("#btn-spawn-dryrun")
                await pilot.pause(1.0)
            self.assertIn("Historical dry run: rsi", app.query_one("#live-run-output", TextArea).text)
            app._show_preview("other", "different content")
            await pilot.click("#status-live")
            await pilot.pause()
            view = app.query_one("#docs-view", TextArea)
            self.assertIn("Running rsi", view.text)
            self.assertIn("Historical dry run: rsi", view.text)

    async def test_start_and_status_are_visible_in_a_narrow_terminal(self):
        from textual.widgets import Button, TabbedContent

        from soltui.tui import SolTuiApp
        app = SolTuiApp(make_settings())
        async with app.run_test(size=(100, 45)) as pilot:
            await pilot.pause()
            app.query_one(TabbedContent).active = "tab-liverun"
            await pilot.pause()
            for name in ("#status-live", "#btn-spawn-dryrun"):
                button = app.query_one(name, Button)
                self.assertGreater(button.region.width, 0)
                self.assertLessEqual(button.region.right, 100)

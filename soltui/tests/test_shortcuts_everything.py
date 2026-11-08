"""Shortcut behavior without starting background jobs or paper experiments."""
import json
import unittest
from unittest import mock

from textual.widgets import DataTable, Input, Select, TabbedContent

from soltui.roster import available_strategies
from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import SolTuiApp


class ShortcutTests(unittest.IsolatedAsyncioTestCase):
    async def test_f8_copies_selected_ranked_row_without_starting_experiment(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            tabs = app.query_one("#main-tabs", TabbedContent)
            tabs.active = "tab-queue"
            await pilot.pause()
            table = app.query_one("#queue-table", DataTable)
            table.clear()
            name = available_strategies()[0][0]
            app._queue_ranked_rows = [{"strategy": name, "params": {"window": 17}, "asset": "BTC"}]
            table.add_row("Selected", "family", "1", "0", "100%", "1%", "50", key="0")
            table.focus()
            await pilot.pause()
            with mock.patch.object(app, "_call", wraps=app._call) as call, \
                 mock.patch.object(app, "_refresh_queue"), mock.patch.object(app, "_start_log") as log:
                await pilot.press("f8")
                await pilot.pause()
                self.assertEqual(tabs.active, "tab-paper-experiments", str(log.call_args))
                self.assertEqual(app.query_one("#paper-exp-strategy", Select).value, name)
                self.assertEqual(app.query_one("#paper-exp-asset", Input).value, "BTC")
                self.assertEqual(json.loads(app.query_one("#paper-exp-params", Input).value), {"window": 17})
                self.assertNotIn("paperexperiment.start", [c.args[0] for c in call.call_args_list])

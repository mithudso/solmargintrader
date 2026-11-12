"""Forward results retain the user's sort and selected trial during redraws."""
import unittest
from unittest import mock

from textual.widgets import DataTable, TabbedContent

from rich.text import Text

from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import SolTuiApp


def result(name, resolved):
    return {"id": name, "asset": "SOL", "label": name, "minutes": 5,
            "resolved": resolved, "correct": resolved, "pending": 0, "expired": 0,
            "changes": 0, "last_issued": None, "last_call": None, "last_outcome": None,
            "settings": [], "cost_bps": 1, "note": ""}


class ForwardSortRefreshTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        super().setUp()
        from soltui.tests.test_tui import offline_console_reads
        self.enterContext(offline_console_reads())

    @staticmethod
    def header(table, column_index):
        column = table.ordered_columns[column_index]
        table.post_message(DataTable.HeaderSelected(table, column.key, column_index, Text(str(column.label))))

    async def test_header_sort_and_selected_trial_survive_refresh(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            app.query_one(TabbedContent).active = "tab-forwardtest"
            await pilot.pause()
            table = app.query_one("#forward-table", DataTable)
            with mock.patch.object(app, "_forward_schedule"):
                app._forward_render([result("a", 2), result("b", 5), result("c", 1)])
                await pilot.pause()
                x = sum(c.get_render_width(table) for c in table.ordered_columns[:3]) + 1
                await pilot.click(table, offset=(x, 0))
                await pilot.pause()
                self.assertEqual([table.get_row_at(i)[3] for i in range(3)], [1, 2, 5])
                self.header(table, 3)
                await pilot.pause()
                self.assertEqual([table.get_row_at(i)[3] for i in range(3)], [5, 2, 1])
                table.move_cursor(row=table.get_row_index("a"))
                app._forward_render([result("c", 11), result("a", 7), result("d", 3)])
                self.assertEqual([table.get_row_at(i)[3] for i in range(3)], [11, 7, 3])
                self.assertEqual(app._strategy_table_key(table), "a")
                self.header(table, 3)
                await pilot.pause()
                self.assertEqual([table.get_row_at(i)[3] for i in range(3)], [3, 7, 11])
                app._forward_render([result("d", 20), result("a", 4), result("e", 10)])
                self.assertEqual([table.get_row_at(i)[3] for i in range(3)], [4, 10, 20])

"""Exports preserve displayed order, formatting, and existing files."""
import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Button

from soltui.csv_table import ExportPanel, ExportTable, export_table


class ExportApp(App):
    def compose(self) -> ComposeResult:
        yield ExportPanel(ExportTable(id="example"))


class ExportTests(unittest.IsolatedAsyncioTestCase):
    async def test_exports_sorted_rows_and_never_overwrites(self):
        with TemporaryDirectory() as directory:
            async with ExportApp().run_test() as pilot:
                table = pilot.app.query_one(ExportTable)
                table.add_column("name", key="name")
                table.add_column("value", key="value")
                table.add_row("z", Text("a,b"))
                table.add_row("a", "two\nlines")
                table.sort("name")
                first = export_table(table, Path(directory))
                second = export_table(table, Path(directory))
                self.assertNotEqual(first, second)
                with first.open(newline="") as handle:
                    self.assertEqual(list(csv.reader(handle)), [["name", "value"], ["a", "two\nlines"], ["z", "a,b"]])
                await pilot.pause()
                self.assertGreater(pilot.app.query_one(Button).region.width, 0)
                self.assertEqual(pilot.app.query_one(Button).region.height, 1)

    async def test_click_saves_to_downloads(self):
        from unittest.mock import patch

        with TemporaryDirectory() as directory:
            downloads = Path(directory) / "Downloads"
            downloads.mkdir()
            async with ExportApp().run_test() as pilot:
                table = pilot.app.query_one(ExportTable)
                table.add_columns("column")
                table.add_row("value")
                with patch("soltui.csv_table.Path.home", return_value=Path(directory)):
                    await pilot.click(".export-csv")
                    await pilot.pause()
                paths = list(downloads.glob("*.csv"))
                self.assertEqual(len(paths), 1)
                with paths[0].open(newline="") as handle:
                    self.assertEqual(list(csv.reader(handle)), [["column"], ["value"]])

    async def test_main_screen_wraps_every_table(self):
        from textual.widgets import DataTable
        from soltui.tests.test_tui import make_settings
        from soltui.tui import SolTuiApp

        app = SolTuiApp(settings=make_settings(), stream_prices=False)
        async with app.run_test(size=(180, 55)) as pilot:
            await pilot.pause()
            tables = list(app.query(DataTable))
            self.assertGreater(len(tables), 20)
            self.assertEqual([t.id for t in tables if not isinstance(t.parent, ExportPanel)], [])

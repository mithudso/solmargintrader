"""CSV export for Textual tables."""
from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable


def _plain(value: object) -> str:
    text = value.plain if isinstance(value, Text) else str(value) if value is not None else ""
    # CSV quoting cannot prevent spreadsheet formulas from untrusted display text.
    # Preserve signed numbers, including grouped values and percentages.
    numeric = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?"
    if text.lstrip().startswith(("=", "+", "-", "@")) and not re.fullmatch(numeric, text.strip()):
        return "'" + text
    return text


def export_table(table: DataTable, directory: Path | None = None) -> Path:
    """Save ordered displayed rows, escaping formula-like text and preserving prior exports."""
    directory = directory or Path.home() / "Downloads"
    stem = (table.id or "table") + "-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    for suffix in range(10000):
        path = directory / f"{stem}{'-' + str(suffix) if suffix else ''}.csv"
        try:
            handle = path.open("x", encoding="utf-8", newline="")
            break
        except FileExistsError:
            continue
    else:
        raise OSError("Could not choose a unique export filename")
    with handle:
        writer = csv.writer(handle)
        writer.writerow([_plain(column.label) for column in table.ordered_columns])
        for index in range(table.row_count):
            writer.writerow([_plain(value) for value in table.get_row_at(index)])
    return path


class ExportTable(DataTable):
    """DataTable marker for the shared export wrapper."""


class ExportPanel(Vertical):
    """Place an export control immediately above its table."""
    DEFAULT_CSS = """
    ExportPanel { height: 1fr; min-height: 4; }
    ExportPanel > Horizontal { height: 1; align-horizontal: right; }
    ExportPanel > Horizontal > Button { width: 15; min-width: 15; height: 1; min-height: 1; padding: 0; border: none; }
    ExportPanel > DataTable { height: 1fr; }
    """

    def __init__(self, table: DataTable) -> None:
        super().__init__()
        self.table = table

    def compose(self) -> ComposeResult:
        with Horizontal():
            button = Button("Export CSV", classes="export-csv")
            button.tooltip = "Save the displayed table rows and columns to a new CSV file in Downloads. Formula-like text is escaped; existing files are preserved."
            button.styles.border = ("none", "transparent")
            yield button
        yield self.table

    @on(Button.Pressed, ".export-csv")
    def export_csv(self, event: Button.Pressed) -> None:
        event.stop()
        try:
            path = export_table(self.table)
        except OSError as exc:
            self.notify(f"CSV export failed: {exc}", severity="error")
        else:
            self.notify(f"Exported CSV to {path}")

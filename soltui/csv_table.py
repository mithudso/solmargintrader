"""CSV export for Textual tables."""
from __future__ import annotations

import csv
import math
import re
from datetime import datetime
from pathlib import Path

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable


def _plain(value: object) -> str:
    return value.plain if isinstance(value, Text) else str(value) if value is not None else ""


def _spreadsheet_cell(value: object) -> str:
    """Neutralize spreadsheet formulas, including hidden leading controls.

    Plain finite decimal numbers keep their numeric meaning. Formula-like text
    gets a leading apostrophe in both headers and values.
    """
    text = _plain(value)
    numeric = bool(re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", text))
    if numeric:
        try:
            numeric = math.isfinite(float(text))
        except ValueError:
            numeric = False
    if (text and ord(text[0]) < 32) or (not numeric and text.lstrip(" \t\r\n\v\f\x00\ufeff").startswith(("=", "+", "-", "@"))):
        return "'" + text
    return text


def export_table(table: DataTable, directory: Path | None = None) -> Path:
    """Save the visible rows in their current order without overwriting a prior export."""
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
        writer.writerow([_spreadsheet_cell(column.label) for column in table.ordered_columns])
        for index in range(table.row_count):
            writer.writerow([_spreadsheet_cell(value) for value in table.get_row_at(index)])
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

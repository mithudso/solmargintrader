"""Interactive read-only Oracle workbench for the frozen ZEC winner universe."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Sparkline,
    Static,
    TextArea,
)

from research import zec_live as live
from research.zec_tui_model import LOOKBACKS, WorkingSet, default_path, label, row_key
from research.zec_tui_source import DataSession, QuoteReader, live_view
from research.zec_tui_workers import LatestWorker


class StrategyPicker(ModalScreen[set | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Cancel"), ("space", "toggle", "Toggle")]

    def __init__(self, choices, selected):
        super().__init__()
        self.choices = choices
        self.selected = set(selected)
        self.showing = []

    def compose(self) -> ComposeResult:
        with Vertical(id="picker-dialog"):
            yield Label(
                "Choose strategies · Space / Enter toggles a row",
                classes="dialog-title",
            )
            yield Input(
                placeholder="Search strategy, parameters or configuration ID",
                id="strategy-search",
            )
            yield DataTable(id="strategy-options", cursor_type="row")
            with Horizontal(classes="dialog-actions"):
                yield Button("Select visible", id="select-visible")
                yield Button("Clear visible", id="clear-visible")
                yield Button("Apply", id="apply-selection", variant="primary")
                yield Button("Cancel", id="cancel-selection")

    def on_mount(self):
        self.query_one("#strategy-options", DataTable).add_columns(
            "Show", "Strategy / parameters", "Mode", "Original .15%", "ID"
        )
        self.refresh_options()
        self.query_one("#strategy-search", Input).focus()

    @on(Input.Changed, "#strategy-search")
    def search(self, event):
        self.refresh_options(event.value)

    def refresh_options(self, search=""):
        table = self.query_one("#strategy-options", DataTable)
        table.clear()
        search = search.casefold()
        self.showing = [
            r
            for r in self.choices
            if search in (label(r) + live.canonical(r) + row_key(r)).casefold()
        ]
        for row in self.showing:
            identity = row_key(row)
            result = row["historical"].get("15", {}).get("return_pct")
            table.add_row(
                "[x]" if identity in self.selected else "[ ]",
                Text(label(row)),
                row["mode"],
                f"{result:+.3f}%" if result is not None else "—",
                row["candidate_id"],
                key=identity,
            )

    def action_toggle(self):
        table = self.query_one("#strategy-options", DataTable)
        if not table.row_count or not table.has_focus:
            return
        identity = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        if identity in self.selected:
            self.selected.remove(identity)
        else:
            self.selected.add(identity)
        table.update_cell_at(
            (table.cursor_row, 0), "[x]" if identity in self.selected else "[ ]"
        )

    @on(DataTable.RowSelected, "#strategy-options")
    def toggle_clicked(self):
        self.action_toggle()

    def action_cancel(self):
        self.dismiss(None)

    def on_button_pressed(self, event):
        identity = event.button.id
        if identity in ("select-visible", "clear-visible"):
            keys = {row_key(r) for r in self.showing}
            self.selected = (
                self.selected | keys
                if identity == "select-visible"
                else self.selected - keys
            )
            self.refresh_options(self.query_one("#strategy-search", Input).value)
        elif identity == "apply-selection":
            self.dismiss(self.selected)
        elif identity == "cancel-selection":
            self.dismiss(None)


class ConfigEditor(ModalScreen[tuple | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Cancel"), ("ctrl+s", "apply", "Apply")]

    def __init__(self, state, identity):
        super().__init__()
        self.state, self.identity = state, identity

    def compose(self) -> ComposeResult:
        original = self.state.originals[self.identity]
        with Vertical(id="editor-dialog"):
            yield Label(Text("Edit " + label(original)), classes="dialog-title")
            yield Static(
                "Changes are UNTESTED live variants. Original backtest returns stay with the original configuration."
            )
            if original["market"] != "spot_reference":
                yield Static(
                    "Reference policy only: editing its parameters does not add a directional adapter."
                )
            yield TextArea(
                json.dumps(self.state.editor_config(self.identity), indent=2),
                id="config-json",
                soft_wrap=False,
            )
            yield Static("", id="config-error")
            with Horizontal(classes="dialog-actions"):
                yield Button("Apply untested", id="apply-config", variant="primary")
                yield Button("Reset original", id="reset-config")
                yield Button("Cancel", id="cancel-config")

    def on_mount(self):
        self.query_one("#config-json", TextArea).focus()

    def action_cancel(self):
        self.dismiss(None)

    def action_apply(self):
        text = self.query_one("#config-json", TextArea).text
        try:
            self.state.edit(self.identity, text)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self.query_one("#config-error", Static).update(
                Text(str(exc), style="bold red")
            )
            return
        self.dismiss((self.identity, "apply"))

    def on_button_pressed(self, event):
        if event.button.id == "apply-config":
            self.action_apply()
        elif event.button.id == "reset-config":
            self.state.overrides.pop(self.identity, None)
            self.dismiss((self.identity, "reset"))
        elif event.button.id == "cancel-config":
            self.dismiss(None)


class OracleWinnersApp(App):
    TITLE = "ZEC Oracle · Strategy workbench"
    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("s", "choose", "Strategies"),
        ("e", "edit", "Edit"),
        ("r", "refresh_now", "Refresh"),
        ("ctrl+s", "save_view", "Save view"),
    ]
    CSS = """
    Screen { background: #0c1420; color: #dce7f3; }
    Header { background: #17283d; }
    .controls { height: 3; padding: 0 1; }
    .controls Label { width: auto; content-align: left middle; margin-right: 1; }
    Select { width: 17; margin-right: 1; }
    #timeframe { width: 11; }
    #lookback { width: 13; }
    #refresh-seconds { width: 8; margin-right: 1; }
    Button { min-width: 7; margin-right: 1; }
    #faster, #slower { min-width: 4; width: 4; }
    #market { height: 2; padding: 0 1; background: #132237; }
    #notice { height: 2; padding: 0 1; color: #a8c1dd; }
    #workspace { height: 1fr; padding: 0 1; }
    #left { width: 1fr; min-width: 40; }
    #shape { height: 5; border: round #2c637d; padding: 0 1; }
    #price-chart { height: 4; color: #68d7e3; }
    #chart-clock { height: 2; color: #a8c1dd; }
    #watchlist { height: 1fr; min-height: 7; }
    #focus-detail { height: 4; color: #a8c1dd; }
    #right { width: 36; margin-left: 1; border: round #2c637d; }
    #indicator-title { height: 2; text-style: bold; padding: 0 1; }
    #indicator-clock { height: 3; padding: 0 1; color: #a8c1dd; }
    #indicators { height: 1fr; min-height: 8; }
    .compact #workspace { layout: vertical; overflow-y: auto; }
    .compact #left { width: 1fr; height: 24; }
    .compact #right { width: 1fr; height: 23; margin: 1 0 0 0; }
    ModalScreen { align: center middle; background: #06101bd9; }
    #picker-dialog, #editor-dialog { width: 94%; height: 90%; background: #152338; border: thick #418aab; padding: 1; }
    .dialog-title { height: 2; text-style: bold; }
    .dialog-actions { height: 3; }
    #strategy-options, #config-json { height: 1fr; }
    #config-error { height: 3; color: #ffb3a7; }
    """

    def __init__(
        self,
        state=None,
        *,
        settings_path=None,
        data_loader=None,
        quote_loader=None,
        clock=time.time,
    ):
        super().__init__()
        self.state = state or WorkingSet()
        self.settings_path = Path(settings_path) if settings_path else default_path()
        self.clock = clock
        self.data_worker = LatestWorker(
            data_loader or DataSession(clock=clock), name="oracle-candles"
        )
        self.quote_worker = LatestWorker(
            quote_loader or QuoteReader(), name="oracle-quotes"
        )
        self.current_frame, self.quote_result = None, None
        self.row_order = []
        self.indicator_keys = []
        self.latest_rows = {}
        self.startup_warning = None
        self.focused_key = None
        self._display_stopping = False
        self._next_data = self._next_quote = 0.0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="controls"):
            yield Label("Bar window")
            yield Select(
                [(i, i) for i in live.STEPS],
                value=self.state.interval,
                allow_blank=False,
                id="timeframe",
            )
            yield Label("Study mode")
            yield Select(
                [
                    (m, m)
                    for m in (
                        "baseline",
                        "shape",
                        "frequency",
                        "all",
                        "shape_control",
                        "frequency_control",
                        "linear_control",
                    )
                ],
                value=self.state.mode,
                allow_blank=False,
                id="study-mode",
            )
            yield Label("Chart")
            yield Select(
                [(f"{n} bars", n) for n in LOOKBACKS],
                value=self.state.lookback,
                allow_blank=False,
                id="lookback",
            )
        with Horizontal(classes="controls"):
            yield Label("Signal refresh s")
            yield Input(str(self.state.refresh), id="refresh-seconds", type="number")
            yield Button("−", id="faster")
            yield Button("+", id="slower")
            yield Button("Apply", id="apply-refresh")
            yield Button("Choose strategies", id="choose-strategies")
        with Horizontal(classes="controls"):
            yield Button("Edit focused", id="edit-focused")
            yield Button("Reset focused", id="reset-focused")
            yield Button("Save view", id="save-view")
            yield Label("Live variants · read-only")
        yield Static("Connecting to existing ZEC/USD recorder…", id="market")
        yield Static(
            "Select a timeframe and choose the strategies you want to watch.",
            id="notice",
        )
        with Horizontal(id="workspace"):
            with Vertical(id="left"):
                yield Static("Shape: waiting for completed bars", id="shape")
                yield Sparkline([], id="price-chart")
                yield Static("", id="chart-clock")
                yield DataTable(id="watchlist", cursor_type="row")
                yield Static("", id="focus-detail")
            with VerticalScroll(id="right"):
                yield Label("Market indicators", id="indicator-title")
                yield Static("Completed trade candles", id="indicator-clock")
                yield DataTable(id="indicators", cursor_type="row")
        yield Footer()

    def on_mount(self):
        self.query_one("#watchlist", DataTable).add_columns(
            "Strategy / configuration",
            "Call",
            "Mode",
            "Net .25%",
            "Net .15%",
            "Evidence",
        )
        self.query_one("#indicators", DataTable).add_columns("Indicator", "Value")
        self.set_class(self.size.width < 110, "compact")
        self.request_data(clear=True)
        self.quote_worker.submit(None)
        self._poll_timer = self.set_interval(0.25, self.poll_workers)
        self.query_one("#watchlist", DataTable).focus()
        if self.startup_warning:
            self.notice(self.startup_warning)

    def on_resize(self, event):
        self.set_class(event.size.width < 110, "compact")

    def request_data(self, *, clear=False):
        if self._display_stopping:
            return
        if clear:
            self.current_frame = None
            self.paint_rows(self.state.visible())
            self.clear_details("Loading this window's completed candles…")
        self.data_worker.submit(
            {
                "interval": self.state.interval,
                "lookback": self.state.lookback,
                "rows": self.state.visible(),
            }
        )
        self._next_data = time.monotonic() + self.state.refresh

    def poll_workers(self):
        if self._display_stopping:
            return
        now = time.monotonic()
        # Drain before scheduling: submit deliberately supersedes unread output.
        # Reversing this order starves loaders slower than the refresh interval.
        completed = self.data_worker.poll()
        if completed is not None:
            if completed.error:
                self.current_frame = {
                    "interval": self.state.interval,
                    "rows": [
                        {
                            **w,
                            "status": "unavailable",
                            "direction": None,
                            "reason": "worker_failed",
                        }
                        for w in self.state.visible()
                    ],
                    "details": None,
                    "error": "calculation_or_feed_failed",
                }
                self.notice(
                    "Refresh failed; retrying within 15 seconds. Configurations were preserved."
                )
                self._next_data = now + 15
            else:
                self.current_frame = completed.value
                if self.current_frame.get("error"):
                    self._next_data = now + 15
        quoted = self.quote_worker.poll()
        if quoted is not None:
            self.quote_result = (
                quoted.value
                if not quoted.error
                else {"quote": None, "error": "quote_reader_failed"}
            )
        if now >= self._next_quote and not self.quote_worker.busy:
            self.quote_worker.submit(None)
            self._next_quote = now + 1
        if now >= self._next_data and not self.data_worker.busy:
            self.request_data()
        self.paint()

    def notice(self, text):
        self.query_one("#notice", Static).update(Text(text))

    def clear_details(self, message):
        self.query_one("#shape", Static).update(Text(message))
        self.query_one("#indicators", DataTable).clear()
        self.indicator_keys = []
        self.query_one("#indicator-clock", Static).update(
            "Indicators unavailable; awaiting valid completed candles."
        )
        self.query_one("#price-chart", Sparkline).data = []
        self.query_one("#chart-clock", Static).update(
            "Chart unavailable; awaiting valid completed candles."
        )

    def paint_rows(self, rows):
        table = self.query_one("#watchlist", DataTable)
        self.latest_rows = {row_key(row): row for row in rows}
        keys = [row_key(r) for r in rows]
        previous = self.focused_key
        cells = []
        for row in rows:
            value = row.get("historical", {}).get("15", {}).get("return_pct")
            higher_fee = row.get("historical", {}).get("25", {}).get("return_pct")
            direction = row.get("direction") or "N/A"
            style = (
                "green"
                if direction == "UP"
                else "red"
                if direction == "DOWN"
                else "cyan"
                if direction == "FLAT"
                else "yellow"
            )
            name = ("✎ " if row.get("edited") else "") + label(row)
            cells.append(
                (
                    Text(name),
                    Text(direction, style=style),
                    row["mode"],
                    f"{higher_fee:+.3f}%" if higher_fee is not None else "—",
                    f"{value:+.3f}%" if value is not None else "—",
                    "UNTESTED" if row.get("edited") else row.get("status", "loading"),
                )
            )
        if keys != self.row_order:
            table.clear()
            for identity, values in zip(keys, cells):
                table.add_row(*values, key=identity)
            self.row_order = keys
            self.focused_key = (
                previous if previous in keys else keys[0] if keys else None
            )
            if self.focused_key:
                table.move_cursor(row=keys.index(self.focused_key), animate=False)
        else:
            columns = list(table.columns)
            for identity, values in zip(keys, cells):
                for column, value in zip(columns, values):
                    table.update_cell(identity, column, value)
        self.update_focus()

    def update_focus(self):
        if self.focused_key in self.state.originals:
            row = self.state.effective(self.focused_key)
            evidence = (
                "UNTESTED edited parameters · original P&L not applied"
                if row.get("edited")
                else "Original one-day backtest selection · not forecast accuracy"
            )
            self.query_one("#focus-detail", Static).update(
                Text(
                    f"{label(row)}\n{row['candidate_id']} · {evidence}\n{self.latest_rows.get(self.focused_key, {}).get('reason') or self.latest_rows.get(self.focused_key, {}).get('status', 'loading')}"
                )
            )
        else:
            self.query_one("#focus-detail", Static).update(
                "No strategies selected in this view. Choose strategies to add some."
            )

    @on(DataTable.RowHighlighted, "#watchlist")
    def watch_row_highlighted(self, event):
        self.focused_key = event.row_key.value
        self.update_focus()

    def paint(self):
        quote = (self.quote_result or {}).get("quote")
        good = (
            quote
            and not (self.quote_result or {}).get("error")
            and 0 <= self.clock() - quote["observed_at"] <= 15
        )
        price = f"${quote['price']:.5f}" if good else "source unavailable / stale"
        self.query_one("#market", Static).update(
            Text(
                f"ZEC/USD  {price}   ·   next {self.state.interval} bar   ·   signal refresh {self.state.refresh:g}s\n{len(self.state.visible())} selected / {len(self.state.choices())} in this view · quote heartbeat 1s",
                style="bold",
            )
        )
        if not self.current_frame:
            return
        frame = live_view(self.current_frame, self.quote_result, self.clock())
        self.paint_rows(frame["rows"])
        details = frame.get("details")
        if not details:
            self.clear_details("Market data unavailable: " + str(frame.get("error")))
            return
        shape = details["shape"]
        position = shape.get("live_range_position", shape.get("range_position"))
        gauge = "—"
        if position is not None:
            slot = min(24, max(0, round(position * 24)))
            gauge = "─" * slot + "●" + "─" * (24 - slot) + f" {position:.0%}"
        age = shape.get("episode_age_bars", "—")
        position_source = (
            "Live quote" if "live_range_position" in shape else "Last close"
        )
        self.query_one("#shape", Static).update(
            Text(
                f"{shape['shape'].replace('_', ' ').upper()} · {shape.get('zone', 'unknown')} zone · episode {age} bars\n{position_source} in observed 48-bar range  {gauge}\n{shape.get('turn_phase', 'No fitted turn')} · not future completion",
                style="dim" if details["stale"] else "cyan",
            )
        )
        self.query_one("#price-chart", Sparkline).data = details["chart"]
        first = (
            live.iso(details["chart_start"])
            if details["chart_start"] is not None
            else "—"
        )
        self.query_one("#chart-clock", Static).update(
            Text(
                f"{len(details['chart'])} completed bars · {first} → {live.iso(details['asof'])}\n{details['contiguous_bars']} contiguous bars · {'RETAINED / STALE' if details['stale'] else 'current window'}"
            )
        )
        self.query_one("#indicator-clock", Static).update(
            Text(
                f"{self.state.interval} trade candles\nAs of {live.iso(details['asof'])}\n{'RETAINED / STALE' if details['stale'] else 'Market context only'}"
            )
        )
        table = self.query_one("#indicators", DataTable)
        names = [item["name"] for item in details["indicators"]]
        rebuild = names != self.indicator_keys
        if rebuild:
            table.clear()
            self.indicator_keys = names
        for item in details["indicators"]:
            value = item["value"]
            rendered = (
                "—"
                if value is None
                else Text(f"{value:,.5f}", style="dim" if details["stale"] else "white")
            )
            if rebuild:
                table.add_row(Text(item["name"]), rendered, key=item["name"])
            else:
                table.update_cell(item["name"], list(table.columns)[1], rendered)

    @on(Select.Changed)
    def changed_window(self, event):
        mapping = {
            "timeframe": "interval",
            "study-mode": "mode",
            "lookback": "lookback",
        }
        attribute = mapping.get(event.select.id)
        if (
            attribute
            and event.value != Select.BLANK
            and getattr(self.state, attribute) != event.value
        ):
            setattr(self.state, attribute, event.value)
            self.request_data(clear=True)
            self.notice(
                "View changed. Strategy bars, chart lookback and refresh cadence remain separate."
            )

    def apply_refresh(self, value):
        try:
            seconds = float(value)
            if not 0.2 <= seconds <= 300:
                raise ValueError()
        except ValueError:
            self.notice("Refresh must be a number from 0.2 through 300 seconds.")
            return
        self.state.refresh = seconds
        self.query_one("#refresh-seconds", Input).value = f"{seconds:g}"
        self._next_data = time.monotonic() + seconds
        self.notice(
            f"Signal refresh set to {seconds:g}s; forecast horizon remains {self.state.interval}."
        )

    @on(Input.Submitted, "#refresh-seconds")
    def refresh_submitted(self, event):
        self.apply_refresh(event.value)

    def action_choose(self):
        self.push_screen(
            StrategyPicker(self.state.choices(), self.state.selected),
            self.selected_changed,
        )

    def selected_changed(self, selected):
        if selected is not None:
            self.state.selected = selected
            self.request_data(clear=True)
            self.notice("Watchlist updated. Save view to keep it across restarts.")

    def action_edit(self):
        if self.focused_key in self.state.originals:
            self.push_screen(ConfigEditor(self.state, self.focused_key), self.edited)
        else:
            self.notice("Select a strategy row before editing.")

    def edited(self, result):
        if result:
            self.request_data(clear=True)
            self.notice(
                "Configuration updated. Edited parameters are untested; Save view keeps your variants."
            )

    def action_refresh_now(self):
        self.request_data()

    def action_save_view(self):
        try:
            self.state.save(self.settings_path)
        except (OSError, ValueError):
            self.notice(
                "Could not save view. Your live selections and edits remain in this session."
            )
        else:
            self.notice(
                "Saved timeframe, watchlist, refresh, chart window and edited variants."
            )

    def on_button_pressed(self, event):
        actions = {
            "choose-strategies": self.action_choose,
            "edit-focused": self.action_edit,
            "save-view": self.action_save_view,
        }
        if event.button.id in actions:
            actions[event.button.id]()
        elif event.button.id == "apply-refresh":
            self.apply_refresh(self.query_one("#refresh-seconds", Input).value)
        elif event.button.id in ("faster", "slower"):
            self.apply_refresh(
                str(
                    min(300, self.state.refresh + 1)
                    if event.button.id == "slower"
                    else max(0.2, self.state.refresh - 1)
                )
            )
        elif event.button.id == "reset-focused" and self.focused_key:
            self.state.overrides.pop(self.focused_key, None)
            self.request_data(clear=True)
            self.notice("Focused configuration reset to its immutable original.")

    def on_unmount(self):
        self._display_stopping = True
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()
        self.data_worker.close(0.1)
        self.quote_worker.close(0.1)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prices", type=Path)
    parser.add_argument("--settings", type=Path, default=default_path())
    parser.add_argument("--intervals", nargs="+", choices=live.STEPS)
    parser.add_argument("--modes", nargs="+", choices=(*live.MODES, "all"))
    parser.add_argument("--refresh", type=float)
    args = parser.parse_args(argv)
    state = WorkingSet()
    warning = None
    try:
        state.load(args.settings)
    except (OSError, ValueError, TypeError, KeyError):
        warning = "Saved preferences could not be loaded; using the original defaults. Existing file was preserved."
    if args.intervals:
        state.interval = args.intervals[0]
    if args.modes:
        state.mode = args.modes[0]
    if args.refresh is not None:
        if not 0.2 <= args.refresh <= 300:
            parser.error("refresh must be from 0.2 through 300 seconds")
        state.refresh = args.refresh
    app = OracleWinnersApp(
        state, settings_path=args.settings, quote_loader=QuoteReader(args.prices)
    )
    app.startup_warning = warning
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

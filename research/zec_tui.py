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
from textual.events import Click
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TextArea,
)

from research import zec_live as live
from research.zec_shape_view import shape_guide, shape_summary
from research.zec_tui_chart import MarketChart
from research.zec_tui_metrics import IndicatorSession
from research.zec_tui_model import LOOKBACKS, WorkingSet, default_path, label, row_key
from research.zec_tui_source import DataSession, QuoteReader, live_view
from research.zec_tui_stream import DisabledStream, TradeStream
from research.zec_tui_workers import LatestWorker


class IndicatorTable(DataTable):
    """A single mouse click plots a row, independent of cursor highlight."""

    class IndicatorClicked(Message):
        def __init__(self, name):
            super().__init__()
            self.name = name

    def on_click(self, event: Click):
        row = event.style.meta.get("row")
        if type(row) is not int or not 0 <= row < self.row_count:
            return
        # DataTable's normal mouse handler only selects an already highlighted
        # cell. Plotting must also work on the first click of a different row.
        event.prevent_default()
        event.stop()
        self.focus()
        self.move_cursor(row=row, animate=False)
        name = self.coordinate_to_cell_key(self.cursor_coordinate).row_key.value
        self.post_message(self.IndicatorClicked(name))


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


class ShapeGuide(ModalScreen[None]):
    BINDINGS: ClassVar = [("escape", "close", "Close guide")]

    def __init__(self, details, interval):
        super().__init__()
        self.details, self.interval = details, interval

    def compose(self) -> ComposeResult:
        with Vertical(id="shape-dialog"):
            yield Label(
                "Understand the observed shape · Esc to close", classes="dialog-title"
            )
            with VerticalScroll(id="shape-guide-scroll", can_focus=True):
                yield Static(
                    Text(shape_guide(self.details, self.interval)),
                    id="shape-guide-body",
                )
            yield Button("Close guide", id="close-shape-guide", variant="primary")

    def on_mount(self):
        self.update_details(self.details, self.interval)
        self.query_one("#shape-guide-scroll").focus()

    def update_details(self, details, interval):
        self.details, self.interval = details, interval
        width = self.query_one("#shape-guide-body").content_size.width - 13
        self.query_one("#shape-guide-body", Static).update(
            Text(shape_guide(details, interval, max(16, width)))
        )

    def action_close(self):
        self.dismiss(None)

    @on(Button.Pressed, "#close-shape-guide")
    def close_button(self, event):
        event.stop()
        self.action_close()


class OracleWinnersApp(App):
    TITLE = "ZEC Oracle · Strategy workbench"
    BINDINGS: ClassVar = [
        ("q", "quit", "Quit"),
        ("s", "choose", "Strategies"),
        ("e", "edit", "Edit"),
        ("h", "shape_guide", "Shape guide"),
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
    #refresh-seconds { width: 12; margin-right: 1; }
    Button { min-width: 7; margin-right: 1; }
    #faster, #slower { min-width: 4; width: 4; }
    #market { height: 2; padding: 0 1; background: #132237; }
    #notice { height: 2; padding: 0 1; color: #a8c1dd; }
    #workspace { height: 1fr; padding: 0 1; }
    #left { width: 1fr; min-width: 40; overflow-y: auto; }
    #shape { height: auto; min-height: 9; border: round #2c637d; padding: 0 1; }
    #price-chart { height: 8; color: #68d7e3; }
    #chart-clock { height: 2; color: #a8c1dd; }
    #watchlist { height: 1fr; min-height: 7; }
    #focus-detail { height: 4; color: #a8c1dd; }
    #right { width: 39; margin-left: 1; border: round #2c637d; }
    #indicator-title { height: 2; text-style: bold; padding: 0 1; }
    #indicator-clock { height: 4; padding: 0 1; color: #a8c1dd; }
    #indicator-hint { height: 2; padding: 0 1; color: #d5a8ed; }
    #two-bar { height: auto; min-height: 5; padding: 0 1; border-top: solid #2c637d; color: #c3d8ed; }
    #indicators { height: 1fr; min-height: 8; }
    .compact #workspace { layout: vertical; overflow-y: auto; }
    .compact #left { width: 1fr; height: 39; }
    .compact #right { width: 1fr; height: 33; margin: 1 0 0 0; }
    ModalScreen { align: center middle; background: #06101bd9; }
    #picker-dialog, #editor-dialog { width: 94%; height: 90%; background: #152338; border: thick #418aab; padding: 1; }
    .dialog-title { height: 2; text-style: bold; }
    .dialog-actions { height: 3; }
    #strategy-options, #config-json { height: 1fr; }
    #config-error { height: 3; color: #ffb3a7; }
    #shape-dialog { width: 94%; height: 92%; background: #152338; border: thick #418aab; padding: 1; }
    #shape-guide-scroll { height: 1fr; }
    #shape-guide-body { height: auto; }
    """

    def __init__(
        self,
        state=None,
        *,
        settings_path=None,
        data_loader=None,
        quote_loader=None,
        stream=None,
        indicator_loader=None,
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
        self.indicator_worker = LatestWorker(
            indicator_loader or IndicatorSession(clock=clock), name="oracle-indicators"
        )
        # Dependency-injected loaders must never secretly create a real network
        # subscription in tests or an embedding application.
        self.trade_stream = (
            stream
            if stream is not None
            else DisabledStream()
            if data_loader is not None or quote_loader is not None
            else TradeStream(clock=clock)
        )
        self.current_frame, self.quote_result = None, None
        self.indicator_frame = None
        self.selected_indicator = None
        self._view_generation = self._source_version = 0
        self._market_token = None
        self._indicator_request_key = None
        self._pending_force = self._pending_quote = False
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
            yield Label("Max refresh s")
            yield Input(str(self.state.refresh), id="refresh-seconds", type="number")
            yield Button("−", id="faster")
            yield Button("+", id="slower")
            yield Button("Apply", id="apply-refresh")
            yield Button("Choose strategies", id="choose-strategies")
        with Horizontal(classes="controls"):
            yield Button("Refresh now [R]", id="refresh-now", variant="primary")
            yield Button("Edit", id="edit-focused")
            yield Button("Reset", id="reset-focused")
            yield Button("Save", id="save-view")
            yield Button("Shape guide [H]", id="show-shape-guide")
        yield Static("Connecting to existing ZEC/USD recorder…", id="market")
        yield Static(
            "Select a timeframe and choose the strategies you want to watch.",
            id="notice",
        )
        with Horizontal(id="workspace"):
            with Vertical(id="left"):
                yield Static("Shape: waiting for completed bars", id="shape")
                yield MarketChart([], id="price-chart")
                yield Static("", id="chart-clock")
                yield DataTable(id="watchlist", cursor_type="row")
                yield Static("", id="focus-detail")
            with VerticalScroll(id="right"):
                yield Label("Market indicators", id="indicator-title")
                yield Static("Completed trade candles", id="indicator-clock")
                yield Static(
                    "Two-bar reversal · waiting for completed candles.", id="two-bar"
                )
                yield Static(
                    "Click / Enter plots a metric; repeat clears.", id="indicator-hint"
                )
                yield IndicatorTable(id="indicators", cursor_type="row")
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
        self._next_quote = time.monotonic() + 1
        self.trade_stream.start()
        self._poll_timer = self.set_interval(0.25, self.poll_workers)
        self.query_one("#watchlist", DataTable).focus()
        if self.startup_warning:
            self.notice(self.startup_warning)

    def on_resize(self, event):
        self.set_class(event.size.width < 110, "compact")

    def request_data(self, *, clear=False, force=False):
        if self._display_stopping or not self.is_running:
            return
        if clear:
            self._view_generation += 1
            self.indicator_frame = None
            self._indicator_request_key = None
            self.current_frame = None
            self.paint_rows(self.state.visible())
            self.clear_details("Loading this window's completed candles…")
        self.data_worker.submit(
            {
                "interval": self.state.interval,
                "lookback": self.state.lookback,
                "rows": self.state.visible(),
                "force": bool(force or self._pending_force),
            }
        )
        self._pending_force = False
        self._next_data = time.monotonic() + self.data_refresh_delay()

    def data_refresh_delay(self):
        step = live.STEPS[self.state.interval]
        now = self.clock()
        next_boundary = (int((now - live.SETTLE_SECONDS) // step) + 1) * step
        until_boundary = next_boundary + live.SETTLE_SECONDS - now
        return min(self.state.refresh, max(0.2, until_boundary))

    def indicator_context(self):
        return (
            self._view_generation,
            self._source_version,
            self.state.interval,
            self.state.lookback,
        )

    def request_indicators(self, *, force=False):
        frame = self.current_frame
        if (
            self._display_stopping
            or not self.is_running
            or not frame
            or not frame.get("details")
            or "market_rows" not in frame
            or "end" not in frame
        ):
            return
        snapshot = self.trade_stream.snapshot(self.state.interval)
        key = (self.indicator_context(), snapshot.get("version"), int(self.clock()))
        if not force:
            if key == self._indicator_request_key:
                return
            if (
                self.indicator_worker.busy
                and self._indicator_request_key is not None
                and self._indicator_request_key[0] == self.indicator_context()
            ):
                return
        self._indicator_request_key = key
        self.indicator_worker.submit(
            {
                "context": self.indicator_context(),
                "interval": self.state.interval,
                "end": frame["end"],
                "lookback": self.state.lookback,
                "rows": frame["market_rows"],
                "configs": [w["config"] for w in self.state.visible()],
                "live": snapshot,
            }
        )

    def poll_workers(self):
        # Textual stops the app's pump before detaching its children; App
        # Unmount arrives later. A queued timer must not query that torn-down DOM.
        if self._display_stopping or not self.is_running:
            self._stop_display()
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
            token = self.current_frame.get("market_token", self.data_worker.generation)
            if token != self._market_token or self.current_frame.get("error"):
                self._market_token = token
                self._source_version += 1
                self.indicator_frame = None
                self._indicator_request_key = None
            if self.current_frame.get("error"):
                self.clear_details(
                    "Market data unavailable: " + str(self.current_frame["error"])
                )
        quoted = self.quote_worker.poll()
        if quoted is not None:
            self.quote_result = (
                quoted.value
                if not quoted.error
                else {"quote": None, "error": "quote_reader_failed"}
            )
        indicated = self.indicator_worker.poll()
        if indicated is not None:
            if (
                not indicated.error
                and indicated.value.get("context") == self.indicator_context()
            ):
                self.indicator_frame = indicated.value
            elif indicated.error:
                self.indicator_frame = None
        if (
            self._pending_quote or now >= self._next_quote
        ) and not self.quote_worker.busy:
            self.quote_worker.submit(None)
            self._pending_quote = False
            self._next_quote = now + 1
        # The chosen cadence is a maximum wait. A slow setting cannot strand
        # streaming indicators behind an already completed bar boundary.
        if self.current_frame and self.current_frame.get("end") is not None:
            settled_end = (
                int(
                    (self.clock() - live.SETTLE_SECONDS)
                    // live.STEPS[self.state.interval]
                )
                * live.STEPS[self.state.interval]
            )
            if settled_end > self.current_frame["end"]:
                self._next_data = min(self._next_data, now)
        if (
            self._pending_force or now >= self._next_data
        ) and not self.data_worker.busy:
            self.request_data(force=self._pending_force)
        self.request_indicators()
        self.paint()

    def notice(self, text):
        self.query_one("#notice", Static).update(Text(text))

    def clear_details(self, message):
        self.query_one("#shape", Static).update(Text(message))
        self.query_one("#indicators", DataTable).clear()
        self.indicator_keys = []
        self.indicator_frame = None
        self.query_one("#indicator-clock", Static).update(
            "Indicators unavailable; awaiting valid completed candles."
        )
        self.query_one("#two-bar", Static).update(
            "Two-bar reversal unavailable; awaiting completed candles."
        )
        self.query_one("#price-chart", MarketChart).set_frame(None)
        self.query_one("#chart-clock", Static).update(
            "Chart unavailable; awaiting valid completed candles."
        )
        if isinstance(self.screen, ShapeGuide):
            self.screen.update_details(None, self.state.interval)

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
        if self._display_stopping or not self.is_running:
            return
        quote = (self.quote_result or {}).get("quote")
        good = (
            quote
            and not (self.quote_result or {}).get("error")
            and 0 <= self.clock() - quote["observed_at"] <= 15
        )
        price = f"${quote['price']:.5f}" if good else "source unavailable / stale"
        self.query_one("#market", Static).update(
            Text(
                f"ZEC/USD  {price}   ·   next {self.state.interval} bar   ·   max refresh {self.state.refresh:g}s + bar closes\n{len(self.state.visible())} selected / {len(self.state.choices())} in this view · quote heartbeat 1s",
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
        self.query_one("#shape", Static).update(
            Text(
                shape_summary(details),
                style="dim" if details["stale"] else "cyan",
            )
        )
        if isinstance(self.screen, ShapeGuide):
            self.screen.update_details(details, self.state.interval)
        metrics = self.indicator_frame
        if metrics and metrics.get("context") != self.indicator_context():
            metrics = None
        readings = (metrics or {}).get("indicators", details["indicators"])
        if self.selected_indicator and self.selected_indicator not in {
            item["name"] for item in readings
        }:
            self.selected_indicator = None
        chart_frame = metrics or {
            "chart": details["chart"],
            "times": [
                details["chart_start"] + i * live.STEPS[self.state.interval]
                for i in range(len(details["chart"]))
            ]
            if details["chart_start"] is not None
            else [],
            "series": {},
            "indicators": readings,
        }
        self.query_one("#price-chart", MarketChart).set_frame(
            chart_frame, self.selected_indicator
        )
        times = chart_frame.get("times", [])
        point_count = len(chart_frame.get("chart", []))
        developing = bool(metrics and metrics.get("live"))
        completed_count = point_count - int(developing)
        first = live.iso(times[0])[5:19].replace("T", " ") if times else "—"
        last = live.iso(times[-1])[5:19].replace("T", " ") if times else "—"
        live_label = (
            " + 1 partial"
            if developing and metrics.get("partial")
            else " + 1 developing"
            if developing
            else ""
        )
        forming_clock = (
            f"Forming starts {live.iso(times[-1])[11:19]} UTC · "
            if developing and times
            else ""
        )
        chart_clock = self.query_one("#chart-clock", Static)
        chart_clock.tooltip = (
            f"Actual plotted candle starts: {live.iso(times[0])} → {live.iso(times[-1])}\n"
            f"{completed_count} completed + {int(developing)} developing = {point_count} plotted points."
            if times
            else "No valid plotted candles"
        )
        chart_clock.update(
            Text(
                f"{completed_count} completed{live_label} · {first} → {last} UTC starts\n"
                f"{forming_clock}source {details['contiguous_bars']} contiguous · {'RETAINED / STALE' if details['stale'] else 'current'}"
            )
        )
        if metrics and metrics.get("live"):
            status = (
                "LIVE · partial observed candle"
                if metrics.get("partial")
                else "LIVE · developing trade candle"
            )
            indicator_clock = (
                f"{self.state.interval} · {status}\n"
                f"Trade {live.iso(metrics['live_at'])[11:19]} UTC\n"
                "Volume: observed trades only\n"
                "Provisional; closed signals fixed"
            )
        else:
            reason = (metrics or {}).get("reason") or "indicator_calculation_pending"
            indicator_clock = (
                f"{self.state.interval} · completed candles\n"
                f"As of {live.iso(details['asof'])}\n"
                f"{'RETAINED / STALE · ' if details['stale'] else ''}{reason}"
            )
        indicator_clock_widget = self.query_one("#indicator-clock", Static)
        indicator_clock_widget.tooltip = (
            f"Latest observed trade: {live.iso(metrics['live_at'])}\n"
            "The first candle after attachment/reconnect is partial. Volume counts only actual observed trades."
            if metrics and metrics.get("live")
            else "Completed readings retained until a fresh contiguous streaming trade bar is available."
        )
        indicator_clock_widget.update(Text(indicator_clock))
        two_bar = (metrics or {}).get("two_bar") or {}
        two_bar_widget = self.query_one("#two-bar", Static)
        two_bar_widget.tooltip = two_bar.get("text")
        two_bar_widget.update(
            Text(
                ("STALE / EXPIRED · " if two_bar.get("stale") else "")
                + two_bar.get(
                    "compact_text",
                    two_bar.get(
                        "text", "Two-bar reversal · calculating completed-bar context…"
                    ),
                )
            )
        )
        self.query_one("#indicator-hint", Static).update(
            Text(
                f"Plot: {self.selected_indicator} · repeat selection clears"
                if self.selected_indicator
                else "Click / Enter plots a metric; repeat clears."
            )
        )
        table = self.query_one("#indicators", DataTable)
        names = [item["name"] for item in readings]
        rebuild = names != self.indicator_keys
        if rebuild:
            table.clear()
            self.indicator_keys = names
        for item in readings:
            value = item["value"]
            rendered = (
                "—"
                if value is None
                else Text(
                    f"{value:,.5f}",
                    style="dim"
                    if (metrics or {}).get("stale", details["stale"])
                    else "white",
                )
            )
            name = Text(
                ("● " if item["name"] == self.selected_indicator else "")
                + item["name"],
                style="bold magenta" if item["name"] == self.selected_indicator else "",
            )
            if rebuild:
                table.add_row(name, rendered, key=item["name"])
            else:
                table.update_cell(item["name"], next(iter(table.columns)), name)
                table.update_cell(item["name"], list(table.columns)[1], rendered)

    @on(DataTable.RowSelected, "#indicators")
    def select_indicator(self, event):
        self.toggle_indicator(event.row_key.value)

    @on(IndicatorTable.IndicatorClicked)
    def clicked_indicator(self, event):
        self.toggle_indicator(event.name)

    def toggle_indicator(self, name):
        self.selected_indicator = None if self.selected_indicator == name else name
        self.paint()

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
        self._next_data = time.monotonic() + self.data_refresh_delay()
        self.notice(
            f"Maximum refresh set to {seconds:g}s; bar-close data stays live and the horizon remains {self.state.interval}."
        )

    @on(Input.Submitted, "#refresh-seconds")
    def refresh_submitted(self, event):
        self.apply_refresh(event.value)

    def action_choose(self):
        self.push_screen(
            StrategyPicker(self.state.choices(), self.state.selected),
            self.selected_changed,
        )

    def action_shape_guide(self):
        details = None
        if self.current_frame:
            details = live_view(
                self.current_frame, self.quote_result, self.clock()
            ).get("details")
        self.push_screen(ShapeGuide(details, self.state.interval))

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
        if self._display_stopping or not self.is_running:
            return
        self._view_generation += 1
        self.indicator_frame = None
        self._indicator_request_key = None
        self._pending_force = self._pending_quote = True
        self.trade_stream.refresh()
        # Repeated manual clicks retain one successor. They do not cancel a
        # bootstrap repeatedly and prevent it from ever producing a frame.
        if not self.data_worker.busy:
            self.request_data(force=True)
        if not self.quote_worker.busy:
            self.quote_worker.submit(None)
            self._pending_quote = False
            self._next_quote = time.monotonic() + 1
        self.request_indicators()
        self.notice(
            "Refreshing all displayed data; provider failure backoff remains in force."
        )

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
            "refresh-now": self.action_refresh_now,
            "choose-strategies": self.action_choose,
            "show-shape-guide": self.action_shape_guide,
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

    def _stop_display(self):
        if self._display_stopping:
            return
        self._display_stopping = True
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()
        self.data_worker.close(0.1)
        self.quote_worker.close(0.1)
        self.indicator_worker.close(0.1)
        self.trade_stream.close(0.3)

    def exit(self, result=None, return_code=0, message=None):
        self._stop_display()
        super().exit(result, return_code=return_code, message=message)

    def on_unmount(self):
        self._stop_display()


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
        state,
        settings_path=args.settings,
        quote_loader=QuoteReader(args.prices),
        stream=TradeStream(),
    )
    app.startup_warning = warning
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

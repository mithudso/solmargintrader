"""Explicit trading controls and a read-only view of the durable paper trial.

The panel owns only its UI workers. The forward collector belongs to its service,
so closing this screen never stops a trial or starts a second collector.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

from research.zec_tui_workers import LatestWorker


def default_home() -> Path:
    return Path.home() / ".local/state/oracle-leverage"


def _text(value, *, limit=240) -> str:
    if value is None:
        return "—"
    if isinstance(value, (dict, list, tuple)):
        return "available" if value else "—"
    return str(value).replace("\x1b", "").replace("\n", " ")[:limit]


def _summary(value) -> str:
    if not isinstance(value, dict):
        return "Performance unavailable"
    cells = []
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            cells.append(f"{key.replace('_', ' ')}: {_text(item, limit=70)}")
    return " · ".join(cells) or "No settled paper predictions yet"


def wallet_text(data):
    wallet = data.get("wallet", {})
    wallet = wallet if isinstance(wallet, dict) else {}
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"

    def address(value):
        return (
            value
            if isinstance(value, str)
            and 32 <= len(value) <= 44
            and all(char in alphabet for char in value)
            else "unavailable"
        )

    current = address(wallet.get("address"))
    lines = [
        f"Transaction wallet: {current}",
        f"Key: {_text(wallet.get('name'), limit=128)} · {'ARMED' if wallet.get('armed') is True else 'DISARMED'} · {_text(wallet.get('status'))}",
    ]
    configured = address(wallet.get("configured_address"))
    if configured != "unavailable" and configured != current:
        lines.append(f"Configured wallet mismatch: {configured}")
    if wallet.get("message"):
        lines.append(_text(wallet["message"]))
    return "\n".join(lines)


def live_market_text(data, asset, now):
    """Keep the current source observation distinct from a recorded prediction."""
    heartbeat = data.get("heartbeat", {})
    assets = heartbeat.get("assets", {}) if isinstance(heartbeat, dict) else {}
    state = assets.get(asset, {}) if isinstance(assets, dict) else {}
    state = state if isinstance(state, dict) else {}
    quote = state.get("quote", {})
    quote = quote if isinstance(quote, dict) else {}
    price = quote.get("price")
    identity_matches = quote.get("asset") == asset
    valid_price = (
        identity_matches
        and type(price) in (int, float)
        and math.isfinite(price)
        and price > 0
    )
    product = _text(quote.get("product", state.get("product", f"{asset}-USD")))
    currency = _text(quote.get("quote_currency", state.get("quote_currency")))
    source = _text(quote.get("venue", state.get("venue")))
    price_text = (
        f"{price:,.6f}".rstrip("0").rstrip(".") if valid_price else "unavailable"
    )
    exchange_at, received_at = quote.get("event_at"), quote.get("observed_at")

    def age(stamp):
        if type(stamp) not in (int, float) or not math.isfinite(stamp):
            return "unavailable"
        elapsed = now - stamp
        if elapsed < 0:
            return f"FUTURE ({-elapsed:.0f}s)"
        return f"{elapsed:.0f}s" + (" · STALE QUOTE" if elapsed > 15 else "")

    events = [
        event
        for event in data.get("events", [])
        if isinstance(event, dict) and event.get("asset") == asset
    ]
    waiting = (
        f"Waiting for a new matching setup; no recent {asset} paper events in this view."
        if not events
        else "Matching paper signals and outcomes appear in the event ledger."
    )
    return (
        f"Live {product}: {price_text} {currency} · {source}\n"
        f"Exchange quote age: {age(exchange_at)} · received age: {age(received_at)} · cached completed minutes: {_text(state.get('cached_minutes'))}\n"
        f"Source status: {_text(state.get('status'))} · error: {_text(state.get('error'))}\n"
        f"{waiting}"
    )


class PositionTable(DataTable):
    """Make the first click select a position, as Enter already does."""

    def on_click(self, event: Click):
        row = event.style.meta.get("row")
        if type(row) is not int or not 0 <= row < self.row_count:
            return
        event.prevent_default()
        event.stop()
        self.focus()
        self.move_cursor(row=row, animate=False)
        key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
        self.post_message(self.RowSelected(self, row, key))


class LeveragePanel(ModalScreen[None]):
    """Keep reads responsive and every mutating operation single-flight."""

    BINDINGS: ClassVar = [
        ("escape", "return_to_oracle", "Return to Oracle"),
        ("q", "return_to_oracle", "Return to Oracle"),
        ("r", "refresh", "Refresh"),
    ]
    DEFAULT_CSS = """
    LeveragePanel { align: center middle; background: #06101be8; }
    #leverage-dialog { width: 98%; height: 96%; background: #152338; border: thick #418aab; padding: 0 1; }
    #leverage-title { height: 2; text-style: bold; }
    #leverage-status { height: 3; color: #a8c1dd; }
    #leverage-wallet { height: auto; min-height: 2; color: #d5f0ff; text-style: bold; border-left: tall #418aab; padding: 0 1; }
    .leverage-controls { height: 3; }
    .leverage-controls Label { width: auto; content-align: left middle; margin-right: 1; }
    #leverage-asset { width: 12; }
    #leverage-interval { width: 17; }
    #leverage-venue { width: 31; }
    #leverage-side { width: 15; }
    #leverage-collateral { width: 13; }
    #leverage-contents { height: 1fr; }
    #leverage-capabilities, #leverage-performance, #leverage-result { height: auto; min-height: 3; }
    #leverage-live-market { height: auto; min-height: 4; color: #c3d8ed; }
    #leverage-strategies { height: 8; min-height: 5; }
    #leverage-positions { height: 7; min-height: 4; }
    #leverage-events { height: auto; min-height: 3; }
    .leverage-section { height: 1; text-style: bold; color: #a8c1dd; }
    #leverage-result { color: #ffdda6; border: round #2c637d; padding: 0 1; }
    #leverage-preview, #leverage-submit, #leverage-close-position { min-width: 12; }
    #leverage-return { min-width: 14; }
    """

    def __init__(
        self, home=None, *, console=None, console_factory=None, clock=time.time
    ):
        super().__init__()
        self.home = Path(home) if home is not None else default_home()
        self.console = console
        self.console_factory = console_factory
        self.clock = clock
        self.snapshot_data = None
        self.last_result = None
        self.preview_id = None
        self.selected_position = None
        self._stopping = False
        self._operation = None
        self._selection_generation = 0
        self._operation_selection = None
        self._next_read = 0.0
        self._next_market_paint = 0.0
        self._read_worker = self._action_worker = None

    def _console(self):
        # Import and disk-backed setup happen in a worker, never on the event loop.
        if self.console is not None:
            return self.console
        if self.console_factory is None:
            from oracle_leverage.console import Console

            return Console(self.home)
        return self.console_factory(self.home)

    def _read(self, request, cancelled):
        if cancelled():
            return None
        value = self._console().snapshot()
        if not isinstance(value, dict):
            raise TypeError("malformed_console_snapshot")
        for key in ("assets", "strategies", "positions", "events"):
            if key in value and not isinstance(value[key], list):
                raise TypeError("malformed_console_snapshot_section")
        if "performance" in value and not isinstance(value["performance"], dict):
            raise TypeError("malformed_console_performance")
        return value

    def _act(self, request, cancelled):
        if cancelled():
            return {
                "status": "cancelled",
                "message": "Operation cancelled before dispatch.",
            }
        console = self._console()
        action, args = request
        value = getattr(console, action)(*args)
        if not isinstance(value, dict):
            raise TypeError("malformed_console_result")
        return value

    def compose(self) -> ComposeResult:
        with Vertical(id="leverage-dialog"):
            yield Label("Leverage & live paper forward test", id="leverage-title")
            yield Static(
                "Loading durable trial status…", id="leverage-status", markup=False
            )
            yield Static(
                "Transaction wallet: loading public identity…",
                id="leverage-wallet",
                markup=False,
            )
            with Horizontal(classes="leverage-controls"):
                yield Label("Asset")
                yield Select(
                    [("ZEC", "ZEC"), ("BTC", "BTC")],
                    value="ZEC",
                    allow_blank=False,
                    id="leverage-asset",
                )
                yield Label("Bar")
                yield Select(
                    [("All bars", 0), *[(f"{n}m", n) for n in (5, 10, 15, 20)]],
                    value=0,
                    allow_blank=False,
                    id="leverage-interval",
                )
                yield Button("Refresh [R]", id="leverage-refresh")
                yield Button("Return [Esc]", id="leverage-return")
            with VerticalScroll(id="leverage-contents"):
                yield Static(
                    "Venue capabilities pending",
                    id="leverage-capabilities",
                    markup=False,
                )
                yield Static(
                    "Live source observation pending…",
                    id="leverage-live-market",
                    markup=False,
                )
                yield Static(
                    "Paper performance pending", id="leverage-performance", markup=False
                )
                yield Label(
                    "Frozen strategy / backtest evidence", classes="leverage-section"
                )
                yield DataTable(id="leverage-strategies", cursor_type="row")
                yield Label(
                    "Positions · select a row before Close", classes="leverage-section"
                )
                yield PositionTable(id="leverage-positions", cursor_type="row")
                yield Static("No trial events yet", id="leverage-events", markup=False)
            with Horizontal(classes="leverage-controls"):
                yield Select(
                    [
                        ("Jupiter CLI · 10×", "jupiter-cli-10x"),
                        ("Jupiter SDK · 1000×", "jupiter-sdk-1000x"),
                    ],
                    value="jupiter-cli-10x",
                    allow_blank=False,
                    id="leverage-venue",
                )
                yield Select(
                    [("Long", "long"), ("Short", "short")],
                    value="short",
                    allow_blank=False,
                    id="leverage-side",
                )
                yield Label("Collateral $")
                yield Input("10", type="number", id="leverage-collateral")
            yield Static(
                "Preview checks a fresh unsigned build. Submit signs and sends that preview after backend arming and revalidation.\n10× collateral: USDC · 1000× collateral: JupUSD · Close uses the selected position's venue.",
                id="leverage-result",
                markup=False,
            )
            with Horizontal(classes="leverage-controls"):
                yield Button("Preview", id="leverage-preview", variant="primary")
                yield Button(
                    "Submit preview",
                    id="leverage-submit",
                    variant="error",
                    disabled=True,
                )
                yield Button(
                    "Close position", id="leverage-close-position", disabled=True
                )

    def on_mount(self):
        self.query_one("#leverage-strategies", DataTable).add_columns(
            "Asset", "Bar", "Shape", "Call", "Evidence"
        )
        self.query_one("#leverage-positions", DataTable).add_columns(
            "Asset", "Venue", "Side", "State", "PnL $", "Position"
        )
        self._read_worker = LatestWorker(self._read, name="oracle-leverage-read")
        self._action_worker = LatestWorker(self._act, name="oracle-leverage-action")
        self._poll_timer = self.set_interval(0.1, self.poll_workers)
        self.action_refresh()

    def action_refresh(self):
        if self._stopping or self._read_worker is None:
            return
        if not self._read_worker.busy:
            self._read_worker.submit(None)
            self._next_read = time.monotonic() + 2

    def _set_result(self, message):
        if not self._stopping and self.is_mounted:
            self.query_one("#leverage-result", Static).update(Text(message))

    def _controls(self):
        busy = self._operation is not None
        self.query_one("#leverage-preview", Button).disabled = busy
        self.query_one("#leverage-submit", Button).disabled = (
            busy or self.preview_id is None
        )
        self.query_one("#leverage-close-position", Button).disabled = (
            busy or self.selected_position is None
        )
        for identity in (
            "leverage-asset",
            "leverage-interval",
            "leverage-venue",
            "leverage-side",
            "leverage-collateral",
        ):
            self.query_one(f"#{identity}").disabled = busy

    def _dispatch(self, action, args):
        if self._stopping or self._operation is not None:
            return
        self._operation = action
        self._operation_selection = self._selection_generation
        self._action_worker.submit((action, args))
        self._set_result(
            f"{action.capitalize()} in progress… No second operation will be sent."
        )
        self._controls()

    def poll_workers(self):
        if self._stopping or not self.is_mounted:
            return
        result = self._read_worker.poll()
        if result is not None:
            if result.error or not isinstance(result.value, dict):
                self.query_one("#leverage-status", Static).update(
                    "Status unavailable · last displayed values may be stale. Backend read failed."
                )
            else:
                self.snapshot_data = result.value
                self.paint_snapshot()
        result = self._action_worker.poll()
        if result is not None:
            action, self._operation = self._operation, None
            if result.error or not isinstance(result.value, dict):
                # An execution error does not prove that a transaction was absent.
                self.preview_id = None
                self._set_result(
                    "Operation result unavailable. Check the durable intent / position state before any retry; no retry was sent."
                )
            else:
                value = result.value
                self.last_result = value
                self.preview_id = None
                if (
                    action == "preview"
                    and self._operation_selection == self._selection_generation
                    and isinstance(value.get("preview_id"), str)
                    and value.get("status")
                    not in ("blocked", "error", "failed", "refused", "cancelled")
                ):
                    self.preview_id = value["preview_id"]
                details = [
                    f"{_text(value.get('status'))}: {_text(value.get('message'), limit=600)}"
                ]
                for key in (
                    "asset",
                    "venue",
                    "side",
                    "collateral_usd",
                    "leverage",
                    "signature",
                    "position_id",
                ):
                    if key in value:
                        details.append(f"{key.replace('_', ' ')}: {_text(value[key])}")
                if (
                    action == "preview"
                    and self._operation_selection != self._selection_generation
                ):
                    details.append(
                        "Selection changed while the preview ran. Generate a new preview before submitting."
                    )
                self._set_result("\n".join(details))
            self._controls()
            self.action_refresh()
        if time.monotonic() >= self._next_read:
            self.action_refresh()
        if (
            self.snapshot_data is not None
            and time.monotonic() >= self._next_market_paint
        ):
            self._next_market_paint = time.monotonic() + 1
            self.paint_live_market()

    def paint_live_market(self):
        asset = self.query_one("#leverage-asset", Select).value
        self.query_one("#leverage-live-market", Static).update(
            Text(live_market_text(self.snapshot_data or {}, asset, self.clock()))
        )

    def paint_snapshot(self):
        data = self.snapshot_data or {}
        stamp = data.get("updated_at")
        age = (
            self.clock() - stamp
            if type(stamp) in (int, float) and math.isfinite(stamp)
            else None
        )
        freshness = (
            "update time unavailable"
            if age is None
            else f"updated {max(0, age):.0f}s ago"
            + (" · STALE" if age > 90 or age < -5 else "")
        )
        self.query_one("#leverage-status", Static).update(
            Text(
                f"Paper forward: {_text(data.get('status'))} · {freshness}\nPaper results are simulated; venue execution status is separate. Closing this panel leaves the forward service running."
            )
        )
        self.query_one("#leverage-wallet", Static).update(Text(wallet_text(data)))
        asset = self.query_one("#leverage-asset", Select).value
        interval = self.query_one("#leverage-interval", Select).value
        capabilities = []
        for row in data.get("assets", []):
            if isinstance(row, dict) and row.get("asset", row.get("symbol")) == asset:
                for key, value in row.items():
                    if key not in ("asset", "symbol"):
                        if isinstance(value, list):
                            capabilities.extend(
                                _summary(item)
                                if isinstance(item, dict)
                                else _text(item)
                                for item in value
                            )
                        elif isinstance(value, dict):
                            capabilities.append(f"{key}: {_summary(value)}")
                        else:
                            capabilities.append(
                                f"{key.replace('_', ' ')}: {_text(value)}"
                            )
        self.query_one("#leverage-capabilities", Static).update(
            Text(
                f"{asset} capabilities\n"
                + (
                    "\n".join(capabilities)
                    or "Capability details unavailable; preview checks the selected venue."
                )
            )
        )
        self.paint_live_market()
        performance = data.get("performance", {})
        if isinstance(performance, dict) and isinstance(
            performance.get("by_asset"), dict
        ):
            selected = performance["by_asset"].get(asset)
            performance = selected if selected is not None else performance
        self.query_one("#leverage-performance", Static).update(
            Text(f"Paper forward · {asset}\n{_summary(performance)}")
        )
        table = self.query_one("#leverage-strategies", DataTable)
        table.clear()
        for index, row in enumerate(data.get("strategies", [])):
            if (
                not isinstance(row, dict)
                or row.get("asset") != asset
                or (interval != 0 and row.get("interval_minutes") != interval)
            ):
                continue
            table.add_row(
                *[
                    Text(_text(row.get(key)))
                    for key in (
                        "asset",
                        "interval_minutes",
                        "shape",
                        "direction",
                        "evidence",
                    )
                ],
                key=f"strategy-{index}",
            )
        positions = self.query_one("#leverage-positions", DataTable)
        positions.clear()
        current = set()
        for index, row in enumerate(data.get("positions", [])):
            if not isinstance(row, dict) or row.get("asset") != asset:
                continue
            identity = row.get("id", row.get("position_id"))
            if not isinstance(identity, str) or not identity or identity in current:
                continue
            current.add(identity)
            positions.add_row(
                *[
                    Text(_text(row.get(key)))
                    for key in ("asset", "venue", "side", "status", "pnl_usd")
                ],
                Text(identity),
                key=identity,
            )
        if self.selected_position not in current:
            self.selected_position = None
        elif self.selected_position in current:
            positions.move_cursor(row=positions.get_row_index(self.selected_position))
        events = []
        for event in data.get("events", [])[-6:]:
            if isinstance(event, dict):
                events.append(
                    " · ".join(
                        _text(event.get(key), limit=140)
                        for key in ("at", "asset", "status", "message")
                        if key in event
                    )
                )
            elif isinstance(event, str):
                events.append(_text(event))
        self.query_one("#leverage-events", Static).update(
            Text(
                "Recent paper / execution events\n"
                + ("\n".join(events) or "No events yet")
            )
        )
        self._controls()

    @on(Select.Changed)
    @on(Input.Changed, "#leverage-collateral")
    def selection_changed(self, event):
        event.stop()
        if not self.is_mounted or self._stopping:
            return
        self.preview_id = None
        self._selection_generation += 1
        if (
            getattr(event, "select", None) is not None
            and event.select.id == "leverage-asset"
        ):
            self.selected_position = None
        if self.snapshot_data is not None:
            self.paint_snapshot()
        self._controls()

    @on(DataTable.RowSelected, "#leverage-positions")
    def position_selected(self, event):
        event.stop()
        self.selected_position = str(event.row_key.value)
        self._controls()

    @on(Button.Pressed)
    def button_pressed(self, event):
        event.stop()
        name = event.button.id
        if name == "leverage-return":
            self.action_return_to_oracle()
        elif name == "leverage-refresh":
            self.action_refresh()
        elif name == "leverage-preview":
            try:
                amount = float(self.query_one("#leverage-collateral", Input).value)
                if not math.isfinite(amount) or amount <= 0:
                    raise ValueError("invalid_amount")
            except ValueError:
                self._set_result(
                    "Collateral must be a finite amount greater than zero."
                )
                return
            self.preview_id = None
            self._dispatch(
                "preview",
                (
                    self.query_one("#leverage-asset", Select).value,
                    self.query_one("#leverage-venue", Select).value,
                    self.query_one("#leverage-side", Select).value,
                    amount,
                ),
            )
        elif name == "leverage-submit" and self.preview_id is not None:
            identity, self.preview_id = self.preview_id, None
            self._dispatch("execute", (identity,))
        elif name == "leverage-close-position" and self.selected_position is not None:
            self.preview_id = None
            self._dispatch("close", (self.selected_position,))

    def action_return_to_oracle(self):
        if self._operation is not None:
            self._set_result(
                "Operation still in flight. Waiting for its final result before returning; no retry will be sent."
            )
            return
        self.stop_owned()
        self.dismiss(None)

    def stop_owned(self):
        if self._stopping:
            return
        self._stopping = True
        if hasattr(self, "_poll_timer"):
            self._poll_timer.stop()
        for worker in (self._read_worker, self._action_worker):
            if worker is not None:
                worker.close(0.15)

    def on_unmount(self):
        self.stop_owned()

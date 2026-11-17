"""Explicit trading controls and a read-only view of the durable paper trial.

The panel owns only its UI workers. The forward collector belongs to its service,
so closing this screen never stops a trial or starts a second collector.
"""

from __future__ import annotations

import copy
import math
import re
import time
from pathlib import Path
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Click
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DataTable, Input, Label, Select, Static

from research.zec_feed_settings import load_feeds, save_feeds
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


def emphasized(value):
    """Color literal text; provider strings never become Rich markup or commands."""
    text = Text(value)
    for pattern, style in (
        (r"https?://[^\s<>]+", "underline bright_cyan"),
        (r"\b(?:LIVE|PRIMARY|ARMED)\b", "bold bright_green"),
        (r"\b(?:STALE|DISARMED|waiting|degraded)\b", "bold yellow"),
        (r"\b(?:MISMATCH|mismatch|unavailable|failed|error)\b", "bold bright_red"),
    ):
        for match in re.finditer(pattern, value):
            text.stylize(style, *match.span())
    return text


def comparison_text(data, asset, venue, now, basis_cache=None, enabled=None):
    enabled = enabled if enabled is not None else {"jupiter": True, "coinbase": True}
    state = data.get("price_comparison", {})
    state = state if isinstance(state, dict) else {}
    feeds = state.get("feeds", {})
    feeds = feeds if isinstance(feeds, dict) else {}
    errors = state.get("errors", {})
    errors = errors if isinstance(errors, dict) else {}
    connected = state.get("connected", {})
    connected = connected if isinstance(connected, dict) else {}
    stamp = state.get("at")
    heartbeat_fresh = (
        type(stamp) in (int, float) and math.isfinite(stamp) and 0 <= now - stamp <= 2
    )
    primary = "jupiter" if venue == "jupiter-sdk-1000x" else "coinbase"
    if not enabled.get(primary):
        primary = next((s for s in ("jupiter", "coinbase") if enabled.get(s)), None)
    lines = [
        f"{asset}/USD · {'both live streams' if all(enabled.values()) else 'selected live stream'} · primary display: {'Jupiter oracle' if primary == 'jupiter' else 'Coinbase book midpoint'}"
    ]
    valid = {}
    exchange_times = {}
    colors = []
    for source, title, maximum in (
        ("jupiter", "Jupiter oracle", 1),
        ("coinbase", "Coinbase synced book midpoint", 3),
    ):
        if not enabled.get(source):
            continue
        rows = feeds.get(source, {})
        row = rows.get(asset, {}) if isinstance(rows, dict) else {}
        row = row if isinstance(row, dict) else {}
        price = row.get("price")
        numeric = (
            row.get("asset") == asset
            and type(price) in (int, float)
            and math.isfinite(price)
            and price > 0
        )
        ages = []
        for key in ("exchange_at", "received_at"):
            stamp = row.get(key)
            ages.append(
                now - stamp
                if type(stamp) in (int, float) and math.isfinite(stamp)
                else None
            )
        fresh = (
            numeric
            and heartbeat_fresh
            and connected.get(source) is True
            and row.get("fresh", True) is True
            and state.get("status") != "stopped"
            and all(age is not None and 0 <= age <= maximum for age in ages)
        )
        valid[source] = price if fresh else None
        exchange_times[source] = row.get("exchange_at") if fresh else None
        display = (
            f"{price:,.8f}".rstrip("0").rstrip(".") + " USD"
            if numeric
            else "unavailable"
        )
        oldest = max(
            (age for age in ages if age is not None and age >= 0), default=float("inf")
        )
        color = (
            "green"
            if fresh
            else "yellow"
            if numeric and oldest <= 5 and state.get("status") != "stopped"
            else "red"
        )
        colors.append(color)
        age_labels = [f"{age:.2f}s" if age is not None else "unknown" for age in ages]
        lines.append(
            f"{title}{' · PRIMARY' if source == primary else ''}: {display} · {color.upper()}● · exchange {age_labels[0]} · received {age_labels[1]}"
            + f" · {'LIVE' if fresh else 'DELAYED' if color == 'yellow' else 'STALE'}"
        )
    both = all(enabled.get(s) for s in ("jupiter", "coinbase"))
    comparable = both and all(
        valid.get(source) is not None for source in ("jupiter", "coinbase")
    )
    skew = (
        abs(exchange_times["jupiter"] - exchange_times["coinbase"])
        if comparable
        else None
    )
    pairs = state.get("pairs", {})
    pair = pairs.get(asset) if isinstance(pairs, dict) else None
    if isinstance(pair, dict):
        backend_skew = pair.get("timestamp_skew_seconds")
        comparable = (
            comparable
            and pair.get("comparable") is True
            and type(backend_skew) in (int, float)
            and math.isfinite(backend_skew)
            and 0 <= backend_skew <= 1
        )
    comparable = comparable and skew is not None and skew <= 1
    if comparable:
        difference = valid["jupiter"] - valid["coinbase"]
        basis = difference / valid["coinbase"] * 10000
        if isinstance(pair, dict):
            backend_difference, backend_basis = (
                pair.get("difference_usd"),
                pair.get("basis_bps"),
            )
            if all(
                type(value) in (int, float) and math.isfinite(value)
                for value in (backend_difference, backend_basis)
            ):
                difference, basis = backend_difference, backend_basis
        line = f"Basis Jupiter − Coinbase: {difference:+.8f} USD ({basis:+.3f} bps) · skew {skew:.2f}s"
        if basis_cache is not None:
            basis_cache["line"] = line
        lines.append(line + " · GREEN●")
    elif both and basis_cache is not None and basis_cache.get("line"):
        color = "RED" if "red" in colors else "YELLOW"
        lines.append(basis_cache["line"] + f" · {color}● · STALE PAIR")
    elif both:
        lines.append("Basis: —")
    result = emphasized("\n".join(lines))
    for color in ("GREEN", "YELLOW", "RED"):
        for match in list(re.finditer(color + "●", result.plain))[::-1]:
            result.stylize(
                {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}[color],
                match.end() - 1,
                match.end(),
            )
            result = result[: match.start()] + result[match.end() - 1 :]
    return result


def bar_view(bar, current=False):
    """Color body movement by its magnitude over trailing completed ranges."""
    label = "Developing 10m" if current else "Previous closed 10m"
    if not isinstance(bar, dict):
        return f"{label} · waiting", "#555b60"
    opening, close, baseline = (
        bar.get("open"),
        bar.get("close"),
        bar.get("baseline_range"),
    )
    if (
        any(
            type(x) not in (int, float) or not math.isfinite(x)
            for x in (opening, close)
        )
        or opening <= 0
    ):
        return f"{label} · waiting", "#555b60"
    change = (close - opening) / opening * 100
    intensity = (
        min(1.0, abs(close - opening) / baseline)
        if type(baseline) in (int, float) and math.isfinite(baseline) and baseline > 0
        else 0
    )
    level = int(80 + 150 * intensity)
    muted = int(74 - 44 * intensity)
    if close > opening:
        color, arrow = f"#{muted:02x}{level:02x}{muted:02x}", "↑"
    elif close < opening:
        color, arrow = f"#{level:02x}{muted:02x}{muted:02x}", "↓"
    else:
        color, arrow = "#555b60", "→"
    progress = bar.get("progress")
    suffix = (
        f" · {progress * 100:.0f}%"
        if current and type(progress) in (int, float) and math.isfinite(progress)
        else ""
    )
    return f"{label} {arrow} {change:+.3f}%{suffix}", color


def bar_text_color(background):
    """Choose a readable label on every magnitude-tinted bar background."""
    channels = [int(background[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [
        v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels
    ]
    luminance = sum(
        a * b for a, b in zip(linear, (0.2126, 0.7152, 0.0722), strict=True)
    )
    return "#000000" if luminance > 0.179 else "#ffffff"


def tilt_text(tilts, tentative=False):
    items = []
    for minutes in (5, 10, 15, 20):
        item = tilts.get(str(minutes), {}) if isinstance(tilts, dict) else {}
        uplift = item.get("uplift_pp") if isinstance(item, dict) else None
        n = item.get("n") if isinstance(item, dict) else None
        if (
            type(uplift) not in (int, float)
            or not math.isfinite(uplift)
            or type(n) is not int
            or n < 20
            or abs(uplift) < 1e-12
        ):
            items.append(f"{minutes}m ?")
        else:
            items.append(
                f"{minutes}m {'↑' if uplift > 0 else '↓'} {uplift:+.1f}pp n={n}"
            )
    return (
        "Next 10m IF UU"
        + (" (developing, tentative)" if tentative else "")
        + " · ΔP(up) vs baseline: "
        + " · ".join(items)
    )


def mtf_tilt_text(scores, frames=None):
    """Display published 10m model components against their training baseline."""
    model = scores.get("10", {}) if isinstance(scores, dict) else {}
    baseline = model.get("base_down_rate") if isinstance(model, dict) else None
    components = model.get("components", []) if isinstance(model, dict) else []
    by_frame = (
        {
            c["minutes"]: c
            for c in components
            if isinstance(c, dict) and type(c.get("minutes")) is int
        }
        if isinstance(components, list)
        else {}
    )
    items = []
    for minutes in (5, 10, 15, 20):
        row = by_frame.get(minutes, {})
        posterior = row.get("posterior_down")
        n = row.get("n")
        if (
            type(baseline) not in (int, float)
            or not math.isfinite(baseline)
            or type(posterior) not in (int, float)
            or not math.isfinite(posterior)
            or type(n) is not int
            or n <= 0
        ):
            frame = frames.get(str(minutes), {}) if isinstance(frames, dict) else {}
            shape = frame.get("shape") if isinstance(frame, dict) else None
            if (
                isinstance(shape, str)
                and shape != "unknown"
                and isinstance(model, dict)
                and model.get("status") == "ready"
            ):
                items.append(f"{minutes}m {_text(shape, limit=24)} unsupported")
            else:
                items.append(f"{minutes}m ?")
        else:
            uplift = (baseline - posterior) * 100
            items.append(f"{minutes}m {uplift:+.1f}pp n={n}")
    return "10m model shape component ΔP(up) vs baseline · " + " · ".join(items)


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
    LeveragePanel Button { text-style: bold; }
    LeveragePanel Link { text-style: underline; color: #4ce5ff; }
    LeveragePanel DataTable > .datatable--header { background: #18475c; color: #8df5ff; text-style: bold; }
    LeveragePanel DataTable > .datatable--cursor { background: #186878; color: #ffffff; text-style: bold; }
    #leverage-body { height: 1fr; overflow-y: hidden; }
    LeveragePanel.short #leverage-body { overflow-y: auto; }
    LeveragePanel.short #leverage-workspace { height: 24; min-height: 24; }
    #leverage-dialog { width: 98%; height: 96%; background: #152338; border: thick #418aab; padding: 0 1; }
    #leverage-title { height: 2; text-style: bold; color: #58e9f0; }
    #leverage-feed-controls { height: 3; }
    #leverage-feed-controls Checkbox { width: auto; margin-right: 1; }
    #leverage-feed-controls Label { width: auto; content-align: left middle; }
    #leverage-feed-notice { height: auto; color: #ffdda6; }
    #leverage-trading { height: auto; }
    #leverage-status { height: auto; min-height: 3; color: #a8c1dd; }
    #leverage-wallet { height: auto; min-height: 2; color: #74f6e0; background: #123440; text-style: bold; border-left: tall #27d9c2; padding: 0 1; }
    .leverage-controls { height: 3; }
    .leverage-controls Label { width: auto; content-align: left middle; margin-right: 1; }
    #leverage-asset { width: 12; }
    #leverage-interval { width: 17; }
    #leverage-venue { width: 31; }
    #leverage-side { width: 15; }
    #leverage-collateral { width: 13; }
    #leverage-workspace { height: 1fr; }
    #leverage-contents { width: 3fr; height: 1fr; }
    #leverage-right { width: 2fr; height: 1fr; margin-left: 1; }
    #leverage-bar-tilts { height: auto; min-height: 1; }
    #leverage-bars { height: 3; }
    #leverage-bars Button { width: 1fr; min-width: 1; height: 3; }
    #leverage-right #leverage-strategies, #leverage-right #leverage-positions { height: 1fr; min-height: 3; }
    #leverage-price-comparison { height: auto; min-height: 7; color: #d9fbff; border: round #28b8b8; padding: 0 1; }
    #leverage-capabilities, #leverage-performance, #leverage-result { height: auto; min-height: 3; }
    #leverage-live-market { height: auto; min-height: 4; color: #c3d8ed; }
    #leverage-strategies { height: 8; min-height: 5; }
    #leverage-positions { height: 7; min-height: 4; }
    #leverage-events { height: auto; min-height: 3; }
    .leverage-section { height: 1; text-style: bold; color: #50dfe8; }
    #leverage-result { color: #ffdda6; border: round #2c637d; padding: 0 1; }
    #leverage-result-region { height: auto; min-height: 3; max-height: 6; }
    #leverage-preview, #leverage-submit, #leverage-close-position { min-width: 12; }
    #leverage-preview { background: #005ea8; color: #ffffff; }
    #leverage-return { min-width: 14; }
    """

    def __init__(
        self,
        home=None,
        *,
        console=None,
        console_factory=None,
        clock=time.time,
        feed_changed=None,
    ):
        super().__init__()
        self.home = Path(home) if home is not None else default_home()
        self.console = console
        self.console_factory = console_factory
        self.clock = clock
        self._feed_settings = (
            self.home / "view.json" if home is not None or console is None else None
        )
        self.feed_enabled = load_feeds(self._feed_settings)
        self._feed_changed = feed_changed
        self._feed_notice = ""
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
        self._basis_cache = {}
        self._basis_key = None
        self._last_feeds = {}
        self._table_rows = {}
        self._read_failed = False
        from research.quote_bars import QuoteBars

        self._quote_bars = QuoteBars(self.home / "dual-quotes")

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
        value["quote_bars"] = self._quote_bars.read(self.clock())
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
            with Horizontal(id="leverage-feed-controls"):
                yield Label("Show feeds")
                yield Checkbox(
                    "Jupiter",
                    value=self.feed_enabled["jupiter"],
                    id="leverage-feed-jupiter",
                )
                yield Checkbox(
                    "Coinbase",
                    value=self.feed_enabled["coinbase"],
                    id="leverage-feed-coinbase",
                )
                yield Button("Return [Esc]", id="leverage-return")
            yield Static("", id="leverage-feed-notice", markup=False)
            with VerticalScroll(id="leverage-body"):
                yield Static(
                    "Next 10m IF UU · ΔP(up) vs baseline: waiting",
                    id="leverage-bar-tilts",
                    markup=False,
                )
                with Horizontal(id="leverage-bars"):
                    yield Button(
                        "Previous closed 10m · waiting", id="leverage-previous-bar"
                    )
                    yield Button("Developing 10m · waiting", id="leverage-current-bar")
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
                    yield Label("Bar", id="leverage-interval-label")
                    yield Select(
                        [("All bars", 0), *[(f"{n}m", n) for n in (5, 10, 15, 20)]],
                        value=0,
                        allow_blank=False,
                        id="leverage-interval",
                    )
                    yield Button("Refresh [R]", id="leverage-refresh")
                with Horizontal(id="leverage-workspace"):
                    with VerticalScroll(id="leverage-contents"):
                        yield Static(
                            "Both price streams: waiting for source observations…",
                            id="leverage-price-comparison",
                            markup=False,
                        )
                        yield Static(
                            "10m reversal: waiting for paper observer",
                            id="leverage-exit50",
                            markup=False,
                        )
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
                            "Paper performance pending",
                            id="leverage-performance",
                            markup=False,
                        )
                        yield Static(
                            "No trial events yet", id="leverage-events", markup=False
                        )
                    with Vertical(id="leverage-right"):
                        yield Label(
                            "Positions · select before Close",
                            classes="leverage-section",
                            id="leverage-positions-title",
                        )
                        yield PositionTable(id="leverage-positions", cursor_type="row")
                        yield Label(
                            "Oracle calls · frozen evidence",
                            classes="leverage-section",
                            id="leverage-strategies-title",
                        )
                        yield DataTable(id="leverage-strategies", cursor_type="row")
                with Vertical(id="leverage-trading"):
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
                    with VerticalScroll(id="leverage-result-region"):
                        yield Static(
                            "Preview checks a fresh unsigned build. Submit signs and sends that preview after backend arming and revalidation.\n10× collateral: USDC · 1000× collateral: JupUSD · Close uses the selected position's venue.",
                            id="leverage-result",
                            markup=False,
                        )
                    with Horizontal(classes="leverage-controls"):
                        yield Button(
                            "Arm state unknown",
                            id="leverage-arm",
                            variant="warning",
                            disabled=True,
                        )
                        yield Button(
                            "Preview", id="leverage-preview", variant="primary"
                        )
                        yield Button(
                            "Submit preview",
                            id="leverage-submit",
                            variant="error",
                            disabled=True,
                        )
                        yield Button(
                            "Close position",
                            id="leverage-close-position",
                            disabled=True,
                        )

    def on_resize(self, event):
        self.set_class(event.size.height < 38, "short")

    def on_mount(self):
        self.set_class(self.size.height < 38, "short")
        self.query_one("#leverage-strategies", DataTable).add_columns(
            "Asset", "Bar", "Shape", "Call", "Evidence"
        )
        self.query_one("#leverage-positions", DataTable).add_columns(
            "Asset", "Source", "Side", "State", "PnL / ROE", "Position"
        )
        self._read_worker = LatestWorker(self._read, name="oracle-leverage-read")
        self._action_worker = LatestWorker(self._act, name="oracle-leverage-action")
        self._poll_timer = self.set_interval(0.1, self.poll_workers)
        self._apply_feed_visibility()
        if self._feed_changed is not None:
            self._feed_changed(dict(self.feed_enabled))
        self.action_refresh()

    def _apply_feed_visibility(self):
        jupiter, coinbase = (self.feed_enabled[k] for k in ("jupiter", "coinbase"))
        for identity in (
            "leverage-bar-tilts",
            "leverage-bars",
            "leverage-wallet",
            "leverage-capabilities",
            "leverage-exit50",
            "leverage-performance",
            "leverage-trading",
        ):
            self.query_one(f"#{identity}").display = jupiter
        for identity in (
            "leverage-live-market",
            "leverage-strategies",
            "leverage-strategies-title",
            "leverage-events",
            "leverage-interval",
            "leverage-interval-label",
        ):
            self.query_one(f"#{identity}").display = coinbase
        self.query_one("#leverage-workspace").display = jupiter or coinbase
        self.query_one("#leverage-status").display = jupiter or coinbase
        self.query_one("#leverage-price-comparison").display = jupiter or coinbase
        self.query_one("#leverage-positions").display = jupiter
        self.query_one("#leverage-positions-title").display = jupiter
        notice = self._feed_notice
        if self._read_failed:
            notice = (
                "Snapshot unavailable. Refresh retries; retained observations may be stale. "
                + notice
            )
        if not jupiter and not coinbase:
            notice = "Both feeds hidden. Re-enable a feed above to resume its view. Shared paper recording continues."
        self.query_one("#leverage-feed-notice", Static).update(Text(notice))

    @on(Checkbox.Changed, "#leverage-feed-controls Checkbox")
    def feed_changed(self, event):
        event.stop()
        if not self.is_mounted or self._stopping:
            return
        source = event.checkbox.id.removeprefix("leverage-feed-")
        if self.feed_enabled.get(source) == event.value:
            return
        self.feed_enabled[source] = event.value
        self._basis_cache.clear()
        self._basis_key = None
        self._feed_notice = ""
        try:
            save_feeds(self._feed_settings, self.feed_enabled)
        except (OSError, ValueError):
            self._feed_notice = (
                "Feed view changed for this session. Preferences could not be saved."
            )
        if self._feed_changed is not None:
            self._feed_changed(dict(self.feed_enabled))
        self._apply_feed_visibility()
        if self.snapshot_data is not None:
            self.paint_snapshot()
        self.action_refresh()

    def action_refresh(self):
        if self._stopping or self._read_worker is None:
            return
        if not self._read_worker.busy:
            self._read_worker.submit(None)
            self._next_read = time.monotonic() + 0.5

    def _set_result(self, message):
        if not self._stopping and self.is_mounted:
            self.query_one("#leverage-result", Static).update(emphasized(message))
            self.query_one("#leverage-result-region", VerticalScroll).scroll_home(
                animate=False
            )

    def _controls(self):
        busy = self._operation is not None
        arm = self.query_one("#leverage-arm", Button)
        venue = self.query_one("#leverage-venue", Select).value
        enabled = (self.snapshot_data or {}).get("enabled_venues")
        armed = (self.snapshot_data or {}).get("armed")
        known = isinstance(enabled, list) and type(armed) is bool
        active = known and armed and venue in enabled
        arm.label = (
            "Disarm " if active else "Arm " if known else "Arm state unknown "
        ) + ("10x" if venue == "jupiter-cli-10x" else "1000x")
        arm.disabled = busy or not known or self._read_failed
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
                self._read_failed = True
                self._apply_feed_visibility()
                self._controls()
                self.query_one(
                    "#leverage-price-comparison", Static
                ).tooltip = (
                    "Backend read failed; last displayed observations are retained."
                )
            else:
                self._read_failed = False
                self._apply_feed_visibility()
                self.snapshot_data = result.value
                comparison = self.snapshot_data.get("price_comparison", {})
                feeds = (
                    comparison.setdefault("feeds", {})
                    if isinstance(comparison, dict)
                    else {}
                )
                for source in ("jupiter", "coinbase"):
                    rows = (
                        feeds.setdefault(source, {}) if isinstance(feeds, dict) else {}
                    )
                    if not isinstance(rows, dict):
                        continue
                    for asset in ("BTC", "ZEC"):
                        row = rows.get(asset)
                        if (
                            isinstance(row, dict)
                            and row.get("asset") == asset
                            and type(row.get("price")) in (int, float)
                            and math.isfinite(row["price"])
                            and row["price"] > 0
                        ):
                            self._last_feeds[(source, asset)] = copy.deepcopy(row)
                        elif (source, asset) in self._last_feeds:
                            rows[asset] = {
                                **self._last_feeds[(source, asset)],
                                "fresh": False,
                            }
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
                preview = value.get("preview", {})
                checked = (
                    preview.get("checked", {}) if isinstance(preview, dict) else {}
                )
                if (
                    action == "preview"
                    and isinstance(checked, dict)
                    and checked.get("verification") == "current_observed_subset"
                ):
                    details.insert(
                        0,
                        "1000x MARKET · entry indicative · close unavailable in this client.",
                    )
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
            self._next_market_paint = time.monotonic() + 0.2
            self.paint_live_market()

    def paint_live_market(self):
        asset = self.query_one("#leverage-asset", Select).value
        venue = self.query_one("#leverage-venue", Select).value
        key = (asset, venue, tuple(self.feed_enabled.items()))
        if key != self._basis_key:
            self._basis_cache.clear()
            self._basis_key = key
        comparison = comparison_text(
            self.snapshot_data or {},
            asset,
            venue,
            self.clock(),
            self._basis_cache,
            self.feed_enabled,
        )
        widget = self.query_one("#leverage-price-comparison", Static)
        signature = (comparison.plain, str(comparison.spans))
        if getattr(self, "_comparison_signature", None) != signature:
            widget.update(comparison)
            self._comparison_signature = signature
        state = (self.snapshot_data or {}).get("price_comparison", {})
        state = state if isinstance(state, dict) else {}
        feeds = state.get("feeds", {}) if isinstance(state.get("feeds"), dict) else {}
        connected = (
            state.get("connected", {})
            if isinstance(state.get("connected"), dict)
            else {}
        )
        details = []
        for source in ("jupiter", "coinbase"):
            if not self.feed_enabled[source]:
                continue
            rows = feeds.get(source, {})
            row = rows.get(asset, {}) if isinstance(rows, dict) else {}
            row = row if isinstance(row, dict) else {}
            ages = []
            for label, field in (
                ("exchange", "exchange_at"),
                ("received", "received_at"),
            ):
                stamp = row.get(field)
                age = (
                    self.clock() - stamp
                    if type(stamp) in (int, float) and math.isfinite(stamp)
                    else None
                )
                ages.append(
                    f"{label} {age:.2f}s" if age is not None else f"{label} unknown"
                )
            details.append(
                f"{source}: {'connected' if connected.get(source) is True else 'disconnected or unknown'}, "
                + ", ".join(ages)
            )
        widget.tooltip = (
            (
                "Backend read failed; last displayed observations are retained. "
                if self._read_failed
                else ""
            )
            + "LIVE: fresh; DELAYED: up to 5s; STALE: longer delay or stopped. "
            + (
                "Basis retains its last valid pair. "
                if all(self.feed_enabled.values())
                else ""
            )
            + "; ".join(details)
        )

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
        asset = self.query_one("#leverage-asset", Select).value
        perf = data.get("performance", {})
        per_asset = perf.get("by_asset", {}) if isinstance(perf, dict) else {}
        perf = per_asset.get(asset, perf) if isinstance(per_asset, dict) else perf
        perf = perf if isinstance(perf, dict) else {}
        mtf = data.get("mtf_forward", {})
        mtf = mtf if isinstance(mtf, dict) else {}
        mtf_perf = mtf.get("performance", {})
        mtf_perf = mtf_perf if isinstance(mtf_perf, dict) else {}

        def number(value):
            return (
                "—"
                if value is None
                else f"{value:.3f}"
                if isinstance(value, float)
                else str(value)
            )

        coinbase_status = Text(
            f"Coinbase {asset} paper {_text(data.get('status'))}: settled {number(perf.get('settled'))} · open {number(perf.get('open'))} · correct {number(perf.get('correct'))} · hit {number(perf.get('hit_rate'))} · net bps {number(perf.get('mean_net_bps'))} "
        )
        coinbase_status.append(
            "●",
            style=(
                "green"
                if age is not None and 0 <= age <= 45
                else "yellow"
                if age is not None and 45 < age <= 90
                else "red"
            ),
        )
        coinbase_status.append(f" {freshness}")
        status = coinbase_status if self.feed_enabled["coinbase"] else Text()
        if self.feed_enabled["jupiter"]:
            status.append(
                f"\nMTF Jupiter ALL-ASSETS {_text(mtf.get('status', 'waiting'))}: settled {number(mtf_perf.get('settled'))} · open {number(mtf_perf.get('open'))} · pending {number(mtf_perf.get('pending_unscored'))} · correct {number(mtf_perf.get('direction_correct'))} · wins {number(mtf_perf.get('paper_wins'))} · hit {number(mtf_perf.get('hit_rate'))} · liquidated {number(mtf_perf.get('verified_liquidations'))} · gross underlying bps {number(mtf_perf.get('mean_unlevered_gross_bps'))}"
            )
        new = data.get("exit50_forward", {})
        new = new if isinstance(new, dict) else {}
        new_perf = (
            new.get("performance", {})
            if isinstance(new.get("performance"), dict)
            else {}
        )
        if self.feed_enabled["jupiter"]:
            status.append(
                f"\n10m +50% paper {_text(new.get('status', 'waiting'))}: open {number(new_perf.get('open'))} · close pending {number(new_perf.get('close_pending'))} · unscored {number(new_perf.get('unscored'))} · settled {number(new_perf.get('settled'))} · profitable {number(new_perf.get('profitable'))}"
            )
        widget = self.query_one("#leverage-status", Static)
        widget.update(status)
        widget.tooltip = (
            freshness
            + "; paper results are simulated."
            + (
                " MTF gross underlying return excludes fees and is not leveraged PnL."
                if self.feed_enabled["jupiter"]
                else ""
            )
        )

        self.query_one("#leverage-wallet", Static).update(emphasized(wallet_text(data)))
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
        new_assets = (
            new.get("assets", {}) if isinstance(new.get("assets"), dict) else {}
        )
        new_asset = (
            new_assets.get(asset, {}) if isinstance(new_assets.get(asset), dict) else {}
        )
        selected_policy = (
            new_asset.get("selected_policy", {})
            if isinstance(new_asset.get("selected_policy"), dict)
            else {}
        )
        indicators = (
            new_asset.get("indicators", {})
            if isinstance(new_asset.get("indicators"), dict)
            else {}
        )
        mtf_assets = (
            mtf.get("assets", {}) if isinstance(mtf.get("assets"), dict) else {}
        )
        mtf_asset = (
            mtf_assets.get(asset, {}) if isinstance(mtf_assets.get(asset), dict) else {}
        )
        frames = (
            mtf_asset.get("frames", {})
            if isinstance(mtf_asset.get("frames"), dict)
            else {}
        )
        quote_bars = data.get("quote_bars", {})
        bars = quote_bars.get(asset, {}) if isinstance(quote_bars, dict) else {}
        bars = bars if isinstance(bars, dict) else {}
        for kind in ("previous", "current"):
            button = self.query_one(f"#leverage-{kind}-bar", Button)
            label, color = bar_view(bars.get(kind), current=kind == "current")
            button.label = f"{asset} {label}"
            button.styles.background = color
            button.styles.color = bar_text_color(color)
            button.tooltip = "Sampled Jupiter oracle quotes; bar requires observations at each boundary and no gap over 5s. Body magnitude / trailing mean range of up to 20 completed 10m bars. Click for prices."
        previous_bar, current_bar = bars.get("previous"), bars.get("current")
        _tentative = (
            isinstance(previous_bar, dict)
            and isinstance(current_bar, dict)
            and type(previous_bar.get("open")) in (int, float)
            and type(previous_bar.get("close")) in (int, float)
            and type(current_bar.get("open")) in (int, float)
            and type(current_bar.get("close")) in (int, float)
            and previous_bar["close"] > previous_bar["open"]
            and current_bar["close"] > current_bar["open"]
        )
        tilts = self.query_one("#leverage-bar-tilts", Static)
        mtf_at = mtf.get("at")
        mtf_age = (
            self.clock() - mtf_at
            if type(mtf_at) in (int, float) and math.isfinite(mtf_at)
            else None
        )
        mtf_age_label = (
            f" · observer age {max(0, mtf_age):.0f}s"
            if mtf_age is not None
            else " · observer age unknown"
        )
        tilts.update(
            Text(mtf_tilt_text(mtf_asset.get("scores", {}), frames) + mtf_age_label)
        )
        tilts.tooltip = "Published 10m model component posterior P(up) minus its training baseline; n is the historical shape count. Not a forecast guarantee."
        shapes = " · ".join(
            f"{m}m {_text(frames.get(str(m), {}).get('shape')) if isinstance(frames.get(str(m)), dict) else '—'}"
            for m in (5, 10, 15, 20)
        )
        comparison = data.get("price_comparison", {})
        feeds = comparison.get("feeds", {}) if isinstance(comparison, dict) else {}
        coinbase = feeds.get("coinbase", {}) if isinstance(feeds, dict) else {}
        book = coinbase.get(asset, {}) if isinstance(coinbase, dict) else {}
        connected = (
            comparison.get("connected", {}) if isinstance(comparison, dict) else {}
        )
        book_fresh = (
            isinstance(book, dict)
            and isinstance(connected, dict)
            and connected.get("coinbase") is True
            and comparison.get("status") != "stopped"
            and type(comparison.get("at")) in (int, float)
            and math.isfinite(comparison["at"])
            and 0 <= self.clock() - comparison["at"] <= 2
            and book.get("asset") == asset
            and book.get("fresh", True) is True
            and all(
                type(book.get(key)) in (int, float)
                and math.isfinite(book[key])
                and 0 <= self.clock() - book[key] <= 3
                for key in ("exchange_at", "received_at")
            )
        )
        visible_book = (
            f"best bid size {_text(book.get('bid_size'))} / ask size {_text(book.get('ask_size'))}"
            if book_fresh
            else "waiting for fresh synced book"
        )
        roe = new_asset.get("roe")
        roe_text = (
            f"{roe * 100:.2f}%"
            if type(roe) in (int, float) and math.isfinite(roe)
            else "—"
        )
        indicator_line = (
            f"Closed 1m EMA9 {_text(indicators.get('ema9'))} / EMA21 {_text(indicators.get('ema21'))} · MACD {_text(indicators.get('macd'))} / signal {_text(indicators.get('macd_signal'))} · BOP SMA3 price proxy {_text(indicators.get('bop_sma3'))}\n"
            if self.feed_enabled["coinbase"]
            else ""
        )
        indicator_note = (
            f"EMA/MACD {_text(new_asset.get('indicator_note', 'waiting for bootstrap'))}; seed {_text(new_asset.get('indicator_seed_s'))}.\nCoinbase {visible_book} · visible liquidity, not order counts."
            if self.feed_enabled["coinbase"]
            else ""
        )
        self.query_one("#leverage-exit50", Static).update(
            Text(
                f"10m reversal {asset}: {_text(new_asset.get('signal', 'waiting'))} · policy {_text(selected_policy.get('family'))}/{_text(selected_policy.get('filter'))} ({_text(selected_policy.get('selection_status'))}) · model {_text(new_asset.get('model_sha256'), limit=64)} · score {_text(new_asset.get('score'))} (context score; not a probability)\n"
                f"Completed shapes: {shapes}\n"
                f"{indicator_line}"
                f"Paper 1000x: {_text(new_asset.get('position_status', 'waiting'))} · modeled collateral ROE {roe_text} · target +50% · intent {_text(new_asset.get('intent'))} · min age 15s / close delay 10s\nAfter modeled trade fees; chain/keeper fees excluded. Oracle proxy; no verified fill.\n{indicator_note}"
            )
        )
        scores = mtf_asset.get("scores", {})
        contexts = []
        for minutes in (5, 10, 15, 20):
            frame = frames.get(str(minutes), {}) if isinstance(frames, dict) else {}
            score = scores.get(str(minutes), {}) if isinstance(scores, dict) else {}
            frame = frame if isinstance(frame, dict) else {}
            score = score if isinstance(score, dict) else {}
            components = score.get("components", []) if isinstance(score, dict) else []
            components = components if isinstance(components, list) else []
            support = (
                ", ".join(
                    f"{c.get('minutes')}m n={c.get('n')}"
                    for c in components
                    if isinstance(c, dict)
                )
                or "waiting"
            )
            contexts.append(
                f"{minutes}m: shape {_text(frame.get('shape'))} · down score {_text(score.get('score_down'))} · support {support}"
            )
        self.query_one("#leverage-performance", Static).update(
            Text(
                f"MTF completed shapes / model · {asset} · selected {_summary(mtf_asset.get('selected', {}))}\n"
                + "\n".join(contexts)
            )
        )
        table = self.query_one("#leverage-strategies", DataTable)
        strategy_rows = [
            row
            for row in data.get("strategies", [])
            if isinstance(row, dict)
            and row.get("asset") == asset
            and (interval == 0 or row.get("interval_minutes") == interval)
        ]
        strategies_changed = self._table_rows.get("strategies") != strategy_rows
        if strategies_changed:
            table.clear()
            self._table_rows["strategies"] = copy.deepcopy(strategy_rows)
        for index, row in enumerate(data.get("strategies", [])):
            if (
                not isinstance(row, dict)
                or row.get("asset") != asset
                or (interval != 0 and row.get("interval_minutes") != interval)
            ):
                continue
            if not strategies_changed:
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
        real_rows = [
            row
            for row in data.get("positions", [])
            if isinstance(row, dict) and row.get("asset") == asset
        ]
        paper_source = new.get("positions", [])
        paper_rows = (
            [
                row
                for row in paper_source
                if isinstance(row, dict) and row.get("asset") == asset
            ]
            if isinstance(paper_source, list)
            else []
        )
        position_rows = {"venue": real_rows, "paper": paper_rows}
        positions_changed = self._table_rows.get("positions") != position_rows
        if positions_changed:
            positions.clear()
            self._table_rows["positions"] = copy.deepcopy(position_rows)
        current = set()
        for row in real_rows:
            identity = row.get("id", row.get("position_id"))
            if not isinstance(identity, str) or not identity or identity in current:
                continue
            current.add(identity)
            if positions_changed:
                positions.add_row(
                    *[
                        Text(_text(row.get(key)))
                        for key in ("asset", "venue", "side", "status", "pnl_usd")
                    ],
                    Text(identity),
                    key=f"venue:{identity}",
                )
        seen_paper = set()
        for row in paper_rows:
            identity = row.get("id")
            if not isinstance(identity, str) or not identity or identity in seen_paper:
                continue
            seen_paper.add(identity)
            roe = row.get("roe")
            value = (
                f"{roe * 100:+.2f}% / +50%"
                if type(roe) in (int, float) and math.isfinite(roe)
                else "— / +50%"
            )
            if positions_changed:
                positions.add_row(
                    Text(asset),
                    Text("PAPER"),
                    Text(_text(row.get("side"))),
                    Text(_text(row.get("status"))),
                    Text(value),
                    Text(identity),
                    key=f"paper:{identity}",
                )
        if self.selected_position not in current:
            self.selected_position = None
        elif positions_changed:
            positions.move_cursor(
                row=positions.get_row_index(f"venue:{self.selected_position}")
            )
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
        key = str(event.row_key.value)
        self.selected_position = (
            key.removeprefix("venue:") if key.startswith("venue:") else None
        )
        if key.startswith("paper:"):
            self._set_result(
                "Paper observation only; no live position is selected for Close."
            )
        self._controls()

    @on(Button.Pressed)
    def button_pressed(self, event):
        event.stop()
        name = event.button.id
        if name in ("leverage-previous-bar", "leverage-current-bar"):
            asset = self.query_one("#leverage-asset", Select).value
            source = (self.snapshot_data or {}).get("quote_bars", {})
            bars = source.get(asset, {}) if isinstance(source, dict) else {}
            kind = "previous" if name == "leverage-previous-bar" else "current"
            bar = bars.get(kind) if isinstance(bars, dict) else None
            self._set_result(
                f"{asset} {kind} 10m bar: {_summary(bar) if isinstance(bar, dict) else 'waiting for causal observations'}"
            )
        elif name == "leverage-return":
            self.action_return_to_oracle()
        elif name == "leverage-refresh":
            self.action_refresh()
        elif name == "leverage-arm":
            if (
                self._read_failed
                or not isinstance(
                    (self.snapshot_data or {}).get("enabled_venues"), list
                )
                or type((self.snapshot_data or {}).get("armed")) is not bool
            ):
                self._set_result("Arm state unavailable; refresh before changing it.")
                return
            venue = self.query_one("#leverage-venue", Select).value
            active = (
                self.snapshot_data["armed"]
                and venue in self.snapshot_data["enabled_venues"]
            )
            self.preview_id = None
            self._dispatch(
                "set_venue_armed",
                (
                    venue,
                    not active,
                    self.query_one("#leverage-collateral", Input).value,
                ),
            )
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

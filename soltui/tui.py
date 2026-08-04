"""Textual TUI: five tabs over the backtester.

    python3 -m soltui.tui

Tabs: Settings, Strategies, Signals, Backtest, Execute (dry-run only).

All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`,
`status`); this file is presentation and wiring. That split is what lets the
logic be tested without driving a terminal, and it mirrors how
`netdnsmonitor/app.py` stays thin over tested modules.

The Execute tab is **dry-run only**. See `paper.py` for why there is no order
path anywhere in this package.
"""

from __future__ import annotations

from typing import Any

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from backtester.core import indicators as ind
from backtester.core.strategies import FAMILY, REGISTRY, build

from .config import INTERVALS, Settings, load_settings, save_settings
from .paper import MODE_LABEL, PaperSession, start_session
from .roster import Roster, RosterError, available_strategies
from .signals import (
    SIGNAL_GROUPS,
    SignalDefaults,
    SignalError,
    coerce,
    from_dict,
    mapped_strategies,
    merged_params,
)
from .runner import SweepRunner, engine_config, load_arrays
from .status import AppState, Phase, build_title, format_pct

# One-line description per signal family, for the Signals tab. Sourced from the
# taxonomy in research/STRATEGIES.md so the two do not drift into disagreement.
FAMILY_NOTES = {
    "baseline": "The null hypothesis. Any strategy that cannot beat it is a cost-generating machine.",
    "trend": "Bets that direction persists. Fails in chop, where every oscillation is a whipsaw pair.",
    "momentum": "Sign of past return predicts the next period. Its risk is momentum crashes.",
    "regime-filter": "Answers 'bull or bear'. Its value is avoiding drawdowns, not making returns.",
    "breakout": "Bets on range expansion. ~30-35% win rate; a few large winners pay for the false starts.",
    "oscillator-reversion": "Buys exhaustion. In a strong trend the reading stays pinned and it gets run over.",
    "mean-reversion": "Buys distance from a mean. Fails when the mean itself shifts.",
    "volume-flow": "Reads participation, not price. Price-blind, which is why it pairs well.",
    "risk-overlay": "Changes position size, not direction. Reshapes the equity curve.",
}

# Indicator functions exposed on the Signals tab, with their equations.
SIGNAL_REFERENCE = [
    ("SMA(n)", "mean of last n closes", "trend"),
    ("EMA(span)", "alpha=2/(span+1), recursive", "trend"),
    ("RSI(p)", "100 - 100/(1+RS), RS=avgGain/avgLoss (Wilder)", "oscillator-reversion"),
    ("MACD(f,s,sig)", "EMA(f)-EMA(s), signal=EMA(sig) of that line", "trend"),
    ("Bollinger(n,k)", "mid +/- k*stdev(ddof=0); bandwidth=(u-l)/mid", "mean-reversion"),
    ("ATR(p)", "Wilder smoothing of max(H-L,|H-pC|,|L-pC|)", "breakout"),
    ("Stochastic(k,d)", "%K=(c-min)/(max-min)*100, %D=SMA(d) of %K", "oscillator-reversion"),
    ("OBV", "cumulative sign(dC) * volume", "volume-flow"),
    ("VWAP(n)", "sum(TP*V)/sum(V), TP=(H+L+C)/3", "mean-reversion"),
    ("Z-score(n)", "(c - mean)/stdev(ddof=1)", "mean-reversion"),
    ("ROC(n)", "c_t/c_{t-n} - 1", "momentum"),
    ("RealisedVol(n)", "stdev(log returns)*sqrt(periods_per_year)", "risk-overlay"),
]


class SolTuiApp(App):
    """The five-tab console."""

    TITLE = "soltui — SOL strategy console"
    SUB_TITLE = "dry-run only · no live order path"
    CSS = """
    #execute-banner {
        background: $warning 30%;
        color: $text;
        border: heavy $warning;
        padding: 1;
        margin-bottom: 1;
    }
    #indicator { color: $accent; padding: 0 1; }
    .form-row { height: 3; }
    .form-row Label { width: 22; content-align: right middle; padding-right: 1; }
    .hint { color: $text-muted; }
    DataTable { height: 1fr; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "run_backtest", "Run backtest"),
        ("c", "cancel", "Cancel sweep"),
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or load_settings()
        self.roster = Roster.from_list(
            [{"name": n} for n in self.settings.enabled_strategies]
        ) or Roster.default()
        if len(self.roster) == 0:
            self.roster = Roster.default()
        self.signals = from_dict(self.settings.signal_defaults)
        self.state = AppState()
        self.runner = SweepRunner(self.state)
        self.session: PaperSession | None = None

    # -- layout ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Build the tab set."""
        yield Header()
        yield Static(build_title(self.state), id="indicator")
        with TabbedContent(initial="tab-backtest"):
            with TabPane("Settings", id="tab-settings"):
                yield from self._settings_pane()
            with TabPane("Strategies", id="tab-strategies"):
                yield from self._strategies_pane()
            with TabPane("Signals", id="tab-signals"):
                yield from self._signals_pane()
            with TabPane("Backtest", id="tab-backtest"):
                yield from self._backtest_pane()
            with TabPane("Execute", id="tab-execute"):
                yield from self._execute_pane()
        yield Footer()

    def _settings_pane(self) -> ComposeResult:
        """Editable settings form."""
        with VerticalScroll():
            yield Static(
                "Saved to ~/.config/soltui/. Mode is dry-run only: this build has "
                "no live order path to select.",
                classes="hint",
            )
            for field_name, label in (
                ("asset", "Asset"),
                ("start", "Start date"),
                ("end", "End date (blank = all)"),
                ("capital", "Capital (USD)"),
                ("fee_bps", "Taker fee (bps)"),
                ("slippage_bps", "Slippage (bps)"),
                ("fill_delay", "Fill delay (bars)"),
                ("cpcv_groups", "CPCV blocks"),
                ("cpcv_k", "CPCV k (blocks/path)"),
            ):
                with Horizontal(classes="form-row"):
                    yield Label(f"{label}:")
                    yield Input(
                        value=str(getattr(self.settings, field_name)),
                        id=f"set-{field_name}",
                    )
            with Horizontal(classes="form-row"):
                yield Label("Interval:")
                yield Select(
                    [(i, i) for i in INTERVALS],
                    value=self.settings.interval,
                    id="set-interval",
                    allow_blank=False,
                )
            with Horizontal(classes="form-row"):
                yield Button("Save settings", variant="primary", id="btn-save")
                yield Static("", id="settings-status")

    def _strategies_pane(self) -> ComposeResult:
        """Add/remove strategies from the roster."""
        with Vertical():
            yield Static(
                "Left: every registered strategy. Right: your roster — what the "
                "Backtest tab will sweep.",
                classes="hint",
            )
            with Horizontal():
                yield DataTable(id="available-table")
                yield DataTable(id="roster-table")
            with Horizontal(classes="form-row"):
                yield Label("Params (k=v):")
                yield Input(placeholder="fast=20 slow=50", id="strategy-params")
            with Horizontal(classes="form-row"):
                yield Button("Add selected →", variant="success", id="btn-add")
                yield Button("← Remove selected", variant="error", id="btn-remove")
                yield Button("Reset to default", id="btn-reset-roster")
            yield Static("", id="roster-status")

    def _signals_pane(self) -> ComposeResult:
        """Editable signal parameters, grouped by indicator.

        These are DEFAULTS. A per-entry value pinned in the Strategies tab wins,
        so editing here never silently overwrites a deliberate choice.
        """
        with VerticalScroll():
            yield Static(
                "Edit signal parameters. These are defaults applied when a strategy "
                "is added without explicit params — an explicit value in the "
                "Strategies tab always wins.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Save signals", variant="primary", id="btn-save-signals")
                yield Button("Reset to defaults", id="btn-reset-signals")
                yield Static("", id="signals-status")
            for group, names in SIGNAL_GROUPS:
                yield Static(f"\n{group}", classes="hint")
                for name in names:
                    with Horizontal(classes="form-row"):
                        yield Label(f"{name}:")
                        yield Input(
                            value=str(getattr(self.signals, name)),
                            id=f"sig-{name}",
                        )
            yield Static(
                "\nReference — equations as implemented in "
                "backtester/core/indicators.py:",
                classes="hint",
            )
            yield DataTable(id="signals-table")
            yield Static("\nFamily behaviour — when each kind fails:", classes="hint")
            yield DataTable(id="families-table")

    def _backtest_pane(self) -> ComposeResult:
        """Run a CPCV sweep over the roster and show the distribution."""
        with Vertical():
            yield Static(
                "CPCV: each strategy is evaluated across C(blocks,k) regime-mixed "
                "paths, not one split. Read IQR and % paths positive, not just the "
                "median.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Run backtest (r)", variant="primary", id="btn-run")
                yield Button("Cancel (c)", variant="error", id="btn-cancel")
                yield Static("", id="backtest-status")
            yield DataTable(id="results-table")

    def _execute_pane(self) -> ComposeResult:
        """Dry-run replay. The banner is not decoration."""
        with Vertical():
            yield Static(MODE_LABEL, id="execute-banner")
            yield Static(
                "This replays a historical simulation bar by bar and shows the fills "
                "a strategy WOULD have made. There is no order path in this package: "
                "no keys, no signing, no venue client.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Label("Strategy:")
                yield Select([], id="exec-strategy", allow_blank=True)
                yield Button("Start dry run", variant="primary", id="btn-paper-start")
            with Horizontal(classes="form-row"):
                yield Button("Step +1", id="btn-step1")
                yield Button("Step +25", id="btn-step25")
                yield Button("To end", id="btn-step-end")
                yield Button("Reset", id="btn-paper-reset")
            yield Static("No dry run started.", id="exec-summary")
            yield DataTable(id="fills-table")

    # -- lifecycle -------------------------------------------------------

    def on_mount(self) -> None:
        """Populate tables and start the indicator refresh."""
        avail = self.query_one("#available-table", DataTable)
        avail.add_columns("strategy", "family")
        avail.cursor_type = "row"
        for name, family in available_strategies():
            avail.add_row(name, family, key=name)

        roster_t = self.query_one("#roster-table", DataTable)
        roster_t.add_columns("in roster", "family", "warm-up")
        roster_t.cursor_type = "row"
        self._refresh_roster_table()

        sig = self.query_one("#signals-table", DataTable)
        sig.add_columns("signal", "equation", "family")
        for name, eq, fam in SIGNAL_REFERENCE:
            sig.add_row(name, eq, fam)

        fam_t = self.query_one("#families-table", DataTable)
        fam_t.add_columns("family", "what it is / when it fails")
        for fam, note in sorted(FAMILY_NOTES.items()):
            fam_t.add_row(fam, note)

        res = self.query_one("#results-table", DataTable)
        res.add_columns(
            "strategy", "family", "median Sharpe", "IQR", "% paths +",
            "median ret", "trades",
        )

        fills = self.query_one("#fills-table", DataTable)
        fills.add_columns(
            "bar", "when", "side", "reason", "price", "units", "cost", "equity"
        )

        self._refresh_exec_choices()
        self.set_interval(self.settings.poll_interval_seconds, self._tick)

    def _tick(self) -> None:
        """Refresh the in-app indicator line. Mirrors the menu-bar title exactly.

        Defensive on purpose: a `set_interval` timer can fire after the screen has
        started tearing down, at which point `query_one` raises NoMatches and
        takes the whole app with it. Resolving through `query()` and no-oping when
        the widget has gone is the difference between a clean exit and a traceback
        on every quit.
        """
        indicator = self.query("#indicator")
        if not indicator:
            return
        indicator.first(Static).update(build_title(self.state))

        if self.runner.running:
            status = self.query("#backtest-status")
            if status:
                status.first(Static).update(
                    f"{self.state.done}/{self.state.total} — "
                    f"{self.state.remaining} left"
                )

    # -- settings --------------------------------------------------------

    @on(Button.Pressed, "#btn-save")
    def _save(self) -> None:
        """Read the form, validate, persist."""
        status = self.query_one("#settings-status", Static)
        try:
            new = Settings(**{**self.settings.to_dict(), **self._read_form()})
            path = save_settings(new)
            self.settings = new
            status.update(f"saved → {path}")
        except Exception as exc:  # noqa: BLE001 - surfaced to the user verbatim
            status.update(f"[red]{type(exc).__name__}: {exc}[/]")

    def _read_form(self) -> dict[str, Any]:
        """Coerce form inputs to their field types."""
        casts: dict[str, Any] = {
            "asset": str, "start": str, "end": str, "capital": float,
            "fee_bps": float, "slippage_bps": float, "fill_delay": int,
            "cpcv_groups": int, "cpcv_k": int,
        }
        out: dict[str, Any] = {}
        for name, cast in casts.items():
            raw = self.query_one(f"#set-{name}", Input).value.strip()
            out[name] = cast(raw) if raw or cast is str else getattr(self.settings, name)
        out["interval"] = str(self.query_one("#set-interval", Select).value)
        out["enabled_strategies"] = [e.name for e in self.roster]
        return out

    # -- roster ----------------------------------------------------------

    def _refresh_roster_table(self) -> None:
        """Redraw the roster side."""
        t = self.query_one("#roster-table", DataTable)
        t.clear()
        for e in self.roster:
            t.add_row(e.label, e.family, str(e.warmup), key=e.label)

    def _refresh_exec_choices(self) -> None:
        """Keep the Execute strategy picker in sync with the roster."""
        sel = self.query_one("#exec-strategy", Select)
        sel.set_options([(e.label, e.label) for e in self.roster])

    def _parse_params(self) -> dict[str, Any]:
        """Parse 'fast=20 slow=50' into typed kwargs."""
        raw = self.query_one("#strategy-params", Input).value.strip()
        params: dict[str, Any] = {}
        for token in raw.split():
            if "=" not in token:
                raise RosterError(f"expected key=value, got {token!r}")
            k, v = token.split("=", 1)
            try:
                params[k] = int(v)
            except ValueError:
                try:
                    params[k] = float(v)
                except ValueError:
                    params[k] = v
        return params

    @on(Button.Pressed, "#btn-add")
    def _add(self) -> None:
        """Add the highlighted available strategy to the roster."""
        status = self.query_one("#roster-status", Static)
        table = self.query_one("#available-table", DataTable)
        try:
            row = table.get_row_at(table.cursor_row)
            name = str(row[0])
            entry = self.roster.add(
                name, **merged_params(name, self.signals, self._parse_params())
            )
            self._refresh_roster_table()
            self._refresh_exec_choices()
            status.update(f"added {entry.label} (warm-up {entry.warmup} bars)")
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")

    @on(Button.Pressed, "#btn-remove")
    def _remove(self) -> None:
        """Remove the highlighted roster entry."""
        status = self.query_one("#roster-status", Static)
        table = self.query_one("#roster-table", DataTable)
        try:
            row = table.get_row_at(table.cursor_row)
            removed = self.roster.remove(str(row[0]))
            self._refresh_roster_table()
            self._refresh_exec_choices()
            status.update(f"removed {removed.label}")
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")

    @on(Button.Pressed, "#btn-reset-roster")
    def _reset_roster(self) -> None:
        """Restore the backtester's default comparison set."""
        self.roster = Roster.default()
        self._refresh_roster_table()
        self._refresh_exec_choices()
        self.query_one("#roster-status", Static).update("roster reset to default")


    # -- signals ---------------------------------------------------------

    @on(Button.Pressed, "#btn-save-signals")
    def _save_signals(self) -> None:
        """Read the signal form, validate, persist into settings."""
        status = self.query_one("#signals-status", Static)
        try:
            updated = SignalDefaults(**{
                name: coerce(
                    name, self.query_one(f"#sig-{name}", Input).value, self.signals
                )
                for _, names in SIGNAL_GROUPS
                for name in names
            })
            self.signals = from_dict(updated.to_dict())
            self.settings.signal_defaults = self.signals.to_dict()
            path = save_settings(self.settings)
            status.update(
                f"saved → {path} · affects {len(mapped_strategies())} strategies"
            )
        except Exception as exc:  # noqa: BLE001 - shown verbatim to the user
            # Deliberately broad: SignalError is the expected case, but a form
            # can also yield ValueError/TypeError, and a UI must not die on
            # bad input. (SignalError was previously listed alongside
            # Exception, which was redundant and implied false specificity.)
            status.update(f"[red]{exc}[/]")

    @on(Button.Pressed, "#btn-reset-signals")
    def _reset_signals(self) -> None:
        """Restore the backtester's shipped signal values."""
        self.signals = SignalDefaults()
        for _, names in SIGNAL_GROUPS:
            for name in names:
                self.query_one(f"#sig-{name}", Input).value = str(
                    getattr(self.signals, name)
                )
        self.query_one("#signals-status", Static).update("reset to shipped defaults")

    # -- backtest --------------------------------------------------------

    def action_run_backtest(self) -> None:
        """Keyboard binding for running a sweep."""
        self._run()

    def action_cancel(self) -> None:
        """Keyboard binding for cancelling."""
        self.runner.cancel()

    @on(Button.Pressed, "#btn-cancel")
    def _cancel_pressed(self) -> None:
        """Ask the worker to stop at the next configuration boundary."""
        self.runner.cancel()
        self.query_one("#backtest-status", Static).update("cancelling…")

    @on(Button.Pressed, "#btn-run")
    def _run(self) -> None:
        """Start a CPCV sweep over the roster."""
        status = self.query_one("#backtest-status", Static)
        try:
            self.runner.start(self.roster, self.settings, on_done=self._sweep_done)
            status.update("running…")
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")

    def _sweep_done(self, outcome: Any) -> None:
        """Worker callback: hand results back to the UI thread."""
        self.call_from_thread(self._render_results, outcome)

    def _render_results(self, outcome: Any) -> None:
        """Fill the results table, best median Sharpe first."""
        table = self.query_one("#results-table", DataTable)
        table.clear()
        for r in outcome.ranked():
            table.add_row(
                r.label, r.family, f"{r.median_sharpe:+.3f}", f"{r.iqr:.3f}",
                f"{r.frac_positive:.0%}", format_pct(r.median_return), str(r.trades),
            )
        skipped = [r for r in outcome.rows if not r.evaluable]
        msg = f"done — {len(outcome.evaluable)} evaluable, {len(outcome.positive)} positive"
        if outcome.cancelled:
            msg = "cancelled — partial results shown"
        if outcome.error:
            msg = f"[red]{outcome.error.splitlines()[0]}[/]"
        if skipped:
            msg += f" · {len(skipped)} skipped (warm-up or trade floor)"
        self.query_one("#backtest-status", Static).update(msg)

    # -- execute (dry run) -----------------------------------------------

    @on(Button.Pressed, "#btn-paper-start")
    @work(thread=True, exclusive=True)
    def _paper_start(self) -> None:
        """Run one backtest and open a replay cursor over it."""
        label = self.query_one("#exec-strategy", Select).value
        summary = self.query_one("#exec-summary", Static)
        if not label:
            self.call_from_thread(summary.update, "[red]pick a strategy first[/]")
            return
        entry = next((e for e in self.roster if e.label == label), None)
        if entry is None:
            self.call_from_thread(summary.update, "[red]strategy left the roster[/]")
            return
        try:
            arrays = load_arrays(self.settings)
            session = start_session(
                build(entry.name, **entry.params), arrays, engine_config(self.settings)
            )
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(summary.update, f"[red]{type(exc).__name__}: {exc}[/]")
            return
        self.session = session
        self.state.phase = Phase.PAPER
        self.call_from_thread(self._refresh_paper)

    @on(Button.Pressed, "#btn-step1")
    def _step1(self) -> None:
        """Advance one bar."""
        self._step(1)

    @on(Button.Pressed, "#btn-step25")
    def _step25(self) -> None:
        """Advance 25 bars."""
        self._step(25)

    @on(Button.Pressed, "#btn-step-end")
    def _step_end(self) -> None:
        """Jump to the final bar."""
        if self.session:
            self.session.seek_end()
            self._refresh_paper()

    @on(Button.Pressed, "#btn-paper-reset")
    def _paper_reset(self) -> None:
        """Rewind the replay."""
        if self.session:
            self.session.reset()
            self._refresh_paper()

    def _step(self, bars: int) -> None:
        """Advance the cursor and redraw."""
        if self.session is None:
            self.query_one("#exec-summary", Static).update(
                "[red]start a dry run first[/]"
            )
            return
        self.session.advance(bars)
        self._refresh_paper()

    def _refresh_paper(self) -> None:
        """Redraw the replay summary and the intended-fills table."""
        if self.session is None:
            return
        s = self.session.summary()
        self.state.paper_return = self.session.pnl
        self.state.paper_fills = self.session.fill_count
        self.query_one("#exec-summary", Static).update(
            f"bar {s['bar']}/{s['bars_total']}  {s['when']}   "
            f"equity {s['equity']:,.2f}   P&L {format_pct(s['pnl'])}   "
            f"exposure {s['exposure']:.2f}   fills {s['fills']}   "
            f"live orders placed: {s['live_orders_placed']}"
        )
        table = self.query_one("#fills-table", DataTable)
        table.clear()
        for f in self.session.intended_fills()[-200:]:
            table.add_row(
                str(f.bar_index), f.when, f.side, f.reason, f"{f.price:,.2f}",
                f"{f.units:,.4f}", f"{f.cost:,.2f}", f"{f.equity_after:,.2f}",
            )


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python3 -m soltui.tui`."""
    SolTuiApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

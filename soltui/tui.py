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
    TextArea,
)

from backtester.core import indicators as ind
from backtester.core.strategies import FAMILY, REGISTRY, build

from . import analyze as analyze_mod
from . import cumulative as cumulative_mod
from . import docs_browser
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

# The Research tab's content. Kept here as data rather than fetched or computed:
# these are the questions each driver answers and what it actually established,
# and both are stable facts about the study. Figures match docs/SCRIPTS.md and
# research/CROSS-ASSET-TRANSFER.md; `python3 research/verify_numbers.py` is the
# gate that keeps the underlying documents honest.
RESEARCH_DRIVERS = [
    ("research/cpcv_sweep.py", "Is a configuration any good?",
     "PBO 0.700 at both daily horizons vs a 0.500 noise line"),
    ("research/cross_asset_cpcv.py", "Does it transfer to another coin?",
     "All 10 top-5 transfers to DOGE/ZEC degraded; none improved"),
    ("research/perturb.py", "Was it fitted to noise?",
     "Pairs are ~2.6x more parameter-sensitive than long-horizon singles"),
    ("research/geometry.py", "Is the leaderboard an artifact of block count?",
     "8->9 blocks moved the best pair -0.441, more than any parameter"),
    ("research/decide.py", "What does each rule say right now?",
     "Targets provably match what the engine would have acted on"),
    ("research/dso_audit.py", "Which results are below the evidence floor?",
     "BTC's rank-1 ou_reversion sits on 6 trades"),
    ("research/sweep.py", "The single 70/30 split it all replaced",
     "In-sample window ended on the highest close in the series"),
    ("research/verify_numbers.py", "Do the docs match their CSVs?",
     "950 figures checked; CI fails the build on drift"),
    ("research/turnover_table.py", "One comparable turnover table",
     "DOGE 3.44% leads SOL 3.32% on a single-timestamp pull"),
]

RESEARCH_FINDINGS = [
    "In-sample rank is anti-informative: PBO 0.700, and Spearman rho(IS, OOS) is "
    "-0.419 at the medium horizon.",
    "The five recommended configurations do not transfer. Only #3 and #4 stayed "
    "positive on all three assets; #2 is 100% positive on SOL and 0% on DOGE "
    "across the same 15 paths.",
    "Path counts are 15 or 21, never the nominal 28 — only buy_and_hold, which "
    "needs no warm-up, reached 28.",
    "The dataset explains more than the strategy: the same 25 strategies score "
    "25/25 on BTC daily and 0/25 on SOL hourly.",
    "Buy-and-hold medians +0.534 on SOL with zero parameters, 2nd of 25 — and on "
    "ZEC it beat all five recommended configurations.",
]

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
    TabbedContent { height: 1fr; }
    #editor-panel {
        height: 16;
        border-top: solid $accent;
    }
    #editor-panel TextArea { height: 1fr; }
    """
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "run_backtest", "Run backtest"),
        ("c", "cancel", "Cancel sweep"),
        ("o", "open_doc", "Open in editor"),
        ("ctrl+s", "save_doc", "Save"),
        ("ctrl+e", "toggle_editor", "Show/hide editor"),
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
        # Populated when the Docs tab composes. Held on the app rather than
        # re-read per keystroke: the catalogue is ~270 rows and filtering it in
        # memory is what keeps the filter box responsive.
        self._docs: list[docs_browser.DocEntry] = []
        self._docs_loaded = False
        # The catalogue path currently shown in the Docs viewer, and whether
        # `read_document` actually returned real text for it (vs a
        # placeholder for a binary/oversized file) -- the Save button trusts
        # this, not the cheap per-row "editable" column, before writing.
        self._docs_current_path: str | None = None
        self._docs_current_editable = False
        # The row the DataTable cursor is on, kept independently of what is
        # actually loaded in the viewer -- the "o" binding opens this even if
        # the click that highlighted it didn't also fire a load.
        self._docs_highlighted_path: str | None = None
        # The text as it was on disk when _docs_current_path was loaded.
        # Compared against the live TextArea to know whether there is an
        # unsaved edit -- without this, navigating to a different file
        # silently overwrote whatever was being edited, with no warning.
        self._docs_loaded_text = ""
        self._cumulative_loaded = False

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
            with TabPane("Analyze", id="tab-analyze"):
                yield from self._analyze_pane()
            with TabPane("Cumulative", id="tab-cumulative"):
                yield from self._cumulative_pane()
            with TabPane("Research", id="tab-research"):
                yield from self._research_pane()
            with TabPane("Docs", id="tab-docs"):
                yield from self._docs_pane()
        yield from self._editor_pane()
        yield Footer()

    def _editor_pane(self) -> ComposeResult:
        """The one file viewer/editor, visible under every tab.

        A single shared instance rather than one per tab: a tab switch must
        never lose whatever is loaded here, and a strategy source file opened
        from the Strategies tab needs somewhere to land that the Docs tab
        doesn't own. "ctrl+e" toggles `#editor-panel.display` to hide it.
        """
        with Vertical(id="editor-panel"):
            with Horizontal(classes="form-row"):
                yield Static("select a file to open it here", id="docs-view-status")
                yield Button("Save (^s)", id="docs-save", variant="primary",
                             disabled=True)
            yield TextArea("", id="docs-view", read_only=True, show_line_numbers=True)

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


    @on(TabbedContent.TabActivated)
    def _populate_on_first_view(self, event: TabbedContent.TabActivated) -> None:
        """Fill the scanning tabs the first time each is opened.

        Deliberately not `on_mount`: Cumulative reads every CSV in
        research/results/ and Docs holds a ~270-row catalogue, and doing both at
        startup would delay the first paint for tabs the user may never open.
        Repeat activations are cheap — Docs filters in memory, and Cumulative has
        an explicit Reload button for when results change underneath it.
        """
        pane = event.pane.id if event.pane else ""
        if pane == "tab-cumulative" and not self._cumulative_loaded:
            self._cumulative_loaded = True
            self._refresh_cumulative()
        elif pane == "tab-docs" and not self._docs_loaded:
            self._docs_loaded = True
            self._refresh_docs()

    # -- Analyze: any coin, any moment -----------------------------------

    def _analyze_pane(self) -> ComposeResult:
        """Replay every rule up to a chosen timestamp, for a chosen coin.

        Distinct from the Signals tab, which reads the *latest* bar of the
        configured asset. Here the coin and the moment are both inputs.
        """
        pairs = analyze_mod.available_assets()
        options = [(f"{a} {i}", f"{a}|{i}") for a, i in pairs]
        with VerticalScroll():
            yield Static(
                "Every registered strategy replayed from the start of history up to "
                "the chosen bar. Strategies are path-dependent, so the series is "
                "truncated first and replayed — the answer is what the rule would "
                "have decided then, not what it decides now.",
                classes="hint",
            )
            if not options:
                yield Static(
                    "No cached series. Fetch one:\n"
                    "  python3 -m backtester.core.fetch --asset SOL --interval 1d "
                    "--start 2021-01-01",
                    id="analyze-empty",
                )
                return
            with Horizontal(classes="form-row"):
                yield Label("Coin / interval")
                yield Select(options, value=options[0][1], id="analyze-asset")
            with Horizontal(classes="form-row"):
                yield Label("As of (UTC)")
                yield Input(placeholder="YYYY-MM-DD or YYYY-MM-DD HH:MM "
                                        "(blank = last bar)", id="analyze-when")
            with Horizontal(classes="form-row"):
                yield Button("Analyze", id="analyze-run", variant="primary")
            yield Static("", id="analyze-headline")
            table = DataTable(id="analyze-table")
            table.add_columns("strategy", "family", "action", "holding -> wants",
                              "warmup", "bars")
            yield table

    @on(Button.Pressed, "#analyze-run")
    def _run_analysis(self) -> None:
        sel = self.query_one("#analyze-asset", Select).value
        if not isinstance(sel, str):
            return
        asset, _, interval = sel.partition("|")
        raw = self.query_one("#analyze-when", Input).value.strip()
        head = self.query_one("#analyze-headline", Static)
        try:
            when = analyze_mod.parse_as_of(raw) if raw else None
            result = analyze_mod.analyse(asset, interval, as_of=when)
        except (ValueError, FileNotFoundError, KeyError) as exc:
            head.update(f"[b]could not analyse:[/b] {exc}")
            return
        head.update(result.headline + ("" if result.truncated
                                       else "   (latest bar)"))
        table = self.query_one("#analyze-table", DataTable)
        table.clear()
        for d in result.decisions:
            table.add_row(d.name, d.family, d.action, d.detail,
                          str(d.warmup), str(d.bars))

    # -- Cumulative: every committed result, floor applied ---------------

    def _cumulative_pane(self) -> ComposeResult:
        """Aggregate the result CSVs without pooling incomparable files."""
        with VerticalScroll():
            yield Static(
                "Every CSV in research/results/. Rows below the "
                f"{cumulative_mod.MIN_RANKABLE_TRADES}-trade evidence floor are "
                "counted separately, never mixed into a ranking: cpcv_evaluate "
                "prints those DROPPED but still returns a full path count. Files "
                "are shown side by side rather than pooled, because a median "
                "across different assets, horizons and geometries describes "
                "nothing.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Reload", id="cumulative-reload", variant="primary")
            yield Static("", id="cumulative-headline")
            per_file = DataTable(id="cumulative-table")
            per_file.add_columns("file", "rankable", "below floor", "positive",
                                 "made money", "median Sharpe", "paths", "best (rankable)")
            yield per_file
            yield Static("[b]Below the floor — what a naive aggregate would rank first[/b]",
                         classes="hint")
            dropped = DataTable(id="cumulative-dropped")
            dropped.add_columns("file", "configuration", "claims Sharpe", "trades", "paths")
            yield dropped

    @on(Button.Pressed, "#cumulative-reload")
    def _reload_cumulative(self) -> None:
        self._refresh_cumulative()

    def _refresh_cumulative(self) -> None:
        summaries = cumulative_mod.load_all()
        self.query_one("#cumulative-headline", Static).update(
            cumulative_mod.headline(summaries))
        table = self.query_one("#cumulative-table", DataTable)
        table.clear()
        for s in summaries:
            best = s.best
            med = s.median_sharpe
            table.add_row(
                s.source, str(len(s.rankable)), str(len(s.below_floor)),
                str(s.positive), str(s.made_money),
                "-" if med is None else f"{med:+.3f}",
                s.path_range,
                "-" if best is None else f"{best.label} {best.median_sharpe:+.3f}",
            )
        drop = self.query_one("#cumulative-dropped", DataTable)
        drop.clear()
        for r in cumulative_mod.floor_casualties(summaries):
            drop.add_row(r.source, r.label, f"{r.median_sharpe:+.3f}",
                         str(r.trades or 0), str(r.n_paths or 0))

    # -- Research: the drivers and what they established -----------------

    def _research_pane(self) -> ComposeResult:
        """The research surface: which driver answers which question."""
        with VerticalScroll():
            yield Static(
                "The drivers that produce every number in this repo, and the "
                "finding each one established. Run them from a terminal — they "
                "are long-running and their output is the artifact, not the "
                "console. docs/SCRIPTS.md carries the full options.",
                classes="hint",
            )
            table = DataTable(id="research-table")
            table.add_columns("driver", "answers", "established")
            for driver, answers, found in RESEARCH_DRIVERS:
                table.add_row(driver, answers, found)
            yield table
            yield Static("[b]Findings that constrain every figure above[/b]",
                         classes="hint")
            for line in RESEARCH_FINDINGS:
                yield Static(f"• {line}")

    # -- Docs: read-only explorer over every tracked file ----------------

    def _docs_pane(self) -> ComposeResult:
        """Browse every file in the repo; open one with a click, Enter, or "o".

        The viewer itself lives in `_editor_pane`, not here -- it is shared
        across every tab. Editable per `docs_browser.is_editable` opens
        read-write there with Save enabled; everything else (and all of
        `research/results/`) opens read-only.
        """
        try:
            self._docs = docs_browser.load_catalog()
        except docs_browser.CatalogUnavailable as exc:
            self._docs = []
            with VerticalScroll():
                yield Static(str(exc), id="docs-empty")
            return
        kinds = [("all kinds", "")] + [(k, k) for k in docs_browser.kinds_of(self._docs)]
        with Vertical():
            yield Static(docs_browser.summarise_catalog(self._docs), id="docs-headline")
            with Horizontal(classes="form-row"):
                yield Input(placeholder="filter by path or summary…", id="docs-filter")
                yield Select(kinds, value="", id="docs-kind")
            with Horizontal():
                listing = DataTable(id="docs-table")
                listing.add_columns("path", "kind", "editable", "lines", "summary")
                # Row cursor, not the DataTable default of cell: a click must
                # land on *a row*, not one cell in it, for RowHighlighted to
                # fire and for the "o" binding below to know which file it is
                # opening. Without this a click just moved a cell cursor and
                # nothing happened -- the bug this pane shipped with.
                listing.cursor_type = "row"
                yield listing

    def _refresh_docs(self) -> None:
        if not getattr(self, "_docs", None):
            return
        query = self.query_one("#docs-filter", Input).value
        kind = self.query_one("#docs-kind", Select).value
        rows = docs_browser.filter_entries(
            self._docs, query, kind if isinstance(kind, str) else "")
        table = self.query_one("#docs-table", DataTable)
        table.clear()
        for e in rows[:400]:
            editable = "yes" if docs_browser.is_editable(e) else ""
            table.add_row(e.path, e.kind, editable, str(e.lines), e.summary[:90],
                          key=e.path)
        self.query_one("#docs-headline", Static).update(
            f"{len(rows)} of {len(self._docs)} shown · "
            f"{docs_browser.summarise_catalog(self._docs)}")

    @on(Input.Changed, "#docs-filter")
    def _docs_filter_changed(self) -> None:
        self._refresh_docs()

    @on(Select.Changed, "#docs-kind")
    def _docs_kind_changed(self) -> None:
        self._refresh_docs()

    @on(DataTable.RowHighlighted, "#docs-table")
    def _docs_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Track the highlighted row so "o" and Enter know what to open.

        `RowHighlighted` is what a mouse click actually fires (a click moves
        the cursor; it does not "select" in Textual's sense). Opening the
        file straight from this handler is also what makes a click behave
        like a file browser instead of requiring a separate Enter press.
        """
        try:
            path = str(event.data_table.get_row_at(event.cursor_row)[0])
        except Exception:  # noqa: BLE001 - an empty table has no row to open
            return
        self._docs_highlighted_path = path
        self._open_doc(path)

    @on(DataTable.RowSelected, "#docs-table")
    def _docs_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on a highlighted row -- a deliberate "open this", so it may
        discard an unsaved edit in whatever was open before (force=True).
        """
        try:
            path = str(event.data_table.get_row_at(event.cursor_row)[0])
        except Exception:  # noqa: BLE001 - an empty table has no row to open
            return
        self._open_doc(path, force=True)

    def action_open_doc(self) -> None:
        """The "o" binding: open whatever row is currently highlighted.

        Exists alongside the click/Enter paths above because mouse-click
        fidelity through a browser-rendered terminal (textual-serve) is not
        guaranteed the way it is in a real terminal -- a keybinding that only
        needs arrow-key navigation to have set `_docs_highlighted_path` is the
        reliable path when a click doesn't land. Also a deliberate action, so
        force=True.
        """
        if self._docs_highlighted_path:
            self._open_doc(self._docs_highlighted_path, force=True)

    def action_save_doc(self) -> None:
        """ctrl+s: save whatever is currently open, from any tab."""
        self._save_current_doc()

    def action_toggle_editor(self) -> None:
        """ctrl+e: hide/show the editor panel without losing its contents."""
        panel = self.query_one("#editor-panel")
        panel.display = not panel.display

    def _open_doc(self, path: str, *, force: bool = False) -> None:
        """Load `path` into the shared editor panel.

        Passive navigation (a click or arrow-key move, via `RowHighlighted`)
        calls this with `force=False`: if it would silently overwrite an
        unsaved edit in a *different* file, it is refused instead. That
        silent overwrite -- `view.text = text` ran unconditionally on every
        cursor move -- was the actual bug behind "editing the file ...
        doesn't automatically save". Deliberate opens (Enter, the "o"
        binding) pass `force=True`: a conscious "open this" action is allowed
        to discard, since the alternative is a file browser that can never be
        told to move on from a file with unsaved edits.
        """
        view = self.query_one("#docs-view", TextArea)
        status = self.query_one("#docs-view-status", Static)
        dirty = self._docs_current_path is not None and view.text != self._docs_loaded_text
        moving_away = dirty and path != self._docs_current_path
        if moving_away and not force:
            status.update(
                f"unsaved changes in {self._docs_current_path} — save "
                f"(ctrl+s) first, or press Enter/\"o\" on {path} to discard "
                f"and open it anyway"
            )
            return

        text, language, is_real_text = docs_browser.read_document(path, self._docs)
        entry = next((e for e in self._docs if e.path == path), None)
        editable = is_real_text and entry is not None and docs_browser.is_editable(entry)

        # Set before `view.text =`, not after: assigning `.text` fires
        # `TextArea.Changed`, whose handler compares against this value to
        # decide whether to show an "unsaved" marker -- if it ran before this
        # line it would compare the new text against the *previous* file's
        # loaded text and misreport a freshly-opened file as dirty.
        self._docs_loaded_text = text
        view.text = text
        view.read_only = not editable
        # Unknown languages must clear the previous one, or a .txt renders with
        # the last file's grammar and looks subtly wrong.
        try:
            view.language = language or None
        except Exception:  # noqa: BLE001 - grammar unavailable in this build
            view.language = None

        self._docs_current_path = path
        self._docs_current_editable = editable
        note = " (discarded unsaved edit)" if moving_away else ""
        status.update(f"{path} — {'editable' if editable else 'read-only'}{note}")
        self.query_one("#docs-save", Button).disabled = not editable

    @on(TextArea.Changed, "#docs-view")
    def _docs_view_changed(self) -> None:
        """Live "unsaved" marker, so a lost-on-navigate edit is visible
        before it is lost, not just guarded against after the fact."""
        if self._docs_current_path is None:
            return
        view = self.query_one("#docs-view", TextArea)
        status = self.query_one("#docs-view-status", Static)
        base = (f"{self._docs_current_path} — "
                f"{'editable' if self._docs_current_editable else 'read-only'}")
        dirty = view.text != self._docs_loaded_text
        status.update(base + (" · unsaved" if dirty else ""))

    @on(Button.Pressed, "#docs-save")
    def _docs_save(self) -> None:
        self._save_current_doc()

    def _save_current_doc(self) -> None:
        """Write the viewer's current text back to disk.

        The keypress/click itself is the confirm-on-save step: there is no
        separate dialog, and `write_document` re-checks editability against
        the live catalogue rather than trusting `_docs_current_editable`, so
        a stale binding from before a catalogue reload cannot write
        somewhere the current rules would refuse.
        """
        status = self.query_one("#docs-view-status", Static)
        if not self._docs_current_path or not self._docs_current_editable:
            status.update("nothing editable is open")
            return
        path = self._docs_current_path
        text = self.query_one("#docs-view", TextArea).text
        try:
            docs_browser.write_document(path, text, self._docs)
        except (PermissionError, FileNotFoundError, OSError) as exc:
            status.update(f"[red]save failed: {exc}[/]")
            return
        self._docs_loaded_text = text
        status.update(f"{path} — saved")


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python3 -m soltui.tui`."""
    SolTuiApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

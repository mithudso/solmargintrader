"""Textual TUI: the console over the backtester.

    python3 -m soltui.tui

Tabs: Settings, Strategies, Signals, Backtest, Top 5, Execute (dry-run only),
Analyze, Cumulative, Research, Docs.

All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`,
`status`); this file is presentation and wiring. That split is what lets the
logic be tested without driving a terminal, and it mirrors how
`netdnsmonitor/app.py` stays thin over tested modules.

The Execute tab is **dry-run only**. See `paper.py` for why there is no order
path anywhere in this package.
"""

from __future__ import annotations

import inspect
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from textual import events, on, work
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
from . import bgcontrol
from . import bgqueue
from . import cumulative as cumulative_mod
from . import docs_browser
from . import top5 as top5_mod
from . import live_run
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
    "sma-gated": "One entry rule -- close above its SMA -- under four sizing schemes. "
                 "Measured 0.92-1.00 correlated, so treat them as one bet, not four.",
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


def _mtime(path: Path) -> float:
    """Modification time, or 0.0 when the file is absent.

    Absent and unchanged must be distinguishable from "changed", and a missing
    background-results file is the normal state before the first sweep -- so
    this returns a sentinel rather than raising.
    """
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def sort_key(value: Any) -> tuple[int, float, str]:
    """Order any cell value sensibly: numbers numerically, text alphabetically.

    Every cell in this app is a string, but many *render* numbers --
    "+0.534", "3.44%", "-3.736213", "4,304", "85%". A plain string sort puts
    "-0.9" above "-3.7" and "9" above "10", which silently misranks exactly
    the columns (median Sharpe, trades) someone sorts to rank. So: parse as a
    number when possible (after stripping the +/%/, decorations), fall back
    to case-insensitive text.

    The tuple keeps `sorted()` away from comparing float with str: group 0 is
    numbers, group 1 text, group 2 the "-"/empty placeholder cells -- always
    last ascending, deliberately, since "no value" ranks below any value.
    """
    text = str(value).strip()
    if text in ("", "-"):
        return (2, 0.0, "")
    try:
        return (0, float(text.replace(",", "").replace("%", "").lstrip("+")), "")
    except ValueError:
        return (1, 0.0, text.casefold())


# Column-header glossary, keyed by the exact header label (case-insensitive).
# One dict for every table on purpose: "median Sharpe" must mean the same
# thing on the Backtest, Top 5 and Cumulative tabs, and a single lookup makes
# a divergence impossible. A label with no entry shows no tooltip -- better
# than a generic sentence pretending to explain it.
HEADER_GLOSSARY = {
    "median sharpe": (
        "Sharpe ratio = mean return / volatility of returns (annualised): "
        "risk-adjusted performance, >0 means paid for the risk taken. This is "
        "the MEDIAN across all CPCV paths, not one backtest's number."),
    "iqr": (
        "Interquartile range: the spread between the 25th and 75th percentile "
        "of per-path Sharpe. Large IQR = the result depends heavily on which "
        "slice of history you test — less trustworthy."),
    "% paths +": (
        "Fraction of CPCV paths (regime-mixed train/test splits) where the "
        "Sharpe was positive. 100% of 15 is still only 15 paths."),
    "median ret": (
        "Median total return across CPCV paths over the tested window, "
        "after fees and slippage."),
    "median return": (
        "Median total return across CPCV paths over the tested window, "
        "after fees and slippage."),
    "trades": (
        "Total trades executed. Below 10 the engine refuses to rank the row "
        "(the evidence floor) — a great Sharpe on 6 trades is noise."),
    "paths": (
        "Number of CPCV paths evaluated. Nominal is C(blocks, k), but slow "
        "strategies lose warm-up blocks; fewer paths = weaker estimate."),
    "rankable": (
        "Rows with at least 1 path AND ≥10 trades — enough evidence to "
        "appear in a ranking at all."),
    "below floor": (
        "Rows the engine evaluated but refused: fewer than 10 trades. "
        "Counted separately, never mixed into rankings."),
    "positive": "Rankable rows whose median Sharpe is above zero.",
    "made money": "Rankable rows whose median return is above zero.",
    "best (rankable)": (
        "Highest median Sharpe among rankable rows only — below-floor rows "
        "are excluded no matter what they claim."),
    "claims sharpe": (
        "The Sharpe this below-floor row reports. Shown to make the point: "
        "on this few trades it would often top a naive ranking."),
    # NB: str.casefold() lowercases Δ to δ, so the key must be δ.
    "δ vs sol": (
        "Change in median Sharpe versus the SOL result the configuration was "
        "selected on. Large negative delta = does not transfer off-asset."),
    "horizon": (
        "Bar-interval class from research/sweep.py: short/medium/long map to "
        "different intervals and parameter scalings."),
    "signals": (
        "The member indicator strategies. (all) = every member must agree "
        "before a position; (any) = one agreeing member is enough."),
    "configuration": "Strategy (or composite) plus its parameter values.",
    "strategy": "The registered strategy name.",
    "in roster": "Strategy label with parameters, as the sweep will run it.",
    "family": (
        "Behavioural family (trend, momentum, mean-reversion, ...) — see the "
        "Signals tab for when each kind fails."),
    "warm-up": (
        "Bars of history the strategy needs before its first signal. Warm-up "
        "eats CPCV blocks, which is why slow strategies have fewer paths."),
    "file": "Source CSV in research/results/ — results are never pooled across files.",
    "equation": "The indicator's formula as implemented in backtester/core/indicators.py.",
    "kind": "Coarse file classification from the repo index (code, doc, result, test...).",
    "editable": "Whether the Docs editor may write this file. research/results/ never is.",
    "lines": "Line count at index build time.",
    "summary": "One-line summary extracted when the repo index was built.",
    "path": "File path relative to the repository root.",
    "bar": "Bar index within the replayed series.",
    "side": "buy or sell.",
    "reason": "Which rule produced the intended fill.",
    "units": "Position size in units of the asset.",
    "cost": "Cash spent or received including fees.",
    "equity": "Account value after the fill, marked at that bar's close.",
    "driver": "The research script that produces this artifact.",
    "answers": "The question the driver was built to answer.",
    "established": "What the run actually established, quoted from the docs.",
    "action": "What the rule would decide at the chosen bar: buy, sell or hold.",
    "holding -> wants": "Position it would be holding, versus what it wants now.",
    "warmup": "Bars of history the strategy needs before its first signal.",
    "bars": "Bars of the truncated series available to the replay.",
    "#": "Rank in research/TOP5-RECOMMENDATION.md — by robustness checks cleared, not by Sharpe.",
    "asset": "The coin the configuration was evaluated on for this row.",
    "when": "Timestamp of the bar (UTC).",
    "price": "Fill price used by the simulation for that bar.",
    "signal": "The indicator this row defines parameters for.",
    "what it is / when it fails": (
        "The family's bet in one line, and the market condition that "
        "reliably breaks it."),
}


class GlossaryTable(DataTable):
    """`DataTable` that explains its column headers on hover.

    Textual tooltips are per-widget, not per-cell, so a static tooltip could
    only describe the whole table. Header cells carry their position in the
    segment style meta (`row == -1` marks the header row — the same meta the
    widget's own hover cursor uses), so the tooltip is swapped on every
    mouse move: over a known header it becomes that column's glossary entry,
    anywhere else it clears rather than lingering half-screen away from what
    it describes.
    """

    def header_tooltip(self, column_index: int) -> str | None:
        """The glossary entry for one column, or None when there isn't one."""
        try:
            label = str(self.ordered_columns[column_index].label)
        except IndexError:
            return None
        return HEADER_GLOSSARY.get(label.strip().casefold())

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        super()._on_mouse_move(event)
        meta = event.style.meta
        tooltip = None
        if meta and meta.get("row") == -1 and meta.get("column", -1) >= 0:
            tooltip = self.header_tooltip(meta["column"])
        if self.tooltip != tooltip:
            self.tooltip = tooltip

    def _on_leave(self, event: events.Leave) -> None:
        super()._on_leave(event)
        self.tooltip = None


class VimTextArea(TextArea):
    """`TextArea` with a small, honest subset of Vim's modal editing.

    Not a full Vim emulation. `textual-vim` on PyPI is a single 0.1.0
    release of unknown maintenance, and whether it even *is* a `TextArea`
    subclass -- and so keeps `read_only`, `language` and
    `show_line_numbers` -- is unverified from its listing. All three matter
    here: `read_only` is `docs_browser`'s actual enforcement point for the
    `research/results/` write guard (`NO_WRITE_PREFIXES`), not a display
    hint, so losing it silently would reopen exactly the hole
    `test_read_only_file_rejects_keystrokes` exists to close. Staying a
    `TextArea` subclass keeps all three working unchanged: every mutating
    command below either defers to a `TextArea` action that already refuses
    when `read_only` is set (`action_delete_right`, `action_delete_line`),
    or is only reachable through `_enter_insert`/`_open_line_below`, which
    refuse to switch into INSERT on a read-only file in the first place.

    Two modes: NORMAL (motions only; nothing is typed) and INSERT (falls
    through to ordinary `TextArea` key handling). Covered commands::

        h j k l     move
        0   $       start / end of line
        g g   G     start / end of document
        i   a       insert before / after the cursor
        o           open a line below and enter insert
        x           delete the character under the cursor
        d d         delete the current line
        :w<enter>   save (the same guarded write as ctrl+s / the button)
        escape      return to NORMAL

    An unbound key in NORMAL mode is swallowed, matching Vim's own
    behaviour, rather than falling through and being typed as text. One
    deliberate deviation from real Vim: entering INSERT is refused outright
    on a read-only file, rather than allowed and only refused at `:w` --
    a blinking insert-mode cursor on a file that can never be saved is a
    worse experience than "i" doing nothing.
    """

    class Mode(Enum):
        NORMAL = "normal"
        INSERT = "insert"

    def __init__(self, *args: Any, on_save: Callable[[], None] | None = None,
                 **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.vim_mode = VimTextArea.Mode.NORMAL
        self._pending_key = ""
        self._colon_active = False
        self._colon_buffer = ""
        # ":w" calls this rather than writing independently, so a Vim save
        # is the exact same guarded path as ctrl+s / the Save button, never
        # a second write path that could drift from it.
        self._on_save = on_save

    async def _on_key(self, event: events.Key) -> None:
        if self.vim_mode is VimTextArea.Mode.INSERT:
            if event.key == "escape":
                event.stop()
                event.prevent_default()
                self.vim_mode = VimTextArea.Mode.NORMAL
                return
            await super()._on_key(event)
            return

        # NORMAL mode: every key is ours, handled or swallowed -- never
        # passed through to be inserted as a stray character.
        event.stop()
        event.prevent_default()
        self._handle_normal_key(event.key, event.character)

    def _handle_normal_key(self, key: str, character: str | None) -> None:
        if self._colon_active:
            self._handle_colon_key(key, character)
            return

        if self._pending_key:
            pending, self._pending_key = self._pending_key, ""
            if pending == "g" and key == "g":
                self.move_cursor(self.document.start)
            elif pending == "d" and key == "d":
                self.action_delete_line()
            # A mismatched second key is dropped rather than processed as
            # its own command -- not accurate to every real-Vim combination,
            # but it never falls through and mistypes text.
            return

        if key in ("g", "d"):
            self._pending_key = key
            return

        # Keyed on `key`, not `character`: for every one of these Textual's
        # key identifier equals the character itself ("h", "0", "x", ...),
        # *except* "$", whose identifier is "dollar_sign" -- handled
        # separately just below rather than smuggled into this dict under
        # the wrong key.
        motions: dict[str, Callable[[], None]] = {
            "h": self.action_cursor_left,
            "l": self.action_cursor_right,
            "j": self.action_cursor_down,
            "k": self.action_cursor_up,
            "0": self.action_cursor_line_start,
            "G": lambda: self.move_cursor(self.document.end),
            "x": self.action_delete_right,
        }
        if key in motions:
            motions[key]()
            return
        if character == "$":
            self.action_cursor_line_end()
            return

        if key == "i":
            self._enter_insert()
        elif key == "a":
            self._enter_insert(after=True)
        elif key == "o":
            self._open_line_below()
        elif character == ":":
            self._colon_active = True
            self._colon_buffer = ""
        # else: an unbound key in NORMAL mode does nothing, matching Vim.

    def _handle_colon_key(self, key: str, character: str | None) -> None:
        if key == "enter":
            self._colon_active = False
            if self._colon_buffer.strip() == "w" and self._on_save is not None:
                self._on_save()
            self._colon_buffer = ""
        elif key == "escape":
            self._colon_active = False
            self._colon_buffer = ""
        elif key == "backspace":
            self._colon_buffer = self._colon_buffer[:-1]
        elif character is not None and character.isprintable():
            self._colon_buffer += character

    def _enter_insert(self, *, after: bool = False) -> None:
        if self.read_only:
            return
        if after:
            self.action_cursor_right()
        self.vim_mode = VimTextArea.Mode.INSERT

    def _open_line_below(self) -> None:
        if self.read_only:
            return
        self.action_cursor_line_end()
        self.insert("\n", maintain_selection_offset=False)
        self.vim_mode = VimTextArea.Mode.INSERT


class SolTuiApp(App):
    """The console: ten tabs over the tested modules."""

    TITLE = "soltui — SOL strategy console"
    SUB_TITLE = "dry-run only · no live order path"
    CSS = """
    #execute-banner, #live-run-banner {
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
        # Last results-file mtime the Queue tab rendered. The background worker
        # is a separate process, so the only way to know it produced something is
        # to look -- but re-parsing the file on every tick would burn the UI
        # thread on a file that changes once every few seconds at most.
        self._queue_results: list[bgqueue.JobResult] = []
        # How far the results file has been consumed, and which file that was, so
        # a refresh parses only what the worker appended since last time.
        self._queue_cursor = bgqueue.ResultsCursor()
        self._top5_loaded = False
        self._top5_configs: list[top5_mod.Top5Config] = []

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
            with TabPane("Top 5", id="tab-top5"):
                yield from self._top5_pane()
            with TabPane("Live Run", id="tab-liverun"):
                yield from self._live_run_pane()
            with TabPane("Execute", id="tab-execute"):
                yield from self._execute_pane()
            with TabPane("Analyze", id="tab-analyze"):
                yield from self._analyze_pane()
            with TabPane("Cumulative", id="tab-cumulative"):
                yield from self._cumulative_pane()
            with TabPane("Queue", id="tab-queue"):
                yield from self._queue_pane()
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
        `VimTextArea` (see its docstring) is a `TextArea` subclass, so every
        existing `query_one("#docs-view", TextArea)` call elsewhere still
        matches it.
        """
        with Vertical(id="editor-panel"):
            with Horizontal(classes="form-row"):
                yield Static("select a file to open it here", id="docs-view-status")
                yield Button("Save (^s)", id="docs-save", variant="primary",
                             disabled=True)
            yield VimTextArea("", id="docs-view", read_only=True,
                               show_line_numbers=True, on_save=self._save_current_doc)

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
                yield GlossaryTable(id="available-table")
                yield GlossaryTable(id="roster-table")
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
            yield GlossaryTable(id="signals-table")
            yield Static("\nFamily behaviour — when each kind fails:", classes="hint")
            yield GlossaryTable(id="families-table")

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
                yield Button("Run Untested Sweep", variant="warning", id="btn-run-untested")
                yield Button("Cancel (c)", variant="error", id="btn-cancel")
                yield Static("", id="backtest-status")
            yield GlossaryTable(id="results-table")

    def _live_run_pane(self) -> ComposeResult:
        """Launcher for the Node.js extension in dry-run mode."""
        with Vertical():
            # A distinct id: `#execute-banner` is the dry-run safety banner the
            # Execute tab owns, and two widgets sharing it made `query_one` return
            # this one instead — silently reading the safety rail off the wrong widget.
            yield Static("LIVE RUN LAUNCHER (DRY-RUN OPTION)", id="live-run-banner")
            yield Static(
                "This tab populates the most profitable/tested configuration and spawns "
                "the Node.js extension's dry-run engine. The TUI itself places no orders.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Label("Recommended:")
                yield Static("Loading...", id="live-run-recommendation", classes="hint")
            with Horizontal(classes="form-row"):
                yield Label("Strategy:")
                yield Input(value="", id="live-run-strategy")
                yield Button("Spawn Node Dryrun", variant="success", id="btn-spawn-dryrun")
                yield Button("Refresh", id="btn-refresh-live-run")
            yield Static("", id="live-run-status")
            yield TextArea(read_only=True, id="live-run-output")

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
            yield GlossaryTable(id="fills-table")

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

        self._poll_queue()

    def _poll_queue(self) -> None:
        """Redraw the Queue tab only when the worker actually wrote something.

        Stat, compare, and usually return: the worker is a separate process
        whose results file changes at the pace of a CPCV evaluation, so parsing
        it on every tick would be work the UI thread does for nothing. The mtime
        check is what makes polling on the existing 2-second cadence cheap.
        """
        if not self.query("#queue-status"):
            return
        # Compared against the mtime of the file state the last read actually
        # consumed, not one sampled afterwards -- a row appended DURING that read
        # would otherwise be recorded as already-seen and never appear.
        if _mtime(bgqueue.RESULTS_PATH) != self._queue_cursor.mtime:
            self._refresh_queue()
            return
        # Nothing new to rank, but the worker may have moved on to another job --
        # or died. `state.json` is a few hundred bytes; the results file is every
        # result ever computed, so only the former is cheap enough per tick.
        #
        # Deliberately NOT gated on the worker being alive: a crashed worker
        # leaves state.json reading "running", and skipping the render there
        # would freeze the pane on its last progress line forever.
        self._render_queue_status(bgqueue.read_state())

    @on(DataTable.HeaderSelected)
    def _sort_by_column(self, event: DataTable.HeaderSelected) -> None:
        """Click any table's column header to sort by it; click again to flip.

        One app-level handler with no selector, on purpose: every DataTable
        in the console -- Cumulative's per-file and below-floor tables, the
        Backtest results, Docs, Strategies, fills, all of them -- gets the
        same behaviour, and a future table gets it for free instead of
        waiting for someone to remember the wiring. Sorting is a view over
        the rows already in the widget, so tables that reload their rows
        (Cumulative's Reload, the Docs filter) reset to their natural order,
        which is correct: the sort belonged to the old rows.

        The per-direction state rides on the widget instance rather than an
        app-level dict keyed by table id, because rows and widget die
        together -- there is nothing to clean up and no stale entry when a
        pane is rebuilt.
        """
        table = event.data_table
        previous = getattr(table, "_sorted_by", None)
        reverse = previous == (event.column_key, False)
        table.sort(event.column_key, key=sort_key, reverse=reverse)
        table._sorted_by = (event.column_key, reverse)

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

    def _strategy_source_path(self, name: str) -> str | None:
        """Catalogue-relative path to the file that defines strategy `name`.

        `inspect.getfile` rather than a hand-maintained name-to-file table:
        several strategies share one module (e.g. everything in
        `advanced.py`), and a static mapping would drift the moment a
        strategy moves files. Returns None -- rather than raising -- for
        anything not resolvable or not present in the Docs catalogue, since
        `docs_browser.resolve` treats the catalogue as an allowlist and a
        strategy file missing from `index/INDEX.json` must fail closed, not
        open an uncatalogued path.
        """
        func = REGISTRY.get(name)
        if func is None:
            return None
        try:
            rel = str(Path(inspect.getfile(func)).resolve()
                      .relative_to(docs_browser.REPO))
        except (TypeError, OSError, ValueError):
            return None
        if not any(e.path == rel for e in self._docs):
            return None
        return rel

    def _open_strategy_file(self, name: str) -> None:
        """Open the source file for strategy `name` in the shared editor.

        Passive (RowHighlighted, so a click behaves the same way it does on
        the Docs tab): respects `_open_doc`'s unsaved-edit guard rather than
        forcing past it, since arrow-keying through the strategy list is
        exactly the kind of incidental navigation that guard exists for.
        """
        rel = self._strategy_source_path(name)
        if rel is None:
            self.query_one("#docs-view-status", Static).update(
                f"{name}: source file not in the Docs catalogue")
            return
        self._open_doc(rel)

    @on(DataTable.RowHighlighted, "#available-table")
    def _available_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            name = str(event.data_table.get_row_at(event.cursor_row)[0])
        except Exception:  # noqa: BLE001 - an empty table has no row to open
            return
        self._open_strategy_file(name)

    @on(DataTable.RowHighlighted, "#roster-table")
    def _roster_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            label = str(event.data_table.get_row_at(event.cursor_row)[0])
        except Exception:  # noqa: BLE001 - an empty table has no row to open
            return
        # The roster table's first column is the entry's *label*
        # (e.g. "rsi_9_30_55", params baked in for display), not the bare
        # REGISTRY name -- has to go through the roster to recover that.
        entry = next((e for e in self.roster if e.label == label), None)
        if entry is not None:
            self._open_strategy_file(entry.name)

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

    @on(Button.Pressed, "#btn-run-untested")
    @work(thread=True)
    def _run_untested_sweep(self) -> None:
        """Run the untested sweep script."""
        status = self.query_one("#backtest-status", Static)
        self.call_from_thread(status.update, "running untested sweep...")
        try:
            import subprocess
            from pathlib import Path
            repo = Path(__file__).resolve().parent.parent
            script = repo / "research" / "sweep_untested.py"
            result = subprocess.run(
                ["python3", str(script)], capture_output=True, text=True, cwd=str(repo)
            )
            if result.returncode == 0:
                self.call_from_thread(status.update, f"untested sweep done.\n{result.stdout[-200:]}")
            else:
                self.call_from_thread(status.update, f"[red]error: {result.stderr}[/]")
        except Exception as exc:
            self.call_from_thread(status.update, f"[red]{exc}[/]")

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
        elif pane == "tab-queue":
            # No once-only guard: unlike Cumulative and Docs, this tab's source
            # is being written by another process right now, so re-reading on
            # every activation is the correct behaviour rather than waste.
            self._refresh_queue()
        elif pane == "tab-top5" and not self._top5_loaded:
            self._top5_loaded = True
            self._refresh_top5()
        elif pane == "tab-liverun":
            self._refresh_live_run()

    # -- Live Run --------------------------------------------------------

    def _refresh_live_run(self) -> None:
        best = live_run.get_best_strategy()
        rec_static = self.query_one("#live-run-recommendation", Static)
        strat_input = self.query_one("#live-run-strategy", Input)
        rec_static.update(f"{best['strategy']} (from {best['source']}) — {best['details']}")
        strat_input.value = best["strategy"]
        
    @on(Button.Pressed, "#btn-refresh-live-run")
    def _btn_refresh_live_run(self) -> None:
        self._refresh_live_run()
        self.query_one("#live-run-status", Static).update("refreshed recommendation")
        
    @on(Button.Pressed, "#btn-spawn-dryrun")
    @work(thread=True)
    def _btn_spawn_dryrun(self) -> None:
        strategy_name = self.query_one("#live-run-strategy", Input).value.strip()
        status = self.query_one("#live-run-status", Static)
        out_area = self.query_one("#live-run-output", TextArea)
        
        def _update(msg: str) -> None:
            if "\n" in msg and "[green]" in msg or "[red]" in msg:
                # We can update the TextArea for large output
                # Just strip tags roughly for TextArea or use RichLog
                import re
                clean = re.sub(r'\[/?(red|green|b)\]', '', msg)
                self.call_from_thread(lambda: setattr(out_area, "text", clean))
            else:
                self.call_from_thread(status.update, msg)
                
        if not strategy_name:
            self.call_from_thread(status.update, "[red]Please enter a strategy name.[/red]")
            return
            
        live_run.spawn_dryrun(strategy_name, _update)

    # -- Top 5: the recommended configurations and their evidence ---------

    def _top5_pane(self) -> ComposeResult:
        """The five recommended configurations, their data, and re-test paths.

        Deliberately titled by the selection rule, not "best by Sharpe": the
        study's PBO of 0.700 means ranking by in-sample Sharpe selects noise,
        so the five here are the ones of research/TOP5-RECOMMENDATION.md --
        drawn from the only seven configurations tested on two independent
        robustness axes, ordered by checks cleared.
        """
        with VerticalScroll():
            yield Static(
                "Selected by robustness checks (CPCV path distribution + ±10% "
                "parameter perturbation, 0 sign flips), NOT by Sharpe rank: "
                "PBO is 0.700 against a 0.500 noise line, so 'top 5 by Sharpe' "
                "would list the rows most likely to be noise. Source: "
                "research/TOP5-RECOMMENDATION.md.",
                classes="hint",
            )
            yield Static("", id="top5-headline")
            configs = GlossaryTable(id="top5-table")
            configs.add_columns("#", "configuration", "horizon", "signals",
                                "median Sharpe", "IQR", "% paths +",
                                "median ret", "trades", "paths")
            configs.cursor_type = "row"
            yield configs
            yield Static(
                "[b]Transfer test — the same configurations off SOL[/b]  "
                "(fitted on SOL; a recommendation that only works there is "
                "an overfit, and two of the five go negative off-asset)",
                classes="hint",
            )
            transfers = GlossaryTable(id="top5-transfers")
            transfers.add_columns("#", "configuration", "asset",
                                  "median Sharpe", "Δ vs SOL", "% paths +",
                                  "median ret", "trades", "paths")
            yield transfers
            yield Static(
                "Benchmark that must stay in view: buy_and_hold, zero "
                "parameters, medium/long median Sharpe +0.534, 68% of paths "
                "positive, +9.4% median return — 2nd of 25 at the medium "
                "horizon. A configuration that does not clearly beat it is "
                "not worth its complexity.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Add selected row's signals to roster",
                             id="top5-add-selected")
                yield Button("Add all top-5 signals to roster",
                             id="top5-add-all")
                yield Button("Run backtest on roster", variant="primary",
                             id="top5-run")
                yield Button("Reload", id="top5-reload")
            yield Static("", id="top5-status")
            yield Static(
                "Re-testing: adding to the roster sweeps each member signal "
                "as a single via the Backtest tab (asset/interval/costs come "
                "from Settings). The all()/any() composites themselves cannot "
                "live in the roster — reproduce those exactly with:\n"
                f"    {top5_mod.REPRO_COMMAND}",
                classes="hint",
            )

    def _refresh_top5(self) -> None:
        headline = self.query_one("#top5-headline", Static)
        try:
            self._top5_configs = top5_mod.load_top5()
        except top5_mod.EvidenceUnavailable as exc:
            self._top5_configs = []
            headline.update(f"[b]{exc}[/b]")
            return

        def fmt(v: float | None, spec: str) -> str:
            return "-" if v is None else format(v, spec)

        table = self.query_one("#top5-table", DataTable)
        table.clear()
        for cfg in self._top5_configs:
            home = cfg.home
            if home is None:
                continue
            table.add_row(
                str(cfg.rank), cfg.label, cfg.horizon,
                " + ".join(cfg.members) + (f" ({cfg.mode})"
                                           if cfg.mode != "single" else ""),
                f"{home.median_sharpe:+.3f}", fmt(home.iqr, ".3f"),
                fmt(home.frac_positive, ".0%"),
                "-" if home.median_return is None
                else format_pct(home.median_return),
                fmt(home.trades, "d"), fmt(home.n_paths, "d"),
                key=str(cfg.rank),
            )
        transfers = self.query_one("#top5-transfers", DataTable)
        transfers.clear()
        for cfg in self._top5_configs:
            for t in cfg.transfers:
                transfers.add_row(
                    str(cfg.rank), cfg.label, t.asset,
                    f"{t.median_sharpe:+.3f}", fmt(t.delta_vs_sol, "+.3f"),
                    fmt(t.frac_positive, ".0%"),
                    "-" if t.median_return is None
                    else format_pct(t.median_return),
                    fmt(t.trades, "d"), fmt(t.n_paths, "d"),
                )
        n = len(self._top5_configs)
        headline.update(
            f"{n} configurations · fitted on {top5_mod.HOME_ASSET} · "
            f"each transfer-tested on "
            f"{', '.join(sorted({t.asset for c in self._top5_configs for t in c.transfers}))}")

    def _top5_add_members(self, configs: list) -> None:
        """Add each distinct member signal to the roster, reporting per-name.

        Uses the same path as the Strategies tab's Add button (signal
        defaults via merged_params), so a name added here behaves identically
        to one added there. Already-present names are counted, not errors —
        clicking twice must not turn into a wall of red.
        """
        added, present = [], []
        for name in top5_mod.roster_candidates(configs):
            try:
                self.roster.add(name, **merged_params(name, self.signals))
                added.append(name)
            except RosterError:
                present.append(name)
        self._refresh_roster_table()
        self._refresh_exec_choices()
        parts = []
        if added:
            parts.append(f"added {', '.join(added)}")
        if present:
            parts.append(f"already in roster: {', '.join(present)}")
        self.query_one("#top5-status", Static).update(
            (" · ".join(parts) or "nothing to add") +
            " — sweep them from here or the Backtest tab")

    @on(Button.Pressed, "#top5-add-selected")
    def _top5_add_selected(self) -> None:
        table = self.query_one("#top5-table", DataTable)
        status = self.query_one("#top5-status", Static)
        try:
            rank = int(str(table.get_row_at(table.cursor_row)[0]))
        except Exception:  # noqa: BLE001 - empty table, nothing selected
            status.update("select a configuration row first")
            return
        cfg = next((c for c in self._top5_configs if c.rank == rank), None)
        if cfg is None:
            status.update("select a configuration row first")
            return
        self._top5_add_members([cfg])

    @on(Button.Pressed, "#top5-add-all")
    def _top5_add_all(self) -> None:
        if not self._top5_configs:
            self.query_one("#top5-status", Static).update(
                "no configurations loaded")
            return
        self._top5_add_members(self._top5_configs)

    @on(Button.Pressed, "#top5-run")
    def _top5_run(self) -> None:
        """Start the same CPCV sweep the Backtest tab runs, from here."""
        status = self.query_one("#top5-status", Static)
        try:
            self.runner.start(self.roster, self.settings, on_done=self._sweep_done)
            status.update("running — results land on the Backtest tab")
        except Exception as exc:  # noqa: BLE001 - surfaced to the user
            status.update(f"[red]{exc}[/]")

    @on(Button.Pressed, "#top5-reload")
    def _top5_reload(self) -> None:
        self._refresh_top5()

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
            table = GlossaryTable(id="analyze-table")
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
            per_file = GlossaryTable(id="cumulative-table")
            per_file.add_columns("file", "rankable", "below floor", "positive",
                                 "made money", "median Sharpe", "paths", "best (rankable)")
            yield per_file
            yield Static("[b]Below the floor — what a naive aggregate would rank first[/b]",
                         classes="hint")
            dropped = GlossaryTable(id="cumulative-dropped")
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

    # -- Queue: the background sweep -------------------------------------

    def _queue_pane(self) -> ComposeResult:
        """Control and read the low-priority background sweep.

        The sweep runs in its own process, so this pane is a *view* of files on
        disk rather than of anything this app is computing. That is why it keeps
        working across a restart of the console, and why every figure here is
        whatever the worker last flushed.
        """
        with VerticalScroll():
            yield Static(
                "A separate low-priority process grinds through parameter space "
                f"and flushes each result as it lands ({bgcontrol.describe_priority()}). "
                "Work is ordered most-promising-first: every strategy card's own "
                "published preset before any variation of it, then near "
                "variations. A background sweep is never finished, only "
                "interrupted, so the order is what decides what you get.",
                classes="hint",
            )
            yield Static(
                f"Ranking is out-of-sample CPCV median Sharpe, and rows under the "
                f"{bgqueue.MIN_TRADES}-trade floor are listed separately and never "
                "ranked — a Sharpe from a handful of trades sorted descending is a "
                "ranking of luck.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Start", variant="primary", id="queue-start")
                yield Button("Stop", variant="error", id="queue-stop")
                yield Button("Refresh", id="queue-refresh")
                yield Button("Fetch missing data", id="queue-fetch")
            yield Static("", id="queue-data")
            yield Static("", id="queue-status")
            yield Static("[b]Ranked — cleared the evidence floor[/b]", classes="hint")
            ranked = DataTable(id="queue-table")
            ranked.add_columns(
                "configuration", "family", "median Sharpe", "IQR",
                "% paths +", "median return", "trades",
            )
            yield ranked
            yield Static(
                "[b]Below the floor — listed, never ranked[/b]", classes="hint"
            )
            floor = DataTable(id="queue-floor")
            floor.add_columns("configuration", "family", "trades", "why")
            yield floor

    @on(Button.Pressed, "#queue-start")
    def _queue_start(self) -> None:
        """Spawn the background worker for the configured asset."""
        status = self.query_one("#queue-status", Static)
        try:
            bgcontrol.start(self.settings.asset)
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{type(exc).__name__}: {exc}[/]")
            return
        status.update("started — results appear as each job lands")
        self._refresh_queue()

    @on(Button.Pressed, "#queue-stop")
    def _queue_stop(self) -> None:
        """Ask the worker to stop at the next job boundary."""
        status = self.query_one("#queue-status", Static)
        if bgcontrol.stop():
            status.update("stopping — the current job finishes first")
        else:
            status.update("no background sweep is running")

    @on(Button.Pressed, "#queue-refresh")
    def _queue_refresh(self) -> None:
        self._refresh_queue()

    @on(Button.Pressed, "#queue-fetch")
    def _queue_fetch(self) -> None:
        """Fetch the price series the sweep is missing.

        The one network action in this package, and it stays the separate
        explicit step `CLAUDE.md` requires: it runs `backtester.core.fetch` --
        the same command shown above the button -- and starting a sweep is NOT a
        side effect of it finishing. Nothing here reaches a venue or an account.
        """
        data = self.query_one("#queue-data", Static)
        missing = self._missing_series()
        if not missing:
            data.update("every series this sweep needs is already cached")
            return
        try:
            bgcontrol.start_fetch([(m.asset, m.interval) for m in missing])
        except Exception as exc:  # noqa: BLE001
            data.update(f"[red]{type(exc).__name__}: {exc}[/]")
            return
        names = ", ".join(f"{m.asset} {m.interval}" for m in missing)
        data.update(
            f"fetching {names} — press Refresh when it finishes "
            f"(log: {bgqueue.BG_DIR / 'fetch.log'})"
        )

    def _missing_series(self) -> list[bgqueue.MissingSeries]:
        """Price files this asset's sweep needs and does not have."""
        try:
            return bgqueue.missing_series(
                self.settings.asset, data_dir=self.settings.data_dir
            )
        except ValueError:
            # An unusable asset symbol is the Settings tab's problem to report;
            # here it just means there is nothing meaningful to check for.
            return []

    def _render_queue_data(self) -> None:
        """Say which series are missing, and name the command that fixes it.

        Checked before the sweep rather than discovered during it. The queue
        interleaves intervals by promise, so a missing 1h file would otherwise
        surface minutes in, after the pane had already reported "running" -- and
        the whole short horizon would be quietly absent from the results.
        """
        line = self.query("#queue-data")
        if not line:
            return
        missing = self._missing_series()
        if not missing:
            line.first(Static).update("")
            return
        commands = "  ·  ".join(m.command_text for m in missing)
        text = (
            f"[yellow]missing price data — {len(missing)} series "
            f"({', '.join(m.interval for m in missing)}) will be skipped:[/] {commands}"
        )
        # A fetch that already ran and left the series missing failed for a
        # reason worth reading -- the 1h series is refused outright unless
        # --allow-gaps is passed. Without this pointer the button looks like it
        # simply did nothing.
        log = bgqueue.BG_DIR / "fetch.log"
        if log.exists():
            text += f"  ·  a previous fetch left these missing; see {log}"
        line.first(Static).update(text)

    def _render_queue_status(self, state: bgqueue.QueueState) -> None:
        """Update just the status line, from the cached results.

        Split out from `_refresh_queue` so the per-tick path can show live
        progress without re-reading and re-ranking every result ever computed.
        """
        line = self.query("#queue-status")
        if not line:
            return
        alive = bgcontrol.is_running()
        live = " · worker alive" if alive else ""
        detail = f" · now: {state.current}" if state.current and alive else ""
        line.first(Static).update(
            bgqueue.summarise(
                state, self._queue_results, self.settings.asset, worker_alive=alive
            )
            + detail
            + live
        )

    def _refresh_queue(self) -> None:
        """Re-read the worker's files and redraw both tables.

        Reads only what was appended since the last refresh: a long sweep's
        results file grows without bound, and re-parsing all of it on every new
        row would make watching the sweep cost more than running it.
        """
        fresh, cursor, restarted = bgqueue.read_results_since(self._queue_cursor)
        if restarted:
            # The file was truncated or replaced, so what we are holding belongs
            # to a sweep that no longer exists.
            self._queue_results = []
        self._queue_results.extend(fresh)
        self._queue_cursor = cursor
        results = self._queue_results
        self._render_queue_data()
        self._render_queue_status(bgqueue.read_state())

        ranked, floor = bgqueue.leaderboard(results, self.settings.asset)
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        for r in ranked[:200]:
            table.add_row(
                r.label, r.family, f"{r.median_sharpe:+.3f}", f"{r.iqr:.3f}",
                f"{r.frac_positive:.0%}", format_pct(r.median_return), str(r.trades),
            )
        floor_table = self.query_one("#queue-floor", DataTable)
        floor_table.clear()
        for r in floor[:200]:
            floor_table.add_row(
                r.label, r.family, str(r.trades),
                r.reason or f"under the {bgqueue.MIN_TRADES}-trade floor",
            )

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
            table = GlossaryTable(id="research-table")
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
                listing = GlossaryTable(id="docs-table")
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

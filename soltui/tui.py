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

import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from textual import events, on, work
from rich.text import Text
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

from . import bgcontrol
from . import cumulative as cumulative_mod
from . import bgqueue
from . import docs_browser
from . import liquidity as liq
from . import top5 as top5_mod
from .commands import (  # noqa: F401 - re-exported: tests and docs import them from here
    UNTESTED_SWEEP_TIMEOUT_S,
    Context,
    Runtime,
    dispatch,
    failure_summary,
    untested_sweep_command,
)
from .config import INTERVALS, Settings, load_settings
from .paper import MODE_LABEL
from .roster import RosterError
from .signals import SIGNAL_GROUPS, SignalDefaults
from .status import build_title, format_pct

from .reference import FAMILY_NOTES, RESEARCH_DRIVERS, RESEARCH_FINDINGS, SIGNAL_REFERENCE  # noqa: F401


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



# Rows the Docs table renders at once. The repo has ~470 tracked files; leave headroom.
DOCS_TABLE_CAP = 1000

# Every Button.Pressed handler below maps to the registry command it runs. tests/test_bridge_buttons.py
# parses this file and fails when a button is missing here or names a command that does not exist, so a
# new button cannot skip the registry (the extension, CLI and API would silently lack its action).
BUTTON_COMMANDS: dict[str, str] = {
    "#btn-save": "settings.save",
    "#btn-add": "roster.add",
    "#btn-remove": "roster.remove",
    "#btn-reset-roster": "roster.reset",
    "#btn-save-signals": "signals.save",
    "#btn-reset-signals": "signals.reset",
    "#btn-cancel": "backtest.cancel",
    "#btn-run": "backtest.run",
    "#btn-run-untested": "backtest.untested_sweep",
    "#btn-paper-start": "paper.start",
    "#btn-step1": "paper.step",
    "#btn-step25": "paper.step",
    "#btn-step-end": "paper.seek_end",
    "#btn-paper-reset": "paper.reset",
    "#btn-refresh-live-run": "live.recommendation",
    "#btn-spawn-dryrun": "live.spawn_dryrun",
    "#top5-add-selected": "top5.add_to_roster",
    "#top5-add-all": "top5.add_to_roster",
    "#top5-run": "backtest.run",
    "#top5-reload": "top5.list",
    "#analyze-run": "analyze.run",
    "#cumulative-reload": "cumulative.summary",
    "#queue-start": "queue.start",
    "#queue-stop": "queue.stop",
    "#queue-refresh": "queue.status",
    "#queue-fetch": "queue.fetch",
    "#liq-refresh": "liquidity.status",
    "#liq-kill": "liquidity.kill",
    "#liq-resume": "liquidity.resume",
    "#docs-save": "docs.write",
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
    """The console: thirteen tabs over the tested modules."""

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
        ("f5", "liq_refresh", "Liquidity: refresh"),
        ("f8", "liq_toggle_kill", "Liquidity: kill/resume"),
    ]

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        # One live Context for the app's life: the registry commands this console dispatches read and
        # mutate these same objects, so in-memory state and command results cannot disagree.
        self.ctx = Context.from_settings(settings or load_settings(), Runtime())
        # Populated when the Docs tab composes.
        self._docs_listing: dict[str, Any] = {}
        self._docs_loaded = False
        # The catalogue path currently shown in the Docs viewer, and whether `docs.read` returned
        # real text for it (vs a placeholder for a binary/oversized file) -- the Save button trusts
        # this, not the cheap per-row "editable" column, before writing.
        self._docs_current_path: str | None = None
        self._docs_current_editable = False
        # The row the DataTable cursor is on, kept independently of what is actually loaded.
        self._docs_highlighted_path: str | None = None
        # The text as it was on disk when _docs_current_path was loaded, to detect unsaved edits.
        self._docs_loaded_text = ""
        self._cumulative_loaded = False
        # Last results-file mtime the Queue tab rendered (the worker is a separate process).
        self._queue_mtime = 0.0
        # Liquidity tab: last rendered file signature, so the 15 s tick rebuilds the tables only
        # when a file actually changed (a rebuild resets the table cursors).
        self._liq_signature: list | None = None
        # Resume removes a safety stop; the first press only arms it (see `_liq_resume_pressed`).
        self._liq_resume_armed_at = 0.0
        self._top5_loaded = False
        self._top5_configs: list[dict[str, Any]] = []

    # State lives on the Context; these keep the names the rest of the app (and tests) use.
    @property
    def settings(self) -> Settings:
        return self.ctx.settings

    @settings.setter
    def settings(self, value: Settings) -> None:
        self.ctx.settings = value

    @property
    def roster(self):
        return self.ctx.roster

    @roster.setter
    def roster(self, value) -> None:
        self.ctx.roster = value

    @property
    def signals(self) -> SignalDefaults:
        return self.ctx.signals

    @signals.setter
    def signals(self, value: SignalDefaults) -> None:
        self.ctx.signals = value

    @property
    def state(self):
        return self.ctx.state

    @property
    def runner(self):
        return self.ctx.runner

    @property
    def session(self):
        return self.ctx.session

    @property
    def _docs(self) -> list[docs_browser.DocEntry]:
        try:
            return self.ctx.catalog()
        except docs_browser.CatalogUnavailable:
            return []

    @_docs.setter
    def _docs(self, value: list[docs_browser.DocEntry]) -> None:
        self.ctx.catalog_override = value

    def _call(self, name: str, params: dict[str, Any] | None = None, *,
              quiet: bool = False) -> dict[str, Any]:
        """Every action goes through the registry, exactly as the CLI, API and extension do."""
        return dispatch(name, params or {}, surface="tui", ctx=self.ctx, quiet=quiet)

    @staticmethod
    def _msg(env: dict[str, Any]) -> str:
        return env["error"]["message"]

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
            with TabPane("Liquidity", id="tab-liquidity"):
                yield from self._liquidity_pane()
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
        for row in self._call("strategies.list")["result"]:
            avail.add_row(row["name"], row["family"], key=row["name"])

        roster_t = self.query_one("#roster-table", DataTable)
        roster_t.add_columns("in roster", "family", "warm-up")
        roster_t.cursor_type = "row"
        self._refresh_roster_table()

        reference = self._call("signals.reference")["result"]
        sig = self.query_one("#signals-table", DataTable)
        sig.add_columns("signal", "equation", "family")
        for r in reference["signals"]:
            sig.add_row(r["signal"], r["equation"], r["family"])

        fam_t = self.query_one("#families-table", DataTable)
        fam_t.add_columns("family", "what it is / when it fails")
        for r in reference["families"]:
            fam_t.add_row(r["family"], r["note"])

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
        self.set_interval(liq.REFRESH_SECONDS, self._liq_tick)
        self._refresh_liquidity(force=True)

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

        Stat, compare, and usually return: the worker is a separate process whose results file
        changes at the pace of a CPCV evaluation, so a full `queue.status` on every tick would be
        work for nothing. The cheap `queue.progress` keeps the status line live; polling is not
        logged (only calls somebody asked for are).
        """
        if not self.query("#queue-status"):
            return
        if _mtime(bgqueue.RESULTS_PATH) != self._queue_mtime:
            self._refresh_queue()
            return
        # Deliberately NOT gated on the worker being alive: a crashed worker leaves state.json
        # reading "running", and skipping the render would freeze the pane on its last line.
        env = self._call("queue.progress", quiet=True)
        if env["ok"]:
            self.query("#queue-status").first(Static).update(env["result"]["summary"])

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
        """Read the form, then settings.save validates and persists."""
        status = self.query_one("#settings-status", Static)
        try:
            params = self._read_form()
        except ValueError as exc:
            status.update(f"[red]{type(exc).__name__}: {exc}[/]")
            return
        env = self._call("settings.save", params)
        status.update(f"saved → {env['result']['path']}" if env["ok"]
                      else f"[red]{self._msg(env)}[/]")

    def _read_form(self) -> dict[str, Any]:
        """Coerce form inputs to their field types. A blank number keeps the saved value."""
        casts: dict[str, Any] = {
            "asset": str, "start": str, "end": str, "capital": float,
            "fee_bps": float, "slippage_bps": float, "fill_delay": int,
            "cpcv_groups": int, "cpcv_k": int,
        }
        out: dict[str, Any] = {}
        for name, cast in casts.items():
            raw = self.query_one(f"#set-{name}", Input).value.strip()
            if raw or cast is str:
                out[name] = cast(raw)
        out["interval"] = str(self.query_one("#set-interval", Select).value)
        return out

    # -- roster ----------------------------------------------------------

    def _refresh_roster_table(self) -> None:
        """Redraw the roster side."""
        t = self.query_one("#roster-table", DataTable)
        t.clear()
        for e in self._call("roster.list")["result"]["entries"]:
            t.add_row(e["label"], e["family"], str(e["warmup"]), key=e["label"])

    def _refresh_exec_choices(self) -> None:
        """Keep the Execute strategy picker in sync with the roster."""
        sel = self.query_one("#exec-strategy", Select)
        labels = [e["label"] for e in self._call("roster.list")["result"]["entries"]]
        sel.set_options([(label, label) for label in labels])

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
            name = str(table.get_row_at(table.cursor_row)[0])
            explicit = self._parse_params()
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")
            return
        env = self._call("roster.add", {"name": name, "params": explicit})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        added = env["result"]["added"]
        self._refresh_roster_table()
        self._refresh_exec_choices()
        status.update(f"added {added['label']} (warm-up {added['warmup']} bars)")

    @on(Button.Pressed, "#btn-remove")
    def _remove(self) -> None:
        """Remove the highlighted roster entry."""
        status = self.query_one("#roster-status", Static)
        table = self.query_one("#roster-table", DataTable)
        try:
            label = str(table.get_row_at(table.cursor_row)[0])
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")
            return
        env = self._call("roster.remove", {"label": label})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        self._refresh_roster_table()
        self._refresh_exec_choices()
        status.update(f"removed {env['result']['removed']['label']}")

    @on(Button.Pressed, "#btn-reset-roster")
    def _reset_roster(self) -> None:
        """Restore the backtester's default comparison set."""
        self._call("roster.reset")
        self._refresh_roster_table()
        self._refresh_exec_choices()
        self.query_one("#roster-status", Static).update("roster reset to default")

    def _strategy_source_path(self, name: str) -> str | None:
        """Catalogue-relative path to the file that defines strategy `name`, or None.

        `strategies.source` resolves it with `inspect.getfile` rather than a hand-kept table and
        fails closed for a file missing from the Docs catalogue (the catalogue is an allowlist).
        """
        env = self._call("strategies.source", {"name": name})
        return env["result"]["path"] if env["ok"] else None

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
        """Read the signal form; signals.save validates and persists."""
        status = self.query_one("#signals-status", Static)
        values = {name: self.query_one(f"#sig-{name}", Input).value
                  for _, names in SIGNAL_GROUPS for name in names}
        env = self._call("signals.save", {"values": values})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        status.update(f"saved → {r['path']} · affects {r['affects']} strategies")

    @on(Button.Pressed, "#btn-reset-signals")
    def _reset_signals(self) -> None:
        """Restore the backtester's shipped signal values."""
        env = self._call("signals.reset")
        for name, value in env["result"]["values"].items():
            widgets = self.query(f"#sig-{name}")
            if widgets:
                widgets.first(Input).value = str(value)
        self.query_one("#signals-status", Static).update("reset to shipped defaults")

    # -- backtest --------------------------------------------------------

    def action_run_backtest(self) -> None:
        """Keyboard binding for running a sweep."""
        self._run()

    def action_cancel(self) -> None:
        """Keyboard binding for cancelling."""
        self._call("backtest.cancel")

    @on(Button.Pressed, "#btn-cancel")
    def _cancel_pressed(self) -> None:
        """Ask the worker to stop at the next configuration boundary."""
        self._call("backtest.cancel")
        self.query_one("#backtest-status", Static).update("cancelling…")

    @on(Button.Pressed, "#btn-run")
    def _run(self) -> None:
        """Start a CPCV sweep over the roster (the work is the `backtest.run` command)."""
        self.query_one("#backtest-status", Static).update("running…")
        self._sweep_worker()

    @work(thread=True, group="sweep")
    def _sweep_worker(self) -> None:
        """Thread only so the UI stays live; the sweep itself is the registry handler."""
        env = self._call("backtest.run")
        self.call_from_thread(self._render_results, env)

    def _render_results(self, env: dict[str, Any]) -> None:
        """Fill the results table, best median Sharpe first."""
        status = self.query_one("#backtest-status", Static)
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        table = self.query_one("#results-table", DataTable)
        table.clear()
        for row in r["rows"]:
            table.add_row(
                row["label"], row["family"], f"{row['median_sharpe']:+.3f}", f"{row['iqr']:.3f}",
                f"{row['frac_positive']:.0%}", format_pct(row["median_return"]), str(row["trades"]),
            )
        status.update(r["message"])

    @on(Button.Pressed, "#btn-run-untested")
    @work(thread=True)
    def _run_untested_sweep(self) -> None:
        """Run the untested sweep (the `backtest.untested_sweep` command) off the UI thread."""
        status = self.query_one("#backtest-status", Static)
        self.call_from_thread(status.update, "running untested sweep...")
        env = self._call("backtest.untested_sweep")
        if env["ok"]:
            self.call_from_thread(status.update, f"untested sweep done.\n{env['result']['output']}")
        else:
            self.call_from_thread(status.update, f"[red]{self._msg(env)}[/]")

    # -- execute (dry run) -----------------------------------------------

    @on(Button.Pressed, "#btn-paper-start")
    @work(thread=True, exclusive=True)
    def _paper_start(self) -> None:
        """Run one backtest and open a replay cursor over it (`paper.start`)."""
        value = self.query_one("#exec-strategy", Select).value
        env = self._call("paper.start", {"label": value if isinstance(value, str) else ""})
        self.call_from_thread(self._refresh_paper, env)

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
        self._refresh_paper(self._call("paper.seek_end"))

    @on(Button.Pressed, "#btn-paper-reset")
    def _paper_reset(self) -> None:
        """Rewind the replay."""
        self._refresh_paper(self._call("paper.reset"))

    def _step(self, bars: int) -> None:
        """Advance the cursor and redraw."""
        self._refresh_paper(self._call("paper.step", {"bars": bars}))

    def _refresh_paper(self, env: dict[str, Any]) -> None:
        """Redraw the replay summary and the intended-fills table from a paper.* result."""
        summary = self.query_one("#exec-summary", Static)
        if not env["ok"]:
            summary.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        summary.update(r["text"])
        table = self.query_one("#fills-table", DataTable)
        table.clear()
        for f in r["fills"]:
            table.add_row(
                str(f["bar"]), f["when"], f["side"], f["reason"], f"{f['price']:,.2f}",
                f"{f['units']:,.4f}", f"{f['cost']:,.2f}", f"{f['equity']:,.2f}",
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
        elif pane == "tab-liquidity":
            self._refresh_liquidity(force=True)
        elif pane == "tab-top5" and not self._top5_loaded:
            self._top5_loaded = True
            self._refresh_top5()
        elif pane == "tab-liverun":
            self._refresh_live_run()

    # -- Live Run --------------------------------------------------------

    def _refresh_live_run(self) -> None:
        best = self._call("live.recommendation")["result"]
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
        if not strategy_name:
            self.call_from_thread(status.update, "[red]Please enter a strategy name.[/red]")
            return
        self.call_from_thread(status.update, f"running dry run for {strategy_name}...")
        env = self._call("live.spawn_dryrun", {"strategy": strategy_name})
        if env["ok"]:
            text = "Dryrun finished successfully.\n" + env["result"]["stdout"]
            self.call_from_thread(status.update, "dry run finished")
        else:
            text = self._msg(env)
            self.call_from_thread(status.update, f"[red]{text.splitlines()[0]}[/]")
        self.call_from_thread(lambda: setattr(out_area, "text", text))

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
        env = self._call("top5.list")
        if not env["ok"]:
            self._top5_configs = []
            headline.update(f"[b]{self._msg(env)}[/b]")
            return
        r = env["result"]
        self._top5_configs = r["configs"]

        def fmt(v: float | None, spec: str) -> str:
            return "-" if v is None else format(v, spec)

        table = self.query_one("#top5-table", DataTable)
        table.clear()
        for cfg in self._top5_configs:
            home = cfg["home"]
            if home is None:
                continue
            table.add_row(
                str(cfg["rank"]), cfg["label"], cfg["horizon"],
                " + ".join(cfg["members"]) + (f" ({cfg['mode']})" if cfg["mode"] != "single" else ""),
                f"{home['median_sharpe']:+.3f}", fmt(home["iqr"], ".3f"),
                fmt(home["frac_positive"], ".0%"),
                "-" if home["median_return"] is None else format_pct(home["median_return"]),
                fmt(home["trades"], "d"), fmt(home["n_paths"], "d"),
                key=str(cfg["rank"]),
            )
        transfers = self.query_one("#top5-transfers", DataTable)
        transfers.clear()
        for cfg in self._top5_configs:
            for t in cfg["transfers"]:
                transfers.add_row(
                    str(cfg["rank"]), cfg["label"], t["asset"],
                    f"{t['median_sharpe']:+.3f}", fmt(t["delta_vs_sol"], "+.3f"),
                    fmt(t["frac_positive"], ".0%"),
                    "-" if t["median_return"] is None else format_pct(t["median_return"]),
                    fmt(t["trades"], "d"), fmt(t["n_paths"], "d"),
                )
        headline.update(
            f"{len(self._top5_configs)} configurations · fitted on {r['home_asset']} · "
            f"each transfer-tested on {', '.join(r['transfer_assets'])}")

    def _top5_add_members(self, ranks: list[int] | None) -> None:
        """Add each distinct member signal to the roster, reporting per-name.

        `top5.add_to_roster` uses the same path as the Strategies tab's Add button (signal defaults
        via merged_params). Already-present names are counted, not errors -- clicking twice must not
        turn into a wall of red.
        """
        status = self.query_one("#top5-status", Static)
        env = self._call("top5.add_to_roster", {"ranks": ranks} if ranks is not None else {})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        added, present = env["result"]["added"], env["result"]["present"]
        self._refresh_roster_table()
        self._refresh_exec_choices()
        parts = []
        if added:
            parts.append(f"added {', '.join(added)}")
        if present:
            parts.append(f"already in roster: {', '.join(present)}")
        status.update((" · ".join(parts) or "nothing to add") +
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
        if not any(c["rank"] == rank for c in self._top5_configs):
            status.update("select a configuration row first")
            return
        self._top5_add_members([rank])

    @on(Button.Pressed, "#top5-add-all")
    def _top5_add_all(self) -> None:
        if not self._top5_configs:
            self.query_one("#top5-status", Static).update("no configurations loaded")
            return
        self._top5_add_members(None)

    @on(Button.Pressed, "#top5-run")
    def _top5_run(self) -> None:
        """Start the same CPCV sweep the Backtest tab runs, from here."""
        self.query_one("#top5-status", Static).update("running — results land on the Backtest tab")
        self._sweep_worker()

    @on(Button.Pressed, "#top5-reload")
    def _top5_reload(self) -> None:
        self._refresh_top5()

    # -- Analyze: any coin, any moment -----------------------------------

    def _analyze_pane(self) -> ComposeResult:
        """Replay every rule up to a chosen timestamp, for a chosen coin.

        Distinct from the Signals tab, which reads the *latest* bar of the
        configured asset. Here the coin and the moment are both inputs.
        """
        pairs = self._call("analyze.assets")["result"]
        options = [(f"{p['asset']} {p['interval']}", f"{p['asset']}|{p['interval']}") for p in pairs]
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
        params: dict[str, Any] = {"asset": asset, "interval": interval}
        if raw:
            params["as_of"] = raw
        env = self._call("analyze.run", params)
        if not env["ok"]:
            head.update(f"[b]could not analyse:[/b] {self._msg(env)}")
            return
        r = env["result"]
        head.update(r["headline"] + ("" if r["truncated"] else "   (latest bar)"))
        table = self.query_one("#analyze-table", DataTable)
        table.clear()
        for d in r["decisions"]:
            table.add_row(d["name"], d["family"], d["action"], d["detail"],
                          str(d["warmup"]), str(d["bars"]))

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
        env = self._call("cumulative.summary")
        if not env["ok"]:
            self.query_one("#cumulative-headline", Static).update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        self.query_one("#cumulative-headline", Static).update(r["headline"])
        table = self.query_one("#cumulative-table", DataTable)
        table.clear()
        for s in r["files"]:
            best, med = s["best"], s["median_sharpe"]
            table.add_row(
                s["source"], str(s["rankable"]), str(s["below_floor"]),
                str(s["positive"]), str(s["made_money"]),
                "-" if med is None else f"{med:+.3f}",
                s["path_range"],
                "-" if best is None else f"{best['label']} {best['median_sharpe']:+.3f}",
            )
        drop = self.query_one("#cumulative-dropped", DataTable)
        drop.clear()
        for c in r["casualties"]:
            drop.add_row(c["source"], c["label"], f"{c['median_sharpe']:+.3f}",
                         str(c["trades"]), str(c["n_paths"]))

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
        env = self._call("queue.start")
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        status.update("started — results appear as each job lands")
        self._refresh_queue()

    @on(Button.Pressed, "#queue-stop")
    def _queue_stop(self) -> None:
        """Ask the worker to stop at the next job boundary."""
        status = self.query_one("#queue-status", Static)
        if self._call("queue.stop")["result"]["stopping"]:
            status.update("stopping — the current job finishes first")
        else:
            status.update("no background sweep is running")

    @on(Button.Pressed, "#queue-refresh")
    def _queue_refresh(self) -> None:
        self._refresh_queue()

    @on(Button.Pressed, "#queue-fetch")
    def _queue_fetch(self) -> None:
        """Fetch the price series the sweep is missing (`queue.fetch`).

        The one network action in this package, and it stays the separate explicit step
        `CLAUDE.md` requires: starting a sweep is NOT a side effect of it finishing.
        """
        data = self.query_one("#queue-data", Static)
        env = self._call("queue.fetch")
        if not env["ok"]:
            data.update(f"[red]{self._msg(env)}[/]")
            return
        fetching = env["result"]["fetching"]
        if not fetching:
            data.update("every series this sweep needs is already cached")
            return
        names = ", ".join(f"{m['asset']} {m['interval']}" for m in fetching)
        data.update(f"fetching {names} — press Refresh when it finishes "
                    f"(log: {env['result']['log']})")

    def _render_queue_data(self, missing: list[dict[str, Any]], fetch_log: str | None) -> None:
        """Say which series are missing, and name the command that fixes it.

        Checked before the sweep rather than discovered during it: the queue interleaves intervals
        by promise, so a missing 1h file would otherwise surface minutes in.
        """
        line = self.query("#queue-data")
        if not line:
            return
        if not missing:
            line.first(Static).update("")
            return
        commands = "  ·  ".join(m["command"] for m in missing)
        text = (
            f"[yellow]missing price data — {len(missing)} series "
            f"({', '.join(m['interval'] for m in missing)}) will be skipped:[/] {commands}"
        )
        # A fetch that already ran and left the series missing failed for a reason worth reading.
        if fetch_log:
            text += f"  ·  a previous fetch left these missing; see {fetch_log}"
        line.first(Static).update(text)

    def _refresh_queue(self) -> None:
        """Re-read the worker's files (`queue.status`) and redraw both tables."""
        env = self._call("queue.status")
        if not env["ok"]:
            self.query_one("#queue-status", Static).update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        self._queue_mtime = _mtime(bgqueue.RESULTS_PATH)
        self._render_queue_data(r["missing"], r["fetch_log"])
        self.query_one("#queue-status", Static).update(r["summary"])
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        for x in r["ranked"]:
            table.add_row(
                x["label"], x["family"], f"{x['median_sharpe']:+.3f}", f"{x['iqr']:.3f}",
                f"{x['frac_positive']:.0%}", format_pct(x["median_return"]), str(x["trades"]),
            )
        floor_table = self.query_one("#queue-floor", DataTable)
        floor_table.clear()
        for x in r["floor"]:
            floor_table.add_row(x["label"], x["family"], str(x["trades"]), x["why"])

    # -- Liquidity: the Aero LP daemon's state files ---------------------

    def _liquidity_pane(self) -> ComposeResult:
        """A read-only view of `status.json` / `scout.json`, plus the KILL switch.

        soltui holds no keys and has no order path: the daemon (`liquidity/`)
        does the managing and writes files; this pane reads them. The only thing
        it writes is the `KILL` file, via the Kill/Resume buttons.
        """
        with VerticalScroll():
            yield Static("", id="liq-banner")
            yield Static("", id="liq-summary")
            yield Static("", id="liq-wallet", classes="hint")
            with Horizontal(classes="form-row"):
                yield Button("Refresh", id="liq-refresh")
                yield Button("Kill", variant="error", id="liq-kill")
                yield Button("Resume", variant="success", id="liq-resume")
            yield Static("", id="liq-status", classes="hint")
            yield Static("[b]Positions[/b]", classes="hint")
            yield DataTable(id="liq-positions")
            yield Static("[b]Scout[/b] — top pools by modelled net APR", classes="hint")
            yield Static("", id="liq-scout-note", classes="hint")
            yield DataTable(id="liq-scout")
            yield Static("[b]Experiments[/b] — arms side by side", classes="hint")
            yield DataTable(id="liq-experiments")
            yield Static("[b]Recent actions[/b] — newest first", classes="hint")
            yield DataTable(id="liq-actions")

    def _liq_tick(self) -> None:
        """Auto-refresh. A no-op until the pane exists (teardown-safe)."""
        if self.query("#liq-summary"):
            self._refresh_liquidity(quiet=True)

    def _fill_table(self, table_id: str, table: dict[str, Any]) -> None:
        widget = self.query_one(table_id, DataTable)
        widget.clear(columns=True)
        widget.add_columns(*table["headers"])
        # Text() so a "[" in a daemon-supplied reason is never read as markup.
        for row in table["rows"]:
            widget.add_row(*(Text(cell) for cell in row))

    def _refresh_liquidity(self, force: bool = False, quiet: bool = False) -> None:
        """Re-read the state files (`liquidity.status`) and redraw.

        The summary and banner are redrawn every time (the "updated Ns ago" text must keep moving,
        and a stale daemon must show). The tables are rebuilt only when a file changed, or on `force`.
        """
        if not self.query("#liq-summary"):
            return
        env = self._call("liquidity.status", quiet=quiet)
        if not env["ok"]:
            self.query_one("#liq-summary", Static).update(Text(self._msg(env)))
            return
        r = env["result"]
        banner = self.query_one("#liq-banner", Static)
        summary = self.query_one("#liq-summary", Static)
        wallet = self.query_one("#liq-wallet", Static)
        if r["summary"] is None:
            summary.update(Text(f"Liquidity: no data. {r['status_reason']}"))
            wallet.update("")
        else:
            badge = Text(f" {r['mode_badge']} ",
                         style="bold white on red" if r["live"] else "bold black on yellow")
            summary.update(Text.assemble(badge, "  ", r["summary"]))
            wallet.update(Text(r["wallet"]))
        if r["killed"]:
            banner.update(Text(
                " Kill switch ON — bot paused. It sends no transactions and leaves "
                "positions as they are. Press Resume (F8) to restart it. ",
                style="bold white on red"))
        else:
            banner.update("")
        if force or r["signature"] != self._liq_signature:
            self._liq_signature = r["signature"]
            for name in ("positions", "experiments", "actions", "scout"):
                self._fill_table(f"#liq-{name}", r["tables"][name])
            self.query_one("#liq-scout-note", Static).update(Text(r["scout_note"]))

    @on(Button.Pressed, "#liq-refresh")
    def _liq_refresh_pressed(self) -> None:
        self._refresh_liquidity(force=True)
        self.query_one("#liq-status", Static).update("refreshed")

    @on(Button.Pressed, "#liq-kill")
    def _liq_kill_pressed(self) -> None:
        self._liq_set_kill(True)

    @on(Button.Pressed, "#liq-resume")
    def _liq_resume_pressed(self) -> None:
        """Resume deletes the KILL file, so it is confirmed: press twice within 10 s.

        The registry refuses `liquidity.resume` without confirm=true on every surface; here the
        first press arms it and the second one supplies the confirmation.
        """
        self._liq_set_kill(False)

    def _liq_set_kill(self, on: bool) -> None:
        """The pane's only write: create (`liquidity.kill`) or delete (`liquidity.resume`) KILL."""
        status = self.query_one("#liq-status", Static)
        if on:
            env = self._call("liquidity.kill")
        else:
            now = time.monotonic()
            if now - self._liq_resume_armed_at > 10.0:
                self._liq_resume_armed_at = now
                status.update(Text("Resume removes the kill switch and lets the daemon act on real "
                                   "money. Press Resume again within 10 s to confirm."))
                return
            self._liq_resume_armed_at = 0.0
            env = self._call("liquidity.resume", {"confirm": True})
        if not env["ok"]:
            status.update(Text(self._msg(env)))
            return
        home = env["result"]["home"]
        status.update(Text(
            f"KILL file created in {home}" if on
            else f"KILL file removed from {home}; the daemon may act again"))
        self._refresh_liquidity(force=True)

    def _liq_tab_active(self) -> bool:
        return self.query_one(TabbedContent).active == "tab-liquidity"

    def action_liq_refresh(self) -> None:
        if self._liq_tab_active():
            self._liq_refresh_pressed()

    def action_liq_toggle_kill(self) -> None:
        if self._liq_tab_active():
            killed = self._call("liquidity.status", quiet=True)["result"]["kill_file"]
            self._liq_set_kill(not killed)

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
            research = self._call("research.get")["result"]
            for r in research["drivers"]:
                table.add_row(r["driver"], r["answers"], r["established"])
            yield table
            yield Static("[b]Findings that constrain every figure above[/b]",
                         classes="hint")
            for line in research["findings"]:
                yield Static(f"• {line}")

    # -- Docs: read-only explorer over every tracked file ----------------

    def _docs_pane(self) -> ComposeResult:
        """Browse every file in the repo; open one with a click, Enter, or "o".

        The viewer itself lives in `_editor_pane`, not here -- it is shared
        across every tab. Editable per `docs_browser.is_editable` opens
        read-write there with Save enabled; everything else (and all of
        `research/results/`) opens read-only.
        """
        env = self._call("docs.list", {"limit": 0})
        if not env["ok"]:
            self._docs_listing = {}
            with VerticalScroll():
                yield Static(self._msg(env), id="docs-empty")
            return
        self._docs_listing = env["result"]
        kinds = [("all kinds", "")] + [(k, k) for k in self._docs_listing["kinds"]]
        with Vertical():
            yield Static(self._docs_listing["headline"], id="docs-headline")
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
        if not self._docs_listing:
            return
        query = self.query_one("#docs-filter", Input).value
        kind = self.query_one("#docs-kind", Select).value
        env = self._call("docs.list", {"query": query, "kind": kind if isinstance(kind, str) else ""})
        if not env["ok"]:
            self.query_one("#docs-headline", Static).update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        table = self.query_one("#docs-table", DataTable)
        table.clear()
        for e in r["entries"]:
            table.add_row(e["path"], e["kind"], "yes" if e["editable"] else "", str(e["lines"]),
                          e["summary"][:90], key=e["path"])
        # The cap keeps the table responsive; say so when it bites instead of silently hiding files.
        capped = (f" (first {r['shown']} listed; filter to narrow)"
                  if r["matched"] > r["shown"] else "")
        self.query_one("#docs-headline", Static).update(
            f"{r['matched']} of {r['total']} match{capped} · {r['headline']}")

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

        env = self._call("docs.read", {"path": path})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        text, language = env["result"]["text"], env["result"]["language"]
        editable = env["result"]["editable"]

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
        """Write the viewer's current text back to disk (`docs.write`).

        The keypress/click itself is the confirm-on-save step. `docs.write` re-checks editability
        against the live catalogue rather than trusting `_docs_current_editable`, so a stale
        binding cannot write somewhere the current rules would refuse.
        """
        status = self.query_one("#docs-view-status", Static)
        if not self._docs_current_path or not self._docs_current_editable:
            status.update("nothing editable is open")
            return
        path = self._docs_current_path
        text = self.query_one("#docs-view", TextArea).text
        env = self._call("docs.write", {"path": path, "text": text})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        self._docs_loaded_text = text
        status.update(f"{path} — saved")

def main(argv: list[str] | None = None) -> int:
    """Entry point for `python3 -m soltui.tui`."""
    SolTuiApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets.option_list import Option
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Select,
    Static,
    TabbedContent,
    Tab,
    TabPane,
    TextArea,
)

from .help import HEADER_GLOSSARY, column_help, control_help, row_help, TAB_HELP
from .help_screen import HelpScreen
from backtester.core import scorecard as sc

from . import bgcontrol
from . import compound as compound_mod
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
from .config import INTERVALS, XPUB_FIELDS, Settings, load_settings
from .hdwallet import redact
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


def _pct(value: Any) -> str:
    """0.5321 -> '53.2%'; None -> '-'. Shared by the Compound tables."""
    return "-" if value is None else f"{100.0 * float(value):.1f}%"


def _num(value: Any) -> str:
    return "-" if value is None else f"{float(value):+.3g}"


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
    "#btn-bt-selected": "queue.backtest",
    "#btn-bt-untested": "queue.backtest",
    "#btn-bt-all": "queue.backtest",
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
    "#pnl-run": "pnl.summary",
    "#wallet-scan": "portfolio.scan",
    "#docs-search-run": "docs.search",
    "#docs-search-free": "docs.search_unload",
    "#compound-toggle": "compound.save",
    "#compound-apply": "compound.save",
    "#compound-reset": "compound.reset",
    "#compound-signal": "compound.signal",
    "#compound-backtest": "compound.backtest",
    "#compound-forward": "compound.forward_tick",
    "#compound-auto": "compound.forward_tick",
    "#compound-refresh": "compound.forward_status",
    "#compound-adopt": "compound.save",
}

class GlossaryTable(DataTable):
    """Explain headers and values using their actual column and table context.

    Textual tooltips are per-widget, not per-cell, so a static tooltip could
    only describe the whole table. Header cells carry their position in the
    segment style meta (`row == -1` marks the header row). The same definition
    follows values in that column; recognised signal rows add their mechanism.
    Leaving the table or moving outside a real cell clears the old explanation.
    """

    def header_tooltip(self, column_index: int) -> str | None:
        """The glossary entry for one column, or None when there isn't one."""
        if column_index < 0:
            return None
        try:
            label = str(self.ordered_columns[column_index].label)
        except IndexError:
            return None
        return column_help(label, self.id)

    def cell_tooltip(self, column_index: int, row_index: int = -1) -> str | None:
        """Use the same definition on a value as on its header."""
        explanation = self.header_tooltip(column_index)
        if 0 <= row_index < self.row_count and self.id in {
            "available-table", "roster-table", "signals-table", "families-table",
            "results-table", "analyze-table", "queue-table", "queue-floor",
        }:
            try:
                specific = row_help(str(self.get_row_at(row_index)[0]))
            except (IndexError, KeyError):
                specific = None
            if specific:
                explanation = f"{specific}\n\n{explanation}" if explanation else specific
        return explanation

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        super()._on_mouse_move(event)
        meta = event.style.meta
        tooltip = None
        if meta and not meta.get("out_of_bounds") and meta.get("column", -1) >= 0:
            tooltip = self.cell_tooltip(meta["column"], meta.get("row", -1))
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
    """The console: sixteen tabs over the tested modules."""

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
    .preset-list { height: 7; margin-bottom: 1; }
    DataTable { height: 1fr; }
    #available-table { width: 3fr; }
    #roster-table { width: 1fr; }
    #docs-filter, #docs-search { width: 1fr; }
    #docs-kind, #docs-search-mode { width: 24; }
    TabbedContent { height: 1fr; }
    #editor-panel {
        height: 16;
        border-top: solid $accent;
    }
    #editor-panel TextArea { height: 1fr; }
    Tooltip { max-width: 76; height: auto; max-height: 18; }
    #help-hint { height: 1; color: $text-muted; padding: 0 1; }
    #compound-table { height: 22; }
    #compound-results { height: 14; }
    #compound-forward { height: 12; }
    #compound-call { padding: 0 1; border: round $accent; }
    #compound-detail { color: $text-muted; padding: 0 1; }
    """
    BINDINGS = [
        Binding("f1", "show_help", "Help / glossary", priority=True),
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
        # Top 5 presets from `top5.presets`, or the reason there are none. Filled before compose.
        self._presets: list[dict[str, Any]] = []
        self._presets_error = ""
        self._analyze_preset = ""
        self._analyze_values: set[str] = set()
        self._pnl_loaded = False

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

    def _load_presets(self) -> None:
        env = self._call("top5.presets", quiet=True)
        if env["ok"]:
            self._presets, self._presets_error = env["result"]["presets"], ""
        else:
            self._presets, self._presets_error = [], self._msg(env)

    def _preset_list(self, tab: str) -> ComposeResult:
        """The Top 5 as clickable options (`OptionList`); a click fills this tab's fields."""
        yield Static("Top 5 presets — click one to fill this tab:", classes="hint")
        if not self._presets:
            yield Static(f"no presets: {self._presets_error or 'Top 5 evidence not loaded'}",
                         classes="hint", id=f"preset-{tab}-empty")
            return
        yield OptionList(*[Option(f"{p['title']}   {p['net_pct_text']}", id=p["value"])
                           for p in self._presets], id=f"preset-{tab}", classes="preset-list")

    def compose(self) -> ComposeResult:
        """Build the tab set."""
        self._load_presets()
        yield Header()
        yield Static(build_title(self.state), id="indicator")
        yield Static("Hover a control, table header or value for help · F1: searchable glossary",
                     id="help-hint", markup=False)
        with TabbedContent(initial="tab-backtest"):
            with TabPane("Settings", id="tab-settings"):
                yield from self._settings_pane()
            with TabPane("Strategies", id="tab-strategies"):
                yield from self._strategies_pane()
            with TabPane("Signals", id="tab-signals"):
                yield from self._signals_pane()
            with TabPane("Compound 5m", id="tab-compound"):
                yield from self._compound_pane()
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
            with TabPane("P&L", id="tab-pnl"):
                yield from self._pnl_pane()
            with TabPane("Wallet", id="tab-wallet"):
                yield from self._wallet_pane()
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
            # At the top so the button stays on screen however many fields the form grows.
            with Horizontal(classes="form-row"):
                yield Button("Save settings", variant="primary", id="btn-save")
                yield Static("", id="settings-status")
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
                ("solana_address", "Solana address (public)"),
                ("base_address", "Base address (public)"),
                ("eth_address", "Ethereum address (public)"),
                ("btc_xpub", "Bitcoin xpub (public key)"),
                ("ltc_xpub", "Litecoin xpub (public key)"),
                ("doge_xpub", "Dogecoin xpub (public key)"),
            ):
                with Horizontal(classes="form-row"):
                    yield Label(f"{label}:")
                    if field_name in XPUB_FIELDS:
                        # An xpub exposes the wallet's whole history, so it is never shown back in full.
                        # Blank keeps the saved key; 'clear' removes it.
                        current = getattr(self.settings, field_name)
                        yield Input(value="", id=f"set-{field_name}", placeholder=(
                            f"set ({redact(current)}) - paste a new key to replace, 'clear' to remove"
                            if current else "not set - paste an extended PUBLIC key (xpub)"))
                    else:
                        yield Input(
                            value=str(getattr(self.settings, field_name)),
                            id=f"set-{field_name}",
                        )
            yield Static("Wallet fields take public addresses and extended public keys only. A private key "
                         "(xprv, a 64-hex key, a Solana secret-key array) is refused.", classes="hint")
            with Horizontal(classes="form-row"):
                yield Label("Interval:")
                yield Select(
                    [(i, i) for i in INTERVALS],
                    value=self.settings.interval,
                    id="set-interval",
                    allow_blank=False,
                )
            yield Static("[b]Signing key source[/b] (read-only; stat only, the files are never opened)",
                         classes="hint")
            yield Static("", id="key-sources")

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
            with Horizontal(classes="form-row"):
                yield Button("Backtest selected", variant="warning", id="btn-bt-selected")
                yield Button("Backtest all untested", variant="warning", id="btn-bt-untested")
                yield Button("Backtest all", variant="warning", id="btn-bt-all")
            yield Static("", id="history-status")
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

    def _compound_pane(self) -> ComposeResult:
        """Compound five-minute call: toggle and tune each metric, backtest and forward test them.

        Every action is a `compound.*` registry command; this pane only renders.
        """
        with VerticalScroll(id="compound-scroll"):
            yield Static(
                "Each metric scores the next 5m bar from -1 (down) to +1 (up). Families vote once, "
                "the regime reweights trend vs reversion styles, and any enabled gate forces FLAT. "
                "Select a row, then Toggle or edit its numbers. Nothing here places an order.",
                classes="hint",
            )
            yield Static("Press Signal now for the live call.", id="compound-call")
            yield GlossaryTable(id="compound-table")
            yield Static("", id="compound-detail")
            with Horizontal(classes="form-row"):
                yield Label("Selected (k=v):")
                yield Input(placeholder="weight=1.5 period=9 enabled=1", id="compound-edit")
            with Horizontal(classes="form-row"):
                yield Label("Aggregate (k=v):")
                yield Input(placeholder="entry=0.25 exit=0.1 leverage=5 fee_bps=6", id="compound-agg")
            with Horizontal(classes="form-row"):
                yield Button("Toggle on/off", id="compound-toggle")
                yield Button("Apply edits", variant="primary", id="compound-apply")
                yield Button("Reset defaults", id="compound-reset")
                yield Button("Adopt tuned settings", id="compound-adopt")
            with Horizontal(classes="form-row"):
                yield Button("Signal now", variant="success", id="compound-signal")
                yield Button("Backtest selected", variant="warning", id="compound-backtest")
                yield Button("Forward tick", id="compound-forward")
                yield Button("Auto-forward: off", id="compound-auto")
                yield Button("Refresh results", id="compound-refresh")
            yield Static("", id="compound-status")
            yield Static(
                "Backtest, latest run: the compound and each enabled metric alone. OOS = the last 30% "
                "of bars; hit = next-bar direction; return = engine P&L after fees at the set leverage.",
                classes="hint",
            )
            yield GlossaryTable(id="compound-results")
            yield Static("", id="compound-fwd-summary")
            yield GlossaryTable(id="compound-forward")

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
            yield from self._preset_list("live")
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
            yield from self._preset_list("exec")
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
        for label in ("strategy", "family", "tested", "times tested", "last tested", "card-preset result"):
            avail.add_column(label, key=label)
        avail.cursor_type = "row"
        for row in self._call("strategies.list")["result"]:
            avail.add_row(row["name"], row["family"], "…", "", "", "", key=row["name"])
        self._refresh_strategy_history()

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
            "backtest median net %", "trades",
        )

        fills = self.query_one("#fills-table", DataTable)
        fills.add_columns(
            "bar", "when", "side", "reason", "price", "units", "cost", "equity"
        )

        self._refresh_exec_choices()
        self._refresh_key_sources()
        self._refresh_portfolio_notice(toast=True)
        self.set_interval(self.settings.poll_interval_seconds, self._tick)
        self.set_interval(liq.REFRESH_SECONDS, self._liq_tick)
        self._refresh_liquidity(force=True)
        self._compound_setup()
        self._install_help()

    def _install_help(self) -> None:
        """Include every form and lazy tab without copying text into handlers."""
        for widget in self.query(Widget):
            text = control_help(widget.id)
            if isinstance(widget, Tab) and widget.id:
                text = TAB_HELP.get(widget.id.removeprefix("--content-tab-"), text)
            if text:
                widget.tooltip = text
            elif isinstance(widget, (Static, DataTable, OptionList, TextArea)):
                pane = next((p for p in widget.ancestors if isinstance(p, TabPane)), None)
                if pane is not None:
                    widget.tooltip = TAB_HELP.get(pane.id)
            if isinstance(widget, Label) and widget.parent is not None:
                for sibling in widget.parent.children:
                    if isinstance(sibling, (Input, Select)):
                        widget.tooltip = control_help(sibling.id)
                        break

    def action_show_help(self) -> None:
        """F1 explains keyboard focus too; hover must not be the only path."""
        if isinstance(self.screen, HelpScreen):
            self.screen.dismiss()
            return
        widget = self.focused
        text = ""
        if isinstance(widget, GlossaryTable):
            text = widget.cell_tooltip(widget.cursor_column, widget.cursor_row) or ""
            # Row cursors do not select a column, so offer all of its definitions.
            if widget.cursor_type == "row":
                definitions = "\n\n".join(
                    f"{column.label}: {widget.header_tooltip(i)}"
                    for i, column in enumerate(widget.ordered_columns)
                    if widget.header_tooltip(i)
                )
                text = text + "\n\n" + definitions
        elif widget is not None:
            text = control_help(widget.id) or str(widget.tooltip or "")
        if not text:
            text = TAB_HELP.get(self.query_one(TabbedContent).active, "")
        self.push_screen(HelpScreen(text))

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
            self._refresh_strategy_history()
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
            "cpcv_groups": int, "cpcv_k": int, "solana_address": str, "base_address": str,
            "eth_address": str, "btc_xpub": str, "ltc_xpub": str, "doge_xpub": str,
        }
        out: dict[str, Any] = {}
        for name, cast in casts.items():
            raw = self.query_one(f"#set-{name}", Input).value.strip()
            if name in XPUB_FIELDS:
                if raw.lower() == "clear":
                    out[name] = ""
                elif raw:
                    out[name] = raw
                continue
            if raw or cast is str:
                out[name] = cast(raw)
        out["interval"] = str(self.query_one("#set-interval", Select).value)
        return out

    # -- roster ----------------------------------------------------------

    def _refresh_strategy_history(self) -> None:
        """Fill the Strategies table's test-history columns from `strategies.history`.

        Cells are updated in place by row and column key, so the cursor, the sort order and the
        highlighted row (which opens that strategy's source) all survive a refresh.
        """
        env = self._call("strategies.history", quiet=True)
        table = self.query_one("#available-table", DataTable)
        status = self.query_one("#history-status", Static)
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        for row in r["rows"]:
            if not row["testable"] and not row["tested"]:
                tested = "n/a"
            else:
                tested = "yes" if row["tested"] else "no"
            for column, value in (("tested", tested), ("times tested", str(row["runs"] or "")),
                                  ("last tested", row["last_tested"] if row["tested"] else ""),
                                  ("card-preset result", row["result"])):
                try:
                    table.update_cell(row["name"], column, value)
                except Exception:  # noqa: BLE001 - a row removed under us; the next refresh redraws
                    pass
        note = (f"{r['asset']}: {r['tested']} tested, {r['untested']} untested "
                "(background sweep results; the Queue tab shows the full leaderboard)")
        action = getattr(self, "_history_action", "")
        status.update(f"{action}\n{note}" if action else note)

    def _start_backtest(self, scope: str, names: list[str] | None = None) -> None:
        """Run `queue.backtest` and say what happened where the user is looking."""
        status = self.query_one("#history-status", Static)
        params: dict[str, Any] = {"scope": scope}
        if names is not None:
            params["names"] = names
        env = self._call("queue.backtest", params)
        if not env["ok"]:
            self._history_action = f"[red]{self._msg(env)}[/]"
        else:
            self._history_action = env["result"]["message"]
        self._refresh_strategy_history()

    @on(Button.Pressed, "#btn-bt-selected")
    def _backtest_selected(self) -> None:
        """Backtest the highlighted strategy (the `queue.backtest` command, scope selected)."""
        table = self.query_one("#available-table", DataTable)
        try:
            name = str(table.get_row_at(table.cursor_row)[0])
        except Exception:  # noqa: BLE001 - nothing highlighted
            self.query_one("#history-status", Static).update("[red]highlight a strategy first[/]")
            return
        self._start_backtest("selected", [name])

    @on(Button.Pressed, "#btn-bt-untested")
    def _backtest_untested(self) -> None:
        """Backtest every strategy with no recorded result."""
        self._start_backtest("untested")

    @on(Button.Pressed, "#btn-bt-all")
    def _backtest_all(self) -> None:
        """Backtest every testable strategy."""
        self._start_backtest("all")

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
        sel.set_options([(label, label) for label in labels]
                        + [(f"Top 5 {p['title']}", p["value"]) for p in self._presets])

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

    # -- Compound 5m -----------------------------------------------------------------------

    _COMPOUND_IDS = tuple(c.id for c in sc.COMPONENTS)

    def _compound_setup(self) -> None:
        self._compound_cfg: dict[str, Any] = sc.default_config()
        self._compound_live: dict[str, str] = {}
        self._compound_learned: dict[str, str] = {}
        self._compound_tuned: dict[str, dict[str, Any]] = {}
        self._compound_bt: dict[str, str] = {}
        self._compound_fwd: dict[str, str] = {}
        self._compound_auto = False
        self._compound_last_bar = 0
        table = self.query_one("#compound-table", GlossaryTable)
        table.cursor_type = "row"
        for label in ("on", "component", "family", "style", "weight", "parameters", "live score",
                      "learned hit (n)", "tuned to", "bt oos hit", "fwd hit (n)"):
            table.add_column(label, key=label)
        results = self.query_one("#compound-results", GlossaryTable)
        results.cursor_type = "row"
        results.add_columns("configuration", "oos calls", "oos hit", "z", "base up", "gross bps",
                            "oracle net bps", "oos return", "oos sharpe", "trades", "max dd", "fees %",
                            "rankable")
        fwd = self.query_one("#compound-forward", GlossaryTable)
        fwd.cursor_type = "row"
        fwd.add_columns("time", "call", "composite", "regime", "price", "next 5m bps", "hit", "blocked by")
        env = self._call("compound.config", quiet=True)
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
        else:
            self.query_one("#compound-status", Static).update(f"[red]{escape(self._msg(env))}[/]")
        self._compound_render_table()
        self._compound_load_results()
        self.set_interval(20, self._compound_auto_tick)

    def _compound_selected(self) -> str:
        table = self.query_one("#compound-table", GlossaryTable)
        row = table.cursor_row if table.row_count else 0
        return self._COMPOUND_IDS[max(0, min(row, len(self._COMPOUND_IDS) - 1))]

    def _compound_render_table(self) -> None:
        table = self.query_one("#compound-table", GlossaryTable)
        keep = table.cursor_row
        table.clear()
        for comp in sc.COMPONENTS:
            entry = self._compound_cfg["components"][comp.id]
            params = " ".join(f"{k}={v:g}" for k, v in entry["params"].items())
            name = comp.id + (" (live only)" if comp.forward_only else "")
            table.add_row("on" if entry["enabled"] else "off", name, comp.family, comp.style,
                          f"{entry['weight']:g}", params, self._compound_live.get(comp.id, ""),
                          self._compound_learned.get(comp.id, ""),
                          " ".join(f"{k}={v:g}" for k, v in self._compound_tuned.get(comp.id, {}).items()
                                   if entry["params"].get(k) != v),
                          self._compound_bt.get(comp.id, ""), self._compound_fwd.get(comp.id, ""),
                          key=comp.id)
        if table.row_count:
            table.move_cursor(row=min(max(keep, 0), table.row_count - 1))
        agg = self._compound_cfg["aggregate"]
        ex = self._compound_cfg["execution"]
        self.query_one("#compound-agg", Input).placeholder = (
            f"entry={agg['entry']:g} exit={agg['exit']:g} min_coverage={agg['min_coverage']:g} "
            f"dedupe_families={agg['dedupe_families']} regime_weighting={agg['regime_weighting']} "
            f"allow_short={agg['allow_short']} adaptive={agg['adaptive']} "
            f"adaptive_prior={agg['adaptive_prior']:g} adaptive_halflife={agg['adaptive_halflife']} "
            f"adaptive_flip={agg['adaptive_flip']} tune={agg['tune']} tune_confidence={agg['tune_confidence']:g} "
            f"tune_min_calls={agg['tune_min_calls']:g} tune_step={agg['tune_step']:g} "
            f"tune_cooldown={agg['tune_cooldown']} leverage={ex['leverage']:g} fee_bps={ex['fee_bps']:g} "
            f"slippage_bps={ex['slippage_bps']:g}")

    @on(DataTable.RowHighlighted, "#compound-table")
    def _compound_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        cid = str(event.row_key.value) if event.row_key is not None else self._compound_selected()
        comp = sc.BY_ID.get(cid)
        if comp is None:
            return
        entry = self._compound_cfg["components"][cid]
        specs = "; ".join(f"{p.name} {p.lo:g}..{p.hi:g}" + (f" ({p.describe})" if p.describe else "")
                          for p in comp.params)
        self.query_one("#compound-detail", Static).update(Text(
            f"{comp.name} [{comp.kind}, {comp.family}/{comp.style}] source: {comp.source}\n"
            f"formula: {comp.formula}\nworks: {comp.useful_when}\nfails: {comp.not_useful_when}\n"
            f"ranges: {specs or 'none'}"))
        values = " ".join([f"weight={entry['weight']:g}"]
                          + [f"{k}={v:g}" for k, v in entry["params"].items()])
        self.query_one("#compound-edit", Input).value = values

    def _compound_save(self, patch: dict[str, Any], what: str) -> None:
        env = self._call("compound.save", {"patch": patch})
        status = self.query_one("#compound-status", Static)
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        self._compound_cfg = env["result"]["config"]
        self._compound_render_table()
        status.update(f"saved: {escape(what)} (config {env['result']['config_hash']})")

    @on(Button.Pressed, "#compound-toggle")
    def _compound_toggle(self) -> None:
        cid = self._compound_selected()
        enabled = not self._compound_cfg["components"][cid]["enabled"]
        self._compound_save({"components": {cid: {"enabled": enabled}}},
                            f"{cid} {'on' if enabled else 'off'}")

    @on(Button.Pressed, "#compound-apply")
    def _compound_apply(self) -> None:
        cid = self._compound_selected()
        status = self.query_one("#compound-status", Static)
        try:
            patch: dict[str, Any] = {}
            edit = self.query_one("#compound-edit", Input).value.strip()
            if edit:
                patch.update(compound_mod.component_patch(cid, compound_mod.parse_kv(edit)))
            agg = self.query_one("#compound-agg", Input).value.strip()
            if agg:
                patch.update(compound_mod.aggregate_patch(compound_mod.parse_kv(agg)))
        except compound_mod.CompoundError as exc:
            status.update(f"[red]{escape(str(exc))}[/]")
            return
        if not patch:
            status.update("nothing to apply: type name=value pairs first")
            return
        self._compound_save(patch, f"{cid} and aggregate settings" if agg else cid)
        self.query_one("#compound-agg", Input).value = ""

    @on(Button.Pressed, "#compound-adopt")
    def _compound_adopt(self) -> None:
        """Save the settings tuning moved to (from the last Signal now) as the new base settings."""
        status = self.query_one("#compound-status", Static)
        patch = {cid: {"params": p} for cid, p in self._compound_tuned.items()
                 if p != self._compound_cfg["components"][cid]["params"]}
        if not patch:
            status.update("nothing to adopt: run Signal now with tune=1; no metric has moved yet")
            return
        self._compound_save({"components": patch}, f"tuned settings for {', '.join(sorted(patch))}")
        self._compound_tuned.clear()

    @on(Button.Pressed, "#compound-reset")
    def _compound_reset(self) -> None:
        env = self._call("compound.reset")
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
            self._compound_live.clear()
            self._compound_render_table()
            self.query_one("#compound-status", Static).update("every component back to its default")
        else:
            self.query_one("#compound-status", Static).update(f"[red]{escape(self._msg(env))}[/]")

    # Not exclusive: an auto-forward tick must not cancel a backtest that is still running.
    @work(thread=True, group="compound")
    def _compound_job(self, name: str, params: dict[str, Any], label: str) -> None:
        self.call_from_thread(self.query_one("#compound-status", Static).update, f"{label}…")
        env = self._call(name, params)
        self.call_from_thread(self._compound_after, name, env)

    def _compound_after(self, name: str, env: dict[str, Any]) -> None:
        status = self.query_one("#compound-status", Static)
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        r = env["result"]
        if name == "compound.signal":
            self._compound_render_signal(r)
            status.update(f"live call scored from {r.get('bars_used', '?')} closed 5m bars")
        elif name == "compound.backtest":
            status.update(f"backtest {r['run_id']}: {r['configurations']} configurations on "
                          f"{', '.join(r['assets']) or '-'}" + (f"; skipped {r['skipped']}" if r["skipped"] else ""))
            self._compound_load_results()
        elif name == "compound.forward_tick":
            self._compound_last_bar = int(r.get("bar_ts") or 0)
            status.update(f"forward: bar {r.get('bar_ts')} call {r['call']}"
                          f"{' recorded' if r['recorded'] else ' (already recorded)'}, "
                          f"{r['resolved']} earlier call(s) resolved")
            self._compound_load_results()

    def _compound_render_signal(self, r: dict[str, Any]) -> None:
        when = time.strftime("%H:%M UTC", time.gmtime(r["decided_at"]))
        blocked = ", ".join(r["blocked_by"]) or "none"
        self.query_one("#compound-call", Static).update(Text(
            f"{r['asset']} next 5m from {when}: {r['call']}   composite {r['composite']}   "
            f"coverage {r['coverage']}   agreement {r['agreement']}\n"
            f"regime {r['regime']} · trend stage {r['trend_stage']} · cycle phase {r['cycle_phase']} · "
            f"round trip {r['round_trip_bps']} bps · gates blocking: {blocked}"))
        self._compound_live = {}
        self._compound_learned = {}
        self._compound_tuned = {}
        for row in r["components"]:
            if "learned_hit" in row:
                self._compound_learned[row["id"]] = (
                    f"{row['learned_hit']:.1%} ({row['learned_calls']:.0f}) x{row['adaptive_mult']:+.2f}")
            if row.get("tuned_params"):
                self._compound_tuned[row["id"]] = row["tuned_params"]
            if row["status"] == "scored":
                self._compound_live[row["id"]] = f"{row['score']:+.2f}" + (" inv" if row.get("inverted") else "")
            elif row["kind"] == "gate" and row["enabled"]:
                self._compound_live[row["id"]] = "BLOCK" if row.get("blocked") else "pass"
            elif row["enabled"]:
                self._compound_live[row["id"]] = row["status"]
        self._compound_render_table()

    def _compound_load_results(self) -> None:
        env = self._call("compound.results", {"asset": self.settings.asset}, quiet=True)
        results = self.query_one("#compound-results", GlossaryTable)
        results.clear()
        self._compound_bt = {}
        window_note = ""
        if env["ok"] and env["result"]["run_id"]:
            window_note = (f"{env['result']['configurations_on_this_oos_window']} configurations scored on "
                           "this out-of-sample window so far (the multiple-testing denominator). ")
        if env["ok"]:
            for row in env["result"]["rows"]:
                results.add_row(
                    row["label"], str(row["oos_calls"]), _pct(row["oos_hit"]), _num(row["oos_z"]),
                    _pct(row["oos_base_up"]), _num(row["oos_gross_bps"]), _num(row["oracle_net_bps"]),
                    _pct(row["oos_return"]), _num(row["oos_sharpe"]), str(row["oos_trades"]),
                    _pct(row["oos_max_dd"]), _num(row["oos_fees_pct"]), "yes" if row["ranked"] else "no")
                if row["label"].startswith("only:"):
                    self._compound_bt[row["label"][5:]] = _pct(row["oos_hit"])
                elif row["label"] == "compound":
                    self._compound_bt["_compound"] = _pct(row["oos_hit"])
        fenv = self._call("compound.forward_status", {"asset": self.settings.asset}, quiet=True)
        fwd = self.query_one("#compound-forward", GlossaryTable)
        fwd.clear()
        self._compound_fwd = {}
        summary = self.query_one("#compound-fwd-summary", Static)
        if fenv["ok"]:
            f = fenv["result"]
            for cid, tally in f["components"].items():
                if tally["decided"]:
                    self._compound_fwd[cid] = f"{_pct(tally['hit_rate'])} ({tally['decided']})"
            c, u = f["compound"], f["compound_ungated"]
            summary.update(Text(
                window_note +
                f"Forward test {f['asset']}: {f['calls_recorded']} bars recorded, {f['resolved']} resolved, "
                f"{f['pending']} pending. Compound: {c['decided']} calls, hit {_pct(c['hit_rate'])}, "
                f"z {_num(c['z_vs_coinflip'])}, net/call {_num(c['net_bps_per_call_if_one_bar'])} bps. "
                f"Without gates: {u['decided']} calls, hit {_pct(u['hit_rate'])}."))
            for row in reversed(f["recent"]):
                fwd.add_row(time.strftime("%m-%d %H:%M", time.gmtime(row["bar_ts"] + 300)), row["call"],
                            _num(row["composite"]), str(row["regime"]), f"{row['price']:.4g}",
                            _num(row["ret_bps"]), {True: "yes", False: "no"}.get(row["hit"], "-"),
                            ", ".join(row.get("blocked_by") or []) or "-")
        else:
            summary.update(f"[red]{escape(self._msg(fenv))}[/]")
        self._compound_render_table()

    @on(Button.Pressed, "#compound-signal")
    def _compound_signal(self) -> None:
        self._compound_job("compound.signal", {"asset": self.settings.asset}, "scoring the latest closed bar")

    @on(Button.Pressed, "#compound-backtest")
    def _compound_backtest(self) -> None:
        self._compound_job("compound.backtest", {"asset": self.settings.asset},
                           "backtesting the compound and each enabled metric alone")

    @on(Button.Pressed, "#compound-forward")
    def _compound_forward(self) -> None:
        self._compound_job("compound.forward_tick", {"asset": self.settings.asset}, "forward tick")

    @on(Button.Pressed, "#compound-auto")
    def _compound_auto_toggle(self) -> None:
        self._compound_auto = not self._compound_auto
        self.query_one("#compound-auto", Button).label = (
            f"Auto-forward: {'on' if self._compound_auto else 'off'}")
        if self._compound_auto:
            self._compound_forward()

    def _compound_auto_tick(self) -> None:
        """Every 20 s: if a new 5m bar has closed (plus 5 s for the venue), take a forward tick."""
        if not getattr(self, "_compound_auto", False):
            return
        now = time.time()
        latest_closed = (int(now) // 300) * 300 - 300
        if latest_closed > self._compound_last_bar and now % 300 >= 5:
            self._compound_last_bar = latest_closed
            self._compound_forward()

    @on(Button.Pressed, "#compound-refresh")
    def _compound_refresh(self) -> None:
        self._compound_load_results()
        self.query_one("#compound-status", Static).update("results and forward test reloaded")

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
        best = r["rows"][0] if r["rows"] else None
        status.update(r["message"] + (f" · best Sharpe: {best['label']} {best['net_pct_text']}"
                                      if best else ""))

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
    def _help_tab_active(self) -> None:
        self.call_after_refresh(self._install_help)

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
        elif pane == "tab-wallet":
            self._refresh_portfolio_notice()
            self._call("portfolio.notice", {"mark_seen": True}, quiet=True)
        elif pane == "tab-liquidity":
            self._refresh_liquidity(force=True)
        elif pane == "tab-top5" and not self._top5_loaded:
            self._top5_loaded = True
            self._refresh_top5()
        elif pane == "tab-liverun":
            self._refresh_live_run()
        elif pane == "tab-pnl" and not self._pnl_loaded:
            self._pnl_loaded = True
            self._pnl_run()

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
            self.call_from_thread(status.update,
                                  f"dry run finished · {env['result']['net_pct_text']}")
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
                                "backtest median net %", "trades", "paths")
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
                                  "backtest median net %", "trades", "paths")
            yield transfers
            yield Static(
                "Benchmark that must stay in view: buy_and_hold, zero "
                "parameters, medium/long median Sharpe +0.534, 68% of paths "
                "positive, +9.4% backtest median net return — 2nd of 25 at the medium "
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

    # -- Settings: where the signing keys live (stat only) ------------------

    def _refresh_key_sources(self) -> None:
        env = self._call("wallet.key_sources", quiet=True)
        box = self.query_one("#key-sources", Static)
        if not env["ok"]:
            box.update(f"[red]{escape(self._msg(env))}[/]")
            return
        lines = []
        for k in env["result"]["keys"]:
            if not k["exists"]:
                state = "missing"
            else:
                state = f"present, mode {k['mode']}" + ("" if k["mode_600"] else "  [red]should be 0600[/]")
            lines.append(f"  {escape(k['label'])}: {escape(k['path'])}: {state}")
        lines.append("  Signing lives in a separate gated component that loads keys itself. This console "
                     "has no private-key field.")
        box.update("\n".join(lines))

    # -- Wallet: what the configured wallets hold (read-only) ----------------

    def _refresh_portfolio_notice(self, toast: bool = False) -> None:
        """Show the one-line 'a balance changed since you last looked' notice, if there is one."""
        env = self._call("portfolio.notice", quiet=True)
        line = env["result"]["line"] if env["ok"] else None
        self.query_one("#portfolio-notice", Static).update(f"[b]{escape(line)}[/b]" if line else "")
        if line and toast:
            self.notify(line, timeout=12)

    def _wallet_pane(self) -> ComposeResult:
        """Find the coins, token contracts, stake accounts and LP positions at the Settings addresses."""
        with VerticalScroll():
            yield Static(
                "Reads the two public addresses from Settings with public endpoints only (no API key, no "
                "private key, no transaction). Every figure is wallet (live): a read of real money at "
                "the time of the scan. Airdrop-looking tokens are flagged and left out of the totals.",
                classes="hint")
            with Horizontal(classes="form-row"):
                yield Label("Chain")
                yield Select([(c, c) for c in ("all", "solana", "base", "ethereum", "bitcoin", "litecoin",
                                                "dogecoin")], value="all", allow_blank=False,
                             id="wallet-chain")
                yield Button("Scan wallet", variant="primary", id="wallet-scan")
                yield Static("", id="wallet-status")
            yield Static("", id="portfolio-notice")
            yield Static("", id="wallet-summary")
            yield Static("[b]Holdings[/b]", classes="hint")
            holdings = GlossaryTable(id="wallet-holdings")
            holdings.add_columns("chain", "asset", "amount", "price $", "value $ (wallet (live))", "status")
            yield holdings
            yield Static("[b]Contracts and accounts each holding lives in[/b]", classes="hint")
            contracts = GlossaryTable(id="wallet-contracts")
            contracts.add_columns("chain", "holding", "kind", "address", "program", "explorer")
            yield contracts

    @on(Button.Pressed, "#wallet-scan")
    def _wallet_scan(self) -> None:
        self.query_one("#wallet-status", Static).update("scanning… (public endpoints are rate limited)")
        self._wallet_worker()

    @work(thread=True, group="wallet", exclusive=True)
    def _wallet_worker(self) -> None:
        chain = self.query_one("#wallet-chain", Select).value
        env = self._call("portfolio.scan", {"chain": chain if isinstance(chain, str) else "all"})
        self.call_from_thread(self._render_wallet, env)

    def _render_wallet(self, env: dict[str, Any]) -> None:
        status = self.query_one("#wallet-status", Static)
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        r = env["result"]
        status.update(f"scanned {r['scanned_at']}" + ("  [yellow]partial[/]" if r["partial"] else ""))
        c = r["counts"]
        lines = [f"[b]wallet (live) total ${r['total_usd']:,.2f}[/b] · {c['holdings']} holdings · "
                 f"{c['stakes']} stake accounts · {c['positions']} LP positions · {c['contracts']} contracts · "
                 f"{c['airdrop_flagged']} airdrop-flagged (excluded)"]
        lines += [f"  skipped: {escape(s)}" for s in r["skipped"]]
        for name, ch in r["chains"].items():
            unpriced = f"  [yellow]no USD price for {', '.join(ch['unpriced'])}: value unknown, not counted[/]" \
                if ch.get("unpriced") else ""
            lines.append(f"  {name}: wallet (live) ${ch['total_usd']:,.2f} ({ch['status']}){unpriced}")
            if "script_types" in ch:
                found = ", ".join(f"{t['type']} {t['balance']:g}" for t in ch["script_types"]) or "no history"
                lines.append(f"    script types with history: {escape(found)}; "
                             f"{ch['derived_addresses']} addresses derived (not listed)")
            lines += [f"    error: {escape(e['source'])}: {escape(e['message'])}" for e in ch["errors"]]
            lines += [f"    note: {escape(n)}" for n in ch["notes"]]
        self.query_one("#wallet-summary", Static).update("\n".join(lines))
        hold = self.query_one("#wallet-holdings", DataTable)
        hold.clear()
        cons = self.query_one("#wallet-contracts", DataTable)
        cons.clear()

        def usd(v: float | None) -> str:
            return "-" if v is None else f"{v:,.2f}"

        for name, ch in r["chains"].items():
            rows = ([ch["native"]] if ch["native"] else []) + ch["holdings"] + ch["stakes"]
            for h in rows:
                flagged = h.get("airdrop")
                state = ("airdrop-flagged, excluded: " + "; ".join(h.get("airdrop_reasons", []))) if flagged \
                    else ("counted" if h.get("usd") is not None else "no price, not counted")
                hold.add_row(name, h["symbol"] + (" (staked)" if h.get("kind") == "stake" else ""),
                             f"{h['amount']:,.6f}", usd(h.get("price_usd")), usd(h.get("usd")), state)
            for p in ch["positions"]:
                hold.add_row(name, f"{p['protocol']} #{p['token_id']} {p.get('pair') or ''}".strip(), "1 NFT", "-",
                             usd(p.get("value_usd")), f"{p['held_by']} · {p['value_source']}")
            for k in ch["contracts"]:
                cons.add_row(name, k["holding"], k["kind"], k["address"], k["program"], k["link"])

    # -- Top 5 presets: one click fills the tab ----------------------------

    @on(OptionList.OptionSelected)
    def _preset_selected(self, event: OptionList.OptionSelected) -> None:
        """Apply a Top 5 preset to the tab whose list it was picked from.

        This only fills fields. Running anything still goes through that tab's own button, and so
        through the registry; a preset click places nothing and starts nothing.
        """
        list_id = event.option_list.id or ""
        if not list_id.startswith("preset-"):
            return
        preset = next((p for p in self._presets if p["value"] == event.option_id), None)
        if preset is None:
            return
        tab = list_id.removeprefix("preset-")
        if tab == "live":
            self.query_one("#live-run-strategy", Input).value = preset["applies"]["live_run"]["strategy"]
            self.query_one("#live-run-status", Static).update(
                f"preset {preset['title']} · {preset['params_text']} · {preset['net_pct_text']}")
        elif tab == "exec":
            self.query_one("#exec-strategy", Select).value = preset["applies"]["execute"]["label"]
            self.query_one("#exec-summary", Static).update(
                f"preset {preset['title']} selected · {preset['params_text']} · press Start dry run")
        elif tab == "analyze":
            self._apply_analyze_preset(preset)

    def _apply_analyze_preset(self, preset: dict[str, Any]) -> None:
        note = self.query_one("#analyze-preset-note", Static)
        select = self.query_one("#analyze-asset", Select)
        want = f"{preset['asset']}|{preset['interval']}"
        if want not in self._analyze_values:
            self._analyze_preset = ""
            note.update(f"[red]{preset['asset']} {preset['interval']} is not cached; fetch it first[/]")
            return
        select.value = want
        self._analyze_preset = preset["value"]
        note.update(f"Judging only {preset['title']}: {preset['params_text']}. "
                    "Press Analyze. Choosing a different coin drops the preset.")

    @on(Select.Changed, "#analyze-asset")
    def _analyze_asset_changed(self, event: Select.Changed) -> None:
        """A coin other than the preset's drops the preset: it was fitted on one series."""
        if not self._analyze_preset:
            return
        preset = next((p for p in self._presets if p["value"] == self._analyze_preset), None)
        if preset and event.value != f"{preset['asset']}|{preset['interval']}":
            self._analyze_preset = ""
            self.query_one("#analyze-preset-note", Static).update("preset dropped: all strategies")

    # -- Analyze: any coin, any moment -----------------------------------

    def _analyze_pane(self) -> ComposeResult:
        """Replay every rule up to a chosen timestamp, for a chosen coin.

        Distinct from the Signals tab, which reads the *latest* bar of the
        configured asset. Here the coin and the moment are both inputs.
        """
        pairs = self._call("analyze.assets")["result"]
        options = [(f"{p['asset']} {p['interval']}", f"{p['asset']}|{p['interval']}") for p in pairs]
        self._analyze_values = {value for _, value in options}
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
            yield from self._preset_list("analyze")
            yield Static("", id="analyze-preset-note", classes="hint")
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
        if self._analyze_preset:
            params["preset"] = self._analyze_preset
        env = self._call("analyze.run", params)
        if not env["ok"]:
            head.update(f"[b]could not analyse:[/b] {self._msg(env)}")
            return
        r = env["result"]
        head.update(r["headline"] + ("" if r["truncated"] else "   (latest bar)")
                    + f"   {r['net_pct_text']}")
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
                                 "made money", "median Sharpe", "paths", "best (rankable)",
                                 "best backtest median net %")
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
                "-" if best is None or best["net_pct"] is None else format_pct(best["net_pct"]),
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
            ranked = GlossaryTable(id="queue-table")
            ranked.add_columns(
                "configuration", "family", "median Sharpe", "IQR",
                "% paths +", "backtest median net %", "trades",
            )
            yield ranked
            yield Static(
                "[b]Below the floor — listed, never ranked[/b]", classes="hint"
            )
            floor = GlossaryTable(id="queue-floor")
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
                f"{x['frac_positive']:.0%}", format_pct(x["net_pct"]), str(x["trades"]),
            )
        floor_table = self.query_one("#queue-floor", DataTable)
        floor_table.clear()
        for x in r["floor"]:
            floor_table.add_row(x["label"], x["family"], str(x["trades"]), x["why"])

    # -- P&L: profit and loss over a window -------------------------------

    def _pnl_pane(self) -> ComposeResult:
        """Net/gross P&L, costs, drawdown, win rate and attribution over a chosen window.

        One section per source. Simulated (backtest, paper, dry-run) and real (live LP) money are
        shown in separate sections and never added: there is no total line on purpose.
        """
        with VerticalScroll():
            yield Static(
                "Profit and loss over a window. Every figure names its source. Simulated and real "
                "money are never summed: each source is its own section.", classes="hint")
            with Horizontal(classes="form-row"):
                yield Label("Window")
                yield Select([(w, w) for w in ("24h", "7d", "30d", "90d", "ytd", "all")],
                             value="30d", allow_blank=False, id="pnl-window")
                yield Label("Custom start")
                yield Input(placeholder="YYYY-MM-DD", id="pnl-start")
                yield Label("end")
                yield Input(placeholder="YYYY-MM-DD", id="pnl-end")
            with Horizontal(classes="form-row"):
                yield Label("Source")
                yield Select([(w, w) for w in ("all", "backtest", "paper", "dry-run", "dry-run LP",
                                               "live LP", "wallet (live)")],
                             value="all", allow_blank=False, id="pnl-source")
                yield Button("Compute P&L", variant="primary", id="pnl-run")
                yield Static("", id="pnl-status")
            yield Static("", id="pnl-summary")
            yield Static("[b]By strategy[/b]", classes="hint")
            by_strategy = GlossaryTable(id="pnl-strategies")
            by_strategy.add_columns("source", "strategy", "asset", "net $", "net % (source named)",
                                    "gross $", "costs $", "realized $", "unrealized $",
                                    "contribution (source named)")
            yield by_strategy
            yield Static("[b]By asset[/b]", classes="hint")
            by_asset = GlossaryTable(id="pnl-assets")
            by_asset.add_columns("source", "asset", "runs", "net $", "net % (source named)",
                                 "contribution (source named)")
            yield by_asset
            yield Static("[b]Best and worst periods[/b]", classes="hint")
            periods = GlossaryTable(id="pnl-periods")
            periods.add_columns("source", "period", "best", "worst")
            yield periods
            yield Static("[b]Daily P&L, cumulative and drawdown[/b]", classes="hint")
            daily = GlossaryTable(id="pnl-daily")
            daily.add_columns("source", "date", "P&L $", "cumulative $",
                              "cumulative % (source named)", "drawdown (source named)")
            yield daily

    @on(Button.Pressed, "#pnl-run")
    def _pnl_run(self) -> None:
        self.query_one("#pnl-status", Static).update("computing…")
        self._pnl_worker()

    def _pnl_params(self) -> dict[str, Any]:
        window = self.query_one("#pnl-window", Select).value
        source = self.query_one("#pnl-source", Select).value
        params: dict[str, Any] = {"window": window if isinstance(window, str) else "30d"}
        if isinstance(source, str) and source != "all":
            params["source"] = source
        for key, wid in (("start", "#pnl-start"), ("end", "#pnl-end")):
            text = self.query_one(wid, Input).value.strip()
            if text:
                params[key] = text
        return params

    @work(thread=True, group="pnl", exclusive=True)
    def _pnl_worker(self) -> None:
        """Three registry calls, off the UI thread: the first may run the roster backtests."""
        params = self._pnl_params()
        envs = {name: self._call(name, params) for name in ("pnl.summary", "pnl.series", "pnl.breakdown")}
        self.call_from_thread(self._render_pnl, envs)

    @staticmethod
    def _usd(v: float | None) -> str:
        if v is None:
            return "-"
        return f"{0.0 if abs(v) < 0.005 else v:+,.2f}"

    @staticmethod
    def _pts(v: float | None, word: str) -> str:
        return "-" if v is None else f"{word} {v * 100:+.2f} pts"

    def _render_pnl(self, envs: dict[str, dict[str, Any]]) -> None:
        status = self.query_one("#pnl-status", Static)
        bad = next((e for e in envs.values() if not e["ok"]), None)
        if bad:
            status.update(f"[red]{self._msg(bad)}[/]")
            return
        summary, series, breakdown = (envs[n]["result"] for n in ("pnl.summary", "pnl.series", "pnl.breakdown"))
        win = summary["window"]
        status.update(f"window {win['label']}: {win['start'] or 'start of data'} to {win['end'] or 'end of data'}")
        lines = [escape(summary["notice"]), ""]
        for sec in summary["sections"]:
            lines.append(f"[b]{sec['label']}[/b]")
            for note in sec["notes"]:
                lines.append(f"  note: {escape(note)}")
            if sec["status"] != "ok":
                lines += [f"  {escape(sec['message'])}", ""]
                continue
            t, d = sec["totals"], sec["drawdown"] or {}
            lines.append(f"  {t['net_pct_text']} · net {self._usd(t['net_usd'])} · gross {self._usd(t['gross_usd'])}"
                         f" · fees {t['fees_usd']:,.2f} · slippage {t['slippage_usd']:,.2f}"
                         f" · borrow/funding {t['borrow_funding_usd']:,.2f}")
            lines.append(f"  realized {self._usd(t['realized_usd'])} · unrealized {self._usd(t['unrealized_usd'])}"
                         + ("" if t["win_rate"] is None else
                            f" · {sec['source']} win rate {t['win_rate']:.0%} of {t['closed_trades']} closed"
                            f" · expectancy {self._usd(t['expectancy_usd'])} per close"))
            if d.get("max_drawdown_usd"):
                pct = d["max_drawdown_pct"]
                rec = (f"recovered after {d['recovery_days']} d" if d["recovered"] else "not recovered")
                lines.append(f"  max drawdown {self._usd(d['max_drawdown_usd'])}"
                             + ("" if pct is None else f" ({sec['source']} {pct * 100:+.1f}% from peak)")
                             + f" · peak {d['peak_date']} · trough {d['trough_date']} · {rec}")
            lines.append("")
        self.query_one("#pnl-summary", Static).update("\n".join(lines))

        def refill(table_id: str, rows: list[tuple]) -> None:
            table = self.query_one(table_id, DataTable)
            table.clear()
            for row in rows:
                table.add_row(*row)

        strat_rows, asset_rows, period_rows, day_rows = [], [], [], []
        for sec in breakdown["sections"]:
            if sec["status"] != "ok":
                continue
            w = sec["source"]
            for r in sec["by_strategy"]:
                strat_rows.append((w, r["strategy"], r["asset"], self._usd(r["net_usd"]), r["net_pct_text"],
                                   self._usd(r["gross_usd"]), f"{r['costs_usd']:,.2f}",
                                   self._usd(r["realized_usd"]), self._usd(r["unrealized_usd"]),
                                   self._pts(r["contribution_pts"], w)))
            for r in sec["by_asset"]:
                asset_rows.append((w, r["name"], str(r["runs"]), self._usd(r["net_usd"]), r["net_pct_text"],
                                   self._pts(r["contribution_pts"], w)))
            for kind in ("day", "week", "month"):
                bw = (sec["best_worst"] or {}).get(kind)
                if bw:
                    period_rows.append((w, kind, f"{bw['best']['period']} {self._usd(bw['best']['pnl'])}",
                                        f"{bw['worst']['period']} {self._usd(bw['worst']['pnl'])}"))
        for sec in series["sections"]:
            if sec["status"] != "ok":
                continue
            w = sec["source"]
            for day in sec["days"][-400:]:
                day_rows.append((w, day["date"], self._usd(day["pnl"]), self._usd(day["cumulative"]),
                                 "-" if day["cumulative_pct"] is None else f"{w} {day['cumulative_pct'] * 100:+.2f}%",
                                 "-" if day["drawdown"] is None else f"{w} {day['drawdown'] * 100:.1f}%"))
        refill("#pnl-strategies", strat_rows)
        refill("#pnl-assets", asset_rows)
        refill("#pnl-periods", period_rows)
        refill("#pnl-daily", day_rows)

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
            yield GlossaryTable(id="liq-positions")
            yield Static("[b]Scout[/b] — top pools by modelled net APR", classes="hint")
            yield Static("", id="liq-scout-note", classes="hint")
            yield GlossaryTable(id="liq-scout")
            yield Static("[b]Experiments[/b] — arms side by side", classes="hint")
            yield GlossaryTable(id="liq-experiments")
            yield Static("[b]Recent actions[/b] — newest first", classes="hint")
            yield GlossaryTable(id="liq-actions")

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
            # Index search is explicit (Enter or the button), never per keystroke: the first
            # search loads the index and a semantic one may start ollama and its ~670 MB model.
            with Horizontal(classes="form-row"):
                yield Input(placeholder="search the index (Enter): keyword, meaning or both…",
                            id="docs-search")
                yield Select([("hybrid", "hybrid"), ("keyword", "keyword"), ("semantic", "semantic")],
                             value="hybrid", allow_blank=False, id="docs-search-mode")
                yield Button("Search", variant="primary", id="docs-search-run")
                yield Button("Free search memory", id="docs-search-free")
            yield Static("Search is not loaded yet; the first search loads it.", id="docs-search-status",
                         classes="hint")
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

    @on(Button.Pressed, "#docs-search-run")
    def _docs_search_pressed(self) -> None:
        """Search the repo index (the `docs.search` command); an empty box restores the file list."""
        self._start_docs_search()

    @on(Input.Submitted, "#docs-search")
    def _docs_search_submitted(self) -> None:
        self._start_docs_search()

    def _start_docs_search(self) -> None:
        query = self.query_one("#docs-search", Input).value.strip()
        status = self.query_one("#docs-search-status", Static)
        if not query:
            status.update("Search box is empty: showing the file list.")
            self._refresh_docs()
            return
        mode = self.query_one("#docs-search-mode", Select).value
        status.update(f"searching ({mode})… the first search loads the index"
                      + ("; semantic may start ollama" if mode != "keyword" else ""))
        self._docs_search_worker(query, mode if isinstance(mode, str) else "hybrid")

    @work(thread=True, exclusive=True, group="docs-search")
    def _docs_search_worker(self, query: str, mode: str) -> None:
        """Thread only so the UI stays live while the index loads or ollama starts."""
        env = self._call("docs.search", {"query": query, "mode": mode})
        self.call_from_thread(self._render_docs_search, env)

    def _render_docs_search(self, env: dict[str, Any]) -> None:
        status = self.query_one("#docs-search-status", Static)
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        table = self.query_one("#docs-table", DataTable)
        table.clear()
        for h in r["hits"]:
            table.add_row(h["path"], h["kind"], "yes" if h["editable"] else "", str(h["lines"]),
                          f"{h['score']:.3f}  {h['summary']}"[:90], key=h["path"])
        used = r["mode_used"] if r["mode_used"] == r["mode"] else f"{r['mode_used']} (asked for {r['mode']})"
        notes = " · ".join(n for n in r["notes"] if n)
        status.update(f"{len(r['hits'])} hits, {used}" + (f" · {notes}" if notes else ""))
        self.query_one("#docs-headline", Static).update(
            f"search results for {r['query']!r}; clear the box and press Search to list files again")

    @on(Button.Pressed, "#docs-search-free")
    def _docs_search_free(self) -> None:
        """Release the cached index and ask ollama to unload the embedding model."""
        env = self._call("docs.search_unload")
        self.query_one("#docs-search-status", Static).update(
            self._msg(env) if not env["ok"] else env["result"]["message"])

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

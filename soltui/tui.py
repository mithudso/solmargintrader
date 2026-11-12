"""Textual TUI: the console over the backtester.

    python3 -m soltui.tui

The panes (Settings, Strategies, Signals, Compound 5m, Backtest, Execute, ... Docs, and Now) are
grouped by `shell.py` into six destinations; `--classic` shows the original tab bar.

All decisions live in the pure modules (`config`, `roster`, `runner`, `paper`,
`status`); this file is presentation and wiring. That split is what lets the
logic be tested without driving a terminal, and it mirrors how
`netdnsmonitor/app.py` stays thin over tested modules.

The Execute tab remains **dry-run only**. The Wallet tab has separately armed
Coinbase live orders, with review by default and an optional quick mode.
"""

from __future__ import annotations

import asyncio
import copy
import io
import json
import math
import threading
import time
import uuid
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from textual import events, on, work
from rich.markup import escape
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets.option_list import Option
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Select,
    Sparkline,
    Static,
    TabbedContent,
    Tab,
    TabPane,
    TextArea,
)

from .csv_table import ExportPanel, ExportTable
from .help import column_help, control_help, row_help, TAB_HELP
from .help import HEADER_GLOSSARY as HEADER_GLOSSARY  # Preserve the existing public re-export.
from .help_screen import HelpScreen
from backtester.core import scorecard as sc

from . import bgcontrol
from . import shell
from . import bots as bots_mod
from .bots_screens import CoinPickerScreen, OptimizeScreen
from .experiment_screens import ExperimentScreen
from . import compound as compound_mod
from . import live_score
from . import cumulative as cumulative_mod
from . import bgqueue
from .backtest_log import BacktestLog
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
from . import config as config_mod
from .config import INTERVALS, XPUB_FIELDS, Settings, load_settings
from .hdwallet import redact
from .paper import MODE_LABEL
from .roster import RosterError, available_strategies
from .signals import SIGNAL_GROUPS, SignalDefaults, merged_params
from .status import build_title, format_pct

from .reference import FAMILY_NOTES, RESEARCH_DRIVERS, RESEARCH_FINDINGS, SIGNAL_REFERENCE  # noqa: F401


class _CaptureWithoutInvalidFd:
    """Keep Textual's stderr capture while reporting a missing descriptor correctly."""

    def __init__(self, capture: Any) -> None:
        self._capture = capture

    def fileno(self) -> int:
        fd = self._capture.fileno()
        if fd < 0:
            raise io.UnsupportedOperation("captured stderr has no file descriptor")
        return fd

    def __getattr__(self, name: str) -> Any:
        return getattr(self._capture, name)


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
    "#signal-live-predictions-start": "forwardtest.ensure",
    "#status-strategies": "queue.progress",
    "#status-forwardtest": "forwardtest.state",
    "#status-compound-backtest": "compound.results",
    "#status-compound-forward": "compound.unattended_status",
    "#status-bots": "bots.progress",
    "#status-backtest": "backtest.status",
    "#batch-status": "batch.status",
    "#batch-resume": "batch.start",
    "#batch-stop": "batch.stop",
    "#batch-fresh": "batch.create",
    "#status-top5": "backtest.status",
    "#status-queue": "queue.progress",
    "#status-live": "live.recommendation",
    "#status-paper": "paper.summary",
    "#strategy-cards-refresh": "strategies.cards",
    "#btn-save": "settings.save",
    "#btn-add": "roster.add",
    "#btn-roster-all": "roster.add_all",
    "#paper-exp-start": "paperexperiment.start",
    "#paper-exp-resume": "paperexperiment.resume",
    "#paper-exp-stop": "paperexperiment.stop",
    "#paper-exp-refresh": "paperexperiment.status",
    "#paper-exp-activity": "paperexperiment.status",
    "#forward-start": "forwardtest.start",
    "#forward-stop": "forwardtest.stop",
    "#forward-refresh": "forwardtest.status",
    "#btn-goto-signal-live": "forwardtest.predictions",
    "#btn-remove": "roster.remove",
    "#btn-reset-roster": "roster.reset",
    "#btn-save-signals": "signals.save",
    "#btn-reset-signals": "signals.reset",
    "#btn-cancel": "backtest.cancel",
    "#btn-run": "backtest.run",
    "#btn-run-untested": "queue.backtest",
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
    "#queue-start-fresh": "queue.start_fresh",
    "#queue-stop": "queue.stop",
    "#queue-refresh": "queue.status",
    "#queue-fetch": "queue.fetch",
    "#liq-refresh": "liquidity.status",
    "#liq-kill": "liquidity.kill",
    "#liq-resume": "liquidity.resume",
    "#docs-save": "docs.write",
    "#pnl-run": "pnl.summary",
    "#wallet-scan": "portfolio.scan",
    "#coinbase-sync": "coinbase.sync",
    "#coinbase-markets": "coinbase.markets",
    "#coinbase-order-preview": "coinbase.order_preview",
    "#coinbase-order-submit": "coinbase.order_submit",
    "#coinbase-order-quick": "coinbase.order_quick",
    "#coinbase-order-check": "coinbase.order_status",
    "#coinbase-order-state": "coinbase.order_state",
    "#advanced-preview": "coinbase.order_preview",
    "#advanced-percent-preview": "coinbase.order_percent_preview",
    "#advanced-conditional-preview": "coinbase.order_conditional_preview",
    "#advanced-submit": "coinbase.order_submit",
    "#advanced-quick": "coinbase.order_quick",
    "#advanced-percent-quick": "coinbase.order_percent_quick",
    "#advanced-conditional-quick": "coinbase.order_conditional_quick",
    "#advanced-token-search": "jupiter.tokens_search",
    "#coinbase-pairs-filter": "coinbase.pairs",
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
    "#compound-unattended-start": "compound.unattended_start",
    "#compound-unattended-stop": "compound.unattended_stop",
    "#compound-scope": "compound.config",
    "#compound-backtest-all": "compound.backtest",
    "#compound-backtest-frontier": "compound.backtest",
    "#compound-unattended-all": "compound.unattended_start",
    "#compound-unattended-stop-all": "compound.unattended_stop",
    "#compound-autopilot": "compound.autopilot",
    "#bots-apply": "bots.save",
    "#bots-edit": "bots.config",
    "#bot-settings-apply": "bots.save",
    "#bot-settings-inherit": "bots.save",
    "#bots-reset": "bots.save",
    "#bots-backtest": "bots.backtest",
    "#bots-forward-start": "bots.forward_start",
    "#bots-forward-stop": "bots.forward_stop",
    "#bots-forward-refresh": "bots.forward_status",
    "#bots-optimize": "bots.optimize",
    "#bots-schedule-start": "bots.schedule_start",
    "#bots-schedule-stop": "bots.schedule_stop",
    "#bots-schedule-status": "bots.schedule_status",
    "#bots-fit-rank": "bots.rank_coins",
    "#bots-fit-audit": "bots.audit_coin",
    "#bots-fit-cancel": "bots.fit_cancel",
    "#bots-workbench": "experiments.list",
    "#bots-coins": "bots.overview",
    "#council-save": "council.config",
    "#council-start": "council.start",
    "#council-stop": "council.stop",
    "#council-refresh": "council.status",
}

class GlossaryTable(ExportTable):
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


class CompoundTable(GlossaryTable):
    """The Compound metric table: a double-click anywhere on a row, or Space, toggles that metric.

    A single click only selects the row, which shows its full detail in the editor below. A single
    click must NOT toggle: a double-click is two clicks, so a toggle on each would leave the metric
    where it was. Textual counts the clicks of one gesture in `Click.chain`.
    """

    BINDINGS = [Binding("space", "toggle_row", "Toggle metric", show=False)]

    class Toggle(Message):
        def __init__(self, row: int) -> None:
            super().__init__()
            self.row = row

    async def _on_click(self, event: events.Click) -> None:
        meta = event.style.meta
        await super()._on_click(event)
        row = meta.get("row")
        if event.chain == 2 and isinstance(row, int) and row >= 0:
            self.post_message(self.Toggle(row))

    def action_toggle_row(self) -> None:
        if self.row_count:
            self.post_message(self.Toggle(self.cursor_row))


class EditorBar(Widget):
    """The orange line between the tabs and the shared editor.

    Drag it up or down to resize the editor; click "x close" at its right end to hide the editor
    (the bar stays, so a click on it, a drag upward or ctrl+e brings the editor back). A
    double-click restores the default height. The app owns the panel and persists the result;
    the bar only reports what the mouse did.
    """

    DEFAULT_CSS = """
    EditorBar { height: 1; width: 1fr; color: $accent; background: $surface; }
    EditorBar:hover { background: $accent 15%; }
    EditorBar.-dragging { background: $accent 30%; }
    """
    CLOSE = " x close "
    MIN_HEIGHT = 3

    class Resized(Message):
        def __init__(self, height: int, final: bool) -> None:
            super().__init__()
            self.height = height
            self.final = final

    class Close(Message):
        pass

    class Open(Message):
        pass

    class Reset(Message):
        pass

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002 - Textual's own keyword
        super().__init__(id=id)
        self.panel_open = True
        self._drag_from: tuple[int, int] | None = None  # (screen_y at press, panel height at press)
        self._moved = False

    def render(self) -> Text:
        width = max(self.size.width, 1)
        if self.panel_open:
            label, right = " ctrl+e hide | drag to resize | double-click resets ", self.CLOSE
        else:
            label, right = " editor hidden: click, drag up or ctrl+e to show it ", ""
        line = max(width - len(right), 0)
        lead = max((line - len(label)) // 2, 0)
        body = ("━" * lead + label)[:line]
        body += "━" * (line - len(body))
        return Text(body + right[: width - len(body)], style="bold")

    def _over_close(self, x: int) -> bool:
        return self.panel_open and x >= self.size.width - len(self.CLOSE)

    def max_height(self) -> int:
        # Keep the header, the tab strip and a few rows of the tab visible.
        return max(self.MIN_HEIGHT, self.app.size.height - 12)

    def _on_mouse_down(self, event: events.MouseDown) -> None:
        self._moved = False  # a new gesture; a drag that ended without a Click must not eat this one
        if self._over_close(event.x):
            return
        panel = self.app.query_one("#editor-panel")
        height = panel.outer_size.height if panel.display else 0
        self._drag_from = (event.screen_y, height)
        self.capture_mouse()
        self.add_class("-dragging")
        event.stop()

    def _on_mouse_move(self, event: events.MouseMove) -> None:
        if self._drag_from is None:
            return
        start_y, start_h = self._drag_from
        if event.screen_y == start_y and not self._moved:
            return
        self._moved = True
        height = min(max(start_h + (start_y - event.screen_y), self.MIN_HEIGHT), self.max_height())
        self.post_message(self.Resized(height, final=False))
        event.stop()

    def _on_mouse_up(self, event: events.MouseUp) -> None:
        if self._drag_from is None:
            return
        start_y, start_h = self._drag_from
        self._drag_from = None
        self.release_mouse()
        self.remove_class("-dragging")
        if self._moved:
            height = min(max(start_h + (start_y - event.screen_y), self.MIN_HEIGHT), self.max_height())
            self.post_message(self.Resized(height, final=True))
        event.stop()

    async def _on_click(self, event: events.Click) -> None:
        event.stop()
        if self._moved:
            self._moved = False
            return
        if self._over_close(event.x):
            self.post_message(self.Close())
        elif not self.panel_open:
            self.post_message(self.Open())
        elif event.chain == 2:
            self.post_message(self.Reset())


class CoinFitFinished(Message):
    """A terminal envelope, posted from a thread without touching widgets."""

    def __init__(self, token: int, bot: str, signature: tuple, envelope: dict[str, Any]) -> None:
        super().__init__()
        self.token, self.bot, self.signature, self.envelope = token, bot, signature, envelope


class BotSettingsScreen(ModalScreen[dict[str, Any] | None]):
    """Edit all settings from the selected bot's current registry configuration."""

    DEFAULT_CSS = """
    BotSettingsScreen { align: center middle; }
    #bot-settings-dialog { width: 80%; max-width: 90; height: 90%; background: $surface;
                           border: thick $accent; padding: 1 2; }
    #bot-settings-fields { height: 1fr; }
    .bot-setting-row { height: 3; }
    .bot-setting-name { width: 32; }
    .bot-setting-value { width: 1fr; }
    #bot-settings-message { height: auto; }
    #bot-settings-buttons { height: 3; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, bot: str, current: dict[str, Any], defaults: dict[str, Any],
                 coins: list[str], asset: str, fetch: Callable[[str], dict[str, Any]], mode: str = "auto") -> None:
        super().__init__()
        self.bot = bot
        self.current = dict(current)
        self.defaults = dict(defaults)
        self.coins = list(dict.fromkeys(coins))
        self.asset = asset
        self.fetch = fetch
        self.drafts: dict[str, dict[str, Any]] = {}
        self.mode = mode
        self.draft_modes: dict[str, str] = {}
        self.baselines = {asset: (dict(current), mode)}
        self._discard_ack: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="bot-settings-dialog"):
            yield Static(f"{bots_mod.LABELS[self.bot]} settings — edit fields, then Apply", markup=False)
            yield Static("Current values are shown. Load built-in defaults edits this form; Apply saves them."
                         + (" Triangle settings are global." if self.bot == "triangle" else ""))
            if self.bot != "triangle":
                yield Static("Inherit global immediately removes this coin's settings and mode overrides.")
            with Horizontal(classes="bot-setting-row"):
                yield Label("Settings for", classes="bot-setting-name")
                yield Select([("Global defaults", ""), *((coin, coin) for coin in self.coins)],
                             value=self.asset, allow_blank=False, id="bot-settings-asset",
                             classes="bot-setting-value")
            with Horizontal(classes="bot-setting-row"):
                yield Label("Optimization mode", classes="bot-setting-name")
                yield Select([("Auto — may adopt better settings", "auto"),
                              ("Manual — keep saved settings", "manual")], value=self.mode,
                             allow_blank=False, id="bot-settings-mode", classes="bot-setting-value")
            with VerticalScroll(id="bot-settings-fields"):
                for key, value in self.current.items():
                    with Horizontal(classes="bot-setting-row"):
                        yield Label(key.replace("_", " "), classes="bot-setting-name")
                        if key == "spacing":
                            yield Select([("Geometric", "geom"), ("Arithmetic", "arith")], value=value,
                                         allow_blank=False, id=f"bot-setting-{key}", classes="bot-setting-value")
                        elif isinstance(value, bool):
                            yield Select([("On", True), ("Off", False)], value=value, allow_blank=False,
                                         id=f"bot-setting-{key}", classes="bot-setting-value")
                        else:
                            yield Input(value=str(value), id=f"bot-setting-{key}", classes="bot-setting-value")
            yield Static("", id="bot-settings-message", markup=False)
            with Horizontal(id="bot-settings-buttons"):
                yield Button("Apply settings", id="bot-settings-apply", variant="primary")
                yield Button("Built-in defaults", id="bot-settings-defaults")
                yield Button("Inherit global", id="bot-settings-inherit", disabled=not bool(self.asset))
                yield Button("Cancel", id="bot-settings-cancel")

    def on_mount(self) -> None:
        self.query_one("#bot-settings-asset").tooltip = "Choose global settings or one coin's effective configuration."
        self.query_one("#bot-settings-mode").tooltip = "Auto may adopt validated improvements. Manual keeps the saved settings while allowing candidate reports."
        self.query_one("#bot-settings-apply").tooltip = "Save changed fields for the selected scope."
        self.query_one("#bot-settings-defaults").tooltip = "Load shipped defaults into the form; Apply saves them."
        self.query_one("#bot-settings-inherit").tooltip = "Remove this coin's settings and mode overrides so it inherits both from global."
        self.query_one("#bot-settings-cancel").tooltip = "Discard edits and close this form."
        for key in self.current:
            self.query_one(f"#bot-setting-{key}").tooltip = f"Edit {key.replace('_', ' ')} for the selected scope."

    @on(Select.Changed, "#bot-settings-asset")
    def _asset_changed(self, event: Select.Changed) -> None:
        asset = str(event.value)
        if asset == self.asset:
            return
        self.drafts[self.asset] = {key: self.query_one(f"#bot-setting-{key}").value for key in self.current}
        self.draft_modes[self.asset] = str(self.query_one("#bot-settings-mode", Select).value)
        env = self.fetch(asset)
        if not env.get("ok"):
            self.query_one("#bot-settings-message", Static).update("Could not load settings for that coin.")
            self.query_one("#bot-settings-asset", Select).value = self.asset
            return
        self.asset = asset
        self._discard_ack = None
        self.query_one("#bot-settings-inherit", Button).disabled = not bool(asset)
        self.current = dict(env["result"]["config"])
        self.mode = env["result"].get("mode", "auto")
        self.baselines.setdefault(asset, (dict(self.current), self.mode))
        self.query_one("#bot-settings-mode", Select).value = self.draft_modes.get(asset, self.mode)
        values = self.drafts.get(asset, self.current)
        for key, value in values.items():
            field = self.query_one(f"#bot-setting-{key}")
            field.value = value if isinstance(field, Select) else str(value)
        self.query_one("#bot-settings-message", Static).update(
            f"Editing {asset or 'global defaults'}; unsaved edits stay in this form.")

    @on(Button.Pressed, "#bot-settings-defaults")
    def _defaults(self) -> None:
        for key, value in self.defaults.items():
            field = self.query_one(f"#bot-setting-{key}")
            field.value = value if isinstance(field, Select) else str(value)
        self.query_one("#bot-settings-message", Static).update("Built-in defaults loaded in the form; press Apply to save them.")

    @on(Button.Pressed, "#bot-settings-inherit")
    def _inherit(self) -> None:
        if self.asset and self._confirm_discard_other_drafts("inherit"):
            self.dismiss({"asset": self.asset, "reset": True})

    def _confirm_discard_other_drafts(self, action: str) -> bool:
        dirty = []
        for asset, values in self.drafts.items():
            if asset == self.asset or asset not in self.baselines:
                continue
            baseline, mode = self.baselines[asset]
            if (any(str(values.get(key)) != str(value) for key, value in baseline.items())
                    or self.draft_modes.get(asset, mode) != mode):
                dirty.append(asset or "global defaults")
        if dirty and self._discard_ack != action:
            self._discard_ack = action
            verb = "Apply" if action == "apply" else "Inherit global"
            self.query_one("#bot-settings-message", Static).update(
                f"Unsaved edits for {', '.join(dirty)} will be discarded. Return to those scopes, "
                f"or press {verb} again to discard them and continue.")
            return False
        return True

    @on(Button.Pressed, "#bot-settings-apply")
    def _apply(self) -> None:
        changes: dict[str, Any] = {}
        try:
            for key, old in self.current.items():
                value = self.query_one(f"#bot-setting-{key}").value
                if isinstance(old, bool):
                    if type(value) is not bool:
                        raise ValueError(f"{key} must be On or Off")
                elif isinstance(old, int):
                    value = int(value)
                elif isinstance(old, float):
                    value = float(value)
                    if not math.isfinite(value):
                        raise ValueError(f"{key} must be finite")
                if value != old:
                    changes[key] = value
        except (TypeError, ValueError) as exc:
            self.query_one("#bot-settings-message", Static).update(f"Invalid value: {exc}")
            return
        mode = self.query_one("#bot-settings-mode", Select).value
        result: dict[str, Any] = {"asset": self.asset}
        if changes:
            result["values"] = changes
        if mode != self.mode:
            result["mode"] = mode
        if self._confirm_discard_other_drafts("apply"):
            self.dismiss(result if len(result) > 1 else None)

    @on(Button.Pressed, "#bot-settings-cancel")
    def action_cancel(self) -> None:
        self.dismiss(None)


class SolTuiApp(App):
    """The console over the tested modules.

    v2 (the default) groups the panes into six destinations (Now, Signal, Research, Money, Library, Archive)
    plus Settings; see `shell.py` and docs/design/soltui-v2/DESIGN.md. Every classic tab is still a
    pane of the one `#main-tabs` TabbedContent, so `query_one(TabbedContent).active = "tab-…"` and every
    pane id keep working; v2 hides that tab bar and drives it from its own navigation. `classic=True`
    shows the original tab bar instead (`python -m soltui.tui --classic`).
    """

    TITLE = "soltui — SOL strategy console"
    SUB_TITLE = "paper by default · Coinbase manual orders can be live"
    COMMANDS = App.COMMANDS | {shell.SolCommands}
    CSS = """
    .simulation-row Input { width: 14; }
    .simulation-row Label { width: auto; margin-right: 1; }
    .simulation-row Checkbox { width: 25; }
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
    #forward-scope { width: 21; }
    #forward-horizon { width: 17; }
    #forward-coins { width: 16; }
    #forward-optimize { width: 24; }
    #forward-mode { width: 14; }
    #forward-start, #forward-stop, #forward-refresh { min-width: 10; }
    #forward-combos { width: 1fr; }
    #coinbase-order-product { width: 30; }
    #coinbase-order-quick { display: none; }
    #coinbase-order-side { width: 16; }
    #coinbase-order-size, #coinbase-order-id { width: 1fr; }
    #coinbase-pairs-query { width: 1fr; }
    #coinbase-pairs-table { height: 8; }
    #coinbase-manual-ticket, #advanced-order-ticket { height: auto; border: round $accent; padding: 0 1; }
    #advanced-product, #advanced-size { width: 1fr; min-width: 14; }
    #advanced-venue, #advanced-type, #advanced-side, #advanced-unit { width: 1fr; min-width: 16; }
    #advanced-quick { display: none; }
    #advanced-percent-preview, #advanced-percent-quick, #advanced-conditional-preview, #advanced-conditional-quick { display: none; }
    #advanced-limit-price, #advanced-stop-price { width: 1fr; }
    #advanced-chart { height: 5; }
    #roster-table { width: 1fr; }
    #docs-filter, #docs-search { width: 1fr; }
    #docs-kind, #docs-search-mode { width: 24; }
    TabbedContent { height: 1fr; }
    #editor-panel {
        height: 16;
    }
    #editor-panel TextArea { height: 1fr; }
    Tooltip { max-width: 76; height: auto; max-height: 18; }
    #help-hint { height: 1; color: $text-muted; padding: 0 1; }
    #compound-table { height: 22; }
    #compound-sections { height: 1fr; }
    #compound-tested { color: $text-muted; padding: 0 1; }
    #compound-results { height: 14; }
    #compound-forward-table { height: 12; }
    #compound-overview { height: 11; }
    #compound-coin { width: 16; }
    #compound-call { padding: 0 1; border: round $accent; }
    #compound-detail { color: $text-muted; padding: 0 1; }
    #compound-autopilot-status { padding: 0 1; border: round $success; }
    #signal-live-stream { padding: 0 1; border: round $accent; }
    #signal-live-chart-container { height: 7; margin: 1 0 0 0; }
    #signal-live-chart-yaxis { width: 14; height: 7; color: $text-muted; }
    #signal-live-plot { width: 1fr; height: 7; align-horizontal: right; }
    #signal-live-chart { height: 7; margin: 0; }
    #signal-live-score-tape { height: 1; }
    #signal-live-price-score, #signal-live-predictions-score { height: auto; text-style: bold; }
    #signal-live-vote-min-score, #signal-live-vote-min-resolved { width: 12; }
    #signal-live-chart-xaxis { height: 1; margin: 0 0 1 0; color: $text-muted; }
    #signal-live-predictions-table { height: 15; }
    #signal-live-detail { color: $text-muted; padding: 0 1; }
    #bots-top Label { width: auto; padding: 0 0 0 1; }
    #bots-bot { width: 24; }
    #bots-top Button { min-width: 8; width: auto; }
    #bots-start { width: 16; }
    #bots-days { width: 8; }
    #bots-config { width: 1fr; min-width: 16; }
    #bots-bt-coins, #bots-opt-coins { height: 14; }
    #bots-about { color: $text-muted; padding: 0 1; }
    #bots-stream { padding: 0 1; border: round $accent; }
    #bots-sections { height: 1fr; }
    #bots-set, #bots-bt-table, #bots-fwd-table { height: 16; }
    #bots-opt-table, #bots-prices { height: 22; }
    #bots-fit-table { height: 14; }
    #bots-fit-windows { height: 12; }
    #bots-fit-equity, #bots-fit-hold { height: 3; }
    #bots-fit-controls Button { width: auto; min-width: 12; }
    #bots-fit-status, #bots-fit-detail, #bots-fit-selection-summary { height: auto; padding: 0 1; }
    #bots-sec-council Input { width: 14; }
    #bots-sec-council Checkbox { width: 20; }
    #council-status, #council-fills { height: auto; padding: 1; }
    #backtest-pick { width: 44; }
    #backtest-roster { color: $text-muted; padding: 0 1; }
    #backtest-bg-status { padding: 0 1; height: auto; }
    /* Every table gets a title line: bold, in the accent colour, with a space above it so a page of
       tables reads as sections rather than one long grid. */
    .table-title { color: $accent; margin-top: 1; padding: 0 1; }

    /* -- v2 shell (docs/design/soltui-v2/DESIGN.md). The classic tab bar stays in the DOM and keeps
       driving the panes; v2 only hides it and navigates through #v2-topbar / #v2-subnav. -- */
    Screen { layers: default overlay; }
    Screen.v2 Header { display: none; }
    Screen.v2 #main-tabs > ContentTabs { display: none; }
    Screen.v2 #compound-sections > ContentTabs { display: none; }
    Screen.classic #v2-topbar, Screen.classic #v2-subnav, Screen.classic #v2-health,
    Screen.classic #v2-live-banner { display: none; }
    #v2-topbar { height: 1; background: $surface; }
    #v2-subnav { height: 1; }
    #status-row { height: 1; }
    #status-row #indicator { width: auto; }
    #v2-health { width: 1fr; height: 1; }
    #v2-live-banner { height: 1; display: none; }
    #v2-live-banner.on { display: block; }
    #v2-explain {
        layer: overlay; dock: right; width: 48; height: 1fr; display: none; margin: 4 0 1 0;
        background: $panel; border-left: thick $accent; padding: 1 2;
    }
    #v2-explain.open { display: block; }
    #now-body { height: 1fr; }
    #now-left, #now-right { width: 1fr; height: 1fr; }
    #now-needs { height: auto; max-height: 14; }
    #now-coins { height: 13; }
    #now-tiles { height: 5; }
    .now-tile { width: 1fr; height: 5; border: round $panel-lighten-1; padding: 0 1; }
    #now-activity, #now-research, #now-prices { padding: 0 1; height: auto; }
    #compound-hero { padding: 0 1; height: auto; margin-bottom: 1; }
    """
    BINDINGS = [
        Binding("f1", "show_help", "Help / glossary", priority=True),
        ("q", "quit", "Quit"),
        ("r", "run_backtest", "Run backtest"),
        ("c", "cancel", "Cancel sweep"),
        ("o", "open_doc", "Open in editor"),
        ("ctrl+s", "save_doc", "Save"),
        ("ctrl+e", "toggle_editor", "Show/hide editor"),
        Binding("ctrl+up", "grow_editor", "Editor taller", show=False),
        Binding("ctrl+down", "shrink_editor", "Editor shorter", show=False),
        Binding("f5", "batch_everything", "Backtest + forward test all", priority=True),
        Binding("f8", "experiment_selected", "Experiment with selected strategy", priority=True),
        # v2 navigation. Inputs and editors consume printable keys first, so typing a 1 or a ? into a
        # field never jumps away; these fire only when a table, list or button has focus.
        Binding("1", "v2_goto('now')", "Now", show=False),
        Binding("2", "v2_goto('signal')", "Signal", show=False),
        Binding("3", "v2_goto('research')", "Research", show=False),
        Binding("4", "v2_goto('money')", "Money", show=False),
        Binding("5", "v2_goto('library')", "Library", show=False),
        Binding("6", "v2_goto('archive')", "Archive", show=False),
        Binding("comma", "v2_goto('settings')", "Settings", show=False),
        Binding("left_square_bracket", "v2_cycle(-1)", "Previous view", show=False),
        Binding("right_square_bracket", "v2_cycle(1)", "Next view", show=False),
        Binding("question_mark", "v2_explain", "Explain"),
    ]

    EDITOR_HEIGHT = 16

    def __init__(self, settings: Settings | None = None, *, ui_state_path: Path | None = None,
                 ensure_autopilot: bool = False, refresh_wallet: bool = False,
                 stream_prices: bool = False, start: str = "tab-backtest", classic: bool = False,
                 auto_recover: bool | None = None) -> None:
        super().__init__()
        # Textual's capture returns -1 from fileno(). Python's multiprocessing
        # resource tracker passes that number to spawn, which rejects it. A
        # stream without a descriptor must raise instead; preserve capture and
        # let the tracker omit stderr rather than changing process-wide streams.
        self._capture_stderr = _CaptureWithoutInvalidFd(self._capture_stderr)
        # v2 shell state. `start` is the pane shown first: the console (`main`) opens on Now; the class
        # default stays Backtest because embedding code and the test suite address its widgets without
        # switching to it first. `classic` restores the original tab bar and theme.
        self._v2 = not classic
        self._auto_prediction_recovery = auto_recover
        self._start = start
        self._v2_dests: tuple[shell.Destination, ...] = shell.DESTINATIONS
        self._v2_dest, self._v2_index = "research", 0
        self._v2_last: dict[str, int] = {}
        self._v2_reads: dict[str, dict[str, Any]] = {}
        self._v2_autopilot: dict[str, Any] | None = None
        self._v2_autopilot_at = 0.0
        self._v2_notice: dict[str, Any] | None = None
        self._v2_needs: list[shell.Need] = []
        self._v2_now_loading = False
        self._v2_cumulative: str | None = None
        self._v2_forward: dict[str, Any] | None = None
        # Now hides the shared editor (it would take half the overview) without persisting that.
        self._v2_editor_suppressed = False
        self._v2_editor_was_open = True
        if self._v2:
            self.register_theme(shell.NIGHT)
            self.theme = shell.NIGHT.name
        # The real console starts the detached price recorder (public Coinbase stream) so the Bots
        # tab's forward tests have data; a test app must never spawn it or reach the network.
        self._stream_prices = stream_prices
        self._bots_loaded = False
        self._bots_bot = "grid"
        self._bots_coins: list[str] = []
        self._bots_ticks = 0
        self._council_busy = False
        self._council_initialized = False
        self._prediction_console_handle = None
        self._bots_schedule_busy = False
        self._bots_schedule_pending: list[tuple[str, bool]] = []
        self._bots_forward_running = False
        self._bots_selected: list[str] = []
        self._bots_runs: list[dict[str, Any]] = []
        self._bots_opt_screen: OptimizeScreen | None = None
        self._bots_fit_busy = False
        self._bots_fit_cancelling = False
        self._bots_fit_generation = 0
        self._bots_fit_active_token: int | None = None
        self._bots_fit_rows: dict[str, dict[str, Any]] = {}
        self._bots_fit_audits: dict[str, dict[str, Any]] = {}
        self._bots_fit_origin: dict[str, Any] | None = None
        self._bots_fit_coin: str | None = None
        self._bots_fit_window_rows: dict[str, dict[str, Any]] = {}
        self._bots_fit_request_id: str | None = None
        self._bots_fit_timer = None
        self._bots_fit_worker_handle = None
        self._bots_fit_alive = threading.Event()
        self._bots_fit_drained = threading.Event()
        self._bots_fit_drained.set()
        self._bots_fit_shutdown_drained = True
        # Where the editor's height and open/closed state persist. None (every test) keeps them
        # in memory, so no test reads or writes the owner's real layout.
        self._ui_state_path = ui_state_path
        # The real console starts any coin's training loop that autopilot wants running; a test
        # app must never spawn background processes.
        self._ensure_autopilot = ensure_autopilot
        # The real console shows the last kept wallet scan at start and re-scans in the background;
        # a test app must neither read the owner's kept scan nor reach the network.
        self._refresh_wallet = refresh_wallet
        self._coinbase_order_preview_data: dict[str, Any] | None = None
        self._coinbase_order_generation = 0
        self._coinbase_order_busy = False
        self._coinbase_order_unknown = True
        self._advanced_preview_data: dict[str, Any] | None = None
        self._advanced_generation = 0
        self._advanced_context_busy = False
        self._advanced_price_history: dict[str, list[tuple[float, float]]] = {}
        self._advanced_context_product = ""
        self._signal_live_price_history: dict[str, list[tuple[float, float]]] = {}
        self._signal_live_prediction_rows: list[dict[str, Any]] = []
        self._signal_live_score_history: dict[str, dict[float, float | None]] = {}
        self._signal_live_last_coin: str | None = None
        self._signal_live_busy = False
        self._signal_live_last_pred_update = 0.0
        self._signal_live_prediction_timer = None
        self._signal_live_prediction_key: tuple[str, float, int] | None = None
        self._signal_live_pred_generation = 0
        self._signal_live_refresh_requested = False
        self._signal_live_alive = threading.Event()
        self._signal_live_alive.set()
        self._signal_live_drained = threading.Event()
        self._signal_live_drained.set()
        self._jupiter_price_busy = False
        self._signal_live_jupiter_at = 0.0
        self._signal_live_jupiter_generation = 0
        self._signal_live_jupiter_coin: str | None = None
        self._signal_live_jupiter_state = "idle"
        self._signal_live_jupiter_drained = threading.Event()
        self._signal_live_jupiter_drained.set()
        self._signal_recovery_busy = False
        self._signal_recovery_at: dict[str, float] = {}
        self._signal_recovery_state: dict[str, Any] = {}
        self._signal_recovery_drained = threading.Event()
        self._signal_recovery_drained.set()
        self._coinbase_pairs_generation = 0
        self._editor_height = self.EDITOR_HEIGHT
        # The text of the preview the editor shows (None when a file or nothing is shown), so a
        # periodic table refresh does not reload an identical preview and reset its scroll.
        self._preview_text: str | None = None
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
        self._docs_revision: str | None = None
        self._forward_running = False
        self._forward_busy = False
        self._forward_seen: dict[str, Any] = {}
        self._batch_id: str | None = None
        self._batch_busy = False
        self._batch_last_summary = ""
        self._batch_log_key: str | None = None
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

    def get_theme_variable_defaults(self) -> dict[str, str]:
        # The CSS names the v2 tokens ($up, $down, ...); it parses before any theme applies.
        return {**super().get_theme_variable_defaults(), **shell.theme_variable_defaults()}

    def compose(self) -> ComposeResult:
        """Build the tab set, and around it the v2 chrome (hidden in classic mode)."""
        self._load_presets()
        yield Header()
        yield shell.SegmentBar(id="v2-topbar")
        yield shell.SegmentBar(id="v2-subnav")
        with Horizontal(id="status-row"):
            yield Static(build_title(self.state), id="indicator")
            yield Static("", id="v2-health")
        yield Static("Hover a control, table header or value for help · F1: searchable glossary · "
                     "? explain · ctrl+p every command", id="help-hint", markup=False)
        yield Static("", id="v2-live-banner")
        with TabbedContent(id="main-tabs", initial=self._start):
            with TabPane("Now", id="tab-now"):
                yield from self._now_pane()
            with TabPane("Settings", id="tab-settings"):
                yield from self._settings_pane()
            with TabPane("Strategies", id="tab-strategies"):
                yield from self._strategies_pane()
            with TabPane("Signals", id="tab-signals"):
                yield from self._signals_pane()
            with TabPane("Compound 5m", id="tab-compound"):
                yield from self._compound_pane()
            with TabPane("Forwardtest", id="tab-forwardtest"):
                yield from self._forward_pane()
            with TabPane("Experiments", id="tab-paper-experiments"):
                yield from self._paper_experiments_pane()
            with TabPane("Bots", id="tab-bots"):
                yield from self._bots_pane()
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
            with TabPane("Advanced order", id="tab-advanced-order"):
                yield from self._advanced_order_pane()
            with TabPane("Research", id="tab-research"):
                yield from self._research_pane()
            with TabPane("Docs", id="tab-docs"):
                yield from self._docs_pane()
        yield from self._editor_pane()
        yield Static("", id="v2-explain")
        yield Footer()

    def _now_pane(self) -> ComposeResult:
        """Now: does anything need me? Built from the same registry reads as every other surface."""
        with Horizontal(id="now-body"):
            with VerticalScroll(id="now-left"):
                yield Static("[b]Needs you[/b]: everything stale, failed or unseen, worst first. "
                             "Enter opens the view that fixes it.", classes="table-title", id="now-needs-title")
                yield OptionList(id="now-needs")
                yield Static("[b]Signal · every coin[/b]: latest backtest verdict, hit rates, paper dollars "
                             "and trainer state. Enter opens that coin's call.", classes="table-title")
                yield ExportPanel(GlossaryTable(id="now-coins"))
                yield Static("[b]Activity[/b]: recent dated events, newest first.", classes="table-title")
                yield Static("Loading…", id="now-activity")
            with VerticalScroll(id="now-right"):
                with Horizontal(id="now-tiles"):
                    for i in range(4):
                        yield Static("", id=f"now-tile-{i}", classes="now-tile")
                yield Static("[b]Research · the evidence so far[/b]", classes="table-title")
                yield Static("Loading…", id="now-research")
                yield Static("[b]Live prices[/b] from the price recorder", classes="table-title")
                yield Static("", id="now-prices")

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
        yield EditorBar(id="editor-bar")
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
                "Saved to ~/.config/soltui/. Strategy execution is dry-run only. "
                "Manual Coinbase orders are separate in Wallet and start disarmed.",
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
                ("fee_bps", "Jupiter Perps fee per side (bps; default 6)"),
                ("borrow_long_bps_hour", "Jupiter long borrow scenario (bps/hour)"),
                ("borrow_short_bps_hour", "Jupiter short borrow scenario (bps/hour)"),
                ("leverage", "Default paper leverage (1–250×)"),
                ("min_confidence", "Default minimum confidence (0–1)"),
                ("slippage_bps", "Slippage (bps)"),
                ("fill_delay", "Fill delay (bars)"),
                ("cpcv_groups", "CPCV blocks"),
                ("cpcv_k", "CPCV k (blocks/path)"),
                ("solana_address", "Solana address (public)"),
                ("base_address", "Base address (public)"),
                ("eth_address", "Ethereum address (public)"),
                ("hyperliquid_address", "Hyperliquid account (public)"),
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
            with Horizontal(classes="form-row"):
                yield Checkbox("Default: use leverage", value=self.settings.use_leverage, id="set-use_leverage")
                yield Checkbox("Default: short DOWN", value=self.settings.allow_short, id="set-allow_short")
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
            with Horizontal(classes="form-row"):
                yield Label("Forwardtest autostart:")
                yield Checkbox(
                    value=getattr(self.settings, "forwardtest_autostart", True),
                    id="set-forwardtest_autostart",
                )
            yield Static("[b]Signing key source[/b] (read-only; stat only, the files are never opened)",
                         classes="hint")
            yield Static("", id="key-sources")

    def _strategies_pane(self) -> ComposeResult:
        """Browse active cards and manage the executable roster."""
        with Vertical():
            yield Static(
                "Left: registered strategy cards. Guides and templates are stored separately. "
                "Right: your executable backtest roster. Space toggles registered strategies.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Input(placeholder="Filter cards by name, family or description", id="strategy-card-filter")
                yield Select([("All active cards", "all"), ("Registered strategies", "registered"),
                              ("TradingView cards", "tradingview")],
                             value="all", allow_blank=False, id="strategy-card-scope")
                yield Button("Refresh cards", id="strategy-cards-refresh")
            yield Static("", id="strategy-card-count", classes="table-title", markup=False)
            with Horizontal():
                yield ExportPanel(GlossaryTable(id="available-table"))
                yield ExportPanel(GlossaryTable(id="roster-table"))
            with Horizontal(classes="form-row"):
                yield Label("Params (k=v):")
                yield Input(placeholder="fast=20 slow=50", id="strategy-params")
            with Horizontal(classes="form-row"):
                yield Button("Add selected →", variant="success", id="btn-add")
                yield Button("Add all to roster", id="btn-roster-all")
                yield Button("← Remove selected", variant="error", id="btn-remove")
                yield Button("Reset to default", id="btn-reset-roster")
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-strategies")
                yield Button("Backtest selected", variant="warning", id="btn-bt-selected")
                yield Button("Backtest all untested", variant="warning", id="btn-bt-untested")
                yield Button("Backtest all", variant="warning", id="btn-bt-all")
            yield Static("", id="history-status")
            yield Static("", id="roster-status")

    def _paper_experiments_pane(self) -> ComposeResult:
        strategies = available_strategies()
        with VerticalScroll():
            yield Static("Prospective paper experiments: the strategy makes predictions on closed 1m candles. "
                         "Directional calls simulate a 1x trade from a future candle open to the chosen "
                         "horizon close, less the Settings round-trip costs. P&L covers settled calls only; "
                         "pending calls are not marked to market. No real orders are placed.", classes="hint")
            with Horizontal(classes="form-row"):
                yield Select([(name, name) for name, _ in strategies], id="paper-exp-strategy",
                             value=strategies[0][0], allow_blank=False)
                yield Input(value=self.settings.asset.upper(), placeholder="Coin", id="paper-exp-asset")
                yield Select([(f"{h} min", h) for h in (1, 5, 30)], value=5,
                             id="paper-exp-horizon", allow_blank=False)
                yield Input(value="1000", placeholder="Paper dollars", id="paper-exp-capital")
            with Horizontal(classes="form-row"):
                yield Input(value="{}", placeholder="Strategy parameters as JSON", id="paper-exp-params")
                yield Button("Start experiment", id="paper-exp-start", variant="success")
                yield Button("Resume selected", id="paper-exp-resume")
                yield Button("Stop selected", id="paper-exp-stop")
                yield Button("Refresh", id="paper-exp-refresh")
                yield Button("Status / activity", id="paper-exp-activity")
            yield Static("", id="paper-exp-transfer", markup=False)
            yield Static("No paper experiments yet.", id="paper-exp-status", markup=False)
            yield Static("Paper experiments — prospective simulated runs", classes="table-title")
            table = GlossaryTable(id="paper-exp-table")
            table.cursor_type = "row"
            table.add_columns("strategy", "coin", "horizon", "state", "calls", "resolved", "trades", "paper $", "P&L $", "message")
            yield ExportPanel(table)
            yield Static("Select a run to inspect its recent predictions and results.", id="paper-exp-detail", markup=False)
            yield Static("Selected experiment — predictions and outcomes", classes="table-title")
            events = GlossaryTable(id="paper-exp-events")
            events.add_columns("issued UTC", "starts UTC", "prediction", "outcome", "move bps", "paper P&L")
            yield ExportPanel(events)

    @on(Button.Pressed, "#paper-exp-start")
    def _paper_exp_start(self) -> None:
        try:
            params = json.loads(self.query_one("#paper-exp-params", Input).value or "{}")
            payload = {"strategy": str(self.query_one("#paper-exp-strategy", Select).value),
                       "asset": self.query_one("#paper-exp-asset", Input).value,
                       "minutes": int(self.query_one("#paper-exp-horizon", Select).value),
                       "capital": float(self.query_one("#paper-exp-capital", Input).value), "params": params}
        except (ValueError, TypeError) as exc:
            self.query_one("#paper-exp-status", Static).update(f"Invalid experiment: {exc}")
            return
        env = self._call("paperexperiment.start", payload)
        if not env["ok"]:
            self.query_one("#paper-exp-status", Static).update(self._msg(env))
            return
        self._paper_exp_refresh()

    @on(Button.Pressed, "#paper-exp-resume")
    def _paper_exp_resume(self) -> None:
        table = self.query_one("#paper-exp-table", GlossaryTable)
        if not table.row_count:
            return
        key = self._strategy_table_key(table)
        env = self._call("paperexperiment.resume", {"id": str(key)})
        if not env["ok"]:
            self.query_one("#paper-exp-status", Static).update(self._msg(env))
        else:
            self._paper_exp_refresh()

    @on(Button.Pressed, "#paper-exp-stop")
    def _paper_exp_stop(self) -> None:
        table = self.query_one("#paper-exp-table", GlossaryTable)
        if not table.row_count:
            return
        key = self._strategy_table_key(table)
        env = self._call("paperexperiment.stop", {"id": str(key)})
        if not env["ok"]:
            self.query_one("#paper-exp-status", Static).update(self._msg(env))
        else:
            self.query_one("#paper-exp-status", Static).update("Stop requested; waiting for the current check.")

    @on(Button.Pressed, "#paper-exp-activity")
    def _paper_exp_activity(self) -> None:
        table = self.query_one("#paper-exp-table", GlossaryTable)
        if not table.row_count:
            self._start_log("Paper experiment", "No experiment selected.")
            return
        key = self._strategy_table_key(table)
        row = getattr(self, "_paper_exp_rows", {}).get(key)
        if not row:
            return
        self._paper_exp_watched = key
        self._paper_exp_watch_state = None
        self._start_log(f"Paper experiment {key}", self._paper_exp_activity_line(row))

    @staticmethod
    def _paper_exp_activity_line(row: dict[str, Any]) -> str:
        trial = row.get("trial") or {}
        return (f"{row['asset']} {row['strategy']} · {row['minutes']}m · {row['phase']} · "
                f"{row['calls_recorded']} predictions, {trial.get('resolved', 0)} resolved, "
                f"{row['trades']} paper trades · P&L ${row['pnl']:+.2f} · "
                f"{trial.get('note') or row['message']}")

    @on(Button.Pressed, "#paper-exp-refresh")
    def _paper_exp_refresh_pressed(self) -> None:
        self._paper_exp_refresh()

    def _paper_exp_tick(self) -> None:
        if self.query("#main-tabs") and self.query_one("#main-tabs", TabbedContent).active == "tab-paper-experiments":
            self._paper_exp_refresh()

    def _paper_exp_refresh(self) -> None:
        env = self._call("paperexperiment.status", quiet=True)
        if not env["ok"]:
            self.query_one("#paper-exp-status", Static).update(self._msg(env))
            return
        runs = env["result"]["experiments"]
        self._paper_exp_rows = {r["id"]: r for r in runs}
        table = self.query_one("#paper-exp-table", GlossaryTable)
        selected = self._strategy_table_key(table) if table.row_count else None
        table.clear()
        for r in runs:
            trial = r.get("trial") or {}
            table.add_row(r["strategy"], r["asset"], str(r["minutes"]), r["phase"],
                          str(r["calls_recorded"]), str(trial.get("resolved", 0)), str(r["trades"]),
                          f"{r['equity']:.2f}", f"{r['pnl']:+.2f}", trial.get("note") or r["message"], key=r["id"])
        self.query_one("#paper-exp-status", Static).update(
            f"{len(runs)} paper experiment(s); {sum(bool(r['running']) for r in runs)} running. "
            "Results are simulated; no order was placed.")
        watched = self._paper_exp_rows.get(getattr(self, "_paper_exp_watched", ""))
        if watched:
            line = self._paper_exp_activity_line(watched)
            if line != getattr(self, "_paper_exp_watch_state", None):
                self._paper_exp_watch_state = line
                self._append_log(f"Paper experiment {watched['id']}", line)
        if runs:
            chosen = self._paper_exp_rows.get(selected, runs[0])
            table.move_cursor(row=table.get_row_index(chosen["id"]))
            self._paper_exp_show(chosen)

    @on(DataTable.RowHighlighted, "#paper-exp-table")
    def _paper_exp_highlighted(self, event: DataTable.RowHighlighted) -> None:
        row = getattr(self, "_paper_exp_rows", {}).get(str(event.row_key.value)) if event.row_key else None
        if row:
            self._paper_exp_show(row)

    def _paper_exp_show(self, row: dict[str, Any]) -> None:
        self.query_one("#paper-exp-detail", Static).update(
            f"{row['asset']} {row['strategy']} · {row['minutes']}m · "
            f"round-trip cost {row['cost_bps']:g} bps · "
            f"{(row.get('trial') or {}).get('note') or row['message']}")
        table = self.query_one("#paper-exp-events", GlossaryTable)
        table.clear()
        dirs = {1: "UP", -1: "DOWN", 0: "FLAT", None: "pending"}
        for call in reversed(row["calls"]):
            table.add_row(time.strftime("%m-%d %H:%M", time.gmtime(call["issued"])),
                          time.strftime("%m-%d %H:%M", time.gmtime(call["start"])),
                          dirs.get(call["prediction"], "?"),
                          "expired" if call["expired"] else dirs.get(call["outcome"], "?"),
                          _num(call["bps"]), _num(call["paper_pnl"]))

    def _simulation_controls(self, prefix: str) -> ComposeResult:
        s = self.settings
        yield Static("Jupiter Perps estimate · 6 bps entry + 6 bps exit on notional (editable in Settings). "
                     "Borrow and slippage are scenarios; network/swap costs are excluded. Other coins use "
                     "synthetic Jupiter economics. Confidence uses the last 100 resolved directional calls "
                     "(at least 20); it is not a calibrated probability. A threshold of 0 disables the gate.",
                     classes="hint")
        with Horizontal(classes="form-row simulation-row"):
            yield Checkbox("Use leverage", value=s.use_leverage, id=f"{prefix}-use-leverage")
            yield Label("Leverage (1–250×):")
            yield Input(str(s.leverage), id=f"{prefix}-leverage", type="number")
        with Horizontal(classes="form-row simulation-row"):
            yield Checkbox("Short DOWN signals", value=s.allow_short, id=f"{prefix}-allow-short")
            yield Label("Minimum confidence (0–1):")
            yield Input(str(s.min_confidence), id=f"{prefix}-min-confidence", type="number")

    def _simulation_form(self, prefix: str) -> dict[str, Any]:
        return {"use_leverage": self.query_one(f"#{prefix}-use-leverage", Checkbox).value,
                "leverage": float(self.query_one(f"#{prefix}-leverage", Input).value),
                "allow_short": self.query_one(f"#{prefix}-allow-short", Checkbox).value,
                "min_confidence": float(self.query_one(f"#{prefix}-min-confidence", Input).value)}

    def _forward_pane(self) -> ComposeResult:
        with Vertical():
            yield Static(
                "Paper direction calls on closed 1m Coinbase data for the chosen coins. UP/DOWN mean a move "
                "beyond the cost threshold; FLAT predicts neither. Once started it runs in the background "
                "until Stop, whatever tab is open.", classes="hint")
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-forwardtest")
                yield Select([("All strategies", "all"), ("Roster only", "roster"),
                              ("Combinations only", "combinations")],
                             id="forward-scope", value="all", allow_blank=False)
                yield Select([("All four", "all"), *((f"{h} min", str(h)) for h in (1, 5, 10, 30))],
                             id="forward-horizon", value="all", allow_blank=False)
                yield Select(self._forward_coin_options(), id="forward-coins",
                             value=self.settings.asset.upper(), allow_blank=False)
                yield Select([("Auto-optimize: on", "on"), ("Auto-optimize: off", "off")],
                             id="forward-optimize", value="on", allow_blank=False)
                yield Button("Start", id="forward-start", variant="success")
                yield Button("Stop", id="forward-stop", disabled=True)
                yield Button("Refresh", id="forward-refresh")
            with Horizontal(classes="form-row"):
                yield Input(placeholder="Combinations: rsi,macd; breakout,obv_trend", id="forward-combos")
                yield Select([(m, m) for m in ("all", "any", "vote", "mean")],
                             id="forward-mode", value="all", allow_blank=False)
            yield from self._simulation_controls("forward")
            yield Static("Forward results by coin, strategy and horizon · Stopped",
                         id="forward-status", classes="table-title", markup=False)
            table = GlossaryTable(id="forward-table")
            table.cursor_type = "row"
            table.add_columns("coin", "trial", "minutes", "resolved", "accuracy", "pending", "expired",
                              "changes", "saved default", "last call", "last outcome", "issued UTC", "cost bps",
                              "confidence", "trade", "net %", "trades", "liquidations", "execution", "active settings")
            yield ExportPanel(table)

    def _forward_coin_options(self) -> list[tuple[str, str]]:
        from .commands import forward_coins

        coins = forward_coins()
        asset = self.settings.asset.upper()
        if asset not in coins:
            coins = [asset, *coins]
        return [("All coins", "all"), *((c, c) for c in coins)]

    @on(Button.Pressed, "#forward-start")
    def _forward_start(self) -> None:
        horizon = self.query_one("#forward-horizon", Select).value
        raw = self.query_one("#forward-combos", Input).value
        coins = self.query_one("#forward-coins", Select).value
        params = {"scope": self.query_one("#forward-scope", Select).value,
                  "mode": self.query_one("#forward-mode", Select).value,
                  "coins": "all" if coins == "all" else [str(coins)],
                  "optimize": self.query_one("#forward-optimize", Select).value == "on",
                  "combinations": [[v.strip() for v in c.split(",")]
                                   for c in raw.split(";") if c.strip()]}
        if horizon != "all":
            params["horizons"] = [int(horizon)]
        status = self.query_one("#forward-status", Static)
        try:
            params.update(self._simulation_form("forward"))
        except ValueError:
            status.update("Enter a leverage and confidence number.")
            return
        env = self._call("forwardtest.start", params)
        if not env["ok"]:
            status.update(self._msg(env))
            return
        result = env["result"]
        run = self._call("forwardtest.run")
        if not run["ok"]:
            status.update(self._msg(run))
            return
        self._forward_running = True
        self._forward_seen = {}
        self._forward_controls()
        status.update(f"{len(result['assets'])} coin(s): watching {result['trials']} trials each; horizons "
                      f"{', '.join(map(str, result['horizons']))} min; auto-optimize "
                      f"{'on' if result['optimize'] else 'off'}. Runs in the background until Stop.")
        self._forward_show_running(result["assets"])

    @on(Button.Pressed, "#forward-stop")
    def _forward_stop(self) -> None:
        env = self._call("forwardtest.stop")
        status = self.query_one("#forward-status", Static)
        if not env.get("ok"):
            status.update(f"Stop not confirmed: {self._msg(env)}")
            return
        result = env.get("result") or {}
        if type(result.get("stopping")) is not bool:
            status.update("Stop not confirmed: the producer returned an invalid safety state.")
            return
        self._forward_running = result["stopping"]
        self._forward_controls()
        if not self._forward_running:
            self._forward_show_running([])
        status.update("Stopping after the current check…" if self._forward_running or self._forward_busy
                      else "Stopped; results saved.")

    @on(Button.Pressed, "#forward-refresh")
    def _forward_refresh(self) -> None:
        if self._forward_busy:
            return
        coins = self.query_one("#forward-coins", Select).value if self.query("#forward-coins") else None
        params = {} if self._forward_running else {"coins": "all" if coins == "all" else [str(coins)]}
        env = self._call("forwardtest.status", params, quiet=True)
        if env["ok"]:
            self._forward_render(env["result"]["rows"])
        else:
            self.query_one("#forward-status", Static).update(self._msg(env))

    def _forward_controls(self) -> None:
        if not self.query("#forward-start"):
            return
        self.query_one("#forward-start", Button).disabled = self._forward_running or self._forward_busy
        self.query_one("#forward-stop", Button).disabled = not self._forward_running
        self.query_one("#forward-refresh", Button).disabled = self._forward_busy
        for wid in ("use-leverage", "leverage", "allow-short", "min-confidence"):
            if self.query(f"#forward-{wid}"):
                self.query_one(f"#forward-{wid}").disabled = self._forward_running
        for wid in ("#forward-coins", "#forward-optimize", "#forward-scope", "#forward-horizon"):
            if self.query(wid):
                self.query_one(wid, Select).disabled = self._forward_running

    def _autostart_forwardtest(self) -> None:
        params = {
            "scope": "all",
            "mode": "all",
            "coins": "all",
            "optimize": True,
            "horizons": [1, 5, 10, 30],
        }
        env = self._call("forwardtest.start", params, quiet=True)
        if not env["ok"]:
            return
        result = env["result"]
        run = self._call("forwardtest.run", quiet=True)
        if not run["ok"]:
            return
        self._forward_running = True
        self._forward_seen = {}
        self._forward_controls()
        self._forward_show_running(result.get("assets", []))

    def _forward_show_running(self, assets: list[str]) -> None:
        """The header says the forward test runs, so it is visible from every tab."""
        base = type(self).SUB_TITLE
        self.sub_title = (f"{base} · forwardtest running on {len(assets)} coin(s)" if assets else base)

    def _forward_schedule(self) -> None:
        """Every 5 s: read the background runner's state; re-read results when a coin was checked.

        The runner (`forwardtest.run`) owns the checking; this only renders, so nothing here
        depends on which tab is open.
        """
        if not self.query("#forward-status"):
            return
        env = self._call("forwardtest.state", quiet=True)
        if not env["ok"]:
            return
        st = env["result"]
        was_busy = self._forward_busy
        self._forward_busy = bool(st["busy"]) or (not st["running"] and st["prepared"])
        self._forward_running = bool(st["running"])
        self._forward_show_running(st.get("assets", []) if self._forward_running else [])
        if not self._forward_running and not st["busy"]:
            self._forward_busy = False
        self._forward_controls()
        seen = {a: v.get("at") for a, v in st["last"].items()}
        if seen != getattr(self, "_forward_seen", {}) or was_busy != self._forward_busy:
            self._forward_seen = seen
            self._forward_status_job(st)

    @work(thread=True, exit_on_error=False, group="forwardtest")
    def _forward_status_job(self, st: dict[str, Any]) -> None:
        env = self._call("forwardtest.status", quiet=True)
        try:
            self.call_from_thread(self._forward_done, env, st)
        except RuntimeError:
            pass  # the app closed while the read was in flight

    def _forward_done(self, env: dict[str, Any], st: dict[str, Any] | None = None) -> None:
        if not self.query("#forward-status"):
            return
        status = self.query_one("#forward-status", Static)
        if env["ok"]:
            self._forward_render(env["result"]["rows"])
        st = st or {}
        last = st.get("last") or {}
        errors = {a: v["error"] for a, v in last.items() if v.get("error")}
        recorded = sum(v.get("recorded", 0) for v in last.values())
        if self._forward_running:
            when = max((v.get("at") or 0 for v in last.values()), default=0)
            stamp = time.strftime("%H:%M:%S", time.localtime(when)) if when else "-"
            text = (f"Running in the background on {len(st.get('assets') or [])} coin(s), auto-optimize "
                    f"{'on' if st.get('optimize') else 'off'} · last check {stamp}, {recorded} new predictions"
                    f" · {st.get('defaults_saved', 0)} setting(s) saved as defaults")
            if errors:
                text += " · will retry " + ", ".join(f"{a}: {e}" for a, e in list(errors.items())[:3])
            status.update(text)
        elif not st.get("busy"):
            status.update("Stopped; results saved.")

    def _forward_render(self, rows: list[dict[str, Any]]) -> None:
        table = self.query_one("#forward-table", DataTable)
        cursor = table.cursor_row
        selected = self._strategy_table_key(table) if table.row_count else None
        sort_state = getattr(table, "_sorted_by", None)
        self._forward_rows = {str(row["id"]): row for row in rows}
        table.clear()
        directions = {-1: "DOWN", 0: "FLAT", 1: "UP"}
        for r in rows:
            issued = (time.strftime("%m-%d %H:%M:%S", time.gmtime(r["last_issued"]))
                      if r["last_issued"] else "-")
            settings = "; ".join(
                f"{m['name']} " + ", ".join(f"{k}={v}" for k, v in m["params"].items())
                for m in r["settings"])
            table.add_row(r.get("asset", "-"), r["label"], r["minutes"], r["resolved"],
                          _pct(r["correct"] / r["resolved"] if r["resolved"] else None),
                          r["pending"], r["expired"], r["changes"], "yes" if r.get("saved_default") else "-",
                          directions.get(r["last_call"], "-"), directions.get(r["last_outcome"], "-"), issued,
                          f"{r['cost_bps']:g}", _pct(r.get("confidence")),
                          "yes" if r.get("traded") else "no", _pct(r.get("net_pct")),
                          r.get("paper_trades", 0), r.get("liquidations", 0),
                          (f"{r['execution']['leverage'] if r['execution']['use_leverage'] else 1:g}x "
                           f"{'long/short' if r['execution']['allow_short'] else 'long only'} "
                           f"min={r['execution']['min_confidence']:g}" if r.get("execution") else "legacy"),
                          r["note"] or settings, key=r["id"])
        if rows:
            if sort_state:
                column, reverse = sort_state
                table.sort(column, key=sort_key, reverse=reverse)
            try:
                cursor = table.get_row_index(selected) if selected is not None else cursor
            except Exception:  # noqa: BLE001 - the selected trial may no longer be in the refreshed results
                pass
            table.move_cursor(row=min(cursor, len(rows) - 1))

    async def on_unmount(self) -> None:
        self._signal_live_alive.clear()
        if self._prediction_console_handle is not None:
            self._prediction_console_handle.close()
            self._prediction_console_handle = None
        if self._signal_recovery_busy:
            await asyncio.to_thread(self._signal_recovery_drained.wait, 5.0)
        self._signal_live_pred_generation += 1
        self._signal_live_refresh_requested = False
        self._signal_live_jupiter_generation += 1
        self._signal_live_jupiter_state = "interrupted"
        if self._jupiter_price_busy:
            # urllib reads have their own bounded timeout. A closing app stops
            # publication immediately even when the read cannot be interrupted.
            self._jupiter_price_shutdown_drained = await asyncio.to_thread(
                self._signal_live_jupiter_drained.wait, 5.0)
        if self._signal_live_prediction_timer is not None:
            self._signal_live_prediction_timer.stop()
            self._signal_live_prediction_timer = None
        if self._signal_live_busy:
            await asyncio.to_thread(self._signal_live_drained.wait, 5.0)
        self._bots_fit_alive.clear()
        if self._bots_fit_timer is not None:
            self._bots_fit_timer.stop()
            self._bots_fit_timer = None
        if self._bots_fit_busy:
            self._call("bots.fit_cancel", {"request_id": self._bots_fit_request_id, "interrupted": True}, quiet=True)
            # The backend has no network and checks the event between bounded windows.
            # The thread posts no UI callbacks while the app is closing.
            self._bots_fit_shutdown_drained = await asyncio.to_thread(self._bots_fit_drained.wait, 5.0)
        if self._forward_running or self._forward_busy:
            self._forward_running = False
            # Stop this process without clearing the saved plan; the next launch resumes it.
            self.ctx.runtime.forward_stop.set()

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
                yield Button("Go to Signal Live", variant="success", id="btn-goto-signal-live")
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
            yield Static("[b]Signal reference[/b]: each signal's equation as implemented and its family.",
                         classes="table-title")
            yield ExportPanel(GlossaryTable(id="signals-table"))
            yield Static("[b]Family behaviour[/b]: what each kind of strategy is and when it fails.",
                         classes="table-title")
            yield ExportPanel(GlossaryTable(id="families-table"))

    def _compound_pane(self) -> ComposeResult:
        """Compound five-minute call in four sections: the live call and its metrics, the backtest,
        the forward test, and every coin. One long page was hard to read (owner, 2026-11-07).

        Every action is a `compound.*` registry command; this pane only renders.
        """
        with Vertical(id="compound-scroll"):
            with Horizontal(classes="form-row"):
                yield Label("Coin:")
                yield Select([(c, c) for c in compound_mod.coins()], value=self._initial_coin(),
                             allow_blank=False, id="compound-coin")
                yield Button("Edits apply to: all coins", id="compound-scope")
                yield Button("Autopilot: on", variant="success", id="compound-autopilot")
            yield Static("", id="compound-autopilot-status")
            yield Static("", id="compound-status")
            with TabbedContent(id="compound-sections", initial="cmp-live"):
                with TabPane("Live", id="cmp-live"):
                    with VerticalScroll():
                        yield Static(
                            "Choose Coinbase stream or Jupiter reference prices. Saved predictions use Coinbase candles.",
                            classes="hint",
                        )
                        with Horizontal(classes="controls"):
                            yield Label("Voting floor accuracy % (Enter to save):")
                            yield Input(str(self.settings.live_vote_min_accuracy), id="signal-live-vote-min-score", type="number")
                            yield Label("Min resolved / horizon:")
                            yield Input(str(self.settings.live_vote_min_resolved), id="signal-live-vote-min-resolved", type="integer")
                        with Horizontal(classes="controls"):
                            yield Label("Price feed:")
                            yield Select([("Coinbase", "coinbase"), ("Jupiter / jup.ag", "jupiter")], value="coinbase", allow_blank=False, id="signal-live-price-source")
                        yield Static("", id="signal-live-vote-status", markup=False)
                        yield Static("Aggregate score — · Flat", id="signal-live-price-score", markup=False)
                        yield Static("", id="signal-live-recovery-status", markup=False)
                        with Horizontal(classes="controls"):
                            yield Button("Forward testing →", id="signal-live-forward-link")
                            yield Button("Start predictions", id="signal-live-predictions-start", variant="primary")
                        yield Static("price recorder: checking…", id="signal-live-stream", markup=True)
                        yield Static("Price graph: loading…", id="signal-live-chart-context", classes="table-title", markup=True)
                        with Horizontal(id="signal-live-chart-container"):
                            yield Static("", id="signal-live-chart-yaxis", markup=True)
                            with Vertical(id="signal-live-plot"):
                                yield Sparkline([], id="signal-live-chart")
                        yield Static("", id="signal-live-score-tape", markup=False)
                        yield Static("", id="signal-live-chart-xaxis", markup=True)
                        yield Static("", id="signal-live-chart-stats", markup=True)
                        yield Static("Aggregate score — · Flat", id="signal-live-predictions-score", markup=False)
                        yield Static("[b]Top performing forward test strategies — predictions[/b]",
                                     id="signal-live-predictions-title",
                                     classes="table-title", markup=True)
                        live_table = GlossaryTable(id="signal-live-predictions-table")
                        live_table.cursor_type = "row"
                        live_table.add_columns("rank", "strategy", "win rate", "resolved",
                                               "1m pred", "5m pred", "10m pred", "30m pred",
                                               "horizon accuracy", "settings")
                        yield ExportPanel(live_table)
                        yield Static("Select a strategy above to inspect its parameters and horizon history.",
                                     id="signal-live-detail", markup=False)
                with TabPane("Call & metrics", id="cmp-call"):
                    with VerticalScroll():
                        yield Static(
                            "Each metric scores the next 5m bar from -1 (down) to +1 (up). Families vote "
                            "once, the regime reweights trend vs reversion styles, and any enabled gate "
                            "forces FLAT. Double-click a metric (or select it and press Space) to switch it; "
                            "a single click shows its full detail in the editor below. No order is placed.",
                            classes="hint")
                        # v2: the call as the answer (badge, composite, gates, context) above the detail.
                        yield Static("No call yet: press Signal now.", id="compound-hero")
                        with Horizontal(classes="form-row"):
                            yield Button("Signal now", variant="success", id="compound-signal")
                            yield Button("Toggle on/off", id="compound-toggle")
                            yield Button("Apply edits", variant="primary", id="compound-apply")
                            yield Button("Reset defaults", id="compound-reset")
                            yield Button("Adopt tuned settings now", id="compound-adopt")
                        yield Static("Press Signal now for the live call.", id="compound-call")
                        yield Static("", id="compound-table-title", classes="table-title")
                        yield ExportPanel(CompoundTable(id="compound-table"))
                        yield Static("", id="compound-detail")
                        with Horizontal(classes="form-row"):
                            yield Label("Selected (k=v):")
                            yield Input(placeholder="weight=1.5 period=9 enabled=1", id="compound-edit")
                        with Horizontal(classes="form-row"):
                            yield Label("Aggregate (k=v):")
                            yield Input(placeholder="entry=0.25 exit=0.1 leverage=5 fee_bps=6", id="compound-agg")
                with TabPane("Backtest", id="cmp-backtest"):
                    with VerticalScroll():
                        with Horizontal(classes="form-row"):
                            yield Button("Test status", id="status-compound-backtest")
                            yield Button("Backtest this coin", variant="warning", id="compound-backtest")
                            yield Button("Frontier: every metric, strongest 2%, held 1 h-24 h",
                                         variant="warning", id="compound-backtest-frontier")
                            yield Button("Backtest all coins", variant="warning", id="compound-backtest-all")
                        yield Static("", id="compound-tested")
                        yield Static("", id="compound-bt-status")
                        yield Static("", id="compound-relations")
                        yield Static("", id="compound-results-title", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="compound-results"))
                with TabPane("Forward test", id="cmp-forward"):
                    with VerticalScroll():
                        with Horizontal(classes="form-row"):
                            yield Button("Test status", id="status-compound-forward")
                            yield Button("Forward tick", id="compound-forward")
                            yield Button("Auto-forward: off", id="compound-auto")
                            yield Button("Refresh results", id="compound-refresh")
                        with Horizontal(classes="form-row"):
                            yield Button("Start unattended training", variant="success",
                                         id="compound-unattended-start")
                            yield Button("Stop unattended", variant="error", id="compound-unattended-stop")
                            yield Static("", id="compound-unattended")
                        yield Static("", id="compound-forward-title", classes="table-title")
                        yield Static("", id="compound-fwd-summary")
                        yield Static("", id="compound-horizon-summary", markup=False)
                        yield ExportPanel(GlossaryTable(id="compound-horizons"))
                        yield Static("Signal forward calls and outcomes", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="compound-forward-table"))
                with TabPane("All coins", id="cmp-coins"):
                    with VerticalScroll():
                        with Horizontal(classes="form-row"):
                            yield Button("Start unattended: all coins", variant="success",
                                         id="compound-unattended-all")
                            yield Button("Stop unattended: all coins", variant="error",
                                         id="compound-unattended-stop-all")
                        yield Static("[b]Every coin at a glance[/b]: its own settings, cached data, latest "
                                     "backtest verdict and hit rate, forward-test calls, hit rate and paper "
                                     "dollars, and whether its trainer runs. Select a coin to see it in full "
                                     "in the editor below.", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="compound-overview"))

    def _bots_pane(self) -> ComposeResult:
        """Five paper bots; Council uses its dedicated prospective controls.

        Every action is a `bots.*` or `prices.*` registry command; every bot is a simulation.
        """
        with Vertical(id="bots-scroll"):
            yield Static("SIMULATION AND DRY RUN ONLY: these bots place no orders.", classes="hint")
            with Horizontal(classes="form-row", id="bots-top"):
                yield Label("Bot", id="bots-picker-label")
                yield Select([(bots_mod.LABELS[b], b) for b in bots_mod.BOT_CHOICES], value="grid",
                             allow_blank=False, id="bots-bot")
                yield Label("Coins")
                yield Button("SOL", id="bots-coins")
                yield Label("Start")
                yield Input(placeholder="start of data", id="bots-start")
                yield Label("Days")
                yield Input(placeholder="all", id="bots-days")
                yield Label("Settings")
                yield Input(placeholder="range_pct=10 rungs=9", id="bots-config")
                yield Button("Apply", variant="primary", id="bots-apply")
                yield Button("Defaults", id="bots-reset")
            with Horizontal(classes="form-row", id="bots-editor-controls"):
                yield Button("Edit all settings", id="bots-edit")
                yield Static("Choose a coin and automatic or manual settings.", classes="hint")
            yield Static("", id="bots-about")
            with Horizontal(classes="form-row", id="bots-actions"):
                yield Button("Test status", id="status-bots")
                yield Button("Backtest", variant="warning", id="bots-backtest")
                yield Button("Start forward test", variant="success", id="bots-forward-start")
                yield Button("Stop forward test", variant="error", id="bots-forward-stop")
                yield Button("Refresh forward", id="bots-forward-refresh")
                yield Button("Auto-optimize (all coins)", variant="warning", id="bots-optimize")
                yield Button("Experiment workbench", id="bots-workbench")
            with Horizontal(classes="form-row", id="bots-fit-controls"):
                yield Button("Rank all coins (quick)", variant="primary", id="bots-fit-rank")
                yield Button("Audit selected coin", id="bots-fit-audit", disabled=True)
                yield Button("Cancel ranking / audit", id="bots-fit-cancel", disabled=True)
            with Horizontal(classes="form-row", id="bots-schedule-controls"):
                yield Button("Start daily auto-optimize", variant="success", id="bots-schedule-start")
                yield Button("Stop daily auto-optimize", variant="error", id="bots-schedule-stop")
                yield Button("Daily optimizer status", id="bots-schedule-status")
            yield Static("Daily optimizer: checking…", id="bots-schedule-summary", markup=False)
            yield Static("Coin suitability: quick ranking is provisional; audit adds multiple windows and stressed costs.",
                         id="bots-fit-status", markup=False)
            yield Static("", id="bots-status")
            yield Static("price recorder: checking…", id="bots-stream")
            with TabbedContent(id="bots-sections", initial="bots-sec-backtest"):
                with TabPane("Council", id="bots-sec-council"):
                    with VerticalScroll():
                        yield Static("Council · paper: Strong Buy opens long; Sell exits. Optional shorts mirror this. Neutral votes hold.", markup=False)
                        with Horizontal(classes="form-row"):
                            yield Label("Coin")
                            yield Input("SOL", id="council-asset")
                            yield Label("Paper capital $")
                            yield Input("10000", id="council-capital", type="number")
                            yield Label("Accuracy floor %")
                            yield Input("60", id="council-accuracy", type="number")
                            yield Label("Resolved floor")
                            yield Input("20", id="council-samples", type="integer")
                        with Horizontal(classes="form-row"):
                            yield Checkbox("Allow shorts", id="council-shorts")
                            yield Checkbox("Use leverage", id="council-leveraged")
                            yield Label("Leverage ×")
                            yield Input("2", id="council-leverage", type="number")
                            yield Label("Entry confidence 0–1")
                            yield Input("0.8", id="council-confidence", type="number")
                        with Horizontal(classes="form-row"):
                            yield Button("Save settings", id="council-save")
                            yield Button("Start paper Council", id="council-start", variant="success")
                            yield Button("Stop Council", id="council-stop", variant="error")
                            yield Button("Refresh", id="council-refresh")
                        yield Static("Read Council status to begin.", id="council-status", markup=False)
                        yield Static("Jupiter fees; real Coinbase candles supply paper fills. Confidence needs 20 prospective outcomes. Stop retains an open paper position.", markup=False)
                        yield Static("", id="council-fills", markup=False)
                with TabPane("Coin suitability", id="bots-sec-fit"):
                    with VerticalScroll():
                        yield Static("Rank all cached coins, then select a row to inspect or audit it. "
                                     "These simulations neither adopt settings nor place orders.", markup=False)
                        yield Static("Coin suitability ranking and selected audit outcomes", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-fit-table"))
                        yield Static("No coin selected.", id="bots-fit-selection-summary", markup=False)
                        yield Static("Select an audit window below to inspect its equity path. Sparklines show shape "
                                     "with independent vertical scales; compare numeric returns for magnitude.", markup=False)
                        yield Static("Equity: no selected result.", id="bots-fit-curve-context", markup=False)
                        yield Static("Bot equity (sampled full-account path)", classes="table-title")
                        yield Sparkline([], id="bots-fit-equity")
                        yield Static("Buy-and-hold equity over the same sample", classes="table-title")
                        yield Sparkline([], id="bots-fit-hold")
                        yield ExportPanel(GlossaryTable(id="bots-fit-windows"))
                        yield Static("Complete metrics, settings and template evidence", classes="table-title")
                        yield Static("No coin selected.", id="bots-fit-detail", markup=False)
                with TabPane("Backtest", id="bots-sec-backtest"):
                    with VerticalScroll():
                        yield Static("No backtest yet for this bot: press Backtest.", id="bots-bt-title")
                        yield Static("[b]Every coin in the last backtest[/b]: select a row to show its detail "
                                     "below", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-bt-coins"))
                        yield Static("[b]What it set[/b] at its start, from the price at that moment",
                                     classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-set"))
                        yield Static("[b]What it made[/b]: the bot beside buy-and-hold of the same capital, "
                                     "after fees and slippage", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-bt-table"))
                with TabPane("Forward test", id="bots-sec-forward"):
                    with VerticalScroll():
                        yield Static("No forward test yet.", id="bots-fwd-summary")
                        yield Static("[b]Forward test so far[/b]: the recorded stream since it started, "
                                     "replayed through the bot in dry-run", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-fwd-table"))
                with TabPane("Auto-optimize", id="bots-sec-optimize"):
                    with VerticalScroll():
                        yield Static("Auto-optimize has not run for this bot.", id="bots-opt-verdict")
                        yield Static("[b]Per coin[/b]: the windows each coin ran and the pick against the "
                                     "current settings out of sample", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-opt-coins"))
                        yield Static("[b]Every configuration searched[/b], best train rank first; the test "
                                     "columns are out of sample", classes="table-title")
                        yield ExportPanel(GlossaryTable(id="bots-opt-table"))
                with TabPane("Live prices", id="bots-sec-prices"):
                    yield Static("[b]Streamed Coinbase markets[/b]: newest best bid and ask from the "
                                 "recorder", classes="table-title")
                    yield ExportPanel(GlossaryTable(id="bots-prices"))

    # -- Bots tab ------------------------------------------------------------

    def _bots_load(self) -> None:
        """First view: fill the coin list and the tables' columns, then render the selected bot."""
        for table_id, cols in (("#bots-bt-coins", ("coin", "from", "to", "hours", "bot return", "hold return",
                                                   "vs hold", "bot max dd", "fills", "bridged h", "history")),
                               ("#bots-opt-coins", ("coin", "history", "windows", "current test median",
                                                    "pick test median", "pick wins", "pick losses", "coin verdict")),
                               ("#bots-set", ("setting", "value")), ("#bots-bt-table", ("metric", "value")),
                               ("#bots-fwd-table", ("metric", "value")),
                               ("#bots-opt-table", ("config change", "train rank", "train median return",
                                                    "test median return")),
                               ("#bots-prices", ("market", "bid", "ask", "spread bps", "quote age s"))):
            table = self.query_one(table_id, DataTable)
            if not table.columns:
                table.add_columns(*cols)
                table.cursor_type = "row"
        for table_id, columns in (
            ("#bots-fit-table", ("coin", "fit", "audit", "suitability score", "sim net", "vs hold", "max dd",
                                 "cycles / deals", "window", "reason")),
            ("#bots-fit-windows", ("window", "from", "to", "cost stress", "sim net", "hold return",
                                   "vs hold", "max dd", "cycles / deals", "costs $")),
        ):
            table = self.query_one(table_id, DataTable)
            if not table.columns:
                table.add_columns(*columns)
                table.cursor_type = "row"
        env = self._call("bots.overview", quiet=True)
        coin = self.settings.asset.upper()
        if env["ok"]:
            self._bots_coins = env["result"]["coins"] or [coin]
        self._bots_selected = [coin if coin in (self._bots_coins or [coin]) else (self._bots_coins or [coin])[0]]
        self._bots_show_coins()
        self._bots_render_selected()
        self._bots_fit_controls()

    def _bots_coin(self) -> str:
        """The first selected coin: what a forward test runs on."""
        return (self._bots_selected or [self.settings.asset.upper()])[0]

    def _bots_show_coins(self) -> None:
        chosen = self._bots_selected
        label = (chosen[0] if len(chosen) == 1 else
                 f"all {len(chosen)}" if self._bots_coins and set(chosen) == set(self._bots_coins) else
                 f"{len(chosen)} coins")
        self.query_one("#bots-coins", Button).label = label

    def _bots_render_config(self) -> bool:
        env = self._call("bots.config", {"bot": self._bots_bot}, quiet=True)
        about = self.query_one("#bots-about", Static)
        if not env["ok"]:
            about.update(Text(self._msg(env)))
            return False
        r = env["result"]
        cfg = " ".join(f"{k}={v}" for k, v in r["config"].items())
        lines = [r["about"], f"Global defaults ({r.get('mode', 'auto')}): {cfg}"]
        selected = [] if self._bots_bot == "triangle" else (self._bots_selected or [self._bots_coin()])
        for coin in selected[:3]:
            coin_env = self._call("bots.config", {"bot": self._bots_bot, "asset": coin}, quiet=True)
            if coin_env.get("ok"):
                values = " ".join(f"{k}={v}" for k, v in coin_env["result"]["config"].items())
                lines.append(f"{coin} effective settings ({coin_env['result'].get('mode', 'auto')}; "
                             f"coin override or global fallback): {values}")
            else:
                lines.append(f"{coin} effective settings unavailable: {self._msg(coin_env)}")
        if len(selected) > 3:
            lines.append(f"{len(selected) - 3} more selected coins; use Edit all settings to inspect each.")
        about.update(Text("\n".join(lines)))
        self.query_one("#bots-config", Input).placeholder = cfg
        return True

    def _bots_render_selected(self) -> None:
        council = self._bots_bot == "council"
        for widget in self.query_one("#bots-top").children:
            if widget.id not in ("bots-picker-label", "bots-bot"):
                widget.display = not council
        for selector in ("#bots-editor-controls", "#bots-actions", "#bots-fit-controls",
                         "#bots-schedule-controls", "#bots-schedule-summary", "#bots-fit-status"):
            self.query_one(selector).display = not council
        sections = self.query_one("#bots-sections", TabbedContent)
        if council:
            self.query_one("#bots-about", Static).update(bots_mod.ABOUT["council"])
            self._bots_forward_running = False
            sections.active = "bots-sec-council"
            self._council_request()
            return
        if sections.active == "bots-sec-council":
            sections.active = "bots-sec-backtest"
        if not self._bots_render_config():
            return
        self.query_one("#bots-coins", Button).disabled = self._bots_bot == "triangle"
        self._bots_fit_controls()
        results = self._call("bots.results", {"bot": self._bots_bot, "limit": 1}, quiet=True)
        if results["ok"] and results["result"]:
            self._bots_runs = list(results["result"])
            self._bots_render_backtest(results["result"][0])
        else:
            self._bots_clear("#bots-set", "#bots-bt-table", "#bots-bt-coins")
            self.query_one("#bots-bt-title", Static).update("No backtest yet for this bot: press Backtest.")
        opt = self._call("bots.optimize_result", {"bot": self._bots_bot}, quiet=True)
        if opt["ok"] and opt["result"]:
            self._bots_render_optimize(opt["result"])
        else:
            self._bots_clear("#bots-opt-table", "#bots-opt-coins")
            self.query_one("#bots-opt-verdict", Static).update("Auto-optimize has not run for this bot.")
        self._bots_forward_refresh()

    def _bots_clear(self, *ids: str) -> None:
        for table_id in ids:
            self.query_one(table_id, DataTable).clear()

    @staticmethod
    def _bots_price(value: float) -> str:
        """Prices from 75,790.12 down to 0.0000023 without scientific notation."""
        if value >= 1000:
            return f"{value:,.2f}"
        if value >= 1:
            return f"{value:,.4f}"
        return f"{value:.8f}".rstrip("0")

    @staticmethod
    def _bots_pct(value: float) -> str:
        """Two decimals: a forward test's first hours move by hundredths of a percent."""
        return f"{value * 100:+.2f}%"

    @staticmethod
    def _bots_fmt(value: Any) -> str:
        if value is None:
            return "-"
        if isinstance(value, bool):
            return "yes" if value else "no"
        if isinstance(value, float):
            return f"{value:,.6g}" if abs(value) < 1e-3 or abs(value) >= 1e6 else f"{value:,.4f}"
        if isinstance(value, (list, tuple)):
            return ", ".join(SolTuiApp._bots_fmt(v) for v in value[:12]) + (" …" if len(value) > 12 else "")
        if isinstance(value, dict):
            return ", ".join(f"{k}={SolTuiApp._bots_fmt(v)}" for k, v in list(value.items())[:8])
        return str(value)

    def _bots_metrics(self, table_id: str, results: dict[str, Any]) -> None:
        table = self.query_one(table_id, DataTable)
        table.clear()
        for key in ("total_return", "hold_return", "excess_return", "max_drawdown", "hold_max_drawdown"):
            if key in results:
                table.add_row(key, self._bots_pct(results[key]) if results[key] is not None else "-")
        for key, value in results.items():
            if key in ("total_return", "hold_return", "excess_return", "max_drawdown", "hold_max_drawdown",
                       "per_triangle", "cycles"):
                continue
            table.add_row(key, self._bots_fmt(value))
        for name, row in (results.get("per_triangle") or {}).items():
            table.add_row(name, f"observed {row['observed']}, best net edge "
                                f"{self._bots_fmt(row['best_edge_bps'])} bps, executed {row['executed']}, "
                                f"P&L ${row['pnl_usd']:,.4f}")

    def _bots_render_backtest(self, r: dict[str, Any]) -> None:
        where = r["asset"] if r["bot"] != "triangle" else "every triangle"
        gap = f"; stopped at a data gap after {r['stopped_at_gap']}" if r.get("stopped_at_gap") else ""
        if r.get("bridged_bars"):
            gap += f"; {r['bridged_bars']} missing hour(s) in {r['bridged_gaps']} short gap(s) bridged flat"
        if r.get("start_note"):
            gap += f"; {r['start_note']}"
        self.query_one("#bots-bt-title", Static).update(Text(
            f"{bots_mod.LABELS[r['bot']]} on {where}, started {r['start']} -> {r['end']} "
            f"({r['interval']}, data: {r['data_source']}{gap}). What it set at the start, then what it made:"))
        set_t = self.query_one("#bots-set", DataTable)
        set_t.clear()
        setup = dict(r.get("set") or {})
        orders = setup.pop("orders", None)
        for key, value in setup.items():
            set_t.add_row(key, self._bots_fmt(value))
        for row in orders or []:
            set_t.add_row(row["order"], f"${row['price']:,.4f} for ${row['usd']:,.2f}; avg ${row['avg_entry']:,.4f}, "
                                        f"take-profit ${row['take_profit']:,.4f}")
        self._bots_metrics("#bots-bt-table", r.get("results") or {})

    def _bots_render_optimize(self, r: dict[str, Any]) -> None:
        v = r["verdict"]
        if isinstance(r.get("reports"), dict):
            head = "Independent coin-specific searches; global defaults unchanged"
        elif v.get("saved"):
            head = "SAVED new settings: " + ", ".join(f"{c['setting']} {c['before']} -> {c['after']}"
                                                      for c in v.get("changes") or [])
        else:
            head = "NOT SAVED: your settings are unchanged"
        skipped_rows = r.get("skipped") or []
        skipped_text = "; ".join(f"{coin}: {reason}" for coin, reason in skipped_rows.items()) if isinstance(
            skipped_rows, dict) else ", ".join(skipped_rows)
        skipped = f" Skipped: {skipped_text}." if skipped_text else ""
        used = r.get("coins_used") or []
        self.query_one("#bots-opt-verdict", Static).update(Text(
            f"Run {r.get('run', 1)}. {head}.\nWhy: {v.get('reason', '-')}\n{r['candidates']} configurations on "
            f"{len(used)} coin(s) ({r['universe']}); picked on {r['train_cells']} train cells, checked on "
            f"{r['test_cells']} test cells ({r['seconds']} s).{skipped}"))
        coins = self.query_one("#bots-opt-coins", DataTable)
        coins.clear()
        for row in r.get("per_coin") or []:
            verdict = row.get("verdict") or {}
            changes = ", ".join(f"{c['setting']} {c['before']} → {c['after']}"
                                for c in verdict.get("changes") or [])
            coin_verdict = ((f"saved [{verdict.get('confidence', 'unreported')}]: " +
                             (changes or "coin-specific settings") + " — " + str(verdict.get("reason") or "no reason reported")) if verdict.get("saved")
                            else ("not saved: " + str(verdict.get("reason") or "no adoption"))) if verdict else "-"
            coins.add_row(row["coin"], row.get("data_source") or "-",
                          f"{row['train_windows']} train / {row['test_windows']} test",
                          self._bots_pct(row["current_test_median"]) if row["current_test_median"] is not None else "-",
                          self._bots_pct(row["pick_test_median"]) if row["pick_test_median"] is not None else "-",
                          str(row["pick_wins"]), str(row["pick_losses"]), coin_verdict)
        table = self.query_one("#bots-opt-table", DataTable)
        table.clear()
        for row in r["table"]:
            label = "(current)" if row["current"] else " ".join(f"{k}={v}" for k, v in row["changes"].items())
            table.add_row(label, self._bots_fmt(row["train_mean_rank"]),
                          self._bots_pct(row["train_median"]) if row["train_median"] is not None else "-",
                          self._bots_pct(row["test_median"]) if row["test_median"] is not None else "-")

    def _bots_render_forward(self, r: dict[str, Any]) -> None:
        summary = self.query_one("#bots-fwd-summary", Static)
        if not r.get("forward"):
            summary.update(Text(r.get("message", "No forward test.")))
            self._bots_clear("#bots-fwd-table")
            return
        f = r["forward"]
        state = "running" if r["running"] else f"stopped {r.get('stopped')}"
        where = f["asset"] if r["bot"] != "triangle" else "every triangle"
        rec = r.get("recorder") or {}
        stream = "recorder live" if rec.get("live") else "RECORDER NOT LIVE: no new data is arriving"
        extra = ""
        if r.get("stopped_at_gap"):
            extra = f"; coverage ends at a recorder gap after {r['stopped_at_gap']}"
        summary.update(Text(f"{bots_mod.LABELS[r['bot']]} forward test on {where}, started {r['started']} "
                            f"({state}); {r.get('snapshots', 0)} snapshots to {r.get('last_snapshot') or '-'}"
                            f"; {stream}{extra}. {r.get('message', '')}"))
        table = self.query_one("#bots-fwd-table", DataTable)
        self._bots_metrics("#bots-fwd-table", r.get("results") or {})
        for key, value in (r.get("set") or {}).items():
            if key != "orders":
                table.add_row(f"set: {key}", self._bots_fmt(value))

    def _bots_render_prices(self, r: dict[str, Any]) -> None:
        stream = self.query_one("#bots-stream", Static)
        prices = r.get("prices") or {}
        if r.get("live"):
            state = (f"recording automatically: {len(prices)} markets, {r.get('recorded_days', 0)} day file(s) "
                     f"in {r.get('dir', 'prices/')}")
        elif r.get("running"):
            state = "price recorder running, waiting for its first snapshot"
        else:
            state = "price recorder not running: restarting it (checked every minute)"
        if r.get("last_error"):
            state += f"; last error: {r['last_error']}"
        top = "  ".join(f"{p.split('-')[0]} {self._bots_price(prices[p]['mid'])}"
                        for p in ("BTC-USD", "ETH-USD", "SOL-USD") if p in prices)
        stream.update(Text(f"{state}   {top}"))
        if not self.query_one("#bots-prices", DataTable).columns:
            return
        table = self.query_one("#bots-prices", DataTable)
        table.clear()
        for product in sorted(prices):
            q = prices[product]
            table.add_row(product, self._bots_price(q["bid"]), self._bots_price(q["ask"]),
                          f"{q['spread_bps']:,.2f}", f"{q['quote_age_s']:,.1f}")

    def _bots_status(self, text: str) -> None:
        self.query_one("#bots-status", Static).update(Text(text))

    # Not exclusive: a forward refresh must not cancel a running optimize.
    @work(thread=True, group="bots")
    def _bots_job(self, name: str, params: dict[str, Any], label: str, log_key: str = "") -> None:
        if self.query("#bots-status"):
            self.call_from_thread(self._bots_status, f"{label}…")
        env = self._call_with_progress(name, params, log_key or "Bot backtest") if name == "bots.backtest" else self._call(name, params)
        self.call_from_thread(self._bots_after, name, env, log_key)

    def _bots_after(self, name: str, env: dict[str, Any], log_key: str = "") -> None:
        if not self.query("#bots-status"):
            return
        if name == "bots.backtest":
            result = env.get("result") or {}
            self._append_log(log_key or "Bot backtest", self._msg(env) if not env["ok"] else
                             f"Finished: {result.get('ran', 0)} coin(s); errors: {result.get('errors') or 'none'}")
        elif name == "bots.optimize":
            self._append_log(log_key or "Bot optimize", self._msg(env) if not env["ok"] else "Optimization finished; see the results tab.")
        if not env["ok"]:
            self._bots_status(f"{name}: {self._msg(env)}")
            if name == "bots.optimize" and self._bots_opt_screen is not None and self._bots_opt_screen.is_attached:
                self._bots_opt_screen.show_result(None, self._msg(env))
            return
        r = env["result"]
        if name == "bots.backtest":
            self._bots_render_many(r)
            self.query_one("#bots-sections", TabbedContent).active = "bots-sec-backtest"
        elif name == "bots.optimize":
            v = r["verdict"]
            msg = (str(v.get("reason")) if isinstance(r.get("reports"), dict) else
                   "SAVED: " + ", ".join(f"{c['setting']} {c['before']} -> {c['after']}" for c in v.get("changes") or [])
                   if v.get("saved") else "not saved: no configuration reliably beat your settings")
            self._bots_status(f"auto-optimize run {r.get('run', 1)}: {msg}")
            self.notify(f"{bots_mod.LABELS[r['bot']]} auto-optimize run {r.get('run', 1)}: {msg}",
                        severity="information" if v.get("saved") else "warning", timeout=12)
            if self._bots_opt_screen is not None and self._bots_opt_screen.is_attached:
                self._bots_opt_screen.show_result(r)
            self._bots_render_selected()  # reloads the (possibly adopted) settings first
            self._bots_render_optimize(r)  # then the report in hand, which is authoritative
            self.query_one("#bots-sections", TabbedContent).active = "bots-sec-optimize"
        elif name in ("bots.forward_start", "bots.forward_stop"):
            self._bots_status("forward test started" if name == "bots.forward_start" else
                              r.get("message", "forward test stopped"))
            self._bots_forward_refresh()
            self.query_one("#bots-sections", TabbedContent).active = "bots-sec-forward"
        elif name == "bots.forward_status":
            self._bots_forward_running = bool(r.get("running"))
            self._bots_render_forward(r)
        elif name == "bots.save":
            scope = f"{r['asset']} coin settings" if r.get("asset") else "global defaults"
            if log_key == "inherit-global" and r.get("asset"):
                self._bots_status(f"{r['asset']} overrides removed; this coin now inherits global settings and mode.")
            else:
                mode = f" ({r['mode']})" if r.get("mode") else ""
                self._bots_status(f"{scope}{mode} saved: " + " ".join(f"{k}={v}" for k, v in r["config"].items()))
            self.query_one("#bots-config", Input).value = ""
            self._bots_render_selected()
        elif name == "prices.ensure":
            if not r.get("running"):
                self._bots_status("the price recorder could not start: " + (r.get("agent_error") or
                                  str((r.get("started") or {}).get("log") or "see prices/recorder.log")))
            self._bots_tick()

    def _bots_forward_refresh(self) -> None:
        if self._bots_bot == "council":
            return
        self._bots_job("bots.forward_status", {"bot": self._bots_bot}, "replaying the recorded stream")

    @on(Button.Pressed, "#council-save")
    @on(Button.Pressed, "#council-start")
    @on(Button.Pressed, "#council-stop")
    @on(Button.Pressed, "#council-refresh")
    def _council_action(self, event: Button.Pressed) -> None:
        name = {"council-save": "council.config", "council-start": "council.start",
                "council-stop": "council.stop", "council-refresh": "council.status"}[event.button.id]
        params = {}
        try:
            if name == "council.config":
                params = {"config": {"asset": self.query_one("#council-asset", Input).value.strip().upper(),
                    "capital": float(self.query_one("#council-capital", Input).value),
                    "min_accuracy": float(self.query_one("#council-accuracy", Input).value),
                    "min_resolved": int(self.query_one("#council-samples", Input).value),
                    "execution": {"allow_short": self.query_one("#council-shorts", Checkbox).value,
                        "use_leverage": self.query_one("#council-leveraged", Checkbox).value,
                        "leverage": float(self.query_one("#council-leverage", Input).value),
                        "min_confidence": float(self.query_one("#council-confidence", Input).value)}}}
        except ValueError:
            self.query_one("#council-status", Static).update("Enter valid Council settings before saving.")
            return
        self._council_request(name, params)

    def _council_request(self, name: str = "council.status", params: dict | None = None) -> None:
        if self._council_busy or not self._signal_live_alive.is_set():
            return
        self._council_busy = True
        self._council_job(name, params or {})

    @work(thread=True, exit_on_error=False, group="council-ui")
    def _council_job(self, name: str, params: dict) -> None:
        try:
            env = self._call(name, params, quiet=True)
            if env.get("ok") and name == "council.config":
                env = self._call("council.status", quiet=True)
            if self._signal_live_alive.is_set():
                self.call_from_thread(self._council_done, env)
        except RuntimeError:
            pass
        finally:
            self._council_busy = False

    def _council_done(self, env: dict) -> None:
        if not self._signal_live_alive.is_set():
            return
        if not env.get("ok"):
            self.query_one("#council-status", Static).update(self._msg(env))
            return
        s = env["result"]
        p = s.get("position")
        position = ("Long" if p["direction"] > 0 else "Short") + f" @ ${p['entry_price']:g}" if p else "Flat"
        confidence = f"{s['confidence']:.1%}" if s.get("confidence") is not None else "Warming up"
        self.query_one("#council-status", Static).update(
            f"{'Running' if s.get('running') else 'Stopped'} · {s.get('message', '')}\n"
            f"{s['config']['asset']} · {position} · Equity ${s.get('equity', 0):,.2f} · "
            f"Confidence {confidence} ({s.get('confidence_samples', 0)} samples)"
            + (" · Fill pending" if s.get("pending") else ""))
        locked = bool(s.get("running") or p or s.get("pending"))
        for widget in self.query("#bots-sec-council Input, #bots-sec-council Checkbox"):
            widget.disabled = locked
        self.query_one("#council-save", Button).disabled = locked
        self.query_one("#council-start", Button).disabled = bool(s.get("running"))
        self.query_one("#council-stop", Button).disabled = not s.get("running")
        if not self._council_initialized:
            cfg = s["config"]
            for field, key in (("asset", "asset"), ("capital", "capital"), ("accuracy", "min_accuracy"), ("samples", "min_resolved")):
                self.query_one(f"#council-{field}", Input).value = str(cfg[key])
            for field, key in (("leverage", "leverage"), ("confidence", "min_confidence")):
                self.query_one(f"#council-{field}", Input).value = str(cfg["execution"][key])
            self.query_one("#council-shorts", Checkbox).value = cfg["execution"]["allow_short"]
            self.query_one("#council-leveraged", Checkbox).value = cfg["execution"]["use_leverage"]
            self._council_initialized = True
        self.query_one("#council-fills", Static).update("\n".join(
            f"{time.strftime('%H:%M:%S UTC', time.gmtime(f['at']))} · {f['side']} @ ${f['price']:g} · {f['reason']}"
            for f in s.get("fills", [])[:20]) or "No paper fills yet.")

    def _bots_tick(self) -> None:
        """Every 5 s: once a minute keep the recorder on (any tab); while the Bots tab is open, the
        stream line, live prices, forward refresh and optimize progress."""
        self._bots_ticks += 1
        if self._stream_prices and self._bots_ticks % 12 == 0:
            self._bots_job("prices.ensure", {}, "checking the price recorder")
        if not self.query("#bots-stream") or not self._bots_loaded:
            return
        try:
            if self.query_one(TabbedContent).active != "tab-bots":
                return
        except NoMatches:
            return
        self._council_request()
        env = self._call("prices.status", quiet=True)
        if env["ok"]:
            self._bots_render_prices(env["result"])
        self._bots_schedule_request("bots.schedule_status")
        # A running forward test advances with the recording: replay what arrived every 30 s.
        if self._bots_ticks % 6 == 0 and self._bots_forward_running:
            self._bots_forward_refresh()
        prog = bots_mod.runtime().progress.get(self._bots_bot)
        if prog and prog.get("fraction", 1) < 1:
            self._bots_status(f"auto-optimize {100 * prog['fraction']:.0f}%: {prog['message']}")

    def _bots_schedule_request(self, name: str, *, show: bool = False) -> None:
        if self._bots_schedule_busy:
            if show:
                self._bots_schedule_pending.append((name, show))
                self.query_one("#bots-schedule-summary", Static).update(Text("Daily optimizer: request queued…"))
            return
        self._bots_schedule_busy = True
        self._bots_schedule_worker(name, show)

    @work(thread=True, group="bots-schedule", exit_on_error=False)
    def _bots_schedule_worker(self, name: str, show: bool) -> None:
        try:
            env = self._call(name, {}, quiet=True)
        except Exception as exc:
            env = {"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}}
        self.call_from_thread(self._bots_schedule_done, name, env, show)

    def _bots_schedule_done(self, name: str, env: dict[str, Any], show: bool) -> None:
        self._bots_schedule_busy = False
        if not self.query("#bots-schedule-summary"):
            return
        if not env.get("ok"):
            text = f"Daily optimizer error: {self._msg(env)}"
        else:
            result = env.get("result") or {}
            def when(value: Any) -> str:
                try:
                    return time.strftime("%Y-%m-%d %H:%M", time.localtime(float(value))) if value else "none"
                except (ValueError, TypeError, OverflowError, OSError):
                    return "unknown"
            current = result.get("current") or {}
            text = (f"Daily optimizer: {result.get('phase', 'unknown')} · enabled {bool(result.get('enabled'))} · "
                    f"last {when(result.get('last_run'))} ({result.get('last_result') or 'none'}) · "
                    f"next {when(result.get('next_run'))} · current {current.get('bot', 'none')} "
                    f"{current.get('coin', '')} · error {result.get('error') or 'none'}")
            if show:
                text += "\n\n" + json.dumps(result, indent=2, default=str)
        self.query_one("#bots-schedule-summary", Static).update(Text(text.split("\n\n", 1)[0]))
        if show:
            self._set_editor_open(True, persist=False)
            self._show_preview("Daily optimizer status", text)
        if self._bots_schedule_pending:
            next_name, next_show = self._bots_schedule_pending.pop(0)
            self._bots_schedule_request(next_name, show=next_show)

    @on(Button.Pressed, "#bots-schedule-start")
    def _bots_schedule_start(self) -> None:
        self._bots_schedule_request("bots.schedule_start", show=True)

    @on(Button.Pressed, "#bots-schedule-stop")
    def _bots_schedule_stop(self) -> None:
        self._bots_schedule_request("bots.schedule_stop", show=True)

    @on(Button.Pressed, "#bots-schedule-status")
    def _bots_schedule_status(self) -> None:
        self._bots_schedule_request("bots.schedule_status", show=True)

    @on(Select.Changed, "#bots-bot")
    def _bots_bot_changed(self, event: Select.Changed) -> None:
        if isinstance(event.value, str) and event.value != self._bots_bot:
            self._bots_fit_generation += 1
            if self._bots_fit_busy:
                self._call("bots.fit_cancel", {"request_id": self._bots_fit_request_id, "interrupted": True}, quiet=True)
            self._bots_bot = event.value
            if self._bots_loaded:
                self._bots_fit_rows.clear()
                self._bots_fit_audits.clear()
                self._bots_fit_origin = None
                self._bots_fit_window_rows.clear()
                self._bots_fit_coin = None
                self._bots_clear("#bots-fit-table", "#bots-fit-windows")
                self.query_one("#bots-fit-equity", Sparkline).data = []
                self.query_one("#bots-fit-hold", Sparkline).data = []
                self.query_one("#bots-fit-curve-context", Static).update("Equity: no selected result.")
                self.query_one("#bots-fit-detail", Static).update("No suitability result for this bot.")
                self.query_one("#bots-fit-selection-summary", Static).update("No suitability result for this bot.")
                self.query_one("#bots-fit-status", Static).update(
                    "Stopping the previous bot's suitability job…" if self._bots_fit_busy else
                    "Coin suitability: rank this bot's coins, then audit a selected row.")
                self._bots_render_selected()

    @on(TabbedContent.TabActivated, "#bots-sections")
    def _bots_section_changed(self, event: TabbedContent.TabActivated) -> None:
        if not self._bots_loaded or event.pane is None:
            return
        picker = self.query_one("#bots-bot", Select)
        if event.pane.id == "bots-sec-council":
            picker.value = "council"
        elif picker.value == "council":
            picker.value = "grid"

    @on(Button.Pressed, "#bots-edit")
    def _bots_edit_settings(self) -> None:
        if self._bots_fit_busy:
            self._bots_status("Wait for the current suitability job before changing settings.")
            return
        bot = self._bots_bot
        coins = ([] if bot == "triangle" else
                 list(dict.fromkeys([*(self._bots_coins or []), *(self._bots_selected or []), self._bots_coin()])))
        asset = self._bots_coin() if bot != "triangle" and len(self._bots_selected) <= 1 else ""

        def fetch(coin: str) -> dict[str, Any]:
            return self._call("bots.config", {"bot": bot, **({"asset": coin} if coin else {})}, quiet=True)

        env = fetch(asset)
        if not env["ok"]:
            self._bots_status(self._msg(env))
            return
        config = env["result"]

        def finished(result: dict[str, Any] | None) -> None:
            if not result:
                return
            if self._bots_bot != bot or self._bots_fit_busy:
                self._bots_status("The bot changed or a suitability job started; no settings were saved.")
                return
            coin = result["asset"]
            payload = {"bot": bot, **({"asset": coin} if coin else {})}
            if result.get("reset"):
                payload["reset"] = True
            else:
                payload.update({key: result[key] for key in ("values", "mode") if key in result})
            if result.get("reset"):
                self._bots_job("bots.save", payload, "restoring global inheritance", "inherit-global")
            else:
                self._bots_job("bots.save", payload, "saving settings")

        self.push_screen(BotSettingsScreen(bot, config["config"], config["defaults"], coins, asset, fetch,
                                           config.get("mode", "auto")), finished)

    @on(Button.Pressed, "#bots-apply")
    def _bots_apply(self) -> None:
        text = self.query_one("#bots-config", Input).value.strip()
        if not text:
            self._bots_status("type settings as name=value pairs first, e.g. " +
                              self.query_one("#bots-config", Input).placeholder)
            return
        self._bots_job("bots.save", {"bot": self._bots_bot, "text": text}, "saving settings")

    @on(Button.Pressed, "#bots-reset")
    def _bots_reset(self) -> None:
        self._bots_job("bots.save", {"bot": self._bots_bot, "reset": True}, "restoring defaults")

    @on(Button.Pressed, "#bots-backtest")
    def _bots_backtest(self) -> None:
        params: dict[str, Any] = {"bot": self._bots_bot, "coins": list(self._bots_selected) or [self._bots_coin()]}
        start = self.query_one("#bots-start", Input).value.strip()
        days = self.query_one("#bots-days", Input).value.strip()
        if start:
            params["start"] = start
        if days:
            try:
                params["days"] = float(days)
            except ValueError:
                self._bots_status(f"days must be a number, got {days!r}")
                return
        n = len(params["coins"])
        label = f"backtesting on {n} coin(s) from " + (params.get("start") or "the beginning of the data")
        log_key = self._start_log("Bot backtest", label)
        self._bots_job("bots.backtest", params, label, log_key)

    @on(Button.Pressed, "#bots-forward-start")
    def _bots_forward_start(self) -> None:
        self._bots_job("bots.forward_start", {"bot": self._bots_bot, "asset": self._bots_coin()},
                       "starting the forward test")

    @on(Button.Pressed, "#bots-forward-stop")
    def _bots_forward_stop(self) -> None:
        self._bots_job("bots.forward_stop", {"bot": self._bots_bot}, "stopping the forward test")

    @on(Button.Pressed, "#bots-forward-refresh")
    def _bots_forward_refresh_pressed(self) -> None:
        self._bots_forward_refresh()

    @on(Button.Pressed, "#bots-workbench")
    def _bots_workbench(self) -> None:
        self.push_screen(ExperimentScreen(self._bots_bot,
                         lambda name, params: self._call(name, params, quiet=True),
                         list(self._bots_selected)))

    @on(Button.Pressed, "#bots-optimize")
    def _bots_optimize(self) -> None:
        """Open the auto-optimize window and start the run; the window follows `bots.progress`."""
        bot = self._bots_bot

        def poll() -> dict[str, Any] | None:
            env = self._call("bots.progress", {"bot": bot}, quiet=True)
            return env["result"] if env["ok"] else None

        bots_mod.runtime().progress.pop(bot, None)
        self._bots_opt_screen = OptimizeScreen(bots_mod.LABELS[bot], poll, GlossaryTable)
        self.push_screen(self._bots_opt_screen)
        log_key = self._start_log("Bot optimize", f"Starting {bot} optimization")
        self._bots_job("bots.optimize", {"bot": bot},
                       "auto-optimizing on every coin (train windows pick, test windows decide)", log_key)

    @on(Button.Pressed, "#bots-coins")
    def _bots_pick_coins(self) -> None:
        """Refresh the coin list, then tick the coins the next backtest runs on."""
        env = self._call("bots.overview", quiet=True)
        if env["ok"] and env["result"]["coins"]:
            self._bots_coins = env["result"]["coins"]

        def chosen(coins: list[str] | None) -> None:
            if coins:
                self._bots_selected = coins
                self._bots_show_coins()
                self._bots_render_config()
            elif coins == []:
                self._bots_status("no coin ticked: the previous choice stays")

        self.push_screen(CoinPickerScreen(self._bots_coins or [self._bots_coin()], self._bots_selected), chosen)

    def _bots_render_many(self, r: dict[str, Any]) -> None:
        """A multi-coin backtest: the per-coin table, then the first run's detail."""
        runs, errors = r.get("runs") or [], r.get("errors") or {}
        self._bots_runs = runs
        table = self.query_one("#bots-bt-coins", DataTable)
        table.clear()
        for row in r.get("summary") or []:
            ret = row.get("total_return")
            table.add_row(row["coin"], row["start"] or "-", row["end"] or "-", self._bots_fmt(row.get("bars")),
                          self._bots_pct(ret) if ret is not None else f"${row.get('pnl_usd') or 0:,.4f}",
                          self._bots_pct(row["hold_return"]) if row.get("hold_return") is not None else "-",
                          self._bots_pct(row["excess_return"]) if row.get("excess_return") is not None else "-",
                          self._bots_pct(row["max_drawdown"]) if row.get("max_drawdown") is not None else "-",
                          self._bots_fmt(row.get("trades")), str(row.get("bridged_bars") or 0),
                          row.get("data_source") or "-", key=row["id"])
        for coin, msg in errors.items():
            table.add_row(coin, "error", msg[:60], "-", "-", "-", "-", "-", "-", "-", "-")
        if runs:
            self._bots_render_backtest(runs[0])
        msg = f"backtest on {r.get('ran', 0)} coin(s): the bot beat buy-and-hold on {r.get('beat_hold', 0)}"
        if errors:
            msg += f"; {len(errors)} could not run ({', '.join(errors)})"
        self._bots_status(msg)

    @on(DataTable.RowSelected, "#bots-bt-coins")
    def _bots_coin_row(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if event.row_key is not None else None
        run = next((x for x in self._bots_runs if x.get("id") == key), None)
        if run is not None:
            self._bots_render_backtest(run)

    def _bots_fit_controls(self) -> None:
        if not self.query("#bots-fit-rank"):
            return
        unsupported = self._bots_bot not in ("grid", "dca")
        selected = self._bots_fit_rows.get(self._bots_fit_coin or "", {})
        bound_data = selected.get("data_sha256")
        self.query_one("#bots-fit-rank", Button).disabled = self._bots_fit_busy or unsupported
        self.query_one("#bots-fit-audit", Button).disabled = (
            self._bots_fit_busy or unsupported or self._bots_fit_coin is None or self._bots_fit_origin is None
            or not isinstance(bound_data, str) or len(bound_data) != 64)
        self.query_one("#bots-fit-cancel", Button).disabled = (
            not self._bots_fit_busy or self._bots_fit_cancelling)
        # A suitability result must correspond to the settings visible when it began.
        for wid in ("#bots-apply", "#bots-edit", "#bots-reset", "#bots-backtest", "#bots-optimize",
                    "#bots-start", "#bots-days", "#bots-config"):
            self.query_one(wid).disabled = self._bots_fit_busy
        if unsupported and not self._bots_fit_busy:
            self.query_one("#bots-fit-status", Static).update(
                "Coin suitability supports Grid and DCA; triangle arbitrage is not a per-coin screen."
                if self._bots_bot == "triangle" else
                "Coin suitability supports Grid and DCA. Use Trend's own testing controls.")

    def _bots_fit_signature(self) -> tuple:
        return (self._bots_bot, repr(self.settings),
                self.query_one("#bots-start", Input).value,
                self.query_one("#bots-days", Input).value,
                json.dumps(bots_mod.get_config(self._bots_bot), sort_keys=True))

    def _bots_fit_begin(self, mode: str) -> None:
        if self._bots_fit_busy:
            return
        if self._bots_bot == "triangle":
            self._bots_fit_controls()
            return
        opt = bots_mod.runtime().progress.get(self._bots_bot)
        if opt and not opt.get("done") and opt.get("fraction", 1) < 1:
            self.query_one("#bots-fit-status", Static).update(
                "Wait for auto-optimize to finish before screening its configuration.")
            return
        params: dict[str, Any] = {"bot": self._bots_bot}
        name = "bots.rank_coins" if mode == "quick" else "bots.audit_coin"
        if mode == "quick":
            params["coins"] = "all"
        elif self._bots_fit_coin is not None:
            params["asset"] = self._bots_fit_coin
        else:
            self.query_one("#bots-fit-status", Static).update("Rank coins and select a row before auditing.")
            return
        start = self.query_one("#bots-start", Input).value.strip()
        days = self.query_one("#bots-days", Input).value.strip()
        if start:
            params["start"] = start
        if days:
            try:
                params["days"] = float(days)
                if not math.isfinite(params["days"]) or params["days"] <= 0:
                    raise ValueError
            except ValueError:
                self.query_one("#bots-fit-status", Static).update("Days must be a finite positive number.")
                return
        if mode == "audit":
            origin = self._bots_fit_origin
            if not origin or not isinstance(origin.get("config"), dict) or not isinstance(origin.get("policy"), dict):
                self.query_one("#bots-fit-status", Static).update("Run a quick ranking before auditing its selected coin.")
                return
            for key in ("common_start", "common_end", "fee_bps", "slippage_bps", "capital_usd"):
                if not isinstance(origin.get(key), (int, float)):
                    self.query_one("#bots-fit-status", Static).update(f"Quick ranking did not bind {key}; rank again before auditing.")
                    return
            params.update(start=str(origin["common_start"]), reference_end=origin["common_end"],
                          days=(origin["common_end"] - origin["common_start"]) / 86400,
                          config=copy.deepcopy(origin["config"]), fee_bps=origin["fee_bps"],
                          slippage_bps=origin["slippage_bps"], capital=origin["capital_usd"],
                          policy=copy.deepcopy(origin["policy"]))
            selected = self._bots_fit_rows[self._bots_fit_coin]
            if not selected.get("data_sha256"):
                self.query_one("#bots-fit-status", Static).update("Selected quick row has no data fingerprint; rank again after resolving its data error.")
                return
            params["expected_data_sha256"] = selected["data_sha256"]
            if origin.get("selection_id"):
                params["selection_id"] = origin["selection_id"]
        try:
            signature = self._bots_fit_signature()
        except (bots_mod.BotError, OSError, ValueError) as exc:
            self.query_one("#bots-fit-status", Static).update(f"Cannot read the current bot settings: {exc}")
            return
        frozen = Context.from_settings(copy.deepcopy(self.settings), self.ctx.runtime)
        self._bots_fit_generation += 1
        token = self._bots_fit_generation
        self._bots_fit_active_token = token
        self._bots_fit_request_id = uuid.uuid4().hex
        params["request_id"] = self._bots_fit_request_id
        self._bots_fit_busy, self._bots_fit_cancelling = True, False
        self._bots_fit_drained.clear()
        self._bots_fit_alive.set()
        self._bots_fit_controls()
        self.query_one("#bots-sections", TabbedContent).active = "bots-sec-fit"
        self.query_one("#bots-fit-status", Static).update(
            "Running quick heuristic ranking…" if mode == "quick" else f"Auditing {self._bots_fit_coin} across windows and stressed costs…")
        self._bots_fit_timer = self.set_interval(0.25, self._bots_fit_poll)
        self._bots_fit_worker_handle = self._bots_fit_worker(token, self._bots_bot, signature, name, params, frozen)

    @work(thread=True, exit_on_error=False, group="coin-suitability")
    def _bots_fit_worker(self, token: int, bot: str, signature: tuple, name: str,
                         params: dict[str, Any], context: Context) -> None:
        try:
            envelope = dispatch(name, params, surface="tui", ctx=context)
        except Exception as exc:  # noqa: BLE001 - dispatch failures still need a terminal UI state
            envelope = {"ok": False, "error": {"message": f"{type(exc).__name__}: {exc}"}, "result": None}
        finally:
            self._bots_fit_drained.set()
        if self._bots_fit_alive.is_set():
            self.post_message(CoinFitFinished(token, bot, signature, envelope))

    def _bots_fit_poll(self) -> None:
        if not self._bots_fit_busy or not self._bots_fit_alive.is_set():
            return
        env = self._call("bots.fit_status", quiet=True)
        state = env.get("result") if env.get("ok") else None
        if not state or state.get("bot") != self._bots_bot:
            return
        status = state.get("status", "running")
        self.query_one("#bots-fit-status", Static).update(
            f"{state.get('mode', 'quick')} · {status} · {100 * state.get('fraction', 0):.0f}%: {state.get('message', '')}")

    @on(CoinFitFinished)
    def _bots_fit_finished(self, event: CoinFitFinished) -> None:
        if not self._bots_fit_alive.is_set() or event.token != self._bots_fit_active_token:
            return
        self._bots_fit_busy = False
        self._bots_fit_active_token = None
        if self._bots_fit_timer is not None:
            self._bots_fit_timer.stop()
            self._bots_fit_timer = None
        self._bots_fit_controls()
        try:
            signature_matches = event.signature == self._bots_fit_signature()
        except (bots_mod.BotError, OSError, ValueError):
            signature_matches = False
        if (event.token != self._bots_fit_generation or event.bot != self._bots_bot or not signature_matches):
            self.query_one("#bots-fit-status", Static).update(
                "Inputs changed; the previous suitability result was discarded. Rank again with the current inputs.")
            return
        env = event.envelope
        if not env.get("ok"):
            self.query_one("#bots-fit-status", Static).update(f"Suitability job failed: {self._msg(env)}")
            return
        try:
            self._bots_fit_render(env["result"])
        except (KeyError, TypeError, ValueError) as exc:
            self.query_one("#bots-fit-status", Static).update(f"Suitability job returned an invalid report: {exc}")

    @on(Button.Pressed, "#bots-fit-rank")
    def _bots_fit_rank(self) -> None:
        self._bots_fit_begin("quick")

    @on(Button.Pressed, "#bots-fit-audit")
    def _bots_fit_audit(self) -> None:
        self._bots_fit_begin("audit")

    @on(Button.Pressed, "#bots-fit-cancel")
    def _bots_fit_cancel(self) -> None:
        if self._bots_fit_busy:
            self._bots_fit_cancelling = True
            self._call("bots.fit_cancel", {"request_id": self._bots_fit_request_id})
            self.query_one("#bots-fit-status", Static).update(
                "Cancelling after the current bounded simulation window; completed rows will be retained.")
            self._bots_fit_controls()

    @staticmethod
    def _bots_fit_date(value: Any) -> str:
        if isinstance(value, (int, float)):
            return time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(value))
        return str(value) if value is not None else "-"

    def _bots_fit_render(self, report: dict[str, Any]) -> None:
        if not isinstance(report, dict) or not isinstance(report.get("rows"), list):
            raise TypeError("expected a report with a rows list")
        rows = [dict(row) for row in report["rows"]]
        if any(not isinstance(row.get("coin"), str) for row in rows):
            raise ValueError("every row needs a coin identifier")
        known = {row["coin"] for row in rows}
        for coin, error in (report.get("errors") or {}).items():
            if coin not in known:
                rows.append({"coin": coin, "fit": "ERROR", "reason": str(error), "metrics": {}})
        if report.get("mode") == "audit" and self._bots_fit_origin is not None:
            self._bots_fit_audits.update({row["coin"]: row for row in rows})
        elif rows or not report.get("cancelled"):
            self._bots_fit_rows = {row["coin"]: row for row in rows}
            self._bots_fit_origin = report
            self._bots_fit_audits.clear()
        table = self.query_one("#bots-fit-table", DataTable)
        table.clear()
        origin = self._bots_fit_origin or report
        for row in self._bots_fit_rows.values():
            metrics = row.get("metrics") or {}
            windows = row.get("windows") or []
            span = (f"{self._bots_fit_date(origin.get('common_start'))} → "
                    f"{self._bots_fit_date(origin.get('common_end'))}")
            if windows:
                span = f"{len(windows)} window(s); {self._bots_fit_date(windows[0].get('start'))}"
            def pct(key, values=metrics):
                return self._bots_pct(values[key]) if values.get(key) is not None else "-"
            table.add_row(row["coin"], str(row.get("fit", row.get("status", "-"))),
                          str(self._bots_fit_audits.get(row["coin"], {}).get("fit", "-")),
                          self._bots_fmt(row.get("score")), pct("total_return"), pct("excess_return"),
                          pct("max_drawdown"), self._bots_fmt(metrics.get("cycles")), span,
                          str(row.get("reason") or "; ".join(row.get("reasons") or [])), key=row["coin"])
        if self._bots_fit_coin not in self._bots_fit_rows:
            self._bots_fit_coin = next(iter(self._bots_fit_rows), None)
        if self._bots_fit_coin is not None:
            self._bots_fit_show(self._bots_fit_coin)
        else:
            self._bots_clear("#bots-fit-windows")
            self.query_one("#bots-fit-equity", Sparkline).data = []
            self.query_one("#bots-fit-hold", Sparkline).data = []
            self.query_one("#bots-fit-curve-context", Static).update("Equity: no selected result.")
            self.query_one("#bots-fit-detail", Static).update("No completed coin rows.")
            self.query_one("#bots-fit-selection-summary", Static).update("No completed coin rows.")
        terminal = "Interrupted" if report.get("interrupted") else "Cancelled" if report.get("cancelled") else "Completed"
        notes = "; ".join(str(n) for n in report.get("notes") or [])
        target = " on " + ", ".join(row["coin"] for row in rows) if report.get("mode") == "audit" else ""
        self.query_one("#bots-fit-status", Static).update(
            f"{terminal} {report.get('mode', 'quick')} suitability{target}: {len(rows)} row(s). "
            f"Fees {self._bots_fmt(report.get('fee_bps'))} bps; slippage {self._bots_fmt(report.get('slippage_bps'))} bps. "
            f"Quick ranks are provisional; no settings were adopted. {notes}")
        self._bots_fit_controls()

    def _bots_fit_show(self, coin: str) -> None:
        row = self._bots_fit_audits.get(coin) or self._bots_fit_rows.get(coin)
        if row is None:
            return
        self._bots_fit_coin = coin
        failures = [str(v) for v in row.get("failures") or []]
        supporting = [str(v) for v in row.get("reasons") or []]
        reasons = list(dict.fromkeys([*failures, *supporting])) or [row.get("reason") or "No reason supplied"]
        missing = row.get("missing_evidence") or []
        metrics = row.get("metrics") or {}
        lead = failures[0] if failures else (str(missing[0]) if missing and row.get("fit") == "INSUFFICIENT_DATA" else str(reasons[0]))
        self.query_one("#bots-fit-selection-summary", Static).update(
            f"{coin}: {row.get('fit', row.get('status', '-'))}. "
            f"{lead[:180]}. "
            f"{len(missing)} evidence limitation(s); complete reasoning and template below.")
        lines = [f"{coin}: {row.get('fit', row.get('status', '-'))}; score {self._bots_fmt(row.get('score'))}",
                 "Verdict basis: " + str(row.get("reason") or "; ".join(reasons)),
                 "Failed checks: " + ("; ".join(failures) if failures else "none reported"),
                 "Supporting checks: " + ("; ".join(supporting) if supporting else "none reported"),
                 "Missing evidence: " + ("; ".join(str(v) for v in missing) if missing else "none reported"),
                 "Full-account metrics:"]
        lines += [f"  {key}: {self._bots_fmt(value)}" for key, value in metrics.items()]
        if self._bots_fit_origin is not None:
            lines.append("Selection settings (audit stays pinned to these): " +
                         json.dumps(self._bots_fit_origin.get("config") or {}, sort_keys=True))
            lines.append("Selection window: " + self._bots_fit_date(self._bots_fit_origin.get("common_start")) +
                         " → " + self._bots_fit_date(self._bots_fit_origin.get("common_end")))
            if self._bots_fit_origin.get("score_formula"):
                lines.append("Heuristic score: " + str(self._bots_fit_origin["score_formula"]))
            if self._bots_fit_origin.get("policy"):
                lines.append("Heuristic policy: " + json.dumps(self._bots_fit_origin["policy"], sort_keys=True))
        for field in row.get("template") or []:
            if isinstance(field, dict):
                lines.append(f"{field.get('metric', field.get('field', '-'))}: {field.get('status', field.get('state', '-'))} · "
                             f"{field.get('reason', '')}; value={self._bots_fmt(field.get('value'))}; "
                             f"basis={field.get('basis', '-')}")
        self.query_one("#bots-fit-detail", Static).update("\n".join(lines))
        curve = row.get("equity") or []
        self.query_one("#bots-fit-equity", Sparkline).data = [float(p[1]) for p in curve if len(p) >= 3]
        self.query_one("#bots-fit-hold", Sparkline).data = [float(p[2]) for p in curve if len(p) >= 3]
        self.query_one("#bots-fit-curve-context", Static).update(
            f"Equity: {coin} · {'audited continuous full account' if coin in self._bots_fit_audits else 'quick development window'}")
        table = self.query_one("#bots-fit-windows", DataTable)
        table.clear()
        self._bots_fit_window_rows.clear()
        for i, window in enumerate(row.get("windows") or []):
            m = window.get("metrics") or {}
            def pct(key, values=m):
                return self._bots_pct(values[key]) if values.get(key) is not None else "-"
            key = f"{coin}:{i}"
            self._bots_fit_window_rows[key] = window
            table.add_row(str(window.get("label", "-")), self._bots_fit_date(window.get("start")),
                          self._bots_fit_date(window.get("end")), self._bots_fmt(window.get("stress")),
                          pct("total_return"), pct("hold_return"), pct("excess_return"), pct("max_drawdown"),
                          self._bots_fmt(m.get("cycles")), self._bots_fmt(m.get("costs_usd")), key=key)
        self._bots_fit_controls()

    @on(DataTable.RowSelected, "#bots-fit-table")
    def _bots_fit_row_selected(self, event: DataTable.RowSelected) -> None:
        coin = event.row_key.value if event.row_key is not None else None
        if coin is not None:
            self._bots_fit_show(str(coin))

    @on(DataTable.RowSelected, "#bots-fit-windows")
    def _bots_fit_window_selected(self, event: DataTable.RowSelected) -> None:
        key = event.row_key.value if event.row_key is not None else None
        window = self._bots_fit_window_rows.get(str(key))
        if window is None:
            return
        curve = window.get("equity") or []
        self.query_one("#bots-fit-equity", Sparkline).data = [float(p[1]) for p in curve if len(p) >= 3]
        self.query_one("#bots-fit-hold", Sparkline).data = [float(p[2]) for p in curve if len(p) >= 3]
        self.query_one("#bots-fit-curve-context", Static).update(
            f"Equity: {self._bots_fit_coin} · {window.get('label', '-')} · "
            f"{self._bots_fit_date(window.get('start'))} → {self._bots_fit_date(window.get('end'))}")

    ROSTER_PICK = "__roster__"

    def action_batch_everything(self) -> None:
        self._batch_request("default")

    @on(Button.Pressed, "#batch-status")
    def _batch_status_pressed(self) -> None:
        self._batch_request("status")

    @on(Button.Pressed, "#batch-resume")
    def _batch_resume_pressed(self) -> None:
        self._batch_request("resume")

    @on(Button.Pressed, "#batch-stop")
    def _batch_stop_pressed(self) -> None:
        self._batch_request("stop")

    @on(Button.Pressed, "#batch-fresh")
    def _batch_fresh_pressed(self) -> None:
        self._batch_request("fresh")

    def _batch_poll(self) -> None:
        if self._batch_id and not self._batch_busy:
            self._batch_request("poll")

    def _batch_request(self, action: str) -> None:
        if self._batch_busy:
            if action not in ("discover", "poll"):
                self.notify("A batch status or start operation is already in progress.", severity="warning")
            return
        self._batch_busy = True
        self._batch_worker(action, self._batch_id)

    @work(thread=True, exit_on_error=False, group="all-market-batch")
    def _batch_worker(self, action: str, run_id: str | None) -> None:
        message = ""
        status: dict[str, Any] | None = None
        try:
            def call(name: str, params: dict[str, Any] | None = None) -> Any:
                env = self._call(name, params or {}, quiet=True)
                if not env.get("ok"):
                    raise ValueError(self._msg(env))
                return env["result"]

            if action in ("discover", "default", "fresh") or not run_id:
                runs = call("batch.list")["runs"]
                active = next((row for row in runs if row.get("running")), None)
                chosen = active or (runs[0] if runs else None)
                run_id = str(chosen["run_id"]) if chosen else None
                if action == "fresh" and active:
                    message = "A batch is already running; stop it before starting a separate batch."
                elif action == "fresh" or (action == "default" and not chosen):
                    created = call("batch.create")
                    run_id = str(created["run_id"])
                    message = "Batch created; starting the worker."
                    call("batch.start", {"run_id": run_id})
            if run_id and action == "resume":
                prior = call("batch.status", {"run_id": run_id})
                if prior.get("running"):
                    message = "The selected batch is already running."
                else:
                    call("batch.start", {"run_id": run_id})
                    message = "Resume requested for the saved batch."
            elif run_id and action == "stop":
                stopped = call("batch.stop", {"run_id": run_id})
                message = ("Stopping this batch after its current work finishes." if stopped.get("stopping")
                           else "This batch is not running. " + str(stopped.get("error") or ""))
            if run_id:
                status = call("batch.status", {"run_id": run_id})
                shown = {row.get("state") for row in status.get("problems") or []}
                extra = []
                if action not in ("discover", "poll"):
                    for state in ("failed", "missing", "unsupported", "partial"):
                        if (status.get("counts") or {}).get(state, 0) and state not in shown:
                            extra.extend(call("batch.cells", {"run_id": run_id, "state": state, "limit": 3})["rows"])
                status["representative_problems"] = extra
            elif action not in ("discover", "poll"):
                message = "No saved batch. Press F5 to create one."
        except Exception as exc:  # noqa: BLE001 - preserve the run id if creation or start failed
            message = f"Batch operation failed: {type(exc).__name__}: {exc}"
        try:
            self.call_from_thread(self._batch_done, action, run_id, status, message)
        except RuntimeError:
            pass

    def _batch_done(self, action: str, run_id: str | None, status: dict[str, Any] | None, message: str) -> None:
        self._batch_busy = False
        if not self.query("#batch-summary"):
            return
        if run_id:
            self._batch_id = run_id
        lines = []
        if message:
            lines.append(message)
        if run_id and not status:
            lines.append(f"Saved batch: {run_id}. Use Batch status or Resume batch to recover it.")
        if status:
            counts = status.get("counts") or {}
            lines.append(f"Batch {status.get('run_id')} · {status.get('phase')} · "
                         f"{'running' if status.get('running') else 'not running'}")
            lines.append("Open Batch status, Resume, Stop, or Start fresh on the Backtest tab.")
            lines.append("Cells: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                         + f" · total={status.get('total', 0)}")
            universe = status.get("universe") or {}
            if universe:
                lines.append(f"Market universe: {universe.get('selection') or universe.get('source', '-')} · "
                             f"eligible={universe.get('eligible', '-')} · excluded={universe.get('excluded', {})}")
            if status.get("current"):
                lines.append(f"Current: {status['current']}")
            if status.get("error"):
                lines.append(f"Error: {status['error']}")
            for row in (status.get("problems") or []) + (status.get("representative_problems") or []):
                lines.append(f"{row['state']}: {row['asset']} {row['interval']} {row['strategy']} "
                             f"{row['horizon']} — {row['reason']}")
            if status.get("problems_truncated"):
                lines.append("Only the first 100 problem cells and representative missing states are shown; "
                             "use batch.cells to page through the full ledger.")
            checks = status.get("forward_checks") or []
            lines.append(f"Forward checks: {len(checks)}; backlog: {status.get('forward_backlog', {})}")
            for row in checks:
                if row.get("error"):
                    lines.append(f"Forward error: {row.get('asset')} {row.get('interval')}: {row['error']}")
            if status.get("notice"):
                lines.append(str(status["notice"]))
            if status.get("log"):
                lines.append(f"Worker log: {status['log']}")
        text = "\n".join(lines) or "No saved batch. Press F5 to create one."
        self.query_one("#batch-summary", Static).update(text.split("\n")[0])
        if action not in ("discover", "poll"):
            self._batch_log_key = self._start_log("All-market batch", text)
        elif action == "poll" and text != self._batch_last_summary and self._batch_log_key:
            self._append_log(self._batch_log_key, text)
        self._batch_last_summary = text

    def _backtest_pane(self) -> ComposeResult:
        """Run a CPCV sweep over the roster (or one roster strategy) and show the distribution."""
        with VerticalScroll():
            yield Static(
                "Pick what Run backtest tests: the whole roster, or one strategy from it. The roster is "
                "the right-hand list on the Strategies tab (Add selected / Remove selected change it). "
                "CPCV evaluates each strategy across C(blocks,k) regime-mixed paths, not one split; read "
                "IQR and % paths positive, not just the median.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Label("Strategy to backtest:")
                yield Select([("Whole roster", self.ROSTER_PICK)], value=self.ROSTER_PICK,
                             allow_blank=False, id="backtest-pick")
                yield Static("", id="backtest-roster")
            yield from self._simulation_controls("backtest")
            yield Checkbox("Use longest continuous window if history has gaps", value=False, id="backtest-longest-contiguous")
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-backtest")
                yield Button("Run backtest (r)", variant="primary", id="btn-run")
                yield Button("Backtest untested + little-tested", variant="warning", id="btn-run-untested")
                yield Button("Cancel (c)", variant="error", id="btn-cancel")
                yield Static("", id="backtest-status")
            with Horizontal(classes="form-row"):
                yield Button("Batch status", id="batch-status")
                yield Button("Resume batch", id="batch-resume")
                yield Button("Stop batch", id="batch-stop", variant="error")
                yield Button("Start fresh batch", id="batch-fresh")
            yield Static("F5: backtest eligible Coinbase USD markets, then begin paper forward tests.", id="batch-summary")
            yield Static("", id="backtest-bg-status")
            yield Static("[b]CPCV results[/b], latest Run backtest: one row per strategy, best median Sharpe "
                         "first. Sharpe, net return and trades are medians across the held-out paths; IQR is "
                         "their spread and % paths + the share that made money.", classes="table-title")
            yield ExportPanel(GlossaryTable(id="results-table"))

    def _live_run_pane(self) -> ComposeResult:
        """Choose a real registered strategy for a historical, no-order simulation."""
        with Vertical():
            yield Static("DRY RUN — HISTORICAL SIMULATION; NO ORDERS", id="live-run-banner")
            yield Static("Choose any registered strategy or a Top 5 preset, then press Start dry run. "
                         "The simulation uses cached candles and Settings costs; it is not live paper trading "
                         "or evidence that a strategy will be profitable.", classes="hint")
            yield from self._preset_list("live")
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-live")
                yield Label("Registered strategy:")
                yield Select([(name, name) for name, _ in available_strategies()], value="buy_and_hold",
                             allow_blank=False, id="live-run-choice")
                yield Button("Start dry run", variant="success", id="btn-spawn-dryrun")
            with Horizontal(classes="form-row"):
                yield Label("Selected:")
                yield Input(value="buy_and_hold", id="live-run-strategy")
                yield Button("Refresh", id="btn-refresh-live-run")
            yield Static("Choose a strategy and press Start dry run.", id="live-run-recommendation")
            yield Static("No dry run started.", id="live-run-status")
            yield TextArea(read_only=True, id="live-run-output")

    def _execute_pane(self) -> ComposeResult:
        """Dry-run replay. The banner is not decoration."""
        with Vertical():
            yield Static(MODE_LABEL, id="execute-banner")
            yield Static(
                "This replays a historical simulation bar by bar and shows the fills "
                "a strategy WOULD have made. This replay does not place orders or use signing keys.",
                classes="hint",
            )
            yield from self._preset_list("exec")
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-paper")
                yield Label("Strategy:")
                yield Select([], id="exec-strategy", allow_blank=True)
                yield Button("Start dry run", variant="primary", id="btn-paper-start")
            with Horizontal(classes="form-row"):
                yield Button("Step +1", id="btn-step1")
                yield Button("Step +25", id="btn-step25")
                yield Button("To end", id="btn-step-end")
                yield Button("Reset", id="btn-paper-reset")
            yield Static("No dry run started.", id="exec-summary")
            yield Static("[b]Dry-run fills[/b]: every simulated fill so far, newest last: bar, time, side, "
                         "reason, price, units, cost and equity after. Nothing here was sent to a venue.", classes="table-title")
            yield ExportPanel(GlossaryTable(id="fills-table"))

    # -- lifecycle -------------------------------------------------------

    def on_mount(self) -> None:
        """Populate tables and start the indicator refresh."""
        if not self.is_headless:
            from . import prediction_recovery
            self._prediction_console_handle = prediction_recovery.register_console()
        self._bots_fit_alive.set()
        avail = self.query_one("#available-table", DataTable)
        for label in ("strategy", "family", "status", "in roster", "tested", "times tested", "last tested", "card-preset result"):
            avail.add_column(label, key=label)
        avail.cursor_type = "row"
        self._load_strategy_cards()
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
        self._wallet_restore()
        self.set_interval(self.settings.poll_interval_seconds, self._tick)
        self.set_interval(liq.REFRESH_SECONDS, self._liq_tick)
        self.set_interval(1, self._signal_live_tick)
        self._signal_live_prediction_timer = self.set_interval(10, self._signal_live_poll_predictions)
        if self._signal_auto_recovery_allowed():
            self._signal_live_request_recovery(startup=True)
        self._forward_controls()
        self.set_interval(5, self._forward_schedule)
        self.set_interval(5, self._advanced_context_tick)
        self.set_interval(5, self._batch_poll)
        self._batch_request("discover")
        self.set_interval(15, self._paper_exp_tick)
        self._refresh_liquidity(force=True)
        self._compound_setup()
        self.set_interval(5, self._bots_tick)
        if self._stream_prices:
            self._bots_job("prices.ensure", {}, "starting the price recorder")
        self._install_help()
        self._apply_ui_state()
        # After the saved editor state: Now hides the editor, and that must not be undone by it.
        self._v2_setup()

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
        self.push_screen(HelpScreen(self._focused_help_text()))

    def _focused_help_text(self) -> str:
        """What F1 and the v2 Explain drawer show: the focused field, else the current tab."""
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
        return text

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
        self._poll_backtest_log()

    def _poll_queue(self) -> None:
        """Redraw the Queue tab only when the worker actually wrote something.

        Stat, compare, and usually return: the worker is a separate process whose results file
        changes at the pace of a CPCV evaluation, so a full `queue.status` on every tick would be
        work for nothing. The cheap `queue.progress` keeps the status line live; polling is not
        logged (only calls somebody asked for are).
        """
        if not self.query("#queue-status"):
            return
        self._show_bg_progress()
        path = bgqueue.active_results_path()
        if (path, _mtime(path)) != self._queue_mtime:
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
            "leverage": float, "min_confidence": float,
            "borrow_long_bps_hour": float, "borrow_short_bps_hour": float,
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
        for name in ("use_leverage", "allow_short"):
            out[name] = self.query_one(f"#set-{name}", Checkbox).value
        out["interval"] = str(self.query_one("#set-interval", Select).value)
        if self.query("#set-forwardtest_autostart"):
            out["forwardtest_autostart"] = bool(self.query_one("#set-forwardtest_autostart", Checkbox).value)
        return out

    # -- roster ----------------------------------------------------------

    def _load_strategy_cards(self) -> None:
        env = self._call("strategies.cards", quiet=True)
        if not env["ok"]:
            self.query_one("#strategy-card-count", Static).update(self._msg(env))
            return
        self._strategy_card_catalog = env["result"]
        self._strategy_cards = {row["key"]: row for row in env["result"]["cards"]}
        self._render_strategy_cards()

    def _render_strategy_cards(self) -> None:
        table = self.query_one("#available-table", DataTable)
        if not table.columns or not hasattr(self, "_strategy_cards"):
            return
        query = self.query_one("#strategy-card-filter", Input).value.casefold().strip()
        scope = self.query_one("#strategy-card-scope", Select).value
        roster_names = {entry.name for entry in self.roster}
        table.clear()
        for key, card in self._strategy_cards.items():
            if scope == "registered" and not card["registered"]:
                continue
            if scope == "spec-only" and card["status"] != "spec-only":
                continue
            if scope == "tradingview" and not card["id"].startswith("tv_"):
                continue
            if query and query not in " ".join(str(card[k]) for k in ("key", "name", "family", "summary")).casefold():
                continue
            status = "specification" if card["status"] == "spec-only" else card["status"]
            if not card["data_available"]:
                status += " · data needed"
            result = "Implementation required" if card["status"] == "spec-only" else "Use the card's runner"
            table.add_row(Text(key if card["registered"] else card["name"]), card["family"], status,
                          "yes" if key in roster_names else "", "…" if card["registered"] else "n/a",
                          "", "", "" if card["registered"] else result, key=key)
        catalog = self._strategy_card_catalog
        self.query_one("#strategy-card-count", Static).update(
            f"{table.row_count} of {catalog['count']} active cards · {catalog['registered']} registered strategies · "
            "guides, templates and research excluded")
        self._apply_strategy_history()
        self._update_strategy_actions()

    @on(Input.Changed, "#strategy-card-filter")
    @on(Select.Changed, "#strategy-card-scope")
    def _strategy_card_filter_changed(self) -> None:
        self._render_strategy_cards()

    @on(Button.Pressed, "#strategy-cards-refresh")
    def _strategy_cards_refresh(self) -> None:
        self._load_strategy_cards()
        self._refresh_strategy_history()

    @staticmethod
    def _strategy_table_key(table: DataTable) -> str:
        row_key, _ = table.coordinate_to_cell_key(table.cursor_coordinate)
        return str(row_key.value)

    def _update_strategy_actions(self, key: str | None = None) -> None:
        if not self.query("#btn-add"):
            return
        if key is None:
            if not self.query("#available-table"):
                return
            table = self.query_one("#available-table", DataTable)
            key = self._strategy_table_key(table) if table.row_count else ""
        card = getattr(self, "_strategy_cards", {}).get(key, {})
        self.query_one("#btn-add", Button).disabled = not card.get("registered", False)
        if self.query("#btn-bt-selected"):
            self.query_one("#btn-bt-selected", Button).disabled = not card.get("testable", False)

    def _registered_card_selected(self, key: str) -> bool:
        card = getattr(self, "_strategy_cards", {}).get(key, {})
        if card.get("registered", False):
            return True
        message = ("This specification needs an implementation before backtesting. Read its card below."
                   if card.get("status") == "spec-only" else
                   "This card uses a separate runner. Read its card below; this roster accepts registered strategies only.")
        self.query_one("#roster-status", Static).update(message)
        return False

    def _refresh_strategy_history(self) -> None:
        """Fill the Strategies table's test-history columns from `strategies.history`.

        Cells are updated in place by row and column key, so the cursor, the sort order and the
        highlighted row (which opens that strategy's source) all survive a refresh.
        """
        env = self._call("strategies.history", quiet=True)
        status = self.query_one("#history-status", Static)
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        r = env["result"]
        self._strategy_history_rows = r["rows"]
        self._apply_strategy_history()
        note = (f"{r['asset']}: {r['tested']} tested, {r['untested']} untested "
                "(background sweep results; the Queue tab shows the full leaderboard)")
        action = getattr(self, "_history_action", "")
        status.update(f"{action}\n{note}" if action else note)

    def _apply_strategy_history(self) -> None:
        table = self.query_one("#available-table", DataTable)
        for row in getattr(self, "_strategy_history_rows", []):
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

    def _start_backtest(self, scope: str, names: list[str] | None = None) -> None:
        """Run `queue.backtest` and say what happened where the user is looking."""
        self.query_one("#history-status", Static)
        params: dict[str, Any] = {"scope": scope}
        if names is not None:
            params["names"] = names
        self._close_finished_worker_logs()
        tail = BacktestLog(bgqueue.BG_DIR / "worker.log")
        env = self._call("queue.backtest", params)
        self._start_log("Strategy backtest", self._msg(env) if not env["ok"] else env["result"]["message"],
                        tail if env["ok"] and env["result"].get("started") else None)
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
            name = self._strategy_table_key(table)
        except Exception:  # noqa: BLE001 - nothing highlighted
            self.query_one("#history-status", Static).update("[red]highlight a strategy first[/]")
            return
        if self._registered_card_selected(name):
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
        entries = self._call("roster.list")["result"]["entries"]
        names = {e["name"] for e in entries}
        available = self.query_one("#available-table", DataTable)
        for row_key in tuple(available.rows):
            available.update_cell(row_key, "in roster", "yes" if row_key.value in names else "")
        for e in entries:
            t.add_row(e["label"], e["family"], str(e["warmup"]), key=e["label"])

    def _refresh_exec_choices(self) -> None:
        """Keep the Execute and Backtest strategy pickers in sync with the roster."""
        sel = self.query_one("#exec-strategy", Select)
        labels = [e["label"] for e in self._call("roster.list")["result"]["entries"]]
        pick = self.query_one("#backtest-pick", Select)
        keep = pick.value
        pick.set_options([(f"Whole roster ({len(labels)} strategies)", self.ROSTER_PICK)]
                         + [(label, label) for label in labels])
        pick.value = keep if keep in labels else self.ROSTER_PICK
        shown = ", ".join(labels[:8]) + (f" +{len(labels) - 8} more" if len(labels) > 8 else "")
        self.query_one("#backtest-roster", Static).update(
            Text(f"roster: {shown}" if labels else "roster is empty: add strategies on the Strategies tab"))
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

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if event.key != "space" or not isinstance(focused, DataTable):
            return
        if focused.id not in ("available-table", "roster-table") or not focused.row_count:
            return
        event.stop()
        event.prevent_default()
        if focused.id == "roster-table":
            self._remove()
            return
        status = self.query_one("#roster-status", Static)
        try:
            name = self._strategy_table_key(focused)
            params = self._parse_params()
        except (RosterError, IndexError) as exc:
            status.update(Text(str(exc)))
            return
        if not self._registered_card_selected(name):
            return
        env = self._call("roster.toggle", {"name": name, "params": params})
        if not env["ok"]:
            status.update(Text(self._msg(env)))
            return
        self._refresh_roster_table()
        self._refresh_exec_choices()
        result = env["result"]
        action = "added" if "added" in result else "removed"
        status.update(Text(f"{action} {result[action]['label']}"))

    @on(Button.Pressed, "#btn-roster-all")
    def _roster_all(self) -> None:
        env = self._call("roster.add_all")
        status = self.query_one("#roster-status", Static)
        if not env["ok"]:
            status.update(Text(self._msg(env)))
            return
        self._refresh_roster_table()
        self._refresh_exec_choices()
        result = env["result"]
        status.update(Text(f"Added {len(result['added'])}; {result['count']} configurations in the roster."))

    @on(Button.Pressed, "#btn-add")
    def _add(self) -> None:
        """Add the highlighted available strategy to the roster."""
        status = self.query_one("#roster-status", Static)
        table = self.query_one("#available-table", DataTable)
        try:
            name = self._strategy_table_key(table)
            explicit = self._parse_params()
        except Exception as exc:  # noqa: BLE001
            status.update(f"[red]{exc}[/]")
            return
        if not self._registered_card_selected(name):
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
        card = getattr(self, "_strategy_cards", {}).get(name)
        rel = card["path"] if card else self._strategy_source_path(name)
        if rel is None:
            if self.query("#docs-view-status"):
                self.query_one("#docs-view-status", Static).update(
                    f"{name}: source file not in the Docs catalogue")
            return
        self._open_doc(rel)

    @on(DataTable.RowSelected, "#available-table")
    @on(DataTable.RowHighlighted, "#available-table")
    def _available_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        try:
            if event.row_key not in event.data_table.rows:
                return
            name = str(event.row_key.value)
        except Exception:  # noqa: BLE001 - an empty table has no row to open
            return
        self._update_strategy_actions(name)
        if isinstance(event, DataTable.RowSelected):
            self._set_editor_open(True, persist=False)
        self._open_strategy_file(name)

    @on(DataTable.RowSelected, "#roster-table")
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
            if isinstance(event, DataTable.RowSelected):
                self._set_editor_open(True, persist=False)
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

    def _initial_coin(self) -> str:
        a = (self.settings.asset or "SOL").upper()
        return a if a in compound_mod.coins() else "SOL"

    def _compound_setup(self) -> None:
        self._compound_coin = self._initial_coin()
        self._compound_scope = "all"
        self._compound_cfg: dict[str, Any] = sc.default_config()
        self._compound_live: dict[str, str] = {}
        self._compound_learned: dict[str, str] = {}
        self._compound_tuned: dict[str, dict[str, Any]] = {}
        self._compound_bt: dict[str, str] = {}
        self._compound_fwd: dict[str, str] = {}
        self._compound_auto = False
        self._compound_last_bar = 0
        self._compound_last_minute = 0
        self._compound_last_refresh = 0.0
        self._compound_autopilot = True
        self._compound_adoptions: list[dict[str, Any]] = []
        self._compound_overview_rows: dict[str, dict[str, Any]] = {}
        self._compound_result_rows: list[dict[str, Any]] = []
        self._compound_forward_rows: list[dict[str, Any]] = []
        self._compound_own: dict[str, Any] = {}
        table = self.query_one("#compound-table", CompoundTable)
        table.cursor_type = "row"
        for label in ("on", "component", "family", "style", "weight", "parameters", "live score",
                      "learned hit (n)", "tuned to", "bt oos hit", "fwd hit (n)"):
            table.add_column(label, key=label)
        results = self.query_one("#compound-results", GlossaryTable)
        results.cursor_type = "row"
        results.add_columns("configuration", "oos return", "buy & hold", "oos sharpe", "trades", "fees %",
                            "net bps 1h", "net bps 24h", "oos calls", "oos hit", "z", "gross bps", "max dd",
                            "rankable")
        hz = self.query_one("#compound-horizons", GlossaryTable)
        hz.add_columns("forecast UTC", "starts UTC", "minutes", "prediction", "return bps", "hit")
        fwd = self.query_one("#compound-forward-table", GlossaryTable)
        fwd.cursor_type = "row"
        fwd.add_columns("time", "call", "composite", "regime", "price", "next 5m bps", "hit", "blocked by")
        ov = self.query_one("#compound-overview", GlossaryTable)
        ov.cursor_type = "row"
        ov.add_columns("coin", "own settings", "data", "backtest verdict", "bt hit", "fwd calls", "fwd hit",
                       "paper $", "unattended")
        if self.query("#signal-live-predictions-table"):
            live_t = self.query_one("#signal-live-predictions-table", GlossaryTable)
            live_t.cursor_type = "row"
        self._signal_live_tick()
        self._signal_live_refresh_predictions()
        env = self._call("compound.config", {"asset": self._compound_coin}, quiet=True)
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
            self._compound_own = env["result"]["own_settings"]
        else:
            self.query_one("#compound-status", Static).update(f"[red]{escape(self._msg(env))}[/]")
        self._compound_load_autopilot()
        self._compound_render_table()
        self._compound_load_results()
        self._compound_show_unattended()
        self._compound_load_overview()
        self.set_interval(20, self._compound_auto_tick)
        if self._ensure_autopilot and self._compound_autopilot:
            self._compound_ensure_autopilot()

    @work(thread=True, group="compound-autopilot", exclusive=True)
    def _compound_ensure_autopilot(self) -> None:
        """Start any coin's training loop autopilot wants running (it waits for each child's lock,
        so it runs off the UI thread)."""
        env = self._call("compound.autopilot_ensure", quiet=True)
        if env["ok"] and env["result"].get("started"):
            self.call_from_thread(self.query_one("#compound-status", Static).update,
                                  Text("autopilot started training for " + ", ".join(env["result"]["started"])))
        self.call_from_thread(self._compound_load_autopilot)
        self.call_from_thread(self._compound_load_overview)

    def _compound_load_autopilot(self) -> None:
        """The switch, which coins train, the LaunchAgent and the recent adoptions."""
        env = self._call("compound.autopilot_status", quiet=True)
        line = self.query_one("#compound-autopilot-status", Static)
        button = self.query_one("#compound-autopilot", Button)
        if not env["ok"]:
            line.update(Text(f"autopilot: {self._msg(env)}"))
            return
        r = env["result"]
        self._compound_autopilot = bool(r["autopilot"])
        self._compound_adoptions = list(r.get("adoptions") or [])
        button.label = f"Autopilot: {'on' if r['autopilot'] else 'off'}"
        button.variant = "success" if r["autopilot"] else "default"
        agent = r.get("agent") or {}
        agent_text = ("LaunchAgent restarts stopped coins every 5 min" if agent.get("loaded")
                      else "LaunchAgent not loaded: python -m soltui.compound_agent install")
        last = self._compound_adoptions[-1] if self._compound_adoptions else None
        last_text = (f"last adoption {time.strftime('%m-%d %H:%M', time.gmtime(int(last['ts'])))} "
                     f"{last['asset']} {last['metric']}" if last else "no tuned settings adopted yet")
        if r["autopilot"]:
            line.update(Text(f"AUTOPILOT ON: tuning runs, every forward tick adopts evidence-gated tuned "
                             f"settings per coin, {len(r['running'])}/{len(r.get('live_coins') or compound_mod.COINS)} coins training; "
                             f"{agent_text}; {last_text}"))
        else:
            line.update(Text(f"autopilot off: settings change only when you change them; "
                             f"{len(r['running'])}/{len(r.get('live_coins') or compound_mod.COINS)} coins training; {last_text}"))

    @on(Button.Pressed, "#compound-autopilot")
    def _compound_autopilot_toggle(self) -> None:
        env = self._call("compound.autopilot", {"enabled": not self._compound_autopilot})
        status = self.query_one("#compound-status", Static)
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        self._compound_reload_config()
        self._compound_load_autopilot()
        self._compound_load_overview()
        status.update("autopilot on: tuning runs and tuned settings are adopted automatically; every coin "
                      "keeps training" if self._compound_autopilot else
                      "autopilot off: no automatic adoption and no automatic restarts (running loops keep going)")

    def _compound_reload_config(self) -> None:
        """Re-read this coin's settings from disk: autopilot saves adoptions from other processes."""
        env = self._call("compound.config", {"asset": self._compound_coin}, quiet=True)
        if env["ok"] and env["result"]["config"] != self._compound_cfg:
            self._compound_cfg = env["result"]["config"]
            self._compound_own = env["result"]["own_settings"]
            self._compound_render_table()
        elif env["ok"]:
            self._compound_own = env["result"]["own_settings"]

    def _compound_selected(self) -> str:
        tables = list(self.query("#compound-table"))
        if not tables:
            return self._COMPOUND_IDS[0]
        table = tables[0]
        return self._strategy_table_key(table) if table.row_count else self._COMPOUND_IDS[0]

    def _compound_titles(self) -> None:
        coin = self._compound_coin
        self.query_one("#compound-table-title", Static).update(
            f"[b]Metrics and gates for {coin}[/b]: on/off, family, weight and parameters; the live score "
            "from the last Signal now; the learned hit rate and weight; where tuning would move it; its "
            "backtest and forward hit rate. Double-click a row or press Space to switch it.")
        self.query_one("#compound-results-title", Static).update(
            f"[b]Backtest results for {coin}[/b], latest run: the compound and each enabled metric alone, "
            "scored on the held-out last 30% of bars (OOS). Hit = next-bar direction; return and Sharpe are "
            "the engine's P&L after fees at the set leverage.")
        self.query_one("#compound-forward-title", Static).update(
            f"[b]Forward test for {coin}[/b] (selected coin only). The trainer may cover other coins; "
            "see All coins for each running status. Separate 1, 5 and 30 minute outcomes use the same "
            "five-minute signal, starting at a future minute open. Legacy calls follow below: "
            "one row per closed 5m bar with the "
            "call, composite score, regime, price, the next bar's move in bps, whether it hit, and any gate "
            "that forced FLAT. No order was placed.")

    def _compound_render_table(self) -> None:
        self._compound_titles()
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
            f"adaptive_window={agg['adaptive_window']} adaptive_prior={agg['adaptive_prior']:g} "
            f"adaptive_halflife={agg['adaptive_halflife']} "
            f"adaptive_flip={agg['adaptive_flip']} tune={agg['tune']} tune_confidence={agg['tune_confidence']:g} "
            f"tune_min_calls={agg['tune_min_calls']:g} tune_step={agg['tune_step']:g} "
            f"tune_cooldown={agg['tune_cooldown']} hold={agg['hold']} entry_quantile={agg['entry_quantile']:g} "
            f"leverage={ex['leverage']:g} fee_bps={ex['fee_bps']:g} "
            f"slippage_bps={ex['slippage_bps']:g} risk_pct={ex['risk_pct']:g} use_wallet={ex['use_wallet']:g}")

    @on(DataTable.RowHighlighted, "#compound-table")
    def _compound_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not self._on_compound_tab():
            return
        # A queued highlight can outlive the compound widgets during shutdown.
        try:
            detail = self.query_one("#compound-detail", Static)
            edit = self.query_one("#compound-edit", Input)
        except NoMatches:
            return
        cid = str(event.row_key.value) if event.row_key is not None else self._compound_selected()
        comp = sc.BY_ID.get(cid)
        if comp is None:
            return
        entry = self._compound_cfg["components"][cid]
        specs = "; ".join(f"{p.name} {p.lo:g}..{p.hi:g}" + (f" ({p.describe})" if p.describe else "")
                          for p in comp.params)
        detail.update(Text(
            f"{comp.name} [{comp.kind}, {comp.family}/{comp.style}] source: {comp.source}\n"
            f"formula: {comp.formula}\nworks: {comp.useful_when}\nfails: {comp.not_useful_when}\n"
            f"ranges: {specs or 'none'}"))
        values = " ".join([f"weight={entry['weight']:g}"]
                          + [f"{k}={v:g}" for k, v in entry["params"].items()])
        edit.value = values
        self._compound_preview_metric(cid)

    def _compound_preview_metric(self, cid: str) -> None:
        if not self._on_compound_tab():
            return  # a background refresh must not take the editor away from another tab
        tuned = self._compound_tuned.get(cid, {})
        columns = {"live score": self._compound_live.get(cid, ""),
                   "learned hit (n) x weight multiplier": self._compound_learned.get(cid, ""),
                   "tuning proposes (last Signal now)": " ".join(f"{k}={v:g}" for k, v in tuned.items()),
                   "backtest out-of-sample hit (alone)": self._compound_bt.get(cid, ""),
                   "forward hit (n)": self._compound_fwd.get(cid, "")}
        self._show_preview(f"{self._compound_coin} {cid}", compound_mod.metric_preview(
            cid, self._compound_cfg, asset=self._compound_coin, own=self._compound_own, columns=columns,
            adoptions=self._compound_adoptions, autopilot=self._compound_autopilot))

    @on(DataTable.RowSelected, "#compound-overview")
    @on(DataTable.RowHighlighted, "#compound-overview")
    def _compound_overview_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not self._on_compound_tab() or event.row_key is None:
            return
        coin = str(event.row_key.value)
        if isinstance(event, DataTable.RowSelected):
            self._set_editor_open(True, persist=False)
        row = self._compound_overview_rows.get(coin)
        if row is None:
            return
        env = self._call("compound.config", {"asset": coin}, quiet=True)
        own = env["result"]["own_settings"] if env["ok"] else {}
        self._show_preview(f"{coin} overview", compound_mod.coin_preview(
            row, own=own, adoptions=self._compound_adoptions, autopilot=self._compound_autopilot))

    @on(DataTable.RowHighlighted, "#compound-results")
    def _compound_result_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not self._on_compound_tab() or not 0 <= event.cursor_row < len(self._compound_result_rows):
            return
        row = self._compound_result_rows[event.cursor_row]
        self._show_preview(f"{self._compound_coin} backtest {row.get('label')}", compound_mod.record_preview(
            f"{self._compound_coin} backtest: {row.get('label')}", row,
            "OOS = the last 30% of bars. Hit = next-bar direction; return = engine P&L after fees at the "
            "set leverage. A row is ranked only with enough out-of-sample calls."))

    @on(DataTable.RowHighlighted, "#compound-forward-table")
    def _compound_forward_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not self._on_compound_tab() or not 0 <= event.cursor_row < len(self._compound_forward_rows):
            return
        row = self._compound_forward_rows[event.cursor_row]
        when = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(int(row["bar_ts"]) + 300))
        self._show_preview(f"{self._compound_coin} forward call {when}", compound_mod.record_preview(
            f"{self._compound_coin} forward call decided at {when}", row,
            "A paper call: recorded and resolved against the next closed 5m bar. No order was placed."))

    @on(Button.Pressed, "#btn-goto-signal-live")
    def _goto_signal_live(self) -> None:
        if getattr(self, "_v2", False):
            self._v2_navigate("signal", 0)
        else:
            self.query_one("#main-tabs", TabbedContent).active = "tab-compound"
            if self.query("#compound-sections"):
                self.query_one("#compound-sections", TabbedContent).active = "cmp-live"

    @on(DataTable.RowHighlighted, "#signal-live-predictions-table")
    def _signal_live_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if 0 <= event.cursor_row < len(self._signal_live_prediction_rows):
            self._signal_live_show_detail(event.cursor_row)

    def _signal_live_show_detail(self, row_idx: int) -> None:
        if not self.query("#signal-live-detail") or not (0 <= row_idx < len(self._signal_live_prediction_rows)):
            return
        r = self._signal_live_prediction_rows[row_idx]
        issued = (time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(r['last_issued']))
                  if r.get('last_issued') else '-')
        detail_lines = [
            f"[b]{r['label']}[/b] on {r['asset']} · Overall Accuracy: [bold green]{r['accuracy']:.1f}%[/] ({r['hits']}/{r['resolved']} correct calls)",
            f"Predictions: 1m: [b]{r['pred_1m']}[/] ({r.get('acc_1m') or '-'}% on {r.get('resolved_1m', 0)} calls) · "
            f"5m: [b]{r['pred_5m']}[/] ({r.get('acc_5m') or '-'}% on {r.get('resolved_5m', 0)} calls) · "
            f"10m: [b]{r['pred_10m']}[/] ({r.get('acc_10m') or '-'}% on {r.get('resolved_10m', 0)} calls) · "
            f"30m: [b]{r['pred_30m']}[/] ({r.get('acc_30m') or '-'}% on {r.get('resolved_30m', 0)} calls)",
            f"Last prediction issued: {issued}",
        ]
        if r.get("settings"):
            settings_str = "; ".join(
                f"{m.get('name', '')} " + ", ".join(f"{k}={v}" for k, v in m.get("params", {}).items())
                for m in r.get("settings", [])
            )
            detail_lines.append(f"Parameters: {settings_str}")
        self.query_one("#signal-live-detail", Static).update("\n".join(detail_lines))

    @on(Input.Submitted, "#signal-live-vote-min-score")
    @on(Input.Submitted, "#signal-live-vote-min-resolved")
    def _signal_live_save_vote_floor(self) -> None:
        try:
            values = {"live_vote_min_accuracy": float(self.query_one("#signal-live-vote-min-score", Input).value),
                      "live_vote_min_resolved": float(self.query_one("#signal-live-vote-min-resolved", Input).value)}
            env = self._call("settings.save", values)
        except ValueError:
            env = {"ok": False, "error": {"message": "Enter a valid percentage and whole resolved count."}}
        self.query_one("#signal-live-vote-status", Static).update("Saved voting floor." if env["ok"] else self._msg(env))
        if env["ok"]:
            self._signal_live_refresh_predictions(force=True)

    def _signal_live_update_score(self, now: float) -> dict[str, Any]:
        rows = self._signal_live_prediction_rows if self._signal_live_last_coin == getattr(self, "_compound_coin", "SOL") else []
        aggregate = live_score.aggregate_predictions(rows, now=now,
            min_accuracy=self.settings.live_vote_min_accuracy, min_resolved=self.settings.live_vote_min_resolved)
        color = "grey70" if aggregate["color"] == "gray" else aggregate["color"]
        score = "—" if aggregate["score"] is None else f"{aggregate['score']:+.1f} / 100"
        text = Text(f"Aggregate score {score} · {aggregate['label']}", style=f"bold {color}")
        text.append(f" · {aggregate['strategies']} strategies / {aggregate['votes']} horizon votes · "
                    f"floor {self.settings.live_vote_min_accuracy:g}%, {self.settings.live_vote_min_resolved} resolved/horizon", style="dim")
        if not aggregate["available"]:
            text.append(" · No qualifying current predictions", style="dim")
        for selector in ("#signal-live-price-score", "#signal-live-predictions-score"):
            if self.query(selector):
                self.query_one(selector, Static).update(text)
        if self.query("#signal-live-forward-link"):
            self.query_one("#signal-live-forward-link", Button).display = not aggregate["available"]
            self._signal_live_render_recovery(aggregate["available"])
        return aggregate

    def _signal_auto_recovery_allowed(self) -> bool:
        # Tests opt in explicitly with mocked commands; a headless UI must not
        # leave real detached producers behind after its virtual screen closes.
        enabled = self._auto_prediction_recovery
        return bool(getattr(self.settings, "forwardtest_autostart", True) and
                    (enabled if enabled is not None else not self.is_headless))

    @on(Button.Pressed, "#signal-live-forward-link")
    def _signal_live_open_forward(self) -> None:
        self.set_focus(None)
        if self._v2:
            destination = self._v2_destination("research")
            index = next(i for i, view in enumerate(destination.views) if view.tab == "tab-forwardtest")
            self._v2_show("research", index)
        else:
            self.query_one("#main-tabs", TabbedContent).active = "tab-forwardtest"

    @on(Button.Pressed, "#signal-live-predictions-start")
    def _signal_live_start_predictions(self) -> None:
        self._signal_live_request_recovery(manual=True)

    def _signal_live_render_recovery(self, available: bool = False) -> None:
        if not self.query("#signal-live-recovery-status"):
            return
        state = self._signal_recovery_state
        status = self.query_one("#signal-live-recovery-status", Static)
        status.display = not available
        status.update(Text(state.get("message", "Checking prediction process…")))
        button = self.query_one("#signal-live-predictions-start", Button)
        button.display = not available and bool(state.get("can_start")) and not state.get("running")
        button.disabled = self._signal_recovery_busy

    def _signal_live_request_recovery(self, *, manual: bool = False, startup: bool = False) -> None:
        if not self._signal_live_alive.is_set() or self._signal_recovery_busy:
            return
        if not startup and not manual:
            if (self.query_one("#main-tabs", TabbedContent).active != "tab-compound" or
                    self.query_one("#compound-sections", TabbedContent).active != "cmp-live"):
                return
        coin = getattr(self, "_compound_coin", "SOL")
        now = time.time()
        rows = self._signal_live_prediction_rows
        current = any(r.get(f"pred_{h}m") in ("UP", "DOWN", "FLAT") and
                      isinstance(r.get(f"issued_{h}m"), (int, float)) and
                      isinstance(r.get(f"expires_{h}m"), (int, float)) and
                      r[f"issued_{h}m"] <= now < r[f"expires_{h}m"]
                      for r in rows for h in (1, 5, 10, 30))
        self._signal_recovery_busy = True
        self._signal_recovery_drained = threading.Event()
        self._signal_live_recovery_job(coin, manual, current, self._signal_auto_recovery_allowed(), self._signal_recovery_drained)

    @work(thread=True, exit_on_error=False, group="signal-prediction-recovery")
    def _signal_live_recovery_job(self, coin: str, manual: bool, current: bool, automatic_allowed: bool,
                                  drained: threading.Event) -> None:
        delivered = False
        try:
            try:
                env = self._call("forwardtest.ensure" if manual else "forwardtest.health",
                                 {"asset": coin, **({"manual": True} if manual else {})}, quiet=True)
                if env.get("ok") and not manual:
                    state = env["result"]
                    due = time.time() - self._signal_recovery_at.get(coin, -float("inf")) >= 30
                    automatic = (automatic_allowed and not state.get("paused") and not state.get("cooldown_seconds") and due and
                                 (not state.get("running") or not current))
                    allowed = state.get("can_start") or state.get("running")
                    if allowed and (manual or automatic):
                        self._signal_recovery_at[coin] = time.time()
                        env = self._call("forwardtest.ensure", {"asset": coin, "manual": manual}, quiet=True)
            except Exception as exc:
                env = {"ok": False, "error": {"message": f"Prediction recovery failed ({type(exc).__name__})"}}
            if self._signal_live_alive.is_set():
                try:
                    self.call_from_thread(self._signal_live_recovery_done, coin, env)
                    delivered = True
                except RuntimeError:
                    pass
        finally:
            if not delivered:
                self._signal_recovery_busy = False
            drained.set()

    def _signal_live_recovery_done(self, coin: str, env: dict[str, Any]) -> None:
        self._signal_recovery_busy = False
        if not self._signal_live_alive.is_set() or coin != getattr(self, "_compound_coin", "SOL"):
            return
        if env.get("ok"):
            self._signal_recovery_state = env["result"]
            self._forward_running = bool(env["result"].get("running"))
            self._forward_controls()
            self._forward_show_running(env["result"].get("assets", []) if self._forward_running else [])
        else:
            self._signal_recovery_at[coin] = time.time()
            self._signal_recovery_state = {"state": "failed", "can_start": True,
                                           "message": (env.get("error") or {}).get("message", "Prediction recovery failed")}
        self._signal_live_update_score(time.time())

    def _signal_live_tick(self) -> None:
        if not self.query("#signal-live-stream"):
            return
        coin = getattr(self, "_compound_coin", "SOL")
        if self.query("#signal-live-price-source") and self.query_one("#signal-live-price-source", Select).value == "jupiter":
            self._signal_live_refresh_predictions()
            self._signal_live_update_score(time.time())
            self._signal_live_jupiter_tick(coin)
            return
        product = f"{coin}-USD"
        now = time.time()
        self._signal_live_refresh_predictions()
        aggregate = self._signal_live_update_score(now)
        try:
            from . import pricefeed
            latest = pricefeed.read_latest()
            st = pricefeed.status()
        except Exception:
            latest = None
            st = {}
        prices = st.get("prices") or {}
        quote = prices.get(product) or {}
        if not quote and latest and "q" in latest:
            q_row = latest["q"].get(product)
            if q_row and len(q_row) >= 6:
                bid, ask, last, bid_size, ask_size, q_time = q_row
                mid = (bid + ask) / 2.0 if bid > 0 and ask > 0 else last
                spread_bps = ((ask - bid) / mid * 10000.0) if mid > 0 else 0.0
                quote = {
                    "bid": bid, "ask": ask, "last": last, "mid": mid,
                    "bid_size": bid_size, "ask_size": ask_size,
                    "spread_bps": spread_bps, "quote_age_s": max(0.0, now - q_time),
                }

        mid = quote.get("mid") or quote.get("last")
        bid = quote.get("bid")
        ask = quote.get("ask")
        bid_size = quote.get("bid_size")
        ask_size = quote.get("ask_size")
        spread_bps = quote.get("spread_bps")
        age = quote.get("quote_age_s")
        is_live = bool(st.get("live", False)) and isinstance(age, (int, float)) and math.isfinite(age) and 0 <= age < 15.0

        source_time = quote.get("quote_ts")
        if source_time is None and isinstance(age, (int, float)) and math.isfinite(age) and age >= 0:
            source_time = now - age
        time_valid = isinstance(source_time, (int, float)) and math.isfinite(source_time) and source_time <= now
        status_widget = self.query_one("#signal-live-stream", Static)
        if mid is not None and isinstance(mid, (int, float)) and math.isfinite(mid) and mid > 0 and time_valid:
            badge = "[bold green]● LIVE STREAM[/]" if is_live else "[bold yellow]○ STREAMING (stale)[/]"
            fmt = ",.6f" if mid < 0.01 else (",.4f" if mid < 1.0 else ",.2f")
            bid_str = f"${bid:{fmt}}" if bid is not None else "-"
            ask_str = f"${ask:{fmt}}" if ask is not None else "-"
            bsize_str = f" ({bid_size:,.2f})" if bid_size is not None else ""
            asize_str = f" ({ask_size:,.2f})" if ask_size is not None else ""
            spr_str = f"{spread_bps:.2f} bps" if spread_bps is not None else "-"
            age_str = f"{age:.1f}s" if age is not None else "-"
            msgs = st.get("messages", 0)
            reconnects = st.get("reconnects", 0)
            status_widget.update(
                f"{badge} · [b]{product}[/b] · Mid: [bold cyan]${mid:{fmt}}[/] · "
                f"Bid: {bid_str}{bsize_str} · Ask: {ask_str}{asize_str} · "
                f"Spread: {spr_str} · Quote age: {age_str} · msgs: {msgs:,} · reconns: {reconnects}"
            )
            history = self._signal_live_price_history.setdefault(coin, [])
            if not history:
                try:
                    from . import compound as compound_mod
                    candles = compound_mod._load_candle_cache(coin, seconds=60)
                    for ts in sorted(candles)[-60:]:
                        close_p = candles[ts][1]
                        if close_p > 0 and math.isfinite(close_p):
                            history.append((float(ts), float(close_p)))
                except Exception:
                    pass
            quote_ts = source_time
            if not isinstance(quote_ts, (int, float)) and isinstance(age, (int, float)) and math.isfinite(age) and age >= 0:
                quote_ts = now - age
            scores = self._signal_live_score_history.setdefault(coin, {})
            if (isinstance(quote_ts, (int, float)) and math.isfinite(quote_ts) and quote_ts <= now
                    and (not history or quote_ts > history[-1][0])):
                history.append((float(quote_ts), float(mid)))
                scores[float(quote_ts)] = aggregate["score"] if is_live else None
                del history[:-120]
                scores_to_keep = {t for t, _ in history}
                for old in list(scores):
                    if old not in scores_to_keep:
                        del scores[old]
            if not history:
                return
            width = self.query_one("#signal-live-plot").content_size.width or 70
            window = live_score.tick_window(history, scores, width)
            visible = window["points"]
            pts = [p for _, p in visible]
            chart_widget = self.query_one("#signal-live-chart", Sparkline)
            chart_widget.styles.width = len(pts) * window["slot"]
            chart_widget.data = pts
            tape = Text(" " * (14 + window["padding"]))
            for value in window["scores"]:
                color = "green" if value is not None and value >= 20 else "red" if value is not None and value <= -20 else "grey70"
                label = "—" if value is None else f"{value:+.1f}"
                tape.append(label.center(window["slot"]), style=color)
            self.query_one("#signal-live-score-tape", Static).update(tape)
            low = min(pts)
            high = max(pts)
            start_p = pts[0]
            chg_pct = (mid - start_p) / start_p * 100.0 if start_p > 0 else 0.0
            color = "green" if chg_pct >= 0 else "red"
            self.query_one("#signal-live-chart-context", Static).update(
                f"[b]{product} real-time price graph[/b] · [bold {color}]${mid:{fmt}} ({chg_pct:+.2f}%)[/] · "
                f"Range: ${low:{fmt}} – ${high:{fmt}} · {len(pts)} points"
            )
            # Render vertical price numbers on Y-axis (7 lines matching sparkline height)
            mid_level = (high + low) / 2.0
            high_str = f"${high:{fmt}}"[:12]
            mid_str = f"${mid_level:{fmt}}"[:12]
            low_str = f"${low:{fmt}}"[:12]
            yaxis_lines = [
                f"[dim]{high_str:>12}[/] ┤",
                f"{' ':>12} │",
                f"{' ':>12} │",
                f"[dim]{mid_str:>12}[/] ┤",
                f"{' ':>12} │",
                f"{' ':>12} │",
                f"[dim]{low_str:>12}[/] ┤",
            ]
            if self.query("#signal-live-chart-yaxis"):
                self.query_one("#signal-live-chart-yaxis", Static).update("\n".join(yaxis_lines))

            # Render horizontal timestamps on X-axis matching the sparkline width
            if self.query("#signal-live-chart-xaxis"):
                prefix = " " * 14
                t_start = visible[0][0]
                t_mid = visible[len(visible) // 2][0]
                t_end = visible[-1][0]
                prefix += " " * window["padding"]
                t0_str = time.strftime("%H:%M:%S", time.gmtime(t_start))
                t1_str = time.strftime("%H:%M:%S", time.gmtime(t_mid))
                t2_str = time.strftime("%H:%M:%S UTC", time.gmtime(t_end))
                chart_widget = self.query_one("#signal-live-chart", Sparkline)
                w = chart_widget.size.width if chart_widget.size.width > 0 else 70
                if len(history) < 2 or int(t_start) == int(t_end):
                    xaxis = f"{prefix}[dim]{t2_str} (now)[/]"
                elif w >= 40:
                    gap1 = max(1, (w // 2) - len(t0_str) - (len(t1_str) // 2))
                    pos_after_t1 = len(t0_str) + gap1 + len(t1_str)
                    gap2 = max(1, w - pos_after_t1 - len(t2_str))
                    xaxis = f"{prefix}[dim]{t0_str}{' ' * gap1}{t1_str}{' ' * gap2}{t2_str}[/]"
                else:
                    gap = max(1, w - len(t0_str) - len(t2_str))
                    xaxis = f"{prefix}[dim]{t0_str}{' ' * gap}{t2_str}[/]"
                self.query_one("#signal-live-chart-xaxis", Static).update(xaxis)

            self.query_one("#signal-live-chart-stats", Static).update(
                f"Subscribed: wss://ws-feed.exchange.coinbase.com · Channel: level2_batch + ticker · "
                f"Last update: {time.strftime('%H:%M:%S UTC', time.gmtime(now))}"
            )
        else:
            self.query_one("#signal-live-chart", Sparkline).data = []
            self.query_one("#signal-live-score-tape", Static).update("")
            self.query_one("#signal-live-chart-context", Static).update(f"{product} price graph · waiting for a usable quote")
            self.query_one("#signal-live-chart-stats", Static).update("")
            status_widget.update(
                f"[yellow]Waiting for {product} stream quotes from pricefeed recorder… (recorder pid: {st.get('pid', '-')})[/]"
            )
            if self.query("#signal-live-chart-yaxis"):
                self.query_one("#signal-live-chart-yaxis", Static).update("")
            if self.query("#signal-live-chart-xaxis"):
                self.query_one("#signal-live-chart-xaxis", Static).update("")

    @on(Select.Changed, "#signal-live-price-source")
    def _signal_live_source_changed(self, event: Select.Changed) -> None:
        self._signal_live_jupiter_generation += 1
        self._signal_live_jupiter_at = 0.0
        self._signal_live_clear_price()
        self._signal_live_tick()

    def _signal_live_clear_price(self) -> None:
        if not self.query("#signal-live-chart"):
            return
        self.query_one("#signal-live-chart", Sparkline).data = []
        for selector in ("#signal-live-score-tape", "#signal-live-chart-stats",
                         "#signal-live-chart-yaxis", "#signal-live-chart-xaxis"):
            self.query_one(selector, Static).update("")
        self.query_one("#signal-live-stream", Static).update("Loading selected price feed…")
        self.query_one("#signal-live-chart-context", Static).update("Price graph: loading…")

    def _signal_live_jupiter_tick(self, coin: str) -> None:
        if not self._signal_live_alive.is_set():
            return
        if self._signal_live_jupiter_coin != coin:
            self._signal_live_jupiter_coin = coin
            self._signal_live_jupiter_generation += 1
            self._signal_live_jupiter_at = 0.0
            self._signal_live_clear_price()
        if self._jupiter_price_busy or time.time() - self._signal_live_jupiter_at < 10:
            return
        self._jupiter_price_busy = True
        self._signal_live_jupiter_state = "running"
        self._signal_live_jupiter_at = time.time()
        drained = self._signal_live_jupiter_drained = threading.Event()
        self._signal_live_jupiter_job(coin, self._signal_live_jupiter_generation, drained)

    @work(thread=True, exit_on_error=False, group="signal-jupiter-price")
    def _signal_live_jupiter_job(self, coin: str, generation: int, drained: threading.Event) -> None:
        delivered = False
        try:
            try:
                env = self._call("prices.quote", {"asset": coin, "source": "jupiter"}, quiet=True)
            except Exception as exc:
                env = {"ok": False, "error": {"message": f"Jupiter price read failed ({type(exc).__name__})"}}
            if self._signal_live_alive.is_set():
                try:
                    self.call_from_thread(self._signal_live_jupiter_done, coin, generation, env)
                    delivered = True
                except RuntimeError:
                    pass  # The app closed after the read completed.
        finally:
            if not delivered:
                self._jupiter_price_busy = False
            drained.set()

    def _signal_live_jupiter_done(self, coin: str, generation: int, env: dict[str, Any]) -> None:
        self._jupiter_price_busy = False
        if not self._signal_live_alive.is_set() or not self.query("#signal-live-price-source"):
            return
        current_coin = getattr(self, "_compound_coin", "SOL")
        jupiter_selected = self.query_one("#signal-live-price-source", Select).value == "jupiter"
        if generation != self._signal_live_jupiter_generation or coin != current_coin or not jupiter_selected:
            self._signal_live_jupiter_state = "discarded"
            if jupiter_selected:
                self._signal_live_jupiter_at = 0.0
                self._signal_live_jupiter_tick(current_coin)
            return
        quote = env.get("result") if isinstance(env, dict) and env.get("ok") else None
        price, at = (quote.get("price"), quote.get("fetched_at")) if isinstance(quote, dict) else (None, None)
        if (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0
                or isinstance(at, bool) or not isinstance(at, (int, float)) or not math.isfinite(at) or at > time.time()):
            self._signal_live_jupiter_state = "failed"
            message = ((env.get("error") or {}).get("message") if isinstance(env, dict) else None) or "Jupiter returned an unusable price"
            self.query_one("#signal-live-stream", Static).update(Text(message))
            return
        self._signal_live_jupiter_state = "completed"
        history = self._signal_live_price_history.setdefault(f"jupiter:{coin}", [])
        if not history or at > history[-1][0]:
            history.append((at, price))
            del history[:-120]
        self.query_one("#signal-live-chart", Sparkline).data = [p for _, p in history]
        self.query_one("#signal-live-chart-context", Static).update(Text(f"Jupiter {coin}/USD ${price:,.6f} · block {quote.get('block_id') or 'unknown'}"))
        self.query_one("#signal-live-stream", Static).update(Text(f"Jupiter reference price · fetched {time.strftime('%H:%M:%S UTC', time.gmtime(at))}"))
        self.query_one("#signal-live-chart-stats", Static).update("Predictions use Coinbase candles. Jupiter prices do not supply bid/ask or executable swap quotes.")
        self.query_one("#signal-live-score-tape", Static).update("")
        self.query_one("#signal-live-chart-yaxis", Static).update("")
        self.query_one("#signal-live-chart-xaxis", Static).update("")

    def _signal_live_poll_predictions(self) -> None:
        # Keep the ten-second schedule independent of chart ticks and read
        # latency. A busy reader skips this period, without a catch-up burst.
        if not self._signal_live_busy:
            self._signal_live_refresh_predictions(force=True)

    def _signal_live_refresh_predictions(self, force: bool = False) -> None:
        if not self._signal_live_alive.is_set() or not self.query("#signal-live-predictions-table"):
            return
        coin = getattr(self, "_compound_coin", "SOL")
        key = (coin, self.settings.live_vote_min_accuracy, self.settings.live_vote_min_resolved)
        changed = key != self._signal_live_prediction_key
        if changed:
            self._signal_live_prediction_key = key
            self._signal_live_pred_generation += 1
            self._signal_live_last_coin = coin
            self._signal_live_last_pred_update = 0.0
            self._signal_live_prediction_rows = []
            self._signal_live_render_predictions(refreshing=True)
        if self._signal_live_busy:
            self._signal_live_refresh_requested |= force or changed
            return
        if not force and not changed:
            return
        self._signal_live_busy = True
        self._signal_live_refresh_requested = False
        # A saved snapshot can take seconds to read. Keep it off the one-second
        # chart timer, and never start a second database read while one is active.
        self._signal_live_drained = threading.Event()
        self._signal_live_predictions_job(key, self._signal_live_pred_generation, self._signal_live_drained)

    @work(thread=True, exit_on_error=False, group="signal-live-predictions")
    def _signal_live_predictions_job(self, key: tuple[str, float, int], generation: int,
                                     drained: threading.Event) -> None:
        try:
            try:
                env = self._call("forwardtest.predictions", {"asset": key[0], "limit": 50}, quiet=True)
            except Exception as exc:
                env = {"ok": False, "error": {"message": str(exc)}}
            if self._signal_live_alive.is_set():
                try:
                    self.call_from_thread(self._signal_live_predictions_done, key, generation, env)
                except RuntimeError:
                    pass  # The app closed after the database read.
        finally:
            drained.set()

    def _signal_live_predictions_done(self, key: tuple[str, float, int], generation: int,
                                      env: dict[str, Any]) -> None:
        self._signal_live_busy = False
        if not self._signal_live_alive.is_set() or not self.query("#signal-live-predictions-table"):
            return
        current = (getattr(self, "_compound_coin", "SOL"), self.settings.live_vote_min_accuracy,
                   self.settings.live_vote_min_resolved)
        if generation != self._signal_live_pred_generation or key != current:
            self._signal_live_refresh_predictions(force=True)
            return
        error = None
        if env.get("ok"):
            self._signal_live_prediction_rows = env["result"]["rows"]
            self._signal_live_last_pred_update = time.time()
        else:
            self._signal_live_prediction_rows = []
            error = (env.get("error") or {}).get("message") or "Prediction read failed."
        self._signal_live_render_predictions(error=error)
        aggregate = self._signal_live_update_score(time.time())
        if not aggregate["available"]:
            self._signal_live_request_recovery()
        if self._signal_live_refresh_requested:
            self._signal_live_refresh_predictions(force=True)

    def _signal_live_render_predictions(self, *, error: str | None = None, refreshing: bool = False) -> None:
        coin = getattr(self, "_compound_coin", "SOL")
        rows = self._signal_live_prediction_rows
        self._signal_live_update_score(time.time())
        table = self.query_one("#signal-live-predictions-table", DataTable)
        cursor = table.cursor_row
        table.clear()
        for idx, r in enumerate(rows, 1):
            def badge(pred: str) -> str:
                if pred == "UP":
                    return "[bold green]▲ UP[/]"
                elif pred == "DOWN":
                    return "[bold red]▼ DOWN[/]"
                elif pred == "FLAT":
                    return "[yellow]— FLAT[/]"
                return "-"
            acc = f"[bold green]{r['accuracy']:.1f}%[/]" if r["accuracy"] >= 65 else f"{r['accuracy']:.1f}%"
            hz_parts = []
            for h in (1, 5, 10, 30):
                hacc = r.get(f"acc_{h}m")
                hn = r.get(f"resolved_{h}m", 0)
                if hacc is not None and hn > 0:
                    hz_parts.append(f"{h}m:{hacc:.0f}%")
                else:
                    hz_parts.append(f"{h}m:-")
            hz_str = " · ".join(hz_parts)
            settings_str = "; ".join(
                f"{m.get('name', '')} " + ", ".join(f"{k}={v}" for k, v in m.get("params", {}).items())
                for m in r.get("settings", [])
            )
            table.add_row(
                f"#{idx}",
                r["label"],
                acc,
                str(r["resolved"]),
                badge(r["pred_1m"]),
                badge(r["pred_5m"]),
                badge(r["pred_10m"]),
                badge(r["pred_30m"]),
                hz_str,
                settings_str or "-",
                key=r["label"],
            )
        if rows:
            table.move_cursor(row=min(cursor, len(rows) - 1))
            self._signal_live_show_detail(min(cursor, len(rows) - 1))
        else:
            self.query_one("#signal-live-detail", Static).update(
                Text(f"Prediction refresh failed: {error}. Retrying every 10s." if error else
                     f"Reading saved predictions for {coin}…" if refreshing else
                     f"No forward test prediction records found for coin {coin} yet.")
            )
        if self.query("#signal-live-predictions-title"):
            upd_time = (time.strftime("%H:%M:%S UTC", time.gmtime(self._signal_live_last_pred_update))
                        if self._signal_live_last_pred_update else "not yet read")
            state = ("Refresh failed; retrying" if error else "Refreshing" if refreshing else "Updated")
            self.query_one("#signal-live-predictions-title", Static).update(
                f"[b]Top performing forward test strategies — predictions[/b] · [dim]{state} {upd_time} (10s refresh)[/]"
            )

    @on(TabbedContent.TabActivated)
    def _tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane is not None:
            if event.pane.id in ("tab-compound", "cmp-call") and hasattr(self, "_compound_cfg"):
                if self.query("#compound-table"):
                    self._compound_preview_metric(self._compound_selected())
            if event.pane.id in ("tab-compound", "cmp-live"):
                self._signal_live_tick()
                self._signal_live_refresh_predictions()

    def _compound_save(self, patch: dict[str, Any], what: str, scope: str | None = None) -> None:
        env = self._call("compound.save", {"patch": patch, "asset": self._compound_coin,
                                            "scope": scope or self._compound_scope})
        status = self.query_one("#compound-status", Static)
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        self._compound_cfg = env["result"]["config"]
        self._compound_render_table()
        where = (f"{self._compound_coin} only" if (scope or self._compound_scope) == "coin" else "all coins")
        status.update(f"saved for {where}: {escape(what)} (config {env['result']['config_hash']})")

    @on(CompoundTable.Toggle)
    def _compound_click_toggle(self, event: CompoundTable.Toggle) -> None:
        table = self.query_one("#compound-table", CompoundTable)
        if 0 <= event.row < table.row_count:
            self._compound_toggle(str(table.ordered_rows[event.row].key.value))

    @on(Button.Pressed, "#compound-toggle")
    def _compound_toggle(self, cid: str | None = None) -> None:
        cid = cid if isinstance(cid, str) else self._compound_selected()
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
        # Tuned settings are this coin's own numbers: never pushed onto the other coins.
        self._compound_save({"components": patch}, f"tuned settings for {', '.join(sorted(patch))}", scope="coin")
        self._compound_tuned.clear()

    @on(Button.Pressed, "#compound-reset")
    def _compound_reset(self) -> None:
        env = self._call("compound.reset", {"asset": self._compound_coin, "scope": self._compound_scope})
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
            self._compound_live.clear()
            self._compound_render_table()
            self.query_one("#compound-status", Static).update("every component back to its default")
        else:
            self.query_one("#compound-status", Static).update(f"[red]{escape(self._msg(env))}[/]")

    # Not exclusive: an auto-forward tick must not cancel a backtest that is still running.
    @work(thread=True, group="compound")
    def _compound_job(self, name: str, params: dict[str, Any], label: str, log_key: str = "") -> None:
        self.call_from_thread(self.query_one("#compound-status", Static).update, f"{label}…")
        env = self._call_with_progress(name, params, log_key or "Compound backtest") if name == "compound.backtest" else self._call(name, params)
        self.call_from_thread(self._compound_after, name, env, log_key)

    def _compound_after(self, name: str, env: dict[str, Any], log_key: str = "") -> None:
        status = self.query_one("#compound-status", Static)
        if name == "compound.backtest":
            result = env.get("result") or {}
            self._append_log(log_key or "Compound backtest", self._msg(env) if not env["ok"] else
                             f"Finished: {result.get('configurations', 0)} configurations on {result.get('assets', [])}; skipped {result.get('skipped', [])}")
        if not env["ok"]:
            status.update(f"[red]{escape(self._msg(env))}[/]")
            return
        r = env["result"]
        if name == "compound.signal":
            self._compound_render_signal(r)
            status.update(f"live call scored from {r.get('bars_used', '?')} closed 5m bars")
        elif name == "compound.backtest":
            status.update(f"backtest {r['run_id']}: {r['configurations']} configurations on "
                          f"{', '.join(r['assets']) or '-'}" + (f"; skipped {', '.join(r['skipped'])}" if r["skipped"] else ""))
            self._compound_load_results()
            self._compound_load_overview()
        elif name == "compound.forward_tick":
            self._compound_last_bar = int(r.get("bar_ts") or 0)
            adopted = r.get("adopted") or {}
            status.update(f"forward: bar {r.get('bar_ts')} call {r['call']}"
                          f"{' recorded' if r['recorded'] else ' (already recorded)'}, "
                          f"{r['resolved']} earlier call(s) resolved"
                          + (f"; autopilot adopted tuned settings for {', '.join(sorted(adopted))}" if adopted else ""))
            if adopted:
                self._compound_reload_config()
                self._compound_load_autopilot()
            self._compound_load_results()

    def _compound_render_signal(self, r: dict[str, Any]) -> None:
        for hero in self.query("#compound-hero"):
            hero.update(shell.signal_hero(r))
        when = time.strftime("%H:%M UTC", time.gmtime(r["decided_at"]))
        blocked = ", ".join(r["blocked_by"]) or "none"
        self.query_one("#compound-call", Static).update(Text(
            f"{r['asset']} next 5m from {when}: {r['call']}   composite {r['composite']}   "
            f"coverage {r['coverage']}   agreement {r['agreement']}\n"
            f"regime {r['regime']} · trend stage {r['trend_stage']} · cycle phase {r['cycle_phase']} · "
            f"round trip {r['round_trip_bps']} bps · gates blocking: {blocked}\n"
            + compound_mod.wallet_line(r.get("wallet") or {}, r.get("sizing") or {})))
        rel = r.get("relations") or {}
        bits = [f"{x['a']} vs {x['b']} ({x['corr']:+.2f})" for x in rel.get("opposed", [])[:4]]
        dups = [f"{x['a']} ~ {x['b']} ({x['corr']:+.2f})" for x in rel.get("duplicates", [])[:4]]
        self.query_one("#compound-relations", Static).update(Text(
            ("Enabled metrics that FIGHT each other (they cancel; keep one side): " + "; ".join(bits) + ". "
             if bits else "No enabled metrics oppose each other. ")
            + ("Duplicates in different families (same evidence counted twice): " + "; ".join(dups) + "."
               if dups else "")))
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
        env = self._call("compound.results", {"asset": self._compound_coin}, quiet=True)
        results = self.query_one("#compound-results", GlossaryTable)
        results.clear()
        self._compound_bt = {}
        window_note = ""
        if env["ok"] and env["result"]["run_id"]:
            window_note = (f"{env['result']['configurations_on_this_oos_window']} configurations scored on "
                           "this out-of-sample window so far (the multiple-testing denominator). ")
        self.query_one("#compound-bt-status", Static).update(Text(
            compound_mod.run_summary(env["result"]["rows"], env["result"].get("configurations_on_this_oos_window"))
            if env["ok"] else self._msg(env)))
        self.query_one("#compound-tested", Static).update(Text(
            compound_mod.tested_line(self._compound_coin, env["result"]["rows"] if env["ok"] else [],
                                     self._compound_cfg)))
        self._compound_result_rows = list(env["result"]["rows"]) if env["ok"] else []
        if env["ok"]:
            for row in env["result"]["rows"]:
                horizons = {h["bars"]: h for h in row.get("oos_horizons") or []}
                results.add_row(
                    compound_mod.readable_label(row["label"]), _pct(row["oos_return"]),
                    _pct(row.get("oos_buy_hold")), _num(row["oos_sharpe"]), str(row["oos_trades"]),
                    _num(row["oos_fees_pct"]), _num((horizons.get(12) or {}).get("net_bps")),
                    _num((horizons.get(288) or {}).get("net_bps")), str(row["oos_calls"]), _pct(row["oos_hit"]),
                    _num(row["oos_z"]), _num(row["oos_gross_bps"]), _pct(row["oos_max_dd"]),
                    "yes" if row["ranked"] else "no")
                if row["label"].startswith("only:"):
                    self._compound_bt[row["label"][5:]] = _pct(row["oos_hit"])
                elif row["label"] == "compound":
                    self._compound_bt["_compound"] = _pct(row["oos_hit"])
        fenv = self._call("compound.forward_status", {"asset": self._compound_coin}, quiet=True)
        fwd = self.query_one("#compound-forward-table", GlossaryTable)
        fwd.clear()
        self._compound_fwd = {}
        self._compound_forward_rows = []
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
                f"Without gates: {u['decided']} calls, hit {_pct(u['hit_rate'])}. "
                + (f"Paper $ at wallet size: {f['paper']['calls']} calls, net ${f['paper']['net_usd']:,.2f} "
                   f"after ${f['paper']['costs_usd']:,.2f} costs." if f.get("paper", {}).get("calls") else
                   "Paper $ at wallet size: no sized calls yet.")))
            hz = f.get("horizon_results", {"horizons": {}, "recent": []})
            htable = self.query_one("#compound-horizons", GlossaryTable)
            htable.clear()
            parts = []
            for minutes in (1, 5, 30):
                item = hz["horizons"].get(minutes, hz["horizons"].get(str(minutes), {}))
                parts.append(f"{minutes}m: {item.get('recorded', 0)} recorded, "
                             f"{item.get('resolved', 0)} resolved, {item.get('pending', 0)} pending, "
                             f"hit {_pct(item.get('hit_rate'))}")
            self.query_one("#compound-horizon-summary", Static).update(" | ".join(parts))
            for row in reversed(hz["recent"]):
                htable.add_row(time.strftime("%m-%d %H:%M", time.gmtime(row["issued_at"])),
                               time.strftime("%m-%d %H:%M", time.gmtime(row["start"])), str(row["minutes"]), row["call"], _num(row["ret_bps"]),
                               {True: "yes", False: "no"}.get(row["hit"], "-"))
            self._compound_forward_rows = list(reversed(f["recent"]))
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
        self._compound_job("compound.signal", {"asset": self._compound_coin}, "scoring the latest closed bar")

    @on(Button.Pressed, "#compound-backtest")
    def _compound_backtest(self) -> None:
        log_key = self._start_log("Compound backtest", "Starting " + self._compound_coin)
        self._compound_job("compound.backtest", {"asset": self._compound_coin},
                           "backtesting the compound and each enabled metric alone", log_key)

    @on(Button.Pressed, "#compound-forward")
    def _compound_forward(self) -> None:
        self._compound_job("compound.forward_tick", {"asset": self._compound_coin}, "forward tick")

    @on(Button.Pressed, "#compound-auto")
    def _compound_auto_toggle(self) -> None:
        self._compound_auto = not self._compound_auto
        self.query_one("#compound-auto", Button).label = (
            f"Auto-forward: {'on' if self._compound_auto else 'off'}")
        if self._compound_auto:
            self._compound_forward()

    def _compound_auto_tick(self) -> None:
        """Every 20 s: show the unattended state; sample each minute if Auto is on.

        Defensive like `_tick`: the timer can fire while the app is tearing down, when `query_one`
        raises NoMatches (a slow CI runner hit exactly that).
        """
        if not self.query("#compound-unattended"):
            return
        try:
            self._compound_show_unattended()
        except NoMatches:
            return
        if not getattr(self, "_compound_auto", False):
            return
        now = time.time()
        latest_minute = int(now) // 60
        if latest_minute > self._compound_last_minute and now % 60 >= 5:
            self._compound_last_minute = latest_minute
            self._compound_forward()

    def _compound_show_unattended(self) -> None:
        env = self._call("compound.unattended_status", {"asset": self._compound_coin}, quiet=True)
        label = self.query_one("#compound-unattended", Static)
        if not env["ok"]:
            label.update(Text(f"unattended: {self._msg(env)}"))
            return
        s = env["result"]
        running = [asset for asset, row in self._compound_overview_rows.items() if row.get("unattended")]
        coverage = (f" Running coins ({len(running)}): {', '.join(running)}."
                    if running else " See All coins for running coverage.")
        if s["running"]:
            since = time.strftime("%m-%d %H:%M UTC", time.gmtime(s["since"])) if s.get("since") else "?"
            label.update(Text(f"unattended training RUNNING for {s['asset']} since {since} (pid {s['pid']}); "
                              f"log {s['log']}.{coverage}"))
            # Its calls (and autopilot's adoptions) land from another process: reload once a minute.
            if time.time() - self._compound_last_refresh > 60:
                self._compound_last_refresh = time.time()
                self._compound_reload_config()
                self._compound_load_autopilot()
                self._compound_load_results()
                self._compound_load_overview()
        else:
            label.update(Text(f"unattended training stopped for {s['asset']}"
                              + (f" · last: {s['last_line'][:120]}" if s.get("last_line") else "") + coverage))

    def _compound_load_overview(self) -> None:
        env = self._call("compound.overview", quiet=True)
        table = self.query_one("#compound-overview", GlossaryTable)
        table.clear()
        if not env["ok"]:
            return
        self._compound_overview_rows = {r["asset"]: r for r in env["result"]["coins"]}
        for r in env["result"]["coins"]:
            table.add_row(r["asset"], "yes" if r["own_settings"] else "-", r["data"] or "none",
                          r["backtest_verdict"], _pct(r["backtest_hit"]), str(r["fwd_calls"]), _pct(r["fwd_hit"]),
                          "-" if r["paper_usd"] is None else f"{r['paper_usd']:+,.2f}",
                          "RUNNING" if r["unattended"] else ("-" if r.get("live", True) else "backtest only"),
                          key=r["asset"])

    @on(Select.Changed, "#compound-coin")
    def _compound_coin_changed(self, event: Select.Changed) -> None:
        if not isinstance(event.value, str) or event.value == getattr(self, "_compound_coin", None):
            return
        self._compound_coin = event.value
        env = self._call("compound.config", {"asset": self._compound_coin}, quiet=True)
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
            self._compound_own = env["result"]["own_settings"]
        self._compound_live.clear()
        self._compound_learned.clear()
        self._compound_tuned.clear()
        self._compound_render_table()
        self._compound_load_results()
        self._compound_show_unattended()
        self._signal_live_tick()
        self._signal_live_refresh_predictions(force=True)
        own = env["ok"] and env["result"]["own_settings"]
        self.query_one("#compound-status", Static).update(
            f"showing {self._compound_coin}" + (" (has its own settings)" if own else " (shared settings)"))

    @on(Button.Pressed, "#compound-scope")
    def _compound_scope_toggle(self) -> None:
        self._compound_scope = "coin" if self._compound_scope == "all" else "all"
        label = f"this coin ({self._compound_coin})" if self._compound_scope == "coin" else "all coins"
        self.query_one("#compound-scope", Button).label = f"Edits apply to: {label}"
        env = self._call("compound.config", {"asset": self._compound_coin}, quiet=True)
        if env["ok"]:
            self._compound_cfg = env["result"]["config"]
            self._compound_render_table()

    @on(Button.Pressed, "#compound-backtest-frontier")
    def _compound_backtest_frontier(self) -> None:
        log_key = self._start_log("Compound backtest", "Starting " + self._compound_coin)
        self._compound_job("compound.backtest", {"asset": self._compound_coin, "frontier": True},
                           "frontier: every metric alone, its strongest 2% of readings, held 1 h, 4 h and 24 h, "
                           "unlevered (about 130 configurations; a few minutes)", log_key)

    @on(Button.Pressed, "#compound-backtest-all")
    def _compound_backtest_all(self) -> None:
        log_key = self._start_log("Compound backtest", "Starting " + "all coins")
        self._compound_job("compound.backtest", {"all": True},
                           "backtesting every coin in parallel, each with its own settings", log_key)

    @on(Button.Pressed, "#compound-unattended-all")
    def _compound_unattended_all(self) -> None:
        env = self._call("compound.unattended_start", {"all": True})
        status = self.query_one("#compound-status", Static)
        if env["ok"]:
            r = env["result"]
            status.update(Text(f"unattended training started for {', '.join(r['started']) or 'no coin'}"
                               + (f"; skipped {', '.join(r['skipped'])}" if r["skipped"] else "")))
        else:
            status.update(f"[red]{escape(self._msg(env))}[/]")
        self._compound_show_unattended()
        self._compound_load_overview()

    @on(Button.Pressed, "#compound-unattended-stop-all")
    def _compound_unattended_stop_all(self) -> None:
        env = self._call("compound.unattended_stop", {"all": True})
        status = self.query_one("#compound-status", Static)
        status.update(Text(f"stop requested for {', '.join(env['result']['stopping']) or 'nothing running'}"
                           + ("; autopilot restarts them within five minutes (turn autopilot off to keep them "
                              "stopped)" if self._compound_autopilot else ""))
                      if env["ok"] else f"[red]{escape(self._msg(env))}[/]")
        self._compound_load_overview()

    @on(Button.Pressed, "#compound-unattended-start")
    def _compound_unattended_start(self) -> None:
        env = self._call("compound.unattended_start", {"asset": self._compound_coin})
        status = self.query_one("#compound-status", Static)
        if env["ok"]:
            status.update(Text(f"unattended training started for {env['result']['asset']} "
                               f"(pid {env['result']['pid']}); it keeps running after you close this console"))
        else:
            status.update(f"[red]{escape(self._msg(env))}[/]")
        self._compound_show_unattended()

    @on(Button.Pressed, "#compound-unattended-stop")
    def _compound_unattended_stop(self) -> None:
        env = self._call("compound.unattended_stop", {"asset": self._compound_coin})
        status = self.query_one("#compound-status", Static)
        if env["ok"]:
            r = env["result"]
            status.update(("stop requested; it exits after the current tick"
                           + ("; autopilot restarts it within five minutes (turn autopilot off to keep it "
                              "stopped)" if r.get("autopilot_restarts") else ""))
                          if r["stopping"] else r.get("message", ""))
        else:
            status.update(f"[red]{escape(self._msg(env))}[/]")
        self._compound_show_unattended()

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
        """Start a CPCV sweep over the picked strategy or the whole roster (`backtest.run`)."""
        pick = self.query_one("#backtest-pick", Select).value
        labels = [pick] if isinstance(pick, str) and pick != self.ROSTER_PICK else None
        self.query_one("#backtest-status", Static).update(
            f"running {labels[0]}…" if labels else "running the whole roster…")
        log_key = self._start_log("CPCV backtest", f"Starting {labels[0] if labels else 'the whole roster'}")
        if not self.runner.running:
            self._cpcv_active_log = log_key
        try:
            execution = self._simulation_form("backtest")
            execution["longest_contiguous"] = self.query_one("#backtest-longest-contiguous", Checkbox).value
        except ValueError:
            self.query_one("#backtest-status", Static).update("Enter a leverage and confidence number.")
            return
        self._sweep_worker(labels, log_key, execution)

    @work(thread=True, group="sweep")
    def _sweep_worker(self, labels: list[str] | None = None, log_key: str = "",
                      execution: dict[str, Any] | None = None) -> None:
        """Thread only so the UI stays live; the sweep itself is the registry handler."""
        params = dict(execution or {})
        if labels:
            params["labels"] = labels
        env = self._call("backtest.run", params)
        self.call_from_thread(self._render_results, env, log_key)

    def _render_results(self, env: dict[str, Any], log_key: str = "") -> None:
        """Fill the results table, best median Sharpe first."""
        status = self.query_one("#backtest-status", Static)
        self._append_log(log_key or "CPCV backtest", self._msg(env) if not env["ok"] else env["result"]["message"])
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
        execution = r.get("execution") or {}
        assumptions = (f" · Jupiter Perps {execution['leverage'] if execution['use_leverage'] else 1:g}x "
                       f"{'long/short' if execution['allow_short'] else 'long only'}, "
                       f"min confidence {execution['min_confidence']:g}" if execution else "")
        status.update(r["message"] + (f" · best Sharpe: {best['label']} {best['net_pct_text']}"
                                      if best else "") + assumptions)

    @on(Button.Pressed, "#btn-run-untested")
    def _run_untested_sweep(self) -> None:
        """Start backtesting, at once and in the background, every strategy never tested or with
        little testing (`queue.backtest`, scope undertested).

        It used to run research/sweep_untested.py, which listed the untested strategies and then
        backtested a fixed handful on one horizon, so the button seemed to find work and do none.
        """
        status = self.query_one("#backtest-status", Static)
        self._close_finished_worker_logs()
        tail = BacktestLog(bgqueue.BG_DIR / "worker.log")
        env = self._call("queue.backtest", {"scope": "undertested"})
        self._start_log("Strategy backtest", self._msg(env) if not env["ok"] else env["result"]["message"],
                        tail if env["ok"] and env["result"].get("started") else None)
        if not env["ok"]:
            status.update(Text(self._msg(env), style="red"))
            return
        r = env["result"]
        names = r.get("strategies") or []
        shown = ", ".join(names[:12]) + (f" +{len(names) - 12} more" if len(names) > 12 else "")
        status.update(Text(r["message"] + (f": {shown}" if shown and r["started"] else "")
                           + (" · progress below and on the Queue tab" if r["started"] else "")))
        self._show_bg_progress()
        self._refresh_strategy_history()

    def _show_bg_progress(self) -> None:
        line = self.query("#backtest-bg-status")
        if not line:
            return
        env = self._call("queue.progress", quiet=True)
        if env["ok"]:
            line.first(Static).update(Text("Background backtests: " + env["result"]["summary"]))

    # -- execute (dry run) -----------------------------------------------

    @on(Button.Pressed, "#btn-paper-start")
    def _paper_start(self) -> None:
        """Run one backtest and open a replay cursor over it (`paper.start`)."""
        value = self.query_one("#exec-strategy", Select).value
        label = value if isinstance(value, str) else ""
        key = self._start_log("Replay", f"Starting historical replay for {label or 'no selection'}")
        self._paper_start_job(label, key)

    @work(thread=True, exclusive=True)
    def _paper_start_job(self, label: str, key: str) -> None:
        env = self._call("paper.start", {"label": label})
        self.call_from_thread(self._append_log, key, env["result"]["text"] if env["ok"] else self._msg(env))
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
        elif pane == "tab-forwardtest":
            self._forward_refresh()
        elif pane == "tab-paper-experiments":
            self._paper_exp_refresh()
        elif pane == "tab-queue" and self.query("#queue-status"):
            # No once-only guard: unlike Cumulative and Docs, this tab's source
            # is being written by another process right now, so re-reading on
            # every activation is the correct behaviour rather than waste.
            self._refresh_queue()
        elif pane == "tab-wallet":
            self._refresh_portfolio_notice()
            self._coinbase_show(self._call("coinbase.account", quiet=True))
            self._coinbase_order_state_start()
            self._coinbase_pairs_start()
            self._call("portfolio.notice", {"mark_seen": True}, quiet=True)
        elif pane == "tab-advanced-order":
            self._coinbase_order_state_start()
            self._jupiter_order_state_start()
        elif pane == "tab-liquidity":
            self._refresh_liquidity(force=True)
        elif pane == "tab-bots":
            if not self._bots_loaded:
                self._bots_loaded = True
                self._bots_load()
            self._bots_tick()
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
        self.query_one("#live-run-recommendation", Static).update(
            "Historical simulation only. No choice here is a profitability recommendation.")

    @on(Button.Pressed, "#btn-refresh-live-run")
    def _btn_refresh_live_run(self) -> None:
        self._refresh_live_run()

    @on(Select.Changed, "#live-run-choice")
    def _live_run_choice(self, event: Select.Changed) -> None:
        if isinstance(event.value, str):
            self.query_one("#live-run-strategy", Input).value = event.value
            self._live_run_preset = None

    @on(Button.Pressed, "#btn-spawn-dryrun")
    def _btn_spawn_dryrun(self) -> None:
        shown = self.query_one("#live-run-strategy", Input).value.strip()
        preset = getattr(self, "_live_run_preset", None)
        strategy_name = preset[1] if preset and preset[0] == shown else shown
        status = self.query_one("#live-run-status", Static)
        if not strategy_name:
            status.update("Choose a strategy first.")
            return
        status.update(f"Running historical simulation for {shown}…")
        self.query_one("#live-run-output", TextArea).text = ""
        key = self._start_log("Dry run", f"Starting {shown}; no orders")
        self._run_selected_dryrun(shown, strategy_name, key)

    @work(thread=True)
    def _run_selected_dryrun(self, shown: str, strategy_name: str, key: str) -> None:
        env = self._call_with_progress("live.spawn_dryrun", {"strategy": strategy_name}, key)
        if env["ok"]:
            text = env["result"]["stdout"]
            status = f"Finished {shown} · {env['result']['net_pct_text']}"
        else:
            text = self._msg(env)
            status = f"Dry run failed: {text}"
        self.call_from_thread(self._finish_selected_dryrun, key, status, text)

    def _finish_selected_dryrun(self, key: str, status: str, text: str) -> None:
        self._append_log(key, text)
        self.query_one("#live-run-status", Static).update(status)
        self.query_one("#live-run-output", TextArea).text = text

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
            yield Static("[b]Top 5 configurations on SOL[/b]: each one's CPCV median Sharpe, spread, share "
                         "of paths positive, median net return, trades and path count.", classes="table-title")
            configs = GlossaryTable(id="top5-table")
            configs.add_columns("#", "configuration", "horizon", "signals",
                                "median Sharpe", "IQR", "% paths +",
                                "backtest median net %", "trades", "paths")
            configs.cursor_type = "row"
            yield ExportPanel(configs)
            yield Static(
                "[b]Transfer test — the same configurations off SOL[/b]  "
                "(fitted on SOL; a recommendation that only works there is "
                "an overfit, and two of the five go negative off-asset)",
                classes="table-title",
            )
            transfers = GlossaryTable(id="top5-transfers")
            transfers.add_columns("#", "configuration", "asset",
                                  "median Sharpe", "Δ vs SOL", "% paths +",
                                  "backtest median net %", "trades", "paths")
            yield ExportPanel(transfers)
            yield Static(
                "Benchmark that must stay in view: buy_and_hold, zero "
                "parameters, medium/long median Sharpe +0.534, 68% of paths "
                "positive, +9.4% backtest median net return — 2nd of 25 at the medium "
                "horizon. A configuration that does not clearly beat it is "
                "not worth its complexity.",
                classes="hint",
            )
            with Horizontal(classes="form-row"):
                yield Button("Test status", id="status-top5")
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
        log_key = self._start_log("CPCV backtest", "Starting the whole roster")
        if not self.runner.running:
            self._cpcv_active_log = log_key
        self._sweep_worker(None, log_key)

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
                "Reads the public wallets from Settings (Base discovery uses configured CDP when available). "
                "The wallet scan uses no private key or transaction. Every figure is wallet (live): a read of real money at "
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
            yield Static("[b]Coinbase account[/b] — trading balances and separate portfolio positions.", classes="table-title")
            with Horizontal(classes="form-row"):
                yield Button("Sync Coinbase", id="coinbase-sync")
                yield Button("Download Coinbase markets", id="coinbase-markets")
                yield Static("", id="coinbase-status")
            with Vertical(id="coinbase-manual-ticket") as ticket:
                ticket.border_title = "Manual Coinbase spot order"
                yield Static("[b]Manual Coinbase spot order[/b] — live orders start disarmed.",
                             classes="table-title")
                yield Static("Market orders quoted in USD or USDC only. BUY spends the quote currency; SELL sells the base coin. "
                             "Quotes and fees are estimates, and the final fill may differ.", classes="hint")
                with Horizontal(classes="form-row"):
                    yield Input(placeholder="Filter Coinbase spot pairs", id="coinbase-pairs-query")
                    yield Button("Filter pairs", id="coinbase-pairs-filter")
                yield Static("Loading the saved spot-pair catalog…", id="coinbase-pairs-status", markup=False)
                pairs = GlossaryTable(id="coinbase-pairs-table")
                pairs.cursor_type = "row"
                pairs.add_columns("Coinbase spot pair — select to use")
                yield ExportPanel(pairs)
                with Horizontal(classes="form-row"):
                    yield Input(value="SOL-USDC", placeholder="Pair, e.g. SOL-USDC", id="coinbase-order-product")
                    yield Select([("BUY", "BUY"), ("SELL", "SELL")], value="BUY", allow_blank=False,
                                 id="coinbase-order-side")
                    yield Input(placeholder="Amount to spend in quote currency", id="coinbase-order-size")
                with Horizontal(classes="form-row"):
                    yield Checkbox("Arm LIVE order submission", value=False, id="coinbase-order-armed")
                    yield Button("Review order", id="coinbase-order-preview", disabled=True)
                    yield Button("Place LIVE order", variant="error", id="coinbase-order-submit", disabled=True)
                    yield Button("Place LIVE immediately", variant="error", id="coinbase-order-quick", disabled=True)
                yield Checkbox("Skip per-order review for this session", value=False, id="coinbase-order-skip-review")
                yield Static("When selected, an armed LIVE order can execute immediately when you press Place LIVE immediately. "
                             "This setting resets when the app closes.", classes="hint")
                yield Static("Disarmed. Checking previous order state before a review can start.",
                             id="coinbase-order-message", markup=False)
                yield Static("", id="coinbase-order-review", markup=False)
                with Horizontal(classes="form-row"):
                    yield Input(placeholder="Coinbase order ID", id="coinbase-order-id")
                    yield Button("Check order", id="coinbase-order-check")
                    yield Button("Refresh order safety", id="coinbase-order-state")
                yield Static("No order submitted in this session.", id="coinbase-order-receipt", markup=False)
            yield Static("Coinbase holdings — available and held balances", classes="table-title")
            cbhold = GlossaryTable(id="coinbase-holdings")
            cbhold.add_columns("portfolio", "asset", "available", "hold")
            yield ExportPanel(cbhold)
            yield Static("[b]Coinbase positions[/b] — totals are approximate; staking is shown separately.", classes="table-title")
            cbpositions = GlossaryTable(id="coinbase-positions")
            cbpositions.add_columns("portfolio", "asset", "account type", "quantity", "value $")
            yield ExportPanel(cbpositions)
            yield Static("[b]Holdings[/b]", classes="table-title")
            holdings = GlossaryTable(id="wallet-holdings")
            holdings.add_columns("chain", "asset", "amount", "price $", "value $ (wallet (live))", "status")
            yield ExportPanel(holdings)
            yield Static("[b]Contracts and accounts each holding lives in[/b]", classes="table-title")
            contracts = GlossaryTable(id="wallet-contracts")
            contracts.add_columns("chain", "holding", "kind", "address", "program", "explorer")
            yield ExportPanel(contracts)

    def _advanced_order_pane(self) -> ComposeResult:
        """Dedicated Money view for the advanced order ticket."""
        with VerticalScroll():
            with Vertical(id="advanced-order-ticket") as ticket:
                ticket.border_title = "Advanced order ticket"
                yield Static("Coinbase spot orders ($100 cap); Jupiter Swap v2 spot market swaps ($100 cap).", classes="hint")
                with Horizontal(classes="form-row"):
                    yield Select([("Coinbase", "coinbase"), ("Jupiter", "jupiter")], value="coinbase",
                                 allow_blank=False, id="advanced-venue")
                    yield Select([("Market", "market"), ("Limit (GTC)", "limit"),
                                  ("Stop-limit (GTC)", "stop_limit"), ("Take-profit + stop bracket (SELL)", "bracket")],
                                 value="market", allow_blank=False, id="advanced-type")
                    yield Select([("BUY", "BUY"), ("SELL", "SELL")], value="BUY", allow_blank=False, id="advanced-side")
                with Horizontal(classes="form-row"):
                    yield Input(value="SOL-USDC", placeholder="Pair, e.g. SOL-USDC", id="advanced-product")
                    yield Input(placeholder="Order amount", id="advanced-size")
                    yield Select([("Auto (BUY quote / SELL coin)", "auto"), ("USD / quote", "quote"),
                                  ("% available balance", "percent"), ("Coin units", "base")],
                                 value="auto", allow_blank=False, id="advanced-unit")
                with Horizontal(classes="form-row"):
                    yield Input(placeholder="Jupiter token symbol or mint", id="advanced-token-query")
                    yield Button("Find Jupiter token", id="advanced-token-search")
                yield Static("Search results include full mint addresses. Jupiter order execution is unavailable until verified.",
                             id="advanced-token-results", markup=False)
                with Horizontal(classes="form-row"):
                    yield Input(placeholder="Limit / take-profit price (quote currency)", id="advanced-limit-price", disabled=True)
                    yield Input(placeholder="Stop trigger price (quote currency)", id="advanced-stop-price", disabled=True)
                with Horizontal(classes="form-row"):
                    yield Select([("Spot 1x", "1x"), ("2x — unavailable", "2x"), ("3x — unavailable", "3x")],
                                 value="1x", allow_blank=False, id="advanced-leverage")
                    yield Select([("Spot / long", "long"), ("Short — unavailable", "short")],
                                 value="long", allow_blank=False, id="advanced-position")
                yield Static("Leveraged and short execution require a supported venue and are not available in this ticket.", classes="hint")
                with Horizontal(classes="form-row"):
                    yield Checkbox("Arm advanced LIVE order", value=False, id="advanced-armed")
                    yield Button("Review advanced order", id="advanced-preview", disabled=True)
                    yield Button("Review % order", id="advanced-percent-preview", disabled=True)
                    yield Button("Review conditional order", id="advanced-conditional-preview", disabled=True)
                    yield Button("Place advanced LIVE order", id="advanced-submit", variant="error", disabled=True)
                    yield Button("Place advanced LIVE immediately", id="advanced-quick", variant="error", disabled=True)
                    yield Button("Place % LIVE immediately", id="advanced-percent-quick", variant="error", disabled=True)
                    yield Button("Place conditional LIVE immediately", id="advanced-conditional-quick", variant="error", disabled=True)
                yield Checkbox("Skip per-order review for this session", value=False, id="advanced-skip-review")
                yield Static("Quick mode can place live orders immediately. Conditional orders can remain open; stop execution and fill are not guaranteed.", classes="hint")
                yield Static("Price graph unavailable: no historical price series loaded for this ticket.", id="advanced-chart-status", markup=False)
                yield Sparkline([], id="advanced-chart")
                yield Static("Strategy forecast unavailable: no ranked forecast loaded for this ticket.", id="advanced-forecast-status", markup=False)
                yield Static("Disarmed. Choose a supported Coinbase market order.", id="advanced-message", markup=False)
                yield Static("", id="advanced-review", markup=False)
                yield Static("No advanced order submitted in this session.", id="advanced-receipt", markup=False)

    def _coinbase_order_values(self) -> tuple[str, str, str, str]:
        product = self.query_one("#coinbase-order-product", Input).value.strip().upper()
        side = str(self.query_one("#coinbase-order-side", Select).value)
        size = self.query_one("#coinbase-order-size", Input).value.strip()
        return product, side, size, "quote" if side == "BUY" else "base"

    @on(Button.Pressed, "#coinbase-pairs-filter")
    @on(Input.Submitted, "#coinbase-pairs-query")
    def _coinbase_pairs_filter(self) -> None:
        self._coinbase_pairs_start()

    def _coinbase_pairs_start(self) -> None:
        self._coinbase_pairs_generation += 1
        token = self._coinbase_pairs_generation
        query = self.query_one("#coinbase-pairs-query", Input).value.strip()
        self.query_one("#coinbase-pairs-status", Static).update("Loading saved Coinbase spot pairs…")
        self._coinbase_pairs_worker(query, token)

    @work(thread=True, group="coinbase-pair-catalog", exit_on_error=False)
    def _coinbase_pairs_worker(self, query: str, token: int) -> None:
        try:
            env = self._call("coinbase.pairs", {"query": query}, quiet=True)
        except Exception:
            env = {"ok": False, "error": {"message": "Could not load the saved spot-pair catalog."}}
        try:
            self.call_from_thread(self._coinbase_pairs_done, env, token)
        except (RuntimeError, NoMatches):
            pass  # The console closed while the catalog was being read.

    def _coinbase_pairs_done(self, env: dict[str, Any], token: int) -> None:
        if token != self._coinbase_pairs_generation:
            return
        status = self.query_one("#coinbase-pairs-status", Static)
        if not env.get("ok"):
            status.update(self._msg(env))
            return
        result = env.get("result") or {}
        pairs = result.get("pairs")
        if not isinstance(pairs, list) or any(not isinstance(pair, str) for pair in pairs):
            status.update("The saved spot-pair catalog is invalid. Download Coinbase markets again.")
            return
        table = self.query_one("#coinbase-pairs-table", DataTable)
        table.clear()
        seen: set[str] = set()
        for pair in pairs:
            if pair not in seen:
                table.add_row(pair, key=pair)
                seen.add(pair)
        state = "complete" if result.get("complete") is True else "incomplete or not downloaded"
        status.update(f"Spot pairs: {len(seen)} matching of {result.get('count', '?')} saved · {state}. "
                      "Select a row to fill the order pair; trading eligibility is checked during review.")

    @on(DataTable.RowSelected, "#coinbase-pairs-table")
    def _coinbase_pair_selected(self, event: DataTable.RowSelected) -> None:
        if self._coinbase_order_busy:
            self.query_one("#coinbase-order-message", Static).update("Wait for the current order operation to finish.")
            return
        if not event.row_key or not event.row_key.value:
            return
        # Selection edits the form only; it cannot review, arm, or submit an order.
        self.query_one("#coinbase-order-armed", Checkbox).value = False
        self.query_one("#coinbase-order-product", Input).value = str(event.row_key.value)
        self.query_one("#coinbase-order-message", Static).update("Pair selected. Review the amount before placing an order.")

    @on(Button.Pressed, "#advanced-token-search")
    @on(Input.Submitted, "#advanced-token-query")
    def _advanced_token_search(self) -> None:
        query = self.query_one("#advanced-token-query", Input).value.strip()
        if not query:
            self.query_one("#advanced-token-results", Static).update("Enter a token symbol or mint.")
            return
        self.query_one("#advanced-token-results", Static).update("Searching Jupiter tokens…")
        self._advanced_token_search_worker(query)

    @work(thread=True, exit_on_error=False, group="advanced-token-search")
    def _advanced_token_search_worker(self, query: str) -> None:
        try:
            env = self._call("jupiter.tokens_search", {"query": query}, quiet=True)
            self.call_from_thread(self._advanced_token_search_done, query, env)
        except (RuntimeError, NoMatches):
            pass

    def _advanced_token_search_done(self, query: str, env: dict[str, Any]) -> None:
        if not self.query("#advanced-token-query") or self.query_one("#advanced-token-query", Input).value.strip() != query:
            return
        target = self.query_one("#advanced-token-results", Static)
        if not env.get("ok"):
            target.update(self._msg(env))
            return
        tokens = (env.get("result") or {}).get("tokens", [])
        target.update("\n".join(f"{t['symbol']} · {t['name']} · {t['mint']} · decimals {t['decimals']} · "
                                f"{'verified' if t['verified'] else 'unverified'}" for t in tokens)
                      or "No matching tokens.")

    def _advanced_values(self) -> tuple[str, str, str, str, str, str]:
        venue = str(self.query_one("#advanced-venue", Select).value)
        kind = str(self.query_one("#advanced-type", Select).value)
        side = str(self.query_one("#advanced-side", Select).value)
        product = self.query_one("#advanced-product", Input).value.strip().upper()
        size = self.query_one("#advanced-size", Input).value.strip()
        unit = str(self.query_one("#advanced-unit", Select).value)
        if unit == "auto":
            unit = "base" if kind != "market" or side == "SELL" else "quote"
        return venue, kind, side, product, size, unit

    def _advanced_signature(self) -> tuple[str, ...]:
        values = self._advanced_values()
        kind = values[1]
        limit = self.query_one("#advanced-limit-price", Input).value.strip() if kind != "market" else ""
        stop = self.query_one("#advanced-stop-price", Input).value.strip() if kind in ("stop_limit", "bracket") else ""
        leverage = str(self.query_one("#advanced-leverage", Select).value)
        position = str(self.query_one("#advanced-position", Select).value)
        return (*values, limit, stop, leverage, position)

    def _advanced_supported(self) -> bool:
        venue, kind, side, product, size, unit = self._advanced_values()
        if (side not in ("BUY", "SELL") or not product or not size
                or self.query_one("#advanced-leverage", Select).value != "1x"
                or self.query_one("#advanced-position", Select).value != "long"):
            return False
        if venue == "coinbase":
            if kind == "market":
                return unit in (("quote", "base", "percent") if side == "BUY" else ("base", "percent"))
            if kind not in ("limit", "stop_limit", "bracket") or unit != "base" or (kind == "bracket" and side != "SELL"):
                return False
            return bool(self.query_one("#advanced-limit-price", Input).value.strip()
                        and (kind == "limit" or self.query_one("#advanced-stop-price", Input).value.strip()))
        elif venue == "jupiter":
            if kind != "market":
                return False
            return unit in (("quote", "base") if side == "BUY" else ("base",))
        return False

    def _advanced_controls(self) -> None:
        if not self.query("#advanced-preview"):
            return
        busy = self._coinbase_order_busy
        for selector in ("#advanced-venue", "#advanced-type", "#advanced-side", "#advanced-product",
                         "#advanced-size", "#advanced-unit", "#advanced-armed", "#advanced-skip-review",
                         "#advanced-leverage", "#advanced-position"):
            self.query_one(selector).disabled = busy
        venue, kind, side, _, _, unit = self._advanced_values()
        conditional = kind != "market"
        self.query_one("#advanced-limit-price", Input).disabled = busy or not conditional or venue == "jupiter"
        self.query_one("#advanced-stop-price", Input).disabled = busy or kind not in ("stop_limit", "bracket") or venue == "jupiter"
        supported = self._advanced_supported()
        locked = busy or self._coinbase_order_unknown or not supported
        quick = self.query_one("#advanced-skip-review", Checkbox).value
        armed = self.query_one("#advanced-armed", Checkbox).value
        preview = self._advanced_preview_data
        valid = bool(preview and preview.get("values") == self._advanced_signature()
                     and isinstance(preview.get("expires_at"), (int, float)) and preview["expires_at"] > time.time())
        percent = self._advanced_values()[5] == "percent"
        for name, show in (("#advanced-preview", not percent and not conditional),
                           ("#advanced-percent-preview", percent and not conditional),
                           ("#advanced-conditional-preview", conditional)):
            button = self.query_one(name, Button)
            button.display = show
            button.disabled = locked
        submit = self.query_one("#advanced-submit", Button)
        submit.display = not quick
        submit.disabled = locked or not armed or not valid
        fast = self.query_one("#advanced-quick", Button)
        fast.display = quick and not percent and not conditional
        fast.disabled = locked or not armed or not quick or percent or conditional or (venue == "jupiter")
        percent_fast = self.query_one("#advanced-percent-quick", Button)
        percent_fast.display = quick and percent and not conditional
        percent_fast.disabled = locked or not armed or not quick or not percent or conditional or (venue == "jupiter")
        conditional_fast = self.query_one("#advanced-conditional-quick", Button)
        conditional_fast.display = quick and conditional
        conditional_fast.disabled = locked or not armed or not quick or not conditional or (venue == "jupiter")

    @on(Input.Changed, "#advanced-product")
    @on(Input.Changed, "#advanced-size")
    @on(Input.Changed, "#advanced-limit-price")
    @on(Input.Changed, "#advanced-stop-price")
    @on(Select.Changed, "#advanced-venue")
    @on(Select.Changed, "#advanced-type")
    @on(Select.Changed, "#advanced-side")
    @on(Select.Changed, "#advanced-unit")
    @on(Select.Changed, "#advanced-leverage")
    @on(Select.Changed, "#advanced-position")
    def _advanced_changed(self) -> None:
        self._advanced_generation += 1
        self._advanced_preview_data = None
        if not self.query("#advanced-review"):
            return
        self.query_one("#advanced-review", Static).update("")
        venue, kind, side, _, _, unit = self._advanced_values()
        pair = self.query_one("#advanced-product", Input).value.strip().upper()
        context_key = venue + ":" + pair
        if context_key != self._advanced_context_product:
            self._advanced_context_product = context_key
            self.query_one("#advanced-chart", Sparkline).data = []
            self.query_one("#advanced-chart-status", Static).update(
                "Loading timestamped session prices…" if venue == "coinbase" else "Jupiter price history unavailable.")
            self.query_one("#advanced-forecast-status", Static).update(
                "Loading recorded forward forecasts…" if venue == "coinbase" else "Jupiter forecast unavailable.")
        if (self.query_one("#advanced-leverage", Select).value != "1x"
                or self.query_one("#advanced-position", Select).value != "long"):
            message = "Unavailable: leverage and short execution require a supported venue. No order can be placed."
        elif venue not in ("coinbase", "jupiter"):
            message = "Unavailable: this venue is not implemented. No order can be placed."
        elif venue == "jupiter":
            if kind != "market":
                message = "Jupiter supports market spot swaps only; conditional orders are unavailable."
            elif unit not in (("quote", "base") if side == "BUY" else ("base",)):
                message = "Jupiter market BUY accepts quote or coin units; SELL accepts coin units. Choose a supported unit."
            elif self.query_one("#advanced-skip-review", Checkbox).value:
                message = "Jupiter orders require explicit per-order review. Quick mode is disabled for Jupiter."
            else:
                message = "Jupiter market swap selected. Enter amount; review before placing LIVE order."
        elif kind in ("limit", "stop_limit", "bracket"):
            if unit != "base":
                message = "Conditional orders require coin units; percentage and quote sizing are unavailable."
            elif kind == "bracket" and side != "SELL":
                message = "The take-profit / stop bracket supports SELL only."
            else:
                direction = ("SELL stops trigger down; BUY stops trigger up. " if kind == "stop_limit" else
                             "Bracket limit is take-profit; stop is the trigger. " if kind == "bracket" else "")
                message = (f"GTC conditional order: {direction}Quick mode can submit immediately; "
                           "an open order locks further orders. Stop execution and fill are not guaranteed.")
        elif unit not in (("quote", "base", "percent") if side == "BUY" else ("base", "percent")):
            message = "Coinbase market BUY accepts quote or coin units; SELL accepts coin units. Choose a supported unit."
        else:
            message = ("Percentage of available quote balance for BUY or coin balance for SELL; rounded down, $100 cap."
                       if unit == "percent" else "Coinbase market order selected. Enter amount; review or use session quick mode.")
        self.query_one("#advanced-message", Static).update(message)
        self._advanced_controls()

    def _advanced_context_tick(self) -> None:
        if self._advanced_context_busy or not self.query("#advanced-product"):
            return
        if self.query_one("#main-tabs", TabbedContent).active != "tab-advanced-order":
            return
        venue, _, _, product, _, _ = self._advanced_values()
        if venue != "coinbase" or "-" not in product:
            return
        asset = product.split("-", 1)[0]
        if not asset.isalnum():
            return
        self._advanced_context_busy = True
        self._advanced_context_worker(product, asset)

    @work(thread=True, exit_on_error=False, group="advanced-market-context")
    def _advanced_context_worker(self, product: str, asset: str) -> None:
        try:
            prices = self._call("prices.status", quiet=True)
            forward = self._call("forwardtest.status", {"coins": [asset]}, quiet=True)
            observed = time.time()
            self.call_from_thread(self._advanced_context_done, product, prices, forward, observed)
        except (RuntimeError, NoMatches):
            pass
        except Exception:  # noqa: BLE001 - context failure must not affect an order
            try:
                self.call_from_thread(self._advanced_context_done, product, {"ok": False}, {"ok": False}, time.time())
            except (RuntimeError, NoMatches):
                pass

    def _advanced_context_done(self, product: str, prices: dict[str, Any], forward: dict[str, Any], now: float) -> None:
        self._advanced_context_busy = False
        if not self.query("#advanced-product") or self._advanced_values()[0] != "coinbase" or self._advanced_values()[3] != product:
            return
        price_result = prices.get("result") or {} if prices.get("ok") else {}
        quote = (price_result.get("prices") or {}).get(product) or {}
        mid, age = quote.get("mid"), quote.get("quote_age_s")
        chart_status = self.query_one("#advanced-chart-status", Static)
        if (isinstance(mid, (int, float)) and not isinstance(mid, bool) and math.isfinite(mid) and mid > 0
                and isinstance(age, (int, float)) and not isinstance(age, bool) and math.isfinite(age)
                and 0 <= age <= now):
            stamp = now - age
            history = self._advanced_price_history.setdefault(product, [])
            if not history or stamp > history[-1][0] + 0.5:
                history.append((stamp, float(mid)))
                del history[:-120]
            self.query_one("#advanced-chart", Sparkline).data = [p for _, p in history]
            freshness = "stale" if age > 30 or not price_result.get("live") else "live recorder"
            chart_status.update(f"{product} session mid-price history · {freshness} · latest "
                                f"{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(stamp))} · "
                                f"{mid:g} · {len(history)} timestamped sample(s); not an execution quote")
        else:
            self.query_one("#advanced-chart", Sparkline).data = []
            chart_status.update(f"{product} price history unavailable: no timestamped recorder quote.")
        rows = ((forward.get("result") or {}).get("rows") or []) if forward.get("ok") else []
        asset = product.split("-", 1)[0]
        eligible = [r for r in rows if r.get("asset") == asset and isinstance(r.get("resolved"), int)
                    and r["resolved"] >= 10 and isinstance(r.get("correct"), int)
                    and 0 <= r["correct"] <= r["resolved"] and r.get("last_call") in (-1, 0, 1)
                    and isinstance(r.get("settings"), list) and len(r["settings"]) == 1
                    and isinstance(r.get("last_issued"), (int, float)) and not isinstance(r["last_issued"], bool)
                    and math.isfinite(r["last_issued"]) and 0 < r["last_issued"] <= now + 86400]
        status = self.query_one("#advanced-forecast-status", Static)
        if not eligible:
            status.update(f"{asset} strategy forecast unavailable: no recorded trial with at least 10 resolved calls.")
            return
        best = max(eligible, key=lambda r: (r["correct"] / r["resolved"], r["resolved"], r["last_issued"]))
        issued = float(best["last_issued"])
        horizon = best.get("minutes", 0)
        stale = not isinstance(horizon, (int, float)) or now - issued > horizon * 60 + 120 or issued > now + 60
        direction = {-1: "DOWN", 0: "FLAT", 1: "UP"}[best["last_call"]]
        status.update(f"Top {asset}-USD recorded trial by historical accuracy: {best.get('label', '-')} · "
                      f"{best['correct']}/{best['resolved']} correct · {horizon} min · {direction} · "
                      f"issued {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(issued))}"
                      f"{' · stale' if stale else ''}. Historical ranking is not a guarantee.")

    @on(Button.Pressed, "#advanced-preview")
    @on(Button.Pressed, "#advanced-percent-preview")
    @on(Button.Pressed, "#advanced-conditional-preview")
    def _advanced_preview_pressed(self) -> None:
        if self._coinbase_order_busy or self._coinbase_order_unknown or not self._advanced_supported():
            return
        values = self._advanced_signature()
        venue, kind, side, product, size, unit, limit, stop, _, _ = values
        self._advanced_preview_data = None
        self._coinbase_order_busy = True
        self._coinbase_order_controls()
        if venue == "jupiter":
            self.query_one("#advanced-message", Static).update("Reviewing with Jupiter Swap v2. No order has been placed.")
            operation = "jupiter.order_preview"
            params = {"product_id": product, "side": side, "size": size, "size_currency": unit}
        else:
            self.query_one("#advanced-message", Static).update("Reviewing with Coinbase. No order has been placed.")
            if kind != "market":
                operation = "coinbase.order_conditional_preview"
                params = {"product_id": product, "side": side, "size": size, "order_type": kind,
                          "limit_price": limit, "stop_price": stop}
            elif unit == "percent":
                operation, params = "coinbase.order_percent_preview", {"product_id": product, "side": side, "percent": size}
            else:
                operation, params = "coinbase.order_preview", {"product_id": product, "side": side, "size": size, "size_currency": unit}
        self._advanced_worker(operation, params, self._advanced_generation, values)

    @on(Button.Pressed, "#advanced-submit")
    def _advanced_submit_pressed(self) -> None:
        self._advanced_controls()
        preview = self._advanced_preview_data
        if self.query_one("#advanced-submit", Button).disabled or not preview:
            return
        venue = (preview.get("values") or ("coinbase",))[0]
        if venue == "jupiter":
            self._advanced_submit("jupiter.order_submit", {"preview_id": preview["preview_id"], "confirm": True})
        else:
            self._advanced_submit("coinbase.order_submit", {"preview_id": preview["preview_id"], "confirm": True})

    @on(Button.Pressed, "#advanced-quick")
    @on(Button.Pressed, "#advanced-percent-quick")
    @on(Button.Pressed, "#advanced-conditional-quick")
    def _advanced_quick_pressed(self) -> None:
        self._advanced_controls()
        venue, kind, side, product, size, unit = self._advanced_values()
        if venue == "jupiter":
            return  # Jupiter orders require explicit review
        percent = unit == "percent"
        button = "#advanced-conditional-quick" if kind != "market" else "#advanced-percent-quick" if percent else "#advanced-quick"
        if self.query_one(button, Button).disabled:
            return
        if kind != "market":
            signature = self._advanced_signature()
            self._advanced_submit("coinbase.order_conditional_quick", {"product_id": product, "side": side,
                                  "size": size, "order_type": kind, "limit_price": signature[6],
                                  "stop_price": signature[7], "skip_confirm": True})
        elif percent:
            self._advanced_submit("coinbase.order_percent_quick", {"product_id": product, "side": side,
                                  "percent": size, "skip_confirm": True})
        else:
            self._advanced_submit("coinbase.order_quick", {"product_id": product, "side": side, "size": size,
                                  "size_currency": unit, "skip_confirm": True})

    def _advanced_submit(self, operation: str, params: dict[str, Any]) -> None:
        self._advanced_preview_data = None
        self._coinbase_order_preview_data = None
        self.query_one("#coinbase-order-armed", Checkbox).value = False
        self._coinbase_order_busy = True
        self._coinbase_order_unknown = True
        self._coinbase_order_controls()
        venue_name = "Jupiter" if "jupiter" in operation else "Coinbase"
        self.query_one("#advanced-message", Static).update(
            f"Submitting a LIVE order. If interrupted, reconcile onchain/{venue_name}; do not retry.")
        self._advanced_worker(operation, params, self._advanced_generation, None)

    @work(thread=True, exit_on_error=False, group="advanced-coinbase-order")
    def _advanced_worker(self, operation: str, params: dict[str, Any], generation: int,
                         values: tuple[str, ...] | None) -> None:
        try:
            env = self._call(operation, params)
        except Exception as exc:  # noqa: BLE001 - never retry an ambiguous submission
            env = {"ok": False, "error": {"message": f"{type(exc).__name__}: order operation failed"}}
        try:
            self.call_from_thread(self._advanced_done, operation, env, generation, values)
        except (RuntimeError, NoMatches):
            pass

    def _advanced_done(self, operation: str, env: dict[str, Any], generation: int,
                       values: tuple[str, ...] | None) -> None:
        self._coinbase_order_busy = False
        msg = self.query_one("#advanced-message", Static)
        preview_ops = ("coinbase.order_preview", "coinbase.order_percent_preview", "coinbase.order_conditional_preview", "jupiter.order_preview")
        if not env.get("ok"):
            reason = self._msg(env)
            if operation not in preview_ops:
                self.query_one("#advanced-armed", Checkbox).value = False
                venue_label = "Jupiter" if "jupiter" in operation else "Coinbase"
                msg.update(f"Order outcome may be unknown. Do not resubmit; reconcile onchain/{venue_label}. " + reason)
            else:
                if "unresolved" in reason.lower():
                    self._coinbase_order_unknown = True
                msg.update(reason)
            self._coinbase_order_controls()
            return
        result = env.get("result") or {}
        if operation in preview_ops:
            expires = result.get("expires_at")
            try:
                field = "balance_percentage" if operation == "coinbase.order_percent_preview" else "size"
                same_size = bool(values) and Decimal(str(result.get(field, ""))) == Decimal(values[4])
            except InvalidOperation:
                same_size = False
            same_conditional = True
            if operation == "coinbase.order_conditional_preview" and values:
                try:
                    same_conditional = (result.get("order_type") == values[1]
                                        and Decimal(str(result.get("limit_price", ""))) == Decimal(values[6])
                                        and (values[1] == "limit" or Decimal(str(result.get("stop_price", ""))) == Decimal(values[7])))
                except InvalidOperation:
                    same_conditional = False
            expected_unit = ("quote" if values and values[2] == "BUY" else "base") if values and values[5] == "percent" else (values[5] if values else "")
            product_matches = bool(values and (result.get("product_id") == values[3] or operation == "jupiter.order_preview"))
            if (not values or generation != self._advanced_generation or values != self._advanced_signature()
                    or not result.get("preview_id") or not isinstance(expires, (int, float)) or expires <= time.time()
                    or not same_size or not same_conditional or not product_matches
                    or any(str(result.get(k, "")) != v for k, v in zip(
                        ("side", "size_currency"), (values[2], expected_unit) if values else (("", ""))))):
                msg.update("Review expired or the order changed. Review it again.")
            else:
                self._advanced_preview_data = {"preview_id": result["preview_id"], "expires_at": expires, "values": values}
                estimate = result.get("estimate") if isinstance(result.get("estimate"), dict) else {}
                if operation == "jupiter.order_preview":
                    routes = " -> ".join(estimate.get("route_plan") or ["Jupiter AMM"])
                    self.query_one("#advanced-review", Static).update(
                        f"LIVE {values[2]} {values[3]} · {values[4]} {values[5]}\n"
                        f"Venue: Jupiter Swap v2 (Solana)\n"
                        f"Input: {estimate.get('in_amount', '-')}\n"
                        f"Estimated output: {estimate.get('out_amount', '-')}\n"
                        f"Price impact: {estimate.get('price_impact_pct', '-')}\n"
                        f"Route: {routes}\n"
                        f"Estimated fee: {estimate.get('fee_lamports', 5000)} lamports\n"
                        f"{result.get('notice', '')}\n"
                        "To place this order, arm live submission and press Place advanced LIVE order.")
                else:
                    self.query_one("#advanced-review", Static).update(
                        f"LIVE {values[2]} {values[3]} · {values[4]} {values[5]}\n"
                        f"Type: {values[1]} · limit: {values[6] or '-'} · stop: {values[7] or '-'}\n"
                        f"Resolved size: {result.get('size', '')} {result.get('size_currency', '')}\n"
                        f"{result.get('sizing_notice', '')}\n"
                        f"Coinbase estimate: {json.dumps(result.get('estimate'), ensure_ascii=True, default=str)}\n"
                        f"Estimated fee: {estimate.get('fee', 'unavailable')} (venue estimate). Maker/taker status "
                        "and final fee depend on execution, especially for limit orders.\n"
                        f"{result.get('notice', '')}")
                msg.update("Review ready. Nothing has been submitted.")
        else:
            order_id = result.get("order_id") or result.get("signature")
            state = str(result.get("status") or "unknown")
            self.query_one("#advanced-receipt", Static).update(json.dumps(result, ensure_ascii=True, default=str))
            if order_id and "coinbase" in operation:
                self.query_one("#coinbase-order-id", Input).value = str(order_id)
            terminal = state.upper() in {"FILLED", "CANCELLED", "CANCELED", "FAILED", "REJECTED", "EXPIRED"}
            if terminal and order_id:
                self._coinbase_order_unknown = False
            self.query_one("#advanced-armed", Checkbox).value = False
            msg.update("Order submitted. " + ("Confirmed onchain." if state.upper() == "FILLED" else
                       ("A resting order locks further orders; check its status at Coinbase." if "coinbase" in operation else "Check status on Solscan.")))
        self._coinbase_order_controls()

    def _jupiter_order_state_start(self) -> None:
        self._jupiter_order_worker("jupiter.order_state", {})

    @work(thread=True, group="jupiter-order-state", exit_on_error=False)
    def _jupiter_order_worker(self, operation: str, params: dict[str, Any]) -> None:
        try:
            env = self._call(operation, params, quiet=True)
            self.call_from_thread(self._jupiter_order_state_done, env)
        except (RuntimeError, NoMatches):
            pass

    def _jupiter_order_state_done(self, env: dict[str, Any]) -> None:
        if not env.get("ok"):
            return
        res = env.get("result") or {}
        if res.get("unresolved"):
            self._coinbase_order_unknown = True
            if self.query("#advanced-message"):
                self.query_one("#advanced-message", Static).update(
                    "A previous Jupiter order is unresolved. Reconcile onchain status before placing another order.")
            self._coinbase_order_controls()

    def _coinbase_order_controls(self) -> None:
        busy = self._coinbase_order_busy
        for name, cls in (("#coinbase-order-product", Input), ("#coinbase-order-side", Select),
                          ("#coinbase-order-size", Input), ("#coinbase-order-armed", Checkbox),
                          ("#coinbase-order-skip-review", Checkbox),
                          ("#coinbase-order-id", Input)):
            self.query_one(name, cls).disabled = busy
        self.query_one("#coinbase-order-preview", Button).disabled = busy or self._coinbase_order_unknown
        self.query_one("#coinbase-order-check", Button).disabled = busy
        self.query_one("#coinbase-order-state", Button).disabled = busy
        preview = self._coinbase_order_preview_data
        valid = bool(preview and preview.get("values") == self._coinbase_order_values()
                     and isinstance(preview.get("expires_at"), (int, float))
                     and preview["expires_at"] > time.time())
        self.query_one("#coinbase-order-submit", Button).disabled = (
            busy or self._coinbase_order_unknown or not valid
            or not self.query_one("#coinbase-order-armed", Checkbox).value)
        quick = self.query_one("#coinbase-order-skip-review", Checkbox).value
        self.query_one("#coinbase-order-submit", Button).display = not quick
        quick_button = self.query_one("#coinbase-order-quick", Button)
        quick_button.display = quick
        product, side, size, _ = self._coinbase_order_values()
        quick_button.disabled = (busy or self._coinbase_order_unknown or not quick
                                 or not self.query_one("#coinbase-order-armed", Checkbox).value
                                 or not product or side not in ("BUY", "SELL") or not size)
        self._advanced_controls()

    @on(Input.Changed, "#coinbase-order-product")
    @on(Input.Changed, "#coinbase-order-size")
    @on(Select.Changed, "#coinbase-order-side")
    def _coinbase_order_changed(self) -> None:
        self._coinbase_order_generation += 1
        self._coinbase_order_preview_data = None
        if self.query("#coinbase-order-review"):
            self.query_one("#coinbase-order-review", Static).update("")
            side = self.query_one("#coinbase-order-side", Select).value
            self.query_one("#coinbase-order-size", Input).placeholder = (
                "Amount to spend in quote currency" if side == "BUY" else "Amount of base coin to sell")
            self._coinbase_order_controls()

    @on(Checkbox.Changed, "#coinbase-order-armed")
    @on(Checkbox.Changed, "#coinbase-order-skip-review")
    @on(Checkbox.Changed, "#advanced-armed")
    @on(Checkbox.Changed, "#advanced-skip-review")
    def _coinbase_order_armed_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id in ("coinbase-order-skip-review", "advanced-skip-review"):
            other_id = "#advanced-skip-review" if event.checkbox.id == "coinbase-order-skip-review" else "#coinbase-order-skip-review"
            if self.query(other_id):
                other = self.query_one(other_id, Checkbox)
                if other.value != event.value:
                    other.value = event.value
        if self.query("#coinbase-order-submit"):
            self._coinbase_order_controls()

    @on(Button.Pressed, "#coinbase-order-preview")
    def _coinbase_order_preview_pressed(self) -> None:
        if self._coinbase_order_busy or self._coinbase_order_unknown:
            return
        product, side, size, unit = self._coinbase_order_values()
        if not product or side not in ("BUY", "SELL") or not size:
            self.query_one("#coinbase-order-message", Static).update("Enter a pair, side and amount to review.")
            return
        self._coinbase_order_preview_data = None
        self._coinbase_order_busy = True
        self._coinbase_order_controls()
        self.query_one("#coinbase-order-message", Static).update("Reviewing with Coinbase… No order has been placed.")
        self._coinbase_order_worker("coinbase.order_preview", {"product_id": product, "side": side,
                                    "size": size, "size_currency": unit}, self._coinbase_order_generation,
                                    (product, side, size, unit))

    @on(Button.Pressed, "#coinbase-order-submit")
    def _coinbase_order_submit_pressed(self) -> None:
        preview = self._coinbase_order_preview_data
        self._coinbase_order_controls()
        if self.query_one("#coinbase-order-submit", Button).disabled or not preview:
            self.query_one("#coinbase-order-message", Static).update("Arm live orders and review an unexpired order first.")
            return
        # Consume the review before starting the worker: a double-click cannot submit twice.
        self._coinbase_order_preview_data = None
        self._advanced_preview_data = None
        self.query_one("#advanced-armed", Checkbox).value = False
        self._coinbase_order_busy = True
        self._coinbase_order_unknown = True
        self._coinbase_order_controls()
        self.query_one("#coinbase-order-message", Static).update(
            "Submitting one LIVE order… If this is interrupted, check Coinbase before doing anything else.")
        self._coinbase_order_worker("coinbase.order_submit", {"preview_id": preview["preview_id"], "confirm": True},
                                    self._coinbase_order_generation, None)

    @on(Button.Pressed, "#coinbase-order-quick")
    def _coinbase_order_quick_pressed(self) -> None:
        self._coinbase_order_controls()
        if self.query_one("#coinbase-order-quick", Button).disabled:
            return
        product, side, size, unit = self._coinbase_order_values()
        self._coinbase_order_preview_data = None
        self._advanced_preview_data = None
        self.query_one("#advanced-armed", Checkbox).value = False
        self._coinbase_order_busy = True
        self._coinbase_order_unknown = True
        self._coinbase_order_controls()
        self.query_one("#coinbase-order-message", Static).update(
            "Submitting one LIVE order immediately… If interrupted, check Coinbase before doing anything else.")
        self._coinbase_order_worker("coinbase.order_quick", {"product_id": product, "side": side,
                                    "size": size, "size_currency": unit, "skip_confirm": True},
                                    self._coinbase_order_generation, None)

    @on(Button.Pressed, "#coinbase-order-check")
    def _coinbase_order_check_pressed(self) -> None:
        if self._coinbase_order_busy:
            return
        order_id = self.query_one("#coinbase-order-id", Input).value.strip()
        if not order_id:
            self.query_one("#coinbase-order-message", Static).update("Enter a Coinbase order ID to check it.")
            return
        self._coinbase_order_busy = True
        self._coinbase_order_controls()
        self.query_one("#coinbase-order-message", Static).update("Checking Coinbase order status…")
        self._coinbase_order_worker("coinbase.order_status", {"order_id": order_id},
                                    self._coinbase_order_generation, None)

    @on(Button.Pressed, "#coinbase-order-state")
    def _coinbase_order_state_pressed(self) -> None:
        self._coinbase_order_state_start()

    def _coinbase_order_state_start(self) -> None:
        self._coinbase_order_generation += 1
        self._coinbase_order_preview_data = None
        self._advanced_preview_data = None
        self._advanced_generation += 1
        self.query_one("#coinbase-order-armed", Checkbox).value = False
        self.query_one("#advanced-armed", Checkbox).value = False
        self.query_one("#coinbase-order-review", Static).update("")
        self.query_one("#advanced-review", Static).update("")
        if self._coinbase_order_busy:
            return
        self._coinbase_order_busy = True
        self._coinbase_order_unknown = True
        self._coinbase_order_controls()
        self.query_one("#coinbase-order-message", Static).update("Checking prior Coinbase order state…")
        self._coinbase_order_worker("coinbase.order_state", {}, self._coinbase_order_generation, None)

    @work(thread=True, group="coinbase-manual-order", exit_on_error=False)
    def _coinbase_order_worker(self, operation: str, params: dict[str, Any], generation: int,
                               values: tuple[str, str, str, str] | None) -> None:
        try:
            env = self._call(operation, params)
        except Exception:
            env = {"ok": False, "error": {"message": "The operation failed or was interrupted."}}
        try:
            self.call_from_thread(self._coinbase_order_done, operation, env, generation, values)
        except (RuntimeError, NoMatches):
            pass  # The console closed; the backend must retain any submission outcome.

    def _coinbase_order_done(self, operation: str, env: dict[str, Any], generation: int,
                             values: tuple[str, str, str, str] | None) -> None:
        self._coinbase_order_busy = False
        msg = self.query_one("#coinbase-order-message", Static)
        if not env.get("ok"):
            reason = self._msg(env)
            if operation in ("coinbase.order_submit", "coinbase.order_quick"):
                self.query_one("#coinbase-order-armed", Checkbox).value = False
                msg.update("Order outcome may be unknown. Do not resubmit; reconcile at Coinbase. " + reason)
            else:
                if operation == "coinbase.order_preview" and "unresolved" in reason.lower():
                    self._coinbase_order_unknown = True
                msg.update(reason)
            self._coinbase_order_controls()
            return
        result = env.get("result") or {}
        if operation == "coinbase.order_state":
            if type(result.get("unresolved")) is not bool:
                msg.update("Cannot verify order safety state. Check Coinbase, then refresh order safety.")
            elif result["unresolved"]:
                self._coinbase_order_unknown = True
                orders = result.get("orders") or []
                self.query_one("#coinbase-order-receipt", Static).update(
                    "Unresolved saved submissions: " + json.dumps(orders, ensure_ascii=True, default=str))
                msg.update("A previous order is unresolved. Check Coinbase before placing another order.")
            else:
                self._coinbase_order_unknown = False
                msg.update("Disarmed. Enter a pair and amount, then review the order.")
        elif operation == "coinbase.order_preview":
            expires = result.get("expires_at")
            try:
                same_size = bool(values) and Decimal(str(result.get("size", ""))) == Decimal(values[2])
            except InvalidOperation:
                same_size = False
            if (generation != self._coinbase_order_generation or values != self._coinbase_order_values()
                    or not result.get("preview_id") or not isinstance(expires, (int, float)) or expires <= time.time()
                    or not same_size or any(str(result.get(k, "")) != v for k, v in zip(
                        ("product_id", "side", "size_currency"),
                        (values[0], values[1], values[3]) if values else ()))):
                msg.update("Review expired or the order changed. Review it again.")
            else:
                self._coinbase_order_preview_data = {"preview_id": result["preview_id"],
                                                     "expires_at": expires, "values": values}
                estimate_data = result.get("estimate") if isinstance(result.get("estimate"), dict) else {}
                estimate = json.dumps(result.get("estimate"), ensure_ascii=True, default=str)
                self.query_one("#coinbase-order-review", Static).update(
                    f"LIVE {values[1]} {values[0]} · {values[2]} {values[3]} currency\n"
                    f"Coinbase estimate: {estimate}\nEstimated fee: {estimate_data.get('fee', 'unavailable')} "
                    "(venue estimate). Maker/taker status and final fee depend on execution.\n"
                    f"{result.get('notice', '')}\n"
                    "To place this order, arm live submission and press Place LIVE order.")
                msg.update("Review ready. Nothing has been submitted.")
        else:
            order_id = result.get("order_id")
            status = str(result.get("status") or "unknown")
            if order_id:
                self.query_one("#coinbase-order-id", Input).value = str(order_id)
            self.query_one("#coinbase-order-receipt", Static).update(
                json.dumps(result, ensure_ascii=True, default=str))
            terminal = status.upper() in {"FILLED", "CANCELLED", "CANCELED", "FAILED", "REJECTED", "EXPIRED"}
            if terminal and ((operation in ("coinbase.order_submit", "coinbase.order_quick") and order_id)
                             or (operation == "coinbase.order_status" and result.get("unresolved") is False)):
                self._coinbase_order_unknown = False
            if operation in ("coinbase.order_submit", "coinbase.order_quick"):
                if operation != "coinbase.order_quick" or status.upper() != "FILLED" or not order_id:
                    self.query_one("#coinbase-order-armed", Checkbox).value = False
                if operation == "coinbase.order_quick" and status.upper() == "FILLED" and order_id:
                    msg.update("Order filled. Quick mode remains armed for the next order.")
                else:
                    msg.update("Order submitted. Check its status at Coinbase before another order." if order_id
                               else "Order outcome unknown. Do not resubmit; reconcile at Coinbase.")
            else:
                msg.update("Coinbase order status: " + status)
        self._coinbase_order_controls()

    @on(Button.Pressed, "#coinbase-sync")
    def _coinbase_sync_button(self) -> None:
        self.query_one("#coinbase-status", Static).update("Syncing Coinbase…")
        self._coinbase_worker("coinbase.sync")

    @on(Button.Pressed, "#coinbase-markets")
    def _coinbase_markets_button(self) -> None:
        self.query_one("#coinbase-status", Static).update("Downloading Coinbase markets…")
        self._coinbase_worker("coinbase.markets")

    @work(thread=True, group="coinbase", exclusive=True)
    def _coinbase_worker(self, operation: str) -> None:
        env = self._call(operation)
        self.call_from_thread(self._coinbase_show if operation == "coinbase.sync" else self._coinbase_market_done, env)

    def _coinbase_market_done(self, env: dict[str, Any]) -> None:
        status = self.query_one("#coinbase-status", Static)
        if not env["ok"]:
            status.update(escape(self._msg(env)))
            self._coinbase_pairs_start()
            return
        r = env["result"]
        incomplete = [name for name, scope in r["scopes"].items() if not scope["complete"]]
        spot = r.get("spot_pairs") or {}
        status.update(f"Spot pairs: {spot.get('count', '?')} "
                      + ("complete" if spot.get("complete") is True else "incomplete")
                      + f" · Wider catalog: {r['count']} products, {r['global_count']} global instruments; "
                      + ("incomplete: " + ", ".join(incomplete) if incomplete else "all scopes complete"))
        self._coinbase_pairs_start()

    def _coinbase_show(self, env: dict[str, Any]) -> None:
        status = self.query_one("#coinbase-status", Static)
        if not env["ok"]:
            status.update(escape(self._msg(env)))
            return
        r = env["result"]
        table = self.query_one("#coinbase-holdings", DataTable)
        table.clear()
        positions = self.query_one("#coinbase-positions", DataTable)
        positions.clear()
        for breakdown in r.get("breakdowns", []):
            name = (breakdown.get("portfolio") or {}).get("name", "")
            for row in breakdown.get("spot_positions", []):
                positions.add_row(str(name), str(row.get("asset", "")), str(row.get("account_type", "unknown")),
                                  str(row.get("total_balance_crypto", "unknown")), str(row.get("total_balance_fiat", "unknown")))
        for row in r.get("accounts", []):
            avail = row.get("available_balance") or {}
            hold = row.get("hold") or {}
            if str(avail.get("value", "0")) in ("0", "0.0", "0.00") and str(hold.get("value", "0")) in ("0", "0.0", "0.00"):
                continue
            table.add_row(str(row.get("portfolio_name", "")), str(row.get("currency", "")),
                          str(avail.get("value", "")), str(hold.get("value", "")))
        from datetime import datetime, timezone
        timestamp = r.get("fetched_at")
        stamp = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if isinstance(timestamp, (int, float)) else "unknown time"
        status.update("Saved Coinbase snapshot " + stamp + " · " + str(r.get("note", r.get("message", ""))))

    def _wallet_restore(self) -> None:
        """Real console only: show the newest kept scan at once, then refresh it in the background."""
        if not self._refresh_wallet:
            return
        env = self._call("portfolio.last", quiet=True)
        last = env["result"] if env["ok"] else {}
        if last.get("result"):
            chain = last.get("chain") or "all"
            select = self.query_one("#wallet-chain", Select)
            if chain in [value for _, value in select._options]:
                select.value = chain
            self._render_wallet({"ok": True, "result": last["result"]})
            self.query_one("#wallet-status", Static).update(
                f"last scan {last['result'].get('scanned_at', '?')} (kept from before the restart)"
                + "; refreshing…")
        if self.settings.solana_address or self.settings.base_address:
            self._wallet_worker()

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
                if h.get("verified_onchain") is False:
                    state += "; indexed balance, not RPC verified"
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
            chosen = preset["applies"]["live_run"]["strategy"]
            self.query_one("#live-run-strategy", Input).value = chosen
            self._live_run_preset = (chosen, preset["value"])
            self.query_one("#live-run-status", Static).update(
                f"preset {preset['title']} selected · {preset['params_text']} · {preset['net_pct_text']} · press Start dry run")
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
            yield Static("[b]What each strategy would do now[/b]: its action at the chosen bar, what it holds "
                         "versus wants, and its warm-up against the bars available.", classes="table-title")
            table = GlossaryTable(id="analyze-table")
            table.add_columns("strategy", "family", "action", "holding -> wants",
                              "warmup", "bars")
            yield ExportPanel(table)

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
            yield Static("[b]Per results file[/b]: how many configurations are rankable, below the floor, "
                         "positive and made money, with the median Sharpe and the best rankable row.", classes="table-title")
            per_file = GlossaryTable(id="cumulative-table")
            per_file.add_columns("file", "rankable", "below floor", "positive",
                                 "made money", "median Sharpe", "paths", "best (rankable)",
                                 "best backtest median net %")
            yield ExportPanel(per_file)
            yield Static("[b]Below the floor — what a naive aggregate would rank first[/b]", classes="table-title")
            dropped = GlossaryTable(id="cumulative-dropped")
            dropped.add_columns("file", "configuration", "claims Sharpe", "trades", "paths")
            yield ExportPanel(dropped)

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
                yield Button("Test status", id="status-queue")
                yield Button("Start", variant="primary", id="queue-start")
                yield Button("Start fresh", id="queue-start-fresh")
                yield Button("Stop", variant="error", id="queue-stop")
                yield Button("Refresh", id="queue-refresh")
                yield Button("Fetch missing data", id="queue-fetch")
            yield Static("", id="queue-data")
            yield Static("", id="queue-status")
            yield Static("[b]Ranked — cleared the evidence floor[/b]", classes="table-title")
            ranked = GlossaryTable(id="queue-table")
            ranked.add_columns(
                "configuration", "family", "median Sharpe", "IQR",
                "% paths +", "backtest median net %", "trades",
            )
            yield ExportPanel(ranked)
            yield Static(
                "[b]Below the floor — listed, never ranked[/b]", classes="table-title"
            )
            floor = GlossaryTable(id="queue-floor")
            floor.add_columns("configuration", "family", "trades", "why")
            yield ExportPanel(floor)

    @on(Button.Pressed, "#queue-start")
    def _queue_start(self) -> None:
        """Spawn the background worker for the configured asset."""
        status = self.query_one("#queue-status", Static)
        self._close_finished_worker_logs()
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

    @on(Button.Pressed, "#queue-start-fresh")
    def _queue_start_fresh(self) -> None:
        """Start a separate sweep without altering historical results."""
        status = self.query_one("#queue-status", Static)
        self._close_finished_worker_logs()
        env = self._call("queue.start_fresh")
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        self._refresh_queue()

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
        path = bgqueue.active_results_path()
        self._queue_mtime = (path, _mtime(path))
        self._render_queue_data(r["missing"], r["fetch_log"])
        self.query_one("#queue-status", Static).update(r["summary"])
        table = self.query_one("#queue-table", DataTable)
        table.clear()
        self._queue_ranked_rows = r["ranked"]
        for index, x in enumerate(r["ranked"]):
            table.add_row(
                x["label"], x["family"], f"{x['median_sharpe']:+.3f}", f"{x['iqr']:.3f}",
                f"{x['frac_positive']:.0%}", format_pct(x["net_pct"]), str(x["trades"]),
                key=str(index),
            )
        floor_table = self.query_one("#queue-floor", DataTable)
        floor_table.clear()
        for x in r["floor"]:
            floor_table.add_row(x["label"], x["family"], str(x["trades"]), x["why"])

    # -- P&L: profit and loss over a window -------------------------------

    def action_experiment_selected(self) -> None:
        tabs = self.query_one("#main-tabs", TabbedContent)
        try:
            horizon_note = ""
            horizon = None
            if tabs.active == "tab-queue":
                table = self.query_one("#queue-table", DataTable)
                if not table.row_count:
                    raise ValueError("Select a ranked Queue result first.")
                row = self._queue_ranked_rows[int(self._strategy_table_key(table))]
                name, params, asset = row["strategy"], row["params"], row["asset"]
            elif tabs.active == "tab-strategies":
                table = self.query_one("#available-table", DataTable)
                if not table.row_count:
                    raise ValueError("Select a registered strategy first.")
                name = self._strategy_table_key(table)
                if not self._registered_card_selected(name):
                    return
                params = merged_params(name, self.signals)
                params.update(self._parse_params())
                asset = self.settings.asset
            elif tabs.active == "tab-forwardtest":
                table = self.query_one("#forward-table", DataTable)
                if not table.row_count:
                    raise ValueError("Select a Forward Test trial first.")
                row = self._forward_rows[self._strategy_table_key(table)]
                members = row.get("settings")
                if not isinstance(members, list) or not members:
                    raise ValueError("The selected Forward Test trial has no available strategy settings.")
                if len(members) != 1:
                    raise ValueError("This Forward Test trial is an ensemble; it cannot be copied as one strategy. Select a single-strategy trial.")
                member = members[0]
                if not isinstance(member, dict):
                    raise ValueError("The selected Forward Test trial has invalid strategy settings.")
                name, params, asset = member["name"], member["params"], row["asset"]
                if row.get("minutes") in (1, 5, 30):
                    horizon = row["minutes"]
                else:
                    horizon_note = (f" The selected {row.get('minutes')}-minute horizon is unavailable in "
                                    "Experiments; choose an available horizon before starting.")
            else:
                raise ValueError("Select a Forward Test trial, ranked Queue result or registered strategy first.")
            if name not in {key for key, _ in available_strategies()} or not isinstance(params, dict):
                raise ValueError("This result does not name an available paper strategy with valid parameters.")
            self.query_one("#paper-exp-strategy", Select).value = name
            self.query_one("#paper-exp-asset", Input).value = str(asset)
            self.query_one("#paper-exp-params", Input).value = json.dumps(params, sort_keys=True)
            if horizon is not None:
                self.query_one("#paper-exp-horizon", Select).value = horizon
            self.set_focus(None)
            tabs.active = "tab-paper-experiments"
            self.query_one("#paper-exp-transfer", Static).update(
                "Strategy and parameters copied. Edit them, then press Start experiment. Nothing has started yet."
                + horizon_note)
        except (ValueError, KeyError, IndexError, AttributeError, RosterError) as exc:
            self._start_log("Experiment selection", str(exc) or "Select a strategy first.")

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
            yield Static("[b]By strategy[/b]", classes="table-title")
            by_strategy = GlossaryTable(id="pnl-strategies")
            by_strategy.add_columns("source", "strategy", "asset", "net $", "net % (source named)",
                                    "gross $", "costs $", "realized $", "unrealized $",
                                    "contribution (source named)")
            yield ExportPanel(by_strategy)
            yield Static("[b]By asset[/b]", classes="table-title")
            by_asset = GlossaryTable(id="pnl-assets")
            by_asset.add_columns("source", "asset", "runs", "net $", "net % (source named)",
                                 "contribution (source named)")
            yield ExportPanel(by_asset)
            yield Static("[b]Best and worst periods[/b]", classes="table-title")
            periods = GlossaryTable(id="pnl-periods")
            periods.add_columns("source", "period", "best", "worst")
            yield ExportPanel(periods)
            yield Static("[b]Daily P&L, cumulative and drawdown[/b]", classes="table-title")
            daily = GlossaryTable(id="pnl-daily")
            daily.add_columns("source", "date", "P&L $", "cumulative $",
                              "cumulative % (source named)", "drawdown (source named)")
            yield ExportPanel(daily)

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
                pct = d.get("percent_at_max_drawdown_usd", d["max_drawdown_pct"])
                rec = (f"recovered after {d['recovery_days']} d" if d["recovered"] else "not recovered")
                lines.append(f"  max drawdown {self._usd(d['max_drawdown_usd'])}"
                             + ("" if pct is None else f" ({sec['source']} {pct * 100:+.1f}% from peak)")
                             + f" · peak {d['peak_date']} · trough {d['trough_date']} · {rec}")
                if d.get("max_drawdown_pct") is not None and d["max_drawdown_pct"] != pct:
                    lines.append(f"  max percentage drawdown {sec['source']} {d['max_drawdown_pct'] * 100:+.1f}%"
                                 f" · peak {d.get('percentage_peak_date')}"
                                 f" · trough {d.get('percentage_trough_date')}")
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

        This archived pane has no order path: the daemon (`liquidity/`)
        does the managing and writes files; this pane reads them. The only thing
        it writes is the `KILL` file, via the Kill/Resume buttons.
        """
        with VerticalScroll():
            yield Static("Archived — the Aero LP manager and scout are retired. Historical position and scout records remain available.", classes="hint")
            yield Static("", id="liq-banner")
            yield Static("", id="liq-summary")
            yield Static("", id="liq-wallet", classes="hint")
            with Horizontal(classes="form-row"):
                yield Button("Refresh", id="liq-refresh")
                yield Button("Kill", variant="error", id="liq-kill")
                yield Button("Resume", variant="success", id="liq-resume")
            yield Static("", id="liq-status", classes="hint")
            yield Static("[b]Positions[/b]", classes="table-title")
            yield ExportPanel(GlossaryTable(id="liq-positions"))
            yield Static("[b]Scout[/b] — top pools by modelled net APR", classes="table-title")
            yield Static("", id="liq-scout-note", classes="hint")
            yield ExportPanel(GlossaryTable(id="liq-scout"))
            yield Static("[b]Experiments[/b] — arms side by side", classes="table-title")
            yield ExportPanel(GlossaryTable(id="liq-experiments"))
            yield Static("[b]Recent actions[/b] — newest first", classes="table-title")
            yield ExportPanel(GlossaryTable(id="liq-actions"))

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
                "positions as they are. The manager is archived; check the service state before acting. ",
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
            yield Static("[b]Research drivers[/b]: the script, the question it answers and what it "
                         "established.", classes="table-title")
            table = GlossaryTable(id="research-table")
            table.add_columns("driver", "answers", "established")
            research = self._call("research.get")["result"]
            for r in research["drivers"]:
                table.add_row(r["driver"], r["answers"], r["established"])
            yield ExportPanel(table)
            yield Static("[b]Findings that constrain every figure above[/b]", classes="table-title")
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
            yield Static("[b]Repository files[/b]: path, kind, whether this console may edit it, length and "
                         "a one-line summary. Select one to open it in the editor below.", classes="table-title")
            with Horizontal():
                listing = GlossaryTable(id="docs-table")
                listing.add_columns("path", "kind", "editable", "lines", "summary")
                # Row cursor, not the DataTable default of cell: a click must
                # land on *a row*, not one cell in it, for RowHighlighted to
                # fire and for the "o" binding below to know which file it is
                # opening. Without this a click just moved a cell cursor and
                # nothing happened -- the bug this pane shipped with.
                listing.cursor_type = "row"
                yield ExportPanel(listing)

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
        self._set_editor_open(not self.query_one("#editor-panel").display)

    # -- the editor's size and visibility (the orange bar above it) ---------------------------

    def _set_editor_open(self, open_: bool, *, persist: bool = True) -> None:
        if self._v2_editor_suppressed:
            # ctrl+e on Now: the owner asked for the editor, so stop hiding it there.
            self._v2_editor_suppressed = False
            self.query_one("#editor-bar").display = True
        panel = self.query_one("#editor-panel")
        panel.display = open_
        bar = self.query_one("#editor-bar", EditorBar)
        bar.panel_open = open_
        bar.refresh()
        if persist:
            self._save_ui_state()

    def _set_editor_height(self, height: int, *, persist: bool = True) -> None:
        bar = self.query_one("#editor-bar", EditorBar)
        self._editor_height = min(max(int(height), EditorBar.MIN_HEIGHT), bar.max_height())
        self.query_one("#editor-panel").styles.height = self._editor_height
        if persist:
            self._save_ui_state()

    @on(EditorBar.Resized)
    def _editor_resized(self, event: EditorBar.Resized) -> None:
        if not self.query_one("#editor-panel").display:
            self._set_editor_open(True, persist=False)
        self._set_editor_height(event.height, persist=event.final)

    @on(EditorBar.Close)
    def _editor_close(self) -> None:
        self._set_editor_open(False)

    @on(EditorBar.Open)
    def _editor_open(self) -> None:
        self._set_editor_open(True)

    def _default_editor_height(self) -> int:
        if self.size.height < 36:
            return max(EditorBar.MIN_HEIGHT, self.size.height // 3)
        return self.EDITOR_HEIGHT

    @on(EditorBar.Reset)
    def _editor_reset(self) -> None:
        self._set_editor_height(self._default_editor_height())

    def action_grow_editor(self) -> None:
        self._set_editor_open(True, persist=False)
        self._set_editor_height(self._editor_height + 2)

    def action_shrink_editor(self) -> None:
        self._set_editor_height(self._editor_height - 2)

    def _apply_ui_state(self) -> None:
        state: dict[str, Any] = {}
        if self._ui_state_path is not None:
            try:
                loaded = json.loads(self._ui_state_path.read_text(encoding="utf-8"))
                state = loaded if isinstance(loaded, dict) else {}
            except (OSError, ValueError):
                state = {}  # first run, or a torn file: the defaults are a fine layout
        height = state.get("editor_height")
        if isinstance(height, int) and not isinstance(height, bool):
            self._set_editor_height(height, persist=False)
        elif self.size.height < 36:
            # Keep the primary workspace usable on first launch in a short terminal.
            self._set_editor_height(self._default_editor_height(), persist=False)
        self._set_editor_open(state.get("editor_open", True) is not False, persist=False)

    def _save_ui_state(self) -> None:
        if self._ui_state_path is None:
            return
        data = {"editor_height": self._editor_height,
                "editor_open": bool(self.query_one("#editor-panel").display)}
        try:
            self._ui_state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._ui_state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data) + "\n", encoding="utf-8")
            tmp.replace(self._ui_state_path)
        except OSError:
            pass  # a layout preference that cannot be saved is not worth interrupting anyone for

    # -- previews: a selected row explained in the shared editor ------------------------------

    def _call_with_progress(self, name: str, params: dict[str, Any], title: str) -> dict[str, Any]:
        ctx = Context(self.settings, self.roster, self.signals, self.ctx.runtime)

        def progress(message: str) -> None:
            try:
                self.call_from_thread(self._append_log, title, message)
            except RuntimeError:
                pass  # The console closed while the backtest was still running.

        ctx.progress = progress
        return dispatch(name, params, surface="tui", ctx=ctx)

    def _start_log(self, title: str, line: str, tail: BacktestLog | None = None) -> str:
        logs = getattr(self, "_test_logs", None)
        if logs is None:
            self._test_logs = logs = {}
        self._test_log_seq = getattr(self, "_test_log_seq", 0) + 1
        key = f"{title} #{self._test_log_seq}"
        logs[key] = {"title": title, "text": f"# {title}\n\n{line}\n", "tail": tail}
        self._backtest_log_title = title
        self._backtest_log_text = logs[key]["text"]
        self._backtest_log_tail = tail
        self._backtest_log_progress = None
        self._set_editor_open(True, persist=False)
        self._show_preview(title, self._backtest_log_text)
        return key

    def _append_log(self, title: str, line: str, *, raw: bool = False) -> None:
        logs = getattr(self, "_test_logs", {})
        key = title if title in logs else next((k for k in reversed(logs) if logs[k]["title"] == title), None)
        if key is None:
            return
        entry = logs[key]
        old = entry["text"]
        entry["text"] = (old + (line if raw else line.rstrip() + "\n"))[-100000:]
        if key == next(reversed(logs)):
            self._backtest_log_text = entry["text"]
        if self._preview_text == old:
            self._show_preview(entry["title"], entry["text"])
            self.query_one("#docs-view", TextArea).scroll_end(animate=False)

    def _close_finished_worker_logs(self) -> None:
        """Detach old log readers before a new worker appends to the shared log."""
        if bgcontrol.is_running():
            return
        for key, entry in list(getattr(self, "_test_logs", {}).items()):
            tail = entry.get("tail")
            if tail is None:
                continue
            for _ in range(2):
                chunk = tail.poll()
                if not chunk:
                    break
                self._append_log(key, chunk, raw=True)
            entry["tail"] = None

    def _poll_backtest_log(self) -> None:
        for key, entry in list(getattr(self, "_test_logs", {}).items()):
            tail = entry["tail"]
            if tail is not None:
                chunk = tail.poll()
                if chunk:
                    self._append_log(key, chunk, raw=True)
        if self.runner.running:
            progress = (self.state.done, self.state.total)
            if progress != getattr(self, "_backtest_log_progress", None):
                self._backtest_log_progress = progress
                self._append_log(getattr(self, "_cpcv_active_log", "CPCV backtest"),
                                 f"Progress: {progress[0]}/{progress[1]} configurations")
        self._refresh_open_test_status()

    # A status view follows existing operations; it never launches or cancels them.
    _TEST_STATUS = {
        "status-strategies": ("Strategy tests", ("history-status",), ("Strategy backtest",), "queue"),
        "status-forwardtest": ("Forward tests", ("forward-status",), (), "forward"),
        "status-compound-backtest": ("Signal backtests", ("compound-status", "compound-bt-status"),
                                     ("Compound backtest",), ""),
        "status-compound-forward": ("Signal forward tests", ("compound-unattended", "compound-fwd-summary"), (), "compound"),
        "status-bots": ("Bot tests", ("bots-status", "bots-fit-status", "bots-fwd-summary"), ("Bot backtest", "Bot optimize"), ""),
        "status-backtest": ("Backtests", ("backtest-status", "backtest-bg-status"),
                            ("CPCV backtest", "Strategy backtest"), "queue"),
        "status-top5": ("Roster backtests", ("top5-status", "backtest-status"), ("CPCV backtest",), ""),
        "status-queue": ("Background sweep", ("queue-status",), ("Strategy backtest",), "queue"),
        "status-live": ("Dry run", ("live-run-status",), ("Dry run",), "live"),
        "status-paper": ("Dry-run replay", ("exec-summary",), ("Replay",), ""),
    }

    def _test_status_text(self, button_id: str) -> str:
        title, widgets, titles, source = self._TEST_STATUS[button_id]
        lines = [f"# {title}", "", "Current status (read-only):"]
        found = False
        for widget_id in widgets:
            matches = self.query(f"#{widget_id}")
            if matches:
                value = matches.first(Static).content
                value = value.plain if isinstance(value, Text) else str(value or "")
                if value.strip():
                    lines.append(value)
                    found = True
        if source == "queue":
            env = self._call("queue.progress", quiet=True)
            lines.append(env["result"]["summary"] if env["ok"] else f"Sweep status unavailable: {self._msg(env)}")
            path = bgqueue.BG_DIR / "worker.log"
            try:
                with path.open("rb") as stream:
                    stream.seek(0, 2)
                    stream.seek(max(0, stream.tell() - 16384))
                    recent = stream.read().decode("utf-8", errors="replace")
                lines.extend(["", f"Recent worker log ({path}; may include older runs):", recent or "Log is empty."])
            except OSError as exc:
                lines.extend(["", f"Worker log unavailable: {exc}"])
            found = True
        elif source == "forward":
            env = self._call("forwardtest.state", quiet=True)
            if env["ok"]:
                state = env["result"]
                assets = ", ".join(state.get("assets") or []) or "none"
                lines.append(f"Forward test: {'running' if state.get('running') else 'stopped'}; coins: {assets}.")
                for coin, latest in (state.get("last") or {}).items():
                    checked = latest.get("at")
                    when = time.strftime("%m-%d %H:%M:%S UTC", time.gmtime(checked)) if checked else "unknown time"
                    detail = latest.get("error") or latest.get("message") or f"{latest.get('recorded', 0)} predictions recorded"
                    lines.append(f"{coin}: {when} — {detail}")
            else:
                lines.append(f"Forward status unavailable: {self._msg(env)}")
            found = True
        elif source == "compound":
            env = self._call("compound.unattended_status", {"asset": self._compound_coin}, quiet=True)
            if env["ok"]:
                state = env["result"]
                lines.append(f"{state['asset']} trainer: {'running' if state.get('running') else 'stopped'}.")
                last = state.get("last_line") or "No recent trainer activity available."
                try:
                    item = json.loads(last)
                except (TypeError, ValueError):
                    lines.append(last)
                else:
                    if item.get("error"):
                        lines.append(f"Last error: {item['error']}")
                    else:
                        lines.append(f"Last call: {item.get('call', 'unknown')}; "
                                     f"recorded: {'yes' if item.get('recorded') else 'no'}; "
                                     f"earlier calls resolved: {item.get('resolved', 0)}.")
                lines.append(f"Log: {state.get('log') or 'unavailable'}")
            else:
                lines.append(f"Trainer status unavailable: {self._msg(env)}")
            found = True
        elif source == "live":
            matches = self.query("#live-run-output")
            if matches and matches.first(TextArea).text:
                lines.extend(["", matches.first(TextArea).text])
                found = True
        for key, log in getattr(self, "_test_logs", {}).items():
            if log["title"] in titles:
                lines.extend(["", f"## {key}", log["text"]])
                found = True
        if not found:
            lines.append("No test status or log is available in this session.")
        return "\n".join(lines)[-100000:]

    @on(Button.Pressed, "#status-strategies")
    @on(Button.Pressed, "#status-forwardtest")
    @on(Button.Pressed, "#status-compound-backtest")
    @on(Button.Pressed, "#status-compound-forward")
    @on(Button.Pressed, "#status-bots")
    @on(Button.Pressed, "#status-backtest")
    @on(Button.Pressed, "#status-top5")
    @on(Button.Pressed, "#status-queue")
    @on(Button.Pressed, "#status-live")
    @on(Button.Pressed, "#status-paper")
    def _open_test_status(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""
        if button_id not in self._TEST_STATUS:
            return
        self._set_editor_open(True, persist=False)
        text = self._test_status_text(button_id)
        self._show_preview(self._TEST_STATUS[button_id][0], text)
        self._test_status_button = button_id
        self._test_status_preview = text if self._preview_text == text else None

    def _refresh_open_test_status(self) -> None:
        button_id = getattr(self, "_test_status_button", None)
        previous = getattr(self, "_test_status_preview", None)
        if not button_id or previous is None or self._preview_text != previous:
            return
        text = self._test_status_text(button_id)
        if text != previous:
            self._show_preview(self._TEST_STATUS[button_id][0], text)
            self._test_status_preview = text if self._preview_text == text else None

    def _show_preview(self, title: str, text: str) -> None:
        """Show generated, read-only text in the shared editor.

        A preview never replaces unsaved edits: if a catalogued file is open with changes, the
        status line says so and the edits stay. An identical preview is not reloaded, so the
        periodic table refresh does not jump the editor back to the top.
        """
        if not self.query("#docs-view") or not self.query("#docs-view-status"):
            return
        view = self.query_one("#docs-view", TextArea)
        status = self.query_one("#docs-view-status", Static)
        if self._docs_current_path is not None and view.text != self._docs_loaded_text:
            status.update(f"unsaved changes in {self._docs_current_path}: save (ctrl+s) to see the "
                          f"{title} preview here")
            return
        if self._preview_text == text and self._docs_current_path is None:
            return
        self._docs_current_path = None
        self._docs_current_editable = False
        self._docs_loaded_text = text
        self._preview_text = text
        view.read_only = True
        view.text = text
        try:
            view.language = "markdown"
        except Exception:  # noqa: BLE001 - grammar unavailable in this build
            view.language = None
        view.scroll_home(animate=False)
        status.update(f"preview: {title} (read-only)")
        self.query_one("#docs-save", Button).disabled = True

    def _on_compound_tab(self) -> bool:
        try:
            return self.query_one(TabbedContent).active == "tab-compound"
        except Exception:  # noqa: BLE001 - during compose there is no tab set yet
            return False

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
        if not self.query("#docs-view") or not self.query("#docs-view-status"):
            return
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
        self._docs_revision = env["result"].get("revision")
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
        self._preview_text = None
        note = " (discarded unsaved edit)" if moving_away else ""
        status.update(f"{path} — {'editable' if editable else 'read-only'}{note}")
        self.query_one("#docs-save", Button).disabled = not editable

    @on(TextArea.Changed, "#docs-view")
    def _docs_view_changed(self) -> None:
        """Live "unsaved" marker, so a lost-on-navigate edit is visible
        before it is lost, not just guarded against after the fact."""
        if self._docs_current_path is None or not self.query("#docs-view") or not self.query("#docs-view-status"):
            return  # A queued change can arrive while the screen is unmounting.
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
        env = self._call("docs.write", {"path": path, "text": text,
                                        "expected_revision": self._docs_revision})
        if not env["ok"]:
            status.update(f"[red]{self._msg(env)}[/]")
            return
        self._docs_loaded_text = text
        self._docs_revision = env["result"].get("revision")
        status.update(f"{path} — saved")

    # -- v2 shell ----------------------------------------------------------
    # Navigation only ever sets `#main-tabs`.active (and the Compound section), so every pane's own
    # TabActivated hooks (lazy loads, help install) run exactly as they do from the classic tab bar.

    # Status reads for the health strip and Now. All read-only and cheap (each well under 20 ms);
    # `compound.autopilot_status` shells out to launchctl, so it refreshes at most once a minute.
    _V2_TICK_READS = ("backtest.status", "queue.progress", "prices.status",
                      "portfolio.last")

    def _v2_setup(self) -> None:
        self.screen.add_class("v2" if self._v2 else "classic")
        tabs = self.query_one("#main-tabs", TabbedContent)
        # Only this TabbedContent's own panes (they sit in its ContentSwitcher), not the sections nested
        # inside Compound or Bots.
        panes = [(p.id, str(tabs.get_tab(p.id).label)) for p in tabs.query(TabPane)
                 if p.id and next(a for a in p.ancestors if isinstance(a, TabbedContent)) is tabs]
        self._v2_dests = shell.with_extra_views(panes)
        coins = self.query_one("#now-coins", GlossaryTable)
        coins.cursor_type = "row"
        coins.add_columns("coin", "backtest verdict", "bt hit", "fwd calls", "fwd hit", "paper $", "unattended")
        self._v2_sync_from_tabs()
        if not self._v2:
            return
        self._v2_health_tick()
        self.set_interval(5, self._v2_health_tick)
        if self._start == "tab-now":
            self._v2_load_now()
            # Focus starts on the classic tab bar, which v2 hides; put it on the list that answers
            # the screen's question instead. Not an input, so the 1-6 / ? keys still navigate.
            self.call_after_refresh(lambda: self.query_one("#now-needs", OptionList).focus())

    def _v2_destination(self, key: str) -> shell.Destination:
        return next(d for d in self._v2_dests if d.key == key)

    def _v2_show(self, dest_key: str, index: int | None = None) -> None:
        dest = self._v2_destination(dest_key)
        index = self._v2_last.get(dest_key, 0) if index is None else index % len(dest.views)
        view = dest.views[index]
        # Drop focus first. A focused widget in the pane being hidden hands focus to a sibling in that
        # same pane, and TabbedContent answers a pane's focus by switching back to it, so the move
        # would bounce. The classic tab bar never hit this because clicking a tab focuses the tab bar.
        self.set_focus(None)
        if view.inner:
            pane = self.query_one(f"#{view.inner}", TabPane)
            inner = next(a for a in pane.ancestors if isinstance(a, TabbedContent))
            inner.active = view.inner
        self.query_one("#main-tabs", TabbedContent).active = view.tab
        self._v2_dest, self._v2_index = dest_key, index
        self._v2_last[dest_key] = index
        self._v2_render_chrome()
        # Synchronously, not after a refresh: the pane's "focused" message must queue before the next
        # key press, or a late one for the view just left switches the tabs back to it.
        self._v2_focus_into(view.inner or view.tab)

    def _v2_focus_into(self, pane_id: str) -> None:
        """Focus the view's first table, list or button: keyboard-ready, and not an input, so the
        number keys keep navigating. Widgets inside a nested, hidden section are skipped."""
        current = self._v2_destination(self._v2_dest).views[self._v2_index]
        if pane_id != (current.inner or current.tab):
            # Scheduled for a view the owner already left (fast keys, or a slow first load such as
            # Cumulative's): focusing into it now would pull the tabs back there.
            return
        panes = self.query(f"#{pane_id}")
        if not panes:
            return
        pane = panes.first(TabPane)

        def shown(widget: Widget) -> bool:
            # A Select's dropdown is an OptionList kept with display: none; focusing it opens nothing
            # useful and confuses the pane. Only widgets displayed all the way up to the pane count.
            node: Any = widget
            while node is not None and node is not pane:
                if not node.display:
                    return False
                node = node.parent
            return True

        candidates = [w for w in pane.query("*")
                      if isinstance(w, (DataTable, OptionList, Button)) and w.focusable and shown(w)
                      and next((a for a in w.ancestors if isinstance(a, TabPane)), None) is pane]
        best = next((w for w in candidates if isinstance(w, (DataTable, OptionList))), None) \
            or next(iter(candidates), None)
        if best is not None:
            best.focus()

    def _v2_sync_from_tabs(self) -> None:
        """Follow the panes when something other than the v2 bars switched them (tests, links)."""
        tabs = self.query("#main-tabs")
        if not tabs:
            return
        active = tabs.first(TabbedContent).active
        inner = None
        if active == "tab-compound":
            sections = self.query("#compound-sections")
            inner = sections.first(TabbedContent).active if sections else None
        found = shell.locate(active, inner, self._v2_dests)
        if found:
            dest, index = found
            self._v2_dest, self._v2_index = dest.key, index
            self._v2_last[dest.key] = index
        self._v2_render_chrome()

    @on(TabbedContent.TabActivated)
    def _v2_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.tabbed_content.id not in ("main-tabs", "compound-sections"):
            return
        self._v2_sync_from_tabs()
        if event.pane is not None and event.pane.id == "tab-now":
            self._v2_load_now()

    def _v2_render_chrome(self) -> None:
        if not self._v2 or not self.query("#v2-topbar"):
            return
        dest = self._v2_destination(self._v2_dest)
        clock = time.strftime("%H:%M")
        price = shell.price_line(self._v2_reads)
        self.query_one("#v2-topbar", shell.SegmentBar).set_segments(
            shell.topbar_segments(dest.key, price, self.SUB_TITLE, clock, self.size.width))
        self.query_one("#v2-subnav", shell.SegmentBar).set_segments(shell.subnav_segments(dest, self._v2_index, self.size.width))
        panel, bar = self.query_one("#editor-panel"), self.query_one("#editor-bar")
        if dest.key == "now" and not self._v2_editor_suppressed and bar.display:
            self._v2_editor_was_open = bool(panel.display)
            self._v2_editor_suppressed = True
            panel.display = bar.display = False
        elif dest.key != "now" and self._v2_editor_suppressed:
            self._v2_editor_suppressed = False
            bar.display = True
            panel.display = self._v2_editor_was_open
        banner = self.query_one("#v2-live-banner", Static)
        banner.set_class(dest.live_money, "on")
        if dest.live_money:
            line = Text()
            line.append(" ◆ LIVE MONEY ", f"bold {shell.TOK['bg']} on {shell.TOK['live']}")
            line.append(" Coinbase orders can move real money. Order forms start disarmed.",
                        shell.TOK["live"])
            banner.update(line)

    def on_resize(self) -> None:
        self._v2_render_chrome()

    @on(shell.SegmentBar.Selected)
    def _v2_segment(self, event: shell.SegmentBar.Selected) -> None:
        kind, _, value = event.segment.partition(":")
        if kind == "dest":
            self._v2_show(value)
        elif kind == "view":
            self._v2_show(self._v2_dest, int(value))

    def action_v2_goto(self, key: str) -> None:
        self._v2_show(key)

    def action_v2_cycle(self, step: int) -> None:
        self._v2_show(self._v2_dest, self._v2_index + int(step))

    def _v2_health_tick(self) -> None:
        """Every background process on one line, refreshed every 5 s; Needs-you follows it."""
        if not self.query("#v2-health"):
            return
        for name in self._V2_TICK_READS:
            self._v2_reads[name] = self._call(name, quiet=True)
        notice = self._call("portfolio.notice", {}, quiet=True)
        self._v2_reads["portfolio.notice"] = notice
        self._v2_notice = notice.get("result") if notice.get("ok") and isinstance(notice.get("result"), dict) else None
        if time.time() - self._v2_autopilot_at > 60:
            self._v2_autopilot_at = time.time()
            env = self._call("compound.autopilot_status", quiet=True)
            self._v2_reads["compound.autopilot_status"] = env
            self._v2_autopilot = env.get("result") if env.get("ok") and isinstance(env.get("result"), dict) else None
        items = shell.health_items(self._v2_reads, forward_running=self._forward_running,
                                   autopilot=self._v2_autopilot)
        self.query_one("#v2-health", Static).update(shell.health_text(items))
        self._v2_render_needs()
        self._v2_render_prices()
        self._v2_render_chrome()

    def _v2_render_needs(self) -> None:
        listing = self.query("#now-needs")
        if not listing:
            return
        valid_reads = {name: env for name, env in self._v2_reads.items() if isinstance(env, dict)}
        self._v2_needs = shell.needs(valid_reads, autopilot=self._v2_autopilot, notice=self._v2_notice)
        options = listing.first(OptionList)
        highlighted = options.highlighted
        options.clear_options()
        required = (*self._V2_TICK_READS, "queue.status", "compound.autopilot_status", "portfolio.notice")
        unavailable = []
        for name in required:
            env = self._v2_reads.get(name)
            # A successful portfolio.notice may legitimately return None.
            if (not isinstance(env, dict) or env.get("ok") is not True or "result" not in env
                    or (not isinstance(env["result"], dict)
                        and not (name == "portfolio.notice" and env["result"] is None))):
                unavailable.append(name)
        if self._v2_needs:
            options.add_options([Option(shell.need_prompt(n), id=f"need-{i}") for i, n in enumerate(self._v2_needs)])
        if unavailable:
            labels = {"backtest.status": "backtest", "queue.progress": "sweep", "queue.status": "sweep",
                      "prices.status": "prices", "portfolio.last": "wallet", "portfolio.notice": "wallet notice",
                      "compound.autopilot_status": "trainer"}
            names = list(dict.fromkeys(labels[name] for name in unavailable))
            options.add_option(Option(shell.status_text("warn", "Status unavailable",
                                      "Loading or failed: " + ", ".join(names)),
                                      id="status-unavailable", disabled=True))
        elif not self._v2_needs:
            options.add_option(Option(shell.status_text("ok", "No flagged issues", "checked status sources only"),
                                      id="need-none"))
        if highlighted is not None and highlighted < options.option_count:
            options.highlighted = highlighted
        count = len(self._v2_needs) + bool(unavailable)
        self.query_one("#now-needs-title", Static).update(
            f"[b]Needs you · {count}[/b] · Enter opens issue")

    @on(OptionList.OptionSelected, "#now-needs")
    def _v2_need_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id or ""
        if not option_id.startswith("need-") or option_id == "need-none":
            return
        need = self._v2_needs[int(option_id.removeprefix("need-"))]
        found = shell.locate(need.tab, need.inner, self._v2_dests)
        if found:
            self._v2_show(found[0].key, found[1])

    @on(DataTable.RowSelected, "#now-coins")
    def _v2_coin_selected(self, event: DataTable.RowSelected) -> None:
        coin = str(event.row_key.value or "")
        select = self.query_one("#compound-coin", Select)
        if coin and coin != select.value:
            try:
                select.value = coin
            except Exception:  # noqa: BLE001 - a coin with no cached data is not in the list
                pass
        self._v2_show("signal", 0)
        row = getattr(self, "_v2_coin_rows", {}).get(coin)
        if row is not None:
            env = self._call("compound.config", {"asset": coin}, quiet=True)
            own = env["result"]["own_settings"] if env["ok"] else {}
            self._set_editor_open(True, persist=False)
            self._show_preview(f"{coin} overview", compound_mod.coin_preview(
                row, own=own, adoptions=self._compound_adoptions, autopilot=self._compound_autopilot))

    def _v2_load_now(self) -> None:
        """The slower Now reads (the per-coin overview is ~0.7 s) run off the UI thread."""
        if self._v2_now_loading:
            return
        self._v2_now_loading = True
        self.run_worker(self._v2_now_worker, thread=True, exclusive=True, group="v2-now", exit_on_error=False)

    def _v2_now_worker(self) -> None:
        data: dict[str, Any] = {"queue.status": None, "compound.autopilot_status": None}
        try:
            data["compound.overview"] = self._call("compound.overview", quiet=True)
            data["compound.autopilot_status"] = self._call("compound.autopilot_status", quiet=True)
            data["queue.status"] = self._call("queue.status", quiet=True)
            data["compound.forward_status"] = self._call("compound.forward_status", quiet=True)
            if self._v2_cumulative is None:
                data["cumulative.summary"] = self._call("cumulative.summary", quiet=True)
        finally:
            try:
                self.call_from_thread(self._v2_render_now, data)
            except RuntimeError:  # the app closed while the reads ran
                self._v2_now_loading = False

    def _v2_render_now(self, data: dict[str, Any]) -> None:
        self._v2_now_loading = False
        if not self.query("#now-coins"):
            return
        self._v2_reads["queue.status"] = data.get("queue.status")
        raw_auto = data.get("compound.autopilot_status")
        self._v2_reads["compound.autopilot_status"] = raw_auto
        auto = raw_auto if isinstance(raw_auto, dict) else {}
        if auto.get("ok") and isinstance(auto.get("result"), dict):
            self._v2_autopilot, self._v2_autopilot_at = auto["result"], time.time()
        else:
            self._v2_autopilot = None
        fwd = data.get("compound.forward_status") or {}
        self._v2_forward = fwd["result"] if fwd.get("ok") else None
        cum = data.get("cumulative.summary") or {}
        if cum.get("ok"):
            self._v2_cumulative = str(cum["result"].get("headline") or "")

        table = self.query_one("#now-coins", GlossaryTable)
        table.clear()
        overview = data.get("compound.overview") or {}
        rows = (overview.get("result") or {}).get("coins", []) if overview.get("ok") else []
        self._v2_coin_rows = {r["asset"]: r for r in rows}
        for r in rows:
            table.add_row(r["asset"], r["backtest_verdict"], _pct(r["backtest_hit"]), str(r["fwd_calls"]),
                          _pct(r["fwd_hit"]), "-" if r["paper_usd"] is None else f"{r['paper_usd']:+,.2f}",
                          "RUNNING" if r["unattended"] else ("-" if r.get("live", True) else "backtest only"),
                          key=r["asset"])

        for i, (label, value, sub) in enumerate(shell.tiles(self._v2_reads, forward=self._v2_forward)[:4]):
            tile = Text()
            tile.append(f"{label}\n", shell.TOK["muted"])
            tile.append_text(value)
            tile.append("\n")
            tile.append_text(sub)
            self.query_one(f"#now-tile-{i}", Static).update(tile)

        self.query_one("#now-activity", Static).update(
            shell.activity_text(shell.activity(self._v2_autopilot, self._v2_reads)))
        research = Text()
        research.append(self._v2_cumulative or "No saved research results found.", shell.TOK["fg"])
        research.append("\nRanked by out-of-sample median Sharpe; rows under 10 trades are listed, never ranked. "
                        "3 Research › Cumulative has every file.", shell.TOK["muted"])
        self.query_one("#now-research", Static).update(research)
        self._v2_render_needs()
        self._v2_render_prices()

    def _v2_render_prices(self) -> None:
        widget = self.query("#now-prices")
        if not widget:
            return
        env = self._v2_reads.get("prices.status") or {}
        prices = (env.get("result") or {}).get("prices") or {} if env.get("ok") else {}
        line = Text()
        for product in ("SOL-USD", "BTC-USD", "ETH-USD", "XRP-USD", "DOGE-USD", "AVAX-USD", "LINK-USD", "SUI-USD"):
            quote = prices.get(product) or {}
            mid = quote.get("mid") or quote.get("last")
            if not isinstance(mid, (int, float)):
                continue
            spread = quote.get("spread_bps")
            line.append(f"{product.split('-')[0]:<5}", f"bold {shell.TOK['fg']}")
            line.append(f"${mid:>12,.4f}" if mid < 10 else f"${mid:>12,.2f}", shell.TOK["fg"])
            if isinstance(spread, (int, float)):
                line.append(f"   spread {spread:.1f} bps", shell.TOK["muted"])
            line.append("\n")
        widget.first(Static).update(line if line.plain else Text("No recorded prices yet.", shell.TOK["muted"]))

    # Explain: the same text F1 shows, in a drawer on the overlay layer so the screen never reflows.
    def action_v2_explain(self) -> None:
        panel = self.query_one("#v2-explain", Static)
        panel.toggle_class("open")
        if panel.has_class("open"):
            self._v2_fill_explain()

    def on_descendant_focus(self) -> None:
        if self.query("#v2-explain.open"):
            self._v2_fill_explain()

    def _v2_fill_explain(self) -> None:
        widget = self.focused
        title = ""
        if isinstance(widget, GlossaryTable) and widget.ordered_columns:
            column = widget.ordered_columns[max(0, min(widget.cursor_column, len(widget.ordered_columns) - 1))]
            title = f"{(widget.id or 'table').replace('-', ' ')} › {column.label}"
        elif widget is not None and widget.id:
            title = widget.id.replace("-", " ")
        if not title:
            dest = self._v2_destination(self._v2_dest)
            title = f"{dest.label} › {dest.views[self._v2_index].label}"
        self.query_one("#v2-explain", Static).update(shell.explain_text(title, self._focused_help_text()))

    # Palette: every destination, the app's own actions, and every registry command by name.
    def v2_palette_entries(self) -> list[shell.PaletteEntry]:
        from functools import partial

        from .commands import COMMANDS

        out: list[shell.PaletteEntry] = []
        for dest in self._v2_dests:
            for i, view in enumerate(dest.views):
                was = f" · was the {view.was} tab" if view.was else ""
                out.append(shell.PaletteEntry(f"Go to {dest.label} › {view.label}",
                                              f"key {dest.hotkey} · {dest.question}{was}",
                                              partial(self._v2_show, dest.key, i), "go"))
        for name, text, action in (("Explain the focused field", "? · the same text as F1, in a drawer",
                                    self.action_v2_explain),
                                   ("Glossary: search every term", "F1", self.action_show_help),
                                   ("Show or hide the editor", "ctrl+e", self.action_toggle_editor),
                                   ("Run backtest on the roster", "r", self.action_run_backtest),
                                   ("Cancel the running backtest", "c", self.action_cancel),
                                   ("Liquidity: refresh", "F5", self.action_liq_refresh)):
            out.append(shell.PaletteEntry(name, text, action, "action"))
        for name, cmd in sorted(COMMANDS.items()):
            runnable = cmd.read_only and not cmd.long_running and not any(p.required for p in cmd.params)
            tab, _button = self._v2_command_home(name)
            found = shell.locate(tab, None, self._v2_dests) if tab else None
            where = f"{found[0].label} › {found[0].views[found[1]].label}" if found else "—"
            text = (f"{cmd.describe[:100]} · {where}"
                    + (" · runs now (read-only)" if runnable else " · opens its view"))
            out.append(shell.PaletteEntry(name, text, partial(self._v2_palette_command, name, runnable), "cmd"))
        return out

    def _v2_command_home(self, name: str) -> tuple[str | None, str | None]:
        """The pane (and button) that owns a registry command: the button map first, then its prefix."""
        if name.startswith("experiments."):
            return "tab-bots", "bots-workbench"
        for selector, command in BUTTON_COMMANDS.items():
            if command != name:
                continue
            for widget in self.query(selector):
                pane = next((a for a in reversed(list(widget.ancestors)) if isinstance(a, TabPane)), None)
                if pane is not None and pane.id:
                    return pane.id, widget.id
        return shell.COMMAND_HOME.get(name.split(".")[0]), None

    def _v2_palette_command(self, name: str, runnable: bool) -> None:
        tab, button = self._v2_command_home(name)
        found = shell.locate(tab, None, self._v2_dests) if tab else None
        if found:
            self._v2_show(found[0].key, found[1])
        if button:
            self.call_after_refresh(lambda: self.query_one(f"#{button}").focus())
        if runnable:
            env = self._call(name, quiet=True)
            message = shell.summarise(env["result"]) if env["ok"] else self._msg(env)
            self.notify(message, title=name, severity="information" if env["ok"] else "error")
        else:
            self.notify(f"{name} is a write or needs parameters: its control is focused here.", title=name)


def main(argv: list[str] | None = None) -> int:
    """Entry point for `python3 -m soltui.tui` (`--classic` for the original tab bar)."""
    import argparse

    parser = argparse.ArgumentParser(prog="soltui", description="The SOL strategy console.")
    parser.add_argument("--classic", action="store_true",
                        help="show the original eighteen-tab bar instead of the v2 destinations")
    args = parser.parse_args(argv)
    SolTuiApp(ui_state_path=config_mod.CONFIG_DIR / "tui.json", ensure_autopilot=True, stream_prices=True,
              refresh_wallet=True, start="tab-backtest" if args.classic else "tab-now",
              classic=args.classic).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

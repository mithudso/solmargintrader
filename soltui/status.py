"""Pure menu-bar title logic, kept out of the rumps shell so it is testable
without a real macOS event loop.

Mirrors `netdnsmonitor/status.py`: one pure `build_title()` the app calls every
tick, plus the state it reads.

## The one rule this module exists to enforce

**A bare number in a menu bar implies a live account.** This project has no live
position, no broker connection, and no order path -- only historical backtests
and a paper simulator. So every money figure in the title carries its source as a
word: `last backtest +9.4%`, `paper +2.1%`. Never a naked `+9.4%`, which a glance
would read as "my money is up 9.4% right now".

The progress indicator is the other half: during a sweep the title shows work
remaining (`backtest 340/630`), because that is the question you actually have
while a sweep runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

# Leading glyphs. Kept ASCII-ish and narrow: a macOS status item has very little
# horizontal room, and wide emoji push the text off the bar on small displays.
ICONS = {
    "idle": "◦",
    "running": "⟳",
    "done": "✓",
    "paper": "▷",
    "error": "✕",
}

# A status item longer than this gets elided by macOS anyway; truncate ourselves
# so the important part (the number) survives rather than the label.
MAX_TITLE_CHARS = 40
# Longest free-form activity label allowed into a title. Capped at composition
# time rather than by clipping the finished string, because the figure the
# indicator exists to show sits at the END and tail-clipping would remove it.
MAX_ACTIVITY_CHARS = 12


class Phase(StrEnum):
    """What the app is doing right now."""

    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    PAPER = "paper"
    ERROR = "error"


@dataclass
class AppState:
    """Everything the title needs, and nothing else.

    Deliberately a plain dataclass with no behaviour: the TUI, the sweep runner
    and the paper simulator all write to it, and `build_title` only reads it.
    """

    phase: Phase = Phase.IDLE
    # Sweep progress. `total` of 0 means "unknown", which renders as a bare count.
    done: int = 0
    total: int = 0
    # Result of the most recent completed backtest, as a decimal fraction
    # (0.094 == +9.4%). None when nothing has been run this session.
    last_backtest_return: float | None = None
    # Paper-simulator session, if one is open. Same units.
    paper_return: float | None = None
    paper_fills: int = 0
    # Short message for the error phase.
    error: str | None = None
    # Free-form label for what is being swept, e.g. "pairs" -- shown when running.
    activity: str = ""
    warnings: list[str] = field(default_factory=list)

    @property
    def remaining(self) -> int:
        """Configurations left in the current sweep; 0 when total is unknown."""
        if self.total <= 0:
            return 0
        return max(self.total - self.done, 0)

    @property
    def percent(self) -> float | None:
        """Sweep completion in [0, 1], or None when total is unknown."""
        if self.total <= 0:
            return None
        return min(self.done / self.total, 1.0)


def format_pct(value: float) -> str:
    """Signed percentage with one decimal, e.g. '+9.4%' or '-70.8%'.

    Always signed: an unsigned '9.4%' is ambiguous at a glance, and this string
    ends up in a menu bar where there is no column header to disambiguate it.
    """
    return f"{value * 100:+.1f}%"


def build_title(state: AppState) -> str:
    """The menu-bar string for `state`.

    Priority order is deliberate: a running sweep outranks a stale result,
    because while work is in flight "how much is left" is the live question. An
    open paper session outranks a finished backtest for the same reason.
    """
    icon = ICONS.get(str(state.phase), "◦")

    if state.phase is Phase.ERROR:
        detail = state.error or "unknown"
        return _clip(f"{icon} SOL: error — {detail}")

    if state.phase is Phase.RUNNING:
        # Cap the caller-supplied label BEFORE composing. Clipping the finished
        # string would eat the count, which sits at the end -- that is the whole
        # reason the indicator exists while a sweep runs.
        what = f" {_shorten(state.activity, MAX_ACTIVITY_CHARS)}" if state.activity else ""
        if state.total > 0:
            return _clip(f"{icon} SOL:{what} {state.done}/{state.total}")
        return _clip(f"{icon} SOL:{what} running")

    if state.phase is Phase.PAPER:
        # "paper" is load-bearing: it is what stops this reading as real money.
        if state.paper_return is None:
            return _clip(f"{icon} SOL: paper session open")
        return _clip(
            f"{icon} SOL: paper {format_pct(state.paper_return)} "
            f"({state.paper_fills} fills)"
        )

    if state.phase is Phase.DONE and state.last_backtest_return is not None:
        # "last backtest" is load-bearing for the same reason.
        return _clip(
            f"{icon} SOL: last backtest {format_pct(state.last_backtest_return)}"
        )

    return _clip(f"{icon} SOL: idle")


def _shorten(text: str, limit: int) -> str:
    """Cap a free-form label, marking that it was cut."""
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 0)] + "…"


def _clip(text: str) -> str:
    """Last-resort length guard that preserves the TAIL of the string.

    Every title in this module puts its figure last (a count, a percentage), so
    an over-long title must lose its head, not its tail -- tail-clipping would
    remove the one thing the indicator exists to show. Variable-length labels are
    already capped by `_shorten` before composition; this only catches the
    residual case of an extreme number.
    """
    if len(text) <= MAX_TITLE_CHARS:
        return text
    # Try dropping the redundant ' SOL' word first -- it costs no information,
    # since the app owns the status item.
    trimmed = text.replace(" SOL:", ":", 1)
    if len(trimmed) <= MAX_TITLE_CHARS:
        return trimmed
    # Still too long: keep the icon and the tail, elide the middle.
    icon, _, rest = trimmed.partition(" ")
    keep = MAX_TITLE_CHARS - len(icon) - 2  # icon + space + ellipsis
    if keep <= 0:
        return trimmed[:MAX_TITLE_CHARS]
    return f"{icon} …{rest[-keep:]}"


def build_menu_summary(state: AppState) -> list[str]:
    """Multi-line detail for the dropdown, where there is room for context.

    The menu can say what the title cannot: that no figure here comes from a
    live account.
    """
    lines: list[str] = []
    if state.phase is Phase.RUNNING and state.total > 0:
        pct = state.percent or 0.0
        lines.append(
            f"Sweeping {state.activity or 'configurations'}: "
            f"{state.done}/{state.total} ({pct:.0%}), {state.remaining} left"
        )
    if state.last_backtest_return is not None:
        lines.append(
            f"Last backtest: {format_pct(state.last_backtest_return)} (historical simulation)"
        )
    if state.paper_return is not None:
        lines.append(
            f"Paper session: {format_pct(state.paper_return)} over {state.paper_fills} "
            f"simulated fills"
        )
    if state.error:
        lines.append(f"Error: {state.error}")
    lines.extend(state.warnings)
    lines.append("No live account is connected — every figure is a simulation.")
    return lines

"""Dry-run simulator for the Execute tab.

## Why this is a replay and not a live loop

The obvious design -- step forward bar by bar and compute fills as you go --
would create a SECOND order-execution path alongside `backtester/core/engine.py`.
That path would not be the one covered by the engine's known-answer tests, so the
two could silently diverge, and the divergence would show up as wrong money.

So this module computes nothing. It runs the existing, tested engine once over
the chosen window and exposes a **cursor** over the result: advance the cursor and
you see the equity and the intended fills up to that bar, exactly as the engine
produced them. It is a replay of a deterministic historical simulation.

## What this module cannot do, by construction

There is **no order path here at all** -- no key handling, no signing, no network
call, no venue client, not even unreachable code. That is the standard
`backtester/README.md` already sets, and this module holds to it. `intended_fills`
returns descriptions of what a strategy *would have done* on historical bars.
Nothing in `soltui/` can reach a venue; wiring live execution would mean routing
through `extension/src/core/commands.js` and its risk rails as separate,
explicit work.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from backtester.core.engine import BacktestResult, EngineConfig, run_backtest
from backtester.core.types import Trade

# Stated in the UI so the mode is never ambiguous.
MODE_LABEL = "DRY RUN — historical replay, no orders are placed"


@dataclass
class IntendedFill:
    """One fill the strategy would have made, for display."""

    bar_index: int
    when: str
    side: str
    reason: str
    price: float
    units: float
    notional: float
    cost: float
    equity_after: float

    @classmethod
    def from_trade(cls, t: Trade, when: str) -> IntendedFill:
        """Adapt an engine Trade for the UI without reinterpreting it."""
        return cls(
            bar_index=t.bar_index,
            when=when,
            side=t.side,
            reason=t.reason,
            price=t.price,
            units=t.units,
            notional=t.notional,
            cost=t.fee + t.slippage + t.borrow_fee_settled,
            equity_after=t.equity_after,
        )


class PaperSession:
    """A cursor over one completed backtest.

    `advance()` moves the cursor; `equity`, `intended_fills` and `pnl` report the
    state up to it. Nothing recomputes -- the underlying result is fixed at
    construction, which is what makes this safe to call from a UI thread.
    """

    def __init__(self, result: BacktestResult, timestamps: Sequence[int] | None = None) -> None:
        self.result = result
        self._ts = np.asarray(
            timestamps if timestamps is not None else result.timestamps
        )
        self.cursor = 0
        self.mode_label = MODE_LABEL

    # -- navigation ------------------------------------------------------

    def __len__(self) -> int:
        """Number of bars in the replay."""
        return int(len(self.result.equity))

    @property
    def at_end(self) -> bool:
        """True when the cursor has reached the final bar."""
        return self.cursor >= len(self) - 1

    def advance(self, bars: int = 1) -> int:
        """Move the cursor forward, clamped to the final bar. Returns the cursor."""
        if bars < 0:
            raise ValueError("advance() only moves forward; use reset() to rewind")
        self.cursor = min(self.cursor + bars, max(len(self) - 1, 0))
        return self.cursor

    def reset(self) -> None:
        """Rewind to the first bar."""
        self.cursor = 0

    def seek_end(self) -> int:
        """Jump to the final bar. Returns the cursor."""
        self.cursor = max(len(self) - 1, 0)
        return self.cursor

    # -- readouts --------------------------------------------------------

    @property
    def equity(self) -> float:
        """Equity at the cursor."""
        if not len(self):
            return 0.0
        return float(self.result.equity[self.cursor])

    @property
    def starting_equity(self) -> float:
        """Equity at the first bar, used as the P&L base."""
        if not len(self):
            return 0.0
        return float(self.result.equity[0])

    @property
    def pnl(self) -> float:
        """Return so far as a decimal fraction, e.g. 0.094 for +9.4%.

        Zero when the starting equity is non-positive rather than dividing by it.
        """
        base = self.starting_equity
        if base <= 0:
            return 0.0
        return self.equity / base - 1.0

    @property
    def exposure(self) -> float:
        """Signed exposure at the cursor."""
        if not len(self):
            return 0.0
        return float(self.result.exposure[self.cursor])

    def intended_fills(self) -> list[IntendedFill]:
        """Fills the strategy would have made up to and including the cursor."""
        return [
            IntendedFill.from_trade(t, self._when(t.bar_index))
            for t in self.result.trades
            if t.bar_index <= self.cursor
        ]

    @property
    def fill_count(self) -> int:
        """How many fills have occurred up to the cursor."""
        return sum(1 for t in self.result.trades if t.bar_index <= self.cursor)

    def _when(self, bar_index: int) -> str:
        """UTC date string for a bar index, or '' when out of range."""
        if bar_index < 0 or bar_index >= len(self._ts):
            return ""
        import datetime as dt

        return dt.datetime.fromtimestamp(
            int(self._ts[bar_index]), tz=dt.UTC
        ).strftime("%Y-%m-%d %H:%M")

    def summary(self) -> dict[str, Any]:
        """Everything the Execute tab shows, in one call."""
        return {
            "mode": self.mode_label,
            "bar": self.cursor,
            "bars_total": len(self),
            "when": self._when(self.cursor),
            "equity": self.equity,
            "pnl": self.pnl,
            "exposure": self.exposure,
            "fills": self.fill_count,
            "at_end": self.at_end,
            "live_orders_placed": 0,  # structurally always zero; see module docstring
        }


def start_session(
    strategy: Any,
    arrays: dict[str, np.ndarray],
    config: EngineConfig,
) -> PaperSession:
    """Run the engine once and return a replay cursor over the result.

    The engine call is the same one the backtester and every test use, so a paper
    session cannot disagree with a backtest of the same inputs.
    """
    result = run_backtest(strategy, arrays, config)
    return PaperSession(result, timestamps=arrays["ts"])

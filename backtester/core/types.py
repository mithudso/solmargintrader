"""Core value types for the backtester, including the look-ahead guard."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

BAR_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")

# Bar interval -> seconds. Coinbase granularities plus a daily default.
INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "6h": 21600,
    "1d": 86400,
}

# Crypto trades every calendar day, so a "year" is 365 bars at 1d -- not 252.
# This choice is stated in the report output, not just here.
HOURS_PER_YEAR = 365 * 24


def periods_per_year(interval: str) -> float:
    """Bars per year for the given interval, using a 365-day crypto year."""
    return (365 * 86400) / INTERVAL_SECONDS[interval]


def hours_per_bar(interval: str) -> float:
    """Length of one bar in hours (borrow fees accrue hourly)."""
    return INTERVAL_SECONDS[interval] / 3600.0


class Mode(enum.StrEnum):
    """Execution mode: unlevered spot, or Jupiter-style perpetual."""

    SPOT = "spot"
    PERP = "perp"


class Side(enum.StrEnum):
    """Direction of a position or fill."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class LookAheadError(IndexError):
    """Raised when a strategy reads a bar at or beyond the current one.

    Subclasses IndexError so that natural numpy/list out-of-bounds handling
    and this guard present the same interface to callers.
    """


@dataclass(frozen=True)
class Bar:
    """A single OHLCV bar. `ts` is UTC epoch seconds."""

    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class BarWindow:
    """A read-only view of history up to and including bar `i`.

    This is the structural look-ahead guard. A strategy receives only this
    object, and every accessor truncates at `i`. Reading past `i` raises
    LookAheadError rather than returning a future value.

    The arrays are stored once and sliced per access; slicing a numpy array
    is a view, so this is cheap.
    """

    __slots__ = ("_ts", "_open", "_high", "_low", "_close", "_volume", "_i")

    def __init__(
        self,
        ts: np.ndarray,
        open_: np.ndarray,
        high: np.ndarray,
        low: np.ndarray,
        close: np.ndarray,
        volume: np.ndarray,
        i: int,
    ) -> None:
        self._ts = ts
        self._open = open_
        self._high = high
        self._low = low
        self._close = close
        self._volume = volume
        self._i = i

    @property
    def i(self) -> int:
        """Index of the current (most recent visible) bar."""
        return self._i

    def __len__(self) -> int:
        """Number of visible bars, i.e. i + 1."""
        return self._i + 1

    # -- truncated series accessors -------------------------------------
    # Each returns bars [0 .. i]. Indexing the result at i+1 raises
    # IndexError from numpy, which is exactly the guard we want.

    @property
    def ts(self) -> np.ndarray:
        """Timestamps up to and including the current bar."""
        return self._ts[: self._i + 1]

    @property
    def opens(self) -> np.ndarray:
        """Open prices up to and including the current bar."""
        return self._open[: self._i + 1]

    @property
    def highs(self) -> np.ndarray:
        """High prices up to and including the current bar."""
        return self._high[: self._i + 1]

    @property
    def lows(self) -> np.ndarray:
        """Low prices up to and including the current bar."""
        return self._low[: self._i + 1]

    @property
    def closes(self) -> np.ndarray:
        """Close prices up to and including the current bar."""
        return self._close[: self._i + 1]

    @property
    def volumes(self) -> np.ndarray:
        """Volumes up to and including the current bar."""
        return self._volume[: self._i + 1]

    def bar(self, offset: int = 0) -> Bar:
        """Bar at `offset` bars before the current one (offset >= 0).

        Raises LookAheadError for a negative offset, which would name a
        future bar.
        """
        if offset < 0:
            raise LookAheadError(
                f"offset {offset} refers to a future bar; only offset >= 0 is visible"
            )
        j = self._i - offset
        if j < 0:
            raise IndexError(f"offset {offset} predates the start of history")
        return Bar(
            ts=int(self._ts[j]),
            open=float(self._open[j]),
            high=float(self._high[j]),
            low=float(self._low[j]),
            close=float(self._close[j]),
            volume=float(self._volume[j]),
        )

    def at(self, index: int) -> Bar:
        """Bar at absolute `index`, guarded against reading the future."""
        if index > self._i:
            raise LookAheadError(
                f"bar {index} is in the future; current bar is {self._i}"
            )
        if index < 0:
            raise IndexError("negative absolute index is not supported")
        return self.bar(self._i - index)


@dataclass
class Trade:
    """One executed fill."""

    ts: int
    bar_index: int
    side: str
    price: float
    units: float
    notional: float
    fee: float
    slippage: float
    borrow_fee_settled: float
    realized_pnl: float
    equity_after: float
    reason: str = "signal"


@dataclass
class Position:
    """An open position. Notional is USD size; collateral is posted margin."""

    side: Side = Side.FLAT
    units: float = 0.0
    entry_price: float = 0.0
    collateral: float = 0.0
    opened_ts: int = 0
    opened_index: int = -1
    accrued_borrow_fee: float = 0.0

    @property
    def is_open(self) -> bool:
        """True when the position holds a non-negligible number of units."""
        return self.side is not Side.FLAT and abs(self.units) > 1e-12

    def notional_at(self, price: float) -> float:
        """Mark-to-market notional at `price`."""
        return abs(self.units) * price

    @property
    def entry_notional(self) -> float:
        """Notional at entry, which is the base for fee accrual."""
        return abs(self.units) * self.entry_price

    def unrealized_pnl(self, price: float) -> float:
        """Price PnL only; borrow fees are tracked separately."""
        if not self.is_open:
            return 0.0
        direction = 1.0 if self.side is Side.LONG else -1.0
        return direction * (price - self.entry_price) * abs(self.units)


@dataclass
class CostConfig:
    """Fee, slippage, and borrow-rate settings.

    Borrow rates are expressed in **basis points per hour** to sidestep the
    documented deci-bps ambiguity in the venue docs. 1.6 bps/hr == 0.016%/hr
    == ~140% APR, which is the documented SOL reference point.
    """

    fee_bps: float = 6.0
    slippage_bps: float = 2.0
    # Jupiter base fee is 0.06% on open and again on close.
    perp_base_fee_bps: float = 6.0
    max_hourly_rate_bps_long: float = 1.6
    max_hourly_rate_bps_short: float = 0.3
    utilization: float = 0.5
    # Governance proposed a dual-slope model with a rate floor that is
    # incompatible with the published flat-linear formula. Default 0 keeps
    # the published behaviour; set it to model the proposed floor.
    min_hourly_rate_bps: float = 0.0
    kink_utilization: float | None = None
    kink_slope_multiplier: float = 3.0
    # Protocol constant. Distinct from the user-facing leverage cap.
    max_lev_constant: float = 500.0

    @property
    def maintenance_margin_fraction(self) -> float:
        """size / max_lev expressed as a fraction of notional (0.002)."""
        return 1.0 / self.max_lev_constant


@dataclass
class RunManifest:
    """Everything needed to reproduce a run byte-for-byte."""

    asset: str
    start: str
    end: str
    interval: str
    mode: str
    leverage: float
    initial_capital: float
    fill_delay: int
    seed: int
    rebalance_threshold: float
    costs: dict[str, Any]
    strategies: dict[str, dict[str, Any]]
    data_source: str
    data_checksum: str
    bar_count: int
    split: float | None
    library_versions: dict[str, str] = field(default_factory=dict)
    periods_per_year: float = 0.0
    sharpe_convention: str = (
        "mean(excess)/stdev(excess, ddof=1) * sqrt(periods_per_year); "
        "365-day crypto year; risk-free rate is an explicit parameter"
    )

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form for JSON serialisation."""
        return asdict(self)

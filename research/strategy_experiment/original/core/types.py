"""Core value types for the backtester, including the look-ahead guard."""

from __future__ import annotations

import enum
import math
from numbers import Real
from collections.abc import Mapping
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


def validate_bar_arrays(
    arrays: Mapping[str, Any], interval: str, *, require_open_volume: bool = True,
) -> dict[str, np.ndarray]:
    """Normalize finite 1-D bars and refuse cadence this simulator cannot model.

    Loaders may retain gaps for inspection. Simulation requires every nominal
    interval: missing bars hide liquidation extremes and elapsed carry, so this
    boundary never invents OHLC or treats missing time as one observed bar.
    """
    if not isinstance(arrays, Mapping):
        raise ValueError("market arrays must be a mapping")
    if not isinstance(interval, str) or interval not in INTERVAL_SECONDS:
        raise ValueError("unsupported bar interval")
    required = ("ts", "high", "low", "close") + (("open", "volume") if require_open_volume else ())
    missing = [name for name in required if name not in arrays]
    if missing:
        raise ValueError(f"market arrays missing required series: {', '.join(missing)}")
    names = tuple(dict.fromkeys((*required, *(name for name in ("open", "volume") if name in arrays))))
    checked: dict[str, np.ndarray] = {}
    for name in names:
        raw = np.asarray(arrays[name])
        if raw.ndim != 1 or raw.dtype.kind not in "iuf":
            raise ValueError(f"{name} must be a one-dimensional numeric series")
        values = raw.astype("float64", copy=False)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{name} contains non-finite values")
        checked[name] = values
    n = checked["close"].size
    if n == 0:
        raise ValueError("cannot backtest an empty series")
    if any(values.size != n for values in checked.values()):
        raise ValueError("market series lengths disagree")
    timestamp = checked["ts"]
    if np.any(np.abs(timestamp) > 10_000_000_000) or np.any(timestamp != np.floor(timestamp)):
        raise ValueError("timestamps must be integral UTC epoch seconds, not milliseconds")
    ts = timestamp.astype("int64")
    if n > 1:
        deltas = np.diff(ts)
        if np.any(deltas <= 0):
            raise ValueError("timestamps must be strictly ascending UTC epoch seconds")
        if np.any(deltas != INTERVAL_SECONDS[interval]):
            raise ValueError(f"timestamp cadence must equal {interval}; gapped or mismatched bars are unsupported")
    checked["ts"] = ts
    for name in ("open", "high", "low", "close"):
        if name in checked and np.any(checked[name] <= 0):
            raise ValueError(f"{name} must contain positive prices")
    high, low, close = checked["high"], checked["low"], checked["close"]
    open_ = checked.get("open", close)
    if np.any(high < low) or np.any(high < np.maximum(open_, close) - 1e-9) or np.any(low > np.minimum(open_, close) + 1e-9):
        raise ValueError("OHLC high/low do not contain the open and close")
    if "volume" in checked and np.any(checked["volume"] < 0):
        raise ValueError("volume must be nonnegative")
    return checked


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

    Public arrays are owned, read-only copies of visible history, cached for
    this window. A NumPy view would expose future bars through its public .base
    and could let an indicator modify the engine's original market data. Private
    attributes are implementation details, not a hostile-Python sandbox.
    """

    __slots__ = ("_ts", "_open", "_high", "_low", "_close", "_volume", "_i", "_visible")

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
        self._visible: dict[str, np.ndarray] = {}

    def _series(self, name: str, source: np.ndarray) -> np.ndarray:
        if name not in self._visible:
            values = np.array(source[: self._i + 1], copy=True)
            values.setflags(write=False)
            self._visible[name] = values
        return self._visible[name]

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
        return self._series("ts", self._ts)

    @property
    def opens(self) -> np.ndarray:
        """Open prices up to and including the current bar."""
        return self._series("opens", self._open)

    @property
    def highs(self) -> np.ndarray:
        """High prices up to and including the current bar."""
        return self._series("highs", self._high)

    @property
    def lows(self) -> np.ndarray:
        """Low prices up to and including the current bar."""
        return self._series("lows", self._low)

    @property
    def closes(self) -> np.ndarray:
        """Close prices up to and including the current bar."""
        return self._series("closes", self._close)

    @property
    def volumes(self) -> np.ndarray:
        """Volumes up to and including the current bar."""
        return self._series("volumes", self._volume)

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
    # Paid at entry/increase, allocated to decided outcomes when units close.
    entry_costs: float = 0.0

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
    # Liquidation is a forced market close, not a fill at the quoted level. The
    # fill price moves ADVERSELY by this many bps from the liquidation price
    # (down for a long, up for a short). Default 0 keeps legacy runs unchanged;
    # the leverage-tier presets set a nonzero value.
    liquidation_penalty_bps: float = 0.0
    # The venue forfeits all REMAINING collateral on liquidation (the maintenance
    # margin is not returned). False keeps the legacy payout of whatever is left.
    liquidation_forfeits_collateral: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Refuse unusable costs before they can subsidize or poison a run."""
        for name in ("fee_bps", "slippage_bps", "perp_base_fee_bps",
                     "max_hourly_rate_bps_long", "max_hourly_rate_bps_short",
                     "min_hourly_rate_bps", "kink_slope_multiplier",
                     "liquidation_penalty_bps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.slippage_bps >= 10_000:
            raise ValueError("slippage_bps must be below 10000")
        if self.liquidation_penalty_bps >= 10_000:
            raise ValueError("liquidation_penalty_bps must be below 10000")
        if not isinstance(self.liquidation_forfeits_collateral, bool):
            raise ValueError("liquidation_forfeits_collateral must be boolean")
        if not isinstance(self.max_lev_constant, Real) or isinstance(self.max_lev_constant, bool) or not math.isfinite(self.max_lev_constant) or self.max_lev_constant <= 0:
            raise ValueError("max_lev_constant must be finite and positive")
        for name in ("utilization", "kink_utilization"):
            value = getattr(self, name)
            if name == "kink_utilization" and value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")

    @property
    def maintenance_margin_fraction(self) -> float:
        """size / max_lev expressed as a fraction of notional (0.002)."""
        return 1.0 / self.max_lev_constant


class IntrabarLayer:
    """Finer bars used to check a coarse bar for a liquidation hidden inside it.

    A daily bar's low and high say THAT the range was visited, not WHEN. Walking
    the finer bars in order recovers the order of events, so borrow fees accrue
    to the moment of the touch and the fill uses the finer bar's open when the
    market gapped through the level. Layers may have gaps (SOL_1h has two);
    a coarse bar is refined only when the layer covers it completely, and every
    other bar falls back to the coarse range, which is never less severe.
    """

    __slots__ = ("interval", "ts", "open", "high", "low", "close")

    def __init__(self, interval: str, arrays: Mapping[str, Any]) -> None:
        if interval not in INTERVAL_SECONDS:
            raise ValueError("unsupported intrabar interval")
        cols: dict[str, np.ndarray] = {}
        for name in ("ts", "open", "high", "low", "close"):
            if name not in arrays:
                raise ValueError(f"intrabar arrays missing {name}")
            raw = np.asarray(arrays[name])
            if raw.ndim != 1 or raw.dtype.kind not in "iuf":
                raise ValueError(f"intrabar {name} must be a one-dimensional numeric series")
            values = raw.astype("float64", copy=False)
            if not np.all(np.isfinite(values)):
                raise ValueError(f"intrabar {name} contains non-finite values")
            cols[name] = values
        n = cols["ts"].size
        if any(v.size != n for v in cols.values()):
            raise ValueError("intrabar series lengths disagree")
        ts = cols["ts"]
        if n > 1 and np.any(np.diff(ts) <= 0):
            raise ValueError("intrabar timestamps must be strictly ascending")
        if n and (np.any(np.abs(ts) > 10_000_000_000) or np.any(ts != np.floor(ts))):
            raise ValueError("intrabar timestamps must be integral UTC epoch seconds")
        for name in ("open", "high", "low", "close"):
            if np.any(cols[name] <= 0):
                raise ValueError(f"intrabar {name} must be positive")
        if np.any(cols["high"] < cols["low"]) or np.any(
            cols["high"] < np.maximum(cols["open"], cols["close"]) - 1e-9
        ) or np.any(cols["low"] > np.minimum(cols["open"], cols["close"]) + 1e-9):
            raise ValueError("intrabar high/low do not contain the open and close")
        self.interval = interval
        self.ts = ts.astype("int64")
        self.open, self.high = cols["open"], cols["high"]
        self.low, self.close = cols["low"], cols["close"]
        for arr in (self.ts, self.open, self.high, self.low, self.close):
            arr.setflags(write=False)

    @property
    def seconds(self) -> int:
        """Length of one fine bar in seconds."""
        return INTERVAL_SECONDS[self.interval]


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

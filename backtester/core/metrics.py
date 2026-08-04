"""Performance metrics with explicitly stated conventions.

Ambiguous annualisation is the most common source of a wrong Sharpe ratio, so
every convention here is named in the signature and echoed into the report:
sample stdev (ddof=1), a 365-day crypto year, and an explicit risk-free rate.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Sequence

import numpy as np

from .types import Trade


@dataclass
class DrawdownInfo:
    """Worst peak-to-trough decline on an equity curve."""

    max_drawdown: float
    peak_index: int
    trough_index: int
    peak_ts: int
    trough_ts: int
    duration_bars: int


@dataclass
class Metrics:
    """Full metric set for one strategy run."""

    total_return: float
    cagr: float
    sharpe: float
    sortino: float
    max_drawdown: float
    max_drawdown_start: str
    max_drawdown_end: str
    max_drawdown_bars: int
    calmar: float
    volatility_annual: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    trade_count: int
    exposure_fraction: float
    total_fees: float
    total_borrow_fees: float
    liquidation_count: int
    final_equity: float
    bars: int

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form for CSV/JSON output."""
        return asdict(self)


def simple_returns(equity: np.ndarray) -> np.ndarray:
    """Per-bar simple returns of an equity curve.

    Guards against a zero or negative equity value, which would otherwise
    produce inf/NaN and silently poison every downstream metric.
    """
    equity = np.asarray(equity, dtype="float64")
    if equity.size < 2:
        return np.zeros(0, dtype="float64")
    prev = equity[:-1]
    safe_prev = np.where(prev <= 0.0, np.nan, prev)
    rets = (equity[1:] - prev) / safe_prev
    # A wiped-out account has no further returns; treat as flat at -100%.
    return np.nan_to_num(rets, nan=0.0, posinf=0.0, neginf=-1.0)


def total_return(equity: np.ndarray) -> float:
    """Cumulative return from first to last equity point."""
    if len(equity) < 2 or equity[0] <= 0:
        return 0.0
    return float(equity[-1] / equity[0] - 1.0)


def cagr(equity: np.ndarray, periods_per_year: float) -> float:
    """Compound annual growth rate. Returns -1.0 for a wiped-out account."""
    if len(equity) < 2 or equity[0] <= 0:
        return 0.0
    if equity[-1] <= 0:
        return -1.0
    years = (len(equity) - 1) / periods_per_year
    if years <= 0:
        return 0.0
    return float((equity[-1] / equity[0]) ** (1.0 / years) - 1.0)


def sharpe_ratio(
    returns: np.ndarray,
    periods_per_year: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Annualised Sharpe ratio.

    `(mean(excess) / stdev(excess, ddof=1)) * sqrt(periods_per_year)`, where
    `risk_free_rate` is an annual rate converted to a per-bar rate. Returns
    0.0 when there is no dispersion, rather than inf.
    """
    returns = np.asarray(returns, dtype="float64")
    if returns.size < 2:
        return 0.0
    rf_per_bar = risk_free_rate / periods_per_year
    excess = returns - rf_per_bar
    sd = float(np.std(excess, ddof=1))
    if sd <= 1e-15:
        return 0.0
    return float(np.mean(excess) / sd * np.sqrt(periods_per_year))


def sortino_ratio(
    returns: np.ndarray,
    periods_per_year: float,
    risk_free_rate: float = 0.0,
) -> float:
    """Annualised Sortino ratio using downside deviation below the target."""
    returns = np.asarray(returns, dtype="float64")
    if returns.size < 2:
        return 0.0
    rf_per_bar = risk_free_rate / periods_per_year
    excess = returns - rf_per_bar
    downside = np.minimum(excess, 0.0)
    dd = float(np.sqrt(np.mean(downside**2)))
    if dd <= 1e-15:
        return 0.0
    return float(np.mean(excess) / dd * np.sqrt(periods_per_year))


def annual_volatility(returns: np.ndarray, periods_per_year: float) -> float:
    """Annualised sample standard deviation of per-bar returns."""
    returns = np.asarray(returns, dtype="float64")
    if returns.size < 2:
        return 0.0
    return float(np.std(returns, ddof=1) * np.sqrt(periods_per_year))


def max_drawdown(equity: np.ndarray, timestamps: np.ndarray) -> DrawdownInfo:
    """Worst peak-to-trough decline, with its location and duration.

    Reported as a negative fraction (-0.42 means a 42% decline).
    """
    equity = np.asarray(equity, dtype="float64")
    if equity.size == 0:
        return DrawdownInfo(0.0, 0, 0, 0, 0, 0)

    running_peak = np.maximum.accumulate(equity)
    safe_peak = np.where(running_peak <= 0.0, np.nan, running_peak)
    dd = (equity - running_peak) / safe_peak
    dd = np.nan_to_num(dd, nan=0.0)

    trough = int(np.argmin(dd))
    peak = int(np.argmax(equity[: trough + 1])) if trough > 0 else 0
    return DrawdownInfo(
        max_drawdown=float(dd[trough]),
        peak_index=peak,
        trough_index=trough,
        peak_ts=int(timestamps[peak]),
        trough_ts=int(timestamps[trough]),
        duration_bars=trough - peak,
    )


def _fmt_ts(ts: int) -> str:
    """UTC date string for a manifest/report field."""
    import datetime as _dt

    if ts <= 0:
        return ""
    return _dt.datetime.fromtimestamp(ts, tz=_dt.UTC).strftime("%Y-%m-%d")


def trade_stats(trades: Sequence[Trade]) -> dict[str, float]:
    """Win rate, profit factor, and average win/loss over closing trades.

    Only fills that realise PnL count as a decided trade. An opening fill has
    no outcome yet, and neither does an increase in size -- counting either
    would dilute the win rate (a resize_up realises only its own cost, so it
    would register as a guaranteed loser).
    """
    undecided = {"open", "resize_up"}
    realised = [t.realized_pnl for t in trades if t.reason not in undecided]
    decided = [p for p in realised if abs(p) > 1e-12]
    if not decided:
        return {
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "trade_count": 0,
        }
    wins = [p for p in decided if p > 0]
    losses = [p for p in decided if p < 0]
    gross_win = float(sum(wins))
    gross_loss = float(-sum(losses))
    return {
        "win_rate": len(wins) / len(decided),
        # An unbounded profit factor is reported as inf deliberately: it means
        # zero losing trades, which is information, not an error.
        "profit_factor": (gross_win / gross_loss) if gross_loss > 1e-12 else float("inf"),
        "avg_win": (gross_win / len(wins)) if wins else 0.0,
        "avg_loss": (-gross_loss / len(losses)) if losses else 0.0,
        "trade_count": len(decided),
    }


def compute_metrics(
    equity: np.ndarray,
    timestamps: np.ndarray,
    trades: Sequence[Trade],
    exposure: np.ndarray,
    periods_per_year: float,
    risk_free_rate: float = 0.0,
    liquidation_count: int = 0,
) -> Metrics:
    """Assemble the full metric set for one run."""
    equity = np.asarray(equity, dtype="float64")
    rets = simple_returns(equity)
    dd = max_drawdown(equity, timestamps)
    ts_stats = trade_stats(trades)
    c = cagr(equity, periods_per_year)

    return Metrics(
        total_return=total_return(equity),
        cagr=c,
        sharpe=sharpe_ratio(rets, periods_per_year, risk_free_rate),
        sortino=sortino_ratio(rets, periods_per_year, risk_free_rate),
        max_drawdown=dd.max_drawdown,
        max_drawdown_start=_fmt_ts(dd.peak_ts),
        max_drawdown_end=_fmt_ts(dd.trough_ts),
        max_drawdown_bars=dd.duration_bars,
        calmar=(c / abs(dd.max_drawdown)) if abs(dd.max_drawdown) > 1e-12 else 0.0,
        volatility_annual=annual_volatility(rets, periods_per_year),
        win_rate=ts_stats["win_rate"],
        profit_factor=ts_stats["profit_factor"],
        avg_win=ts_stats["avg_win"],
        avg_loss=ts_stats["avg_loss"],
        trade_count=int(ts_stats["trade_count"]),
        exposure_fraction=float(np.mean(np.abs(exposure))) if len(exposure) else 0.0,
        total_fees=float(sum(t.fee + t.slippage for t in trades)),
        total_borrow_fees=float(sum(t.borrow_fee_settled for t in trades)),
        liquidation_count=liquidation_count,
        final_equity=float(equity[-1]) if equity.size else 0.0,
        bars=int(equity.size),
    )

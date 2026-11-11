"""Offline Volty Expan Close stop-order simulation, never an execution client.

The public Pine rule uses SMA(TR), not Wilder ATR. Orders formed at a close
become active on the next candle. OHLC does not reveal the intrabar path;
``nearest`` follows the TradingView historical OHLC path convention. This is
an independently implemented research model, not certified Pine fill parity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class VoltyConfig:
    length: int = 5
    atr_mult: float = 0.75
    fee_bps: float = 10.0
    slippage_bps: float = 2.0
    carry_bps_hour: float = 0.1
    initial_capital: float = 10_000.0

    def __post_init__(self):
        if isinstance(self.length, bool) or not isinstance(self.length, int) or self.length < 1:
            raise ValueError("length must be a positive integer")
        for name in ("atr_mult", "fee_bps", "slippage_bps", "carry_bps_hour", "initial_capital"):
            value = getattr(self, name)
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.atr_mult <= 0 or self.initial_capital <= 0 or self.slippage_bps >= 10_000:
            raise ValueError("multiplier/capital must be positive and slippage < 10000 bps")


def validate(bars: dict[str, np.ndarray], step: int) -> None:
    if step <= 0 or len(bars["timestamp"]) < 3:
        raise ValueError("positive cadence and at least three bars required")
    n = len(bars["timestamp"])
    if any(len(v) != n or not np.isfinite(v).all() for v in bars.values()):
        raise ValueError("finite equal-length OHLCV arrays required")
    ts = bars["timestamp"]
    if np.any(ts != ts.astype(np.int64)) or np.any(np.diff(ts) != step):
        raise ValueError("timestamps must be integral, unique and contiguous")
    o, h, lo, c = (bars[k] for k in ("open", "high", "low", "close"))
    if np.any(lo <= 0) or np.any(h < np.maximum(o, c)) or np.any(lo > np.minimum(o, c)):
        raise ValueError("invalid OHLC envelope")
    if np.any(bars["volume"] < 0):
        raise ValueError("negative volume")


def stop_levels(bars: dict[str, np.ndarray], config: VoltyConfig) -> tuple[np.ndarray, np.ndarray]:
    """Return active levels; index t contains only information through t-1."""
    h, lo, c = (bars[k] for k in ("high", "low", "close"))
    tr = np.maximum(h[1:] - lo[1:], np.maximum(abs(h[1:] - c[:-1]), abs(lo[1:] - c[:-1])))
    sums = np.r_[0.0, np.cumsum(tr)]
    width = np.full(len(c), np.nan)
    length = config.length
    if len(tr) >= length:
        width[length:] = (sums[length:] - sums[:-length]) / length * config.atr_mult
    # ta.tr is unavailable at bar zero; Pine also guards not na(close[length]).
    return np.r_[np.nan, c[:-1] + width[:-1]], np.r_[np.nan, c[:-1] - width[:-1]]


def simulate(bars: dict[str, np.ndarray], config: VoltyConfig, step: int,
             start: int = 0, end: int | None = None, path: str = "nearest",
             keep_fills: bool = False) -> dict:
    """Fresh 1x equity-sized long/short book; no leverage or live venue claim.

    Size stays fixed until reversal. Both replacement stops are eligible each
    bar; same-side triggers do not pyramid. Opposite triggers close then reverse.
    Carry is a declared scenario on marked notional, not observed ZEC funding.
    Each segment pays a final market close. Warm history creates no positions.
    """
    validate(bars, step)
    end = len(bars["close"]) if end is None else end
    if not 0 <= start < end <= len(bars["close"]):
        raise ValueError("invalid replay window")
    if path not in ("nearest", "high-first", "low-first"):
        raise ValueError("unknown OHLC path")
    upper, lower = stop_levels(bars, config)
    o, h, lo, c, ts = (bars[k] for k in ("open", "high", "low", "close", "timestamp"))
    cash, qty, entry = config.initial_capital, 0.0, 0.0
    fee, slip = config.fee_bps / 1e4, config.slippage_bps / 1e4
    fees = slippage = carry = 0.0
    trades = wins = ambiguous = 0
    eq = np.empty(end - start)
    fills = []
    bankrupt = False
    trade_equity = cash

    def fill(direction, raw, i, terminal=False):
        nonlocal cash, qty, entry, fees, slippage, trades, wins, trade_equity, bankrupt
        if qty and (terminal or np.sign(qty) != direction):
            execution = raw * (1 - np.sign(qty) * slip)
            paid = abs(qty) * execution * fee
            slippage += abs(qty) * abs(execution - raw)
            fees += paid
            cash += qty * (execution - entry) - paid
            trades += 1
            wins += int(cash > trade_equity)
            if keep_fills:
                fills.append({"timestamp": int(ts[i]), "event": "close", "price": float(execution), "units": float(qty)})
            qty = 0.0
        if cash <= 0:
            bankrupt = True
            cash = 0.0
        if not terminal and not qty and not bankrupt:
            trade_equity = cash
            execution = raw * (1 + direction * slip)
            units = cash / (execution * (1 + fee))
            paid = units * execution * fee
            cash -= paid
            fees += paid
            slippage += units * abs(execution - raw)
            qty, entry = direction * units, execution
            if keep_fills:
                fills.append({"timestamp": int(ts[i]), "event": "open", "price": float(execution), "units": float(qty)})

    for i in range(start, end):
        if bankrupt:
            eq[i-start] = 0.0
            continue
        up, down = upper[i], lower[i]
        buy, sell = h[i] >= up, lo[i] <= down
        if buy or sell:
            if buy and sell:
                ambiguous += 1
            high_first = (path == "high-first" or (path == "nearest" and h[i]-o[i] < o[i]-lo[i]))
            # A gap crosses its stop at the open before any intrabar movement.
            buy_first = o[i] >= up or (o[i] > down and high_first)
            events = ((1, buy, max(o[i], up)), (-1, sell, min(o[i], down)))
            if not buy_first:
                events = events[::-1]
            for direction, touched, raw in events:
                if touched:
                    fill(direction, raw, i)
        if qty:
            cost = abs(qty) * c[i] * config.carry_bps_hour / 1e4 * step / 3600
            cash -= cost
            carry += cost
            # Refuse to compound a synthetic account once its equity is gone.
            if cash + qty * (c[i]-entry) <= 0:
                bankrupt = True
                cash, qty = 0.0, 0.0
        eq[i-start] = max(0.0, cash + qty * (c[i]-entry))
    if qty:
        fill(0, c[end-1], end-1, terminal=True)
        eq[-1] = cash
    previous = np.r_[config.initial_capital, eq[:-1]]
    returns = np.divide(eq, previous, out=np.ones_like(eq), where=previous > 0) - 1
    peak = np.maximum.accumulate(np.r_[config.initial_capital, eq])[1:]
    std = float(np.std(returns))
    result = {"return": float(eq[-1] / config.initial_capital - 1),
              "max_drawdown": float(np.max(1 - eq/peak)),
              "sharpe": float(np.mean(returns)/std * math.sqrt(365*86400/step)) if std > 0 else 0.0,
              "trades": trades, "win_rate": wins/trades if trades else 0.0,
              "fees": fees, "slippage": slippage, "carry": carry,
              "ambiguous_bars": ambiguous, "bankrupt": bankrupt,
              "first_timestamp": int(ts[start]), "last_timestamp": int(ts[end-1]),
              "equity": eq}
    if keep_fills:
        result["fills"] = fills
    return result

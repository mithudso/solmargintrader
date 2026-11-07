"""Compound five-minute scorecard: score each metric, aggregate into an UP / DOWN / FLAT call.

    from backtester.core.scorecard import default_config, evaluate, explain, Bars

Every component maps visible history to a score in [-1, 1] (+1 = the metric says the next
bar closes higher, -1 = lower, 0 = no opinion, NaN = undefined here). Gates map history to
"blocked" (no trade, whatever the score says). The aggregator combines enabled scores with
per-family de-duplication and regime weighting, then applies the gates.

## Why the score series are computed vectorised, and what keeps that honest

A strategy normally recomputes its indicator on every bar from a `BarWindow`, which cannot
see the future by construction. Thirty components over a year of 5m bars (105k bars) that
way is O(n^2) and takes hours. So every component here is a vectorised, *causal* function:
rolling windows and `ewm(adjust=False)` recursions, where the value at bar t depends only on
bars <= t. Causality is not assumed. `tests/test_scorecard.py` checks every component for
**prefix invariance**: the score at bar t computed from bars [0..t] must equal the score at
bar t computed from the whole series. A one-bar leak (a `shift(-1)`, a centred window, a
`fillna(method="bfill")`) fails that test.

## Why families are de-duplicated

RSI, Stochastic, CCI, Bollinger %B and the z-score are five views of one quantity (where the
close sits in its recent range): measured on five coins their 5m scores correlate 0.80-0.98, so
they form one family, "stretch". Price-vs-EMA, the EMA cross and Ichimoku correlate 0.83-0.89
("ma-trend"); MACD and rate of change 0.80 ("momentum"). Families are claims about measurement,
not about names: `relations()` reports pairs that move together or against each other. Averaging every enabled indicator lets
the family with the most members outvote a family with one, which measures how many
indicators someone wrote, not how much evidence there is. With `dedupe_families` on, each
family contributes its weighted mean once, at the weight of its heaviest member.

## Why regime weighting exists

The source catalogue (5minleveragestrategies.json, `regime_identification`) states that
trend signals and mean-reversion signals fail in each other's regimes. The aggregator
classifies each bar as trend / range / squeeze / neutral from ADX and Bollinger bandwidth,
then multiplies each component's weight by its style's multiplier for that regime.

## What this module does not do

No I/O, no network, no order path. Live data (funding, open interest, order book, headlines)
arrives through `aux`; components that need it are NaN when it is absent, and the caller
reports them as unavailable instead of as a neutral zero.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import pandas as pd

BAR_SECONDS = 300

# Component parameters and auxiliary inputs: plain JSON-shaped mappings.
Params = dict[str, Any]

STYLES = ("trend", "momentum", "reversion", "breakout", "flow", "derivatives", "context",
          "lifecycle", "adaptive", "cross-asset", "gate")
REGIMES = ("trend", "range", "squeeze", "neutral")

# Weight multipliers per (regime, style). Styles not listed keep 1.0. The direction of each
# entry is from the catalogue's regime table: continuation in trends, fades in ranges,
# expansion out of compression.
REGIME_MULTIPLIERS: dict[str, dict[str, float]] = {
    "trend": {"trend": 1.5, "momentum": 1.3, "reversion": 0.3, "breakout": 1.0},
    "range": {"trend": 0.5, "momentum": 0.6, "reversion": 1.5, "breakout": 0.6},
    "squeeze": {"trend": 0.8, "momentum": 1.0, "reversion": 0.6, "breakout": 1.6},
    "neutral": {},
}


class ScorecardError(ValueError):
    """Raised for an unusable configuration or input."""


# -- inputs -----------------------------------------------------------------------------------


@dataclass
class Bars:
    """One contiguous run of bars. Callers split gapped data into several of these."""

    ts: np.ndarray
    open: np.ndarray
    high: np.ndarray
    low: np.ndarray
    close: np.ndarray
    volume: np.ndarray

    def __post_init__(self) -> None:
        arrays = [np.asarray(getattr(self, k), dtype="float64") for k in
                  ("ts", "open", "high", "low", "close", "volume")]
        n = arrays[0].size
        if any(a.ndim != 1 or a.size != n for a in arrays):
            raise ScorecardError("bar arrays must be one-dimensional and equal length")
        if n and not all(np.all(np.isfinite(a)) for a in arrays):
            raise ScorecardError("bar arrays contain non-finite values")
        self.ts, self.open, self.high, self.low, self.close, self.volume = arrays
        if n > 1 and np.any(np.diff(self.ts) <= 0):
            raise ScorecardError("timestamps must be strictly ascending")

    def __len__(self) -> int:
        return int(self.close.size)

    @classmethod
    def from_mapping(cls, arrays: Mapping[str, Any]) -> "Bars":
        """Accept the engine's `frame_to_arrays` keys (`ts`) or a CSV's (`timestamp`)."""
        ts = arrays["ts"] if "ts" in arrays else arrays["timestamp"]
        return cls(ts, arrays["open"], arrays["high"], arrays["low"], arrays["close"],
                   arrays["volume"])

    def slice(self, end: int) -> "Bars":
        """Bars [0, end) -- the prefix used by the look-ahead tests."""
        return Bars(self.ts[:end], self.open[:end], self.high[:end], self.low[:end],
                    self.close[:end], self.volume[:end])


def contiguous_segments(ts: np.ndarray, step: int = BAR_SECONDS) -> list[tuple[int, int]]:
    """[start, end) index ranges with no missing bar inside.

    The engine refuses gapped bars (`validate_bar_arrays`) and so do these indicators: a
    20-bar mean across a hole is not a 100-minute mean. Splitting restarts every indicator
    at a gap instead of inventing the missing OHLC.
    """
    ts = np.asarray(ts, dtype="int64")
    if ts.size == 0:
        return []
    cuts = np.where(np.diff(ts) != step)[0]
    starts = np.concatenate(([0], cuts + 1))
    ends = np.concatenate((cuts + 1, [ts.size]))
    return [(int(a), int(b)) for a, b in zip(starts, ends, strict=True)]


# -- causal series helpers ----------------------------------------------------------------------
# Each takes full arrays and returns the series whose value at t uses only inputs <= t.


def _s(x: np.ndarray) -> pd.Series:
    return pd.Series(np.asarray(x, dtype="float64"))


def ema(x: np.ndarray, span: int) -> np.ndarray:
    return _s(x).ewm(span=span, adjust=False, min_periods=span).mean().to_numpy()


def sma(x: np.ndarray, window: int) -> np.ndarray:
    return _s(x).rolling(window, min_periods=window).mean().to_numpy()


def rstd(x: np.ndarray, window: int) -> np.ndarray:
    return _s(x).rolling(window, min_periods=window).std(ddof=0).to_numpy()


def wilder(x: np.ndarray, period: int) -> np.ndarray:
    return _s(x).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().to_numpy()


def true_range(b: Bars) -> np.ndarray:
    prev = np.concatenate(([np.nan], b.close[:-1]))
    tr = np.maximum.reduce([b.high - b.low, np.abs(b.high - prev), np.abs(b.low - prev)])
    tr[0] = b.high[0] - b.low[0]
    return tr


def atr(b: Bars, period: int) -> np.ndarray:
    return wilder(true_range(b), period)


def log_returns(close: np.ndarray) -> np.ndarray:
    out = np.full(close.size, np.nan)
    out[1:] = np.diff(np.log(close))
    return out


def rsi_series(close: np.ndarray, period: int) -> np.ndarray:
    d = np.diff(close, prepend=np.nan)
    gain = wilder(np.where(d > 0, d, 0.0), period)
    loss = wilder(np.where(d < 0, -d, 0.0), period)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
        out = 100.0 - 100.0 / (1.0 + rs)
    out = np.where((loss == 0) & (gain > 0), 100.0, out)
    out = np.where((loss == 0) & (gain == 0), 50.0, out)
    out[: period] = np.nan
    return out


def dmi(b: Bars, period: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(+DI, -DI, ADX), Wilder smoothing."""
    up = np.diff(b.high, prepend=np.nan)
    down = -np.diff(b.low, prepend=np.nan)
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    plus_dm[0] = minus_dm[0] = 0.0
    tr_s = wilder(true_range(b), period)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi = 100.0 * wilder(plus_dm, period) / tr_s
        mdi = 100.0 * wilder(minus_dm, period) / tr_s
        dx = 100.0 * np.abs(pdi - mdi) / (pdi + mdi)
    dx = np.where(np.isfinite(dx), dx, 0.0)
    dx[: period] = np.nan
    adx = _s(dx).ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean().to_numpy()
    return pdi, mdi, adx


def vwap(b: Bars, mode: int, window: int) -> np.ndarray:
    """mode 0: UTC-session VWAP (resets at 00:00 UTC); mode 1: rolling `window`-bar VWAP."""
    tp = (b.high + b.low + b.close) / 3.0
    pv = tp * b.volume
    if mode == 1:
        num = _s(pv).rolling(window, min_periods=window).sum().to_numpy()
        den = _s(b.volume).rolling(window, min_periods=window).sum().to_numpy()
    else:
        day = (b.ts // 86400).astype("int64")
        num = pd.Series(pv).groupby(day).cumsum().to_numpy()
        den = pd.Series(b.volume).groupby(day).cumsum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    return np.where(den > 0, out, tp)


def rolling_max(x: np.ndarray, window: int) -> np.ndarray:
    return _s(x).rolling(window, min_periods=window).max().to_numpy()


def rolling_min(x: np.ndarray, window: int) -> np.ndarray:
    return _s(x).rolling(window, min_periods=window).min().to_numpy()


def prior(x: np.ndarray, k: int = 1) -> np.ndarray:
    """x shifted forward by k: value at t is x[t-k]. Never a negative shift."""
    out = np.full(x.size, np.nan)
    if k < x.size:
        out[k:] = x[: x.size - k]
    return out


def pct_rank(x: np.ndarray, window: int) -> np.ndarray:
    """Percentile (0-100) of x[t] within its trailing window, inclusive of t."""
    s = _s(x)
    return (s.rolling(window, min_periods=window).rank(pct=True) * 100.0).to_numpy()


def bars_since_change(sign: np.ndarray) -> np.ndarray:
    """Bars since `sign` last changed (0 on the bar it changes). Causal by construction."""
    out = np.zeros(sign.size)
    count = 0.0
    for i in range(sign.size):
        if i == 0 or sign[i] != sign[i - 1]:
            count = 0.0
        else:
            count += 1.0
        out[i] = count
    return out


def held(signal: np.ndarray, bars: int) -> np.ndarray:
    """Hold each non-zero signal for `bars` bars after it fires (latest signal wins)."""
    if bars <= 1:
        return signal
    out = np.zeros(signal.size)
    last, age = 0.0, bars
    for i in range(signal.size):
        if signal[i] != 0 and np.isfinite(signal[i]):
            last, age = float(signal[i]), 0
        out[i] = last if age < bars else 0.0
        age += 1
    out[np.isnan(signal)] = np.nan
    return out


def _clip(x: np.ndarray) -> np.ndarray:
    return np.clip(x, -1.0, 1.0)


def _safe_div(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        out = a / b
    return np.where(np.isfinite(out), out, np.nan)


def _undefined_until(x: np.ndarray, n: int) -> np.ndarray:
    x = np.array(x, dtype="float64")
    x[: min(n, x.size)] = np.nan
    return x


# -- component catalogue -----------------------------------------------------------------------


@dataclass(frozen=True)
class ParamSpec:
    """One adjustable number. `kind` is int or float; bounds are inclusive."""

    name: str
    default: float
    lo: float
    hi: float
    kind: str = "int"
    describe: str = ""

    def coerce(self, value: Any) -> float | int:
        try:
            v = float(value)
        except (TypeError, ValueError) as exc:
            raise ScorecardError(f"{self.name} must be a number, got {value!r}") from exc
        if not math.isfinite(v):
            raise ScorecardError(f"{self.name} must be finite")
        if v < self.lo or v > self.hi:
            raise ScorecardError(f"{self.name}={v:g} is outside [{self.lo:g}, {self.hi:g}]")
        if self.kind == "int":
            if v != int(v):
                raise ScorecardError(f"{self.name} must be a whole number, got {value!r}")
            return int(v)
        return v

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "default": self.default, "min": self.lo, "max": self.hi,
                "kind": self.kind, "describe": self.describe}


@dataclass(frozen=True)
class Component:
    """One scored metric or gate."""

    id: str
    name: str
    family: str
    style: str
    kind: str  # "score" or "gate"
    params: tuple[ParamSpec, ...]
    fn: Callable[[Bars, dict[str, Any], dict[str, Any]], np.ndarray]
    formula: str
    useful_when: str
    not_useful_when: str
    source: str = "added"
    needs: tuple[str, ...] = ()
    forward_only: bool = False
    default_enabled: bool = True
    default_weight: float = 1.0

    def defaults(self) -> dict[str, Any]:
        return {p.name: (int(p.default) if p.kind == "int" else float(p.default)) for p in self.params}

    def warmup(self, params: Mapping[str, Any]) -> int:
        """Largest lookback-like parameter; a display hint, not a guarantee."""
        ints = [int(v) for k, v in params.items()
                if isinstance(v, int) and k not in ("mode", "hold", "weekend", "cooldown")]
        return max(ints, default=1)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "family": self.family, "style": self.style,
            "kind": self.kind, "params": [p.to_dict() for p in self.params],
            "formula": self.formula, "useful_when": self.useful_when,
            "not_useful_when": self.not_useful_when, "source": self.source,
            "needs": list(self.needs), "forward_only": self.forward_only,
            "default_enabled": self.default_enabled, "default_weight": self.default_weight,
        }


P = ParamSpec

# Shared parameter shapes.
_ATR = P("atr", 14, 2, 200, "int", "ATR period used to normalise distances")


def _c_ema_cross(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if p["fast"] >= p["slow"]:
        raise ScorecardError("ema_cross: fast must be below slow")
    diff = ema(b.close, p["fast"]) - ema(b.close, p["slow"])
    return np.tanh(_safe_div(diff, p["scale"] * atr(b, p["atr"])))


def _c_macd(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if p["fast"] >= p["slow"]:
        raise ScorecardError("macd: fast must be below slow")
    line = ema(b.close, p["fast"]) - ema(b.close, p["slow"])
    signal = _s(line).ewm(span=p["signal"], adjust=False, min_periods=p["signal"]).mean().to_numpy()
    return np.tanh(_safe_div(line - signal, p["scale"] * atr(b, p["atr"])))


def _c_adx(b: Bars, p: Params, aux: Params) -> np.ndarray:
    pdi, mdi, adx = dmi(b, p["period"])
    strength = np.clip((adx - p["threshold"]) / p["threshold"], 0.0, 1.0)
    direction = np.tanh(2.0 * _safe_div(pdi - mdi, pdi + mdi) * 2.0)
    out = direction * strength
    return np.where(np.isnan(adx), np.nan, out)


def _c_vwap_side(b: Bars, p: Params, aux: Params) -> np.ndarray:
    v = vwap(b, p["mode"], p["window"])
    out = np.tanh(_safe_div(b.close - v, p["scale"] * atr(b, p["atr"])))
    return _undefined_until(out, p["window"] if p["mode"] == 1 else p["atr"])


def _htf_close(b: Bars, minutes: int) -> np.ndarray:
    """Close of the most recent COMPLETED higher-timeframe bar, forward-filled.

    A 5m bar stamped t covers [t, t+300). The HTF bar ending at boundary B is complete once
    the 5m bar with t + 300 == B has closed, so its close is that bar's close. Bars before
    the first completed boundary are NaN.
    """
    step = minutes * 60
    end = b.ts + BAR_SECONDS
    at_boundary = (end % step) == 0
    out = np.where(at_boundary, b.close, np.nan)
    return pd.Series(out).ffill().to_numpy()


def _c_htf_trend(b: Bars, p: Params, aux: Params) -> np.ndarray:
    minutes = p["tf_minutes"]
    if minutes % 5 or minutes <= 5:
        raise ScorecardError("htf_trend: tf_minutes must be a multiple of 5 above 5")
    step = minutes * 60
    end = b.ts + BAR_SECONDS
    at_boundary = (end % step) == 0
    closes = b.close[at_boundary]
    htf_ema = ema(closes, p["span"]) if closes.size else closes
    series = np.full(b.close.size, np.nan)
    series[at_boundary] = htf_ema
    htf_ema_now = pd.Series(series).ffill().to_numpy()
    htf_close = _htf_close(b, minutes)
    scale = p["scale"] * atr(b, p["atr"]) * math.sqrt(minutes / 5.0)
    return np.tanh(_safe_div(htf_close - htf_ema_now, scale))


def _c_ichimoku(b: Bars, p: Params, aux: Params) -> np.ndarray:
    t, k, s = p["tenkan"], p["kijun"], p["senkou"]
    tenkan = (rolling_max(b.high, t) + rolling_min(b.low, t)) / 2.0
    kijun = (rolling_max(b.high, k) + rolling_min(b.low, k)) / 2.0
    # The cloud plotted at t was computed `kijun` bars ago: shift forward, never back.
    span_a = prior((tenkan + kijun) / 2.0, k)
    span_b = prior((rolling_max(b.high, s) + rolling_min(b.low, s)) / 2.0, k)
    top, bottom = np.fmax(span_a, span_b), np.fmin(span_a, span_b)
    tk = np.sign(tenkan - kijun)
    out = np.where(b.close > top, 0.5 + 0.5 * (tk > 0), np.where(b.close < bottom, -0.5 - 0.5 * (tk < 0), 0.0))
    return np.where(np.isnan(top) | np.isnan(tk), np.nan, out)


def _c_roc(b: Bars, p: Params, aux: Params) -> np.ndarray:
    lr = log_returns(b.close)
    sigma = rstd(lr, p["vol_window"])
    roc = np.log(b.close) - np.log(prior(b.close, p["window"]))
    return np.tanh(_safe_div(roc, p["scale"] * sigma * math.sqrt(p["window"])))


def _c_persistence(b: Bars, p: Params, aux: Params) -> np.ndarray:
    lr = log_returns(b.close)
    rho = _s(lr).rolling(p["window"], min_periods=p["window"]).corr(_s(prior(lr, 1))).to_numpy()
    last = np.sign(lr)
    return _clip(p["gain"] * rho * last)


def _c_rsi(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if not p["oversold"] < 50 < p["overbought"]:
        raise ScorecardError("rsi: need oversold < 50 < overbought")
    r = rsi_series(b.close, p["period"])
    below = _clip((50.0 - r) / (50.0 - p["oversold"]))
    above = _clip((50.0 - r) / (p["overbought"] - 50.0))
    out = np.where(r < 50.0, below, above)
    return -out if p["mode"] == 1 else out


def _c_stochastic(b: Bars, p: Params, aux: Params) -> np.ndarray:
    hi, lo = rolling_max(b.high, p["k"]), rolling_min(b.low, p["k"])
    k = 100.0 * _safe_div(b.close - lo, hi - lo)
    k = np.where(hi == lo, 50.0, k)
    d = sma(k, p["d"])
    base = _clip((50.0 - k) / (50.0 - p["oversold"]))
    turning = np.where(base > 0, k > d, k < d)
    out = np.where(turning, base, 0.5 * base)
    return np.where(np.isnan(d), np.nan, out)


def _c_cci(b: Bars, p: Params, aux: Params) -> np.ndarray:
    tp = (b.high + b.low + b.close) / 3.0
    mean = sma(tp, p["period"])
    mad = _s(tp).rolling(p["period"], min_periods=p["period"]).apply(
        lambda w: np.mean(np.abs(w - w.mean())), raw=True).to_numpy()
    cci = _safe_div(tp - mean, 0.015 * mad)
    return _clip(-cci / p["extreme"])


def _c_bollinger(b: Bars, p: Params, aux: Params) -> np.ndarray:
    mid, sd = sma(b.close, p["window"]), rstd(b.close, p["window"])
    pb = _safe_div(b.close - (mid - p["k"] * sd), 2.0 * p["k"] * sd)
    return _clip(1.0 - 2.0 * pb)


def _c_zscore(b: Bars, p: Params, aux: Params) -> np.ndarray:
    z = _safe_div(b.close - sma(b.close, p["window"]), rstd(b.close, p["window"]))
    return _clip(-z / p["entry"])


def _c_vwap_reversion(b: Bars, p: Params, aux: Params) -> np.ndarray:
    v = vwap(b, p["mode"], p["window"])
    out = _clip(-_safe_div(b.close - v, p["stretch"] * atr(b, p["atr"])))
    return _undefined_until(out, p["window"] if p["mode"] == 1 else p["atr"])


def _c_donchian(b: Bars, p: Params, aux: Params) -> np.ndarray:
    upper = prior(rolling_max(b.high, p["window"]), 1)
    lower = prior(rolling_min(b.low, p["window"]), 1)
    raw = np.where(b.close > upper, 1.0, np.where(b.close < lower, -1.0, 0.0))
    raw = np.where(np.isnan(upper), np.nan, raw)
    return held(raw, p["hold"])


def _c_squeeze(b: Bars, p: Params, aux: Params) -> np.ndarray:
    mid, sd = sma(b.close, p["window"]), rstd(b.close, p["window"])
    upper, lower = mid + p["k"] * sd, mid - p["k"] * sd
    width = _safe_div(upper - lower, mid)
    rank = pct_rank(width, p["lookback"])
    squeezed = _s((rank <= p["squeeze_pct"]).astype(float)).rolling(
        p["recent"], min_periods=1).max().to_numpy() > 0
    vol_ok = b.volume > p["vol_mult"] * sma(b.volume, p["window"])
    raw = np.where(squeezed & vol_ok & (b.close > upper), 1.0,
                   np.where(squeezed & vol_ok & (b.close < lower), -1.0, 0.0))
    raw = np.where(np.isnan(rank), np.nan, raw)
    return held(raw, p["hold"])


def _c_continuation(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if p["fast"] >= p["slow"]:
        raise ScorecardError("trend_continuation: fast must be below slow")
    v = vwap(b, 0, 1)
    ef, es = ema(b.close, p["fast"]), ema(b.close, p["slow"])
    vol_ok = b.volume > p["vol_mult"] * sma(b.volume, p["vol_window"])
    up = (b.close > v) & (ef > es) & vol_ok
    down = (b.close < v) & (ef < es) & vol_ok
    raw = np.where(up, 1.0, np.where(down, -1.0, 0.0))
    raw = np.where(np.isnan(es) | np.isnan(sma(b.volume, p["vol_window"])), np.nan, raw)
    return held(raw, p["hold"])


def _c_sweep(b: Bars, p: Params, aux: Params) -> np.ndarray:
    lo = prior(rolling_min(b.low, p["lookback"]), 1)
    hi = prior(rolling_max(b.high, p["lookback"]), 1)
    long_ = (b.low < lo) & (b.close > lo)
    short = (b.high > hi) & (b.close < hi)
    raw = np.where(long_ & ~short, 1.0, np.where(short & ~long_, -1.0, 0.0))
    raw = np.where(np.isnan(lo), np.nan, raw)
    return held(raw, p["hold"])


def _c_fib(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if not 0 < p["zone_lo"] < p["zone_hi"] < 1:
        raise ScorecardError("fib_pullback: need 0 < zone_lo < zone_hi < 1")
    hi, lo = rolling_max(b.high, p["swing"]), rolling_min(b.low, p["swing"])
    rng = hi - lo
    trend = np.sign(b.close - ema(b.close, p["trend"]))
    up_zone = (b.close <= hi - p["zone_lo"] * rng) & (b.close >= hi - p["zone_hi"] * rng)
    dn_zone = (b.close >= lo + p["zone_lo"] * rng) & (b.close <= lo + p["zone_hi"] * rng)
    out = np.where((trend > 0) & up_zone, 0.7, np.where((trend < 0) & dn_zone, -0.7, 0.0))
    return np.where(np.isnan(rng) | np.isnan(trend), np.nan, out)


def _c_obv(b: Bars, p: Params, aux: Params) -> np.ndarray:
    step = np.sign(np.diff(b.close, prepend=b.close[0])) * b.volume
    obv = np.cumsum(step)
    gap = obv - sma(obv, p["window"])
    return np.tanh(_safe_div(gap, sma(b.volume, p["window"]) * math.sqrt(p["window"]) * p["scale"]))


def _c_cmf(b: Bars, p: Params, aux: Params) -> np.ndarray:
    rng = b.high - b.low
    clv = np.where(rng > 0, _safe_div((b.close - b.low) - (b.high - b.close), rng), 0.0)
    num = _s(clv * b.volume).rolling(p["window"], min_periods=p["window"]).sum().to_numpy()
    den = _s(b.volume).rolling(p["window"], min_periods=p["window"]).sum().to_numpy()
    return _clip(_safe_div(num, den) / p["scale"])


def _c_volume(b: Bars, p: Params, aux: Params) -> np.ndarray:
    """An unusually heavy bar, signed by which way it closed. Average volume scores 0."""
    rel = _safe_div(b.volume, prior(sma(b.volume, p["window"]), 1))
    direction = np.sign(b.close - b.open)
    return direction * np.clip((rel - 1.0) / p["scale"], 0.0, 1.0)


def _c_bop(b: Bars, p: Params, aux: Params) -> np.ndarray:
    """Balance of power: (close - open) / (high - low), averaged; who won each bar."""
    rng = b.high - b.low
    bop = np.where(rng > 0, _safe_div(b.close - b.open, rng), 0.0)
    return _clip(sma(bop, p["window"]) / p["scale"])


def zigzag_state(close: np.ndarray, pct: float) -> tuple[np.ndarray, np.ndarray]:
    """(leg direction, last confirmed pivot) per bar, WITHOUT repainting.

    A charting ZigZag redraws: it moves the last pivot to a new extreme after the fact, so its
    past legs use future prices. Here a pivot is confirmed only once price has reversed by `pct`
    from the running extreme, on the bar that completes that reversal, and is never moved again.
    """
    n = close.size
    leg = np.zeros(n)
    pivot = np.full(n, np.nan)
    trend, ext, piv = 0, close[0] if n else 0.0, np.nan
    hi = lo = close[0] if n else 0.0
    for i in range(n):
        c = close[i]
        if trend == 0:
            hi, lo = max(hi, c), min(lo, c)
            if c >= lo * (1 + pct):
                trend, piv, ext = 1, lo, c
            elif c <= hi * (1 - pct):
                trend, piv, ext = -1, hi, c
        elif trend == 1:
            if c > ext:
                ext = c
            elif c <= ext * (1 - pct):
                trend, piv, ext = -1, ext, c
        else:
            if c < ext:
                ext = c
            elif c >= ext * (1 + pct):
                trend, piv, ext = 1, ext, c
        leg[i] = trend
        pivot[i] = piv
    return leg, pivot


def _c_zigzag(b: Bars, p: Params, aux: Params) -> np.ndarray:
    pct = p["pct"] / 100.0
    leg, pivot = zigzag_state(b.close, pct)
    progress = np.clip(np.abs(b.close - pivot) / pivot / (2.0 * pct), 0.0, 1.0)
    return np.where(leg == 0, np.nan, leg * progress)


def _c_ema(b: Bars, p: Params, aux: Params) -> np.ndarray:
    return np.tanh(_safe_div(b.close - ema(b.close, p["span"]), p["scale"] * atr(b, p["atr"])))


def _aligned_last(series_ts: np.ndarray, values: np.ndarray, bar_ts: np.ndarray,
                  max_age: float = 2 * 3600) -> np.ndarray:
    """Most recent value whose timestamp is <= the bar's CLOSE time (bar_ts + 300).

    A value older than `max_age` seconds is NaN, not carried forward: a funding cache that
    stopped in August must not keep scoring November bars with August's rate.
    """
    if series_ts.size == 0:
        return np.full(bar_ts.size, np.nan)
    order = np.argsort(series_ts)
    st, sv = np.asarray(series_ts)[order], np.asarray(values, dtype="float64")[order]
    close = bar_ts + BAR_SECONDS
    idx = np.searchsorted(st, close, side="right") - 1
    safe = np.clip(idx, 0, None)
    fresh = (idx >= 0) & (close - st[safe] <= max_age)
    return np.where(fresh, sv[safe], np.nan)


def _c_funding(b: Bars, p: Params, aux: Params) -> np.ndarray:
    funding = aux.get("funding")
    if not funding:
        return np.full(len(b), np.nan)
    rate = _aligned_last(np.asarray(funding["ts"]), np.asarray(funding["rate"]), b.ts)
    # Hyperliquid's hourly rate has a structural floor (~0.125 bps/h); only the excess over it
    # is crowding.
    return -np.tanh((rate - p["baseline_bps"] * 1e-4) / (p["scale_bps"] * 1e-4))


def _live_only(b: Bars, value: float | None) -> np.ndarray:
    out = np.full(len(b), np.nan)
    if value is not None and math.isfinite(value) and len(b):
        out[-1] = value
    return out


def _c_premium(b: Bars, p: Params, aux: Params) -> np.ndarray:
    live = aux.get("live") or {}
    prem = live.get("premium")
    if prem is None:
        return _live_only(b, None)
    return _live_only(b, -math.tanh(float(prem) / (p["scale_bps"] * 1e-4)))


def _c_oi(b: Bars, p: Params, aux: Params) -> np.ndarray:
    live = aux.get("live") or {}
    hist = live.get("oi_history") or []  # [(ts, oi), ...] oldest first, from the forward ledger
    if len(hist) < 2 or len(b) < 2:
        return _live_only(b, None)
    now_ts, now_oi = hist[-1]
    base = [h for h in hist if h[0] <= now_ts - p["minutes"] * 60]
    if not base or base[-1][1] <= 0:
        return _live_only(b, None)
    d_oi = (now_oi - base[-1][1]) / base[-1][1]
    k = max(1, min(len(b) - 1, p["minutes"] // 5))
    d_px = math.copysign(1.0, b.close[-1] - b.close[-1 - k]) if b.close[-1] != b.close[-1 - k] else 0.0
    mag = math.tanh(abs(d_oi) / (p["scale_pct"] / 100.0))
    score = d_px * mag if d_oi > 0 else -0.3 * d_px * mag
    return _live_only(b, score)


def _c_book(b: Bars, p: Params, aux: Params) -> np.ndarray:
    live = aux.get("live") or {}
    imb = live.get("book_imbalance")
    if imb is None:
        return _live_only(b, None)
    return _live_only(b, max(-1.0, min(1.0, float(imb) / p["scale"])))


def _c_btc_lead(b: Bars, p: Params, aux: Params) -> np.ndarray:
    ref = aux.get("btc_close")
    if ref is None:
        return np.full(len(b), np.nan)
    ref = np.asarray(ref, dtype="float64")
    if ref.size != len(b):
        raise ScorecardError("btc_close must be aligned bar-for-bar with the asset")
    lr = log_returns(ref)
    sigma = rstd(lr, p["vol_window"])
    return np.tanh(_safe_div(lr, p["scale"] * sigma))


def trend_stage(b: Bars, p: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(direction, age_bars, extension_atr) of the fast/slow EMA trend."""
    ef, es = ema(b.close, p["fast"]), ema(b.close, p["slow"])
    direction = np.sign(ef - es)
    age = bars_since_change(np.nan_to_num(direction))
    ext = _safe_div(b.close - es, atr(b, p["atr"])) * direction
    return direction, age, ext


def _c_lifecycle(b: Bars, p: Params, aux: Params) -> np.ndarray:
    if p["fast"] >= p["slow"]:
        raise ScorecardError("trend_lifecycle: fast must be below slow")
    d, age, ext = trend_stage(b, p)
    exhausted = ext > p["exhausted_atr"]
    early = age <= p["early_bars"]
    mature = d * 0.5 * np.clip(1.0 - ext / p["exhausted_atr"], 0.0, 1.0)
    out = np.where(exhausted, -0.5 * d, np.where(early, d, mature))
    return np.where(np.isnan(ext), np.nan, out)


LIFECYCLE_LABELS = ("early", "mature", "exhausted", "none")


def lifecycle_labels(b: Bars, p: Mapping[str, Any]) -> np.ndarray:
    d, age, ext = trend_stage(b, p)
    lab = np.where(ext > p["exhausted_atr"], "exhausted", np.where(age <= p["early_bars"], "early", "mature"))
    return np.where(np.isnan(ext) | (d == 0), "none", lab)


def cycle_phase(b: Bars, p: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """(phase label, score) for a Wyckoff-style read of the last `window` bars.

    markup: long mean rising and price in the upper half; markdown: the mirror.
    accumulation: flat mean, price in the lower third; distribution: flat mean, upper third.
    """
    w = p["window"]
    hi, lo = rolling_max(b.high, w), rolling_min(b.low, w)
    pos = _safe_div(b.close - lo, hi - lo)
    mean = sma(b.close, w)
    slope_pct = 100.0 * _safe_div(mean - prior(mean, p["slope_bars"]), prior(mean, p["slope_bars"]))
    flat = np.abs(slope_pct) <= p["flat_pct"]
    labels = np.where(~flat & (slope_pct > 0) & (pos > 0.5), "markup",
                      np.where(~flat & (slope_pct < 0) & (pos < 0.5), "markdown",
                               np.where(flat & (pos < 0.35), "accumulation",
                                        np.where(flat & (pos > 0.65), "distribution", "transition"))))
    score = np.select([labels == "markup", labels == "markdown", labels == "accumulation",
                       labels == "distribution"], [0.6, -0.6, 0.3, -0.3], 0.0)
    undefined = np.isnan(slope_pct) | np.isnan(pos)
    labels = np.where(undefined, "none", labels)
    return labels, np.where(undefined, np.nan, score)


def _c_cycle(b: Bars, p: Params, aux: Params) -> np.ndarray:
    return cycle_phase(b, p)[1]


# -- gates: True means "no trade on this bar" ---------------------------------------------------


def round_trip_bps(fee_bps: float, slippage_bps: float) -> float:
    """Open and close each pay the fee and the slippage."""
    return 2.0 * (float(fee_bps) + float(slippage_bps))


def _g_cost(b: Bars, p: Params, aux: Params) -> np.ndarray:
    rt = aux.get("round_trip_bps", 16.0)
    move = _s(np.abs(log_returns(b.close)) * 1e4).rolling(p["window"], min_periods=p["window"]).mean().to_numpy()
    expected = move * math.sqrt(p["hold_bars"])
    blocked = expected < p["multiple"] * rt
    return np.where(np.isnan(move), True, blocked)


def _g_liquidation(b: Bars, p: Params, aux: Params) -> np.ndarray:
    lev = aux.get("leverage", 5.0)
    stop_pct = p["stop_atr"] * atr(b, p["atr"]) / b.close
    liq_pct = 1.0 / max(lev, 1e-9)
    blocked = stop_pct > p["max_fraction"] * liq_pct
    return np.where(np.isnan(stop_pct), True, blocked)


def _g_shock(b: Bars, p: Params, aux: Params) -> np.ndarray:
    prev_atr = prior(atr(b, p["atr"]), 1)
    rng = b.high - b.low
    vol_mean, vol_sd = prior(sma(b.volume, p["vol_window"]), 1), prior(rstd(b.volume, p["vol_window"]), 1)
    z = _safe_div(b.volume - vol_mean, vol_sd)
    shock = (rng > p["range_mult"] * prev_atr) | (z > p["vol_z"])
    shock = np.nan_to_num(shock.astype(float))
    cooled = _s(shock).rolling(p["cooldown"] + 1, min_periods=1).max().to_numpy() > 0
    return cooled


def _g_session(b: Bars, p: Params, aux: Params) -> np.ndarray:
    hours = aux.get("blocked_hours") or ()
    end = b.ts + BAR_SECONDS  # the call is made at the bar's close
    hour = ((end // 3600) % 24).astype(int)
    blocked = np.isin(hour, list(hours))
    if p["weekend"]:
        weekday = ((end // 86400) + 3) % 7  # 1970-01-01 was a Thursday; Monday == 0
        blocked |= weekday >= 5
    return blocked


def _g_events(b: Bars, p: Params, aux: Params) -> np.ndarray:
    events = aux.get("events") or []
    end = b.ts + BAR_SECONDS
    blocked = np.zeros(len(b), dtype=bool)
    for ev in events:
        at = float(ev["ts"])
        blocked |= (end >= at - p["before_min"] * 60) & (end <= at + p["after_min"] * 60)
    return blocked


def _g_volume(b: Bars, p: Params, aux: Params) -> np.ndarray:
    short = sma(b.volume, p["short"])
    long_ = sma(b.volume, p["long"])
    blocked = short < p["min_ratio"] * long_
    return np.where(np.isnan(long_), True, blocked)


def _g_news(b: Bars, p: Params, aux: Params) -> np.ndarray:
    live = aux.get("live") or {}
    out = np.zeros(len(b), dtype=bool)
    if "news_error" in live:
        out[-1:] = True  # fail closed: an enabled news gate that could not look blocks the call
        return out
    hits = live.get("news_hits")
    if hits:
        out[-1:] = True
    return out


COMPONENTS: tuple[Component, ...] = (
    # trend / direction
    Component("ema_cross", "EMA crossover", "ma-trend", "trend", "score",
              (P("fast", 9, 2, 200), P("slow", 21, 3, 400), P("scale", 0.5, 0.05, 10, "float",
               "ATRs of EMA gap that saturate the score"), _ATR), _c_ema_cross,
              "tanh((EMA_fast - EMA_slow) / (scale * ATR))",
              "Sustained trends; confirms direction.", "Chop; lag makes late entries and whipsaws.",
              "Trend following / moving-average crossover"),
    Component("ema_trend", "Price vs EMA", "ma-trend", "trend", "score",
              (P("span", 50, 2, 1000), P("scale", 1.0, 0.05, 10, "float", "ATRs from the EMA for a full score"),
               _ATR), _c_ema,
              "tanh((close - EMA_span) / (scale * ATR))",
              "Trending tape where price holds one side of its average.", "Chop around the average.",
              "added (user request: exponential moving average)"),
    Component("macd", "MACD histogram", "momentum", "momentum", "score",
              (P("fast", 12, 2, 200), P("slow", 26, 3, 400), P("signal", 9, 2, 100),
               P("scale", 0.25, 0.01, 10, "float", "ATRs of histogram that saturate"), _ATR), _c_macd,
              "tanh((MACD - signal) / (scale * ATR)); MACD = EMA_fast - EMA_slow",
              "Trend confirmation, momentum shifts.", "Flat noisy markets; repeated crossovers whipsaw.",
              "MACD"),
    Component("adx_dmi", "ADX / DMI direction", "directional", "trend", "score",
              (P("period", 14, 2, 100), P("threshold", 20, 5, 60, "float", "ADX below this scores 0")),
              _c_adx, "sign(+DI - -DI) * clip((ADX - threshold)/threshold, 0, 1)",
              "Selecting trend vs range; filtering weak breakouts.",
              "Abrupt regime changes before smoothing catches up.", "Average Directional Index (ADX)"),
    Component("vwap_side", "Price vs VWAP", "vwap", "trend", "score",
              (P("mode", 0, 0, 1, "int", "0 = UTC-session VWAP, 1 = rolling"), P("window", 48, 5, 2000,
               "int", "bars, rolling mode only"), P("scale", 1.0, 0.05, 10, "float"), _ATR), _c_vwap_side,
              "tanh((close - VWAP) / (scale * ATR))",
              "Intraday trend context when other evidence agrees.", "Thin markets; incompatible sessions.",
              "VWAP"),
    Component("htf_trend", "Higher-timeframe trend", "higher-timeframe", "context", "score",
              (P("tf_minutes", 60, 10, 1440, "int", "multiple of 5"), P("span", 20, 2, 200),
               P("scale", 1.0, 0.05, 10, "float"), _ATR), _c_htf_trend,
              "tanh((HTF close - EMA(HTF closes)) / (scale * ATR * sqrt(tf/5))), completed HTF bars only",
              "Execution checklist step 3: a 15m/1h regime filter with a 5m trigger.",
              "Turning points, where the higher timeframe lags.", "added (execution_checklist step 3)"),
    Component("ichimoku", "Ichimoku cloud", "ma-trend", "trend", "score",
              (P("tenkan", 9, 2, 100), P("kijun", 26, 3, 200), P("senkou", 52, 4, 400)), _c_ichimoku,
              "+0.5 above the (displaced) cloud, +1 if also tenkan > kijun; mirrored below; 0 inside",
              "Multi-timeframe trend filter in orderly markets.", "Very short-term scalping; abrupt regime changes.",
              "Ichimoku Cloud", default_enabled=False),
    # momentum / adaptive
    Component("roc", "Rate of change (vol-scaled)", "momentum", "momentum", "score",
              (P("window", 12, 1, 500), P("vol_window", 96, 10, 2000), P("scale", 1.0, 0.05, 10, "float")),
              _c_roc, "tanh(log(C_t/C_{t-n}) / (scale * sigma_1bar * sqrt(n)))",
              "Persistent one-way moves.", "Mean-reverting tape; after exhaustion.", "Breakout / momentum"),
    Component("persistence", "Return persistence (lag-1 autocorrelation)", "autocorrelation", "adaptive",
              "score", (P("window", 96, 10, 2000), P("gain", 5.0, 0.5, 50, "float")), _c_persistence,
              "clip(gain * rho_1 * sign(r_t)); rho_1 = rolling lag-1 autocorrelation of 5m returns",
              "Tells continuation from reversal tape without choosing a regime by hand.",
              "Autocorrelation near zero (the usual case at 5m); then it scores near 0.", "added"),
    # oscillators (one family: they measure one thing)
    Component("rsi", "RSI", "stretch", "reversion", "score",
              (P("period", 14, 2, 200), P("oversold", 30, 1, 49, "float"), P("overbought", 70, 51, 99, "float"),
               P("mode", 0, 0, 1, "int", "0 = fade extremes, 1 = momentum (sign flipped)")), _c_rsi,
              "(50 - RSI) scaled to +-1 at the oversold/overbought levels",
              "Range trading, pullback timing.", "Strong trends: RSI stays overbought.",
              "Relative Strength Index (RSI)"),
    Component("stochastic", "Stochastic %K/%D", "stretch", "reversion", "score",
              (P("k", 14, 2, 200), P("d", 3, 1, 50), P("oversold", 20, 1, 49, "float")), _c_stochastic,
              "(50 - %K) scaled; full weight only while %K turns back through %D",
              "Pullback timing inside a trend.", "One-way trends: signals too early.", "Stochastic oscillator"),
    Component("cci", "Commodity Channel Index", "stretch", "reversion", "score",
              (P("period", 20, 2, 200), P("extreme", 150, 50, 400, "float")), _c_cci,
              "clip(-CCI / extreme)", "Range extremes.", "Trends.", "added (oscillator family)",
              default_enabled=False),
    # mean reversion
    Component("bollinger", "Bollinger %B fade", "stretch", "reversion", "score",
              (P("window", 20, 2, 500), P("k", 2.0, 0.5, 5, "float")), _c_bollinger,
              "clip(1 - 2 * %B): +1 at the lower band, -1 at the upper",
              "Mean reversion at extreme bands.", "A trend that walks the band.", "Bollinger Bands"),
    Component("zscore", "Z-score fade", "stretch", "reversion", "score",
              (P("window", 48, 5, 2000), P("entry", 2.0, 0.5, 5, "float")), _c_zscore,
              "clip(-z / entry), z = (P - MA_n) / SD_n", "Ranges with a stable mean.",
              "Strong trends; losses compound without a stop.", "Mean reversion"),
    Component("vwap_reversion", "VWAP stretch fade", "vwap", "reversion", "score",
              (P("mode", 0, 0, 1, "int", "0 = session, 1 = rolling"), P("window", 48, 5, 2000),
               P("stretch", 2.0, 0.2, 10, "float", "ATRs from VWAP for a full score"), _ATR), _c_vwap_reversion,
              "clip(-(close - VWAP) / (stretch * ATR))", "Flat VWAP ranges.", "Trend days.",
              "VWAP", default_enabled=False),
    # breakout / volatility / structure
    Component("donchian", "Donchian breakout", "breakout", "breakout", "score",
              (P("window", 20, 2, 500), P("hold", 3, 1, 50, "int", "bars a signal persists")), _c_donchian,
              "+1 when close > prior n-bar high, -1 below prior low; held for `hold` bars",
              "A range resolves with a decisive close.", "False breakouts that return inside.",
              "Breakout / momentum"),
    Component("squeeze", "Volatility-squeeze breakout", "volatility", "breakout", "score",
              (P("window", 20, 5, 500), P("k", 2.0, 0.5, 5, "float"), P("lookback", 288, 20, 5000),
               P("squeeze_pct", 20, 1, 50, "float", "bandwidth percentile that counts as compressed"),
               P("recent", 6, 1, 100, "int", "bars since the squeeze"), P("vol_mult", 1.5, 0.5, 10, "float"),
               P("hold", 3, 1, 50)), _c_squeeze,
              "after bandwidth <= squeeze_pct percentile, close outside a band on volume > vol_mult * avg",
              "Compression into a liquid range, then decisive expansion.",
              "Compression continues; breakout without participation.", "Volatility-squeeze breakout"),
    Component("trend_continuation", "5m trend continuation (VWAP + EMA + volume)", "composite-rule", "trend",
              "score", (P("fast", 9, 2, 200), P("slow", 21, 3, 400), P("vol_window", 20, 2, 500),
                        P("vol_mult", 1.2, 0.5, 10, "float"), P("hold", 2, 1, 50)), _c_continuation,
              "+1 when close > session VWAP and EMA_fast > EMA_slow and volume > vol_mult * avg; mirrored",
              "A directional liquid session already under way.", "Flat ranges, late extensions, thin liquidity.",
              "Five-minute trend continuation (VWAP + momentum + volume)"),
    Component("liquidity_sweep", "Liquidity sweep / failed breakout", "structure", "reversion", "score",
              (P("lookback", 24, 3, 500), P("hold", 2, 1, 50)), _c_sweep,
              "+1 when the low pierces the prior n-bar low and the close reclaims it; mirrored at highs",
              "Well-defined ranges with equal highs/lows.", "Genuine news or liquidation breakouts.",
              "Liquidity-sweep / failed-breakout reversal"),
    Component("zigzag", "ZigZag leg (non-repainting)", "swing", "trend", "score",
              (P("pct", 0.5, 0.05, 20, "float", "percent reversal that confirms a pivot"),), _c_zigzag,
              "+/-1 for the current confirmed up/down leg, scaled by progress from the pivot (full at 2 x pct); "
              "a pivot is confirmed only after the reversal, never moved later",
              "Swing direction once a reversal is confirmed.", "Confirmation lags by pct; chop flips it often.",
              "added (user request: zig zag)"),
    Component("fib_pullback", "Fibonacci pullback zone", "structure", "trend", "score",
              (P("swing", 48, 5, 2000), P("trend", 50, 5, 1000), P("zone_lo", 0.382, 0.1, 0.9, "float"),
               P("zone_hi", 0.618, 0.15, 0.95, "float")), _c_fib,
              "+0.7 in an uptrend when price sits in the [zone_lo, zone_hi] retracement of the swing; mirrored",
              "Pullbacks that respect a clear swing.", "Subjective anchors; news-driven tape.",
              "Fibonacci retracement", default_enabled=False),
    # volume / flow
    Component("obv", "On-balance volume trend", "volume-flow", "flow", "score",
              (P("window", 20, 2, 500), P("scale", 1.0, 0.05, 10, "float")), _c_obv,
              "tanh((OBV - SMA(OBV)) / (scale * SMA(volume) * sqrt(n)))",
              "Breakout confirmation, accumulation clues.", "Fragmented or anomalous volume.",
              "On-Balance Volume (OBV)"),
    Component("volume", "Volume (relative, signed by the bar)", "volume-flow", "flow", "score",
              (P("window", 48, 2, 2000, "int", "bars of average volume to compare against"),
               P("scale", 1.0, 0.1, 20, "float", "multiples of average volume above 1x for a full score")),
              _c_volume, "sign(close - open) * clip((volume / avg volume of prior bars - 1) / scale, 0, 1)",
              "Breakout and capitulation bars carry unusual volume.", "Volume alone has no direction; a "
              "heavy bar can be absorption.", "added (user request: volume)"),
    Component("bop", "Balance of power", "candle-pressure", "flow", "score",
              (P("window", 14, 1, 500), P("scale", 0.5, 0.05, 1, "float")), _c_bop,
              "clip(SMA((close - open) / (high - low)) / scale)",
              "Persistent one-sided bars.", "Doji-heavy chop; it is close to Chaikin money flow's CLV.",
              "added (user request: balance of power)"),
    Component("money_flow", "Chaikin money flow (order-flow proxy)", "volume-flow", "flow", "score",
              (P("window", 20, 2, 500), P("scale", 0.25, 0.02, 1, "float")), _c_cmf,
              "clip(CMF / scale); CMF = sum(CLV * V) / sum(V). A candle-derived proxy, NOT taker delta",
              "Persistent one-sided prints.", "Large isolated prints; it cannot see who crossed the spread.",
              "Order-flow imbalance / aggressive-volume delta"),
    # derivatives positioning
    Component("funding", "Funding rate (contrarian)", "positioning", "derivatives", "score",
              (P("scale_bps", 0.5, 0.05, 50, "float", "excess hourly funding (bps) that saturates"),
               P("baseline_bps", 0.125, -5, 5, "float", "structural hourly rate subtracted first")), _c_funding,
              "-tanh((funding_1h - baseline) / scale): longs paying above baseline is crowding, a mild down bias",
              "Crowded positioning before a flush.", "Funding can stay extreme for days.",
              "Funding-rate arbitrage / cash-and-carry", needs=("funding",), default_weight=0.5),
    Component("premium", "Perp premium vs oracle (contrarian)", "positioning", "derivatives", "score",
              (P("scale_bps", 5.0, 0.5, 100, "float"),), _c_premium,
              "-tanh(premium / scale), Hyperliquid mark vs oracle", "Stretched basis.",
              "Basis can trend; live only, cannot be backtested here.", "added (cross-venue observation)",
              needs=("live",), forward_only=True, default_weight=0.5),
    Component("oi_flow", "Open-interest change x price", "positioning", "derivatives", "score",
              (P("minutes", 15, 5, 240), P("scale_pct", 0.5, 0.05, 10, "float")), _c_oi,
              "rising OI confirms the price direction; falling OI (unwind) leans against it at 0.3x",
              "New positioning behind a move.", "Needs several forward ticks of OI history; live only.",
              "added (cross-venue observation)", needs=("live",), forward_only=True, default_weight=0.5),
    Component("book_imbalance", "Order-book imbalance", "orderflow", "flow", "score",
              (P("depth_bps", 10, 1, 200, "float", "book depth around mid counted"),
               P("scale", 0.5, 0.05, 1, "float")), _c_book,
              "(bid size - ask size) / (bid + ask) within depth_bps of mid, Hyperliquid L2",
              "A liquid book with persistent one-sided depth.", "Spoofing; a snapshot is not flow. Live only.",
              "Order-flow imbalance / aggressive-volume delta", needs=("live",), forward_only=True,
              default_weight=0.5),
    Component("btc_lead", "BTC lead (last bar)", "cross-asset", "cross-asset", "score",
              (P("vol_window", 96, 10, 2000), P("scale", 2.0, 0.1, 20, "float")), _c_btc_lead,
              "tanh(BTC 5m log return / (scale * sigma_BTC)), same closed bar",
              "Majors move together; BTC often prints first.", "Idiosyncratic SOL news.", "added",
              needs=("btc",), default_weight=0.5),
    # lifecycle
    Component("trend_lifecycle", "Trend lifecycle stage", "lifecycle", "lifecycle", "score",
              (P("fast", 9, 2, 200), P("slow", 21, 3, 400), P("early_bars", 12, 1, 500),
               P("exhausted_atr", 3.0, 0.5, 20, "float", "extension beyond slow EMA, in ATRs"), _ATR),
              _c_lifecycle,
              "early (age <= early_bars): +dir; mature: +0.5*dir fading with extension; exhausted: -0.5*dir",
              "Avoiding late-stage extensions the catalogue warns about.", "Trends that keep extending.",
              "added (lifecycle stage)"),
    Component("cycle_phase", "Market-cycle phase (Wyckoff-style)", "lifecycle-cycle", "lifecycle", "score",
              (P("window", 288, 24, 10000, "int", "bars; 288 = one day of 5m"), P("slope_bars", 48, 2, 2000),
               P("flat_pct", 0.5, 0.01, 10, "float", "|slope| below this % is a flat phase")), _c_cycle,
              "markup +0.6, markdown -0.6, accumulation +0.3, distribution -0.3, transition 0",
              "Context for which side to favour at 5m.", "Phase labels are descriptive, slow to turn.",
              "added (lifecycle stage)", default_weight=0.5),
    # gates
    Component("gate_cost", "Cost hurdle", "gate", "gate", "gate",
              (P("window", 48, 5, 2000), P("hold_bars", 3, 1, 100, "int", "bars a position is expected to last"),
               P("multiple", 1.0, 0.1, 10, "float", "required move as a multiple of round-trip cost")), _g_cost,
              "block when mean|r| * sqrt(hold_bars) < multiple * round-trip bps",
              "Execution checklist step 2: expected move must clear fees, impact and slippage.",
              "It blocks most 5m bars on SOL; that is the finding, not a bug.", "execution_checklist step 2"),
    Component("gate_liquidation", "Liquidation distance", "gate", "gate", "gate",
              (P("stop_atr", 1.5, 0.2, 20, "float"), P("max_fraction", 0.5, 0.05, 1, "float",
               "stop must sit inside this fraction of the distance to liquidation"), _ATR), _g_liquidation,
              "block when stop_atr * ATR / price > max_fraction / leverage",
              "Every leveraged trade.", "Gaps jump through stops before execution.",
              "Risk-first leveraged scalp / liquidation-distance gating"),
    Component("gate_shock", "Shock / unstable bar", "gate", "gate", "gate",
              (P("range_mult", 3.0, 1, 20, "float"), P("vol_z", 4.0, 1, 20, "float"),
               P("vol_window", 96, 10, 2000), P("cooldown", 3, 0, 100), _ATR), _g_shock,
              "block when range > range_mult * prior ATR or volume z > vol_z, plus cooldown bars",
              "Unscheduled news proxy: the regime table's crowded/unstable no-trade state.",
              "A shock that is the start of a clean trend is skipped.", "regime_identification: no-trade"),
    Component("gate_session", "Session filter", "gate", "gate", "gate",
              (P("weekend", 0, 0, 1, "int", "1 = no trades Saturday/Sunday UTC"),), _g_session,
              "block in the UTC hours listed in `blocked_hours` (aggregate settings) and optionally weekends",
              "Thin hours where spreads widen.", "Hours are a guess unless measured.", "added",
              default_enabled=False),
    Component("gate_events", "Scheduled-event blackout", "gate", "gate", "gate",
              (P("before_min", 15, 0, 1440), P("after_min", 30, 0, 1440)), _g_events,
              "block within [event - before, event + after] for each event in the events file",
              "CPI/FOMC/unlock windows where 5m direction is a coin flip with fat tails.",
              "Only as good as the events file.", "regime_identification: event/news risk",
              needs=("events",)),
    Component("gate_volume", "Thin-market filter", "gate", "gate", "gate",
              (P("short", 12, 1, 500), P("long", 288, 10, 10000), P("min_ratio", 0.3, 0.01, 2, "float")),
              _g_volume, "block when SMA(volume, short) < min_ratio * SMA(volume, long)",
              "Thin liquidity makes 5m signals unreliable.", "Quiet but orderly sessions.", "added"),
    Component("gate_news", "Headline risk (live)", "gate", "gate", "gate",
              (P("window_min", 30, 5, 1440),), _g_news,
              "block when a headline naming the asset appeared within window_min (live RSS read)",
              "Headline-driven reversals.", "Keyword match only; no sentiment is scored. Live only.",
              "regime_identification: immediate event/news risk", needs=("live",), forward_only=True,
              default_enabled=False),
)

BY_ID: dict[str, Component] = {c.id: c for c in COMPONENTS}
if len(BY_ID) != len(COMPONENTS):  # pragma: no cover - import-time guard
    raise RuntimeError("duplicate component id")

# Catalogue entries from 5minleveragestrategies.json that are NOT five-minute direction calls,
# and why. Shown in the tab and the skill so nothing in the source file silently disappears.
NOT_DIRECTIONAL: dict[str, str] = {
    "Range / grid trading": "Places resting orders on both sides; no direction call. Tested by the grid tools.",
    "Scalping": "A trade style, not a signal. Every component here is a scalping input; the cost gate "
                "is the scalping hurdle.",
    "Swing trading": "Multi-day horizon. See the registry's swing_confluence strategy.",
    "Dollar-cost averaging (DCA)": "Accumulation schedule, not a forecast. Registry strategy dca.",
    "Cross-exchange arbitrage": "Needs simultaneous executable prices on two venues; not in OHLCV.",
    "Funding-rate arbitrage / cash-and-carry": "Market-neutral carry, not direction. Its input (funding) "
                                               "is scored here as a positioning signal.",
    "Triangular arbitrage": "Needs three synchronous order books on one venue; not in OHLCV.",
    "Jupiter long/short-flow imbalance filter": "Jupiter does not publish the rolling imbalance as history; "
                                                "the live Hyperliquid book imbalance is the closest observable.",
}


# -- configuration -----------------------------------------------------------------------------

AGGREGATE_SPECS: tuple[ParamSpec, ...] = (
    P("entry", 0.25, 0.01, 1, "float", "|composite| needed to call UP or DOWN"),
    P("exit", 0.10, 0.0, 1, "float", "a held position stays on while |composite| >= exit (same sign)"),
    P("min_coverage", 0.5, 0.0, 1, "float", "share of enabled weight that must be defined to call"),
    P("dedupe_families", 1, 0, 1, "int", "1 = each family votes once"),
    P("regime_weighting", 1, 0, 1, "int", "1 = scale styles by regime"),
    P("adx_period", 14, 2, 100),
    P("trend_adx", 25, 5, 80, "float"),
    P("range_adx", 18, 1, 60, "float"),
    P("squeeze_pct", 15, 1, 50, "float"),
    P("squeeze_lookback", 288, 20, 5000),
    P("allow_short", 1, 0, 1, "int", "0 = long or flat only"),
    P("adaptive", 1, 0, 1, "int", "1 = weight each metric by its own learned edge over a coin flip"),
    P("adaptive_prior", 100, 0, 100000, "float",
      "pseudo-calls at 50% every metric starts with; larger = slower to trust a streak"),
    P("adaptive_window", 4032, 12, 1000000, "int",
      "only calls from the last N bars count, so the record is capped; 4032 = two weeks of 5m"),
    P("adaptive_halflife", 0, 0, 1000000, "int",
      "0 = every call in the window counts equally; N = calls also fade, counting half after N bars"),
    P("adaptive_flip", 1, 0, 1, "int", "1 = invert a metric that is reliably WRONG instead of muting it"),
    P("tune", 0, 0, 1, "int", "1 = each metric moves its numbers to a neighbouring setting once that "
      "neighbour is proving more accurate"),
    P("tune_confidence", 0.95, 0.5, 0.9999, "float",
      "posterior probability a neighbour must beat the current settings by before a move"),
    P("tune_min_calls", 300, 10, 1000000, "float", "decayed calls a neighbour needs before it can be adopted"),
    P("tune_step", 0.25, 0.05, 1.0, "float", "neighbours sit at x(1 - step) and x(1 + step) of each number"),
    P("tune_cooldown", 576, 1, 1000000, "int", "bars to wait after a move (576 = two days of 5m)"),
)

EXECUTION_SPECS: tuple[ParamSpec, ...] = (
    P("leverage", 5.0, 1.0, 250.0, "float", "perp leverage for P&L and the liquidation gate"),
    P("fee_bps", 4.5, 0.0, 100.0, "float",
      "per side; Hyperliquid base taker 0.045% (Jupiter Perps 0.06%; research/results/hyperliquid-costs-2026-11-07.json)"),
    P("slippage_bps", 2.0, 0.0, 100.0, "float",
      "per side; Hyperliquid book cost at $2k was at most 2.2 bps on all ten coins; raise it per coin for large size"),
    P("risk_pct", 1.0, 0.01, 100.0, "float",
      "percent of the wallet's usable collateral a trade may lose at its stop, costs included"),
    P("use_wallet", 1.0, 0.0, 1.0, "float", "1 = read the Settings Solana address and size calls to it"),
)


# Cross-parameter rules, checked when a config is saved, so a bad pair is refused at the form
# instead of silently disabling a component at evaluation time.
RELATIONS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "ema_cross": (("fast", "slow", "fast must be below slow"),),
    "macd": (("fast", "slow", "fast must be below slow"),),
    "trend_continuation": (("fast", "slow", "fast must be below slow"),),
    "trend_lifecycle": (("fast", "slow", "fast must be below slow"),),
    "fib_pullback": (("zone_lo", "zone_hi", "zone_lo must be below zone_hi"),),
}


def default_config() -> dict[str, Any]:
    """Every component with its default switch, weight and parameters."""
    return {
        "components": {c.id: {"enabled": c.default_enabled, "weight": c.default_weight,
                              "params": c.defaults()} for c in COMPONENTS},
        "aggregate": {s.name: (int(s.default) if s.kind == "int" else float(s.default))
                      for s in AGGREGATE_SPECS},
        "execution": {s.name: float(s.default) for s in EXECUTION_SPECS},
        "blocked_hours": [],
    }


def normalise_config(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    """Fill defaults, validate every number, drop unknown keys. Raises ScorecardError."""
    cfg = default_config()
    if raw is None:
        return cfg
    if not isinstance(raw, Mapping):
        raise ScorecardError("config must be an object")
    comps = raw.get("components") or {}
    if not isinstance(comps, Mapping):
        raise ScorecardError("components must be an object")
    for cid, entry in comps.items():
        if cid not in BY_ID:
            continue  # a component removed from the code: ignore, never crash on an old file
        if not isinstance(entry, Mapping):
            raise ScorecardError(f"{cid}: entry must be an object")
        comp, out = BY_ID[cid], cfg["components"][cid]
        if "enabled" in entry:
            out["enabled"] = bool(entry["enabled"])
        if "weight" in entry:
            try:
                out["weight"] = P("weight", 1, 0, 10, "float").coerce(entry["weight"])
            except ScorecardError as exc:
                raise ScorecardError(f"{cid}: {exc}") from exc
        params = entry.get("params") or {}
        if not isinstance(params, Mapping):
            raise ScorecardError(f"{cid}: params must be an object")
        specs = {p.name: p for p in comp.params}
        for name, value in params.items():
            if name not in specs:
                raise ScorecardError(f"{cid}: unknown parameter {name!r}; known: {', '.join(specs)}")
            try:
                out["params"][name] = specs[name].coerce(value)
            except ScorecardError as exc:
                raise ScorecardError(f"{cid}: {exc}") from exc
    for section, specs in (("aggregate", AGGREGATE_SPECS), ("execution", EXECUTION_SPECS)):
        given = raw.get(section) or {}
        if not isinstance(given, Mapping):
            raise ScorecardError(f"{section} must be an object")
        known = {s.name: s for s in specs}
        for name, value in given.items():
            if name not in known:
                raise ScorecardError(f"{section}: unknown setting {name!r}; known: {', '.join(known)}")
            cfg[section][name] = known[name].coerce(value)
    for cid, rules in RELATIONS.items():
        params = cfg["components"][cid]["params"]
        for a, b, why in rules:
            if not params[a] < params[b]:
                raise ScorecardError(f"{cid}: {why} (got {a}={params[a]:g}, {b}={params[b]:g})")
    if cfg["components"]["htf_trend"]["params"]["tf_minutes"] % 5:
        raise ScorecardError("htf_trend: tf_minutes must be a multiple of 5")
    agg = cfg["aggregate"]
    if agg["exit"] > agg["entry"]:
        raise ScorecardError("aggregate: exit must not exceed entry")
    if agg["range_adx"] > agg["trend_adx"]:
        raise ScorecardError("aggregate: range_adx must not exceed trend_adx")
    hours = raw.get("blocked_hours", [])
    if not isinstance(hours, (list, tuple)) or not all(isinstance(h, int) and 0 <= h <= 23 for h in hours):
        raise ScorecardError("blocked_hours must be a list of UTC hours 0-23")
    cfg["blocked_hours"] = sorted(set(hours))
    return cfg


def config_hash(cfg: Mapping[str, Any]) -> str:
    """Stable id for a normalised config: the forward ledger and results key on it."""
    text = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def standalone_config(cfg: Mapping[str, Any], component_id: str) -> dict[str, Any]:
    """`cfg` with only one score component enabled and every gate off.

    A component's own track record must not borrow the compound's gates or its learned weights,
    or the standalone row would measure those as much as the component.
    """
    if component_id not in BY_ID or BY_ID[component_id].kind != "score":
        raise ScorecardError(f"{component_id!r} is not a score component")
    out = json.loads(json.dumps(cfg))
    for cid, entry in out["components"].items():
        entry["enabled"] = cid == component_id
    out["components"][component_id]["weight"] = 1.0
    # A standalone row measures the metric itself. Learned weighting would mute a metric that is
    # losing (its multiplier drops to 0) and the row would report no calls instead of the record.
    out["aggregate"]["adaptive"] = 0
    out["aggregate"]["tune"] = 0
    return out


# -- evaluation --------------------------------------------------------------------------------


def adaptive_counts(score: np.ndarray, close: np.ndarray, entry: float, window: int, halflife: float = 0,
                    seed: Sequence[tuple[int, float, float]] = ()) -> tuple[np.ndarray, np.ndarray]:
    """(hits, calls) a metric has on record when deciding at each bar.

    A metric "calls" a bar when |score| >= entry; the call is right when the next bar moves the
    called way (unchanged closes are not counted). The call made at bar k is only known to be
    right or wrong once bar k+1 has CLOSED, so it enters the record used at bar k+1, never at k.
    That one-bar lag keeps the learned weights free of look-ahead; the prefix-invariance test
    checks it with adaptive weighting on.

    The record is CAPPED: only calls resolved within the last `window` bars count. Without a
    cap, five months of history would make each new miss move the hit rate by a meaningless
    amount; with it, a miss today moves it as much as a miss did on day one. `halflife` > 0
    additionally fades calls inside the window.

    `seed` holds earlier resolved calls from the forward ledger as (k, hit, call) with k the
    call's bar index relative to bar 0 (k < 0). They expire from the window like any other call.
    """
    n = close.size
    w = int(window)
    lam = 1.0 if not halflife else 0.5 ** (1.0 / float(halflife))
    vote = np.where(np.isfinite(score) & (np.abs(np.nan_to_num(score)) >= entry), np.sign(np.nan_to_num(score)), 0.0)
    move = np.zeros(n)
    move[:-1] = np.sign(np.diff(close))
    decided = (vote != 0) & (move != 0)
    decided[-1:] = False  # the last bar's outcome has not happened yet
    hit = decided & (vote == move)
    # Extended timeline: w slots of pre-history (for ledger calls), then the n bars. Position
    # w + j holds the outcomes that become known at bar j.
    x_hit = np.zeros(w + n)
    x_call = np.zeros(w + n)
    x_hit[w + 1:] = hit[:-1]
    x_call[w + 1:] = decided[:-1]
    for k, h, c in seed:
        pos = w + int(k) + 1
        if 0 <= pos <= w:
            x_hit[pos] += h
            x_call[pos] += c

    def windowed(x: np.ndarray) -> np.ndarray:
        # S_inf[q] = lam * S_inf[q-1] + x[q]; dropping everything older than w bars leaves
        # S[q] = S_inf[q] - lam**w * S_inf[q-w]. With lam == 1 this is a rolling sum.
        if lam == 1.0:
            s_inf = np.cumsum(x)
        else:
            s_inf = pd.Series(np.concatenate(([0.0], x))).ewm(alpha=1.0 - lam, adjust=False).mean().to_numpy()[1:]
            s_inf = s_inf / (1.0 - lam)
        old = np.zeros_like(s_inf)
        old[w:] = s_inf[:-w] if w else s_inf
        return (s_inf - (lam ** w) * old)[w:]

    return windowed(x_hit), windowed(x_call)


def adaptive_multiplier(hits: np.ndarray, calls: np.ndarray, prior: float, flip: bool) -> np.ndarray:
    """Edge over a coin flip from a hit rate shrunk toward 50%.

    p = (hits + prior/2) / (calls + prior); edge = 2p - 1. Multiplying weights by the raw hit
    rate (0.55 vs 0.47) would barely separate a useful metric from a harmful one and would still
    let a metric that is wrong more often than right vote. The edge is zero at 50%, so a metric
    with no demonstrated skill gets no say; negative edges are muted, or inverted with `flip`.
    """
    den = calls + prior
    p = np.where(den > 0, (hits + prior / 2.0) / np.where(den > 0, den, 1.0), 0.5)
    edge = 2.0 * p - 1.0
    return edge if flip else np.maximum(edge, 0.0)


def _phi(z: np.ndarray) -> np.ndarray:
    """Standard normal CDF (Abramowitz-Stegun 7.1.26 erf, |error| < 1.5e-7); numpy has no erf."""
    x = np.abs(z) / math.sqrt(2.0)
    tt = 1.0 / (1.0 + 0.3275911 * x)
    y = 1.0 - (((((1.061405429 * tt - 1.453152027) * tt) + 1.421413741) * tt - 0.284496736) * tt
               + 0.254829592) * tt * np.exp(-x * x)
    return 0.5 * (1.0 + np.sign(z) * y)


def beta_posterior(hits: np.ndarray, calls: np.ndarray, prior: float) -> tuple[np.ndarray, np.ndarray]:
    """(mean, variance) of the hit probability under a Beta(prior/2, prior/2) prior.

    This is Bayes' theorem for a right/wrong record: every resolved call adds one to the hits
    or to the misses, and the posterior narrows as the count grows. Decayed counts make it a
    posterior that also forgets.
    """
    a = hits + prior / 2.0
    b = np.maximum(calls - hits, 0.0) + prior / 2.0
    s = np.maximum(a + b, 1e-12)
    return a / s, a * b / (s * s * (s + 1.0))


def p_better_than(mean_a: np.ndarray, var_a: np.ndarray, mean_b: np.ndarray, var_b: np.ndarray) -> np.ndarray:
    """P(true hit rate of a > that of b), normal approximation to two Beta posteriors.

    It treats the two records as independent. They are scored on the same bars and positively
    correlated, so the true variance of the difference is smaller: this errs toward NOT moving.
    """
    return _phi((mean_a - mean_b) / np.sqrt(np.maximum(var_a + var_b, 1e-18)))


TUNE_SKIP = ("mode", "weekend")
TUNE_MAX_MOVES = 50


def neighbours(comp: Component, params: Mapping[str, Any], step: float) -> list[dict[str, Any]]:
    """Settings one step away from `params`, one number at a time, valid and distinct."""
    out: list[dict[str, Any]] = []
    for spec in comp.params:
        if spec.name in TUNE_SKIP or (spec.kind == "int" and spec.lo == 0 and spec.hi == 1):
            continue
        v = params[spec.name]
        for factor in (1.0 - step, 1.0 + step):
            nv: float | int = v * factor
            if spec.kind == "int":
                nv = int(round(nv))
                if nv == v:
                    nv = v + (1 if factor > 1 else -1)
            nv = min(max(nv, spec.lo), spec.hi)
            if nv == v:
                continue
            cand = {**params, spec.name: int(nv) if spec.kind == "int" else float(nv)}
            if any(not cand[a] < cand[b] for a, b, _ in RELATIONS.get(comp.id, ())):
                continue
            if cand not in out:
                out.append(cand)
    return out


def tune_component(comp: Component, bars: Bars, params: Mapping[str, Any], aux: Mapping[str, Any],
                   agg: Mapping[str, Any]) -> tuple[np.ndarray, list[tuple[int, dict[str, Any]]]]:
    """Score series that walks to better neighbouring settings as evidence arrives.

    At every bar t the active settings are compared with their neighbours using each one's
    record up to t-1 (`adaptive_counts`). A neighbour is adopted only when P(it is more accurate)
    exceeds `tune_confidence` and it has `tune_min_calls` decayed calls; then the search
    re-centres on it and waits `tune_cooldown` bars. Moving after every single miss would chase
    noise: at 5m about half of all outcomes are coin flips. Every quantity used at t is known at
    t, which the prefix-invariance test checks with tuning on.

    Returns (score series, [(bar index, settings adopted there), ...]).
    """
    n = len(bars)
    active = dict(params)
    out = np.full(n, np.nan)
    moves: list[tuple[int, dict[str, Any]]] = []
    start, earliest = 0, 0
    prior, entry = agg["adaptive_prior"], agg["entry"]
    win, hl = agg["adaptive_window"], agg["adaptive_halflife"]
    while True:
        cands = [active] + neighbours(comp, active, agg["tune_step"])
        series, stats = [], []
        for c in cands:
            try:
                s = _clip(np.asarray(comp.fn(bars, dict(c), aux), dtype="float64"))
            except ScorecardError:
                if c is active:
                    raise
                continue
            h, k = adaptive_counts(s, bars.close, entry, win, hl)
            series.append((c, s, k))
            stats.append(beta_posterior(h, k, prior))
        cur_series = series[0][1]
        switch_at, choice = None, None
        if len(moves) < TUNE_MAX_MOVES and earliest < n:
            m0, v0 = stats[0]
            best_p = np.zeros(n)
            best_j = np.full(n, -1)
            for j in range(1, len(series)):
                mj, vj = stats[j]
                pj = np.where(series[j][2] >= agg["tune_min_calls"], p_better_than(mj, vj, m0, v0), 0.0)
                better = pj > best_p
                best_p = np.where(better, pj, best_p)
                best_j = np.where(better, j, best_j)
            ok = np.where(best_p[earliest:] > agg["tune_confidence"])[0]
            if ok.size:
                switch_at = int(earliest + ok[0])
                choice = int(best_j[switch_at])
        if switch_at is None:
            out[start:] = cur_series[start:]
            return out, moves
        out[start:switch_at] = cur_series[start:switch_at]
        active = dict(series[choice][0])
        moves.append((switch_at, active))
        start = switch_at
        earliest = switch_at + int(agg["tune_cooldown"])


@dataclass
class Evaluation:
    """Everything the aggregator produced for one contiguous run of bars."""

    bars: Bars
    config: dict[str, Any]
    scores: dict[str, np.ndarray]
    gates: dict[str, np.ndarray]
    regime: np.ndarray
    composite: np.ndarray
    coverage: np.ndarray
    blocked: np.ndarray
    indication: np.ndarray  # -1, 0, +1
    errors: dict[str, str] = field(default_factory=dict)
    # id -> {"hit_rate", "calls", "multiplier"} arrays, when adaptive weighting is on.
    adaptive: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)
    # id -> [(bar index, settings adopted there)], when tuning is on.
    tuned: dict[str, list[tuple[int, dict[str, Any]]]] = field(default_factory=dict)


def classify_regime(b: Bars, agg: Mapping[str, Any]) -> np.ndarray:
    """trend / range / squeeze / neutral per bar, from ADX and Bollinger bandwidth."""
    _, _, adx = dmi(b, agg["adx_period"])
    mid, sd = sma(b.close, 20), rstd(b.close, 20)
    width_rank = pct_rank(_safe_div(4.0 * sd, mid), agg["squeeze_lookback"])
    out = np.full(len(b), "neutral", dtype=object)
    out[np.nan_to_num(width_rank, nan=100.0) <= agg["squeeze_pct"]] = "squeeze"
    out[np.nan_to_num(adx, nan=agg["trend_adx"] - 1e-9) <= agg["range_adx"]] = "range"
    out[np.nan_to_num(adx, nan=0.0) >= agg["trend_adx"]] = "trend"
    return out


def _aux_for(cfg: Mapping[str, Any], aux: Mapping[str, Any] | None) -> dict[str, Any]:
    out = dict(aux or {})
    ex = cfg["execution"]
    out.setdefault("round_trip_bps", round_trip_bps(ex["fee_bps"], ex["slippage_bps"]))
    out.setdefault("leverage", ex["leverage"])
    out.setdefault("blocked_hours", tuple(cfg.get("blocked_hours") or ()))
    return out


def evaluate(bars: Bars, config: Mapping[str, Any] | None = None,
             aux: Mapping[str, Any] | None = None) -> Evaluation:
    """Score, aggregate and gate every bar of one contiguous run."""
    cfg = normalise_config(config)
    aux_ = _aux_for(cfg, aux)
    n = len(bars)
    agg = cfg["aggregate"]
    scores: dict[str, np.ndarray] = {}
    gates: dict[str, np.ndarray] = {}
    errors: dict[str, str] = {}
    tuned: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for comp in COMPONENTS:
        entry = cfg["components"][comp.id]
        if not entry["enabled"]:
            continue
        try:
            if agg["tune"] and comp.kind == "score" and not comp.forward_only and n:
                values, moves = tune_component(comp, bars, entry["params"], aux_, agg)
                if moves:
                    tuned[comp.id] = moves
            else:
                values = comp.fn(bars, dict(entry["params"]), aux_)
        except ScorecardError as exc:
            # Never drop an enabled component silently: an errored gate BLOCKS (fails closed)
            # and an errored score counts as undefined, which lowers coverage.
            errors[comp.id] = str(exc)
            if comp.kind == "gate":
                gates[comp.id] = np.ones(n, dtype=bool)
            continue
        values = np.asarray(values)
        if values.shape != (n,):
            raise ScorecardError(f"{comp.id} returned shape {values.shape}, expected ({n},)")
        if comp.kind == "gate":
            gates[comp.id] = values.astype(bool)
        else:
            scores[comp.id] = _clip(values.astype("float64"))

    regime = classify_regime(bars, agg) if n else np.array([], dtype=object)
    num = np.zeros(n)
    den = np.zeros(n)
    present = np.zeros(n)
    failed_scores = [c for c in errors if BY_ID[c].kind == "score"]
    total = sum(cfg["components"][c]["weight"] for c in (*scores, *failed_scores)) or 0.0
    by_family: dict[str, list[str]] = {}
    for cid in scores:
        by_family.setdefault(BY_ID[cid].family, []).append(cid)

    def mult(style: str) -> np.ndarray:
        if not agg["regime_weighting"]:
            return np.ones(n)
        out = np.ones(n)
        for name, table in REGIME_MULTIPLIERS.items():
            if style in table:
                out = np.where(regime == name, table[style], out)
        return out

    learned: dict[str, dict[str, np.ndarray]] = {}
    if agg["adaptive"] and n:
        seeds = aux_.get("adaptive_seed") or {}
        for cid in scores:
            h, c = adaptive_counts(scores[cid], bars.close, agg["entry"], agg["adaptive_window"],
                                   agg["adaptive_halflife"], seeds.get(cid, ()))
            prior = agg["adaptive_prior"]
            learned[cid] = {
                "hit_rate": np.where(c + prior > 0, (h + prior / 2.0) / np.maximum(c + prior, 1e-12), 0.5),
                "calls": c,
                "multiplier": adaptive_multiplier(h, c, prior, bool(agg["adaptive_flip"])),
            }

    for family, members in by_family.items():
        fam_num = np.zeros(n)
        fam_den = np.zeros(n)
        fam_wmax = np.zeros(n)
        for cid in members:
            s = scores[cid]
            w = cfg["components"][cid]["weight"] * mult(BY_ID[cid].style)
            if cid in learned:
                m = learned[cid]["multiplier"]
                s = s * np.sign(m)  # a flipped (reliably wrong) metric votes the other way
                w = w * np.abs(m)
            ok = np.isfinite(s) & (w > 0)
            fam_num += np.where(ok, w * np.nan_to_num(s), 0.0)
            fam_den += np.where(ok, w, 0.0)
            fam_wmax = np.maximum(fam_wmax, np.where(ok, w, 0.0))
            present += np.where(np.isfinite(s), cfg["components"][cid]["weight"], 0.0)
        if agg["dedupe_families"]:
            fam_score = np.where(fam_den > 0, _safe_div(fam_num, fam_den), 0.0)
            num += fam_wmax * np.nan_to_num(fam_score)
            den += fam_wmax
        else:
            num += fam_num
            den += fam_den

    composite = np.where(den > 0, _safe_div(num, den), np.nan)
    coverage = present / total if total > 0 else np.zeros(n)
    composite = np.where(coverage >= agg["min_coverage"], composite, np.nan)
    blocked = np.zeros(n, dtype=bool)
    for g in gates.values():
        blocked |= g
    call = np.where(composite >= agg["entry"], 1, np.where(composite <= -agg["entry"], -1, 0))
    call = np.where(np.isnan(composite) | blocked, 0, call)
    if not agg["allow_short"]:
        call = np.where(call < 0, 0, call)
    return Evaluation(bars, cfg, scores, gates, regime, composite, coverage, blocked,
                      call.astype("int8"), errors, learned, tuned)


def target_path(ev: Evaluation) -> np.ndarray:
    """Position target per bar with entry/exit hysteresis.

    Enter on a call. Stay on while the composite keeps the same sign with |composite| >= exit
    and no gate blocks; otherwise go flat (or flip, if the opposite call fires). Hysteresis is
    the main defence against paying a 16 bps round trip on every 5m wiggle.
    """
    agg = ev.config["aggregate"]
    out = np.zeros(len(ev.bars))
    pos = 0.0
    for i in range(out.size):
        c, comp = int(ev.indication[i]), ev.composite[i]
        if c != 0:
            pos = float(c)
        elif pos != 0.0:
            keep = (not ev.blocked[i]) and np.isfinite(comp) and comp * pos >= agg["exit"]
            pos = pos if keep else 0.0
        out[i] = pos
    return out


def explain(ev: Evaluation, i: int = -1, catalogue: bool = False) -> dict[str, Any]:
    """Per-component breakdown at bar i: what each metric said and how much it counted."""
    n = len(ev.bars)
    if n == 0:
        raise ScorecardError("no bars to explain")
    i = i % n
    cfg = ev.config
    agg = cfg["aggregate"]
    regime = str(ev.regime[i])
    rows = []
    for comp in COMPONENTS:
        entry = cfg["components"][comp.id]
        row: dict[str, Any] = {"id": comp.id, "name": comp.name, "family": comp.family, "style": comp.style,
                               "kind": comp.kind, "enabled": entry["enabled"], "weight": entry["weight"],
                               "params": dict(entry["params"]), "forward_only": comp.forward_only}
        if comp.id in ev.errors:
            row["status"], row["detail"] = "error", ev.errors[comp.id]
            if comp.kind == "gate":
                row["blocked"] = True
        elif not entry["enabled"]:
            row["status"] = "off"
        elif comp.kind == "gate":
            row["blocked"] = bool(ev.gates[comp.id][i])
            row["status"] = "blocking" if row["blocked"] else "pass"
        else:
            s = float(ev.scores[comp.id][i])
            if math.isfinite(s):
                m = 1.0
                if agg["regime_weighting"]:
                    m = REGIME_MULTIPLIERS.get(regime, {}).get(comp.style, 1.0)
                a = 1.0
                if comp.id in ev.adaptive:
                    lr = ev.adaptive[comp.id]
                    a = float(lr["multiplier"][i])
                    calls_i = float(lr["calls"][i])
                    hits_i = (float(lr["hit_rate"][i]) * (calls_i + agg["adaptive_prior"])
                              - agg["adaptive_prior"] / 2.0)
                    mean, var = beta_posterior(np.array([hits_i]), np.array([calls_i]), agg["adaptive_prior"])
                    row.update(learned_hit=round(float(lr["hit_rate"][i]), 4),
                               learned_calls=round(calls_i, 1), adaptive_mult=round(a, 4),
                               p_better_than_coinflip=round(float(_phi((mean - 0.5) / np.sqrt(np.maximum(var, 1e-18)))[0]), 4))
                moves = [mv for mv in ev.tuned.get(comp.id, []) if mv[0] <= i]
                if moves:
                    row.update(tuned_params=dict(moves[-1][1]), tuned_moves=len(moves),
                               tuned_since=int(ev.bars.ts[moves[-1][0]]))
                vote = s * (1.0 if a >= 0 else -1.0)
                row.update(status="scored", score=round(s, 4), regime_mult=m,
                           effective_weight=round(entry["weight"] * m * abs(a), 4),
                           vote="up" if vote > 0 else "down" if vote < 0 else "none",
                           inverted=a < 0)
            else:
                row["status"] = "unavailable" if (comp.needs or comp.forward_only) else "warming up"
        if catalogue:
            row.update(formula=comp.formula, useful_when=comp.useful_when,
                       not_useful_when=comp.not_useful_when, source=comp.source)
        rows.append(row)
    scored = [r for r in rows if r.get("status") == "scored"]
    comp = float(ev.composite[i])
    call = int(ev.indication[i])
    lc = cfg["components"]["trend_lifecycle"]["params"]
    cp = cfg["components"]["cycle_phase"]["params"]
    agree = sum(r["effective_weight"] for r in scored
                if math.isfinite(comp) and r["score"] * (-1 if r.get("inverted") else 1) * comp > 0)
    weight = sum(r["effective_weight"] for r in scored)
    return {
        "bar_ts": int(ev.bars.ts[i]),
        "decided_at": int(ev.bars.ts[i]) + BAR_SECONDS,
        "price": float(ev.bars.close[i]),
        "call": {1: "UP", -1: "DOWN"}.get(call, "FLAT"),
        "composite": None if not math.isfinite(comp) else round(comp, 4),
        "coverage": round(float(ev.coverage[i]), 4),
        "agreement": None if weight == 0 else round(agree / weight, 4),
        "regime": regime,
        "trend_stage": str(lifecycle_labels(ev.bars, lc)[i]),
        "cycle_phase": str(cycle_phase(ev.bars, cp)[0][i]),
        "blocked_by": [g for g, v in ev.gates.items() if bool(v[i])],
        "entry": agg["entry"],
        "adaptive": bool(agg["adaptive"]),
        "relations": relations(ev),
        "round_trip_bps": round_trip_bps(cfg["execution"]["fee_bps"], cfg["execution"]["slippage_bps"]),
        "components": rows,
    }


# -- which metrics duplicate or fight each other ------------------------------------------------

OPPOSED_CORR = -0.6
DUPLICATE_CORR = 0.85


def relations(ev: Evaluation, window: int = 2016, min_points: int = 200) -> dict[str, list[dict[str, Any]]]:
    """Pairs of enabled metrics whose recent scores move against (opposed) or with (duplicate)
    each other, measured on the last `window` bars of this evaluation.

    Opposed pairs cancel in the composite: with both on, the call rests on whichever side has
    more weight. Duplicates in different families count the same evidence twice.
    """
    ids = [c for c in ev.scores if np.isfinite(ev.scores[c][-window:]).sum() >= min_points]
    opposed, duplicates = [], []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            sa, sb = ev.scores[a][-window:], ev.scores[b][-window:]
            m = np.isfinite(sa) & np.isfinite(sb)
            if m.sum() < min_points or np.std(sa[m]) == 0 or np.std(sb[m]) == 0:
                continue
            r = float(np.corrcoef(sa[m], sb[m])[0, 1])
            row = {"a": a, "b": b, "corr": round(r, 3), "same_family": BY_ID[a].family == BY_ID[b].family}
            if r <= OPPOSED_CORR:
                opposed.append(row)
            elif r >= DUPLICATE_CORR and not row["same_family"]:
                duplicates.append(row)
    opposed.sort(key=lambda r: r["corr"])
    duplicates.sort(key=lambda r: -r["corr"])
    return {"opposed": opposed, "duplicates": duplicates}


# -- forecast statistics -----------------------------------------------------------------------


CALIBRATION_EDGES = (-1.0001, -0.5, -0.25, -0.1, 0.1, 0.25, 0.5, 1.0001)


def forecast_stats(evals: Sequence[Evaluation], ts_from: float | None = None,
                   ts_to: float | None = None) -> dict[str, Any]:
    """Direction accuracy of the per-bar call over the NEXT bar, within [ts_from, ts_to).

    Outcome for a call at bar t: sign(close[t+1] - close[t]). Ties are excluded from the hit
    rate and counted. `oracle_net_bps` is what a perfect direction call would earn per one-bar
    round trip after costs -- the ceiling, which at 5m is usually negative.
    """
    rows = []
    for ev in evals:
        b = ev.bars
        if len(b) < 2:
            continue
        sel = np.ones(len(b) - 1, dtype=bool)
        if ts_from is not None:
            sel &= b.ts[:-1] >= ts_from
        if ts_to is not None:
            sel &= b.ts[:-1] < ts_to
        r = np.diff(np.log(b.close))[sel] * 1e4
        rows.append((ev.indication[:-1][sel], r, ev.composite[:-1][sel]))
    if not rows:
        return {"bars": 0, "calls": 0}
    call = np.concatenate([x[0] for x in rows]).astype(float)
    ret = np.concatenate([x[1] for x in rows])
    comp = np.concatenate([x[2] for x in rows])
    rt = None
    if evals:
        ex = evals[0].config["execution"]
        rt = round_trip_bps(ex["fee_bps"], ex["slippage_bps"])
    active = call != 0
    decided = active & (ret != 0)
    hits = (np.sign(ret) == call) & decided
    n_dec = int(decided.sum())
    hit_rate = float(hits.sum() / n_dec) if n_dec else None
    signed = (call * ret)[active]
    up_base = float((ret > 0).mean()) if ret.size else None
    z = None
    if n_dec:
        z = (hits.sum() - 0.5 * n_dec) / math.sqrt(0.25 * n_dec)
    calib = []
    finite = np.isfinite(comp)
    for lo, hi in zip(CALIBRATION_EDGES[:-1], CALIBRATION_EDGES[1:], strict=True):
        m = finite & (comp >= lo) & (comp < hi) & (ret != 0)
        calib.append({"from": round(max(lo, -1.0), 2), "to": round(min(hi, 1.0), 2), "n": int(m.sum()),
                      "up_rate": None if not m.any() else round(float((ret[m] > 0).mean()), 4)})
    out = {
        "bars": int(ret.size),
        "calls": int(active.sum()),
        "coverage": round(float(active.mean()), 4) if ret.size else 0.0,
        "ties": int((active & (ret == 0)).sum()),
        "hit_rate": None if hit_rate is None else round(hit_rate, 4),
        "z_vs_coinflip": None if z is None else round(float(z), 2),
        "base_up_rate": None if up_base is None else round(up_base, 4),
        "gross_bps_per_call": None if not signed.size else round(float(signed.mean()), 3),
        "mean_abs_move_bps": round(float(np.abs(ret).mean()), 3) if ret.size else None,
        "round_trip_bps": rt,
        "calibration": calib,
    }
    if rt is not None and signed.size:
        out["net_bps_per_call_if_one_bar"] = round(float(signed.mean()) - rt, 3)
    if rt is not None and ret.size:
        out["oracle_net_bps"] = round(float(np.abs(ret).mean()) - rt, 3)
    return out


def catalog() -> dict[str, Any]:
    """The whole catalogue, for the tab, the CLI and the skill."""
    return {
        "components": [c.to_dict() for c in COMPONENTS],
        "aggregate": [s.to_dict() for s in AGGREGATE_SPECS],
        "execution": [s.to_dict() for s in EXECUTION_SPECS],
        "regime_multipliers": REGIME_MULTIPLIERS,
        "not_directional": NOT_DIRECTIONAL,
    }

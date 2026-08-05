"""What every registered strategy, signal and indicator says about the last bar.

    python3 research/decide.py --asset SOL --interval 1d
    python3 research/decide.py --data data/BTC_1d.csv --json

Three sections, because they are three different kinds of claim:

  * **Strategies** -- every entry in `core.strategies.REGISTRY`, replayed
    bar-by-bar from the start of history. Several carry state (`_holding`), so
    today's target exposure is *path-dependent*: it depends on which past bar
    opened the position, not only on today's indicator values. There is no
    shortcut. Calling `on_bar` once on the last bar would report a different --
    and wrong -- number for every stateful strategy.
  * **Signals** -- the stateless one-bar comparisons underneath those
    strategies (MACD line vs signal, close vs band, +DI vs -DI). Each is
    printed with the rule that produced it, because the same fact reads
    opposite ways to a reversion and a breakout rule: a close below the lower
    Bollinger band is bullish to `bb_reversion` and bearish to `bb_breakout`.
    That disagreement is the informative part and must stay visible.
  * **Indicators** -- raw values from `core.indicators`. Many have no
    direction at all (ATR, realised vol, half-life), and those are printed with
    an explicit "no directional reading" rather than being forced into a verb.

Deliberately NOT here:

  * A consensus verdict or a BUY/SELL vote count across strategies. These rules
    are heavily correlated; `research/cpcv_sweep.interpret` exists precisely to
    kill the "lots of strategies agree, so it must be real" misreading. The
    per-family tally is printed as a description of correlated rules, labelled
    as such, never as a score.
  * Any order placement. This reads a CSV and prints text.

NOT INVESTMENT ADVICE. Every line is a mechanical rule evaluated on cached
history. None of it is a forecast.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core import indicators as ind  # noqa: E402
from backtester.core.data import CsvLoader, checksum_frame, frame_to_arrays  # noqa: E402

# Imported rather than re-implemented on purpose. This is the engine's own
# clamp of a raw target to what the mode permits; a second copy here could
# drift from it, and then this script would confidently report an exposure the
# backtester would never have taken.
from backtester.core.engine import _resolve_target  # noqa: E402
from backtester.core.strategies import FAMILY, REGISTRY, build  # noqa: E402
from backtester.core.types import (  # noqa: E402
    INTERVAL_SECONDS,
    BarWindow,
    Mode,
    periods_per_year,
)

# Minimum change in target exposure, as a fraction of equity, that is reported
# as a BUY or a SELL. The risk-overlay strategies (`voltarget`, `atr_sized`,
# `garch_voltarget`) re-size continuously, so with a zero tolerance they would
# report a trade on essentially every bar. Mirrors the engine's
# `rebalance_threshold` in spirit; stated in the output because it changes what
# the verbs mean.
DEFAULT_TOLERANCE = 0.01

# Exposure magnitude below which a position is called flat rather than long or
# short. Well under any tradeable size.
FLAT_EPSILON = 1e-9

HOLD_LONG = "HOLD-LONG"
HOLD_SHORT = "HOLD-SHORT"
FLAT = "FLAT"
BUY = "BUY"
SELL = "SELL"
INSUFFICIENT = "NO-DATA"

BULLISH = "bullish"
BEARISH = "bearish"
NEUTRAL = "neutral"
UNAVAILABLE = "n/a"
# Not "neutral": neutral means the rule looked and found nothing, whereas this
# means the indicator has no side to give. ATR does not become bullish.
NO_DIRECTION = "no-direction"


# --------------------------------------------------------------------------
# strategies
# --------------------------------------------------------------------------


@dataclass
class StrategyDecision:
    """One strategy's reading of the final bar."""

    key: str
    name: str
    family: str
    action: str
    target: float | None
    previous: float | None
    warmup: int
    bars: int
    params: dict[str, Any] = field(default_factory=dict)
    note: str = ""

    @property
    def detail(self) -> str:
        """Human-readable exposure transition, or why there isn't one."""
        if self.target is None:
            return self.note
        prev = "flat" if self.previous is None else f"{self.previous:+.2f}"
        return f"{prev} -> {self.target:+.2f}"

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form."""
        return {
            "key": self.key,
            "name": self.name,
            "family": self.family,
            "action": self.action,
            "target_exposure": self.target,
            "previous_exposure": self.previous,
            "warmup_bars": self.warmup,
            "bars_available": self.bars,
            "params": self.params,
            "note": self.note,
            "detail": self.detail,
        }


def replay_targets(
    strategy: Any,
    arrays: dict[str, np.ndarray],
    *,
    mode: Mode = Mode.SPOT,
    allow_short: bool = False,
) -> np.ndarray:
    """Every target exposure the strategy would have asked for, bar by bar.

    Mirrors `engine.run_backtest` steps 4 and 5 exactly: a fresh instance is
    driven forward from bar 0, `on_bar` is called only for `i >= warmup_bars()`
    (so a stateful strategy sees the same call sequence the engine gives it),
    and each raw target goes through the engine's own clamp.

    Returns an array as long as the series, NaN for every bar the strategy was
    not asked about. The NaNs are the point: they mark bars where there is no
    decision, as opposed to a decision to stay flat.
    """
    ts, op = arrays["ts"], arrays["open"]
    hi, lo, cl, vol = arrays["high"], arrays["low"], arrays["close"], arrays["volume"]
    n = len(cl)
    warmup = max(0, int(strategy.warmup_bars()))
    out = np.full(n, np.nan, dtype="float64")
    for i in range(warmup, n):
        window = BarWindow(ts, op, hi, lo, cl, vol, i)
        out[i] = _resolve_target(strategy.on_bar(window), mode, allow_short)
    return out


def classify(
    previous: float | None, target: float, tolerance: float = DEFAULT_TOLERANCE
) -> str:
    """Turn a change in target exposure into a verb.

    `previous is None` means the strategy has not been asked before, and the
    book starts flat, so the comparison is against zero.

    HOLD is deliberately split into HOLD-LONG / HOLD-SHORT / FLAT. Collapsing
    "stay fully long" and "stay in cash" into one word would be the single most
    misleading thing this script could print -- they are opposite instructions.
    """
    prior = 0.0 if previous is None else previous
    delta = target - prior
    if delta > tolerance:
        return BUY
    if delta < -tolerance:
        return SELL
    if target > FLAT_EPSILON:
        return HOLD_LONG
    if target < -FLAT_EPSILON:
        return HOLD_SHORT
    return FLAT


def decide_strategy(
    key: str,
    arrays: dict[str, np.ndarray],
    *,
    mode: Mode = Mode.SPOT,
    allow_short: bool = False,
    tolerance: float = DEFAULT_TOLERANCE,
) -> StrategyDecision:
    """Replay one registered strategy and report its final decision."""
    strategy = build(key)
    n = len(arrays["close"])
    warmup = max(0, int(strategy.warmup_bars()))
    family = FAMILY.get(key, "unclassified")
    params = dict(getattr(strategy, "params", {}))

    # The engine refuses to run at all in this case; reporting a verdict here
    # would be inventing one for a strategy that cannot compute its indicator.
    if n <= warmup:
        return StrategyDecision(
            key=key,
            name=strategy.name,
            family=family,
            action=INSUFFICIENT,
            target=None,
            previous=None,
            warmup=warmup,
            bars=n,
            params=params,
            note=f"needs > {warmup} bars, has {n}",
        )

    targets = replay_targets(strategy, arrays, mode=mode, allow_short=allow_short)
    target = float(targets[-1])
    previous = float(targets[-2]) if n >= warmup + 2 else None
    return StrategyDecision(
        key=key,
        name=strategy.name,
        family=family,
        action=classify(previous, target, tolerance),
        target=target,
        previous=previous,
        warmup=warmup,
        bars=n,
        params=params,
    )


def strategy_decisions(
    arrays: dict[str, np.ndarray],
    *,
    keys: Sequence[str] | None = None,
    mode: Mode = Mode.SPOT,
    allow_short: bool = False,
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[StrategyDecision]:
    """Decisions for every requested registry key, in registry order."""
    wanted = list(REGISTRY) if keys is None else list(keys)
    unknown = [k for k in wanted if k not in REGISTRY]
    if unknown:
        raise KeyError(f"unknown strategies {unknown}; available: {sorted(REGISTRY)}")
    return [
        decide_strategy(
            k, arrays, mode=mode, allow_short=allow_short, tolerance=tolerance
        )
        for k in wanted
    ]


def family_tally(decisions: Sequence[StrategyDecision]) -> dict[str, dict[str, int]]:
    """Action counts grouped by taxonomy family.

    Grouped rather than totalled because a raw total across all 25 reads as a
    vote, and these rules are not independent -- three of them are moving-average
    crossovers in different clothes. Disagreement BETWEEN families (trend long,
    mean-reversion flat) is the part worth looking at.
    """
    out: dict[str, dict[str, int]] = {}
    for d in decisions:
        out.setdefault(d.family, {})
        out[d.family][d.action] = out[d.family].get(d.action, 0) + 1
    return out


# --------------------------------------------------------------------------
# signals -- stateless one-bar rules
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalRule:
    """A one-bar comparison, its rule text, and how to evaluate it."""

    key: str
    rule: str
    evaluate: Callable[[BarWindow], tuple[str, str]]


def _fmt(value: float, places: int = 2) -> str:
    """Format a float, or 'nan' when it is not finite."""
    return "nan" if not np.isfinite(value) else f"{value:,.{places}f}"


def _threshold_reading(
    value: float, low: float, high: float, *, low_is_bullish: bool
) -> str:
    """Reading for an oscillator with a low and a high band."""
    if not np.isfinite(value):
        return UNAVAILABLE
    if value <= low:
        return BULLISH if low_is_bullish else BEARISH
    if value >= high:
        return BEARISH if low_is_bullish else BULLISH
    return NEUTRAL


def _sig_macd(w: BarWindow) -> tuple[str, str]:
    line, signal, hist = ind.macd(w.closes, 12, 26, 9)
    if not (np.isfinite(line) and np.isfinite(signal)):
        return UNAVAILABLE, "insufficient history"
    reading = BULLISH if line > signal else BEARISH
    return reading, f"line {_fmt(line, 3)} vs signal {_fmt(signal, 3)} (hist {_fmt(hist, 3)})"


def _sig_rsi(w: BarWindow) -> tuple[str, str]:
    value = ind.rsi(w.closes, 14)
    return _threshold_reading(value, 30.0, 70.0, low_is_bullish=True), f"RSI {_fmt(value)}"


def _sig_stochastic(w: BarWindow) -> tuple[str, str]:
    k, d = ind.stochastic(w.highs, w.lows, w.closes, 14, 3)
    return (
        _threshold_reading(k, 20.0, 80.0, low_is_bullish=True),
        f"%K {_fmt(k)} / %D {_fmt(d)}",
    )


def _sig_bb_reversion(w: BarWindow) -> tuple[str, str]:
    mid, upper, lower, _ = ind.bollinger(w.closes, 20, 2.0)
    if not np.isfinite(mid):
        return UNAVAILABLE, "insufficient history"
    close = float(w.closes[-1])
    if close < lower:
        reading = BULLISH
    elif close > upper:
        reading = BEARISH
    else:
        reading = NEUTRAL
    return reading, f"close {_fmt(close)} in [{_fmt(lower)}, {_fmt(upper)}] mid {_fmt(mid)}"


def _sig_bb_breakout(w: BarWindow) -> tuple[str, str]:
    mid, upper, lower, bw = ind.bollinger(w.closes, 20, 2.0)
    if not np.isfinite(mid):
        return UNAVAILABLE, "insufficient history"
    close = float(w.closes[-1])
    if close > upper:
        reading = BULLISH
    elif close < lower:
        reading = BEARISH
    else:
        reading = NEUTRAL
    return reading, f"close {_fmt(close)} vs upper {_fmt(upper)} (bandwidth {_fmt(bw, 4)})"


def _sig_keltner(w: BarWindow) -> tuple[str, str]:
    centre = ind.ema(w.closes, 20)
    atr = ind.atr(w.highs, w.lows, w.closes, 14)
    if not (np.isfinite(centre) and np.isfinite(atr)):
        return UNAVAILABLE, "insufficient history"
    close = float(w.closes[-1])
    upper, lower = centre + 2.0 * atr, centre - 2.0 * atr
    if close > upper:
        reading = BULLISH
    elif close < lower:
        reading = BEARISH
    else:
        reading = NEUTRAL
    return reading, f"close {_fmt(close)} vs channel [{_fmt(lower)}, {_fmt(upper)}]"


def _sig_donchian(w: BarWindow) -> tuple[str, str]:
    # The channel excludes the current bar, matching DonchianBreakout: a channel
    # containing today's own high makes the breakout test nearly always false.
    if len(w.closes) < 22:
        return UNAVAILABLE, "insufficient history"
    close = float(w.closes[-1])
    upper = float(np.max(w.highs[-21:-1]))
    lower = float(np.min(w.lows[-11:-1]))
    if close > upper:
        reading = BULLISH
    elif close < lower:
        reading = BEARISH
    else:
        reading = NEUTRAL
    return reading, f"close {_fmt(close)} vs prior 20-high {_fmt(upper)} / 10-low {_fmt(lower)}"


def _sig_sma_regime(w: BarWindow) -> tuple[str, str]:
    ma = ind.sma(w.closes, 200)
    if not np.isfinite(ma):
        return UNAVAILABLE, "needs 200 bars"
    close = float(w.closes[-1])
    return (BULLISH if close > ma else BEARISH), f"close {_fmt(close)} vs SMA200 {_fmt(ma)}"


def _sig_golden_cross(w: BarWindow) -> tuple[str, str]:
    fast, slow = ind.sma(w.closes, 50), ind.sma(w.closes, 200)
    if not (np.isfinite(fast) and np.isfinite(slow)):
        return UNAVAILABLE, "needs 200 bars"
    return (BULLISH if fast > slow else BEARISH), f"SMA50 {_fmt(fast)} vs SMA200 {_fmt(slow)}"


def _sig_ts_momentum(w: BarWindow) -> tuple[str, str]:
    value = ind.roc(w.closes, 90)
    if not np.isfinite(value):
        return UNAVAILABLE, "needs 91 bars"
    return (BULLISH if value > 0 else BEARISH), f"90-bar ROC {value * 100:+.2f}%"


def _sig_vwap(w: BarWindow) -> tuple[str, str]:
    vwap = ind.rolling_vwap(w.highs, w.lows, w.closes, w.volumes, 20)
    if not np.isfinite(vwap):
        return UNAVAILABLE, "insufficient history"
    close = float(w.closes[-1])
    gap = (close / vwap - 1.0) * 100.0 if vwap > 0 else float("nan")
    return (
        (BULLISH if close < vwap else BEARISH),
        f"close {_fmt(close)} vs VWAP20 {_fmt(vwap)} ({gap:+.2f}%)",
    )


def _sig_zscore(w: BarWindow) -> tuple[str, str]:
    z = ind.zscore(w.closes, 20)
    return _threshold_reading(z, -2.0, 2.0, low_is_bullish=True), f"z {_fmt(z, 2)}"


def _sig_adx_di(w: BarWindow) -> tuple[str, str]:
    plus, minus, adx = ind.directional_movement(w.highs, w.lows, w.closes, 14)
    if not np.isfinite(adx):
        return UNAVAILABLE, "needs 43 bars"
    detail = f"+DI {_fmt(plus)} / -DI {_fmt(minus)} / ADX {_fmt(adx)}"
    if adx < 25.0:
        # ADX measures strength, not direction. Below the conventional line
        # there is no trend to be long or short of, so the DI comparison is
        # noise and reporting it as a direction would manufacture one.
        return NEUTRAL, detail + " -- ADX below 25, no trend"
    return (BULLISH if plus > minus else BEARISH), detail


def _sig_ichimoku(w: BarWindow) -> tuple[str, str]:
    # Cloud computed from history ending `displacement` bars back, matching
    # IchimokuCloud. Reading a span computed at the current bar would be reading
    # data from the future -- the classic Ichimoku look-ahead trap.
    displacement = 26
    closes, highs, lows = w.closes, w.highs, w.lows
    if len(closes) < 52 + displacement:
        return UNAVAILABLE, "needs 78 bars"
    cut = len(closes) - displacement
    _, _, span_a, span_b = ind.ichimoku(highs[:cut], lows[:cut], 9, 26, 52)
    if not (np.isfinite(span_a) and np.isfinite(span_b)):
        return UNAVAILABLE, "insufficient history"
    close = float(closes[-1])
    top, bottom = max(span_a, span_b), min(span_a, span_b)
    if close > top:
        reading = BULLISH
    elif close < bottom:
        reading = BEARISH
    else:
        reading = NEUTRAL
    return reading, f"close {_fmt(close)} vs cloud [{_fmt(bottom)}, {_fmt(top)}]"


def _sig_obv(w: BarWindow) -> tuple[str, str]:
    series = ind.obv(w.closes, w.volumes)
    if len(series) < 20:
        return UNAVAILABLE, "insufficient history"
    ma = float(np.mean(series[-20:]))
    now = float(series[-1])
    return (BULLISH if now > ma else BEARISH), f"OBV {now:,.0f} vs its SMA20 {ma:,.0f}"


SIGNAL_RULES: tuple[SignalRule, ...] = (
    SignalRule("macd_cross", "MACD(12,26,9) line above its signal line", _sig_macd),
    SignalRule("rsi_14", "RSI(14) <= 30 oversold / >= 70 overbought", _sig_rsi),
    SignalRule("stochastic_14_3", "%K <= 20 oversold / >= 80 overbought", _sig_stochastic),
    SignalRule(
        "bb_reversion_20_2",
        "close below the lower Bollinger(20, 2) band (reversion reading)",
        _sig_bb_reversion,
    ),
    SignalRule(
        "bb_breakout_20_2",
        "close above the upper Bollinger(20, 2) band (breakout reading)",
        _sig_bb_breakout,
    ),
    SignalRule(
        "keltner_20_14_2", "close outside the EMA20 +/- 2*ATR14 channel", _sig_keltner
    ),
    SignalRule(
        "donchian_20_10",
        "close above the prior 20-bar high / below the prior 10-bar low",
        _sig_donchian,
    ),
    SignalRule("sma_200_regime", "close above its 200-bar SMA", _sig_sma_regime),
    SignalRule("sma_50_200_cross", "SMA50 above SMA200 (golden cross)", _sig_golden_cross),
    SignalRule("ts_momentum_90", "90-bar rate of change above zero", _sig_ts_momentum),
    SignalRule(
        "vwap_20_reversion",
        "close below the 20-bar VWAP (reversion reading)",
        _sig_vwap,
    ),
    SignalRule(
        "zscore_20", "20-bar close z-score <= -2 / >= +2 (reversion reading)", _sig_zscore
    ),
    SignalRule(
        "adx_14_di", "+DI above -DI, but only when ADX(14) >= 25", _sig_adx_di
    ),
    SignalRule(
        "ichimoku_cloud",
        "close above the cloud projected onto this bar from 26 bars back",
        _sig_ichimoku,
    ),
    SignalRule("obv_trend_20", "OBV above its own 20-bar average", _sig_obv),
)


@dataclass
class SignalReading:
    """One evaluated signal rule."""

    key: str
    rule: str
    reading: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form."""
        return {
            "key": self.key,
            "rule": self.rule,
            "reading": self.reading,
            "detail": self.detail,
        }


def signal_readings(window: BarWindow) -> list[SignalReading]:
    """Evaluate every signal rule on the final bar."""
    out = []
    for rule in SIGNAL_RULES:
        reading, detail = rule.evaluate(window)
        out.append(SignalReading(rule.key, rule.rule, reading, detail))
    return out


# --------------------------------------------------------------------------
# indicators -- values, with a reading only where one honestly exists
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class IndicatorRow:
    """One indicator, the `core.indicators` functions behind it, its evaluator.

    Evaluators take the bars-per-year for the series as a second argument even
    when they ignore it, so that an annualised reading cannot silently inherit a
    daily convention on an hourly file.
    """

    key: str
    sources: tuple[str, ...]
    evaluate: Callable[[BarWindow, float], tuple[str, str, str]]


def _ind_price(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    closes = w.closes
    parts = [f"SMA{n} {_fmt(ind.sma(closes, n))}" for n in (20, 50, 200)]
    parts.append(f"EMA20 {_fmt(ind.ema(closes, 20))}")
    return NO_DIRECTION, "; ".join(parts), "a level, not a comparison; see sma_200_regime"


def _ind_rsi(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.rsi(w.closes, 14)
    reading = _threshold_reading(value, 30.0, 70.0, low_is_bullish=True)
    return reading, _fmt(value), "<= 30 oversold / >= 70 overbought"


def _ind_macd(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    line, signal, hist = ind.macd(w.closes, 12, 26, 9)
    value = f"line {_fmt(line, 3)} signal {_fmt(signal, 3)} hist {_fmt(hist, 3)}"
    if not np.isfinite(line) or not np.isfinite(signal):
        return UNAVAILABLE, value, "insufficient history"
    return (BULLISH if line > signal else BEARISH), value, "line vs signal"


def _ind_bollinger(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    mid, upper, lower, bw = ind.bollinger(w.closes, 20, 2.0)
    return (
        NO_DIRECTION,
        f"mid {_fmt(mid)} upper {_fmt(upper)} lower {_fmt(lower)} bw {_fmt(bw, 4)}",
        "bands are levels; bandwidth is a squeeze measure, not a direction",
    )


def _ind_atr(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.atr(w.highs, w.lows, w.closes, 14)
    close = float(w.closes[-1])
    pct = value / close * 100.0 if close > 0 and np.isfinite(value) else float("nan")
    return (
        NO_DIRECTION,
        f"{_fmt(value)} ({_fmt(pct)}% of close)",
        "a volatility magnitude; sizes a position, never picks a side",
    )


def _ind_stochastic(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    k, d = ind.stochastic(w.highs, w.lows, w.closes, 14, 3)
    reading = _threshold_reading(k, 20.0, 80.0, low_is_bullish=True)
    return reading, f"%K {_fmt(k)} %D {_fmt(d)}", "%K <= 20 oversold / >= 80 overbought"


def _ind_vwap(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.rolling_vwap(w.highs, w.lows, w.closes, w.volumes, 20)
    return NO_DIRECTION, _fmt(value), "a level; see vwap_20_reversion"


def _ind_zscore(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.zscore(w.closes, 20)
    reading = _threshold_reading(value, -2.0, 2.0, low_is_bullish=True)
    return reading, _fmt(value, 2), "<= -2 / >= +2, read as reversion"


def _ind_roc(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    values = [ind.roc(w.closes, n) for n in (20, 90)]
    shown = "; ".join(
        f"{n}-bar {v * 100:+.2f}%" if np.isfinite(v) else f"{n}-bar nan"
        for n, v in zip((20, 90), values)
    )
    long_roc = values[-1]
    if not np.isfinite(long_roc):
        return UNAVAILABLE, shown, "needs 91 bars for the 90-bar reading"
    return (
        BULLISH if long_roc > 0 else BEARISH,
        shown,
        "reading is the 90-bar leg, sign only",
    )


def _ind_realised_vol(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.realised_vol(w.closes, 20, ppy)
    return (
        NO_DIRECTION,
        f"{_fmt(value * 100)}% annualised",
        f"a volatility magnitude, annualised at {ppy:,.0f} bars/year",
    )


def _ind_ewma_vol(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.ewma_vol(w.closes, 0.94, ppy)
    return (
        NO_DIRECTION,
        f"{_fmt(value * 100)}% annualised",
        f"RiskMetrics lambda 0.94, annualised at {ppy:,.0f} bars/year",
    )


def _ind_dm(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    plus, minus, adx = ind.directional_movement(w.highs, w.lows, w.closes, 14)
    value = f"+DI {_fmt(plus)} -DI {_fmt(minus)} ADX {_fmt(adx)}"
    if not np.isfinite(adx):
        return UNAVAILABLE, value, "needs 43 bars"
    if adx < 25.0:
        # ADX measures strength, not direction: below the conventional line
        # there is no trend to be long or short of, so the DI comparison is
        # noise and calling it a direction would manufacture one.
        return NEUTRAL, value, "ADX below 25 -- no trend, DI comparison withheld"
    return (BULLISH if plus > minus else BEARISH), value, "+DI vs -DI, gated on ADX >= 25"


def _ind_variance_ratio(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    vr = ind.variance_ratio(w.closes, 250, 5)
    hurst = ind.hurst_from_variance_ratio(vr, 5)
    value = f"VR(250, lag 5) {_fmt(vr, 3)} -> Hurst {_fmt(hurst, 3)}"
    if not np.isfinite(vr):
        return UNAVAILABLE, value, "needs 251 bars"
    regime = "trending" if vr > 1 else "mean-reverting"
    return NO_DIRECTION, value, f"a regime reading ({regime}), not a side"


def _ind_half_life(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    value = ind.ou_half_life(w.closes, 250)
    if value == float("inf"):
        shown = "inf"
        note = "no reversion fitted -- a reversion rule has no thesis here"
    elif not np.isfinite(value):
        shown, note = "nan", "needs 251 bars"
    else:
        shown, note = f"{value:,.1f} bars", "gates reversion rules; not a side"
    return NO_DIRECTION, shown, note


def _ind_ichimoku(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    tenkan, kijun, span_a, span_b = ind.ichimoku(w.highs, w.lows, 9, 26, 52)
    return (
        NO_DIRECTION,
        f"tenkan {_fmt(tenkan)} kijun {_fmt(kijun)} spanA {_fmt(span_a)} spanB {_fmt(span_b)}",
        "computed AT this bar, so the cloud these form belongs 26 bars ahead; "
        "comparing them to today's close reads the future -- see ichimoku_cloud",
    )


def _ind_obv(w: BarWindow, ppy: float) -> tuple[str, str, str]:
    series = ind.obv(w.closes, w.volumes)
    if len(series) < 2:
        return UNAVAILABLE, "nan", "needs 2 bars"
    return (
        NO_DIRECTION,
        f"{float(series[-1]):,.0f}",
        "a cumulative level whose absolute value is arbitrary; see obv_trend_20",
    )


# Every indicator reported, and which `core.indicators` functions each one
# covers. `test_decide.py` asserts this covers the module, so a newly added
# indicator cannot be silently omitted from the readout.
INDICATOR_ROWS: tuple[IndicatorRow, ...] = (
    IndicatorRow("moving_averages", ("sma", "ema"), _ind_price),
    IndicatorRow("rsi_14", ("rsi",), _ind_rsi),
    IndicatorRow("macd_12_26_9", ("macd",), _ind_macd),
    IndicatorRow("bollinger_20_2", ("bollinger",), _ind_bollinger),
    IndicatorRow("atr_14", ("atr",), _ind_atr),
    IndicatorRow("stochastic_14_3", ("stochastic",), _ind_stochastic),
    IndicatorRow("vwap_20", ("rolling_vwap",), _ind_vwap),
    IndicatorRow("zscore_20", ("zscore",), _ind_zscore),
    IndicatorRow("roc", ("roc",), _ind_roc),
    IndicatorRow("realised_vol_20", ("realised_vol",), _ind_realised_vol),
    IndicatorRow("ewma_vol", ("ewma_vol",), _ind_ewma_vol),
    IndicatorRow("directional_movement_14", ("directional_movement",), _ind_dm),
    IndicatorRow(
        "variance_ratio_250",
        ("variance_ratio", "hurst_from_variance_ratio"),
        _ind_variance_ratio,
    ),
    IndicatorRow("ou_half_life_250", ("ou_half_life",), _ind_half_life),
    IndicatorRow("ichimoku_9_26_52", ("ichimoku",), _ind_ichimoku),
    IndicatorRow("obv", ("obv",), _ind_obv),
)

# Public functions in `core.indicators` that are NOT reported, with the reason.
# A helper or a series-returning variant has nothing to print for one bar.
INDICATOR_SKIP: dict[str, str] = {
    "ema_series": "returns a series; the scalar `ema` is reported instead",
    "wilder_smooth": "smoothing primitive used by atr/rsi/adx, not an indicator",
    "true_range": "per-bar series consumed by `atr`",
    "rolling_realised_vol": "vectorised series form of `realised_vol`",
}


@dataclass
class IndicatorReading:
    """One indicator's value, its reading, and why the reading is what it is."""

    key: str
    reading: str
    value: str
    note: str

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe form."""
        return {
            "key": self.key,
            "reading": self.reading,
            "value": self.value,
            "note": self.note,
        }


def indicator_readings(
    window: BarWindow, bars_per_year: float = 365.0
) -> list[IndicatorReading]:
    """Evaluate every indicator row on the final bar."""
    out = []
    for row in INDICATOR_ROWS:
        reading, value, note = row.evaluate(window, bars_per_year)
        out.append(IndicatorReading(row.key, reading, value, note))
    return out


# --------------------------------------------------------------------------
# report assembly and rendering
# --------------------------------------------------------------------------

DISCLAIMER = (
    "NOT INVESTMENT ADVICE. Every line below is a mechanical rule evaluated on "
    "cached history, not a forecast. The rules are heavily correlated -- three "
    "of the strategies are moving-average crossovers wearing different hats -- "
    "so agreement among them is not evidence."
)


def _iso(ts: int) -> str:
    """UTC ISO-8601 stamp for an epoch second."""
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_report(
    arrays: dict[str, np.ndarray],
    *,
    asset: str,
    interval: str,
    source: str,
    checksum: str,
    keys: Sequence[str] | None = None,
    mode: Mode = Mode.SPOT,
    allow_short: bool = False,
    tolerance: float = DEFAULT_TOLERANCE,
    fill_delay: int = 1,
) -> dict[str, Any]:
    """Everything the text and JSON renderers need, computed once."""
    n = len(arrays["close"])
    if n == 0:
        raise ValueError("no bars to decide on")
    window = BarWindow(
        arrays["ts"],
        arrays["open"],
        arrays["high"],
        arrays["low"],
        arrays["close"],
        arrays["volume"],
        n - 1,
    )
    decisions = strategy_decisions(
        arrays, keys=keys, mode=mode, allow_short=allow_short, tolerance=tolerance
    )
    applies_to = (
        "this bar's close (fill_delay=0)"
        if fill_delay == 0
        else f"the open of the bar {fill_delay} interval(s) after the decision bar"
    )
    return {
        "asset": asset,
        "interval": interval,
        "source": source,
        "data_checksum": checksum,
        "bars": n,
        "decision_bar": {
            "index": n - 1,
            "timestamp": int(arrays["ts"][-1]),
            "utc": _iso(int(arrays["ts"][-1])),
            "close": float(arrays["close"][-1]),
        },
        "execution": {
            "mode": str(mode),
            "allow_short": bool(allow_short),
            "exposure_bounds": [
                -1.0 if (allow_short and mode is Mode.PERP) else 0.0,
                1.0,
            ],
            "change_tolerance": tolerance,
            "fill_delay": fill_delay,
            "applies_to": applies_to,
        },
        "disclaimer": DISCLAIMER,
        "strategies": [d.to_dict() for d in decisions],
        "family_tally": family_tally(decisions),
        "signals": [s.to_dict() for s in signal_readings(window)],
        "indicators": [
            i.to_dict() for i in indicator_readings(window, periods_per_year(interval))
        ],
    }


def _table(rows: Sequence[Sequence[str]], headers: Sequence[str]) -> list[str]:
    """Left-aligned fixed-width table as a list of lines."""
    widths = [len(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            widths[j] = max(widths[j], len(cell))
    fmt = lambda cells: "  ".join(  # noqa: E731
        c.ljust(widths[j]) if j < len(cells) - 1 else c for j, c in enumerate(cells)
    )
    out = [fmt(headers), fmt(["-" * w for w in widths])]
    out.extend(fmt(list(r)) for r in rows)
    return out


def render_text(report: dict[str, Any]) -> str:
    """The human-readable readout."""
    bar = report["decision_bar"]
    ex = report["execution"]
    lines = [
        f"Rule readout -- {report['asset']} {report['interval']}",
        "",
        f"  data           {report['source']}  ({report['bars']} bars, "
        f"sha256 {report['data_checksum'][:12]})",
        f"  decision bar   #{bar['index']}  {bar['utc']}  close {bar['close']:,.4f}",
        f"  would execute  at {ex['applies_to']}",
        f"  exposure       mode {ex['mode']}, bounds "
        f"[{ex['exposure_bounds'][0]:+.2f}, {ex['exposure_bounds'][1]:+.2f}]",
        f"  change tol     {ex['change_tolerance']:.3f} of equity -- a smaller move in "
        "target exposure reports as HOLD, not BUY/SELL",
        "",
        report["disclaimer"],
        "",
        "STRATEGIES -- path-dependent; each replayed bar-by-bar from the start of history",
    ]
    rows = [
        [s["key"], s["family"], s["action"], s["detail"], f"{s['warmup_bars']}"]
        for s in report["strategies"]
    ]
    lines.extend(
        "  " + line
        for line in _table(rows, ["strategy", "family", "action", "exposure", "warmup"])
    )

    lines += ["", "  by family (a description of correlated rules, NOT a vote):"]
    for fam in sorted(report["family_tally"]):
        counts = report["family_tally"][fam]
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        lines.append(f"    {fam:<20} {summary}")

    lines += ["", "SIGNALS -- stateless one-bar comparisons"]
    rows = [[s["key"], s["reading"], s["detail"]] for s in report["signals"]]
    lines.extend("  " + line for line in _table(rows, ["signal", "reading", "value"]))
    lines += ["", "  rules (the same fact reads opposite ways to a reversion and a breakout):"]
    lines.extend(f"    {s['key']:<20} {s['rule']}" for s in report["signals"])

    lines += ["", "INDICATORS -- values; a reading only where the indicator has one"]
    rows = [[i["key"], i["reading"], i["value"]] for i in report["indicators"]]
    lines.extend("  " + line for line in _table(rows, ["indicator", "reading", "value"]))
    lines += ["", "  notes:"]
    lines.extend(f"    {i['key']:<24} {i['note']}" for i in report["indicators"])
    lines.append("")
    return "\n".join(lines)


def default_data_path(asset: str, interval: str) -> Path:
    """Conventional cache location, matching what `core.fetch` writes."""
    return REPO / "data" / f"{asset}_{interval}.csv"


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    ap = argparse.ArgumentParser(
        prog="python3 research/decide.py",
        description=(
            "Print what every registered strategy, signal and indicator says "
            "about the last bar of a cached series. Research only -- NOT "
            "investment advice."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--asset", default="SOL", help="base asset symbol")
    ap.add_argument(
        "--interval", default="1d", choices=sorted(INTERVAL_SECONDS), help="bar interval"
    )
    ap.add_argument(
        "--data", default=None, help="path to a cached CSV (default: data/<asset>_<interval>.csv)"
    )
    ap.add_argument("--start", default=None, help="inclusive UTC start date")
    ap.add_argument(
        "--end",
        default=None,
        help="inclusive UTC end date; the last bar in range becomes the decision bar",
    )
    ap.add_argument(
        "--strategy",
        action="append",
        default=None,
        help=f"repeatable; default is every registered strategy: {sorted(REGISTRY)}",
    )
    ap.add_argument(
        "--mode", default="spot", choices=[m.value for m in Mode], help="exposure mode"
    )
    ap.add_argument(
        "--allow-short", action="store_true", help="permit short exposure (perp only)"
    )
    ap.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="minimum change in target exposure reported as BUY/SELL",
    )
    ap.add_argument(
        "--fill-delay",
        type=int,
        default=1,
        help="bars between a decision and its fill; affects the header only",
    )
    ap.add_argument("--allow-gaps", action="store_true", help="accept an incomplete series")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    ap.add_argument("--out", default=None, help="write the output to this file as well")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    path = Path(args.data) if args.data else default_data_path(args.asset, args.interval)
    loader = CsvLoader(path, allow_gaps=args.allow_gaps)
    try:
        frame = loader.load(args.asset, args.start, args.end, args.interval)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = build_report(
        frame_to_arrays(frame),
        asset=args.asset,
        interval=args.interval,
        source=str(path),
        checksum=checksum_frame(frame),
        keys=args.strategy,
        mode=Mode(args.mode),
        allow_short=args.allow_short,
        tolerance=args.tolerance,
        fill_delay=args.fill_delay,
    )
    text = json.dumps(report, indent=2, sort_keys=True) if args.json else render_text(report)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

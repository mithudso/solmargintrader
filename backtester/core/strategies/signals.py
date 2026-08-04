"""Indicator-driven strategies.

Each class is a thin wrapper over `core.indicators`: the indicator layer does
the arithmetic, the class turns a value into a target exposure. Grouped in one
module because they are one-screen each and share the same imports; the registry
treats them exactly like separately-filed strategies.

Convention followed throughout: `on_bar` returns a target exposure for the NEXT
bar in [-1, 1], and reads history only through the `BarWindow` it is handed.
Stateful classes (those with a `_holding` flag) derive that state from past
decisions and past bars only, never from a future price.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import indicators as ind
from ..types import BarWindow


class MacdCross:
    """Trend/momentum. Long while the MACD line is above its signal line."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        if not 0 < fast < slow:
            raise ValueError("require 0 < fast < slow")
        self.fast, self.slow, self.signal = fast, slow, signal
        self.name = f"macd_{fast}_{slow}_{signal}"
        self.params: dict[str, Any] = {"fast": fast, "slow": slow, "signal": signal}

    def warmup_bars(self) -> int:
        """Slow EMA plus the signal EMA of the MACD line."""
        return self.slow + self.signal * ind.EMA_WARMUP_MULTIPLE

    def on_bar(self, history: BarWindow) -> float:
        """Long on a bullish MACD/signal relationship."""
        line, sig, _ = ind.macd(history.closes, self.fast, self.slow, self.signal)
        if not np.isfinite(line) or not np.isfinite(sig):
            return 0.0
        return 1.0 if line > sig else 0.0


class BollingerReversion:
    """Mean-reversion. Buy a close below the lower band, exit back at the mid."""

    def __init__(self, window: int = 20, num_std: float = 2.0) -> None:
        self.window, self.num_std = window, num_std
        self._holding = False
        self.name = f"bb_reversion_{window}_{num_std:g}"
        self.params: dict[str, Any] = {"window": window, "num_std": num_std}

    def warmup_bars(self) -> int:
        """One full band window."""
        return self.window

    def on_bar(self, history: BarWindow) -> float:
        """Enter below the lower band; exit on reversion to the mid."""
        closes = history.closes
        mid, _, lower, _ = ind.bollinger(closes, self.window, self.num_std)
        if not np.isfinite(mid):
            return 0.0
        close = float(closes[-1])
        if not self._holding and close < lower:
            self._holding = True
        elif self._holding and close > mid:
            self._holding = False
        return 1.0 if self._holding else 0.0


class BollingerBreakout:
    """Volatility breakout. Long a close above the upper band.

    Optional squeeze filter: only act when bandwidth is in the lowest quantile
    of its recent range, which is the classic "expansion follows contraction"
    setup. Without the filter this is a momentum entry that buys strength.
    """

    def __init__(
        self,
        window: int = 20,
        num_std: float = 2.0,
        squeeze_lookback: int = 0,
        squeeze_quantile: float = 0.25,
    ) -> None:
        self.window, self.num_std = window, num_std
        self.squeeze_lookback = squeeze_lookback
        self.squeeze_quantile = squeeze_quantile
        self._holding = False
        self.name = f"bb_breakout_{window}_{num_std:g}" + (
            f"_sq{squeeze_lookback}" if squeeze_lookback else ""
        )
        self.params: dict[str, Any] = {
            "window": window,
            "num_std": num_std,
            "squeeze_lookback": squeeze_lookback,
            "squeeze_quantile": squeeze_quantile,
        }

    def warmup_bars(self) -> int:
        """Band window plus any squeeze history."""
        return self.window + self.squeeze_lookback

    def on_bar(self, history: BarWindow) -> float:
        """Long above the upper band; exit back below the mid."""
        closes = history.closes
        mid, upper, _, bw = ind.bollinger(closes, self.window, self.num_std)
        if not np.isfinite(mid):
            return 0.0
        close = float(closes[-1])

        squeezed = True
        if self.squeeze_lookback > 0:
            hist = np.array(
                [
                    ind.bollinger(closes[: len(closes) - k], self.window, self.num_std)[3]
                    for k in range(self.squeeze_lookback)
                ],
                dtype="float64",
            )
            hist = hist[np.isfinite(hist)]
            if hist.size:
                squeezed = bw <= float(np.quantile(hist, self.squeeze_quantile))

        if not self._holding and close > upper and squeezed:
            self._holding = True
        elif self._holding and close < mid:
            self._holding = False
        return 1.0 if self._holding else 0.0


class KeltnerBreakout:
    """Volatility breakout on an ATR channel around an EMA.

    Differs from Bollinger by using ATR (true range, so it sees gaps) instead
    of close-to-close stdev. That makes it less prone to the Bollinger failure
    mode where a gap compresses stdev while actual risk rises.
    """

    def __init__(self, ema_span: int = 20, atr_period: int = 14, mult: float = 2.0) -> None:
        self.ema_span, self.atr_period, self.mult = ema_span, atr_period, mult
        self._holding = False
        self.name = f"keltner_{ema_span}_{atr_period}_{mult:g}"
        self.params: dict[str, Any] = {
            "ema_span": ema_span,
            "atr_period": atr_period,
            "mult": mult,
        }

    def warmup_bars(self) -> int:
        """Whichever of the EMA or ATR recursion needs more history."""
        return (
            max(self.ema_span, self.atr_period) * ind.EMA_WARMUP_MULTIPLE + 1
        )

    def on_bar(self, history: BarWindow) -> float:
        """Long above the upper ATR channel; exit below the centre line."""
        closes, highs, lows = history.closes, history.highs, history.lows
        centre = ind.ema(closes, self.ema_span)
        a = ind.atr(highs, lows, closes, self.atr_period)
        if not np.isfinite(centre) or not np.isfinite(a):
            return 0.0
        close = float(closes[-1])
        if not self._holding and close > centre + self.mult * a:
            self._holding = True
        elif self._holding and close < centre:
            self._holding = False
        return 1.0 if self._holding else 0.0


class TsMomentum:
    """Time-series momentum: long when trailing return over `window` is positive.

    The Moskowitz/Ooi/Pedersen form -- the sign of a past return predicting the
    next period. Distinct from cross-sectional momentum, which ranks assets
    against each other and needs a universe this dataset does not have.
    """

    def __init__(self, window: int = 60, threshold: float = 0.0) -> None:
        if window < 1:
            raise ValueError("window must be >= 1")
        self.window, self.threshold = window, threshold
        self.name = f"ts_momentum_{window}"
        self.params: dict[str, Any] = {"window": window, "threshold": threshold}

    def warmup_bars(self) -> int:
        """One lookback plus the base bar."""
        return self.window + 1

    def on_bar(self, history: BarWindow) -> float:
        """Long while trailing return exceeds the threshold."""
        r = ind.roc(history.closes, self.window)
        if not np.isfinite(r):
            return 0.0
        return 1.0 if r > self.threshold else 0.0


class StochasticOversold:
    """Oscillator mean-reversion with a turn-up confirmation.

    Requires %K below `oversold` AND %K above %D, i.e. oversold *and already
    turning*. Buying oversold alone is the classic way to be run over in a
    downtrend; demanding the crossover costs some entries and avoids some of it.
    """

    def __init__(
        self, k_period: int = 14, d_period: int = 3,
        oversold: float = 20.0, exit_level: float = 80.0,
    ) -> None:
        self.k_period, self.d_period = k_period, d_period
        self.oversold, self.exit_level = oversold, exit_level
        self._holding = False
        self.name = f"stoch_{k_period}_{d_period}"
        self.params: dict[str, Any] = {
            "k_period": k_period,
            "d_period": d_period,
            "oversold": oversold,
            "exit_level": exit_level,
        }

    def warmup_bars(self) -> int:
        """%K window plus the %D smoothing."""
        return self.k_period + self.d_period + 1

    def on_bar(self, history: BarWindow) -> float:
        """Long when oversold and turning up; exit when overbought."""
        k, d = ind.stochastic(
            history.highs, history.lows, history.closes, self.k_period, self.d_period
        )
        if not np.isfinite(k) or not np.isfinite(d):
            return 0.0
        if not self._holding and k < self.oversold and k > d:
            self._holding = True
        elif self._holding and k > self.exit_level:
            self._holding = False
        return 1.0 if self._holding else 0.0


class VwapReversion:
    """Buy a discount to rolling VWAP, exit on reversion to it.

    Rolling rather than session-anchored: crypto trades continuously, so there
    is no session open to anchor to. That makes this a short-horizon
    fair-value-deviation signal rather than the intraday execution benchmark
    VWAP normally serves as.
    """

    def __init__(self, window: int = 20, entry_discount: float = 0.02) -> None:
        self.window, self.entry_discount = window, entry_discount
        self._holding = False
        self.name = f"vwap_reversion_{window}_{entry_discount:g}"
        self.params: dict[str, Any] = {
            "window": window,
            "entry_discount": entry_discount,
        }

    def warmup_bars(self) -> int:
        """One VWAP window."""
        return self.window

    def on_bar(self, history: BarWindow) -> float:
        """Enter below VWAP by the discount; exit at or above VWAP."""
        v = ind.rolling_vwap(
            history.highs, history.lows, history.closes, history.volumes, self.window
        )
        if not np.isfinite(v) or v <= 0:
            return 0.0
        close = float(history.closes[-1])
        if not self._holding and close < v * (1.0 - self.entry_discount):
            self._holding = True
        elif self._holding and close >= v:
            self._holding = False
        return 1.0 if self._holding else 0.0


class ObvTrend:
    """Volume-flow confirmation: long while OBV is above its own moving average.

    Price-blind by construction -- it reads accumulation/distribution, so it is
    a natural partner for a price-based trend signal rather than a standalone.
    """

    def __init__(self, ma_window: int = 20) -> None:
        self.ma_window = ma_window
        self.name = f"obv_trend_{ma_window}"
        self.params: dict[str, Any] = {"ma_window": ma_window}

    def warmup_bars(self) -> int:
        """OBV needs the MA window plus one differencing bar."""
        return self.ma_window + 2

    def on_bar(self, history: BarWindow) -> float:
        """Long when cumulative signed volume trends up."""
        series = ind.obv(history.closes, history.volumes)
        if len(series) < self.ma_window:
            return 0.0
        ma = float(np.mean(series[-self.ma_window :]))
        return 1.0 if float(series[-1]) > ma else 0.0


class ZScoreReversion:
    """Mean-reversion on the z-score of price against its trailing mean."""

    def __init__(self, window: int = 20, entry_z: float = -2.0, exit_z: float = 0.0) -> None:
        if entry_z >= exit_z:
            raise ValueError("entry_z must be below exit_z for a long-reversion rule")
        self.window, self.entry_z, self.exit_z = window, entry_z, exit_z
        self._holding = False
        self.name = f"zscore_{window}_{entry_z:g}"
        self.params: dict[str, Any] = {
            "window": window,
            "entry_z": entry_z,
            "exit_z": exit_z,
        }

    def warmup_bars(self) -> int:
        """One z-score window."""
        return self.window

    def on_bar(self, history: BarWindow) -> float:
        """Enter when stretched below the mean; exit on reversion."""
        z = ind.zscore(history.closes, self.window)
        if not np.isfinite(z):
            return 0.0
        if not self._holding and z <= self.entry_z:
            self._holding = True
        elif self._holding and z >= self.exit_z:
            self._holding = False
        return 1.0 if self._holding else 0.0


class Sma200Regime:
    """Regime filter: fully long above the slow MA, flat below it.

    The single most-cited "stay out of the worst drawdowns" overlay. Useful
    mainly as a baseline to test whether more elaborate signals add anything
    over a one-line regime rule.
    """

    def __init__(self, window: int = 200) -> None:
        self.window = window
        self.name = f"sma_regime_{window}"
        self.params: dict[str, Any] = {"window": window}

    def warmup_bars(self) -> int:
        """One MA window."""
        return self.window

    def on_bar(self, history: BarWindow) -> float:
        """Long while price is above the slow average."""
        closes = history.closes
        ma = ind.sma(closes, self.window)
        if not np.isfinite(ma):
            return 0.0
        return 1.0 if float(closes[-1]) > ma else 0.0


class VolTargetTrend:
    """Trend entry sized inversely to realised volatility.

    Continuous exposure rather than binary: when the trend filter is on,
    exposure is `target_vol / realised_vol` capped at 1. This is a risk overlay
    more than a signal -- it changes the shape of the equity curve rather than
    the direction of the bet, which is why it is worth testing as a wrapper on
    other signals.
    """

    def __init__(
        self, trend_window: int = 100, vol_window: int = 20, target_vol: float = 0.60
    ) -> None:
        if target_vol <= 0:
            raise ValueError("target_vol must be positive")
        self.trend_window, self.vol_window = trend_window, vol_window
        self.target_vol = target_vol
        self.name = f"voltarget_{trend_window}_{vol_window}_{target_vol:g}"
        self.params: dict[str, Any] = {
            "trend_window": trend_window,
            "vol_window": vol_window,
            "target_vol": target_vol,
        }

    def warmup_bars(self) -> int:
        """Whichever of the trend or vol window is longer."""
        return max(self.trend_window, self.vol_window) + 1

    def on_bar(self, history: BarWindow) -> float:
        """Scaled long exposure while the trend filter is on."""
        closes = history.closes
        ma = ind.sma(closes, self.trend_window)
        if not np.isfinite(ma) or float(closes[-1]) <= ma:
            return 0.0
        vol = ind.realised_vol(closes, self.vol_window)
        if not np.isfinite(vol) or vol <= 1e-9:
            return 1.0
        return float(min(1.0, self.target_vol / vol))


class GridLong:
    """Long-only grid: accumulate in steps as price falls below an anchor.

    Exposure is a staircase in the *distance below* a rolling anchor, so it
    scales into weakness. Included because it is heavily used in crypto and
    fails in a characteristic, instructive way: it is short volatility and long
    the assumption of a range, so a sustained trend down maximises exposure at
    exactly the wrong time.
    """

    def __init__(self, anchor_window: int = 50, levels: int = 4, step: float = 0.05) -> None:
        if levels < 1 or step <= 0:
            raise ValueError("levels must be >= 1 and step must be positive")
        self.anchor_window, self.levels, self.step = anchor_window, levels, step
        self.name = f"grid_{anchor_window}_{levels}_{step:g}"
        self.params: dict[str, Any] = {
            "anchor_window": anchor_window,
            "levels": levels,
            "step": step,
        }

    def warmup_bars(self) -> int:
        """One anchor window."""
        return self.anchor_window

    def on_bar(self, history: BarWindow) -> float:
        """Exposure rises one rung per `step` below the rolling anchor."""
        closes = history.closes
        anchor = ind.sma(closes, self.anchor_window)
        if not np.isfinite(anchor) or anchor <= 0:
            return 0.0
        drawdown = 1.0 - float(closes[-1]) / anchor
        if drawdown <= 0:
            return 0.0
        rungs = min(int(drawdown / self.step) + 1, self.levels)
        return float(rungs) / float(self.levels)

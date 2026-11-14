"""Five textbook mechanisms that the cited trading guides name and the registry lacked.

Source: `tradingstrategyresults.json` (a catalogue of strategies and indicators from
public trading guides). Checked against the registry, five OHLCV-only mechanisms had
no implementation: dollar-cost averaging, the EMA / golden-cross crossover, the PPO,
Fibonacci retracement entries, and the multi-indicator swing-trade confluence.

Each class is the simplest honest version of its mechanism, in the same convention as
`signals.py`: `on_bar` returns a target exposure for the NEXT bar and reads history
only through the `BarWindow` it is handed. Stateful classes keep a `_holding` flag
derived from past decisions and past bars only.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import indicators as ind
from ..types import BarWindow


class DollarCostAveraging:
    """Deploy a fixed budget in equal instalments at a fixed bar interval.

    Target exposure is the cumulative fraction of the budget deployed so far:
    `min(1, instalments_done / instalments)`. That is an approximation of true DCA,
    which buys equal CASH amounts: here an instalment is worth a fixed fraction of
    equity, so the invested share drifts with price between instalments. The
    approximation is the engine's, not a choice -- it takes exposure targets, not
    cash orders -- and it matters little against the real effect, which is that a
    ramp lags buy-and-hold in any sustained uptrend.

    The bar count comes from `len(history.closes)`, i.e. bars seen so far, never
    from a future bar.
    """

    def __init__(self, instalments: int = 10, interval: int = 7) -> None:
        if instalments < 1 or interval < 1:
            raise ValueError("instalments and interval must be >= 1")
        self.instalments, self.interval = instalments, interval
        self.name = f"dca_{instalments}x{interval}"
        self.params: dict[str, Any] = {"instalments": instalments, "interval": interval}

    def warmup_bars(self) -> int:
        """No indicator: the first instalment goes in on the first tradable bar."""
        return 0

    def on_bar(self, history: BarWindow) -> float:
        """Fraction of the budget deployed after this many bars."""
        done = (len(history.closes) - 1) // self.interval + 1
        return min(1.0, done / self.instalments)


class EmaCrossover:
    """Long while the fast EMA is above the slow EMA (the "golden cross" at 50/200).

    The EMA twin of `MaCrossover`: same rule, but recent closes weigh more, so it
    turns earlier and whipsaws more. Kept separate rather than a flag on
    `MaCrossover` so each has its own stable name in sweep output.
    """

    def __init__(self, fast: int = 50, slow: int = 200) -> None:
        if fast < 1 or slow < 1:
            raise ValueError("EMA spans must be >= 1")
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be shorter than slow ({slow})")
        self.fast, self.slow = fast, slow
        self.name = f"ema_crossover_{fast}_{slow}"
        self.params: dict[str, Any] = {"fast": fast, "slow": slow}

    def warmup_bars(self) -> int:
        """The slow EMA needs `slow` closes to seed."""
        return self.slow

    def on_bar(self, history: BarWindow) -> float:
        """Long while fast EMA > slow EMA."""
        closes = history.closes
        fast_ma = ind.ema(closes, self.fast)
        slow_ma = ind.ema(closes, self.slow)
        if not (np.isfinite(fast_ma) and np.isfinite(slow_ma)):
            return 0.0
        return 1.0 if fast_ma > slow_ma else 0.0


class PpoCross:
    """Long while the PPO line is above its signal line.

    Algebraically MACD divided by the slow EMA, so on one asset over a short span the
    two cross at almost the same bars. The card records that and the redundancy
    measurement is `research/signal_redundancy.py`'s job, not an assumption here.
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9) -> None:
        if not 0 < fast < slow or signal < 1:
            raise ValueError("require 0 < fast < slow and signal >= 1")
        self.fast, self.slow, self.signal = fast, slow, signal
        self.name = f"ppo_{fast}_{slow}_{signal}"
        self.params: dict[str, Any] = {"fast": fast, "slow": slow, "signal": signal}

    def warmup_bars(self) -> int:
        """Slow EMA plus the signal EMA of the PPO line (same shape as MACD)."""
        return self.slow + self.signal + 2

    def on_bar(self, history: BarWindow) -> float:
        """Long while PPO > its signal line."""
        line, sig, _ = ind.ppo(history.closes, self.fast, self.slow, self.signal)
        if not (np.isfinite(line) and np.isfinite(sig)):
            return 0.0
        return 1.0 if line > sig else 0.0


class FibRetracement:
    """Buy a pullback into the Fibonacci zone of an up-swing, once it turns up.

    Swing: highest high and lowest low of the last `lookback` bars, valid only when
    the low came BEFORE the high (an up-swing) and the range is non-zero.

    Enter: close at or below the `entry_ratio` retracement, at or above the
    `invalid_ratio` retracement, and above the previous close (the turn has begun;
    buying a falling knife into a level is the usual way this idea loses).
    Exit: the swing high is retaken (target reached) or close breaks below the
    `invalid_ratio` level (the structure failed).
    """

    def __init__(
        self, lookback: int = 60, entry_ratio: float = 0.382, invalid_ratio: float = 0.786
    ) -> None:
        if lookback < 5:
            raise ValueError("lookback must be >= 5")
        if not 0.0 < entry_ratio < invalid_ratio < 1.0:
            raise ValueError("require 0 < entry_ratio < invalid_ratio < 1")
        self.lookback = lookback
        self.entry_ratio, self.invalid_ratio = entry_ratio, invalid_ratio
        self._holding = False
        self._target = self._invalid = None
        self.name = f"fib_{lookback}_{entry_ratio:g}_{invalid_ratio:g}"
        self.params: dict[str, Any] = {
            "lookback": lookback,
            "entry_ratio": entry_ratio,
            "invalid_ratio": invalid_ratio,
        }

    def warmup_bars(self) -> int:
        """One full swing window plus the previous close."""
        return self.lookback + 1

    def on_bar(self, history: BarWindow) -> float:
        """Long inside the retracement zone of an up-swing after a turn up."""
        highs, lows, closes = history.highs, history.lows, history.closes
        if self._holding:
            if closes[-1] >= self._target or closes[-1] < self._invalid:
                self._holding = False
            return 1.0 if self._holding else 0.0
        if len(closes) < self.lookback + 1:
            return 0.0
        h = highs[-self.lookback :]
        lo = lows[-self.lookback :]
        hi_i, lo_i = int(np.argmax(h)), int(np.argmin(lo))
        swing_hi, swing_lo = float(h[hi_i]), float(lo[lo_i])
        close, prev = float(closes[-1]), float(closes[-2])
        if lo_i >= hi_i or swing_hi - swing_lo <= 1e-12:
            self._holding = False
            return 0.0
        entry = ind.fib_level(swing_hi, swing_lo, self.entry_ratio)
        invalid = ind.fib_level(swing_hi, swing_lo, self.invalid_ratio)
        if invalid <= close <= entry and close > prev:
            self._holding = True
            self._target, self._invalid = swing_hi, invalid
        return 1.0 if self._holding else 0.0


class SwingConfluence:
    """Swing trade: breakout above resistance, confirmed by several indicators.

    The guides describe a swing entry as a breakout confirmed by SMA, MACD, RSI or
    volume. Here: close above the prior `breakout` bars' high (resistance), AND at
    least `min_confirms` of four confirmations -- close above its SMA, MACD histogram
    positive, RSI above 50, OBV above its own average. Exit when close falls below
    the prior `exit_lookback` bars' low (the swing's structure weakens).

    The resistance level excludes the current bar, otherwise a close could never
    exceed a high that already contains it.
    """

    def __init__(
        self,
        breakout: int = 20,
        exit_lookback: int = 10,
        ma_window: int = 50,
        min_confirms: int = 2,
    ) -> None:
        if breakout < 2 or exit_lookback < 2 or ma_window < 2:
            raise ValueError("windows must be >= 2")
        if not 1 <= min_confirms <= 4:
            raise ValueError("min_confirms must be between 1 and 4")
        self.breakout, self.exit_lookback = breakout, exit_lookback
        self.ma_window, self.min_confirms = ma_window, min_confirms
        self._holding = False
        self.name = f"swing_{breakout}_{exit_lookback}_{ma_window}_{min_confirms}"
        self.params: dict[str, Any] = {
            "breakout": breakout,
            "exit_lookback": exit_lookback,
            "ma_window": ma_window,
            "min_confirms": min_confirms,
        }

    def warmup_bars(self) -> int:
        """Longest of the breakout window, exit window, SMA and the MACD span."""
        return max(self.breakout + 1, self.exit_lookback + 1, self.ma_window, 36)

    def _confirmations(self, history: BarWindow) -> int:
        closes = history.closes
        n = 0
        sma = ind.sma(closes, self.ma_window)
        if np.isfinite(sma) and float(closes[-1]) > sma:
            n += 1
        _, _, hist = ind.macd(closes)
        if np.isfinite(hist) and hist > 0:
            n += 1
        if ind.rsi(closes) > 50.0:
            n += 1
        flow = ind.obv(closes, history.volumes)
        if len(flow) >= 20 and float(flow[-1]) > float(np.mean(flow[-20:])):
            n += 1
        return n

    def on_bar(self, history: BarWindow) -> float:
        """Long after a confirmed breakout; flat once the swing low breaks."""
        highs, lows, closes = history.highs, history.lows, history.closes
        if len(closes) < self.warmup_bars():
            return 0.0
        close = float(closes[-1])
        if self._holding:
            if close < float(np.min(lows[-self.exit_lookback - 1 : -1])):
                self._holding = False
        elif close > float(np.max(highs[-self.breakout - 1 : -1])):
            if self._confirmations(history) >= self.min_confirms:
                self._holding = True
        return 1.0 if self._holding else 0.0

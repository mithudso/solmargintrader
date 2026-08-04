"""The nine mechanisms that needed code rather than data.

Every strategy here was a `spec-only` card whose stated gap was "implementable
now — needs code, not data". Each one is deliberately the *simplest honest*
version of its mechanism, because the point of implementing them was to measure
them, and a nine-parameter implementation measured on one split tells you less
than a three-parameter one.

Two of them are **regime selectors** rather than directional signals
(`HurstRegimeSwitch`, `VolRegimeSwitch`). They matter more than their measured
numbers suggest: every other strategy in this package bets on either trend or
reversion being present, and none of them checks which one actually is. That is
the failure that dominates all sixteen previously-measured results.

Where a card's proposed parameters differed from what a working implementation
needs, the card was updated to match the code — not the other way round. The
drift tests in `tests/test_strategy_cards.py` enforce that they agree.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from .. import indicators as ind
from ..types import BarWindow


class DualMomentum:
    """Trailing return over the formation window, **excluding** the most recent bars.

    The 12-1 construction is standard in the momentum literature because the most
    recent period tends to *reverse*; including it dilutes the signal. This is the
    cheapest available upgrade to `TsMomentum`.
    """

    def __init__(self, formation: int = 12, skip: int = 1) -> None:
        if formation < 2 or skip < 0 or skip >= formation:
            raise ValueError("need formation >= 2 and 0 <= skip < formation")
        self.formation, self.skip = formation, skip
        self.name = f"dual_momentum_{formation}_{skip}"
        self.params: dict[str, Any] = {"formation": formation, "skip": skip}

    def warmup_bars(self) -> int:
        return self.formation + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        if len(closes) < self.formation + 1:
            return 0.0
        # The skipped tail is excluded from BOTH ends of the return, so this is the
        # return from t-formation to t-skip, not a shifted full-window return.
        recent = closes[-1 - self.skip]
        older = closes[-1 - self.formation]
        if older <= 0:
            return 0.0
        return 1.0 if recent / older - 1.0 > 0.0 else 0.0


class AdxFilteredTrend:
    """Long only while a directional trend is both present and up.

    Every trend strategy in this package fails the same way — chop — and ADX is
    the conventional measure of whether a trend exists at all. So this gates
    direction (`+DI > -DI`) on strength (`ADX > threshold`) rather than adding
    another directional opinion.
    """

    def __init__(self, adx_period: int = 14, adx_threshold: float = 25.0) -> None:
        if adx_period < 2 or adx_threshold < 0:
            raise ValueError("need adx_period >= 2 and adx_threshold >= 0")
        self.adx_period, self.adx_threshold = adx_period, adx_threshold
        self.name = f"adx_trend_{adx_period}_{adx_threshold:g}"
        self.params: dict[str, Any] = {
            "adx_period": adx_period,
            "adx_threshold": adx_threshold,
        }

    def warmup_bars(self) -> int:
        # ADX is a Wilder smoothing of DX, itself built from smoothed DM and ATR:
        # three nested recursions, so three periods of history before it settles.
        return 3 * self.adx_period + 1

    def on_bar(self, history: BarWindow) -> float:
        plus_di, minus_di, adx = ind.directional_movement(
            history.highs, history.lows, history.closes, self.adx_period
        )
        if not np.isfinite(adx):
            return 0.0
        if adx <= self.adx_threshold:
            return 0.0
        return 1.0 if plus_di > minus_di else 0.0


class MaRibbon:
    """Exposure scales with the fraction of adjacent MA pairs in correct order.

    A graded version of `MaCrossover`, which softens the all-or-nothing whipsaw of
    a single crossing. Honestly the weakest mechanism in this file: more knobs on
    an idea already measured as regime-dependent is not obviously progress.
    """

    def __init__(self, windows: int = 5, base: int = 10) -> None:
        if windows < 2 or base < 2:
            raise ValueError("need windows >= 2 and base >= 2")
        self.windows, self.base = windows, base
        self.name = f"ma_ribbon_{windows}x{base}"
        self.params: dict[str, Any] = {"windows": windows, "base": base}

    @property
    def _spans(self) -> list[int]:
        return [self.base * (i + 1) for i in range(self.windows)]

    def warmup_bars(self) -> int:
        return self._spans[-1]

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        spans = self._spans
        if len(closes) < spans[-1]:
            return 0.0
        means = [ind.sma(closes, s) for s in spans]
        if not all(np.isfinite(m) for m in means):
            return 0.0
        ordered = sum(1 for a, b in zip(means, means[1:]) if a > b)
        return ordered / (len(spans) - 1)


class IchimokuCloud:
    """Long while price is above the cloud that was projected onto this bar.

    The displacement is the whole trap. `SenkouA`/`SenkouB` are conventionally
    *plotted* `displacement` bars into the future, so the cloud sitting at the
    current bar was computed `displacement` bars **ago**. Reading a value computed
    at the current bar as if it were the current cloud reads future data.

    This implementation therefore computes the cloud from history ending
    `displacement` bars back and compares it against today's close — the only
    ordering that is both faithful to the indicator and free of look-ahead.
    """

    def __init__(
        self,
        tenkan: int = 9,
        kijun: int = 26,
        senkou_b: int = 52,
        displacement: int = 26,
    ) -> None:
        if min(tenkan, kijun, senkou_b, displacement) < 1:
            raise ValueError("every Ichimoku period must be >= 1")
        self.tenkan, self.kijun = tenkan, kijun
        self.senkou_b, self.displacement = senkou_b, displacement
        self.name = f"ichimoku_{tenkan}_{kijun}_{senkou_b}"
        self.params: dict[str, Any] = {
            "tenkan": tenkan,
            "kijun": kijun,
            "senkou_b": senkou_b,
            "displacement": displacement,
        }

    def warmup_bars(self) -> int:
        return self.senkou_b + self.displacement

    def on_bar(self, history: BarWindow) -> float:
        highs, lows, closes = history.highs, history.lows, history.closes
        need = self.senkou_b + self.displacement
        if len(closes) < need:
            return 0.0
        # Truncate to what was visible `displacement` bars ago; that is the cloud
        # now overhead. Slicing history rather than shifting a plotted series is
        # what keeps the look-ahead impossible instead of merely unlikely.
        cut = len(closes) - self.displacement
        _, _, span_a, span_b = ind.ichimoku(
            highs[:cut], lows[:cut], self.tenkan, self.kijun, self.senkou_b
        )
        if not (np.isfinite(span_a) and np.isfinite(span_b)):
            return 0.0
        return 1.0 if closes[-1] > max(span_a, span_b) else 0.0


class OuHalfLifeReversion:
    """Z-score reversion with an Ornstein-Uhlenbeck hold cap and a screening rule.

    This is the named gap in both `BollingerReversion` and `ZScoreReversion`:
    neither bounds the hold, so a trade whose thesis has not played out becomes an
    unbounded bet that the mean will return. Two additions fix that:

    * **Screening.** If the fitted half-life exceeds `max_half_life_bars`, or the
      series shows no reversion at all, take no position. That rule would have
      disqualified raw SOL price before either reversion strategy was run.
    * **Hold cap.** Exit unconditionally after `hold_multiple x half_life` bars,
      whatever the signal says.
    """

    def __init__(
        self,
        fit_window: int = 250,
        entry_z: float = -2.0,
        hold_multiple: float = 2.5,
        max_half_life_bars: int = 30,
    ) -> None:
        if fit_window < 20 or hold_multiple <= 0 or max_half_life_bars < 1:
            raise ValueError("need fit_window >= 20, hold_multiple > 0, max_half_life >= 1")
        self.fit_window = fit_window
        self.entry_z = entry_z
        self.hold_multiple = hold_multiple
        self.max_half_life_bars = max_half_life_bars
        self.name = f"ou_reversion_{fit_window}_{hold_multiple:g}"
        self.params: dict[str, Any] = {
            "fit_window": fit_window,
            "entry_z": entry_z,
            "hold_multiple": hold_multiple,
            "max_half_life_bars": max_half_life_bars,
        }
        self._holding = False
        self._bars_held = 0

    def warmup_bars(self) -> int:
        return self.fit_window + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        if len(closes) < self.fit_window + 1:
            return 0.0

        half_life = ind.ou_half_life(closes, self.fit_window)
        # Not mean-reverting in any tradeable sense: refuse the whole series rather
        # than trade a model that does not describe it.
        if not np.isfinite(half_life) or half_life > self.max_half_life_bars:
            self._holding, self._bars_held = False, 0
            return 0.0

        z = ind.zscore(closes, min(self.fit_window, 20))
        if not np.isfinite(z):
            return 0.0

        if self._holding:
            self._bars_held += 1
            if z >= 0.0 or self._bars_held > self.hold_multiple * half_life:
                self._holding, self._bars_held = False, 0
                return 0.0
            return 1.0

        if z <= self.entry_z:
            self._holding, self._bars_held = True, 0
            return 1.0
        return 0.0


class HurstRegimeSwitch:
    """A meta-signal: measure whether the series trends or reverts, then act accordingly.

    Every other strategy here is a bet that one of those two behaviours is
    present, and none of them checks. This estimates a variance ratio, converts it
    to the Hurst scale readers expect, and runs the matching rule — trend-following
    above `trend_threshold`, mean-reversion below `revert_threshold`, and **flat in
    the ambiguous band between them**, because "I cannot tell" is a position.
    """

    def __init__(
        self,
        window: int = 250,
        lag: int = 5,
        trend_threshold: float = 0.55,
        revert_threshold: float = 0.45,
        trend_window: int = 50,
        entry_z: float = -2.0,
    ) -> None:
        if not 0.0 < revert_threshold < trend_threshold < 1.0:
            raise ValueError("need 0 < revert_threshold < trend_threshold < 1")
        self.window, self.lag = window, lag
        self.trend_threshold, self.revert_threshold = trend_threshold, revert_threshold
        self.trend_window, self.entry_z = trend_window, entry_z
        self.name = f"hurst_switch_{window}_{trend_threshold:g}_{revert_threshold:g}"
        self.params: dict[str, Any] = {
            "window": window,
            "lag": lag,
            "trend_threshold": trend_threshold,
            "revert_threshold": revert_threshold,
            "trend_window": trend_window,
            "entry_z": entry_z,
        }

    def warmup_bars(self) -> int:
        return max(self.window, self.trend_window) + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        vr = ind.variance_ratio(closes, self.window, self.lag)
        h = ind.hurst_from_variance_ratio(vr, self.lag)
        if not np.isfinite(h):
            return 0.0

        if h > self.trend_threshold:
            anchor = ind.sma(closes, self.trend_window)
            if not np.isfinite(anchor):
                return 0.0
            return 1.0 if closes[-1] > anchor else 0.0

        if h < self.revert_threshold:
            z = ind.zscore(closes, min(self.window, 20))
            if not np.isfinite(z):
                return 0.0
            return 1.0 if z <= self.entry_z else 0.0

        # Ambiguous: neither regime is established, so hold nothing.
        return 0.0


class VolRegimeSwitch:
    """Trend-follow in calm volatility, stand aside when volatility is elevated.

    The card for this proposed a hidden Markov model. A two-or-three-state HMM
    needs either a new dependency or a hand-rolled Baum-Welch, and a **volatility
    tercile** captures most of the benefit for a fraction of the machinery — so
    that is what this is, and the card says so. The latent-state version remains
    open.

    The regime is classified against the trailing distribution of realised
    volatility only, so the state at bar *t* uses no data after *t*. A smoothed
    (whole-sample Viterbi) state would be a look-ahead violation that looked like
    a spectacular result.
    """

    def __init__(
        self,
        vol_window: int = 20,
        lookback: int = 250,
        calm_quantile: float = 0.5,
        trend_window: int = 100,
    ) -> None:
        if not 0.0 < calm_quantile < 1.0 or vol_window < 2 or lookback < vol_window * 2:
            raise ValueError("need 0 < calm_quantile < 1 and lookback >= 2*vol_window")
        self.vol_window, self.lookback = vol_window, lookback
        self.calm_quantile, self.trend_window = calm_quantile, trend_window
        self.name = f"vol_regime_{vol_window}_{calm_quantile:g}"
        self.params: dict[str, Any] = {
            "vol_window": vol_window,
            "lookback": lookback,
            "calm_quantile": calm_quantile,
            "trend_window": trend_window,
        }

    def warmup_bars(self) -> int:
        return max(self.lookback, self.trend_window) + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        if len(closes) < self.lookback + 1:
            return 0.0

        # Trailing distribution of realised vol, rebuilt from visible bars only.
        window = closes[-(self.lookback + 1) :]
        vols = [
            ind.realised_vol(window[: i + 1], self.vol_window)
            for i in range(self.vol_window, len(window))
        ]
        vols = [v for v in vols if np.isfinite(v)]
        if len(vols) < 10:
            return 0.0
        cutoff = float(np.quantile(vols, self.calm_quantile))
        current = ind.realised_vol(closes, self.vol_window)
        if not np.isfinite(current) or current > cutoff:
            return 0.0

        anchor = ind.sma(closes, self.trend_window)
        if not np.isfinite(anchor):
            return 0.0
        return 1.0 if closes[-1] > anchor else 0.0


class AtrSizedTrend:
    """Trend entry sized so one ATR of adverse move costs a fixed fraction of equity.

    Risk-normalised rather than notional-normalised, so the same rule behaves
    consistently across volatility regimes.

    **What this harness cannot model:** a real ATR stop exits intrabar at a price.
    Exposure here changes at bar boundaries, so `stop_atr_multiple` sizes the
    position and never triggers an exit. Any comparison against a stop-based
    system elsewhere is therefore flattering to that system, and the card says so.
    """

    def __init__(
        self,
        atr_period: int = 14,
        risk_per_trade: float = 0.01,
        stop_atr_multiple: float = 2.0,
        trend_window: int = 100,
    ) -> None:
        if not 0.0 < risk_per_trade <= 1.0 or stop_atr_multiple <= 0 or atr_period < 2:
            raise ValueError("need 0 < risk_per_trade <= 1, stop_atr_multiple > 0")
        self.atr_period, self.risk_per_trade = atr_period, risk_per_trade
        self.stop_atr_multiple, self.trend_window = stop_atr_multiple, trend_window
        self.name = f"atr_sized_{atr_period}_{risk_per_trade:g}"
        self.params: dict[str, Any] = {
            "atr_period": atr_period,
            "risk_per_trade": risk_per_trade,
            "stop_atr_multiple": stop_atr_multiple,
            "trend_window": trend_window,
        }

    def warmup_bars(self) -> int:
        return max(3 * self.atr_period, self.trend_window) + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        anchor = ind.sma(closes, self.trend_window)
        if not np.isfinite(anchor) or closes[-1] <= anchor:
            return 0.0

        atr_now = ind.atr(history.highs, history.lows, closes, self.atr_period)
        price = float(closes[-1])
        if not np.isfinite(atr_now) or atr_now <= 0 or price <= 0:
            return 0.0

        # Fraction of equity such that stop_atr_multiple ATRs of adverse move costs
        # risk_per_trade of the account.
        stop_fraction = self.stop_atr_multiple * atr_now / price
        if stop_fraction <= 0:
            return 0.0
        return float(min(1.0, self.risk_per_trade / stop_fraction))


class GarchVolTarget:
    """Vol-targeted trend using an EWMA variance forecast rather than a trailing stdev.

    `VolTargetTrend` reacts with a lag equal to its vol window. This uses the
    GARCH(1,1) special case `omega=0, alpha=1-lam, beta=lam` — i.e. RiskMetrics
    EWMA — which anticipates volatility clustering instead of measuring it after
    the fact.

    Fixed `lam` rather than fitted parameters, deliberately: fitted GARCH
    coefficients are unstable on short samples, and refitting every bar is both
    slow and an invitation to look-ahead. The fitted version stays on the card as
    open work.
    """

    def __init__(
        self,
        lam: float = 0.94,
        target_vol: float = 0.6,
        trend_window: int = 100,
    ) -> None:
        if not 0.0 < lam < 1.0 or target_vol <= 0 or trend_window < 2:
            raise ValueError("need 0 < lam < 1, target_vol > 0, trend_window >= 2")
        self.lam, self.target_vol, self.trend_window = lam, target_vol, trend_window
        self.name = f"garch_voltarget_{lam:g}_{target_vol:g}"
        self.params: dict[str, Any] = {
            "lam": lam,
            "target_vol": target_vol,
            "trend_window": trend_window,
        }

    def warmup_bars(self) -> int:
        return self.trend_window + 1

    def on_bar(self, history: BarWindow) -> float:
        closes = history.closes
        anchor = ind.sma(closes, self.trend_window)
        if not np.isfinite(anchor) or closes[-1] <= anchor:
            return 0.0
        sigma = ind.ewma_vol(closes, self.lam)
        if not np.isfinite(sigma) or sigma <= 0:
            return 0.0
        return float(min(1.0, self.target_vol / sigma))

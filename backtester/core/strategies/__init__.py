"""Strategy registry.

Adding a strategy requires a module implementing the Strategy Protocol (see
core/engine.py) plus one entry in REGISTRY -- no engine changes.
"""

from __future__ import annotations

from typing import Any, Callable

from .advanced import (
    AdxFilteredTrend,
    AtrSizedTrend,
    DualMomentum,
    GarchVolTarget,
    HurstRegimeSwitch,
    IchimokuCloud,
    MaRibbon,
    OuHalfLifeReversion,
    VolRegimeSwitch,
)
from .breakout import DonchianBreakout
from .buy_and_hold import BuyAndHold
from .composite import COMBINE_MODES, Composite
from .ma_crossover import MaCrossover
from .rsi import RsiMeanReversion
from .signals import (
    BollingerBreakout,
    BollingerReversion,
    GridLong,
    KeltnerBreakout,
    MacdCross,
    ObvTrend,
    Sma200Regime,
    StochasticOversold,
    TsMomentum,
    VolTargetTrend,
    VwapReversion,
    ZScoreReversion,
)

# name -> zero-argument-capable factory producing a fresh, unprimed instance.
# Factories rather than instances because several strategies carry state, and a
# shared instance would leak position state between runs.
REGISTRY: dict[str, Callable[..., Any]] = {
    "buy_and_hold": BuyAndHold,
    "ma_crossover": MaCrossover,
    "rsi": RsiMeanReversion,
    "breakout": DonchianBreakout,
    "macd": MacdCross,
    "bb_reversion": BollingerReversion,
    "bb_breakout": BollingerBreakout,
    "keltner": KeltnerBreakout,
    "ts_momentum": TsMomentum,
    "stochastic": StochasticOversold,
    "vwap_reversion": VwapReversion,
    "obv_trend": ObvTrend,
    "zscore": ZScoreReversion,
    "sma_regime": Sma200Regime,
    "voltarget": VolTargetTrend,
    "grid": GridLong,
    # Implemented from spec-only cards: each needed code, not a new data source.
    "dual_momentum": DualMomentum,
    "adx_trend": AdxFilteredTrend,
    "ma_ribbon": MaRibbon,
    "ichimoku": IchimokuCloud,
    "ou_reversion": OuHalfLifeReversion,
    "hurst_switch": HurstRegimeSwitch,
    "vol_regime": VolRegimeSwitch,
    "atr_sized": AtrSizedTrend,
    "garch_voltarget": GarchVolTarget,
}

# Taxonomy family per registry key, used by the sweep to reason about
# orthogonality when proposing pairs.
#
# A family here is a claim that two members are NOT independent bets, so it has
# to answer to measurement. `research/signal_redundancy.py` scores this dict
# against exposure vectors; when the two disagree, this dict is what changes.
#
# Hence `sma-gated`: sma_regime, voltarget, atr_sized and garch_voltarget all
# gate on `close > sma(closes, trend_window)` with the same window, so their
# long/flat state is algebraically identical and only position SIZE differs.
# They were previously split across `regime-filter` and `risk-overlay`, which
# claimed a diversification that cannot exist. Measured on SOL: correlation
# 0.92-1.00 with active agreement 1.000 on both daily and hourly.
# (atr_sized reads 0.92 rather than 1.00 only because it also flattens on a
# degenerate ATR, an extra exit the other three do not have.)
FAMILY: dict[str, str] = {
    "buy_and_hold": "baseline",
    "ma_crossover": "trend",
    "macd": "trend",
    "ts_momentum": "momentum",
    "sma_regime": "sma-gated",
    "breakout": "breakout",
    "bb_breakout": "breakout",
    "keltner": "breakout",
    "rsi": "oscillator-reversion",
    "stochastic": "oscillator-reversion",
    "bb_reversion": "mean-reversion",
    "zscore": "mean-reversion",
    "vwap_reversion": "mean-reversion",
    "grid": "mean-reversion",
    "dual_momentum": "momentum",
    "adx_trend": "regime-filter",
    "ma_ribbon": "trend",
    "ichimoku": "trend",
    "ou_reversion": "mean-reversion",
    "hurst_switch": "regime-filter",
    "vol_regime": "regime-filter",
    "atr_sized": "sma-gated",
    "garch_voltarget": "sma-gated",
    "obv_trend": "volume-flow",
    "voltarget": "sma-gated",
}

DEFAULT_SET = ("buy_and_hold", "ma_crossover", "rsi", "breakout")


def build(name: str, **params: Any) -> Any:
    """Instantiate a registered strategy by name."""
    if name not in REGISTRY:
        raise KeyError(f"unknown strategy {name!r}; available: {sorted(REGISTRY)}")
    return REGISTRY[name](**params)


def build_all(names: list[str] | tuple[str, ...] | None = None) -> list[Any]:
    """Instantiate several strategies; `None` or 'all' means the default set."""
    if names is None or list(names) == ["all"]:
        names = list(DEFAULT_SET)
    return [build(n) for n in names]


def build_composite(
    specs: list[tuple[str, dict[str, Any]]], mode: str = "all"
) -> Composite:
    """Build a Composite from (registry-name, params) pairs."""
    return Composite([build(n, **p) for n, p in specs], mode=mode)


__all__ = [
    "REGISTRY",
    "FAMILY",
    "DEFAULT_SET",
    "COMBINE_MODES",
    "build",
    "build_all",
    "build_composite",
    "Composite",
]

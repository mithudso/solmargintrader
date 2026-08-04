"""Strategy registry.

Adding a strategy requires a module implementing the Strategy Protocol (see
core/engine.py) plus one entry in REGISTRY -- no engine changes.
"""

from __future__ import annotations

from typing import Any, Callable

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
}

# Taxonomy family per registry key, used by the sweep to reason about
# orthogonality when proposing pairs.
FAMILY: dict[str, str] = {
    "buy_and_hold": "baseline",
    "ma_crossover": "trend",
    "macd": "trend",
    "ts_momentum": "momentum",
    "sma_regime": "regime-filter",
    "breakout": "breakout",
    "bb_breakout": "breakout",
    "keltner": "breakout",
    "rsi": "oscillator-reversion",
    "stochastic": "oscillator-reversion",
    "bb_reversion": "mean-reversion",
    "zscore": "mean-reversion",
    "vwap_reversion": "mean-reversion",
    "grid": "mean-reversion",
    "obv_trend": "volume-flow",
    "voltarget": "risk-overlay",
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

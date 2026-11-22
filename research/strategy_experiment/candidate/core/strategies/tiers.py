"""Leverage-tier strategies: an existing strategy held as a perp position.

The signal is the base strategy's, unchanged and long/flat. The tier supplies
the leverage the HARNESS must run it at (`engine_leverage`, see
`core/leverage.py::tier_config`). Under a spot EngineConfig a tier strategy is
just its base strategy, which keeps it constructible everywhere the registry is
iterated; the leverage only takes effect when the runner honours it.
"""

from __future__ import annotations

import json
from typing import Any

from ..types import BarWindow


class _LeverageTier:
    tier = "low"
    engine_mode = "perp"

    def __init__(self, base: str = "macd", leverage: float = 2.0,
                 base_params: str = "") -> None:
        from . import REGISTRY

        if base not in REGISTRY or base.startswith("lev_"):
            raise ValueError(f"unknown base strategy {base!r}")
        if not leverage > 1.0:
            raise ValueError("leverage must exceed 1")
        kw: dict[str, Any] = json.loads(base_params) if base_params else {}
        self.base, self.engine_leverage = base, float(leverage)
        self._inner = REGISTRY[base](**kw)
        self.name = f"lev_{self.tier}_{leverage:g}x_{self._inner.name}"
        self.params: dict[str, Any] = {"base": base, "leverage": leverage,
                                       "base_params": base_params}

    def warmup_bars(self) -> int:
        """Same warm-up as the wrapped strategy."""
        return self._inner.warmup_bars()

    def on_bar(self, history: BarWindow) -> float:
        """Delegate to the base signal; leverage is applied by the engine."""
        return self._inner.on_bar(history)


class LevLow(_LeverageTier):
    """Low margin tier, 2x by default."""
    tier = "low"

    def __init__(self, base: str = "macd", leverage: float = 2.0, base_params: str = "") -> None:
        super().__init__(base, leverage, base_params)


class LevMedium(_LeverageTier):
    """Medium margin tier, 5x by default."""
    tier = "medium"

    def __init__(self, base: str = "macd", leverage: float = 5.0, base_params: str = "") -> None:
        super().__init__(base, leverage, base_params)


class LevHigh(_LeverageTier):
    """High margin tier, 20x by default."""
    tier = "high"

    def __init__(self, base: str = "macd", leverage: float = 20.0, base_params: str = "") -> None:
        super().__init__(base, leverage, base_params)

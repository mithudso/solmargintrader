"""Pinned adapters over fourteen existing price-only strategy cards.

These are exposure rules reused as prospective directional hypotheses. A flat
exposure remains FLAT; it is never silently reinterpreted as a bearish forecast.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from backtester.core import indicators, types
from backtester.core.strategies import REGISTRY
from backtester.core.strategy_cards import load_all
from backtester.core.types import BarWindow

STRATEGY_IDS = (
    "ma_crossover",
    "rsi",
    "breakout",
    "macd",
    "bb_reversion",
    "bb_breakout",
    "keltner",
    "ts_momentum",
    "stochastic",
    "zscore",
    "sma_regime",
    "ema_crossover",
    "ppo",
    "ma_ribbon",
)
REPLAY_BARS = 2048


class StrategySet:
    def __init__(self) -> None:
        cards = {card.registry_key: card for card in load_all().values()}
        self._catalog = []
        for key in STRATEGY_IDS:
            card = cards[key]
            overrides = {"short_when_below": True} if key == "ma_crossover" else {}
            parameters = {**card.defaults(), **overrides}
            strategy = REGISTRY[key](**parameters)
            module = Path(inspect.getfile(type(strategy)))
            material = (
                card.path.read_bytes()
                + module.read_bytes()
                + Path(indicators.__file__).read_bytes()
                + Path(types.__file__).read_bytes()
                + np.__version__.encode()
                + json.dumps(parameters, sort_keys=True).encode()
            )
            version = hashlib.sha256(material).hexdigest()
            self._catalog.append(
                {
                    "strategy_id": key,
                    "version": version,
                    "card": str(card.path),
                    "card_sha256": hashlib.sha256(card.path.read_bytes()).hexdigest(),
                    "parameters": parameters,
                    "parameter_overrides": overrides,
                    "parameter_rationale": "directional_shadow_variant"
                    if overrides
                    else "card_defaults",
                    "warmup_bars": int(strategy.warmup_bars()),
                    "family": card.family,
                    "prediction_semantics": "sign_of_strategy_exposure",
                    "execution_authority": "none_directional_hypotheses_only",
                    "input_semantics": "sampled_reference_ohlc_without_trade_volume",
                    "confidence_semantics": "historical_directional_hit_rate_not_profit_probability",
                    "replay_bars": REPLAY_BARS,
                }
            )

    def catalog(self) -> list[dict[str, Any]]:
        return json.loads(json.dumps(self._catalog))

    def predict(self, bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
        bars = bars[-REPLAY_BARS:]
        if not bars:
            return [
                {**entry, "direction": None, "reason": "warmup_required"}
                for entry in self.catalog()
            ]
        arrays = [
            np.asarray([bar[key] for bar in bars])
            for key in ("ts", "open", "high", "low", "close")
        ]
        # NaN denotes missing volume. None of the selected implementations reads
        # it; this is not zero volume and must not qualify a volume-based card.
        volume = np.full(len(bars), np.nan)
        result = []
        for entry in self.catalog():
            if len(bars) <= entry["warmup_bars"]:
                result.append({**entry, "direction": None, "reason": "warmup_required"})
                continue
            strategy = REGISTRY[entry["strategy_id"]](**entry["parameters"])
            try:
                value = 0.0
                for i in range(entry["warmup_bars"], len(bars)):
                    value = float(strategy.on_bar(BarWindow(*arrays, volume, i)))
                if not math.isfinite(value):
                    raise ValueError
                result.append(
                    {
                        **entry,
                        "direction": int(value > 0) - int(value < 0),
                        "reason": None,
                    }
                )
            except (ValueError, ArithmeticError, IndexError):
                result.append(
                    {**entry, "direction": None, "reason": "strategy_unavailable"}
                )
        return result

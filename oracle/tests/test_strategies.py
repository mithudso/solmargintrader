from __future__ import annotations

import unittest
from unittest.mock import patch

from backtester.core.strategies import REGISTRY
from oracle.strategies import STRATEGY_IDS, StrategySet


class StrategyTests(unittest.TestCase):
    def test_fourteen_card_backed_price_only_rules(self):
        strategies = StrategySet()
        self.assertEqual(len(strategies.catalog()), 14)
        self.assertEqual(
            set(STRATEGY_IDS) & {"vwap_reversion", "obv_trend", "swing_confluence"},
            set(),
        )
        for entry in strategies.catalog():
            self.assertEqual(len(entry["card_sha256"]), 64)
            self.assertEqual(
                entry["parameters"],
                {
                    **REGISTRY[entry["strategy_id"]]().params,
                    **entry["parameter_overrides"],
                },
            )

    def test_falling_series_uses_explicit_bearish_variant_preserves_flat(self):
        bars = [
            {
                "ts": i * 60,
                "open": 500 - i,
                "high": 501 - i,
                "low": 499 - i,
                "close": 500 - i,
            }
            for i in range(205)
        ]
        result = {row["strategy_id"]: row for row in StrategySet().predict(bars)}
        self.assertEqual(result["ma_crossover"]["direction"], -1)
        self.assertEqual(
            result["ma_crossover"]["parameter_overrides"], {"short_when_below": True}
        )
        self.assertEqual(
            result["ma_crossover"]["parameter_rationale"], "directional_shadow_variant"
        )
        self.assertEqual(result["sma_regime"]["direction"], 0)
        self.assertFalse(result["sma_regime"]["parameter_overrides"])

    def test_warmup_is_unavailable_and_catalog_is_copy(self):
        strategies = StrategySet()
        self.assertTrue(all(r["direction"] is None for r in strategies.predict([])))
        copy = strategies.catalog()
        copy[0]["parameters"]["fast"] = -100
        self.assertNotEqual(strategies.catalog()[0]["parameters"]["fast"], -100)

    def test_barwindow_cannot_read_future_or_trade_volume(self):
        from backtester.core.types import BarWindow

        def refuse_volume(self):
            raise AssertionError("price-only strategy tried to read volume")

        bars = [
            {
                "ts": i * 60,
                "open": 100 + i,
                "high": 101 + i,
                "low": 99 + i,
                "close": 100 + i,
            }
            for i in range(205)
        ]
        with patch.object(BarWindow, "volumes", property(refuse_volume)):
            result = StrategySet().predict(bars)
        self.assertEqual(len(result), 14)
        self.assertTrue(all(r["direction"] in (-1, 0, 1) for r in result))

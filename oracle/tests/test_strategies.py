from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backtester.core.strategies import REGISTRY
from oracle.strategies import STRATEGY_IDS, StrategySet


class StrategyTests(unittest.TestCase):
    def test_card_parameters_and_hashes_share_the_exact_parsed_snapshot(self):
        from backtester.core import strategy_cards

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for card in strategy_cards.load_all().values():
                if card.registry_key in STRATEGY_IDS:
                    (root / card.path.name).write_bytes(card.path.read_bytes())
            target = root / "ma_crossover.md"
            before = target.read_bytes()
            changed = before.replace(b"fast: {default: 20,", b"fast: {default: 21,", 1)
            self.assertNotEqual(changed, before)
            with patch.object(strategy_cards, "CARD_DIR", root):
                expected = StrategySet().catalog()[0]
                read_bytes, read_text = Path.read_bytes, Path.read_text

                def mutate_after_bytes(path):
                    raw = read_bytes(path)
                    if path == target:
                        path.write_bytes(changed)
                    return raw

                def mutate_after_text(path, *args, **kwargs):
                    text = read_text(path, *args, **kwargs)
                    if path == target:
                        path.write_bytes(changed)
                    return text

                with patch.object(Path, "read_bytes", mutate_after_bytes), patch.object(Path, "read_text", mutate_after_text):
                    actual = StrategySet().catalog()[0]
            self.assertEqual(actual["parameters"]["fast"], 20)
            self.assertEqual(actual["card_sha256"], hashlib.sha256(before).hexdigest())
            self.assertEqual(actual["version"], expected["version"])
            self.assertEqual(target.read_bytes(), changed)

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

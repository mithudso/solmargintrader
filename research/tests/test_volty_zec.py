from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtester.core.volty import VoltyConfig, simulate, stop_levels
from backtester.voltycli import aggregate, rank


def bars(prices):
    prices = np.asarray(prices, dtype=float)
    return {"timestamp": np.arange(len(prices))*60, "open": prices.copy(),
            "high": prices+1, "low": prices-1, "close": prices.copy(), "volume": np.ones(len(prices))}


class VoltyTests(unittest.TestCase):
    def test_future_cannot_change_past_stops_or_fills(self):
        original = bars([100, 100, 102, 101, 105, 99, 104, 106])
        changed = {k: v.copy() for k, v in original.items()}
        for key in ("open", "high", "low", "close"):
            changed[key][6:] *= 3
        config = VoltyConfig(length=1)
        np.testing.assert_equal(stop_levels(original, config)[0][:6], stop_levels(changed, config)[0][:6])
        first = simulate(original, config, 60, end=6, keep_fills=True)
        other = simulate(changed, config, 60, end=6, keep_fills=True)
        self.assertEqual(first["fills"], other["fills"])
        self.assertTrue(all(f["timestamp"] >= 120 for f in first["fills"]))

    def test_sma_true_range_not_wilder_or_current_bar(self):
        data = bars([100, 102, 108, 109, 110])
        upper, _ = stop_levels(data, VoltyConfig(length=2, atr_mult=0.5))
        self.assertTrue(np.isnan(upper[:3]).all())
        # TR at 1=3, TR at 2=7; active stop at 3 is 108+mean(3,7)*.5.
        self.assertEqual(upper[3], 110.5)

    def test_gap_fill_and_fees(self):
        data = bars([100, 100, 110, 115])
        config = VoltyConfig(length=1, atr_mult=1, fee_bps=0, slippage_bps=0, carry_bps_hour=0)
        result = simulate(data, config, 60, keep_fills=True)
        self.assertEqual(result["fills"][0]["price"], 110)
        self.assertAlmostEqual(result["return"], 115/110-1)
        charged = simulate(data, VoltyConfig(length=1, atr_mult=1), 60)
        self.assertLess(charged["return"], result["return"])
        self.assertGreater(charged["fees"], 0)
        self.assertGreater(charged["carry"], 0)

    def test_intrabar_ambiguity_is_reported_and_costed(self):
        data = bars([100, 100, 100])
        data["high"][-1], data["low"][-1] = 104, 96
        config = VoltyConfig(length=1, atr_mult=1, fee_bps=0, slippage_bps=0, carry_bps_hour=0)
        high = simulate(data, config, 60, path="high-first", keep_fills=True)
        low = simulate(data, config, 60, path="low-first", keep_fills=True)
        self.assertEqual(high["ambiguous_bars"], 1)
        self.assertEqual(high["trades"], 2)
        self.assertGreater(high["fills"][0]["units"], 0)
        self.assertLess(low["fills"][0]["units"], 0)

    def test_invalid_config_and_missing_candles_fail(self):
        with self.assertRaises(ValueError):
            VoltyConfig(length=0)
        with self.assertRaises(ValueError):
            VoltyConfig(atr_mult=float("nan"))
        data = bars([100, 100, 100])
        data["timestamp"][-1] += 60
        with self.assertRaisesRegex(ValueError, "contiguous"):
            simulate(data, VoltyConfig(), 60)

    def test_resampling_drops_incomplete_buckets_and_ranking_is_train_only(self):
        data = pd.DataFrame(bars([100]*12))
        data = data[data.timestamp != 120]
        out = aggregate(data, 60, 300)
        self.assertEqual(out.timestamp.tolist(), [300])
        self.assertEqual(out.volume.tolist(), [5])
        rows = [{"length": 1, "atr_mult": .25, "return": .1, "max_drawdown": .1},
                {"length": 2, "atr_mult": .5, "return": .2, "max_drawdown": .2}]
        self.assertEqual(rank(rows)["length"], 2)
        from backtester.core.strategy_cards import CARD_DIR, load_card
        card = load_card(CARD_DIR.parent / "guides" / "volty_expan_close.md")
        self.assertTrue(card.implemented)
        self.assertFalse(card.buildable)
        self.assertEqual(card.runner, "backtester.voltycli")


if __name__ == "__main__":
    unittest.main()

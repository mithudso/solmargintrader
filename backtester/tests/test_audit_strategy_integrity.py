from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from backtester.core import compound, indicators, scorecard, trigger_conditions
from backtester.core.dcasim import DcaConfig
from backtester.core.strategies.advanced import IchimokuCloud
from backtester.core.strategies.composite import Composite
from backtester.core.strategies.ma_crossover import MaCrossover
from backtester.core.strategies import rsi as rsi_module
from backtester.core.strategies import advanced as advanced_module
from backtester.core.strategies.signals import VolTargetTrend
from backtester.core.strategies.textbook import FibRetracement
from backtester.core.strategies.trigger import TriggerTrade
from backtester.core.types import BarWindow


def window(close, *, i=None, step=86400, highs=None):
    close = np.asarray(close, float)
    n = len(close)
    return BarWindow(np.arange(n) * step, close.copy(), close.copy() if highs is None else np.asarray(highs, float),
                     close.copy(), close, np.ones(n), n - 1 if i is None else i)


class StrategyIntegrityTests(unittest.TestCase):
    def test_rsi_reuses_smoothing_without_changing_causal_targets(self):
        closes = 100 + 12 * np.sin(np.arange(160) / 6) + np.arange(160) * .01
        strategy = rsi_module.RsiMeanReversion(period=5)
        holding = False
        original = rsi_module.wilder_rsi
        with patch.object(rsi_module, "wilder_rsi", wraps=original) as recompute:
            for i in range(6, len(closes)):
                value = original(closes[:i + 1], 5)
                if not holding and value < 30: holding = True
                elif holding and value > 50: holding = False
                self.assertEqual(strategy.on_bar(window(closes, i=i)), float(holding))
        self.assertLessEqual(recompute.call_count, 1)

    def test_ewma_reuses_recursion_without_changing_daily_reference(self):
        closes = np.exp(np.linspace(0, .5, 160) + .02 * np.sin(np.arange(160))) * 100
        strategy = advanced_module.GarchVolTarget(trend_window=5, target_vol=.01)
        original = indicators.ewma_vol
        with patch.object(indicators, "ewma_vol", wraps=original) as recompute:
            for i in range(6, len(closes)):
                anchor = indicators.sma(closes[:i + 1], 5)
                expected = 0 if closes[i] <= anchor else min(1, .01 / original(closes[:i + 1], .94))
                self.assertAlmostEqual(strategy.on_bar(window(closes, i=i)), expected)
        self.assertLessEqual(recompute.call_count, 1)

    def test_invalid_research_measurement_cannot_activate_conditions(self):
        values = np.ones(65)
        for column in range(5):
            arrays = [values.copy() for _ in range(5)]
            arrays[column][-1] = float("inf")
            with self.subTest(column=column), self.assertRaises(ValueError):
                trigger_conditions.compute_conditions(*arrays)

    def test_composite_cannot_convert_nonfinite_member_to_exposure(self):
        member = lambda value: SimpleNamespace(name=str(value), params={}, on_bar=lambda history: value, warmup_bars=lambda: 0)
        for mode in ("all", "any", "vote", "mean"):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                Composite([member(1), member(float("nan"))], mode=mode).on_bar(window([1, 2]))

    def test_stop_emits_flat_even_if_another_trigger_fires(self):
        strategy = TriggerTrade(horizon=10, stop=0.05)
        with patch.object(strategy, "_fires", return_value=True):
            self.assertEqual(strategy.on_bar(window([100, 90, 80], i=0)), 1)
            self.assertEqual(strategy.on_bar(window([100, 90, 80], i=2)), 0)
            self.assertIsNone(strategy._entry_i)

    def test_infinite_stop_and_fractional_ma_windows_refuse_at_construction(self):
        with self.assertRaises(ValueError): TriggerTrade(stop=float("inf"))
        for fast, slow in ((2.5, 10), (2, 10.5), (True, 10)):
            with self.subTest(fast=fast, slow=slow), self.assertRaises(ValueError):
                MaCrossover(fast=fast, slow=slow)

    def test_fibonacci_retake_uses_established_target_despite_current_wick(self):
        closes = np.array([100, 110, 120, 130, 140, 150, 160, 170, 180, 200, 150, 155, 205], float)
        highs = closes.copy(); highs[-1] = 211
        strategy = FibRetracement(lookback=10)
        self.assertEqual(strategy.on_bar(window(closes, i=11, highs=highs)), 1)
        self.assertEqual(strategy.on_bar(window(closes, i=12, highs=highs)), 0)

    def test_ichimoku_waits_for_longest_period_and_displacement(self):
        strategy = IchimokuCloud(tenkan=9, kijun=80, senkou_b=20, displacement=5)
        self.assertEqual(strategy.warmup_bars(), 85)
        with patch("backtester.core.strategies.advanced.ind.ichimoku") as calculate:
            self.assertEqual(strategy.on_bar(window(np.arange(50) + 100)), 0)
            calculate.assert_not_called()

    def test_volatility_target_scales_with_observed_cadence(self):
        closes = np.exp(np.linspace(0, 0.5, 110) + 0.02 * np.sin(np.arange(110))) * 100
        daily = VolTargetTrend(target_vol=0.01).on_bar(window(closes))
        hourly = VolTargetTrend(target_vol=0.01).on_bar(window(closes, step=3600))
        self.assertGreater(daily, 0)
        self.assertAlmostEqual(hourly, daily / np.sqrt(24))

    def test_every_derived_dca_safety_order_respects_venue_minimum(self):
        with self.assertRaises(ValueError):
            DcaConfig(safety_order_usd=10, min_order_usd=10, volume_scale=0.1, max_safety_orders=3)

    def test_nonfinite_cached_funding_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SOL_funding_1h.csv"
            path.write_text("timestamp,funding_rate\n1700000000,Infinity\n")
            with self.assertRaises(compound.CompoundDataError):
                compound.load_funding("SOL", Path(directory))

    def test_live_book_nan_remains_unavailable_before_saturation(self):
        bars = scorecard.Bars(np.array([0, 300]), *[np.ones(2) for _ in range(5)])
        for value in (float("nan"), float("inf"), -float("inf")):
            scores = scorecard._c_book(bars, {"scale": 0.5}, {"live": {"book_imbalance": value}})
            self.assertTrue(np.isnan(scores).all())
        self.assertEqual(scorecard._c_book(bars, {"scale": 0.5}, {"live": {"book_imbalance": 0.5}})[-1], 1)

    def test_adx_uses_wilder_recursion_after_initial_seed(self):
        close = np.array([10., 11., 12., 13., 14., 15., 14., 13., 14., 15.])
        # DX ends 0, 50, 25, 62.5. Recursive ADX ends 50, 50, 37.5, 50;
        # the last-two DX mean would instead return 43.75.
        self.assertAlmostEqual(indicators.directional_movement(close + .5, close - .5, close, period=2)[2], 50)

"""Tests for the five mechanisms named by the cited trading guides.

Source catalogue: `tradingstrategyresults.json`. Each test targets what the
mechanism could get *wrong*: DCA's ramp arithmetic, the PPO's scale invariance (the
one property that separates it from MACD), the Fibonacci up-swing order and the
turn-up condition, and the swing breakout level excluding its own bar. A final
class applies the one-bar-leak test the repo requires for anything touching signal
generation.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core import indicators as ind
from backtester.core.strategies import REGISTRY, build
from backtester.core.strategies.textbook import (
    DollarCostAveraging,
    EmaCrossover,
    FibRetracement,
    PpoCross,
    SwingConfluence,
)
from backtester.core.types import BarWindow


def window(closes, highs=None, lows=None, volumes=None, upto=None) -> BarWindow:
    """A BarWindow at bar `upto` (default: the final bar) of the supplied series."""
    c = np.asarray(closes, dtype="float64")
    h = np.asarray(highs if highs is not None else c, dtype="float64")
    lo = np.asarray(lows if lows is not None else c, dtype="float64")
    v = np.asarray(volumes if volumes is not None else np.full(len(c), 1_000.0), dtype="float64")
    ts = np.arange(len(c), dtype="int64") * 86400
    return BarWindow(ts, c, h, lo, c, v, len(c) - 1 if upto is None else upto)


def walk(strategy, closes, highs=None, lows=None, volumes=None) -> list[float]:
    """Exposure after every bar, feeding the strategy one growing window at a time."""
    c = np.asarray(closes, dtype="float64")
    h = c if highs is None else np.asarray(highs, dtype="float64")
    lo = c if lows is None else np.asarray(lows, dtype="float64")
    v = np.full(len(c), 1_000.0) if volumes is None else np.asarray(volumes, dtype="float64")
    out = []
    for i in range(len(c)):
        out.append(strategy.on_bar(window(c, h, lo, v, upto=i)))
    return out


class TestDca(unittest.TestCase):
    def test_exposure_ramps_by_one_instalment_per_interval(self) -> None:
        s = DollarCostAveraging(instalments=10, interval=7)
        got = [s.on_bar(window(np.ones(n))) for n in (1, 7, 8, 14, 15, 63, 64, 500)]
        self.assertEqual(got, [0.1, 0.1, 0.2, 0.2, 0.3, 0.9, 1.0, 1.0])

    def test_exposure_never_exceeds_the_budget(self) -> None:
        s = DollarCostAveraging(instalments=4, interval=1)
        self.assertEqual(max(s.on_bar(window(np.ones(n))) for n in range(1, 50)), 1.0)

    def test_after_the_ramp_it_is_buy_and_hold(self) -> None:
        s = DollarCostAveraging(instalments=5, interval=3)
        self.assertEqual(s.on_bar(window(np.ones(200))), build("buy_and_hold").on_bar(window(np.ones(200))))

    def test_degenerate_schedules_are_refused(self) -> None:
        for kw in ({"instalments": 0}, {"interval": 0}):
            with self.assertRaises(ValueError):
                DollarCostAveraging(**kw)


class TestEmaCrossover(unittest.TestCase):
    def test_an_uptrend_is_long_and_a_downtrend_is_flat(self) -> None:
        up = 100 * 1.01 ** np.arange(300)
        self.assertEqual(EmaCrossover(50, 200).on_bar(window(up)), 1.0)
        self.assertEqual(EmaCrossover(50, 200).on_bar(window(up[::-1].copy())), 0.0)

    def test_it_turns_earlier_than_the_sma_cross_after_a_reversal(self) -> None:
        # Flat, then a sharp rally: the EMA weights the new closes more, so it crosses first.
        closes = np.concatenate([np.full(120, 100.0), np.linspace(100, 130, 15)])
        ema_first = next(i for i in range(120, 135) if EmaCrossover(10, 40).on_bar(window(closes, upto=i)) == 1.0)
        from backtester.core.strategies.ma_crossover import MaCrossover
        sma_first = next(i for i in range(120, 135) if MaCrossover(10, 40).on_bar(window(closes, upto=i)) == 1.0)
        self.assertLessEqual(ema_first, sma_first)

    def test_it_waits_for_the_slow_ema_to_exist(self) -> None:
        self.assertEqual(EmaCrossover(5, 20).on_bar(window(np.arange(1.0, 15.0))), 0.0)
        self.assertEqual(EmaCrossover(5, 20).warmup_bars(), 20)

    def test_fast_must_be_shorter_than_slow(self) -> None:
        with self.assertRaises(ValueError):
            EmaCrossover(50, 50)


class TestPpo(unittest.TestCase):
    def setUp(self) -> None:
        rng = np.random.default_rng(3)
        self.closes = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.02, 300)))

    def test_ppo_is_scale_invariant_but_macd_is_not(self) -> None:
        a = ind.ppo(self.closes)
        b = ind.ppo(self.closes * 37.0)
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, places=6)
        self.assertNotAlmostEqual(ind.macd(self.closes)[0], ind.macd(self.closes * 37.0)[0], places=3)

    def test_ppo_line_is_macd_line_over_the_slow_ema_in_percent(self) -> None:
        macd_line = ind.macd(self.closes)[0]
        self.assertAlmostEqual(ind.ppo(self.closes)[0], 100.0 * macd_line / ind.ema(self.closes, 26), places=5)

    def test_ppo_is_nan_without_enough_history(self) -> None:
        self.assertTrue(all(np.isnan(x) for x in ind.ppo(self.closes[:30])))

    def test_a_zero_slow_ema_is_refused_rather_than_divided_by(self) -> None:
        self.assertTrue(all(np.isnan(x) for x in ind.ppo(np.zeros(100))))

    def test_accelerating_uptrend_is_long_and_flat_series_is_not(self) -> None:
        # Log-price grows quadratically, so the PPO itself keeps rising above its signal.
        # (A constant-growth series has a constant PPO, equal to its signal: not long.)
        up = 100 * np.exp(1e-4 * np.arange(120) ** 2)
        self.assertEqual(PpoCross().on_bar(window(up)), 1.0)
        self.assertEqual(PpoCross().on_bar(window(np.full(120, 100.0))), 0.0)

    def test_spans_must_be_ordered(self) -> None:
        with self.assertRaises(ValueError):
            PpoCross(fast=26, slow=12)


class TestFibLevel(unittest.TestCase):
    def test_ratio_zero_is_the_high_and_one_is_the_low(self) -> None:
        self.assertEqual(ind.fib_level(200.0, 100.0, 0.0), 200.0)
        self.assertEqual(ind.fib_level(200.0, 100.0, 1.0), 100.0)
        self.assertEqual(ind.fib_level(200.0, 100.0, 0.5), 150.0)
        self.assertAlmostEqual(ind.fib_level(200.0, 100.0, 0.618), 138.2)


class TestFibRetracement(unittest.TestCase):
    base = [100, 110, 120, 130, 140, 150, 160, 170, 180, 200]

    def strat(self) -> FibRetracement:
        return FibRetracement(lookback=10, entry_ratio=0.382, invalid_ratio=0.786)

    def test_it_buys_the_turn_inside_the_zone_not_the_fall_into_it(self) -> None:
        out = walk(self.strat(), self.base + [150, 155])
        # 150 is inside the zone but still falling (prev close 200): no entry.
        self.assertEqual(out[10], 0.0)
        # 155 is inside the zone and above the previous close: entry.
        self.assertEqual(out[11], 1.0)

    def test_it_exits_when_the_swing_high_is_retaken(self) -> None:
        out = walk(self.strat(), self.base + [150, 155, 210])
        self.assertEqual(out[11], 1.0)
        self.assertEqual(out[12], 0.0)

    def test_it_exits_when_the_zone_is_broken(self) -> None:
        out = walk(self.strat(), self.base + [150, 155, 120])
        self.assertEqual(out[11], 1.0)
        self.assertEqual(out[12], 0.0)

    def test_a_pullback_deeper_than_the_invalid_level_is_not_bought(self) -> None:
        out = walk(self.strat(), self.base + [150, 120, 125])
        self.assertEqual(out[12], 0.0)

    def test_a_down_swing_is_never_bought(self) -> None:
        down = self.base[::-1] + [160, 165]
        self.assertEqual(max(walk(self.strat(), down)), 0.0)

    def test_a_flat_range_has_no_swing(self) -> None:
        self.assertEqual(max(walk(self.strat(), [100.0] * 40)), 0.0)

    def test_ratios_must_be_ordered_inside_zero_one(self) -> None:
        for kw in ({"entry_ratio": 0.8, "invalid_ratio": 0.5}, {"invalid_ratio": 1.0}, {"entry_ratio": 0.0}):
            with self.assertRaises(ValueError):
                FibRetracement(**kw)


class TestSwingConfluence(unittest.TestCase):
    def rising(self, n: int = 90) -> np.ndarray:
        return 100.0 + 0.5 * np.arange(n)

    def test_a_confirmed_breakout_is_long(self) -> None:
        s = SwingConfluence(min_confirms=2)
        self.assertEqual(walk(s, self.rising())[-1], 1.0)

    def test_the_resistance_level_excludes_the_current_bar(self) -> None:
        # Flat at 100 then a close exactly equal to the prior high is NOT a breakout.
        closes = np.concatenate([np.full(80, 100.0), [100.0]])
        self.assertEqual(max(walk(SwingConfluence(min_confirms=1), closes)), 0.0)

    def test_no_breakout_means_no_trade_however_many_confirmations(self) -> None:
        # Rising, then a pause below the prior high: SMA/RSI/OBV still agree, but no breakout.
        closes = np.concatenate([self.rising(80), [self.rising(80)[-1] - 1.0]])
        self.assertEqual(SwingConfluence(min_confirms=1).on_bar(window(closes)), 0.0)

    def test_requiring_every_confirmation_is_stricter_than_requiring_one(self) -> None:
        c = self.rising()
        loose = sum(walk(SwingConfluence(min_confirms=1), c))
        strict = sum(walk(SwingConfluence(min_confirms=4), c))
        self.assertGreaterEqual(loose, strict)

    def test_it_exits_when_the_swing_low_breaks(self) -> None:
        closes = np.concatenate([self.rising(90), [self.rising(90)[-1] - 30.0]])
        out = walk(SwingConfluence(min_confirms=2), closes)
        self.assertEqual(out[-2], 1.0)
        self.assertEqual(out[-1], 0.0)

    def test_bad_parameters_are_refused(self) -> None:
        for kw in ({"min_confirms": 0}, {"min_confirms": 5}, {"breakout": 1}):
            with self.assertRaises(ValueError):
                SwingConfluence(**kw)


class TestNoLookahead(unittest.TestCase):
    """The decision at bar t must not change when bars after t change."""

    def test_every_new_strategy_ignores_the_future(self) -> None:
        rng = np.random.default_rng(11)
        n = 320
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
        high, low = close * 1.01, close * 0.99
        vol = rng.uniform(500, 1500, n)
        cut = 260
        close2, high2, low2, vol2 = close.copy(), high.copy(), low.copy(), vol.copy()
        close2[cut + 1:] *= 5.0
        high2[cut + 1:] *= 5.0
        low2[cut + 1:] *= 0.2
        vol2[cut + 1:] *= 9.0
        for key in ("dca", "ema_crossover", "ppo", "fib_retracement", "swing_confluence"):
            with self.subTest(strategy=key):
                a, b = build(key), build(key)
                got_a = got_b = None
                for i in range(cut + 1):
                    got_a = a.on_bar(window(close, high, low, vol, upto=i))
                    got_b = b.on_bar(window(close2, high2, low2, vol2, upto=i))
                self.assertEqual(got_a, got_b)


class TestRegistered(unittest.TestCase):
    def test_all_five_are_registered_with_families(self) -> None:
        from backtester.core.strategies import FAMILY

        for key in ("dca", "ema_crossover", "ppo", "fib_retracement", "swing_confluence"):
            self.assertIn(key, REGISTRY)
            self.assertIn(key, FAMILY)

    def test_exposure_is_always_in_zero_one(self) -> None:
        rng = np.random.default_rng(5)
        close = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 400)))
        for key in ("dca", "ema_crossover", "ppo", "fib_retracement", "swing_confluence"):
            s = build(key)
            for v in walk(s, close, close * 1.01, close * 0.99):
                self.assertTrue(0.0 <= v <= 1.0, (key, v))


if __name__ == "__main__":
    unittest.main()

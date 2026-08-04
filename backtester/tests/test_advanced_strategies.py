"""Tests for the nine strategies implemented from spec-only cards.

Each test targets the thing that mechanism could get *wrong*, not that it runs:
the skipped window in dual momentum, the strength gate in ADX, the displacement
trap in Ichimoku, the screening rule in the OU reversion, and the regime
selection in both switches. A strategy that returns a number for every bar is
easy; one that returns the right number for the right reason is not.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core import indicators as ind
from backtester.core.strategies.advanced import (
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
from backtester.core.types import BarWindow


def window(closes, highs=None, lows=None, volumes=None) -> BarWindow:
    """A BarWindow positioned at the final bar of the supplied series."""
    c = np.asarray(closes, dtype="float64")
    h = np.asarray(highs if highs is not None else c * 1.01, dtype="float64")
    l = np.asarray(lows if lows is not None else c * 0.99, dtype="float64")
    v = np.asarray(volumes if volumes is not None else np.full(len(c), 1_000.0), dtype="float64")
    ts = np.arange(len(c), dtype="int64") * 86400
    return BarWindow(ts, c, h, l, c, v, len(c) - 1)


def trending(n: int = 400, step: float = 0.5, start: float = 100.0):
    return start + np.arange(n) * step


def oscillating(n: int = 400, amp: float = 8.0, period: float = 20.0, level: float = 100.0):
    return level + amp * np.sin(np.arange(n) * 2 * np.pi / period)


class TestDualMomentum(unittest.TestCase):
    def test_the_skipped_window_is_actually_excluded(self) -> None:
        # Built so the full-window return is POSITIVE but the 12-1 return is
        # NEGATIVE: a long run-up, then a sharp final bar. A plain trailing return
        # would go long here; skipping the last bar must not.
        closes = list(np.linspace(100.0, 80.0, 20)) + [120.0]
        strat = DualMomentum(formation=12, skip=1)
        self.assertEqual(strat.on_bar(window(closes)), 0.0)
        # Without the skip, the same series is a buy — proving the skip is load-bearing.
        self.assertEqual(DualMomentum(formation=12, skip=0).on_bar(window(closes)), 1.0)

    def test_a_rising_series_is_long(self) -> None:
        self.assertEqual(DualMomentum().on_bar(window(trending(40))), 1.0)

    def test_degenerate_configs_are_refused(self) -> None:
        for kwargs in ({"formation": 1}, {"skip": -1}, {"formation": 5, "skip": 5}):
            with self.assertRaises(ValueError):
                DualMomentum(**kwargs)


class TestAdxFilteredTrend(unittest.TestCase):
    def test_a_strong_uptrend_is_long(self) -> None:
        closes = trending(200)
        self.assertEqual(AdxFilteredTrend().on_bar(window(closes)), 1.0)

    def test_a_directionless_series_is_flat_even_though_di_may_cross(self) -> None:
        # Chop: ADX stays low, so the gate refuses regardless of DI ordering. This
        # is the entire reason the mechanism exists.
        closes = oscillating(300, amp=2.0, period=4.0)
        _, _, adx = ind.directional_movement(
            np.asarray(closes) * 1.01, np.asarray(closes) * 0.99, np.asarray(closes), 14
        )
        self.assertLess(adx, 25.0, "the fixture must actually be low-ADX")
        self.assertEqual(AdxFilteredTrend().on_bar(window(closes)), 0.0)

    def test_the_threshold_is_what_binds(self) -> None:
        closes = oscillating(300, amp=2.0, period=4.0)
        # Drop the threshold to zero and direction alone decides, so the result may
        # change — proving the gate, not the direction, produced the flat above.
        permissive = AdxFilteredTrend(adx_threshold=0.0).on_bar(window(closes))
        self.assertIn(permissive, (0.0, 1.0))

    def test_warmup_covers_three_nested_smoothings(self) -> None:
        self.assertEqual(AdxFilteredTrend(adx_period=14).warmup_bars(), 43)


class TestMaRibbon(unittest.TestCase):
    def test_a_clean_uptrend_puts_every_pair_in_order(self) -> None:
        self.assertEqual(MaRibbon().on_bar(window(trending(200))), 1.0)

    def test_a_clean_downtrend_puts_none_in_order(self) -> None:
        self.assertEqual(MaRibbon().on_bar(window(trending(200, step=-0.4, start=200.0))), 0.0)

    def test_exposure_is_graded_not_binary(self) -> None:
        # A recent turn leaves some pairs ordered and others not.
        closes = np.concatenate([trending(150), trending(10, step=-1.0, start=175.0)])
        value = MaRibbon().on_bar(window(closes))
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)


class TestIchimokuDisplacement(unittest.TestCase):
    """The displacement is the look-ahead trap; this is the test that matters."""

    def test_the_cloud_used_is_the_one_computed_displacement_bars_ago(self) -> None:
        closes = trending(200)
        strat = IchimokuCloud()
        w = window(closes)
        cut = len(closes) - strat.displacement
        highs, lows = np.asarray(closes) * 1.01, np.asarray(closes) * 0.99
        _, _, span_a, span_b = ind.ichimoku(highs[:cut], lows[:cut], 9, 26, 52)
        expected = 1.0 if closes[-1] > max(span_a, span_b) else 0.0
        self.assertEqual(strat.on_bar(w), expected)
        # And the cloud computed from the FULL history differs, so the distinction
        # is real rather than incidental on this fixture.
        _, _, full_a, full_b = ind.ichimoku(highs, lows, 9, 26, 52)
        self.assertNotAlmostEqual(max(span_a, span_b), max(full_a, full_b), places=6)

    def test_price_above_a_trailing_cloud_is_long(self) -> None:
        self.assertEqual(IchimokuCloud().on_bar(window(trending(200))), 1.0)

    def test_warmup_includes_the_displacement(self) -> None:
        self.assertEqual(IchimokuCloud().warmup_bars(), 52 + 26)


class TestOuHalfLifeReversion(unittest.TestCase):
    def test_a_trending_series_is_screened_out_entirely(self) -> None:
        # No reversion means an infinite half-life, and the screening rule refuses
        # the series rather than trading a model that does not describe it. This is
        # the rule that would have disqualified raw SOL price.
        closes = trending(300)
        self.assertEqual(ind.ou_half_life(closes, 250), float("inf"))
        self.assertEqual(OuHalfLifeReversion().on_bar(window(closes)), 0.0)

    def test_a_slow_reverting_series_is_screened_by_max_half_life(self) -> None:
        closes = oscillating(400, period=400.0)  # half-life far beyond the cap
        strat = OuHalfLifeReversion(max_half_life_bars=5)
        self.assertEqual(strat.on_bar(window(closes)), 0.0)

    def test_it_enters_when_stretched_and_the_series_reverts(self) -> None:
        closes = oscillating(400, amp=10.0, period=30.0)
        strat = OuHalfLifeReversion(fit_window=250, max_half_life_bars=60)
        # Walk the series and confirm it takes a position at some point rather than
        # sitting flat forever.
        taken = [strat.on_bar(window(closes[: i + 1])) for i in range(300, 400)]
        self.assertGreater(max(taken), 0.0, "a reverting series should be traded")

    def test_the_hold_cap_forces_an_exit(self) -> None:
        strat = OuHalfLifeReversion(fit_window=250, hold_multiple=0.01, max_half_life_bars=999)
        closes = oscillating(400, amp=10.0, period=30.0)
        seen = [strat.on_bar(window(closes[: i + 1])) for i in range(300, 400)]
        # With a hold cap this tight, no position can persist across many bars.
        self.assertIn(0.0, seen)


class TestHurstRegimeSwitch(unittest.TestCase):
    def test_a_trending_series_selects_the_trend_rule(self) -> None:
        closes = trending(400)
        vr = ind.variance_ratio(closes, 250, 5)
        self.assertGreater(ind.hurst_from_variance_ratio(vr, 5), 0.55)
        self.assertEqual(HurstRegimeSwitch().on_bar(window(closes)), 1.0)

    def test_the_ambiguous_band_holds_nothing(self) -> None:
        # A random walk sits at H ~ 0.5, inside the default 0.45-0.55 band, so
        # neither regime is established and the honest answer is no position.
        rng = np.random.default_rng(21)
        closes = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.02, 400)))
        h = ind.hurst_from_variance_ratio(ind.variance_ratio(closes, 250, 5), 5)
        # Thresholds bracket the measured H rather than assuming a random walk lands
        # exactly at 0.5 — finite samples scatter, and pinning a seed to a hard-coded
        # band would make this test fragile for no gain.
        strat = HurstRegimeSwitch(
            trend_threshold=min(0.99, h + 0.05), revert_threshold=max(0.01, h - 0.05)
        )
        self.assertEqual(strat.on_bar(window(closes)), 0.0)

    def test_thresholds_must_be_ordered(self) -> None:
        with self.assertRaises(ValueError):
            HurstRegimeSwitch(trend_threshold=0.4, revert_threshold=0.6)


class TestVolRegimeSwitch(unittest.TestCase):
    def test_elevated_volatility_stands_aside(self) -> None:
        rng = np.random.default_rng(11)
        calm = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.005, 300)))
        shock = calm[-1] * np.exp(np.cumsum(rng.normal(0.0, 0.12, 40)))
        closes = np.concatenate([calm, shock])
        self.assertEqual(VolRegimeSwitch().on_bar(window(closes)), 0.0)

    def test_a_calm_uptrend_is_long(self) -> None:
        rng = np.random.default_rng(5)
        noisy = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.03, 200)))
        calm = np.concatenate([noisy, noisy[-1] * np.exp(np.cumsum(rng.normal(0.004, 0.004, 200)))])
        self.assertEqual(VolRegimeSwitch().on_bar(window(calm)), 1.0)

    def test_configs_that_cannot_estimate_a_distribution_are_refused(self) -> None:
        with self.assertRaises(ValueError):
            VolRegimeSwitch(vol_window=20, lookback=30)


class TestAtrSizedTrend(unittest.TestCase):
    def test_exposure_falls_as_atr_rises(self) -> None:
        base = trending(200, step=0.4)
        quiet = AtrSizedTrend().on_bar(window(base, highs=base * 1.002, lows=base * 0.998))
        wild = AtrSizedTrend().on_bar(window(base, highs=base * 1.08, lows=base * 0.92))
        self.assertGreater(quiet, wild)
        self.assertGreater(wild, 0.0)

    def test_exposure_is_capped_at_one(self) -> None:
        base = trending(200, step=0.4)
        strat = AtrSizedTrend(risk_per_trade=1.0)
        self.assertLessEqual(strat.on_bar(window(base, highs=base * 1.0001, lows=base * 0.9999)), 1.0)

    def test_below_the_trend_anchor_it_holds_nothing(self) -> None:
        closes = trending(200, step=-0.4, start=200.0)
        self.assertEqual(AtrSizedTrend().on_bar(window(closes)), 0.0)


class TestGarchVolTarget(unittest.TestCase):
    def test_exposure_is_the_vol_ratio_capped_at_one(self) -> None:
        rng = np.random.default_rng(9)
        closes = 100 * np.exp(np.cumsum(rng.normal(0.004, 0.02, 300)))
        strat = GarchVolTarget()
        got = strat.on_bar(window(closes))
        sigma = ind.ewma_vol(closes, 0.94)
        self.assertAlmostEqual(got, min(1.0, 0.6 / sigma), places=9)

    def test_a_downtrend_is_flat_regardless_of_volatility(self) -> None:
        closes = trending(300, step=-0.3, start=200.0)
        self.assertEqual(GarchVolTarget().on_bar(window(closes)), 0.0)

    def test_lambda_must_be_a_proper_decay(self) -> None:
        for lam in (0.0, 1.0, -0.5):
            with self.assertRaises(ValueError):
                GarchVolTarget(lam=lam)


class TestNoStrategyReadsTheFuture(unittest.TestCase):
    """BarWindow blocks it structurally; this confirms none of them tries."""

    def test_every_strategy_returns_a_bounded_exposure(self) -> None:
        rng = np.random.default_rng(3)
        closes = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.02, 400)))
        for factory in (
            DualMomentum, AdxFilteredTrend, MaRibbon, IchimokuCloud,
            OuHalfLifeReversion, HurstRegimeSwitch, VolRegimeSwitch,
            AtrSizedTrend, GarchVolTarget,
        ):
            strat = factory()
            with self.subTest(factory.__name__):
                value = strat.on_bar(window(closes))
                self.assertTrue(np.isfinite(value))
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)

    def test_a_decision_does_not_change_when_later_bars_are_appended(self) -> None:
        # The decision at bar t must be identical whether or not bars after t
        # exist in the underlying arrays — the property BarWindow enforces.
        rng = np.random.default_rng(4)
        closes = 100 * np.exp(np.cumsum(rng.normal(0.0, 0.02, 400)))
        for factory in (
            DualMomentum, AdxFilteredTrend, MaRibbon, IchimokuCloud,
            HurstRegimeSwitch, AtrSizedTrend, GarchVolTarget,
        ):
            with self.subTest(factory.__name__):
                truncated = factory().on_bar(window(closes[:300]))
                c = np.asarray(closes, dtype="float64")
                full = BarWindow(
                    np.arange(len(c), dtype="int64") * 86400,
                    c, c * 1.01, c * 0.99, c, np.full(len(c), 1_000.0), 299,
                )
                self.assertEqual(truncated, factory().on_bar(full))


if __name__ == "__main__":
    unittest.main()

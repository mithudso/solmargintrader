"""Known-answer tests for indicators, strategies, and the composite combiner.

Indicator values here are hand-computed, not captured from a previous run, so a
regression points at the arithmetic rather than at "something changed".
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core import indicators as ind
from backtester.core.data import SyntheticLoader, frame_to_arrays
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import (
    COMBINE_MODES,
    FAMILY,
    REGISTRY,
    Composite,
    build,
    build_composite,
)
from backtester.core.types import BarWindow, LookAheadError


class TestIndicatorArithmetic(unittest.TestCase):
    """Each indicator against a value computed by hand."""

    def test_sma(self) -> None:
        """Mean of the last `window` values."""
        self.assertAlmostEqual(ind.sma(np.array([1.0, 2, 3, 4, 5]), 3), 4.0, places=12)

    def test_sma_insufficient_history_is_nan(self) -> None:
        """Not enough bars yields NaN rather than a partial-window average."""
        self.assertTrue(np.isnan(ind.sma(np.array([1.0, 2.0]), 5)))

    def test_ema_matches_hand_recursion(self) -> None:
        """span=3 -> alpha=0.5, seeded by SMA of the first 3 values."""
        # seed = mean(1,2,3) = 2; then .5*4+.5*2 = 3; then .5*5+.5*3 = 4
        self.assertAlmostEqual(
            ind.ema(np.array([1.0, 2, 3, 4, 5]), 3), 4.0, places=12
        )

    def test_ema_cap_is_float_equivalent_to_full_recursion(self) -> None:
        """The default cap must match the uncapped recursion to ~1e-12 relative.

        Asserted as RELATIVE error: an absolute tolerance is meaningless here
        because the value scales with price level.
        """
        rng = np.random.default_rng(3)
        series = 100 + np.cumsum(rng.normal(0, 1, 2000))
        capped = ind.ema(series, 20)
        full = ind.ema(series, 20, cap_multiple=10_000)
        self.assertLess(abs(capped - full) / abs(full), 1e-12)

    def test_ema_cap_accuracy_improves_monotonically(self) -> None:
        """A larger cap is never less accurate -- pins the documented table."""
        rng = np.random.default_rng(3)
        series = 100 + np.cumsum(rng.normal(0, 1, 2000))
        full = ind.ema(series, 20, cap_multiple=10_000)
        errs = [
            abs(ind.ema(series, 20, cap_multiple=c) - full) / abs(full)
            for c in (3, 5, 8, 12)
        ]
        self.assertEqual(errs, sorted(errs, reverse=True))
        self.assertLess(errs[-1], 1e-12)

    def test_wilder_smooth(self) -> None:
        """period=2 -> seed mean(2,4)=3; then (3*1+6)/2 = 4.5."""
        self.assertAlmostEqual(
            ind.wilder_smooth(np.array([2.0, 4.0, 6.0]), 2), 4.5, places=12
        )

    def test_rsi_all_gains_is_100(self) -> None:
        """A monotonically rising series has no downside."""
        self.assertAlmostEqual(ind.rsi(np.arange(1.0, 30.0), 14), 100.0, places=10)

    def test_rsi_all_losses_is_zero(self) -> None:
        """A monotonically falling series has no upside."""
        self.assertAlmostEqual(ind.rsi(np.arange(30.0, 1.0, -1.0), 14), 0.0, places=10)

    def test_rsi_neutral_without_history(self) -> None:
        """Too little history returns the neutral 50, not NaN."""
        self.assertEqual(ind.rsi(np.array([1.0, 2.0]), 14), 50.0)

    def test_bollinger_hand_computed(self) -> None:
        """window=3 on [1,2,3]: mid=2, population sd=sqrt(2/3)."""
        mid, up, lo, bw = ind.bollinger(np.array([1.0, 2.0, 3.0]), 3, 2.0)
        sd = np.sqrt(2.0 / 3.0)
        self.assertAlmostEqual(mid, 2.0, places=12)
        self.assertAlmostEqual(up, 2.0 + 2 * sd, places=12)
        self.assertAlmostEqual(lo, 2.0 - 2 * sd, places=12)
        self.assertAlmostEqual(bw, (up - lo) / mid, places=12)

    def test_true_range_takes_the_max_of_three(self) -> None:
        """TR = max(H-L, |H-prevC|, |L-prevC|)."""
        tr = ind.true_range(
            np.array([10.0, 12.0]), np.array([8.0, 9.0]), np.array([9.0, 11.0])
        )
        self.assertEqual(len(tr), 1)
        self.assertAlmostEqual(float(tr[0]), 3.0, places=12)

    def test_atr_is_positive_on_real_shaped_bars(self) -> None:
        """ATR of a widening series is positive and finite."""
        h = np.array([10.0, 11, 12, 13, 14, 15])
        l = np.array([9.0, 10, 11, 12, 13, 14])
        c = np.array([9.5, 10.5, 11.5, 12.5, 13.5, 14.5])
        a = ind.atr(h, l, c, 3)
        self.assertTrue(np.isfinite(a))
        self.assertGreater(a, 0.0)

    def test_zscore_hand_computed(self) -> None:
        """window=3 on [1,2,3]: sample sd=1, mean=2 -> z=1."""
        self.assertAlmostEqual(ind.zscore(np.array([1.0, 2.0, 3.0]), 3), 1.0, places=12)

    def test_zscore_flat_window_is_zero_not_infinite(self) -> None:
        """Zero dispersion must not divide by ~0 and emit a huge score."""
        self.assertEqual(ind.zscore(np.array([5.0, 5.0, 5.0]), 3), 0.0)

    def test_roc(self) -> None:
        """window=2 on [100,110,121] -> 121/100 - 1."""
        self.assertAlmostEqual(
            ind.roc(np.array([100.0, 110.0, 121.0]), 2), 0.21, places=12
        )

    def test_obv_cumulates_signed_volume(self) -> None:
        """Direction of the close change signs each bar's volume."""
        series = ind.obv(
            np.array([10.0, 11.0, 10.0, 12.0]), np.array([100.0, 200, 300, 400])
        )
        np.testing.assert_allclose(series, [0.0, 200.0, -100.0, 300.0])

    def test_vwap_weights_by_volume(self) -> None:
        """A high-volume bar pulls VWAP toward its typical price."""
        h = np.array([10.0, 20.0])
        l = np.array([10.0, 20.0])
        c = np.array([10.0, 20.0])
        v = np.array([1.0, 999.0])
        got = ind.rolling_vwap(h, l, c, v, 2)
        self.assertGreater(got, 19.0)

    def test_vwap_zero_volume_falls_back_to_mean(self) -> None:
        """A zero-volume window must not divide by zero."""
        got = ind.rolling_vwap(
            np.array([10.0, 20.0]), np.array([10.0, 20.0]),
            np.array([10.0, 20.0]), np.array([0.0, 0.0]), 2,
        )
        self.assertAlmostEqual(got, 15.0, places=12)

    def test_stochastic_at_range_extremes(self) -> None:
        """A close at the window high gives %K = 100."""
        h = np.array([10.0, 11, 12, 13])
        l = np.array([5.0, 5, 5, 5])
        c = np.array([6.0, 7, 8, 13])
        k, d = ind.stochastic(h, l, c, 2, 1)
        self.assertAlmostEqual(k, 100.0, places=10)
        self.assertAlmostEqual(d, k, places=10)

    def test_realised_vol_of_flat_series_is_zero(self) -> None:
        """No variation means no volatility."""
        self.assertAlmostEqual(
            ind.realised_vol(np.full(30, 50.0), 20), 0.0, places=12
        )

    def test_macd_zero_on_flat_series(self) -> None:
        """Both EMAs coincide on a flat series, so the line is zero."""
        line, sig, hist = ind.macd(np.full(200, 42.0), 12, 26, 9)
        self.assertAlmostEqual(line, 0.0, places=8)
        self.assertAlmostEqual(hist, 0.0, places=8)


class TestEveryRegisteredStrategy(unittest.TestCase):
    """Contract tests applied to all 16 registered strategies."""

    @classmethod
    def setUpClass(cls) -> None:
        """One shared synthetic series long enough for the slowest warm-up."""
        df = SyntheticLoader(n_bars=800, seed=17).load("SOL", None, None, "1d")
        cls.arrays = frame_to_arrays(df)

    def test_all_have_a_family(self) -> None:
        """The sweep reasons about orthogonality via FAMILY; keep it complete."""
        self.assertEqual(set(REGISTRY), set(FAMILY))

    def test_all_run_and_return_bounded_exposure(self) -> None:
        """Every strategy runs and every emitted target is within [-1, 1]."""
        for name in REGISTRY:
            with self.subTest(strategy=name):
                strat = build(name)
                n = len(self.arrays["close"])
                warm = strat.warmup_bars()
                self.assertLess(warm, n, f"{name} warmup exceeds the test series")
                for i in range(warm, n, 37):  # stride to keep the test quick
                    w = BarWindow(
                        self.arrays["ts"], self.arrays["open"], self.arrays["high"],
                        self.arrays["low"], self.arrays["close"], self.arrays["volume"], i,
                    )
                    target = strat.on_bar(w)
                    self.assertTrue(
                        np.isfinite(target), f"{name} returned non-finite {target!r}"
                    )
                    self.assertGreaterEqual(target, -1.0)
                    self.assertLessEqual(target, 1.0)

    def test_none_reads_beyond_the_current_bar(self) -> None:
        """A window at index i must satisfy every strategy without raising.

        Complements the cheating-strategy guard: that proves the guard fires,
        this proves no shipped strategy trips it.
        """
        for name in REGISTRY:
            with self.subTest(strategy=name):
                strat = build(name)
                i = strat.warmup_bars()
                w = BarWindow(
                    self.arrays["ts"], self.arrays["open"], self.arrays["high"],
                    self.arrays["low"], self.arrays["close"], self.arrays["volume"], i,
                )
                try:
                    strat.on_bar(w)
                except LookAheadError as exc:  # pragma: no cover
                    self.fail(f"{name} attempted to read the future: {exc}")

    def test_all_are_deterministic(self) -> None:
        """Two identical runs of each strategy produce identical equity."""
        cfg = EngineConfig(interval="1d")
        for name in REGISTRY:
            with self.subTest(strategy=name):
                a = run_backtest(build(name), self.arrays, cfg)
                b = run_backtest(build(name), self.arrays, cfg)
                np.testing.assert_array_equal(a.equity, b.equity)

    def test_fresh_instance_has_no_leaked_state(self) -> None:
        """Stateful strategies must not carry position state between runs."""
        cfg = EngineConfig(interval="1d")
        for name in REGISTRY:
            with self.subTest(strategy=name):
                first = run_backtest(build(name), self.arrays, cfg)
                # A second, separately-built instance must reproduce run one.
                second = run_backtest(build(name), self.arrays, cfg)
                self.assertAlmostEqual(
                    first.metrics.total_return, second.metrics.total_return, places=12
                )


class TestComposite(unittest.TestCase):
    """The combiner that makes pair/multi-signal testing possible."""

    class _Const:
        """Fixed-output member for exercising the combination modes."""

        def __init__(self, value: float, warm: int = 3) -> None:
            self.value, self._warm = value, warm
            self.name = f"const{value:g}"
            self.params: dict = {"value": value}

        def warmup_bars(self) -> int:
            """Configurable so warm-up propagation can be tested."""
            return self._warm

        def on_bar(self, history: BarWindow) -> float:
            """Always the configured constant."""
            return self.value

    def _window(self) -> BarWindow:
        df = SyntheticLoader(n_bars=50, seed=1).load("SOL", None, None, "1d")
        a = frame_to_arrays(df)
        return BarWindow(a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], 40)

    def test_all_mode_takes_the_minimum(self) -> None:
        """'all' requires agreement, so the weakest member governs."""
        c = Composite([self._Const(1.0), self._Const(0.0)], mode="all")
        self.assertAlmostEqual(c.on_bar(self._window()), 0.0, places=12)

    def test_any_mode_takes_the_maximum(self) -> None:
        """'any' lets a single member trigger."""
        c = Composite([self._Const(1.0), self._Const(0.0)], mode="any")
        self.assertAlmostEqual(c.on_bar(self._window()), 1.0, places=12)

    def test_vote_mode_scales_with_agreement(self) -> None:
        """Two of three members long gives 2/3 exposure."""
        c = Composite(
            [self._Const(1.0), self._Const(1.0), self._Const(0.0)], mode="vote"
        )
        self.assertAlmostEqual(c.on_bar(self._window()), 2.0 / 3.0, places=12)

    def test_mean_mode_preserves_continuous_sizing(self) -> None:
        """'mean' averages fractional members rather than binarising them."""
        c = Composite([self._Const(0.5), self._Const(1.0)], mode="mean")
        self.assertAlmostEqual(c.on_bar(self._window()), 0.75, places=12)

    def test_all_mode_uses_min_not_product(self) -> None:
        """Two half-sized members mean 'both half', not 'one quarter'."""
        c = Composite([self._Const(0.5), self._Const(0.5)], mode="all")
        self.assertAlmostEqual(c.on_bar(self._window()), 0.5, places=12)

    def test_warmup_is_the_longest_member(self) -> None:
        """No member may be consulted before it is fully defined."""
        c = Composite([self._Const(1.0, warm=5), self._Const(1.0, warm=99)], mode="all")
        self.assertEqual(c.warmup_bars(), 99)

    def test_rejects_empty_and_bad_mode(self) -> None:
        """Configuration errors fail at construction."""
        with self.assertRaises(ValueError):
            Composite([], mode="all")
        with self.assertRaises(ValueError):
            Composite([self._Const(1.0)], mode="nonsense")

    def test_registry_composite_runs_end_to_end(self) -> None:
        """A real two-signal composite backtests without error."""
        df = SyntheticLoader(n_bars=600, seed=23).load("SOL", None, None, "1d")
        arrays = frame_to_arrays(df)
        comp = build_composite([("ma_crossover", {}), ("obv_trend", {})], mode="all")
        res = run_backtest(comp, arrays, EngineConfig(interval="1d"))
        self.assertGreater(len(res.equity), 0)
        self.assertIn("ma_crossover", comp.name)

    def test_all_modes_are_reachable(self) -> None:
        """Every advertised mode is accepted."""
        for mode in COMBINE_MODES:
            with self.subTest(mode=mode):
                c = Composite([self._Const(1.0)], mode=mode)
                self.assertTrue(np.isfinite(c.on_bar(self._window())))


if __name__ == "__main__":
    unittest.main(verbosity=2)

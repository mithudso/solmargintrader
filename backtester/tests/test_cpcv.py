"""Known-answer tests for combinatorial purged CV and PBO.

The PBO cases are constructed so the correct answer is known by design: a signal
set where the in-sample winner always wins out-of-sample must yield PBO ~ 0, and
one where in-sample rank carries no information must yield PBO ~ 0.5. Without
those two anchors, a PBO implementation can be arbitrarily wrong and still look
plausible.
"""

from __future__ import annotations

import itertools
import math
import unittest

import numpy as np

from backtester.core.cpcv import (
    CpcvResult,
    cpcv_evaluate,
    evaluate_block,
    make_groups,
    pbo_cscv,
)
from backtester.core.data import SyntheticLoader, frame_to_arrays
from backtester.core.engine import EngineConfig
from backtester.core.strategies import build
from backtester.core.types import BarWindow


class TestMakeGroups(unittest.TestCase):
    """Partitioning must be exact and near-equal."""

    def test_exact_partition(self) -> None:
        """Blocks tile [0, n) with no gap and no overlap."""
        for n, g in ((100, 5), (1875, 8), (37, 4), (8823, 10)):
            with self.subTest(n=n, g=g):
                b = make_groups(n, g)
                self.assertEqual(len(b), g)
                self.assertEqual(b[0][0], 0)
                self.assertEqual(b[-1][1], n)
                for (s1, e1), (s2, _) in zip(b, b[1:]):
                    self.assertEqual(e1, s2, "blocks must be contiguous")
                self.assertEqual(sum(e - s for s, e in b), n)

    def test_sizes_differ_by_at_most_one(self) -> None:
        """A short tail block would be systematically noisier than the rest."""
        b = make_groups(1875, 8)
        sizes = [e - s for s, e in b]
        self.assertLessEqual(max(sizes) - min(sizes), 1)

    def test_rejects_degenerate(self) -> None:
        """Too few groups, or more groups than bars, is a programming error."""
        with self.assertRaises(ValueError):
            make_groups(100, 1)
        with self.assertRaises(ValueError):
            make_groups(3, 8)


class TestEvaluateBlock(unittest.TestCase):
    """Warm-up isolation is the real leakage vector for fixed-parameter strategies."""

    @classmethod
    def setUpClass(cls) -> None:
        """A series long enough for slow warm-ups."""
        df = SyntheticLoader(n_bars=900, seed=31).load("SOL", None, None, "1d")
        cls.arrays = frame_to_arrays(df)
        cls.cfg = EngineConfig(interval="1d")

    def test_block_without_enough_preceding_history_is_unusable(self) -> None:
        """A block at index 0 cannot warm a 200-bar indicator."""
        b = evaluate_block(lambda: build("sma_regime", window=200), self.arrays, 0, 200, self.cfg)
        self.assertFalse(b.usable)
        self.assertIn("warm-up", b.reason)

    def test_block_with_enough_preceding_history_is_usable(self) -> None:
        """Given 200 preceding bars, the same block evaluates."""
        b = evaluate_block(
            lambda: build("sma_regime", window=200), self.arrays, 300, 500, self.cfg
        )
        self.assertTrue(b.usable, b.reason)
        # Measured region is the block itself, so returns has len(block)-1 entries.
        self.assertEqual(b.returns.size, 200 - 1)

    def test_measured_region_excludes_warmup(self) -> None:
        """Returns cover only [start, end), never the warm-up lead."""
        for start, end in ((300, 400), (500, 700)):
            with self.subTest(start=start):
                b = evaluate_block(
                    lambda: build("ma_crossover", fast=20, slow=50),
                    self.arrays, start, end, self.cfg,
                )
                self.assertTrue(b.usable, b.reason)
                self.assertEqual(b.returns.size, (end - start) - 1)

    def test_no_state_leaks_between_blocks(self) -> None:
        """A stateful strategy evaluated twice on one block gives one answer."""
        mk = lambda: build("rsi", period=14)
        a = evaluate_block(mk, self.arrays, 400, 600, self.cfg)
        b = evaluate_block(mk, self.arrays, 400, 600, self.cfg)
        np.testing.assert_array_equal(a.returns, b.returns)

    def test_too_short_block_is_unusable(self) -> None:
        """Fewer than 3 bars cannot produce a return series."""
        b = evaluate_block(lambda: build("buy_and_hold"), self.arrays, 500, 502, self.cfg)
        self.assertFalse(b.usable)


class TestCpcvEvaluate(unittest.TestCase):
    """Path construction and the distribution summary."""

    @classmethod
    def setUpClass(cls) -> None:
        """Real-ish series with enough bars for 8 groups."""
        df = SyntheticLoader(n_bars=1200, seed=5).load("SOL", None, None, "1d")
        cls.arrays = frame_to_arrays(df)
        cls.cfg = EngineConfig(interval="1d")

    def test_path_count_is_n_choose_k(self) -> None:
        """Every combination of usable blocks becomes one path."""
        r = cpcv_evaluate(
            "bh", lambda: build("buy_and_hold"), self.arrays, self.cfg,
            n_groups=8, k_test=2,
        )
        self.assertFalse(r.insufficient, r.reason)
        self.assertEqual(r.n_paths, math.comb(r.usable_blocks, 2))
        self.assertEqual(r.path_sharpes.size, r.n_paths)

    def test_k_three_gives_more_paths_than_k_two(self) -> None:
        """C(n,3) > C(n,2) for n >= 5."""
        a = cpcv_evaluate("bh", lambda: build("buy_and_hold"), self.arrays, self.cfg, 8, 2)
        b = cpcv_evaluate("bh", lambda: build("buy_and_hold"), self.arrays, self.cfg, 8, 3)
        self.assertGreater(b.n_paths, a.n_paths)

    def test_quantiles_are_ordered(self) -> None:
        """q1 <= median <= q3 always."""
        r = cpcv_evaluate("bh", lambda: build("buy_and_hold"), self.arrays, self.cfg, 8, 2)
        self.assertLessEqual(r.q1_sharpe, r.median_sharpe)
        self.assertLessEqual(r.median_sharpe, r.q3_sharpe)
        self.assertGreaterEqual(r.spread, 0.0)

    def test_frac_positive_is_a_fraction(self) -> None:
        """Stability measure must lie in [0, 1]."""
        r = cpcv_evaluate("bh", lambda: build("buy_and_hold"), self.arrays, self.cfg, 8, 2)
        self.assertGreaterEqual(r.frac_positive, 0.0)
        self.assertLessEqual(r.frac_positive, 1.0)

    def test_slow_strategy_on_short_series_is_flagged_not_silently_wrong(self) -> None:
        """A 200-bar warm-up against 8 groups of a short series must be reported.

        This is the mechanism that surfaces "the long horizon is unanswerable on
        this data" rigorously instead of emitting a confident wrong number.
        """
        short = {k: v[:600] for k, v in self.arrays.items()}
        r = cpcv_evaluate(
            "slow", lambda: build("ts_momentum", window=200), short, self.cfg,
            n_groups=8, k_test=2,
        )
        # 600/8 = 75-bar blocks; a 201-bar warm-up needs 201 preceding bars, so
        # the early blocks cannot be evaluated at all.
        self.assertLess(r.usable_blocks, 8)
        if r.insufficient:
            self.assertTrue(r.reason)

    def test_insufficient_when_series_too_short_for_groups(self) -> None:
        """Fewer bars than groups is reported, not raised."""
        tiny = {k: v[:5] for k, v in self.arrays.items()}
        r = cpcv_evaluate("bh", lambda: build("buy_and_hold"), tiny, self.cfg, 8, 2)
        self.assertTrue(r.insufficient)
        self.assertEqual(r.n_paths, 0)

    def test_deterministic(self) -> None:
        """Same inputs give the same distribution."""
        a = cpcv_evaluate("x", lambda: build("macd"), self.arrays, self.cfg, 8, 2)
        b = cpcv_evaluate("x", lambda: build("macd"), self.arrays, self.cfg, 8, 2)
        np.testing.assert_array_equal(a.path_sharpes, b.path_sharpes)


class TestPboCscv(unittest.TestCase):
    """PBO against constructed cases whose answers are known by design."""

    @staticmethod
    def _blocks(values: list[float], n: int = 8, size: int = 50) -> list[np.ndarray]:
        """n blocks of constant per-bar return, one constant per block."""
        return [np.full(size, v) for v in values]

    def test_consistent_winner_gives_low_pbo(self) -> None:
        """If one config dominates every block, in-sample rank generalises."""
        rng = np.random.default_rng(1)
        good = [rng.normal(0.004, 0.01, 60) for _ in range(8)]
        bad = [rng.normal(-0.004, 0.01, 60) for _ in range(8)]
        worse = [rng.normal(-0.008, 0.01, 60) for _ in range(8)]
        out = pbo_cscv({"good": good, "bad": bad, "worse": worse})
        self.assertLess(out["pbo"], 0.25, f"expected low PBO, got {out}")
        self.assertGreater(out["n_splits"], 0)

    def test_pure_noise_gives_pbo_near_one_half_on_average(self) -> None:
        """With no real signal, in-sample selection is a coin flip on average.

        Averaged over seeds, not asserted per-seed. Single-realization PBO has
        enormous spread (measured 0.03 to 0.97 across 30 seeds) because the 70
        splits of 8 blocks are highly dependent: one outlier block makes a
        configuration win every split that block lands in train, and lose every
        split it lands in test. Averaged over realizations the estimator sits on
        its theoretical 0.5. A per-seed band would be a flaky assertion about
        sampling luck rather than about the estimator.
        """
        vals = []
        for seed in range(30):
            rng = np.random.default_rng(seed)
            configs = {
                f"n{i}": [rng.normal(0.0, 0.01, 60) for _ in range(8)]
                for i in range(12)
            }
            vals.append(pbo_cscv(configs)["pbo"])
        mean_pbo = float(np.mean(vals))
        self.assertGreater(mean_pbo, 0.35, f"mean PBO on noise was {mean_pbo:.3f}")
        self.assertLess(mean_pbo, 0.65, f"mean PBO on noise was {mean_pbo:.3f}")

    def test_pbo_discriminates_signal_from_noise(self) -> None:
        """The load-bearing property: PBO must separate real edge from luck.

        A configuration set with genuinely ordered means should yield PBO near
        0, and identically-distributed noise should yield far higher PBO. If
        this fails, PBO carries no information regardless of its absolute value.
        """
        def mean_pbo(mu_step: float) -> float:
            out = []
            for seed in range(15):
                rng = np.random.default_rng(seed)
                cfgs = {
                    f"c{i}": [rng.normal(mu_step * i, 0.01, 60) for _ in range(8)]
                    for i in range(12)
                }
                out.append(pbo_cscv(cfgs)["pbo"])
            return float(np.mean(out))

        noise = mean_pbo(0.0)
        signal = mean_pbo(0.0008)
        self.assertLess(signal, 0.10, f"real signal should generalise, got {signal:.3f}")
        self.assertGreater(
            noise, signal + 0.25,
            f"PBO failed to discriminate: noise {noise:.3f} vs signal {signal:.3f}",
        )

    def test_requires_matching_block_counts(self) -> None:
        """A split must be comparable across configurations."""
        with self.assertRaises(ValueError):
            pbo_cscv({"a": self._blocks([0.1] * 8), "b": self._blocks([0.1] * 6, n=6)})

    def test_too_few_blocks_returns_nan(self) -> None:
        """Under 4 blocks there is no meaningful half-split."""
        out = pbo_cscv({"a": self._blocks([0.1] * 3), "b": self._blocks([0.2] * 3)})
        self.assertTrue(math.isnan(out["pbo"]))

    def test_single_config_returns_nan(self) -> None:
        """PBO is about selection among alternatives; one config has none."""
        out = pbo_cscv({"only": self._blocks([0.1] * 8)})
        self.assertTrue(math.isnan(out["pbo"]))

    def test_split_cap_is_respected(self) -> None:
        """max_splits bounds the enumeration for large block counts."""
        rng = np.random.default_rng(3)
        configs = {f"c{i}": [rng.normal(0, 0.01, 30) for _ in range(12)] for i in range(4)}
        out = pbo_cscv(configs, max_splits=25)
        self.assertLessEqual(out["n_splits"], 25)

    def test_pbo_is_a_probability(self) -> None:
        """Result must lie in [0, 1]."""
        rng = np.random.default_rng(11)
        configs = {f"c{i}": [rng.normal(0.001 * i, 0.01, 40) for _ in range(8)] for i in range(6)}
        out = pbo_cscv(configs)
        self.assertGreaterEqual(out["pbo"], 0.0)
        self.assertLessEqual(out["pbo"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

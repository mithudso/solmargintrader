"""Tests for the Deflated Sharpe Ratio.

The first test is the one that matters: it pins the implementation to a figure the
source paper states in prose, so the formula cannot drift into something plausible but
wrong. Bailey & López de Prado report that at N=1,000 independent trials with unit
cross-sectional variance and zero mean, the expected maximum Sharpe is **3.26**. If that
test fails, every other number this module produces is worthless.

The rest check the reductions to results that are known independently: the PSR
denominator collapsing to Lo's (2002) standard error under normality, monotonicity in N,
and the refusals.
"""

from __future__ import annotations

import math
import unittest
from statistics import NormalDist

import numpy as np

from backtester.core.deflated_sharpe import (
    EULER_MASCHERONI,
    DeflatedSharpeError,
    deannualise,
    deflated_sharpe_ratio,
    effective_trials,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    trial_sharpe_variance,
)


class TestExpectedMaxSharpe(unittest.TestCase):
    def test_it_reproduces_the_figure_the_paper_states(self) -> None:
        # THE anchor. The paper: "after only 1,000 independent backtests ... the
        # expected maximum Sharpe Ratio is 3.26" at zero mean and unit variance.
        got = expected_max_sharpe(1000, 1.0)
        self.assertAlmostEqual(got, 3.26, places=2)
        self.assertAlmostEqual(got, 3.2551, places=3)

    def test_the_benchmark_grows_with_the_size_of_the_search(self) -> None:
        # The whole point: trying more things raises the bar a result must clear.
        values = [expected_max_sharpe(n, 1.0) for n in (2, 10, 25, 100, 1000, 10_000)]
        for earlier, later in zip(values, values[1:]):
            self.assertLess(earlier, later)

    def test_it_scales_with_the_spread_of_the_trials(self) -> None:
        # E[max] is linear in the standard deviation of the trial Sharpes.
        one = expected_max_sharpe(100, 1.0)
        four = expected_max_sharpe(100, 4.0)
        self.assertAlmostEqual(four, 2.0 * one, places=9)

    def test_zero_dispersion_means_no_selection_bias(self) -> None:
        # If every trial posted the same Sharpe, picking the best of them selected
        # nothing, so the benchmark is just the mean.
        self.assertAlmostEqual(expected_max_sharpe(500, 0.0, trial_mean=0.4), 0.4, places=12)

    def test_the_mean_shifts_the_benchmark(self) -> None:
        base = expected_max_sharpe(100, 1.0)
        self.assertAlmostEqual(expected_max_sharpe(100, 1.0, trial_mean=0.3), base + 0.3, places=9)

    def test_it_matches_the_formula_term_by_term(self) -> None:
        # Independent re-derivation, so a typo in one place cannot pass.
        n, var, g, Z = 137.0, 0.25, EULER_MASCHERONI, NormalDist().inv_cdf
        want = math.sqrt(var) * ((1 - g) * Z(1 - 1 / n) + g * Z(1 - 1 / (n * math.e)))
        self.assertAlmostEqual(expected_max_sharpe(n, var), want, places=12)

    def test_a_single_trial_is_refused(self) -> None:
        # N=1 evaluates the inverse normal CDF at 0, and there is no selection bias
        # in a search of one.
        for bad in (1, 0, -5, float("nan"), float("inf")):
            with self.assertRaises(DeflatedSharpeError):
                expected_max_sharpe(bad, 1.0)

    def test_a_negative_variance_is_refused(self) -> None:
        for bad in (-1.0, float("nan"), float("inf")):
            with self.assertRaises(DeflatedSharpeError):
                expected_max_sharpe(100, bad)


class TestProbabilisticSharpe(unittest.TestCase):
    def test_under_normality_it_reduces_to_lo_2002(self) -> None:
        # skew=0, kurtosis=3 must give the classic sqrt((1 + SR^2/2)/(T-1)) error.
        sr, t = 0.15, 500
        want = NormalDist().cdf(sr * math.sqrt(t - 1) / math.sqrt(1 + sr**2 / 2))
        self.assertAlmostEqual(probabilistic_sharpe_ratio(sr, t), want, places=12)

    def test_a_sharpe_equal_to_the_benchmark_is_a_coin_flip(self) -> None:
        self.assertAlmostEqual(
            probabilistic_sharpe_ratio(0.2, 400, benchmark=0.2), 0.5, places=12
        )

    def test_more_observations_raise_confidence_in_the_same_sharpe(self) -> None:
        short = probabilistic_sharpe_ratio(0.1, 60)
        long = probabilistic_sharpe_ratio(0.1, 2000)
        self.assertLess(short, long)

    def test_negative_skew_and_fat_tails_reduce_confidence(self) -> None:
        # The correction the plain Sharpe ratio misses: the same Sharpe earned with a
        # left tail is weaker evidence.
        plain = probabilistic_sharpe_ratio(0.2, 500)
        skewed = probabilistic_sharpe_ratio(0.2, 500, skew=-1.5, kurtosis=3.0)
        fat = probabilistic_sharpe_ratio(0.2, 500, skew=0.0, kurtosis=9.0)
        self.assertLess(skewed, plain)
        self.assertLess(fat, plain)

    def test_it_refuses_a_non_positive_implied_variance(self) -> None:
        # Rather than returning a probability derived from a negative variance.
        with self.assertRaises(DeflatedSharpeError):
            probabilistic_sharpe_ratio(2.0, 500, skew=5.0, kurtosis=1.0)

    def test_too_few_observations_is_refused(self) -> None:
        for bad in (1, 0, -3):
            with self.assertRaises(DeflatedSharpeError):
                probabilistic_sharpe_ratio(0.1, bad)


class TestDeflatedSharpe(unittest.TestCase):
    def test_a_best_of_many_sharpe_can_fail_against_zero_beating_evidence(self) -> None:
        # The headline behaviour. A Sharpe that looks clearly positive against a
        # benchmark of zero can be unremarkable against the expected maximum.
        sr, t = 0.12, 300
        naive = probabilistic_sharpe_ratio(sr, t)             # benchmark 0
        r = deflated_sharpe_ratio(sr, t, n_trials=1000, trial_variance=0.02)
        self.assertGreater(naive, 0.95, "against zero this looks strong")
        self.assertLess(r.deflated_sharpe, naive)
        self.assertFalse(r.survives)
        self.assertGreater(r.benchmark_sharpe, sr)

    def test_a_genuinely_strong_result_still_survives(self) -> None:
        r = deflated_sharpe_ratio(0.5, 2000, n_trials=25, trial_variance=0.01)
        self.assertTrue(r.survives)
        self.assertGreater(r.deflated_sharpe, 0.99)

    def test_the_haircut_grows_with_the_search(self) -> None:
        small = deflated_sharpe_ratio(0.2, 500, n_trials=10, trial_variance=0.05)
        large = deflated_sharpe_ratio(0.2, 500, n_trials=5000, trial_variance=0.05)
        self.assertLess(large.deflated_sharpe, small.deflated_sharpe)
        self.assertGreater(large.haircut, small.haircut)

    def test_the_result_carries_every_input_needed_to_check_it(self) -> None:
        r = deflated_sharpe_ratio(0.3, 800, n_trials=50, trial_variance=0.03,
                                  skew=-0.4, kurtosis=4.5)
        d = r.to_dict()
        for key in ("sharpe", "benchmark_sharpe", "deflated_sharpe", "n_trials",
                    "n_obs", "trial_sharpe_variance", "skew", "kurtosis", "survives"):
            self.assertIn(key, d)
        self.assertEqual(d["n_trials"], 50)
        self.assertEqual(d["skew"], -0.4)


class TestUnitsAndHelpers(unittest.TestCase):
    def test_deannualise_inverts_the_usual_annualisation(self) -> None:
        # An annual Sharpe of 1.5 on daily bars is a small per-bar Sharpe.
        self.assertAlmostEqual(deannualise(1.5, 365.0), 1.5 / math.sqrt(365.0), places=12)
        self.assertAlmostEqual(deannualise(2.0, 4.0), 1.0, places=12)

    def test_deannualise_refuses_unusable_input(self) -> None:
        for sr, ppy in ((float("nan"), 252.0), (1.0, 0.0), (1.0, -4.0), (float("inf"), 252.0)):
            with self.assertRaises(DeflatedSharpeError):
                deannualise(sr, ppy)

    def test_trial_variance_ignores_non_finite_entries(self) -> None:
        got = trial_sharpe_variance([0.1, 0.2, 0.3, float("nan")])
        self.assertAlmostEqual(got, float(np.var([0.1, 0.2, 0.3], ddof=1)), places=12)

    def test_trial_variance_needs_at_least_two_finite_trials(self) -> None:
        with self.assertRaises(DeflatedSharpeError):
            trial_sharpe_variance([0.2, float("nan")])

    def test_effective_trials_discounts_a_known_duplicate_pair(self) -> None:
        # This repo's real case: 25 registered strategies, of which bb_reversion and
        # zscore are one hypothesis, so the search had 24 independent trials.
        self.assertEqual(effective_trials(25, [2]), 24.0)
        self.assertEqual(effective_trials(25), 25.0)
        self.assertEqual(effective_trials(25, [3, 2]), 22.0)

    def test_a_smaller_effective_n_understates_the_haircut(self) -> None:
        # Which is why effective_trials is documented as a floor on the correction:
        # collapsing duplicates lowers N, and a lower N is a gentler benchmark.
        raw = expected_max_sharpe(25, 0.05)
        collapsed = expected_max_sharpe(effective_trials(25, [2]), 0.05)
        self.assertLess(collapsed, raw)

    def test_effective_trials_refuses_nonsense(self) -> None:
        for args in ((0, ()), (25, [1]), (25, [0]), (2, [3])):
            with self.assertRaises(DeflatedSharpeError):
                effective_trials(*args)


if __name__ == "__main__":
    unittest.main()

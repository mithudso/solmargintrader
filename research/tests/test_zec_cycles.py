"""Cycle inference must recover clocks without inventing them in price trends."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from research.zec_cycles import (
    Spectrum,
    fit_forecast,
    holm,
    null_test,
    pivots,
    surrogate_paths,
)


class CycleTests(unittest.TestCase):
    def test_known_harmonic_recovered_with_missing_observations_and_linear_drift(self):
        ts = np.arange(1440) * 60
        y = 4 + np.arange(1440) * 0.0002 + 0.02 * np.sin(2 * np.pi * ts / 7200)
        keep = np.ones(1440, bool)
        keep[[12, 48, 730, 731, 1101]] = False
        basis = Spectrum(ts[keep], 60, 86400)
        power = basis.power(y[keep])[0]
        self.assertAlmostEqual(basis.periods[np.argmax(power)], 7200)
        self.assertGreater(power.max(), 0.999999)

    def test_linear_trend_has_no_oscillatory_explanatory_power(self):
        ts = np.arange(100) * 60
        result = Spectrum(ts, 60).power(4 + ts * 0.0001)
        self.assertLess(result.max(), 1e-3)

    def test_spectrum_matches_independent_nested_regression(self):
        rng = np.random.default_rng(72)
        ts = np.arange(300) * 300
        y = 4 + np.cumsum(rng.normal(0, 0.01, 300))
        periods = np.array([6000.0, 12000.0, 18000.0])
        basis = Spectrum(ts, 300, periods=periods)
        baseline = np.column_stack([np.ones(300), ts / 90000])
        residual = y - baseline @ np.linalg.lstsq(baseline, y, rcond=None)[0]
        for i, period in enumerate(periods):
            design = np.column_stack(
                [
                    baseline,
                    np.cos(2 * np.pi * ts / period),
                    np.sin(2 * np.pi * ts / period),
                ]
            )
            error = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
            expected = 1 - (error @ error) / (residual @ residual)
            self.assertAlmostEqual(basis.power(y)[0, i], expected, places=10)

    def test_holm_is_monotone_and_corrects_every_search(self):
        np.testing.assert_allclose(holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])
        np.testing.assert_allclose(holm([0.001, 1, 0.2]), [0.003, 1, 0.4])

    def test_surrogates_preserve_magnitudes_or_exact_return_multiset(self):
        ts = np.arange(100) * 60
        y = np.random.default_rng(2).normal(size=100).cumsum()
        drift = (y[-1] - y[0]) / (ts[-1] - ts[0])
        centered = np.diff(y) - drift * 60
        for mode in ("random_sign", "block_permutation"):
            paths = surrogate_paths(ts, y, 5, np.random.default_rng(33), mode)
            for row in np.diff(paths) - drift * 60:
                if mode == "random_sign":
                    np.testing.assert_allclose(
                        np.abs(row), np.abs(centered), atol=1e-12
                    )
                else:
                    np.testing.assert_allclose(
                        np.sort(row), np.sort(centered), atol=1e-12
                    )

    def test_pivot_is_not_known_until_reversal_confirmation(self):
        y = np.array([0, 0.01, 0.03, 0.02, 0, -0.03, -0.02, 0, 0.04, 0.02, 0])
        points = pivots(y, 0.02)
        self.assertTrue(all(p["index"] < p["confirmed_index"] for p in points))
        for end in range(3, len(y)):
            prefix = pivots(y[:end], 0.02)
            self.assertEqual(prefix, [p for p in points if p["confirmed_index"] < end])

    def test_forecast_cannot_read_future_test_prices(self):
        ts = np.arange(400) * 300
        prices = np.exp(4 + 0.01 * np.sin(2 * np.pi * ts / 12000))
        frame = pd.DataFrame({"timestamp": ts, "close": prices})
        first = fit_forecast(frame.iloc[:300], frame.iloc[300:], 300)
        poison = frame.iloc[300:].copy()
        poison["close"] *= np.arange(1, 101)
        second = fit_forecast(frame.iloc[:300], poison, 300)
        for name in ("cycle", "linear", "persistence"):
            np.testing.assert_array_equal(first[name], second[name])

    def test_known_cycle_beats_search_adjusted_no_clock_surrogates(self):
        ts = np.arange(500) * 60
        p = 4 + 0.1 * np.sin(2 * np.pi * np.arange(500) / 50)
        rows, *_ = null_test(ts, p, 60, replicates=199)
        self.assertEqual(rows[0]["period_minutes"], 50)
        self.assertLessEqual(rows[0]["p_conservative"], 0.01)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import unittest

import numpy as np

from research import scalp_1s_features as F
from research import scalp_1s_study as S


def synthetic_segment(n: int = 700, seed: int = 7) -> dict:
    rng = np.random.default_rng(seed)
    times = 1_800_000_000 + np.sort(rng.uniform(0, n, size=2 * n))
    prices = 100.0 * np.exp(np.cumsum(rng.normal(0, 2e-5, size=times.size)))
    (segment,) = F.second_bars(times, prices, max_gap_s=10)
    return segment


class ScalpFeatureTests(unittest.TestCase):
    def test_no_feature_reads_a_later_bar(self):
        segment = synthetic_segment()
        full = F.feature_table(segment)
        for cut in (350, 500, 699):
            part = {key: value[:cut] for key, value in segment.items()}
            table = F.feature_table(part)
            for name, values in table.items():
                np.testing.assert_allclose(
                    values,
                    full[name][:cut],
                    rtol=1e-9,
                    atol=1e-12,
                    equal_nan=True,
                    err_msg=f"{name} at prefix {cut}",
                )

    def test_a_changed_future_cannot_move_an_earlier_reading(self):
        segment = synthetic_segment()
        before = F.feature_table(segment)
        changed = {key: value.copy() for key, value in segment.items()}
        for key in ("open", "high", "low", "close"):
            changed[key][600:] *= 1.5
        after = F.feature_table(changed)
        for name in before:
            np.testing.assert_array_equal(
                before[name][:600], after[name][:600], err_msg=name
            )

    def test_second_bars_fill_short_silences_and_split_long_ones(self):
        times = np.array([10.2, 10.8, 11.1, 14.0, 20.0, 20.5, 21.0])
        prices = np.array([100.0, 101.0, 99.0, 98.0, 97.0, 96.0, 95.0])
        first, second = F.second_bars(times, prices)
        self.assertEqual(first["time"].tolist(), [10, 11, 12, 13, 14])
        self.assertEqual(first["close"].tolist(), [101.0, 99.0, 99.0, 99.0, 98.0])
        self.assertEqual(first["open"].tolist(), [100.0, 99.0, 99.0, 99.0, 98.0])
        self.assertEqual(first["high"][0], 101.0)
        self.assertEqual(first["filled"].tolist(), [False, False, True, True, False])
        self.assertEqual(second["time"].tolist(), [20, 21])
        self.assertEqual(second["close"].tolist(), [96.0, 95.0])
        self.assertEqual(F.second_bars([], []), [])
        with self.assertRaises(ValueError):
            F.second_bars([2.0, 1.0], [1.0, 1.0])
        with self.assertRaises(ValueError):
            F.second_bars([1.0, 2.0], [1.0, -1.0])

    def test_breakout_compares_with_the_prior_window_only(self):
        flat = np.full(22, 100.0)
        up = flat.copy()
        up[-1] = 101.0
        self.assertEqual(F.breakout(up, up, up, 20)[-1], 1.0)
        self.assertEqual(F.breakout(flat, flat, flat, 20)[-1], 0.0)
        self.assertTrue(math.isnan(F.breakout(flat, flat, flat, 20)[19]))

    def test_slope_and_curvature_recover_a_line_and_a_parabola(self):
        x = np.arange(60, dtype=float)
        line = 100.0 + 0.5 * x
        self.assertAlmostEqual(
            F.slope_bps(line, 20)[-1], 0.5 / line[-1] * 1e4, places=9
        )
        self.assertAlmostEqual(F.curvature_bps(line, 20)[-1], 0.0, places=9)
        parabola = 1000.0 + (x - 30.0) ** 2
        self.assertAlmostEqual(
            F.curvature_bps(parabola, 20)[-1] * parabola[-1] / 1e4, 2.0, places=9
        )
        self.assertTrue(math.isnan(F.slope_bps(line, 20)[18]))

    def test_sign_runs_time_only_whole_runs(self):
        values = [1, 1, 1, -1, -1, 0, -1, 2, 2, -3]
        self.assertEqual(F.sign_runs(values), [(-1, 4), (1, 2)])
        self.assertEqual(F.sign_runs([1, 1, 1]), [])
        self.assertEqual(F.sign_runs([np.nan, 1, np.nan, -1, 1]), [(-1, 1)])

    def test_vote_has_a_dead_band_and_keeps_missing_values_missing(self):
        out = F.vote([1.0, -2.0, 0.0, F.VOTE_EPSILON / 2, np.nan])
        self.assertEqual(out[:4].tolist(), [1.0, -1.0, 0.0, 0.0])
        self.assertTrue(math.isnan(out[4]))

    def test_two_bar_waits_for_two_complete_buckets(self):
        time = np.arange(100, 130)
        close = np.r_[
            np.linspace(10, 9, 10), np.linspace(9, 8, 10), np.linspace(8, 9, 10)
        ]
        open_ = np.r_[close[0], close[:-1]]
        out = F.two_bar(time, open_, close, 10)
        self.assertTrue(np.isnan(out[:19]).all())
        self.assertEqual(out[19], 1.0)  # two completed down buckets -> watch up
        self.assertEqual(out[28], 1.0)
        self.assertEqual(out[29], 0.0)  # the newest pair is down then up


class ScalpStudyTests(unittest.TestCase):
    def test_the_payout_is_lopsided_and_liquidates_near_ten_basis_points(self):
        self.assertAlmostEqual(S.payout_pct(0), -2.0, places=6)
        self.assertLess(S.payout_pct(1), 0)
        self.assertAlmostEqual(S.payout_pct(-5), -52.0, places=6)
        self.assertGreater(S.payout_pct(5), 20)
        self.assertLess(S.payout_pct(5), 30)
        self.assertEqual(S.payout_pct(-9.8), -100.0)
        self.assertGreater(S.payout_pct(-9.7), -100.0)

    def test_a_split_never_contains_a_label_that_ends_outside_it(self):
        n = 1000
        frame = {
            "time": np.arange(n),
            "fwd": np.arange(n, dtype=float),
            "features": {"x": np.ones(n)},
        }
        frame["fwd"][n - S.HORIZON :] = np.nan
        _, _, train = S.stack([frame], ["x"], 0.0, 0.6, (0, n - 1))
        _, _, test = S.stack([frame], ["x"], 0.6, 1.0, (0, n - 1))
        boundary = 0.6 * (n - 1)
        self.assertLess(train.max() + S.HORIZON, boundary)
        self.assertGreaterEqual(test.min(), boundary)
        self.assertEqual(len(set(train) & set(test)), 0)

    def test_score_counts_overlapping_bars_as_one_sample_per_horizon(self):
        rng = np.random.default_rng(3)
        x = rng.normal(size=6000)
        y = x + rng.normal(size=6000)
        result = S.score(x, y)
        self.assertGreater(result["hit_follow"], 0.6)
        self.assertAlmostEqual(
            result["hit_se"], math.sqrt(0.25 / (6000 / S.HORIZON)), places=6
        )
        self.assertEqual(S.score(np.zeros(5000), y[:5000]), {"n": 5000})

    def test_every_tile_names_a_feature_the_table_produces(self):
        table = F.feature_table(synthetic_segment(400))
        for _, feature, _ in S.TILES:
            self.assertIn(feature, table)
        self.assertEqual(len({key for key, _, _ in S.TILES}), 16)
        for window in F.SLOPE_WINDOWS:
            self.assertIn(f"lsl_{window}", table)
            self.assertIn(f"acc_{window}", table)


if __name__ == "__main__":
    unittest.main()

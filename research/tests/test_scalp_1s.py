from __future__ import annotations

import math
import unittest

import numpy as np

from research import scalp_1s_experiments as X
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


def _frame(close, start=1_800_000_000):
    """A one-segment frame from closes, shaped like the study's, with every variant's vote attached."""
    close = np.asarray(close, dtype=np.float64)
    open_ = np.concatenate([close[:1], close[:-1]])
    seg = {
        "time": np.arange(start, start + close.size, dtype=np.int64),
        "open": open_,
        "high": np.maximum(open_, close),
        "low": np.minimum(open_, close),
        "close": close,
    }
    fwd = np.full(close.size, np.nan)
    fwd[: close.size - S.HORIZON] = (
        close[S.HORIZON :] / close[: -S.HORIZON] - 1.0
    ) * 1e4
    frame = {**seg, "fwd": fwd}
    X.variant_votes([frame])
    return frame


def _walk(n, seed):
    rng = np.random.default_rng(seed)
    return 100.0 * np.exp(
        np.cumsum(rng.normal(0.0, 2e-5, n) + 4e-6 * np.sin(np.arange(n) / 40.0))
    )


class ScalpExperimentTests(unittest.TestCase):
    def test_the_grid_is_unique_and_covers_every_tile(self):
        ids = [variant["id"] for variant in F.VARIANTS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 300)
        # MACD is tested over at least three dozen pairings of its fast and slow averages.
        macd = [v["params"] for v in F.VARIANTS if v["kind"] == "macd"]
        self.assertGreaterEqual(len({(p["fast"], p["slow"]) for p in macd}), 36)
        self.assertGreaterEqual(len({p["signal"] for p in macd}), 3)
        self.assertTrue(all(p["slow"] > p["fast"] for p in macd))
        for kind in ("psar", "supertrend", "emacross"):
            self.assertGreaterEqual(
                sum(1 for v in F.VARIANTS if v["kind"] == kind), 36, kind
            )
        # No setting needs more bars than the window keeps, and old names lead to new ones.
        self.assertLessEqual(max(v["need"] for v in F.VARIANTS), 900)
        self.assertTrue(set(F.VARIANT_ALIASES.values()) <= set(ids))
        self.assertFalse(set(F.VARIANT_ALIASES) & set(ids))
        self.assertEqual(set(F.TILE_VARIANTS), {key for key, _, _ in S.TILES})
        self.assertTrue(set(F.TILE_VARIANTS.values()) <= set(ids))
        self.assertEqual(len(set(F.TILE_VARIANTS.values())), len(F.TILE_VARIANTS))
        self.assertEqual(
            F.EXPERIMENT_HORIZONS, tuple(sorted(set(F.EXPERIMENT_HORIZONS)))
        )
        self.assertIn(S.HORIZON, F.EXPERIMENT_HORIZONS)

    def test_a_tile_and_its_starting_variant_vote_alike(self):
        frame = _frame(_walk(700, 1))
        seg = {key: frame[key] for key in ("time", "open", "high", "low", "close")}
        table = F.feature_table(seg)
        for key, feature, _ in S.TILES:
            tile = np.nan_to_num(F.vote(table[feature]), nan=0.0)
            variant = frame["variants"][F.TILE_VARIANTS[key]]
            np.testing.assert_array_equal(variant[400:], tile[400:], err_msg=key)

    def test_a_variant_is_silent_until_it_has_its_bars(self):
        frame = _frame(_walk(700, 2))
        for variant in F.VARIANTS:
            self.assertFalse(
                frame["variants"][variant["id"]][: variant["need"] - 1].any(),
                variant["id"],
            )

    def test_the_table_scores_a_vote_against_the_later_close_only(self):
        rising = _frame(100.0 + 0.01 * np.arange(700))
        table = X.experiment_table([rising])
        hit, calls = table["roc_2"][30]
        self.assertEqual(hit, 1.0)
        # 700 bars: two are warm-up, thirty have no outcome yet.
        self.assertEqual(calls, 700 - 2 - 30)
        self.assertEqual(table["roc_2"][300][1], 700 - 2 - 300)
        np.testing.assert_array_equal(
            X.forward_sign(np.array([1.0, 2.0, 2.0, 1.0]), 1), [1, 0, -1, 0]
        )

    def test_the_replay_cannot_see_past_the_slice_it_scores(self):
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        a = _walk(2400, 3)
        b = a.copy()
        # Same market for the first 1,300 seconds, then a different one.
        b[1300:] = b[1299] * np.exp(
            np.cumsum(np.random.default_rng(9).normal(0.0, 6e-5, 1100))
        )
        span = (1_800_000_000, 1_800_000_000 + 2400)
        first = X.replay([[_frame(a)]], slots, prior, S.HORIZON, 0.0, 0.5, span)
        second = X.replay([[_frame(b)]], slots, prior, S.HORIZON, 0.0, 0.5, span)
        self.assertGreater(first["seconds"], 500)
        for name in X.REPLAY_NAMES:
            self.assertEqual(first[name], second[name], name)
        self.assertEqual(first["changes"], second["changes"])
        self.assertEqual(first["switched_share"], second["switched_share"])
        # And the later slice does differ, so the comparison is not vacuous.
        self.assertNotEqual(
            X.replay([[_frame(a)]], slots, prior, S.HORIZON, 0.5, 1.0, span)["plain"],
            X.replay([[_frame(b)]], slots, prior, S.HORIZON, 0.5, 1.0, span)["plain"],
        )

    def test_a_setting_takes_a_slot_only_when_clearly_ahead(self):
        kinds = ["slope", "slope", "slope", "roc", "slope"]
        peers = X.same_kind(kinds)
        prior = np.array([0.52, 0.52, 0.50, 0.52, 0.52])
        horizon = 30
        enough = X.PROMOTE_MIN_EFF * horizon * 6.0

        def run(rates, counts=None, locks=None, assign=(0,), now=10_000, priors=prior):
            calls = np.array(
                counts if counts is not None else [enough] * 5, dtype=float
            )
            hit = np.array(rates) * calls
            return X.find_promotions(
                list(assign),
                hit,
                calls,
                priors,
                peers,
                locks or [-math.inf] * len(assign),
                now,
                horizon,
                "clear",
            )

        self.assertEqual(run([0.50, 0.62, 0.50, 0.50, 0.50]), [(0, 1)])
        # Ahead but not clearly; too few calls on either side; no edge; contradicted by the recording.
        self.assertEqual(run([0.50, 0.53, 0.50, 0.50, 0.50]), [])
        self.assertEqual(
            run(
                [0.50, 0.90, 0.50, 0.50, 0.50],
                counts=[enough, 100, enough, enough, enough],
            ),
            [],
        )
        self.assertEqual(
            run(
                [0.50, 0.90, 0.50, 0.50, 0.50],
                counts=[100, enough, enough, enough, enough],
            ),
            [],
        )
        self.assertEqual(run([0.30, 0.45, 0.30, 0.30, 0.30]), [])
        self.assertEqual(run([0.50, 0.50, 0.62, 0.50, 0.50]), [])
        # Another kind never takes the slot, and a recently changed slot is left alone.
        self.assertEqual(run([0.50, 0.50, 0.50, 0.90, 0.50]), [])
        self.assertEqual(
            run([0.50, 0.62, 0.50, 0.50, 0.50], locks=[10_000 - X.PROMOTE_LOCK_S + 1]),
            [],
        )
        # One setting is never given to two slots.
        self.assertEqual(
            run(
                [0.50, 0.62, 0.50, 0.50, 0.50],
                assign=(0, 2),
                priors=np.array([0.52] * 5),
            ),
            [(0, 1)],
        )
        self.assertAlmostEqual(X.wilson_lower(0.5, 100, 1.96), 0.40383, places=5)
        self.assertEqual(X.wilson_lower(0.6, 0), 0.0)

    def test_the_default_rule_takes_the_highest_estimate_once_known_and_ahead(self):
        self.assertEqual(X.DEFAULT_RULE, "best")
        self.assertEqual(
            (X.BEST_MIN_EFF, X.BEST_LOCK_S, X.BEST_MARGIN), (40, 1800, 0.01)
        )
        self.assertIn(
            (X.BEST_MIN_EFF, X.BEST_LOCK_S, X.BEST_MARGIN), X.BEST_LIMITS_TRIED
        )
        kinds = ["slope", "slope", "slope", "roc", "slope"]
        peers = X.same_kind(kinds)
        np.testing.assert_array_equal(peers[0], [0, 1, 2, 4])
        np.testing.assert_array_equal(peers[3], [3])
        flat = np.full(5, 0.52)
        enough = X.BEST_MIN_EFF * 30 * 6.0

        def run(
            rates,
            counts=None,
            assign=(0,),
            priors=flat,
            locks=None,
            now=10_000,
            limits=None,
        ):
            calls = np.array(counts if counts is not None else [enough] * 5)
            return X.find_promotions(
                list(assign),
                np.array(rates) * calls,
                calls,
                priors,
                peers,
                locks or [-math.inf] * len(assign),
                now,
                30,
                "best",
                limits,
            )

        # Two points ahead is enough: no cautious estimate. The best of several wins.
        self.assertEqual(run([0.52, 0.54, 0.50, 0.50, 0.50]), [(0, 1)])
        self.assertEqual(run([0.50, 0.60, 0.50, 0.90, 0.66]), [(0, 4)])
        # Under a point ahead is not, and nor is a setting level with the one in use.
        self.assertEqual(run([0.52, 0.527, 0.50, 0.50, 0.50]), [])
        self.assertEqual(run([0.70, 0.60, 0.50, 0.50, 0.66]), [])
        self.assertEqual(run([0.55, 0.55, 0.55, 0.50, 0.55]), [])
        # Both settings need their calls first: 40 independent ones' worth, 1,200 at 30 seconds.
        few = [enough, 1199.0, enough, enough, enough]
        self.assertEqual(run([0.50, 0.90, 0.50, 0.50, 0.50], counts=few), [])
        few[1] = 1200.0
        self.assertEqual(run([0.50, 0.90, 0.50, 0.50, 0.50], counts=few), [(0, 1)])
        self.assertEqual(
            run(
                [0.50, 0.90, 0.50, 0.50, 0.50],
                counts=[100.0, enough, enough, enough, enough],
            ),
            [],
        )
        # A slot that just changed keeps its setting for half an hour.
        self.assertEqual(
            run([0.50, 0.60, 0.50, 0.50, 0.50], locks=[10_000 - X.BEST_LOCK_S + 1]),
            [],
        )
        self.assertEqual(
            run([0.50, 0.60, 0.50, 0.50, 0.50], locks=[10_000 - X.BEST_LOCK_S]),
            [(0, 1)],
        )
        # Two slots of one kind take different settings, the first slot the better one.
        self.assertEqual(
            run([0.50, 0.60, 0.50, 0.50, 0.70], assign=(0, 2)), [(0, 4), (1, 1)]
        )
        # With every limit at zero it is the rule with no waiting: the recorded rate alone decides.
        self.assertEqual(
            run(
                [0.0] * 5,
                counts=[0.0] * 5,
                priors=np.array([0.51, 0.5, 0.55, 0.6, 0.5]),
                locks=[10_000],
                limits=(0, 0, 0.0),
            ),
            [(0, 2)],
        )
        with self.assertRaises(ValueError):
            X.find_promotions([0], flat, flat, flat, peers, [0], 0, 30, "sometimes")

    def test_a_reading_under_half_votes_the_other_way_in_the_inverse_aggregate(self):
        # Edges +0.10, +0.05, 0 and -0.10: the last reading says down, so it counts as up.
        self.assertAlmostEqual(
            X.signed_score([0.6, 0.55, 0.5, 0.4], np.array([1.0, 1.0, -1.0, -1.0])), 1.0
        )
        self.assertAlmostEqual(
            X.signed_score([0.6, 0.55, 0.5, 0.4], np.array([1.0, 1.0, 1.0, 1.0])), 0.2
        )
        self.assertIsNone(X.signed_score([0.5, 0.5], np.array([1.0, -1.0])))

    def test_a_switched_setting_without_its_bars_leaves_the_tile_on_the_starting_one(
        self,
    ):
        # Every prior equal except one long MACD. With the rule's limits at zero the MACD tile
        # switches to it at once, long before it has its 270 bars. The grid must still be
        # scored from second 78.
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        prior["macd_20_90_9"] = 0.60
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        frame = _frame(_walk(400, 4))
        out = X.replay([[frame]], slots, prior, S.HORIZON, limits=(0, 0, 0.0))
        warm = max(v["need"] for v in F.VARIANTS if v["id"] in slots)
        scored = int(
            (
                (np.arange(400) + 1 >= warm)
                & (X.forward_sign(frame["close"], S.HORIZON) != 0)
            ).sum()
        )
        self.assertEqual(out["seconds"], scored)
        self.assertIn(
            {
                "time": int(frame["time"][0]),
                "from": "macd_12_26_9",
                "to": "macd_20_90_9",
            },
            out["change_log"]["best"],
        )
        self.assertEqual(out["changes"]["clear"], 0)
        self.assertGreater(out["switched_share"]["best"], 0.0)
        # With the shipped limits nothing has its calls yet in 400 seconds, so nothing switches.
        calm = X.replay([[frame]], slots, prior, S.HORIZON)
        self.assertEqual(calm["changes"]["best"], 0)
        self.assertEqual(calm["best"], calm["weighted"])

    def test_the_rule_is_replayed_under_each_set_of_limits(self):
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        frame = _frame(_walk(3000, 11))
        rows = X.rule_limits(
            {"sample": ([[frame]], prior, 0.0, 1.0, None)}, slots, S.HORIZON
        )
        self.assertEqual(len(rows), len(X.BEST_LIMITS_TRIED))
        self.assertEqual(sum(1 for row in rows if row["shipped"]), 1)
        eager, shipped = rows[0], next(row for row in rows if row["shipped"])
        self.assertEqual(
            (eager["min_eff"], eager["lock_s"], eager["margin"]), (0, 0, 0.0)
        )
        # No waiting switches far more often than the shipped limits do.
        self.assertGreater(
            eager["sample"]["changes"], 10 * max(1, shipped["sample"]["changes"])
        )
        self.assertEqual(eager["sample"]["seconds"], shipped["sample"]["seconds"])

    def test_a_waiting_tile_never_reads_a_setting_another_tile_is_reading(self):
        # Five settings of one kind and one of another. need = bars each must have.
        peers = X.same_kind(["b", "b", "b", "b", "b", "r"])
        need = np.array([21, 61, 451, 6, 500, 3])
        start = np.array([0, 1, 5])
        # Nothing waiting: the choices themselves.
        chosen = np.array([3, 1, 5])
        np.testing.assert_array_equal(
            X.settings_in_effect(chosen, start, need, peers, 100), chosen
        )
        # The first tile waits for setting 2 and falls back to its starting setting 0.
        np.testing.assert_array_equal(
            X.settings_in_effect(np.array([2, 1, 5]), start, need, peers, 100),
            [0, 1, 5],
        )
        # The second tile has taken setting 0, so the waiting first tile reads the next free
        # setting with its bars: 1 is free and has them at 100 bars, and at 50 bars only 3 does.
        crossed = np.array([2, 0, 5])
        np.testing.assert_array_equal(
            X.settings_in_effect(crossed, start, need, peers, 100), [1, 0, 5]
        )
        np.testing.assert_array_equal(
            X.settings_in_effect(crossed, start, need, peers, 50), [3, 0, 5]
        )
        # With its bars the chosen setting is read, and the input is never changed in place.
        np.testing.assert_array_equal(
            X.settings_in_effect(crossed, start, need, peers, 451), [2, 0, 5]
        )
        np.testing.assert_array_equal(crossed, [2, 0, 5])

    def test_betting_against_a_setting_that_was_usually_wrong(self):
        train = {
            "a": {30: [0.46, 1000], 60: [0.55, 1000]},
            "b": {30: [0.49, 1000], 60: [0.52, 1000]},
            "c": {30: [0.55, 1000], 60: [0.47, 1000]},
            "d": {30: [0.40, 10], 60: [None, 0]},
        }
        later = {
            "a": {30: [0.45, 600], 60: [0.5, 600]},
            "b": {30: [0.53, 300], 60: [0.5, 300]},
            "c": {30: [0.60, 600], 60: [0.52, 600]},
            "d": {30: [0.40, 600], 60: [0.5, 600]},
        }
        out = X.inverse_study(train, later, horizons=(30, 60))
        row = out["30"]["under_50"]
        # a and b were under half; d had too few calls to say. Against a: 55% of 600; against b: 47% of 300.
        self.assertEqual([row["settings"], row["of"], row["calls_later"]], [2, 4, 900])
        self.assertAlmostEqual(
            row["inverse_hit_later"], (0.55 * 600 + 0.47 * 300) / 900
        )
        self.assertEqual(row["still_under_50_later"], 1)
        self.assertEqual(row["lowest_hit"], 0.46)
        self.assertEqual(row["best"][0][0], "a")
        self.assertAlmostEqual(row["se"], math.sqrt(0.25 / (600 / 30)))
        self.assertEqual(out["30"]["at_most_48"]["settings"], 1)
        self.assertEqual(out["60"]["under_50"]["best"][0][0], "c")

    def test_the_running_record_fades_then_scores_the_calls_one_horizon_old(self):
        frame = _frame(100.0 + 0.01 * np.arange(200))
        counts = X.decayed_counts(frame, 30)
        decay = math.exp(-math.log(2) / X.WEIGHT_HALF_LIFE_S)
        # Momentum 2s votes up from bar 2; the call at bar i is scored at bar i + 30 and fades after.
        expected = sum(decay ** (199 - (i + 30)) for i in range(2, 170))
        self.assertAlmostEqual(counts["roc_2"][1], expected, places=9)
        self.assertAlmostEqual(counts["roc_2"][0], expected, places=9)
        np.testing.assert_allclose(
            X.weights_of([0.6, 0.55, 0.5, 0.4]), [2 / 3, 1 / 3, 0, 0]
        )
        np.testing.assert_allclose(X.weights_of([0.5, 0.4]), [0.5, 0.5])
        self.assertEqual(
            [X.tier_of(v) for v in (0.8, -0.75, 0.5, -0.375, 0.2)],
            ["strong", "strong", "lean", "lean", "mixed"],
        )

    def test_the_replay_reports_the_path_after_each_tier(self):
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        out = X.replay([[_frame(_walk(3000, 5))]], slots, prior, S.HORIZON)
        for name in X.REPLAY_NAMES:
            for tier, row in out[name].items():
                if "path_bps" not in row:
                    continue
                self.assertEqual(
                    [step for step, _ in row["path_bps"]],
                    list(X.PATH_STEPS),
                    f"{name} {tier}",
                )
                self.assertAlmostEqual(
                    row["path_bps"][-1][1], row["mean_follow_bps"], places=9
                )

    def test_the_rule_fixture_makes_the_switch_rules_choose(self):
        frame = _frame(_walk(420, 6))
        prior = {
            variant["id"]: 0.5 + 0.03 * math.cos(k)
            for k, variant in enumerate(F.VARIANTS)
        }
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        rule = X.rule_fixture(frame, prior, slots, S.HORIZON)
        self.assertEqual(len(rule["weights"]), len(slots))
        self.assertAlmostEqual(sum(rule["weights"]), 1.0, places=9)
        self.assertAlmostEqual(sum(rule["made_up"]["weights"]), 1.0, places=9)
        self.assertTrue(all(value in (-1, 0, 1) for value in rule["votes"]))
        self.assertLessEqual(abs(rule["inverse_score"]), 1.0)
        self.assertEqual(set(rule["switches"]), set(X.RULES))
        for name, switches in rule["switches"].items():
            self.assertGreaterEqual(len(switches), 1, name)
            for start, switched in switches:
                self.assertIn(start, slots)
                self.assertNotIn(switched, slots)
            self.assertEqual(len({switched for _, switched in switches}), len(switches))
        self.assertGreaterEqual(
            len(rule["switches"]["best"]), len(rule["switches"]["clear"])
        )

    def test_the_shipped_model_carries_each_choice_its_own_replayed_record(self):
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        frame = _frame(_walk(3000, 8))
        base = X.replay([[frame]], slots, prior, S.HORIZON)
        measured = {name: X.measured_tiers(base, base, name) for name in X.REPLAY_NAMES}
        table = X.experiment_table([frame])
        usually_wrong = X.inverse_study(table, table)[str(S.HORIZON)]["under_50"]
        model = X.experiments_model(
            [key for key, _, _ in S.TILES],
            table,
            S.HORIZON,
            measured,
            base,
            usually_wrong,
        )
        self.assertEqual(model["version"], 3)
        self.assertEqual(model["promotion"]["rule"], "best")
        self.assertEqual(
            [
                model["promotion"][key]
                for key in ("best_min_eff", "best_lock_s", "best_margin")
            ],
            [X.BEST_MIN_EFF, X.BEST_LOCK_S, X.BEST_MARGIN],
        )
        self.assertEqual(set(model["measured_rules"]), {"clear", "best"})
        self.assertEqual(set(model["measured_inverse"]), {"off", "best"})
        self.assertEqual(model["aliases"], F.VARIANT_ALIASES)
        self.assertEqual(len(model["variants"]), len(F.VARIANTS))
        self.assertEqual(model["replay"]["changes"], base["changes"])
        for tier, row in model["measured"].items():
            self.assertEqual(row["live"]["hit"], base["weighted"][tier]["hit"])
        self.assertIn("inverse_hit_later", model["usually_wrong"])


class ScalpStreakAndFadeTests(unittest.TestCase):
    def _series(self, score, sign, fwd=None, lowest=None, highest=None):
        n = len(score)
        return {
            "group": 0,
            "time": np.arange(1_800_000_000, 1_800_000_000 + n, dtype=np.int64),
            "ready": np.ones(n, dtype=bool),
            "weighted": np.array(score, dtype=float),
            "plain": np.zeros(n),
            "sign": np.array(sign, dtype=float),
            "fwd": np.array(
                fwd if fwd is not None else [float(v) for v in sign], dtype=float
            ),
            "lowest": np.array(
                lowest if lowest is not None else [-1.0] * n, dtype=float
            ),
            "highest": np.array(
                highest if highest is not None else [1.0] * n, dtype=float
            ),
        }

    def test_strong_calls_are_counted_by_their_place_in_a_run(self):
        # Sixty one-second runs, sixty runs of three and sixty of seven, all strong up, spaced by quiet seconds.
        score, sign = [], []
        for length, right in ((1, 1), (3, -1), (7, 1)):
            for _ in range(60):
                score += [0.9] * length + [0.0] * 3
                sign += [right] * length + [0] * 3
        out = X.streaks([self._series(score, sign)], 30)["weighted"]
        self.assertEqual(
            out["runs"],
            {
                "count": 180,
                "mean_s": (60 + 180 + 420) / 180,
                "median_s": 3.0,
                "one_second_only": 60,
            },
        )
        self.assertEqual(
            [out[b]["n"] for b in ("1", "2", "3-5", "6-10", "2+")],
            [180, 120, 60 * 1 + 60 * 3, 60 * 2, 480],
        )
        # The second second in a row: sixty in runs that went against, sixty in runs that went with.
        self.assertAlmostEqual(out["2"]["correct"], 0.5)
        self.assertAlmostEqual(out["2"]["reversed"], 0.5)
        self.assertAlmostEqual(out["6-10"]["correct"], 1.0)
        self.assertEqual(out["11+"], {"n": 0})
        # A lean, or a strong call the other way, breaks the run.
        broken = X.streaks(
            [self._series(([0.9, 0.5, 0.9, -0.9, -0.9] + [0.0] * 5) * 60, [1] * 600)],
            30,
        )["weighted"]
        self.assertEqual([broken[b]["n"] for b in ("1", "2")], [180, 60])
        self.assertAlmostEqual(broken["2"]["correct"], 0.0)

    def test_a_reversal_is_measured_three_ways(self):
        # A strong up call every ten seconds; a strong down call follows forty seconds after every other one.
        n = 1200
        score = np.zeros(n)
        score[::20] = 0.9
        score[40::40] = -0.9
        lowest = np.full(n, -1.0)
        lowest[
            ::80
        ] = -12.0  # some up calls see price fall past the bust distance on the way
        highest = np.full(n, 6.0)  # every down call sees price rise 6 bp on the way
        out = X.streaks(
            [self._series(score, np.sign(score) * -1, lowest=lowest, highest=highest)],
            30,
        )["weighted"]["1"]
        self.assertAlmostEqual(out["reversed"], 1.0)
        self.assertAlmostEqual(out["correct"], 0.0)
        ups = int((score > 0).sum())
        downs = int((score < 0).sum())
        self.assertEqual(out["n"], ups + downs)
        # Up calls at 0, 20, 60, 100...: a down call within sixty seconds follows each of them.
        self.assertGreater(out["flipped_within_60s"], 0.9)
        busted = int(((score > 0) & (lowest <= -9.8)).sum())
        self.assertAlmostEqual(out["adverse_bust"], busted / (ups + downs))
        self.assertAlmostEqual(out["adverse_5bp"], (busted + downs) / (ups + downs))

    def test_the_call_series_is_the_replay_second_by_second(self):
        prior = {variant["id"]: 0.52 for variant in F.VARIANTS}
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        groups = [[_frame(_walk(1500, 11))], [_frame(_walk(1500, 12))]]
        replayed = X.replay(groups, slots, prior, S.HORIZON)
        # A switch changes only the tuned grid; the weighted call keeps the starting one.
        strong = [0, 0]
        for fr in X.call_series(groups, slots, prior, S.HORIZON):
            mask = (
                fr["ready"]
                & (np.abs(fr["weighted"]) >= X.WEIGHTED_STRONG)
                & (fr["sign"] != 0)
            )
            strong[0] += int(mask.sum())
            strong[1] += int((np.sign(fr["weighted"][mask]) == fr["sign"][mask]).sum())
        row = replayed["weighted"]["strong"]
        self.assertEqual(strong[0], row["n"])
        if "hit" in row:
            self.assertAlmostEqual(strong[1] / strong[0], row["hit"], places=12)

    def test_fading_wins_exactly_when_the_reading_was_wrong(self):
        slots = [F.TILE_VARIANTS[key] for key, _, _ in S.TILES]
        frame = _frame(
            100.0 * np.exp(np.cumsum(np.random.default_rng(13).normal(0.0, 2e-5, 8000)))
        )
        out = X.fade([[frame]], slots, S.HORIZON)
        self.assertEqual(len(out["cases"]), len(X.FADE_HALF_LIVES) * len(X.FADE_BELOW))
        for case in out["cases"]:
            for name in ("tiles", "all"):
                row = case[name]
                if row["below_calls"]:
                    self.assertAlmostEqual(
                        row["follow_when_below"] + row["fade_when_below"],
                        1.0,
                        places=12,
                    )
        # One reading, one memory, recomputed call by call from the definition.
        case = next(
            c for c in out["cases"] if c["half_life_s"] == 600 and c["below"] == 0.5
        )
        self.assertTrue(
            case["tiles_each"], "some reading spent time under 50% on a random walk"
        )
        chosen = case["tiles_each"][0][0]
        ids = [variant["id"] for variant in F.VARIANTS]
        _, sign, counted, correct = X.outcomes(frame, ids, S.HORIZON)
        v = ids.index(chosen)
        decay = math.exp(-math.log(2) / 600)
        hit = calls = 0.0
        below = right = 0
        for t in range(sign.size):
            hit *= decay
            calls *= decay
            if t >= S.HORIZON:
                hit += float(correct[t - S.HORIZON, v])
                calls += float(counted[t - S.HORIZON, v])
            if (
                sign[t] != 0
                and counted[t, v]
                and calls >= X.FADE_MIN_CALLS
                and hit / calls < 0.5
            ):
                below += 1
                right += int(correct[t, v])
        mine = [row for row in case["tiles_each"] if row[0] == chosen]
        self.assertGreaterEqual(below, 600)
        self.assertEqual(mine[0][1], below)
        self.assertAlmostEqual(mine[0][2], 1.0 - right / below, places=12)


if __name__ == "__main__":
    unittest.main()

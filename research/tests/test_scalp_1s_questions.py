from __future__ import annotations

import contextlib
import gzip
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from research import scalp_1s_coins as C
from research import scalp_1s_experiments as X
from research import scalp_1s_features as F
from research import scalp_1s_questions as Q
from research import scalp_1s_study as S
from research.tests.test_scalp_1s import _frame, _walk

START = 1_800_000_000
H = Q.HORIZON
READERS = ("breakout_60", "roc_60", "roc_5", "zscore_20")


def _plain(close, votes: dict, start=START):
    """A frame with hand-written votes, for exact counts."""
    close = np.asarray(close, dtype=np.float64)
    fwd = np.full(close.size, np.nan)
    fwd[: close.size - H] = (close[H:] / close[:-H] - 1.0) * 1e4
    return {
        "time": np.arange(start, start + close.size, dtype=np.int64),
        "close": close,
        "fwd": fwd,
        "variants": {k: np.asarray(v, dtype=np.int8) for k, v in votes.items()},
    }


def _series(group, score, sign, start=START):
    n = len(score)
    return {
        "group": group,
        "time": np.arange(start, start + n, dtype=np.int64),
        "ready": np.ones(n, dtype=bool),
        "weighted": np.array(score, dtype=float),
        "sign": np.array(sign, dtype=float),
    }


def _two_markets(seed, n=3000, split_at=1800):
    """Two price paths that are the same up to `split_at` and differ after it."""
    a = _walk(n, seed)
    b = a.copy()
    b[split_at:] = b[split_at - 1] * np.exp(
        np.cumsum(np.random.default_rng(seed + 100).normal(0.0, 6e-5, n - split_at))
    )
    return a, b


class CombinationTests(unittest.TestCase):
    IDS = ("roc_2", "roc_5", "breakout_20", "bop_5", "slope_60")
    SPAN = (START, START + 3000)

    @classmethod
    def setUpClass(cls):
        # Identical for the first 60% (1,800 of 3,000 seconds) and different from the split on.
        a, b = _two_markets(21)
        cls.same, cls.changed = _frame(a), _frame(b)

    def test_a_combination_speaks_only_when_every_member_agrees(self):
        # Price rises throughout, so "up" is always right. 100 seconds, 70 with an outcome.
        n = 100
        a = np.r_[np.ones(40), -np.ones(30), np.zeros(30)]
        b = np.r_[np.ones(20), -np.ones(50), np.ones(30)]
        frame = _plain(100.0 + 0.01 * np.arange(n), {"a": a, "b": b})
        combos, hits, calls, seconds, spoken = Q.agreement_counts(
            [frame], ["a", "b"], 2, [(0.0, 1.0)], None
        )
        self.assertEqual(combos, [(0, 1)])
        self.assertEqual(seconds[0], n - H)
        # Both up for seconds 0-19 (right), both down for 40-69 (wrong); 20-39 they disagree.
        self.assertEqual([calls[0, 0], hits[0, 0]], [50, 20])
        # One market: the seconds it spoke in are its calls.
        self.assertEqual(spoken[0, 0], 50)
        # The same market twice is twice the calls in the same fifty seconds of the clock.
        twice = Q.agreement_counts(
            [frame, dict(frame)], ["a", "b"], 2, [(0.0, 1.0)], None
        )
        self.assertEqual([twice[2][0, 0], twice[4][0, 0]], [100, 50])
        singles = Q.agreement_counts([frame], ["a", "b"], 1, [(0.0, 1.0)], None)
        self.assertEqual(list(singles[2][0]), [70, 70])
        self.assertEqual(list(singles[1][0]), [40, 20])

    def test_the_ranking_is_made_on_the_first_slice_only(self):
        # The two markets part company exactly at the split: nothing after it may reach the ranking.
        first = Q.combination_study([self.same], list(self.IDS), self.SPAN)
        second = Q.combination_study([self.changed], list(self.IDS), self.SPAN)
        for size in ("1", "2", "3"):
            rows_a, rows_b = first["sizes"][size]["top"], second["sizes"][size]["top"]
            self.assertTrue(rows_a)
            self.assertEqual(
                [row["members"] for row in rows_a], [row["members"] for row in rows_b]
            )
            self.assertEqual(
                [row["first"] for row in rows_a], [row["first"] for row in rows_b]
            )
            for key in ("tried", "eligible"):
                self.assertEqual(
                    first["sizes"][size][key], second["sizes"][size][key], key
                )
        self.assertEqual(first["sizes"]["2"]["tried"], 10)
        self.assertNotEqual(
            [row["later"] for row in first["sizes"]["1"]["top"]],
            [row["later"] for row in second["sizes"]["1"]["top"]],
        )

    def test_a_price_jump_at_the_split_cannot_move_anything_learned_before_it(self):
        # Scaling every price from the split on flips the sign of any outcome that reaches past
        # it, whichever way it pointed: one second of overlap would change a first-slice count.
        ids = list(self.IDS)
        path = _walk(3000, 21)
        base = _frame(path)
        ranked = Q.combination_study([base], ids, self.SPAN)
        fitted = Q.fitted_vote([base], ids[:4], self.SPAN)
        for scale in (0.5, 2.0):
            moved = path.copy()
            moved[1800:] *= scale
            frame = _frame(moved)
            again = Q.combination_study([frame], ids, self.SPAN)
            for size in ("1", "2", "3"):
                self.assertEqual(
                    [(r["members"], r["first"]) for r in ranked["sizes"][size]["top"]],
                    [(r["members"], r["first"]) for r in again["sizes"][size]["top"]],
                )
            refit = Q.fitted_vote([frame], ids[:4], self.SPAN)
            self.assertEqual(fitted["largest_weights"], refit["largest_weights"])
            self.assertEqual(fitted["first"], refit["first"])

    def test_a_combination_that_goes_quiet_later_is_still_ranked_and_carries_no_rate(
        self,
    ):
        # "a" and "b" agree and are right throughout the first 60%, then "b" says nothing.
        n = 2000
        close = 100.0 + 0.01 * np.arange(n)
        quiet = np.r_[np.ones(1200), np.zeros(800)]
        votes = {"a": np.ones(n), "b": quiet, "c": -np.ones(n)}
        out = Q.combination_study(
            [_plain(close, votes)], ["a", "b", "c"], (START, START + n)
        )
        top = out["sizes"]["2"]["top"][0]
        self.assertEqual(top["members"], ["a", "b"])
        self.assertEqual(top["first"]["hit"], 1.0)
        self.assertEqual(top["later"], {"calls": 0})
        # The later summary is over combinations with enough later calls only: here none of the pairs.
        self.assertEqual(out["sizes"]["2"]["measured_later"], 0)
        self.assertIsNone(out["sizes"]["2"]["all_later_best"])
        self.assertIsNone(out["sizes"]["2"]["top_later_mean"])
        singles = {
            tuple(row["members"]): row["later"] for row in out["sizes"]["1"]["top"]
        }
        self.assertEqual(singles[("a",)]["hit"], 1.0)
        self.assertEqual(singles[("c",)]["hit"], 0.0)
        self.assertEqual(singles[("a",)]["calls"], 800 - H)

    def test_the_fit_never_sees_the_slice_it_is_scored_on(self):
        ids = list(self.IDS[:4])
        first = Q.fitted_vote([self.same], ids, self.SPAN)
        second = Q.fitted_vote([self.changed], ids, self.SPAN)
        self.assertEqual(first["largest_weights"], second["largest_weights"])
        self.assertEqual(first["first"], second["first"])
        self.assertNotEqual(first["later"], second["later"])
        self.assertAlmostEqual(first["first"]["top"]["share"], 0.2, delta=0.08)
        extra = Q.fitted_vote(
            [self.same], ids, self.SPAN, extra={"other": [self.changed]}
        )
        self.assertEqual(set(extra["other"]), {"all", "top"})

    def test_the_confident_share_is_cut_where_the_first_slice_put_it(self):
        # Four readings that are each right 70% of the time. After the split three of them fall
        # silent: no later score reaches the first slice's cut, so no later second is "confident".
        n = 3000
        rng = np.random.default_rng(7)
        close = _walk(n, 8)
        sign = X.forward_sign(close, H).astype(float)
        votes = {}
        for name in "abcd":
            vote = np.where(rng.random(n) < 0.7, sign, rng.choice([-1.0, 1.0], n))
            if name != "a":
                vote[1800:] = 0
            votes[name] = vote
        out = Q.fitted_vote([_plain(close, votes)], list("abcd"), (START, START + n))
        self.assertGreater(out["first"]["top"]["hit"], 0.7)
        self.assertEqual(out["later"]["top"]["share"], 0.0)
        self.assertIsNone(out["later"]["top"]["hit"])
        self.assertGreater(out["later"]["all"]["n"], 1000)

    def test_a_later_sample_is_scored_with_the_first_slices_weights_and_cut(self):
        n = 3000
        rng = np.random.default_rng(7)
        close = _walk(n, 8)
        sign = X.forward_sign(close, H).astype(float)
        votes = {
            k: np.where(rng.random(n) < 0.7, sign, rng.choice([-1.0, 1.0], n))
            for k in "abcd"
        }
        # The same prices with three of the four readings silent throughout: every score is
        # under the first slice's cut, so none is "confident", whatever that sample's own spread.
        quiet = {k: (v if k == "a" else np.zeros(n)) for k, v in votes.items()}
        out = Q.fitted_vote(
            [_plain(close, votes)],
            list("abcd"),
            (START, START + n),
            extra={"quiet": [_plain(close, quiet)]},
        )
        self.assertGreater(out["quiet"]["all"]["n"], 1000)
        self.assertEqual(out["quiet"]["top"]["share"], 0.0)
        self.assertIsNone(out["quiet"]["top"]["hit"])
        # A sample in which every reading points the wrong way is scored with the weights the
        # first slice gave: it comes out wrong. Fitted on itself it would come out right.
        wrong = {k: -v for k, v in votes.items()}
        turned = Q.fitted_vote(
            [_plain(close, votes)],
            list("abcd"),
            (START, START + n),
            extra={"wrong": [_plain(close, wrong)]},
        )
        self.assertEqual(turned["largest_weights"], out["largest_weights"])
        self.assertLess(turned["wrong"]["all"]["hit"], 0.3)
        self.assertGreater(out["first"]["all"]["hit"], 0.7)

    def test_two_markets_moving_as_one_are_not_two_looks(self):
        # The same market recorded twice gives twice the calls and no more information:
        # the error bar must not shrink.
        ids = list(self.IDS[:3])
        one = Q.combination_study([self.same], ids, self.SPAN)
        two = Q.combination_study([self.same, dict(self.same)], ids, self.SPAN)
        for size in ("1", "2"):
            for a, b in zip(
                one["sizes"][size]["top"], two["sizes"][size]["top"], strict=True
            ):
                self.assertEqual(a["members"], b["members"])
                self.assertEqual(a["later"]["hit"], b["later"]["hit"])
                self.assertEqual(b["later"]["calls"], 2 * a["later"]["calls"])
                self.assertAlmostEqual(a["later"]["se"], b["later"]["se"], places=12)
        fit_one = Q.fitted_vote([self.same], ids, self.SPAN)
        fit_two = Q.fitted_vote([self.same, dict(self.same)], ids, self.SPAN)
        self.assertAlmostEqual(
            fit_one["later"]["all"]["se"], fit_two["later"]["all"]["se"], places=12
        )

    def test_members_are_the_tiles_and_the_best_known_setting_of_each_kind(self):
        enough = Q.MIN_CALLS * H
        table = {v["id"]: {H: [0.5, enough]} for v in F.VARIANTS}
        table["macd_3_17_5"][H] = [0.6, enough]
        table["roc_2"][H] = [0.7, enough]
        # A setting right every time on too few calls is not "the best".
        table["zscore_600"][H] = [1.0, enough - 1]
        table["rsi_120"][H] = [None, 0]
        members = Q.members_for(table)
        self.assertEqual(members[:16], [F.TILE_VARIANTS[k] for k, _, _ in S.TILES])
        self.assertIn("macd_3_17_5", members)
        self.assertNotIn("zscore_600", members)
        self.assertEqual(len(members), len(set(members)))
        self.assertEqual(members.count("roc_2"), 1)


class AgreementTests(unittest.TestCase):
    def test_buckets(self):
        self.assertEqual(
            [Q._bucket(v, Q.NET_EDGES) for v in (1, 3, 4, 12, 15, 16)],
            ["1-3", "1-3", "4-7", "12-13", "14-15", "16"],
        )
        self.assertEqual(
            [Q._bucket(v, Q.DENSITY_EDGES) for v in (1, 2, 16, 31)],
            ["1", "2-5", "16-30", "31+"],
        )
        self.assertAlmostEqual(Q.standard_error(3000), math.sqrt(0.25 / 100))
        self.assertEqual(Q.standard_error(3), 0.5)
        self.assertAlmostEqual(Q.standard_error(300, 3), math.sqrt(0.25 / 100))

    def test_the_plain_vote_is_scored_by_how_many_readings_net_one_way(self):
        # Up for 1,000 seconds, then down. Three readings that are all right once the grid is warm
        # and all wrong before it: only warmed-up seconds may be counted.
        ids = ["roc_2", "roc_5", "breakout_20"]
        n = 2000
        at = np.arange(n)
        close = 100.0 + 0.01 * np.where(at <= 1000, at, 2000 - at)
        sign = X.forward_sign(close, H).astype(float)
        warm = max(v["need"] for v in F.VARIANTS if v["id"] in ids)
        self.assertEqual(warm, 21)
        vote = np.where(at + 1 >= warm, sign, -sign)
        out = Q.by_net_votes([_plain(close, dict.fromkeys(ids, vote))], ids)
        self.assertEqual(list(out), ["1-3"])
        expected = int(((sign != 0) & (at + 1 >= warm)).sum())
        self.assertEqual([out["1-3"]["n"], out["1-3"]["hit"]], [expected, 1.0])
        # Two against one nets a single vote, in the direction of the two.
        split = {"roc_2": vote, "roc_5": vote, "breakout_20": -vote}
        self.assertEqual(Q.by_net_votes([_plain(close, split)], ids)["1-3"]["hit"], 1.0)
        # The error bar counts seconds of the clock: the same market twice is no more looks.
        self.assertAlmostEqual(out["1-3"]["se"], math.sqrt(0.25 / (expected / H)))
        frame = _plain(close, dict.fromkeys(ids, vote))
        twice = Q.by_net_votes([frame, dict(frame)], ids)
        self.assertEqual(twice["1-3"]["n"], 2 * expected)
        self.assertEqual(twice["1-3"]["se"], out["1-3"]["se"])

    def test_strong_calls_are_counted_over_exactly_the_last_thirty_seconds(self):
        # Two strong calls 29 seconds apart share a window; 30 seconds apart they do not.
        score, sign = [], []
        for gap, second_outcome in ((29, -1), (30, 1)):
            for _ in range(400):
                block_score = [0.0] * 100
                block_sign = [0] * 100
                block_score[0], block_sign[0] = 0.9, 1
                block_score[gap], block_sign[gap] = 0.9, second_outcome
                score += block_score
                sign += block_sign
        out = Q.strong_density([_series(0, score, sign)])
        self.assertEqual([out["1"]["n"], out["1"]["hit"]], [1200, 1.0])
        self.assertEqual([out["2-5"]["n"], out["2-5"]["hit"]], [400, 0.0])
        # A second market calling in the same seconds doubles the calls, not the looks.
        self.assertAlmostEqual(out["1"]["se"], math.sqrt(0.25 / (1200 / H)))
        twice = Q.strong_density([_series(0, score, sign), _series(1, score, sign)])
        self.assertEqual(twice["1"]["n"], 2400)
        self.assertEqual(twice["1"]["se"], out["1"]["se"])
        # The other direction is counted apart: a down call after up calls is a first call.
        mixed = Q.strong_density(
            [
                _series(
                    0,
                    ([0.9] * 5 + [-0.9] + [0.0] * 40) * 400,
                    ([1] * 5 + [-1] + [0] * 40) * 400,
                )
            ]
        )
        self.assertEqual(mixed["1"]["n"], 800)

    def test_only_a_ready_strong_call_is_counted(self):
        n = 400
        row = _series(0, [0.9] * n + [0.74] * n + [0.9] * n, [1] * 3 * n)
        row["ready"][2 * n :] = False
        out = Q.strong_density([row])
        # The lean stretch and the not-ready stretch add nothing: the first 400 seconds only, of
        # which the first fifteen fall in buckets too small to report.
        self.assertEqual(list(out), ["16-30"])
        self.assertEqual(out["16-30"]["n"], n - 15)

    def test_a_strong_call_is_sorted_by_what_the_other_markets_said(self):
        n = 400
        mine = _series(0, [0.9] * n * 3, [1] * n * 3)
        other = _series(1, [0.9] * n + [0.0] * n + [-0.9] * n, [1] * n * 3)
        out = Q.across_markets([mine, other])
        # The second market's own calls are sorted too: its agreeing and opposing stretches.
        self.assertEqual(out["with_another"]["n"], 2 * n)
        self.assertEqual(out["alone"]["n"], n)
        self.assertEqual(out["against_another"]["n"], 2 * n)
        self.assertEqual(out["alone"]["hit"], 1.0)
        self.assertEqual(out["against_another"]["hit"], 0.5)
        # One market only: nothing to compare with.
        self.assertEqual(Q.across_markets([mine]), {})
        # Both markets' calls in the same seconds are one look: 800 calls in 400 seconds of clock.
        self.assertAlmostEqual(out["with_another"]["se"], math.sqrt(0.25 / (n / H)))

    def test_markets_are_matched_by_the_clock_not_by_position(self):
        # The second market's recording starts 400 seconds after the first's.
        n = 400
        mine = _series(0, [0.9] * 3 * n, [1] * n + [-1] * 2 * n)
        other = _series(1, [-0.9] * n + [0.0] * n, [-1] * 2 * n, start=START + n)
        out = Q.across_markets([mine, other])
        # Seconds 0-399: the other is not being read, so the call is not sorted at all.
        # Seconds 400-799: the other says down against my up, and price went down.
        # Seconds 800-1199: the other is quiet.
        self.assertEqual(
            [out["against_another"]["n"], out["against_another"]["hit"]], [2 * n, 0.5]
        )
        self.assertEqual([out["alone"]["n"], out["alone"]["hit"]], [n, 0.0])
        self.assertNotIn("with_another", out)


class LargeMoveTests(unittest.TestCase):
    N = 3000
    JUMPS = (500, 1000, 1500, 2000, 2500)
    EVEN = (1.2, 1.4, 1.6, 1.8)

    def _case(self, group=0, vol_scale=1.0):
        # Flat with small wiggles and five 1% jumps: the 30 seconds before each see a large move.
        close = 100.0 + 0.001 * np.sin(np.arange(self.N))
        for at in self.JUMPS:
            close[at:] += 1.0
        frame = _plain(close, {k: np.ones(self.N) for k in READERS})
        frame["features"] = {"rv_30": vol_scale * np.linspace(1.0, 2.0, self.N)}
        outcome = X.forward_sign(close, H).astype(float)
        return frame, _series(group, [0.9] * self.N, outcome)

    def test_a_large_move_is_the_top_twentieth_of_the_slice_it_is_learned_on(self):
        n = 2000
        # Moves of 1-100 bp for the first 1,200 seconds and enormous ones after.
        fwd = np.where(np.arange(n) < 1200, np.arange(n) % 100 + 1.0, 1e6)
        frame = {"time": START + np.arange(n), "fwd": fwd}
        (edge,) = Q.large_edges([[frame]], 0.0, 0.6, (START, START + n))
        inside = np.arange(n) + H < 0.6 * n
        self.assertAlmostEqual(edge, float(np.quantile(fwd[inside], 0.95)))
        self.assertLess(edge, 101.0)
        whole = {"time": START + np.arange(1000), "fwd": np.arange(1.0, 1001.0)}
        self.assertAlmostEqual(Q.large_edges([[whole]])[0], 950.05)
        self.assertEqual(Q.large_edges([[]]), [math.inf])
        # One edge per market, each from its own moves.
        self.assertEqual(len(Q.large_edges([[frame], [whole]])), 2)

    def test_the_volatility_fifths_are_cut_where_the_earlier_slice_put_them(self):
        frame, _ = self._case()
        span = (START, START + self.N)
        (edges,) = Q.volatility_edges([[frame]], 0.0, 0.6, span)
        inside = np.arange(self.N) + H < 0.6 * self.N
        np.testing.assert_allclose(
            edges, np.quantile(frame["features"]["rv_30"][inside], [0.2, 0.4, 0.6, 0.8])
        )
        self.assertEqual(Q.volatility_edges([[]]), [[math.inf] * 4])

    def test_the_seconds_before_a_large_move_are_read_apart(self):
        frame, row = self._case()
        out = Q.large_moves([[frame]], [row], [50.0], [list(self.EVEN)])
        self.assertEqual(out["seconds"]["large"], 5 * H)
        self.assertGreaterEqual(out["large_independent"], 5)
        self.assertLessEqual(out["large_independent"], 10)
        # Every reading said up, and every jump was up.
        self.assertEqual(out["large"]["strong_call"]["hit"], 1.0)
        self.assertEqual(out["large"]["breakout_60"]["spoke_share"], 1.0)
        self.assertLess(out["all"]["strong_call"]["hit"], 1.0)
        fifths = out["by_volatility_quintile"]
        self.assertEqual([q["quintile"] for q in fifths], [1, 2, 3, 4, 5])
        # Volatility rises evenly through the recording and one jump falls in each fifth.
        for q in fifths:
            self.assertAlmostEqual(q["seconds_share"], 0.2, delta=0.02)
            self.assertAlmostEqual(q["large_share"], out["large_share"], delta=0.02)
        # With cuts learned on a quieter stretch, everything here counts as the top fifth.
        low = Q.large_moves([[frame]], [row], [50.0], [[0.1, 0.2, 0.3, 0.4]])
        self.assertEqual(
            [q["seconds_share"] for q in low["by_volatility_quintile"]],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        )

    def test_each_market_uses_its_own_size_and_its_own_volatility_cuts(self):
        frame, row = self._case()
        loud, loud_row = self._case(group=1, vol_scale=100.0)
        out = Q.large_moves(
            [[frame], [loud]],
            [row, loud_row],
            [50.0, 1e9],
            [list(self.EVEN), [100 * v for v in self.EVEN]],
        )
        # The second market's moves are never large by its own size, so only the first's count.
        self.assertEqual(out["seconds"]["large"], 5 * H)
        for q in out["by_volatility_quintile"]:
            self.assertAlmostEqual(q["seconds_share"], 0.2, delta=0.02)

    def test_an_error_bar_counts_only_the_blocks_in_which_that_reading_spoke(self):
        # Twenty jumps. The strong call speaks before all of them, the breakout before the first five.
        n, jumps = 10_500, range(500, 10_500, 500)
        close = 100.0 + 0.001 * np.sin(np.arange(n))
        for at in jumps:
            close[at:] += 1.0
        votes = {k: np.ones(n) for k in READERS}
        votes["breakout_60"] = np.r_[np.ones(2500), np.zeros(n - 2500)]
        frame = _plain(close, votes)
        frame["features"] = {"rv_30": np.linspace(1.0, 2.0, n)}
        row = _series(0, [0.9] * n, X.forward_sign(close, H).astype(float))
        out = Q.large_moves([[frame]], [row], [50.0], [list(self.EVEN)])
        self.assertEqual(out["seconds"]["large"], 20 * H)
        self.assertEqual(out["large"]["breakout_60"]["spoke_share"], 0.25)
        self.assertGreater(
            out["large"]["breakout_60"]["se"], 1.5 * out["large"]["strong_call"]["se"]
        )
        self.assertAlmostEqual(
            out["large"]["strong_call"]["se"],
            math.sqrt(0.25 / out["large_independent"]),
        )
        # One look per move, wherever the thirty seconds before it fall on the clock.
        self.assertEqual(out["large_independent"], 20)
        self.assertAlmostEqual(
            out["large"]["breakout_60"]["se"], math.sqrt(0.25 / 5), places=12
        )
        for shift in (7, 15, 29):
            moved = _plain(close, votes, start=START + shift)
            moved["features"] = frame["features"]
            later = Q.large_moves(
                [[moved]],
                [_series(0, [0.9] * n, row["sign"], start=START + shift)],
                [50.0],
                [list(self.EVEN)],
            )
            self.assertEqual(later["large_independent"], 20)
        # A reading that spoke for only five seconds before each move still had one look at each,
        # and a stretch of large moves ten minutes long is twenty looks, not one.
        self.assertEqual(Q.looks(set()), 0.0)
        self.assertEqual(Q.looks({s for at in jumps for s in range(at - 5, at)}), 20.0)
        self.assertEqual(Q.looks(set(range(1000, 1600))), 20.0)
        self.assertEqual(Q.looks({10, 40, 71}), 2.0)
        # The same market twice: twice the seconds, the same moves, the same error bars.
        twin, twin_row = dict(frame), dict(row, group=1)
        both = Q.large_moves(
            [[frame], [twin]], [row, twin_row], [50.0, 50.0], [list(self.EVEN)] * 2
        )
        self.assertEqual(both["seconds"]["large"], 2 * out["seconds"]["large"])
        self.assertEqual(both["large_independent"], out["large_independent"])
        self.assertEqual(
            both["large"]["strong_call"]["se"], out["large"]["strong_call"]["se"]
        )
        self.assertAlmostEqual(
            both["all"]["strong_call"]["se"], out["all"]["strong_call"]["se"], places=12
        )
        for one, two in zip(
            out["by_volatility_quintile"], both["by_volatility_quintile"], strict=True
        ):
            self.assertAlmostEqual(one["strong_se"], two["strong_se"], places=12)
            self.assertEqual(one["strong_hit"], two["strong_hit"])
        self.assertLess(out["by_volatility_quintile"][0]["strong_se"], 0.5)

    def test_a_market_that_never_moved_has_no_large_move(self):
        flat = _plain(np.full(600, 50.0), {k: np.ones(600) for k in READERS})
        flat["features"] = {"rv_30": np.zeros(600)}
        self.assertEqual(Q.large_edges([[flat]]), [0.0])
        out = Q.large_moves(
            [[flat]], [_series(0, [0.9] * 600, [0] * 600)], [0.0], [[0.0] * 4]
        )
        self.assertEqual(out["seconds"], {"large": 0, "all": 0})


class OrderBookTests(unittest.TestCase):
    def _book(self, seconds, mid, bid=1.0, ask=1.0):
        seconds = np.asarray(seconds, dtype=np.int64)
        return {
            "second": seconds,
            "mid": np.asarray(mid, dtype=float),
            "bid_size": np.full(seconds.size, bid),
            "ask_size": np.full(seconds.size, ask),
            "spread": np.full(seconds.size, 0.01),
        }

    def test_a_book_row_received_later_cannot_move_an_earlier_reading(self):
        n = 400
        frame = _plain(np.full(n, 100.0), {})
        seconds = START + np.arange(n)
        mid = 100.0 + 0.001 * np.arange(n)
        before = Q.book_features(frame, self._book(seconds, mid))
        changed = mid.copy()
        changed[350:] += 5.0
        after = Q.book_features(frame, self._book(seconds, changed))
        for name, values in before.items():
            np.testing.assert_array_equal(values[:350], after[name][:350], err_msg=name)
        self.assertFalse(np.array_equal(before["lead_2"][350:], after["lead_2"][350:]))
        # The reading at second t uses the row received in second t, never t + 1.
        np.testing.assert_allclose(
            before["book_roc_2"][2:], (mid[2:] / mid[:-2] - 1.0) * 1e4
        )
        self.assertTrue(np.isnan(before["basis_dev"][:299]).all())
        self.assertTrue(np.isfinite(before["basis_dev"][299:]).all())

    def test_holding_the_book_back_a_second_reads_the_row_of_the_second_before(self):
        n = 100
        frame = _plain(np.full(n, 100.0), {})
        mid = 100.0 + 0.01 * np.arange(n) ** 1.5
        book = self._book(START + np.arange(n), mid, bid=3.0, ask=1.0)
        now, late = Q.book_features(frame, book), Q.book_features(frame, book, lag=1)
        np.testing.assert_allclose(late["book_roc_2"][3:], now["book_roc_2"][2:-1])
        self.assertTrue(np.isnan(late["imbalance"][0]))
        self.assertEqual(late["imbalance"][1], 0.5)

    def test_a_stale_or_missing_book_gives_no_reading(self):
        n = 50
        frame = _plain(np.full(n, 100.0), {})
        # Rows only for the first ten seconds: fresh for three more, then nothing.
        book = self._book(START + np.arange(10), np.full(10, 100.0), bid=3.0, ask=1.0)
        feats = Q.book_features(frame, book)
        self.assertTrue(np.isfinite(feats["imbalance"][: 10 + Q.BOOK_STALE_S]).all())
        self.assertTrue(np.isnan(feats["imbalance"][10 + Q.BOOK_STALE_S :]).all())
        self.assertEqual(feats["imbalance"][0], 0.5)
        late = self._book(START + 100 + np.arange(5), np.full(5, 100.0))
        self.assertTrue(np.isnan(Q.book_features(frame, late)["imbalance"]).all())

    def test_the_delayed_outcome_starts_after_the_fill_delay(self):
        close = np.array([1.0, 2.0, 3.0, 2.0, 1.0, 5.0, 5.0])
        np.testing.assert_array_equal(
            Q.delayed_sign(close, 2, 0), X.forward_sign(close, 2)
        )
        # From close[t + 1] to close[t + 3].
        np.testing.assert_array_equal(
            Q.delayed_sign(close, 2, 1), [0, -1, 1, 1, 0, 0, 0]
        )
        np.testing.assert_array_equal(Q.delayed_sign(close[:2], 2, 1), [0, 0])

    def test_the_book_keeps_the_last_row_received_in_each_second_and_skips_bad_lines(
        self,
    ):
        def coinbase(received, bid, ask, bid_size=1, ask_size=1, asset="BTC"):
            return {
                "venue": "coinbase",
                "asset": asset,
                "bid": bid,
                "ask": ask,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "received_at": received,
            }

        def oracle(exchange, received):
            return {
                "venue": "jupiter",
                "asset": "BTC",
                "price": 100.0,
                "exchange_at": exchange,
                "received_at": received,
            }

        lines = [
            # Written out of order: the row received last in second 10 must win, not the last in the file.
            json.dumps(coinbase(10.9, 110.0, 112.0, 3)),
            json.dumps(coinbase(10.2, 99.0, 101.0, 2)),
            json.dumps(coinbase(12.1, 100.0, 100.5, 1, 4)),
            json.dumps(coinbase(13.0, None, 100.5)),
            json.dumps(coinbase(13.0, 0, 0, asset="ZEC")),
            json.dumps({"venue": "coinbase", "bid": 1, "ask": 2, "received_at": 14.0}),
            '{"venue": "coinbase", "asset": "BTC", "bid": 1',
            "not json at all",
            json.dumps(oracle(10.0, 10.2)),
            json.dumps(oracle(11.0, 11.4)),
            json.dumps({"venue": "elsewhere", "asset": "BTC", "received_at": 15.0}),
        ]
        with tempfile.TemporaryDirectory() as folder:
            first = Path(folder) / "dual-quotes-a.jsonl.gz"
            with gzip.open(first, "wt", encoding="utf-8") as stream:
                stream.write("\n".join(lines) + "\n")
            # A second hour file cut off mid-write: what was read before the cut is kept.
            whole = Path(folder) / "whole.gz"
            with gzip.open(whole, "wt", encoding="utf-8") as stream:
                for i in range(2000):
                    stream.write(json.dumps(coinbase(20.0 + i, 50.0, 52.0)) + "\n")
            data = whole.read_bytes()
            whole.unlink()
            (Path(folder) / "dual-quotes-b.jsonl.gz").write_bytes(
                data[: len(data) // 2]
            )
            books, latency = Q.read_book(Path(folder))
        self.assertEqual(list(books), ["BTC"])
        np.testing.assert_array_equal(books["BTC"]["second"][:2], [10, 12])
        np.testing.assert_array_equal(books["BTC"]["mid"][:2], [111.0, 100.25])
        np.testing.assert_array_equal(books["BTC"]["bid_size"][:2], [3.0, 1.0])
        self.assertGreater(books["BTC"]["second"].size, 2)
        self.assertEqual(latency["BTC"]["ticks"], 2)
        self.assertAlmostEqual(latency["BTC"]["p50"], 0.3, places=6)

    def _leading(self, n=6000):
        # The oracle follows the book one second late.
        rng = np.random.default_rng(3)
        book_mid = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 1e-4, n)))
        close = np.r_[book_mid[0], book_mid[:-1]]
        frame = _plain(close, {})
        book = self._book(START + np.arange(n), book_mid)
        row = _series(0, [0.0] * n, X.forward_sign(close, H))
        return frame, book, row, (START, START + n)

    def test_a_book_that_leads_the_price_scores_above_half_until_the_delay_passes(self):
        frame, book, row, span = self._leading()
        out = Q.book_study([[frame]], [book], [row], span)
        lead = out["readings"]["lead_2"]
        self.assertGreater(lead["delay_0"]["3"]["later"]["hit"], 0.6)
        # Two seconds later the oracle has caught up: the book says nothing more.
        self.assertLess(
            abs(lead[f"delay_{S.ENTRY_DELAY}"]["3"]["later"]["hit"] - 0.5), 0.05
        )
        self.assertNotIn("strong_call", out["with_the_call"]["later"])
        # Held back by the second it leads by, the book knows nothing the oracle does not.
        late = Q.book_study([[frame]], [book], [row], span, lag=1)
        # Its lead over the oracle is then exactly nothing, and its own momentum is the oracle's.
        self.assertNotIn("lead_2", late["readings"])
        self.assertLess(
            abs(late["readings"]["book_roc_2"]["delay_0"]["3"]["later"]["hit"] - 0.5),
            0.05,
        )
        self.assertGreater(
            out["readings"]["book_roc_2"]["delay_0"]["3"]["later"]["hit"], 0.6
        )
        # The same market and book twice are twice the calls in the same seconds: no smaller error bar.
        twice = Q.book_study(
            [[frame], [dict(frame)]], [book, book], [row, dict(row, group=1)], span
        )
        for name, delays in out["readings"].items():
            for delay, horizons in delays.items():
                for horizon, parts in horizons.items():
                    for part, cell in parts.items():
                        other = twice["readings"][name][delay][horizon][part]
                        self.assertEqual(cell["hit"], other["hit"])
                        self.assertAlmostEqual(cell["se"], other["se"], places=12)
        cell = out["readings"]["book_roc_2"]["delay_0"]["3"]["later"]
        self.assertLess(cell["se"], 0.05)
        self.assertGreater(cell["se"], 0.5 / math.sqrt(0.4 * 6000 / 3) - 1e-9)

    def test_the_error_bar_of_a_call_beside_the_book_counts_clock_seconds(self):
        frame, book, _, span = self._leading()
        n = frame["close"].size
        row = _series(0, [0.9] * n, X.forward_sign(frame["close"], H))
        one = Q.book_study([[frame]], [book], [row], span)
        two = Q.book_study(
            [[frame], [dict(frame)]], [book, book], [row, dict(row, group=1)], span
        )
        self.assertIn("strong_call", one["with_the_call"]["later"])
        for part in ("first", "later"):
            for key, delays in one["with_the_call"][part].items():
                for delay, cell in delays.items():
                    other = two["with_the_call"][part][key][delay]
                    self.assertEqual(cell["hit"], other["hit"])
                    self.assertAlmostEqual(cell["se"], other["se"], places=12)

    def test_a_large_deviation_is_sized_on_the_first_part_only(self):
        # The book's distance from the oracle is a hundred times wider after the split. Sized on
        # the first part, nearly every later second is "large"; sized on everything, a fifth would be.
        n = 6000
        rng = np.random.default_rng(4)
        basis = np.where(np.arange(n) < 3600, 1e-4, 1e-2) * rng.normal(0.0, 1.0, n)
        close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 1e-4, n)))
        frame = _plain(close, {})
        book = self._book(START + np.arange(n), close * (1.0 + basis))
        row = _series(0, [0.0] * n, X.forward_sign(close, H))
        out = Q.book_study([[frame]], [book], [row], (START, START + n))
        large = out["with_the_call"]["later"]["book_large_deviation"]["delay_0"]
        self.assertGreater(large["share"], 0.8)
        self.assertAlmostEqual(
            out["with_the_call"]["first"]["book_large_deviation"]["delay_0"]["share"],
            0.2,
            delta=0.03,
        )

    def test_a_market_with_a_book_but_no_bars_is_passed_over(self):
        frame, book, row, span = self._leading(2000)
        out = Q.book_study([[], [frame]], [book, book], [row], span)
        self.assertIn("lead_2", out["readings"])


class CoinTests(unittest.TestCase):
    def test_each_market_is_compared_with_the_others_pooled(self):
        rows = {
            "A": {"strong": {"hit": 0.60, "hit_se": 0.03, "n": 3000}},
            "B": {"strong": {"hit": 0.50, "hit_se": 0.03, "n": 3000}},
            "C": {"strong": {"hit": 0.50, "hit_se": 0.03, "n": 6000}},
            "D": {"strong": {"n": 12}},
        }
        out = C.compare(rows)
        self.assertEqual(set(out), {"A", "B", "C"})
        self.assertAlmostEqual(out["A"]["others"], 0.5)
        self.assertAlmostEqual(out["A"]["difference"], 0.1)
        z = 0.1 / math.hypot(0.03, math.sqrt(0.25 / 300))
        self.assertAlmostEqual(out["A"]["z"], z)
        self.assertAlmostEqual(out["B"]["others"], (0.6 * 3000 + 0.5 * 6000) / 9000)
        # Three rated markets: the p-value is the two-sided one times three, capped at one.
        self.assertEqual(out["A"]["coins_compared"], 3)
        self.assertAlmostEqual(
            out["A"]["p_adjusted"], 3 * math.erfc(z / math.sqrt(2.0))
        )
        self.assertLess(out["C"]["p_adjusted"], 1.0)
        # Markets that are all alike: nothing stands out, and the adjusted p-value is capped at one.
        alike = {name: rows["B"] for name in "XYZ"}
        self.assertEqual(
            {row["p_adjusted"] for row in C.compare(alike).values()}, {1.0}
        )
        self.assertEqual(C.compare({"A": rows["A"], "D": rows["D"]}), {})

    def test_the_rates_are_read_at_the_call_horizon(self):
        model = {
            "horizons": [5, 30],
            "call_horizon_s": 30,
            "variants": [
                {"id": "a", "prior": [0.1, 0.9]},
                {"id": "b", "prior": [0.2, None]},
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "experiments.json"
            path.write_text(json.dumps(model), encoding="utf-8")
            self.assertEqual(C.shipped_prior(path), {"a": 0.9, "b": 0.5})
        shipped = C.shipped_prior()
        self.assertEqual(set(shipped), {v["id"] for v in F.VARIANTS})

    def test_each_tier_is_taken_from_its_own_aggregate(self):
        def tier(hit):
            return {
                "hit": hit,
                "hit_se": 0.1,
                "n": 500,
                "share": 0.2,
                "mean_follow_bps": 0.5,
            }

        replayed = {
            "seconds": 10,
            "changes": {"best": 4},
            "best": {
                "strong": tier(0.6),
                "any": {"hit": 0.55, "hit_se": 0.1, "n": 900},
                "lean": {"n": 12},
            },
            "weighted": {"strong": tier(0.7)},
            "plain": {"strong": tier(0.8)},
        }
        frame = _plain(100.0 + 0.01 * np.arange(200), {})
        table = {"breakout_60": {H: [None, 0]}}
        with (
            mock.patch.object(C.X, "replay", return_value=replayed),
            mock.patch.object(C.X, "experiment_table", return_value=table),
        ):
            row = C.coin_row([[frame]], [], {})
        self.assertEqual(
            [
                row["strong"]["hit"],
                row["strong_no_switching"]["hit"],
                row["strong_one_vote_each"]["hit"],
                row["any_call"]["hit"],
            ],
            [0.6, 0.7, 0.8, 0.55],
        )
        # Too few calls to rate: the count alone, never a rate.
        self.assertEqual(row["lean"], {"n": 12})
        self.assertEqual(row["breakout_60"], {"hit": None, "n": 0, "hit_se": None})
        self.assertEqual([row["switches"], row["scored_seconds"]], [4, 10])
        self.assertEqual(row["flat_share"], 0.0)
        self.assertNotIn("share", row["any_call"])

    def test_a_market_is_scored_with_the_windows_own_call(self):
        frame = _frame(_walk(3000, 31))
        result = C.study({"SOL": [[frame]], "NONE": []})
        self.assertEqual(list(result["coins"]), ["SOL"])
        row = result["coins"]["SOL"]
        self.assertAlmostEqual(row["hours"], 3000 / 3600)
        self.assertGreater(row["scored_seconds"], 2000)
        self.assertGreater(row["median_move_bps"], 0.0)
        self.assertLess(row["flat_share"], 0.05)
        self.assertEqual(result["strong_against_the_others"], {})

    def _ticks(self, folder, name, coins, seconds, gz=False):
        path = Path(folder) / name
        opener = gzip.open if gz else open
        rng = np.random.default_rng(len(name))
        with opener(path, "wt", encoding="utf-8") as stream:
            for coin in coins:
                price = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 3e-5, seconds)))
                for i in range(seconds):
                    row = {
                        "a": coin,
                        "p": float(price[i]),
                        "e": (START + i) * 1000 + 200,
                        "r": 0,
                    }
                    stream.write(json.dumps(row) + "\n")
        return path

    def _main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = C.main([str(a) for a in argv])
            except SystemExit as stop:
                code = stop.code
        return code, out.getvalue(), err.getvalue()

    def test_the_command_names_what_it_could_not_score_and_fails_when_nothing_was(
        self,
    ):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "coins.json"
            long = self._ticks(folder, "long.jsonl", ["SOL"], 700)
            short = self._ticks(folder, "short.jsonl", ["ETH"], 120)
            code, printed, _ = self._main(
                "--ticks", long, "--ticks", short, "--out", out
            )
            self.assertEqual(code, 0)
            result = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(list(result["coins"]), ["SOL"])
            self.assertEqual(result["too_short_ticks"], {"ETH": 120})
            self.assertEqual(result["in_sample_sources"], [])
            self.assertTrue(result["prior_file"].endswith("experiments.json"))
            self.assertEqual(json.loads(printed)["too_short"], ["ETH"])
            self.assertFalse(Path(str(out) + ".tmp").exists())
            # Nothing long enough: a failure, not an empty success.
            nothing = Path(folder) / "none.json"
            code, printed, _ = self._main("--ticks", short, "--out", nothing)
            self.assertEqual(code, 1)
            self.assertIn("no market had 600 seconds", printed)
            self.assertFalse(nothing.exists())
            # The same file twice would count every call twice.
            code, _, err = self._main(
                "--ticks", long, "--ticks", long, "--out", nothing
            )
            self.assertEqual(code, 2)
            self.assertIn("given twice", err)
            absent = Path(folder) / "absent.json"
            # A rates file that lacks some of today's settings is refused before any scoring.
            thin = Path(folder) / "thin.json"
            model = json.loads(C.SHIPPED.read_text(encoding="utf-8"))
            model["variants"] = model["variants"][:-5]
            thin.write_text(json.dumps(model), encoding="utf-8")
            code, _, err = self._main(
                "--ticks", long, "--prior", thin, "--out", nothing
            )
            self.assertEqual(code, 2)
            self.assertIn("lacks 5 settings", err)
            for argv in (
                ["--out", nothing],
                ["--ticks", long, "--prior", absent, "--out", nothing],
            ):
                code, _, err = self._main(*argv)
                self.assertEqual(code, 2, argv)
            self.assertFalse(nothing.exists())

    def test_a_recording_cut_off_mid_write_is_read_up_to_the_cut(self):
        with tempfile.TemporaryDirectory() as folder:
            whole = self._ticks(folder, "whole.jsonl.gz", ["SOL"], 4000, gz=True)
            data = whole.read_bytes()
            cut = Path(folder) / "cut.jsonl.gz"
            cut.write_bytes(data[: len(data) // 2])
            ticks = S.read_live(cut)
            self.assertGreater(ticks["SOL"][0].size, 500)
            self.assertLess(ticks["SOL"][0].size, 4000)
            messy = Path(folder) / "messy.jsonl"
            messy.write_text(
                '{"a":"SOL","p":70.5,"e":1000}\n'
                '{"a":"SOL","p":70.6}\n'
                '{"a":"SOL","p":"x","e":2000}\n'
                '{"a":"SOL","p":-1,"e":3000}\n'
                '{"a":7,"p":1,"e":4000}\n'
                "not json\n"
                '{"a":"SOL","p":70.7,"e":5000}\n',
                encoding="utf-8",
            )
            times, prices = S.read_live(messy)["SOL"]
            np.testing.assert_array_equal(times, [1.0, 5.0])
            np.testing.assert_array_equal(prices, [70.5, 70.7])


class MainTests(unittest.TestCase):
    N = 2400
    CUT = 1440  # the first bar past the 60% mark of the span

    def _capture(self, folder, late_seed):
        """A base capture of two markets with books, identical up to the split and different after."""
        rows = []
        for k, asset in enumerate(("BTC", "ETH")):
            head = np.random.default_rng(10 + k).normal(0, 2e-4, self.CUT)
            tail = np.random.default_rng(late_seed + k).normal(
                0, 2e-4, self.N - self.CUT
            )
            price = 100.0 * np.exp(np.cumsum(np.r_[head, tail]))
            for i in range(self.N):
                rows.append(
                    {
                        "venue": "jupiter",
                        "asset": asset,
                        "price": float(price[i]),
                        "exchange_at": START + i + 0.2,
                        "received_at": START + i + 0.5,
                    }
                )
                rows.append(
                    {
                        "venue": "coinbase",
                        "asset": asset,
                        "bid": float(price[i]) - 0.01,
                        "ask": float(price[i]) + 0.01,
                        "bid_size": 1.0 + (i % 3),
                        "ask_size": 2.0,
                        "received_at": START + i + 0.7,
                    }
                )
        path = Path(folder) / "dual-quotes-2026112800.jsonl.gz"
        with gzip.open(path, "wt", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, separators=(",", ":")) + "\n")

    def _run(self, folder):
        out = Path(folder) / "summary.json"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(Q.main(["--base", str(folder), "--out", str(out)]), 0)
        return json.loads(out.read_text(encoding="utf-8"))

    @staticmethod
    def _learned(summary):
        """Everything the command reports as learned on, or read on, the first 60%."""
        book = summary["order_book"]
        return {
            "combinations": {
                size: {
                    "top": [(row["members"], row["first"]) for row in block["top"]],
                    "tried": block["tried"],
                    "eligible": block["eligible"],
                }
                for size, block in summary["combinations"]["sizes"].items()
            },
            "fits": {
                name: {"first": fit["first"], "weights": fit["largest_weights"]}
                for name, fit in summary["fitted_vote"].items()
            },
            "net_first": summary["net_votes"]["base_first_60pct"],
            "edges": summary["large_moves"]["base_after_60pct"]["edges_bps"],
            "book_first": {
                name: {
                    delay: {h: part.get("first") for h, part in horizons.items()}
                    for delay, horizons in delays.items()
                }
                for name, delays in book["readings"].items()
            },
            "book_with_first": book["with_the_call"]["first"],
        }

    def test_nothing_after_the_split_reaches_what_the_command_learned_before_it(self):
        with (
            tempfile.TemporaryDirectory() as one,
            tempfile.TemporaryDirectory() as other,
        ):
            self._capture(one, 500)
            self._capture(other, 900)
            first = self._run(one)
            # The cut-offs for the base recording are learned on its first part and nowhere else.
            with (
                mock.patch.object(
                    Q, "volatility_edges", wraps=Q.volatility_edges
                ) as vol,
                mock.patch.object(Q, "large_edges", wraps=Q.large_edges) as large,
            ):
                second = self._run(other)
        span = tuple(second["base_span"])
        for spy in (vol, large):
            self.assertEqual(spy.call_args_list[0].args[1:], (0.0, S.SPLIT[0], span))
            self.assertEqual(len(spy.call_args_list), 1)
        self.assertEqual(self._learned(first), self._learned(second))
        # The later parts do differ, so the comparison is not vacuous.
        self.assertNotEqual(
            first["combinations"]["sizes"]["1"]["top"],
            second["combinations"]["sizes"]["1"]["top"],
        )
        self.assertEqual(first["order_book"]["markets"], ["BTC", "ETH"])
        self.assertGreater(
            first["order_book"]["oracle_arrival_delay_s"]["BTC"]["p50"], 0.0
        )
        self.assertIn("readings", first["order_book"]["book_one_second_late"])
        self.assertIn("not a clean test", first["what_was_seen_when"])

    def test_what_the_two_capture_test_cannot_see(self):
        # First-slice figures stop a full horizon before the split, so a reading that looked up to
        # 29 seconds ahead would pass the test above. That is the business of the feature and
        # settling tests in test_scalp_1s; this only pins the gap the comparison relies on.
        frame = _plain(_walk(600, 4), {})
        inside = X._window(frame, H, 0.0, 0.5, (START, START + 599))
        self.assertLessEqual(int(frame["time"][inside].max()) + H, START + 300)

    def test_the_command_refuses_a_base_folder_with_nothing_to_read(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "summary.json"
            for base in (folder, Path(folder) / "absent"):
                with (
                    contextlib.redirect_stderr(io.StringIO()),
                    self.assertRaises(SystemExit) as stop,
                ):
                    Q.main(["--base", str(base), "--out", str(out)])
                self.assertEqual(stop.exception.code, 2)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()

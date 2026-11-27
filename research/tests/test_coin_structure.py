from __future__ import annotations

import io
import json
import math
import tempfile
import unittest
import urllib.error
import zlib
from datetime import UTC, datetime
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

from research import coin_structure as cs

DAY_MS = 86_400_000
HOUR_MS = 3_600_000
STUDY_END_MS = 260 * DAY_MS
REQUEST_BODY = {"req": {"coin": "X", "interval": "1d"}}


def candle(
    t: int, o: float, h: float, low: float, c: float, v: float, interval: str = "1d"
) -> dict:
    span = cs.INTERVALS[interval] * 1000
    return {
        "t": t,
        "T": t + span - 1,
        "s": "X",
        "i": interval,
        "o": str(o),
        "h": str(h),
        "l": str(low),
        "c": str(c),
        "v": str(v),
        "n": 1,
    }


def random_walk(interval: str, bars: int, seed: int) -> list[dict]:
    """A series of `bars` candles that ends at STUDY_END_MS."""
    rng = np.random.default_rng(seed)
    span = cs.INTERVALS[interval] * 1000
    start = STUDY_END_MS - bars * span
    close = 50 * np.exp(rng.normal(0, 0.02, bars).cumsum())
    wick = 1 + rng.uniform(0.001, 0.02, (bars, 2))
    rows, previous = [], 50.0
    for k, c in enumerate(close):
        hi, lo = max(previous, c) * wick[k, 0], min(previous, c) / wick[k, 1]
        rows.append(
            candle(start + k * span, previous, hi, lo, float(c), 100 + k, interval)
        )
        previous = float(c)
    return rows


DEFAULT_BARS = {
    ("X", "1d"): 260,
    ("X", "1h"): 24 * 100,
    ("BTC", "1d"): 260,
    ("NEW", "1d"): 12,
}


def fetched(
    tmp: str,
    bars: dict[tuple[str, str], int] = DEFAULT_BARS,
    series: dict[tuple[str, str], list[dict]] | None = None,
) -> Path:
    """Run the real `fetch` against a stand-in for the candle endpoint."""
    coin = next(iter(bars))[0]

    def post(body: dict) -> bytes:
        key = (body["req"]["coin"], body["req"]["interval"])
        rows = (series or {}).get(key) or random_walk(key[1], bars[key], len(key[0]))
        return json.dumps(rows).encode()

    out = Path(tmp) / "study"
    references = [symbol for symbol, _ in bars if symbol != coin]
    with (
        mock.patch.object(cs, "_post", side_effect=post),
        mock.patch("builtins.print"),
    ):
        cs.fetch(coin, references, out)
    return out


def calendar_series() -> dict[tuple[str, str], list[dict]]:
    """Flat at 100, except +10% on Wednesdays and +1% in the 14:00 UTC hour."""
    daily, hourly = [], []
    previous = 100.0
    for k in range(260):
        t = k * DAY_MS
        wednesday = datetime.fromtimestamp(t / 1000, UTC).weekday() == 2
        close = 110.0 if wednesday else 100.0
        hi, lo = max(previous, close) + 0.5, min(previous, close) - 0.5
        daily.append(candle(t, previous, hi, lo, close, 10))
        previous = close
    previous = 100.0
    for k in range(24 * 30):
        t = STUDY_END_MS - (24 * 30 - k) * HOUR_MS
        busy = datetime.fromtimestamp(t / 1000, UTC).hour == 14
        close = 101.0 if busy else 100.0
        hi, lo = max(previous, close) + 0.1, min(previous, close) - 0.1
        hourly.append(candle(t, previous, hi, lo, close, 10 if busy else 1, "1h"))
        previous = close
    return {("X", "1d"): daily, ("X", "1h"): hourly}


class ParseTests(unittest.TestCase):
    def test_rejects_anything_but_a_complete_candle_list(self) -> None:
        bodies = [
            json.dumps(payload).encode()
            for payload in ({"error": "rate limited"}, [], ["x"], [{"t": 0, "T": 1}])
        ]
        for body in [*bodies, b"<html>bad gateway</html>"]:
            with (
                self.subTest(body=body),
                self.assertRaisesRegex(ValueError, "X: response is not a candle list"),
            ):
                cs.parse_candles(body, "X")

    def test_forming_candle_is_dropped(self) -> None:
        rows = [candle(0, 1, 2, 0.5, 1.5, 10), candle(DAY_MS, 1.5, 3, 1, 2, 20)]
        frame = cs.normalize_candles(rows, "1d", now_ms=DAY_MS + 5)
        self.assertEqual(frame["timestamp"].tolist(), [0])
        self.assertEqual(
            list(frame.columns), ["timestamp", "open", "high", "low", "close", "volume"]
        )


class RequestTests(unittest.TestCase):
    def failing(self, status: int) -> mock.Mock:
        error = urllib.error.HTTPError("u", status, "no", {}, io.BytesIO(b""))
        self.addCleanup(error.close)
        return mock.Mock(side_effect=error)

    def test_a_refused_request_is_not_repeated_and_names_the_series(self) -> None:
        urlopen = self.failing(400)
        with (
            mock.patch.object(cs.urllib.request, "urlopen", urlopen),
            mock.patch.object(cs.time, "sleep") as sleep,
            self.assertRaisesRegex(RuntimeError, "X 1d: candle request failed"),
        ):
            cs._post(REQUEST_BODY)
        self.assertEqual((urlopen.call_count, sleep.call_count), (1, 0))

    def test_a_server_error_is_retried_then_reported(self) -> None:
        urlopen = self.failing(503)
        with (
            mock.patch.object(cs.urllib.request, "urlopen", urlopen),
            mock.patch.object(cs.time, "sleep") as sleep,
            mock.patch("sys.stderr") as notices,
            self.assertRaisesRegex(RuntimeError, "X 1d"),
        ):
            cs._post(REQUEST_BODY)
        self.assertEqual(urlopen.call_count, cs.REQUEST_ATTEMPTS)
        self.assertEqual(sleep.call_count, cs.REQUEST_ATTEMPTS - 1)
        written = "".join(call.args[0] for call in notices.write.call_args_list)
        self.assertEqual(written.count("X 1d: retrying"), cs.REQUEST_ATTEMPTS - 1)


class PivotTests(unittest.TestCase):
    def test_pivot_is_known_only_after_span_bars(self) -> None:
        high = np.array([1, 2, 5, 2, 1, 2, 3], dtype=float)
        pivots = cs.confirmed_pivots(high, high - 0.5, 2)
        self.assertEqual(
            [(p["index"], p["kind"], p["confirm"]) for p in pivots],
            [(2, "high", 4), (4, "low", 6)],
        )

    def test_later_bars_do_not_change_an_earlier_pivot(self) -> None:
        rng = np.random.default_rng(7)
        high = 100 + rng.normal(0, 1, 80).cumsum()
        full = cs.confirmed_pivots(high, high - 1, 3)
        prefix = cs.confirmed_pivots(high[:50], high[:50] - 1, 3)
        self.assertEqual(prefix, [p for p in full if p["confirm"] < 50])

    def test_tied_extremes_give_one_pivot_at_the_earliest_bar(self) -> None:
        high = np.array([1, 2, 4, 4, 2, 1, 1], dtype=float)
        pivots = cs.confirmed_pivots(high, high - 3, 2)
        self.assertEqual([p["index"] for p in pivots if p["kind"] == "high"], [2])

    def test_double_top_beside_a_higher_earlier_bar_is_kept(self) -> None:
        high = np.array([9, 5, 8, 8, 5, 5, 5], dtype=float)
        pivots = cs.confirmed_pivots(high, high - 4, 2)
        self.assertEqual([p["index"] for p in pivots if p["kind"] == "high"], [3])


class ClusterTests(unittest.TestCase):
    def test_groups_within_tolerance_and_counts_kinds(self) -> None:
        pivots = [
            {"index": 1, "kind": "low", "price": 100.0},
            {"index": 5, "kind": "high", "price": 101.0},
            {"index": 9, "kind": "low", "price": 120.0},
        ]
        levels = cs.cluster_levels(pivots, 0.02)
        self.assertEqual(len(levels), 2)
        first = levels[0]
        self.assertEqual(
            (first["touches"], first["pivot_highs"], first["pivot_lows"]), (2, 1, 1)
        )
        self.assertAlmostEqual(first["level"], 100.5)
        self.assertEqual((first["first_index"], first["last_index"]), (1, 5))

    def test_a_chain_of_close_pivots_cannot_stretch_a_group(self) -> None:
        prices = [100 * 1.002**k for k in range(40)]
        pivots = [
            {"index": k, "kind": "low", "price": price}
            for k, price in enumerate(prices)
        ]
        levels = cs.cluster_levels(pivots, 0.03)
        self.assertGreater(len(levels), 1)
        for level in levels:
            self.assertLessEqual(level["high"] / level["low"] - 1, 0.03)
        self.assertEqual(sum(level["touches"] for level in levels), 40)


class VolumeProfileTests(unittest.TestCase):
    def test_volume_is_conserved_and_poc_is_the_heaviest_bin(self) -> None:
        high = np.array([11, 12, 30, 11.5], dtype=float)
        low = np.array([10, 10.5, 20, 10.2], dtype=float)
        volume = np.array([100, 300, 50, 200], dtype=float)
        profile = cs.volume_profile(high, low, volume, 0.05)
        self.assertAlmostEqual(sum(profile["volume"]), volume.sum())
        self.assertTrue(10 <= profile["poc"] <= 12)
        self.assertLessEqual(profile["value_area_low"], profile["poc"])
        self.assertGreaterEqual(profile["value_area_high"], profile["poc"])

    def test_zero_range_bar_lands_in_one_bin(self) -> None:
        profile = cs.volume_profile(
            np.array([10.0, 20.0]), np.array([10.0, 5.0]), np.array([7.0, 0.0]), 0.1
        )
        self.assertEqual(sorted(v for v in profile["volume"] if v), [7.0])

    def test_wider_value_area_cannot_be_narrower(self) -> None:
        rng = np.random.default_rng(2)
        low = 50 + rng.random(200) * 20
        args = (low * 1.03, low, rng.random(200) * 10, 0.01)
        narrow, wide = cs.volume_profile(*args, 0.5), cs.volume_profile(*args, 0.9)
        self.assertLessEqual(wide["value_area_low"], narrow["value_area_low"])
        self.assertGreaterEqual(wide["value_area_high"], narrow["value_area_high"])


class LevelReactionTests(unittest.TestCase):
    def setUp(self) -> None:
        # Low of 90 at bar 2, confirmed at bar 4; price returns to it at bar 8.
        self.close = np.array(
            [100, 95, 91, 96, 100, 104, 103, 99, 92, 95, 98, 97], dtype=float
        )
        self.pivots = [{"index": 2, "kind": "low", "price": 90.0, "confirm": 4}]

    def react(
        self,
        close: np.ndarray,
        pivots: list[dict],
        horizon: int = 2,
        placebo: tuple[float, ...] = (),
    ) -> dict:
        return cs.level_reactions(
            close + 1, close - 1, close, pivots, 0.015, horizon, placebo
        )

    def test_support_test_uses_the_test_bar_close_as_entry(self) -> None:
        result = self.react(self.close, self.pivots)
        support = result["support"]
        self.assertEqual(support["tests"], 1)
        self.assertAlmostEqual(support["mean_forward"], 98 / 92 - 1)
        self.assertEqual(support["held_rate"], 1.0)
        self.assertEqual(result["resistance"]["tests"], 0)

    def test_previous_close_must_sit_clear_of_the_level(self) -> None:
        # Bar 7 closes at 91, inside the tolerance band above 90. It is the
        # test (bar 6 closed clear at 103); bar 8 is not, because bar 7 was not
        # clear.
        close = self.close.copy()
        close[7:9] = 91.0
        support = self.react(close, self.pivots)["support"]
        self.assertEqual(support["tests"], 1)
        self.assertAlmostEqual(support["mean_forward"], 95 / 91 - 1)

    def test_no_test_before_the_level_is_confirmed(self) -> None:
        late = [{"index": 2, "kind": "low", "price": 90.0, "confirm": 9}]
        self.assertEqual(self.react(self.close, late)["support"]["tests"], 0)

    def test_outcome_ignores_bars_beyond_the_horizon(self) -> None:
        changed = self.close.copy()
        changed[-1] = 10.0
        before = self.react(self.close, self.pivots)["support"]
        after = self.react(changed, self.pivots)["support"]
        self.assertEqual(before["mean_forward"], after["mean_forward"])

    def test_a_broken_support_is_not_tested_again(self) -> None:
        close = np.array(
            [100, 95, 91, 96, 100, 104, 85, 95, 100, 91, 95, 96], dtype=float
        )
        support = self.react(close, self.pivots)["support"]
        self.assertEqual((support["tests"], support["held_rate"]), (1, 0.0))
        self.assertAlmostEqual(support["mean_forward"], 100 / 85 - 1)

    def test_one_bar_reaching_two_levels_tests_the_nearer_in_any_order(self) -> None:
        # Bar 8 falls from 103 through 92 and 80 and closes at 82: 92 breaks.
        close = np.array(
            [100, 95, 91, 96, 100, 104, 103, 103, 82, 85, 88, 90], dtype=float
        )
        levels = [
            {"index": 2, "kind": "low", "price": 92.0, "confirm": 4},
            {"index": 1, "kind": "low", "price": 80.0, "confirm": 4},
        ]
        forward = self.react(close, levels)["support"]
        backward = self.react(close, levels[::-1])["support"]
        self.assertEqual(forward, backward)
        self.assertEqual((forward["tests"], forward["held_rate"]), (1, 0.0))

    def test_tests_of_different_levels_do_not_overlap(self) -> None:
        # Supports at 90 and 80 are reached on consecutive bars 8 and 9.
        close = np.array(
            [100, 95, 91, 96, 100, 104, 103, 99, 92, 82, 85, 88, 90, 91], dtype=float
        )
        pivots = [
            *self.pivots,
            {"index": 1, "kind": "low", "price": 80.0, "confirm": 4},
        ]
        self.assertEqual(self.react(close, pivots, horizon=1)["support"]["tests"], 2)
        self.assertEqual(self.react(close, pivots, horizon=3)["support"]["tests"], 1)

    def test_resistance_break_is_not_held(self) -> None:
        close = np.array([90, 95, 99, 94, 90, 88, 89, 92, 98, 104, 106], dtype=float)
        pivots = [{"index": 2, "kind": "high", "price": 100.0, "confirm": 4}]
        resistance = self.react(close, pivots)["resistance"]
        self.assertEqual((resistance["tests"], resistance["held_rate"]), (1, 0.0))
        self.assertAlmostEqual(resistance["mean_forward"], 106 / 98 - 1)

    def test_placebo_applies_the_same_rules_to_an_offset_line(self) -> None:
        # +10% puts the placebo line at 99, which bar 7 reaches from 103.
        result = self.react(self.close, self.pivots, placebo=(0.10,))
        placebo = result["support"]["placebo"]
        self.assertEqual(placebo["tests"], 1)
        self.assertAlmostEqual(placebo["mean_forward"], 95 / 99 - 1)
        none = self.react(self.close, self.pivots)["support"]["placebo"]
        self.assertEqual((none["tests"], none["held_rate"]), (0, None))


class DrawdownTests(unittest.TestCase):
    def test_peak_bar_low_is_not_the_trough(self) -> None:
        ts = np.arange(5) * 86_400.0
        high = np.array([10, 20, 15, 14, 25], dtype=float)
        low = np.array([9, 5, 12, 11, 13], dtype=float)
        episodes = cs.drawdowns(ts, high, low, 0.25)
        self.assertEqual(len(episodes), 1)
        self.assertEqual((episodes[0]["peak"], episodes[0]["trough"]), (20.0, 11.0))
        self.assertEqual(episodes[0]["recovered_date"], "1970-01-05")

    def test_open_decline_is_reported_without_recovery(self) -> None:
        ts = np.arange(3) * 86_400.0
        episodes = cs.drawdowns(
            ts, np.array([10.0, 9.0, 8.0]), np.array([9.0, 6.0, 5.0]), 0.25
        )
        self.assertEqual(
            [(e["trough"], e["recovered_date"]) for e in episodes], [(5.0, None)]
        )


class ReturnStatisticTests(unittest.TestCase):
    def test_grouped_returns_reports_mean_count_and_t(self) -> None:
        sample = np.array([0.01, 0.03, -0.02, -0.04])
        rows = cs.grouped_returns(sample, np.array([0, 0, 1, 1]), ["a", "b"])
        self.assertEqual([(r["label"], r["n"]) for r in rows], [("a", 2), ("b", 2)])
        self.assertAlmostEqual(rows[0]["mean"], 0.02)
        self.assertEqual(rows[1]["up_rate"], 0.0)
        expected_t = 0.02 / (np.std([0.01, 0.03], ddof=1) / math.sqrt(2))
        self.assertAlmostEqual(rows[0]["t"], expected_t)

    def test_next_bar_conditions_pair_each_bar_with_the_following_one(self) -> None:
        returns = np.array([0.12, 0.01, -0.11, 0.02, 0.06, -0.03, 0.11, 0.04])
        rows = {r["condition"]: r for r in cs.next_bar_conditions(returns)}
        big_gain = rows["after a gain of 10% or more"]
        self.assertEqual(big_gain["n"], 2)
        self.assertAlmostEqual(big_gain["next_mean"], (0.01 + 0.04) / 2)
        self.assertNotIn("after a loss of 10% or more", rows)  # one case only
        self.assertEqual(rows["all days"]["n"], 7)
        self.assertAlmostEqual(rows["all days"]["next_mean"], returns[1:].mean())

    def test_autocorrelation_of_a_constant_series_is_absent(self) -> None:
        self.assertIsNone(cs.autocorrelation(np.zeros(10), 1))
        alternating = np.array([1.0, -1.0] * 6)
        self.assertAlmostEqual(cs.autocorrelation(alternating, 1), -1.0)

    def test_comovement_reports_beta_per_window(self) -> None:
        rng = np.random.default_rng(5)
        reference = rng.normal(0, 0.02, 200)
        # Twice the reference's move, then three times over the last 90 days.
        own = np.concatenate([2 * reference[:110], 3 * reference[110:]])

        def frame(log_returns: np.ndarray) -> pd.DataFrame:
            close = 100 * np.exp(np.concatenate([[0.0], log_returns.cumsum()]))
            return pd.DataFrame({"timestamp": np.arange(201) * 86_400, "close": close})

        windows = cs.reference_comovement(frame(own), frame(reference), cs.Settings())
        days = (windows["full"]["days"], windows["last_90d"]["days"])
        self.assertEqual(days, (200, 90))
        self.assertAlmostEqual(windows["last_90d"]["beta"], 3.0)
        self.assertAlmostEqual(windows["last_90d"]["correlation"], 1.0)
        self.assertTrue(2.0 < windows["full"]["beta"] < 3.0)

        short = cs.reference_comovement(
            frame(own).tail(61), frame(reference).tail(61), cs.Settings()
        )
        self.assertEqual(list(short), ["full"])  # a 90-day row would repeat it


class FrozenStudyTests(unittest.TestCase):
    def test_fetch_freezes_inputs_and_refuses_an_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = fetched(tmp)
            source = json.loads((out / "source.json").read_text())
            self.assertEqual(
                sorted(source["series"]), ["BTC_1d", "NEW_1d", "X_1d", "X_1h"]
            )
            raw = zlib.decompress((out / "inputs" / "X_1d.json.zlib").read_bytes())
            self.assertEqual(cs.sha256(raw), source["series"]["X_1d"]["raw_sha256"])
            self.assertEqual(source["series"]["X_1d"]["bars"], 260)
            with self.assertRaisesRegex(SystemExit, "output exists"):
                cs.fetch("X", [], out)

    def test_fetch_keeps_symbol_case_and_rejects_path_like_symbols(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars = {("kPEPE", "1d"): 80, ("kPEPE", "1h"): 400, ("BTC", "1d"): 80}
            out = fetched(tmp, bars)
            self.assertTrue((out / "kPEPE_1d.csv").exists())
            source = json.loads((out / "source.json").read_text())
            self.assertEqual(source["references"], ["BTC"])
            for bad in ("../x", "A B", ""):
                with self.assertRaisesRegex(SystemExit, "not a coin symbol"):
                    cs.fetch(bad, [], Path(tmp) / "other")
            self.assertFalse((Path(tmp) / "other").exists())

    def test_analyze_writes_strict_json_and_a_report_of_its_settings(self) -> None:
        def reject(token: str) -> None:
            raise AssertionError(f"non-finite JSON literal {token}")

        with tempfile.TemporaryDirectory() as tmp:
            out = fetched(tmp)
            result = cs.analyze(out, cs.Settings(daily_pivot_span=3))
            stored = json.loads(
                (out / "structure.json").read_text(), parse_constant=reject
            )
            self.assertEqual(stored["schema"], "coin-structure/v1")
            self.assertEqual(stored["settings"]["daily_pivot_span"], 3)
            self.assertEqual(result["summary"]["daily_bars"], 260)
            report = (out / "structure.md").read_text()
            self.assertIn("# X price structure", report)
            self.assertIn(
                "Daily swing levels (7-day pivots, groups no wider than 3%)", report
            )
            self.assertIn("| BTC | last 90d | 90 |", report)
            self.assertIn("Left out for too few shared days: NEW.", report)
            self.assertEqual(result["skipped_references"], ["NEW"])
            self.assertGreater(len(result["daily_levels"]), 3)
            reactions = result["level_reactions"]["hourly_pivots_24bar_horizon"]
            self.assertGreater(reactions["support"]["tests"], 0)
            self.assertGreater(reactions["support"]["placebo"]["tests"], 0)

    def test_levels_are_placed_against_the_last_hourly_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = cs.analyze(fetched(tmp))
            summary = result["summary"]
            newest = summary["last_hourly_close"]
            self.assertNotEqual(newest, summary["last_close"])
            for level in result["daily_levels"] + result["hourly_levels"]:
                self.assertAlmostEqual(level["distance"], level["level"] / newest - 1)
                expected = "resistance" if level["level"] > newest else "support"
                self.assertEqual(level["role"], expected)
            node = result["volume_profiles"]["hourly_last_90d"]["nodes"][0]
            self.assertAlmostEqual(node["distance"], node["level"] / newest - 1)

    def test_calendar_rows_and_summary_match_a_hand_built_series(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars = {("X", "1d"): 260, ("X", "1h"): 24 * 30}
            result = cs.analyze(fetched(tmp, bars, calendar_series()))
        weekday = {row["label"]: row for row in result["weekday"]}
        self.assertAlmostEqual(weekday["Wed"]["mean"], 0.10)
        self.assertAlmostEqual(weekday["Thu"]["mean"], 100 / 110 - 1)
        self.assertAlmostEqual(weekday["Mon"]["mean"], 0.0)
        hours = {row["label"]: row for row in result["hour_utc"]}
        self.assertAlmostEqual(hours["14"]["mean"], 0.01)
        self.assertAlmostEqual(hours["15"]["mean"], 100 / 101 - 1)
        # 30 busy hours of volume 10; the first bar has no return and is left out.
        self.assertAlmostEqual(hours["14"]["volume_share"], 300 / (300 + 689))

        # 1970-01-01 was a Thursday, so day k is a Wednesday when (k + 3) % 7 == 2.
        close = np.array([110.0 if (k + 3) % 7 == 2 else 100.0 for k in range(260)])
        log_returns = np.diff(np.log(close))
        summary = result["summary"]
        self.assertAlmostEqual(
            summary["annualized_volatility"], log_returns.std(ddof=1) * math.sqrt(365)
        )
        self.assertAlmostEqual(
            summary["volatility_30d"], log_returns[-30:].std(ddof=1) * math.sqrt(365)
        )
        # A day's true range spans both closes plus the 0.5 wicks: 11 on a
        # Wednesday and the day after, 1 otherwise. Fourteen days hold two weeks.
        self.assertAlmostEqual(
            summary["atr14_fraction"], (4 * 11 + 10 * 1) / 14 / close[-1]
        )
        self.assertEqual(summary["all_time_high"], 110.5)

    def test_reference_with_too_few_shared_days_is_left_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            correlations = cs.analyze(fetched(tmp))["correlations"]
            self.assertEqual(sorted(correlations), ["BTC"])

    def test_too_little_or_stale_history_is_refused_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            few = fetched(tmp, {("X", "1d"): 40, ("X", "1h"): 400})
            with self.assertRaisesRegex(ValueError, "X: 40 daily bars are too few"):
                cs.analyze(few)
        with tempfile.TemporaryDirectory() as tmp:
            few = fetched(tmp, {("X", "1d"): 80, ("X", "1h"): 100})
            with self.assertRaisesRegex(ValueError, "X: 100 hourly bars are too few"):
                cs.analyze(few)
        with tempfile.TemporaryDirectory() as tmp:
            stale = [
                {**row, "t": row["t"] - 30 * DAY_MS, "T": row["T"] - 30 * DAY_MS}
                for row in random_walk("1h", 400, 1)
            ]
            bars = {("X", "1d"): 80, ("X", "1h"): 400}
            out = fetched(tmp, bars, {("X", "1h"): stale})
            with self.assertRaisesRegex(ValueError, "hourly bars end before"):
                cs.analyze(out)

    def test_analyze_rejects_a_changed_csv_or_raw_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = fetched(tmp)
            csv = out / "X_1d.csv"
            original = csv.read_bytes()
            csv.write_bytes(original + b"\n")
            with self.assertRaisesRegex(ValueError, "frozen hash"):
                cs.analyze(out)
            csv.write_bytes(original)

            raw = out / "inputs" / "X_1h.json.zlib"
            raw.write_bytes(zlib.compress(b"[]"))
            with self.assertRaisesRegex(ValueError, "frozen hash"):
                cs.analyze(out)

    def test_csv_that_is_not_the_normalized_response_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = fetched(tmp)
            csv = out / "BTC_1d.csv"
            lines = csv.read_bytes().split(b"\n")
            lines[1] = lines[1] + b"9"  # alter the first bar's volume
            edited = b"\n".join(lines)
            csv.write_bytes(edited)
            source_path = out / "source.json"
            source = json.loads(source_path.read_text())
            source["series"]["BTC_1d"]["csv_sha256"] = cs.sha256(edited)
            source_path.write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError, "not the normalization"):
                cs.analyze(out)

    def test_main_prints_usage_error_for_an_unknown_phase(self) -> None:
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit) as raised:
            cs.main(["publish", "--output", "/nonexistent"])
        self.assertEqual(raised.exception.code, 2)


class BoundaryTests(unittest.TestCase):
    """Edges a careless edit would move without any other test noticing."""

    CLOSE = np.array([100, 95, 91, 96, 100, 104, 103, 99, 92, 95, 98, 97], dtype=float)

    def react(self, close: np.ndarray, pivots: list[dict], horizon: int) -> dict:
        return cs.level_reactions(close + 1, close - 1, close, pivots, 0.015, horizon)

    def test_candles_of_another_interval_are_dropped(self) -> None:
        rows = [candle(0, 1, 2, 0.5, 1.5, 10), candle(0, 1, 2, 0.5, 1.5, 10, "1h")]
        frame = cs.normalize_candles(rows, "1d", now_ms=10 * DAY_MS)
        self.assertEqual(len(frame), 1)

    def test_a_level_cannot_be_tested_on_its_confirmation_bar(self) -> None:
        def tests(confirm: int) -> int:
            pivot = {"index": 2, "kind": "low", "price": 90.0, "confirm": confirm}
            return self.react(self.CLOSE, [pivot], 2)["support"]["tests"]

        self.assertEqual((tests(7), tests(8)), (1, 0))  # price returns at bar 8

    def test_second_bar_at_a_level_is_not_a_second_test(self) -> None:
        close = self.CLOSE.copy()
        close[7:9] = 91.0  # bars 7 and 8 both sit on the level
        pivot = {"index": 2, "kind": "low", "price": 90.0, "confirm": 4}
        self.assertEqual(self.react(close, [pivot], 1)["support"]["tests"], 1)

    def test_standard_error_and_baseline_are_the_stated_statistics(self) -> None:
        close = np.array(
            [100, 95, 91, 96, 100, 104, 103, 99, 92, 82, 85, 88, 90, 91], dtype=float
        )
        pivot = {"index": 2, "kind": "low", "price": 90.0, "confirm": 4}
        result = self.react(close, [pivot], 1)
        forward = np.array([82 / 92 - 1, 85 / 82 - 1])  # tests at bars 8 and 9
        support = result["support"]
        self.assertEqual(support["tests"], 2)
        self.assertAlmostEqual(support["mean_forward"], forward.mean())
        self.assertAlmostEqual(
            support["standard_error"], forward.std(ddof=1) / math.sqrt(2)
        )
        every_bar = close[1:] / close[:-1] - 1
        self.assertAlmostEqual(result["baseline_mean_forward"], every_bar.mean())
        self.assertAlmostEqual(result["baseline_up_rate"], (every_bar > 0).mean())

    def test_volume_nodes_and_value_area_on_a_three_price_profile(self) -> None:
        price = np.array([10.0, 20.0, 14.0])
        profile = cs.volume_profile(price, price, np.array([60.0, 30.0, 10.0]), 0.05)
        nodes = profile["nodes"]
        self.assertEqual([round(n["share"], 6) for n in nodes], [0.6, 0.3, 0.1])
        for node, expected in zip(nodes, (10.0, 20.0, 14.0), strict=True):
            self.assertLess(abs(node["level"] / expected - 1), 0.05)
        # 60% at the first price is short of 70%, so the area grows upward
        # until it takes in the bin holding 14.
        self.assertAlmostEqual(profile["value_area_low"], 10.0)
        self.assertAlmostEqual(profile["value_area_high"], 10 * math.exp(0.35))

    def test_equal_high_is_not_a_new_peak_and_trough_is_the_lowest_low(self) -> None:
        ts = np.arange(5) * 86_400.0
        high = np.array([10, 20, 15, 20, 12], dtype=float)
        low = np.array([9, 18, 10, 17, 11], dtype=float)
        episodes = cs.drawdowns(ts, high, low, 0.25)
        self.assertEqual(len(episodes), 1)
        episode = episodes[0]
        self.assertEqual((episode["trough"], episode["days_to_trough"]), (10.0, 1))
        self.assertIsNone(episode["recovered_date"])

    def test_a_sample_without_spread_has_no_t_statistic(self) -> None:
        rows = cs.grouped_returns(np.full(4, 0.01), np.zeros(4, dtype=int), ["a"])
        self.assertIsNone(rows[0]["t"])
        self.assertIn("n/a", cs.signed(rows[0]["t"], 2))


class FailureTests(unittest.TestCase):
    def gapped(self) -> list[dict]:
        rows = random_walk("1d", 80, 3)
        return rows[:40] + rows[41:]

    def test_failed_fetch_names_the_series_and_leaves_nothing_behind(self) -> None:
        bars = {("X", "1d"): 80, ("X", "1h"): 400, ("BTC", "1d"): 80}
        null_open = random_walk("1d", 80, 3)
        null_open[5] = {**null_open[5], "o": None}
        for broken in (self.gapped(), null_open):
            with (
                self.subTest(rows=len(broken)),
                tempfile.TemporaryDirectory() as tmp,
            ):
                with self.assertRaisesRegex(ValueError, "BTC_1d: unusable candles"):
                    fetched(tmp, bars, {("BTC", "1d"): broken})
                self.assertEqual(list(Path(tmp).iterdir()), [])
                # The same directory name works on the next attempt.
                self.assertTrue((fetched(tmp, bars) / "source.json").exists())

    def test_analyze_names_a_directory_that_is_not_a_study(self) -> None:
        with (
            tempfile.TemporaryDirectory() as tmp,
            self.assertRaisesRegex(ValueError, "not a fetched study"),
        ):
            cs.analyze(Path(tmp))

    def test_analyze_names_a_missing_frozen_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = fetched(tmp)
            (out / "inputs" / "BTC_1d.json.zlib").unlink()
            with self.assertRaisesRegex(ValueError, "BTC_1d: frozen input unreadable"):
                cs.analyze(out)


class WindowTests(unittest.TestCase):
    def test_recent_profile_covers_exactly_the_stated_days(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = cs.analyze(fetched(tmp))
        profile = result["volume_profiles"]["hourly_last_90d"]
        # Volume is 100 + bar index; 90 days back from the last of 2,400 bars
        # takes in bars 239 to 2,399.
        self.assertAlmostEqual(sum(profile["volume"]), sum(range(339, 2500)))
        # The absolute-return figure must come from absolute returns.
        self.assertNotEqual(
            result["daily_abs_autocorrelation"]["1"],
            result["daily_autocorrelation"]["1"],
        )

    def test_short_hourly_history_is_labelled_with_its_real_span(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars = {("X", "1d"): 80, ("X", "1h"): 400}
            result = cs.analyze(fetched(tmp, bars))
        self.assertEqual(
            list(result["volume_profiles"]), ["daily_full_history", "hourly_last_16d"]
        )


if __name__ == "__main__":
    unittest.main()

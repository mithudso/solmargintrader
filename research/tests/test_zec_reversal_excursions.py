"""Causal event timing, true opens, censoring and excursion units."""

from __future__ import annotations

import unittest

import numpy as np

from research.zec_reversal_excursions import (
    MINUTE,
    NS,
    aggregate,
    event_outcome,
    events_for,
    minute_bars,
)


def bar(stamp, opening=100, close=100, low=None, high=None):
    return {
        "ts": stamp,
        "open": opening,
        "close": close,
        "low": min(opening, close) if low is None else low,
        "high": max(opening, close) if high is None else high,
        "present": True,
        "gap_safe": True,
    }


def fixture(two=False):
    bars = [bar(t) for t in range(0, 3600, MINUTE)]
    bars[0]["open"] = 99 if two else 101
    bars[9]["close"] = 100
    bars[10]["open"] = 100
    bars[19]["close"] = 102
    # Minute1 is above the actual current open; minute2 first closes below.
    bars[20] = bar(1200, 103, 104)
    bars[21] = bar(1260, 104, 102, low=80, high=105)
    return bars


class Causality(unittest.TestCase):
    def test_disjoint_one_and_two_up_setup_contexts_and_first_cross(self):
        for two in (False, True):
            bars = fixture(two)
            events, _ = events_for(bars, "gap_safe", "intrabar")
            event = next(e for e in events if e["current_start"] == 1200)
            self.assertEqual(event["signal_at"], 1320)
            self.assertEqual(event["true_open"], 103)
            self.assertEqual(event["signal_price"], 102)
            self.assertEqual(event["cohort"], "after_two_up" if two else "after_one_up")

    def test_later_same_bar_prices_and_final_color_do_not_select_intrabar_signal(self):
        bars = fixture()
        original = next(
            e
            for e in events_for(bars, "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        for b in bars[22:30]:
            b.update(
                open=500, high=600, low=400, close=550, present=False, gap_safe=False
            )
        changed = next(
            e
            for e in events_for(bars, "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        self.assertEqual(original, changed)
        # Even truncating capture after the known trigger cannot erase it.
        short = next(
            e
            for e in events_for(bars[:22], "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        self.assertEqual(original, short)

    def test_signal_minute_low_is_never_counted_as_later_distance(self):
        bars = fixture()
        for b in bars[22:27]:
            b.update(open=102, low=101, high=103, close=101.5)
        e = next(
            e
            for e in events_for(bars, "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        o = event_outcome(e, {b["ts"]: b for b in bars}, 5)
        self.assertEqual(o["future_low"], 101)
        r = o["references"]["signal_close"]
        self.assertEqual(r["down_usd"], 1)
        self.assertAlmostEqual(r["down_pct"], 100 / 102)
        self.assertEqual(r["adverse_usd"], 1)
        self.assertTrue(r["continued_down"])

    def test_future_lower_low_does_not_imply_lower_endpoint(self):
        bars = fixture()
        for b in bars[22:27]:
            b.update(open=102, low=99, high=106, close=105)
        e = next(
            e
            for e in events_for(bars, "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        r = event_outcome(e, {b["ts"]: b for b in bars}, 5)["references"][
            "signal_close"
        ]
        self.assertEqual(r["down_usd"], 3)
        self.assertFalse(r["continued_down"])
        self.assertEqual(r["endpoint_decline_usd"], -3)

    def test_midpoint_and_close_confirmation_use_only_their_actual_signal_price(self):
        bars = fixture()
        for i in range(22, 30):
            bars[i] = bar(i * MINUTE, 102, 101 - (i - 22) * 0.1)
        for policy, elapsed in (
            ("intrabar", 2),
            ("midpoint", 5),
            ("close_confirmation", 10),
        ):
            e = next(
                e
                for e in events_for(bars, "gap_safe", policy)[0]
                if e["current_start"] == 1200
            )
            self.assertEqual(e["elapsed_minutes"], elapsed)
            self.assertEqual(e["signal_at"], 1200 + elapsed * MINUTE)
            self.assertEqual(e["signal_price"], bars[19 + elapsed]["close"])

    def test_missing_or_gapped_prior_and_current_prefix_withhold_signal(self):
        for slot in (0, 19, 20, 21):
            bars = fixture()
            bars[slot]["gap_safe"] = False
            self.assertFalse(
                any(
                    e["current_start"] == 1200
                    for e in events_for(bars, "gap_safe", "intrabar")[0]
                )
            )
            self.assertTrue(
                any(
                    e["current_start"] == 1200
                    for e in events_for(bars, "present", "intrabar")[0]
                )
            )

    def test_future_gaps_and_capture_edges_censor_without_forwardfill(self):
        bars = fixture()
        e = next(
            e
            for e in events_for(bars, "gap_safe", "intrabar")[0]
            if e["current_start"] == 1200
        )
        table = {b["ts"]: b for b in bars}
        table[1380]["gap_safe"] = False
        self.assertEqual(
            event_outcome(e, table, 5)["status"], "missing_or_gap_censored"
        )
        del table[1380]
        self.assertEqual(event_outcome(e, table, 5)["status"], "capture_censored")

    def test_zero_excursions_and_flat_endpoints_stay_in_denominator(self):
        bars = [bar(t) for t in range(0, 1200, MINUTE)]
        e = {"id": "x", "signal_at": 600, "signal_price": 100, "mask": "gap_safe"}
        s = aggregate([e], {b["ts"]: b for b in bars}, 5)["references"]["signal_close"]
        self.assertEqual(s["n"], 1)
        self.assertEqual(s["down_usd"]["mean"], 0)
        self.assertEqual(s["flat_endpoint"], 1)
        self.assertEqual(s["continuation_rate"], 0)

    def test_next_open_is_separate_reference_and_can_reverse_endpoint_sign(self):
        bars = [bar(t, 95, 97, low=94, high=101) for t in range(600, 900, MINUTE)]
        e = {"id": "x", "signal_at": 600, "signal_price": 100, "mask": "gap_safe"}
        o = event_outcome(e, {b["ts"]: b for b in bars}, 5)
        self.assertTrue(o["references"]["signal_close"]["continued_down"])
        self.assertFalse(o["references"]["next_minute_open"]["continued_down"])
        self.assertEqual(o["references"]["next_minute_open"]["down_usd"], 1)

    def test_nonoverlap_selection_is_time_based_even_when_first_outcome_censored(self):
        bars = [bar(t) for t in range(600, 1800, MINUTE)]
        bars[0]["gap_safe"] = False
        events = [
            {"id": str(t), "signal_at": t, "signal_price": 100, "mask": "gap_safe"}
            for t in (600, 660, 1200)
        ]
        s = aggregate(events, {b["ts"]: b for b in bars}, 5, nonoverlap=True)
        self.assertEqual(s["selected_events"], 2)
        self.assertEqual(s["overlap_excluded"], 1)
        self.assertEqual(s["missing_or_gap_censored"], 1)
        self.assertEqual(s["observed_events"], 1)

    def test_minute_buckets_exact_boundaries_empty_minutes_and_gap_points(self):
        times = np.array([60, 119, 120, 179, 240], dtype=np.int64) * NS
        prices = np.array([100, 102, 101, 98, 99], dtype=float)
        bars = minute_bars(
            times, prices, 20 * NS, 290 * NS, [(120 * NS, 120 * NS, "candidate")]
        )
        self.assertEqual([b["ts"] for b in bars], [60, 120, 180])
        self.assertEqual(bars[0]["close"], 102)
        self.assertEqual(bars[1]["open"], 101)
        self.assertFalse(bars[1]["gap_safe"])
        self.assertFalse(bars[2]["present"])
        self.assertIsNone(bars[2]["close"])

    def test_flat_or_down_previous_bar_cannot_trigger_bearish_continuation_setup(self):
        for close in (100, 99):
            bars = fixture()
            bars[19]["close"] = close
            self.assertFalse(
                any(
                    e["current_start"] == 1200
                    for e in events_for(bars, "gap_safe", "intrabar")[0]
                )
            )


if __name__ == "__main__":
    unittest.main()

"""Fixed-ten-minute bearish conditions, true opens, causality and source cache."""

from __future__ import annotations

import copy
import math
import unittest
from unittest.mock import patch

from oracle.feeds import FeedUnavailable
from research.zec_tui_alerts import bearish_alert
from research.zec_tui_metrics import STREAK_HASH
from research.zec_tui_source import AlertSession, Cancelled

START = 12_000


def bar(stamp, opening=100.0, close=101.0):
    return {
        "ts": stamp,
        "open": opening,
        "high": max(opening, close) + 1,
        "low": min(opening, close) - 1,
        "close": close,
        "volume": 12.0,
    }


def context(now, *, uu=False):
    rows = {
        START - 1200: bar(START - 1200, 102, 101),
        START - 900: bar(START - 900, 101, 100),
        START - 600: bar(START - 600, 100, 101),
        START - 300: bar(START - 300, 101, 102),
        START: bar(START, 100, 99),
    }
    if uu:
        rows[START - 1200] = bar(START - 1200, 98, 99)
        rows[START - 900] = bar(START - 900, 99, 100)
    end = int(now // 300) * 300
    return {
        "rows": {t: row for t, row in rows.items() if t < end},
        "end": end,
        "calculated_at": now,
        "error": None,
        "reference": {"reversals": 19, "total": 24, "source_sha256": STREAK_HASH},
    }


def snapshot(now, price=99.0):
    return {
        "bar": {"ts": int(now // 600) * 600, "open": 200.0, "close": price},
        "connected": True,
        "gap": False,
        "reason": None,
        "partial": True,
        "observed_at": now,
        "event_at": now,
    }


class BearishChecks(unittest.TestCase):
    def test_midpoint_threshold_and_partial_stream_open_is_never_true_open(self):
        for offset, expected in (
            (299, "waiting"),
            (300, "observed_reversal"),
            (303, "observed_reversal"),
            (599.99, "observed_reversal"),
        ):
            with self.subTest(offset=offset):
                now = START + offset
                result = bearish_alert(context(now), snapshot(now), now)
                self.assertEqual(result["state"], expected)
                self.assertEqual(result["target_at"], START + 600)
                self.assertEqual(result["direction"], None if offset < 300 else "DOWN")
                if offset >= 300:
                    self.assertEqual(result["true_open"], 100)
                    self.assertIn("NOT calibrated live odds", result["text"])
                    self.assertFalse(result["qualified"])
        now = START + 303
        # A stream attached at $200 must not turn $101 into a reversal below
        # the true $100 opening of this ten-minute candle.
        result = bearish_alert(context(now), snapshot(now, 101), now)
        self.assertEqual(result["state"], "none")
        self.assertEqual(result["true_open"], 100)
        self.assertEqual(
            bearish_alert(context(now), snapshot(now, 100), now)["state"], "none"
        )

    def test_first_half_must_really_be_completed_and_present(self):
        now = START + 301
        saved = context(now)
        saved["end"] = START
        result = bearish_alert(saved, snapshot(now), now)
        self.assertEqual(result["reason"], "true_open_unavailable")
        saved = context(now)
        saved["rows"].pop(START)
        result = bearish_alert(saved, snapshot(now), now)
        self.assertEqual(result["reason"], "true_open_unavailable")
        self.assertIsNone(result["direction"])

    def test_prior_full_up_requires_both_adjacent_constituents(self):
        now = START + 303
        for missing in (START - 600, START - 300):
            with self.subTest(missing=missing):
                saved = context(now)
                saved["rows"].pop(missing)
                # A nearby off-grid candle cannot replace a missing half.
                saved["rows"][missing + 1] = bar(missing + 1)
                result = bearish_alert(saved, snapshot(now), now)
                self.assertEqual(result["reason"], "previous_constituent_missing")
                self.assertIsNone(result["direction"])

    def test_uu_watch_uses_two_whole_adjacent_ten_minute_bars(self):
        now = START + 10
        saved = context(now, uu=True)
        result = bearish_alert(saved, snapshot(now), now)
        self.assertEqual((result["state"], result["direction"]), ("uu_watch", "DOWN"))
        self.assertEqual(result["target_at"], START + 600)
        self.assertIn("19/24 = 79.2%", result["text"])
        self.assertIn("one captured day", result["text"])
        self.assertIn("NOT LIVE ODDS", result["text"])
        self.assertFalse(result["qualified"])
        for missing in (START - 1200, START - 900):
            with self.subTest(missing=missing):
                incomplete = copy.deepcopy(saved)
                incomplete["rows"].pop(missing)
                result = bearish_alert(incomplete, snapshot(now), now)
                self.assertEqual(result["state"], "waiting")
                self.assertIsNone(result["direction"])

    def test_observed_reversal_takes_priority_over_historical_uu_watch(self):
        now = START + 303
        result = bearish_alert(context(now, uu=True), snapshot(now), now)
        self.assertEqual(result["state"], "observed_reversal")
        self.assertIsNone(result["historical"])
        self.assertNotIn("79.2", result["text"])
        self.assertIn("Midpoint condition untested", result["text"])

    def test_no_symmetric_dd_or_flat_alert(self):
        now = START + 303
        for close in (99, 100):
            with self.subTest(close=close):
                saved = context(now)
                saved["rows"][START - 300] = bar(START - 300, 101, close)
                result = bearish_alert(saved, snapshot(now, 99), now)
                self.assertEqual(result["state"], "none")
                self.assertIsNone(result["direction"])
                self.assertIn("no DD → UP alert", result["text"])

    def test_receipt_and_event_must_be_fresh_real_current_bucket_trades(self):
        now = START + 303
        for key, value in (
            ("connected", False),
            ("gap", True),
            ("reason", "stream_gap"),
            ("observed_at", now - 15.001),
            ("event_at", now - 15.001),
            ("observed_at", now + 0.001),
            ("event_at", now + 0.001),
            ("event_at", math.nan),
        ):
            with self.subTest(key=key, value=value):
                stream = snapshot(now)
                stream[key] = value
                for uu in (True, False):
                    result = bearish_alert(context(now, uu=uu), stream, now)
                    self.assertEqual(result["state"], "unavailable")
                    self.assertIsNone(result["direction"])
        for key, value in (("ts", START - 600), ("close", 0), ("close", math.inf)):
            with self.subTest(key=key, value=value):
                stream = snapshot(now)
                stream["bar"][key] = value
                self.assertEqual(
                    bearish_alert(context(now), stream, now)["state"], "unavailable"
                )
        fresh_edge = snapshot(now)
        fresh_edge.update(observed_at=now - 15, event_at=now - 15)
        self.assertEqual(
            bearish_alert(context(now), fresh_edge, now)["state"], "observed_reversal"
        )

    def test_stale_history_future_history_and_clock_rollback_fail_closed(self):
        now = START + 303
        for key, value in (
            ("end", START),
            ("end", START + 600),
            ("end", START + 1),
            ("end", True),
            ("calculated_at", now + 1),
            ("calculated_at", math.inf),
            ("error", "coinbase_http_429"),
        ):
            with self.subTest(key=key, value=value):
                saved = context(now, uu=True)
                saved[key] = value
                result = bearish_alert(saved, snapshot(now), now)
                self.assertEqual(result["state"], "unavailable")
                self.assertIsNone(result["direction"])
        for bad_now in (0, math.nan, math.inf, True):
            self.assertIsNone(
                bearish_alert(context(now), snapshot(now), bad_now)["target_at"]
            )

    def test_rollover_clears_old_target_and_does_not_reuse_previous_stream_bar(self):
        now = START + 599
        saved = context(now)
        self.assertEqual(
            bearish_alert(saved, snapshot(now), now)["state"], "observed_reversal"
        )
        rolled = bearish_alert(saved, snapshot(now), START + 600)
        self.assertIsNone(rolled["direction"])
        self.assertEqual(rolled["target_at"], START + 1200)
        self.assertNotEqual(rolled["state"], "observed_reversal")

    def test_future_rows_and_bad_ohlcv_cannot_supply_true_open_or_full_bar(self):
        now = START + 303
        saved = context(now)
        baseline = bearish_alert(saved, snapshot(now), now)
        saved["rows"][START + 300] = bar(START + 300, 1, 1000)
        saved["rows"][START + 600] = bar(START + 600, 1, 1000)
        self.assertEqual(bearish_alert(saved, snapshot(now), now), baseline)
        for key, value in (
            ("open", math.nan),
            ("high", 90),
            ("low", 110),
            ("volume", -1),
            ("ts", START + 1),
        ):
            with self.subTest(key=key, value=value):
                corrupt = context(now)
                corrupt["rows"][START][key] = value
                self.assertEqual(
                    bearish_alert(corrupt, snapshot(now), now)["reason"],
                    "true_open_unavailable",
                )

    def test_unverified_history_reference_never_produces_numeric_live_odds(self):
        now = START + 10
        for reference in (
            None,
            {"reversals": 19, "total": 24, "source_sha256": "changed"},
        ):
            saved = context(now, uu=True)
            saved["reference"] = reference
            result = bearish_alert(saved, snapshot(now), now)
            self.assertEqual(result["state"], "uu_watch")
            self.assertIsNone(result["historical"])
            self.assertNotIn("79.2", result["text"])


class AlertClient:
    def __init__(self):
        self.calls = []
        self.error = None
        self.missing = set()

    def fetch(self, step, start, end):
        self.calls.append((step, start, end))
        if self.error:
            raise FeedUnavailable(self.error)
        return {
            t: bar(t)
            for t in range(start - step, end + step, step)
            if t not in self.missing
        }


class AlertSources(unittest.TestCase):
    def setUp(self):
        self.now = [START + 100.0]
        self.client = AlertClient()
        self.source = AlertSession(self.client, clock=lambda: self.now[0])

    def load(self, force=False, cancelled=lambda: False):
        return self.source({"force": force}, cancelled)

    def test_fixed_five_minute_recent_context_filters_provider_extra_rows(self):
        loaded = self.load()
        self.assertEqual(self.client.calls, [(300, START - 1800, START)])
        self.assertEqual(set(loaded["rows"]), set(range(START - 1800, START, 300)))
        self.assertEqual(loaded["reference"]["reversals"], 19)
        self.assertEqual(loaded["reference"]["total"], 24)
        self.assertEqual(loaded["reference"]["source_sha256"], STREAK_HASH)
        self.assertEqual(
            bearish_alert(loaded, snapshot(self.now[0]), self.now[0])["state"],
            "uu_watch",
        )

    def test_success_cache_force_and_new_settled_five_minute_boundary(self):
        first = self.load()
        first["rows"].clear()
        self.assertEqual(len(self.load()["rows"]), 6)
        self.assertEqual(len(self.client.calls), 1)
        self.load(force=True)
        self.assertEqual(len(self.client.calls), 2)
        self.now[0] = START + 302.9
        self.load()
        self.assertEqual(len(self.client.calls), 2)
        self.now[0] = START + 303
        next_half = self.load()
        self.assertEqual(len(self.client.calls), 3)
        self.assertEqual(next_half["end"], START + 300)
        self.assertEqual(self.client.calls[-1], (300, START - 1500, START + 300))
        self.assertIn(START, next_half["rows"])

    def test_failure_backoff_is_preserved_even_for_force_and_does_not_slide(self):
        self.client.error = "coinbase_http_429"
        self.assertEqual(self.load()["error"], "coinbase_http_429")
        deadline = self.source.retry_at
        for offset in (1, 5, 14.99):
            self.now[0] = START + 100 + offset
            self.assertEqual(self.load(force=True)["error"], "coinbase_http_429")
            self.assertEqual(self.source.retry_at, deadline)
        self.assertEqual(len(self.client.calls), 1)
        self.client.error = None
        self.now[0] = deadline
        self.assertIsNone(self.load(force=True)["error"])
        self.assertEqual(len(self.client.calls), 2)

    def test_incomplete_latest_candle_fails_closed_with_backoff(self):
        self.client.missing.add(START - 300)
        self.assertEqual(self.load()["error"], "alert_recent_candle_missing")
        self.load(force=True)
        self.assertEqual(len(self.client.calls), 1)
        self.now[0] += 15
        self.client.missing.clear()
        self.assertIsNone(self.load()["error"])
        self.assertEqual(len(self.client.calls), 2)

    def test_cancellation_leaves_no_partial_context_or_retry_penalty(self):
        cancellation = iter((False, False, True))
        with self.assertRaises(Cancelled):
            self.load(cancelled=lambda: next(cancellation))
        self.assertIsNone(self.source.context)
        self.assertIsNone(self.source.last_error)
        self.assertIsNone(self.load()["error"])
        self.assertEqual(len(self.client.calls), 2)

    def test_reference_failure_cannot_prevent_live_condition_or_invent_fraction(self):
        with patch(
            "research.zec_tui_source.streak_reference",
            side_effect=ValueError("hash mismatch"),
        ):
            loaded = self.load()
        self.assertIsNone(loaded["error"])
        self.assertIsNone(loaded["reference"])
        result = bearish_alert(loaded, snapshot(self.now[0]), self.now[0])
        self.assertEqual(result["state"], "uu_watch")
        self.assertNotIn("79.2", result["text"])


if __name__ == "__main__":
    unittest.main()

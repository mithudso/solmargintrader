"""Frozen HYPE RSI paper cohort: finite sample, source gaps, implementation binding, service shape."""
from __future__ import annotations

import fcntl
import http.client
import io
import itertools
import json
import os
import plistlib
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from email.utils import formatdate
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from ecosystem import hype_forward as h

STEP = h.STEP
START = 1_800_000_000 // STEP * STEP
NOW = START + 1200  # 20 minutes into the hour that follows the seed
TOTAL = h.SEED_BARS + h.MAX_BARS + 40


def series(count, price):
    ts = START - h.SEED_BARS * STEP + np.arange(count) * STEP
    close = np.asarray([price(i) for i in range(count)], dtype=float)
    opens = np.r_[close[0], close[:-1]]
    return {"ts": ts.astype("int64"), "open": opens, "high": np.maximum(opens, close) + .1,
            "low": np.minimum(opens, close) - .1, "close": close, "volume": close * 0 + 1}


def drift(i):
    return 100.0 + i * .2 if i < 60 else (112.0 - (i - 60) * 4.0 if i < 66 else 88.0 + (i - 66) * 1.5)


def dips(i):
    return 100.0 + (i % 80) * .2 - 30.0 * np.exp(-((i % 80) - 40) ** 2 / 4.0)


def oversold_at_activation(i):
    # Rises, then falls hard through the last seed bar so RSI < 30 when the sample starts.
    return 100.0 + i * .2 if i < 191 else 138.0 - (i - 190) * 4.0 if i < 201 else 98.0 - (i - 200) * .3


class Feed:
    """Serves the closed bars of a prebuilt series, as the Binance reader would."""

    def __init__(self, bars):
        self.bars = bars
        self.drop = set()

    def __call__(self, after, now, limit=1000, until=None):
        mask = self.bars["ts"] + STEP + h.CLOSE_SETTLE_S <= (now if until is None else min(now, until))
        if after is not None:
            mask &= self.bars["ts"] > after
        keep = [i for i in np.flatnonzero(mask) if int(self.bars["ts"][i]) not in self.drop]
        if not keep:
            return None
        keep = keep[-limit:] if after is None else keep[:limit]
        rows = {key: value[keep] for key, value in self.bars.items()}
        if len(keep) > 1 and np.any(np.diff(rows["ts"]) != STEP):
            raise h.SourceGap("source_gap")
        return rows


def init(home, feed, owner="hype-test-owner", now=NOW):
    return h.initialize(home, owner, now=now, fetcher=feed, clock=lambda: now)


def tick(home, feed, now):
    return h.tick(home, now=now, fetcher=feed, clock=lambda: now)


def metrics(value):
    return {a["id"]: a["latest"]["metrics"] for a in value["accounts"]}


def klines(ts, o=1, hi=2, lo=.5, c=1.5, v=1, close_time=None):
    return [ts * 1000, str(o), str(hi), str(lo), str(c), str(v), (ts + STEP) * 1000 - 1 if close_time is None else close_time]


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class DoneCohort(unittest.TestCase):
    """One completed cohort, built by a single catch-up tick, shared by read-only tests."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.home = Path(cls.tmp.name) / "cohort"
        cls.feed = Feed(series(TOTAL, drift))
        cls.meta = init(cls.home, cls.feed)["metadata"]
        cls.done = tick(cls.home, cls.feed, cls.meta["last_sample_bar"] + STEP + 100)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_catch_up_across_the_last_sample_bar_truncates_and_completes(self):
        value = self.done
        self.assertEqual((value["status"], value["reason"]), ("completed", "sample_complete"))
        self.assertEqual((value["last_ts"], value["sample_bars"]), (self.meta["last_sample_bar"], h.MAX_BARS))
        with closing(sqlite3.connect(self.home / "hype-forward.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT max(bar) FROM candles").fetchone()[0], self.meta["last_sample_bar"])
        self.assertGreater(value["late_bars"], 0)

    def test_completed_sample_never_reads_the_feed_again(self):
        calls = []
        value = h.tick(self.home, now=self.meta["expires_at"] - 1, fetcher=lambda *a, **k: calls.append(a), clock=lambda: 0)
        self.assertEqual((calls, value["status"]), ([], "completed"))

    def test_completion_outranks_a_later_expiry(self):
        value = tick(self.home, self.feed, self.meta["expires_at"] + STEP)
        self.assertEqual((value["status"], value["reason"]), ("completed", "sample_complete"))

    def test_a_finished_sample_cannot_be_overwritten_by_a_late_terminal_write(self):
        h._terminal(self.home, "blocked", "stale_loser")
        self.assertEqual(h.report(self.home)["status"], "completed")

    def test_each_account_reports_finite_ordered_results(self):
        by_id = metrics(self.done)
        self.assertEqual(set(by_id), {a["id"] for a in h.ACCOUNTS})
        for item in by_id.values():
            self.assertTrue(np.isfinite(item["total_return"]))
            self.assertGreaterEqual(item["max_drawdown"], 0.0)
        self.assertGreaterEqual(by_id["rsi-fill1-fee10"]["total_return"], by_id["rsi-fill1-fee25"]["total_return"])

    def test_stale_flag_is_false_once_the_sample_is_finished(self):
        self.assertFalse(h.report(self.home, now=self.meta["expires_at"] + 10 * STEP)["stale"])


class HypeForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "cohort"
        self.feed = Feed(series(TOTAL, drift))

    def test_owner_label_is_required_and_validated(self):
        for bad in ("", "AB", "has space", None, "x" * 80, "abc\n"):
            with self.subTest(owner=bad), self.assertRaisesRegex(ValueError, "invalid_owner_label"):
                init(self.home, self.feed, owner=bad)
            self.assertFalse(self.home.exists())

    def test_initialization_freezes_rule_sample_and_expiry(self):
        value = init(self.home, self.feed)
        meta = value["metadata"]
        self.assertTrue(value["paper_only"])
        self.assertEqual(meta["spec"], h.SPEC)
        self.assertEqual((meta["spec"]["oversold"], meta["spec"]["exit_level"]), (30.0, 55.0))
        self.assertEqual(meta["activation"], START + STEP)
        self.assertEqual(meta["last_sample_bar"], meta["activation"] + (h.MAX_BARS - 1) * STEP)
        self.assertEqual(meta["expires_at"], meta["activation"] + (h.MAX_BARS + h.EXPIRY_GRACE_BARS) * STEP)
        self.assertEqual(value["status"], "running")
        self.assertTrue(all(a["latest"] is None for a in value["accounts"]))
        self.assertIn("backtester/core/engine.py", meta["implementation"])
        self.assertRegex(meta["implementation"]["runtime"]["numpy"], r"^\d+\.\d+$")
        self.assertRegex(meta["implementation"]["runtime"]["python"], r"^\d+\.\d+$")
        with self.assertRaises(FileExistsError):
            init(self.home, self.feed)

    def test_a_failed_init_leaves_no_store_and_no_staging_file(self):
        with patch.object(h.os, "link", side_effect=OSError("boom")), self.assertRaises(OSError):
            init(self.home, self.feed)
        self.assertEqual(list(self.home.iterdir()), [])
        init(self.home, self.feed)  # a clean retry works

    def test_stale_seed_is_refused(self):
        with self.assertRaisesRegex(ValueError, "seed_stale"):
            h.initialize(self.home, "hype-test-owner", now=NOW + 5 * STEP,
                         fetcher=lambda after, now, limit=1000: self.feed(after, NOW, limit),
                         clock=lambda: NOW + 5 * STEP)

    def test_no_account_trades_before_activation_even_when_oversold_at_the_seed_end(self):
        feed = Feed(series(TOTAL, oversold_at_activation))
        init(self.home, feed)
        first = tick(self.home, feed, NOW + STEP)  # bar ts=START: still before activation
        self.assertEqual(first["sample_bars"], 0)
        for account in first["accounts"]:
            if account["kind"] == "rsi":
                self.assertEqual(account["latest"]["metrics"]["trades"], 0, account["id"])
                self.assertFalse(account["latest"]["metrics"]["open"], account["id"])
        later = tick(self.home, feed, START + 3 * STEP + 1200)  # activation bar closed, fill bar visible
        self.assertEqual(later["sample_bars"], 2)
        self.assertTrue(metrics(later)["rsi-fill1-fee10"]["open"])

    def test_sample_ends_by_itself_at_the_frozen_bar_count_on_hourly_ticks(self):
        meta = init(self.home, self.feed)["metadata"]
        now, value = NOW, None
        for _ in range(h.MAX_BARS + 10):
            now += STEP
            value = tick(self.home, self.feed, now)
            if value["status"] != "running":
                break
        self.assertEqual((value["status"], value["last_ts"], value["sample_bars"], value["late_bars"]),
                         ("completed", meta["last_sample_bar"], h.MAX_BARS, 0))

    def test_dip_is_bought_and_costs_and_delay_change_the_result(self):
        feed = Feed(series(TOTAL, dips))
        meta = init(self.home, feed)["metadata"]
        by_id = metrics(tick(self.home, feed, meta["last_sample_bar"] + STEP + 100))
        self.assertGreaterEqual(by_id["rsi-fill1-fee10"]["trades"], 1)
        self.assertGreater(by_id["rsi-fill1-fee10"]["total_return"], by_id["rsi-fill1-fee25"]["total_return"])
        self.assertGreater(by_id["rsi-fill2-fee10"]["total_return"], by_id["rsi-fill2-fee25"]["total_return"])
        self.assertNotEqual(by_id["rsi-fill1-fee10"]["total_return"], by_id["rsi-fill2-fee10"]["total_return"])
        self.assertTrue(by_id["hold-fee10"]["open"])

    def test_source_gap_ends_the_sample_and_is_never_backfilled(self):
        init(self.home, self.feed)
        now = NOW + STEP
        tick(self.home, self.feed, now)
        self.feed.drop = {START + 2 * STEP}
        value = None
        for _ in range(6):
            now += STEP
            value = tick(self.home, self.feed, now)
        self.assertEqual((value["status"], value["reason"]),
                         ("blocked", f"source_gap:expected={START + 2 * STEP},got={START + 3 * STEP}"))
        stored = value["last_ts"]
        self.feed.drop = set()
        again = tick(self.home, self.feed, now + 10 * STEP)
        self.assertEqual((again["last_ts"], again["status"]), (stored, "blocked"))

    def test_transient_feed_errors_retry_and_stay_visible(self):
        init(self.home, self.feed)
        now = NOW + STEP
        value = None
        for error in (TimeoutError("down"), h.FeedError("invalid_feed_prices")):
            with self.subTest(error=type(error).__name__):
                def failing(*args, error=error, **kwargs):
                    raise error
                value = h.tick(self.home, now=now, fetcher=failing, clock=lambda: now)
                self.assertEqual(value["status"], "running")
                self.assertIn("feed_error:" + type(error).__name__, value["reason"])
        before = value["last_ts"]
        recovered = tick(self.home, self.feed, now)
        self.assertGreater(recovered["last_ts"], before)
        self.assertIsNone(recovered["reason"])

    def test_defects_outside_the_feed_are_not_swallowed(self):
        init(self.home, self.feed)

        def broken(*args, **kwargs):
            raise TypeError("bug")
        with self.assertRaises(TypeError):
            h.tick(self.home, now=NOW + STEP, fetcher=broken, clock=lambda: NOW + STEP)

    def test_expiry_needs_two_consecutive_polls_and_survives_one_bad_clock_read(self):
        meta = init(self.home, self.feed)["metadata"]
        late = meta["expires_at"] + 1
        self.assertEqual(tick(self.home, self.feed, late)["status"], "running")
        self.assertEqual(tick(self.home, self.feed, NOW + STEP)["status"], "running")  # clock recovered, strike cleared
        self.assertEqual(tick(self.home, self.feed, late)["status"], "running")
        value = tick(self.home, self.feed, late + 30)
        self.assertEqual((value["status"], value["reason"]), ("expired", "hard_expiry_before_sample_complete"))

    def test_strikes_clear_on_any_poll_before_expiry_even_inside_the_wait_window(self):
        meta = init(self.home, self.feed)["metadata"]
        late = meta["expires_at"] + 1
        self.assertEqual(tick(self.home, self.feed, late)["status"], "running")  # strike 1
        h.tick(self.home, now=NOW + 10, fetcher=lambda *a: None, clock=lambda: NOW + 10)  # no fetch is due
        self.assertEqual(tick(self.home, self.feed, late)["status"], "running")  # strike 1 again, not 2

    def test_a_hot_journal_left_by_a_killed_writer_is_recovered_for_every_reader(self):
        init(self.home, self.feed)
        database = self.home / "hype-forward.sqlite3"
        script = (f"import os,sqlite3;db=sqlite3.connect({str(database)!r},isolation_level=None);"
                  "db.execute('PRAGMA cache_size=1');db.execute('BEGIN');"
                  "db.executemany('INSERT INTO snapshots VALUES(?,?,?,?)',[('x',i,0.0,'y'*2000) for i in range(3000)]);"
                  "os._exit(1)")
        subprocess.run([sys.executable, "-c", script], check=False)
        journal = Path(str(database) + "-journal")
        self.assertTrue(journal.exists() and journal.stat().st_size > 0, "the fixture must leave a hot journal")
        self.assertEqual(h.report(self.home)["status"], "running")
        self.assertFalse(journal.exists())
        with closing(sqlite3.connect(database)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 0)

    def test_fetch_waits_until_the_next_bar_has_settled(self):
        last = init(self.home, self.feed)["last_ts"]
        calls = []
        h.tick(self.home, now=last + 2 * STEP + h.CLOSE_SETTLE_S - 1, fetcher=lambda *a, **k: calls.append(a), clock=lambda: 0)
        self.assertEqual(calls, [])
        h.tick(self.home, now=last + 2 * STEP + h.CLOSE_SETTLE_S, fetcher=lambda *a, **k: calls.append(a), clock=lambda: 0)
        self.assertEqual(len(calls), 1)

    def test_changed_implementation_blocks_and_stays_blocked(self):
        init(self.home, self.feed)
        altered = {**h.implementation(), "ecosystem/hype_forward.py": "0" * 64}
        with patch.object(h, "implementation", return_value=altered):
            value = tick(self.home, self.feed, NOW + STEP)
        self.assertEqual(value["status"], "blocked")
        self.assertTrue(value["reason"].startswith("implementation_changed:"), value["reason"])
        self.assertEqual(value["reason"], "implementation_changed:ecosystem/hype_forward.py")  # names what differs
        again = tick(self.home, self.feed, NOW + 3 * STEP)
        self.assertEqual((again["status"], again["reason"], again["last_ts"]),
                         ("blocked", value["reason"], value["last_ts"]))

    def test_late_observation_is_counted_exactly_and_accumulates(self):
        init(self.home, self.feed)
        value = tick(self.home, self.feed, START + 6 * STEP)
        # Bars ts=START..START+4*STEP arrive at START+6*STEP; only an age beyond two steps is late.
        self.assertEqual(value["late_bars"], 4)
        self.assertEqual(tick(self.home, self.feed, START + 6 * STEP + 1200)["late_bars"], 4)

    def test_stale_flag_boundary(self):
        last = init(self.home, self.feed)["last_ts"]
        self.assertFalse(h.report(self.home, now=last + 3 * STEP + h.STALE_GRACE_S - 1)["stale"])
        self.assertTrue(h.report(self.home, now=last + 3 * STEP + h.STALE_GRACE_S)["stale"])

    def test_a_racing_writer_does_not_end_the_sample(self):
        init(self.home, self.feed)
        now = NOW + STEP

        def racing(after, at, limit=1000, until=None):
            arrays = self.feed(after, at, limit, until)
            tick(self.home, self.feed, now)  # the other writer advances first
            return arrays
        value = h.tick(self.home, now=now, fetcher=racing, clock=lambda: now)
        self.assertEqual(value["status"], "running")
        self.assertEqual(value["last_ts"], START)
        self.assertEqual(h.report(self.home)["sample_bars"], 0)

    def test_a_gap_after_the_sample_end_does_not_block_a_complete_sample(self):
        meta = init(self.home, self.feed)["metadata"]
        last = meta["last_sample_bar"]
        self.feed.drop = {last + 2 * STEP}
        value = tick(self.home, self.feed, last + 5 * STEP)
        self.assertEqual((value["status"], value["last_ts"]), ("completed", last))

    def test_polling_long_after_the_sample_end_completes_through_the_real_reader(self):
        meta = init(self.home, self.feed)["metadata"]
        last = meta["last_sample_bar"]
        tick(self.home, self.feed, last + 100)  # catch up to the bar before the last
        bars = self.feed.bars
        wanted = np.isin(bars["ts"], [last, last + STEP, last + 2 * STEP])
        rows = [klines(int(t), o, hi, lo, c, v) for t, o, hi, lo, c, v in zip(*(bars[k][wanted] for k in h.FIELDS))]
        now = last + STEP + h.MAX_SKEW_S * 10  # a late wake-up: well past the cap plus the skew margin

        def served(request, timeout):
            response = Response(json.dumps(rows).encode())
            response.headers = {"Date": formatdate(now, usegmt=True)}
            return response
        with patch.object(h, "urlopen", side_effect=served):
            value = h.tick(self.home, now=now, fetcher=h.fetch_closed, clock=lambda: now)
        self.assertEqual((value["status"], value["last_ts"]), ("completed", last))

    def test_candles_are_immutable(self):
        init(self.home, self.feed)
        with closing(sqlite3.connect(self.home / "hype-forward.sqlite3")) as db:
            with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable_paper_candle"):
                db.execute("UPDATE candles SET close=1")
            with self.assertRaisesRegex(sqlite3.DatabaseError, "immutable_paper_candle"):
                db.execute("DELETE FROM candles")

    def test_store_safety(self):
        init(self.home, self.feed)
        link = self.root / "link"
        link.symlink_to(self.home)
        with self.assertRaisesRegex(ValueError, "unsafe_paper_home"):
            h.report(link)
        other = self.root / "other"
        other.mkdir()
        (other / "hype-forward.sqlite3").symlink_to(self.home / "hype-forward.sqlite3")
        with self.assertRaisesRegex(ValueError, "unsafe_paper_store"):
            h.report(other)
        foreign = self.root / "foreign"
        foreign.mkdir()
        sqlite3.connect(foreign / "hype-forward.sqlite3").close()
        with self.assertRaisesRegex(ValueError, "incompatible_paper_store"):
            h.report(foreign)

    def test_write_connection_rolls_back_and_read_connection_cannot_write(self):
        init(self.home, self.feed)
        with self.assertRaises(RuntimeError), h.connection(self.home, write=True) as db:
            db.execute("UPDATE state SET reason='x'")
            raise RuntimeError
        self.assertIsNone(h.report(self.home)["reason"])
        with self.assertRaises(sqlite3.OperationalError), h.connection(self.home) as db:
            db.execute("UPDATE state SET reason='x'")


class FetchClosedTests(unittest.TestCase):
    def fetch(self, payload, after=None, now=NOW, raw=None, record=None, server_now=None, date=True):
        body = raw if raw is not None else json.dumps(payload).encode()

        def fake(request, timeout):
            if record is not None:
                record.append(request.full_url)
            response = Response(body)
            stamp = formatdate(now if server_now is None else server_now, usegmt=True) if date is True else date
            response.headers = {} if stamp is False else {"Date": stamp}
            return response
        with patch.object(h, "urlopen", side_effect=fake):
            return h.fetch_closed(after, now)

    def test_forming_and_unsettled_bars_are_excluded(self):
        forming = [klines(START - STEP), klines(START)]
        self.assertEqual(self.fetch(forming)["ts"].tolist(), [START - STEP])
        # Closed at START, but the settle margin has not passed yet.
        self.assertIsNone(self.fetch(forming, now=START + h.CLOSE_SETTLE_S - 1))
        self.assertIsNotNone(self.fetch(forming, now=START + h.CLOSE_SETTLE_S))

    def test_local_clock_skew_cannot_store_a_forming_bar(self):
        forming = [klines(START - STEP), klines(START)]
        # The local clock says the bar has closed; the venue's clock says it has not.
        arrays = self.fetch(forming, now=START + STEP + 4, server_now=START + STEP - 20)
        self.assertEqual(arrays["ts"].tolist(), [START - STEP])
        # Both clocks agree: the bar is accepted.
        self.assertEqual(self.fetch(forming, now=START + STEP + 4)["ts"].tolist(), [START - STEP, START])

    def test_a_clock_far_from_the_venues_is_refused(self):
        for offset in (-h.MAX_SKEW_S - 5, h.MAX_SKEW_S + 5):
            with self.subTest(offset=offset), self.assertRaisesRegex(h.FeedError, "clock_skew"):
                self.fetch([klines(START - STEP)], server_now=NOW + offset)
        self.assertIsNotNone(self.fetch([klines(START - STEP)], server_now=NOW + h.MAX_SKEW_S))

    def test_a_zone_less_date_is_not_read_as_local_time(self):
        for zone in ("America/New_York", "Asia/Tokyo", "UTC"):
            with self.subTest(zone=zone), patch.dict(os.environ, {"TZ": zone}):
                time.tzset()
                self.addCleanup(time.tzset)
                with self.assertRaisesRegex(h.FeedError, "missing_server_time"):
                    self.fetch([klines(START - STEP)], date="Fri, 15 Jan 2027 08:58:20 -0000")

    def test_missing_or_garbled_server_time_fails_closed(self):
        for date in (False, "nonsense"):
            with self.subTest(date=date), self.assertRaisesRegex(h.FeedError, "missing_server_time"):
                self.fetch([klines(START - STEP)], date=date)

    def test_request_parameters_and_after_filter(self):
        urls = []
        arrays = self.fetch([klines(START - 2 * STEP), klines(START - STEP)], after=START - 2 * STEP, record=urls)
        self.assertEqual(arrays["ts"].tolist(), [START - STEP])
        self.assertIn(f"startTime={(START - STEP) * 1000}", urls[0])
        self.assertIn("symbol=HYPEUSDT", urls[0])
        self.assertIn("interval=1h", urls[0])

    def test_invalid_payloads_are_typed_feed_errors(self):
        cases = [
            ("invalid_feed", {"not": "a list"}),
            ("invalid_feed_candle", [["x"]]),
            ("invalid_feed_timestamp", [klines(START - STEP + 5)]),
            ("invalid_feed_timestamp", [klines(START - STEP, close_time=1)]),
            ("invalid_feed_prices", [klines(START - STEP, c="NaN")]),
            ("invalid_feed_prices", [klines(START - STEP, hi=1, c=1.5)]),
            ("invalid_feed_prices", [klines(START - STEP, lo=0)]),
            ("invalid_feed_prices", [klines(START - STEP, v=-1)]),
        ]
        for label, payload in cases:
            with self.subTest(case=label, payload=str(payload)[:40]), self.assertRaisesRegex(h.FeedError, label):
                self.fetch(payload)
        self.assertEqual(self.fetch([klines(START - STEP)])["ts"].tolist(), [START - STEP])

    def test_overflow_and_garbage_become_feed_errors_not_crashes(self):
        opened = (START - STEP) * 1000
        bad_close = b'[[%d,"1","2","0.5","1.5","1",Infinity]]' % opened
        huge = b'[[%d,"1","2","0.5","1e999","1",%d]]' % (opened, START * 1000 - 1)
        for raw in (bad_close, b"not json", huge):
            with self.subTest(raw=raw[:20]), self.assertRaises(h.FeedError):
                self.fetch(None, raw=raw)

    def test_oversized_response_and_http_errors(self):
        with self.assertRaisesRegex(h.FeedError, "feed_response_too_large"):
            self.fetch(None, raw=b" " * 2_000_001)
        with patch.object(h, "urlopen", side_effect=http.client.IncompleteRead(b"")), self.assertRaises(OSError):
            h.fetch_closed(None, NOW)

    def test_gap_between_returned_bars_is_a_source_gap(self):
        with self.assertRaises(h.SourceGap):
            self.fetch([klines(START - 3 * STEP), klines(START - STEP)])

    def test_duplicate_or_reordered_rows_are_a_bad_payload_not_a_gap(self):
        for rows in ([klines(START - STEP), klines(START - STEP)], [klines(START - STEP), klines(START - 2 * STEP)]):
            with self.subTest(rows=len(rows)), self.assertRaisesRegex(h.FeedError, "invalid_feed_order") as raised:
                self.fetch(rows)
            self.assertNotIsInstance(raised.exception, h.SourceGap)


class RunAndCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "cohort"
        self.feed = Feed(series(TOTAL, drift))
        for sig in (signal.SIGINT, signal.SIGTERM):
            self.addCleanup(signal.signal, sig, signal.getsignal(sig))

    def run_loop(self, ticks):
        out = io.StringIO()
        with patch.object(h, "tick", side_effect=ticks), patch.object(h.time, "sleep"), \
                patch.object(h.time, "monotonic", side_effect=itertools.count(0, 31)), redirect_stdout(out):
            code = h.run(self.home, poll=30)
        return code, [json.loads(line) for line in out.getvalue().splitlines()]

    @staticmethod
    def value(status, **extra):
        return {"as_of": 1, "status": status, "reason": None, "last_ts": 2, "sample_bars": 3,
                "late_bars": 0, "stale": False, **extra}

    def test_run_exits_zero_when_the_sample_finishes_so_launchd_does_not_restart_it(self):
        init(self.home, self.feed)
        code, lines = self.run_loop([self.value("running"), self.value("completed", reason="sample_complete")])
        self.assertEqual(code, 0)
        self.assertEqual([line["status"] for line in lines], ["running", "completed"])
        self.assertIn("late_bars", lines[0])

    def test_run_reports_store_errors_with_detail_and_keeps_going(self):
        init(self.home, self.feed)
        code, lines = self.run_loop([sqlite3.OperationalError("disk"), self.value("blocked", reason="source_gap")])
        self.assertEqual(code, 0)
        self.assertEqual((lines[0]["status"], lines[0]["reason"]), ("store_error", "paper_store_failed"))
        self.assertIn("OperationalError:disk", lines[0]["error"])

    def test_second_run_exits_cleanly_instead_of_crashing(self):
        init(self.home, self.feed)
        fd = os.open(self.home / "hype-forward.lock", os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(h.run(self.home), 0)
        self.assertEqual(json.loads(out.getvalue()), {"status": "already_running"})

    def test_run_fails_fast_on_a_missing_store(self):
        with self.assertRaises(sqlite3.OperationalError):
            h.run(self.root / "missing")

    def test_repeated_store_failures_end_the_process_with_a_failing_exit_code(self):
        init(self.home, self.feed)
        code, lines = self.run_loop([sqlite3.OperationalError("disk")] * h.MAX_STORE_ERRORS)
        self.assertEqual(code, 2)
        self.assertEqual(lines[-1]["failures"], h.MAX_STORE_ERRORS)

    def test_a_good_poll_resets_the_failure_count(self):
        init(self.home, self.feed)
        broken = [sqlite3.OperationalError("disk")] * (h.MAX_STORE_ERRORS - 1)
        code, _ = self.run_loop([*broken, self.value("running"), *broken, self.value("completed")])
        self.assertEqual(code, 0)

    def test_sigterm_stops_the_loop_cleanly(self):
        init(self.home, self.feed)

        def term(*args):
            os.kill(os.getpid(), signal.SIGTERM)
            return self.value("running")
        code, lines = self.run_loop(term)
        self.assertEqual((code, len(lines)), (0, 1))

    def test_main_status_init_errors_and_help(self):
        init(self.home, self.feed)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(h.main(["--home", str(self.home), "status"]), 0)
        self.assertTrue(json.loads(out.getvalue())["paper_only"])
        err = io.StringIO()
        with patch.object(h, "urlopen", side_effect=AssertionError("no network call is allowed")), redirect_stderr(err):
            self.assertEqual(h.main(["--home", str(self.root / "none"), "status"]), 2)
            self.assertEqual(h.main(["--home", str(self.root / "x"), "init", "--owner", "AB"]), 2)
            self.assertEqual(h.main(["--home", str(self.home), "init", "--owner", "valid-owner"]), 2)
        text = err.getvalue()
        self.assertIn("run init --owner <label> first", text)
        self.assertIn("invalid_owner_label", text)
        self.assertIn("a store already exists", text)
        self.assertFalse((self.root / "x").exists())
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            h.main(["--home", str(self.home), "init"])

    def test_main_dispatches_run_and_install(self):
        with patch.object(h, "run", return_value=0) as run:
            self.assertEqual(h.main(["--home", str(self.home), "run"]), 0)
        run.assert_called_once_with(self.home)
        with patch.object(h, "install_service", return_value={"label": "l"}) as install, redirect_stdout(io.StringIO()):
            self.assertEqual(h.main(["--home", str(self.home), "install-service", "--python", "/x/python"]), 0)
        install.assert_called_once_with(self.home, Path("/x/python"))


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "cohort"
        init(self.home, Feed(series(TOTAL, drift)))
        self.fake_home = self.root / "fake-home"
        self.fake_home.mkdir()
        self.calls = []

    def python(self, name="venv"):
        path = self.root / name / "bin" / "python"
        path.parent.mkdir(parents=True)
        path.write_text("")
        path.chmod(0o755)
        return path

    def runner(self, implementation=None, loaded=False, probe=(0, None, ""), fail_bootstrap=False):
        def fake(cmd, **kwargs):
            self.calls.append(list(cmd))
            if cmd[0] != "launchctl":  # the installed-code probe
                code, out, err = probe
                return SimpleNamespace(returncode=code, stderr=err,
                                       stdout=out if out is not None else json.dumps(implementation or h.implementation()))
            if cmd[1] == "print":
                return SimpleNamespace(returncode=0 if loaded else 1, stdout=b"", stderr=b"")
            if cmd[1] == "bootstrap" and fail_bootstrap:
                raise subprocess.CalledProcessError(5, cmd, stderr=b"Bootstrap failed: 5")
            return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
        return fake

    def install(self, python, implementation=None, **options):
        with patch("pathlib.Path.home", return_value=self.fake_home), \
                patch.object(h.sys, "platform", "darwin"), \
                patch.object(h.subprocess, "run", side_effect=self.runner(implementation, **options)):
            return h.install_service(self.home, python=python)

    def test_the_installed_code_probe_is_isolated_with_dash_i(self):
        python = self.python()
        self.install(python)
        probe = self.calls[0]
        self.assertEqual(probe[:3], [str(python), "-I", "-c"])
        self.assertNotEqual(probe[0], "launchctl")

    def test_plist_restarts_only_after_a_crash_and_is_bootstrapped(self):
        result = self.install(self.python())
        document = plistlib.loads(Path(result["path"]).read_bytes())
        self.assertEqual(document["KeepAlive"], {"SuccessfulExit": False})
        self.assertTrue(document["RunAtLoad"])
        self.assertEqual(document["ThrottleInterval"], 10)
        self.assertEqual(document["ProgramArguments"][1:],
                         ["-I", "-m", "ecosystem.hype_forward", "--home", str(self.home), "run"])
        self.assertEqual([c[1] for c in self.calls if c[0] == "launchctl"], ["print", "bootstrap", "enable"])
        self.assertEqual(oct(Path(result["path"]).stat().st_mode & 0o777), "0o600")

    def test_installed_code_that_differs_from_the_frozen_hash_is_refused_before_anything_is_written(self):
        with self.assertRaisesRegex(ValueError, "installed_implementation_mismatch"):
            self.install(self.python(), implementation={"ecosystem/hype_forward.py": "0" * 64})
        self.assertEqual(list(self.fake_home.rglob("*.plist")), [])
        self.assertFalse([c for c in self.calls if c[0] == "launchctl"])

    def test_worktree_interpreter_is_refused_without_side_effects(self):
        with self.assertRaisesRegex(ValueError, "stable_installed_python_required"):
            self.install(self.python("proj-wt-abc"))
        self.assertEqual(self.calls, [])
        self.assertEqual(list(self.fake_home.rglob("*.plist")), [])

    def test_an_already_loaded_service_is_not_bootstrapped_twice(self):
        self.install(self.python(), loaded=True)
        self.assertEqual([c[1] for c in self.calls if c[0] == "launchctl"], ["print", "enable"])

    def test_launchctl_failure_names_the_cause(self):
        with self.assertRaisesRegex(ValueError, "launchctl_failed: Bootstrap failed: 5"):
            self.install(self.python(), fail_bootstrap=True)

    def test_a_failed_probe_shows_why_the_interpreter_cannot_import_the_code(self):
        with self.assertRaisesRegex(ValueError, "installed_probe_failed: .*ModuleNotFoundError"):
            self.install(self.python(), probe=(1, "", "ModuleNotFoundError: No module named 'ecosystem'"))
        with self.assertRaisesRegex(ValueError, "installed_probe_output_invalid"):
            self.install(self.python("other"), probe=(0, "not json", ""))
        self.assertEqual(list(self.fake_home.rglob("*.plist")), [])

    def test_service_needs_macos(self):
        with patch.object(h.sys, "platform", "linux"), self.assertRaisesRegex(ValueError, "launchd_service_requires_macos"):
            h.install_service(self.home, python=self.python())

    def test_a_conflicting_existing_plist_is_not_overwritten(self):
        python = self.python()
        path = Path(self.install(python)["path"])
        path.write_bytes(plistlib.dumps({"Label": "other"}))
        with self.assertRaisesRegex(ValueError, "service_configuration_conflict"):
            self.install(python)
        self.assertEqual(plistlib.loads(path.read_bytes()), {"Label": "other"})


if __name__ == "__main__":
    unittest.main()

"""Incremental aggregation and checkpoint round-trip in `research/tick_backfill.py`.

The backfill walks a month of trades BACKWARD in pages, folding each page into
a running per-bar aggregate. That means a bar's opening trade usually arrives
*after* its closing trade, and often in a different page entirely. If the merge
uses arrival order anywhere, open and close come out swapped -- silently, and
only on bars that straddle a page boundary, which is the hardest possible thing
to notice in a month of output. These tests pin that.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.ticks import _parse_trades  # noqa: E402
from research.tick_backfill import MinuteAggregator, _write_ck  # noqa: E402

BASE = "2026-07-06T00:00:"


def _trades(spec: list[tuple[int, str, float, float]]) -> pd.DataFrame:
    """(trade_id, 'SS.ffffff', price, size) -> a parsed tick frame."""
    return _parse_trades(
        [
            {"trade_id": tid, "side": "buy", "size": str(size),
             "price": str(price), "time": f"{BASE}{sec}Z"}
            for tid, sec, price, size in spec
        ]
    )


class TestMinuteAggregator(unittest.TestCase):
    def setUp(self):
        self.agg = MinuteAggregator(60)

    def test_single_page_gives_time_ordered_ohlc(self):
        self.agg.add(_trades([(3, "30.0", 103.0, 1.0), (2, "20.0", 99.0, 2.0),
                              (1, "10.0", 100.0, 3.0)]))
        bar = self.agg.frame().iloc[0]
        self.assertEqual(bar["open"], 100.0)
        self.assertEqual(bar["close"], 103.0)
        self.assertEqual(bar["high"], 103.0)
        self.assertEqual(bar["low"], 99.0)
        self.assertEqual(bar["volume"], 6.0)

    def test_open_survives_arriving_in_a_later_page(self):
        """The backward walk: the newest page lands first, the open comes last."""
        self.agg.add(_trades([(9, "50.0", 105.0, 1.0)]))          # newest page
        self.agg.add(_trades([(1, "05.0", 100.0, 1.0)]))          # older page
        bar = self.agg.frame().iloc[0]
        self.assertEqual(bar["open"], 100.0, "the earliest trade must win the open")
        self.assertEqual(bar["close"], 105.0, "the latest trade must keep the close")

    def test_close_is_not_overwritten_by_an_older_page(self):
        self.agg.add(_trades([(9, "50.0", 105.0, 1.0)]))
        self.agg.add(_trades([(5, "30.0", 101.0, 1.0)]))
        self.assertEqual(self.agg.frame().iloc[0]["close"], 105.0)

    def test_page_order_does_not_change_the_result(self):
        pages = [
            _trades([(1, "05.0", 100.0, 1.0)]),
            _trades([(2, "25.0", 98.0, 2.0)]),
            _trades([(3, "45.0", 104.0, 3.0)]),
        ]
        forward, backward = MinuteAggregator(60), MinuteAggregator(60)
        for p in pages:
            forward.add(p)
        for p in reversed(pages):
            backward.add(p)
        pd.testing.assert_frame_equal(forward.frame(), backward.frame())
        self.assertEqual(forward.frame().iloc[0]["open"], 100.0)
        self.assertEqual(forward.frame().iloc[0]["close"], 104.0)

    def test_same_timestamp_ties_break_by_trade_id(self):
        self.agg.add(_trades([(2, "10.0", 50.0, 1.0)]))
        self.agg.add(_trades([(1, "10.0", 40.0, 1.0)]))
        bar = self.agg.frame().iloc[0]
        self.assertEqual(bar["open"], 40.0)
        self.assertEqual(bar["close"], 50.0)

    def test_volume_accumulates_across_pages_without_double_counting(self):
        self.agg.add(_trades([(2, "20.0", 100.0, 1.5)]))
        self.agg.add(_trades([(1, "10.0", 100.0, 2.5)]))
        self.assertEqual(self.agg.frame().iloc[0]["volume"], 4.0)

    def test_bars_are_separated_by_interval_and_sorted(self):
        self.agg.add(_trades([(1, "10.0", 100.0, 1.0)]))
        self.agg.add(_parse_trades([{"trade_id": 2, "side": "buy", "size": "1",
                                     "price": "200", "time": "2026-07-06T00:05:00Z"}]))
        f = self.agg.frame()
        self.assertEqual(len(f), 2)
        self.assertTrue(f["timestamp"].is_monotonic_increasing)
        self.assertEqual(int(f["timestamp"].iloc[1] - f["timestamp"].iloc[0]), 300)

    def test_empty_page_is_a_no_op(self):
        self.agg.add(_trades([(1, "10.0", 100.0, 1.0)]))
        before = self.agg.frame()
        self.agg.add(_parse_trades([]))
        pd.testing.assert_frame_equal(self.agg.frame(), before)


class TestCheckpointRoundTrip(unittest.TestCase):
    """A resumed job must produce exactly what an uninterrupted one would."""

    def test_state_survives_save_and_load(self):
        first = MinuteAggregator(60)
        first.add(_trades([(9, "50.0", 105.0, 1.0)]))
        with tempfile.TemporaryDirectory() as tmp:
            ck = Path(tmp) / "ck.json"
            _write_ck(ck, first, cursor=9, pages=1, trades=1, done=False)
            self.assertTrue(ck.exists())
            resumed = MinuteAggregator(60)
            resumed.load(json.loads(ck.read_text())["bars"])

        # The resumed aggregator now receives the older page, as the real job would.
        resumed.add(_trades([(1, "05.0", 100.0, 1.0)]))
        uninterrupted = MinuteAggregator(60)
        uninterrupted.add(_trades([(9, "50.0", 105.0, 1.0)]))
        uninterrupted.add(_trades([(1, "05.0", 100.0, 1.0)]))
        pd.testing.assert_frame_equal(resumed.frame(), uninterrupted.frame())
        self.assertEqual(resumed.frame().iloc[0]["open"], 100.0)

    def test_checkpoint_write_is_atomic(self):
        """No .tmp left behind, so a killed job cannot resume from a partial file."""
        agg = MinuteAggregator(60)
        agg.add(_trades([(1, "10.0", 100.0, 1.0)]))
        with tempfile.TemporaryDirectory() as tmp:
            ck = Path(tmp) / "ck.json"
            _write_ck(ck, agg, cursor=1, pages=1, trades=1, done=True)
            self.assertEqual([p.name for p in Path(tmp).iterdir()], ["ck.json"])
            self.assertTrue(json.loads(ck.read_text())["done"])


if __name__ == "__main__":
    unittest.main()

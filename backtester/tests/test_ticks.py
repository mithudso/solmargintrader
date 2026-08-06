"""Tick fetch and tick->bar aggregation. No network: every test uses fixtures."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from backtester.core import ticks as ticks_mod
from backtester.core.data import validate_bars
from backtester.core.ticks import (
    TRADE_COLUMNS,
    _parse_trades,
    trades_to_bars,
)

# Two minutes of trades, newest first, exactly as the API returns them.
RAW = [
    {"trade_id": 105, "side": "sell", "size": "2.0", "price": "101.0",
     "time": "2026-07-06T00:01:30.500000Z"},
    {"trade_id": 104, "side": "buy", "size": "1.0", "price": "103.0",
     "time": "2026-07-06T00:01:10.000000Z"},
    {"trade_id": 103, "side": "buy", "size": "3.0", "price": "99.0",
     "time": "2026-07-06T00:00:45.250000Z"},
    {"trade_id": 102, "side": "sell", "size": "1.5", "price": "102.0",
     "time": "2026-07-06T00:00:20.000000Z"},
    {"trade_id": 101, "side": "buy", "size": "0.5", "price": "100.0",
     "time": "2026-07-06T00:00:05.000000Z"},
]


class TestParseTrades(unittest.TestCase):
    def test_field_mapping_is_by_name_not_position(self):
        """The mapping hazard: price must be price, size must be size."""
        df = _parse_trades(RAW)
        self.assertEqual(list(df.columns), list(TRADE_COLUMNS))
        first = df.iloc[0]
        self.assertEqual(int(first["trade_id"]), 105)
        self.assertEqual(float(first["price"]), 101.0)
        self.assertEqual(float(first["size"]), 2.0)
        self.assertEqual(first["side"], "sell")

    def test_timestamps_are_epoch_seconds_with_subsecond_precision(self):
        df = _parse_trades(RAW)
        expected = pd.Timestamp("2026-07-06T00:01:30.5Z").timestamp()
        self.assertAlmostEqual(float(df["timestamp"].iloc[0]), expected, places=3)
        # Sub-second detail is the whole point of ticks; it must survive.
        self.assertNotEqual(float(df["timestamp"].iloc[0]) % 1, 0.0)

    def test_empty_page_returns_empty_frame_with_contract_columns(self):
        df = _parse_trades([])
        self.assertTrue(df.empty)
        self.assertEqual(list(df.columns), list(TRADE_COLUMNS))


class TestTradesToBars(unittest.TestCase):
    def setUp(self):
        self.trades = _parse_trades(RAW).sort_values("timestamp").reset_index(drop=True)

    def test_ohlc_comes_from_trade_order_not_price_order(self):
        bars = trades_to_bars(self.trades, "1m")
        self.assertEqual(len(bars), 2)
        first = bars.iloc[0]
        # Bucket 00:00 holds trades 101, 102, 103 in time order.
        self.assertEqual(float(first["open"]), 100.0)   # earliest trade
        self.assertEqual(float(first["close"]), 99.0)   # latest trade
        self.assertEqual(float(first["high"]), 102.0)
        self.assertEqual(float(first["low"]), 99.0)
        self.assertEqual(float(first["volume"]), 5.0)

    def test_bars_are_labelled_by_window_open(self):
        bars = trades_to_bars(self.trades, "1m")
        opens = [
            pd.Timestamp(int(t), unit="s", tz="UTC").isoformat()
            for t in bars["timestamp"]
        ]
        self.assertEqual(
            opens,
            ["2026-07-06T00:00:00+00:00", "2026-07-06T00:01:00+00:00"],
        )

    def test_aggregated_bars_satisfy_the_bar_contract(self):
        bars = trades_to_bars(self.trades, "1m")
        validate_bars(bars, "1m", strict_gaps=True)

    def test_coarser_interval_collapses_to_one_bar(self):
        bars = trades_to_bars(self.trades, "1h")
        self.assertEqual(len(bars), 1)
        self.assertEqual(float(bars["open"].iloc[0]), 100.0)
        self.assertEqual(float(bars["close"].iloc[0]), 101.0)
        self.assertEqual(float(bars["high"].iloc[0]), 103.0)
        self.assertEqual(float(bars["volume"].iloc[0]), 8.0)

    def test_empty_intervals_are_omitted_not_invented(self):
        """A bar with no trades must not be fabricated."""
        gapped = self.trades[self.trades["trade_id"] != 104]
        gapped = gapped[gapped["trade_id"] != 105]
        bars = trades_to_bars(gapped, "1m")
        self.assertEqual(len(bars), 1)

    def test_empty_frame_refuses_rather_than_returning_zero_bars(self):
        with self.assertRaises(ValueError):
            trades_to_bars(self.trades.iloc[0:0], "1m")

    def test_raw_api_order_does_not_invert_open_and_close(self):
        """The API returns newest-first; aggregating that must not flip OHLC."""
        newest_first = _parse_trades(RAW)  # exactly as the API hands it over
        self.assertGreater(
            float(newest_first["timestamp"].iloc[0]),
            float(newest_first["timestamp"].iloc[-1]),
        )
        bars = trades_to_bars(newest_first, "1m")
        expected = trades_to_bars(self.trades, "1m")
        pd.testing.assert_frame_equal(bars, expected)
        self.assertEqual(float(bars["open"].iloc[0]), 100.0)
        self.assertEqual(float(bars["close"].iloc[0]), 99.0)

    def test_same_microsecond_trades_break_ties_by_trade_id(self):
        """Coinbase stamps one order's fills identically; order must be stable."""
        tied = [
            {"trade_id": 202, "side": "buy", "size": "1.0", "price": "50.0",
             "time": "2026-07-06T00:00:10.000000Z"},
            {"trade_id": 201, "side": "buy", "size": "1.0", "price": "40.0",
             "time": "2026-07-06T00:00:10.000000Z"},
        ]
        forward = trades_to_bars(_parse_trades(tied), "1m")
        reversed_input = trades_to_bars(_parse_trades(list(reversed(tied))), "1m")
        pd.testing.assert_frame_equal(forward, reversed_input)
        # Lower trade_id happened first, so it is the open regardless of input order.
        self.assertEqual(float(forward["open"].iloc[0]), 40.0)
        self.assertEqual(float(forward["close"].iloc[0]), 50.0)

    def test_missing_required_column_refuses(self):
        with self.assertRaises(ValueError):
            trades_to_bars(self.trades.drop(columns=["price"]), "1m")


class TestTruncationIsNotWritableBySilence(unittest.TestCase):
    """`to_csv` drops `attrs`, so truncation must be caught before the write."""

    def _truncated_frame(self):
        df = _parse_trades(RAW).sort_values("timestamp").reset_index(drop=True)
        df.attrs["truncated"] = True
        return df

    def _run(self, extra_args):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trades.csv"
            with mock.patch.object(
                ticks_mod, "fetch_trades", return_value=self._truncated_frame()
            ):
                code = ticks_mod.main(
                    [
                        "--asset", "SOL",
                        "--start", "2026-07-06T00:00:00Z",
                        "--end", "2026-08-06T00:00:00Z",
                        "--out", str(out),
                        *extra_args,
                    ]
                )
            return code, out.exists()

    def test_refuses_to_write_a_file_that_understates_its_own_window(self):
        code, written = self._run([])
        self.assertEqual(code, 1)
        self.assertFalse(written, "a truncated window must not reach disk unflagged")

    def test_allow_truncated_is_an_explicit_disclosure(self):
        code, written = self._run(["--allow-truncated"])
        self.assertEqual(code, 0)
        self.assertTrue(written)

    def test_complete_window_writes_without_the_flag(self):
        complete = _parse_trades(RAW).sort_values("timestamp").reset_index(drop=True)
        complete.attrs["truncated"] = False
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "trades.csv"
            with mock.patch.object(ticks_mod, "fetch_trades", return_value=complete):
                code = ticks_mod.main(
                    ["--start", "2026-07-06T00:00:00Z", "--end",
                     "2026-07-06T01:00:00Z", "--out", str(out)]
                )
            self.assertEqual(code, 0)
            self.assertTrue(out.exists())


if __name__ == "__main__":
    unittest.main()

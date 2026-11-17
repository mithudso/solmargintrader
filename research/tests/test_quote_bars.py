"""Closed and developing bars reconstructed from recorded public quotes."""

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from research.quote_bars import QuoteBars


class QuoteBarTests(unittest.TestCase):
    def test_bar_rotation_and_gap_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dual-quotes-20261116T13-abcd.jsonl.gz"
            rows = [
                {
                    "venue": "jupiter",
                    "asset": "BTC",
                    "exchange_at": t,
                    "price": 100 + (t - 600) / 1000,
                }
                for t in range(600, 1801)
            ]
            with gzip.open(path, "wt") as stream:
                for row in rows:
                    stream.write(json.dumps(row) + "\n")
            bars = QuoteBars(tmp)
            result = bars.read(1800, budget=1000000)["BTC"]
            self.assertEqual(result["previous"]["start"], 1200)
            self.assertEqual(result["previous"]["open"], 100.6)
            self.assertEqual(result["current"]["start"], 1800)
            self.assertAlmostEqual(result["current"]["baseline_range"], 0.599)
            bars.bars["BTC"][1200]["gap"] = 6
            self.assertIsNone(bars.read(1800)["BTC"]["previous"])

    def test_concatenated_gzip_members_follow_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dual-quotes-20261116T13-abcd.jsonl.gz"
            first = {
                "venue": "jupiter",
                "asset": "BTC",
                "exchange_at": 600,
                "price": 100,
            }
            second = {**first, "exchange_at": 601, "price": 101}
            path.write_bytes(gzip.compress((json.dumps(first) + "\n").encode()))
            bars = QuoteBars(tmp)
            self.assertEqual(bars.read(600)["BTC"]["current"]["close"], 100)
            with path.open("ab") as stream:
                stream.write(gzip.compress((json.dumps(second) + "\n").encode()))
            self.assertEqual(bars.read(601)["BTC"]["current"]["close"], 101)

    def test_future_or_bad_prices_do_not_form_bar(self):
        bars = QuoteBars("/nonexistent")
        bars._add(
            {
                "venue": "jupiter",
                "asset": "BTC",
                "exchange_at": 601,
                "price": float("nan"),
            },
            600,
        )
        bars._add(
            {"venue": "jupiter", "asset": "BTC", "exchange_at": 700, "price": 10}, 600
        )
        self.assertIsNone(bars._view("BTC", 600)["current"])

import unittest

import numpy as np

from research.exit50_orderflow import NS, book_feature


def book():
    a = np.zeros((2, 40, 2))
    a[0, :3] = [[99.99, 2], [99.95, 1], [99.89, 1]]
    a[1, :3] = [[100.01, 1], [100.05, 1], [100.11, 1]]
    return a


class OrderFlowTests(unittest.TestCase):
    def test_visible_notional_not_order_count_and_strict_causal_lookup(self):
        b = book()
        other = book()
        other[0, 0, 1] = 30
        value = book_feature([10 * NS, 12 * NS], [b, other], [], 11 * NS)
        self.assertEqual(value["status"], "ready")
        self.assertEqual(value["quote_ns"], 10 * NS)
        self.assertAlmostEqual(value["bid_notional"], 99.99 * 2 + 99.95)
        self.assertAlmostEqual(value["ask_notional"], 100.01 + 100.05)
        self.assertGreater(value["imbalance"], 0)

    def test_gap_and_freshness_guards(self):
        self.assertEqual(
            book_feature([10 * NS], [book()], [], 9 * NS)["status"], "no_prior_book"
        )
        self.assertEqual(
            book_feature([10 * NS], [book()], [], 12 * NS)["status"], "ready"
        )
        self.assertEqual(
            book_feature([10 * NS], [book()], [], 12 * NS + 1)["status"], "stale"
        )
        self.assertEqual(
            book_feature(
                [10 * NS], [book()], [(11 * NS, 11 * NS, "connection_gap")], 11 * NS
            )["status"],
            "connection_or_receipt_gap",
        )
        self.assertEqual(
            book_feature(
                [10 * NS], [book()], [(10 * NS, 11 * NS, "receipt_gap")], 11 * NS
            )["status"],
            "connection_or_receipt_gap",
        )
        self.assertEqual(
            book_feature(
                [12 * NS], [book()], [(11 * NS, 11 * NS, "connection_open")], 12 * NS
            )["status"],
            "ready",
        )

    def test_truncated_and_crossed_books_are_not_claimed_complete(self):
        b = book()
        b[:, 2] = 0
        self.assertEqual(
            book_feature([NS], [b], [], NS)["status"], "truncated_visible_band"
        )
        b = book()
        b[0, 0, 0] = 101
        self.assertEqual(book_feature([NS], [b], [], NS)["status"], "invalid_book")

    def test_bad_order_of_snapshots_fails(self):
        with self.assertRaisesRegex(ValueError, "invalid_quote_sequence"):
            book_feature([2 * NS, NS], [book(), book()], [], 2 * NS)


class TakerQuoteTests(unittest.TestCase):
    def test_three_closed_minutes_missing_and_zero_reset(self):
        from research.exit50_orderflow import taker_quote_imbalance

        def row(i, total, buy):
            return [
                i * 60000,
                "1",
                "1",
                "1",
                "1",
                "1",
                i * 60000 + 59999,
                str(total),
                1,
                "1",
                str(buy),
                "0",
            ]

        result = taker_quote_imbalance(
            [row(0, 10, 8), row(1, 10, 5), row(2, 10, 2), row(3, 0, 0), row(5, 10, 5)]
        )
        self.assertEqual(result[0]["available_at_ms"], 60000)
        self.assertAlmostEqual(result[2]["sma3"], 0)
        self.assertIsNone(result[3]["imbalance"])
        self.assertIsNone(result[4]["sma3"])
        with self.assertRaisesRegex(ValueError, "invalid_kline_quote_volume"):
            taker_quote_imbalance([row(0, 10, 11)])

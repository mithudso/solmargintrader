"""Invalid market evidence cannot become a simulated execution or poison time."""

import json
import unittest

from backtester.core.trianglesim import (Triangle, TriangleConfig, TriangleReplay,
                                         cycle_edges_bps, parse_snapshot_line, run_triangle_backtest)

TRIANGLE = Triangle("ETH", "BTC")


def _book():
    return {"ETH-USD": (3000., 3000., 1., 1., 0.),
            "BTC-USD": (60000., 60000., 1., 1., 0.),
            "ETH-BTC": (.0505, .0505, 1., 1., 0.)}


class TriangleInputTests(unittest.TestCase):
    def test_invalid_displayed_size_cannot_execute_with_negative_or_guessed_notional(self):
        for invalid in (-1., 0., float("nan"), float("inf")):
            book = _book()
            book["ETH-USD"] = (3000., 3000., 1., invalid, 0.)
            with self.subTest(size=invalid):
                result = run_triangle_backtest(TriangleConfig(latency_s=0), [(0., book)], [TRIANGLE])
                self.assertEqual(result.executed, 0)

    def test_future_or_nonfinite_quote_time_is_unusable(self):
        for invalid in (1., float("inf"), float("nan")):
            book = _book()
            book["ETH-USD"] = (3000., 3000., 1., 1., invalid)
            with self.subTest(quote_time=invalid):
                self.assertIsNone(cycle_edges_bps(TRIANGLE, book, 0, now=0., max_age=5.))

    def test_nonfinite_feed_time_refuses_before_state_changes(self):
        for invalid in (float("nan"), float("inf"), True):
            replay = TriangleReplay(TriangleConfig(), [TRIANGLE])
            with self.subTest(time=invalid):
                with self.assertRaises(ValueError):
                    replay.feed(invalid, _book())
                self.assertEqual(replay.result().snapshots, 0)

    def test_malformed_snapshot_values_are_discarded_without_parser_escape(self):
        for value in ({}, {"bid": 1}, [1, 2, 1, 10 ** 1000, 1, 0]):
            with self.subTest(quote=value):
                parsed = parse_snapshot_line(json.dumps({"t": 0, "q": {"ETH-USD": value}}))
                self.assertEqual(parsed, (0., {}))
        self.assertIsNone(parse_snapshot_line(json.dumps({"t": 10 ** 1000, "q": {}})))

    def test_nonfinite_derived_cycle_edges_cannot_be_reported_as_an_opportunity(self):
        book = {"ETH-USD": (1e-308, 1e-308, None, None, 0.),
                "BTC-USD": (1e308, 1e308, None, None, 0.),
                "ETH-BTC": (1., 1., None, None, 0.)}
        self.assertIsNone(cycle_edges_bps(TRIANGLE, book, 0, now=0., max_age=5.))


if __name__ == "__main__":
    unittest.main()

"""Shape teaching must preserve provenance, gaps and conditional meaning."""

from __future__ import annotations

import copy
import unittest

from research.shape_study import SHAPES
from research.tests.test_zec_tui_model import candles
from research.zec_shape_view import GUIDES, price_trace, shape_guide, shape_summary
from research.zec_tui_model import market_details


class ShapeTeaching(unittest.TestCase):
    def test_every_detector_label_has_a_distinct_explanation(self):
        self.assertEqual(set(GUIDES), set(SHAPES))
        details = market_details(candles(), "1m", 6000)
        for name in SHAPES:
            with self.subTest(shape=name):
                details["shape"]["shape"] = name
                text = shape_guide(details, "1m")
                self.assertIn(GUIDES[name][0], text)
                self.assertIn(GUIDES[name][2], text)
                self.assertIn(GUIDES[name][3], text)
                self.assertIn(GUIDES[name][4], text)
                self.assertIn("not a fitted or predicted path", text)
        self.assertIn("either direction", GUIDES["compression"][3])

    def test_actual_trace_is_exactly_the_observed_48_closes_not_chart_crop(self):
        rows = candles()
        short = market_details(rows, "1m", 6000, lookback=48)
        long = market_details(rows, "1m", 6000, lookback=300)
        expected = [rows[i * 60]["close"] for i in range(52, 100)]
        self.assertEqual(short["shape"]["trace"], expected)
        self.assertEqual(short["shape"], long["shape"])
        self.assertEqual(short["shape"]["trace_start"], 3120)
        self.assertEqual(short["shape"]["trace_end"], 5940)
        future = candles(110)
        future[6000]["close"] = 999999
        self.assertEqual(short, market_details(future, "1m", 6000, lookback=48))

    def test_gap_cannot_be_hidden_by_a_teaching_trace(self):
        rows = candles()
        del rows[95 * 60]
        details = market_details(rows, "1m", 6000)
        self.assertEqual(details["shape"]["shape"], "unknown")
        self.assertNotIn("trace", details["shape"])
        self.assertIn("Actual trace unavailable", shape_guide(details, "1m"))

    def test_guide_does_not_mutate_calls_and_relabels_retained_data(self):
        details = market_details(candles(), "1m", 6000)
        baseline = copy.deepcopy(details)
        shape_guide(details, "1m")
        self.assertEqual(details, baseline)
        details["stale"] = True
        self.assertIn("RETAINED / STALE", shape_summary(details))
        self.assertIn("RETAINED / STALE DATA", shape_guide(details, "1m"))
        self.assertIn("Shape unavailable", shape_guide(None, "1m"))

    def test_live_range_marker_and_completed_close_provenance_stay_distinct(self):
        details = market_details(candles(), "1m", 6000)
        details["shape"]["live_range_position"] = 1.2
        text = shape_guide(details, "1m")
        self.assertIn("Live quote in observed 48-bar range", text)
        self.assertIn("120%", text)
        self.assertIn("LAST COMPLETED CLOSE", text)
        self.assertIn("1970-01-01T00:52:00Z", text)

    def test_curve_fit_is_explained_as_past_fit_not_directional_confidence(self):
        details = market_details(candles(), "1m", 6000)
        details["shape"].update(shape="bowl", fitted_turn_bars_ago=12, fit_r2=0.9)
        text = shape_guide(details, "1m")
        self.assertIn("Fitted low: 12.0 bars", text)
        self.assertIn("historical fit quality, not forecast confidence", text)
        details["shape"]["shape"] = "range"
        self.assertNotIn("Fitted low:", shape_guide(details, "1m"))

    def test_trace_dot_marks_the_last_actual_close_with_no_future_extension(self):
        text = price_trace(list(range(48)), width=32)
        rows = text.splitlines()
        self.assertEqual(rows[0].split("│")[1][-1], "●")
        self.assertEqual(text.count("●"), 1)
        self.assertIn("47.000", rows[0])
        self.assertIn("0.000", rows[6])
        self.assertIn("Actual trace unavailable", price_trace([1, 2]))
        self.assertIn("Actual trace unavailable", price_trace([float("nan")] * 48))

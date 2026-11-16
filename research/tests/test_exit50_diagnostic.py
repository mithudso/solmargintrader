import unittest
from unittest.mock import patch

from research.exit50_diagnostic import diagnostic_candidates


class BookAlignmentTests(unittest.TestCase):
    def test_only_prior_fresh_complete_book_qualifies(self):
        rows = [
            {
                "decision_ns": 540_000_000_000,
                "status": "ready",
                "band_covered_by_visible_levels": True,
                "quote_ns": 539_000_000_000,
                "imbalance": -0.1,
            },
            {
                "decision_ns": 600_000_000_000,
                "status": "ready",
                "band_covered_by_visible_levels": True,
                "quote_ns": 600_000_000_001,
                "imbalance": -0.9,
            },
        ]
        signal = {"eligible": True}
        with patch("research.exit50_diagnostic.signal_at", return_value=signal):
            result = diagnostic_candidates(
                {},
                {"near_end": {}, "confirmed_uu": {}},
                {"rows": rows},
                540_000_000_000,
                600_000_000_000,
            )
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["book_status"], "qualified")
        self.assertTrue(result[0]["book_negative"])
        self.assertEqual(result[1]["book_status"], "invalid_book")
        self.assertIsNone(result[1]["book_negative"])

    def test_stale_truncated_and_zero_never_become_negative(self):
        rows = [
            {
                "decision_ns": 540_000_000_000,
                "status": "truncated_visible_band",
                "band_covered_by_visible_levels": False,
                "quote_ns": 539_000_000_000,
                "imbalance": -0.1,
            },
            {
                "decision_ns": 600_000_000_000,
                "status": "ready",
                "band_covered_by_visible_levels": True,
                "quote_ns": 597_000_000_000,
                "imbalance": 0,
            },
        ]
        with patch(
            "research.exit50_diagnostic.signal_at", return_value={"eligible": True}
        ):
            result = diagnostic_candidates(
                {},
                {"near_end": {}, "confirmed_uu": {}},
                {"rows": rows},
                540_000_000_000,
                600_000_000_000,
            )
        self.assertTrue(all(x["book_negative"] is None for x in result))


if __name__ == "__main__":
    unittest.main()

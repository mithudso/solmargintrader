import unittest
from unittest.mock import patch

from research.exit50_diagnostic import (
    diagnostic_candidates,
    evaluate_diagnostic,
    full_grid_position,
)


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

    def test_incomplete_proof_blocks_diagnostic_evaluation(self):
        plan = {
            "schema": "exit50-zec-l2-lazy-plan/v1",
            "candidate_count": 1,
            "all_needed_count": 1,
            "selected_slots": [600],
            "cases": [],
        }
        with self.assertRaisesRegex(ValueError, "diagnostic_source_proof_incomplete"):
            evaluate_diagnostic({}, [{}], "/tmp", "/tmp", plan)

    def test_diagnostic_requires_full_grid_only_through_terminal(self):
        entry = 100_000_000_000_000
        c = {"decision_s": 0, "cap_s": 20, "entry_price": entry}
        points = [
            (i * 200_000, entry if i < 5 else entry + 98_000_000_000) for i in range(6)
        ]
        terminal = full_grid_position(c, {}, lambda _: points, "fixed", 10)
        self.assertEqual(terminal["status"], "liquidated")
        self.assertEqual(terminal["exit_us"], 1_000_000)
        missing = points[:2] + points[3:]
        result = full_grid_position(c, {}, lambda _: missing, "fixed", 10)
        self.assertEqual(result["status"], "unscored")
        self.assertEqual(result["at_us"], 400_000)

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

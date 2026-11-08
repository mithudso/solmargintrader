"""Failure checks for the independent source-review gate and literal evidence."""

from __future__ import annotations

import copy
import unittest

from scripts.render_tradingview_script_cards import (
    INCOMPLETE_DIR,
    REVIEW_FIELDS,
    card_path,
    check_readiness,
    check_review,
    identity,
    literal,
    read_coverage,
)


class SourceReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = {
            "publication_id": "demo",
            "in_scope": True,
            "purpose": "Use the source's ten-bar filter to describe price direction.",
            "readiness": {
                "status": "usable-specification",
                "reason": "A ten-bar arithmetic mean is defined.",
                "gaps": [],
            },
        }
        self.source = {
            "source_sha256": "a" * 64,
            "raw_description_sha256": "b" * 64,
            "description_characters": 100,
        }
        self.audit = {
            "publication_id": "demo",
            "profile_sha256": identity(self.profile),
            "source_sha256": "a" * 64,
            "raw_description_sha256": "b" * 64,
            "verdict": "pass",
            "reviewed_fields": sorted(REVIEW_FIELDS),
            "source_read_ranges": [[0, 60], [60, 100]],
            "summary": "Reviewed the complete description and its interpretation.",
            "findings": [],
        }

    def test_changed_parameter_invalidates_prior_semantic_acceptance(self) -> None:
        check_review(self.profile, self.source, self.audit)
        changed = {
            **self.profile,
            "purpose": self.profile["purpose"].replace("ten", "twenty"),
        }
        with self.assertRaisesRegex(ValueError, "stale"):
            check_review(changed, self.source, self.audit)

    def test_revised_source_and_unread_tail_refuse_acceptance(self) -> None:
        for field, value in (
            ("source_sha256", "c" * 64),
            ("raw_description_sha256", "d" * 64),
            ("source_read_ranges", [[0, 99]]),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                check_review(self.profile, self.source, {**self.audit, field: value})

    def test_pass_label_does_not_override_unresolved_medium_finding(self) -> None:
        audit = copy.deepcopy(self.audit)
        audit["findings"] = [
            {
                "severity": "medium",
                "status": "open",
                "issue": "Ten is an example, not a default.",
            }
        ]
        with self.assertRaisesRegex(ValueError, "unresolved"):
            check_review(self.profile, self.source, audit)
        audit["findings"][0]["status"] = "resolved"
        check_review(self.profile, self.source, audit)

    def test_exclusion_requires_scope_reason_review(self) -> None:
        profile = {
            "publication_id": "demo",
            "in_scope": False,
            "classification": "non-trading",
            "exclusion_reason": "Pixel artwork.",
        }
        audit = {**self.audit, "profile_sha256": identity(profile)}
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            check_review(profile, self.source, audit)
        audit["reviewed_fields"] = [
            "in_scope",
            "classification",
            "exclusion_reason",
            "evidence",
        ]
        check_review(profile, self.source, audit)

    def test_full_read_coverage_refuses_gap_or_reversed_range(self) -> None:
        self.assertTrue(read_coverage([[0, 70], [50, 100]], 100))
        self.assertFalse(read_coverage([[0, 50], [51, 100]], 100))
        self.assertFalse(read_coverage([[0, 100], [70, 50]], 100))

    def test_source_fences_and_markup_stay_inside_literal_evidence(self) -> None:
        quote = "```\n<script>not executable evidence</script>\n````"
        text = literal(quote)
        self.assertEqual(text, "`````text\n" + quote + "\n`````")

    def test_quote_display_cleans_line_endings_without_mutating_raw_evidence(
        self,
    ) -> None:
        quote = "first  \r\n    indented\t"
        self.assertEqual(literal(quote), "```text\nfirst\n    indented\n```")
        self.assertEqual(quote, "first  \r\n    indented\t")

    def test_incomplete_card_is_physically_under_requested_directory(self) -> None:
        source = {"publication_id": "demo", "name": "A source indicator"}
        # A disclosed calculation alone is not a qualified standalone coin test.
        self.assertEqual(card_path(source, self.profile).parent, INCOMPLETE_DIR)
        profile = {
            **self.profile,
            "readiness": {
                "status": "incomplete",
                "reason": "The adaptive weight is hidden.",
                "gaps": ["Adaptive weight equation."],
            },
        }
        self.assertEqual(card_path(source, profile).parent, INCOMPLETE_DIR)
        self.assertIn(
            "backtester/strategy_cards/incomplete/", str(card_path(source, profile))
        )

    def test_usable_status_cannot_coexist_with_blocking_computation_gap(self) -> None:
        profile = copy.deepcopy(self.profile)
        profile["readiness"]["gaps"] = ["Core filter update is not defined."]
        with self.assertRaisesRegex(ValueError, "contradictory"):
            check_readiness(profile)


if __name__ == "__main__":
    unittest.main()

"""Failure checks for the independent source-review gate and literal evidence."""

from __future__ import annotations

import copy
import unittest

from scripts.render_tradingview_script_cards import (
    REVIEW_FIELDS,
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


if __name__ == "__main__":
    unittest.main()

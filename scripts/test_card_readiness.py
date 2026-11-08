"""Prevent loss, duplicate ownership and stale reviews during card relocation."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from backtester.core.strategy_cards import load_all
from scripts.check_tradingview_cards import load_catalog, validate_readiness


class CardReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.directory = self.repo / "backtester/strategy_cards"
        self.directory.mkdir(parents=True)
        (self.directory / "incomplete").mkdir()
        source = Path(__file__).resolve().parents[1] / "backtester/strategy_cards"
        # This pre-existing card stays active in the real catalog.
        template = (source / "macd.md").read_text()
        self.review = {"cards": []}
        for key, disposition in (
            ("active_example", "keep"),
            ("research_example", "incomplete"),
        ):
            folder = (
                self.directory
                if disposition == "keep"
                else self.directory / "incomplete"
            )
            path = folder / f"{key}.md"
            # Keep this fixture a specification, with no runtime ownership claim.
            frontmatter, body = template.split("---\n", 2)[1:]
            lines = []
            for line in frontmatter.splitlines():
                if line.startswith("id:"):
                    line = f"id: {key}"
                elif line.startswith("status:"):
                    line = "status: spec-only"
                elif line.startswith("success_basis:"):
                    line = "success_basis: a-priori"
                elif line.startswith(("runner:", "registry_key:", "evaluation:")):
                    line = line.split(":", 1)[0] + ": null"
                lines.append(line)
            path.write_text("---\n" + "\n".join(lines) + "\n---\n" + body)
            quote = next(line for line in body.splitlines() if len(line.strip()) >= 20)
            self.review["cards"].append(
                {
                    "id": key,
                    "disposition": disposition,
                    "path": path.relative_to(self.repo).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "reason": "Fixture decision for relocation integrity.",
                    "evidence": [quote],
                    "gaps": ["Fixture research gap."],
                }
            )
        self.created = {row["id"] for row in self.review["cards"]}

    def check(self):
        active, incomplete = load_catalog(self.repo)
        validate_readiness(self.review, self.created, active, incomplete, self.repo)

    def test_runtime_loader_excludes_incomplete_but_audit_preserves_it(self):
        self.assertEqual(set(load_all(self.directory)), {"active_example"})
        active, incomplete = load_catalog(self.repo)
        self.assertEqual(set(active) | set(incomplete), self.created)
        self.check()

    def test_duplicate_between_directories_is_refused(self):
        path = self.directory / "active_example.md"
        (self.directory / "incomplete" / path.name).write_bytes(path.read_bytes())
        with self.assertRaisesRegex(ValueError, "both active and incomplete"):
            self.check()

    def test_guide_and_research_locations_keep_evidence_and_stay_out_of_runtime(self):
        for folder, disposition in (("guides", "guide"), ("strategy_research", "research")):
            with self.subTest(disposition=disposition):
                old = self.directory / "incomplete" / "research_example.md"
                target = self.repo / "backtester" / folder / old.name
                target.parent.mkdir(exist_ok=True)
                old.rename(target)
                row = self.review["cards"][1]
                row["disposition"] = disposition
                row["path"] = target.relative_to(self.repo).as_posix()
                self.check()
                self.assertNotIn("research_example", load_all(self.directory))
                target.rename(old)
                row["disposition"] = "incomplete"
                row["path"] = old.relative_to(self.repo).as_posix()

    def test_missing_or_duplicate_review_is_refused(self):
        self.review["cards"] = [self.review["cards"][0]] * 2
        with self.assertRaisesRegex(ValueError, "exactly once"):
            self.check()

    def test_wrong_location_is_refused(self):
        self.review["cards"][1]["disposition"] = "keep"
        with self.assertRaisesRegex(ValueError, "disagrees with card location"):
            self.check()

    def test_edited_card_requires_a_new_review(self):
        path = self.directory / "active_example.md"
        path.write_text(path.read_text() + "\nChanged formula.\n")
        with self.assertRaisesRegex(ValueError, "review is stale"):
            self.check()

    def test_unbound_evidence_is_refused(self):
        self.review["cards"][0]["evidence"] = [
            "This quotation never occurred in the card."
        ]
        with self.assertRaisesRegex(ValueError, "not bound to card text"):
            self.check()

    def test_unreviewed_research_card_is_refused(self):
        self.created.remove("research_example")
        self.review["cards"].pop()
        with self.assertRaisesRegex(ValueError, "outside the reviewed extraction"):
            self.check()


if __name__ == "__main__":
    unittest.main()

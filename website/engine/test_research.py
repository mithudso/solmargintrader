from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from website.scripts.export_research import export, public_body


class ResearchExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        (self.repo / "research").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def add(self, source, body):
        path = self.repo / source
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        subprocess.run(["git", "add", source], cwd=self.repo, check=True)

    def test_full_article_source_and_published_hashes_with_private_path_transform(self):
        text = "# A measured result\n\nA losing strategy is a valid research result.\n\nLocal receipt: /Users/owner/private/evidence.json\n\nCosts remain material.\n\nLimitation: historical evidence does not predict returns.\n"
        self.add("research/RESULT.md", text)
        files = export(self.repo)
        catalog = json.loads(files["catalog.json"])
        article = catalog["articles"][0]
        self.assertNotIn("body", article)
        shard = json.loads(files[Path(article["bodyPath"]).name])
        body = shard["articles"][article["bodyKey"]]
        self.assertIn("losing strategy", body["body"])
        self.assertEqual(body["body"], "# A measured result\n\nA losing strategy is a valid research result.\n\nLocal receipt: [local artifact not published]\n\nCosts remain material.\n\nLimitation: historical evidence does not predict returns.\n")
        self.assertNotIn("/Users/", body["body"])
        self.assertEqual(body["sourceSha256"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(body["publishedSha256"], hashlib.sha256(body["body"].encode()).hexdigest())
        self.assertEqual(files, export(self.repo))

    def test_untracked_and_prompt_files_never_publish(self):
        self.add("research/RESULT.md", "# Result\n\nA study.")
        self.add("research/PRIVATE-PROMPTS.md", "# Internal instructions")
        (self.repo / "research/local-untracked.md").write_text("# Private local draft")
        catalog = json.loads(export(self.repo)["catalog.json"])
        self.assertEqual([a["source"] for a in catalog["articles"]], ["research/RESULT.md"])

    def test_tracked_symlinks_cannot_publish_files_outside_research_scope(self):
        private = self.repo / "private-note.md"
        private.write_text("# Private note\n\nDo not publish this fixture.")
        alias = self.repo / "research" / "alias.md"
        alias.symlink_to(private)
        subprocess.run(["git", "add", "research/alias.md"], cwd=self.repo, check=True)
        with self.assertRaisesRegex(ValueError, "symlink refused"):
            export(self.repo)

    def test_symlink_parent_cannot_redirect_a_tracked_research_file(self):
        self.add("research/study/result.md", "# Public result")
        public = self.repo / "research" / "study"
        (public / "result.md").unlink()
        public.rmdir()
        private = self.repo / "private"
        private.mkdir()
        (private / "result.md").write_text("# Private fixture")
        public.symlink_to(private, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink refused"):
            export(self.repo)

    def test_incomplete_cards_cannot_be_presented_as_runnable(self):
        self.add("backtester/strategy_cards/incomplete/sample.md", "# Experimental card\n\nNot implemented.")
        article = json.loads(export(self.repo)["catalog.json"])["articles"][0]
        self.assertEqual(article["category"], "Incomplete profiles")
        self.assertIn("not coin-test ready", article["status"])

    def test_secrets_abort_publication(self):
        self.add("research/leak.md", "# Unsafe\n\n-----BEGIN PRIVATE KEY-----")
        with self.assertRaisesRegex(ValueError, "credential-like content refused"):
            export(self.repo)

    def test_private_shell_home_path_redacted(self):
        self.assertNotIn("~/.ssh", public_body("Key storage ~/.ssh/wallet.private is private."))

    def test_tracked_symlink_and_symlinked_ancestor_refuse_before_read(self):
        outside = self.repo / "outside"
        outside.mkdir()
        canary = outside / "RESULT.md"
        canary.write_text("# Unpublished canary")
        link = self.repo / "research/RESULT.md"
        link.symlink_to(canary)
        subprocess.run(["git", "add", "research/RESULT.md"], cwd=self.repo, check=True)
        with self.assertRaisesRegex(ValueError, "unsafe publication source"):
            export(self.repo)
        link.unlink()
        link.parent.rmdir()
        link.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "unsafe publication source"):
            export(self.repo)


if __name__ == "__main__":
    unittest.main()

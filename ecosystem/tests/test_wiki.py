"""Real temporary Git snapshots exercise provenance and the inert read boundary."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from ecosystem import wiki
from scripts.build_ecosystem_wiki import compile_snapshot, main


class WikiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        temporary = Path(self.temp.name)
        template = temporary / "empty-git-template"
        template.mkdir()
        self.git_env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.git_env.update({
            "HOME": str(temporary / "home"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TEMPLATE_DIR": str(template),
        })
        self.enterContext(patch.dict(os.environ, self.git_env, clear=True))
        self.repo = temporary / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "--template", str(template))
        sources = {
            "README.md": "# Workspace\nArchitecture map.\n",
            "oracle/README.md": "# Oracle guide\nFresh source timestamps.\n<script>untrusted()</script>\n[Do not execute](javascript:alert(1))\n",
            "botmanager/README.md": "# Manager guide\nRuntime owner and recorded profit.\n",
            "backtester/strategy_cards/rsi.md": "# RSI card\nFees and slippage are part of net return.\n",
            "backtester/strategy_cards/incomplete/reference.md": "# Unfinished idea\nNot a runnable strategy.\n",
            "docs/ARCHITECTURE.md": "# Architecture\nComponent owners stay separate.\n",
            "docs/unrelated.md": "# Unrelated\nExcluded outside the allowlist.\n",
        }
        for name, body in sources.items():
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body)
        self.git("add", ".")
        self.commit()
        self.initial_commit = self.git("rev-parse", "HEAD").strip()
        (self.repo / "oracle/private-note.md").write_text("Untracked private canary.")
        self.output = self.repo / "ecosystem/wiki_content"
        self.build()
        self.enterContext(patch.object(wiki, "SNAPSHOT_DIR", self.output))
        wiki._load_cached.cache_clear()
        self.addCleanup(wiki._load_cached.cache_clear)

    def git(self, *args):
        return subprocess.run(
            ["git", *args],
            cwd=self.repo,
            env=self.git_env,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout

    def commit(self):
        self.git(
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "user.name=Wiki Test",
            "-c",
            "user.email=wiki@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )

    def build(self, **kwargs):
        manifest, bundle = compile_snapshot(self.repo, self.output, **kwargs)
        self.output.mkdir(parents=True, exist_ok=True)
        (self.output / "pages.json").write_bytes(bundle)
        (self.output / "manifest.json").write_bytes(manifest)
        return manifest, bundle

    def rewrite_manifest(self, mutate):
        path = self.output / "manifest.json"
        value = json.loads(path.read_text())
        mutate(value)
        value.pop("snapshot_sha256")
        value["snapshot_sha256"] = hashlib.sha256(wiki.canonical(value)).hexdigest()
        path.write_bytes(wiki.canonical(value))

    def test_only_tracked_allowlisted_documents_are_compiled(self):
        result = wiki.catalog(limit=5000)
        self.assertEqual(result["status"], "available")
        paths = {row["source_path"] for row in result["pages"]}
        self.assertEqual(len(paths), 6)
        self.assertNotIn("oracle/private-note.md", paths)
        self.assertNotIn("docs/unrelated.md", paths)
        self.assertNotIn("private canary", json.dumps(result))

    def test_page_preserves_exact_text_hash_and_commit_provenance(self):
        source = "oracle/README.md"
        result = wiki.page(wiki.page_id(source))
        record = result["page"]
        self.assertEqual(result["status"], "available")
        self.assertEqual(record["body"], (self.repo / source).read_text())
        self.assertEqual(
            record["content_sha256"],
            hashlib.sha256(record["body"].encode()).hexdigest(),
        )
        self.assertEqual(record["source_commit"], self.initial_commit)
        self.assertEqual(record["source_state"], "committed")
        self.assertIn(self.initial_commit, record["source_url"])
        self.assertEqual(record["source_location"], f"{wiki.CANONICAL_REPO}/{source}")
        self.assertFalse(record["is_execution_evidence"])

    def test_full_text_search_and_pagination_cover_documents_beyond_title(self):
        result = wiki.catalog("FEES slippage", limit=1)
        self.assertEqual(result["total"], 1)
        self.assertEqual(
            result["pages"][0]["source_path"], "backtester/strategy_cards/rsi.md"
        )
        first = wiki.catalog(limit=2)
        second = wiki.catalog(limit=2, offset=first["next_offset"])
        self.assertEqual(first["total"], 6)
        self.assertTrue(first["truncated"])
        self.assertFalse(
            {row["id"] for row in first["pages"]}
            & {row["id"] for row in second["pages"]}
        )
        self.assertEqual(wiki.catalog("no such phrase")["pages"], [])

    def test_incomplete_cards_and_plans_never_claim_execution_evidence(self):
        record = wiki.page(
            wiki.page_id("backtester/strategy_cards/incomplete/reference.md")
        )["page"]
        self.assertEqual(record["kind"], "incomplete_reference")
        self.assertFalse(record["is_execution_evidence"])

    def test_adversarial_markdown_is_returned_as_inert_content(self):
        record = wiki.page(wiki.page_id("oracle/README.md"))["page"]
        self.assertEqual(record["content_format"], "text/markdown")
        self.assertIn("<script>untrusted()</script>", record["body"])
        self.assertIn("javascript:alert(1)", record["body"])
        self.assertEqual(wiki.catalog("untrusted")["total"], 1)

    def test_invalid_queries_and_path_ids_are_rejected(self):
        for query, limit, offset in (
            (None, 1, 0),
            ("x" * 257, 1, 0),
            ("\0", 1, 0),
            ("", True, 0),
            ("", 0, 0),
            ("", 5001, 0),
            ("", 1, -1),
        ):
            with (
                self.subTest(query=query, limit=limit, offset=offset),
                self.assertRaises(ValueError),
            ):
                wiki.catalog(query, limit, offset)
        for identity in (
            "../../state.json",
            "/etc/passwd",
            "doc-" + "0" * 24 + "/..",
            None,
        ):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                wiki.page(identity)
        self.assertEqual(wiki.page("doc-" + "0" * 24)["reason"], "wiki_page_not_found")

    def test_changed_bundle_and_forged_metadata_fail_closed(self):
        path = self.output / "pages.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.assertEqual(wiki.catalog()["status"], "unavailable")
        self.build()
        self.rewrite_manifest(
            lambda value: value["pages"][0].update(source_path="../../private.md")
        )
        self.assertEqual(wiki.page(wiki.page_id("README.md"))["status"], "unavailable")
        self.build(refresh_provenance=True)
        self.rewrite_manifest(
            lambda value: value["pages"][0].update(private_key="do not expose")
        )
        result = wiki.catalog()
        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("do not expose", json.dumps(result))

    def test_source_symlinks_are_not_copied_and_runtime_symlinks_are_refused(self):
        source = self.repo / "oracle/README.md"
        source.unlink()
        source.symlink_to(self.repo / "README.md")
        with self.assertRaises(ValueError):
            compile_snapshot(self.repo, self.output)
        manifest = self.output / "manifest.json"
        saved = self.output / "original.json"
        manifest.rename(saved)
        manifest.symlink_to(saved)
        self.assertEqual(wiki.catalog()["status"], "unavailable")

    def test_snapshot_is_deterministic_and_keeps_truthful_build_provenance(self):
        first = self.build()
        self.assertEqual(first, self.build())
        source = self.repo / "oracle/README.md"
        source.write_text(source.read_text() + "\nA changed public guide.\n")
        changed = self.build()
        self.assertNotEqual(first, changed)
        record = wiki.page(wiki.page_id("oracle/README.md"))["page"]
        self.assertIsNone(record["source_commit"])
        self.assertIsNone(record["source_url"])
        self.assertEqual(record["source_state"], "working_tree_snapshot")
        self.git("add", "oracle/README.md")
        self.commit()
        self.assertEqual(changed, self.build())
        refreshed = self.build(refresh_provenance=True)
        self.assertNotEqual(changed, refreshed)
        record = wiki.page(wiki.page_id("oracle/README.md"))["page"]
        self.assertEqual(record["source_commit"], self.git("rev-parse", "HEAD").strip())

    def test_missing_snapshot_is_explicitly_unavailable(self):
        (self.output / "pages.json").unlink()
        self.assertEqual(wiki.catalog()["reason"], "wiki_snapshot_unavailable")
        self.assertEqual(
            wiki.page(wiki.page_id("README.md"))["reason"], "wiki_snapshot_unavailable"
        )

    def test_build_check_detects_source_changes_without_writing(self):
        arguments = ["--repo", str(self.repo), "--output", str(self.output), "--check"]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 0)
        before = (self.output / "manifest.json").read_bytes()
        source = self.repo / "botmanager/README.md"
        source.write_text(source.read_text() + "\nNew lifecycle documentation.\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(arguments), 1)
        self.assertEqual((self.output / "manifest.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

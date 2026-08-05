"""The repository index: isolation, correctness, and the staleness gate.

No test here builds the real index or calls the network. `index/build.py`'s
`semantic` subcommand is the only thing in this repo that opens a socket, and it
talks to localhost ollama; a test that exercised it would be neither deterministic
nor available in CI.

The load-bearing test is the first one. `AGENTS.md` requires that the backtest
engine never touches the network, and the index tooling does — so the guarantee
worth pinning is not "the index is careful" but **"the engine cannot reach the
index at all"**. An import edge from `backtester/` to `index/` would put a socket
one `import` away from the engine, and nothing else in the suite would notice.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
INDEX_DIR = REPO / "index"

sys.path.insert(0, str(INDEX_DIR))


class IsolationTests(unittest.TestCase):
    def test_the_engine_has_no_import_edge_to_the_index_tooling(self):
        """The one guarantee that matters, and it is structural rather than careful.

        `index/build.py --semantic` opens a socket to localhost. The engine is
        required never to touch the network. Those two facts coexist safely only
        while nothing under `backtester/` can import `index`, so that is asserted
        directly instead of trusted.
        """
        offenders = []
        for py in sorted(REPO.joinpath("backtester").rglob("*.py")):
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeError):  # pragma: no cover
                continue
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module]
                for m in mods:
                    # This test file legitimately reaches the tooling to test it;
                    # nothing that ships in the engine may.
                    if m.split(".")[0] in {"build", "search", "make_files_doc",
                                           "make_concepts_doc", "index"}:
                        if py.name != "test_index.py":
                            offenders.append(f"{py.relative_to(REPO)} imports {m}")
        self.assertEqual(offenders, [], "engine code must not import index tooling")

    def test_the_index_tooling_does_not_import_the_engine_either(self):
        """Kept acyclic in both directions.

        The index describes the repo; if it imported the engine it would execute
        the thing it is meant to be describing, and a broken engine would then
        break the index that a reader is using to understand why.
        """
        for name in ("build.py", "search.py", "make_files_doc.py", "make_concepts_doc.py"):
            tree = ast.parse((INDEX_DIR / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    mods = [node.module]
                for m in mods:
                    self.assertNotIn(m.split(".")[0], {"backtester", "soltui"},
                                     f"index/{name} must not import {m}")

    def test_only_the_semantic_path_can_open_a_socket(self):
        """`build.py all` is offline, and that is a property worth pinning.

        Every `urllib` reference in the builder must sit inside the embedding path.
        If a future edit moved a fetch into metadata extraction, `all` would
        silently start requiring a network, and the docstring promising otherwise
        would become false.
        """
        src = (INDEX_DIR / "build.py").read_text(encoding="utf-8")
        tree = ast.parse(src)
        allowed = {"embed", "build_semantic"}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name not in allowed:
                body = ast.get_source_segment(src, node) or ""
                self.assertNotIn("urlopen", body,
                                 f"{node.name}() must not open a socket")


class ClassificationTests(unittest.TestCase):
    """`kind` is what makes `--kind code-python` usable, and the order it resolves
    in is a decision rather than an accident: a test *is* Python and a strategy
    card *is* markdown, but the more specific answer is the one a searcher wants.
    """

    def setUp(self):
        import build
        self.classify = build.classify

    def test_specificity_wins_over_extension(self):
        self.assertEqual(self.classify("backtester/tests/test_engine.py"), "test")
        self.assertEqual(self.classify("backtester/strategy_cards/zscore.md"),
                         "strategy-card")
        self.assertEqual(self.classify("research/results/cpcv_results.csv"), "result")
        self.assertEqual(self.classify("research/coin-intelligence/btc-bitcoin.md"),
                         "coin-reference")

    def test_plain_files_fall_through_to_their_language(self):
        self.assertEqual(self.classify("backtester/core/engine.py"), "code-python")
        self.assertEqual(self.classify("extension/src/core/grid.js"), "code-js")
        self.assertEqual(self.classify("docs/ARCHITECTURE.md"), "doc")
        self.assertEqual(self.classify("README.md"), "doc")


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        import build
        self.b = build

    def test_a_shebang_does_not_hide_a_jsdoc_header(self):
        """The executable tools open with `#!/usr/bin/env node`, which defeated the
        JSDoc match and left those files with no summary at all.
        """
        js = "#!/usr/bin/env node\n/**\n * CLI surface.\n */\nexport function x(){}"
        self.assertIn("CLI surface", self.b.js_docstring(js))

    def test_frontmatter_reads_scalars_and_skips_nested_blocks(self):
        fm = self.b.parse_frontmatter(
            "---\nid: zscore\nstatus: implemented\nparams:\n  window: 20\n---\nbody")
        self.assertEqual(fm["id"], "zscore")
        self.assertEqual(fm["status"], "implemented")
        self.assertNotIn("window", fm, "nested keys must not be flattened into the top level")

    def test_python_facts_reports_symbols_and_imports(self):
        doc, syms, imports = self.b.python_facts(
            '"""Doc."""\nimport numpy\nfrom backtester.core import engine\n'
            "CONST = 1\ndef f():\n    pass\nclass K:\n    pass\n")
        self.assertEqual(doc, "Doc.")
        self.assertIn("f()", syms)
        self.assertIn("class K", syms)
        self.assertIn("CONST", syms)
        self.assertIn("numpy", imports)
        self.assertIn("backtester", imports)

    def test_a_derived_csv_summary_states_shape_not_prose(self):
        s = self.b.csv_summary("x.csv", ["a", "b"], 10)
        self.assertIn("10 rows", s)
        self.assertIn("2 columns", s)


class TextIndexTests(unittest.TestCase):
    def setUp(self):
        import build
        self.b = build

    def test_identifiers_are_indexed_whole_and_in_parts(self):
        """A reader searching `fee_bps` and a reader searching `fee` should both
        land on the cost code, so the builder emits both forms.
        """
        toks = self.b.tokenize("fee_bps slippage_bps applied")
        self.assertIn("fee_bps", toks)
        self.assertIn("slippage_bps", toks)

    def test_stopwords_are_dropped(self):
        self.assertEqual(self.b.tokenize("the and for that"), [])

    def test_bm25_ranks_the_denser_document_first(self):
        import search
        text = {
            "postings": {"cpcv": {"a.py": 10, "b.py": 1}},
            "docLengths": {"a.py": 100, "b.py": 100},
            "stats": {"avgDocLength": 100.0},
        }
        ranked = search.bm25("cpcv", text)
        self.assertEqual(ranked[0][0], "a.py")

    def test_rank_fusion_uses_position_not_score_magnitude(self):
        """BM25 scores and cosine similarities live on different scales, so fusing
        raw values would let whichever is numerically larger dominate.
        """
        import search
        a = [("x", 99.0), ("y", 98.0)]      # big scores
        b = [("y", 0.9), ("x", 0.1)]        # small scores, opposite order
        fused = dict(search.fuse(a, b))
        self.assertAlmostEqual(fused["x"], fused["y"], places=6)


class ConceptTests(unittest.TestCase):
    def test_every_shipped_concept_matches_at_least_one_file(self):
        """A concept matching nothing is a taxonomy the repo does not have. The
        builder drops those; this pins that it did.
        """
        p = INDEX_DIR / "CONCEPT-INDEX.json"
        if not p.exists():
            self.skipTest("index not built")
        con = json.loads(p.read_text())
        for c in con["concepts"]:
            self.assertGreater(c["matchingFiles"], 0, f"{c['id']} matches no file")
            self.assertTrue(c["files"], f"{c['id']} has no file list")

    def test_the_reported_count_is_the_corpus_not_the_truncation(self):
        """`matchingFiles` counted the truncated list once, so every concept
        claimed exactly 30 files. The two numbers are now distinct on purpose.
        """
        p = INDEX_DIR / "CONCEPT-INDEX.json"
        if not p.exists():
            self.skipTest("index not built")
        con = json.loads(p.read_text())
        self.assertTrue(any(c["matchingFiles"] > c["shown"] for c in con["concepts"]),
                        "expected at least one concept to match more files than it shows")
        for c in con["concepts"]:
            self.assertGreaterEqual(c["matchingFiles"], c["shown"])


class StalenessGateTests(unittest.TestCase):
    def test_the_committed_index_matches_the_tree(self):
        """The guard this repo learned to want. Two result files here could not be
        re-derived and one was wrong; an index is the same failure class with a
        friendlier face, so CI re-hashes rather than trusts.
        """
        if not (INDEX_DIR / "INDEX.json").exists():
            self.skipTest("index not built")
        r = subprocess.run([sys.executable, str(INDEX_DIR / "build.py"), "--check"],
                           capture_output=True, text=True, cwd=str(REPO))
        self.assertEqual(r.returncode, 0,
                         f"index is stale — rebuild with `python3 index/build.py all`\n"
                         f"{r.stdout}{r.stderr}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

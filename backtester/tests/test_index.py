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

import hashlib

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
INDEX_DIR = REPO / "index"

sys.path.insert(0, str(INDEX_DIR))


def socket_call_owners(source):
    offenders = []

    class Check(ast.NodeVisitor):
        def __init__(self):
            self.allowed = False
            self.owner = "<module>"

        def visit_FunctionDef(self, node):
            # Defaults/decorators execute in the enclosing scope, even on an
            # otherwise permitted embedding function.
            for field, value in ast.iter_fields(node):
                if field != "body":
                    for child in value if isinstance(value, list) else [value]:
                        if isinstance(child, ast.AST):
                            self.visit(child)
            before = self.allowed, self.owner
            self.allowed = self.allowed or node.name in {"embed", "build_semantic"}
            self.owner = node.name
            for child in node.body:
                self.visit(child)
            self.allowed, self.owner = before

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Call(self, node):
            name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
            if name == "urlopen" and not self.allowed:
                offenders.append(self.owner)
            self.generic_visit(node)

    Check().visit(ast.parse(source))
    return offenders


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
                                           "make_concepts_doc", "index", "idle",
                                           "ollama_ensure"}:
                        if py.name not in {"test_index.py", "test_index_search_tooling.py", "test_index_runtime_guards.py"}:
                            offenders.append(f"{py.relative_to(REPO)} imports {m}")
        self.assertEqual(offenders, [], "engine code must not import index tooling")

    def test_the_index_tooling_does_not_import_the_engine_either(self):
        """Kept acyclic in both directions.

        The index describes the repo; if it imported the engine it would execute
        the thing it is meant to be describing, and a broken engine would then
        break the index that a reader is using to understand why.
        """
        for name in ("build.py", "search.py", "make_files_doc.py", "make_concepts_doc.py",
                     "idle.py", "ollama_ensure.py"):
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
        self.assertEqual(socket_call_owners(src), [], "only semantic execution may open a socket")

    def test_module_level_socket_mutant_is_detected_without_executing_it(self):
        source = "import urllib.request\nurllib.request.urlopen('https://invalid.example')\n"
        with patch.object(Path, "read_text", return_value=source), self.assertRaises(AssertionError):
            self.test_only_the_semantic_path_can_open_a_socket()
        self.assertEqual(socket_call_owners("def embed(x=urlopen('invalid')): pass"), ["<module>"])


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
    def test_merge_stages_cannot_create_a_duplicate_catalog(self):
        import build
        import io
        import tempfile
        from contextlib import redirect_stdout
        from unittest import mock

        # Git emits a path for each unmerged stage; Docs uses that path as a
        # unique table key. Hash comparisons alone used to hide the duplicates.
        git_result = subprocess.CompletedProcess([], 0, stdout="README.md\0README.md\0README.md\0")
        with mock.patch.object(build.subprocess, "run", return_value=git_result):
            self.assertEqual(build.tracked_files(), ["README.md"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "README.md"
            source.write_text("valid source")
            entry = {"path": "README.md", "sha1": hashlib.sha1(source.read_bytes()).hexdigest()}
            catalog = root / "INDEX.json"
            catalog.write_text(json.dumps({"files": [entry, entry], "generatedAt": "test"}))
            output = io.StringIO()
            with mock.patch.object(build, "REPO", root), mock.patch.object(build, "INDEX_JSON", catalog), \
                 mock.patch.object(build, "tracked_files", return_value=["README.md"]), redirect_stdout(output):
                self.assertEqual(build.check(), 1)
            self.assertIn("duplicate catalog paths", output.getvalue())
            self.assertIn("README.md", output.getvalue())

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


class IndexTreeBoundaryTests(unittest.TestCase):
    """Tracked names are literal, and tracked links cannot export local files."""

    def test_git_names_survive_quotes_unicode_and_newlines(self):
        import tempfile
        from unittest.mock import patch
        import build
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            import os
            template = root / "empty-template"
            template.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                       GIT_TEMPLATE_DIR=str(template))
            subprocess.run(["git", "init", "--template=" + str(template), "-q", str(root)], check=True, env=env)
            names = ['quoted"file.md', "unicodé.md", "line\nbreak.md", " leading.md"]
            for name in names:
                (root / name).write_text("public fixture\n")
            subprocess.run(["git", "-C", str(root), "add", "--", *names], check=True, env=env)
            with patch.object(build, "REPO", root):
                self.assertEqual(build.tracked_files(), sorted(names))
                self.assertEqual(sorted(e["path"] for e in build.build_meta()["files"]), sorted(names))

    def test_tracked_file_symlink_cannot_export_a_local_canary(self):
        import tempfile
        from unittest.mock import patch
        import build
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "outside.txt"
            outside.write_text("PRIVATE-SYNTHETIC-CANARY")
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "leak.md").symlink_to(outside)
            with patch.object(build, "REPO", root), patch.object(build, "tracked_files", return_value=["leak.md"]):
                with self.assertRaises((OSError, ValueError)):
                    build.build_meta()

    def test_symlink_ancestor_cannot_export_a_local_canary(self):
        import tempfile
        from unittest.mock import patch
        import build
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()
            (outside / "secret.md").write_text("PRIVATE-SYNTHETIC-CANARY")
            (root / "alias").symlink_to(outside, target_is_directory=True)
            with patch.object(build, "REPO", root), patch.object(build, "tracked_files", return_value=["alias/secret.md"]):
                with self.assertRaises((OSError, ValueError)):
                    build.build_meta()

    def test_direct_hash_and_text_reads_refuse_symlinks(self):
        import tempfile
        from unittest.mock import patch
        import build
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "private.txt"
            target.write_text("PRIVATE-SYNTHETIC-CANARY")
            alias = root / "public.md"
            alias.symlink_to(target)
            with patch.object(build, "REPO", root):
                for reader in (build.sha1_of, build.read_text):
                    with self.subTest(reader=reader.__name__), self.assertRaises((OSError, ValueError)):
                        reader(alias)


class IndexSemanticEvidenceTests(unittest.TestCase):
    def test_partial_embedding_batch_never_publishes_a_misaligned_pair(self):
        import tempfile
        from unittest.mock import patch
        import build
        import ollama_ensure
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(build, "REPO", root), patch.object(build, "LOCAL_NPZ", root / "local.npz"), patch.object(build, "LOCAL_MANIFEST", root / "local.json"), patch.object(build, "semantic_corpus", return_value=(["x"] * 33, ["a.py"] * 33)), patch.object(ollama_ensure, "ensure", return_value=ollama_ensure.Status(True, True, False, True, "synthetic")), patch.object(build, "embed", side_effect=[[[1.0, 0.0]] * 32, []]), patch.object(build, "_atomic_write") as write:
                self.assertEqual(build.build_semantic({"files": []}, local=True), 1)
                write.assert_not_called()

    def test_invalid_embedding_vectors_never_publish(self):
        import tempfile
        from unittest.mock import patch
        import build
        import ollama_ensure
        for vectors in ([[[float("nan"), 1.0]]], [[[0.0, 0.0]]], [[[1.0, 0.0], [1.0]]]):
            with self.subTest(vectors=vectors), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                count = len(vectors[0])
                with patch.object(build, "REPO", root), patch.object(build, "LOCAL_NPZ", root / "local.npz"), patch.object(build, "LOCAL_MANIFEST", root / "local.json"), patch.object(build, "semantic_corpus", return_value=(["x"] * count, ["a.py"] * count)), patch.object(ollama_ensure, "ensure", return_value=ollama_ensure.Status(True, True, False, True, "synthetic")), patch.object(build, "embed", return_value=vectors[0]), patch.object(build, "_atomic_write") as write:
                    self.assertEqual(build.build_semantic({"files": []}, local=True), 1)
                    write.assert_not_called()

    def test_interrupted_pair_publication_cannot_map_new_vectors_to_old_owners(self):
        import tempfile
        import numpy as np
        from unittest.mock import patch
        import build
        import search
        import ollama_ensure
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            array, manifest = root / "local.npz", root / "local.json"
            np.savez_compressed(array, embeddings=np.array([[1.0, 0.0]], dtype="float16"))
            manifest.write_text(json.dumps({"dims": 2, "chunks": 1, "chunkOwners": ["old.py"]}))
            original_write = build._atomic_write
            def write(path, data):
                if path == manifest and b'new.py' in data:
                    raise OSError("synthetic publication failure")
                original_write(path, data)
            with patch.object(build, "REPO", root), patch.object(build, "LOCAL_NPZ", array), patch.object(build, "LOCAL_MANIFEST", manifest), patch.object(build, "semantic_corpus", return_value=(["x"], ["new.py"])), patch.object(ollama_ensure, "ensure", return_value=ollama_ensure.Status(True, True, False, True, "synthetic")), patch.object(build, "embed", return_value=[[0.0, 1.0]]), patch.object(build, "_atomic_write", side_effect=write):
                with self.assertRaises(OSError):
                    build.build_semantic({"files": []}, local=True)
            search._CACHE.clear()
            with self.assertRaises(ValueError):
                search._semantic_matrix((manifest, array))
            search._CACHE.clear()


class IndexHelperBoundaryTests(unittest.TestCase):
    def test_local_ollama_probe_never_follows_a_redirect(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import ollama_ensure
        reached = []
        class Destination(BaseHTTPRequestHandler):
            def do_GET(self):
                reached.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"models": []}')
            def log_message(self, *_):
                pass
        destination = ThreadingHTTPServer(("127.0.0.1", 0), Destination)
        class Redirect(Destination):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{destination.server_port}/elsewhere")
                self.end_headers()
        redirect = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        servers = [destination, redirect]
        threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in servers]
        for thread in threads:
            thread.start()
        try:
            self.assertIsNone(ollama_ensure.installed_models(f"http://127.0.0.1:{redirect.server_port}"))
            self.assertEqual(reached, [])
        finally:
            for server, thread in zip(servers, threads):
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_malformed_model_lists_degrade_without_attribute_errors(self):
        from unittest.mock import patch
        import ollama_ensure
        for data in ([], {"models": None}, {"models": [3]}, {"models": "bad"}):
            with self.subTest(data=data), patch.object(ollama_ensure, "_get_json", return_value=data):
                self.assertIsNone(ollama_ensure.installed_models())

    def test_spawn_failure_reports_a_failed_readiness_status(self):
        from unittest.mock import patch
        import ollama_ensure
        with patch.object(ollama_ensure, "installed_models", return_value=None), patch.object(ollama_ensure, "start_server", side_effect=OSError("synthetic")):
            result = ollama_ensure.ensure()
        self.assertFalse(result.ok)
        self.assertFalse(result.started)

    def test_busy_and_held_lock_decisions_are_throttled(self):
        import tempfile
        from unittest.mock import patch
        import idle
        for busy in (True, False):
            with self.subTest(busy=busy), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                with patch.object(idle, "STATE_FILE", root / "state.json"), patch.object(idle, "semantic_status", return_value=("stale", "synthetic")) as status, patch.object(idle, "is_idle", return_value=not busy), patch.object(idle, "lock_free", return_value=False), patch.dict("os.environ", {"INDEX_NO_AUTO": "0"}), patch.object(idle.ollama_ensure, "ensure", side_effect=AssertionError("unexpected readiness")):
                    idle._write_state({"last_build_at": 1900})
                    idle.maybe_start(now=2000)
                    idle.maybe_start(now=2001)
                    self.assertEqual(status.call_count, 1)

    def test_finished_build_preserves_the_hourly_sweep_clock(self):
        import tempfile
        from unittest.mock import patch
        import idle
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(idle, "STATE_FILE", root / "state.json"), patch.object(idle, "LOCK_FILE", root / "lock"), patch.object(idle, "OUT", root), patch.object(idle.build, "build_meta", return_value={}), patch.object(idle.build, "build_semantic", return_value=0):
                idle._write_state({"last_build_at": 1900})
                self.assertEqual(idle.run_build(), 0)
                self.assertEqual(idle._read_state()["last_build_at"], 1900)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

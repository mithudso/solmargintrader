"""Synthetic semantic generations cannot be paired across replacements."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "index"))
import search
import build


class SemanticBindingTests(unittest.TestCase):
    def setUp(self):
        search._CACHE.clear()
        self.addCleanup(search._CACHE.clear)

    def test_unreadable_source_cannot_publish_empty_postings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            item = {"id": "fixture", "path": "source.py", "ext": ".py", "title": "source", "summary": "", "symbols": []}
            with patch.object(build, "REPO", root), patch.object(Path, "read_text", side_effect=PermissionError("fixture")):
                with self.assertRaises(OSError):
                    build.build_text({"files": [item], "generatedAt": "fixture"})

    def test_rejects_mixed_generation_before_starting_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.npz"
            current = root / "current.npz"
            manifest = root / "manifest.json"
            np.savez_compressed(original, embeddings=np.array([[1, 0], [0, 1]], dtype="float16"))
            np.savez_compressed(current, embeddings=np.array([[0, 1], [1, 0]], dtype="float16"))
            manifest.write_text(json.dumps({"chunkOwners": ["A", "B"],
                "arraySha256": hashlib.sha256(original.read_bytes()).hexdigest()}))
            with patch.object(search, "semantic_pair", return_value=(manifest, current)), \
                 patch.object(search.ollama_ensure, "ensure") as ensure:
                self.assertIsNone(search.semantic("query", notes=[], start_ollama=False))
            ensure.assert_not_called()
            with self.assertRaises(ValueError):
                search._semantic_matrix((manifest, current))

    def test_matching_pair_loads_and_unbound_legacy_pair_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            array = root / "array.npz"
            manifest = root / "manifest.json"
            np.savez_compressed(array, embeddings=np.array([[1, 0]], dtype="float16"))
            data = {"chunkOwners": ["A"], "arraySha256": hashlib.sha256(array.read_bytes()).hexdigest()}
            manifest.write_text(json.dumps(data))
            _, matrix, owners = search._semantic_matrix((manifest, array))
            self.assertEqual(owners, ["A"])
            self.assertEqual(matrix.tolist(), [[1.0, 0.0]])
            search._CACHE.clear()
            manifest.write_text(json.dumps({"chunkOwners": ["A"]}))
            with self.assertRaises(ValueError):
                search._semantic_matrix((manifest, array))

    def test_builder_binds_written_bytes_without_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            array, manifest = root / "array.npz", root / "manifest.json"
            with patch.multiple(build, REPO=root, SEMANTIC_NPZ=array, SEMANTIC_MANIFEST=manifest), \
                 patch.object(build, "semantic_corpus", return_value=(["fixture"], ["A"])), \
                 patch.object(build.ollama_ensure, "ensure", return_value=SimpleNamespace(ok=True, message="fixture")), \
                 patch.object(build, "embed", return_value=[[1, 0]]):
                self.assertEqual(build.build_semantic({"files": []}), 0)
            self.assertEqual(json.loads(manifest.read_text())["arraySha256"],
                             hashlib.sha256(array.read_bytes()).hexdigest())
            self.assertEqual(search._semantic_matrix((manifest, array))[2], ["A"])

    def test_requested_limit_and_kind_are_applied_before_semantic_truncation(self):
        entries = [{"id": str(i), "path": f"{i}.py", "kind": "wanted" if i == 40 else "other",
                    "lines": 1, "summary": ""} for i in range(41)]
        ranked = [(str(i), float(41 - i)) for i in range(41)]

        def fake_semantic(query, limit=40, **kwargs):
            return ranked[:limit]

        with patch.object(search, "_cached_json", return_value={"files": entries}), \
             patch.object(search, "semantic", side_effect=fake_semantic):
            all_hits = search.run_query("fixture", "semantic", 100, auto_index=False)
            filtered = search.run_query("fixture", "semantic", 10, kind="wanted", auto_index=False)
        self.assertEqual(len(all_hits.hits), 41)
        self.assertEqual([hit.path for hit in filtered.hits], ["40.py"])
        with patch.object(search, "load", return_value={"files": entries}), \
             patch.object(search, "semantic", side_effect=fake_semantic), \
             patch.object(search, "show") as show:
            self.assertEqual(search.main(["--semantic", "--kind", "wanted", "fixture"]), 0)
        self.assertEqual(len(show.call_args.args[0]), 41)


if __name__ == "__main__":
    unittest.main()

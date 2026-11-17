"""Offline keyword index round-trip, integrity, and ranking guarantees."""
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "index"))
import build
import search
import text_index


class CompressedIndexTests(unittest.TestCase):
    def test_exact_roundtrip_and_scores(self):
        source = {"postings": {"fee_bps": {"a": 4, "b": 1}, "fee": {"a": 1}},
                  "docLengths": {"a": 12, "b": 8}, "stats": {"avgDocLength": 10}}
        raw = (json.dumps(source, separators=(",", ":"), sort_keys=True) + "\n").encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TEXT-INDEX.json.gz"
            text_index.write(path, source)
            compressed = path.read_bytes()
            self.assertEqual(gzip.decompress(compressed), raw)
            self.assertEqual(path.with_suffix('.gz.sha256').read_text().strip(), hashlib.sha256(raw).hexdigest())
            decoded = text_index.read(path)
            self.assertEqual(decoded, source)
            for query in ("fee_bps", "fee", "missing"):
                self.assertEqual(search.bm25(query, decoded), search.bm25(query, source))
            self.assertEqual(compressed[3] & 8, 0)  # no filename
            self.assertEqual(compressed[4:8], b"\0" * 4)
            text_index.write(path, source)
            self.assertEqual(path.read_bytes(), compressed)

    def test_missing_corrupt_and_mismatched_fail_closed_with_legacy_present(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "TEXT-INDEX.json.gz"
            path.with_suffix("").write_text('{}')
            with self.assertRaises(ValueError):
                text_index.read(path)
            text_index.write(path, {"postings": {"key": {"a": 1}}})
            path.write_bytes(path.read_bytes()[:-5])
            with self.assertRaises(ValueError):
                text_index.read(path)
            text_index.write(path, {"postings": {"key": {"a": 1}}})
            path.with_suffix('.gz.sha256').write_text('0' * 64)
            with self.assertRaises(ValueError):
                text_index.read(path)

    def test_freshness_gate_rejects_corrupt_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.txt"
            source.write_text("source")
            catalog = root / "INDEX.json"
            catalog.write_text(json.dumps({"files": [{"path": "source.txt", "sha1": hashlib.sha1(source.read_bytes()).hexdigest()}],
                                           "generatedAt": "test"}))
            artifact = root / "TEXT-INDEX.json.gz"
            text_index.write(artifact, {"postings": {"key": {"a": 1}}})
            meta = json.loads(catalog.read_text())
            meta["textSha256"] = artifact.with_suffix('.gz.sha256').read_text().strip()
            catalog.write_text(json.dumps(meta))
            with mock.patch.object(build, "REPO", root), mock.patch.object(build, "INDEX_JSON", catalog), \
                 mock.patch.object(build, "TEXT_JSON", artifact), \
                 mock.patch.object(build, "tracked_files", return_value=["source.txt"]):
                self.assertEqual(build.check(), 0)
                text_index.write(artifact, {"postings": {"old": {"a": 1}}})
                self.assertEqual(build.check(), 1, "a valid old artifact must not match current metadata")
                artifact.write_bytes(b"corrupt")
                self.assertEqual(build.check(), 1)


if __name__ == '__main__':
    unittest.main()

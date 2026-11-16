import datetime as dt
import gzip
import tempfile
import unittest
from pathlib import Path

from scripts.preserve_dual_quotes import retain


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.src = Path(self.tmp.name) / "src"
        self.dst = Path(self.tmp.name) / "dst"
        self.src.mkdir()
        self.now = dt.datetime(2026, 11, 16, 10, 15, tzinfo=dt.UTC)

    def write(self, hour, data=b"quote"):
        p = self.src / f"dual-quotes-20261116T{hour}-abcd.jsonl.gz"
        p.write_bytes(gzip.compress(data))
        return p

    def run_copy(self, cap=100000):
        return retain(self.src, self.dst, self.now, cap=cap, min_free=0)

    def test_closed_hour_only_and_restart_is_idempotent(self):
        closed = self.write("09")
        current = self.write("10")
        self.assertEqual(self.run_copy()["files_copied"], 1)
        self.assertEqual((self.dst / closed.name).read_bytes(), closed.read_bytes())
        self.assertFalse((self.dst / current.name).exists())
        self.assertEqual(self.run_copy()["files_copied"], 0)
        self.assertTrue((self.dst / (closed.name + ".receipt.json")).exists())

    def test_corrupt_gzip_never_copied(self):
        p = self.write("09")
        p.write_bytes(p.read_bytes()[:-3])
        with self.assertRaises((EOFError, OSError)):
            self.run_copy()
        self.assertFalse((self.dst / p.name).exists())

    def test_conflict_is_not_overwritten(self):
        p = self.write("09")
        self.run_copy()
        other = gzip.compress(b"different")
        (self.dst / p.name).write_bytes(other)
        with self.assertRaisesRegex(RuntimeError, "conflict"):
            self.run_copy()
        self.assertEqual((self.dst / p.name).read_bytes(), other)

    def test_byte_cap_stops_before_copy(self):
        p = self.write("09")
        with self.assertRaisesRegex(RuntimeError, "cap"):
            self.run_copy(cap=1)
        self.assertFalse((self.dst / p.name).exists())


if __name__ == "__main__":
    unittest.main()

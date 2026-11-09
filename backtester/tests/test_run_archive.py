from __future__ import annotations

import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from backtester.core.run_archive import ArchiveError, backup_archive, import_run, read_run


class RunArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / "output"
        self.output.mkdir()
        self.archive = self.root / "runs.db"
        self.content = b"timestamp,equity\n1,99\n"
        (self.output / "equity.csv").write_bytes(self.content)
        for name in ("comparison.csv", "report.md", "trades_test.csv", "equity_test.csv"):
            (self.output / name).write_bytes(self.content)
        self.inventory = {name: hashlib.sha256(self.content).hexdigest() for name in
                          ("equity.csv", "comparison.csv", "report.md", "trades_test.csv", "equity_test.csv")}
        self.write_manifest(self.inventory)

    def write_manifest(self, inventory):
        fields = {name: "fixture" for name in ("asset", "start", "end", "interval", "mode",
                  "leverage", "initial_capital", "fill_delay", "seed", "rebalance_threshold",
                  "costs", "data_source", "data_checksum", "bar_count", "split",
                  "library_versions", "periods_per_year", "sharpe_convention")}
        (self.output / "run_manifest.json").write_text(json.dumps({**fields, "strategies": {"test": {}}, "artifact_sha256": inventory}))

    def test_round_trip_and_idempotency(self):
        run_id = import_run(self.archive, self.output)
        self.assertEqual(import_run(self.archive, self.output), run_id)
        manifest, artifacts = read_run(self.archive, run_id)
        self.assertEqual(manifest, (self.output / "run_manifest.json").read_bytes())
        self.assertEqual(artifacts, {name: self.content for name in self.inventory})
        self.assertEqual(self.archive.stat().st_mode & 0o777, 0o600)

    def test_corrupt_or_missing_source_is_never_published(self):
        (self.output / "equity.csv").write_bytes(b"tampered")
        with self.assertRaisesRegex(ArchiveError, "digest mismatch"):
            import_run(self.archive, self.output)
        self.assertFalse(self.archive.exists())
        (self.output / "equity.csv").unlink()
        with self.assertRaisesRegex(ArchiveError, "missing"):
            import_run(self.archive, self.output)

    def test_traversal_and_symlinks_are_rejected(self):
        self.write_manifest({**self.inventory, "../outside": "a" * 64})
        with self.assertRaisesRegex(ArchiveError, "unsafe"):
            import_run(self.archive, self.output)
        self.write_manifest({**self.inventory, "link": hashlib.sha256(self.content).hexdigest()})
        (self.output / "link").symlink_to(self.output / "equity.csv")
        with self.assertRaisesRegex(ArchiveError, "unsafe"):
            import_run(self.archive, self.output)

    def test_corrupt_stored_artifact_is_detected(self):
        run_id = import_run(self.archive, self.output)
        with closing(sqlite3.connect(self.archive)) as db, db:
            db.execute("UPDATE artifacts SET content = ?", (b"changed",))
        with self.assertRaisesRegex(ArchiveError, "digest mismatch"):
            read_run(self.archive, run_id)
        with self.assertRaises(ArchiveError):
            import_run(self.archive, self.output)

    def test_missing_stored_artifact_is_detected(self):
        run_id = import_run(self.archive, self.output)
        with closing(sqlite3.connect(self.archive)) as db, db:
            db.execute("DELETE FROM artifacts")
        with self.assertRaisesRegex(ArchiveError, "inventory mismatch"):
            read_run(self.archive, run_id)

    def test_duplicate_manifest_key_rejected(self):
        (self.output / "run_manifest.json").write_text('{"artifact_sha256": {}, "artifact_sha256": {}}')
        with self.assertRaises(ArchiveError):
            import_run(self.archive, self.output)

    def test_backup_is_independently_readable_and_never_overwrites(self):
        run_id = import_run(self.archive, self.output)
        backup = self.root / "backup.db"
        backup_archive(self.archive, backup)
        self.assertEqual(read_run(backup, run_id)[1]["equity.csv"], self.content)
        with self.assertRaises(FileExistsError):
            backup_archive(self.archive, backup)

    def test_refuses_insecure_existing_archive(self):
        self.archive.touch(mode=0o644)
        self.archive.chmod(0o644)
        with self.assertRaisesRegex(ArchiveError, "private"):
            import_run(self.archive, self.output)


if __name__ == "__main__":
    unittest.main()

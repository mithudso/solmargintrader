from __future__ import annotations

from pathlib import Path
from contextlib import closing
import sqlite3
import tempfile
import unittest

from backtester.core.history_store import import_history, read_history
from backtester.core.run_archive import ArchiveError, backup_archive
from backtester.core.data import DataValidationError, SnapshotLoader


class HistoryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.db = root / "history.db"
        self.csv = root / "bars.csv"
        self.csv.write_text("timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n60,11,13,10,12,6\n")
        self.kw = dict(instrument="SOL-USD", venue="example", source="test fixture", interval_seconds=60)

    def test_roundtrip_idempotency_and_range(self):
        key = import_history(self.db, self.csv, **self.kw)
        self.assertEqual(key, import_history(self.db, self.csv, **self.kw))
        meta, rows = read_history(self.db, key, 60, 60)
        self.assertEqual(meta["instrument"], "SOL-USD")
        self.assertEqual(rows, [(60, 11., 13., 10., 12., 6.)])
        with self.assertRaisesRegex(ArchiveError, "not fully covered"):
            read_history(self.db, key, 0, 120)

    def test_snapshot_loader_checks_identity_and_cadence(self):
        key = import_history(self.db, self.csv, **self.kw)
        loader = SnapshotLoader(self.db, key)
        self.assertEqual(loader.load("SOL", None, None, "1m")["close"].tolist(), [11., 12.])
        with self.assertRaises(DataValidationError):
            loader.load("BTC", None, None, "1m")
        with self.assertRaises(DataValidationError):
            loader.load("SOL", None, None, "1h")

    def test_intraday_cutoff_excludes_unfinished_candle(self):
        key = import_history(self.db, self.csv, **self.kw)
        frame = SnapshotLoader(self.db, key).load("SOL", None, "1970-01-01 00:01:30", "1m")
        self.assertEqual(frame["timestamp"].tolist(), [0])

    def test_cutoff_at_last_bar_close_is_covered(self):
        key = import_history(self.db, self.csv, **self.kw)
        frame = SnapshotLoader(self.db, key).load("SOL", None, "1970-01-01 00:02:00", "1m")
        self.assertEqual(frame["timestamp"].tolist(), [0, 60])

    def test_explicit_midnight_is_not_a_whole_date(self):
        self.csv.write_text("timestamp,open,high,low,close,volume\n1609459140,10,12,9,11,5\n1609459200,11,13,10,12,6\n1609459260,11,13,10,12,6\n")
        key = import_history(self.db, self.csv, **self.kw)
        frame = SnapshotLoader(self.db, key).load("SOL", None, "2021-01-01 00:00:00", "1m")
        self.assertEqual(frame["timestamp"].tolist(), [1609459140])

    def test_loader_refuses_unknown_quote_or_venue(self):
        key = import_history(self.db, self.csv, **{**self.kw, "instrument": "SOL-UNKNOWN"})
        with self.assertRaisesRegex(DataValidationError, "requested asset and quote"):
            SnapshotLoader(self.db, key).load("SOL", None, None, "1m")
        key = import_history(self.db, self.csv, **{**self.kw, "venue": "unknown"})
        with self.assertRaisesRegex(DataValidationError, "venue"):
            SnapshotLoader(self.db, key).load("SOL", None, None, "1m")

    def test_explicit_usdt_quote_preserves_instrument_identity(self):
        key = import_history(self.db, self.csv, **{**self.kw, "instrument": "SOL-USDT"})
        loader = SnapshotLoader(self.db, key, quote="USDT")
        self.assertEqual(loader.load("SOL", None, None, "1m")["close"].tolist(), [11., 12.])
        with self.assertRaises(DataValidationError):
            SnapshotLoader(self.db, key, quote="USDC").load("SOL", None, None, "1m")

    def test_corrupt_snapshot_is_detected(self):
        key = import_history(self.db, self.csv, **self.kw)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE history_bars SET c=100 WHERE ts=60")
        with self.assertRaisesRegex(ArchiveError, "content mismatch"):
            read_history(self.db, key, 0, 60)
        with self.assertRaises(ArchiveError):
            import_history(self.db, self.csv, **self.kw)

    def test_invalid_input_never_publishes_partial_snapshot(self):
        self.csv.write_text("timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n120,11,13,10,12,6\n")
        with self.assertRaisesRegex(ArchiveError, "noncontiguous"):
            import_history(self.db, self.csv, **self.kw)
        with closing(sqlite3.connect(self.db)) as db, db:
            self.assertEqual(db.execute("SELECT count(*) FROM history_snapshots").fetchone()[0], 0)

    def test_failed_write_rolls_back_new_snapshot(self):
        original = import_history(self.db, self.csv, **self.kw)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("CREATE TRIGGER abort_new BEFORE INSERT ON history_bars BEGIN SELECT RAISE(ABORT, 'injected failure'); END")
        self.csv.write_text("timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n60,11,13,10,11,6\n")
        with self.assertRaises(sqlite3.IntegrityError):
            import_history(self.db, self.csv, **self.kw)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM history_snapshots").fetchone()[0], 1)
        self.assertEqual(read_history(self.db, original, 0, 60)[0]["count"], 2)

    def test_backup_restores_history(self):
        original = import_history(self.db, self.csv, **self.kw)
        backup = self.db.parent / "backup.db"
        backup_archive(self.db, backup)
        self.assertEqual(read_history(backup, original, 0, 60)[0]["count"], 2)

    def test_corrected_content_gets_new_identity(self):
        original = import_history(self.db, self.csv, **self.kw)
        self.csv.write_text("timestamp,open,high,low,close,volume\n0,10,12,9,11,5\n60,11,13,10,11,6\n")
        corrected = import_history(self.db, self.csv, **self.kw)
        self.assertNotEqual(original, corrected)
        self.assertEqual(read_history(self.db, original, 60, 60)[1][0][4], 12)


if __name__ == "__main__":
    unittest.main()

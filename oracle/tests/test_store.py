from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from oracle.store import Store


class StoreTests(unittest.TestCase):
    def test_foreign_archive_refused_without_ddl(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "foreign.db"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("CREATE TABLE owner_data (x INTEGER)")
                db.execute("INSERT INTO owner_data VALUES(42)")
            with self.assertRaisesRegex(ValueError, "schema_not_supported"):
                Store(path)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(
                    db.execute("SELECT x FROM owner_data").fetchone()[0], 42
                )
                self.assertEqual(
                    db.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall(),
                    [("owner_data",)],
                )

    def test_history_is_bounded_and_cursor_paginates(self):
        with tempfile.TemporaryDirectory() as root:
            store = Store(Path(root) / "history.db")
            with store.connection() as db:
                for i in range(3):
                    store.event(db, "test", str(i), {"n": i})
            page = store.history(limit=2)
            self.assertEqual([e["data"]["n"] for e in page["events"]], [0, 1])
            self.assertEqual(
                store.history(after=page["next_after"])["events"][0]["data"]["n"], 2
            )
            self.assertEqual(store.path.stat().st_mode & 0o777, 0o600)
            for bad in (0, True, 1001):
                with self.assertRaises(ValueError):
                    store.history(limit=bad)

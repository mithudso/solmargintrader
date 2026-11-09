"""Forward-test display reads do not request the active writer's lock."""

from __future__ import annotations

import sqlite3
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from unittest.mock import patch

from soltui import commands, config, forwardtest as ft
from soltui.tests.test_forwardtest import BASE, candles


class ForwardDatabaseConcurrency(unittest.TestCase):
    def setUp(self) -> None:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.enterContext(patch.object(config, "CONFIG_DIR", Path(tmp.name)))
        self.path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
        self.path.parent.mkdir()
        self.trial = {"label": "hold", "mode": "all", "members": [ft.member("buy_and_hold", {})]}
        self.plan = {"assets": ["SOL"], "trials": [self.trial], "horizons": (1,)}

    def advance(self, minute: int) -> dict:
        return ft.tick("SOL", [self.trial], (1,), 16.0, tune=False,
                       fetch=lambda *a, **k: candles(minute),
                       clock=lambda: BASE + minute * 60 + 4, code="concurrency-fixture")

    def test_saved_plan_read_works_during_legacy_writer_without_migrating(self) -> None:
        # This is deliberately a legacy rollback-journal database. Reading its
        # plan must work before any writer is explicitly started on new code.
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("CREATE TABLE session(id INTEGER PRIMARY KEY,plan TEXT)")
            writer.execute("INSERT INTO session VALUES(1,?)", (ft._json(self.plan),))
            writer.commit()
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE session SET plan=?", (ft._json({"horizons": [30]}),))
            self.assertEqual(ft.load_session(), self.plan)
            self.assertEqual(writer.execute("PRAGMA journal_mode").fetchone()[0], "delete")
            self.assertEqual(writer.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),
                             [("session",)])

    def test_plan_read_does_not_create_missing_legacy_session_table(self) -> None:
        with closing(sqlite3.connect(self.path)) as db:
            db.execute("CREATE TABLE candle(asset TEXT)")
            db.commit()
            self.assertIsNone(ft.load_session())
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),
                             [("candle",)])
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "delete")

    def test_current_schema_connection_does_not_acquire_writer_slot(self) -> None:
        ft.save_session(self.plan)
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE session SET plan=plan")
            with closing(ft._db(self.path)) as other:
                self.assertFalse(other.in_transaction)
                self.assertEqual(other.execute("PRAGMA journal_mode").fetchone()[0], "wal")
                self.assertEqual(other.execute("SELECT count(*) FROM session").fetchone()[0], 1)

    def test_reader_snapshot_does_not_prevent_writer_commit(self) -> None:
        ft.save_session(self.plan)
        with closing(sqlite3.connect(self.path)) as reader, closing(ft._db(self.path)) as writer:
            self.assertEqual(writer.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            reader.execute("BEGIN")
            original = reader.execute("SELECT plan FROM session").fetchone()[0]
            writer.execute("BEGIN IMMEDIATE")
            writer.execute("UPDATE session SET plan=?", (ft._json({"horizons": [30]}),))
            writer.commit()
            self.assertEqual(reader.execute("SELECT plan FROM session").fetchone()[0], original)
            self.assertEqual(ft.load_session(), {"horizons": (30,)})

    def test_failed_migration_closes_connection_and_can_recover(self) -> None:
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("CREATE TABLE session(id INTEGER PRIMARY KEY,plan TEXT)")
            writer.execute("BEGIN IMMEDIATE")
            connect = sqlite3.connect
            opened = []

            def tracked_connect(*args, **kwargs):
                db = connect(*args, **{**kwargs, "timeout": .05})
                opened.append(db)
                return db

            with patch.object(ft.sqlite3, "connect", side_effect=tracked_connect):
                with self.assertRaisesRegex(sqlite3.OperationalError, "locked"):
                    ft._db(self.path)
            self.assertEqual(len(opened), 1)
            with self.assertRaisesRegex(sqlite3.ProgrammingError, "closed"):
                opened[0].execute("SELECT 1")
            writer.rollback()
        with closing(ft._db(self.path)) as db:
            self.assertTrue(ft._schema_current(db))
            self.assertFalse(db.in_transaction)

    def test_display_and_manual_check_read_committed_evidence_during_real_tick(self) -> None:
        ft.save_session(self.plan)
        self.advance(0)
        baseline = self.advance(2)["rows"]
        self.assertEqual(baseline[0]["resolved"], 1)
        entered, release = Event(), Event()
        outcomes, failures = [], []
        forecast = ft._predict

        def paused_forecast(*args, **kwargs):
            entered.set()
            if not release.wait(10):
                raise AssertionError("The test did not release the forward writer")
            return forecast(*args, **kwargs)

        def run_tick():
            try:
                outcomes.append(self.advance(3))
            except BaseException as exc:
                failures.append(exc)

        ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        with patch.object(ft, "_predict", side_effect=paused_forecast):
            worker = Thread(target=run_tick, name="test-forward-writer")
            worker.start()
            try:
                self.assertTrue(entered.wait(5), "The real tick must hold its write transaction")
                self.assertEqual(ft.status("SOL"), baseline)
                predictions = commands.dispatch("forwardtest.predictions", {"asset": "SOL"}, ctx=ctx, quiet=True)
                self.assertTrue(predictions["ok"], predictions)
                self.assertEqual(predictions["result"]["rows"][0]["resolved"], 1)
                state = commands.dispatch("forwardtest.state", {}, ctx=ctx, quiet=True)
                self.assertTrue(state["ok"], state)
                with patch("soltui.current_signal.check", return_value={"checked": True}) as check:
                    manual = commands.dispatch("signals.check", {"asset": "SOL"}, ctx=ctx, quiet=True)
                self.assertTrue(manual["ok"], manual)
                check.assert_called_once_with("SOL", self.plan["trials"])
            finally:
                release.set()
                worker.join(5)
        self.assertFalse(worker.is_alive(), "The forward writer must finish and close its connection")
        self.assertEqual(failures, [])
        self.assertEqual(len(outcomes), 1)
        self.assertGreater(outcomes[0]["rows"][0]["last_issued"], baseline[0]["last_issued"])
        self.assertGreater(outcomes[0]["recorded"], 0)


if __name__ == "__main__":
    unittest.main()

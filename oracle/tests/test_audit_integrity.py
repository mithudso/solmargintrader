from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager, nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from oracle import cli, gum_orders, gum_webhook_orders
from oracle import engine as engine_module
from oracle.engine import OracleEngine
from oracle.reader import ReadOnlyOracle
from oracle.tests import test_archived_reader as recorded
from oracle.tests.test_core import observation


class TemporalIntegrityTests(unittest.TestCase):
    def test_prediction_aggregates_evidence_once_for_all_strategy_versions(self):
        fixture = self.fixture()
        statements = []
        original = fixture.writer.store.connection

        @contextmanager
        def traced():
            with original() as db:
                db.set_trace_callback(statements.append)
                yield db

        with patch.object(fixture.writer.store, "connection", traced):
            predictions = fixture.writer.predictions(now=1001)
        joins = [sql for sql in statements if "from resolutions" in sql.lower() and "join forecasts" in sql.lower()]
        self.assertEqual(len(joins), 1)
        first = next(row for row in predictions["strategies"] if row["strategy_id"] == fixture.catalog[0]["strategy_id"])
        self.assertEqual(first["resolved"], 1)
        self.assertEqual(first["confidence_percent"], 100)

    def test_requested_success_poll_interval_is_preserved(self):
        stop = Mock()
        stop.is_set.return_value = False
        feed = Mock()
        feed.poll.return_value = None
        args = SimpleNamespace(archive=Path("/unused"), instrument="SOL/USD", source="recorder",
                               recorder_root=Path("/unused"), interval=300, max_ticks=2)
        with (patch.object(cli, "owner", return_value=nullcontext()),
              patch.object(cli.threading, "Event", return_value=stop),
              patch.object(cli.signal, "signal"), patch.object(cli, "emit"),
              patch("oracle.engine.OracleEngine"), patch("oracle.feeds.RecorderFeed", return_value=feed)):
            self.assertEqual(cli.run(args), 0)
        stop.wait.assert_called_once_with(300)

    def test_fifo_secret_is_refused_before_any_blocking_open(self):
        original = os.open

        def nonblocking_open(path, flags):
            self.assertTrue(flags & os.O_NONBLOCK)
            return original(path, flags)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fifo"
            os.mkfifo(path, 0o600)
            with patch.object(cli.os, "open", side_effect=nonblocking_open), self.assertRaisesRegex(ValueError, "secret_file_must_be_private"):
                cli.read_private_secret(path)

    def test_malformed_durable_leg_stays_unknown_without_dispatch(self):
        from unittest.mock import patch

        for legs in (True, {"untrusted": "shape"}, [None]):
            with self.subTest(legs=legs), patch.object(gum_webhook_orders, "_save") as save:
                state = {"phase": "awaiting_fill", "legs": legs}
                result = gum_webhook_orders._resume(None, {}, object(), state,
                    now=1000, started=1000, enabled=lambda: True, allow_live=True)
                self.assertEqual(result, "unknown")
                self.assertEqual(save.call_args.kwargs["result"], {"reason": "fill_requires_reconciliation"})

    def test_oversized_integer_is_not_a_number(self):
        self.assertFalse(engine_module.number(10**400))

    def test_decimal_scale_is_bounded_before_formatting(self):
        with self.assertRaises(gum_orders.GumError):
            gum_orders._decimal("1e-100000")

    def test_archive_is_private_before_first_sqlite_open(self):
        from unittest.mock import patch

        from oracle.store import Store

        original = sqlite3.connect
        modes = []

        def connect(path, *args, **kwargs):
            modes.append(Path(path).stat().st_mode & 0o777 if Path(path).exists() else None)
            return original(path, *args, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            prior = os.umask(0o022)
            try:
                with patch("oracle.store.sqlite3.connect", side_effect=connect):
                    Store(Path(directory) / "archive.sqlite3")
            finally:
                os.umask(prior)
        self.assertEqual(modes[0], 0o600)

    def test_reader_revalidates_appended_forecast_before_next_query(self):
        fixture = self.fixture()
        reader = ReadOnlyOracle(fixture.path, instrument="SOL/USD", archived_versions=True)
        card = fixture.catalog[0]
        with fixture.writer.store.connection() as db:
            db.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)", (
                "invalid", card["strategy_id"], card["version"], 1001, 1061, -1, 100, "{}"))
        with self.assertRaisesRegex(ValueError, "oracle_recorded_policy_binding_invalid"):
            reader.predictions(1002)

    def test_later_observations_do_not_change_past_market(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = OracleEngine(Path(directory) / "archive.sqlite3")
            engine.ingest(observation(24), now=1441)
            before = engine.market(1441)
            engine.ingest(observation(25, 200), now=1501)
            self.assertEqual(engine.market(1441), before)
            self.assertEqual(engine.market(1400)["reason"], "no_market_data")

    def test_delayed_receipt_is_not_known_before_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = OracleEngine(Path(directory) / "archive.sqlite3")
            engine.ingest(observation(24, received_at=1450), now=1450)
            self.assertEqual(engine.market(1441)["status"], "unavailable")
            self.assertEqual(engine.market(1450)["status"], "available")

    def fixture(self):
        fixture = recorded.ArchivedReaderTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_premature_resolution_refuses_before_exposing_votes(self):
        fixture = self.fixture()
        with fixture.writer.store.connection() as db:
            db.execute("DROP TRIGGER immutable_resolutions_UPDATE")
            db.execute("UPDATE resolutions SET resolved_at=901 WHERE forecast='prior'")
        with self.assertRaisesRegex(ValueError, "oracle_recorded_resolution_invalid"):
            ReadOnlyOracle(fixture.path, instrument="SOL/USD", archived_versions=True)

    def test_contradictory_resolution_refuses(self):
        fixture = self.fixture()
        with fixture.writer.store.connection() as db:
            db.execute("DROP TRIGGER immutable_resolutions_UPDATE")
            db.execute("UPDATE resolutions SET hit=0 WHERE forecast='prior'")
        with self.assertRaisesRegex(ValueError, "oracle_recorded_resolution_invalid"):
            ReadOnlyOracle(fixture.path, instrument="SOL/USD", archived_versions=True)

    def test_orphan_resolution_refuses(self):
        fixture = self.fixture()
        with closing(sqlite3.connect(fixture.path)) as db, db:
            db.execute("INSERT INTO resolutions VALUES('missing',1,1,960,'{}')")
        with self.assertRaisesRegex(ValueError, "oracle_recorded_resolution_invalid"):
            ReadOnlyOracle(fixture.path, instrument="SOL/USD", archived_versions=True)

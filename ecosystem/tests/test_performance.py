from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from ecosystem import performance


class PerformanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.batch = "a" * 32
        self.directory = self.home / "batches" / self.batch
        self.directory.mkdir(parents=True)
        (self.home / "state.json").write_text(
            json.dumps({"batch_id": self.batch, "config": {"quote": "USD"}})
        )
        self.batch_db = self.directory / "batch.sqlite3"
        self.native = self.directory / "forward.sqlite3"
        with closing(sqlite3.connect(self.batch_db)) as db, db:
            db.executescript(
                "CREATE TABLE meta(key,value); CREATE TABLE cell(id,asset,interval,strategy,horizon,state,reason,selected,score); CREATE TABLE attempt(cell,job_id,state,result);"
            )
            db.executemany(
                "INSERT INTO meta VALUES(?,?)",
                [
                    (key, json.dumps(value))
                    for key, value in {
                        "id": self.batch,
                        "version": 1,
                        "code_id": "fixture",
                        "settings": {"capital": 1000.0},
                    }.items()
                ],
            )
            for n, asset in enumerate(("SOL", "BTC"), start=1):
                db.execute(
                    "INSERT INTO cell VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        n,
                        asset,
                        "1m",
                        "rsi",
                        "medium",
                        "completed",
                        "",
                        json.dumps({"name": "rsi", "params": {"period": 14}}),
                        0.25,
                    ),
                )
                db.execute(
                    "INSERT INTO attempt VALUES(?,?,?,?)",
                    (
                        n,
                        f"variant{n}",
                        "evaluated",
                        json.dumps({"params": {"period": 14}, "median_return": -0.02}),
                    ),
                )
        with closing(sqlite3.connect(self.native)) as db, db:
            db.executescript("""
                CREATE TABLE trial(id TEXT PRIMARY KEY,asset,label,minutes,execution);
                CREATE TABLE call(trial,bar,issued,start,finish,generation,guesses,prediction,outcome,expired,traded,net_return,fees_bps,borrow_bps,slippage_bps,liquidated);
            """)
            db.execute(
                "INSERT INTO trial VALUES(?,?,?,?,?)",
                (
                    "trial-sol",
                    "SOL",
                    f"f5:{self.batch}:rsi:1m:medium",
                    1,
                    '{"fee_schedule":"jupiter-perps"}',
                ),
            )

    def call(self, bar=100, *, ret=None, issued=None, finish=None, outcome=None):
        issued = bar + 0.25 if issued is None else issued
        finish = bar + 62 if finish is None else finish
        outcome = 1 if ret is not None and outcome is None else outcome
        with closing(sqlite3.connect(self.native)) as db, db:
            db.execute(
                "INSERT INTO call VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "trial-sol",
                    bar,
                    issued,
                    bar + 2,
                    finish,
                    0,
                    "[]",
                    1,
                    outcome,
                    0,
                    1,
                    ret,
                    5.0 if ret is not None else None,
                    2.0 if ret is not None else None,
                    1.0 if ret is not None else None,
                    0 if ret is not None else None,
                ),
            )

    def sol(self, now=1000):
        return performance.report(self.home, "rsi", now=now)["coins"][0]["forward"]

    def test_no_resolved_returns_are_unknown_not_break_even(self):
        self.call()
        first = self.sol(now=130)
        self.assertEqual(first["resolved"], 0)
        self.assertIsNone(first["realized_pnl_usd"])
        self.assertEqual(first["profit_assessment"], "unknown_no_resolved_economics")
        self.assertEqual(first["pending"], 1)

    def test_source_already_nets_costs_and_compounds_each_trial_only(self):
        self.call(ret=0.10)
        self.call(bar=200, ret=-0.05)
        result = performance.report(self.home, "rsi", now=500)
        measured = result["coins"][0]["forward"]
        self.assertAlmostEqual(measured["realized_pnl_usd"], 45.0)
        self.assertAlmostEqual(measured["realized_return_percent"], 4.5)
        self.assertEqual(measured["profit_assessment"], "profit_on_resolved_calls")
        self.assertAlmostEqual(measured["fees_bps"], 10.5)
        self.assertTrue(measured["costs_already_in_net_return"])
        self.assertIsNone(result["summary"]["portfolio_pnl_usd"])
        self.assertIsNone(result["coins"][1]["forward"]["realized_pnl_usd"])
        self.assertEqual(result["coins"][0]["backtest"]["median_return_percent"], -2)

    def test_negative_paper_pnl_and_restart_are_preserved(self):
        self.call(ret=-0.20)
        before = hashlib.sha256(self.native.read_bytes()).hexdigest()
        first = self.sol()
        again = self.sol()
        self.assertAlmostEqual(first["realized_pnl_usd"], -200)
        self.assertEqual(first, again)
        self.assertEqual(first["profit_assessment"], "loss_on_resolved_calls")
        self.assertEqual(before, hashlib.sha256(self.native.read_bytes()).hexdigest())
        with closing(sqlite3.connect(performance._path(self.home))) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM resolution").fetchone()[0], 1
            )
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM resolution")

    def test_disable_is_prospective_preserves_old_records_and_marks_gap_unknown(self):
        self.call(ret=0.10)
        self.sol(now=180)
        off = performance.set_recording(self.home, False, 0, now=200)
        self.assertEqual(off["revision"], 1)
        self.call(bar=220, ret=0.50)
        performance.set_recording(self.home, True, 1, now=300)
        self.call(bar=320, ret=-0.10)
        result = self.sol(now=500)
        self.assertEqual(
            (
                result["calls"],
                result["recorded"],
                result["excluded"],
                result["resolved"],
            ),
            (3, 2, 1, 2),
        )
        self.assertIsNone(result["realized_pnl_usd"])
        self.assertEqual(result["profit_assessment"], "unknown_unrecorded_periods")
        with closing(sqlite3.connect(performance._path(self.home))) as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM resolution").fetchone()[0], 2
            )
            self.assertEqual(db.execute("SELECT count(*) FROM policy").fetchone()[0], 3)

    def test_future_settlement_does_not_leak_into_report(self):
        self.call(ret=0.50)
        before = self.sol(now=130)
        self.assertIsNone(before["realized_pnl_usd"])
        after = self.sol(now=170)
        self.assertAlmostEqual(after["realized_pnl_usd"], 500)

    def test_mutated_native_economics_fail_closed_without_rewriting_projection(self):
        self.call(ret=0.10)
        self.sol()
        with closing(sqlite3.connect(self.native)) as db, db:
            db.execute("UPDATE call SET net_return=0.75")
        result = performance.report(self.home, now=1001)
        self.assertEqual(result["source"]["status"], "unavailable")
        self.assertIsNone(result["coins"][0]["forward"]["realized_pnl_usd"])
        with closing(sqlite3.connect(performance._path(self.home))) as db:
            stored = json.loads(db.execute("SELECT body FROM resolution").fetchone()[0])
            self.assertEqual(stored["net_return"], 0.10)

    def test_frozen_capital_changes_fail_closed(self):
        self.call(ret=0.10)
        self.sol()
        with closing(sqlite3.connect(self.batch_db)) as db, db:
            db.execute(
                "UPDATE meta SET value=? WHERE key='settings'",
                (json.dumps({"capital": 100_000}),),
            )
        self.assertIsNone(self.sol()["realized_pnl_usd"])

    def test_revision_guard_and_invalid_policy_cannot_replace_saved_choice(self):
        performance.set_recording(self.home, False, 0, now=200)
        with self.assertRaisesRegex(ValueError, "recording_revision_conflict"):
            performance.set_recording(self.home, True, 0, now=300)
        with self.assertRaises(ValueError):
            performance.set_recording(self.home, "yes", 1)
        self.assertFalse(performance.recording(self.home)["enabled"])

    def test_cursor_drains_bounded_pages_without_duplicate_records(self):
        for bar in (100, 200, 300):
            self.call(bar=bar, ret=0.01)
        with patch.object(performance, "PAGE", 1):
            self.assertTrue(performance.sync(self.home, now=1000)["has_more"])
            self.assertTrue(performance.sync(self.home, now=1000)["has_more"])
            self.assertFalse(performance.sync(self.home, now=1000)["has_more"])
        self.assertEqual(self.sol()["recorded"], 3)

    def test_quote_currency_is_not_assumed_to_be_usd(self):
        state = json.loads((self.home / "state.json").read_text())
        state["config"]["quote"] = "USDC"
        (self.home / "state.json").write_text(json.dumps(state))
        self.call(ret=0.10)
        result = self.sol()
        self.assertEqual(result["quote_currency"], "USDC")
        self.assertAlmostEqual(result["realized_pnl_reference"], 100)
        self.assertIsNone(result["realized_pnl_usd"])
        self.assertIsNone(result["paper_capital_usd"])
        self.assertEqual(result["realized_return_percent"], 10.000000000000009)

    def test_missing_native_economics_makes_whole_trial_profit_unknown(self):
        self.call(ret=0.10)
        self.call(bar=200, outcome=1)
        result = self.sol()
        self.assertEqual(result["missing_economics"], 1)
        self.assertIsNone(result["realized_pnl_usd"])
        self.assertEqual(result["profit_assessment"], "unknown_missing_economics")

    def test_invalid_source_can_recover_without_foreign_store_or_fake_profit(self):
        with closing(sqlite3.connect(self.native)) as db, db:
            db.execute("ALTER TABLE call RENAME TO unavailable_call")
        first = performance.report(self.home, now=1000)
        self.assertEqual(first["source"]["status"], "unavailable")
        with closing(sqlite3.connect(self.native)) as db, db:
            db.execute("ALTER TABLE unavailable_call RENAME TO call")
        self.call(ret=-0.10)
        self.assertAlmostEqual(self.sol()["realized_pnl_usd"], -100)

    def test_traversal_and_missing_source_are_unavailable_without_creating_source(self):
        with self.assertRaises(ValueError):
            performance.report(self.home, "../secrets")
        absent = self.home / "absent"
        result = performance.report(absent)
        self.assertEqual(result["status"], "unavailable")
        self.assertFalse(absent.exists())

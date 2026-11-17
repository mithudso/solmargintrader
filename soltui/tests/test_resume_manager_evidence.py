"""Maintenance regressions use isolated authority stores and synthetic receipts."""

from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from botmanager.blind import decide

from soltui import f5_batch, research_admission
from soltui.experiments import ExperimentError, ExperimentStore, compare_runs
from soltui.tests import test_learning_owner as learning_fixture
from soltui.tests import test_manager_evidence as evidence_fixture


class ManagerEvidenceResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.store = ExperimentStore(self.root / "authority")

    def test_trial_bounds_and_substituted_block_verdict_are_refused(self):
        run = self.store.manager_create(evidence_fixture.specification())["run_id"]
        with self.assertRaises(ExperimentError):
            self.store.manager_trial(run, "a" * 32, "train", 20)
        self.assertEqual(self.store.manager_status(run)["consumed_cells"], 0)
        self.store.manager_trial(run, "a" * 32, "train", 19)
        evidence = evidence_fixture.evidence()
        for candidate in evidence["packet"]["candidates"]:
            for cell in candidate["cells"]:
                cell["block"] += 10
                metrics = {
                    k: cell[k]
                    for k in (
                        "net_return",
                        "drawdown",
                        "turnover",
                        "trades",
                        "uncertainty",
                    )
                }
                result = json.dumps(
                    {
                        "status": "completed",
                        "report": {"metrics": metrics, "certified": True},
                    }
                )
                with self.store._connect() as db:
                    for stress in (0, 1):
                        db.execute(
                            "INSERT INTO manager_trials VALUES(?,?,?,?,?)",
                            (
                                run,
                                candidate["id"],
                                "train",
                                2 * cell["block"] + stress,
                                result,
                            ),
                        )
        evidence["verdict"] = decide(evidence["packet"])
        with self.assertRaisesRegex(ExperimentError, "chronological blocks"):
            self.store.manager_finalists(run, evidence)

    def test_import_replay_binds_exposure_and_historical_status(self):
        first = [{"coin": "SOL", "start": 1, "end": 10}]
        self.store.manager_import(
            "fixture", "one", "a" * 64, first, attempts=1, historical=True
        )
        self.store.manager_import(
            "fixture", "one", "a" * 64, first, attempts=1, historical=True
        )
        for intervals, historical in (
            ([], True),
            ([{"coin": "SOL", "start": 2, "end": 10}], True),
            (first, False),
        ):
            with (
                self.subTest(intervals=intervals, historical=historical),
                self.assertRaisesRegex(ExperimentError, "identity changed"),
            ):
                self.store.manager_import(
                    "fixture",
                    "one",
                    "a" * 64,
                    intervals,
                    attempts=1,
                    historical=historical,
                )
        with self.store._connect() as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM manager_exposures").fetchone()[0], 1
            )

    def test_list_limit_filters_before_decoding_specs(self):
        for i in range(15):
            self.store.create_run(
                {
                    "source": "native" if i % 2 else "tradingview",
                    "bot": "grid",
                    "candidates": [{"x": i}],
                }
            )
        original = self.store._run
        with patch.object(self.store, "_run", wraps=original) as decode:
            values = self.store.list_runs(source="native", bot="grid", limit=2)
        self.assertEqual(len(values), 2)
        self.assertEqual(decode.call_count, 2)
        self.assertTrue(all(v["spec"]["source"] == "native" for v in values))

    def test_failed_windows_cannot_replace_measured_coverage(self):
        meta = {
            k: "same"
            for k in ("bot", "interval", "currency", "strategy", "data_source")
        }
        meta.update(
            return_unit="fraction",
            drawdown_unit="fraction",
            fee_bps=1,
            slippage_bps=1,
            borrow_bps_per_day=0,
            fill_delay=1,
        )
        spec = {
            "source": "native",
            "bot": "grid",
            "provenance": meta,
            "candidates": [{}],
        }
        runs = [self.store.create_run(spec), self.store.create_run(spec)]
        for index, run in enumerate(runs):
            self.store.reserve_exploration(
                run, [{"coin": "SOL", "start": 0, "end": 20}]
            )
            for window in range(2):
                self.store.record_cell(
                    run,
                    "0",
                    str(window),
                    {
                        "coin": "SOL",
                        "split": "train",
                        "start": window * 10,
                        "end": window * 10 + 10,
                        "status": "completed" if index == window else "failed",
                        "metrics": {"total_return": 0.1} if index == window else {},
                        "error": None if index == window else "fixture failure",
                    },
                )
        self.assertFalse(compare_runs(self.store, *runs)["comparable"])
        self.assertTrue(compare_runs(self.store, runs[0], runs[0])["comparable"])

    def test_pending_f5_attempt_retains_series_exposure(self):
        root = self.root / "f5"
        directory = root / ("a" * 32)
        directory.mkdir(parents=True)
        csv = self.root / "SOL.csv"
        csv.write_text("timestamp\n100\n160\n")
        with closing(sqlite3.connect(directory / "batch.sqlite3")) as db, db:
            db.executescript(
                "CREATE TABLE meta(key TEXT,value TEXT);CREATE TABLE cell(id INTEGER,asset TEXT,interval TEXT,state TEXT);CREATE TABLE attempt(cell INTEGER,job_id TEXT,state TEXT,result TEXT);CREATE TABLE series(asset TEXT,interval TEXT,path TEXT,sha256 TEXT);"
            )
            db.execute("INSERT INTO meta VALUES(?,?)", ("phase", json.dumps("stopped")))
            db.execute("INSERT INTO cell VALUES(1,'SOL','1m','pending')")
            db.execute("INSERT INTO attempt VALUES(1,'job','completed','{}')")
            db.execute(
                "INSERT INTO series VALUES(?,?,?,?)",
                ("SOL", "1m", str(csv), hashlib.sha256(csv.read_bytes()).hexdigest()),
            )
        evidence = research_admission.inspect_history(root, "f5")
        self.assertEqual(evidence["coverage"], "verified", evidence)
        trial = next(r for r in evidence["records"] if r["id"].startswith("trial:"))
        self.assertEqual(
            trial["intervals"], [{"coin": "SOL", "start": 100.0, "end": 220.0}]
        )

    def test_reconciled_promotion_replay_preserves_rollback(self):
        fixture = learning_fixture.LearningOwnerTests(
            "test_owner_manager_publication_and_rollback_preserve_account"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        real = fixture.owner.reconcile
        receipts = []

        def capture(*args):
            result = real(*args)
            receipts.append(copy.deepcopy(args))
            return result

        with patch.object(fixture.owner, "reconcile", side_effect=capture):
            fixture.test_owner_manager_publication_and_rollback_preserve_account()
        with fixture.owner.connection() as db:
            before = [tuple(r) for r in db.execute("SELECT * FROM learned_defaults")]
        result = real(*receipts[0])
        self.assertEqual(result["state"], "rolled_back")
        with fixture.owner.connection() as db:
            self.assertEqual(
                [tuple(r) for r in db.execute("SELECT * FROM learned_defaults")], before
            )
        # Simulate a delayed first owner acknowledgement while preserving the
        # later accepted manager transition and immutable publication journals.
        with fixture.owner.connection(True) as db:
            db.execute(
                "UPDATE learning_requests SET manager_receipt=NULL WHERE request_id=?",
                (receipts[0][1],),
            )
        result = real(*receipts[0])
        self.assertEqual(result["state"], "rolled_back")
        with fixture.owner.connection() as db:
            self.assertEqual(
                [tuple(r) for r in db.execute("SELECT * FROM learned_defaults")], before
            )

    def test_signal_cache_refetches_rejected_delayed_publication(self):
        import numpy as np

        seconds = 86400
        now = 10 * seconds + 10

        def bars(last):
            ts = np.arange(last - 4 * seconds, last + seconds, seconds)
            price = np.ones(len(ts)) * 10
            return {
                "ts": ts,
                "open": price,
                "high": price + 1,
                "low": price - 1,
                "close": price,
                "volume": price,
            }

        stale = bars(8 * seconds)
        fresh = bars(9 * seconds)
        cache = {}
        with patch(
            "soltui.compound.fetch_closed_candles", side_effect=[stale, fresh]
        ) as fetch:
            with self.assertRaisesRegex(ValueError, "No current closed"):
                f5_batch._signal_response(
                    cache, "SOL", "1d", fetch, seconds=seconds, now=now
                )
            self.assertFalse(cache)
            self.assertIs(
                f5_batch._signal_response(
                    cache, "SOL", "1d", fetch, seconds=seconds, now=now
                ),
                fresh,
            )
            self.assertIs(
                f5_batch._signal_response(
                    cache, "SOL", "1d", fetch, seconds=seconds, now=now
                ),
                fresh,
            )
            self.assertEqual(fetch.call_count, 2)

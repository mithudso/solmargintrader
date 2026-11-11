"""Causal reference-paper accounting and exact study-policy continuation."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester.core.engine import run_backtest
from backtester.core.types import BarWindow
from backtester.core.zec_ensemble import build_ensemble, candidate_id
from ecosystem import votes
from ecosystem import zec_forward as z


def arrays(start, count, step):
    close = 100 + np.arange(count) * 0.1
    return {"ts": start + np.arange(count) * step, "open": close - 0.05,
            "high": close + 1, "low": close - 1, "close": close, "volume": close * 0 + 100}


class ZecForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "forward"
        self.now = 360_000
        self.seeds = {}
        self.source = {}
        selected = []
        for interval, step in z.INTERVALS.items():
            a = arrays(self.now - step * 120, 120, step)
            self.source[interval] = a
            path = self.root / f"ZEC_{interval}.csv"
            pd.DataFrame({"timestamp" if k == "ts" else k: v for k, v in a.items()}).to_csv(path, index=False)
            self.seeds[interval] = path
            for window in range(3, 8):
                config = {"schema_version": 1, "interval": interval, "mode": "single",
                          "members": [{"strategy": "ts_momentum", "params": {"window": window}}],
                          "persistence": 1, "rebalance_threshold": 0.1}
                policy = build_ensemble(config)
                policy.on_bar(BarWindow(a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], len(a["ts"]) - 1))
                selected.append({"candidate_id": candidate_id(config), "interval": interval, "config": config,
                                 "costs": {"fee_bps": 10, "slippage_bps": 2},
                                 "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                 "initial_state": policy.checkpoint_state()})
        self.selection = self.root / "top10.json"
        self.value = {"schema_version": 1, "study_id": "fixture-study", "selected": selected}
        self.selection.write_text(z.canonical(self.value))
        (self.root / "manifest.json").write_text(json.dumps({
            "study_id": "fixture-study", "top10_sha256": hashlib.sha256(self.selection.read_bytes()).hexdigest(),
            "fingerprint": {"code": {k: v for k, v in z.implementation().items() if k.startswith("backtester/core/")}}}))

    def initialize(self):
        with patch.object(z, "fetch_closed", return_value=None):
            return z.initialize(self.home, self.selection, self.seeds, now=self.now)

    def next(self, timestamp, now):
        seed = self.source["1m"]
        price = float(seed["close"][-1]) + ((timestamp - self.now) // 60 + 1) * .1
        a = {"ts": np.array([timestamp]), "open": np.array([price - .05]),
             "high": np.array([price + 1]), "low": np.array([price - 1]),
             "close": np.array([price]), "volume": np.array([100.0])}
        return z.tick(self.home, now=now, fetcher=lambda interval, *_: a if interval == "1m" else None)

    def test_exact_canonical_continuation_no_warmup_fills_and_next_open_only(self):
        start = self.initialize()
        self.assertEqual(len(start["accounts"]), 10)
        self.assertTrue(all(a["costs_paid"]["fees_paid"] == 0 for a in start["accounts"]))
        first = self.next(self.now, self.now + 61)["accounts"][0]
        self.assertEqual(first["status"], "waiting")
        decision = self.next(self.now + 60, self.now + 121)["accounts"][0]
        self.assertEqual(decision["target"], 1)
        self.assertEqual(decision["costs_paid"]["fees_paid"], 0)
        filled = self.next(self.now + 120, self.now + 181)["accounts"][0]
        self.assertGreater(filled["costs_paid"]["fees_paid"], 0)
        self.assertGreater(filled["costs_paid"]["slippage_paid"], 0)
        original = self.source["1m"]
        live = arrays(self.now, 3, 60)
        live = {k: v + (original["close"][-1] + .1 - 100) if k != "ts" and k != "volume" else v for k, v in live.items()}
        full = {k: np.concatenate((original[k], live[k])) for k in original}
        row = self.value["selected"][0]
        expected = run_backtest(z.ForwardStrategy(row["config"], self.now + 60, full), full, z.engine_config(row), close_at_end=False)
        self.assertAlmostEqual(filled["equity"], float(expected.equity[-1]), places=8)
        self.assertAlmostEqual(filled["costs_paid"]["fees_paid"], expected.account.fees_paid, places=8)
        # A new process can read the exact same state without refitting/reseeding.
        resumed = z.report(self.home, now=self.now + 181)["accounts"][0]
        self.assertEqual(resumed["config_hash"], filled["config_hash"])
        self.assertEqual(resumed["equity"], filled["equity"])

    def test_stateful_rsi_persistence_restarts_match_uninterrupted_engine(self):
        full = arrays(60_000, 180, 60)
        close = 100 + 5 * np.sin(np.arange(180) / 4)
        full.update(open=close - .05, high=close + 1, low=close - 1, close=close)
        config = {"schema_version": 1, "interval": "1m", "mode": "single",
                  "members": [{"strategy": "rsi", "params": {"period": 7, "oversold": 35, "exit_level": 60}}],
                  "persistence": 2, "rebalance_threshold": .1}
        row = {"config": config, "interval": "1m", "costs": {"fee_bps": 10, "slippage_bps": 2}}
        activation = int(full["ts"][120])
        expected = run_backtest(z.ForwardStrategy(config, activation, full), full,
                                z.engine_config(row), close_at_end=False)
        seed = {k: v[:120] for k, v in full.items()}
        policy = build_ensemble(config)
        policy.on_bar(BarWindow(seed["ts"], seed["open"], seed["high"], seed["low"], seed["close"], seed["volume"], 119))
        wrapper = z.ForwardStrategy(config, activation, seed)
        wrapper.inner.restore_state(policy.checkpoint_state())
        tail = {k: v[-(wrapper.warmup_bars() + 1):] for k, v in seed.items()}
        result = run_backtest(wrapper, tail, z.engine_config(row), close_at_end=False)
        for i in range(120, 180):
            history = {k: v[:i + 1] for k, v in full.items()}
            new = {k: v[i:i + 1] for k, v in full.items()}
            result = run_backtest(z.ForwardStrategy(config, activation, history), new,
                                  z.engine_config(row), close_at_end=False, continuation=result.continuation)
        self.assertAlmostEqual(float(expected.equity[-1]), float(result.equity[-1]), places=8)
        self.assertAlmostEqual(expected.account.fees_paid, result.account.fees_paid, places=8)
        self.assertAlmostEqual(expected.account.position.units, result.account.position.units, places=8)

    def test_gap_or_outage_never_backfills_prospective_decisions(self):
        self.initialize()
        self.next(self.now, self.now + 61)
        report = self.next(self.now + 120, self.now + 181)
        row = report["accounts"][0]
        self.assertEqual(row["status"], "blocked")
        self.assertEqual(row["reason"], "forward_source_gap")
        self.assertFalse(row["available"])
        self.home = self.root / "outage"
        self.initialize()
        self.next(self.now, self.now + 61)
        report = self.next(self.now + 60, self.now + 600)
        row = report["accounts"][0]
        self.assertEqual(row["reason"], "missed_forward_bars_review_required")
        self.assertEqual(row["decisions"], 0)
        self.assertEqual(row["costs_paid"]["fees_paid"], 0)

    def accounting_identity(self):
        with z.connection(self.home) as db:
            return {
                "candidates": [list(row) for row in db.execute("SELECT id,rank,interval,config,activation,seed,state,last_ts FROM candidates ORDER BY rank")],
                "forecasts": [list(row) for row in db.execute("SELECT * FROM forecasts ORDER BY id,bar")],
                "candles": [list(row) for row in db.execute("SELECT * FROM candles ORDER BY interval,bar")],
            }

    def test_successful_empty_poll_clears_only_transient_health_before_and_after_activation(self):
        def unavailable(*_):
            raise OSError("temporary fixture failure")
        self.initialize()
        baseline = self.accounting_identity()
        failed = z.tick(self.home, now=self.now + 1, fetcher=unavailable)
        self.assertEqual(failed["accounts"][0]["reason"], "feed_unavailable")
        recovered = z.tick(self.home, now=self.now + 2, fetcher=lambda *_: None)
        self.assertEqual(recovered["accounts"][0]["status"], "waiting")
        self.assertEqual(recovered["accounts"][0]["reason"], "first_post_start_closed_bar")
        self.assertFalse(recovered["accounts"][0]["available"])
        self.assertEqual(self.accounting_identity(), baseline)
        self.next(self.now, self.now + 61)
        self.next(self.now + 60, self.now + 121)
        baseline = self.accounting_identity()
        for reason in ("feed_unavailable", "closed_candle_stale"):
            with self.subTest(reason=reason):
                with z.connection(self.home, write=True) as db:
                    db.execute("UPDATE candidates SET status='blocked',reason=?", (reason,))
                recovered = z.tick(self.home, now=self.now + 122, fetcher=lambda *_: None)
                row = recovered["accounts"][0]
                self.assertEqual(row["status"], "running")
                self.assertIsNone(row["reason"])
                self.assertTrue(row["available"])
                self.assertEqual(row["target"], 1)
                self.assertEqual(self.accounting_identity(), baseline)

    def test_successful_poll_never_clears_or_advances_review_blocks(self):
        self.initialize()
        self.next(self.now, self.now + 61)
        baseline = self.accounting_identity()
        for reason in ("forward_source_gap", "missed_forward_bars_review_required"):
            with self.subTest(reason=reason):
                with z.connection(self.home, write=True) as db:
                    db.execute("UPDATE candidates SET status='blocked',reason=?", (reason,))
                recovered = z.tick(self.home, now=self.now + 62, fetcher=lambda *_: None)
                self.assertEqual(recovered["accounts"][0]["reason"], reason)
                self.assertEqual(recovered["accounts"][0]["status"], "blocked")
                self.assertEqual(self.accounting_identity(), baseline)
                self.next(self.now + 60, self.now + 121)
                self.assertEqual(self.accounting_identity(), baseline)

    def test_configuration_and_seed_hash_are_bound(self):
        self.value["selected"][0]["config"]["persistence"] = 2
        self.selection.write_text(z.canonical(self.value))
        with self.assertRaisesRegex(ValueError, "configuration_changed"):
            self.initialize()
        self.assertFalse(self.home.exists())

    def test_readonly_projection_is_exact_pair_stale_fails_closed(self):
        self.initialize()
        ui = self.root / "ui"
        z.publish(self.home, ui)
        sol = votes.report(ui, "SOL/USD", now=self.now)
        self.assertEqual(sol["instrument"], "SOL/USD")
        self.assertFalse(sol["selected_experiment"]["selected"])
        zec = votes.report(ui, "ZEC/USDT", now=self.now)
        self.assertEqual(zec["percentage_semantics"], "target_exposure_not_probability")
        self.assertFalse(zec["tradable"])
        self.assertIsNone(zec["signal"])
        self.next(self.now, self.now + 61)
        warming = votes.report(ui, "ZEC/USDT", now=self.now + 61)
        self.assertEqual(warming["graph"]["ticks"], [])
        self.next(self.now + 60, self.now + 121)
        current = votes.report(ui, "ZEC/USDT", now=self.now + 121)
        self.assertEqual(len(current["graph"]["ticks"]), 1)
        self.assertEqual(current["signal"], "Long")
        stale = votes.report(ui, "ZEC/USDT", now=self.now + 161)
        self.assertIsNone(stale["signal"])
        self.assertEqual(stale["status"], "unavailable")
        self.assertEqual(len(current["selected_experiment"]["accounts"]), 10)

    def test_changed_policy_implementation_cannot_resume_or_publish_signal(self):
        self.initialize()
        self.next(self.now, self.now + 61)
        self.next(self.now + 60, self.now + 121)
        with patch.object(z, "implementation", return_value={"changed": "hash"}):
            current = z.tick(self.home, now=self.now + 122, fetcher=lambda *_: self.fail("must refuse before network"))
            self.assertEqual(current["accounts"][0]["reason"], "study_implementation_changed")
            self.assertFalse(current["accounts"][0]["available"])

    def test_failed_atomic_publication_leaves_retryable_absent_store(self):
        with patch.object(z, "_publish_database", side_effect=OSError("interrupted")), self.assertRaises(OSError):
            self.initialize()
        self.assertFalse(z._path(self.home).exists())
        self.assertEqual(len(self.initialize()["accounts"]), 10)

    def test_foreign_database_is_preserved(self):
        self.home.mkdir()
        path = z._path(self.home)
        path.write_bytes(b"foreign data")
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, "incompatible_study_store"):
            self.initialize()
        self.assertEqual(before, path.read_bytes())

    def test_foreign_read_does_not_create_store(self):
        with self.assertRaisesRegex(ValueError, "not_initialized"):
            z.report(self.home)
        self.assertFalse(self.home.exists())

"""Offline paper accounting and fail-closed control boundary tests."""

import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from unittest.mock import patch

from oracle_leverage import autotrade
from oracle_leverage import autotrade_engine as engine
from oracle_leverage.autotrade_advice import Advice, AsyncAdvice
from oracle_leverage.autotrade_worker import Session


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.plan = engine.make_plan(at=100, price=100, direction="long", collateral=10)
        self.position = engine.open_position(self.plan, 100)

    def test_frozen_plan_and_liquidation_during_close(self):
        self.plan["liquidation_price"] = 1
        self.assertNotEqual(self.plan, self.position["plan"])
        p = self.position
        for t in range(101, 116):
            p = engine.step(p, at=t, price=106)
        self.assertEqual(p["state"], "closing")
        p = engine.step(p, at=116, price=p["plan"]["liquidation_price"])
        self.assertEqual((p["state"], p["outcome"]), ("liquidated", "failure"))

    def test_costs_close_lag_and_distinct_prices(self):
        p = self.position
        for t in range(101, 116):
            p = engine.step(p, at=t, price=106)
        for t in range(116, 126):
            p = engine.step(p, at=t, price=105)
        self.assertEqual(p["state"], "closed")
        self.assertEqual(p["trigger_price"], 106)
        self.assertLess(p["exit_price"], 105)
        self.assertGreater(p["fees_usd"], 0)
        self.assertGreater(p["borrow_usd"], 0)
        self.assertLess(p["net_pnl_usd"], p["gross_pnl_usd"])

    def test_close_slippage_liquidation_and_worst_loss_reserve(self):
        for leverage in (10, 1000):
            for direction in ("long", "short"):
                plan = engine.make_plan(
                    at=1000,
                    price=100,
                    direction=direction,
                    collateral=10,
                    leverage=leverage,
                )
                sign = 1 if direction == "long" else -1

                def close_at(observed, plan=plan):
                    p = engine.open_position(plan, 1000)
                    for t in range(1001, 1025):
                        p = engine.step(p, at=t, price=100, stop=t == 1001)
                    return engine.step(p, at=1025, price=observed)

                crossing = plan["liquidation_price"] + sign * 0.000001
                liquidated = close_at(crossing)
                self.assertEqual(liquidated["outcome"], "failure")
                self.assertGreaterEqual(
                    liquidated["net_pnl_usd"], -engine.worst_loss(10, leverage)
                )
                safely_above = (plan["liquidation_price"] + sign * 0.00001) / (
                    1 - sign * plan["slippage_rate"]
                )
                closed = close_at(safely_above)
                self.assertEqual(closed["state"], "closed")
                self.assertGreaterEqual(
                    closed["net_pnl_usd"], -engine.worst_loss(10, leverage)
                )
                self.assertGreater(closed["fees_usd"], 0)
                self.assertGreater(closed["borrow_usd"], 0)

    def test_gap_out_of_order_and_wrong_basis_are_unknown(self):
        for kwargs in (
            {"at": 103, "price": 100},
            {"at": 100, "price": 100},
            {"at": 101, "price": 100, "basis": "coinbase"},
        ):
            self.assertEqual(engine.step(self.position, **kwargs)["state"], "unknown")


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": self.tmp.name})
        self.env.start()
        self.db = autotrade._connect()
        self.now = 100.0
        self.session = Session(self.db, lambda: self.now)

    def tearDown(self):
        self.db.close()
        self.env.stop()
        self.tmp.cleanup()

    def tick(self, at, price=100):
        if (
            self.session.s.get("state") == "running"
            and self.session.s.get("first_entry_at") is None
            and self.session.s.get("warmup_samples") == 0
            and at - 0.001 >= self.session.s["started_at"]
        ):
            self.now = at - 0.001
            self.session.tick(
                {
                    "asset": "BTC",
                    "feed_id": 1,
                    "quote_currency": "USD",
                    "received_at": self.now,
                    "exchange_at": self.now,
                    "price": price,
                }
            )
        self.now = at
        self.session.tick(
            {
                "asset": "BTC",
                "feed_id": 1,
                "quote_currency": "USD",
                "received_at": at,
                "exchange_at": at,
                "price": price,
            }
        )

    def test_paper_start_entry_and_outcome(self):
        result = self.session.request("start-1", "start", {"mode": "paper"})
        self.assertTrue(result["accepted"])
        self.tick(101)
        self.assertEqual(self.session.s["entries"], 1)
        self.assertLess(
            self.session.s["first_entry_at"], result["first_entry_deadline"]
        )
        for at in range(102, 117):
            self.tick(at, 106)
        for at in range(117, 127):
            self.tick(at, 105)
        events = self.db.execute(
            "SELECT kind FROM events WHERE kind='position_outcome'"
        ).fetchall()
        self.assertEqual(len(events), 1)
        self.assertGreater(self.session.s["net_pnl_usd"], 0)

    def test_deadline_and_gap_fail_visible(self):
        self.session.request("start-1", "start", {})
        self.now = 1001
        self.session.timer()
        self.assertEqual(self.session.s["state"], "failed")
        self.assertIn("deadline", self.session.s["reason"])
        self.session.request("start-2", "start", {})
        self.tick(1002)
        self.now = 1005
        self.session.timer()
        self.assertEqual(self.session.s["position"]["outcome"], "unknown")
        self.assertEqual(self.session.s["state"], "blocked")

    def test_learning_is_prospective_and_records_liquidation(self):
        self.session.request("start-1", "start", {})
        self.tick(101)
        issued = dict(self.session.s["forecast"])
        self.assertEqual(issued["samples"], 0)
        self.tick(102, self.session.s["position"]["plan"]["liquidation_price"])
        self.assertEqual(self.session.s["learner"]["samples"], 1)
        self.assertEqual(self.session.s["learner"]["losses"], 1)
        self.assertEqual(self.session.s["learner"]["liquidations"], 1)
        self.assertEqual(issued["samples"], 0)
        self.assertLess(self.session.s["learner"]["net_pnl_usd"], 0)

    def test_causal_downward_ticks_produce_short_on_next_entry(self):
        self.session.request("start-1", "start", {})
        self.session.learner["net_pnl_usd"] = 20
        self.tick(101)
        self.tick(102, self.session.s["position"]["plan"]["liquidation_price"])
        # Wait through cooldown; all observations are chronological.
        for at in range(103, 133):
            self.tick(at, 90 - (at - 102) * 0.01)
        self.assertEqual(self.session.s["position"]["plan"]["direction"], "short")
        self.assertFalse(self.session.s["forecast"]["forced"])

    def test_failed_commit_restores_memory_and_sqlite(self):
        class FailCommit:
            def __init__(self, db):
                self.db = db

            def __getattr__(self, name):
                return getattr(self.db, name)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.db.rollback()
                raise sqlite3.OperationalError("injected commit failure")

        self.session.db = FailCommit(self.db)
        with self.assertRaises(sqlite3.OperationalError):
            self.session.request("bad-start", "start", {})
        self.assertEqual(self.session.s["state"], "stopped")
        self.assertIsNone(self.db.execute("SELECT value FROM session").fetchone())
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM requests").fetchone()[0], 0
        )

    def test_startup_failure_private_receipt(self):
        with (
            patch(
                "subprocess.Popen", side_effect=OSError("secret provider diagnostic")
            ),
            self.assertRaisesRegex(RuntimeError, "private receipt"),
        ):
            autotrade.configure("explicit-startup-failure", {})
        path = os.path.join(self.tmp.name, "owner-start-error.json")
        with open(path) as stream:
            receipt = stream.read()
        self.assertNotIn("secret", receipt)
        self.assertEqual(os.stat(path).st_mode & 0o077, 0)

    def test_1000x_paper_model_minimum_hold_and_touch(self):
        for direction in ("long", "short"):
            plan = engine.make_plan(
                at=100, price=100, direction=direction, collateral=10, leverage=1000
            )
            self.assertEqual(plan["model_version"], "exit50-proxy-v1")
            p = engine.open_position(plan, 100)
            p = engine.step(p, at=101, price=100, stop=True)
            self.assertEqual(p["submit_at"], 115)
            self.assertEqual(p["close_at"], 125)
            p = engine.step(p, at=102, price=plan["liquidation_price"])
            self.assertEqual((p["state"], p["outcome"]), ("liquidated", "failure"))

    def test_1000_target_net_and_delayed_close(self):
        for direction in ("long", "short"):
            plan = engine.make_plan(
                at=100, price=100, direction=direction, collateral=10, leverage=1000
            )
            p = engine.open_position(plan, 100)
            for at in range(101, 126):
                p = engine.step(p, at=at, price=plan["target_price"])
            self.assertEqual(p["state"], "closed")
            self.assertGreaterEqual(p["net_pnl_usd"], 5)
            self.assertEqual(p["submit_at"], 115)
            self.assertEqual(p["close_at"], 125)
            self.assertIn("excludes network/keeper", plan["cost_scope"])

    def test_side_cohort_isolation_and_restart_retention(self):
        from oracle_leverage.autotrade_worker import boost_eligible

        self.session.request("start-a", "start", {})
        original = self.session.learner_asset
        self.session.learner.update(
            samples=100,
            wins=90,
            net_pnl_usd=100,
            brier_sum=10,
            high_n=40,
            high_wins=35,
            high_score_sum=35,
            sides={
                "long": {
                    "samples": 100,
                    "wins": 90,
                    "net_pnl_usd": 100,
                    "brier_sum": 10,
                    "high_n": 40,
                    "high_wins": 35,
                    "high_score_sum": 35,
                }
            },
        )
        self.session.s.update(net_pnl_usd=20, peak_net_usd=20)
        self.assertTrue(
            boost_eligible(self.session.learner, 0.9, self.session.s, "long")
        )
        self.assertFalse(
            boost_eligible(self.session.learner, 0.9, self.session.s, "short")
        )
        with self.db:
            self.session._save_learner()
        self.session.request("stop-a", "stop", None)
        self.session.request("start-b", "start", {"venue": "jupiter-sdk-1000x"})
        self.assertNotEqual(self.session.learner_asset, original)
        self.assertEqual(self.session.learner["samples"], 0)
        self.session.request("stop-b", "stop", None)
        self.session.request("start-c", "start", {"venue": "jupiter-cli-10x"})
        self.assertEqual(self.session.learner["samples"], 100)
        self.assertEqual(self.session.s["history"]["net_pnl_usd"], 100)

    def test_pre_start_exchange_time_ignored_and_warmup_chooses_direction(self):
        self.now = 1000.5
        self.session.request("start-1", "start", {})
        self.now = 1000.6
        self.session.tick(
            {
                "asset": "BTC",
                "feed_id": 1,
                "quote_currency": "USD",
                "received_at": 1000.6,
                "exchange_at": 1000.2,
                "price": 100,
            }
        )
        self.assertEqual(self.session.s["warmup_samples"], 0)
        self.now = 1000.7
        self.session.tick(
            {
                "asset": "BTC",
                "feed_id": 1,
                "quote_currency": "USD",
                "received_at": 1000.7,
                "exchange_at": 1000.7,
                "price": 100,
            }
        )
        self.assertIsNone(self.session.s["position"])
        self.now = 1000.8
        self.session.tick(
            {
                "asset": "BTC",
                "feed_id": 1,
                "quote_currency": "USD",
                "received_at": 1000.8,
                "exchange_at": 1000.8,
                "price": 99.9,
            }
        )
        self.assertEqual(self.session.s["position"]["plan"]["direction"], "short")
        self.assertFalse(self.session.s["forecast"]["forced"])

    def test_quantum_rejected_before_acceptance_and_session_remains_usable(self):
        for venue in ("jupiter-cli-10x", "jupiter-sdk-1000x"):
            with self.assertRaisesRegex(ValueError, "six decimals"):
                self.session.request(
                    "invalid-" + venue,
                    "start",
                    {"venue": venue, "base_collateral_usd": 0.0000001},
                )
        self.assertEqual(self.session.s["state"], "stopped")
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM requests").fetchone()[0], 0
        )
        self.assertTrue(
            self.session.request("valid", "start", {"base_collateral_usd": 0.000001})[
                "accepted"
            ]
        )
        self.tick(101)
        self.assertEqual(self.session.s["position"]["plan"]["collateral_usd"], 0.000001)

    def test_model_exception_is_journaled_and_owner_state_remains_usable(self):
        self.session.request("start-1", "start", {})
        self.tick(101)
        with patch(
            "oracle_leverage.autotrade_worker.engine.step",
            side_effect=ValueError("private detail"),
        ):
            self.now = 102
            self.session.handle_tick(
                {
                    "asset": "BTC",
                    "feed_id": 1,
                    "quote_currency": "USD",
                    "received_at": 102,
                    "exchange_at": 102,
                    "price": 100,
                }
            )
        self.assertEqual(self.session.s["state"], "blocked")
        self.assertEqual(self.session.s["position"]["outcome"], "unknown")
        self.assertNotIn("private detail", self.session.s["reason"])
        self.assertEqual(
            self.session.request("ack", "stop", {"acknowledge_unknown": True})["state"],
            "stopped",
        )

    def test_post_start_quote_required(self):
        self.now = 1000.5
        self.session.request("start-new", "start", {})
        self.now = 1000.6
        self.session.tick(
            {
                "asset": "BTC",
                "feed_id": 1,
                "quote_currency": "USD",
                "received_at": 1000.25,
                "exchange_at": 1000.25,
                "price": 100,
            }
        )
        self.assertIsNone(self.session.s["position"])
        self.tick(1001, 100)
        self.assertGreaterEqual(self.session.s["first_entry_at"], 1000.5)

    def test_unknown_requires_explicit_ack_and_loss_history_persists(self):
        self.session.request("start-1", "start", {})
        self.tick(101)
        self.session.error("feed gap")
        with self.assertRaisesRegex(ValueError, "acknowledge_unknown"):
            self.session.request("stop-1", "stop", {"acknowledge_unknown": False})
        self.session.request("stop-2", "stop", {"acknowledge_unknown": True})
        self.assertEqual(self.session.s["state"], "stopped")
        self.assertEqual(self.session.s["position"]["outcome"], "unknown")
        self.session.request("start-2", "start", {})
        self.assertEqual(self.session.learner["availability_failures"], 1)
        self.assertGreater(
            self.db.execute(
                "SELECT count(*) FROM events WHERE kind='feed_failure'"
            ).fetchone()[0],
            0,
        )

    def test_private_projection_and_canonical_replay(self):
        self.session.request("start-1", "start", {})
        self.tick(101)
        response = self.session.request(
            "stop-1", "stop", {"acknowledge_unknown": False}
        )
        self.assertNotIn("weights", response["learner"])
        self.assertNotIn("features", response["forecast"])
        self.assertNotIn("features", response["position"]["forecast"])
        replay = self.session.request("stop-1", "stop", {"acknowledge_unknown": False})
        self.assertTrue(replay["replayed"])
        self.assertNotIn("weights", replay["learner"])
        self.assertNotIn("features", replay["forecast"])

    def test_1000_and_10x_never_share_learning(self):
        self.session.request("start-1", "start", {})
        original = self.session.learner_asset
        self.session.request("stop-1", "stop", None)
        self.session.request("start-2", "start", {"venue": "jupiter-sdk-1000x"})
        self.assertNotEqual(original, self.session.learner_asset)
        self.tick(101)
        self.assertEqual(self.session.s["position"]["plan"]["leverage"], 1000)

    def test_zec_uses_its_own_feed_and_learner_partition(self):
        self.session.request("start-zec", "start", {"asset": "ZEC"})
        self.now = 101
        self.session.tick(
            {
                "asset": "ZEC",
                "feed_id": 66,
                "quote_currency": "USD",
                "received_at": 101,
                "exchange_at": 101,
                "price": 25,
            }
        )
        self.now = 101.1
        self.session.tick(
            {
                "asset": "ZEC",
                "feed_id": 66,
                "quote_currency": "USD",
                "received_at": 101.1,
                "exchange_at": 101.1,
                "price": 25,
            }
        )
        self.assertEqual(self.session.s["position"]["plan"]["asset"], "ZEC")
        self.assertEqual(self.session.learner_asset, self.session.s["cohort_id"])
        self.assertEqual(self.session.s["entries"], 1)

    def test_boost_requires_high_score_reliability_and_explicit_cap(self):
        from oracle_leverage.autotrade_worker import boost_eligible

        self.session.request("start-1", "start", {"max_collateral_usd": 12})
        self.session.learner.update(
            samples=100,
            wins=90,
            losses=10,
            net_pnl_usd=100,
            brier_sum=10,
            high_n=29,
            high_wins=25,
            high_score_sum=25,
            weights=[2.0, 0.0, 0.0],
            sides={
                "long": {
                    "samples": 100,
                    "wins": 90,
                    "net_pnl_usd": 100,
                    "brier_sum": 10,
                    "high_n": 40,
                    "high_wins": 35,
                    "high_score_sum": 35,
                }
            },
        )
        self.session.s.update(net_pnl_usd=20, peak_net_usd=20)
        self.assertFalse(
            boost_eligible(self.session.learner, 0.9, self.session.s, "long")
        )
        self.session.learner.update(high_n=40, high_wins=35, high_score_sum=35)
        self.assertTrue(
            boost_eligible(self.session.learner, 0.9, self.session.s, "long")
        )
        self.tick(101)
        self.assertFalse(self.session.s["forecast"]["boost_eligible"])
        self.assertEqual(self.session.s["position"]["plan"]["collateral_usd"], 10)
        self.session.learner["availability_failures"] = 1
        self.assertFalse(
            boost_eligible(self.session.learner, 0.9, self.session.s, "long")
        )

    def test_forecast_identity_freshness_and_advisory_direction(self):
        self.now = 120
        f = {
            "forecast_id": "forecast-1",
            "asset": "BTC",
            "horizon_seconds": 600,
            "source_basis": "jupiter-pyth:1",
            "market_address": "BXQQo2VTJV2upjdA6qFMGBY3uMyTMnRmaZjPCB5ZVmr7",
            "kind": "oracle-ohlc",
            "stream": "fixed_rate@200ms",
            "model_version": "projected-logit-l2-v1",
            "target_type": "closed-price-up-vs-nonup-v1",
            "cutoff_at": 120,
            "target_at": 720,
            "issued_at": 120,
            "reference_price": 100,
            "p_up": 0.2,
            "sample_count": 20,
            "mode": "active",
        }
        self.session.request("forecast-1", "forecast", f)
        self.session.request("start-1", "start", {})
        self.tick(121)
        self.assertEqual(self.session.s["position"]["plan"]["direction"], "short")
        self.assertEqual(self.session.s["forecast"]["source"], "Chrome Oracle advisory")
        changed = dict(f, p_up=0.8)
        with self.assertRaisesRegex(ValueError, "Forecast ID reused"):
            self.session.request("forecast-2", "forecast", changed)
        self.now = 152
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.session.request("forecast-3", "forecast", dict(f, forecast_id="new"))

    def test_boost_rounds_down_to_usdc_quantum_and_cap(self):
        self.session.request(
            "start-q",
            "start",
            {"base_collateral_usd": 10.000001, "max_collateral_usd": 15.000001},
        )
        self.session.learner.update(
            samples=100,
            wins=90,
            losses=10,
            net_pnl_usd=100,
            brier_sum=10,
            high_n=40,
            high_wins=35,
            high_score_sum=35,
            weights=[2.0, 0.0, 0.0],
            sides={
                "long": {
                    "samples": 100,
                    "wins": 90,
                    "net_pnl_usd": 100,
                    "brier_sum": 10,
                    "high_n": 40,
                    "high_wins": 35,
                    "high_score_sum": 35,
                }
            },
        )
        self.session.s.update(net_pnl_usd=20, peak_net_usd=20)
        self.tick(101)
        self.assertTrue(self.session.s["forecast"]["boost_eligible"])
        self.assertEqual(
            self.session.s["position"]["plan"]["collateral_usd"], 15.000001
        )
        self.assertLessEqual(
            self.session.s["position"]["plan"]["collateral_usd"], 15.000001
        )

    def test_paper_boost_is_bounded_and_downgrades(self):
        self.session.request("start-1", "start", {"max_session_loss_usd": 50})
        self.session.learner.update(
            samples=100,
            wins=90,
            losses=10,
            net_pnl_usd=100,
            brier_sum=10,
            high_n=40,
            high_wins=35,
            high_score_sum=35,
            weights=[2.0, 0.0, 0.0],
            sides={
                "long": {
                    "samples": 100,
                    "wins": 90,
                    "net_pnl_usd": 100,
                    "brier_sum": 10,
                    "high_n": 40,
                    "high_wins": 35,
                    "high_score_sum": 35,
                }
            },
        )
        self.session.s.update(net_pnl_usd=20, peak_net_usd=20)
        self.tick(101)
        self.assertTrue(self.session.s["forecast"]["boost_eligible"])
        self.assertEqual(self.session.s["position"]["plan"]["collateral_usd"], 15)
        self.assertFalse(
            __import__(
                "oracle_leverage.autotrade_worker", fromlist=["boost_eligible"]
            ).boost_eligible(
                self.session.learner, 0.9, dict(self.session.s, loss_streak=3), "long"
            )
        )

    def test_stop_keeps_close_at_risk_and_loss_stops_new_entries(self):
        self.session.request("start-1", "start", {"max_session_loss_usd": 10.2})
        self.tick(101)
        self.session.request("stop-1", "stop", None)
        self.assertEqual(self.session.s["state"], "stopping")
        self.tick(102)
        self.assertEqual(self.session.s["position"]["state"], "closing")
        self.tick(103, self.session.s["position"]["plan"]["liquidation_price"])
        self.assertEqual(self.session.s["state"], "stopped")
        self.assertEqual(self.session.s["learner"]["liquidations"], 1)

    def test_session_loss_budget_blocks_further_entry(self):
        self.session.request("start-1", "start", {"max_session_loss_usd": 10.2})
        self.tick(101)
        self.tick(102, self.session.s["position"]["plan"]["liquidation_price"])
        for at in range(103, 133):
            self.tick(at, 90)
        self.assertEqual(self.session.s["state"], "blocked")
        self.assertIn("not overall profitable", self.session.s["reason"])
        self.assertEqual(self.session.s["entries"], 1)

    def test_idempotency_restart_and_1000x_refusal(self):
        first = self.session.request("start-1", "start", {})
        replay = self.session.request("start-1", "start", {})
        self.assertTrue(replay["replayed"])
        self.assertEqual(first["session_id"], replay["original_session_id"])
        with self.assertRaises(ValueError):
            self.session.request("start-1", "start", {"mode": "live"})
        self.tick(101)
        recovered = Session(self.db, lambda: 102)
        self.assertEqual(recovered.s["position"]["outcome"], "unknown")
        self.assertEqual(recovered.s["state"], "blocked")
        replay_after_restart = recovered.request("start-1", "start", {})
        self.assertTrue(replay_after_restart["replayed"])
        self.assertEqual(replay_after_restart["state"], "blocked")
        with self.assertRaisesRegex(ValueError, "queue and payout"):
            recovered.request(
                "1000x", "start", {"venue": "jupiter-sdk-1000x", "mode": "live"}
            )
        self.assertEqual(
            os.stat(os.path.join(self.tmp.name, "journal.sqlite3")).st_mode & 0o077, 0
        )

    def test_config_rejects_secret_fields(self):
        with self.assertRaises(ValueError):
            self.session.request("config-1", "configure", {"api_key": "secret"})
        self.assertNotIn(
            "secret", repr(self.db.execute("SELECT * FROM events").fetchall())
        )


class AdviceTests(unittest.TestCase):
    def test_async_advice_never_waits_for_provider(self):
        import threading

        gate = threading.Event()

        class SlowAdvisor:
            enabled = True
            remaining = 1

            def ask(self, facts):
                gate.wait(1)
                self.remaining -= 1
                return {"status": "advisory", "direction": "short"}

        advisor = AsyncAdvice(SlowAdvisor())
        before = time.monotonic()
        advisor.offer({"price": 100, "momentum": 0}, 100)
        self.assertLess(time.monotonic() - before, 0.2)
        self.assertIsNone(advisor.poll())
        gate.set()
        deadline = time.monotonic() + 1
        result = None
        while result is None and time.monotonic() < deadline:
            result = advisor.poll()
            time.sleep(0.01)
        self.assertEqual(result["result"]["direction"], "short")

    def test_advice_is_bounded_and_does_not_return_key_or_raw_content(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def read(self, size):
                return json.dumps(
                    {
                        "content": [
                            {"type": "text", "text": json.dumps({"direction": "short"})}
                        ]
                    }
                ).encode()

        class Opener:
            def open(self, request, timeout):
                self.timeout = timeout
                return Response()

        opener = Opener()
        advice = Advice(
            enabled=True,
            max_calls=1,
            opener=opener,
            environ={"ANTHROPIC_API_KEY": "private-test-key"},
        )
        result = advice.ask({"price": 100, "momentum": -0.01})
        self.assertEqual(result, {"status": "advisory", "direction": "short"})
        self.assertNotIn("private-test-key", repr(result))
        self.assertEqual(opener.timeout, 3)
        self.assertEqual(
            advice.ask({"price": 100, "momentum": 0})["status"], "unavailable"
        )
        self.assertEqual(
            Advice().ask({"price": 100, "momentum": 0})["status"], "unavailable"
        )


class OwnerProcessTests(unittest.TestCase):
    def test_slow_cleanup_keeps_ipc_responsive_and_fences_generation(self):
        script = """
import os, queue, time
import oracle_leverage.autotrade_worker as worker
count=0
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self):
        global count
        count+=1; self.id=count; self.events=queue.Queue(); self.thread=Thread()
    def start(self):
        with open(os.environ['MARKER'],'a') as f: f.write('start%d\\n' % self.id)
    def close(self):
        self.events.put(('error','late-old-event'))
        time.sleep(.6)
        with open(os.environ['MARKER'],'a') as f: f.write('close%d\\n' % self.id)
class Advisor:
    def __init__(self, advisor): pass
    def offer(self, *args): pass
    def poll(self): return None
    def close(self): time.sleep(.6)
worker.ExecutionFeed=Feed; worker.AsyncAdvice=Advisor
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "marker")
            env = dict(
                os.environ, ORACLE_AUTOTRADE_HOME=tmp, MARKER=marker, INDEX_NO_AUTO="1"
            )
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    first = autotrade.start("start-a", {})
                    self.assertTrue(first["accepted"])
                    self.assertEqual(autotrade.stop("stop-a")["state"], "stopped")
                    before = time.monotonic()
                    status = autotrade.status()
                    self.assertLess(time.monotonic() - before, 0.5)
                    self.assertEqual(status["cleanup"], "in_progress")
                    before = time.monotonic()
                    with self.assertRaisesRegex(ValueError, "cleanup"):
                        autotrade.start("start-b", {})
                    self.assertLess(time.monotonic() - before, 0.5)
                    replay = autotrade.start("start-a", {})
                    self.assertTrue(replay["replayed"])
                    self.assertEqual(replay["state"], "stopped")
                    deadline = time.monotonic() + 4
                    while (
                        autotrade.status().get("cleanup") != "idle"
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.02)
                    second = autotrade.start("start-b", {})
                    self.assertTrue(second["accepted"])
                    self.assertNotEqual(first["session_id"], second["session_id"])
                    replay = autotrade.start("start-b", {})
                    self.assertTrue(replay["replayed"])
                    self.assertEqual(autotrade.status()["state"], "running")
                    with open(marker) as stream:
                        rows = stream.read().splitlines()
                    self.assertEqual(rows, ["start1", "close1", "start2"])
                    self.assertEqual(autotrade.stop("stop-b")["state"], "stopped")
                    before = time.monotonic()
                    owner.terminate()
                    owner.wait(timeout=1)
                    self.assertLess(time.monotonic() - before, 1)
            finally:
                if owner.poll() is None:
                    owner.terminate()
                    owner.wait(timeout=5)

    def test_failed_cleanup_fences_new_start_without_blocking_status(self):
        script = """
import queue
import oracle_leverage.autotrade_worker as worker
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self): self.events=queue.Queue(); self.thread=Thread()
    def start(self): pass
    def close(self): raise RuntimeError('private cleanup failure')
worker.ExecutionFeed=Feed
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ORACLE_AUTOTRADE_HOME=tmp, INDEX_NO_AUTO="1")
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    autotrade.start("start-a", {})
                    autotrade.stop("stop-a")
                    deadline = time.monotonic() + 2
                    status = autotrade.status()
                    while (
                        not status.get("cleanup", "").startswith("failed")
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.02)
                        status = autotrade.status()
                    self.assertTrue(status["cleanup"].startswith("failed"))
                    self.assertNotIn("private cleanup failure", repr(status))
                    with self.assertRaisesRegex(ValueError, "cleanup"):
                        autotrade.start("start-b", {})
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_stopping_position_keeps_feed_until_unknown_terminal(self):
        script = """
import os, queue, threading, time
import oracle_leverage.autotrade_worker as worker
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self): self.events=queue.Queue(); self.thread=Thread()
    def start(self):
        def send():
            for _ in range(2):
                now=time.time()
                self.events.put(('tick', {'asset':'BTC','feed_id':1,'quote_currency':'USD','received_at':now,'exchange_at':now,'price':100}))
                time.sleep(.02)
            time.sleep(.5)
            self.events.put(('error','stub_disconnect'))
        threading.Thread(target=send,daemon=True).start()
    def close(self):
        with open(os.environ['MARKER'],'w') as f: f.write('closed')
worker.ExecutionFeed=Feed
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "closed")
            env = dict(
                os.environ, ORACLE_AUTOTRADE_HOME=tmp, MARKER=marker, INDEX_NO_AUTO="1"
            )
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    autotrade.start("start-open", {})
                    deadline = time.monotonic() + 1
                    state = autotrade.status()
                    while not state.get("position") and time.monotonic() < deadline:
                        time.sleep(0.02)
                        state = autotrade.status()
                    self.assertEqual(state["position"]["state"], "open")
                    self.assertEqual(autotrade.stop("stop-open")["state"], "stopping")
                    time.sleep(0.1)
                    self.assertFalse(os.path.exists(marker))
                    self.assertEqual(autotrade.status()["state"], "stopping")
                    deadline = time.monotonic() + 2
                    while not os.path.exists(marker) and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(os.path.exists(marker))
                    state = autotrade.status()
                    self.assertEqual(state["state"], "blocked")
                    self.assertEqual(state["position"]["outcome"], "unknown")
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_feed_stops_and_new_session_opens_fresh_owned_feed(self):
        script = """
import os, queue
import oracle_leverage.autotrade_worker as worker
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self): self.events=queue.Queue(); self.thread=Thread()
    def start(self):
        with open(os.environ['MARKER'], 'a') as f: f.write('start\\n')
    def close(self):
        with open(os.environ['MARKER'], 'a') as f: f.write('close\\n')
worker.ExecutionFeed=Feed
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "marker")
            env = dict(
                os.environ, ORACLE_AUTOTRADE_HOME=tmp, MARKER=marker, INDEX_NO_AUTO="1"
            )
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    self.assertTrue(autotrade.start("start-a", {})["accepted"])
                    self.assertEqual(autotrade.stop("stop-a")["state"], "stopped")
                    deadline = time.monotonic() + 2
                    rows = []
                    while time.monotonic() < deadline:
                        if os.path.exists(marker):
                            with open(marker) as stream:
                                rows = stream.read().splitlines()
                        if rows == ["start", "close"]:
                            break
                        time.sleep(0.02)
                    self.assertEqual(rows, ["start", "close"])
                    deadline = time.monotonic() + 2
                    while (
                        autotrade.status().get("cleanup") != "idle"
                        and time.monotonic() < deadline
                    ):
                        time.sleep(0.02)
                    self.assertTrue(autotrade.start("start-b", {})["accepted"])
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline:
                        with open(marker) as stream:
                            rows = stream.read().splitlines()
                        if rows == ["start", "close", "start"]:
                            break
                        time.sleep(0.02)
                    self.assertEqual(rows, ["start", "close", "start"])
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_failed_feed_is_closed_and_failure_is_visible(self):
        script = """
import os, queue
import oracle_leverage.autotrade_worker as worker
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self): self.events=queue.Queue(); self.thread=Thread()
    def start(self): self.events.put(('error','stub_failure'))
    def close(self):
        with open(os.environ['MARKER'], 'w') as f: f.write('closed')
worker.ExecutionFeed=Feed
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "closed")
            env = dict(
                os.environ, ORACLE_AUTOTRADE_HOME=tmp, MARKER=marker, INDEX_NO_AUTO="1"
            )
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    self.assertTrue(autotrade.start("start-fail", {})["accepted"])
                    deadline = time.monotonic() + 2
                    while not os.path.exists(marker) and time.monotonic() < deadline:
                        time.sleep(0.02)
                    self.assertTrue(os.path.exists(marker))
                    self.assertEqual(autotrade.status()["state"], "failed")
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_control_spawns_from_source_and_cleans_owned_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            spawned = []
            original = subprocess.Popen

            def track(*args, **kwargs):
                spawned.append(original(*args, **kwargs))
                self.assertEqual(
                    kwargs["cwd"],
                    str(
                        __import__("pathlib")
                        .Path(autotrade.__file__)
                        .resolve()
                        .parent.parent
                    ),
                )
                return spawned[-1]

            try:
                with (
                    patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}),
                    patch("subprocess.Popen", side_effect=track),
                ):
                    self.assertEqual(autotrade.status()["state"], "unavailable")
                    self.assertEqual(spawned, [])
                    autotrade.configure("explicit-owner-bootstrap", {})
                    self.assertEqual(autotrade.status()["state"], "stopped")
                    self.assertEqual(len(spawned), 1)
            finally:
                for process in spawned:
                    process.terminate()
                    process.wait(timeout=5)

    def test_socket_paper_start_with_stub_feed(self):
        script = """
import queue, time
import oracle_leverage.autotrade_worker as worker
class Thread:
    def is_alive(self): return True
class Feed:
    def __init__(self): self.events=queue.Queue(); self.thread=Thread()
    def start(self):
        now=time.time()
        self.events.put(('tick', {'asset':'BTC','feed_id':1,'quote_currency':'USD','received_at':now,'exchange_at':now,'price':100}))
        time.sleep(.01)
        now=time.time()
        self.events.put(('tick', {'asset':'BTC','feed_id':1,'quote_currency':'USD','received_at':now,'exchange_at':now,'price':100}))
    def close(self): pass
worker.ExecutionFeed=Feed
worker.serve()
"""
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ORACLE_AUTOTRADE_HOME=tmp, INDEX_NO_AUTO="1")
            owner = subprocess.Popen(
                [sys.executable, "-c", script],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                with patch.dict(os.environ, {"ORACLE_AUTOTRADE_HOME": tmp}):
                    result = autotrade.start("socket-start", {})
                    self.assertTrue(result["accepted"])
                    deadline = time.monotonic() + 1
                    while time.monotonic() < deadline:
                        state = autotrade.status()
                        if state.get("position"):
                            break
                        time.sleep(0.02)
                    self.assertEqual(state["position"]["state"], "open")
                    self.assertTrue(state["forecast"]["forced"])
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_malformed_socket_does_not_kill_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ORACLE_AUTOTRADE_HOME=tmp, INDEX_NO_AUTO="1")
            owner = subprocess.Popen(
                [sys.executable, "-m", "oracle_leverage.autotrade_worker"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                for data in (b"[]\n", b"x" * 65537 + b"\n"):
                    with closing(socket.socket(socket.AF_UNIX)) as client:
                        client.settimeout(2)
                        client.connect(path)
                        client.sendall(data)
                        self.assertFalse(json.loads(client.recv(65536))["ok"])
                with closing(socket.socket(socket.AF_UNIX)) as client:
                    client.settimeout(2)
                    client.connect(path)
                    client.sendall(b'{"action":"status"}\n')
                    self.assertTrue(json.loads(client.recv(65536))["ok"])
            finally:
                owner.terminate()
                owner.wait(timeout=5)

    def test_one_private_owner_answers_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ORACLE_AUTOTRADE_HOME=tmp, INDEX_NO_AUTO="1")
            owner = subprocess.Popen(
                [sys.executable, "-m", "oracle_leverage.autotrade_worker"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                path = os.path.join(tmp, "owner.sock")
                deadline = time.monotonic() + 5
                while not os.path.exists(path) and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(os.path.exists(path))
                self.assertEqual(os.stat(path).st_mode & 0o077, 0)
                with closing(socket.socket(socket.AF_UNIX)) as client:
                    client.settimeout(2)
                    client.connect(path)
                    client.sendall(b'{"action":"status"}\n')
                    response = json.loads(client.recv(65536))
                self.assertEqual(response["result"]["state"], "stopped")
                rival = subprocess.run(
                    [sys.executable, "-m", "oracle_leverage.autotrade_worker"],
                    check=False,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
                self.assertEqual(rival.returncode, 0)
            finally:
                owner.terminate()
                owner.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()

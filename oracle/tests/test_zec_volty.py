"""Exercise live configuration and durable fills through an inert GUM transport."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from dataclasses import replace
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from oracle.cli import owner
from oracle.gum_orders import GumError, b58encode, gum_account_owner
from oracle.tests.test_gum_orders import ACCOUNT
from oracle.tests.test_gum_webhook_orders import LifecycleProvider
from oracle.zec_volty import (
    LivePolicy,
    VoltyRunner,
    VoltyVenue,
    main,
    preflight,
    rotate_allocation,
)
from oracle.zec_volty_signal import STRATEGY_ID, WINDOW_SEC, VoltyObservation


class InertGum(LifecycleProvider):
    def __init__(self):
        super().__init__()
        self.preferences = [{"symbol": "ZEC", "isolated": True, "leverage": 25}]

    def __call__(self, method, path, owner, body=None):
        if path == f"/tradingAccount/{ACCOUNT}/leverage":
            self.calls.append((method, path, owner, body))
            return self.preferences
        result = super().__call__(method, path, owner, body)
        if method == "POST":
            self.history[-1]["transactions"][0]["price"] = str(self.market["markPrice"])
        return result

    def reprice(self, price):
        self.market.update(
            bestBid=price - 0.01, bestAsk=price, markPrice=price, indexPrice=price
        )

    @property
    def creates(self):
        return [
            body for method, path, _, body in self.calls
            if method == "POST" and path == "/order/create"
        ]


class DeployedRunnerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.state = Path(directory.name)
        self.inbox = self.state / "live.sqlite3"
        self.now = (1_800_000_000 // WINDOW_SEC) * WINDOW_SEC + 90
        self.clock = lambda: self.now
        mock_time = patch("time.time", side_effect=self.clock)
        mock_time.start()
        self.addCleanup(mock_time.stop)
        key = Ed25519PrivateKey.from_private_bytes(bytes([24]) * 32)
        self.policy = LivePolicy(
            owner=b58encode(key.public_key().public_bytes_raw()),
            trading_account=ACCOUNT,
            subaccount_id=2,
            key_file=self.state / "fixture-never-read",
            allocation="10",
            allocation_basis="collateral",
            max_slippage_bps=10,
            max_order_notional_usdc="20",
        )
        self.inert = InertGum()
        self.venue = VoltyVenue(self.policy, self.inbox, call=self.inert, signer=key.sign)
        self.mark = 1000
        self.runner = VoltyRunner(self.state, source=self, venue=self.venue, clock=self.clock)

    def read(self):
        window = (self.now // WINDOW_SEC) * WINDOW_SEC
        return VoltyObservation(window, self.now, self.mark, 1001, 999)

    def step(self, mark):
        self.now += 1
        self.mark = mark
        return self.runner.step()

    def status(self):
        return json.loads((self.state / "status.json").read_text())

    def open_long(self):
        self.assertEqual(self.step(1000), "armed")
        self.assertEqual(self.status()["telemetry"]["market"], {
            "window_start": self.now // WINDOW_SEC * WINDOW_SEC, "mark_at": self.now,
            "mark": 1000, "upper": 1001, "lower": 999,
        })
        self.assertEqual(self.step(1002), "checking")
        status = self.status()
        self.assertEqual(status["signal"]["side"], "buy")
        self.assertEqual(status["orders"][0]["state"], "acknowledged")
        self.assertTrue(status["orders"][0]["client_order_id"].isdigit())
        self.assertIsNone(status["orders"][0]["order_id"])
        self.assertEqual(status["orders"][0]["fills"], [])
        self.assertEqual(status["telemetry"]["activity"][0]["outcome"], "pending")
        self.assertEqual(self.step(1002), "armed")
        self.assertEqual(self.status()["orders"][0]["state"], "filled")
        self.assertEqual(self.status()["telemetry"]["activity"][0]["outcome"], "complete")

    def test_bounded_both_directions_and_close_first_with_funded_receipts(self):
        self.open_long()
        opened = self.inert.creates[0]
        self.assertEqual(opened["side"], "Bid")
        self.assertEqual(opened["timeInForce"], "FillOrKill")
        self.assertLessEqual(
            Decimal(str(opened["quantity"])) * Decimal(str(opened["price"])),
            Decimal(20),
        )

        # The held notional is above the opening cap; the reduce-only exit
        # must still be possible up to the separate venue-defined close limit.
        self.inert.reprice(1250)
        self.assertGreater(Decimal(str(opened["quantity"])) * 1250, 20)
        self.assertEqual(self.step(998), "checking")
        close = self.inert.creates[1]
        self.assertTrue(close["reduceOnly"])
        self.assertEqual(close["side"], "Ask")
        self.assertEqual(self.step(998), "checking")
        self.assertEqual(len(self.inert.creates), 2)
        self.assertTrue(self.status()["orders"][0]["settlement_pending"])
        self.inert.settle()
        self.assertEqual(self.step(998), "checking")
        self.assertEqual(len(self.inert.creates), 2)
        self.assertEqual(self.step(998), "checking")
        opened_short = self.inert.creates[2]
        self.assertFalse(opened_short["reduceOnly"])
        self.assertEqual(opened_short["side"], "Ask")
        self.assertEqual(self.step(998), "armed")

        orders = self.status()["orders"]
        self.assertEqual([(o["side"], o["leg"]) for o in orders], [
            ("sell", "open"), ("sell", "close"), ("buy", "open"),
        ])
        for order in orders:
            self.assertEqual(order["state"], "filled")
            self.assertTrue(order["order_id"].isdigit())
            self.assertEqual(order["filled_quantity"], order["requested_quantity"])
            self.assertEqual(len(order["fills"]), 1)
            self.assertEqual(set(order["fills"][0]), {"signature", "price", "size", "fee", "timestamp"})

    def test_capped_open_keeps_persisted_short_terms_on_mark_refresh(self):
        self.inert.reprice(1000.10)
        plan = self.venue.plan("ZEC", "sell")
        self.assertEqual(plan["quantity"], "0.019")
        self.assertLess(plan["collateral_native"], plan["collateral_budget_native"])
        self.inert.market["markPrice"] = 1000.40
        fresh = self.venue.plan("ZEC", "sell")
        self.assertEqual(fresh["price_cap"], plan["price_cap"])
        self.assertGreater(
            Decimal(fresh["unit_margin_budget_usdc"]), Decimal(plan["unit_margin_budget_usdc"])
        )

        receipt = self.venue.submit_leg(plan, "11")
        self.assertEqual(receipt["status"], "pending")
        self.assertEqual(len(self.inert.creates), 1)
        order = self.inert.creates[0]
        self.assertEqual(Decimal(str(order["quantity"])), Decimal(plan["quantity"]))
        self.assertEqual(Decimal(str(order["price"])), Decimal(plan["price_cap"]))
        self.assertEqual(order["collateralAmount"], plan["collateral_native"])

    def test_repriced_short_uses_fresh_allocation_ceiling_not_fresh_planned_collateral(self):
        self.inert.reprice(1000.10)
        self.inert.market["markPrice"] = 1000.40
        plan = self.venue.plan("ZEC", "sell")
        self.inert.market["markPrice"] = 1000.10
        fresh = self.venue.plan("ZEC", "sell")
        self.assertEqual(fresh["price_cap"], plan["price_cap"])
        self.assertGreater(plan["collateral_native"], fresh["collateral_native"])

        self.venue.submit_leg(plan, "11")
        self.assertEqual(len(self.inert.creates), 1)
        self.assertEqual(self.inert.creates[0]["collateralAmount"], plan["collateral_native"])

    def test_quote_refresh_cannot_push_persisted_open_past_notional_cap(self):
        plan = self.venue.plan("ZEC", "sell")
        self.assertEqual(Decimal(plan["quantity"]), Decimal("0.02"))
        self.inert.reprice(1000.10)
        with self.assertRaisesRegex(GumError, "gum_order_notional_cap_exceeded"):
            self.venue.submit_leg(plan, "11")
        self.assertEqual(self.inert.creates, [])

    def test_unknown_submission_blocks_new_legs_and_restart_never_replays(self):
        self.assertEqual(self.step(1000), "armed")
        self.inert.response_error = True
        self.assertEqual(self.step(1002), "blocked")
        self.assertEqual(self.step(998), "blocked")
        self.assertEqual(len(self.inert.creates), 1)
        self.assertEqual(self.status()["orders"][0]["state"], "unknown")
        activity = self.status()["telemetry"]["activity"]
        self.assertEqual([a["outcome"] for a in activity], ["preceding_order_unresolved", "unknown"])
        self.runner = VoltyRunner(self.state, source=self, venue=self.venue, clock=self.clock)
        self.assertEqual(self.step(1000), "blocked")
        self.assertEqual(self.step(1002), "blocked")
        self.assertEqual(len(self.inert.creates), 1)

    def test_restart_does_not_open_old_target_after_close(self):
        self.open_long()
        self.assertEqual(self.step(998), "checking")
        self.inert.settle()
        self.assertEqual(self.step(998), "checking")
        self.assertEqual(len(self.inert.creates), 2)
        self.runner = VoltyRunner(self.state, source=self, venue=self.venue, clock=self.clock)
        self.assertEqual(self.step(1000), "armed")
        self.assertEqual(len(self.inert.creates), 2)
        self.assertEqual(self.step(1002), "checking")
        self.assertEqual(len(self.inert.creates), 3)
        self.assertEqual(self.inert.creates[-1]["side"], "Bid")

    def test_new_crossing_supersedes_unopened_reversal_target_in_same_window(self):
        self.open_long()
        self.assertEqual(self.step(998), "checking")
        self.inert.settle()
        self.assertEqual(self.step(1002), "checking")
        self.assertEqual(len(self.inert.creates), 3)
        self.assertEqual(self.inert.creates[-1]["side"], "Bid")
        self.assertFalse(self.inert.creates[-1]["reduceOnly"])

    def test_existing_unowned_position_and_external_fill_history_are_refused(self):
        self.inert.position()
        with self.assertRaisesRegex(GumError, "volty_external_position_or_fill"):
            self.step(1000)
        self.assertEqual(self.inert.creates, [])
        self.inert.positions = []
        self.inert.history = [{"symbol": "ZEC", "orderId": "9", "clientOrderId": "1", "filledSize": "1"}]
        with self.assertRaisesRegex(GumError, "volty_external_position_or_fill"):
            self.step(1002)
        self.assertEqual(self.inert.creates, [])

    def test_kill_marker_reconciles_but_will_not_dispatch_after_resume(self):
        self.open_long()
        self.assertEqual(self.step(998), "checking")
        self.inert.settle()
        halt = self.state / "KILL"
        halt.touch()
        self.assertEqual(self.step(998), "paused")
        self.assertEqual(self.step(998), "paused")
        self.assertIsNone(self.status()["telemetry"]["market"])
        self.assertEqual(len(self.inert.creates), 2)
        self.assertEqual(self.status()["orders"][0]["state"], "filled")

        halt.unlink()
        self.assertEqual(self.step(998), "armed")
        self.assertEqual(len(self.inert.creates), 2)
        self.assertEqual(self.step(1002), "checking")
        self.assertEqual(self.inert.creates[-1]["side"], "Bid")

    def test_learning_ticks_are_durable_and_dedupe_after_restart(self):
        self.assertEqual(self.step(1000), "armed")
        self.assertEqual(self.runner.step(), "armed")
        self.runner = VoltyRunner(self.state, source=self, venue=self.venue, clock=self.clock)
        self.assertEqual(self.runner.step(), "armed")
        self.assertEqual(self.step(1000.4), "armed")
        with closing(sqlite3.connect(self.state / "learning-ticks.sqlite3")) as db:
            observed = db.execute("SELECT mark_at,received_ms,mark FROM ticks ORDER BY mark_at").fetchall()
        self.assertEqual(observed, [(self.now - 1, (self.now - 1) * 1000, 1000), (self.now, self.now * 1000, 1000.4)])
        self.assertEqual(self.status()["telemetry"]["capture"], "recording")
        self.assertFalse(self.inert.creates)

    def test_preflight_requires_exact_venue_leverage_funding_and_both_valid_plans(self):
        preview = preflight(self.venue)
        self.assertEqual(preview["selected_leverage"], 25)
        self.assertEqual([item["side"] for item in preview["preview"]], ["buy", "sell"])
        self.assertEqual(self.inert.creates, [])

        self.inert.preferences[0]["leverage"] = 50
        with self.assertRaisesRegex(GumError, "gum_exact_leverage_preference_required"):
            preflight(self.venue)
        self.inert.preferences[0]["leverage"] = 25
        no_margin = {"freeBalance": "0", "availableToTrade": "0", "tokenBalance": 0}
        self.inert.balance = no_margin
        with self.assertRaisesRegex(GumError, "gum_insufficient_collateral"):
            preflight(self.venue)
        narrow_path = self.state / "absent.sqlite3"
        self.inert._cash(Decimal(100))
        below_minimum = VoltyVenue(
            replace(self.policy, max_order_notional_usdc="3"),
            narrow_path,
            call=self.inert,
        )
        with self.assertRaisesRegex(GumError, "gum_below_minimum_order"):
            preflight(below_minimum)
        self.assertFalse(narrow_path.exists())
        self.assertEqual(self.inert.creates, [])

    def test_private_policy_and_account_claim_fence_different_inboxes(self):
        path = self.state / "policy.json"
        path.write_text(json.dumps(self.policy.__dict__, default=str))
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "live_policy_not_private"):
            LivePolicy.load(path)
        path.chmod(0o600)
        self.assertEqual(LivePolicy.load(path), self.policy)

        with patch.object(Path, "home", return_value=self.state):
            another = gum_account_owner(self.venue, "tradingview", self.state / "another.sqlite3")
            with (
                gum_account_owner(self.venue, "volty", self.inbox),
                self.assertRaisesRegex(GumError, "gum_account_already_running"),
                another,
            ):
                self.fail("account lock allowed a second venue writer")
            another = gum_account_owner(self.venue, "tradingview", self.state / "another.sqlite3")
            with self.assertRaisesRegex(GumError, "gum_account_bound_to_another_inbox"), another:
                self.fail("a different inbox discarded durable account state")
            with gum_account_owner(self.venue, "volty", self.inbox):
                pass

    def test_read_only_cli_preflight_never_loads_signer_or_creates_state(self):
        path = self.state / "policy.json"
        path.write_text(json.dumps(self.policy.__dict__, default=str))
        path.chmod(0o600)
        absent = self.state / "fresh"
        stream = StringIO()
        with (
            patch("oracle.zec_volty.load_signer", side_effect=AssertionError("unexpected signer access")),
            patch("oracle.zec_volty.VoltyVenue", wraps=lambda policy, path: VoltyVenue(policy, path, call=self.inert)),
            redirect_stdout(stream),
        ):
            self.assertEqual(main(["--preflight", "--config", str(path), "--state-dir", str(absent)]), 0)
        self.assertTrue(json.loads(stream.getvalue())["eligible"])
        self.assertFalse(absent.exists())
        self.assertEqual(self.inert.creates, [])

    def journal_bindings(self):
        with closing(sqlite3.connect(self.inbox)) as db:
            active = db.execute("SELECT binding FROM volty_policy WHERE slot=1").fetchone()[0]
            events = db.execute(
                "SELECT event_id,portfolio_id,status,client_order_id,plan,result FROM signals ORDER BY rowid"
            ).fetchall()
        return active, events

    def rotate(self, replacement=None):
        if replacement is None:
            replacement = replace(self.policy, allocation="50")
        with patch.object(Path, "home", return_value=self.state):
            return rotate_allocation(self.state, self.policy, replacement, call=self.inert)

    def test_allocation_rotation_preserves_fills_and_configures_fresh_signals(self):
        self.open_long()
        self.assertEqual(self.step(998), "checking")
        self.inert.settle()
        kill = self.state / "KILL"
        kill.touch()
        self.assertEqual(self.step(998), "paused")
        self.assertEqual(self.step(998), "paused")
        kill.unlink()
        old_binding, old_rows = self.journal_bindings()
        self.assertEqual([row[2] for row in old_rows], ["complete", "expired"])

        replacement = replace(self.policy, allocation="50")
        old_file, new_file = self.state / "old.json", self.state / "new.json"
        for path, config in ((old_file, self.policy), (new_file, replacement)):
            path.write_text(json.dumps(config.__dict__, default=str))
            path.chmod(0o600)
        stream = StringIO()
        with (
            patch.object(Path, "home", return_value=self.state),
            patch("oracle.zec_volty.load_signer", side_effect=AssertionError("unexpected signer access")),
            patch("oracle.zec_volty.rotate_allocation", wraps=lambda state, old, new:
                  rotate_allocation(state, old, new, call=self.inert)),
            redirect_stdout(stream),
        ):
            self.assertEqual(main([
                "--rotate-allocation-from", str(old_file), "--config", str(new_file),
                "--state-dir", str(self.state),
            ]), 0)
        receipt = json.loads(stream.getvalue())
        self.assertEqual(receipt["allocation"], "50")
        self.assertEqual(receipt["max_order_notional_usdc"], "20")
        self.assertEqual([item["side"] for item in receipt["preview"]], ["buy", "sell"])
        self.assertEqual(len(self.inert.creates), 2)

        current = VoltyVenue(replacement, self.inbox, call=self.inert, signer=self.venue.signer)
        self.assertNotEqual(current.binding, old_binding)
        self.assertEqual(self.journal_bindings(), (current.binding, old_rows))
        current.verify_binding()
        self.assertTrue(preflight(current)["eligible"])
        with self.assertRaisesRegex(GumError, "volty_live_inbox_policy_changed"):
            preflight(self.venue)
        with self.assertRaisesRegex(GumError, "volty_live_inbox_policy_changed"):
            self.venue.verify_binding()

        self.runner = VoltyRunner(self.state, source=self, venue=current, clock=self.clock)
        self.assertEqual(self.step(1000), "armed")
        self.assertEqual(self.step(1002), "checking")
        self.assertEqual(self.step(1002), "armed")
        _, new_rows = self.journal_bindings()
        self.assertEqual(new_rows[:2], old_rows)
        self.assertEqual(new_rows[2][1:3], (current.binding, "complete"))
        self.assertEqual(len(self.inert.creates), 3)
        current.verify_lineage(current.get_net_position())

        with closing(sqlite3.connect(self.inbox)) as db, db:
            # Retirement is per exact event. A stray old-policy row and a
            # previously retired event made executable must both fail closed.
            db.execute(
                "INSERT INTO signals (event_id,digest,symbol,side,timestamp,status,mode,portfolio_id) "
                "VALUES ('unregistered','x','ZEC','buy',?,'expired','live',?)",
                (self.now, old_binding),
            )
        with self.assertRaisesRegex(GumError, "volty_live_inbox_binding_mismatch"):
            current.verify_binding()
        with closing(sqlite3.connect(self.inbox)) as db, db:
            db.execute("DELETE FROM signals WHERE event_id='unregistered'")
            db.execute("UPDATE signals SET status='queued' WHERE event_id=?", (old_rows[0][0],))
        with self.assertRaisesRegex(GumError, "volty_live_inbox_binding_mismatch"):
            preflight(current)

    def test_allocation_rotation_fails_with_foreign_or_unresolved_signal(self):
        before = self.journal_bindings()
        for status, binding, reason in (
            ("expired", "foreign-policy", "volty_live_inbox_binding_mismatch"),
            ("queued", self.venue.binding, "volty_execution_requires_reconciliation"),
            ("unknown", self.venue.binding, "volty_execution_requires_reconciliation"),
        ):
            with self.subTest(status=status):
                with closing(sqlite3.connect(self.inbox)) as db, db:
                    db.execute(
                        "INSERT INTO signals (event_id,digest,symbol,side,timestamp,status,mode,portfolio_id) "
                        "VALUES ('blocked','x','ZEC','buy',?,?,'live',?)",
                        (self.now, status, binding),
                    )
                with self.assertRaisesRegex(GumError, reason):
                    self.rotate()
                self.assertEqual(self.journal_bindings()[0], before[0])
                self.assertFalse(self.inert.calls)
                with closing(sqlite3.connect(self.inbox)) as db, db:
                    db.execute("DELETE FROM signals WHERE event_id='blocked'")

    def test_allocation_rotation_fails_with_owned_position_or_changes_other_than_allocation(self):
        self.open_long()
        before = self.journal_bindings()
        with self.assertRaisesRegex(GumError, "volty_open_position_requires_reconciliation"):
            self.rotate()
        with self.assertRaisesRegex(GumError, "volty_rotation_requires_allocation_only_change"):
            self.rotate(replace(self.policy, allocation="50", max_order_notional_usdc="80"))
        with self.assertRaisesRegex(GumError, "volty_rotation_requires_new_allocation"):
            self.rotate(replace(self.policy, allocation="10.0"))
        self.assertEqual(self.journal_bindings(), before)
        self.assertEqual(len(self.inert.creates), 1)

    def test_allocation_rotation_requires_both_offline_owner_locks(self):
        before = self.journal_bindings()
        with (
            owner(self.state / "status.json"),
            self.assertRaisesRegex(RuntimeError, "archive_owner_already_running"),
        ):
            self.rotate()
        with (
            patch.object(Path, "home", return_value=self.state),
            gum_account_owner(self.venue, STRATEGY_ID, self.inbox),
            self.assertRaisesRegex(GumError, "gum_account_already_running"),
        ):
            self.rotate()
        self.assertEqual(self.journal_bindings(), before)
        self.assertFalse(self.inert.calls)

    def test_observe_reports_history_without_venue_reads_or_submissions(self):
        self.open_long()
        self.runner = VoltyRunner(self.state, source=self, clock=self.clock)
        old_calls = len(self.inert.calls)
        self.assertEqual(self.step(1000), "watching")
        self.assertEqual(self.step(998), "watching")
        status = self.status()
        self.assertEqual(status["mode"], "observe")
        self.assertEqual(status["orders"][0]["state"], "filled")
        self.assertEqual(len(self.inert.calls), old_calls)

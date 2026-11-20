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

from oracle.gum_orders import GumError, b58encode, gum_account_owner
from oracle.tests.test_gum_orders import ACCOUNT
from oracle.tests.test_gum_webhook_orders import LifecycleProvider
from oracle.zec_volty import LivePolicy, VoltyRunner, VoltyVenue, main, preflight
from oracle.zec_volty_signal import WINDOW_SEC, VoltyObservation


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

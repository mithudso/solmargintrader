"""GUM reversals require durable per-leg identity, a fill and settled collateral."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from oracle import gum_webhook_orders as worker
from oracle.gum_orders import GumAmbiguous, GumError, GumOrders, b58encode
from oracle.tests.test_gum_orders import ACCOUNT, ISOLATED, Provider
from oracle.webhook import accept_signal
from oracle.webhook_orders import database, records


class Venue:
    binding = "gum-policy-1"
    owner = "owner-public-key"
    account_id = "cross-account"
    subaccount_id = 0

    def __init__(self):
        self.position_side = None
        self.position_size = "0"
        self.plans = []
        self.submissions = []
        self.reconciliations = []
        self.submit_error = None
        self.plan_error = None
        self.receipt_change = {}
        self.status = "filled"
        self.settled = True

    def plan(self, symbol, side, account_id):
        self.plans.append((symbol, side, account_id))
        if self.plan_error:
            raise self.plan_error
        if self.position_side == side:
            action, quantity = "noop", "0"
        elif self.position_side:
            action, quantity = "close", self.position_size
        else:
            action, quantity = "open", "2.000"
        return {
            "venue": "jupiter-gum",
            "product_id": "ZEC-PERP",
            "account_id": self.account_id,
            "owner": self.owner,
            "subaccount_id": self.subaccount_id,
            "binding": self.binding,
            "action": action,
            "side": side,
            "target_side": side,
            "quantity": quantity,
            "isolated": True,
            "reduce_only": action == "close",
            "leverage": "2",
            "allocation": "75",
            "allocation_basis": "collateral",
        }

    def submit_leg(self, plan, client_id, *, enabled, deadline):
        self.last_enabled = enabled
        self.last_deadline = deadline
        self.submissions.append((dict(plan), client_id))
        if self.submit_error:
            raise self.submit_error
        return {
            "client_order_id": client_id,
            "account_id": self.account_id,
            "symbol": "ZEC",
            "side": plan["side"],
        }

    def reconcile(self, plan, client_id):
        self.reconciliations.append((dict(plan), client_id))
        if self.status == "filled":
            self.position_side = None if plan["action"] == "close" else plan["side"]
            self.position_size = "0" if plan["action"] == "close" else plan["quantity"]
        result = {
            "status": self.status,
            "client_order_id": client_id,
            "account_id": self.account_id,
            "owner": self.owner,
            "subaccount_id": self.subaccount_id,
            "symbol": "ZEC",
            "side": plan["side"],
            "reduce_only": plan["reduce_only"],
            "isolated": True,
            "original_quantity": plan["quantity"],
            "filled_quantity": plan["quantity"] if self.status == "filled" else "0",
            "position": {
                "side": self.position_side,
                "size": self.position_size,
                "isolated": True,
            },
            "settled": self.settled,
            "order_id": "10",
            "transactions": [
                {"signature": "public-gum-transaction-receipt", "type": "fill"}
            ]
            if self.status == "filled"
            else [],
        }
        result.update(self.receipt_change)
        return result


class LifecycleProvider(Provider):
    """The actual adapter uses REST-shaped reads and writes, with no network."""

    def __init__(self):
        super().__init__()
        self.market["riskTiers"][0]["maxLeverage"] = 50
        self.unsettled_credit = Decimal(0)

    def _cash(self, amount):
        self.balance = {
            "freeBalance": str(amount),
            "availableToTrade": str(amount),
            "tokenBalance": int(amount * 1000000),
        }

    def settle(self):
        self._cash(Decimal(self.balance["freeBalance"]) + self.unsettled_credit)
        self.unsettled_credit = Decimal(0)
        self.idle_balance = {
            "freeBalance": "0",
            "availableToTrade": "0",
            "tokenBalance": 0,
        }

    def __call__(self, method, path, owner, body=None):
        if path == f"/tradingAccount/{ACCOUNT}/leverage":
            self.calls.append((method, path, owner, body))
            return []
        if path == "/market/ZEC":
            self.market["timestamp"] = int(time.time())
        result = super().__call__(method, path, owner, body)
        if method != "POST":
            return result
        if not any(row["pubkey"] == ISOLATED for row in self.account_rows):
            self.isolated_account()
        quantity = Decimal(str(body["quantity"]))
        collateral = Decimal(body["collateralAmount"]) / 1000000
        fee = quantity * 1000 * Decimal("0.00035")
        if body["reduceOnly"]:
            self.unsettled_credit = Decimal(self.positions[0]["collateral"]) - fee
            self.positions = []
            self.idle_balance = {
                "freeBalance": str(self.unsettled_credit),
                "availableToTrade": "0",
                "tokenBalance": int(self.unsettled_credit * 1000000),
            }
            executed = -self.unsettled_credit
        else:
            self._cash(Decimal(self.balance["freeBalance"]) - collateral)
            self.positions = [
                {
                    "symbol": "ZEC",
                    "isolated": True,
                    "side": body["side"],
                    "size": str(quantity),
                    "collateral": str(collateral - fee),
                }
            ]
            executed = collateral
        self.history.append(
            {
                "orderId": str(len(self.history) + 1),
                "clientOrderId": body["clientOrderId"],
                "symbol": "ZEC",
                "side": body["side"],
                "isolated": True,
                "reduceOnly": body["reduceOnly"],
                "orderType": "market",
                "timeInForce": "fok",
                "originalSize": str(quantity),
                "filledSize": str(quantity),
                "initialCollateral": str(collateral),
                "executedCollateral": str(executed),
                "status": "filled",
                "transactions": [
                    {
                        "signature": b58encode(bytes([len(self.history) + 1]) * 64),
                        "type": "fill",
                        "timestamp": int(time.time()),
                        "price": "1000",
                        "size": str(quantity),
                        "fee": str(fee),
                        "role": "taker",
                    }
                ],
            }
        )
        return result


class GumWebhookOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "signals.sqlite3"
        self.venue = Venue()
        self.secret = "test-private-secret-" * 3

    def enqueue(self, event_id="event-1", *, side="buy", mode="live", binding=None):
        return accept_signal(
            self.path,
            json.dumps(
                {
                    "event_id": event_id,
                    "symbol": "CRYPTO:ZECUSD",
                    "side": side,
                    "timestamp": 1000,
                    "secret": self.secret,
                }
            ).encode(),
            self.secret,
            now=1000,
            mode=mode,
            portfolio_id=(self.venue.binding if binding is None else binding)
            if mode != "inbox"
            else None,
        )

    def process(self, **kwargs):
        return worker.process_one(
            self.path,
            self.venue,
            self.venue.binding,
            now=kwargs.pop("now", 1000),
            allow_live=kwargs.pop("allow_live", True),
            **kwargs,
        )

    def row(self):
        return records(self.path)[0]

    def state(self):
        return json.loads(self.row()["plan"])

    def test_acceptance_is_pending_and_full_fill_completes_once(self):
        self.enqueue()
        self.assertEqual(self.process(), "pending")
        self.assertEqual(self.row()["status"], "pending")
        self.assertEqual(self.process(), "complete")
        self.assertEqual(self.process(), "idle")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.venue.last_deadline, 1300)
        self.assertTrue(self.venue.last_enabled())
        self.assertEqual(self.row()["order_id"], "10")
        self.assertEqual(
            json.loads(self.row()["result"])["transactions"][0]["signature"],
            "public-gum-transaction-receipt",
        )

    def test_reverse_closes_then_separately_replans_after_full_fill_and_settlement(
        self,
    ):
        self.venue.position_side, self.venue.position_size = "buy", "3.000"
        self.enqueue(side="sell")
        self.assertEqual(self.process(), "pending")
        self.assertTrue(self.venue.submissions[0][0]["reduce_only"])
        self.assertEqual(self.venue.submissions[0][0]["quantity"], "3.000")
        self.assertEqual(self.process(), "closed")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.process(), "pending")
        self.assertFalse(self.venue.submissions[1][0]["reduce_only"])
        self.assertEqual(self.venue.submissions[1][0]["quantity"], "2.000")
        self.assertEqual(self.process(), "complete")
        self.assertEqual(self.venue.position_side, "sell")
        legs = self.state()["legs"]
        self.assertEqual([leg["state"] for leg in legs], ["filled", "filled"])
        self.assertNotEqual(legs[0]["client_order_id"], legs[1]["client_order_id"])

    def test_filled_close_waits_for_collateral_settlement(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.venue.settled = False
        self.enqueue()
        self.assertEqual(self.process(), "pending")
        self.assertEqual(self.process(), "pending")
        self.assertEqual(self.process(), "pending")
        self.assertEqual(len(self.venue.submissions), 1)
        self.venue.settled = True
        self.assertEqual(self.process(), "closed")
        self.assertEqual(self.process(), "pending")
        self.assertEqual(len(self.venue.submissions), 2)

    def test_same_side_signal_does_not_accumulate_exposure(self):
        self.venue.position_side, self.venue.position_size = "buy", "2.000"
        self.enqueue()
        self.assertEqual(self.process(), "complete")
        self.assertFalse(self.venue.submissions)
        self.assertEqual(self.venue.position_size, "2.000")

    def test_dry_run_close_preview_never_submits_or_promotes(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue(mode="dry-run")
        self.assertEqual(self.process(), "dry-run")
        self.assertEqual(self.state()["preview"]["action"], "close")
        self.assertEqual(self.enqueue(mode="live"), "duplicate")
        self.assertEqual(self.process(), "idle")
        self.assertFalse(self.venue.submissions)

    def test_inbox_event_cannot_be_promoted(self):
        self.enqueue(mode="inbox")
        self.assertEqual(self.enqueue(), "duplicate")
        self.assertEqual(self.process(), "idle")
        self.assertFalse(self.venue.plans)

    def test_duplicate_live_alert_is_one_submission(self):
        self.enqueue()
        self.process()
        self.assertEqual(self.enqueue(), "duplicate")
        self.process()
        self.assertEqual(self.process(), "idle")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_ambiguous_submission_never_retries_and_blocks_later_signal(self):
        self.enqueue()
        self.venue.submit_error = TimeoutError("private upstream body")
        self.assertEqual(self.process(), "unknown")
        self.venue.status = "unknown"
        self.enqueue("event-2", side="sell")
        for _ in range(3):
            self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertNotIn(
            "private upstream", self.path.read_bytes().decode(errors="ignore")
        )

    def test_known_unsent_adapter_refusal_does_not_create_a_permanent_halt(self):
        self.enqueue()
        self.venue.submit_error = GumError("gum_plan_expired")
        self.assertEqual(self.process(), "refused")
        self.assertEqual(self.state()["legs"][0]["state"], "refused")
        self.assertEqual(self.process(), "idle")
        self.assertFalse(self.venue.reconciliations)

    def test_ambiguous_adapter_error_is_not_a_known_unsent_refusal(self):
        self.enqueue()
        self.venue.submit_error = GumAmbiguous("gum_submission_requires_reconciliation")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.row()["status"], "unknown")

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_real_adapter_http_contract_open_close_settle_and_reverse(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # This deterministic test key is unrelated to any owner wallet.
        key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        provider = LifecycleProvider()
        venue = GumOrders(
            b58encode(key.public_key().public_bytes_raw()),
            ACCOUNT,
            2,
            leverage="2",
            allocation="75",
            allocation_basis="collateral",
            signer=key.sign,
            call=provider,
        )

        def alert(event_id, side):
            timestamp = int(time.time())
            return accept_signal(
                self.path,
                json.dumps(
                    {
                        "event_id": event_id,
                        "symbol": "CRYPTO:ZECUSD",
                        "side": side,
                        "timestamp": timestamp,
                        "secret": self.secret,
                    }
                ).encode(),
                self.secret,
                now=timestamp,
                mode="live",
                portfolio_id=venue.binding,
            )

        def process():
            return worker.process_one(self.path, venue, venue.binding, allow_live=True)

        self.assertEqual(alert("real-open", "buy"), "received")
        self.assertEqual(process(), "pending")
        self.assertEqual(process(), "complete")
        self.assertEqual(venue.get_net_position()["side"], "buy")
        first = records(self.path)[0]
        first_receipt = json.loads(first["result"])
        self.assertGreater(Decimal(first_receipt["actual_fee_usdc"]), 0)
        self.assertEqual(first_receipt["transactions"][0]["role"], "taker")
        self.assertEqual(first_receipt["transactions"][0]["price"], "1000")

        self.assertEqual(alert("real-reverse", "sell"), "received")
        self.assertEqual(process(), "pending")
        self.assertEqual(
            process(), "pending"
        )  # Full close, but collateral is not cash yet.
        self.assertIsNone(venue.get_net_position()["side"])
        self.assertEqual(len([c for c in provider.calls if c[0] == "POST"]), 2)
        provider.settle()
        self.assertEqual(process(), "closed")
        self.assertEqual(process(), "pending")
        self.assertEqual(process(), "complete")
        self.assertEqual(venue.get_net_position()["side"], "sell")
        self.assertEqual(process(), "idle")

        posts = [call[3] for call in provider.calls if call[0] == "POST"]
        self.assertEqual(len(posts), 3)
        self.assertEqual([body["reduceOnly"] for body in posts], [False, True, False])
        self.assertEqual([body["side"] for body in posts], ["Bid", "Ask", "Ask"])
        self.assertTrue(all(body["timeInForce"] == "FillOrKill" for body in posts))
        self.assertEqual(posts[0]["collateralAmount"], 75000000)
        self.assertEqual(posts[1]["collateralAmount"], 0)
        self.assertLess(posts[2]["collateralAmount"], posts[0]["collateralAmount"])
        self.assertEqual(len({body["clientOrderId"] for body in posts}), 3)
        reverse = records(self.path)[0]
        legs = json.loads(reverse["plan"])["legs"]
        self.assertEqual([leg["state"] for leg in legs], ["filled", "filled"])
        self.assertTrue(legs[0]["receipt"]["settled"])
        self.assertGreater(Decimal(legs[1]["receipt"]["actual_fee_usdc"]), 0)
        self.assertTrue(all(leg["receipt"]["transactions"] for leg in legs))

    def test_crash_after_commit_recovers_by_read_only_reconciliation(self):
        self.enqueue()
        self.venue.submit_error = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.process()
        self.assertEqual(self.row()["status"], "submitting")
        self.venue.submit_error = None
        self.assertEqual(self.process(), "complete")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_crash_before_submit_commit_is_refused_at_startup(self):
        self.enqueue()
        original = worker._save

        def crash(path, row, status, state, **kwargs):
            if status == "submitting":
                raise KeyboardInterrupt()
            return original(path, row, status, state, **kwargs)

        with patch.object(worker, "_save", crash), self.assertRaises(KeyboardInterrupt):
            self.process()
        self.assertEqual(self.row()["status"], "planning")
        worker.recover_planning(self.path)
        self.assertEqual(self.row()["status"], "refused")
        self.assertEqual(self.process(), "idle")
        self.assertFalse(self.venue.submissions)

    def test_partial_close_never_opens_opposite_position(self):
        self.venue.position_side, self.venue.position_size = "sell", "3.000"
        self.enqueue()
        self.process()
        self.venue.status = "cancelled"
        self.venue.receipt_change = {
            "filled_quantity": "1.000",
            "position": {"side": "sell", "size": "2.000", "isolated": True},
        }
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_partial_open_is_ambiguous_and_blocks_new_signal(self):
        self.enqueue()
        self.process()
        self.venue.status = "cancelled"
        self.venue.receipt_change = {
            "filled_quantity": "1.000",
            "position": {"side": "buy", "size": "1.000", "isolated": True},
        }
        self.assertEqual(self.process(), "unknown")
        self.enqueue("later", side="sell")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_zero_fill_cancellation_is_terminal_without_opening(self):
        self.venue.position_side, self.venue.position_size = "sell", "3.000"
        self.enqueue()
        self.process()
        self.venue.status = "cancelled"
        self.assertEqual(self.process(), "cancelled")
        self.assertEqual(self.process(), "idle")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_filled_history_without_flat_close_position_does_not_open(self):
        self.venue.position_side, self.venue.position_size = "sell", "3.000"
        self.enqueue()
        self.process()
        self.venue.receipt_change = {
            "position": {"side": "sell", "size": "1.000", "isolated": True}
        }
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_full_fill_with_wrong_account_identity_cannot_complete(self):
        self.enqueue()
        self.process()
        self.venue.receipt_change = {"account_id": "different-account"}
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.row()["status"], "unknown")

    def test_filled_status_without_fill_transaction_cannot_complete(self):
        self.enqueue()
        self.process()
        self.venue.receipt_change = {
            "transactions": [{"signature": "submit-only", "type": "submit"}]
        }
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_changed_binding_preserves_old_receipt_without_reinterpreting_it(self):
        self.enqueue()
        self.process()
        self.venue.binding = "different-policy"
        self.assertEqual(self.process(), "blocked")
        self.assertEqual(self.row()["status"], "pending")
        self.assertFalse(self.venue.reconciliations)

    def test_foreign_queued_venue_is_not_claimed(self):
        self.enqueue(binding="coinbase-portfolio")
        self.assertEqual(self.process(), "blocked")
        self.assertEqual(self.row()["status"], "queued")
        self.assertFalse(self.venue.plans)

    def test_expired_signal_after_close_remains_flat(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.assertEqual(self.process(), "closed")
        self.assertEqual(self.process(now=1301), "expired")
        self.assertIsNone(self.venue.position_side)
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.state()["legs"][0]["receipt"]["status"], "filled")

    def test_kill_during_close_can_reconcile_but_cannot_open(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.assertEqual(self.process(enabled=lambda: False), "closed")
        self.assertEqual(self.process(enabled=lambda: False), "disarmed")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_dry_run_service_can_reconcile_old_live_leg_but_not_reopen(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.assertEqual(self.process(allow_live=False), "closed")
        self.assertEqual(self.process(allow_live=False), "disarmed")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_new_live_signal_needs_explicit_live_worker(self):
        self.enqueue()
        self.assertEqual(self.process(allow_live=False), "disarmed")
        self.assertEqual(self.row()["status"], "queued")
        self.assertFalse(self.venue.plans)

    def test_disarm_after_plan_never_submits(self):
        self.enqueue()
        checks = iter((True, False))
        self.assertEqual(self.process(enabled=lambda: next(checks)), "refused")
        self.assertFalse(self.venue.submissions)

    def test_position_changed_after_close_halts_instead_of_closing_again(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.process()
        self.venue.position_side, self.venue.position_size = "sell", "4.000"
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.process(), "blocked")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_interrupted_next_plan_preserves_completed_close(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.process()
        self.venue.plan_error = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.process()
        self.assertEqual(self.row()["status"], "planning")
        worker.recover_planning(self.path)
        self.assertEqual(self.state()["legs"][0]["receipt"]["status"], "filled")
        self.assertFalse(self.venue.position_side)
        self.assertEqual(len(self.venue.submissions), 1)

    def test_leg_id_is_stable_nonzero_u64_and_leg_specific(self):
        one = worker.client_order_id("binding", "event", 0)
        self.assertEqual(one, worker.client_order_id("binding", "event", 0))
        self.assertNotEqual(one, worker.client_order_id("binding", "event", 1))
        self.assertTrue(0 < int(one) < 2**64)

    def test_corrupted_stored_close_proof_cannot_reopen_after_restart(self):
        self.venue.position_side, self.venue.position_size = "sell", "1.000"
        self.enqueue()
        self.process()
        self.process()
        state = self.state()
        state["legs"][0]["receipt"]["settled"] = False
        with database(self.path) as db, db:
            db.execute("UPDATE signals SET plan=?", (json.dumps(state),))
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.process(), "blocked")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_wrong_durable_leg_id_does_not_poll_or_submit(self):
        self.enqueue()
        self.process()
        state = self.state()
        state["legs"][0]["client_order_id"] = "123"
        with database(self.path) as db, db:
            db.execute("UPDATE signals SET plan=?", (json.dumps(state),))
        self.assertEqual(self.process(), "unknown")
        self.assertFalse(self.venue.reconciliations)
        self.assertEqual(len(self.venue.submissions), 1)

    def test_later_full_receipt_resolves_unknown_without_resubmitting(self):
        self.enqueue()
        self.venue.submit_error = TimeoutError()
        self.assertEqual(self.process(), "unknown")
        self.venue.submit_error = None
        self.assertEqual(self.process(), "complete")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_next_same_side_event_is_a_noop_after_verified_open(self):
        self.enqueue()
        self.process()
        self.process()
        self.enqueue("same-direction")
        self.assertEqual(self.process(), "complete")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_corrupted_or_legacy_pending_plan_cannot_reach_adapter(self):
        self.enqueue()
        with database(self.path) as db, db:
            db.execute(
                "UPDATE signals SET status='unknown', plan=?",
                (json.dumps({"product_id": "ZEC-USD"}),),
            )
        self.assertEqual(self.process(), "blocked")
        self.assertFalse(self.venue.reconciliations)


if __name__ == "__main__":
    unittest.main()

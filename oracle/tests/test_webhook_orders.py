"""Webhook sends bind durable identity and never retry ambiguous orders."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from oracle.webhook import accept_signal
from oracle.webhook_orders import database, process_one, records, recover_planning


class Venue:
    def __init__(self):
        self.plans = []
        self.submissions = []
        self.lookups = []
        self.searches = []
        self.submit_error = None
        self.status = "FILLED"
        self.identity_side = "BUY"
        self.found = None

    def plan(self, symbol, side, portfolio_id):
        self.plans.append((symbol, side, portfolio_id))
        return {
            "product_id": "SOL-USDC",
            "side": side.upper(),
            "size_field": "quote_size" if side == "buy" else "base_size",
            "size": "75.00" if side == "buy" else "0.75",
            "portfolio_id": portfolio_id,
        }

    def submit(self, plan, client_order_id):
        self.submissions.append((dict(plan), client_order_id))
        if self.submit_error:
            raise self.submit_error
        return {
            "order_id": "order-1",
            "product_id": plan["product_id"],
            "side": plan["side"],
            "client_order_id": client_order_id,
        }

    def get(self, order_id):
        self.lookups.append(order_id)
        client_order_id = self.submissions[-1][1]
        return {
            "order_id": order_id,
            "product_id": "SOL-USDC",
            "side": self.identity_side,
            "client_order_id": client_order_id,
            "status": self.status,
        }

    def find(self, client_order_id, product_id, portfolio_id):
        self.searches.append((client_order_id, product_id, portfolio_id))
        return self.found


class WebhookOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "signals.sqlite3"
        self.venue = Venue()
        self.secret = "test-private-secret-" * 3

    def enqueue(self, event_id="alert-1", *, mode="live", side="buy"):
        body = json.dumps(
            {
                "event_id": event_id,
                "symbol": "COINBASE:SOLUSDC",
                "side": side,
                "timestamp": 1000,
                "secret": self.secret,
            }
        ).encode()
        return accept_signal(
            self.path,
            body,
            self.secret,
            now=1000,
            mode=mode,
            portfolio_id="default-portfolio" if mode != "inbox" else None,
        )

    def process(self, **kwargs):
        return process_one(
            self.path,
            self.venue,
            "default-portfolio",
            now=1000,
            allow_live=kwargs.pop("allow_live", True),
            **kwargs,
        )

    def first_record(self):
        return records(self.path)[0]

    def test_dry_run_plans_without_submitting_and_cannot_be_promoted(self):
        self.enqueue(mode="dry-run")
        self.assertEqual(self.process(), "dry-run")
        self.assertEqual(self.first_record()["mode"], "dry-run")
        self.assertEqual(self.enqueue(mode="live"), "duplicate")
        self.assertEqual(self.process(), "idle")
        self.assertEqual(len(self.venue.plans), 1)
        self.assertFalse(self.venue.submissions)
        self.assertFalse(self.venue.lookups)

    def test_inbox_duplicate_cannot_be_promoted_to_live(self):
        self.enqueue(mode="inbox")
        self.assertEqual(self.enqueue(mode="live"), "duplicate")
        self.assertEqual(self.process(), "idle")
        self.assertEqual(self.first_record()["status"], "received")
        self.assertEqual(self.first_record()["mode"], "inbox")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)

    def test_live_submits_once_and_reconciles_terminal_identity(self):
        self.enqueue()
        self.assertEqual(self.process(), "complete")
        row = self.first_record()
        self.assertEqual(row["status"], "complete")
        self.assertEqual(row["order_id"], "order-1")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.venue.submissions[0][1], row["client_order_id"])
        self.assertEqual(self.venue.lookups, ["order-1"])
        self.assertEqual(json.loads(row["result"])["status"], "FILLED")
        self.assertEqual(self.enqueue(), "duplicate")
        self.assertEqual(self.process(), "idle")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_timeout_blocks_following_order_and_replay_never_resubmits(self):
        self.enqueue()
        self.venue.submit_error = TimeoutError("transport failed after send")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.first_record()["status"], "unknown")
        self.assertEqual(self.enqueue(), "duplicate")
        self.enqueue("alert-2")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(len(self.venue.plans), 1)
        self.assertEqual(len(self.venue.searches), 2)
        self.assertEqual(
            {r["event_id"]: r["status"] for r in records(self.path)},
            {"alert-1": "unknown", "alert-2": "queued"},
        )

    def test_unknown_can_only_complete_from_matching_client_order(self):
        self.enqueue()
        self.venue.submit_error = TimeoutError("may have sent")
        self.assertEqual(self.process(), "unknown")
        row = self.first_record()
        self.venue.found = {
            "order_id": "recovered-order",
            "product_id": "SOL-USDC",
            "side": "BUY",
            "client_order_id": "different-client-id",
            "status": "FILLED",
        }
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.first_record()["status"], "unknown")
        self.venue.found["client_order_id"] = row["client_order_id"]
        self.assertEqual(self.process(), "complete")
        self.assertEqual(self.first_record()["order_id"], "recovered-order")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_malformed_submission_and_search_replies_remain_unknown(self):
        self.enqueue()
        submit = self.venue.submit

        def malformed(plan, client_order_id):
            submit(plan, client_order_id)
            return []

        self.venue.submit = malformed
        self.assertEqual(self.process(), "unknown")
        self.venue.found = []
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.first_record()["status"], "unknown")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_malformed_known_order_reply_does_not_allow_resubmit(self):
        self.enqueue()
        self.venue.get = lambda _: ["invalid reply"]
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.first_record()["status"], "pending")

    def test_pending_order_is_read_until_terminal_without_new_submit(self):
        self.enqueue()
        self.venue.status = "OPEN"
        self.assertEqual(self.process(), "pending")
        self.enqueue("alert-2")
        self.assertEqual(self.process(), "pending")
        self.venue.status = "FILLED"
        self.assertEqual(self.process(), "complete")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.venue.lookups, ["order-1"] * 3)
        self.assertEqual(
            {r["event_id"]: r["status"] for r in records(self.path)},
            {"alert-1": "complete", "alert-2": "queued"},
        )

    def test_known_order_identity_mismatch_remains_blocking(self):
        self.enqueue()
        self.venue.identity_side = "SELL"
        self.assertEqual(self.process(), "unknown")
        self.enqueue("alert-2")
        self.assertEqual(self.process(), "unknown")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(self.first_record()["status"], "queued")
        self.assertEqual(records(self.path)[1]["status"], "pending")

    def test_expired_signal_never_reaches_venue(self):
        self.enqueue()
        self.assertEqual(
            process_one(
                self.path, self.venue, "default-portfolio", now=1301, allow_live=True
            ),
            "expired",
        )
        self.assertEqual(self.first_record()["status"], "expired")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)

    def test_interrupted_planning_is_refused_without_sending(self):
        self.enqueue()
        with database(self.path) as db, db:
            db.execute("UPDATE signals SET status='planning'")
        self.assertEqual(self.process(), "blocked")
        recover_planning(self.path)
        self.assertEqual(self.first_record()["status"], "refused")
        self.assertEqual(
            json.loads(self.first_record()["result"])["reason"],
            "interrupted_before_submission",
        )
        self.assertEqual(self.process(), "idle")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)

    def test_dry_run_service_cannot_submit_previously_queued_live_signal(self):
        self.enqueue(mode="live")
        self.assertEqual(self.process(allow_live=False), "disarmed")
        self.assertEqual(self.first_record()["status"], "queued")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)

    def test_portfolio_switch_refuses_old_queued_signal_before_planning(self):
        self.enqueue(mode="live")
        self.assertEqual(
            process_one(
                self.path,
                self.venue,
                "different-portfolio",
                now=1000,
                allow_live=True,
            ),
            "refused",
        )
        self.assertEqual(self.first_record()["status"], "refused")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)

    def test_disarmed_worker_does_not_plan_or_submit(self):
        self.enqueue()
        self.assertEqual(self.process(enabled=lambda: False), "disarmed")
        self.assertEqual(self.first_record()["status"], "queued")
        self.assertFalse(self.venue.plans)
        self.assertFalse(self.venue.submissions)


if __name__ == "__main__":
    unittest.main()

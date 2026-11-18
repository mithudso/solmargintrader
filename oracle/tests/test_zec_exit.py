"""Offline acceptance for a host-owned, one-shot ZEC exit mandate."""

from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from threading import Lock

from oracle.gum_orders import GumAmbiguous, GumError, GumOrders, b58encode
from oracle.tests.test_gum_orders import ACCOUNT, OWNER
from oracle.tests.test_gum_webhook_orders import LifecycleProvider, Venue
from oracle.zec_exit import (
    CloseMandate,
    PositionEvidence,
    ZecExitGuard,
    initialize_exit_ledger,
)


class CloseVenue(Venue):
    def __init__(self):
        super().__init__()
        self.position_side = "buy"
        self.position_size = "2"
        self.plan_changes = {}
        self.before_dispatch = lambda: None

    def plan(self, symbol, side, account_id):
        plan = super().plan(symbol, side, account_id)
        return (
            plan
            | {
                "symbol": symbol,
                "position_before": {
                    "side": self.position_side,
                    "size": self.position_size,
                    "isolated": True,
                },
                "collateral_native": 0,
                "price_cap": "99",
                "notional_cap": "200",
                "taker_fee_bps": "3.5",
                "max_slippage_bps": 50,
                "observed_at": time.time(),
                "market_timestamp": int(time.time()),
                "market_last_updated_ms": 1,
            }
            | self.plan_changes
        )

    def submit_leg(self, plan, client_id, *, enabled, deadline, approve_fresh):
        self.before_dispatch()
        if not enabled() or approve_fresh(plan) is not True:
            raise GumError("fixture_no_longer_authorized")
        return super().submit_leg(plan, client_id, enabled=enabled, deadline=deadline)


class DriftingMarket(LifecycleProvider):
    def __init__(self, second_quote):
        super().__init__()
        self.second_quote = second_quote
        self.quote_reads = 0

    def __call__(self, method, path, owner, body=None):
        if path == "/market/ZEC":
            self.quote_reads += 1
            if self.quote_reads == 2:
                self.market.update(self.second_quote)
        return super().__call__(method, path, owner, body)


class ZecCloseTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "exits.sqlite3"
        initialize_exit_ledger(self.path)
        self.lock = Lock()
        self.armed = True
        self.venue = CloseVenue()
        self.fingerprint = "a" * 64
        self.mandate = CloseMandate(
            mandate_id="first",
            binding=self.venue.binding,
            position_fingerprint=self.fingerprint,
            position_side="buy",
            quantity="2",
            expires_at=time.time() + 60,
            max_data_age_seconds=3,
            price_limit="98",
            max_notional_usd="210",
            max_taker_fee_bps="4",
            max_slippage_bps=50,
        )
        self.authority = {self.mandate.mandate_id: self.mandate}
        self.position_age = 0
        self.guard = self.make_guard()

    def position_evidence(self):
        return PositionEvidence(
            binding=self.venue.binding,
            fingerprint=self.fingerprint,
            side=self.venue.position_side,
            quantity=self.venue.position_size,
            observed_at=time.time() - self.position_age,
        )

    def make_guard(self, path=None):
        return ZecExitGuard(
            path or self.path,
            self.venue,
            lookup_mandate=self.authority.get,
            attest_position=self.position_evidence,
            enabled=lambda: self.armed,
            owner_lock=lambda: self.lock,
        )

    def test_durable_one_leg_before_dispatch_and_verified_settlement(self):
        def check_consumed():
            self.assertTrue(self.lock.locked())
            with closing(sqlite3.connect(self.path)) as db:
                row = db.execute("SELECT status FROM zec_exits").fetchone()
            self.assertEqual(row, ("submitting",))

        self.venue.before_dispatch = check_consumed
        result = self.guard.close("first")
        self.assertEqual(result["status"], "pending")
        plan, client_id = self.venue.submissions[0]
        self.assertEqual(client_id, result["client_order_id"])
        self.assertEqual(
            (plan["action"], plan["side"], plan["quantity"]), ("close", "sell", "2")
        )
        self.assertTrue(plan["reduce_only"])
        self.assertEqual(plan["collateral_native"], 0)
        reopened = self.make_guard()
        self.assertEqual(reopened.close("first"), result)
        self.venue.settled = False
        self.assertEqual(
            reopened.reconcile("first")["reason"], "close_awaiting_settlement"
        )
        self.venue.settled = True
        closed = reopened.reconcile("first")
        self.assertEqual(closed["status"], "closed")
        self.assertEqual(closed["receipt"]["position"]["size"], "0")
        self.assertEqual(len(self.venue.submissions), 1)
        self.assertEqual(len(self.venue.plans), 1)

    def test_disarmed_missing_expired_stale_and_reopened_positions_are_blocked(self):
        for variant in ("disarmed", "missing", "expired", "stale", "reopened"):
            with self.subTest(variant=variant):
                self.armed = variant != "disarmed"
                self.position_age = 4 if variant == "stale" else 0
                self.fingerprint = "b" * 64 if variant == "reopened" else "a" * 64
                mandate = (
                    replace(self.mandate, expires_at=time.time() - 1)
                    if variant == "expired"
                    else self.mandate
                )
                self.authority.clear()
                if variant != "missing":
                    self.authority["first"] = mandate
                self.assertEqual(self.guard.close("first")["status"], "blocked")
        self.assertEqual(self.venue.plans, [])
        self.assertEqual(self.venue.submissions, [])

    def test_refuses_reversals_wrong_size_and_economic_limit_breaches(self):
        for changes in (
            {"action": "open", "reduce_only": False},
            {"action": "noop"},
            {"quantity": "1"},
            {"collateral_native": 1},
            {"price_cap": "97.99"},
            {"notional_cap": "211"},
            {"taker_fee_bps": "4.01"},
            {"max_slippage_bps": 51},
            {"observed_at": time.time() - 4},
            {"market_timestamp": int(time.time()) - 4},
            {"market_last_updated_ms": 3500},
        ):
            with self.subTest(changes=changes):
                self.venue.plan_changes = changes
                self.assertEqual(self.guard.close("first")["status"], "blocked")
        self.assertEqual(self.venue.submissions, [])

    def test_short_uses_buy_ceiling_and_live_fingerprint(self):
        self.venue.position_side = "sell"
        self.authority["first"] = replace(
            self.mandate, position_side="sell", price_limit="101"
        )
        self.venue.plan_changes = {"price_cap": "101.01"}
        self.assertEqual(self.guard.close("first")["status"], "blocked")
        self.venue.plan_changes = {"price_cap": "101"}
        self.assertEqual(self.guard.close("first")["status"], "pending")
        self.assertEqual(self.venue.submissions[0][0]["side"], "buy")

    def test_revocation_during_adapter_validation_prevents_send(self):
        def revoke():
            self.authority.clear()

        self.venue.before_dispatch = revoke
        result = self.guard.close("first")
        self.assertEqual(result["status"], "refused")
        self.assertEqual(self.venue.submissions, [])
        self.assertEqual(self.make_guard().close("first"), result)

    def test_unknown_partial_and_changed_policy_require_reconciliation(self):
        self.venue.submit_error = GumAmbiguous("fixture_order_may_have_arrived")
        unknown = self.guard.close("first")
        self.assertEqual(unknown["status"], "unknown")
        self.assertEqual(self.make_guard().close("first"), unknown)

        prior_binding = self.venue.binding
        self.venue.binding = "changed-trading-policy"
        self.authority["second"] = replace(
            self.mandate, mandate_id="second", binding=self.venue.binding
        )
        self.assertEqual(
            self.guard.close("second")["reason"],
            "mandate_consumed_or_prior_close_unresolved",
        )
        self.assertEqual(self.guard.reconcile("first")["status"], "blocked")
        self.venue.binding = prior_binding
        self.authority["second"] = replace(self.mandate, mandate_id="second")
        self.venue.status = "cancelled"
        self.venue.receipt_change = {"filled_quantity": "1"}
        self.assertEqual(self.guard.reconcile("first")["status"], "partial")
        self.assertEqual(self.guard.close("second")["status"], "blocked")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_crash_between_submit_and_receipt_cannot_resubmit(self):
        self.venue.submit_error = SystemExit("fixture_process_died")
        with self.assertRaises(SystemExit):
            self.guard.close("first")
        self.assertEqual(self.make_guard().close("first")["status"], "unknown")
        self.assertEqual(self.make_guard().reconcile("first")["status"], "closed")
        self.assertEqual(len(self.venue.submissions), 1)

    def test_parallel_calls_consume_once(self):
        other = self.make_guard()
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(self.guard.close, "first")
            two = pool.submit(other.close, "first")
        self.assertEqual(one.result(), two.result())
        self.assertEqual(len(self.venue.submissions), 1)

    def actual_guard(self, provider, owner, signer, mandate_id="first"):
        provider.position(size="0.149")
        venue = GumOrders(
            owner,
            ACCOUNT,
            2,
            leverage="2",
            signer=signer,
            call=provider,
        )
        mandate = replace(
            self.mandate,
            mandate_id=mandate_id,
            binding=venue.binding,
            quantity="0.149",
            price_limit="994",
            max_notional_usd="150",
        )
        self.authority[mandate_id] = mandate

        def attest():
            position = venue.get_net_position()
            return PositionEvidence(
                binding=venue.binding,
                fingerprint=self.fingerprint,
                side=position["side"],
                quantity=position["size"],
                observed_at=time.time(),
            )

        return ZecExitGuard(
            self.path,
            venue,
            lookup_mandate=self.authority.get,
            attest_position=attest,
            enabled=lambda: True,
            owner_lock=lambda: self.lock,
        )

    def test_fresh_quote_drift_refuses_before_signing_or_sending(self):
        for mandate_id, changes in (
            ("fee", {"takerFeeBps": 4.25}),
            ("notional", {"markPrice": 1020}),
            ("reconciliation_fee", {"takerFeeBps": 3.75}),
        ):
            with self.subTest(changes=changes):
                provider = DriftingMarket(changes)
                signed = []
                guard = self.actual_guard(provider, OWNER, signed.append, mandate_id)
                self.assertEqual(
                    guard.close(mandate_id)["reason"], "close_definitely_unsent"
                )
                self.assertEqual(provider.quote_reads, 2)
                self.assertFalse(signed)
                self.assertFalse(any(call[0] == "POST" for call in provider.calls))

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_actual_adapter_only_emits_one_signed_close_to_offline_fixture(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        provider = LifecycleProvider()
        guard = self.actual_guard(
            provider, b58encode(key.public_key().public_bytes_raw()), key.sign
        )
        self.assertEqual(guard.close("first")["status"], "pending")
        self.assertEqual(
            guard.reconcile("first")["reason"], "close_awaiting_settlement"
        )
        provider.settle()
        self.assertEqual(guard.reconcile("first")["status"], "closed")
        posts = [call[3] for call in provider.calls if call[0] == "POST"]
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["side"], "Ask")
        self.assertIs(posts[0]["reduceOnly"], True)
        self.assertEqual(posts[0]["collateralAmount"], 0)

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_revocation_after_signing_is_checked_before_post(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        provider = LifecycleProvider()
        signatures = []

        def sign_and_revoke(message):
            frozen_signature = key.sign(message)
            signatures.append(frozen_signature)
            self.authority.clear()
            return frozen_signature

        guard = self.actual_guard(
            provider, b58encode(key.public_key().public_bytes_raw()), sign_and_revoke
        )
        self.assertEqual(guard.close("first")["reason"], "close_definitely_unsent")
        self.assertEqual(len(signatures), 1)
        self.assertFalse(any(call[0] == "POST" for call in provider.calls))

    def test_requires_existing_private_ledger_and_rejects_symlinks(self):
        missing = self.path.with_name("missing.sqlite3")
        with self.assertRaises(FileNotFoundError):
            self.make_guard(missing)
        self.assertFalse(missing.exists())
        with self.assertRaises(FileExistsError):
            initialize_exit_ledger(self.path)
        symlink = self.path.with_name("link.sqlite3")
        symlink.symlink_to(self.path)
        with self.assertRaises(OSError):
            self.make_guard(symlink)
        self.path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "ledger_not_private"):
            self.make_guard()
        with self.assertRaisesRegex(ValueError, "ledger_not_private"):
            self.guard.close("first")

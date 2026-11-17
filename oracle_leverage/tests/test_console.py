"""Guards for the trading UI boundary; venues remain fixtures."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage.console import VENUES, Console, valid_signature

ADDRESS = "1" * 32
SIGNATURE = "3" * 87


class FakeCLI:
    def __init__(self):
        self.executed = 0
        self.closed = 0
        self.address = ADDRESS
        self.fail = False
        self.missing_fee = False
        self.signed = 0

    def wallet(self):
        return {
            "address": self.address,
            "name": "owner",
            "type": "solana",
            "active": True,
        }

    def preview(self, asset, side, amount, *, key_name=None):
        result = {
            "sizeUsd": 100,
            "entryPriceUsd": 100,
            "liquidationPriceUsd": 91,
            "openFeeUsd": 0.06,
        }
        if self.missing_fee:
            result.pop("openFeeUsd")
        return result

    def positions(self, *, key_name=None):
        return {
            "positions": [{"positionPubkey": "2" * 32, "asset": "BTC", "side": "long"}]
        }

    def execute(self, asset, side, amount, *, key_name=None):
        self.executed += 1
        if self.fail:
            raise RuntimeError("ambiguous fixture after send")
        return {"signature": SIGNATURE}

    def close(self, identity, *, key_name=None):
        self.closed += 1
        return {"signature": SIGNATURE}

    def sign_transaction(self, transaction, *, key_name):
        self.signed += 1
        return {"signer": self.address, "signedTransaction": "fixture-signed"}


class FakeSDK:
    def __init__(self):
        self.calls = []
        self.fail_execute = False

    def call(self, payload):
        self.calls.append(payload["action"])
        action = payload["action"]
        if action == "service-positions":
            return {
                "status": "ready",
                "queued": "0",
                "claims": [],
                "positions": [
                    {
                        "address": "2" * 32,
                        "owner": ADDRESS,
                        "asset": "ZEC",
                        "isLong": True,
                        "notional": "5000000000",
                    }
                ],
            }
        if action in ("service-build-open", "service-build-close"):
            return {
                "status": "ready",
                "build": {"serializedTxBase64": "fixture-unsigned"},
                "checked": {
                    "program": "yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA",
                    "owner": payload["owner"],
                    "asset": payload["asset"],
                    "side": payload.get("side"),
                    "margin": payload.get("margin"),
                    "leverage": 1000,
                    "position": "2" * 32,
                },
                "fees": {"closeFeePpm": 20, "winFeePpm": 30000},
            }
        if action == "service-signed":
            return {"status": "ready", "signature": SIGNATURE}
        if action == "service-execute":
            if self.fail_execute:
                raise RuntimeError("ambiguous fixture after transmission")
            return {
                "status": "submitted",
                "signature": SIGNATURE,
                "service_status": "Processing",
                "queue_position": 2,
            }
        raise AssertionError(action)


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "home"
        self.cli = FakeCLI()
        self.sdk = FakeSDK()
        self.now = time.time()
        self.console = Console(
            self.home, cli=self.cli, sdk=self.sdk, clock=lambda: self.now
        )
        self.console.store.put_meta("venue_reconciled_at", self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def arm(self, **updates):
        path = self.home / "config.json"
        path.write_text(
            json.dumps(
                {
                    "armed": True,
                    "wallet_address": ADDRESS,
                    "max_collateral_usd": 10,
                    **updates,
                }
            )
        )
        path.chmod(0o600)

    def preview(self):
        result = self.console.preview("BTC", VENUES[0], "long", "10")
        self.assertEqual(result["status"], "ready")
        return result["preview_id"]

    def test_explicit_venue_arming_is_atomic_public_and_independent(self):
        result = self.console.set_venue_armed(VENUES[0], True, "12")
        self.assertEqual(result["status"], "armed")
        self.assertEqual(self.console.config()["enabled_venues"], [VENUES[0]])
        self.assertEqual(
            self.console.config()["venue_collateral_caps"][VENUES[0]], "12"
        )
        self.assertEqual((self.home / "config.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.cli.signed + self.cli.executed, 0)
        self.assertEqual(
            self.console.set_venue_armed(VENUES[1], True, "5")["status"], "armed"
        )
        self.assertTrue(self.console.config()["sdk"]["enabled"])
        self.assertEqual(
            self.console.set_venue_armed(VENUES[0], False, "")["status"], "disarmed"
        )
        self.assertEqual(self.console.config()["enabled_venues"], [VENUES[1]])
        self.assertTrue(self.console.config()["armed"])
        preview = self.preview()
        self.assertEqual(self.console.execute(preview)["status"], "blocked")
        self.assertEqual(self.cli.executed, 0)

    def test_arming_never_clears_unknown_intent(self):
        self.console.store.put_intent("unknown-1", "submit", "unknown", {}, {})
        self.assertEqual(
            self.console.set_venue_armed(VENUES[0], True, "10")["status"], "armed"
        )
        self.assertEqual(self.console.store.intent("unknown-1")["status"], "unknown")
        self.assertEqual(self.cli.signed + self.cli.executed, 0)

    def test_arming_rejects_invalid_caps_and_wallet_change(self):
        self.assertEqual(
            self.console.set_venue_armed(VENUES[0], True, "NaN")["status"], "blocked"
        )
        self.assertEqual(
            self.console.set_venue_armed(VENUES[0], True, "10")["status"], "armed"
        )
        self.cli.address = "2" * 32
        self.assertEqual(
            self.console.set_venue_armed(VENUES[1], True, "5")["status"], "blocked"
        )
        self.assertEqual(self.console.config()["enabled_venues"], [VENUES[0]])

    def test_disarmed_submit_does_not_call_execute(self):
        self.assertEqual(self.console.execute(self.preview())["status"], "blocked")
        self.assertEqual(self.cli.executed, 0)

    def test_standard_zec_is_blocked_and_sdk_build_is_unsigned(self):
        self.assertEqual(
            self.console.preview("ZEC", VENUES[0], "short", 10)["status"], "blocked"
        )
        self.assertEqual(
            self.console.preview("ZEC", VENUES[1], "short", 5)["status"], "ready"
        )
        self.assertEqual(self.cli.signed, 0)

    def test_sdk_requires_both_arming_and_explicit_venue_enable(self):
        identity = self.console.preview("ZEC", VENUES[1], "short", 5)["preview_id"]
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.arm()
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.assertEqual(self.cli.signed, 0)

    def test_sdk_submit_uses_checked_signed_bytes_and_persists_processing(self):
        self.arm(sdk={"enabled": True})
        identity = self.console.preview("ZEC", VENUES[1], "short", 5)["preview_id"]
        result = self.console.execute(identity)
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(self.cli.signed, 1)
        self.assertEqual(self.sdk.calls[-2:], ["service-signed", "service-execute"])
        self.assertEqual(self.console.store.intent(identity)["status"], "submitted")
        self.assertEqual(self.console.execute(identity)["status"], "blocked")

    def test_sdk_unknown_outcome_preserves_signature_and_can_reconcile(self):
        self.arm(sdk={"enabled": True})
        self.sdk.fail_execute = True
        identity = self.console.preview("BTC", VENUES[1], "long", 5)["preview_id"]
        self.assertEqual(self.console.execute(identity)["status"], "unknown")
        intent = self.console.store.intent(identity)
        self.assertEqual(json.loads(intent["response_json"])["signature"], SIGNATURE)
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.now += 20
        self.console._signature_statuses = lambda signatures, cfg: [
            {"confirmationStatus": "confirmed", "err": None}
        ]
        self.console.reconcile()
        self.assertEqual(self.console.store.intent(identity)["status"], "confirmed")

    def test_sdk_close_routes_by_tagged_owned_position(self):
        self.arm(sdk={"enabled": True})
        result = self.console.close("1000x:" + "2" * 32)
        self.assertEqual(result["status"], "submitted")
        self.assertEqual(self.cli.closed, 0)
        self.assertEqual(
            self.sdk.calls[-3:],
            ["service-build-close", "service-signed", "service-execute"],
        )

    def test_missing_fee_is_not_replaced_with_zero(self):
        self.cli.missing_fee = True
        self.assertEqual(
            self.console.preview("BTC", VENUES[0], "long", 10)["status"], "error"
        )

    def test_preview_exposes_reviewable_order_amount_price_and_fee(self):
        result = self.console.preview("BTC", VENUES[0], "long", 10)
        self.assertEqual(result["leverage"], 10)
        self.assertEqual(result["collateral_usd"], "10")
        self.assertIn("100 USD position", result["message"])
        self.assertIn("opening fee $0.06", result["message"])

    def test_keeper_mismatch_falls_back_to_non_executable_unsigned_inspection(self):
        from oracle_leverage.cli import AdapterError

        calls = []

        def inspect(payload):
            calls.append(payload["action"])
            if payload["action"] == "service-build-open":
                raise AdapterError("service_keeper_mismatch")
            return {
                "status": "inspection",
                "simulation": {"status": "passed"},
                "checked": {
                    "program": "yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA",
                    "owner": ADDRESS,
                    "asset": "ZEC",
                    "side": "short",
                    "margin": "10000000",
                    "leverage": 1000,
                },
                "fees": {"closeFeePpm": 20, "winFeePpm": 30000},
            }

        with patch.object(self.sdk, "call", side_effect=inspect):
            result = self.console.preview("ZEC", VENUES[1], "short", "10")
        self.assertEqual(calls, ["service-build-open", "service-inspect-open"])
        self.assertEqual(result["status"], "inspection")
        self.assertNotIn("preview_id", result)
        self.assertIn("Submit is unavailable", result["message"])
        self.assertIn("JupUSD", result["message"])
        self.assertEqual(self.cli.signed + self.cli.executed, 0)
        self.assertEqual(self.console.store.intents(), [])

    def test_mismatched_inspection_is_rejected(self):
        from oracle_leverage.cli import AdapterError

        results = [
            AdapterError("service_keeper_mismatch"),
            {
                "status": "inspection",
                "simulation": {"status": "passed"},
                "checked": {"owner": "wrong"},
            },
        ]
        with patch.object(self.sdk, "call", side_effect=results):
            result = self.console.preview("ZEC", VENUES[1], "short", "10")
        self.assertEqual(result["status"], "error")
        self.assertNotIn("preview_id", result)
        self.assertEqual(self.cli.signed + self.cli.executed, 0)

    def test_malformed_inspection_simulation_is_handled_safely(self):
        from oracle_leverage.cli import AdapterError

        response = {
            "status": "inspection",
            "simulation": None,
            "checked": {
                "program": "yoLovHV5eT4DNPMG2Bu1NLmq8nVygEAPrNT1Rx6vWFA",
                "owner": ADDRESS,
                "asset": "ZEC",
                "side": "short",
                "margin": "10000000",
                "leverage": 1000,
            },
        }
        with patch.object(
            self.sdk,
            "call",
            side_effect=[AdapterError("service_keeper_mismatch"), response],
        ):
            result = self.console.preview("ZEC", VENUES[1], "short", "10")
        self.assertEqual(result["status"], "error")
        self.assertNotIn("preview_id", result)
        self.assertEqual(self.cli.signed + self.cli.executed, 0)

    def test_sdk_keeper_mismatch_explains_safe_preview_block(self):
        from oracle_leverage.cli import AdapterError

        with patch.object(
            self.sdk, "call", side_effect=AdapterError("service_keeper_mismatch")
        ):
            result = self.console.preview("ZEC", VENUES[1], "short", "10")
        self.assertEqual(result["status"], "error")
        self.assertIn("keeper signer", result["message"])
        self.assertIn("no order was signed or submitted", result["message"].lower())
        self.assertEqual(self.cli.signed + self.cli.executed, 0)

    def test_known_insufficient_funds_error_is_actionable_without_raw_output(self):
        from oracle_leverage.cli import AdapterError

        def fail(*args, **kwargs):
            raise AdapterError("jupiter_insufficient_funds")

        self.cli.preview = fail
        result = self.console.preview("BTC", VENUES[0], "long", 10)
        self.assertIn("USDC collateral", result["message"])
        self.assertIn("SOL network balance", result["message"])
        self.assertEqual(self.cli.executed, 0)

    def test_wallet_change_or_cap_prevents_funded_call(self):
        identity = self.preview()
        self.arm()
        self.cli.address = "2" * 32
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.assertEqual(self.cli.executed, 0)
        self.cli.address = ADDRESS
        self.arm(max_collateral_usd=5)
        self.assertEqual(self.console.execute(identity)["status"], "blocked")

    def test_success_is_journalled_and_replay_is_never_automatic(self):
        self.assertTrue(valid_signature(SIGNATURE))
        identity = self.preview()
        self.arm()
        self.assertEqual(self.console.execute(identity)["status"], "submitted")
        self.assertEqual(self.console.store.intent(identity)["status"], "submitted")
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.assertEqual(self.cli.executed, 1)

    def test_exception_after_dispatch_is_durable_unknown(self):
        identity = self.preview()
        self.arm()
        self.cli.fail = True
        self.assertEqual(self.console.execute(identity)["status"], "unknown")
        self.assertEqual(self.console.store.intent(identity)["status"], "unknown")
        self.assertEqual(self.console.execute(self.preview())["status"], "blocked")
        self.assertEqual(self.cli.executed, 1)

    def test_unresolved_intent_older_than_ui_history_still_blocks(self):
        self.arm()
        self.console.store.put_intent("old", "open", "unknown", {}, {})
        for n in range(105):
            self.console.store.put_intent(str(n), "preview", "ready", {}, {})
        self.assertEqual(self.console.execute(self.preview())["status"], "blocked")
        self.assertEqual(self.cli.executed, 0)

    def test_expired_preview_and_unknown_position_refuse(self):
        identity = self.preview()
        self.arm()
        self.now += 31
        self.assertEqual(self.console.execute(identity)["status"], "blocked")
        self.console.store.put_meta("venue_reconciled_at", self.now)
        self.assertEqual(self.console.close("9" * 32)["status"], "blocked")
        self.assertEqual(self.cli.closed, 0)

    def test_stopped_heartbeat_never_claims_running(self):
        self.console.store.put_meta("heartbeat", {"at": self.now, "status": "stopped"})
        self.assertEqual(self.console.snapshot()["status"], "paper-forward-stopped")
        self.console.store.put_meta(
            "heartbeat",
            {
                "at": self.now,
                "status": "running",
                "assets": {"BTC": {"error": "stale_quote"}},
            },
        )
        self.assertEqual(self.console.snapshot()["status"], "paper-forward-degraded")

    def test_full_transaction_wallet_and_configured_mismatch_are_visible(self):
        self.assertEqual(self.console.snapshot()["wallet"]["address"], ADDRESS)
        self.arm(wallet_address="2" * 32)
        wallet = self.console.snapshot()["wallet"]
        self.assertEqual(wallet["address"], ADDRESS)
        self.assertEqual(wallet["configured_address"], "2" * 32)
        self.assertEqual(wallet["status"], "mismatch")

    def test_wallet_read_error_is_unavailable_not_an_empty_confirmed_wallet(self):
        self.cli.wallet = lambda: (_ for _ in ()).throw(
            RuntimeError("fixture unavailable")
        )
        wallet = self.console.snapshot()["wallet"]
        self.assertEqual(wallet["status"], "unavailable")
        self.assertIsNone(wallet["address"])

    def test_dual_prices_compare_only_fresh_aligned_quotes_and_never_substitute_coinbase(
        self,
    ):
        def quote(price, age=0):
            return {
                "price": price,
                "exchange_at": self.now - age,
                "received_at": self.now - age,
            }

        data = {
            "at": self.now,
            "status": "streaming",
            "connected": {"jupiter": True, "coinbase": True},
            "feeds": {
                "jupiter": {"BTC": quote(100.1)},
                "coinbase": {"BTC": quote(100)},
            },
        }
        self.console.store.put_meta("dual_quotes", data)
        pair = self.console.price_comparison()["pairs"]["BTC"]
        self.assertAlmostEqual(pair["basis_bps"], 10)
        self.assertEqual(pair["primary_1000x_price"], 100.1)
        data["feeds"]["jupiter"]["BTC"] = quote(100.1, 2)
        self.console.store.put_meta("dual_quotes", data)
        pair = self.console.price_comparison()["pairs"]["BTC"]
        self.assertIsNone(pair["basis_bps"])
        self.assertIsNone(pair["primary_1000x_price"])
        data["feeds"]["jupiter"]["BTC"] = quote(100.1)
        data["feeds"]["coinbase"]["BTC"] = quote(100, 1.5)
        self.console.store.put_meta("dual_quotes", data)
        self.assertIsNone(self.console.price_comparison()["pairs"]["BTC"]["basis_bps"])

    def test_dead_dual_collector_cannot_leave_fresh_quotes_in_snapshot(self):
        quote = {"price": 100, "exchange_at": self.now, "received_at": self.now}
        self.console.store.put_meta(
            "dual_quotes",
            {
                "at": self.now - 3,
                "status": "streaming",
                "connected": {"jupiter": True, "coinbase": True},
                "feeds": {"jupiter": {"BTC": quote}, "coinbase": {"BTC": quote}},
            },
        )
        comparison = self.console.price_comparison()
        self.assertEqual(comparison["status"], "stale")
        self.assertFalse(comparison["pairs"]["BTC"]["comparable"])

    def test_zero_signature_and_unsafe_config_are_rejected(self):
        self.assertFalse(valid_signature("1" * 64))
        self.arm()
        (self.home / "config.json").chmod(0o644)
        with self.assertRaisesRegex(ValueError, "owner-only"):
            self.console.config()

    def test_missing_position_envelope_cannot_become_an_empty_wallet(self):
        self.arm()
        self.cli.positions = lambda **kwargs: {"error": "fixture"}
        self.assertEqual(self.console.execute(self.preview())["status"], "blocked")
        self.assertEqual(self.cli.executed, 0)

    def test_incomplete_rpc_state_never_resolves_a_submission(self):
        self.arm()
        identity = self.preview()
        self.assertEqual(self.console.execute(identity)["status"], "submitted")
        self.now += 20
        self.console._signature_statuses = lambda signatures, cfg: [
            {"confirmationStatus": "confirmed"}
        ]
        self.console.reconcile()
        self.assertEqual(self.console.store.intent(identity)["status"], "submitted")
        self.now += 20
        self.console._signature_statuses = lambda signatures, cfg: [
            {"confirmationStatus": "confirmed", "err": None}
        ]
        self.console.reconcile()
        self.assertEqual(self.console.store.intent(identity)["status"], "confirmed")

    def test_invalid_rpc_error_type_preserves_unknown_quarantine(self):
        self.arm()
        self.console.store.put_intent(
            "uncertain", "open", "unknown", {}, {"signature": SIGNATURE}
        )
        for error in (False, 0, [], "", {}):
            self.now += 20
            self.console._signature_statuses = lambda signatures, cfg, error=error: [
                {"confirmationStatus": "confirmed", "err": error}
            ]
            self.console.reconcile()
            self.assertEqual(
                self.console.store.intent("uncertain")["status"], "unknown"
            )


if __name__ == "__main__":
    unittest.main()

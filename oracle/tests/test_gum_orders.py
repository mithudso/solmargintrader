from __future__ import annotations

import copy
import importlib.util
import time
import unittest
from decimal import Decimal
from unittest.mock import patch

from oracle.gum_orders import (
    MARKET_ID,
    GumAmbiguous,
    GumError,
    GumOrders,
    action_message,
    b58decode,
    b58encode,
    discover,
)

OWNER = b58encode(bytes([7]) * 32)
ACCOUNT = b58encode(bytes([9]) * 32)
ISOLATED = b58encode(bytes([10]) * 32)
BLOCKHASH = b58encode(bytes([8]) * 32)
CLIENT_ID = "18446744073709551615"

# Generated with official gum-perp-sdk 0.2.0 SignableTradingRequest::message_to_sign
# at commit08bc398d78350a49ae047ecbdd3ffc6233c082d3. See action.rs/request.rs.
PREFIX = "08080808080808080808080808080808080808080808080808080808080808080afd23d1134d8b39513c49c67720abbffa8addf50eb783a890bab5fb6473bedb0107070707070707070707070707070707070707070707070707070707070707072e"
OPEN_VECTOR = (
    PREFIX
    + "1ec06878040000000002030000005a4543a18601000000000095000000000000000001000201ffffffffffffffff"
)
CLOSE_VECTOR = (
    PREFIX
    + "1e000000000000000002030000005a4543a18601000000000095000000000000000101010201ffffffffffffffff"
)


class Provider:
    def __init__(self):
        self.calls = []
        self.market = {
            "symbol": "ZEC",
            "pubkey": MARKET_ID,
            "baseDecimals": 6,
            "baseLotSize": 1000,
            "quoteLotSize": 10,
            "tickSize": 0.01,
            "stepSize": 0.001,
            "bestBid": 999.99,
            "bestAsk": 1000,
            "markPrice": 1000,
            "indexPrice": 1000,
            "maxAccountPositionNotional": 100000,
            "takerFeeBps": 3.5,
            "maxLeverage": 50,
            "timestamp": int(time.time()),
            "lastUpdatedMs": 1,
            "riskTiers": [{"notionalCap": 10000, "maxLeverage": 50}],
            "orderLimitConfig": {
                "market": {
                    "minOrderQty": 0.001,
                    "minOrderNotional": 5,
                    "maxOpenOrderQty": 25,
                    "maxCloseOrderQty": 25,
                    "maxOpenOrderNotional": 20000,
                    "maxCloseOrderNotional": 20000,
                }
            },
        }
        self.balance = {
            "freeBalance": "100",
            "availableToTrade": "100",
            "tokenBalance": 100000000,
        }
        self.idle_balance = {
            "freeBalance": "0",
            "availableToTrade": "0",
            "tokenBalance": 0,
        }
        self.account_rows = [
            {"pubkey": ACCOUNT, "subaccountId": 2, "isolated": False, "market": None}
        ]
        self.positions, self.orders, self.history = [], [], []
        self.direct_positions = None
        self.exists = True
        self.response_error = False
        self.preferences = []

    def isolated_account(self):
        self.account_rows.append(
            {"pubkey": ISOLATED, "subaccountId": 2, "isolated": True, "market": "ZEC"}
        )

    def position(self, side="Bid", size="0.149"):
        self.isolated_account()
        self.positions = [
            {
                "symbol": "ZEC",
                "isolated": True,
                "side": side,
                "size": size,
                "collateral": "75",
            }
        ]

    def __call__(self, method, path, owner, body=None):
        self.calls.append((method, path, owner, copy.deepcopy(body)))
        if path == "/health":
            result = {"trading_available": True}
        elif path == "/market/ZEC":
            result = self.market
        elif path == "/tradingAccount":
            result = {"exists": self.exists, "accounts": self.account_rows}
        elif path == f"/tradingAccount/{ACCOUNT}/positions":
            result = self.positions
        elif path == f"/tradingAccount/{ISOLATED}/positions":
            result = (
                self.direct_positions
                if self.direct_positions is not None
                else self.positions
            )
        elif path.endswith("/orders"):
            result = self.orders
        elif path.endswith("/leverage"):
            result = self.preferences
        elif path == f"/tradingAccount/{ACCOUNT}/balances":
            result = self.balance
        elif path == f"/tradingAccount/{ISOLATED}/balances":
            result = self.idle_balance
        elif "/orderHistory?" in path:
            result = {"orders": self.history}
        elif path == "/blockhash":
            result = {"blockhash": BLOCKHASH}
        elif method == "POST" and path == "/order/create":
            if self.response_error:
                raise OSError("lost response")
            result = {"symbol": "ZEC", "clientOrderId": body["clientOrderId"]}
        else:
            raise AssertionError((method, path))
        return copy.deepcopy(result)


class GumOrderTests(unittest.TestCase):
    def setUp(self):
        self.provider = Provider()
        self.venue = GumOrders(OWNER, ACCOUNT, 2, leverage="2", call=self.provider)

    def test_official_sdk_golden_open_and_reduce_only_actions(self):
        for side, reduce, budget, expected in (
            ("buy", False, 75000000, OPEN_VECTOR),
            ("sell", True, 0, CLOSE_VECTOR),
        ):
            with self.subTest(side=side):
                message = action_message(
                    OWNER,
                    BLOCKHASH,
                    subaccount_id=2,
                    price_lots=100001,
                    base_lots=149,
                    side=side,
                    reduce_only=reduce,
                    collateral_native=budget,
                    client_order_id=CLIENT_ID,
                )
                self.assertEqual(message.hex(), expected)

    def test_action_rejects_client_overflow_and_reduce_collateral(self):
        for client, collateral, reduce in (
            ("18446744073709551616", 0, False),
            ("0", 0, False),
            ("001", 0, False),
            ("1", 1, True),
        ):
            with self.assertRaises(GumError):
                action_message(
                    OWNER,
                    BLOCKHASH,
                    subaccount_id=2,
                    price_lots=1,
                    base_lots=1,
                    side="buy",
                    reduce_only=reduce,
                    collateral_native=collateral,
                    client_order_id=client,
                )

    def test_invalid_or_noncanonical_identity_refused(self):
        for value in ("", "0" * 44, "111", OWNER + "1"):
            with self.assertRaises(GumError):
                b58decode(value)

    def test_discovery_reports_absent_accounts_without_signing(self):
        self.provider.account_rows = []
        self.provider.exists = False
        result = discover(OWNER, call=self.provider)
        self.assertFalse(result["accounts"]["exists"])
        self.assertTrue(all(call[0] == "GET" for call in self.provider.calls))
        with self.assertRaisesRegex(GumError, "account_missing"):
            self.venue.preflight()

    def test_open_caps_effective_leverage_after_fees(self):
        plan = self.venue.plan("CRYPTO:ZECUSD", "buy", ACCOUNT)
        self.assertEqual(plan["action"], "open")
        self.assertEqual(plan["collateral_native"], 75000000)
        self.assertEqual(plan["price_cap"], "1005.00")
        self.assertEqual(plan["quantity"], "0.147")
        collateral = Decimal(plan["collateral_native"]) / 1000000
        notional, fee = (
            Decimal(plan["notional_cap"]),
            Decimal(plan["estimated_open_fee_usdc"]),
        )
        adverse = Decimal(plan["quantity"]) * (
            Decimal(plan["price_cap"]) - Decimal("999.99")
        )
        self.assertLessEqual(notional / (collateral - fee - adverse), 2)
        self.assertTrue(plan["isolated"])
        self.assertFalse(plan["reduce_only"])

    def test_notional_allocation_does_not_turn_75_into_150_percent(self):
        venue = GumOrders(
            OWNER,
            ACCOUNT,
            2,
            leverage="2",
            allocation_basis="notional",
            call=self.provider,
        )
        plan = venue.plan("ZEC", "sell", ACCOUNT)
        self.assertEqual(plan["collateral_native"], 37500000)
        self.assertLessEqual(Decimal(plan["notional_cap"]), 75)
        self.assertLess(Decimal(plan["price_cap"]), Decimal("999.99"))

    def test_reversal_closes_exact_position_without_new_collateral(self):
        self.provider.position("Bid", "1.234")
        plan = self.venue.plan("ZECUSD", "sell", ACCOUNT)
        self.assertEqual(
            (plan["action"], plan["side"], plan["target_side"]),
            ("close", "sell", "sell"),
        )
        self.assertEqual(plan["quantity"], "1.234")
        self.assertEqual(plan["collateral_native"], 0)
        self.assertTrue(plan["reduce_only"])
        self.assertEqual(self.venue.plan("ZEC", "buy", ACCOUNT)["action"], "noop")

    def test_policy_binding_changes_for_account_leverage_and_basis(self):
        self.assertNotEqual(
            self.venue.binding,
            GumOrders(OWNER, ACCOUNT, 2, leverage="3", call=self.provider).binding,
        )
        self.assertNotEqual(
            self.venue.binding,
            GumOrders(
                OWNER,
                ACCOUNT,
                2,
                leverage="2",
                allocation_basis="notional",
                call=self.provider,
            ).binding,
        )

    def test_explicit_preference_required_for_higher_tier_but_not_small_default(self):
        self.provider.market["riskTiers"] = [
            {"notionalCap": 100, "maxLeverage": 50},
            {"notionalCap": 10000, "maxLeverage": 25},
        ]
        with self.assertRaisesRegex(GumError, "risk_tier_configuration"):
            self.venue.plan("ZEC", "buy", ACCOUNT)
        self.provider.preferences = [{"symbol": "ZEC", "isolated": True, "leverage": 2}]
        self.assertEqual(self.venue.plan("ZEC", "buy", ACCOUNT)["action"], "open")
        self.provider.preferences[0]["leverage"] = 1
        with self.assertRaisesRegex(GumError, "preference_too_low"):
            self.venue.plan("ZEC", "buy", ACCOUNT)

    def test_price_caps_round_towards_stricter_slippage(self):
        self.provider.market.update(bestAsk=987.23, bestBid=987.22, markPrice=987.22)
        venue = GumOrders(
            OWNER, ACCOUNT, 2, leverage="2", max_slippage_bps=10, call=self.provider
        )
        self.assertEqual(venue.plan("ZEC", "buy", ACCOUNT)["price_cap"], "988.21")
        self.assertEqual(venue.plan("ZEC", "sell", ACCOUNT)["price_cap"], "986.24")

    def test_sell_risk_budget_includes_book_above_mark_and_adverse_fill(self):
        self.provider.market.update(bestAsk=1001, bestBid=1000, markPrice=990)
        venue = GumOrders(
            OWNER, ACCOUNT, 2, leverage="2", max_slippage_bps=10, call=self.provider
        )
        plan = venue.plan("ZEC", "sell", ACCOUNT)
        quantity, cap = Decimal(plan["quantity"]), Decimal(plan["price_cap"])
        equity = (
            Decimal(75)
            - quantity * (Decimal(1001) - cap)
            - quantity * Decimal(1001) * Decimal("0.00035")
        )
        self.assertLessEqual(quantity * Decimal(1001) / equity, 2)

    def test_wrong_asset_account_and_market_are_refused(self):
        for symbol in ("SOLUSD", "ZECUSDT", "BTC", "ZEC-EUR"):
            with self.assertRaises(GumError):
                self.venue.plan(symbol, "buy", ACCOUNT)
        with self.assertRaises(GumError):
            self.venue.plan("ZEC", "buy", ISOLATED)
        self.provider.market["pubkey"] = ACCOUNT
        with self.assertRaisesRegex(GumError, "market_identity"):
            self.venue.preflight()

    def test_stale_quote_fee_and_size_limits_are_not_guessed(self):
        for key, value in (
            ("timestamp", int(time.time()) - 30),
            ("takerFeeBps", None),
            ("lastUpdatedMs", 6000),
        ):
            with self.subTest(key=key):
                saved = self.provider.market[key]
                self.provider.market[key] = value
                with self.assertRaises(GumError):
                    self.venue.plan("ZEC", "buy", ACCOUNT)
                self.provider.market[key] = saved
        self.provider.market["orderLimitConfig"]["market"]["maxOpenOrderQty"] = 0.1
        with self.assertRaisesRegex(GumError, "order_limit"):
            self.venue.plan("ZEC", "buy", ACCOUNT)

    def test_open_orders_and_shared_cross_positions_refuse(self):
        self.provider.orders = [{"symbol": "ZEC"}]
        with self.assertRaisesRegex(GumError, "open_orders"):
            self.venue.plan("ZEC", "buy", ACCOUNT)
        self.provider.orders = []
        self.provider.positions = [
            {"symbol": "ZEC", "side": "Bid", "size": "1", "isolated": False}
        ]
        with self.assertRaisesRegex(GumError, "foreign_or_cross"):
            self.venue.plan("ZEC", "sell", ACCOUNT)

    def test_missing_isolated_snapshot_is_not_treated_as_flat(self):
        self.provider.position()
        self.provider.direct_positions = []
        with self.assertRaisesRegex(GumError, "inconsistent_isolated"):
            self.venue.get_net_position()

    def test_idle_isolated_collateral_refuses_an_extra_deposit(self):
        self.provider.isolated_account()
        self.provider.idle_balance["tokenBalance"] = 2000000
        with self.assertRaisesRegex(GumError, "idle_isolated_collateral"):
            self.venue.plan("ZEC", "buy", ACCOUNT)

    def history(self, plan, status="filled", filled=None):
        self.provider.history = [
            {
                "orderId": "123",
                "clientOrderId": CLIENT_ID,
                "symbol": "ZEC",
                "side": "Bid" if plan["side"] == "buy" else "Ask",
                "isolated": True,
                "reduceOnly": plan["reduce_only"],
                "orderType": "market",
                "timeInForce": "fok",
                "originalSize": plan["quantity"],
                "filledSize": plan["quantity"] if filled is None else filled,
                "initialCollateral": str(Decimal(plan["collateral_native"]) / 1000000),
                "executedCollateral": "-75" if plan["reduce_only"] else "75",
                "status": status,
                "transactions": [
                    {
                        "type": "fill",
                        "signature": b58encode(bytes([11]) * 64),
                        "timestamp": int(time.time()),
                        "price": plan["price_cap"],
                        "size": plan["quantity"] if filled is None else filled,
                        "fee": str(
                            Decimal(plan["price_cap"])
                            * Decimal(plan["quantity"] if filled is None else filled)
                            * Decimal("0.00035")
                        ),
                        "role": "taker",
                    }
                ],
            }
        ]

    def test_reconciliation_never_infers_absent_order_or_partial_fill_success(self):
        plan = self.venue.plan("ZEC", "buy", ACCOUNT)
        self.assertEqual(self.venue.reconcile(plan, CLIENT_ID)["status"], "unknown")
        self.history(plan, "partially_filled_cancelled", "0.001")
        self.assertEqual(self.venue.reconcile(plan, CLIENT_ID)["status"], "cancelled")
        self.provider.history[0]["side"] = "Ask"
        with self.assertRaisesRegex(GumError, "order_identity"):
            self.venue.reconcile(plan, CLIENT_ID)

    def test_close_waits_for_flat_isolated_drain_and_parent_credit(self):
        self.provider.position()
        plan = self.venue.plan("ZEC", "sell", ACCOUNT)
        self.history(plan)
        self.provider.positions = []
        result = self.venue.reconcile(plan, CLIENT_ID)
        self.assertEqual(result["status"], "filled")
        self.assertFalse(result["settled"])
        self.provider.balance["freeBalance"] = "175"
        self.assertTrue(self.venue.reconcile(plan, CLIENT_ID)["settled"])
        self.provider.idle_balance["tokenBalance"] = 1
        self.assertFalse(self.venue.reconcile(plan, CLIENT_ID)["settled"])

    def test_fill_economics_are_bound_to_quantity_price_cap_and_fee_quote(self):
        plan = self.venue.plan("ZEC", "buy", ACCOUNT)
        self.history(plan)
        result = self.venue.reconcile(plan, CLIENT_ID)
        self.assertEqual(
            Decimal(result["actual_fee_usdc"]),
            Decimal(plan["price_cap"]) * Decimal(plan["quantity"]) * Decimal("0.00035"),
        )
        for field, value in (
            ("price", "1005.01"),
            ("size", "0.001"),
            ("size", "0.0001"),
            ("fee", "1"),
            ("fee", "-1"),
            ("signature", ""),
            ("timestamp", True),
        ):
            with self.subTest(field=field, value=value):
                self.history(plan)
                self.provider.history[0]["transactions"][0][field] = value
                with self.assertRaises(GumError):
                    self.venue.reconcile(plan, CLIENT_ID)
        self.history(plan)
        self.provider.history[0]["transactions"] = []
        with self.assertRaisesRegex(GumError, "trail_quantity"):
            self.venue.reconcile(plan, CLIENT_ID)

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_signed_submit_is_owner_verified_one_shot_and_cap_bound(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        owner = b58encode(key.public_key().public_bytes_raw())
        venue = GumOrders(
            owner, ACCOUNT, 2, leverage="2", signer=key.sign, call=self.provider
        )
        plan = venue.plan("ZEC", "buy", ACCOUNT)
        receipt = venue.submit_leg(plan, CLIENT_ID)
        self.assertEqual(receipt["client_order_id"], CLIENT_ID)
        posts = [call for call in self.provider.calls if call[0] == "POST"]
        self.assertEqual(len(posts), 1)
        body = posts[0][3]
        self.assertEqual(body["timeInForce"], "FillOrKill")
        self.assertEqual(body["collateralAmount"], 75000000)
        self.assertTrue(body["signature"].startswith("0:"))
        tampered = dict(plan, quantity="0.150")
        with self.assertRaisesRegex(GumError, "plan_lots_changed"):
            venue.submit_leg(tampered, "2")
        self.assertEqual(
            len([call for call in self.provider.calls if call[0] == "POST"]), 1
        )
        self.provider.response_error = True
        with self.assertRaises(GumAmbiguous):
            venue.submit_leg(plan, "3")
        self.assertEqual(
            len([call for call in self.provider.calls if call[0] == "POST"]), 2
        )

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_wrong_signer_is_refused_before_any_write(self):
        self.venue.signer = lambda message: bytes(64)
        plan = self.venue.plan("ZEC", "buy", ACCOUNT)
        with self.assertRaisesRegex(GumError, "signature_owner"):
            self.venue.submit_leg(plan, CLIENT_ID)
        self.assertFalse(any(call[0] == "POST" for call in self.provider.calls))

    @unittest.skipUnless(
        importlib.util.find_spec("cryptography"), "optional Jupiter signing extra"
    )
    def test_disarm_or_quote_aging_during_signing_prevents_post(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
        owner = b58encode(key.public_key().public_bytes_raw())
        enabled, clock = [True], [time.monotonic()]
        venue = GumOrders(owner, ACCOUNT, 2, leverage="2", call=self.provider)
        plan = venue.plan("ZEC", "buy", ACCOUNT)

        def disarm(message):
            enabled[0] = False
            return key.sign(message)

        venue.signer = disarm
        with self.assertRaisesRegex(GumError, "disarmed_or_expired"):
            venue.submit_leg(plan, CLIENT_ID, enabled=lambda: enabled[0])

        def age_quote(message):
            clock[0] += 6
            return key.sign(message)

        venue.signer = age_quote
        with (
            patch("oracle.gum_orders.time.monotonic", side_effect=lambda: clock[0]),
            self.assertRaisesRegex(GumError, "stale_market"),
        ):
            venue.submit_leg(plan, CLIENT_ID)
        self.assertFalse(any(call[0] == "POST" for call in self.provider.calls))

    def test_mutable_disarm_and_deadline_refuse_before_signing(self):
        signed = []
        self.venue.signer = lambda message: signed.append(message) or bytes(64)
        plan = self.venue.plan("ZEC", "buy", ACCOUNT)
        with self.assertRaisesRegex(GumError, "disarmed_or_expired"):
            self.venue.submit_leg(plan, CLIENT_ID, deadline=time.time() - 1)
        enabled = [True]

        def change_on_blockhash(method, path, owner, body):
            result = self.provider(method, path, owner, body)
            if path == "/blockhash":
                enabled[0] = False
            return result

        self.venue.call = change_on_blockhash
        with self.assertRaisesRegex(GumError, "disarmed_or_expired"):
            self.venue.submit_leg(plan, CLIENT_ID, enabled=lambda: enabled[0])
        self.assertEqual(signed, [])
        self.assertFalse(any(call[0] == "POST" for call in self.provider.calls))

    def test_slow_account_reads_do_not_refresh_old_market_snapshot(self):
        clock = [time.monotonic()]

        def slow_balance(method, path, owner, body):
            result = self.provider(method, path, owner, body)
            if path.endswith("/balances"):
                clock[0] += 6
            return result

        self.venue.call = slow_balance
        with (
            patch("oracle.gum_orders.time.monotonic", side_effect=lambda: clock[0]),
            self.assertRaisesRegex(GumError, "stale_market"),
        ):
            self.venue.plan("ZEC", "buy", ACCOUNT)


if __name__ == "__main__":
    unittest.main()

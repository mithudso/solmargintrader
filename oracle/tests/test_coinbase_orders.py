from __future__ import annotations

import copy
import subprocess
import unittest
from unittest.mock import patch

from oracle.coinbase_orders import (
    CoinbaseAmbiguous,
    CoinbaseError,
    CoinbaseOrders,
    product_id,
)

PORTFOLIO = "487d6679-dafe-5b8d-8c03-ae2768477bfc"
CLIENT_ID = "abc4d27b-6dd0-4e47-ab50-c238ec33a6a6"
ORDER_ID = "bcd4d27b-6dd0-4e47-ab50-c238ec33a6a6"


def account(currency, available):
    return {
        "currency": currency,
        "active": True,
        "ready": True,
        "available_balance": {"currency": currency, "value": available},
        "hold": {"currency": currency, "value": "500"},
    }


class Provider:
    def __init__(self):
        self.calls = []
        self.product = {
            "product_id": "SOL-USDC",
            "product_type": "SPOT",
            "status": "online",
            "base_currency_id": "SOL",
            "quote_currency_id": "USDC",
            "base_increment": "0.0001",
            "base_min_size": "0.0001",
            "base_max_size": "1000000",
            "quote_increment": "0.01",
            "quote_min_size": "1",
            "quote_max_size": "1000000",
        }
        self.pages = [
            {
                "portfolio_id": PORTFOLIO,
                "size": 2,
                "accounts": [account("SOL", "5.12345"), account("USDC", "101.23")],
            }
        ]
        self.order_pages = [{"orders": [], "has_next": False}]
        self.order = {
            "order_id": ORDER_ID,
            "client_order_id": CLIENT_ID,
            "product_id": "SOL-USDC",
            "side": "BUY",
            "status": "PENDING",
        }
        self.error = None

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ["products", "get"]:
            return copy.deepcopy(self.product)
        if args[0] == "balance":
            return copy.deepcopy(
                self.pages[1 if any(a.startswith("cursor==") for a in args) else 0]
            )
        if args[:2] == ["orders", "list"]:
            return copy.deepcopy(
                self.order_pages[
                    1 if any(a.startswith("cursor==") for a in args) else 0
                ]
            )
        if args[:2] in (["orders", "create"], ["orders", "get"]):
            if self.error:
                raise self.error
            return copy.deepcopy(self.order)
        raise AssertionError(args)


class CoinbaseOrdersTests(unittest.TestCase):
    def setUp(self):
        self.provider = Provider()
        self.orders = CoinbaseOrders(call=self.provider)

    def test_buy_uses_available_quote_not_hold_and_rounds_down(self):
        plan = self.orders.plan("COINBASE:SOLUSDC", "buy", PORTFOLIO)
        self.assertEqual(plan["size"], "75.92")
        self.assertEqual(plan["size_field"], "quote_size")
        self.assertEqual(plan["available"], "101.23")
        self.assertEqual(plan["balance_percentage"], "75")
        self.assertFalse(
            any(c[:2] == ["orders", "create"] for c in self.provider.calls)
        )

    def test_sell_uses_base_balance_and_rounds_down(self):
        plan = self.orders.plan("SOL/USDC", "SELL", PORTFOLIO)
        self.assertEqual(plan["size"], "3.8425")
        self.assertEqual(plan["size_field"], "base_size")

    def test_complete_pagination_is_required_even_if_balance_on_first_page(self):
        self.provider.pages = [
            {
                "portfolio_id": PORTFOLIO,
                "accounts": [account("USDC", "100")],
                "has_next": True,
                "cursor": "next",
            },
            {"portfolio_id": PORTFOLIO, "accounts": [], "size": 0},
        ]
        self.assertEqual(
            self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)["size"], "75.00"
        )
        self.assertEqual(len([c for c in self.provider.calls if c[0] == "balance"]), 2)
        self.provider.pages[1]["has_next"] = True
        self.provider.pages[1]["cursor"] = "next"
        with self.assertRaises(CoinbaseError):
            self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)

    def test_wrong_portfolio_and_incomplete_pages_refuse(self):
        for page in (
            {"portfolio_id": "other", "accounts": [], "size": 0},
            {"portfolio_id": PORTFOLIO, "accounts": []},
        ):
            with self.subTest(page=page):
                self.provider.pages = [page]
                with self.assertRaises(CoinbaseError):
                    self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)

    def test_minimum_and_maximum_refuse_without_resizing(self):
        for value in ("0", "0.5", "2000000"):
            with self.subTest(value=value):
                self.provider.pages[0]["accounts"] = [account("USDC", value)]
                with self.assertRaises(CoinbaseError):
                    self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)

    def test_missing_duplicate_and_inactive_available_balance_refuse(self):
        for rows in (
            [],
            [account("USDC", "100"), account("USDC", "100")],
            [{**account("USDC", "100"), "active": False}],
            [{**account("USDC", "100"), "ready": False}],
        ):
            with self.subTest(rows=rows):
                self.provider.pages[0] = {
                    "portfolio_id": PORTFOLIO,
                    "accounts": rows,
                    "size": len(rows),
                }
                with self.assertRaises(CoinbaseError):
                    self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)

    def test_non_exact_and_nonfinite_decimal_refuse(self):
        for invalid in (None, True, 100, 1.5, "NaN", "Infinity", "-1", "1e3", "1.2.3"):
            with self.subTest(invalid=invalid):
                self.provider.pages[0]["accounts"] = [account("USDC", invalid)]
                with self.assertRaises(CoinbaseError):
                    self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)

    def test_invalid_or_wrong_product_refuses(self):
        for changes in (
            {"status": "offline"},
            {"product_type": "FUTURE"},
            {"product_id": "SOL-USD"},
            {"quote_currency_id": "USD"},
            {"quote_increment": None},
            {"quote_increment": "0"},
        ):
            with self.subTest(changes=changes):
                original = self.provider.product
                self.provider.product = {**original, **changes}
                with self.assertRaises(CoinbaseError):
                    self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)
                self.provider.product = original

    def test_symbol_mapping_ignores_chart_exchange_but_preserves_quote(self):
        for symbol, expected in (
            ("COINBASE:SOLUSD", "SOL-USD"),
            ("BINANCE:SOLUSDC", "SOL-USDC"),
            ("SOLUSDC", "SOL-USDC"),
            ("SOL/USD", "SOL-USD"),
            ("BTC-EUR", "BTC-EUR"),
        ):
            self.assertEqual(product_id(symbol), expected)
        for invalid in (
            "BAD-EXCHANGE:SOLUSDT",
            "SOL",
            "COINBASE:SOL",
            "SOL--USD",
            "SOL-USD.P",
            "USDUSD",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(CoinbaseError):
                product_id(invalid)

    def test_submit_calls_create_once_with_exact_size_and_id(self):
        plan = self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)
        result = self.orders.submit(plan, CLIENT_ID)
        self.assertEqual(result["order_id"], ORDER_ID)
        calls = [c for c in self.provider.calls if c[:2] == ["orders", "create"]]
        self.assertEqual(len(calls), 1)
        self.assertIn("quote_size=75.92", calls[0])
        self.assertIn("portfolio_id=" + PORTFOLIO, calls[0])
        self.assertIn("client_order_id=" + CLIENT_ID, calls[0])
        self.assertFalse(any(c.startswith("base_size=") for c in calls[0]))

    def test_submit_failure_is_ambiguous_and_sanitized_without_retry(self):
        plan = self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)
        self.provider.error = subprocess.TimeoutExpired("sensitive-command", 30)
        with self.assertRaisesRegex(CoinbaseAmbiguous, "^coinbase_submission_unknown$"):
            self.orders.submit(plan, CLIENT_ID)
        self.assertEqual(
            len([c for c in self.provider.calls if c[:2] == ["orders", "create"]]), 1
        )

    def test_submit_identity_mismatch_is_ambiguous(self):
        plan = self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)
        for changes in (
            {"client_order_id": "foreign"},
            {"product_id": "SOL-USD"},
            {"side": "SELL"},
            {"order_id": None},
        ):
            with self.subTest(changes=changes):
                original = self.provider.order
                self.provider.order = {**original, **changes}
                with self.assertRaises(CoinbaseAmbiguous):
                    self.orders.submit(plan, CLIENT_ID)
                self.provider.order = original

    def test_missing_client_id_preserves_known_order_id(self):
        del self.provider.order["client_order_id"]
        result = self.orders.submit(
            self.orders.plan("SOL-USDC", "BUY", PORTFOLIO), CLIENT_ID
        )
        self.assertEqual(result["order_id"], ORDER_ID)
        self.assertNotIn("client_order_id", result)

    def test_invalid_client_id_refuses_before_create(self):
        plan = self.orders.plan("SOL-USDC", "BUY", PORTFOLIO)
        with self.assertRaises(CoinbaseError):
            self.orders.submit(plan, "not-a-uuid")
        self.assertFalse(
            any(c[:2] == ["orders", "create"] for c in self.provider.calls)
        )

    def test_get_verifies_returned_order_id(self):
        self.assertEqual(self.orders.get(ORDER_ID)["order_id"], ORDER_ID)
        with self.assertRaises(CoinbaseError):
            self.orders.get("different-id")

    def test_find_paginated_client_id_and_missing_id_remains_unknown(self):
        self.provider.order_pages = [
            {"orders": [], "has_next": True, "cursor": "next"},
            {"orders": [{"order_id": ORDER_ID}], "has_next": False},
        ]
        self.assertEqual(
            self.orders.find(CLIENT_ID, "SOL-USDC", PORTFOLIO)["order_id"], ORDER_ID
        )
        del self.provider.order["client_order_id"]
        self.assertIsNone(self.orders.find(CLIENT_ID, "SOL-USDC", PORTFOLIO))

    def test_transport_error_never_echoes_provider_error(self):
        def failure(args):
            raise ValueError("secret material")

        orders = CoinbaseOrders(call=failure)
        with self.assertRaisesRegex(CoinbaseError, "^coinbase_operation_failed$"):
            orders.get(ORDER_ID)

    def test_cli_does_not_use_shell_and_bounds_output(self):
        def fake_run(args, **kwargs):
            self.assertEqual(
                args,
                ["/absolute/coinbase", "orders", "get", ORDER_ID, "product_type==SPOT"],
            )
            self.assertNotIn("shell", kwargs)
            self.assertEqual(kwargs["timeout"], 30)
            kwargs["stdout"].write(b'{"order_id":"' + ORDER_ID.encode() + b'"}')
            return subprocess.CompletedProcess(args, 0)

        with patch("oracle.coinbase_orders.subprocess.run", side_effect=fake_run):
            self.assertEqual(
                CoinbaseOrders("/absolute/coinbase").get(ORDER_ID)["order_id"], ORDER_ID
            )


if __name__ == "__main__":
    unittest.main()

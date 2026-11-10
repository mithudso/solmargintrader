from __future__ import annotations

import unittest
from decimal import Decimal

from botmanager.accounting import accounting_snapshot


def fixture():
    return {
        "starting_equity": "1000",
        "currency": "USDC",
        "fills": [
            {"side": "buy", "quantity": "10", "price": "10", "fee": "2"},
            {"side": "sell", "quantity": "4", "price": "15", "fee": "1"},
        ],
        "marks": {"base": "12"},
        "cashflows": [
            {"kind": "deposit", "amount": "50"},
            {"kind": "withdrawal", "amount": "20"},
            {"kind": "expense", "amount": "3"},
        ],
    }


class AccountingTests(unittest.TestCase):
    def value(self, snapshot, key):
        return Decimal(snapshot[key]["value"])

    def test_fifo_partial_close_charges_each_fee_once(self):
        result = accounting_snapshot(fixture())
        self.assertEqual(self.value(result, "fees"), Decimal(3))
        self.assertEqual(self.value(result, "realized_net_pnl"), Decimal("18.2"))
        self.assertEqual(self.value(result, "unrealized_net_pnl"), Decimal("10.8"))
        self.assertEqual(self.value(result, "net_pnl"), Decimal(26))
        self.assertEqual(
            self.value(result, "realized_net_pnl")
            + self.value(result, "unrealized_net_pnl")
            - self.value(result, "transaction_expense"),
            self.value(result, "net_pnl"),
        )

    def test_cashflow_identity(self):
        result = accounting_snapshot(fixture())
        self.assertEqual(self.value(result, "cash"), Decimal(984))
        self.assertEqual(
            self.value(result, "equity"),
            self.value(result, "cash") + self.value(result, "marked_inventory"),
        )
        self.assertEqual(
            self.value(result, "net_pnl"),
            self.value(result, "equity")
            - self.value(result, "starting_equity")
            - self.value(result, "deposits")
            + self.value(result, "withdrawals"),
        )

    def test_missing_mark_keeps_pnl_null(self):
        run = fixture()
        run["marks"] = {}
        result = accounting_snapshot(run)
        self.assertIsNone(result["net_pnl"]["value"])
        self.assertIn("inventory_mark_unavailable", result["net_pnl"]["reason"])
        self.assertEqual(self.value(result, "realized_net_pnl"), Decimal("18.2"))

    def test_rent_is_not_profit(self):
        run = {
            "starting_equity": "100",
            "currency": "USDC",
            "fills": [],
            "cashflows": [{"kind": "rent_lock", "amount": "2"}],
        }
        result = accounting_snapshot(run)
        self.assertEqual(self.value(result, "cash"), Decimal(98))
        self.assertEqual(self.value(result, "refundable_rent_asset"), Decimal(2))
        self.assertEqual(self.value(result, "net_pnl"), Decimal(0))
        run["cashflows"].append({"kind": "rent_refund", "amount": "2"})
        self.assertEqual(self.value(accounting_snapshot(run), "net_pnl"), Decimal(0))

    def test_missing_fee_and_oversell_are_unknown(self):
        run = fixture()
        del run["fills"][0]["fee"]
        self.assertIsNone(accounting_snapshot(run)["equity"]["value"])
        run = fixture()
        run["fills"][1]["quantity"] = "11"
        self.assertIsNone(accounting_snapshot(run)["net_pnl"]["value"])

    def test_float_is_not_misrepresented_as_exact(self):
        run = fixture()
        run["starting_equity"] = 1000.0
        self.assertIsNone(accounting_snapshot(run)["net_pnl"]["value"])

    def test_missing_cashflow_amount_is_not_reported_as_zero(self):
        run = fixture()
        run["cashflows"] = [{"kind": "deposit"}]
        result = accounting_snapshot(run)
        self.assertIsNone(result["deposits"]["value"])
        self.assertIsNone(result["net_pnl"]["value"])

    def test_missing_fee_preserves_known_gross(self):
        run = fixture()
        del run["fills"][0]["fee"]
        result = accounting_snapshot(run)
        self.assertEqual(self.value(result, "realized_gross_pnl"), Decimal(20))
        self.assertIsNone(result["realized_net_pnl"]["value"])

    def test_absent_ledgers_are_unknown_instead_of_empty(self):
        for field in ("fills", "cashflows"):
            run = fixture()
            del run[field]
            result = accounting_snapshot(run)
            self.assertIsNone(result["net_pnl"]["value"])
            self.assertIn("ledger_unavailable", result["net_pnl"]["reason"])

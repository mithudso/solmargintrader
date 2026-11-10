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

    def test_unavailable_marks_mapping_never_crashes(self):
        for marks in (None, [], "missing", 42):
            run = fixture()
            run["marks"] = marks
            result = accounting_snapshot(run)
            for key in (
                "traded_inventory",
                "marked_inventory",
                "unrealized_net_pnl",
                "equity",
                "net_pnl",
            ):
                self.assertIsNone(result[key]["value"])
                self.assertIn("inventory_mark_unavailable", result[key]["reason"])
            self.assertEqual(self.value(result, "realized_net_pnl"), Decimal("18.2"))

    def test_incomplete_fill_ledger_does_not_claim_inventory(self):
        for fills in (None, {}, [fixture()["fills"][0], None], ["bad"]):
            run = fixture()
            run["fills"] = fills
            result = accounting_snapshot(run)
            for key in (
                "traded_inventory",
                "marked_inventory",
                "unrealized_net_pnl",
                "net_pnl",
            ):
                self.assertIsNone(result[key]["value"])
                self.assertTrue(result[key]["reason"])
            self.assertIsNone(result["residuals"])
            self.assertTrue(result["residuals_reason"])
            self.assertEqual(self.value(result, "refundable_rent_asset"), Decimal(0))
            self.assertEqual(self.value(result, "deposits"), Decimal(50))

    def test_incomplete_cashflows_preserve_known_trade_accounting(self):
        for flows in (None, {}, [None], [{"kind": "rent_lock", "amount": "2"}, {}]):
            run = fixture()
            run["cashflows"] = flows
            result = accounting_snapshot(run)
            for key in (
                "refundable_rent_asset",
                "marked_inventory",
                "cash",
                "equity",
                "net_pnl",
                "deposits",
            ):
                self.assertIsNone(result[key]["value"])
                self.assertTrue(result[key]["reason"])
            self.assertEqual(self.value(result, "traded_inventory"), Decimal(72))
            self.assertEqual(self.value(result, "realized_net_pnl"), Decimal("18.2"))
            self.assertEqual(result["residuals"], [{"asset": "base", "quantity": "6"}])

    def test_reference_loss_and_cost_float_lineage_remains_canonical(self):
        result = accounting_snapshot(
            {
                "spec": {},
                "input": {"descriptor": {"capital_quote": 100.0}},
                "checkpoint": {
                    "cash_quote": 70.0,
                    "exposure_quote": 20.0,
                    "equity_quote": 90.0,
                    "fees_quote": 1.25,
                    "quote_currency": "USD",
                    "lots": [],
                },
            }
        )
        self.assertEqual(result["arithmetic"], "canonical_simulator_float")
        self.assertEqual(result["net_pnl"]["value"], -10.0)
        self.assertIsInstance(result["net_pnl"]["value"], float)
        self.assertEqual(result["fees"]["value"], 1.25)
        self.assertEqual(result["currency"], "USD")

from __future__ import annotations

import unittest

from botmanager.domain import ManagerError
from botmanager.strategies.arbitrage import diagnose_cycle

from oracle.quotes import capture_quote
from oracle.tests.test_quotes import SOL, USDC, fixture


def quote(a, b, amount, out, minimum=None, t=100):
    raw = fixture(amount, out)
    raw.update(
        inputMint=a,
        outputMint=b,
        otherAmountThreshold=str(out if minimum is None else minimum),
    )
    raw["routePlan"][0]["swapInfo"].update(inputMint=a, outputMint=b, feeMint=a)
    return capture_quote(
        {"inputMint": a, "outputMint": b, "amount": amount, "slippageBps": 50},
        raw,
        requested_at=t,
        received_at=t + 0.1,
        expires_at=t + 5,
        max_latency_s=2,
    )


def costs(quotes, each=1):
    return {
        q["observation_id"]: {
            "network_fee_start_raw": each,
            "priority_fee_start_raw": 0,
            "rent_start_raw": 0,
            "failed_transaction_start_raw": each,
            "cost_currency_mint": SOL,
            "route_platform_fees_in_output": True,
            "fill_policy": "minimum_output",
        }
        for q in quotes
    }


class CycleTests(unittest.TestCase):
    def test_profit_loss_and_failure_are_costed_not_booked(self):
        q = [quote(SOL, USDC, 100, 120), quote(USDC, SOL, 120, 110)]
        r = diagnose_cycle(q, costs(q), now=101, failed_leg=None)
        self.assertEqual(r["pessimistic_paper_net_start_raw"], 8)
        self.assertIsNone(r["booked_profit_start_raw"])
        self.assertFalse(r["live_supported"])
        self.assertEqual(
            diagnose_cycle(q, costs(q, 8), now=101, failed_leg=None)[
                "pessimistic_paper_net_start_raw"
            ],
            -6,
        )
        unwind = quote(USDC, SOL, 120, 90)
        c = costs([*q, unwind])
        r = diagnose_cycle(q, c, now=101, failed_leg=1, unwind=unwind)
        self.assertEqual(r["pessimistic_paper_net_start_raw"], -13)

    def test_stale_future_missing_and_size_mismatch_refuse(self):
        q = [quote(SOL, USDC, 100, 120), quote(USDC, SOL, 119, 110)]
        for now in (99, 106, 101):
            with self.assertRaises(ManagerError):
                diagnose_cycle(q, costs(q), now=now, failed_leg=None)
        good = [q[0], quote(USDC, SOL, 120, 110)]
        with self.assertRaises(ManagerError):
            diagnose_cycle(good, {}, now=101, failed_leg=None)
        with self.assertRaises(ManagerError):
            diagnose_cycle(good, costs(good), now=101, failed_leg=1)

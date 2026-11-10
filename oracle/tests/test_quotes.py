from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from oracle.quotes import (
    QuoteError,
    capture_quote,
    collect_quote,
    import_quote,
    read_quotes,
)

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


def fixture(amount=100000000, output=16198753):
    return {
        "inputMint": SOL,
        "outputMint": USDC,
        "inAmount": str(amount),
        "outAmount": str(output),
        "otherAmountThreshold": str(output - 100),
        "swapMode": "ExactIn",
        "slippageBps": 50,
        "contextSlot": 12345,
        "timeTaken": 0.01,
        "platformFee": None,
        "routePlan": [
            {
                "percent": 100,
                "swapInfo": {
                    "ammKey": SOL,
                    "label": "fixture",
                    "inputMint": SOL,
                    "outputMint": USDC,
                    "inAmount": str(amount),
                    "outAmount": str(output),
                    "feeAmount": "1",
                    "feeMint": SOL,
                },
            }
        ],
    }


class QuoteTests(unittest.TestCase):
    def test_exact_amount_mints_clocks_and_cost_missingness(self):
        request = {
            "inputMint": SOL,
            "outputMint": USDC,
            "amount": 100000000,
            "slippageBps": 50,
        }
        q = capture_quote(
            request,
            fixture(),
            requested_at=100,
            received_at=100.1,
            expires_at=105,
            max_latency_s=2,
        )
        self.assertFalse(q["fee_complete"])
        self.assertFalse(q["certified"])
        for delta in ({"amount": 2}, {"outputMint": SOL}):
            with self.assertRaises(QuoteError):
                capture_quote(
                    {**request, **delta},
                    fixture(),
                    requested_at=100,
                    received_at=100.1,
                    expires_at=105,
                    max_latency_s=2,
                )
        with self.assertRaises(QuoteError):
            capture_quote(
                request,
                fixture(),
                requested_at=100,
                received_at=103,
                expires_at=105,
                max_latency_s=2,
            )

    def test_no_optin_no_state_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "absent.sqlite3"
            with self.assertRaises(QuoteError):
                collect_quote(p, {}, enabled=False)
            self.assertFalse(p.exists())

    def test_import_is_append_only_and_amount_bound(self):
        from oracle.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "history.sqlite3"
            Store(p)
            q = capture_quote(
                {
                    "inputMint": SOL,
                    "outputMint": USDC,
                    "amount": 100000000,
                    "slippageBps": 50,
                },
                fixture(),
                requested_at=100,
                received_at=100.1,
                expires_at=105,
                max_latency_s=2,
            )
            import_quote(p, q)
            import_quote(p, q)
            rows = read_quotes(p)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["observation_id"], q["observation_id"])
            with self.assertRaises(QuoteError):
                import_quote(p, {**q, "fee_complete": True})

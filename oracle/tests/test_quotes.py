from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from oracle.quotes import (
    QuoteError,
    capture_quote,
    collect_quote,
    import_quote,
    read_quote_page,
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
        "priceImpactPct": "0.001",
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


class QuoteEvidenceReviewTests(unittest.TestCase):
    def capture(self, response):
        return capture_quote(
            {
                "inputMint": SOL,
                "outputMint": USDC,
                "amount": 100000000,
                "slippageBps": 50,
            },
            response,
            requested_at=100,
            received_at=100.1,
            expires_at=105,
            max_latency_s=2,
        )

    def test_direct_route_direction_amounts_and_allocation_reconcile(self):
        for change in (
            {"inputMint": USDC, "outputMint": SOL},
            {"inAmount": "0", "outAmount": "0"},
            {"inAmount": "1"},
            {"outAmount": "1"},
            {"inputMint": USDC, "outputMint": SOL, "inAmount": "0", "outAmount": "0"},
        ):
            with self.subTest(change=change):
                raw = fixture()
                raw["routePlan"][0]["swapInfo"].update(change)
                with self.assertRaises(QuoteError):
                    self.capture(raw)
        for percent in (1, 50, 99):
            raw = fixture()
            raw["routePlan"][0]["percent"] = percent
            with self.assertRaises(QuoteError):
                self.capture(raw)
        raw = fixture()
        raw["routePlan"][0]["bps"] = 5000
        with self.assertRaises(QuoteError):
            self.capture(raw)

    def test_split_and_multihop_are_explicitly_unsupported(self):
        import copy

        for multihop in (False, True):
            raw = fixture()
            first = raw["routePlan"][0]
            second = copy.deepcopy(first)
            raw["routePlan"].append(second)
            if multihop:
                middle = "11111111111111111111111111111111"
                first["swapInfo"].update(outputMint=middle, outAmount="100")
                second["swapInfo"].update(inputMint=middle, inAmount="100")
            else:
                for leg in raw["routePlan"]:
                    leg["percent"] = 50
                    leg["swapInfo"].update(inAmount="50000000", outAmount="8099376")
            with self.assertRaisesRegex(QuoteError, "quote_route_topology_unsupported"):
                self.capture(raw)

    def test_price_impact_exact_fraction_survives_capture_and_import(self):
        from oracle.quotes import validate_observation
        from oracle.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            Store(path)
            raw = fixture()
            raw["priceImpactPct"] = "0.990000000000000000001"
            observation = self.capture(raw)
            self.assertEqual(
                observation["response"]["priceImpactPct"], raw["priceImpactPct"]
            )
            self.assertEqual(
                observation["price_impact"],
                {
                    "value": "0.990000000000000000001",
                    "unit": "fraction",
                    "state": "observed",
                    "reason": None,
                },
            )
            self.assertEqual(observation["route_policy"], "direct_single_leg_100pct_v1")
            self.assertEqual(validate_observation(observation), observation)
            import_quote(path, observation)
            self.assertEqual(read_quotes(path), [observation])

    def test_missing_and_invalid_impact_are_distinct(self):
        raw = fixture()
        del raw["priceImpactPct"]
        observation = self.capture(raw)
        self.assertIsNone(observation["response"]["priceImpactPct"])
        self.assertEqual(observation["price_impact"]["state"], "unavailable")
        self.assertIn("price_impact_unavailable", observation["certification_reasons"])
        for value in (
            True,
            0.1,
            [],
            "NaN",
            "Infinity",
            "1.001",
            "-0.01",
            "0.1%",
            "",
            "1e999",
            "0.1 secret",
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(QuoteError, "quote_price_impact_invalid"),
            ):
                self.capture({**fixture(), "priceImpactPct": value})

    def test_invalid_impact_import_and_platform_fee_topology_refuse(self):
        import copy

        from oracle.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.sqlite3"
            Store(path)
            original = self.capture(fixture())
            for value in ("NaN", "Infinity", "-0.1", "1.1"):
                invalid = copy.deepcopy(original)
                invalid["response"]["priceImpactPct"] = value
                with self.assertRaisesRegex(QuoteError, "quote_price_impact_invalid"):
                    import_quote(path, invalid)
            self.assertEqual(read_quotes(path), [])
        raw = fixture()
        raw["platformFee"] = {"amount": "1", "feeBps": 1}
        with self.assertRaisesRegex(
            QuoteError, "quote_platform_fee_topology_unsupported"
        ):
            self.capture(raw)


class QuotePageTests(unittest.TestCase):
    def test_sequence_gaps_append_and_exact_replay(self):
        from oracle.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quotes.sqlite3"
            Store(path)

            def add(output):
                response = fixture(output=output)
                request = {
                    k: response[k] for k in ("inputMint", "outputMint", "slippageBps")
                }
                request["amount"] = int(response["inAmount"])
                q = capture_quote(
                    request,
                    response,
                    requested_at=100,
                    received_at=100.1,
                    expires_at=105,
                    max_latency_s=2,
                )
                import_quote(path, q)
                return q

            first = add(1000)
            import_quote(path, first)  # ignored insert consumes an AUTOINCREMENT id
            add(2000)
            page = read_quote_page(path, limit=1)
            self.assertEqual(page, read_quote_page(path, limit=1))
            self.assertEqual(page["next_after"], 1)
            self.assertTrue(page["has_more"])
            add(3000)
            rest = read_quote_page(path, after=page["next_after"], limit=10)
            self.assertEqual([row["sequence"] for row in rest["items"]], [3, 4])
            self.assertEqual(rest["next_after"], 4)
            self.assertFalse(rest["has_more"])
            self.assertEqual(read_quote_page(path, after=4)["next_after"], 4)

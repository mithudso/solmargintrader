from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from oracle.cli import main
from oracle.engine import OracleEngine
from oracle.feeds import (
    SOL_MINT,
    USDC_MINT,
    FeedUnavailable,
    JupiterPriceFeed,
    RecorderFeed,
    validate_instrument,
)

HAS_MCP = importlib.util.find_spec("mcp") is not None
if HAS_MCP:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

REPO = Path(__file__).resolve().parents[2]


def tick(instrument: str, i: int, price: float) -> dict:
    return {
        "source": "coinbase_recorder",
        "instrument": instrument,
        "venue": "coinbase_exchange",
        "kind": "stream_snapshot_mid",
        "event_id": f"tick-{i}",
        "observed_at": i * 60 + 1,
        "received_at": i * 60 + 1,
        "price": price,
    }


class MultiInstrumentTests(unittest.TestCase):
    def test_instrument_is_validated_before_archive_creation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "archive.sqlite3"
            for value in (
                None,
                "",
                "BTC",
                "BTC/USD/USDC",
                "../BTC/USD",
                "BTC /USD",
                "BTC/BTC",
                "BTC/USD\n",
            ):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    OracleEngine(path, instrument=value)
                self.assertFalse(path.exists())
        self.assertEqual(validate_instrument("JitoSOL/usdc"), "JITOSOL/USDC")

    def test_one_archive_cannot_pool_two_instruments(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "archive.sqlite3"
            engine = OracleEngine(path, instrument="BTC/USD")
            engine.ingest(tick("BTC/USD", 0, 50000), now=1)
            with self.assertRaisesRegex(ValueError, "policy_mismatch"):
                OracleEngine(path, instrument="ETH/USD")
            with self.assertRaisesRegex(ValueError, "instrument_not_supported"):
                engine.ingest(tick("ETH/USD", 1, 2000), now=61)
            self.assertEqual(engine.status()["counts"]["observations"], 1)
            self.assertEqual(
                engine.market(now=1)["observation"]["instrument"], "BTC/USD"
            )

    def test_forecasts_evidence_and_outputs_are_instrument_bound(self):
        with tempfile.TemporaryDirectory() as root:
            btc = OracleEngine(
                Path(root) / "btc.sqlite3", instrument="BTC/USD", minimum_resolved=1
            )
            eth = OracleEngine(
                Path(root) / "eth.sqlite3", instrument="ETH/USD", minimum_resolved=1
            )
            for i in range(80):
                btc.ingest(tick("BTC/USD", i, 500 - i), now=i * 60 + 1)
                eth.ingest(tick("ETH/USD", i, 100 + i), now=i * 60 + 1)
            self.assertNotEqual(btc.policy_hash, eth.policy_hash)
            btc_output = btc.predictions(now=4741)
            eth_output = eth.predictions(now=4741)
            self.assertEqual(btc_output["signal"], "Strong Sell")
            self.assertEqual(eth_output["signal"], "Strong Buy")
            for engine, instrument in ((btc, "BTC/USD"), (eth, "ETH/USD")):
                self.assertEqual(engine.market(now=4741)["instrument"], instrument)
                self.assertEqual(engine.predictions(now=4741)["instrument"], instrument)
                self.assertEqual(engine.status()["instrument"], instrument)
                self.assertEqual(engine.history()["instrument"], instrument)
                self.assertTrue(
                    all(row["instrument"] == instrument for row in engine.strategies())
                )
                self.assertTrue(
                    all(
                        row["instrument"] == instrument
                        for row in engine.predictions(now=1)["strategies"]
                    )
                )
                predictions = [
                    row["data"]
                    for row in engine.history(1000)["events"]
                    if row["type"] == "prediction"
                ]
                self.assertTrue(predictions)
                self.assertTrue(
                    all(row["instrument"] == instrument for row in predictions)
                )

    def test_recorder_selects_exact_explicit_currency_without_mutating_snapshot(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "latest.json"
            path.write_text(
                json.dumps(
                    {
                        "t": 100,
                        "q": {
                            "BTC-USD": [50000, 50002, 50001, 1, 1, 99],
                            "BTC-USDC": [49000, 49002, 49001, 1, 1, 99],
                        },
                    }
                )
            )
            before = path.read_bytes()
            usd = RecorderFeed(root, instrument="BTC/USD", clock=lambda: 100).poll()
            usdc = RecorderFeed(root, instrument="BTC/USDC", clock=lambda: 100).poll()
            self.assertEqual(usd["instrument"], "BTC/USD")
            self.assertEqual(usdc["instrument"], "BTC/USDC")
            self.assertEqual(usd["price"], 50001)
            self.assertEqual(usdc["price"], 49001)
            self.assertNotEqual(usd["event_id"], usdc["event_id"])
            self.assertEqual(path.read_bytes(), before)
            with self.assertRaisesRegex(FeedUnavailable, "instrument_unavailable"):
                RecorderFeed(root, instrument="ETH/USD", clock=lambda: 100).poll()

    def test_jupiter_requires_explicit_public_mint_identity_for_new_pair(self):
        with self.assertRaisesRegex(FeedUnavailable, "instrument_mapping_required"):
            JupiterPriceFeed(instrument="BTC/USDC")
        for mints in (
            {"BTC": SOL_MINT},
            {"BTC": "secret\n", "USDC": USDC_MINT},
            {"BTC": SOL_MINT, "USDC": SOL_MINT},
        ):
            with (
                self.subTest(mints=mints),
                self.assertRaisesRegex(FeedUnavailable, "instrument_mapping_invalid"),
            ):
                JupiterPriceFeed(instrument="BTC/USDC", mints=mints)
        # A fiat USD label may never be silently mapped to a stablecoin mint.
        with self.assertRaisesRegex(FeedUnavailable, "instrument_not_onchain"):
            JupiterPriceFeed(
                instrument="BTC/USD", mints={"BTC": SOL_MINT, "USD": USDC_MINT}
            )
        calls = []
        payload = {
            SOL_MINT: {"usdPrice": 150, "blockId": 100},
            USDC_MINT: {"usdPrice": 1, "blockId": 101},
        }

        def transport(url, *_):
            calls.append(url)
            return payload

        with patch.dict(os.environ, {"JUPITER_API_KEY": "test-fixture"}):
            # The mapping is an explicit operator declaration, not discovered BTC metadata.
            result = JupiterPriceFeed(
                instrument="BTC/USDC",
                mints={"BTC": SOL_MINT, "USDC": USDC_MINT},
                transport=transport,
                clock=lambda: 100,
            ).poll()
        self.assertEqual(result["instrument"], "BTC/USDC")
        self.assertIn(SOL_MINT, calls[0])
        self.assertEqual(result["provider_block_ids"], {SOL_MINT: 100, USDC_MINT: 101})

    def test_cli_run_and_query_use_selected_instrument(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            archive = root / "btc.sqlite3"
            now = __import__("time").time()
            (root / "latest.json").write_text(
                json.dumps(
                    {"t": now, "q": {"BTC-USD": [50000, 50002, 50001, 1, 1, now]}}
                )
            )
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(
                    [
                        "--archive",
                        str(archive),
                        "--instrument",
                        "BTC/USD",
                        "run",
                        "--recorder-root",
                        str(root),
                        "--max-ticks",
                        "1",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(out.getvalue())["market"]["instrument"], "BTC/USD"
            )
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(
                    ["--archive", str(archive), "--instrument", "BTC/USD", "status"]
                )
            self.assertEqual(code, 0)
            self.assertEqual(
                json.loads(out.getvalue())["data"]["instrument"], "BTC/USD"
            )


@unittest.skipUnless(HAS_MCP, "optional official MCP SDK is not installed")
class MultiInstrumentProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_reader_uses_explicit_archive_instrument(self):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / "eth.sqlite3"
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "oracle.server",
                    "--archive",
                    str(archive),
                    "--instrument",
                    "ETH/USD",
                ],
                env={"PYTHONPATH": str(REPO)},
            )
            async with (
                stdio_client(parameters) as (reader, writer),
                ClientSession(reader, writer) as client,
            ):
                await client.initialize()
                status = await asyncio.wait_for(
                    client.call_tool("oracle_status", {}), 5
                )
                self.assertTrue(
                    status.model_dump(by_alias=True)["structuredContent"]["ok"]
                )
                self.assertEqual(
                    status.model_dump(by_alias=True)["structuredContent"]["data"][
                        "instrument"
                    ],
                    "ETH/USD",
                )
                market = await client.call_tool("oracle_market", {})
                self.assertEqual(
                    market.model_dump(by_alias=True)["structuredContent"]["data"][
                        "instrument"
                    ],
                    "ETH/USD",
                )
                self.assertEqual(
                    market.model_dump(by_alias=True)["structuredContent"]["data"][
                        "status"
                    ],
                    "unavailable",
                )


if __name__ == "__main__":
    unittest.main()

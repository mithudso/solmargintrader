from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

HAS_MCP = importlib.util.find_spec("mcp") is not None
if HAS_MCP:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
    from pydantic import AnyUrl

    from oracle.server import SubscriptionHub

REPO = Path(__file__).resolve().parents[2]


@unittest.skipUnless(HAS_MCP, "optional official MCP SDK is not installed")
class SubscriptionTests(unittest.IsolatedAsyncioTestCase):
    async def test_isolation_unsubscription_and_slow_consumer(self):
        class Session:
            def __init__(self, delay=0):
                self.messages = []
                self.delay = delay

            async def send_resource_updated(self, uri):
                await asyncio.sleep(self.delay)
                self.messages.append(str(uri))

        hub = SubscriptionHub(timeout=0.01)
        first, second, slow = Session(), Session(), Session(1)
        await hub.subscribe(first, "oracle://market")
        await hub.subscribe(second, "oracle://status")
        await hub.subscribe(slow, "oracle://market")
        values = {
            f"oracle://{name}": "1" for name in ("market", "predictions", "status")
        }
        await asyncio.wait_for(hub.publish(values), 0.5)
        self.assertEqual(first.messages, ["oracle://market"])
        self.assertEqual(second.messages, ["oracle://status"])
        self.assertEqual(slow.messages, [])
        await hub.unsubscribe(first, "oracle://market")
        values["oracle://market"] = "2"
        await hub.publish(values)
        self.assertEqual(len(first.messages), 1)
        self.assertNotIn(slow, hub._sessions)


@unittest.skipUnless(HAS_MCP, "optional official MCP SDK is not installed")
class ProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_stdio_discovery_calls_notifications_and_clean_exit(self):
        notices = []

        async def handle(message):
            if isinstance(message, types.ServerNotification):
                notices.append(message)

        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "archive.sqlite3"
            parameters = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-m",
                    "oracle.server",
                    "--archive",
                    str(archive),
                    "--poll-seconds",
                    ".1",
                    "--repo",
                    str(REPO),
                ],
                env={"PYTHONPATH": str(REPO), "JUPITER_API_KEY": "secret-test-key"},
            )
            async with (
                stdio_client(parameters) as (reader, writer),
                ClientSession(reader, writer, message_handler=handle) as session,
            ):
                initialized = await session.initialize()
                self.assertTrue(initialized.capabilities.resources.subscribe)
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                self.assertEqual(len(names), 8)
                self.assertFalse(
                    any("submit" in name or "sign" in name for name in names)
                )
                market = await session.call_tool("oracle_market", {})
                self.assertTrue(market.structuredContent["ok"])
                self.assertEqual(
                    market.structuredContent["data"]["status"], "unavailable"
                )
                invalid = await session.call_tool(
                    "oracle_history", {"limit": "secret-input"}
                )
                self.assertTrue(invalid.isError)
                self.assertNotIn("secret-input", str(invalid))
                invalid = await session.call_tool(
                    "oracle_market", {"key": "secret-input"}
                )
                self.assertTrue(invalid.isError)
                self.assertNotIn("secret-input", str(invalid))
                ready = await session.call_tool("oracle_readiness", {})
                self.assertFalse(ready.structuredContent["data"]["live_ready"])
                self.assertNotIn("secret-test-key", str(ready))
                resources = await session.list_resources()
                self.assertEqual(len(resources.resources), 3)
                uri = AnyUrl("oracle://market")
                await session.subscribe_resource(uri)
                for _ in range(30):
                    if notices:
                        break
                    await asyncio.sleep(0.05)
                self.assertTrue(notices)
                snapshot = await session.read_resource(uri)
                self.assertEqual(
                    json.loads(snapshot.contents[0].text)["data"]["status"],
                    "unavailable",
                )
                from oracle.engine import OracleEngine

                engine = OracleEngine(archive)
                now = time.time()
                engine.ingest(
                    {
                        "source": "fixture",
                        "venue": "fixture",
                        "kind": "reference",
                        "instrument": "SOL/USDC",
                        "event_id": "first",
                        "observed_at": now,
                        "received_at": now,
                        "price": 100,
                    },
                    now=now,
                )
                before = len(notices)
                for _ in range(30):
                    await asyncio.sleep(0.05)
                    if len(notices) > before:
                        break
                self.assertGreater(len(notices), before)
                snapshot = await session.read_resource(uri)
                self.assertEqual(
                    json.loads(snapshot.contents[0].text)["data"]["observation"][
                        "price"
                    ],
                    100,
                )
                await session.unsubscribe_resource(uri)
                count = len(notices)
                now = time.time()
                engine.ingest(
                    {
                        "source": "fixture",
                        "venue": "fixture",
                        "kind": "reference",
                        "instrument": "SOL/USDC",
                        "event_id": "second",
                        "observed_at": now,
                        "received_at": now,
                        "price": 101,
                    },
                    now=now,
                )
                await asyncio.sleep(0.3)
                self.assertEqual(len(notices), count)


if __name__ == "__main__":
    unittest.main()

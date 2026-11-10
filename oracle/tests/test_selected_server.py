from __future__ import annotations

import asyncio
import builtins
import hashlib
import importlib.util
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from oracle.engine import OracleEngine
from oracle.store import canonical

HAS_MCP = importlib.util.find_spec("mcp") is not None
if HAS_MCP:
    from mcp import ClientSession, StdioServerParameters, types
    from mcp.client.stdio import stdio_client
    from pydantic import AnyUrl

    from ecosystem import votes
    from oracle.server import selected_prediction_view, selection_home

REPO = Path(__file__).resolve().parents[2]


@unittest.skipUnless(HAS_MCP, "official MCP SDK not installed")
class SelectionBindingTests(unittest.TestCase):
    def test_only_exact_documented_layout_is_inferred(self):
        home = Path("/tmp/selection-fixture")
        archive = home / "oracle/SOL/history.sqlite3"
        self.assertEqual(selection_home(archive, "SOL/USD"), home)
        self.assertEqual(selection_home(archive, "SOL/USD", home), home)
        self.assertIsNone(selection_home(home / "history.sqlite3", "SOL/USD"))
        self.assertIsNone(
            selection_home(home / "oracle/BTC/history.sqlite3", "SOL/USD")
        )
        with self.assertRaisesRegex(ValueError, "control_home_archive_mismatch"):
            selection_home(archive, "SOL/USD", home / "other")

    def test_unavailable_adapter_never_ignores_explicit_or_later_saved_selection(self):
        original_import = builtins.__import__

        def without_adapter(name, *args, **kwargs):
            if name == "ecosystem.votes":
                raise ImportError("fixture unavailable dependency")
            return original_import(name, *args, **kwargs)

        engine = SimpleNamespace(
            instrument="SOL/USD",
            predictions=lambda: {"status": "available", "signal": "Strong Buy"},
        )
        with (
            tempfile.TemporaryDirectory() as root,
            patch("builtins.__import__", side_effect=without_adapter),
        ):
            home = Path(root)
            optional = selected_prediction_view(engine, home)
            required = selected_prediction_view(engine, home, required=True)
            self.assertEqual(optional()["signal"], "Strong Buy")
            self.assertEqual(required()["status"], "unavailable")
            (home / "voters.sqlite3").write_text("fixture selection exists")
            self.assertEqual(optional()["status"], "unavailable")
            self.assertIsNone(optional()["signal"])
            self.assertNotIn("fixture unavailable", json.dumps(optional()))


@unittest.skipUnless(HAS_MCP, "official MCP SDK not installed")
class SelectedProtocolTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_stdio_tools_resources_and_selection_invalidation(self):
        # Controlled native evidence: one current call and twenty prior resolved
        # calls from the same policy. This is protocol evidence, not market alpha.
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            archive = home / "oracle/SOL/history.sqlite3"
            engine = OracleEngine(archive, instrument="SOL/USD")
            now = time.time()
            engine.ingest(
                {
                    "source": "fixture",
                    "venue": "fixture",
                    "kind": "reference",
                    "event_id": "current",
                    "instrument": "SOL/USD",
                    "observed_at": now,
                    "received_at": now,
                    "price": 100,
                },
                now=now,
            )
            card = engine.strategies()[0]
            with engine.store.connection() as db:
                for index in range(21):
                    identity = f"fixture-{index}"
                    issued = now if index == 20 else now - 180 - index * 60
                    expiry = issued + 60
                    body = {
                        "id": identity,
                        "strategy_id": card["strategy_id"],
                        "version": card["version"],
                        "parameters": card["parameters"],
                        "policy_hash": engine.policy_hash,
                        "instrument": "SOL/USD",
                        "issued_at": issued,
                        "expires_at": expiry,
                        "direction": 1,
                    }
                    db.execute(
                        "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                        (
                            identity,
                            card["strategy_id"],
                            card["version"],
                            issued,
                            expiry,
                            1,
                            100,
                            canonical(body),
                        ),
                    )
                    if index < 20:
                        db.execute(
                            "INSERT INTO resolutions VALUES(?,?,?,?,?)",
                            (identity, 1, 1, expiry, "{}"),
                        )
            votes.set_voters(home, "SOL/USD", [], 0)
            before = hashlib.sha256(archive.read_bytes()).hexdigest()
            notices = []
            changed = asyncio.Event()

            async def handle(message):
                if isinstance(message, types.ServerNotification):
                    notices.append(message)
                    changed.set()

            # Stabilize volatile display clocks inside this fixture only. A
            # further invalidation must then reflect a real selection change.
            script = """
import sys
from ecosystem import votes
from oracle import server
original = votes.report
def stable(*args, **kwargs):
    result = original(*args, **kwargs)
    result['as_of'] = 1
    if 'age_seconds' in result.get('market', {}):
        result['market']['age_seconds'] = 0
    return result
votes.report = stable
raise SystemExit(server.main(sys.argv[1:]))
"""
            params = StdioServerParameters(
                command=sys.executable,
                args=[
                    "-c",
                    script,
                    "--archive",
                    str(archive),
                    "--instrument",
                    "SOL/USD",
                    "--control-home",
                    str(home),
                    "--poll-seconds",
                    ".1",
                ],
                env={"PYTHONPATH": str(REPO)},
            )
            async with (
                stdio_client(params) as (reader, writer),
                ClientSession(reader, writer, message_handler=handle) as client,
            ):
                await client.initialize()
                self.assertEqual(len((await client.list_tools()).tools), 8)
                self.assertEqual(len((await client.list_resources()).resources), 3)
                initial = (
                    await client.call_tool("oracle_predictions", {})
                ).structuredContent
                self.assertTrue(initial["ok"])
                self.assertEqual(initial["data"]["selected_ids"], [])
                self.assertEqual(initial["data"]["reason"], "no_selected_voters")
                self.assertIsNone(initial["data"]["signal"])
                uri = AnyUrl("oracle://predictions")
                await client.subscribe_resource(uri)
                await asyncio.wait_for(changed.wait(), 3)
                changed.clear()
                stable_count = len(notices)
                await asyncio.sleep(
                    0.25
                )  # Tests this polling feature's unchanged interval.
                self.assertEqual(len(notices), stable_count)
                votes.set_voters(home, "SOL/USD", [card["strategy_id"]], 1)
                await asyncio.wait_for(changed.wait(), 3)
                selected = (
                    await client.call_tool("oracle_predictions", {})
                ).structuredContent["data"]
                self.assertEqual(selected["signal"], "Strong Buy")
                self.assertEqual(selected["selection"]["revision"], 2)
                resource = json.loads(
                    (await client.read_resource(uri)).contents[0].text
                )["data"]
                self.assertEqual(resource["selected_ids"], [card["strategy_id"]])
                self.assertEqual(resource["balance_percent"], 100)
                self.assertEqual(selected["aggregate"], resource["aggregate"])
                vetoed = (await client.call_tool("oracle_veto", {})).structuredContent[
                    "data"
                ]
                self.assertEqual(vetoed["signal"], "Strong Buy")
                self.assertFalse(vetoed["enforcement"])
                await client.unsubscribe_resource(uri)
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)

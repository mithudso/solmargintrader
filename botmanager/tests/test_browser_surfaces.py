from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from botmanager.adapters.extension import BrowserStore
from botmanager.registry import CommandContext, dispatch

from tests.test_extension_adapter import ORIGIN, snapshot


class BrowserSurfaceTests(unittest.TestCase):
    def test_real_registry_discovery_control_guards_and_offline_nulls(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("botmanager.adapters.default_installations", return_value=()),
        ):
            home = Path(directory)
            store, context = BrowserStore(home), CommandContext(home=home)
            owner = snapshot()
            store.poll(
                {"schema_version": 1, "snapshot": owner, "receipts": []},
                origin=ORIGIN,
                allowed_origins=[ORIGIN],
            )
            identity = "browser:" + owner["installation_id"] + ":grid"
            before = store.path.read_bytes()
            discovery = dispatch("discover", {}, context)
            self.assertTrue(discovery["ok"], discovery)
            browsers = [
                record
                for record in discovery["data"]["installations"]
                if record["source"] == "browser"
            ]
            self.assertEqual(len(browsers), 1)
            self.assertEqual(browsers[0]["installation_id"], owner["installation_id"])
            result = dispatch("status", {"identity": identity, "why": True}, context)
            self.assertTrue(result["ok"], result)
            status = result["data"]
            self.assertEqual(status["identity"], identity)
            self.assertEqual(status["observed_state"], "stopped")
            self.assertIsNone(status["financials"]["exposure_usd"]["value"])
            self.assertEqual(store.path.read_bytes(), before)
            missing = dispatch("start", {"identity": identity}, context)
            self.assertEqual(missing["error"]["code"], "expected_observation_required")
            start = dispatch(
                "start",
                {
                    "identity": identity,
                    "request_id": str(uuid4()),
                    "expected_generation": 0,
                    "expected_config_hash": owner["config_hash"],
                },
                context,
            )
            self.assertTrue(start["ok"], start)
            self.assertEqual(start["data"]["outcome"], "pending")
            stop = dispatch(
                "stop",
                {
                    "identity": identity,
                    "request_id": str(uuid4()),
                    "expected_generation": 0,
                    "expected_config_hash": owner["config_hash"],
                },
                context,
            )
            self.assertTrue(stop["ok"], stop)
            receipt = dispatch(
                "browser-receipt", {"request_id": start["data"]["request_id"]}, context
            )
            self.assertEqual(receipt["data"]["outcome"], "skipped")

    def test_armed_owner_is_not_reported_as_stopped_paper(self):
        with tempfile.TemporaryDirectory() as directory:
            home, owner = Path(directory), snapshot()
            owner.update(mode="full-auto", armed=True)
            BrowserStore(home).poll(
                {"schema_version": 1, "snapshot": owner, "receipts": []},
                origin=ORIGIN,
                allowed_origins=[ORIGIN],
            )
            result = dispatch(
                "status",
                {"identity": "browser:" + owner["installation_id"] + ":grid"},
                CommandContext(home=home),
            )
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["data"]["observed_state"], "unknown")
            self.assertIsNone(result["data"]["mode"])
            self.assertFalse(result["data"]["action_capabilities"]["stop"]["available"])

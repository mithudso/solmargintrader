"""Native Volty inspection exports only bounded public evidence."""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from soltui import commands


class VoltyStatusTests(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.dict(os.environ, {"SOLTUI_CONFIG_DIR": str(directory)}))
        self.path = directory / "zec-volty" / "status.json"
        self.path.parent.mkdir()
        self.at = int(time.time())

    def dispatch(self):
        return commands.dispatch("zec.volty.status", {}, surface="native", ctx=object(), quiet=True)

    def snapshot(self, **values):
        return {
            "schema": 1, "mode": "observe", "state": "watching", "updated_at": self.at,
            "signal": None, "orders": [], **values,
        }

    def write(self, value):
        self.path.write_text(json.dumps(value), encoding="utf-8")

    def test_missing_corrupt_or_future_status_remains_unavailable(self):
        self.assertTrue(commands.COMMANDS["zec.volty.status"].read_only)
        self.assertIsNone(self.dispatch()["result"])
        self.path.write_bytes(b'{"schema": 1, "credential":')
        self.assertIsNone(self.dispatch()["result"])
        self.write(self.snapshot(updated_at=self.at + 900))
        self.assertIsNone(self.dispatch()["result"])

    def test_reader_never_follows_final_symlinks_or_reads_unbounded_input(self):
        private = self.path.parent / "private-file"
        private.write_text(json.dumps(self.snapshot()), encoding="utf-8")
        self.path.symlink_to(private)
        self.assertIsNone(self.dispatch()["result"])
        self.path.unlink()
        self.path.write_bytes(private.read_bytes() + b" " * (256 * 1024))
        self.assertIsNone(self.dispatch()["result"])

    def test_only_public_signal_and_order_fields_cross_the_bridge(self):
        signal = {"side": "buy", "at": self.at, "event_id": "volty:1", "mark": 600,
                  "upper": 599, "lower": 580}
        fill = {"signature": "0:venue-signature", "price": "600.10", "size": "0.017",
                "fee": "0.01", "timestamp": self.at}
        order = {"event_id": "volty:1", "client_order_id": "1234", "side": "buy", "leg": "open", "state": "filled",
                 "order_id": "100900000000000123456", "requested_quantity": "0.017",
                 "filled_quantity": "0.017", "updated_at": self.at, "fills": [fill]}
        expected = self.snapshot(mode="live", state="armed", signal=signal, orders=[order])
        self.write({**expected, "private_key": "hidden", "signal": {**signal, "wallet": "hidden"},
                    "orders": [{**order, "path": "hidden", "fills": [{**fill, "internal": "hidden"}]}]})
        self.assertEqual(self.dispatch()["result"], expected)

    def test_observe_preserves_live_history_and_unverified_order_remains_pending(self):
        order = {"event_id": "volty:1", "client_order_id": "1234", "side": "buy", "leg": "open", "state": "acknowledged",
                 "order_id": None, "requested_quantity": "0.017", "filled_quantity": None,
                 "updated_at": self.at, "fills": []}
        self.write(self.snapshot(orders=[order]))
        self.assertEqual(self.dispatch()["result"]["orders"], [order])
        self.write(self.snapshot(mode="live", state="checking", orders=[order]))
        self.assertEqual(self.dispatch()["result"]["orders"], [order])
        self.write(self.snapshot(mode="live", state="checking", orders=[{**order, "state": "filled"}]))
        self.assertIsNone(self.dispatch()["result"])

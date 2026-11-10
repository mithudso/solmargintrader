from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from botmanager.adapters.extension import (
    BrowserStore,
    browser_quiescent,
    resolve_browser,
)
from botmanager.domain import ManagerError

ORIGIN = "chrome-extension://" + "a" * 32


def snapshot():
    return {
        "installation_id": str(uuid4()),
        "native_id": "grid",
        "generation": 0,
        "config_revision": 1,
        "config_hash": "1" * 64,
        "source_hash": "2" * 64,
        "runtime_id": None,
        "running": False,
        "mode": "dry-run",
        "armed": False,
        "kill_switch": False,
        "extension_version": "0.6.4",
    }


class BrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = BrowserStore(Path(self.temp.name))
        self.addCleanup(self.temp.cleanup)
        self.owner = snapshot()

    def poll(self, receipts=(), owner=None, **kwargs):
        return self.store.poll(
            {
                "schema_version": 1,
                "snapshot": owner or self.owner,
                "receipts": list(receipts),
            },
            origin=ORIGIN,
            allowed_origins=[ORIGIN],
            now=100,
            **kwargs,
        )

    def control(self, operation="start", request_id=None, **kwargs):
        return self.store.control(
            self.owner["installation_id"],
            operation,
            request_id or str(uuid4()),
            expected_generation=0,
            expected_config_hash=self.owner["config_hash"],
            now=100,
            **kwargs,
        )

    def test_reads_do_not_create_registration_and_profiles_stay_distinct(self):
        self.assertEqual(self.store.discover(now=100), [])
        self.assertFalse(self.store.path.exists())
        self.poll()
        other = snapshot()
        self.poll(owner=other)
        records = self.store.discover(now=100)
        self.assertEqual(len(records), 2)
        self.assertNotEqual(
            records[0]["bots"][0]["bot_id"], records[1]["bots"][0]["bot_id"]
        )
        self.assertEqual(self.store.discover(now=200)[0]["state"], "offline")
        adapter = resolve_browser(
            "browser:" + self.owner["installation_id"] + ":grid", home=self.store.home
        )
        self.assertIsNotNone(adapter)

    def test_strict_envelopes_origin_and_canary_exclusion(self):
        message = {"schema_version": 1, "snapshot": self.owner, "receipts": []}
        for changed in (
            {**message, "secret_canary": "never-persist-this"},
            {**message, "schema_version": True},
            {**message, "snapshot": {**self.owner, "secrets": "never-persist-this"}},
        ):
            with self.assertRaises(ManagerError):
                self.store.poll(changed, origin=ORIGIN, allowed_origins=[ORIGIN])
        with self.assertRaises(ManagerError):
            self.store.poll(
                message,
                origin="chrome-extension://" + "b" * 32,
                allowed_origins=[ORIGIN],
            )
        self.assertFalse(self.store.path.exists())
        self.poll()
        self.assertNotIn(
            "never-persist-this", self.store.path.read_bytes().decode(errors="ignore")
        )

    def test_write_ahead_replay_lost_ack_transplant_and_stop_revocation(self):
        self.poll()
        started = self.control()
        self.assertEqual(started["outcome"], "pending")
        command = self.poll()["controls"][0]
        stop = self.control("stop")
        self.assertEqual(
            self.store.receipt(started["request_id"])["reason"], "revoked_by_later_stop"
        )
        self.assertEqual([c["operation"] for c in self.poll()["controls"]], ["stop"])
        self.assertEqual(self.control("stop", stop["request_id"]), stop)
        with self.assertRaises(ManagerError):
            self.control("start", stop["request_id"])
        owner = {**self.owner, "generation": 1}
        receipt = {
            "request_id": stop["request_id"],
            "outcome": "acknowledged",
            "reason": "paper_stopped",
            "generation": 1,
            "runtime_id": None,
            "config_hash": command["expected_config_hash"],
        }
        result = self.poll([receipt], owner=owner)
        self.assertEqual(result["acknowledged"], [stop["request_id"]])
        self.assertEqual(
            self.poll([receipt], owner=owner)["acknowledged"], [stop["request_id"]]
        )
        self.assertEqual(
            self.store.receipt(stop["request_id"])["outcome"], "acknowledged"
        )
        self.assertTrue(
            browser_quiescent(self.store.home) is False
        )  # fixture clock expired at real time

    def test_generation_config_and_expired_owner_refuse(self):
        self.poll()
        stale = self.store.control(
            self.owner["installation_id"],
            "start",
            str(uuid4()),
            expected_generation=1,
            expected_config_hash="3" * 64,
            now=100,
        )
        self.assertEqual(stale["reason"], "browser_owner_context_changed")
        expired = self.store.control(
            self.owner["installation_id"],
            "start",
            str(uuid4()),
            expected_generation=0,
            expected_config_hash="1" * 64,
            now=300,
        )
        self.assertEqual(expired["reason"], "browser_owner_expired")
        for key in ("generation", "config_revision"):
            owner = copy.deepcopy(self.owner)
            owner[key] = -1
            with self.assertRaises(ManagerError):
                self.poll(owner=owner)

    def test_live_armed_owner_is_unsupported_and_stop_does_not_claim_success(self):
        self.owner.update(mode="full-auto", armed=True)
        self.poll()
        self.assertEqual(self.store.discover(now=100)[0]["state"], "unsupported")
        for operation in ("start", "stop"):
            self.assertEqual(
                self.control(operation)["reason"], "browser_paper_slot_unavailable"
            )

    def test_queued_start_expires_before_a_reappearing_owner_can_execute_it(self):
        self.poll()
        receipt = self.control()
        message = {"schema_version": 1, "snapshot": self.owner, "receipts": []}
        reply = self.store.poll(
            message, origin=ORIGIN, allowed_origins=[ORIGIN], now=300
        )
        self.assertEqual(reply["controls"], [])
        self.assertEqual(
            self.store.receipt(receipt["request_id"])["reason"], "browser_owner_expired"
        )

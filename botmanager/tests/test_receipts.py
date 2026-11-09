from __future__ import annotations

import json
import unittest
from dataclasses import FrozenInstanceError
from uuid import uuid4

from botmanager.domain import ManagerError


class ReceiptTests(unittest.TestCase):
    def body(self, **changes):
        return {
            "schema_version": 1,
            "bot_id": str(uuid4()),
            "operation": "stop",
            "request_id": str(uuid4()),
            "runtime_id": "session-7",
            "owner_id": "soltui-installation-2",
            "owner_generation": 3,
            "config_revision": 2,
            "outcome": "acknowledged",
            "reason": "owner_acknowledged",
            "metadata": {"detail_ref": "journal/receipt-2", "elapsed_seconds": 0.25},
            **changes,
        }

    def receipt(self, **changes):
        from botmanager.receipts import CommandReceipt

        return CommandReceipt(**self.body(**changes))

    def test_all_outcomes_round_trip_with_separate_owner_and_config_identity(self):
        from botmanager.receipts import CommandReceipt

        for outcome in ("acknowledged", "pending", "skipped", "failed", "unknown"):
            with self.subTest(outcome=outcome):
                receipt = self.receipt(outcome=outcome)
                body = json.loads(json.dumps(receipt.to_dict(), allow_nan=False))
                self.assertEqual(CommandReceipt.from_dict(body).to_dict(), body)
                self.assertEqual(body["runtime_id"], "session-7")
                self.assertEqual(body["owner_id"], "soltui-installation-2")
                self.assertEqual(body["owner_generation"], 3)
                self.assertEqual(body["config_revision"], 2)

    def test_unknown_is_not_retryable_or_evidence_of_no_exposure(self):
        receipt = self.receipt(outcome="unknown", reason="acknowledgment_lost")
        self.assertFalse(receipt.safe_to_retry)
        self.assertTrue(receipt.reconciliation_required)
        body = receipt.to_dict()
        self.assertFalse(body["safe_to_retry"])
        self.assertTrue(body["reconciliation_required"])
        self.assertNotIn("exposure_cleared", body)
        self.assertNotIn("stopped", body)

    def test_runtime_identity_can_be_explicitly_unavailable(self):
        receipt = self.receipt(
            runtime_id=None,
            owner_id=None,
            owner_generation=None,
            outcome="skipped",
            reason="runtime_not_available",
        )
        self.assertIsNone(receipt.runtime_id)
        self.assertIsNone(receipt.owner_id)
        self.assertIsNone(receipt.owner_generation)

    def test_unversioned_owner_revision_requires_explicit_reason_and_can_bind_hash(
        self,
    ):
        from botmanager.receipts import CommandReceipt

        receipt = self.receipt(
            config_revision=None,
            config_revision_unavailable_reason="owner_does_not_version_configurations",
            metadata={"config_hash": "a" * 64},
        )
        self.assertIsNone(receipt.config_revision)
        self.assertEqual(receipt.metadata["config_hash"], "a" * 64)
        self.assertEqual(
            CommandReceipt.from_dict(receipt.to_dict()).to_dict(), receipt.to_dict()
        )
        self.assertIsNone(self.receipt().config_revision_unavailable_reason)

    def test_revision_reason_must_match_missing_revision_and_use_fixed_enum(self):
        from botmanager.receipts import CommandReceipt

        for changes in (
            {"config_revision": None},
            {"config_revision": None, "config_revision_unavailable_reason": "unknown"},
            {"config_revision": None, "config_revision_unavailable_reason": True},
            {
                "config_revision_unavailable_reason": "owner_does_not_version_configurations"
            },
        ):
            with self.subTest(changes=changes), self.assertRaises(ManagerError):
                self.receipt(**changes)
        body = self.receipt().to_dict()
        with self.assertRaises(ManagerError):
            CommandReceipt.from_dict({**body, "config_revision": None})

    def test_types_versions_and_closed_enums_are_strict(self):
        invalid = {
            "schema_version": [True, 1.0, 2],
            "bot_id": [None, "bad-id", 1],
            "request_id": [None, "", 1],
            "operation": [None, "kill_everything", True],
            "runtime_id": [True, 7, ""],
            "owner_id": [True, {}, ""],
            "owner_generation": [True, -1, 2.0, "2"],
            "config_revision": [True, 0, 2.0, "2"],
            "outcome": [None, "success", "outcome_unknown", True, []],
            "reason": [None, "", {}, "credential canary value"],
            "metadata": [None, [], "body"],
        }
        for field, values in invalid.items():
            for value in values:
                with (
                    self.subTest(field=field, value=value),
                    self.assertRaises(ManagerError),
                ):
                    self.receipt(**{field: value})

    def test_metadata_rejects_nonfinite_and_arbitrary_owner_bodies_without_reflection(
        self,
    ):
        for metadata in (
            {"elapsed_seconds": float("nan")},
            {"elapsed_seconds": float("inf")},
            {"elapsed_seconds": -1},
            {"elapsed_seconds": True},
            {"elapsed_seconds": "1"},
            {"config_hash": "a" * 63},
            {"config_hash": "A" * 64},
            {"config_hash": "g" * 64},
            {"config_hash": 1},
            {"owner_response": {"api_key": "receipt-credential-canary"}},
            {"detail_ref": {"token": "receipt-credential-canary"}},
            {"detail_ref": ""},
            {1: "receipt-credential-canary"},
        ):
            with (
                self.subTest(metadata=metadata),
                self.assertRaises(ManagerError) as raised,
            ):
                self.receipt(metadata=metadata)
            self.assertNotIn("receipt-credential-canary", str(raised.exception))

    def test_receipts_and_metadata_are_immutable_and_detached(self):
        metadata = {"detail_ref": "journal/one"}
        receipt = self.receipt(metadata=metadata)
        metadata["detail_ref"] = "journal/two"
        self.assertEqual(receipt.metadata["detail_ref"], "journal/one")
        with self.assertRaises(FrozenInstanceError):
            receipt.outcome = "failed"
        with self.assertRaises(TypeError):
            receipt.metadata["detail_ref"] = "journal/three"
        body = receipt.to_dict()
        body["metadata"]["detail_ref"] = "journal/four"
        self.assertEqual(receipt.metadata["detail_ref"], "journal/one")

    def test_deserialization_refuses_forged_retry_flags_or_unknown_fields(self):
        from botmanager.receipts import CommandReceipt

        body = self.receipt(outcome="unknown").to_dict()
        for changes in (
            {"safe_to_retry": True},
            {"safe_to_retry": 0},
            {"reconciliation_required": False},
            {"reconciliation_required": 1},
            {"owner_body": "receipt-credential-canary"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ManagerError):
                CommandReceipt.from_dict({**body, **changes})
        for value in (None, [], "body"):
            with self.assertRaises(ManagerError):
                CommandReceipt.from_dict(value)

    def test_control_operations_do_not_alias_stop_cancel_close_and_disarm(self):
        for operation in (
            "start",
            "pause_entries",
            "stop",
            "cancel_orders",
            "close_position",
            "emergency_stop",
        ):
            self.assertEqual(self.receipt(operation=operation).operation, operation)

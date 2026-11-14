"""Offline trust-boundary counterexamples from the complete component audit."""

from __future__ import annotations

import copy
import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from botmanager.adapters.executor import ExecutorAdapter
from botmanager.backup import restore_backup
from botmanager.diagnostics_commands import _write_bundle
from botmanager.domain import ManagerError, fingerprint
from botmanager.health import health_snapshot
from botmanager.registry import CommandContext, dispatch
from botmanager.reports import render_report
from botmanager.research_owner import OwnerClient
from botmanager.status import runtime_snapshot
from botmanager.strategies import rebind_checkpoint, validate_checkpoint
from botmanager.strategies.base import identity
from botmanager.strategies.grid import evaluate

from botmanager import data as data_module
from botmanager import transport
from tests.test_health import runtime
from tests.test_paper import grid, recording


class FullAuditRegressionTests(unittest.TestCase):
    def status_fixture(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        spec = grid()
        data = data_module.load_recording(recording(Path(temp.name), 80))
        checkpoint = evaluate(spec, data, len(data["bars"]))
        now = data["identity"]["end_ts"] + 60
        row = {
            "spec": spec.to_dict(),
            "bot_id": spec.bot_id,
            "input": data,
            "checkpoint": checkpoint,
            "runtime_id": "fixture",
            "owner": None,
            "generation": 1,
            "desired": "running",
            "observed": "waiting",
            "reason": "reference_input_exhausted",
            "heartbeat": now - 1,
            "evaluated": now - 1,
            "tick_started": None,
            "cursor": checkpoint["cursor"],
        }
        return spec, row, now

    def test_segmented_status_uses_absolute_cursor_and_total_bars(self):
        spec, row, now = self.status_fixture()
        row["input"]["bar_offset"] = 512
        total = 512 + len(row["input"]["bars"])
        row["cursor"] = row["checkpoint"]["cursor"] = total
        result = runtime_snapshot(
            spec, row, now=now, worker_alive=True, supervisor_alive=True
        )
        self.assertEqual(result["reference_run"]["total_bars"], total)
        self.assertEqual(
            result["latest_decision"]["value"], "reference_input_exhausted"
        )
        self.assertIsNone(result["next_trigger"]["value"])

    def test_public_status_does_not_clamp_future_clocks_to_fresh_observations(self):
        spec, row, now = self.status_fixture()
        row["heartbeat"] = row["evaluated"] = now + 1
        row["input"]["descriptor"].update(max_source_age_s=10, activation_at=now - 1)
        row["input"]["prospective"] = {
            "latest_observed": now + 1,
            "health": "available",
            "delivery": "prospective_reference",
        }
        result = runtime_snapshot(
            spec, row, now=now, worker_alive=True, supervisor_alive=True
        )
        self.assertEqual(result["observed_state"], "degraded")
        self.assertIsNone(result["heartbeat_age_seconds"]["value"])
        self.assertIsNone(result["data_age_seconds"]["value"])
        self.assertIsNone(result["last_completed_evaluation"]["value"])
        self.assertEqual(result["input_quality"]["state"], "unavailable")

    def test_report_csv_treats_untrusted_formula_text_as_text_and_keeps_losses_numeric(
        self,
    ):
        report = {
            "name": '=HYPERLINK("https://example.invalid")',
            "pnl": -2.5,
            "label": "\t+SUM(1,2)",
        }
        rows = dict(list(csv.reader(io.StringIO(render_report(report, "csv"))))[1:])
        self.assertEqual(rows["name"], "'" + report["name"])
        self.assertEqual(rows["label"], "'" + report["label"])
        self.assertEqual(rows["pnl"], "-2.5")

    def test_non_object_backup_manifest_is_refused_without_creating_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "backup"
            source.mkdir()
            destination = Path(tmp) / "restored"
            for value in ([], None, 1, True, "AUDIT_CANARY"):
                (source / "manifest.json").write_text(json.dumps(value))
                with self.subTest(value_type=type(value).__name__):
                    with self.assertRaises(ManagerError) as caught:
                        restore_backup(source, destination)
                    self.assertEqual(caught.exception.code, "backup_unavailable")
                    self.assertNotIn("AUDIT_CANARY", str(caught.exception))
                    self.assertFalse(destination.exists())

    def test_non_grid_checkpoint_schema_rejects_boolean_version(self):
        spec = SimpleNamespace(
            strategy_id="dca",
            bot_id="synthetic",
            config_hash="synthetic",
            config_revision=1,
            strategy_version="synthetic",
            venue="synthetic",
            base_mint="base",
            quote_mint="quote",
            execution_model="synthetic",
        )
        data = {
            "snapshot_hash": "synthetic",
            "identity": {"quote_currency": "USD"},
            "bars": [],
        }
        expected = identity(spec, data)
        checkpoint = {
            "schema_version": True,
            "cursor": 0,
            "last_bar_ts": None,
            "quote_currency": "USD",
            "identity": expected,
            "run_hash": fingerprint(expected),
        }
        with self.assertRaises(ManagerError) as caught:
            validate_checkpoint(spec, data, checkpoint)
        self.assertEqual(caught.exception.code, "corrupt_checkpoint")

    def test_returned_engine_identity_cannot_poison_later_identity_checks(self):
        cached = getattr(
            data_module, "_cached_engine_identity", data_module.engine_identity
        )
        cached.cache_clear()
        self.addCleanup(cached.cache_clear)
        expected = copy.deepcopy(data_module.engine_identity())
        exposed = data_module.engine_identity()
        exposed["modules"]["synthetic"] = "synthetic-changed-hash"
        exposed["numpy"] = "synthetic-version"
        self.assertEqual(data_module.engine_identity(), expected)

    def test_diagnostics_publish_preserves_a_concurrently_created_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "diagnostics.zip"
            canary = b"synthetic-existing-file"
            output.write_bytes(canary)
            original_exists = Path.exists

            def stale_exists(path):
                # Model a contender publishing just after the initial check.
                return False if path == output else original_exists(path)

            with (
                patch.object(Path, "exists", stale_exists),
                self.assertRaises(FileExistsError),
            ):
                _write_bundle(output, {}, {})
            self.assertEqual(output.read_bytes(), canary)
            self.assertEqual(list(Path(tmp).iterdir()), [output])

    def test_non_object_cycle_documents_return_sanitized_failure_envelopes(self):
        with tempfile.TemporaryDirectory() as tmp:
            document = Path(tmp) / "cycle.json"
            for value in ([], None, "synthetic", 1, True):
                with self.subTest(value=value):
                    document.write_text(json.dumps(value))
                    response = dispatch(
                        "cycle-check",
                        {"descriptor": str(document)},
                        CommandContext(home=Path(tmp) / "manager"),
                    )
                    self.assertFalse(response["ok"])
                    self.assertEqual(response["error"]["code"], "input_unavailable")
            self.assertFalse((Path(tmp) / "manager").exists())

    def test_peer_credentials_unavailable_refuses_the_transport(self):
        with (
            patch("botmanager.transport.sys.platform", "synthetic-unsupported"),
            patch("botmanager.transport.socket", SimpleNamespace()),
            self.assertRaises(ManagerError) as caught,
        ):
            transport._peer(SimpleNamespace())
        self.assertEqual(caught.exception.code, "unsafe_transport")

    def test_adoption_errors_do_not_echo_dependency_exception_payloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = data_module.load_recording(recording(Path(tmp)))
            spec = grid()
            checkpoint = evaluate(spec, data, 1)
            canary = "SYNTHETIC_CANARY_491"
            for error in (KeyError(canary), ValueError(canary), TypeError(canary)):
                with (
                    self.subTest(kind=type(error).__name__),
                    patch(
                        "backtester.core.gridsim.rebind_grid_state", side_effect=error
                    ),
                    self.assertRaises(ManagerError) as caught,
                ):
                    rebind_checkpoint(spec, data, checkpoint, entries_paused=True)
                self.assertEqual(caught.exception.code, "reconciliation_required")
                self.assertNotIn(canary, str(caught.exception))

    def test_research_owner_non_object_results_fail_at_the_protocol_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            owner = OwnerClient(
                {
                    "version": 2,
                    "interpreter": sys.executable,
                    "repository": tmp,
                    "config_root": tmp,
                    "authority": None,
                    "expected_identity": {},
                }
            )
            for value in ([], None, "SYNTHETIC_CANARY_491", 1):
                response = json.dumps(
                    {
                        "ok": True,
                        "command": "research.protocol",
                        "result": value,
                        "error": None,
                    }
                ).encode()
                with (
                    self.subTest(kind=type(value).__name__),
                    patch(
                        "botmanager.research_owner.bounded_process",
                        return_value=(0, response, b""),
                    ),
                    self.assertRaises(ManagerError) as caught,
                ):
                    owner.call("status", {})
                self.assertEqual(caught.exception.code, "research_unavailable")
                self.assertNotIn("SYNTHETIC_CANARY_491", str(caught.exception))

    def test_malformed_executor_error_cannot_erase_submission_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmp:
            adapter = ExecutorAdapter(
                {
                    "version": 1,
                    "interpreter": sys.executable,
                    "home": tmp,
                    "identity": {
                        "protocol": 1,
                        "wallet": "synthetic",
                        "source_digest": "0" * 64,
                        "installation_digest": "0" * 64,
                        "config_digest": "0" * 64,
                        "venue": "jupiter-swap-v1",
                    },
                }
            )
            response = json.dumps(
                {
                    "ok": False,
                    "command": "manager.swap",
                    "result": None,
                    "error": "SYNTHETIC_CANARY_491",
                }
            ).encode()
            with (
                patch(
                    "botmanager.adapters.executor.bounded_process",
                    return_value=(1, response, b""),
                ),
                self.assertRaises(ManagerError) as caught,
            ):
                adapter._call("manager.swap", {})
            self.assertEqual(caught.exception.code, "executor_outcome_unknown")
            self.assertNotIn("SYNTHETIC_CANARY_491", str(caught.exception))

    def test_future_or_unrepresentable_clocks_do_not_certify_fresh_health(self):
        for value in (101, 10**400):
            with self.subTest(value_type=type(value).__name__):
                row = runtime()
                row["heartbeat"] = value
                row["evaluated"] = value
                row["input"]["prospective"]["latest_observed"] = value
                result = health_snapshot(row, now=100)
                self.assertNotEqual(result["process"]["state"], "healthy")
                self.assertNotEqual(result["input"]["state"], "available")
                self.assertNotEqual(result["evaluation"]["state"], "completed")

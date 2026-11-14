from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.config import resolve_config
from botmanager.domain import BotSpec
from botmanager.registry import COMMANDS, CommandContext, dispatch
from botmanager.store import ManagerStore

from tests import isolated_default_owner


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(isolated_default_owner())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "manager"
        self.context = CommandContext(home=self.home)
        self.spec = BotSpec.create(
            "pinned-grid", "grid", resolve_config("grid", {}, {"range_pct": 8.0}, None)
        )

    def snapshot(self):
        from botmanager.status import draft_snapshot

        return draft_snapshot(self.spec)

    def test_draft_dimensions_are_independent_and_observations_are_unavailable(self):
        status = self.snapshot()
        self.assertEqual(status["schema_version"], 1)
        self.assertEqual((status["mode"], status["armed"]), ("paper", False))
        self.assertEqual(status["lifecycle"], "draft")
        self.assertEqual(status["desired_state"], "draft")
        self.assertEqual(status["observed_state"], "not_running")
        self.assertEqual(status["input_quality"]["state"], "missing")
        self.assertEqual(status["owner_reachability"]["state"], "not_applicable")
        for key in ("runtime_id", "runtime_owner_id", "owner_generation"):
            self.assertIsNone(status[key])
        self.assertEqual(status["runtime_reason"], "runtime_not_available")
        for key in (
            "heartbeat_age_seconds",
            "data_age_seconds",
            "last_completed_evaluation",
            "latest_decision",
            "next_trigger",
            "submission_certainty",
        ):
            self.assertIsNone(status[key]["value"], key)
            self.assertTrue(status[key]["reason"], key)
        self.assertIn("runtime_not_available", status["blockers"])

    def test_config_and_spec_owner_are_distinct_from_runtime_identity(self):
        status = self.snapshot()
        for key in (
            "bot_id",
            "display_name",
            "source",
            "owner",
            "strategy_id",
            "strategy_version",
            "config_revision",
            "config_hash",
            "source_identity",
        ):
            self.assertEqual(status[key], getattr(self.spec, key))
        self.assertEqual(status["spec_owner"], "manager")
        self.assertIsNone(status["runtime_owner_id"])
        identity = status["evidence_identity"]
        for key in (
            "strategy_id",
            "strategy_version",
            "config_revision",
            "config_hash",
            "venue",
            "base_mint",
            "quote_mint",
            "bar_seconds",
            "execution_model",
        ):
            self.assertEqual(identity[key], getattr(self.spec, key))
        for mode in ("backtest", "paper", "live"):
            evidence = status["evidence"][mode]
            self.assertEqual(evidence["state"], "untested")
            for key in (
                "dataset_hash",
                "proof_hash",
                "start_at",
                "end_at",
                "engine_version",
                "cost_model_id",
                "result_ref",
            ):
                self.assertIsNone(evidence[key]["value"])
                self.assertTrue(evidence[key]["reason"])
        self.assertFalse(status["evidence"]["live"]["venue_compatibility_verified"])

    def test_financial_unknowns_never_become_zero_or_virtual_allocation(self):
        status = self.snapshot()
        for key in (
            "exposure_usd",
            "allocated_capital_usd",
            "realized_net_pnl_usd",
            "unrealized_net_pnl_usd",
            "costs_usd",
        ):
            self.assertIsNone(status["financials"][key]["value"])
            self.assertTrue(status["financials"][key]["reason"])
        virtual = status["configured_virtual_capital"]
        self.assertEqual(virtual["value"], self.spec.resolved_values["capital_usd"])
        self.assertFalse(virtual["reserved"])

    def test_actions_have_distinct_semantics_and_honest_availability(self):
        status = self.snapshot()
        self.assertEqual(status["capabilities"], ["inspect"])
        actions = status["action_capabilities"]
        self.assertEqual(
            set(actions),
            {
                "inspect",
                "start",
                "pause_entries",
                "stop",
                "cancel_orders",
                "close_position",
                "emergency_stop",
            },
        )
        self.assertTrue(actions["inspect"]["available"])
        for operation in set(actions) - {"inspect"}:
            self.assertFalse(actions[operation]["available"])
            self.assertEqual(actions[operation]["reason"], "runtime_not_available")
        self.assertEqual(len({item["semantics"] for item in actions.values()}), 7)
        self.assertIn("retain positions", actions["stop"]["semantics"])

    def test_manual_pins_and_provenance_survive_without_mutation(self):
        before = self.spec.to_dict()
        status = self.snapshot()
        self.assertEqual(status["manual_pins"]["values"], {"range_pct": 8.0})
        self.assertEqual(status["manual_pins"]["config_hash"], self.spec.config_hash)
        self.assertEqual(
            status["manual_pins"]["provenance"]["range_pct"],
            before["provenance"]["range_pct"],
        )
        self.assertFalse(status["tuning"]["proposals"]["available"])
        self.assertTrue(status["tuning"]["proposals"]["read_only"])
        self.assertFalse(status["tuning"]["adoption"]["available"])
        self.assertFalse(status["tuning"]["automatic_edits"])
        status["manual_pins"]["values"]["range_pct"] = 90
        self.assertEqual(self.spec.to_dict(), before)
        self.assertEqual(self.snapshot()["manual_pins"]["values"]["range_pct"], 8.0)

    def test_pure_mapping_does_not_access_stores_or_owners(self):
        with (
            patch("botmanager.store.ManagerStore", side_effect=AssertionError("store")),
            patch("builtins.open", side_effect=AssertionError("file")),
            patch("socket.socket", side_effect=AssertionError("network")),
            patch("subprocess.Popen", side_effect=AssertionError("process")),
        ):
            status = self.snapshot()
            self.assertEqual(status, self.snapshot())
        self.assertEqual(json.loads(json.dumps(status, allow_nan=False)), status)
        self.assertFalse(self.home.exists())

    def test_evidence_modes_and_configuration_identities_do_not_alias(self):
        from botmanager.status import draft_snapshot

        status = self.snapshot()
        status["evidence"]["backtest"]["result_ref"]["value"] = "fixture-only"
        self.assertIsNone(status["evidence"]["paper"]["result_ref"]["value"])
        self.assertIsNone(status["evidence"]["live"]["result_ref"]["value"])
        other = BotSpec.create(
            "hourly-grid",
            "grid",
            resolve_config("grid", {"bar_seconds": 3600}, {"range_pct": 8.0}, None),
        )
        identity = draft_snapshot(other)["evidence_identity"]
        self.assertEqual(identity["bar_seconds"], 3600)
        self.assertNotEqual(identity["config_hash"], status["config_hash"])
        self.assertNotEqual(identity, status["evidence_identity"])

    def test_why_registered_and_supported_by_cli_without_envelope_change(self):
        flags = {flag for names, _ in COMMANDS["status"].arguments for flag in names}
        self.assertIn("--why", flags)
        store = ManagerStore(self.home)
        store.create_spec(self.spec)
        run = subprocess.run(
            [sys.executable, "-m", "botmanager", "status", self.spec.bot_id, "--why"],
            env={**os.environ, "SOLBOT_HOME": str(self.home)},
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        body = json.loads(run.stdout)
        self.assertEqual(
            set(body), {"schema_version", "request_id", "ok", "data", "error"}
        )
        self.assertEqual(body["data"]["explanation"]["reason"], "runtime_not_available")
        self.assertIn("draft", body["data"]["explanation"]["summary"])
        self.assertIsNone(body["error"])

    def test_absent_and_existing_status_reads_have_no_filesystem_mutation(self):
        result = dispatch("status", {"why": True}, self.context)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["data"]["bots"], [])
        self.assertFalse(self.home.exists())
        ManagerStore(self.home).create_spec(self.spec)

        def files():
            return {
                p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                for p in self.home.iterdir()
            }

        before = files()
        for params in ({"why": True}, {"identity": self.spec.bot_id, "why": True}):
            self.assertTrue(dispatch("status", params, self.context)["ok"])
        self.assertEqual(before, files())
        self.assertFalse(dispatch("status", {"why": "true"}, self.context)["ok"])

    def test_canonical_strategies_and_unsupported_capabilities_remain_honest(self):
        strategies = dispatch("help", {}, self.context)["data"]["strategies"]
        self.assertEqual(
            set(strategies) - {"council"},
            {
                "grid",
                "dca",
                "trend",
                "momentum",
                "arbitrage",
            },
        )
        self.assertEqual(strategies["council"], "external-only")
        self.assertEqual(
            strategies["arbitrage"], "conditional_quote_cycle_research_only"
        )
        ManagerStore(self.home).create_spec(self.spec)
        for operation in ("start", "stop"):
            result = dispatch(operation, {"identity": self.spec.bot_id}, self.context)
            self.assertEqual(result["error"]["code"], "runtime_not_available")

    def _assert_completed_status_and_cli(self, spec, ledger):
        before = ledger.get(spec.bot_id)
        reference = before["input"]["identity"]
        expected_engine = (
            reference["engine"]
            if reference["schema_version"] == 1
            else reference["engine_identity"]["package"]
        )
        # Exercise the complete public projection, not an isolated helper/key.
        result = dispatch(
            "status", {"identity": spec.bot_id, "why": True}, self.context
        )
        run = subprocess.run(
            [sys.executable, "-m", "botmanager", "status", spec.bot_id, "--why"],
            env={**os.environ, "SOLBOT_HOME": str(self.home)},
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(result["ok"], result)
        body = json.loads(run.stdout)
        self.assertTrue(body["ok"], body)
        self.assertIsNone(body["error"])
        for status in (result["data"], body["data"]):
            paper = status["evidence"]["paper"]
            self.assertEqual(paper["state"], "reference_only")
            self.assertEqual(paper["engine_version"]["value"], expected_engine)
            self.assertEqual(
                paper["engine_identity"]["value"], reference["engine_identity"]
            )
            self.assertFalse(paper["venue_compatibility_verified"])
            self.assertEqual(status["progress"]["cursor"], 2)
            self.assertEqual(status["runtime_id"], before["runtime_id"])
            self.assertEqual(
                status["reference_financials"]["cash_quote"],
                before["checkpoint"]["cash_quote"],
            )
            self.assertEqual(
                paper["result_ref"]["value"], before["checkpoint"]["run_hash"]
            )
            self.assertIsNone(status["evidence"]["live"]["engine_version"]["value"])
            self.assertIn("explanation", status)
        self.assertEqual(ledger.get(spec.bot_id), before)

    def _completed_oracle_status(self, mode):
        from uuid import uuid4

        from botmanager.ledger import RuntimeLedger
        from botmanager.oracle_data import capture, prepare_descriptor
        from botmanager.strategies import evaluate
        from botmanager.worker import prospective_tick

        from tests.test_oracle_data import START, append, archive

        path = Path(self.temp.name) / "oracle.sqlite3"
        producer = archive(path, 120)
        ledger = RuntimeLedger(self.home)
        pending = []
        for family in ("grid", "dca", "trend", "momentum"):
            spec = BotSpec.create(
                "oracle-" + mode + "-" + family,
                family,
                resolve_config(family, {}, {}, None),
            )
            ManagerStore(self.home).create_spec(spec)
            descriptor = prepare_descriptor(
                path,
                capital_quote=1000,
                strategy_id=family,
                now=START + 120,
                mode=mode,
                start_ts=START if mode == "historical" else None,
                end_ts=START + 120 if mode == "historical" else None,
            )
            data = capture(descriptor, strategy_id=family, now=START + 120)
            self.assertEqual(data["identity"]["schema_version"], 2)
            self.assertNotIn("engine", data["identity"])
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            generation = ledger.claim(spec.bot_id, "status-fixture")
            pending.append((spec, data, generation))
        if mode == "prospective":
            append(producer, 120, 241)
        for spec, data, generation in pending:
            with self.subTest(mode=mode, family=spec.strategy_id):
                if mode == "prospective":
                    prospective_tick(
                        ledger, ledger.get(spec.bot_id), generation, now=START + 241
                    )
                else:
                    ledger.commit_tick(
                        spec.bot_id, generation, 0, evaluate(spec, data, 2)
                    )
                self._assert_completed_status_and_cli(spec, ledger)

    def test_completed_schema2_historical_full_status_and_cli(self):
        self._completed_oracle_status("historical")

    def test_completed_schema2_prospective_full_status_and_cli(self):
        self._completed_oracle_status("prospective")

    def test_completed_schema1_status_retains_legacy_pinned_engine(self):
        from uuid import uuid4

        from botmanager.data import load_recording
        from botmanager.domain import fingerprint
        from botmanager.ledger import RuntimeLedger
        from botmanager.strategies import evaluate

        from tests.test_paper import recording

        ManagerStore(self.home).create_spec(self.spec)
        data = load_recording(recording(Path(self.temp.name)))
        data["identity"]["engine"] = "solmargintrader-backtester/0.1.0"
        data["identity"]["engine_identity"]["package"] = data["identity"]["engine"]
        data["snapshot_hash"] = fingerprint(
            {k: v for k, v in data.items() if k != "snapshot_hash"}
        )
        ledger = RuntimeLedger(self.home)
        ledger.register(self.spec, data)
        ledger.control(self.spec, "start", str(uuid4()))
        generation = ledger.claim(self.spec.bot_id, "legacy-status-fixture")
        ledger.commit_tick(
            self.spec.bot_id, generation, 0, evaluate(self.spec, data, 2)
        )
        self._assert_completed_status_and_cli(self.spec, ledger)

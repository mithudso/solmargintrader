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


class StatusTests(unittest.TestCase):
    def setUp(self):
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

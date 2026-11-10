from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from botmanager.data import load_recording

from botmanager import research
from tests.test_paper import grid, recording


class ResearchTests(unittest.TestCase):
    def test_partitions_purge_embargo_and_train_only_candidates(self):
        partitions = research.partition(800, horizon=4, warmup=5, blocks=10)
        self.assertLess(partitions["train"][-1][1], partitions["validation"][0][0])
        self.assertLess(partitions["validation"][-1][1], partitions["holdout"][0][0])
        self.assertEqual(partitions["holdout"][-1][1], 800)
        with self.assertRaisesRegex(ValueError, "insufficient"):
            research.partition(30, horizon=10, warmup=20, blocks=10)
        a = research.candidates(grid(), {"rungs": [8, 10]}, max_configurations=32)
        self.assertEqual(len(a), 3)
        with self.assertRaisesRegex(ValueError, "budget"):
            research.candidates(
                grid(), {"rungs": list(range(1, 40))}, max_configurations=32
            )

    def test_backtest_runs_canonical_costed_engine_reference_label(self):
        with tempfile.TemporaryDirectory() as d:
            spec = grid()
            data = load_recording(recording(Path(d), 40))
            report = research.backtest(spec, data)
            self.assertIn("net_return", report["metrics"])
            self.assertFalse(report["certified"])
            self.assertIn("reference", report["reason"])
            self.assertGreater(report["metrics"]["turnover"], 0)

    def test_final_blocks_alpha_cost_and_uncertainty(self):
        left = [
            {
                "block": i,
                "net_return": 0.01,
                "drawdown": 0.01,
                "turnover": 1.0,
                "trades": 4,
                "uncertainty": 0.0,
                "coverage": True,
                "certified": True,
                "cost_stress": True,
            }
            for i in range(12)
        ]
        right = [{**c, "net_return": 0.03} for c in left]
        confidence = {"method": "independent_sign", "seed": 0, "minimum_blocks": 10}
        self.assertTrue(
            research.final_comparison(left, right, ordinal=1, confidence=confidence)[
                "accepted"
            ]
        )
        self.assertFalse(
            research.final_comparison(
                left, right[:9], ordinal=1, confidence=confidence
            )["accepted"]
        )
        self.assertFalse(
            research.final_comparison(right, left, ordinal=1, confidence=confidence)[
                "accepted"
            ]
        )
        self.assertFalse(
            research.final_comparison(
                left,
                [{**c, "certified": False} for c in right],
                ordinal=1,
                confidence=confidence,
            )["accepted"]
        )
        self.assertFalse(
            research.final_comparison(left, right, ordinal=100, confidence=confidence)[
                "accepted"
            ]
        )

    def test_owner_pipeline_real_sandbox_winner_and_cancel_spent(self):
        from soltui.experiments import ExperimentError, ExperimentStore

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = grid()
            data = load_recording(recording(root, 800))
            options = {
                "ranges": {"rungs": [8]},
                "horizon_bars": 1,
                "warmup_bars": 1,
                "blocks": 10,
                "confidence": {
                    "method": "block_bootstrap",
                    "seed": 0,
                    "minimum_blocks": 10,
                },
            }
            seen = []

            def fixture(candidate, snapshot):
                seen.append(
                    (candidate.resolved_values["rungs"], snapshot["bars"][0]["ts"])
                )
                return {
                    "metrics": {
                        "net_return": 0.03
                        if candidate.resolved_values["rungs"] == 8
                        else 0.01,
                        "drawdown": 0.01,
                        "turnover": 1.0,
                        "trades": 4,
                        "uncertainty": 0.01,
                    },
                    "certified": True,
                }

            owner = ExperimentStore(root / "authority")
            from botmanager.blind import decide, run_judge

            judge = run_judge if sys.platform == "darwin" else decide
            report = research.execute(
                owner, spec, data, options, evaluator=fixture, judge=judge
            )
            self.assertEqual(report["outcome"]["outcome"], "proposal_pending_shadow")
            self.assertEqual(report["consumed_cells"], 120)
            self.assertFalse(report["outcome"]["proposal"]["automatic_promotion"])
            self.assertEqual(len(seen), 120)
            with self.assertRaises(ExperimentError):
                owner.manager_unseal(report["run_id"])
            # A different bot ID or random opaque IDs cannot reopen those dates.
            with self.assertRaises(ExperimentError):
                research.execute(
                    owner,
                    grid("new-bot"),
                    data,
                    options,
                    evaluator=fixture,
                    judge=judge,
                )

    def test_proposal_receipt_crash_reconciliation_and_pin_race(self):
        from uuid import uuid4

        from botmanager.domain import ManagerError
        from botmanager.store import ManagerStore

        with tempfile.TemporaryDirectory() as d:
            store = ManagerStore(Path(d))
            spec = store.create_spec(grid())
            proposal = {
                "version": 2,
                "authority": {
                    "namespace_id": "fixture",
                    "isolation_mode": "isolated",
                    "coverage": "registered_roots_only",
                },
                "production_eligible": False,
                "request_id": str(uuid4()),
                "run_id": "fixture",
                "bot_id": spec.bot_id,
                "baseline_revision": spec.config_revision,
                "baseline_hash": spec.config_hash,
                "pins": dict(spec.user_overrides),
                "changes": {"rungs": 8},
                "evidence_digest": "a" * 64,
                "state": "pending_shadow",
                "automatic_promotion": False,
                "reason": "requires_7_calendar_days_and_30_prospective_paper_trades",
            }

            class Owner:
                calls = 0

                def call(self, operation, params):
                    if operation == "proposal":
                        return {"proposal": proposal, "reconcilable": True}
                    self.calls += 1
                    if self.calls == 1:
                        raise OSError("crash after manager commit")
                    return {"receipt": params["receipt"]}

            owner = Owner()
            with self.assertRaises(OSError):
                research.reconcile_proposal(store, owner, "fixture")
            receipt = research.reconcile_proposal(store, owner, "fixture")
            self.assertFalse(receipt["configuration_changed"])
            self.assertEqual(store.get_spec(spec.bot_id), spec)
            store.edit(
                spec.bot_id, {"rungs": 9}, expected_revision=1, request_id=str(uuid4())
            )
            # Exact replay recognizes its own receipt after a later manual edit.
            self.assertEqual(
                research.reconcile_proposal(store, owner, "fixture"), receipt
            )
            with self.assertRaises(ManagerError):
                store.record_research_proposal({**proposal, "request_id": str(uuid4())})

    def test_cancel_after_unseal_remains_spent_and_retains_incumbent(self):
        from botmanager.blind import decide

        from soltui.experiments import ExperimentError, ExperimentStore

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = grid()
            data = load_recording(recording(root, 800))
            owner = ExperimentStore(root / "authority")
            options = {
                "ranges": {"rungs": [8]},
                "horizon_bars": 1,
                "warmup_bars": 1,
                "blocks": 10,
                "confidence": {
                    "method": "block_bootstrap",
                    "seed": 0,
                    "minimum_blocks": 10,
                },
            }
            calls = []

            def fixture(candidate, snapshot):
                calls.append(snapshot["bars"][0]["ts"])
                return {
                    "metrics": {
                        "net_return": 0.03
                        if candidate.resolved_values["rungs"] == 8
                        else 0.01,
                        "drawdown": 0.01,
                        "turnover": 1.0,
                        "trades": 4,
                        "uncertainty": 0.01,
                    },
                    "certified": True,
                }

            with self.assertRaisesRegex(ValueError, "cancelled"):
                research.execute(
                    owner,
                    spec,
                    data,
                    options,
                    judge=decide,
                    evaluator=fixture,
                    cancelled=lambda: len(calls) >= 80,
                )
            run = owner.list_runs()[0]
            status = owner.manager_status(run["id"])
            self.assertEqual(status["state"], "finished")
            self.assertIsNotNone(status["final_spent_at"])
            self.assertEqual(status["outcome"]["reason"], "cancelled")
            self.assertEqual(status["outcome"]["outcome"], "retained_incumbent")
            with self.assertRaises(ExperimentError):
                owner.manager_unseal(run["id"])
            cutoff = data["bars"][len(data["bars"]) // 2]["ts"]
            self.assertTrue(all(t < cutoff for t in calls[:40]))

    def test_costs_change_actual_canonical_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            spec = grid()
            descriptor = recording(root, 40)
            cheap = research.backtest(spec, load_recording(descriptor))
            expensive = research.backtest(
                spec,
                load_recording({**descriptor, "fee_bps": 100.0, "slippage_bps": 100.0}),
            )
            self.assertLess(
                expensive["metrics"]["net_return"], cheap["metrics"]["net_return"]
            )

    def test_invalid_independence_and_manual_pin_refuse_before_trials(self):
        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec

        pinned = BotSpec.create(
            "pinned", "grid", resolve_config("grid", {}, {"rungs": 8}, None)
        )
        with self.assertRaisesRegex(ValueError, "manual pins"):
            research.candidates(pinned, {"rungs": [10]})

    def test_public_setup_and_default_plan_do_not_initialize_authority(self):
        import json
        from unittest.mock import patch

        from botmanager.registry import CommandContext, dispatch
        from botmanager.store import ManagerStore

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = CommandContext(home=root / "manager")
            store = ManagerStore(context.home)
            spec = store.create_spec(grid())
            with patch(
                "botmanager.research_owner.OwnerClient.call",
                return_value={
                    "identity": {"loaded": "reviewed"},
                    "canonical_authority": None,
                },
            ):
                setup = dispatch(
                    "research-setup", {"config_root": str(root / "owner")}, context
                )
                self.assertTrue(setup["ok"], setup)
                descriptor = json.loads(
                    Path(setup["data"]["descriptor_path"]).read_text()
                )
                self.assertEqual(
                    descriptor["expected_identity"], {"loaded": "reviewed"}
                )
                self.assertFalse((root / "owner").exists())
                repeat = dispatch(
                    "research-setup", {"config_root": str(root / "owner")}, context
                )
                self.assertEqual(setup["data"], repeat["data"])
            plan = dispatch("research-plan", {"identity": spec.bot_id}, context)
            self.assertTrue(plan["ok"], plan)
            self.assertFalse(plan["data"]["strict_final_eligible"])
            options = json.loads(Path(plan["data"]["plan_path"]).read_text())
            self.assertLessEqual(len(research.candidates(spec, options["ranges"])), 3)
            self.assertEqual(options["confidence"]["minimum_blocks"], 10)

    def test_default_plan_preserves_pins_and_verifies_feature_horizon(self):
        from botmanager.config import resolve_config
        from botmanager.domain import BotSpec

        pinned = BotSpec.create(
            "pinned", "grid", resolve_config("grid", {}, {"rungs": 8}, None)
        )
        plan = research.default_plan(pinned)
        self.assertNotIn("rungs", plan["ranges"])
        momentum = BotSpec.create(
            "momentum", "momentum", resolve_config("momentum", {}, {}, None)
        )
        plan = research.default_plan(momentum)
        self.assertGreaterEqual(plan["horizon_bars"], 60)
        self.assertEqual(plan["warmup_bars"], plan["horizon_bars"])

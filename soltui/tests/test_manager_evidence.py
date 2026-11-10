from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from botmanager.blind import decide

from soltui.experiments import ExperimentError, ExperimentStore


def evidence():
    from .research_fixtures import packet

    p = packet()
    return {"packet": p, "verdict": decide(p)}


def specification(tag="one"):
    return {
        "protocol_version": 2,
        "source": "native",
        "bot": "momentum",
        "incumbent_id": "a" * 32,
        "scope": {
            "family": "momentum",
            "coin": "SOL",
            "base_mint": "So11111111111111111111111111111111111111112",
            "quote_mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "bar_seconds": 60,
            "execution_model": "reference",
        },
        "context": {
            "bot_id": tag,
            "config_hash": tag,
            "input_hash": tag,
            "engine_hash": tag,
        },
        "candidates": [
            {"id": "a" * 32, "config": {}},
            {"id": "b" * 32, "config": {"window": 4}},
        ],
        "budget": {"configurations": 32, "cells": 1000},
        "geometry": {
            name: [
                {"coin": "SOL", "start": start + i * 4, "end": start + i * 4 + 3}
                for i in range(10)
            ]
            for name, start in [("train", 1), ("validation", 60), ("holdout", 110)]
        },
        "policy": {
            "minimum_trades": 30,
            "maximum_drawdown": 0.2,
            "drawdown_weight": 0.5,
        },
        "confidence": {"method": "independent_sign", "seed": 0, "minimum_blocks": 10},
        "search": {"window": [4]},
        "owner_identity": "fixture",
    }


class ManagerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ExperimentStore(Path(self.temp.name) / "authority")

    def freeze(self, run):
        e = evidence()
        for split in ("train", "validation"):
            if split == "validation":
                self.store.manager_finalists(run, e)
            self.store.manager_expose(run, split)
            for c in e["packet"]["candidates"]:
                for cell in c["cells"]:
                    for stress in (0, 1):
                        ticket = self.store.manager_trial(
                            run, c["id"], split, cell["block"] * 2 + stress
                        )
                        metrics = {
                            k: cell[k]
                            for k in (
                                "net_return",
                                "drawdown",
                                "turnover",
                                "trades",
                                "uncertainty",
                            )
                        }
                        self.store.manager_trial_result(
                            run,
                            ticket,
                            {
                                "status": "completed",
                                "report": {"metrics": metrics, "certified": True},
                            },
                        )
        self.store.manager_freeze(run, "b" * 32, e)

    def test_concurrent_ordinals_ignore_new_bot_and_hash(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            runs = list(
                pool.map(
                    lambda i: self.store.manager_create(specification(str(i))), range(8)
                )
            )
        self.assertEqual(sorted(r["ordinal"] for r in runs), list(range(1, 9)))
        self.assertAlmostEqual(
            runs[0]["alpha"], 0.05 / (runs[0]["ordinal"] * (runs[0]["ordinal"] + 1))
        )

    def test_manager_dates_block_legacy_and_fresh_fingerprints(self):
        run = self.store.manager_create(specification())["run_id"]
        self.freeze(run)
        self.store.manager_unseal(run)
        self.store.manager_finish(
            run, {"outcome": "retained_incumbent", "reason": "cancelled"}
        )
        other = self.store.manager_create(specification("new-hash"))["run_id"]
        self.freeze(other)
        with self.assertRaisesRegex(ExperimentError, "spent"):
            self.store.manager_unseal(other)
        with self.assertRaisesRegex(ExperimentError, "spent"):
            self.store.manager_unseal(run)

    def test_failure_consumes_trial_and_failed_trial_cannot_retry(self):
        run = self.store.manager_create(specification())["run_id"]
        ticket = self.store.manager_trial(run, "a" * 32, "train", 0)
        self.store.manager_trial_result(run, ticket, {"status": "failed"})
        with self.assertRaises(ExperimentError):
            self.store.manager_trial(run, "a" * 32, "train", 0)
        self.assertEqual(self.store.manager_status(run)["consumed_cells"], 1)

    def test_unaware_active_client_refuses_future_final(self):
        client = Path(self.temp.name) / "old-f5"
        client.mkdir()
        self.store.manager_register_client(
            {"root": str(client), "kind": "f5", "active": True}
        )
        run = self.store.manager_create(specification())["run_id"]
        self.freeze(run)
        with self.assertRaisesRegex(ExperimentError, "client"):
            self.store.manager_unseal(run)

    def test_immutable_spec_budget_and_protocol(self):
        for key, value in [
            ("budget", {"configurations": 33, "cells": 1000}),
            ("unexpected", True),
        ]:
            spec = specification()
            spec[key] = value
            with self.assertRaises(ExperimentError):
                self.store.manager_create(spec)

    def test_concurrent_final_reservation_exactly_one_wins(self):
        import threading

        runs = [
            self.store.manager_create(specification(str(i)))["run_id"] for i in range(2)
        ]
        for run in runs:
            self.freeze(run)
        barrier = threading.Barrier(2)

        def reserve(run):
            barrier.wait()
            try:
                self.store.manager_unseal(run)
                return True
            except ExperimentError:
                return False

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, runs))
        self.assertEqual(sorted(results), [False, True])

    def test_forged_valid_packet_without_trial_evidence_refused(self):
        run = self.store.manager_create(specification())["run_id"]
        with self.assertRaisesRegex(ExperimentError, "completed comparable"):
            self.store.manager_finalists(run, evidence())

    def test_later_external_attempts_increment_existing_counter(self):
        first = self.store.manager_create(specification())
        self.store.manager_import("known-f5", "trial-1", "a" * 64, [], attempts=5)
        second = self.store.manager_create(specification("second"))
        self.assertEqual(second["ordinal"], first["ordinal"] + 6)
        self.store.manager_import("known-f5", "trial-2", "b" * 64, [], attempts=1)
        third = self.store.manager_create(specification("third"))
        self.assertEqual(third["ordinal"], second["ordinal"] + 2)

    def test_initialization_epoch_blocks_old_dates_without_resetting_attempts(self):
        self.store.manager_mark_history_gap(
            "first-epoch", "unknown earlier history", cutoff=100
        )
        first = self.store.manager_create(specification())
        self.freeze(first["run_id"])
        self.store.manager_unseal(first["run_id"])
        proof = self.store.manager_history_revision(exclude_run=first["run_id"])
        self.assertTrue(proof)
        self.store.manager_mark_history_gap("first-epoch", "attempted reset", cutoff=1)
        gap = self.store.manager_coverage()["blockers"][0]
        self.assertEqual(gap["affects_dates_before"], 100)
        old = specification("older")
        for rows in old["geometry"].values():
            for interval in rows:
                interval["start"] /= 10
                interval["end"] /= 10
        second = self.store.manager_create(old)
        self.assertEqual(second["ordinal"], first["ordinal"] + 1)
        self.freeze(second["run_id"])
        with self.assertRaisesRegex(ExperimentError, "unknown prior history"):
            self.store.manager_unseal(second["run_id"])

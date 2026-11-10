from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

from botmanager import blind


def packet():
    return {
        "version": 2,
        "policy": {
            "minimum_trades": 30,
            "maximum_drawdown": 0.2,
            "drawdown_weight": 0.5,
        },
        "candidates": [
            {
                "id": c * 32,
                "cells": [
                    {
                        "block": i,
                        "net_return": ret,
                        "drawdown": 0.01,
                        "turnover": 1.0,
                        "trades": 3,
                        "uncertainty": 0.01,
                        "coverage": True,
                        "certified": True,
                        "cost_stress": True,
                    }
                    for i in range(10)
                ],
            }
            for c, ret in [("a", 0.02), ("b", 0.03)]
        ],
    }


class BlindTests(unittest.TestCase):
    def test_unknown_metadata_at_every_level_refused(self):
        for location in ["packet", "policy", "candidate", "cell"]:
            p = packet()
            target = {
                "packet": p,
                "policy": p["policy"],
                "candidate": p["candidates"][0],
                "cell": p["candidates"][0]["cells"][0],
            }[location]
            target["strategy"] = "/private/mapping.json"
            with self.assertRaises(ValueError):
                blind.decide(p)

    def test_relabel_row_order_and_exact_tie(self):
        p = packet()
        a = blind.decide(p)
        self.assertEqual(a["tied_ids"], ["b" * 32])
        p["candidates"].reverse()
        for c in p["candidates"]:
            c["cells"].reverse()
        self.assertEqual(a["tied_ids"], blind.decide(p)["tied_ids"])
        p["candidates"][0]["id"] = "c" * 32
        self.assertEqual(blind.decide(p)["tied_ids"], ["c" * 32])
        p["candidates"][0]["cells"] = copy.deepcopy(p["candidates"][1]["cells"])
        self.assertEqual(set(blind.decide(p)["tied_ids"]), {"a" * 32, "c" * 32})
        self.assertEqual(blind.resolve_tie(blind.decide(p), "a" * 32), "a" * 32)

    def test_fabricated_or_stale_verdict_refused(self):
        p = packet()
        v = blind.decide(p)
        for field, value in [
            ("tied_ids", ["f" * 32]),
            ("packet_digest", "0" * 64),
            ("policy_digest", "0" * 64),
        ]:
            bad = {**v, field: value}
            with self.assertRaises(ValueError):
                blind.verify(p, bad)

    def test_missing_cells_costs_trades_and_drawdown(self):
        p = packet()
        p["candidates"][1]["cells"].pop()
        with self.assertRaises(ValueError):
            blind.decide(p)
        for field, value in [
            ("trades", 0),
            ("drawdown", 0.21),
            ("certified", False),
            ("cost_stress", False),
        ]:
            p = packet()
            for c in p["candidates"]:
                for cell in c["cells"]:
                    cell[field] = value
            self.assertEqual(blind.decide(p)["tied_ids"], [])

    def test_actual_isolation_denies_private_repo_network_and_process(self):
        with tempfile.TemporaryDirectory() as d:
            secret = Path(d) / "mapping.json"
            secret.write_text("private parameters")
            proof = blind.probe_isolation([secret, Path(__file__).resolve()])
            if sys.platform == "darwin":
                self.assertTrue(proof["available"], proof)
            if proof["available"]:
                self.assertEqual(proof["reads_denied"], [True, True])
                self.assertEqual(proof["metadata_denied"], [True, True])
                self.assertTrue(proof["network_denied"])
                self.assertTrue(proof["process_denied"])
                self.assertEqual(blind.run_judge(packet())["tied_ids"], ["b" * 32])
            else:
                with self.assertRaisesRegex(ValueError, "isolation_unavailable"):
                    blind.run_judge(packet())

    def test_process_output_and_deadline_are_bounded(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "output limit"):
                blind.bounded_process(
                    [sys.executable, "-I", "-S", "-c", 'print("x"*10000)'],
                    b"",
                    cwd=d,
                    env={},
                    limit=100,
                )
            with self.assertRaisesRegex(ValueError, "deadline"):
                blind.bounded_process(
                    [sys.executable, "-I", "-S", "-c", "import time; time.sleep(5)"],
                    b"",
                    cwd=d,
                    env={},
                    timeout=0.05,
                )

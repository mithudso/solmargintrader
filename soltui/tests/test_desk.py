"""Immutable array-bound provenance and an explicit, paper-only handoff."""
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import numpy as np

from soltui import commands, config, desk
from soltui.roster import Roster, RosterEntry
from soltui.tests.bridge_support import World


class DeskTests(unittest.TestCase):
    def snapshot(self):
        self.settings = config.Settings(asset="SOL", interval="1h", use_leverage=True,
                                        leverage=3, allow_short=True, min_confidence=.85)
        self.roster = Roster([RosterEntry("ma_crossover", {"fast": 3, "slow": 9})])
        self.arrays = {"ts": np.array([100, 200]), "close": np.array([5., 6.])}
        return desk.research_context(self.settings, self.roster, self.arrays)

    def test_provenance_uses_loaded_arrays_and_detaches_roster(self):
        snap = self.snapshot()
        self.assertEqual(snap["id"], desk.context_id(snap))
        self.assertEqual(snap["cpcv"], {"cpcv_groups": 8, "cpcv_k": 2})
        self.assertNotIn("solana_address", snap)
        self.assertNotIn("data_dir", snap)
        self.roster.entries[0].params["fast"] = 4
        self.assertEqual(snap["entries"][0]["params"]["fast"], 3)
        self.arrays["close"][0] = 10
        changed = desk.research_context(self.settings, self.roster, self.arrays)
        self.assertNotEqual(snap["data_sha256"], changed["data_sha256"])

    def test_handoff_pins_strategy_and_all_execution_fields(self):
        snap = self.snapshot()
        plan = desk.handoff_plan(snap, self.roster.labels[0], [5], False)
        self.assertEqual(plan["execution"], snap["execution"])
        self.assertEqual(plan["trials"][0]["members"][0]["params"]["fast"], 3)
        self.assertEqual(plan["assets"], ["SOL"])
        self.assertFalse(plan["tune"])
        self.assertEqual(plan["source"]["backtest_context"], snap["id"])
        self.assertEqual(plan["horizons"], (5,))
        self.assertEqual(plan["source"]["snapshot"], snap)
        plan["source"]["snapshot"]["entries"][0]["params"]["fast"] = 99
        self.assertEqual(snap["entries"][0]["params"]["fast"], 3)

    def test_modified_or_old_snapshot_and_unknown_member_fail_closed(self):
        snap = self.snapshot()
        for key, value in [("asset", "BTC"), ("strategy_revision", "old")]:
            changed = {**snap, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                desk.handoff_plan(changed, self.roster.labels[0], [5], False)
        stale = {**snap, "strategy_revision": "old"}
        stale["id"] = desk.context_id(stale)
        with self.assertRaisesRegex(ValueError, "code changed"):
            desk.handoff_plan(stale, self.roster.labels[0], [5], False)
        with self.assertRaisesRegex(ValueError, "exact strategy"):
            desk.handoff_plan(snap, "missing", [5], False)

    def test_incomplete_or_invalid_execution_is_not_defaulted(self):
        snap = self.snapshot()
        for execution in [{"fee_bps": 6}, {**snap["execution"], "fee_bps": -1}]:
            changed = copy.deepcopy(snap)
            changed["execution"] = execution
            changed["id"] = desk.context_id(changed)
            with self.assertRaises(ValueError):
                desk.handoff_plan(changed, self.roster.labels[0], [5], False)

    def test_registry_handoff_prepares_only_and_refuses_overrides(self):
        snap = self.snapshot()
        with World(), patch("threading.Thread.start") as start:
            result = commands.dispatch("forwardtest.start", {"snapshot": snap,
                "source_label": self.roster.labels[0], "horizons": [5], "optimize": False})
            self.assertTrue(result["ok"], result)
            start.assert_not_called()
            state = commands.dispatch("forwardtest.state")["result"]
            self.assertTrue(state["prepared"])
            self.assertFalse(state["running"])
            self.assertEqual(state["execution"], snap["execution"])
            commands.dispatch("forwardtest.stop")
            for extra in [{"coins": ["BTC"]}, {"allow_short": False}, {"min_confidence": .1}]:
                denied = commands.dispatch("forwardtest.start", {"snapshot": snap,
                    "source_label": self.roster.labels[0], **extra})
                self.assertFalse(denied["ok"])
                self.assertEqual(denied["error"]["code"], "bad_params")
            start.assert_not_called()

    def test_unwrapped_member_cannot_claim_an_exact_handoff(self):
        snap = self.snapshot()
        with patch("soltui.forwardtest.member", return_value={"name": "other", "params": {}}):
            with self.assertRaisesRegex(ValueError, "wrapper cannot be handed off exactly"):
                desk.handoff_plan(snap, self.roster.labels[0], [5], False)

    def test_no_completed_sweep_is_honestly_empty(self):
        with World():
            result = commands.dispatch("backtest.results")
            self.assertTrue(result["ok"])
            self.assertEqual(result["result"]["rows"], [])
            self.assertIsNone(result["result"]["context"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.domain import ManagerError
from botmanager.health import HealthStore, entries_paused
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.strategies import evaluate

from tests.test_paper import grid, recording


class EntryControlTests(unittest.TestCase):
    def test_pause_fences_inflight_entry_and_replay_cannot_undo_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            spec, ledger = grid(), RuntimeLedger(home)
            ManagerStore(home).create_spec(spec)
            data = load_recording(recording(home))
            ledger.register(spec, data)
            ledger.control(spec, "start", str(uuid4()))
            generation = ledger.claim(spec.bot_id, "test")
            row = ledger.get(spec.bot_id)
            state = evaluate(spec, data, 2)
            request_id = str(uuid4())
            receipt = HealthStore(home).pause(row, "pause", request_id)
            self.assertTrue(entries_paused(home, spec.bot_id, row["runtime_id"]))
            with self.assertRaises(ManagerError) as caught:
                ledger.commit_tick(spec.bot_id, generation, 0, state)
            self.assertEqual(caught.exception.code, "stale_generation")
            self.assertIsNone(ledger.get(spec.bot_id)["checkpoint"])
            self.assertEqual(
                HealthStore(home).pause(ledger.get(spec.bot_id), "pause", request_id),
                receipt,
            )
            HealthStore(home).pause(ledger.get(spec.bot_id), "resume", str(uuid4()))
            self.assertFalse(entries_paused(home, spec.bot_id, row["runtime_id"]))
            self.assertEqual(
                HealthStore(home).pause(ledger.get(spec.bot_id), "pause", request_id),
                receipt,
            )
            self.assertFalse(entries_paused(home, spec.bot_id, row["runtime_id"]))

    def test_health_and_registry_reads_leave_absent_home_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "absent"
            self.assertFalse(entries_paused(home, str(uuid4()), str(uuid4())))
            result = dispatch("alerts", {}, CommandContext(home=home))
            self.assertTrue(result["ok"])
            self.assertEqual(result["data"]["alerts"], [])
            self.assertFalse(home.exists())

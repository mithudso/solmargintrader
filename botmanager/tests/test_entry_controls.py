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

    def test_pause_keeps_failed_runtime_blocked_and_does_not_claim_exit_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            spec, ledger = grid(), RuntimeLedger(home)
            ManagerStore(home).create_spec(spec)
            ledger.register(spec, load_recording(recording(home)))
            ledger.control(spec, "start", str(uuid4()))
            with ledger.connection(True) as db:
                db.execute(
                    "UPDATE runs SET observed='failed',reason='worker_exited' WHERE bot_id=?",
                    (spec.bot_id,),
                )
            before = ledger.get(spec.bot_id)
            receipt = HealthStore(home).pause(before, "pause", str(uuid4()))
            after = ledger.get(spec.bot_id)
            self.assertFalse(receipt["exits_continue"])
            self.assertEqual(receipt["exit_owner_state"], "failed")
            self.assertEqual(after["observed"], "failed")
            self.assertEqual(after["reason"], "worker_exited")
            self.assertEqual(after["failures"], before["failures"])
            self.assertIsNone(ledger.claim(spec.bot_id, "should-not-own"))


def held_exit_worker(home, bot_id, generation, parent_pid):
    """Use the real worker; hold only evaluations after the entry checkpoint."""
    import time
    from unittest.mock import patch

    from botmanager.strategies import evaluate as canonical_evaluate
    from botmanager.worker import run_worker

    def evaluate(*args, **kwargs):
        cursor = args[2]
        if cursor > 2:
            (Path(home) / ("evaluation-held-" + bot_id)).touch()
            while not (Path(home) / "allow-exits").exists():
                time.sleep(0.01)
        return canonical_evaluate(*args, **kwargs)

    with (
        patch("botmanager.worker.BARS_PER_TICK", 2),
        patch("botmanager.strategies.evaluate", side_effect=evaluate),
    ):
        run_worker(home, bot_id, generation, parent_pid)


class ActiveEntryControlTests(unittest.TestCase):
    def test_pause_handoff_under_saturation_restarts_owner_and_keeps_exits(self):
        import time

        from botmanager.domain import fingerprint
        from botmanager.supervisor import Supervisor

        with tempfile.TemporaryDirectory(prefix="solbot-pause-active-") as directory:
            home = Path(directory)
            data = load_recording(recording(home))
            for index, bar in enumerate(data["bars"]):
                price = 100 if index == 0 else 90 if index in (1, 4) else 120
                bar.update(open=price, high=price, low=price, close=price)
            data["snapshot_hash"] = fingerprint(
                {k: v for k, v in data.items() if k != "snapshot_hash"}
            )
            ledger, store = RuntimeLedger(home), ManagerStore(home)
            for index in range(10):
                spec = grid("pause-saturated-" + str(index))
                store.create_spec(spec)
                ledger.register(spec, data)
                ledger.control(spec, "start", str(uuid4()))
            supervisor = Supervisor(home, worker_target=held_exit_worker).open()
            try:

                def spin(predicate, timeout=8):
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        supervisor.step()
                        if predicate():
                            return
                        time.sleep(0.02)
                    self.fail("pause handoff timed out")

                spin(
                    lambda: (
                        len(supervisor.children) == 4
                        and all(
                            ledger.get(bot)["cursor"] == 2
                            for bot in supervisor.children
                        )
                    )
                )
                bot = next(iter(supervisor.children))
                spin(lambda: (home / ("evaluation-held-" + bot)).exists())
                before = ledger.get(bot)
                self.assertTrue(before["checkpoint"]["lots"])
                old_pid = supervisor.children[bot][0].pid
                receipt = HealthStore(home).pause(before, "pause", str(uuid4()))
                self.assertTrue(receipt["exits_continue"])
                self.assertEqual(ledger.get(bot)["observed"], "recovering")
                spin(
                    lambda: (
                        bot in supervisor.children
                        and supervisor.children[bot][0].pid != old_pid
                    )
                )
                retained = ledger.get(bot)
                self.assertEqual(retained["checkpoint"], before["checkpoint"])
                self.assertEqual(retained["failures"], before["failures"])
                self.assertEqual(len(supervisor.children), 4)
                (home / "allow-exits").touch()
                spin(lambda: ledger.get(bot)["cursor"] == 8)
                after = ledger.get(bot)
                old_buys = [
                    fill
                    for fill in before["checkpoint"]["fills"]
                    if fill["side"] == "buy"
                ]
                new_buys = [
                    fill
                    for fill in after["checkpoint"]["fills"]
                    if fill["side"] == "buy"
                ]
                self.assertEqual(new_buys, old_buys)
                self.assertTrue(
                    any(fill["side"] == "sell" for fill in after["checkpoint"]["fills"])
                )
                self.assertEqual(after["checkpoint"]["lots"], [])
                self.assertEqual(after["failures"], [])
                # Resume uses the same claimable handoff without resetting account.
                paused_pid = supervisor.children[bot][0].pid
                HealthStore(home).pause(after, "resume", str(uuid4()))
                spin(
                    lambda: (
                        bot in supervisor.children
                        and supervisor.children[bot][0].pid != paused_pid
                    )
                )
                self.assertEqual(ledger.get(bot)["checkpoint"], after["checkpoint"])
                self.assertEqual(ledger.get(bot)["failures"], [])
            finally:
                supervisor.close()

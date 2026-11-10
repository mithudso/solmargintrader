"""Real process capacity fixture; optimizer pressure is a labelled CPU fixture."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import signal
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.supervisor import Supervisor
from botmanager.worker import lock_held

from tests.test_paper import grid, recording


def optimizer_pressure(root, ready, stop):
    from soltui.research_admission import optimizer_lease

    with optimizer_lease(Path(root)):
        ready.set()
        digest = b"deterministic-pressure"
        while not stop.is_set():
            for _ in range(500):
                digest = hashlib.sha256(digest).digest()
            time.sleep(0.001)


class LoadTests(unittest.TestCase):
    def test_ten_paper_bots_four_workers_with_one_optimizer_fixture(self):
        with tempfile.TemporaryDirectory(prefix="solbot-load-") as tmp:
            home = Path(tmp)
            data = load_recording(recording(home))
            ledger = RuntimeLedger(home)
            store = ManagerStore(home)
            specs = [grid("load-" + str(i)) for i in range(10)]
            for spec in specs:
                store.create_spec(spec)
                ledger.register(spec, data)
                ledger.control(spec, "start", str(uuid4()))
            authority = home / "isolated-research-pressure"
            authority.mkdir()
            with closing(sqlite3.connect(authority / "experiments.sqlite3")) as db:
                db.execute("CREATE TABLE fixture (id INTEGER)")
            context = multiprocessing.get_context("spawn")
            ready, stop = context.Event(), context.Event()
            optimizer = context.Process(
                target=optimizer_pressure, args=(str(authority), ready, stop)
            )
            optimizer.start()
            supervisor = None
            metrics = {}
            try:
                self.assertTrue(ready.wait(5))
                supervisor = Supervisor(home).open()

                def spin(predicate, timeout=10):
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        supervisor.step()
                        if predicate():
                            return
                        time.sleep(0.02)
                    self.fail("load fixture condition timeout")

                spin(
                    lambda: (
                        len(supervisor.children) == 4
                        and all(
                            ledger.get(bot)["cursor"] == 8
                            for bot in supervisor.children
                        )
                    )
                )
                metrics["active"] = len(supervisor.children)
                metrics["queued"] = len(
                    [
                        bot
                        for bot in ledger.ids()
                        if bot not in supervisor.children
                        and ledger.get(bot)["desired"] == "running"
                    ]
                )
                self.assertEqual((metrics["active"], metrics["queued"]), (4, 6))
                timings = []
                for _ in range(20):
                    started = time.monotonic()
                    result = dispatch("status", {}, CommandContext(home=home))
                    self.assertTrue(result["ok"], result)
                    timings.append(time.monotonic() - started)
                metrics["status_p95_s"] = sorted(timings)[18]
                self.assertLess(metrics["status_p95_s"], 1)
                bot = next(iter(supervisor.children))
                spec = next(s for s in specs if s.bot_id == bot)
                before = ledger.get(bot)["checkpoint"]
                process = supervisor.children[bot][0]
                started = time.monotonic()
                process.kill()
                process.join(2)
                supervisor.step()
                metrics["crash_detection_s"] = time.monotonic() - started
                self.assertLess(metrics["crash_detection_s"], 15)
                for queued in specs:
                    if queued.bot_id != bot:
                        ledger.control(queued, "stop", str(uuid4()))
                supervisor.close()
                supervisor = Supervisor(home).open()
                spin(
                    lambda: (
                        bot in supervisor.children
                        and ledger.get(bot)["observed"] == "waiting"
                    )
                )
                self.assertEqual(ledger.get(bot)["checkpoint"], before)
                self.assertEqual(ledger.fills(bot), before["fills"])
                evaluation_events = [
                    e for e in ledger.events(bot) if e["kind"] == "tick.committed"
                ]
                self.assertLessEqual(len(evaluation_events), 1)
                started = time.monotonic()
                ledger.control(spec, "stop", str(uuid4()))
                metrics["stop_ack_s"] = time.monotonic() - started
                self.assertLess(metrics["stop_ack_s"], 2)
                spin(lambda: not lock_held(home / "locks" / (bot + ".lock")))
                metrics["owner_release_s"] = time.monotonic() - started
                self.assertLess(metrics["owner_release_s"], 10)
                self.assertEqual(ledger.get(bot)["checkpoint"], before)
                # The actual 15-second watchdog is exercised without changing clocks.
                # Restart a second stopped account for the independent watchdog probe.
                other = next(s for s in specs if s.bot_id != bot)
                ledger.control(other, "start", str(uuid4()))
                spin(
                    lambda: (
                        other.bot_id in supervisor.children
                        and ledger.get(other.bot_id)["heartbeat"] is not None
                    )
                )
                stalled_bot = other.bot_id
                stalled = supervisor.children[stalled_bot][0]
                os.kill(stalled.pid, signal.SIGSTOP)
                heartbeat = ledger.get(stalled_bot)["heartbeat"]
                started = time.monotonic()
                spin(lambda: stalled_bot not in supervisor.children, timeout=17)
                metrics["stale_detection_from_freeze_s"] = time.monotonic() - started
                metrics["stale_detection_from_last_heartbeat_s"] = (
                    time.time() - heartbeat
                )
                self.assertLess(metrics["stale_detection_from_freeze_s"], 16)
                metrics["optimizer_kind"] = (
                    "synthetic_cpu_pressure_with_canonical_optimizer_lease_not_research_quality_run"
                )
                print("LOAD_METRICS " + json.dumps(metrics, sort_keys=True), flush=True)
            finally:
                if supervisor:
                    supervisor.close()
                stop.set()
                optimizer.join(5)
                if optimizer.is_alive():
                    optimizer.kill()
                    optimizer.join(2)
                optimizer.close()

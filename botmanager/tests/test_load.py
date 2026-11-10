"""Real paper workers and a canonical optimizer over isolated numerical inputs."""

from __future__ import annotations

import gzip
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
from unittest.mock import patch
from uuid import uuid4

from botmanager.data import load_recording
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.supervisor import Supervisor
from botmanager.worker import lock_held

from tests.test_paper import grid, recording


def optimizer_recording(root, attempt, count=1024):
    """Generate explicit non-overlapping numerical-source fixture observations."""
    root.mkdir()
    path = root / "observations.jsonl.gz"
    start = 1700000040 + attempt * (count + 100) * 60
    with gzip.open(path, "wt") as out:
        for second in range(count * 60):
            price = [100, 92, 101, 108][(second // 60) % 4]
            timestamp = start + second
            out.write(
                json.dumps(
                    {
                        "t": timestamp,
                        "q": {
                            "SOL-USD": [
                                price - 0.1,
                                price + 0.1,
                                price,
                                10,
                                10,
                                timestamp,
                            ]
                        },
                    }
                )
                + "\n"
            )
    return {
        "schema_version": 1,
        "installation_id": "isolated-load-numerical-fixture",
        "source": "coinbase_exchange_recorder",
        "paths": [str(path)],
        "product": "SOL-USD",
        "quote_currency": "USD",
        "bar_seconds": 60,
        "start_ts": start,
        "end_ts": start + count * 60,
        "fee_bps": 6.0,
        "slippage_bps": 2.0,
        "carry_bps_per_hour": 0.0,
        "min_order_quote": 10.0,
        "capital_quote": 1000.0,
    }


def optimizer_pressure(root, ready, stop):
    from botmanager.research import backtest, execute

    from soltui.experiments import ExperimentStore
    from soltui.research_admission import optimizer_lease, register_authority

    root = Path(root).resolve()
    config = root / "owner-config"
    environment = {
        "SOLTUI_CONFIG_DIR": str(config),
        "SOLTUI_RESEARCH_REGISTRY": str(root / "namespace.json"),
    }
    reports = []
    owner = ExperimentStore(root)
    authority = {
        "id": str(uuid4()),
        "root": str(root),
        "known_clients": [{"root": str(root), "kind": "native", "active": False}],
        "inventory_complete": True,
    }

    def save():
        temporary = root / "load-outcome.tmp"
        temporary.write_text(
            json.dumps(
                {
                    "fixture": "isolated_numerical_source_not_production_certification",
                    "runs": reports,
                }
            )
        )
        temporary.replace(root / "load-outcome.json")

    with patch.dict(os.environ, environment):
        registration = register_authority(
            authority, config, consent=True, initialize_first=False
        )
        from botmanager.domain import fingerprint

        context = {
            key: registration[key]
            for key in (
                "namespace_id",
                "isolation_mode",
                "coverage",
                "initialization_epoch",
            )
        }
        context["roster_revision"] = fingerprint(registration)
        with optimizer_lease(root):
            attempt = 0
            while not stop.is_set():
                descriptor = optimizer_recording(
                    root / ("source-" + str(attempt)), attempt
                )
                data = load_recording(descriptor)

                def evaluator(spec, snapshot):
                    # Reservation is already durable when the first real cell starts.
                    ready.set()
                    return backtest(spec, snapshot)

                options = {
                    "ranges": {"rungs": list(range(5, 36))},
                    "horizon_bars": 1,
                    "warmup_bars": 1,
                    "blocks": 10,
                    "confidence": {
                        "method": "block_bootstrap",
                        "seed": 0,
                        "minimum_blocks": 10,
                    },
                }
                try:
                    report = execute(
                        owner,
                        grid("load-optimizer"),
                        data,
                        options,
                        evaluator=evaluator,
                        cancelled=stop.is_set,
                        authority_context=context,
                    )
                    reports.append(
                        {
                            "run_id": report["run_id"],
                            "consumed_cells": report["consumed_cells"],
                            "outcome": report["outcome"],
                        }
                    )
                except ValueError:
                    if not stop.is_set():
                        raise
                    reports.append(
                        {
                            "outcome": {
                                "outcome": "retained_incumbent",
                                "reason": "cancelled_by_load_fixture_shutdown",
                            }
                        }
                    )
                save()
                attempt += 1


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
            context = multiprocessing.get_context("spawn")
            ready, stop = context.Event(), context.Event()
            optimizer = context.Process(
                target=optimizer_pressure, args=(str(authority), ready, stop)
            )
            optimizer.start()
            supervisor = None
            metrics = {}
            try:
                self.assertTrue(ready.wait(10))
                self.assertTrue(optimizer.is_alive())
                self.assertTrue(lock_held(authority / "research-optimizer.lock"))
                with closing(
                    sqlite3.connect(
                        (authority / "experiments.sqlite3").as_uri() + "?mode=ro",
                        uri=True,
                    )
                ) as db:
                    self.assertGreater(
                        db.execute("SELECT count(*) FROM manager_trials").fetchone()[0],
                        0,
                    )
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
                # Recovery keeps its slot while all other intents remain queued.
                spin(
                    lambda: (
                        bot in supervisor.children
                        and ledger.get(bot)["observed"] == "waiting"
                    )
                )
                self.assertEqual(ledger.get(bot)["checkpoint"], before)
                self.assertEqual(len(supervisor.children), 4)
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
                self.assertLess(metrics["stale_detection_from_freeze_s"], 15)
                self.assertLess(metrics["stale_detection_from_last_heartbeat_s"], 15)
                self.assertTrue(optimizer.is_alive())
                self.assertTrue(lock_held(authority / "research-optimizer.lock"))
                with closing(
                    sqlite3.connect(
                        (authority / "experiments.sqlite3").as_uri() + "?mode=ro",
                        uri=True,
                    )
                ) as db:
                    metrics["optimizer_attempts"] = db.execute(
                        "SELECT count(*) FROM manager_attempts"
                    ).fetchone()[0]
                    metrics["optimizer_reserved_cells"] = db.execute(
                        "SELECT count(*) FROM manager_trials"
                    ).fetchone()[0]
                    metrics["optimizer_completed_cells"] = db.execute(
                        "SELECT count(*) FROM manager_trials WHERE result IS NOT NULL"
                    ).fetchone()[0]
                    metrics["optimizer_stages"] = [
                        row[0]
                        for row in db.execute(
                            "SELECT DISTINCT split FROM manager_trials"
                        )
                    ]
                    metrics["optimizer_outcomes"] = [
                        json.loads(row[0])
                        for row in db.execute(
                            "SELECT outcome FROM manager_attempts WHERE outcome IS NOT NULL"
                        )
                    ]
                self.assertGreater(metrics["optimizer_completed_cells"], 0)
                self.assertIn("train", metrics["optimizer_stages"])
                metrics["optimizer_kind"] = (
                    "canonical_m4_training_and_isolated_resolver_numerical_fixture_uncertified_source"
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
                exitcode = optimizer.exitcode
                optimizer.close()
                self.assertEqual(exitcode, 0)
                with closing(
                    sqlite3.connect(
                        (authority / "experiments.sqlite3").as_uri() + "?mode=ro",
                        uri=True,
                    )
                ) as db:
                    final_outcomes = [
                        json.loads(row[0])
                        for row in db.execute(
                            "SELECT outcome FROM manager_attempts ORDER BY ordinal"
                        )
                    ]
                    self.assertTrue(
                        all(
                            outcome["outcome"] == "retained_incumbent"
                            for outcome in final_outcomes
                        )
                    )
                    reused_dates = db.execute(
                        "SELECT count(*) FROM exposures a JOIN exposures b ON a.run_id<b.run_id AND a.coin=b.coin AND a.start<b.end AND a.end>b.start"
                    ).fetchone()[0]
                    self.assertGreater(
                        db.execute("SELECT count(*) FROM exposures").fetchone()[0], 0
                    )
                    self.assertEqual(reused_dates, 0)
                print(
                    "OPTIMIZER_OUTCOME "
                    + json.dumps(
                        {
                            "source_certified": False,
                            "outcomes": final_outcomes,
                            "overlapping_reused_dates": reused_dates,
                            "clean_exit": exitcode == 0,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )

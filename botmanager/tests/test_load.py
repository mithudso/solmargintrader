"""Real paper workers and a canonical optimizer over isolated numerical inputs."""

from __future__ import annotations

import gzip
import json
import multiprocessing
import os
import signal
import sqlite3
import sys
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

from tests import isolated_default_owner
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


def optimizer_judge(platform):
    from botmanager.blind import decide, run_judge

    if platform == "darwin":
        return run_judge, "macos_deny_default_sandbox"
    # These are explicit numerical fixtures, not an alternative production
    # resolver. Production run_judge must still refuse unsupported platforms.
    return decide, "pure_numerical_fixture_no_os_isolation"


def optimizer_pressure(root, ready, stop, fixture_platform=None):
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
    judge, judge_mode = optimizer_judge(fixture_platform or sys.platform)
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
                    "judge_mode": judge_mode,
                    "os_isolation_claimed": judge_mode == "macos_deny_default_sandbox",
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
                        judge=judge,
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
    def setUp(self):
        self.enterContext(isolated_default_owner())

    def test_ten_paper_bots_four_workers_with_one_optimizer_fixture(self):
        self.run_load_fixture()

    def test_forced_linux_numerical_fixture_retains_full_load_and_watchdog(self):
        self.run_load_fixture(fixture_platform="linux")

    def run_load_fixture(self, *, fixture_platform=None):
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
                target=optimizer_pressure,
                args=(str(authority), ready, stop, fixture_platform),
            )
            optimizer.start()
            supervisor = None
            _, judge_mode = optimizer_judge(fixture_platform or sys.platform)
            metrics = {
                "optimizer_judge_mode": judge_mode,
                "optimizer_os_isolation_claimed": judge_mode == "macos_deny_default_sandbox",
            }
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
                        and ledger.get(other.bot_id)["pid"]
                        == supervisor.children[other.bot_id][0].pid
                        and ledger.get(other.bot_id)["observed"] == "waiting"
                        and lock_held(home / "locks" / (other.bot_id + ".lock"))
                    )
                )
                stalled_bot = other.bot_id
                stalled = supervisor.children[stalled_bot][0]
                heartbeat = ledger.get(stalled_bot)["heartbeat"]
                stalled_pid = stalled.pid
                os.kill(stalled_pid, signal.SIGSTOP)
                started = time.monotonic()
                # Observe this exact process, not the reusable bot slot. A later
                # replacement owner must not hide retirement of the frozen PID.
                deadline = started + 17
                while time.monotonic() < deadline:
                    supervisor.step()
                    current = supervisor.children.get(stalled_bot)
                    if current is None or current[0] is not stalled:
                        break
                    time.sleep(0.02)
                else:
                    row = ledger.get(stalled_bot)
                    self.fail(
                        "frozen owner watchdog timeout: "
                        + json.dumps(
                            {
                                "pid": stalled_pid,
                                "generation": row["generation"],
                                "observed": row["observed"],
                                "reason": row["reason"],
                                "heartbeat_age_s": time.time() - row["heartbeat"],
                                "events": ledger.events(stalled_bot)[-5:],
                            },
                            sort_keys=True,
                        )
                    )
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
                    "canonical_m4_training_numerical_fixture_uncertified_source"
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
                workload = json.loads((authority / "load-outcome.json").read_text())
                self.assertEqual(workload["judge_mode"], judge_mode)
                self.assertEqual(
                    workload["os_isolation_claimed"],
                    judge_mode == "macos_deny_default_sandbox",
                )
                print(
                    "OPTIMIZER_OUTCOME "
                    + json.dumps(
                        {
                            "source_certified": False,
                            "judge_mode": workload["judge_mode"],
                            "os_isolation_claimed": workload["os_isolation_claimed"],
                            "outcomes": final_outcomes,
                            "overlapping_reused_dates": reused_dates,
                            "clean_exit": exitcode == 0,
                        },
                        sort_keys=True,
                    ),
                    flush=True,
                )


def journal_lock_worker(home, bot_id, generation, parent_pid):
    """Expose an owned heartbeat, then retain a requested journal transaction."""
    from botmanager.worker import lifetime_lock

    home = Path(home)
    ledger = RuntimeLedger(home)
    with lifetime_lock(home / "locks" / (bot_id + ".lock")):
        ledger.heartbeat(bot_id, generation, os.getpid())
        (home / "owner-ready").touch()
        while not (home / "hold-journal").exists():
            time.sleep(0.01)
        with closing(sqlite3.connect(ledger.path)) as db:
            mode = (home / "hold-journal").read_text()
            if mode == "READ":
                db.execute("BEGIN")
                db.execute("SELECT cursor FROM runs WHERE bot_id=?", (bot_id,)).fetchone()
            else:
                db.execute("BEGIN " + mode)
                db.execute("UPDATE runs SET cursor=cursor+1000 WHERE bot_id=?", (bot_id,))
            (home / "journal-held").touch()
            while True:
                time.sleep(0.01)


class LockedJournalWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(isolated_default_owner())

    def frozen_owner(self, home, mode, *, stopped_peer=False):
        spec = grid("locked-journal")
        store, ledger = ManagerStore(home), RuntimeLedger(home)
        specs = [spec]
        if stopped_peer:
            # Reconciliation must hit the stopped peer before the live owner.
            specs = sorted([spec, grid("stopped-peer")], key=lambda item: item.bot_id)
            spec = specs[-1]
        data = load_recording(recording(home))
        for registered in specs:
            store.create_spec(registered)
            ledger.register(registered, data)
        ledger.control(spec, "start", str(uuid4()))
        supervisor = Supervisor(home, worker_target=journal_lock_worker).open()
        self.addCleanup(supervisor.close)
        deadline = time.monotonic() + 8
        while not (home / "owner-ready").exists():
            supervisor.step()
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        # Cache a real owned heartbeat before freezing the database writer.
        supervisor.step()
        before = ledger.get(spec.bot_id)
        process = supervisor.children[spec.bot_id][0]
        self.assertEqual(before["pid"], process.pid)
        (home / "hold-journal").write_text(mode)
        while not (home / "journal-held").exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        os.kill(process.pid, signal.SIGSTOP)
        return supervisor, ledger, spec, process, before

    def test_frozen_shared_reader_does_not_abort_stopped_peer_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            supervisor, ledger, spec, process, before = self.frozen_owner(
                home, "READ", stopped_peer=True
            )
            try:
                peer = next(bot for bot in ledger.ids() if bot != spec.bot_id)
                self.assertEqual(ledger.ids()[0], peer)
                peer_before = ledger.get(peer)
                self.assertEqual(peer_before["desired"], "stopped")
                # Prove the child holds only a shared reader: reserving a write
                # succeeds, but it cannot obtain the lock needed by commit.
                with closing(sqlite3.connect(ledger.path, timeout=0)) as probe:
                    probe.execute("BEGIN IMMEDIATE")
                    probe.rollback()
                    with self.assertRaises(sqlite3.OperationalError):
                        probe.execute("BEGIN EXCLUSIVE")
                started = time.monotonic()
                supervisor.step()
                self.assertLess(time.monotonic() - started, 2)
                self.assertEqual(ledger.get(peer), peer_before)
                deadline = started + 17
                while time.monotonic() < deadline:
                    supervisor.step()
                    current = supervisor.children.get(spec.bot_id)
                    if current is None or current[0] is not process:
                        break
                    time.sleep(0.02)
                self.assertLess(time.monotonic() - started, 15)
                self.assertLess(time.time() - before["heartbeat"], 15)
                self.assertNotIn(spec.bot_id, supervisor.children)
                self.assertFalse(lock_held(home / "locks" / (spec.bot_id + ".lock")))
                after = ledger.get(spec.bot_id)
                for field in ("cursor", "checkpoint", "input", "runtime_id"):
                    self.assertEqual(after[field], before[field])
                self.assertEqual(after["observed"], "recovering")
                self.assertEqual(after["reason"], "heartbeat_stale")
                self.assertEqual(after["generation"], before["generation"] + 1)
                self.assertEqual(ledger.get(peer)["observed"], "stopped")
            finally:
                supervisor.close()

    def test_poll_defers_normal_journal_waits_while_commit_is_blocked(self):
        for mode in ("READ", "EXCLUSIVE"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                supervisor, ledger, spec, process, before = self.frozen_owner(
                    Path(directory), mode, stopped_peer=True
                )
                normal_connection = supervisor.ledger.connection
                attempts = []

                def guarded_connection(
                    *args,
                    _attempts=attempts,
                    _supervisor=supervisor,
                    _connection=normal_connection,
                    **kwargs,
                ):
                    _attempts.append(True)
                    if _supervisor._journal_blocked():
                        # A normal connection can spend its full busy timeout
                        # before the next owner watchdog poll. The nonblocking
                        # availability probe must defer this work altogether.
                        raise AssertionError("poll entered a blocked journal wait")
                    return _connection(*args, **kwargs)

                try:
                    started = time.monotonic()
                    with patch.object(
                        supervisor.ledger, "connection", guarded_connection
                    ):
                        supervisor.step()
                    self.assertLess(time.monotonic() - started, 2)
                    self.assertEqual(attempts, [])
                    self.assertIs(supervisor.children[spec.bot_id][0], process)
                finally:
                    supervisor.close()
                after = ledger.get(spec.bot_id)
                for field in ("cursor", "checkpoint", "input", "runtime_id"):
                    self.assertEqual(after[field], before[field])

    def test_stopped_reconciliation_preserves_nontransient_errors(self):
        from botmanager.domain import ManagerError

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            spec = grid("stopped-error-propagation")
            ledger = RuntimeLedger(home)
            ManagerStore(home).create_spec(spec)
            ledger.register(spec, load_recording(recording(home)))
            supervisor = Supervisor(home).open()
            try:
                before = ledger.get(spec.bot_id)
                corrupt = ManagerError("store_unavailable", "fixture", 4)
                corrupt.__cause__ = sqlite3.DatabaseError("malformed database fixture")
                for error in (ManagerError("invalid_spec", "fixture", 4), corrupt):
                    with (
                        self.subTest(code=error.code),
                        patch.object(supervisor.ledger, "stopped", side_effect=error),
                        self.assertRaises(ManagerError) as caught,
                    ):
                        supervisor.step()
                    self.assertIs(caught.exception, error)
                    self.assertEqual(ledger.get(spec.bot_id), before)
            finally:
                supervisor.close()

    def test_frozen_reserved_and_exclusive_writers_meet_watchdog_without_lost_state(self):
        from botmanager.health import HealthStore

        for mode in ("IMMEDIATE", "EXCLUSIVE"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                supervisor, ledger, spec, process, before = self.frozen_owner(home, mode)
                try:
                    started = time.monotonic()
                    deadline = started + 17
                    while time.monotonic() < deadline:
                        supervisor.step()
                        current = supervisor.children.get(spec.bot_id)
                        if current is None or current[0] is not process:
                            break
                        time.sleep(0.02)
                    elapsed = time.monotonic() - started
                    heartbeat_age = time.time() - before["heartbeat"]
                    self.assertLess(elapsed, 15)
                    self.assertLess(heartbeat_age, 15)
                    print(
                        "LOCKED_WATCHDOG_METRICS "
                        + json.dumps(
                            {"mode": mode, "freeze_s": elapsed,
                             "heartbeat_age_s": heartbeat_age}, sort_keys=True
                        ), flush=True,
                    )
                    self.assertNotIn(spec.bot_id, supervisor.children)
                    self.assertFalse(lock_held(home / "locks" / (spec.bot_id + ".lock")))
                    after = ledger.get(spec.bot_id)
                    self.assertEqual(after["cursor"], before["cursor"])
                    self.assertEqual(after["checkpoint"], before["checkpoint"])
                    self.assertEqual(after["input"], before["input"])
                    self.assertEqual(after["runtime_id"], before["runtime_id"])
                    self.assertEqual(after["observed"], "recovering")
                    self.assertEqual(after["reason"], "heartbeat_stale")
                    self.assertEqual(after["generation"], before["generation"] + 1)
                    self.assertTrue(
                        any(
                            alert["code"] == "heartbeat_stale"
                            for alert in HealthStore(home).page()["alerts"]
                        )
                    )
                finally:
                    supervisor.close()

    def test_shutdown_reaps_frozen_writer_before_retrying_conditional_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor, ledger, spec, _, before = self.frozen_owner(
                Path(directory), "EXCLUSIVE"
            )
            started = time.monotonic()
            supervisor.close()
            self.assertLess(time.monotonic() - started, 2)
            self.assertEqual(supervisor.children, {})
            after = ledger.get(spec.bot_id)
            self.assertEqual(after["cursor"], before["cursor"])
            self.assertEqual(after["checkpoint"], before["checkpoint"])
            self.assertEqual(after["generation"], before["generation"] + 1)
            self.assertEqual(after["observed"], "recovering")

    def test_shutdown_reports_pending_failure_write_without_claiming_reconciliation(self):
        from botmanager.domain import ManagerError

        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            spec = grid("unavailable-failure-journal")
            ManagerStore(home).create_spec(spec)
            ledger = RuntimeLedger(home)
            ledger.register(spec, load_recording(recording(home)))
            ledger.control(spec, "start", str(uuid4()))
            supervisor = Supervisor(home).open()
            before = ledger.get(spec.bot_id)
            supervisor._pending_failures[spec.bot_id] = (
                before["generation"], "heartbeat_stale"
            )
            with (
                patch.object(
                    supervisor.ledger, "failed",
                    side_effect=ManagerError("store_unavailable", "fixture", 4),
                ),
                self.assertRaises(ManagerError) as caught,
            ):
                supervisor.close()
            self.assertEqual(caught.exception.code, "store_unavailable")
            self.assertIsNone(supervisor.server)
            self.assertFalse(lock_held(home / "supervisor.lock"))
            self.assertIn(spec.bot_id, supervisor._pending_failures)
            self.assertEqual(ledger.get(spec.bot_id), before)

    def test_shutdown_never_enters_sqlite_busy_timeout_before_reaping(self):
        with tempfile.TemporaryDirectory() as directory:
            supervisor, ledger, spec, _, before = self.frozen_owner(
                Path(directory), "EXCLUSIVE"
            )
            connection = supervisor.ledger.connection
            blocked_attempts = []

            def delayed_connection(*args, **kwargs):
                if spec.bot_id in supervisor.children:
                    blocked_attempts.append(True)
                    # Model an overloaded runner's SQLite busy wait. This delay
                    # must be unreachable until the exact owner is reaped.
                    time.sleep(2.1)
                return connection(*args, **kwargs)

            started = time.monotonic()
            with patch.object(supervisor.ledger, "connection", delayed_connection):
                supervisor.close()
            self.assertEqual(blocked_attempts, [])
            self.assertLess(time.monotonic() - started, 2)
            after = ledger.get(spec.bot_id)
            self.assertEqual(after["checkpoint"], before["checkpoint"])
            self.assertEqual(after["cursor"], before["cursor"])
            self.assertEqual(after["generation"], before["generation"] + 1)

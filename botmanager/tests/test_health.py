from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from botmanager.health import HealthStore, health_snapshot, rotate_diagnostics


def runtime():
    return {
        "bot_id": "bot",
        "runtime_id": "run",
        "generation": 1,
        "desired": "running",
        "observed": "running",
        "heartbeat": 99,
        "evaluated": 98,
        "tick_started": None,
        "input": {
            "identity": {"source": "fixture"},
            "descriptor": {"max_source_age_s": 10},
            "prospective": {"latest_observed": 99, "health": "available"},
        },
        "checkpoint": {"realized_net_pnl_quote": -2, "exposure_quote": 50},
    }


class HealthTests(unittest.TestCase):
    def test_alive_process_can_have_stale_inputs(self):
        row = runtime()
        row["input"]["prospective"]["latest_observed"] = 70
        result = health_snapshot(row, now=100)
        self.assertEqual(result["process"]["state"], "healthy")
        self.assertEqual(result["input"]["state"], "source_stale")
        self.assertIn("source_stale", result["blockers"])

    def test_stopped_bot_retains_exposure(self):
        row = runtime()
        row["desired"] = "stopped"
        result = health_snapshot(row, now=100)
        self.assertEqual(result["process"]["state"], "stopped")
        self.assertEqual(result["exposure_quote"], 50)

    def test_fresh_input_stalled_evaluation_and_valid_loss_separate(self):
        row = runtime()
        row["tick_started"] = 80
        result = health_snapshot(row, now=100)
        self.assertEqual(result["input"]["state"], "available")
        self.assertEqual(result["evaluation"]["state"], "stalled")
        self.assertEqual(result["results"]["state"], "loss")
        self.assertFalse(result["performance_warning"]["available"])
        row["checkpoint"]["realized_net_pnl_quote"] = None
        self.assertEqual(
            health_snapshot(row, now=100)["results"]["state"], "unavailable"
        )
        row["heartbeat"] = None
        self.assertEqual(health_snapshot(row, now=100)["process"]["state"], "stale")

    def test_alert_dedup_and_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = HealthStore(Path(tmp))
            row = runtime()
            row["heartbeat"] = 0
            store.observe(row, now=100)
            store.observe(row, now=101)
            alerts = store.page()["alerts"]
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0]["occurrences"], 2)
            self.assertEqual(alerts[0]["notified_at"], 100)
            cursor = store.page()["next_after"]
            self.assertEqual(alerts[0]["evidence"]["source"], row["input"]["identity"])
            row["heartbeat"] = 101
            store.observe(row, now=102)
            resolved = store.page()["alerts"][0]
            self.assertEqual(resolved["state"], "resolved")
            self.assertEqual(resolved["resolved_at"], 102)
            updates = store.page(after=cursor)
            self.assertEqual(updates["alerts"][0]["key"], resolved["key"])
            self.assertGreater(updates["next_after"], cursor)
            self.assertEqual(
                resolved["evidence"]["health"]["process"]["state"], "healthy"
            )

    def test_pure_health_read_and_absent_alerts_do_not_create(self):
        row = runtime()
        old = copy.deepcopy(row)
        health_snapshot(row, now=100)
        self.assertEqual(row, old)
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "missing"
            self.assertEqual(HealthStore(home).page()["alerts"], [])
            self.assertFalse(home.exists())

    def test_rotation_retains_only_bounded_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "financial-evidence.json"
            evidence.write_text("retained")
            for i in range(5):
                log = root / "diagnostics.log"
                log.write_text(str(i) * 20)
                rotate_diagnostics(log, max_bytes=10, keep=2)
            self.assertEqual(
                sorted(p.name for p in root.glob("diagnostics.log*")),
                ["diagnostics.log.1", "diagnostics.log.2"],
            )
            self.assertEqual(evidence.read_text(), "retained")

    def test_fresh_heartbeat_does_not_hide_failure_or_stalled_intent(self):
        row = runtime()
        row.update(observed="recovering", reason="worker_exited")
        result = health_snapshot(row, now=100)
        self.assertEqual(result["process"]["state"], "healthy")
        self.assertEqual(result["lifecycle"]["observed"], "recovering")
        self.assertIn("worker_exited", result["blockers"])
        row.update(observed="failed", reason="tick_stalled", tick_started=None)
        result = health_snapshot(row, now=100)
        self.assertEqual(result["evaluation"]["state"], "stalled")
        self.assertIn("runtime_failed", result["blockers"])
        self.assertIn("tick_stalled", result["blockers"])
        self.assertIn("evaluation_stalled", result["blockers"])
        self.assertEqual(result["results"]["state"], "loss")
        self.assertFalse(result["performance_warning"]["available"])

    def test_fast_crash_is_alerted_before_recovery_and_resolution_retains_origin(self):
        import time
        from uuid import uuid4

        from botmanager.data import load_recording
        from botmanager.ledger import RuntimeLedger
        from botmanager.store import ManagerStore
        from botmanager.supervisor import Supervisor

        from tests.test_paper import grid, recording

        with tempfile.TemporaryDirectory(
            prefix="solbot-fast-crash-alert-"
        ) as directory:
            home = Path(directory)
            spec = grid("fast-crash")
            store, ledger = ManagerStore(home), RuntimeLedger(home)
            store.create_spec(spec)
            ledger.register(spec, load_recording(recording(home)))
            ledger.control(spec, "start", str(uuid4()))
            supervisor = Supervisor(home).open()
            try:

                def spin(predicate, timeout=8):
                    deadline = time.monotonic() + timeout
                    while time.monotonic() < deadline:
                        supervisor.step()
                        if predicate():
                            return
                        time.sleep(0.02)
                    self.fail("failure alert recovery timed out")

                spin(lambda: ledger.get(spec.bot_id)["observed"] == "waiting")
                before = ledger.get(spec.bot_id)
                process = supervisor.children[spec.bot_id][0]
                # Skip the normal periodic sample throughout the crash branch.
                supervisor._health_at = time.monotonic() + 60
                process.kill()
                process.join(2)
                supervisor.step()
                alerts = HealthStore(home).page(bot_id=spec.bot_id)["alerts"]
                crash = next(
                    alert for alert in alerts if alert["code"] == "worker_exited"
                )
                self.assertEqual(crash["state"], "active")
                self.assertEqual(crash["runtime_id"], before["runtime_id"])
                self.assertEqual(crash["evidence"]["origin"]["reason"], "worker_exited")
                self.assertEqual(
                    crash["evidence"]["source"], before["input"]["identity"]
                )
                spin(
                    lambda: (
                        spec.bot_id in supervisor.children
                        and ledger.get(spec.bot_id)["observed"] == "waiting"
                    )
                )
                supervisor._health_at = 0
                supervisor.step()
                resolved = next(
                    alert
                    for alert in HealthStore(home).page(bot_id=spec.bot_id)["alerts"]
                    if alert["code"] == "worker_exited"
                )
                self.assertEqual(resolved["state"], "resolved")
                self.assertEqual(
                    resolved["evidence"]["origin"], crash["evidence"]["origin"]
                )
                self.assertEqual(
                    ledger.get(spec.bot_id)["checkpoint"], before["checkpoint"]
                )
                # The watchdog's explicit reason survives tick_started clearing.
                row = ledger.get(spec.bot_id)
                ledger.begin_tick(spec.bot_id, row["generation"])
                with ledger.connection(True) as db:
                    db.execute(
                        "UPDATE runs SET tick_started=? WHERE bot_id=?",
                        (time.time() - 15, spec.bot_id),
                    )
                supervisor._health_at = time.monotonic() + 60
                supervisor.step()
                stalls = {
                    alert["code"]: alert
                    for alert in HealthStore(home).page(bot_id=spec.bot_id)["alerts"]
                }
                self.assertEqual(stalls["tick_stalled"]["state"], "active")
                self.assertEqual(stalls["evaluation_stalled"]["state"], "active")
                self.assertEqual(
                    stalls["tick_stalled"]["evidence"]["origin"]["reason"],
                    "tick_stalled",
                )
            finally:
                supervisor.close()

    def test_claim_without_owned_heartbeat_cannot_resolve_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            store = HealthStore(Path(directory))
            row = runtime()
            row.update(observed="recovering", reason="worker_exited", pid=None)
            store.observe(row, now=100)
            row.update(
                observed="running", reason="worker_starting", heartbeat=101, pid=None
            )
            store.observe(row, now=101)
            crash = next(
                alert
                for alert in store.page()["alerts"]
                if alert["code"] == "worker_exited"
            )
            self.assertEqual(crash["state"], "active")
            row.update(
                observed="waiting",
                reason="reference_input_exhausted",
                heartbeat=102,
                pid=12345,
            )
            store.observe(row, now=102)
            crash = next(
                alert
                for alert in store.page()["alerts"]
                if alert["code"] == "worker_exited"
            )
            self.assertEqual(crash["state"], "resolved")

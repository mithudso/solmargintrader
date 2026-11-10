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

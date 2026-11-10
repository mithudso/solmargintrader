from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4

from ecosystem import control, runner


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "control"
        self.manager = Path(self.temp.name) / "manager"
        self.controllers = []
        self.addCleanup(self.close)

    def plane(self):
        result = control.ControlPlane(self.home, self.manager)
        self.controllers.append(result)
        return result

    def close(self):
        for controller in self.controllers:
            controller.close()

    def wait(self, plane, identity, states=("succeeded", "failed", "interrupted")):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            row = plane.actions(identity)["action"]
            if row and row["state"] in states:
                return row
            time.sleep(0.02)
        self.fail(f"action did not reach {states}")

    def test_legacy_registered_source_has_no_producer_mutations(self):
        self.home = Path(self.temp.name) / "ecosystem-paper-v2"
        legacy = self.home.parent / "ecosystem-paper-v1"
        legacy.mkdir()
        (legacy / "state.json").write_text("{}")
        plane = self.plane()
        self.assertTrue(plane.register_legacy())
        self.assertEqual(plane.experiment_home("legacy-v1"), legacy)
        for action in (
            "pipeline.start",
            "pipeline.stop",
            "oracle.restart",
            "backtest.stop",
            "recorder.stop",
        ):
            with self.assertRaisesRegex(ValueError, "legacy_source_read_only"):
                plane._execute(action, {"run_id": "legacy-v1"}, str(uuid4()))
        self.assertEqual((legacy / "state.json").read_text(), "{}")
        self.assertFalse((legacy / "runtime-settings.json").exists())

    def test_manager_preparation_owns_paths_and_registration(self):
        plane = self.plane()
        identity = str(uuid4())
        request = str(uuid4())
        with patch.object(
            plane,
            "_manager",
            return_value={
                "descriptor_path": str(
                    self.home / "manager-inputs" / (UUID(request).hex + ".json")
                )
            },
        ) as owner:
            plane._execute(
                "manager.prepare-input",
                {"identity": identity, "mode": "prospective"},
                request,
            )
            args = owner.call_args.args
            self.assertEqual(args[0], "prepare-input")
            self.assertEqual(args[1]["archive"], "shared-sol-usd")
            self.assertTrue(args[1]["reference"])
            self.assertTrue(Path(args[1]["output"]).is_relative_to(self.home))
        with self.assertRaisesRegex(ValueError, "invalid_action_parameters"):
            plane._execute(
                "manager.prepare-input",
                {"identity": identity, "output": "/tmp/arbitrary"},
                request,
            )
        with patch.object(plane, "_manager") as owner:
            with self.assertRaisesRegex(ValueError, "arbitrary_descriptor_forbidden"):
                plane._execute(
                    "manager.apply",
                    {"identity": identity, "descriptor": "/tmp/arbitrary.json"},
                    request,
                )
            owner.assert_not_called()
        with self.assertRaisesRegex(ValueError, "prepared_input_unavailable"):
            plane._execute("manager.register-input", {"identity": identity}, request)
        self.assertEqual(
            plane._execute("manager.cycle-check", {"identity": identity}, request)[
                "status"
            ],
            "unavailable",
        )

    def test_durable_uuid_idempotency_and_conflict(self):
        plane = self.plane()
        identity = str(uuid4())
        with patch.object(
            plane, "_execute", return_value={"owner_observed": True}
        ) as execute:
            first, created = plane.submit("oracle.stop", identity, {})
            again, duplicate = plane.submit("oracle.stop", identity, {})
            self.assertTrue(created)
            self.assertFalse(duplicate)
            self.assertEqual(first["id"], again["id"])
            with self.assertRaisesRegex(ValueError, "request_id_conflict"):
                plane.submit("oracle.start", identity, {})
            final = self.wait(plane, identity)
            self.assertEqual(final["state"], "succeeded")
            self.assertTrue(final["result"]["owner_observed"])
            self.assertEqual(execute.call_count, 1)
        replacement = self.plane()
        self.assertEqual(replacement.actions(identity)["action"], final)

    def test_restart_marks_lost_running_action_interrupted_without_replay(self):
        identity = str(uuid4())
        with control.database(self.home) as db:
            db.execute(
                "INSERT INTO action VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    identity,
                    "oracle.stop",
                    "fixture-digest",
                    "{}",
                    "running",
                    time.time(),
                    None,
                    None,
                    None,
                ),
            )
        with patch.object(control.ControlPlane, "_execute") as execute:
            plane = self.plane()
            final = self.wait(plane, identity)
            self.assertEqual(final["state"], "interrupted")
            self.assertEqual(final["error"], "reconcile_owner_before_retry")
            execute.assert_not_called()

    def test_two_controllers_hold_one_action_owner_lock(self):
        first, second = self.plane(), self.plane()
        entered, release = threading.Event(), threading.Event()
        identities = [str(uuid4()), str(uuid4())]
        active, peak, calls = 0, 0, []
        mutex = threading.Lock()

        def handle(action, params, identity):
            nonlocal active, peak
            with mutex:
                active += 1
                peak = max(peak, active)
                calls.append(identity)
            entered.set()
            release.wait(2)
            with mutex:
                active -= 1
            return {"status": "owner_complete"}

        with patch.object(control.ControlPlane, "_execute", side_effect=handle):
            first.submit("oracle.stop", identities[0], {})
            self.assertTrue(entered.wait(2))
            second.submit("oracle.start", identities[1], {})
            time.sleep(0.3)
            self.assertEqual(calls, [identities[0]])
            self.assertEqual(first.actions(identities[0])["action"]["state"], "running")
            release.set()
            for identity in identities:
                self.assertEqual(self.wait(first, identity)["state"], "succeeded")
        self.assertEqual(peak, 1)
        self.assertCountEqual(calls, identities)

    def test_live_orders_and_credential_parameters_are_refused_before_queue(self):
        plane = self.plane()
        for action, params in (
            ("orders.submit", {}),
            ("manager.create", {"mode": "live"}),
            ("manager.create", {"armed": True}),
            ("manager.create", {"config_context": {"api_key": "never-store-me"}}),
            ("manager.create", {"authorization": "never-store-me"}),
            ("manager.create", {"access_token": "never-store-me"}),
        ):
            with (
                self.subTest(action=action, params=list(params)),
                self.assertRaises(ValueError),
            ):
                plane.submit(action, str(uuid4()), params)
        self.assertEqual(plane.actions()["actions"], [])

    def test_owner_errors_do_not_echo_arbitrary_or_secret_text(self):
        plane = self.plane()
        identity = str(uuid4())
        with patch.object(
            plane, "_execute", side_effect=RuntimeError("api_key=do-not-echo")
        ):
            plane.submit("oracle.stop", identity, {})
            final = self.wait(plane, identity)
        self.assertEqual(final["state"], "failed")
        self.assertEqual(final["error"], "owner_operation_failed")
        self.assertNotIn("do-not-echo", json.dumps(final))

    def test_launch_freezes_actual_config_without_starting_real_worker(self):
        plane = self.plane()
        identity = str(uuid4())
        params = {
            "name": "Selected paper baseline",
            "coins": ["SOL", "BTC"],
            "strategies": ["rsi"],
            "intervals": ["1d"],
            "horizons": ["medium"],
            "start": "2025-01-01",
            "end": "2025-02-01",
            "capital": 2500,
            "swap_provider": "reference",
            "record_pnl": True,
        }
        with patch.object(
            runner, "start", return_value={"status": "start_requested"}
        ) as start:
            plane.submit("research.launch", identity, params)
            final = self.wait(plane, identity)
        self.assertEqual(final["state"], "succeeded", final)
        start.assert_called_once()
        result = final["result"]
        path = plane.experiment_home(result["experiment_id"])
        state = runner.load(path)
        self.assertEqual(state["config"]["coins"], ["BTC", "SOL"])
        self.assertEqual(state["config"]["strategies"], ["rsi"])
        self.assertEqual(state["config"]["research_capital"], 2500)
        self.assertEqual(state["config"]["swap_provider"], "reference")
        self.assertEqual(state["config"]["mode"], "paper")
        self.assertFalse(state["live_enabled"])
        self.assertEqual(path.parent, self.home / "research")
        self.assertIsNone(state["batch_id"])

    def test_invalid_launch_does_not_leave_registered_experiment(self):
        plane = self.plane()
        with patch.object(runner, "start") as start:
            plane.submit(
                "research.launch",
                str(uuid4()),
                {"swap_provider": "reference", "record_pnl": "yes"},
            )
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and any(
                row["state"] == "queued" for row in plane.actions()["actions"]
            ):
                time.sleep(0.02)
            rows = plane.actions()["actions"]
            self.wait(plane, rows[0]["id"])
        start.assert_not_called()
        self.assertEqual(len(plane.experiments()), 1)

    def test_jupiter_paper_launch_freezes_explicit_cost_scenario(self):
        plane = self.plane()
        identity = str(uuid4())
        scenario = {
            "source": "configured_scenario",
            "fee_bps": 7,
            "referral_fee_bps": 10,
            "slippage_bps": 3,
            "borrow_long_bps_hour": 0.1,
            "borrow_short_bps_hour": 0.02,
        }
        with patch.object(runner, "start", return_value={"status": "start_requested"}):
            plane.submit(
                "research.launch",
                identity,
                {
                    "swap_provider": "jupiter",
                    "cost_model": scenario,
                    "capital": 4500,
                    "coins": ["SOL"],
                    "strategies": ["rsi"],
                    "start": "2025-01-01",
                    "end": "2025-02-01",
                },
            )
            result = self.wait(plane, identity)
        self.assertEqual(result["state"], "succeeded", result)
        config = runner.load(plane.experiment_home(result["result"]["experiment_id"]))[
            "config"
        ]
        self.assertEqual(config["swap_provider"], "jupiter")
        self.assertEqual(config["research_capital"], 4500)
        self.assertEqual(config["cost_model"]["source"], "configured_scenario")
        self.assertEqual(config["cost_model"]["fee_bps"], 7)
        self.assertEqual(config["cost_model"]["total_fee_bps"], 17)
        self.assertEqual(config["cost_model"]["slippage_bps"], 3)
        self.assertEqual(config["cost_model"]["borrow_long_bps_hour"], 0.1)

    def test_experiment_lookup_rejects_unknown_paths_and_symlink(self):
        plane = self.plane()
        for identity in ("../outside", "/tmp/outside", str(uuid4())):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                plane.experiment_home(identity)
        self.home.mkdir(exist_ok=True)
        research = self.home / "research"
        research.mkdir()
        linked = research / "linked"
        linked.symlink_to(Path(self.temp.name))
        with control.database(self.home) as db:
            db.execute(
                "INSERT INTO experiment VALUES(?,?,?,?)",
                ("unsafe", "unsafe", str(linked), time.time()),
            )
        with self.assertRaisesRegex(ValueError, "invalid_experiment_home"):
            plane.experiment_home("unsafe")

    def test_interrupted_schema_creation_does_not_leave_partial_control_store(self):
        connect = sqlite3.connect

        def interrupted(*args, **kwargs):
            db = connect(*args, **kwargs)
            db.set_authorizer(
                lambda operation, name, *_: (
                    sqlite3.SQLITE_DENY
                    if operation == sqlite3.SQLITE_CREATE_TABLE and name == "experiment"
                    else sqlite3.SQLITE_OK
                )
            )
            return db

        with (
            patch.object(control.sqlite3, "connect", side_effect=interrupted),
            self.assertRaises(sqlite3.DatabaseError),
            control.database(self.home),
        ):
            self.fail("the second CREATE must fail before yielding")
        with control.database(self.home) as db:
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
        self.assertTrue({"action", "experiment"} <= tables)

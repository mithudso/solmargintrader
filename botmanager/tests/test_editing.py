from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from botmanager.domain import BotSpec, ManagerError, canonical, fingerprint
from botmanager.ledger import RuntimeLedger
from botmanager.registry import COMMANDS, CommandContext, dispatch
from botmanager.store import ManagerStore
from botmanager.strategies.grid import evaluate

from tests.test_paper import recording


def _reap_edit_child(process):
    try:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
    finally:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()


class EditingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "manager"
        self.context = CommandContext(home=self.home)
        self.store = ManagerStore(self.home)
        self.ledger = RuntimeLedger(self.home)
        self.spec = self.call("create", strategy="grid", name="first", set=["rungs=8"])
        self.bot = self.spec["bot_id"]

    def call(self, command, **params):
        result = dispatch(command, params, self.context)
        self.assertTrue(result["ok"], result)
        return result["data"]

    def refusal(self, command, code=None, **params):
        result = dispatch(command, params, self.context)
        self.assertFalse(result["ok"], result)
        if code:
            self.assertEqual(result["error"]["code"], code, result)
        return result

    def edit(self, **params):
        return self.call("edit", identity=self.bot, **params)

    def register(self):
        descriptor = recording(self.root)
        path = self.root / "descriptor.json"
        path.write_text(json.dumps(descriptor))
        self.call("register-input", identity=self.bot, descriptor=str(path))
        return path

    def run_prefix(self, cursor):
        self.call("start", identity=self.bot)
        generation = self.ledger.claim(self.bot, "fixture-owner")
        row = self.ledger.get(self.bot)
        cp = evaluate(BotSpec.from_dict(row["spec"]), row["input"], cursor)
        self.ledger.commit_tick(self.bot, generation, 0, cp)
        return generation, cp

    def test_edit_retains_values_pins_creation_and_immutable_history(self):
        saved = self.edit(set=["range_pct=20"], expected_revision=1)["spec"]
        self.assertEqual(saved["config_revision"], 2)
        for key in ("bot_id", "created_at", "source_identity", "display_name"):
            self.assertEqual(saved[key], self.spec[key])
        self.assertEqual(saved["resolved_values"]["rungs"], 8)
        self.assertEqual(saved["provenance"]["rungs"], self.spec["provenance"]["rungs"])
        self.assertEqual(saved["user_overrides"], {"rungs": 8, "range_pct": 20})
        self.assertEqual(ManagerStore(self.home).get_spec(self.bot).to_dict(), saved)
        history = self.call("history", identity=self.bot)
        self.assertEqual(
            [v["spec"]["config_revision"] for v in history["versions"]], [1, 2]
        )
        self.assertEqual(history["versions"][0]["spec"], self.spec)

    def test_same_value_pin_is_change_but_identical_pin_is_noop(self):
        first = self.edit(set=["range_pct=15.0"])
        second = self.edit(set=["range_pct=15.0"])
        self.assertEqual(first["spec"]["config_revision"], 2)
        self.assertEqual(second["spec"], first["spec"])
        self.assertEqual(second["receipt"]["outcome"], "skipped")
        self.assertEqual(len(self.call("history", identity=self.bot)["versions"]), 2)

    def test_cas_and_request_replay_after_later_revision(self):
        request_id = str(uuid4())
        first = self.edit(
            set=["range_pct=20"], request_id=request_id, expected_revision=1
        )
        self.edit(set=["deadband_bps=30"])
        self.assertEqual(
            self.edit(set=["range_pct=20"], request_id=request_id, expected_revision=1),
            first,
        )
        self.refusal(
            "edit",
            "stale_revision",
            identity=self.bot,
            set=["range_pct=21"],
            expected_revision=1,
        )
        self.refusal(
            "edit",
            "identity_conflict",
            identity=self.bot,
            set=["range_pct=21"],
            request_id=request_id,
        )
        self.assertEqual(self.store.get_spec(self.bot).config_revision, 3)

    def test_invalid_settings_never_mutate_or_reflect_canary(self):
        before = self.store.path.read_bytes()
        for values in (
            ["token=secret-canary"],
            ["range_pct=NaN"],
            ["rungs=true"],
            ["range_pct=20", "range_pct=21"],
            ["armed=true"],
            ["mode=live"],
        ):
            result = self.refusal("edit", identity=self.bot, set=values)
            self.assertNotIn("secret-canary", json.dumps(result))
            self.assertEqual(self.store.path.read_bytes(), before)

    def test_saved_edit_keeps_runtime_evidence_and_controls_pinned(self):
        self.register()
        _, cp = self.run_prefix(2)
        old = self.ledger.get(self.bot)
        self.edit(set=["range_pct=20"])
        self.assertEqual(self.ledger.get(self.bot), old)
        status = self.call("status", identity=self.bot)
        self.assertEqual(status["config_revision"], 2)
        self.assertEqual(status["active_config_revision"], 1)
        self.assertEqual(
            status["evidence_identity"]["config_hash"], self.spec["config_hash"]
        )
        self.assertTrue(status["pending_changes"])
        self.assertEqual(
            status["reference_financials"]["exposure_quote"], cp["exposure_quote"]
        )
        self.refusal("apply", "adoption_blocked", identity=self.bot)
        self.call("stop", identity=self.bot)
        self.refusal("apply", "adoption_blocked", identity=self.bot)

    def test_stopped_apply_archives_identity_and_fences_old_generation(self):
        self.register()
        generation, _ = self.run_prefix(1)
        stop_id = str(uuid4())
        stopped = self.call("stop", identity=self.bot, request_id=stop_id)
        self.ledger.stopped(self.bot)
        old = self.ledger.get(self.bot)
        old_events = self.ledger.events(self.bot)
        self.edit(set=["range_pct=20"])
        result = self.call("apply", identity=self.bot, expected_revision=2)
        new = self.ledger.get(self.bot)
        self.assertEqual(new["desired"], "stopped")
        self.assertEqual(new["cursor"], 0)
        self.assertGreater(new["generation"], old["generation"])
        self.assertNotEqual(new["runtime_id"], old["runtime_id"])
        self.assertEqual(result["receipt"]["prior_runtime_id"], old["runtime_id"])
        history = self.call("history", identity=self.bot)
        archived = next(r for r in history["runs"] if r["archived"])
        self.assertEqual(archived["state"], old)
        self.assertEqual(archived["events"], list(reversed(old_events)))
        self.assertEqual(
            self.call("stop", identity=self.bot, request_id=stop_id), stopped
        )
        self.assertEqual(self.ledger.get(self.bot), new)
        self.call("start", identity=self.bot)
        with self.assertRaises(ManagerError) as caught:
            self.ledger.heartbeat(self.bot, generation, 42)
        self.assertEqual(caught.exception.code, "stale_generation")

    def test_repeated_apply_does_not_reset_runtime(self):
        self.register()
        self.run_prefix(1)
        self.call("stop", identity=self.bot)
        self.ledger.stopped(self.bot)
        before = self.ledger.get(self.bot)
        result = self.call("apply", identity=self.bot)
        self.assertEqual(result["receipt"]["outcome"], "skipped")
        self.assertEqual(self.ledger.get(self.bot), before)

    def test_schema_is_registry_derived_and_absent_reads_are_inert(self):
        from botmanager.config import COMMON, DEFAULTS, STRATEGY_VERSIONS

        schema = self.call("schema")
        self.assertEqual(set(schema["commands"]), set(COMMANDS))
        self.assertEqual(schema["commands"]["edit"]["api_parameters"], ["overrides"])
        self.refusal(
            "edit",
            "invalid_input",
            identity=self.bot,
            set=["range_pct=20"],
            config_context={"bar_seconds": 120},
        )
        for strategy, defaults in DEFAULTS.items():
            fields = schema["strategies"][strategy]["fields"]
            self.assertEqual(set(fields), {*COMMON, *defaults, "execution_model"})
            self.assertEqual(
                schema["strategies"][strategy]["version"], STRATEGY_VERSIONS[strategy]
            )
        absent = self.root / "absent"
        for name, params in [("schema", {}), ("history", {"identity": "missing"})]:
            dispatch(name, params, CommandContext(home=absent))
        self.assertFalse(absent.exists())

    def test_schema1_reads_inert_and_write_migrates_exact_body(self):
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("DROP TABLE spec_requests")
            db.execute("DROP TABLE spec_versions")
            db.execute("PRAGMA user_version=1")
        original = self.store.path.read_bytes()
        self.assertEqual(
            self.call("history", identity=self.bot)["versions"][0]["spec"], self.spec
        )
        self.assertEqual(self.store.path.read_bytes(), original)
        self.edit(set=["range_pct=22"])
        with closing(sqlite3.connect(self.store.path)) as db, db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(
            self.call("history", identity=self.bot, revision=1)["versions"][0]["spec"],
            self.spec,
        )

    def test_concurrent_fresh_process_edits_merge_explicit_deltas(self):
        env = dict(os.environ, SOLBOT_HOME=str(self.home))
        processes = []
        for setting in ("range_pct=20", "deadband_bps=45"):
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "botmanager",
                    "edit",
                    self.bot,
                    "--set",
                    setting,
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.addCleanup(_reap_edit_child, process)
            processes.append(process)
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, (stdout, stderr))
        spec = self.store.get_spec(self.bot)
        self.assertEqual(spec.config_revision, 3)
        self.assertEqual(spec.resolved_values["range_pct"], 20)
        self.assertEqual(spec.resolved_values["deadband_bps"], 45)

    def test_concurrent_edit_apply_serializes_cas(self):
        self.register()
        self.edit(set=["range_pct=20"])
        env = dict(os.environ, SOLBOT_HOME=str(self.home))
        commands = [("edit", "--set", "deadband_bps=40"), ("apply",)]
        processes = [
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "botmanager",
                    args[0],
                    self.bot,
                    *args[1:],
                    "--expected-revision",
                    "2",
                ],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for args in commands
        ]
        results = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertIn(process.returncode, (0, 2), (stdout, stderr))
            results.append(json.loads(stdout))
        self.assertTrue(results[0]["ok"])
        self.assertEqual(self.store.get_spec(self.bot).config_revision, 3)
        active_revision = self.ledger.get(self.bot)["spec"]["config_revision"]
        if results[1]["ok"]:
            self.assertEqual(active_revision, 2)
        else:
            self.assertEqual(results[1]["error"]["code"], "stale_revision")
            self.assertEqual(active_revision, 1)

    def test_cross_operation_uuid_is_not_reexecuted(self):
        request_id = str(uuid4())
        self.edit(set=["range_pct=20"], request_id=request_id)
        self.refusal(
            "apply", "identity_conflict", identity=self.bot, request_id=request_id
        )
        other = str(uuid4())
        self.call("apply", identity=self.bot, request_id=other)
        self.refusal(
            "edit",
            "identity_conflict",
            identity=self.bot,
            request_id=other,
            set=["rungs=9"],
        )

    def test_mutation_receipt_and_acceptance_transplants_refuse(self):
        first_id, second_id = str(uuid4()), str(uuid4())
        self.edit(set=["range_pct=20"], request_id=first_id)
        self.edit(set=["range_pct=22"], request_id=second_id)
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.row_factory = sqlite3.Row
            first = dict(
                db.execute(
                    "SELECT * FROM spec_requests WHERE request_id=?", (first_id,)
                ).fetchone()
            )
            second = dict(
                db.execute(
                    "SELECT * FROM spec_requests WHERE request_id=?", (second_id,)
                ).fetchone()
            )
        for mode in ("result", "acceptance", "all"):
            with (
                self.subTest(mode=mode),
                closing(sqlite3.connect(self.store.path)) as db,
                db,
            ):
                request, result, acceptance = map(
                    json.loads, (first["request"], first["result"], first["acceptance"])
                )
                if mode == "result":
                    result["receipt"]["owner_generation"] = 100
                elif mode == "acceptance":
                    acceptance = json.loads(second["acceptance"])
                else:
                    request, result, acceptance = map(
                        json.loads,
                        (second["request"], second["result"], second["acceptance"]),
                    )
                checksum = fingerprint(
                    {"request": request, "result": result, "acceptance": acceptance}
                )
                db.execute(
                    "UPDATE spec_requests SET request=?,result=?,acceptance=?,checksum=? WHERE request_id=?",
                    (
                        canonical(request),
                        canonical(result),
                        canonical(acceptance),
                        checksum,
                        first_id,
                    ),
                )
                db.commit()
                self.refusal(
                    "edit",
                    "invalid_receipt",
                    identity=self.bot,
                    set=["range_pct=20"],
                    request_id=first_id,
                )
        self.assertEqual(self.store.get_spec(self.bot).config_revision, 3)

    def test_adoption_receipt_replays_after_later_edit_and_adoption(self):
        self.register()
        self.edit(set=["range_pct=20"])
        first_id = str(uuid4())
        first = self.call(
            "apply", identity=self.bot, expected_revision=2, request_id=first_id
        )
        self.edit(set=["range_pct=22"])
        self.call("apply", identity=self.bot)
        current = self.ledger.get(self.bot)
        self.assertEqual(
            self.call(
                "apply", identity=self.bot, expected_revision=2, request_id=first_id
            ),
            first,
        )
        self.assertEqual(self.ledger.get(self.bot), current)
        second_id = str(uuid4())
        self.call("apply", identity=self.bot, request_id=second_id)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            row = db.execute(
                "SELECT request,result,checksum,acceptance FROM adoption_requests WHERE request_id=?",
                (second_id,),
            ).fetchone()
            db.execute(
                "UPDATE adoption_requests SET request=?,result=?,checksum=?,acceptance=? WHERE request_id=?",
                (*row, first_id),
            )
        self.refusal(
            "apply",
            "invalid_receipt",
            identity=self.bot,
            expected_revision=2,
            request_id=first_id,
        )
        self.assertEqual(self.ledger.get(self.bot), current)

    def test_adoption_archives_fills_and_all_events_atomically(self):
        from unittest.mock import patch

        self.register()
        self.run_prefix(4)
        self.call("stop", identity=self.bot)
        self.ledger.stopped(self.bot)
        old = self.ledger.get(self.bot)
        self.assertTrue(old["checkpoint"]["fills"])
        self.assertEqual(old["checkpoint"]["lots"], [])
        self.edit(set=["range_pct=20"])
        with patch(
            "botmanager.ledger.save_mutation",
            side_effect=ManagerError("fixture", "Fixture abort."),
        ):
            self.refusal("apply", "fixture", identity=self.bot)
        self.assertEqual(self.ledger.get(self.bot), old)
        self.assertEqual(len(self.ledger.history(self.bot)), 1)
        self.call("apply", identity=self.bot)
        archived = self.call("history", identity=self.bot)["runs"][0]
        self.assertEqual(archived["state"], old)
        self.assertEqual(len(archived["control_receipts"]), 2)

    def test_held_lock_unknown_and_corrupt_boundary_refuse(self):
        from botmanager.worker import lifetime_lock

        self.register()
        self.edit(set=["range_pct=20"])
        with lifetime_lock(self.home / "locks" / (self.bot + ".lock")):
            self.refusal("apply", "adoption_blocked", identity=self.bot)
        old = self.ledger.get(self.bot)
        for column, value in (
            ("observed", "unknown"),
            ("tick_started", 123.0),
            ("checkpoint", "{}"),
        ):
            with self.subTest(column=column):
                with closing(sqlite3.connect(self.ledger.path)) as db, db:
                    db.execute(
                        f"UPDATE runs SET {column}=? WHERE bot_id=?", (value, self.bot)
                    )
                self.refusal("apply", identity=self.bot)
                with closing(sqlite3.connect(self.ledger.path)) as db, db:
                    db.execute(
                        f"UPDATE runs SET {column}=? WHERE bot_id=?",
                        (old[column], self.bot),
                    )
        self.assertEqual(self.ledger.get(self.bot), old)

    def test_input_capital_timeframe_currency_validation_and_explicit_new_descriptor(
        self,
    ):
        path = self.register()
        self.edit(set=["capital_usd=2000"])
        old = self.ledger.get(self.bot)
        self.refusal("apply", "incompatible_input", identity=self.bot)
        descriptor = json.loads(path.read_text())
        descriptor["capital_quote"] = 2000
        descriptor["quote_currency"] = "USDC"
        path.write_text(json.dumps(descriptor))
        self.refusal("apply", identity=self.bot, descriptor=str(path))
        self.assertEqual(self.ledger.get(self.bot), old)
        descriptor["quote_currency"] = "USD"
        path.write_text(json.dumps(descriptor))
        self.call("apply", identity=self.bot, descriptor=str(path))
        self.assertEqual(
            self.ledger.get(self.bot)["input"]["identity"]["capital_quote"], 2000
        )
        self.edit(set=["bar_seconds=120"])
        self.refusal("apply", "incompatible_input", identity=self.bot)
        self.edit(set=["bar_seconds=60", "rungs=101"])
        status = self.call("status", identity=self.bot)
        self.assertFalse(status["action_capabilities"]["apply"]["available"])
        self.assertIn("compatible_explicit_input_required", status["adoption_blockers"])

    def test_fresh_cli_edit_history_schema_apply_and_replay(self):
        env = dict(os.environ, SOLBOT_HOME=str(self.home))
        request = str(uuid4())

        def cli(*args):
            run = subprocess.run(
                [sys.executable, "-m", "botmanager", *args],
                env=env,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(run.returncode, 0, (run.stdout, run.stderr))
            return json.loads(run.stdout)["data"]

        saved = cli("edit", "first", "--set", "range_pct=20", "--request-id", request)
        cli("edit", "first", "--set", "rungs=10")
        self.assertEqual(
            cli("edit", "first", "--set", "range_pct=20", "--request-id", request),
            saved,
        )
        self.assertEqual(
            cli("history", "first", "--revision", "1")["versions"][0]["spec"], self.spec
        )
        self.assertIn("grid", cli("schema", "grid")["strategies"])
        self.assertEqual(
            cli("apply", "first")["receipt"]["reason"], "draft_uses_saved_revision"
        )
        self.assertIsNone(self.ledger.get(self.bot))

    def test_full_mutation_quotas_do_not_block_stop(self):
        from unittest.mock import patch

        self.register()
        self.call("start", identity=self.bot)
        with patch("botmanager.mutations.MAX_MUTATIONS", 0):
            self.refusal(
                "edit", "resource_limit", identity=self.bot, set=["range_pct=20"]
            )
            self.refusal("apply", "resource_limit", identity=self.bot)
            self.call("stop", identity=self.bot)
        self.assertEqual(self.ledger.get(self.bot)["desired"], "stopped")
        self.assertEqual(self.store.get_spec(self.bot).config_revision, 1)

    def test_archive_corruption_fails_closed(self):
        self.register()
        self.edit(set=["range_pct=20"])
        self.call("apply", identity=self.bot)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            raw = json.loads(db.execute("SELECT body FROM archives").fetchone()[0])
            raw["run"]["runtime_id"] = str(uuid4())
            db.execute(
                "UPDATE archives SET body=?,checksum=?",
                (canonical(raw), fingerprint(raw)),
            )
        self.refusal("history", "corrupt_checkpoint", identity=self.bot)

    def test_malformed_schema_refuses_even_reads(self):
        with closing(sqlite3.connect(self.store.path)) as db, db:
            db.execute("DROP TABLE spec_requests")
        self.refusal("config", "incompatible_store", identity=self.bot)

    def test_malformed_runtime_schema_refuses_reads(self):
        self.register()
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("DROP TABLE archives")
        self.refusal("status", "incompatible_store", identity=self.bot)

    def test_replay_validates_original_revision_not_later_cross_field_values(self):
        trend = self.call("create", strategy="trend", name="trend")
        request_id = str(uuid4())
        first = self.call(
            "edit",
            identity=trend["bot_id"],
            set=["fast_period=15"],
            request_id=request_id,
        )
        self.call(
            "edit", identity=trend["bot_id"], set=["fast_period=10", "slow_period=12"]
        )
        self.assertEqual(
            self.call(
                "edit",
                identity=trend["bot_id"],
                set=["fast_period=15"],
                request_id=request_id,
            ),
            first,
        )

    def test_schema2_runtime_migrates_without_losing_control_bindings(self):
        self.register()
        request_id = str(uuid4())
        stopped = self.call("stop", identity=self.bot, request_id=request_id)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            db.execute("DROP TABLE archives")
            db.execute("DROP TABLE adoption_requests")
            for field in ("runtime_id", "origin_sequence", "origin"):
                db.execute(f"ALTER TABLE events DROP COLUMN {field}")
            db.execute("PRAGMA user_version=2")
            original = db.execute("SELECT * FROM requests").fetchall()
        before = self.ledger.path.read_bytes()
        self.call("history", identity=self.bot)
        self.assertEqual(self.ledger.path.read_bytes(), before)
        self.edit(set=["range_pct=21"])
        self.call("apply", identity=self.bot)
        with closing(sqlite3.connect(self.ledger.path)) as db, db:
            self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 5)
            self.assertEqual(db.execute("SELECT * FROM requests").fetchall(), original)
        self.assertEqual(
            self.call("stop", identity=self.bot, request_id=request_id), stopped
        )

    def test_edit_preserves_old_defaults_after_packaged_default_change(self):
        from unittest.mock import patch

        from botmanager.config import DEFAULTS

        with patch(
            "botmanager.config.DEFAULTS",
            {**DEFAULTS, "grid": {**DEFAULTS["grid"], "range_pct": 25.0}},
        ):
            saved = self.edit(set=["deadband_bps=40"])["spec"]
        self.assertEqual(saved["resolved_values"]["range_pct"], 15.0)
        self.assertEqual(
            saved["provenance"]["range_pct"], self.spec["provenance"]["range_pct"]
        )

    def test_original_start_receipt_cannot_start_new_adopted_run(self):
        self.register()
        request_id = str(uuid4())
        original = self.call("start", identity=self.bot, request_id=request_id)
        self.call("stop", identity=self.bot)
        self.ledger.stopped(self.bot)
        self.edit(set=["range_pct=21"])
        self.call("apply", identity=self.bot)
        current = self.ledger.get(self.bot)
        self.assertEqual(
            self.call("start", identity=self.bot, request_id=request_id), original
        )
        self.assertEqual(self.ledger.get(self.bot), current)
        self.assertEqual(current["desired"], "stopped")

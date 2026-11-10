from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from botmanager.domain import ManagerError
from botmanager.ledger import RuntimeLedger
from botmanager.registry import CommandContext, dispatch
from botmanager.store import ManagerStore

from tests.test_paper import recording


class ReadConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.context = CommandContext(home=self.home)
        self.store = ManagerStore(self.home)
        self.ledger = RuntimeLedger(self.home)
        self.bot = self.call("create", strategy="grid", name="first")["bot_id"]

    def call(self, command, **params):
        result = dispatch(command, params, self.context)
        self.assertTrue(result["ok"], result)
        return result["data"]

    def register(self, bot=None):
        path = self.root / "descriptor.json"
        path.write_text(json.dumps(recording(self.root)))
        self.call("register-input", identity=bot or self.bot, descriptor=str(path))
        return path

    def edit_adopt(self, bot=None):
        self.call("edit", identity=bot or self.bot, set=["range_pct=20"])
        self.call("apply", identity=bot or self.bot)

    def test_delta_merges_latest_competing_trend_field(self):
        bot = self.call("create", strategy="trend", name="trend")["bot_id"]
        original = self.store.get_spec
        fired = False

        def after_initial_read(identity):
            nonlocal fired
            before = original(identity)
            if not fired:
                fired = True
                ManagerStore(self.home).edit(bot, {"slow_period": 100})
            return before

        with patch.object(self.store, "get_spec", side_effect=after_initial_read):
            result = self.store.edit(bot, {"fast_period": 50})
        self.assertEqual(result["spec"]["config_revision"], 3)
        self.assertEqual(result["spec"]["resolved_values"]["slow_period"], 100)
        self.assertEqual(result["spec"]["resolved_values"]["fast_period"], 50)

    def test_history_retries_edit_adopt_between_journals(self):
        self.register()
        original = ManagerStore.history
        fired = False

        def after_versions(store, bot, revision=None):
            nonlocal fired
            versions = original(store, bot, revision)
            if not fired:
                fired = True
                self.edit_adopt()
            return versions

        with patch.object(ManagerStore, "history", after_versions):
            result = self.call("history", identity=self.bot)
        self.assertTrue(fired)
        self.assertEqual(
            [v["spec"]["config_revision"] for v in result["versions"]], [1, 2]
        )
        self.assertEqual(
            [r["state"]["spec"]["config_revision"] for r in result["runs"]], [1, 2]
        )

    def test_single_status_retries_edit_adopt_after_saved_read(self):
        self.register()
        original = ManagerStore.get_spec
        fired = False

        def after_spec(store, identity):
            nonlocal fired
            spec = original(store, identity)
            if not fired:
                fired = True
                self.edit_adopt()
            return spec

        with patch.object(ManagerStore, "get_spec", after_spec):
            result = self.call("status", identity=self.bot)
        self.assertTrue(fired)
        self.assertEqual(result["saved_config_revision"], 2)
        self.assertEqual(result["active_config_revision"], 2)
        self.assertFalse(result["pending_changes"])

    def test_fleet_status_retries_edit_adopt_after_inventory_read(self):
        self.register()
        original = ManagerStore.list_specs
        fired = False

        def after_inventory(store):
            nonlocal fired
            specs = original(store)
            if not fired:
                fired = True
                self.edit_adopt()
            return specs

        with (
            patch.object(ManagerStore, "list_specs", after_inventory),
            patch("botmanager.registry._discover", return_value={"installations": []}),
        ):
            result = self.call("status")["bots"][0]
        self.assertTrue(fired)
        self.assertEqual(result["saved_config_revision"], 2)
        self.assertEqual(result["active_config_revision"], 2)
        self.assertFalse(result["pending_changes"])

    def test_fleet_runtime_rows_share_snapshot_during_same_revision_adoptions(self):
        descriptor = self.register()
        second = self.call("create", strategy="grid", name="second")["bot_id"]
        self.register(second)
        before = {bot: self.ledger.get(bot)["runtime_id"] for bot in (self.bot, second)}
        data = json.loads(descriptor.read_text())
        data["fee_bps"] = 7.0
        descriptor.write_text(json.dumps(data))
        with closing(sqlite3.connect(self.ledger.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
        original = RuntimeLedger._decode
        fired = False

        def after_first_runtime(ledger, db, row, **kwargs):
            nonlocal fired
            result = original(ledger, db, row, **kwargs)
            if not fired and row is not None:
                fired = True
                for bot in (self.bot, second):
                    self.call("apply", identity=bot, descriptor=str(descriptor))
            return result

        with (
            patch.object(RuntimeLedger, "_decode", after_first_runtime),
            patch("botmanager.registry._discover", return_value={"installations": []}),
        ):
            result = self.call("status")["bots"]
        self.assertTrue(fired)
        self.assertEqual({row["bot_id"]: row["runtime_id"] for row in result}, before)
        for bot, runtime_id in before.items():
            self.assertNotEqual(self.ledger.get(bot)["runtime_id"], runtime_id)

    def test_composite_reads_do_not_create_home_or_mutation_lock(self):
        before = {
            path.name: (path.read_bytes(), path.stat().st_mtime_ns)
            for path in self.home.iterdir()
        }
        with patch("botmanager.registry._discover", return_value={"installations": []}):
            for command, params in (
                ("history", {"identity": self.bot}),
                ("status", {"identity": self.bot}),
                ("status", {}),
            ):
                self.call(command, **params)
                missing = self.root / "absent"
                dispatch(command, params, CommandContext(home=missing))
                self.assertFalse(missing.exists())
        self.assertFalse((self.home / "mutation.lock").exists())
        self.assertEqual(
            {
                path.name: (path.read_bytes(), path.stat().st_mtime_ns)
                for path in self.home.iterdir()
            },
            before,
        )

    def test_competing_trend_change_still_honors_cas_and_final_cross_fields(self):
        for expected, initial_slow, competing_slow, code in (
            (1, 30, 100, "stale_revision"),
            (None, 100, 30, "invalid_input"),
        ):
            with self.subTest(expected=expected):
                bot = self.call(
                    "create",
                    strategy="trend",
                    name="trend-" + str(initial_slow),
                    set=[f"slow_period={initial_slow}"],
                )["bot_id"]
                original = self.store.get_spec
                fired = False

                def after_initial_read(
                    identity, original=original, bot=bot, competing_slow=competing_slow
                ):
                    nonlocal fired
                    before = original(identity)
                    if not fired:
                        fired = True
                        ManagerStore(self.home).edit(
                            bot, {"slow_period": competing_slow}
                        )
                    return before

                with (
                    patch.object(
                        self.store, "get_spec", side_effect=after_initial_read
                    ),
                    self.assertRaises(ManagerError) as caught,
                ):
                    self.store.edit(
                        bot, {"fast_period": 50}, expected_revision=expected
                    )
                self.assertEqual(caught.exception.code, code)
                saved = self.store.get_spec(bot)
                self.assertEqual(saved.config_revision, 2)
                self.assertEqual(saved.resolved_values["slow_period"], competing_slow)
                self.assertEqual(saved.resolved_values["fast_period"], 10)

    def test_continuous_edits_exhaust_bounded_read_without_mixed_response(self):
        self.register()
        original = RuntimeLedger.get_many
        captures = 0

        def change_after_capture(ledger, bot_ids):
            nonlocal captures
            rows = original(ledger, bot_ids)
            captures += 1
            self.call("edit", identity=self.bot, set=[f"deadband_bps={25 + captures}"])
            return rows

        with patch.object(RuntimeLedger, "get_many", change_after_capture):
            result = dispatch("status", {"identity": self.bot}, self.context)
        self.assertFalse(result["ok"])
        self.assertIsNone(result["data"])
        self.assertEqual(result["error"]["code"], "read_conflict")
        self.assertEqual(captures, 3)
        self.assertEqual(self.ledger.get(self.bot)["observed"], "stopped")
        self.assertEqual(self.store.get_spec(self.bot).config_revision, 4)

    def test_status_snapshot_survives_concurrent_worker_commit_and_stop(self):
        from botmanager.domain import BotSpec
        from botmanager.strategies.grid import evaluate

        self.register()
        self.call("start", identity=self.bot)
        generation = self.ledger.claim(self.bot, "fixture-worker")
        row = self.ledger.get(self.bot)
        checkpoint = evaluate(BotSpec.from_dict(row["spec"]), row["input"], 2)
        with closing(sqlite3.connect(self.ledger.path)) as db:
            db.execute("PRAGMA journal_mode=WAL")
        original = RuntimeLedger._decode
        fired = False

        def commit_and_stop_after_capture(ledger, db, raw, **kwargs):
            nonlocal fired
            captured = original(ledger, db, raw, **kwargs)
            if not fired and raw is not None:
                fired = True
                self.ledger.commit_tick(self.bot, generation, 0, checkpoint)
                self.call("stop", identity=self.bot)
            return captured

        with patch.object(RuntimeLedger, "_decode", commit_and_stop_after_capture):
            result = self.call("status", identity=self.bot)
        self.assertTrue(fired)
        self.assertEqual(result["progress"]["cursor"], 0)
        self.assertEqual(result["desired_state"], "running")
        self.assertEqual(
            result["saved_config_revision"], result["active_config_revision"]
        )
        current = self.ledger.get(self.bot)
        self.assertEqual(current["cursor"], 2)
        self.assertEqual(current["checkpoint"], checkpoint)
        self.assertEqual(current["desired"], "stopped")
        self.assertNotEqual(current["observed"], "blocked")
        with self.assertRaises(ManagerError) as caught:
            self.ledger.heartbeat(self.bot, generation, 42)
        self.assertEqual(caught.exception.code, "stale_generation")

"""Remember per-coin paper learning across settings and real disk reopen."""

import copy
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from oracle_leverage.autotrade_worker import Session, pack, policy, public_state


class DurableCoinLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.sqlite3"
        self.now = 100.0
        self.sequence = 0
        self.db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        self.addCleanup(lambda: self.db.close())
        self.session = Session(self.db, clock=lambda: self.now)

    def request(self, action, config=None):
        self.sequence += 1
        return self.session.request(f"memory-{self.sequence}", action, config)

    def tick(self, price):
        self.now += 1
        asset = self.session.s["policy"]["asset"]
        self.session.tick(
            {
                "asset": asset,
                "feed_id": {"BTC": 1, "ZEC": 66}[asset],
                "quote_currency": "USD",
                "received_at": self.now,
                "exchange_at": self.now,
                "price": price,
            }
        )

    def opening_forecast(self):
        for _ in range(6):
            self.tick(100)
            if self.session.s.get("position"):
                return self.session.s["position"]["forecast"]
        self.fail("Fresh observed fixture quotes did not open the paper position")

    def win(self, config=None):
        self.request("start", config or {})
        self.opening_forecast()
        plan = self.session.s["position"]["plan"]
        samples = self.session.learner["samples"]
        for _ in range(45):
            self.tick(plan["target_price"] * 1.0001)
            if self.session.learner["samples"] == samples + 1:
                self.request("stop")
                return
        self.fail("Observed fixture target did not settle one winning outcome")

    def test_settings_change_reuses_model_but_not_policy_qualification(self):
        self.win()
        self.request("start", {"base_collateral_usd": 11})
        forecast = self.opening_forecast()
        self.assertGreater(forecast["score"], 0.5)
        self.assertEqual(self.session.learner["samples"], 0)
        memory = public_state(self.session.s)["learning_memory"]
        self.assertEqual(memory["profile"]["samples"], 1)
        self.assertEqual(memory["coins"]["BTC"]["samples"], 1)
        self.assertTrue(memory["storage"]["durable"])

    def test_coin_switch_and_cold_restart_restore_separate_results(self):
        self.win({"asset": "BTC"})
        self.win({"asset": "ZEC"})
        self.db.close()
        self.db = sqlite3.connect(self.path)
        self.session = Session(self.db, clock=lambda: self.now)
        self.request("start", {"asset": "BTC", "base_collateral_usd": 11})
        self.assertGreater(self.opening_forecast()["score"], 0.5)
        memory = public_state(self.session.s)["learning_memory"]
        self.assertEqual(memory["coins"]["BTC"]["samples"], 1)
        self.assertEqual(memory["coins"]["ZEC"]["samples"], 1)
        self.assertEqual(memory["profile"]["samples"], 1)
        self.assertEqual(self.session.learner["samples"], 0)

    def test_incompatible_products_keep_separate_models_and_shared_coin_history(self):
        self.win()
        self.request("start", {"venue": "jupiter-sdk-1000x"})
        self.assertEqual(self.opening_forecast()["score"], 0.5)
        self.assertEqual(self.session.learner["samples"], 0)
        memory = public_state(self.session.s)["learning_memory"]
        self.assertEqual(memory["profile"]["samples"], 0)
        self.assertEqual(memory["coins"]["BTC"]["samples"], 1)

    def test_outcome_and_model_are_saved_on_disk_as_replayable_records(self):
        self.win()
        row = self.db.execute("SELECT payload FROM learner_memory_samples").fetchone()
        saved = json.loads(row[0])
        self.assertEqual(saved["asset"], "BTC")
        self.assertEqual(saved["venue"], "jupiter-cli-10x")
        self.assertEqual(saved["outcome"], "win")
        self.assertEqual(len(saved["features"]), 3)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.db.close()
        self.db = sqlite3.connect(self.path)
        values = [
            json.loads(row[0])
            for row in self.db.execute("SELECT value FROM learner_memory_profiles")
        ]
        self.assertTrue(
            any(row["samples"] == 1 and row["weights"] != [0, 0, 0] for row in values)
        )

    def test_failed_write_rolls_back_model_cohort_and_session_then_retries_once(self):
        self.win()
        self.request("start", {"base_collateral_usd": 11})
        self.opening_forecast()
        plan = self.session.s["position"]["plan"]
        self.db.execute(
            "CREATE TRIGGER deny_memory BEFORE INSERT ON learner_memory_samples BEGIN SELECT RAISE(ABORT,'fixture disk write failed'); END"
        )
        self.db.commit()
        failed = False
        for _ in range(45):
            try:
                self.tick(plan["target_price"] * 1.0001)
            except sqlite3.IntegrityError:
                failed = True
                break
        self.assertTrue(failed)
        self.assertEqual(self.session.learner["samples"], 0)
        self.assertEqual(self.session.s["net_pnl_usd"], 0)
        self.assertEqual(self.session.memory_profile["samples"], 1)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM learner_memory_samples").fetchone()[
                0
            ],
            1,
        )
        self.db.execute("DROP TRIGGER deny_memory")
        self.db.commit()
        self.tick(plan["target_price"] * 1.0001)
        self.assertEqual(self.session.learner["samples"], 1)
        self.assertEqual(self.session.memory_profile["samples"], 2)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM learner_memory_samples").fetchone()[
                0
            ],
            2,
        )

    def test_duplicate_outcome_does_not_train_twice_and_changed_replay_refuses(self):
        self.win()
        payload = json.loads(
            self.db.execute(
                "SELECT payload FROM events WHERE kind='position_outcome'"
            ).fetchone()[0]
        )
        before = self.db.execute(
            "SELECT value FROM learner_memory_profiles ORDER BY identity"
        ).fetchall()
        with self.db:
            self.assertFalse(self.session._learn(payload))
        self.assertEqual(self.session.learner["samples"], 1)
        self.assertEqual(
            before,
            self.db.execute(
                "SELECT value FROM learner_memory_profiles ORDER BY identity"
            ).fetchall(),
        )
        altered = copy.deepcopy(payload)
        altered["net_pnl_usd"] += 1
        with self.assertRaisesRegex(ValueError, "reused with different data"), self.db:
            self.session._learn(altered)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM learner_memory_samples").fetchone()[
                0
            ],
            1,
        )

    def test_legacy_coin_checkpoint_is_restored_without_rewriting_old_cohorts(self):
        self.win()
        original = copy.deepcopy(self.session.s)
        legacy_policy = {k: v for k, v in policy({}).items() if k != "learning_model"}
        cohort = hashlib.sha256(pack(legacy_policy).encode()).hexdigest()
        original.pop("learning_memory", None)
        original.update(policy=legacy_policy, policy_hash=cohort, cohort_id=cohort)
        saved_learner = pack(self.session.learner)
        self.db.close()
        self.path = Path(self.temp.name) / "legacy.sqlite3"
        self.db = sqlite3.connect(self.path)
        os.chmod(self.path, 0o600)
        self.db.executescript(
            "CREATE TABLE session(singleton INTEGER PRIMARY KEY,value TEXT); CREATE TABLE learner_cohorts(cohort TEXT PRIMARY KEY,value TEXT); CREATE TABLE requests(id TEXT PRIMARY KEY,fingerprint TEXT,result TEXT,at REAL);"
        )
        self.db.execute("INSERT INTO session VALUES(1,?)", (pack(original),))
        self.db.execute(
            "INSERT INTO learner_cohorts VALUES(?,?)", (cohort, saved_learner)
        )
        self.db.execute(
            "INSERT INTO learner_cohorts VALUES(?,?)", ("f" * 64, saved_learner)
        )
        self.db.execute(
            "INSERT INTO requests VALUES('legacy','proof',?,?)",
            (pack(original), self.now),
        )
        self.db.commit()
        self.session = Session(self.db, clock=lambda: self.now)
        self.request("start", {"base_collateral_usd": 11})
        self.assertGreater(self.opening_forecast()["score"], 0.5)
        self.assertEqual(self.session.learner["samples"], 0)
        self.assertEqual(
            self.db.execute(
                "SELECT value FROM learner_cohorts WHERE cohort=?", (cohort,)
            ).fetchone()[0],
            saved_learner,
        )
        self.assertEqual(
            self.db.execute(
                "SELECT value FROM learner_cohorts WHERE cohort=?", ("f" * 64,)
            ).fetchone()[0],
            saved_learner,
        )
        memory = public_state(self.session.s)["learning_memory"]
        self.assertEqual(memory["coins"]["BTC"]["samples"], 1)
        self.assertEqual(memory["storage"]["unattributed_cohorts"], 1)

    def test_corrupt_checkpoint_refuses_without_overwriting_saved_data(self):
        self.win()
        identity, raw = self.db.execute(
            "SELECT identity,value FROM learner_memory_profiles WHERE asset='BTC'"
        ).fetchone()
        broken = json.loads(raw)
        broken["weights"] = ["invalid"]
        stored = json.dumps(broken)
        self.db.execute(
            "UPDATE learner_memory_profiles SET value=? WHERE identity=?",
            (stored, identity),
        )
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "invalid"):
            Session(self.db, clock=lambda: self.now)
        self.assertEqual(
            self.db.execute(
                "SELECT value FROM learner_memory_profiles WHERE identity=?",
                (identity,),
            ).fetchone()[0],
            stored,
        )

    def test_idle_timer_does_not_rewrite_completed_learning_index(self):
        self.win()
        self.now += 1
        self.session.timer()
        before = self.db.total_changes
        self.now += 1
        self.session.timer()
        self.assertEqual(self.db.total_changes, before)

    def legacy_cohort(self, config, samples, weight, version="paper-net-outcome-v1"):
        selected = {k: v for k, v in policy(config).items() if k != "learning_model"}
        cohort = hashlib.sha256(pack(selected).encode()).hexdigest()
        learner = dict(
            self.session.learner,
            samples=samples,
            wins=samples,
            losses=0,
            liquidations=0,
            weights=[weight, 0.0, 0.0],
        )
        learner["version"] = version
        self.db.execute(
            "INSERT INTO learner_cohorts VALUES(?,?)", (cohort, pack(learner))
        )
        return selected, cohort

    def test_selecting_older_legacy_policy_cannot_replace_saved_model(self):
        selected, cohort = self.legacy_cohort({}, 100, 2.0)
        self.legacy_cohort({"base_collateral_usd": 11}, 5, -2.0)
        self.session.memory_store.register(cohort, selected, self.now)
        changed = policy({"base_collateral_usd": 11})
        value = self.session.memory_store.select(
            changed, hashlib.sha256(pack(changed).encode()).hexdigest(), self.now + 1
        )
        self.assertEqual(value["samples"], 100)
        self.assertEqual(value["weights"], [2.0, 0.0, 0.0])

    def test_unknown_legacy_model_is_retained_without_seeding_current_model(self):
        self.legacy_cohort({}, 10, 1.0, "unknown-future-model-v999")
        selected = policy({})
        value = self.session.memory_store.select(
            selected, hashlib.sha256(pack(selected).encode()).hexdigest(), self.now
        )
        self.assertEqual(value["samples"], 0)
        self.assertEqual(
            self.db.execute("SELECT COUNT(*) FROM learner_cohorts").fetchone()[0], 1
        )
        unknown = dict(selected, learning_model="unknown-policy-model-v999")
        cohort = hashlib.sha256(pack(unknown).encode()).hexdigest()
        self.assertFalse(self.session.memory_store.register(cohort, unknown, self.now))

    def test_inconsistent_counts_refuse_cold_restart_without_reset(self):
        key, raw = self.db.execute(
            "SELECT identity,value FROM learner_memory_profiles"
        ).fetchone()
        for changes in (
            {"samples": 10, "wins": 8, "losses": 8},
            {"samples": 10, "wins": 8, "losses": 2, "liquidations": 3},
        ):
            invalid = dict(json.loads(raw), **changes)
            self.db.execute(
                "UPDATE learner_memory_profiles SET value=? WHERE identity=?",
                (pack(invalid), key),
            )
            self.db.commit()
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                Session(self.db, clock=lambda: self.now)
            self.assertEqual(
                self.db.execute(
                    "SELECT value FROM learner_memory_profiles WHERE identity=?", (key,)
                ).fetchone()[0],
                pack(invalid),
            )

    def test_later_timer_failure_does_not_undo_committed_import_in_memory(self):
        selected, cohort = self.legacy_cohort({"asset": "ZEC"}, 10, 1.0)
        for n in range(129):
            saved = {"policy": selected, "cohort_id": cohort} if n == 128 else {}
            self.db.execute(
                "INSERT INTO requests VALUES(?,?,?,?)",
                (str(n), "fixture", pack(saved), 1.0),
            )
        self.db.execute("UPDATE learner_memory_import SET cursor=0,target=129")
        self.db.commit()
        self.session = Session(self.db, clock=lambda: self.now)
        self.request("start", {})
        self.db.execute(
            "CREATE TRIGGER deny_failure BEFORE INSERT ON events WHEN NEW.kind='feed_failure' BEGIN SELECT RAISE(ABORT,'fixture failure-event write denied'); END"
        )
        self.db.commit()
        self.now += 901
        with self.assertRaisesRegex(sqlite3.IntegrityError, "fixture failure-event"):
            self.session.timer()
        saved = json.loads(self.db.execute("SELECT value FROM session").fetchone()[0])
        self.assertEqual(self.session.s, saved)
        self.assertEqual(saved["learning_memory"]["coins"]["ZEC"]["samples"], 10)
        self.assertEqual(
            self.db.execute("SELECT cursor FROM learner_memory_import").fetchone()[0],
            129,
        )

    def test_archived_other_model_is_not_mislabeled_as_current_profile(self):
        key, asset, venue, raw = self.db.execute(
            "SELECT * FROM learner_memory_profiles"
        ).fetchone()
        archived = dict(json.loads(raw), version="future", samples=5, wins=5, losses=0)
        self.db.execute(
            "INSERT INTO learner_memory_profiles VALUES(?,?,?,?)",
            (key + "future", asset, venue, pack(archived)),
        )
        self.session._refresh_memory()
        profile = self.session.s["learning_memory"]["coins"][asset]["profiles"][venue]
        self.assertEqual(profile["samples"], 0)
        self.assertNotEqual(profile["model_version"], "future")

    def test_saved_summary_never_projects_private_weights_or_storage_paths(self):
        self.win()
        summary = self.session.s["learning_memory"]
        summary["profile"]["weights"] = "private-weights"
        summary["storage"]["path"] = "private-path"
        summary["coins"]["BTC"]["profiles"]["jupiter-cli-10x"]["weights"] = (
            "private-nested"
        )
        summary["coins"]["other-private-asset"] = {"data": "private-extra"}
        visible = json.dumps(public_state(self.session.s))
        for private in (
            "private-weights",
            "private-path",
            "private-nested",
            "private-extra",
        ):
            self.assertNotIn(private, visible)


if __name__ == "__main__":
    unittest.main()

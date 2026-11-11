"""Prospective stop issuance, open-book replay and persistent service boundaries."""
from __future__ import annotations

import json
import plistlib
import sqlite3
import subprocess
import tempfile
import unittest
from contextlib import closing, contextmanager
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backtester.core.volty import VoltyConfig, simulate, stop_levels
from ecosystem import volty_forward as v


def bars(last, count=32, step=60):
    ts = np.arange(last - (count - 1) * step, last + step, step)
    price = np.arange(count) * .1 + 100
    return {"timestamp": ts, "open": price, "high": price + .3, "low": price - .3,
            "close": price + .1, "volume": price * 0 + 1}


class VoltyForwardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "cohort"
        self.now = 864_000 + 10
        self.specs = self.root / "specs.json"
        self.specs.write_text(json.dumps({"schema_version": 1, "accounts": [
            {"interval": interval, "paper_only": True, "config": asdict(VoltyConfig(length=5, atr_mult=1.25))}
            for interval in v.STEPS]}))
        self.seeds = {interval: bars(int(self.now // step) * step - step, step=step)
                      for interval, step in v.STEPS.items()}

    def initialize(self):
        return v.initialize(self.home, self.specs, now=self.now,
                            fetcher=lambda interval, *_: self.seeds[interval], clock=lambda: self.now)

    def one(self, opened, now):
        data = bars(opened, count=1)
        return v.tick(self.home, now=now, fetcher=lambda interval, *_: data if interval == "1m" else None, clock=lambda: now)

    @contextmanager
    def delayed_database(self, instant, phase):
        """Advance a fake wall clock inside a real SQLite lock/commit boundary."""
        connect = sqlite3.connect
        triggered = []
        class DelayedConnection(sqlite3.Connection):
            def execute(self, sql, *args, **kwargs):
                if not triggered and phase == "lock" and (sql == "BEGIN IMMEDIATE" or sql.startswith("INSERT INTO metadata")):
                    triggered.append(True)
                    instant[0] += 120
                return super().execute(sql, *args, **kwargs)

            def commit(self):
                result = super().commit()
                if not triggered and phase == "commit":
                    triggered.append(True)
                    instant[0] += 120
                return result
        with patch.object(v.sqlite3, "connect", side_effect=lambda *args, **kwargs: connect(*args, factory=DelayedConnection, **kwargs)):
            yield triggered

    def assert_minute_has_no_late_confirmation(self):
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM decision_confirmations WHERE durable_at>=effective").fetchone()[0], 0)
            return [dict(row) for row in db.execute("SELECT a.status,a.reason,d.issued,d.effective,c.durable_at FROM accounts a JOIN decisions d ON d.id=a.id LEFT JOIN decision_confirmations c ON c.id=d.id AND c.effective=d.effective WHERE a.interval='1m' ORDER BY d.effective DESC")]

    def test_initialization_lock_wait_cannot_backdate_a_decision(self):
        instant = [self.now]
        with self.delayed_database(instant, "lock") as delayed, self.assertRaisesRegex(ValueError, "missed_decision_window"):
            v.initialize(self.home, self.specs, now=self.now, fetcher=lambda interval, *_: self.seeds[interval], clock=lambda: instant[0])
        self.assertTrue(delayed)
        with closing(sqlite3.connect(v._path(self.home))) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM decision_confirmations").fetchone()[0], 0)

    def test_initialization_replay_delay_is_measured_after_all_decisions_commit(self):
        instant = [self.now]
        levels = v._levels
        calls = []
        def delayed_levels(*args):
            result = levels(*args)
            calls.append(True)
            if len(calls) == 6:
                instant[0] += 120
            return result
        with patch.object(v, "_levels", side_effect=delayed_levels):
            v.initialize(self.home, self.specs, now=self.now, fetcher=lambda interval, *_: self.seeds[interval], clock=lambda: instant[0])
        rows = self.assert_minute_has_no_late_confirmation()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["durable_at"] is None and row["status"] == "blocked" for row in rows))
        self.assertTrue(all(row["issued"] < row["effective"] for row in rows))

    def test_initialization_commit_delay_leaves_immutable_late_decisions_ineligible(self):
        instant = [self.now]
        with self.delayed_database(instant, "commit") as delayed:
            v.initialize(self.home, self.specs, now=self.now, fetcher=lambda interval, *_: self.seeds[interval], clock=lambda: instant[0])
        self.assertTrue(delayed)
        rows = self.assert_minute_has_no_late_confirmation()
        self.assertTrue(all(row["durable_at"] is None and row["reason"] == "missed_decision_window" for row in rows))
        with v.connection(self.home, write=True) as db, self.assertRaisesRegex(sqlite3.IntegrityError, "immutable_paper_decision"):
            db.execute("UPDATE decisions SET issued=issued-120")

    def prepare_first_active_minute(self):
        self.initialize()
        floor = int(self.now // 60) * 60
        self.one(floor, floor + 64)
        self.one(floor + 60, floor + 124)
        return floor

    def tick_with_delay(self, phase):
        floor = self.prepare_first_active_minute()
        instant = [floor + 184]
        data = bars(floor + 120, count=1)
        fetcher = lambda interval, *_: data if interval == "1m" else None
        if phase in {"lock", "commit"}:
            with self.delayed_database(instant, phase) as delayed:
                value = v.tick(self.home, now=instant[0], fetcher=fetcher, clock=lambda: instant[0])
            self.assertTrue(delayed)
        else:
            simulate_original = v.volty.simulate
            def delayed_replay(*args, **kwargs):
                result = simulate_original(*args, **kwargs)
                instant[0] += 120
                return result
            with patch.object(v.volty, "simulate", side_effect=delayed_replay):
                value = v.tick(self.home, now=instant[0], fetcher=fetcher, clock=lambda: instant[0])
        rows = [row for row in value["accounts"] if row["interval"] == "1m"]
        self.assertTrue(all(row["status"] == "blocked" for row in rows))
        self.assertTrue(all(row["reason"] == "missed_decision_window" for row in rows))
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM decision_confirmations WHERE effective=?", (floor + 240,)).fetchone()[0], 0)
            self.assertTrue(all(row[0] < row[1] for row in db.execute("SELECT durable_at,effective FROM decision_confirmations")))

    def test_tick_lock_delay_cannot_make_late_stop_eligible(self):
        self.tick_with_delay("lock")

    def test_tick_replay_delay_cannot_make_late_stop_eligible(self):
        self.tick_with_delay("replay")

    def test_tick_commit_delay_cannot_make_late_stop_eligible(self):
        self.tick_with_delay("commit")

    def test_crash_before_initial_confirmation_retains_ineligible_decisions(self):
        with patch.object(v, "_confirm", side_effect=RuntimeError("crash_after_decision_commit")), self.assertRaisesRegex(RuntimeError, "crash_after_decision_commit"):
            self.initialize()
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 6)
            self.assertEqual(db.execute("SELECT count(*) FROM decision_confirmations").fetchone()[0], 0)
        with patch.object(v, "fetch_closed") as fetch:
            value = v.tick(self.home, now=self.now + 1, clock=lambda: self.now + 1, fetcher=fetch)
        fetch.assert_not_called()
        self.assertTrue(all(row["reason"] == "unconfirmed_decision" for row in value["accounts"]))
        self.assertTrue(all(row["latest"] is None for row in value["accounts"]))

    def test_crash_before_tick_confirmation_never_confirms_on_restart(self):
        floor = self.prepare_first_active_minute()
        with patch.object(v, "_confirm", side_effect=RuntimeError("crash_after_decision_commit")), self.assertRaisesRegex(RuntimeError, "crash_after_decision_commit"):
            self.one(floor + 120, floor + 184)
        with v.connection(self.home) as db:
            pending = db.execute("SELECT d.id,d.effective FROM decisions d LEFT JOIN decision_confirmations c ON d.id=c.id AND d.effective=c.effective WHERE c.id IS NULL").fetchall()
        self.assertEqual(len(pending), 1)
        self.one(floor + 120, floor + 185)
        with v.connection(self.home) as db:
            self.assertIsNone(db.execute("SELECT * FROM decision_confirmations WHERE id=? AND effective=?", tuple(pending[0])).fetchone())
            self.assertEqual(db.execute("SELECT reason FROM accounts WHERE id=?", (pending[0][0],)).fetchone()[0], "unconfirmed_decision")

    def test_spec_replacement_during_fetch_cannot_mix_configuration_and_provenance(self):
        original = self.specs.read_bytes()
        replaced = json.loads(original)
        for row in replaced["accounts"]:
            row["config"]["length"] = 9
        def replace_during_fetch(interval, *_):
            self.specs.write_text(json.dumps(replaced))
            return self.seeds[interval]
        value = v.initialize(self.home, self.specs, now=self.now, fetcher=replace_during_fetch, clock=lambda: self.now)
        import hashlib
        self.assertEqual(value["metadata"]["specs_sha256"], hashlib.sha256(original).hexdigest())
        self.assertNotEqual(value["metadata"]["specs_sha256"], hashlib.sha256(self.specs.read_bytes()).hexdigest())
        self.assertTrue(all(row["config"]["length"] == 5 for row in value["accounts"]))

    def test_default_engine_economics_and_open_book_are_separate(self):
        data = bars(300, count=6)
        data["high"][-1] += 5
        config = VoltyConfig(length=1, atr_mult=1)
        closed = simulate(data, config, 60, keep_fills=True)
        opened = simulate(data, config, 60, keep_fills=True, close_at_end=False)
        self.assertEqual(closed["fills"][-1]["event"], "close")
        self.assertNotEqual(opened["open_account"]["units"], 0)
        self.assertLess(opened["fees"], closed["fees"])
        self.assertNotIn("open_account", closed)
        self.assertAlmostEqual(opened["equity"][-1], opened["open_account"]["cash"] + opened["open_account"]["units"] * (opened["open_account"]["marked_price"] - opened["open_account"]["entry_price"]))

    def test_delay_catches_one_bar_lookahead_and_future_mutation(self):
        data = bars(360, count=7)
        data["high"][2] += 5
        config = VoltyConfig(length=1, atr_mult=1, fee_bps=0, slippage_bps=0, carry_bps_hour=0)
        native = simulate(data, config, 60, close_at_end=False, keep_fills=True)
        delayed = simulate(data, config, 60, close_at_end=False, keep_fills=True, signal_delay_bars=1)
        self.assertEqual(native["fills"][0]["timestamp"], 120)
        self.assertFalse(any(fill["timestamp"] == 120 for fill in delayed["fills"]))
        changed = {key: value.copy() for key, value in data.items()}
        for key in ("open", "high", "low", "close"):
            changed[key][-1] *= 10
        before = simulate(data, config, 60, end=6, close_at_end=False, signal_delay_bars=1, keep_fills=True)
        after = simulate(changed, config, 60, end=6, close_at_end=False, signal_delay_bars=1, keep_fills=True)
        self.assertEqual(before["fills"], after["fills"])
        with self.assertRaises(ValueError):
            simulate(data, config, 60, signal_delay_bars=True)

    def test_six_frozen_accounts_no_retroactive_fills_and_exact_stops(self):
        value = self.initialize()
        self.assertEqual(len(value["accounts"]), 6)
        self.assertTrue(all(row["latest"] is None for row in value["accounts"]))
        with v.connection(self.home) as db:
            for row in db.execute("SELECT * FROM decisions"):
                self.assertLess(row["issued"], row["effective"])
                account = db.execute("SELECT * FROM accounts WHERE id=?", (row["id"],)).fetchone()
                arrays = self.seeds[account["interval"]]
                padded = {key: np.r_[values, values[-1]] for key, values in arrays.items()}
                self.assertEqual(row["upper"], stop_levels(padded, VoltyConfig(**json.loads(account["config"])))[0][-1])
        # Initialization never changes or reuses an existing cohort.
        with self.assertRaises(FileExistsError):
            self.initialize()

    def test_durable_cursor_restart_and_idempotent_poll(self):
        self.initialize()
        floor = int(self.now // 60) * 60
        self.one(floor, floor + 64)
        self.one(floor + 60, floor + 124)
        value = self.one(floor + 120, floor + 184)
        rows = [row for row in value["accounts"] if row["interval"] == "1m"]
        self.assertTrue(all(row["latest"] is not None for row in rows))
        self.assertTrue(all(row["latest"]["metrics"]["first_timestamp"] == floor + 120 for row in rows))
        snapshots = [(row["id"], row["latest"]) for row in rows]
        reloaded = v.report(self.home, now=floor + 185)
        self.assertEqual(snapshots, [(row["id"], row["latest"]) for row in reloaded["accounts"] if row["interval"] == "1m"])
        self.one(floor + 120, floor + 185)
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 2)
            self.assertTrue(all(row[0] < row[1] for row in db.execute("SELECT issued,effective FROM decisions")))

    def test_outage_blocks_without_backfilling_and_preserves_evidence(self):
        self.initialize()
        floor = int(self.now // 60) * 60
        late = bars(floor + 60, count=2)
        report = v.tick(self.home, now=floor + 124, fetcher=lambda *_: late, clock=lambda: floor + 124)
        rows = [row for row in report["accounts"] if row["interval"] == "1m"]
        self.assertTrue(all(row["reason"] == "missed_decision_window" for row in rows))
        recovered = self.one(floor + 120, floor + 184)
        self.assertTrue(all(row["reason"] == "missed_decision_window" for row in recovered["accounts"] if row["interval"] == "1m"))
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM snapshots").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 6)

    def test_implementation_change_blocks_without_a_new_cohort(self):
        self.initialize()
        with patch.object(v, "implementation", return_value={"changed": "hash"}):
            report = v.tick(self.home, now=self.now + 1, clock=lambda: self.now + 1)
        self.assertTrue(all(row["reason"] == "implementation_changed" for row in report["accounts"]))
        with v.connection(self.home) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM decisions").fetchone()[0], 6)

    def test_native_10m_complete_pairs_and_closed_only(self):
        def raw_bar(opened):
            return [opened * 1000, "100", "102", "99", "101", "3", (opened + 300) * 1000 - 1]
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                pass
            def read(self, _):
                return json.dumps([raw_bar(ts) for ts in (0, 300, 600, 1200)]).encode()
        with patch.object(v, "urlopen", return_value=Response()) as call:
            result = v.fetch_closed("10m", None, 1800)
        self.assertEqual(result["timestamp"].tolist(), [0])
        self.assertEqual(result["volume"].tolist(), [6])
        self.assertIn("interval=5m", call.call_args[0][0].full_url)
        self.assertNotIn("interval=10m", call.call_args[0][0].full_url)

    def test_launchd_uses_stable_python_and_does_not_duplicate_existing_job(self):
        self.initialize()
        python = self.root / "venv" / "bin" / "python"
        python.parent.mkdir(parents=True)
        python.touch()
        with patch.object(v.sys, "platform", "darwin"), patch.object(v.Path, "home", return_value=self.root), patch.object(v.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as call:
            result = v.install_service(self.home, python)
            document = plistlib.loads(Path(result["path"]).read_bytes())
            self.assertTrue(document["RunAtLoad"])
            self.assertTrue(document["KeepAlive"])
            self.assertEqual(document["ProgramArguments"][:4], [str(python), "-I", "-m", "ecosystem.volty_forward"])
            self.assertFalse(any("bootstrap" in args[0][0] for args in call.call_args_list))
            self.assertEqual(Path(result["path"]).stat().st_mode & 0o777, 0o600)
        with patch.object(v.sys, "platform", "darwin"), self.assertRaisesRegex(ValueError, "stable_installed"):
            v.install_service(self.home, "/tmp/project-wt-worker/bin/python")

    def test_read_missing_does_not_create_store(self):
        with self.assertRaises(sqlite3.OperationalError):
            v.report(self.home)
        self.assertFalse(self.home.exists())

    def test_worker_lease_prevents_second_process(self):
        self.initialize()
        import fcntl
        lock = v._path(self.home).with_suffix(".lock")
        with lock.open("wb") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                v.run(self.home, poll=.01)


if __name__ == "__main__":
    unittest.main()

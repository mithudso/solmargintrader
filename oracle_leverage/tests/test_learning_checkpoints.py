"""Prospective JS states exercise the private native mirror through real SQLite."""
from __future__ import annotations

import concurrent.futures
import contextlib
import copy
import hashlib
import json
import os
import sqlite3
import stat
import subprocess
import tempfile
import threading
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import learning_checkpoints as store

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = "11111111-1111-4111-8111-111111111111"
LINEAGE = "22222222-2222-4222-8222-222222222222"
OTHER_LINEAGE = "33333333-3333-4333-8333-333333333333"
FIXTURES = r"""
import { newOracleState, transitionOracle, validateOracleState } from './extension/src/1000x/oracle-model.js';
import { newLiveState, transitionLive, validateLiveState } from './extension/src/1000x/oracle-live-model.js';
const horizons = [60,300,600,900,1200,3600];
const source = 'fixed_rate@200ms:6:Ew8sRjpuBttpmhSUeaAn4dLAegWnz55AuafVcGuojCPS:oracle-ohlc';
const cutoff = 1800000000, now = cutoff*1000;
function minute(market, horizon) {
  const key = JSON.stringify([1,'projected-logit-l2-v1','fixed-price-context-v1','closed-price-up-vs-nonup-v1',horizon,market,source]);
  const first = {market,source,key,horizon,cutoff,rows:[{time:cutoff-60,close:100}],nowMs:now+2000,eligible:true,features:Array(22).fill(0.1)};
  const empty = newOracleState(first), pending = transitionOracle(null,first).state;
  const mature = {...first,cutoff:cutoff+horizon,nowMs:now+horizon*1000+2000,rows:Array.from({length:horizon/60},(_,i)=>({time:cutoff+i*60,close:100.1}))};
  const resolved = transitionOracle(pending,mature).state;
  const expired = transitionOracle(pending,{...mature,eligible:false,nowMs:now+horizon*1000+90001}).state;
  for(const state of [empty,pending,resolved,expired]) validateOracleState(state,key);
  return {market,horizon,key,empty,pending,resolved,expired};
}
function live(market) {
  const identity = {market,source}, empty = newLiveState(identity);
  let pending = empty;
  for(let i=0;i<=30;i++) {
    const stamp=now+i*1000;
    pending=transitionLive(pending,{identity,quote:{price:100+i*0.01,exchangeMs:stamp,receivedMs:stamp},nowMs:stamp}).state;
  }
  const endpoints = Object.fromEntries(horizons.map(h=>{
    const stamp=now+30000+h*1000+1000;
    return [h,transitionLive(pending,{identity,quote:{price:100.5,exchangeMs:stamp,receivedMs:stamp},nowMs:stamp}).state];
  }));
  const expired=transitionLive(pending,{identity,quote:null,nowMs:now+30000+3600000+2001}).state;
  for(const state of [empty,pending,expired,...Object.values(endpoints)]) validateLiveState(state,state.key);
  return {market,key:empty.key,empty,pending,endpoints,expired};
}
const minutes = ['SOL','BTC','ZEC','A12345678901'].flatMap(m=>horizons.map(h=>minute(m,h)));
const first=minute('SOL',60); let large=first.pending;
for(let i=1;i<=132;i++) {
  const t=cutoff+i*60;
  large=transitionOracle(large,{market:'SOL',source,key:first.key,horizon:60,cutoff:t,rows:[{time:t-60,close:100+i*0.01}],nowMs:t*1000+2000,eligible:true,features:Array(22).fill(0.1)}).state;
}
validateOracleState(large,large.key);
console.log(JSON.stringify({minutes,live:['SOL','BTC','ZEC','A12345678901'].map(live),large}));
"""


class LearningCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        generated = subprocess.run(["node", "--input-type=module", "-e", FIXTURES], cwd=ROOT,
                                   capture_output=True, text=True, timeout=30, check=True)
        cls.fixtures = json.loads(generated.stdout)
        cls.minute = next(x for x in cls.fixtures["minutes"] if x["market"] == "SOL" and x["horizon"] == 600)
        cls.live = cls.fixtures["live"][0]

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="oracle-learning-test-")
        self.addCleanup(self.scratch.cleanup)
        self.home = Path(self.scratch.name) / "private"
        self.environment = patch.dict(os.environ, {"ORACLE_LEARNING_HOME": str(self.home)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def checkpoint(self, state, revision=1, lineage=LINEAGE, text=None):
        return {"lineage": lineage, "revision": revision,
                "text": text if text is not None else json.dumps(state, separators=(",", ":"), allow_nan=False)}

    def save(self, state, revision=1, kind="minute", namespace=NAMESPACE, lineage=LINEAGE, text=None):
        return store.save(namespace, kind, state["key"], self.checkpoint(state, revision, lineage, text))

    def read(self, state=None, kind="minute", namespace=NAMESPACE):
        state = self.minute["pending"] if state is None else state
        page = store.load(namespace, kind, state["key"])
        if not page["found"]:
            return page
        text = page["text"]
        while len(text) < page["length"]:
            chunk = store.load(namespace, kind, state["key"], len(text), page["digest"])
            self.assertLessEqual(len(chunk["text"]), store.CHUNK_CHARS)
            self.assertTrue(chunk["text"])
            text += chunk["text"]
        return {**page, "text": text}

    @contextlib.contextmanager
    def database(self):
        with contextlib.closing(sqlite3.connect(self.home / "checkpoints.sqlite3")) as db, db:
            yield db

    def assert_kept_head(self, state=None, revision=1, kind="minute"):
        expected = self.minute["pending"] if state is None else state
        loaded = self.read(expected, kind)
        self.assertEqual(loaded["revision"], revision)
        self.assertEqual(json.loads(loaded["text"]), expected)

    def test_all_coin_and_horizon_partitions_survive_cold_reopen(self):
        for fixture in self.fixtures["minutes"]:
            for revision, name in enumerate(("empty", "pending", "resolved"), 1):
                self.save(fixture[name], revision)
            self.assert_kept_head(fixture["resolved"], 3)
        for fixture in self.fixtures["live"]:
            self.save(fixture["pending"], kind="live")
            self.assert_kept_head(fixture["pending"], kind="live")
        self.assertEqual(stat.S_IMODE(self.home.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.home / "checkpoints.sqlite3").stat().st_mode), 0o600)

    def test_both_reducers_allow_real_terminal_progress(self):
        self.save(self.minute["pending"])
        self.save(self.minute["expired"], 2)
        self.assert_kept_head(self.minute["expired"], 2)
        self.save(self.live["pending"], kind="live")
        self.save(self.live["expired"], 2, "live")
        self.assert_kept_head(self.live["expired"], 2, "live")
        for horizon, endpoint in self.live["endpoints"].items():
            namespace = f"{int(horizon):08x}-1111-4111-8111-111111111111"
            self.save(self.live["pending"], kind="live", namespace=namespace)
            self.save(endpoint, 2, "live", namespace)
            self.assertEqual(json.loads(self.read(endpoint, "live", namespace)["text"]), endpoint)

    def test_live_fractional_quote_timestamps_remain_supported(self):
        state = copy.deepcopy(self.live["pending"])
        state["lastQuote"]["exchangeMs"] += 0.125
        state["lastQuote"]["receivedMs"] += 0.25
        self.save(state, kind="live")
        self.assert_kept_head(state, kind="live")

    def test_exact_upload_bytes_define_digest_and_same_revision_identity(self):
        state = self.minute["pending"]
        text = json.dumps(state, indent=2) + "\n"
        saved = self.save(state, text=text)
        self.assertEqual(saved["digest"], hashlib.sha256(text.encode()).hexdigest())
        self.assertEqual(self.read()["text"], text)
        duplicate = self.save(state, text=text)
        self.assertEqual(duplicate["status"], "unchanged")
        self.assertTrue(duplicate["saved"])
        with self.assertRaisesRegex(ValueError, "revision_conflict"):
            self.save(state)
        self.assertEqual(self.read()["text"], text)

    def test_lineage_and_revision_cas_refuse_replacement(self):
        self.save(self.minute["resolved"], 2)
        stale = self.save(self.minute["pending"], 1)
        self.assertFalse(stale["saved"])
        self.assertEqual(stale["status"], "disk_newer")
        with self.assertRaisesRegex(ValueError, "lineage_conflict"):
            self.save(self.minute["resolved"], 3, lineage=OTHER_LINEAGE)
        self.assert_kept_head(self.minute["resolved"], 2)

    def test_first_review_malformed_and_boolean_schema_cannot_replace_good_head(self):
        self.save(self.minute["pending"])
        for field, replacement in (("schema", True), ("schema", 1.0), ("model.weights", [])):
            state = copy.deepcopy(self.minute["pending"])
            target, name = (state["model"], "weights") if "." in field else (state, field)
            target[name] = replacement
            with self.subTest(field=field, replacement=replacement), self.assertRaises(ValueError):
                self.save(state, 2)
            self.assert_kept_head()

    def test_first_review_zero_samples_cannot_erase_pending(self):
        self.save(self.minute["pending"])
        with self.assertRaisesRegex(ValueError, "count_regression"):
            self.save(self.minute["empty"], 2)
        self.assert_kept_head()
        self.save(self.live["pending"], kind="live")
        with self.assertRaisesRegex(ValueError, "count_regression"):
            self.save(self.live["empty"], 2, "live")
        self.assert_kept_head(self.live["pending"], kind="live")

    def test_pending_identity_is_immutable_for_retention_and_resolution(self):
        for kind, fixture, resolved in (("minute", self.minute, self.minute["resolved"]),
                                        ("live", self.live, self.live["endpoints"]["60"])):
            self.save(fixture["pending"], kind=kind)
            for field, value in (("reference", 123), ("x", [0] * (22 if kind == "minute" else 5))):
                candidate = copy.deepcopy(fixture["pending"])
                candidate["pending"][0][field] = value
                with self.subTest(kind=kind, field=field), self.assertRaisesRegex(ValueError, "pending_identity_conflict"):
                    self.save(candidate, 2, kind)
            candidate = copy.deepcopy(resolved)
            if kind == "minute":
                candidate["recent"][0]["x"] = [0] * 22
            else:
                candidate["metrics"]["60"]["recent"][0]["baseline"] = [0.5, 0.25, 0.25]
            with self.assertRaisesRegex(ValueError, "pending_identity_conflict"):
                self.save(candidate, 2, kind)
            self.assert_kept_head(fixture["pending"], kind=kind)

    def test_removing_pending_requires_terminal_progress_in_its_horizon(self):
        self.save(self.minute["pending"])
        changed = copy.deepcopy(self.minute["pending"])
        changed["pending"] = []
        with self.assertRaises(ValueError):
            self.save(changed, 2)
        self.assert_kept_head()
        self.save(self.live["pending"], kind="live")
        changed = copy.deepcopy(self.live["pending"])
        old = changed["pending"].pop(0)
        changed["metrics"][str(old["horizon"])]["issued"] -= 1
        with self.assertRaisesRegex(ValueError, "count_regression"):
            self.save(changed, 2, "live")
        self.assert_kept_head(self.live["pending"], kind="live")

    def test_all_cumulative_progress_and_watermarks_cannot_decrease(self):
        resolved = self.minute["resolved"]
        self.save(resolved)
        paths = [("issued",), ("lastIssuedCutoff",), ("lastClosedTarget",), ("updatedAtMs",),
                 ("totals", "up"), ("totals", "candidate", "brier"),
                 ("totals", "baseline", "logLoss")]
        for path in paths:
            candidate = copy.deepcopy(resolved)
            target = candidate
            for field in path[:-1]:
                target = target[field]
            target[path[-1]] = 0
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.save(candidate, 2)
            self.assert_kept_head(resolved)
        live = copy.deepcopy(self.live["endpoints"]["60"])
        live["metrics"]["60"]["capacityDrops"] = 4
        self.save(live, kind="live")
        for path in (("revision",), ("lastProbeBucket",), ("lastProbeAtMs",),
                     ("lastQuote", "exchangeMs"), ("lastQuote", "receivedMs"),
                     ("metrics", "60", "capacityDrops"), ("metrics", "60", "candidate", "brier")):
            candidate = copy.deepcopy(live)
            target = candidate
            for field in path[:-1]:
                target = target[field]
            target[path[-1]] = 0
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.save(candidate, 2, "live")
            self.assert_kept_head(live, kind="live")

    def test_model_cannot_change_without_new_samples(self):
        for kind, state in (("minute", self.minute["pending"]), ("live", self.live["pending"])):
            self.save(state, kind=kind)
            changed = copy.deepcopy(state)
            model = changed["model"] if kind == "minute" else changed["models"]["60"]
            if kind == "minute":
                model["weights"][0] = 1
            else:
                model["weights"][0][0] = 1
            with self.assertRaisesRegex(ValueError, "training_without_samples"):
                self.save(changed, 2, kind)
            self.assert_kept_head(state, kind=kind)

    def test_strict_nested_fields_dimensions_counters_and_secrets_before_io(self):
        mutations = [
            ("minute", ("model", "extra"), "unexpected"),
            ("minute", ("model", "apiKey"), "fixture-secret-never-store"),
            ("minute", ("model", "weights"), [0] * 21),
            ("minute", ("model", "bias"), True),
            ("minute", ("pending", 0, "x"), [0] * 21),
            ("minute", ("pending", 0, "modelSamples"), True),
            ("minute", ("totals", "candidate", "secret"), "refuse"),
            ("minute", ("historicalTrainingSamples",), 1),
            ("minute", ("historicalTrainingSamples",), False),
            ("live", ("models", "60", "weights"), []),
            ("live", ("models", "60", "bias"), [0] * 2),
            ("live", ("metrics", "60", "counts"), [0, 0, True]),
            ("live", ("metrics", "60", "candidate", "extra"), 0),
            ("live", ("pending", 0, "p"), [0.2, 0.2, 0.2]),
            ("live", ("pending", 0, "credential"), "refuse"),
            ("live", ("history", 0, "extra"), 0),
            ("live", ("lastQuote", "password"), "refuse"),
        ]
        for kind, path, replacement in mutations:
            state = copy.deepcopy(self.minute["pending"] if kind == "minute" else self.live["pending"])
            target = state
            for field in path[:-1]:
                target = target[field]
            target[path[-1]] = replacement
            with self.subTest(kind=kind, path=path), self.assertRaises(ValueError), patch.object(store, "_database") as database:
                self.save(state, kind=kind)
            database.assert_not_called()
        self.assertFalse(self.home.exists())

    def test_wrong_model_source_horizon_and_version_refuse_before_storage(self):
        for index, replacement in ((0, True), (0, 2), (1, "other-model"), (2, "other-features"),
                                   (3, "other-target"), (4, 120), (5, "sol"), (6, "fixed_rate@200ms:6:bad:oracle-ohlc")):
            state = copy.deepcopy(self.minute["pending"])
            binding = json.loads(state["key"])
            binding[index] = replacement
            key = json.dumps(binding, separators=(",", ":"))
            with self.subTest(index=index), self.assertRaises(ValueError):
                store.save(NAMESPACE, "minute", key, self.checkpoint(state))
        state = copy.deepcopy(self.minute["pending"])
        state["source"] = self.live["key"]
        with self.assertRaises(ValueError):
            self.save(state)
        self.assertFalse(self.home.exists())

    def test_size_nonfinite_duplicate_field_and_deep_json_refuse_before_storage(self):
        valid = self.checkpoint(self.minute["pending"])["text"]
        malformed = [valid + " " * store.MAX_BYTES, "[" * 2000 + "]" * 2000,
                     valid.replace('"schema":1', '"schema":1,"schema":1'),
                     valid.replace('"bias":0', '"bias":NaN'), valid.replace('"bias":0', '"bias":1e999'),
                     valid.replace('"bias":0', '"bias":' + "[" * 20 + "0" + "]" * 20)]
        for text in malformed:
            with self.subTest(length=len(text)), self.assertRaises(ValueError):
                self.save(self.minute["pending"], text=text)
        self.assertFalse(self.home.exists())

    def test_first_review_save_and_load_share_bounded_decompression(self):
        self.save(self.minute["pending"])
        with self.database() as db:
            db.execute("UPDATE checkpoints SET payload=?", (zlib.compress(b" " * (store.MAX_BYTES * 4)),))
        sizes = []
        original = store.zlib.decompressobj
        class BoundedUnpacker:
            def __init__(self):
                self.inner = original()
            def decompress(self, payload, maximum):
                sizes.append(maximum)
                raw = self.inner.decompress(payload, maximum)
                sizes.append(len(raw))
                return raw
            def __getattr__(self, name):
                return getattr(self.inner, name)
        with patch.object(store.zlib, "decompress", side_effect=AssertionError("unbounded decoder used")), patch.object(store.zlib, "decompressobj", BoundedUnpacker):
            for operation in (lambda: self.read(), lambda: self.save(self.minute["resolved"], 2)):
                with self.assertRaisesRegex(ValueError, "checkpoint_corrupt"):
                    operation()
        self.assertEqual(sizes, [store.MAX_BYTES + 1] * 4)
        with self.database() as db:
            self.assertEqual(db.execute("SELECT revision FROM checkpoints").fetchone()[0], 1)

    def test_digest_length_truncated_trailing_and_oversized_blob_corruption_refuse(self):
        for mutation, value in (("digest", "0" * 64), ("length", 1), ("payload", b"broken"),
                                ("payload", zlib.compress(b"{}") + b"trailing"),
                                ("payload", b"x" * (store.MAX_COMPRESSED_BYTES + 1))):
            with self.subTest(mutation=mutation, size=len(value) if isinstance(value, bytes) else value):
                self.save(self.minute["pending"])
                with self.database() as db:
                    db.execute(f"UPDATE checkpoints SET {mutation}=?", (value,))
                with self.assertRaisesRegex(ValueError, "checkpoint_corrupt"):
                    self.read()
                with self.assertRaisesRegex(ValueError, "checkpoint_corrupt"):
                    self.save(self.minute["resolved"], 2)
                with self.database() as db:
                    db.execute("DELETE FROM checkpoints")

    def test_paged_reads_exact_digest_and_changed_midread_refuse(self):
        state = self.fixtures["large"]
        text = json.dumps(state, indent=4)
        self.assertGreater(len(text), store.CHUNK_CHARS)
        saved = self.save(state, text=text)
        self.assertEqual(self.read(state)["text"], text)
        first = store.load(NAMESPACE, "minute", state["key"])
        self.assertEqual(len(first["text"]), store.CHUNK_CHARS)
        self.save(state, 2, text=text + "\n")
        with self.assertRaisesRegex(ValueError, "changed_during_read"):
            store.load(NAMESPACE, "minute", state["key"], store.CHUNK_CHARS, saved["digest"])

    def test_outcomes_archive_is_idempotent_and_cannot_rewrite_old_identity(self):
        state = self.minute["resolved"]
        self.save(state)
        self.save(state, 2)
        with self.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0], 1)
            db.execute("UPDATE outcomes SET payload='{}'")
        with self.assertRaisesRegex(ValueError, "outcome_identity_conflict"):
            self.save(state, 3)
        self.assert_kept_head(state, 2)
        endpoint = self.live["endpoints"]["60"]
        self.save(endpoint, kind="live")
        self.save(endpoint, 2, "live")
        with self.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outcomes WHERE kind='live'").fetchone()[0], 1)

    def test_checkpoint_failure_rolls_back_outcome_and_model_metrics_together(self):
        self.save(self.minute["pending"])
        with self.database() as db:
            db.execute("CREATE TRIGGER deny_checkpoint BEFORE UPDATE ON checkpoints BEGIN SELECT RAISE(ABORT,'fixture checkpoint write denied'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.save(self.minute["resolved"], 2)
        self.assert_kept_head()
        with self.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0], 0)

    def test_first_review_concurrent_first_directory_and_database_creation(self):
        barrier = threading.Barrier(4)
        original = Path.mkdir
        def synchronized_mkdir(path, *args, **kwargs):
            if path == self.home:
                barrier.wait(timeout=5)
            return original(path, *args, **kwargs)
        def create(index):
            namespace = f"{index:08x}-1111-4111-8111-111111111111"
            return self.save(self.minute["pending"], namespace=namespace)
        with patch.object(Path, "mkdir", synchronized_mkdir), concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(create, range(4)))
        self.assertTrue(all(result["saved"] for result in results))
        with self.database() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM checkpoints").fetchone()[0], 4)

    def test_concurrent_exclusive_database_file_creation_verifies_the_winner(self):
        self.home.mkdir(mode=0o700)
        barrier = threading.Barrier(4)
        original = os.open
        def synchronized_open(path, flags, mode=0o777, *args, **kwargs):
            if Path(path) == self.home / "checkpoints.sqlite3":
                barrier.wait(timeout=5)
            return original(path, flags, mode, *args, **kwargs)
        def create(_):
            db = store._database(True)
            db.close()
        with patch.object(store.os, "open", synchronized_open), concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(create, range(4)))
        self.assertEqual(stat.S_IMODE((self.home / "checkpoints.sqlite3").stat().st_mode), 0o600)

    def test_readonly_absent_or_uninitialized_never_creates_paths_or_schema(self):
        self.assertEqual(self.read(), {"found": False})
        self.assertEqual(store.profiles(), {"profiles": []})
        self.assertFalse(self.home.exists())
        self.home.mkdir(mode=0o700)
        path = self.home / "checkpoints.sqlite3"
        path.touch(mode=0o600)
        self.assertEqual(self.read(), {"found": False})
        self.assertEqual(store.profiles(), {"profiles": []})
        with contextlib.closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master").fetchall(), [])
        self.assertEqual(list(self.home.iterdir()), [path])

    def test_private_directory_symlink_database_symlink_modes_and_hardlink_refuse(self):
        outside = Path(self.scratch.name) / "outside"
        outside.mkdir(mode=0o700)
        self.home.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.save(self.minute["pending"])
        self.home.unlink()
        self.home.mkdir(mode=0o755)
        with self.assertRaises(ValueError):
            self.save(self.minute["pending"])
        self.home.chmod(0o700)
        database = self.home / "checkpoints.sqlite3"
        target = outside / "target"
        target.touch(mode=0o600)
        database.symlink_to(target)
        with self.assertRaises(ValueError):
            self.save(self.minute["pending"])
        database.unlink()
        os.link(target, database)
        with self.assertRaises(ValueError):
            self.save(self.minute["pending"])
        database.unlink()
        database.touch(mode=0o644)
        with self.assertRaises(ValueError):
            self.save(self.minute["pending"])

    def test_profiles_only_returns_bounded_recovery_metadata(self):
        for index in range(35):
            namespace = f"{index:08x}-1111-4111-8111-111111111111"
            self.save(self.minute["pending"], namespace=namespace)
        result = store.profiles()
        self.assertEqual(len(result["profiles"]), 32)
        self.assertTrue(all(set(row) == {"namespace", "partitions", "saved_at"} for row in result["profiles"]))
        self.assertEqual(len(store.profiles(2)["profiles"]), 2)
        for invalid in (True, 0, 33, 1.0):
            with self.assertRaises(ValueError):
                store.profiles(invalid)

    def test_registry_learning_commands_use_only_the_checkpoint_store(self):
        from soltui import commands

        state = self.minute["pending"]
        address = {"namespace": NAMESPACE, "kind": "minute", "key": state["key"]}
        with patch.object(commands, "_autotrade_call", side_effect=AssertionError("owner path used")) as owner:
            saved = commands.dispatch("oracle.learning.save", {**address, "checkpoint": self.checkpoint(state)},
                                      surface="native", ctx=object(), quiet=True)
            self.assertTrue(saved["ok"], saved)
            loaded = commands.dispatch("oracle.learning.load", address, surface="native", ctx=object(), quiet=True)
            self.assertEqual(json.loads(loaded["result"]["text"]), state)
            profiles = commands.dispatch("oracle.learning.profiles", {}, surface="native", ctx=object(), quiet=True)
            self.assertEqual(profiles["result"]["profiles"][0]["namespace"], NAMESPACE)
            owner.assert_not_called()
        self.assertFalse(commands.COMMANDS["oracle.learning.save"].read_only)
        self.assertTrue(commands.COMMANDS["oracle.learning.load"].read_only)
        self.assertTrue(commands.COMMANDS["oracle.learning.profiles"].read_only)
        with patch.object(store, "load", side_effect=sqlite3.OperationalError("private/path fixture-secret")):
            refused = commands.dispatch("oracle.learning.load", address, ctx=object(), quiet=True)
        self.assertEqual(refused["error"]["code"], "unavailable")
        self.assertNotIn("fixture-secret", json.dumps(refused))
        self.assertNotIn("private/path", json.dumps(refused))


if __name__ == "__main__":
    unittest.main()

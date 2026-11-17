"""Durable coin experience, separate from policy-qualified paper evidence.

The session owns the SQLite transaction. Checkpoints, resolved samples and the
policy learner therefore commit or roll back together. No status read creates
this store, and no existing cohort is deleted or rewritten by migration.
"""

from __future__ import annotations

import hashlib
import json
import math

MODEL_VERSION = "coin-paper-logit-v1"
FEATURE_VERSION = "bias-side-momentum-v1"
TARGET_VERSION = "closed-paper-net-positive-v1"
ASSETS = ("BTC", "ZEC")
VENUES = ("jupiter-cli-10x", "jupiter-sdk-1000x")


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))


def score(weights, features):
    value = sum(w * x for w, x in zip(weights, features))
    return 1 / (1 + math.exp(-max(-20.0, min(20.0, value))))


def identity(policy):
    venue = policy.get("venue")
    expected = {
        "jupiter-cli-10x": (10, "linear-10x-v1"),
        "jupiter-sdk-1000x": (1000, "exit50-proxy-v1"),
    }.get(venue)
    if (
        policy.get("mode") != "paper"
        or policy.get("learning_model") not in (None, MODEL_VERSION)
        or policy.get("asset") not in ASSETS
        or expected is None
        or type(policy.get("leverage")) is not int
        or (policy["leverage"], policy.get("execution_model")) != expected
        or policy.get("price_basis") != "jupiter-oracle-usd"
    ):
        raise ValueError("Unsupported remembered-learning identity")
    value = {
        "asset": policy["asset"],
        "venue": venue,
        "leverage": policy["leverage"],
        "execution_model": policy["execution_model"],
        "price_basis": policy["price_basis"],
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "target_version": TARGET_VERSION,
    }
    return hashlib.sha256(encode(value).encode()).hexdigest(), value


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _checked_learner(value):
    if not isinstance(value, dict):
        raise TypeError("Saved learning state is invalid; it was not reset")
    for key in ("samples", "wins", "losses", "liquidations"):
        if type(value.get(key)) is not int or value[key] < 0:
            raise ValueError("Saved learning counts are invalid; they were not reset")
    if (
        value["wins"] + value["losses"] != value["samples"]
        or value["liquidations"] > value["losses"]
    ):
        raise ValueError("Saved learning counts are inconsistent")
    if not _number(value.get("net_pnl_usd")):
        raise ValueError("Saved learning result is invalid")
    weights = value.get("weights")
    if (
        not isinstance(weights, list)
        or len(weights) != 3
        or any(not _number(w) or abs(w) > 5 for w in weights)
    ):
        raise ValueError("Saved learning model is invalid; it was not reset")
    return value


class LearningMemory:
    def __init__(self, db):
        self.db = db
        db.executescript("""
        CREATE TABLE IF NOT EXISTS learner_memory_profiles (
            identity TEXT PRIMARY KEY, asset TEXT NOT NULL, venue TEXT NOT NULL,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learner_memory_cohorts (
            cohort TEXT PRIMARY KEY, identity TEXT NOT NULL, asset TEXT NOT NULL,
            venue TEXT NOT NULL, seen_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learner_memory_samples (
            intent_id TEXT PRIMARY KEY, identity TEXT NOT NULL,
            at REAL NOT NULL, fingerprint TEXT NOT NULL, payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learner_memory_import (
            singleton INTEGER PRIMARY KEY CHECK(singleton=1),
            cursor INTEGER NOT NULL, target INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO learner_memory_import
            SELECT 1,0,COALESCE(MAX(rowid),0) FROM requests;
        """)
        db.execute("PRAGMA synchronous=FULL")

    def profile(self, policy, now):
        key, dimensions = identity(policy)
        row = self.db.execute(
            "SELECT value FROM learner_memory_profiles WHERE identity=?", (key,)
        ).fetchone()
        if row:
            value = _checked_learner(json.loads(row[0]))
            if (
                value.get("version") != MODEL_VERSION
                or type(value.get("observed_samples")) is not int
                or not 0 <= value["observed_samples"] <= value["samples"]
                or not _number(value.get("updated_at"))
                or not _number(value.get("seeded_at"))
            ):
                raise ValueError("Saved learning version or checkpoint is invalid")
            return value
        value = {
            "version": MODEL_VERSION,
            "samples": 0,
            "wins": 0,
            "losses": 0,
            "liquidations": 0,
            "net_pnl_usd": 0.0,
            "weights": [0.0, 0.0, 0.0],
            "observed_samples": 0,
            "seed_cohort": None,
            "seeded_at": 0.0,
            "updated_at": now,
        }
        self._save(key, dimensions, value)
        return value

    def _save(self, key, dimensions, value):
        _checked_learner(value)
        self.db.execute(
            "INSERT INTO learner_memory_profiles VALUES(?,?,?,?) "
            "ON CONFLICT(identity) DO UPDATE SET value=excluded.value",
            (key, dimensions["asset"], dimensions["venue"], encode(value)),
        )

    def register(self, cohort, policy, at):
        if (
            not isinstance(cohort, str)
            or hashlib.sha256(encode(policy).encode()).hexdigest() != cohort
        ):
            return False
        try:
            key, dimensions = identity(policy)
        except (ValueError, TypeError, KeyError):
            return False
        if not _number(at) or at < 0:
            return False
        self.db.execute(
            "INSERT INTO learner_memory_cohorts VALUES(?,?,?,?,?) "
            "ON CONFLICT(cohort) DO UPDATE SET seen_at=MAX(seen_at,excluded.seen_at)",
            (cohort, key, dimensions["asset"], dimensions["venue"], at),
        )
        row = self.db.execute(
            "SELECT value FROM learner_cohorts WHERE cohort=?", (cohort,)
        ).fetchone()
        if row:
            legacy = _checked_learner(json.loads(row[0]))
            value = self.profile(policy, at)
            if (
                legacy["samples"] > 0
                and legacy.get("version") == "paper-net-outcome-v1"
                and value["observed_samples"] == 0
                and value["seed_cohort"] is None
            ):
                # A complete trained checkpoint can seed a compatible model.
                # Freeze that seed once: choosing an old policy is not new
                # evidence and must never replace remembered experience.
                for name in (
                    "samples",
                    "wins",
                    "losses",
                    "liquidations",
                    "net_pnl_usd",
                    "weights",
                ):
                    value[name] = legacy[name]
                value.update(seed_cohort=cohort, seeded_at=at, updated_at=at)
                self._save(key, dimensions, value)
        return True

    def select(self, policy, cohort, now):
        self.register(cohort, policy, now)
        # A previously used exact policy remains identifiable without guessing
        # the coin behind an opaque historical cohort hash.
        legacy_policy = {k: v for k, v in policy.items() if k != "learning_model"}
        legacy_cohort = hashlib.sha256(encode(legacy_policy).encode()).hexdigest()
        self.register(legacy_cohort, legacy_policy, now)
        return self.profile(policy, now)

    def import_legacy(self, limit=128):
        cursor, target = self.db.execute(
            "SELECT cursor,target FROM learner_memory_import WHERE singleton=1"
        ).fetchone()
        if cursor >= target:
            return False
        rows = self.db.execute(
            "SELECT rowid,result,at FROM requests WHERE rowid>? AND rowid<=? "
            "ORDER BY rowid LIMIT ?",
            (cursor, target, limit),
        ).fetchall()
        for rowid, raw, at in rows:
            try:
                result = json.loads(raw)
            except (ValueError, TypeError):
                cursor = rowid
                continue
            if isinstance(result, dict) and isinstance(result.get("policy"), dict):
                self.register(result.get("cohort_id"), result["policy"], at)
            cursor = rowid
        self.db.execute(
            "UPDATE learner_memory_import SET cursor=? WHERE singleton=1",
            (cursor if rows else target,),
        )
        return True

    def record(self, policy, position, now):
        key, dimensions = identity(policy)
        forecast = position["forecast"]
        features = forecast["features"]
        intent = position["plan"]["intent_id"]
        if (
            not isinstance(intent, str)
            or not 1 <= len(intent) <= 128
            or not isinstance(features, list)
            or len(features) != 3
            or any(not _number(x) or abs(x) > 1 for x in features)
            or position.get("state") not in ("closed", "liquidated")
            or position.get("outcome") not in ("win", "loss", "failure")
            or not _number(position.get("net_pnl_usd"))
            or not _number(forecast.get("score"))
            or not 0 <= forecast["score"] <= 1
            or forecast.get("version") != MODEL_VERSION
            or not _number(now)
            or now < 0
        ):
            raise ValueError("Resolved learning outcome is invalid")
        payload = {
            "asset": dimensions["asset"],
            "venue": dimensions["venue"],
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "target_version": TARGET_VERSION,
            "intent_id": intent,
            "features": features,
            "forecast_score": forecast["score"],
            "outcome": position["outcome"],
            "net_pnl_usd": position["net_pnl_usd"],
            "state": position["state"],
            "exited_at": position.get("exited_at"),
        }
        packed = encode(payload)
        fingerprint = hashlib.sha256(packed.encode()).hexdigest()
        previous = self.db.execute(
            "SELECT fingerprint FROM learner_memory_samples WHERE intent_id=?",
            (intent,),
        ).fetchone()
        if previous:
            if previous[0] != fingerprint:
                raise ValueError(
                    "Saved learning outcome identity was reused with different data"
                )
            return False
        value = self.profile(policy, now)
        won = position["outcome"] == "win"
        predicted = score(value["weights"], features)
        value["weights"] = [
            max(-5.0, min(5.0, w + 0.05 * (int(won) - predicted) * x))
            for w, x in zip(value["weights"], features)
        ]
        value["samples"] += 1
        value["observed_samples"] += 1
        value["wins" if won else "losses"] += 1
        value["liquidations"] += int(position["state"] == "liquidated")
        value["net_pnl_usd"] += position["net_pnl_usd"]
        value["updated_at"] = now
        self.db.execute(
            "INSERT INTO learner_memory_samples VALUES(?,?,?,?,?)",
            (intent, key, now, fingerprint, packed),
        )
        self._save(key, dimensions, value)
        return True

    def summary(self, policy, now):
        value = self.profile(policy, now)
        coins = {
            asset: {
                "samples": 0,
                "wins": 0,
                "losses": 0,
                "net_pnl_usd": 0.0,
                "cohorts": 0,
                "profiles": {},
            }
            for asset in ASSETS
        }
        for asset, raw in self.db.execute(
            "SELECT m.asset,c.value FROM learner_memory_cohorts m "
            "JOIN learner_cohorts c ON c.cohort=m.cohort"
        ):
            row = _checked_learner(json.loads(raw))
            result = coins[asset]
            for name in ("samples", "wins", "losses", "net_pnl_usd"):
                result[name] += row[name]
            result["cohorts"] += 1
        for key, asset, venue in self.db.execute(
            "SELECT identity,asset,venue FROM learner_memory_profiles"
        ):
            if asset not in ASSETS or venue not in VENUES:
                continue
            expected_policy = dict(
                policy,
                asset=asset,
                venue=venue,
                leverage=10 if venue == VENUES[0] else 1000,
                execution_model="linear-10x-v1"
                if venue == VENUES[0]
                else "exit50-proxy-v1",
            )
            if key != identity(expected_policy)[0]:
                # A different model/source/version remains archived, not
                # presented as a compatible current profile.
                continue
            row = self.profile(expected_policy, now)
            coins[asset]["profiles"][venue] = {
                "samples": row["samples"],
                "model_version": MODEL_VERSION,
                "updated_at": row["updated_at"],
            }
        unknown = self.db.execute(
            "SELECT COUNT(*) FROM learner_cohorts c WHERE NOT EXISTS "
            "(SELECT 1 FROM learner_memory_cohorts m WHERE m.cohort=c.cohort)"
        ).fetchone()[0]
        cursor, target = self.db.execute(
            "SELECT cursor,target FROM learner_memory_import WHERE singleton=1"
        ).fetchone()
        database = self.db.execute("PRAGMA database_list").fetchone()[2]
        return {
            "version": 1,
            "asset": policy["asset"],
            "profile": {
                "asset": policy["asset"],
                "venue": policy["venue"],
                "model_version": MODEL_VERSION,
                "samples": value["samples"],
                "updated_at": value["updated_at"],
            },
            "coins": coins,
            "storage": {
                "kind": "sqlite",
                "durable": bool(database),
                "name": "journal.sqlite3",
                "last_saved_at": value["updated_at"],
                "legacy_index_complete": cursor >= target,
                "unattributed_cohorts": unknown,
            },
            "scope": "Remembered modeled paper results; policy qualification remains separate. Legacy rows are retained.",
        }

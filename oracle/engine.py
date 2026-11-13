"""Prospective, source-bound shadow forecasts; no execution capability."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

from .feeds import validate_instrument
from .graphdb import history as graph_history
from .graphdb import market_shape, record_tick
from .store import Store, canonical
from .strategies import StrategySet
from .voting import MINIMUM_ACCURACY, Vote, aggregate

SCHEMA_VERSION = 2
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/ -]{0,199}\Z")


def number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


class OracleEngine:
    def __init__(
        self,
        path: str | Path,
        *,
        instrument: str = "SOL/USDC",
        horizon_seconds: int = 60,
        bar_seconds: int = 60,
        max_age: float = 15,
        minimum_resolved: int = 20,
        resolution_tolerance: float = 15,
    ) -> None:
        if any(
            type(x) is not int or not 1 <= x <= 86400
            for x in (horizon_seconds, bar_seconds, minimum_resolved)
        ):
            raise ValueError("invalid_oracle_policy")
        if any(
            not number(x) or not 0 < x <= 3600 for x in (max_age, resolution_tolerance)
        ):
            raise ValueError("invalid_oracle_policy")
        self.instrument = validate_instrument(instrument)
        self.horizon_seconds, self.bar_seconds = horizon_seconds, bar_seconds
        self.max_age, self.minimum_resolved = max_age, minimum_resolved
        self.minimum_vote_accuracy = MINIMUM_ACCURACY
        self.resolution_tolerance = resolution_tolerance
        self.strategy_set = StrategySet()
        implementation = hashlib.sha256()
        for name in (
            "engine.py",
            "store.py",
            "strategies.py",
            "voting.py",
            "graphdb.py",
        ):
            implementation.update(name.encode())
            implementation.update(Path(__file__).with_name(name).read_bytes())
        self.policy = {
            "schema_version": SCHEMA_VERSION,
            "instrument": self.instrument,
            "horizon_seconds": horizon_seconds,
            "implementation_sha256": implementation.hexdigest(),
            "bar_seconds": bar_seconds,
            "max_age": max_age,
            "minimum_resolved": minimum_resolved,
            "minimum_vote_accuracy": MINIMUM_ACCURACY,
            "vote_threshold_semantics": "strictly_greater_than_minimum",
            "resolution_tolerance": resolution_tolerance,
            "flat_band_bps": 0,
            "window": "all_resolved_in_this_policy",
            "strategies": [
                {k: row[k] for k in ("strategy_id", "version", "parameters")}
                for row in self.strategies()
            ],
        }
        self.policy_hash = hashlib.sha256(canonical(self.policy).encode()).hexdigest()
        self.store = Store(path, expected_policy=canonical(self.policy))
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT body FROM metadata WHERE key='policy'"
            ).fetchone()
            if existing is not None and existing[0] != canonical(self.policy):
                raise ValueError("archive_policy_mismatch_use_new_archive")
            db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('policy',?)",
                (canonical(self.policy),),
            )

    def strategies(self) -> list[dict]:
        return [
            {**entry, "instrument": self.instrument}
            for entry in self.strategy_set.catalog()
        ]

    def _clock(self, now: float | None) -> float:
        now = time.time() if now is None else now
        if not number(now) or now < 0:
            raise ValueError("invalid_clock")
        return float(now)

    def _observation(self, incoming: dict, now: float) -> dict:
        if not isinstance(incoming, dict):
            raise ValueError("invalid_observation")  # noqa: TRY004 - uniform validation boundary
        keys = ("source", "instrument", "venue", "kind", "event_id")
        if any(
            not isinstance(incoming.get(k), str) or not IDENTITY.fullmatch(incoming[k])
            for k in keys
        ):
            raise ValueError("invalid_observation_identity")
        if incoming["instrument"] != self.instrument:
            raise ValueError("instrument_not_supported")
        if any(
            not number(incoming.get(k)) for k in ("observed_at", "received_at", "price")
        ):
            raise ValueError("invalid_observation_numbers")
        if (
            not 0 <= incoming["observed_at"] <= incoming["received_at"] <= now
            or incoming["price"] <= 0
        ):
            raise ValueError("invalid_observation_times_or_price")
        result = {
            k: incoming[k] for k in (*keys, "observed_at", "received_at", "price")
        }
        for key in ("timestamp_semantics", "provider"):
            if key in incoming:
                if not isinstance(incoming[key], str) or not IDENTITY.fullmatch(
                    incoming[key]
                ):
                    raise ValueError("invalid_observation_provenance")
                result[key] = incoming[key]
        verified = incoming.get("upstream_recency_verified", False)
        if type(verified) is not bool:
            raise ValueError("invalid_observation_provenance")
        result["upstream_recency_verified"] = verified
        for key in ("bid", "ask", "base_usd_price", "quote_usd_price"):
            if key in incoming:
                if not number(incoming[key]) or incoming[key] <= 0:
                    raise ValueError("invalid_observation_provenance")
                result[key] = incoming[key]
        if "bid" in result and "ask" in result and result["bid"] > result["ask"]:
            raise ValueError("invalid_observation_spread")
        # Only public numeric provider identifiers may cross into the archive.
        if "provider_block_ids" in incoming:
            blocks = incoming["provider_block_ids"]
            if (
                not isinstance(blocks, dict)
                or len(blocks) > 2
                or any(
                    not isinstance(k, str)
                    or not IDENTITY.fullmatch(k)
                    or type(v) is not int
                    or v < 0
                    for k, v in blocks.items()
                )
            ):
                raise ValueError("invalid_observation_provenance")
            result["provider_block_ids"] = blocks
        return result

    def ingest(self, observation: dict, now: float | None = None) -> dict:
        now = self._clock(now)
        observation = self._observation(observation, now)
        scope = {k: observation[k] for k in ("source", "instrument", "venue", "kind")}
        raw_key = "observation:" + observation["event_id"]
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            saved_scope = db.execute(
                "SELECT body FROM metadata WHERE key='scope'"
            ).fetchone()
            if saved_scope and saved_scope[0] != canonical(scope):
                raise ValueError("archive_source_mismatch_use_new_archive")
            db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('scope',?)", (canonical(scope),)
            )
            existing = db.execute(
                "SELECT body FROM events WHERE event_key=?", (raw_key,)
            ).fetchone()
            if existing:
                saved = json.loads(existing[0])
                if {k: v for k, v in saved.items() if k != "received_at"} != {
                    k: v for k, v in observation.items() if k != "received_at"
                }:
                    raise ValueError("observation_identity_conflict")
                return {"schema_version": 1, "status": "duplicate", "accepted": False}
            self.store.event(db, "observation", raw_key, observation)
            previous = db.execute(
                "SELECT observed FROM observations ORDER BY observed DESC LIMIT 1"
            ).fetchone()
            if previous and observation["observed_at"] <= previous[0]:
                return {
                    "schema_version": 1,
                    "status": "out_of_order_archived",
                    "accepted": False,
                }
            db.execute(
                "INSERT INTO observations VALUES(?,?,?,?,?)",
                (
                    observation["event_id"],
                    observation["observed_at"],
                    observation["received_at"],
                    observation["price"],
                    canonical(observation),
                ),
            )
            self._resolve(db, observation, now)
            if (
                now - observation["observed_at"] <= self.max_age
                and now - observation["received_at"] <= self.max_age
            ):
                self._issue(db, observation, now)
        return {"schema_version": 1, "status": "accepted", "accepted": True}

    def _resolve(self, db: Any, observation: dict, now: float) -> None:
        pending = db.execute(
            "SELECT f.* FROM forecasts f LEFT JOIN resolutions r ON f.id=r.forecast WHERE r.forecast IS NULL AND f.target<=? ORDER BY f.target",
            (observation["observed_at"],),
        ).fetchall()
        for row in pending:
            timely = (
                observation["observed_at"] <= row["target"] + self.resolution_tolerance
                and observation["received_at"]
                <= row["target"] + self.resolution_tolerance
                and now <= row["target"] + self.resolution_tolerance
            )
            move = observation["price"] - row["reference"]
            outcome = (int(move > 0) - int(move < 0)) if timely else None
            hit = int(outcome == row["direction"]) if outcome is not None else None
            body = {
                "forecast_id": row["id"],
                "observation_id": observation["event_id"],
                "resolved_at": now,
                "outcome": outcome,
                "hit": hit,
                "reason": "resolved" if timely else "resolution_gap",
                "price": observation["price"] if timely else None,
            }
            db.execute(
                "INSERT INTO resolutions VALUES(?,?,?,?,?)",
                (row["id"], outcome, hit, now, canonical(body)),
            )
            self.store.event(db, "resolution", "resolution:" + row["id"], body)

    def _bars(self, db: Any, bucket: int) -> list[dict]:
        observations = db.execute(
            "SELECT observed,price FROM observations WHERE observed>=? AND observed<? ORDER BY observed",
            (max(0, bucket - 2048) * self.bar_seconds, bucket * self.bar_seconds),
        ).fetchall()
        groups: dict[int, list[float]] = {}
        for row in observations:
            groups.setdefault(int(row[0] // self.bar_seconds), []).append(row[1])
        # A missing bucket resets warm-up. No forward fill or synthetic volume.
        keys = []
        cursor = bucket - 1
        while cursor in groups and len(keys) < 2048:
            keys.append(cursor)
            cursor -= 1
        return [
            {
                "ts": k * self.bar_seconds,
                "open": groups[k][0],
                "high": max(groups[k]),
                "low": min(groups[k]),
                "close": groups[k][-1],
            }
            for k in reversed(keys)
        ]

    def _issue(self, db: Any, observation: dict, now: float) -> None:
        bucket = int(observation["observed_at"] // self.bar_seconds)
        key = "issued_bucket"
        previous = db.execute(
            "SELECT body FROM metadata WHERE key=?", (key,)
        ).fetchone()
        if previous and int(previous[0]) >= bucket:
            return
        features = self._bars(db, bucket)
        signals = self.strategy_set.predict(features)
        candidates, votes = [], []
        for signal in signals:
            strategy_id = signal["strategy_id"]
            resolved_row = db.execute(
                "SELECT count(r.hit),coalesce(sum(r.hit),0) FROM resolutions r JOIN forecasts f ON f.id=r.forecast WHERE f.strategy=? AND f.version=? AND r.resolved_at<=?",
                (strategy_id, signal["version"], now),
            ).fetchone()
            resolved, hits = resolved_row
            forecast_id = None
            if signal["direction"] is not None:
                identity = f"{self.policy_hash}:{strategy_id}:{bucket}"
                forecast_id = hashlib.sha256(identity.encode()).hexdigest()
                body = {
                    "schema_version": 1,
                    "forecast_id": forecast_id,
                    "source": observation["source"],
                    "instrument": observation["instrument"],
                    "venue": observation["venue"],
                    "kind": observation["kind"],
                    "strategy_id": strategy_id,
                    "version": signal["version"],
                    "parameters": signal["parameters"],
                    "parameter_overrides": signal["parameter_overrides"],
                    "parameter_rationale": signal["parameter_rationale"],
                    "card_sha256": signal["card_sha256"],
                    "direction": signal["direction"],
                    "issued_at": now,
                    "expires_at": now + self.horizon_seconds,
                    "horizon_seconds": self.horizon_seconds,
                    "reference_price": observation["price"],
                    "observation_id": observation["event_id"],
                    "feature_cutoff": features[-1]["ts"] + self.bar_seconds,
                    "policy_hash": self.policy_hash,
                    "tradable": False,
                    "prediction_semantics": signal["prediction_semantics"],
                    "upstream_recency_verified": observation[
                        "upstream_recency_verified"
                    ],
                }
                db.execute(
                    "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)",
                    (
                        forecast_id,
                        strategy_id,
                        signal["version"],
                        now,
                        now + self.horizon_seconds,
                        signal["direction"],
                        observation["price"],
                        canonical(body),
                    ),
                )
                self.store.event(db, "prediction", "prediction:" + forecast_id, body)
                votes.append(
                    Vote(
                        strategy_id,
                        signal["direction"],
                        hits,
                        resolved,
                        now,
                        now + self.horizon_seconds,
                    )
                )
            candidates.append(
                {
                    **signal,
                    "forecast_id": forecast_id,
                    "issued_at": now if forecast_id else None,
                    "expires_at": now + self.horizon_seconds if forecast_id else None,
                    "hits": hits,
                    "resolved": resolved,
                    "accuracy_percent": hits * 100 / resolved if resolved else None,
                }
            )

        aggregate_snapshot = aggregate(
            votes,
            now=now,
            minimum_resolved=self.minimum_resolved,
            minimum_accuracy=self.minimum_vote_accuracy,
        )
        included = {
            row["strategy_id"]: row["weight"] for row in aggregate_snapshot["included"]
        }
        excluded = {
            row["strategy_id"]: row["reason"] for row in aggregate_snapshot["excluded"]
        }
        graph_predictions = [
            {
                **candidate,
                "vote_eligible": candidate["strategy_id"] in included,
                "vote_weight": included.get(candidate["strategy_id"]),
                "reason": candidate["reason"]
                or excluded.get(candidate["strategy_id"]),
            }
            for candidate in candidates
        ]
        aggregate_snapshot.update(
            {
                "instrument": self.instrument,
                "as_of": now,
                "horizon_seconds": self.horizon_seconds,
                "percentage_semantics": "signed_weighted_vote_balance_not_probability",
                "tradable": False,
            }
        )
        record_tick(
            db,
            {
                "tick_id": hashlib.sha256(
                    f"{self.policy_hash}:graphdb:{self.instrument}:{bucket}".encode()
                ).hexdigest(),
                "instrument": self.instrument,
                "policy_hash": self.policy_hash,
                "bar_index": bucket,
                "chart_time": int(observation["observed_at"]),
                "observed_at": observation["observed_at"],
                "received_at": observation["received_at"],
                "price": observation["price"],
                "observation_id": observation["event_id"],
                "market_shape": market_shape(features),
                "aggregate": aggregate_snapshot,
            },
            graph_predictions,
        )
        db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (key, str(bucket)))

    def market(self, now: float | None = None) -> dict:
        now = self._clock(now)
        with self.store.connection() as db:
            row = db.execute(
                "SELECT body FROM observations ORDER BY observed DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return {
                "schema_version": 1,
                "status": "unavailable",
                "instrument": self.instrument,
                "reason": "no_market_data",
                "tradable": False,
            }
        observation = json.loads(row[0])
        age = now - observation["observed_at"]
        current = (
            0 <= age <= self.max_age
            and 0 <= now - observation["received_at"] <= self.max_age
        )
        return {
            "schema_version": 1,
            "status": "available" if current else "unavailable",
            "instrument": self.instrument,
            "reason": None if current else "stale_market_data",
            "age_seconds": age,
            "tradable": False,
            "observation": observation,
            "limitations": []
            if observation["upstream_recency_verified"]
            else ["upstream_event_time_unknown"],
        }

    def predictions(self, now: float | None = None) -> dict:
        now = self._clock(now)
        market = self.market(now)
        rows, votes = [], []
        with self.store.connection() as db:
            for entry in self.strategies():
                forecast = db.execute(
                    "SELECT body FROM forecasts WHERE strategy=? AND version=? AND issued<=? ORDER BY issued DESC LIMIT 1",
                    (entry["strategy_id"], entry["version"], now),
                ).fetchone()
                counts = db.execute(
                    "SELECT count(r.hit),coalesce(sum(r.hit),0) FROM resolutions r JOIN forecasts f ON f.id=r.forecast WHERE f.strategy=? AND f.version=? AND r.resolved_at<=?",
                    (entry["strategy_id"], entry["version"], now),
                ).fetchone()
                resolved, hits = counts
                body = (
                    json.loads(forecast[0])
                    if forecast
                    else {
                        "strategy_id": entry["strategy_id"],
                        "instrument": self.instrument,
                        "direction": None,
                        "reason": "warmup_required",
                    }
                )
                body.update(
                    {
                        "hits": hits,
                        "resolved": resolved,
                        "confidence_percent": hits * 100 / resolved
                        if resolved
                        else None,
                        "confidence_semantics": "historical_directional_accuracy_not_profit_probability",
                        "needs_review": resolved >= self.minimum_resolved
                        and hits / resolved <= MINIMUM_ACCURACY,
                        "suggested_next_step": "versioned_shadow_challenger"
                        if resolved >= self.minimum_resolved
                        and hits / resolved <= MINIMUM_ACCURACY
                        else None,
                    }
                )
                rows.append(body)
                if forecast:
                    votes.append(
                        Vote(
                            entry["strategy_id"],
                            body["direction"],
                            hits,
                            resolved,
                            body["issued_at"],
                            body["expires_at"],
                        )
                    )
        result = aggregate(
            votes,
            now=now,
            minimum_resolved=self.minimum_resolved,
            minimum_accuracy=self.minimum_vote_accuracy,
        )
        if market["status"] != "available":
            result.update(
                {
                    "status": "unavailable",
                    "signal": None,
                    "balance_percent": None,
                    "reason": market["reason"],
                }
            )
        return {
            "schema_version": 1,
            "as_of": now,
            "instrument": self.instrument,
            "status": result["status"],
            "signal": result["signal"],
            "horizon_seconds": self.horizon_seconds,
            "policy_hash": self.policy_hash,
            "tradable": False,
            "market": market,
            "strategies": rows,
            "aggregate": result,
            "percentage_semantics": "signed_weighted_vote_balance_not_probability",
            "limitations": market.get("limitations", []),
        }

    def history(self, limit: int = 100, after: int = 0) -> dict:
        return {**self.store.history(limit, after), "instrument": self.instrument}

    def graph_history(self, limit: int = 240) -> dict:
        with self.store.connection() as db:
            return graph_history(db, self.instrument, limit)

    def status(self) -> dict:
        with self.store.connection() as db:
            tables = {
                row[0]
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            counts = {
                table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in (
                    "events",
                    "observations",
                    "forecasts",
                    "resolutions",
                    "graphdb_ticks",
                    "graphdb_predictions",
                )
                if table in tables
            }
            counts.setdefault("graphdb_ticks", 0)
            counts.setdefault("graphdb_predictions", 0)
        return {
            "schema_version": 1,
            "instrument": self.instrument,
            "policy_hash": self.policy_hash,
            "policy": self.policy,
            "archive": str(self.store.path),
            "counts": counts,
            "mode": "shadow_reference",
            "tradable": False,
            "automatic_parameter_changes": False,
            "resolution_semantics": "endpoint_direction_zero_move_is_flat_missing_target_is_unresolved",
        }

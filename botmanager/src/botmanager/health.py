"""Independent health dimensions and a durable, bounded alert projection."""

from __future__ import annotations

import json
import math
import sqlite3
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .domain import ManagerError, canonical, fingerprint
from .store import data_home


def _finite(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def health_snapshot(runtime: Mapping[str, Any], *, now: float) -> dict[str, Any]:
    """Do not infer input freshness, profit or finality from a heartbeat."""
    heartbeat = runtime.get("heartbeat")
    evaluated = runtime.get("evaluated")
    cp = runtime.get("checkpoint") or {}
    data = runtime.get("input") or {}
    source = data.get("prospective")
    running = runtime.get("desired") == "running"
    age = max(0.0, now - heartbeat) if _finite(heartbeat) else None
    process = (
        "stopped"
        if not running
        else "healthy"
        if age is not None and age < 15
        else "stale"
    )
    if running and runtime.get("observed") == "pending" and heartbeat is None:
        process = "queued"
    if source is None:
        input_state, input_reason = "reference", "historical_input_is_not_live"
    else:
        latest = source.get("latest_observed")
        input_state = source.get("health", "unavailable")
        max_age = data.get("descriptor", {}).get("max_source_age_s")
        if not _finite(latest) or not _finite(max_age):
            input_state = "unavailable"
        elif now - latest > max_age:
            input_state = "source_stale"
        input_reason = "accepted_observation_clock"
    tick = runtime.get("tick_started")
    evaluation = (
        "stalled"
        if running and _finite(tick) and now - tick >= 15
        else "completed"
        if _finite(evaluated)
        else "unavailable"
    )
    pnl = cp.get("realized_net_pnl_quote")
    result = "unavailable" if not _finite(pnl) else "loss" if pnl < 0 else "measured"
    blockers = []
    if process == "stale":
        blockers.append("heartbeat_stale")
    if input_state not in (
        "reference",
        "available",
        "waiting_for_completed_bin",
        "waiting_for_observations",
    ):
        blockers.append(input_state)
    observed, reason = runtime.get("observed"), runtime.get("reason")
    if running and observed in ("recovering", "failed", "blocked"):
        if reason in (
            "worker_exited",
            "worker_spawn_failed",
            "tick_stalled",
            "heartbeat_stale",
            "corrupt_checkpoint",
        ):
            blockers.append(reason)
        if observed in ("failed", "blocked"):
            blockers.append("runtime_" + observed)
    if reason == "tick_stalled" and observed in ("recovering", "failed", "blocked"):
        evaluation = "stalled"
    if evaluation == "stalled":
        blockers.append("evaluation_stalled")
    return {
        "schema_version": 1,
        "lifecycle": {"observed": observed, "reason": reason},
        "process": {"state": process, "heartbeat_age_seconds": age},
        "input": {"state": input_state, "reason": input_reason},
        "evaluation": {"state": evaluation, "last_completed_at": evaluated},
        "results": {
            "state": result,
            "reason": "valid_losing_result"
            if result == "loss"
            else "measurement_not_available"
            if result == "unavailable"
            else "canonical_reference_result",
        },
        "evidence": {"state": "reference_only", "live_eligible": False},
        "submission": {"state": "not_applicable", "reason": "paper_only"},
        "exposure_quote": cp.get("exposure_quote"),
        "exposure_reason": None
        if _finite(cp.get("exposure_quote"))
        else "exposure_not_measured",
        "blockers": blockers,
        "performance_warning": {
            "available": False,
            "reason": "compatible_baseline_and_sample_required",
        },
    }


class HealthStore:
    """Alerts are derived; accepted controls and financial journals never rotate."""

    def __init__(self, home: Path | None = None):
        self.home = Path(home) if home is not None else data_home()
        self.path = self.home / "health.sqlite3"

    @contextmanager
    def connection(self, write=False):
        db = None
        try:
            if write:
                self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
            db = sqlite3.connect(
                self.path if write else self.path.absolute().as_uri() + "?mode=ro",
                uri=not write,
                timeout=1,
            )
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            if write:
                self.path.chmod(0o600)
                db.execute(
                    "CREATE TABLE IF NOT EXISTS alerts (sequence INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, bot_id TEXT NOT NULL, runtime_id TEXT NOT NULL, code TEXT NOT NULL, state TEXT NOT NULL, first_at REAL NOT NULL, last_at REAL NOT NULL, notified_at REAL NOT NULL, occurrences INTEGER NOT NULL, resolved_at REAL, evidence TEXT NOT NULL)"
                )
            yield db
            if write:
                db.commit()
        except (sqlite3.Error, OSError) as exc:
            raise ManagerError(
                "store_unavailable", "Health journal is unavailable.", 4
            ) from exc
        finally:
            if db is not None:
                db.close()

    def observe(self, row, *, now, cooldown=300):
        snapshot = health_snapshot(row, now=now)
        codes = set(snapshot["blockers"])
        bot_id, runtime_id = row["bot_id"], row["runtime_id"]
        evidence_body = {
            "health": snapshot,
            "source": row["input"]["identity"],
            "generation": row["generation"],
            "origin": {
                "runtime_id": runtime_id,
                "source": row["input"]["identity"],
                "observed": row.get("observed"),
                "reason": row.get("reason"),
                "generation": row["generation"],
                "at": now,
            },
        }
        evidence = canonical(evidence_body)
        with self.connection(True) as db:
            for code in codes:
                evidence = canonical(evidence_body)
                key = fingerprint([bot_id, runtime_id, code])
                old = db.execute("SELECT * FROM alerts WHERE key=?", (key,)).fetchone()
                if old is None:
                    db.execute(
                        "INSERT INTO alerts(key,bot_id,runtime_id,code,state,first_at,last_at,notified_at,occurrences,evidence) VALUES (?,?,?,?,'active',?,?,?,?,?)",
                        (key, bot_id, runtime_id, code, now, now, now, 1, evidence),
                    )
                else:
                    previous = json.loads(old["evidence"])
                    evidence = canonical(
                        {
                            **evidence_body,
                            "origin": previous.get("origin", evidence_body["origin"]),
                        }
                    )
                    notified = (
                        now
                        if old["state"] == "resolved"
                        or now - old["notified_at"] >= cooldown
                        else old["notified_at"]
                    )
                    db.execute(
                        "UPDATE alerts SET state='active',last_at=?,notified_at=?,occurrences=occurrences+1,resolved_at=NULL,evidence=? WHERE key=?",
                        (now, notified, evidence, key),
                    )
                    if old["state"] == "resolved" or notified != old["notified_at"]:
                        db.execute(
                            "UPDATE alerts SET sequence=(SELECT coalesce(max(sequence),0)+1 FROM alerts) WHERE key=?",
                            (key,),
                        )
            for old in db.execute(
                "SELECT key,code,runtime_id,evidence FROM alerts WHERE bot_id=? AND state='active'",
                (bot_id,),
            ).fetchall():
                if old["code"] not in codes or old["runtime_id"] != runtime_id:
                    failure_codes = {
                        "worker_exited",
                        "worker_spawn_failed",
                        "tick_stalled",
                        "runtime_failed",
                        "runtime_blocked",
                        "corrupt_checkpoint",
                    }
                    if (
                        old["runtime_id"] == runtime_id
                        and old["code"] in failure_codes
                        and row.get("desired") == "running"
                        and (
                            row.get("observed")
                            in ("pending", "recovering", "failed", "blocked")
                            or row.get("pid") is None
                        )
                    ):
                        # A new claim's synthetic heartbeat is not proof that its
                        # replacement process has actually taken ownership.
                        continue
                    previous = json.loads(old["evidence"])
                    resolution = canonical(
                        {
                            **evidence_body,
                            "origin": previous.get("origin", evidence_body["origin"]),
                        }
                    )
                    db.execute(
                        "UPDATE alerts SET state='resolved',resolved_at=?,last_at=?,evidence=? WHERE key=?",
                        (now, now, resolution, old["key"]),
                    )
                    db.execute(
                        "UPDATE alerts SET sequence=(SELECT coalesce(max(sequence),0)+1 FROM alerts) WHERE key=?",
                        (old["key"],),
                    )
        return snapshot

    def page(self, *, bot_id=None, after=0, limit=100):
        if (
            type(after) is not int
            or after < 0
            or type(limit) is not int
            or not 1 <= limit <= 1000
        ):
            raise ManagerError(
                "invalid_input", "A valid cursor and limit are required."
            )
        rows = []
        if self.path.exists():
            with self.connection() as db:
                rows = [
                    dict(r)
                    for r in db.execute(
                        "SELECT * FROM alerts WHERE sequence>? AND (? IS NULL OR bot_id=?) ORDER BY sequence LIMIT ?",
                        (after, bot_id, bot_id, limit + 1),
                    )
                ]
        more = len(rows) > limit
        rows = rows[:limit]
        for row in rows:
            row["evidence"] = json.loads(row["evidence"])
        return {
            "schema_version": 1,
            "alerts": rows,
            "next_after": rows[-1]["sequence"] if rows else after,
            "has_more": more,
        }

    def pause(self, row, operation, request_id):
        from .ledger import RuntimeLedger
        from .mutations import request_identity

        request_id = request_identity(request_id)
        if row["spec"]["strategy_id"] not in ("grid", "dca"):
            raise ManagerError(
                "capability_unavailable",
                "Entry pause requires a separable entry/exit strategy model.",
                3,
            )
        if operation not in ("pause", "resume"):
            raise ManagerError("invalid_input", "Unknown entry operation.")
        binding = {
            "bot_id": row["bot_id"],
            "runtime_id": row["runtime_id"],
            "config_hash": row["spec"]["config_hash"],
            "operation": operation,
        }
        ledger = RuntimeLedger(self.home)
        with ledger.connection(True) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS entry_controls (request_id TEXT PRIMARY KEY, binding TEXT NOT NULL, receipt TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS entry_pauses (bot_id TEXT PRIMARY KEY, runtime_id TEXT NOT NULL, paused INTEGER NOT NULL)"
            )
            old = db.execute(
                "SELECT * FROM entry_controls WHERE request_id=?", (request_id,)
            ).fetchone()
            if old:
                if old["binding"] != canonical(binding):
                    raise ManagerError(
                        "identity_conflict", "Control request binding changed."
                    )
                return json.loads(old["receipt"])
            current = db.execute(
                "SELECT * FROM runs WHERE bot_id=?", (row["bot_id"],)
            ).fetchone()
            if (
                not current
                or current["runtime_id"] != row["runtime_id"]
                or current["generation"] != row["generation"]
            ):
                raise ManagerError(
                    "stale_generation",
                    "The active owner changed before control acceptance.",
                    3,
                )
            paused = operation == "pause"
            handoff = current["desired"] == "running" and current["observed"] in (
                "running",
                "waiting",
                "pending",
                "recovering",
            )
            generation = current["generation"] + 1
            receipt = {
                "schema_version": 1,
                "request_id": request_id,
                **binding,
                "owner_generation": generation,
                "outcome": "acknowledged",
                "reason": "entry_policy_persisted_and_prior_generation_revoked",
                "entries_paused": paused,
                "exits_continue": handoff,
                "exit_owner_state": "handoff" if handoff else current["observed"],
                "safe_to_retry": False,
            }
            db.execute(
                "INSERT OR REPLACE INTO entry_pauses VALUES (?,?,?)",
                (row["bot_id"], row["runtime_id"], int(paused)),
            )
            db.execute(
                "UPDATE runs SET generation=?,observed=CASE WHEN desired='running' AND observed IN ('running','waiting','pending','recovering') THEN 'recovering' ELSE observed END,reason=CASE WHEN desired='running' AND observed IN ('running','waiting','pending','recovering') THEN ? ELSE reason END WHERE bot_id=?",
                (generation, "entry_" + operation + "_handoff", row["bot_id"]),
            )
            ledger._event(
                db, {**dict(current), "generation": generation}, operation + ".entries"
            )
            db.execute(
                "INSERT INTO entry_controls VALUES (?,?,?)",
                (request_id, canonical(binding), canonical(receipt)),
            )
        return receipt


def entries_paused(home, bot_id, runtime_id):
    from .ledger import RuntimeLedger

    store = RuntimeLedger(home)
    if not store.path.exists():
        return False
    with store.connection() as db:
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entry_pauses'"
        ).fetchone():
            return False
        row = db.execute(
            "SELECT * FROM entry_pauses WHERE bot_id=?", (bot_id,)
        ).fetchone()
        return bool(row and row["runtime_id"] == runtime_id and row["paused"])


def rotate_diagnostics(path, *, max_bytes=1_000_000, keep=3):
    """Rotate only the explicitly selected diagnostic log, never evidence files."""
    path = Path(path)
    if path.name != "diagnostics.log" or path.is_symlink():
        raise ManagerError("invalid_input", "Only the diagnostic log may rotate.")
    if not path.exists() or path.stat().st_size <= max_bytes:
        return
    for index in range(keep, 0, -1):
        source = path if index == 1 else path.with_name(path.name + f".{index - 1}")
        target = path.with_name(path.name + f".{index}")
        if source.exists():
            source.replace(target)

"""Durable external trial identities observed from the existing F5 owner.

Registration does not create a manager draft or start a worker. The original
batch and forward databases remain the only evidence for lifecycle observations.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

SCHEMA_VERSION = 1
APPLICATION_ID = 0x45524331
MAX_CELLS = 1_000_000
SAFE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
INTERVALS = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "6h": 360, "1d": 1440}
CELL_STATES = {
    "pending",
    "running",
    "completed",
    "partial",
    "missing",
    "unsupported",
    "failed",
}


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _path(home: str | Path) -> Path:
    return Path(home).expanduser().absolute() / "registrations.sqlite3"


def _read(path: Path) -> sqlite3.Connection:
    if path.is_symlink() or not path.is_file():
        raise ValueError("evidence_unavailable")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


@contextmanager
def _ledger(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("registration_store_unavailable")
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if version == 0 and app_id == 0 and not tables:
                db.execute(
                    "CREATE TABLE registration (bot_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, identity TEXT NOT NULL, created REAL NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE observation (bot_id TEXT PRIMARY KEY REFERENCES registration(bot_id), body TEXT NOT NULL, observed REAL NOT NULL)"
                )
                db.execute(
                    "CREATE INDEX registration_batch ON registration(batch_id,bot_id)"
                )
                for action in ("UPDATE", "DELETE"):
                    db.execute(
                        f"CREATE TRIGGER registration_no_{action.lower()} BEFORE {action} ON registration BEGIN SELECT RAISE(ABORT,'immutable registration'); END"
                    )
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            elif version != SCHEMA_VERSION or app_id != APPLICATION_ID:
                raise ValueError("registration_store_incompatible")
            path.chmod(0o600)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


def _forward(path: Path, batch_id: str) -> tuple[dict[tuple[str, str, int], dict], str]:
    if not path.is_file():
        return {}, "forward_evidence_missing"
    try:
        with closing(_read(path)) as db, db:
            rows = db.execute(
                """
                SELECT t.id,t.asset,t.label,t.minutes,count(c.bar) AS calls,
                       max(c.issued) AS last_issued,max(c.finish) AS last_target,
                       count(c.outcome) AS resolved,
                       coalesce(sum(CASE WHEN c.outcome=c.prediction THEN 1 ELSE 0 END),0) AS hits
                FROM trial t LEFT JOIN call c ON c.trial=t.id
                WHERE t.label LIKE ? GROUP BY t.id
            """,
                (f"f5:{batch_id}:%",),
            ).fetchall()
        evidence: dict[tuple[str, str, int], dict] = {}
        for row in rows:
            body = dict(row)
            if (
                type(body["asset"]) is not str
                or not SAFE_NAME.fullmatch(body["asset"])
                or type(body["label"]) is not str
                or len(body["label"]) > 250
                or type(body["minutes"]) is not int
                or body["minutes"] not in INTERVALS.values()
                or type(body["id"]) is not str
                or len(body["id"]) > 200
                or not all(
                    type(body[k]) is int and body[k] >= 0
                    for k in ("calls", "resolved", "hits")
                )
                or body["hits"] > body["resolved"]
                or body["resolved"] > body["calls"]
            ):
                raise ValueError
            for field in ("last_issued", "last_target"):
                value = body[field]
                if value is not None and (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError
            key = (body["asset"], body["label"], body["minutes"])
            if key not in evidence or (body["last_issued"] or -1) > (
                evidence[key]["last_issued"] or -1
            ):
                evidence[key] = body
        return evidence, "available"
    except (OSError, ValueError, sqlite3.Error):
        return {}, "forward_evidence_unavailable"


def _identity(row: sqlite3.Row, batch_id: str, directory: Path, code_id: str) -> dict:
    if (
        type(row["id"]) is not int
        or row["id"] < 1
        or any(
            type(row[k]) is not str or not SAFE_NAME.fullmatch(row[k])
            for k in ("asset", "strategy")
        )
        or row["interval"] not in INTERVALS
        or row["horizon"] not in ("short", "medium", "long")
        or row["state"] not in CELL_STATES
    ):
        raise ValueError("batch_cell_invalid")
    bot_id = str(uuid5(NAMESPACE_URL, f"solmargintrader:f5:{batch_id}:{row['id']}"))
    label = f"f5:{batch_id}:{row['strategy']}:{row['interval']}:{row['horizon']}"
    return {
        "schema_version": SCHEMA_VERSION,
        "bot_id": bot_id,
        "display_name": f"{row['asset']} {row['strategy']} {row['interval']} {row['horizon']}",
        "source": "f5_batch",
        "owner": "soltui.f5_batch",
        "batch_id": batch_id,
        "cell_id": row["id"],
        "strategy_id": row["strategy"],
        "strategy_version": code_id,
        "asset": row["asset"],
        "quote_currency": "USD",
        "interval": row["interval"],
        "preset_horizon": row["horizon"],
        "mode": "paper",
        "armed": False,
        "batch_directory": str(directory),
        "backtest_cell_ref": {"batch_id": batch_id, "cell_id": row["id"]},
        "forward_trial_label": label,
    }


def _observation(
    row: sqlite3.Row, identity: dict, forward: dict, forward_status: str, now: float
) -> dict:
    state = row["state"]
    score = row["score"]
    if score is not None and (
        type(score) not in (int, float) or not math.isfinite(score)
    ):
        raise ValueError("batch_score_invalid")
    selected = None
    if row["selected"] is not None:
        try:
            selected = json.loads(row["selected"])
            if (
                not isinstance(selected, dict)
                or selected.get("name") != identity["strategy_id"]
                or not isinstance(selected.get("params"), dict)
            ):
                raise ValueError
            _json(selected)
        except (ValueError, TypeError):
            raise ValueError("selected_configuration_invalid") from None
    trial = forward.get(
        (
            identity["asset"],
            identity["forward_trial_label"],
            INTERVALS[identity["interval"]],
        )
    )
    lifecycle, observed, reason = "backtest", "pending", "backtest_not_completed"
    if state == "running":
        observed, reason = "backtesting", "backtest_in_progress"
    elif state in ("missing", "unsupported", "failed"):
        observed, reason = "blocked", f"backtest_{state}"
    elif state in ("completed", "partial"):
        if selected is None or score is None:
            observed, reason = "blocked", "backtest_evidence_incomplete"
        else:
            observed, reason = "backtest_completed", "forward_evidence_missing"
            if trial is not None and trial["calls"] > 0:
                issued = trial["last_issued"]
                if issued is None or issued > now:
                    observed, reason = "blocked", "forward_evidence_invalid_clock"
                else:
                    lifecycle = "forward"
                    age = now - issued
                    fresh = age <= max(120, INTERVALS[identity["interval"]] * 60 * 3)
                    observed = (
                        "forecast_recorded" if fresh else "stale_forward_evidence"
                    )
                    reason = (
                        "prospective_calls_observed" if fresh else "forward_calls_stale"
                    )
            elif trial is not None:
                reason = "forward_trial_has_no_calls"
    return {
        "lifecycle": lifecycle,
        "observed_state": observed,
        "reason": reason,
        "backtest": {
            "state": state,
            "score": score,
            "selected_configuration": selected,
            "configuration_hash": hashlib.sha256(_json(selected).encode()).hexdigest()
            if selected is not None
            else None,
            "selection_is_independent_validation": False,
        },
        "forward": {
            "status": "observed" if trial is not None else forward_status,
            "trial_id": trial["id"] if trial else None,
            "calls": trial["calls"] if trial else None,
            "resolved": trial["resolved"] if trial else None,
            "hits": trial["hits"] if trial else None,
            "last_issued": trial["last_issued"] if trial else None,
            "last_target": trial["last_target"] if trial else None,
            "accuracy_percent": 100 * trial["hits"] / trial["resolved"]
            if trial and trial["resolved"]
            else None,
        },
        "runtime_running": None,
        "runtime_reason": "owner_liveness_not_observed",
        "capabilities": ["inspect"],
        "automatic_promotion": False,
        "live_ready": False,
    }


def sync_registrations(home: str | Path, batch_id: str, batch_root: str | Path) -> dict:
    """Idempotently register every frozen cell and refresh owner-derived evidence."""
    if type(batch_id) is not str or re.fullmatch(r"[0-9a-f]{32}", batch_id) is None:
        raise ValueError("invalid_batch_id")
    directory = Path(batch_root).expanduser().absolute() / batch_id
    path = directory / "batch.sqlite3"
    now = time.time()
    try:
        with closing(_read(path)) as source, source:
            source.execute("BEGIN")
            meta = {
                row[0]: json.loads(row[1])
                for row in source.execute(
                    "SELECT key,value FROM meta WHERE key IN ('id','code_id')"
                )
            }
            if (
                meta.get("id") != batch_id
                or type(meta.get("code_id")) is not str
                or re.fullmatch(r"[0-9a-f]{64}", meta["code_id"]) is None
            ):
                raise ValueError("batch_identity_invalid")
            count = source.execute("SELECT count(*) FROM cell").fetchone()[0]
            if not 1 <= count <= MAX_CELLS:
                raise ValueError("batch_cell_count_invalid")
            rows = source.execute(
                "SELECT id,asset,interval,strategy,horizon,state,selected,score FROM cell ORDER BY id"
            ).fetchall()
        # Release the owner's read lock before updating a potentially large
        # external matrix. Registration must not stall the batch worker's writes.
        forward, forward_status = _forward(directory / "forward.sqlite3", batch_id)
        added = 0
        states: dict[str, int] = {}
        with _ledger(_path(home)) as target:
            for row in rows:
                identity = _identity(row, batch_id, directory, meta["code_id"])
                encoded = _json(identity)
                existing = target.execute(
                    "SELECT identity FROM registration WHERE bot_id=?",
                    (identity["bot_id"],),
                ).fetchone()
                if existing is not None and existing[0] != encoded:
                    raise ValueError("registration_identity_conflict")
                if existing is None:
                    target.execute(
                        "INSERT INTO registration VALUES(?,?,?,?)",
                        (identity["bot_id"], batch_id, encoded, now),
                    )
                    added += 1
                observation = _observation(row, identity, forward, forward_status, now)
                target.execute(
                    "INSERT OR REPLACE INTO observation VALUES(?,?,?)",
                    (identity["bot_id"], _json(observation), now),
                )
                states[observation["observed_state"]] = (
                    states.get(observation["observed_state"], 0) + 1
                )
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "available",
            "batch_id": batch_id,
            "registered": count,
            "added": added,
            "observed_states": states,
            "forward_evidence_status": forward_status,
            "observed_at": now,
            "source": "f5_batch",
            "owner": "soltui.f5_batch",
            "live_ready": False,
        }
    except (OSError, sqlite3.Error, json.JSONDecodeError):
        raise ValueError("registration_evidence_unavailable") from None


def read_registrations(
    home: str | Path, *, limit: int = 100, after: str = "", batch_id: str | None = None
) -> dict:
    """Read a bounded external inventory; absence never creates a store."""
    if (
        type(limit) is not int
        or not 1 <= limit <= 1000
        or type(after) is not str
        or len(after) > 36
    ):
        raise ValueError("invalid_registration_page")
    if batch_id is not None and (
        type(batch_id) is not str or re.fullmatch(r"[0-9a-f]{32}", batch_id) is None
    ):
        raise ValueError("invalid_batch_id")
    try:
        with closing(_read(_path(home))) as db:
            if (
                db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
            ):
                raise ValueError
            where, args = "r.bot_id>?", [after]
            if batch_id is not None:
                where += " AND r.batch_id=?"
                args.append(batch_id)
            rows = db.execute(
                f"SELECT r.identity,r.created,o.body,o.observed FROM registration r LEFT JOIN observation o ON o.bot_id=r.bot_id WHERE {where} ORDER BY r.bot_id LIMIT ?",
                (*args, limit + 1),
            ).fetchall()
            total = db.execute(
                "SELECT count(*) FROM registration"
                + (" WHERE batch_id=?" if batch_id is not None else ""),
                (batch_id,) if batch_id is not None else (),
            ).fetchone()[0]
        more = len(rows) > limit
        bots = []
        for row in rows[:limit]:
            identity = json.loads(row["identity"])
            if (
                not isinstance(identity, dict)
                or identity.get("schema_version") != SCHEMA_VERSION
                or identity.get("source") != "f5_batch"
                or identity.get("owner") != "soltui.f5_batch"
                or identity.get("mode") != "paper"
                or identity.get("armed") is not False
                or re.fullmatch(r"[0-9a-f-]{36}", identity.get("bot_id", "")) is None
            ):
                raise ValueError
            observation = (
                json.loads(row["body"])
                if row["body"]
                else {
                    "lifecycle": "unknown",
                    "observed_state": "unknown",
                    "live_ready": False,
                }
            )
            if (
                not isinstance(observation, dict)
                or observation.get("live_ready") is not False
                or any(key in observation for key in identity)
            ):
                raise ValueError
            age = (
                max(0, time.time() - row["observed"])
                if row["observed"] is not None
                else None
            )
            bots.append(
                {
                    **identity,
                    **observation,
                    "registered_at": row["created"],
                    "observed_at": row["observed"],
                    "observation_age_seconds": age,
                    "registration_observation_stale": age is None or age > 120,
                }
            )
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "available",
            "source": "f5_batch",
            "owner": "soltui.f5_batch",
            "bots": bots,
            "total": total,
            "next_after": bots[-1]["bot_id"] if more else None,
            "read_only": True,
            "live_ready": False,
        }
    except (OSError, ValueError, sqlite3.Error, TypeError, KeyError):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "registration_store_unavailable",
            "bots": [],
            "total": None,
            "next_after": None,
            "read_only": True,
            "live_ready": False,
        }

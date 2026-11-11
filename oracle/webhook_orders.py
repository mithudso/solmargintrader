"""Durable Coinbase webhook dispatch; Oracle votes do not qualify these orders."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

TERMINAL = {"FILLED", "CANCELLED", "CANCELED", "EXPIRED", "FAILED", "REJECTED"}
BLOCKING = ("planning", "submitting", "unknown", "pending")


@contextmanager
def database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Create privately before sqlite opens it; never accept a symlink for order state.
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    os.chmod(path, 0o600)
    with closing(sqlite3.connect(path, timeout=5)) as db:
        db.row_factory = sqlite3.Row
        with db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS signals (event_id TEXT PRIMARY KEY, digest TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, timestamp INTEGER NOT NULL, status TEXT NOT NULL)"
            )
            columns = {r[1] for r in db.execute("PRAGMA table_info(signals)")}
            for name, kind in (
                ("mode", "TEXT DEFAULT 'inbox'"),
                ("plan", "TEXT"),
                ("result", "TEXT"),
                ("client_order_id", "TEXT"),
                ("order_id", "TEXT"),
                ("portfolio_id", "TEXT"),
            ):
                if name not in columns:
                    db.execute(f"ALTER TABLE signals ADD COLUMN {name} {kind}")
        yield db


def records(path: Path, limit: int = 50) -> list[dict]:
    if not 1 <= limit <= 1000:
        raise ValueError("invalid_limit")
    if not path.exists():
        return []
    with database(path) as db:
        return [
            dict(r)
            for r in db.execute(
                "SELECT event_id,symbol,side,timestamp,status,mode,plan,result,client_order_id,order_id,portfolio_id FROM signals ORDER BY rowid DESC LIMIT ?",
                (limit,),
            )
        ]


def _update(path: Path, event_id: str, status: str, **fields):
    if set(fields) - {"plan", "result", "client_order_id", "order_id"}:
        raise ValueError("invalid_state_fields")
    names = ["status", *fields]
    values = [status, *fields.values(), event_id]
    with database(path) as db, db:
        db.execute(
            "UPDATE signals SET "
            + ",".join(f"{n}=?" for n in names)
            + " WHERE event_id=?",
            values,
        )


def recover_planning(path: Path):
    """Call only after acquiring the exclusive owner lock on service startup."""
    with database(path) as db, db:
        db.execute(
            "UPDATE signals SET status='refused',result=? WHERE status='planning'",
            (json.dumps({"reason": "interrupted_before_submission"}),),
        )


def _reconcile(path, row, venue):
    plan = json.loads(row["plan"])
    try:
        order = (
            venue.get(row["order_id"])
            if row["order_id"]
            else venue.find(
                row["client_order_id"], plan["product_id"], plan["portfolio_id"]
            )
        )
        if not isinstance(order, dict) or not order:
            return "unknown"
        if (
            not order.get("order_id")
            or order.get("product_id") != plan["product_id"]
            or order.get("side") != plan["side"]
            or (row["order_id"] and order["order_id"] != row["order_id"])
            or (
                not row["order_id"]
                and order.get("client_order_id") != row["client_order_id"]
            )
            or (
                order.get("client_order_id") is not None
                and order["client_order_id"] != row["client_order_id"]
            )
        ):
            return "unknown"
        state = "complete" if order.get("status") in TERMINAL else "pending"
        _update(
            path,
            row["event_id"],
            state,
            order_id=order["order_id"],
            result=json.dumps(order, allow_nan=False),
        )
        return state
    except (ValueError, RuntimeError, OSError):
        return "unknown"


def process_one(
    path: Path,
    venue,
    portfolio_id: str,
    *,
    now=None,
    enabled=lambda: True,
    allow_live=False,
) -> str:
    """One worker owns the inbox. Persist the exact request before one create call."""
    now = time.time() if now is None else now
    started = time.monotonic()
    with database(path) as db:
        db.execute("BEGIN IMMEDIATE")
        blocked = db.execute(
            "SELECT * FROM signals WHERE status IN ('planning','submitting','unknown','pending') ORDER BY rowid LIMIT 1"
        ).fetchone()
        if blocked:
            db.commit()
            if blocked["status"] == "planning":
                return "blocked"
            return _reconcile(path, blocked, venue)
        if not enabled():
            db.commit()
            return "disarmed"
        row = db.execute(
            "SELECT * FROM signals WHERE status='queued' ORDER BY rowid LIMIT 1"
        ).fetchone()
        if row is None:
            db.commit()
            return "idle"
        if row["mode"] == "live" and not allow_live:
            db.commit()
            return "disarmed"
        if not now - 300 <= row["timestamp"] <= now + 30:
            db.execute(
                "UPDATE signals SET status='expired' WHERE event_id=?",
                (row["event_id"],),
            )
            db.commit()
            return "expired"
        db.execute(
            "UPDATE signals SET status='planning' WHERE event_id=?", (row["event_id"],)
        )
        db.commit()
    try:
        if row["portfolio_id"] != portfolio_id:
            raise ValueError("portfolio_changed")
        plan = venue.plan(row["symbol"], row["side"], portfolio_id)
        if now + time.monotonic() - started - row["timestamp"] > 300 or not enabled():
            raise ValueError("signal_expired")
        client_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                "soloracle:coinbase:" + portfolio_id + ":" + row["event_id"],
            )
        )
        if row["mode"] != "live":
            _update(
                path,
                row["event_id"],
                "dry-run",
                plan=json.dumps(plan, allow_nan=False),
                client_order_id=client_id,
            )
            return "dry-run"
        # Commit-before-send makes any subsequent exception an ambiguous outcome.
        _update(
            path,
            row["event_id"],
            "submitting",
            plan=json.dumps(plan, allow_nan=False),
            client_order_id=client_id,
        )
    except (ValueError, RuntimeError, OSError):
        _update(
            path,
            row["event_id"],
            "refused",
            result=json.dumps({"reason": "coinbase_plan_unavailable"}),
        )
        return "refused"
    try:
        # The durable commit can wait on I/O; check the kill/deadline again after it.
        if not enabled() or now + time.monotonic() - started - row["timestamp"] > 300:
            _update(
                path,
                row["event_id"],
                "refused",
                result=json.dumps({"reason": "disarmed_or_expired_before_submission"}),
            )
            return "refused"
        result = venue.submit(plan, client_id)
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("order_id"), str)
            or not result["order_id"]
            or result.get("product_id") != plan["product_id"]
            or result.get("side") != plan["side"]
            or (
                result.get("client_order_id") is not None
                and result["client_order_id"] != client_id
            )
        ):
            raise ValueError("unverified_submission_identity")
        _update(
            path,
            row["event_id"],
            "pending",
            order_id=result["order_id"],
            result=json.dumps(result, allow_nan=False),
        )
    except (ValueError, RuntimeError, OSError):
        _update(
            path,
            row["event_id"],
            "unknown",
            result=json.dumps({"reason": "submission_requires_reconciliation"}),
        )
        return "unknown"
    with database(path) as db:
        pending = db.execute(
            "SELECT * FROM signals WHERE event_id=?", (row["event_id"],)
        ).fetchone()
    return _reconcile(path, pending, venue)

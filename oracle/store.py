"""Private append-only SQLite Oracle event archive with transactional state."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, path: str | Path, *, expected_policy: str | None = None) -> None:
        self.path = Path(path).expanduser().absolute()
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise ValueError("archive_symlink_refused")
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            application = db.execute("PRAGMA application_id").fetchone()[0]
            tables = {
                r[0]
                for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            if version not in (0, 1, 2) or (tables and application != 0x4F52434C):
                raise ValueError("archive_schema_not_supported")
            if application not in (0, 0x4F52434C):
                raise ValueError("archive_schema_not_supported")
            if expected_policy is not None:
                recorded = db.execute("SELECT body FROM metadata WHERE key='policy'").fetchone() if "metadata" in tables else None
                if recorded is not None and recorded[0] != expected_policy:
                    raise ValueError("archive_policy_mismatch_use_new_archive")
                # Refuse before any DDL or persistent PRAGMA changes. An archive
                # that lost its policy cannot acquire a new identity over history.
                if recorded is None and any(
                    db.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None
                    for table in ("events", "observations", "forecasts", "resolutions", "graphdb_ticks", "graphdb_predictions")
                    if table in tables
                ):
                    raise ValueError("archive_policy_unavailable_use_new_archive")
            schema = """
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL, event_key TEXT NOT NULL UNIQUE, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS observations (
                    event_id TEXT PRIMARY KEY, observed REAL NOT NULL, received REAL NOT NULL,
                    price REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS forecasts (
                    id TEXT PRIMARY KEY, strategy TEXT NOT NULL, version TEXT NOT NULL,
                    issued REAL NOT NULL, target REAL NOT NULL, direction INTEGER NOT NULL,
                    reference REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS resolutions (
                    forecast TEXT PRIMARY KEY REFERENCES forecasts(id),
                    outcome INTEGER, hit INTEGER, resolved_at REAL NOT NULL, body TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS graphdb_ticks (
                    tick_id TEXT PRIMARY KEY, instrument TEXT NOT NULL, policy_hash TEXT NOT NULL,
                    bar_index INTEGER NOT NULL, chart_time INTEGER NOT NULL,
                    observed_at REAL NOT NULL, received_at REAL NOT NULL, price REAL NOT NULL,
                    observation_id TEXT NOT NULL, market_shape TEXT NOT NULL, aggregate TEXT NOT NULL,
                    UNIQUE(instrument,policy_hash,bar_index));
                CREATE TABLE IF NOT EXISTS graphdb_predictions (
                    tick_id TEXT NOT NULL REFERENCES graphdb_ticks(tick_id),
                    strategy_id TEXT NOT NULL, strategy_version TEXT NOT NULL,
                    forecast_id TEXT, direction INTEGER, issued_at REAL, expires_at REAL,
                    hits INTEGER NOT NULL, resolved INTEGER NOT NULL, accuracy_percent REAL,
                    vote_weight REAL, vote_eligible INTEGER NOT NULL CHECK(vote_eligible IN (0,1)),
                    reason TEXT, PRIMARY KEY(tick_id,strategy_id),
                    CHECK(direction IS NULL OR direction IN (-1,0,1)));
                CREATE INDEX IF NOT EXISTS observation_time ON observations(observed);
                CREATE INDEX IF NOT EXISTS forecast_target ON forecasts(target);
                CREATE INDEX IF NOT EXISTS graphdb_tick_time ON graphdb_ticks(instrument,bar_index);
            """
            for statement in schema.split(";"):
                if statement.strip():
                    db.execute(statement)
            for table in (
                "events",
                "observations",
                "forecasts",
                "resolutions",
                "graphdb_ticks",
                "graphdb_predictions",
            ):
                for operation in ("UPDATE", "DELETE"):
                    db.execute(
                        f"CREATE TRIGGER IF NOT EXISTS immutable_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_archive'); END"
                    )
            db.execute("PRAGMA user_version=2")
            db.execute("PRAGMA application_id=1330791244")
        self.path.chmod(0o600)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def event(db: sqlite3.Connection, kind: str, key: str, body: dict) -> None:
        db.execute(
            "INSERT INTO events(kind,event_key,body) VALUES(?,?,?)",
            (kind, key, canonical(body)),
        )

    def history(self, limit: int = 100, after: int = 0) -> dict:
        if (
            type(limit) is not int
            or not 1 <= limit <= 1000
            or type(after) is not int
            or after < 0
        ):
            raise ValueError("invalid_history_page")
        with self.connection() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE sequence>? ORDER BY sequence LIMIT ?",
                (after, limit),
            ).fetchall()
        return {
            "schema_version": 1,
            "events": [
                {
                    "sequence": row["sequence"],
                    "type": row["kind"],
                    "data": json.loads(row["body"]),
                }
                for row in rows
            ],
            "next_after": rows[-1]["sequence"] if rows else after,
        }

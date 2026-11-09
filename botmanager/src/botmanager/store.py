"""Local SQLite ledger. Constructing a store and reading absent state are inert."""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .domain import BotSpec, ManagerError, canonical, utc_now

STORE_SCHEMA_VERSION = 1
BACKUP_DESCRIPTOR_VERSION = 1
# Future versions append migrations here; they must not reinterpret pinned specs.
MIGRATIONS = {
    1: (
        (
            "CREATE TABLE specs (bot_id TEXT PRIMARY KEY, display_name TEXT NOT NULL COLLATE NOCASE UNIQUE, "
            "source TEXT NOT NULL, owner TEXT NOT NULL, source_identity TEXT NOT NULL, body TEXT NOT NULL, "
            "UNIQUE(source, owner, source_identity))"
        ),
        (
            "CREATE TABLE events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, "
            "bot_id TEXT NOT NULL REFERENCES specs(bot_id), body TEXT NOT NULL)"
        ),
    )
}


def data_home() -> Path:
    configured = os.environ.get("SOLBOT_HOME")
    return (
        Path(configured).expanduser().absolute()
        if configured
        else Path.home() / ".config" / "solbot"
    )


class ManagerStore:
    def __init__(self, home: Path | str | None = None) -> None:
        self.home = Path(home).absolute() if home is not None else data_home()
        self.path = self.home / "manager.sqlite3"

    @property
    def initialized(self) -> bool:
        return self.path.is_file()

    @contextmanager
    def _connection(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        db = None
        try:
            if write:
                self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
                db = sqlite3.connect(self.path, timeout=5)
                self.path.chmod(0o600)
            else:
                db = sqlite3.connect(
                    self.path.as_uri() + "?mode=ro", uri=True, timeout=5
                )
            db.execute("PRAGMA foreign_keys=ON")
            if not write:
                db.execute("PRAGMA query_only=ON")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0 and write:
                db.execute("BEGIN IMMEDIATE")
                # Another process may have completed initialization while we waited.
                version = db.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    for statement in MIGRATIONS[1]:
                        db.execute(statement)
                    db.execute("PRAGMA user_version=1")
                    version = 1
                db.commit()
            if version != STORE_SCHEMA_VERSION:
                raise ManagerError(
                    "incompatible_store",
                    "Store schema is incompatible; no migration was applied.",
                    4,
                )
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except sqlite3.IntegrityError as exc:
            if db is not None:
                db.rollback()
            raise ManagerError(
                "store_conflict",
                "Identity, display name, or event conflicts with the ledger.",
                2,
            ) from exc
        except (sqlite3.Error, OSError) as exc:
            if db is not None:
                db.rollback()
            raise ManagerError(
                "store_unavailable", "The manager ledger is unavailable or corrupt.", 4
            ) from exc
        finally:
            if db is not None:
                db.close()

    @staticmethod
    def _decode(body: str) -> BotSpec:
        try:
            raw = json.loads(body)
            if not isinstance(raw, dict):
                raise TypeError
            return BotSpec.from_dict(raw)
        except (ValueError, TypeError) as exc:
            raise ManagerError(
                "invalid_spec",
                "The stored bot specification is invalid or incompatible.",
                4,
            ) from exc

    def list_specs(self) -> list[BotSpec]:
        if not self.initialized:
            return []
        with self._connection() as db:
            return [
                self._decode(row[0])
                for row in db.execute("SELECT body FROM specs ORDER BY display_name")
            ]

    def get_spec(self, id_or_name: str) -> BotSpec | None:
        if not self.initialized:
            return None
        with self._connection() as db:
            rows = db.execute(
                "SELECT body FROM specs WHERE bot_id=? OR display_name=? COLLATE NOCASE",
                (id_or_name, id_or_name),
            ).fetchall()
            if len(rows) > 1:
                raise ManagerError(
                    "ambiguous_identity", "Use a bot UUID to resolve this identity."
                )
            return self._decode(rows[0][0]) if rows else None

    def create_spec(self, spec: BotSpec) -> BotSpec:
        # Validate before any home or database creation, including direct store callers.
        spec = BotSpec.from_dict(spec.to_dict())
        event = {
            "schema_version": 1,
            "event_id": str(uuid4()),
            "bot_id": spec.bot_id,
            "event_type": "spec.created",
            "occurred_at": utc_now(),
            "config_revision": spec.config_revision,
            "config_hash": spec.config_hash,
        }
        with self._connection(write=True) as db:
            db.execute(
                "INSERT INTO specs VALUES (?,?,?,?,?,?)",
                (
                    spec.bot_id,
                    spec.display_name,
                    spec.source,
                    spec.owner,
                    spec.source_identity,
                    canonical(spec.to_dict()),
                ),
            )
            self._insert_event(db, event)
        return spec

    @staticmethod
    def _insert_event(db: sqlite3.Connection, event: Mapping[str, Any]) -> None:
        db.execute(
            "INSERT INTO events(event_id,bot_id,body) VALUES (?,?,?)",
            (event["event_id"], event["bot_id"], canonical(event)),
        )

    def append_event(self, event: Mapping[str, Any]) -> dict[str, Any]:
        # Events contain typed references, never unbounded owner response/log bodies.
        allowed = {
            "schema_version",
            "event_id",
            "bot_id",
            "event_type",
            "occurred_at",
            "config_revision",
            "config_hash",
        }
        if not isinstance(event, Mapping) or not set(event) <= allowed:
            raise ManagerError("invalid_input", "Event fields are invalid.")
        result = {"schema_version": 1, "occurred_at": utc_now(), **event}
        if (
            type(result["schema_version"]) is not int
            or result["schema_version"] != 1
            or any(
                not isinstance(result.get(key), str) or not result[key]
                for key in ("event_id", "bot_id", "event_type", "occurred_at")
            )
        ):
            raise ManagerError("invalid_input", "Event fields are invalid.")
        try:
            if (
                datetime.fromisoformat(result["occurred_at"]).tzinfo is None
                or not re.fullmatch(r"[a-z][a-z0-9_.]{0,63}", result["event_type"])
                or len(result["event_id"]) > 128
                or (
                    "config_revision" in result
                    and type(result["config_revision"]) is not int
                )
            ):
                raise ValueError
        except ValueError as exc:
            raise ManagerError("invalid_input", "Event fields are invalid.") from exc
        spec = self.get_spec(result["bot_id"])
        if spec is None:
            raise ManagerError("bot_not_found", "Bot identity was not found.")
        if (
            result.get("config_revision", spec.config_revision) != spec.config_revision
            or result.get("config_hash", spec.config_hash) != spec.config_hash
        ):
            raise ManagerError(
                "invalid_input", "Event configuration reference is invalid."
            )
        with self._connection(write=True) as db:
            self._insert_event(db, result)
        return result

    def backup_descriptor(self) -> dict[str, Any]:
        return {
            "schema_version": BACKUP_DESCRIPTOR_VERSION,
            "store_schema_version": STORE_SCHEMA_VERSION,
            "path": str(self.path),
            "initialized": self.initialized,
            "format": "sqlite3",
            "method": "sqlite_connection_backup",
            "contains": ["pinned_specs", "events"],
            "credentials": False,
        }

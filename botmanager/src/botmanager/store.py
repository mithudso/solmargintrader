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
from .mutations import (
    check_revision,
    mutation_lock,
    mutation_result,
    replay_mutation,
    request_body,
    request_identity,
    save_mutation,
    validate_tables,
)

STORE_SCHEMA_VERSION = 2
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
    ),
    2: (
        "CREATE TABLE spec_versions (bot_id TEXT NOT NULL REFERENCES specs(bot_id), revision INTEGER NOT NULL, body TEXT NOT NULL, saved_at TEXT NOT NULL, request_id TEXT, PRIMARY KEY(bot_id,revision))",
        "CREATE TABLE spec_requests (request_id TEXT PRIMARY KEY, request TEXT NOT NULL, result TEXT NOT NULL, checksum TEXT NOT NULL, acceptance TEXT NOT NULL)",
    ),
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
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in ((0, 1, 2) if write else (1, 2)):
                raise ManagerError(
                    "incompatible_store",
                    "Store schema is incompatible; no migration was applied.",
                    4,
                )
            if version == 0 and write:
                for statement in MIGRATIONS[1]:
                    db.execute(statement)
                version = 1
                db.execute("PRAGMA user_version=1")
            if version == 1 and write:
                # Decode every existing body before migration. Never resolve current defaults.
                rows = db.execute(
                    "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs"
                ).fetchall()
                specs = [self._decode_indexed(row) for row in rows]
                for statement in MIGRATIONS[2]:
                    db.execute(statement)
                for spec in specs:
                    self._insert_version(db, spec, spec.created_at, None)
                db.execute("PRAGMA user_version=2")
                version = 2
            tables = {
                "specs": "bot_id display_name source owner source_identity body",
                "events": "sequence event_id bot_id body",
            }
            if version >= 2:
                tables.update(
                    spec_versions="bot_id revision body saved_at request_id",
                    spec_requests="request_id request result checksum acceptance",
                )
            validate_tables(db, tables)
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

    @classmethod
    def _decode_indexed(cls, row: tuple[Any, ...]) -> BotSpec:
        spec = cls._decode(row[5])
        indexed_fields = (
            "bot_id",
            "display_name",
            "source",
            "owner",
            "source_identity",
        )
        if any(
            type(stored) is not type(getattr(spec, key)) or stored != getattr(spec, key)
            for key, stored in zip(indexed_fields, row[:5], strict=True)
        ):
            raise ManagerError(
                "invalid_spec", "The stored bot identity does not match its index.", 4
            )
        return spec

    def list_specs(self) -> list[BotSpec]:
        if not self.initialized:
            return []
        with self._connection() as db:
            return [
                self._checked_latest(db, row)
                for row in db.execute(
                    "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs ORDER BY display_name"
                )
            ]

    def get_spec(self, id_or_name: str) -> BotSpec | None:
        if not self.initialized:
            return None
        with self._connection() as db:
            rows = db.execute(
                "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs WHERE bot_id=? OR display_name=? COLLATE NOCASE",
                (id_or_name, id_or_name),
            ).fetchall()
            if len(rows) > 1:
                raise ManagerError(
                    "ambiguous_identity", "Use a bot UUID to resolve this identity."
                )
            return self._checked_latest(db, rows[0]) if rows else None

    def capture_view(self, identity=None, *, history=False, revision=None):
        """Compose journals only while append-only saved identities stay stable.

        A runtime snapshot lies between two equal manager inventories. Since
        edits append monotonically increasing revisions and identities are never
        deleted/reused, equality proves that the saved state was unchanged across
        that runtime capture. Runtime-only changes share one SQLite snapshot.
        No home, lock file, write transaction or mutation flock is needed.
        """
        from .ledger import RuntimeLedger

        if identity is not None and (not isinstance(identity, str) or not identity):
            raise ManagerError("invalid_input", "A bot identity is required.")
        if history and identity is None:
            raise ManagerError("invalid_input", "A bot identity is required.")
        ledger = RuntimeLedger(self.home)
        for _ in range(3):
            initialized = self.initialized
            inventory = self.list_specs()
            error = None
            result = None
            try:
                specs = inventory
                if identity is not None:
                    spec = self.get_spec(identity)
                    if spec is None:
                        raise ManagerError(
                            "bot_not_found", "Bot identity was not found."
                        )
                    specs = [spec]
                if history:
                    versions = self.history(spec.bot_id, revision)
                    if not versions:
                        raise ManagerError(
                            "revision_not_found",
                            "Saved configuration revision was not found.",
                        )
                    result = {
                        "schema_version": 1,
                        "bot_id": spec.bot_id,
                        "versions": versions,
                        "runs": ledger.history(spec.bot_id, revision),
                    }
                else:
                    rows = ledger.get_many([spec.bot_id for spec in specs])
                    result = {
                        "initialized": initialized,
                        "bots": [(spec, rows[spec.bot_id]) for spec in specs],
                    }
            except ManagerError as exc:
                # A changing inventory can also invalidate an intermediate
                # selection. Recheck before returning that read's error.
                error = exc
            if initialized == self.initialized and inventory == self.list_specs():
                if error is not None:
                    raise error
                return result
        raise ManagerError(
            "read_conflict",
            "Saved configurations changed during the read; no combined snapshot was returned.",
            4,
        )

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
            self._insert_version(db, spec, spec.created_at, None)
            self._insert_event(db, event)
        return spec

    @staticmethod
    def _insert_version(db, spec, saved_at, request_id):
        db.execute(
            "INSERT INTO spec_versions VALUES (?,?,?,?,?)",
            (
                spec.bot_id,
                spec.config_revision,
                canonical(spec.to_dict()),
                saved_at,
                request_id,
            ),
        )

    @classmethod
    def _checked_latest(cls, db, row):
        spec = cls._decode_indexed(row)
        if db.execute("PRAGMA user_version").fetchone()[0] >= 2:
            latest = db.execute(
                "SELECT revision,body FROM spec_versions WHERE bot_id=? ORDER BY revision DESC LIMIT 1",
                (spec.bot_id,),
            ).fetchone()
            if (
                latest is None
                or latest["revision"] != spec.config_revision
                or canonical(cls._decode(latest["body"]).to_dict())
                != canonical(spec.to_dict())
            ):
                raise ManagerError(
                    "invalid_spec",
                    "Latest specification disagrees with immutable history.",
                    4,
                )
        return spec

    def history(self, bot_id, revision=None):
        if revision is not None and (type(revision) is not int or revision < 1):
            raise ManagerError("invalid_input", "Revision must be a positive integer.")
        if not self.initialized:
            return []
        with self._connection() as db:
            row = db.execute(
                "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs WHERE bot_id=?",
                (bot_id,),
            ).fetchone()
            if row is None:
                return []
            latest = self._checked_latest(db, row)
            if db.execute("PRAGMA user_version").fetchone()[0] == 1:
                return (
                    [
                        {
                            "spec": latest.to_dict(),
                            "saved_at": latest.created_at,
                            "request_id": None,
                        }
                    ]
                    if revision in (None, latest.config_revision)
                    else []
                )
            result = []
            for row in db.execute(
                "SELECT * FROM spec_versions WHERE bot_id=? ORDER BY revision",
                (bot_id,),
            ):
                spec = self._decode(row["body"])
                if (
                    spec.bot_id != bot_id
                    or spec.config_revision != row["revision"]
                    or any(
                        getattr(spec, key) != getattr(latest, key)
                        for key in (
                            "created_at",
                            "display_name",
                            "source_identity",
                            "strategy_id",
                        )
                    )
                ):
                    raise ManagerError(
                        "invalid_spec",
                        "Historical specification attribution is invalid.",
                        4,
                    )
                if revision in (None, spec.config_revision):
                    result.append(
                        {
                            "spec": spec.to_dict(),
                            "saved_at": row["saved_at"],
                            "request_id": row["request_id"],
                        }
                    )
            return result

    def has_edit_request(self, request_id):
        if not self.initialized:
            return False
        with self._connection() as db:
            return (
                db.execute("PRAGMA user_version").fetchone()[0] >= 2
                and db.execute(
                    "SELECT 1 FROM spec_requests WHERE request_id=?", (request_id,)
                ).fetchone()
                is not None
            )

    def edit(self, identity, changes, *, expected_revision=None, request_id=None):
        from .config import validate_delta
        from .ledger import RuntimeLedger

        request_id = request_identity(request_id, expected_revision)
        # Refuse malformed settings before opening any write transaction or lock file.
        initial = self.get_spec(identity)
        if initial is None:
            raise ManagerError("bot_not_found", "Bot identity was not found.")
        # Only intrinsic delta checks belong here. Both new requests and replay
        # validate merged values against their exact base inside the transaction.
        validate_delta(initial.strategy_id, changes)
        request = request_body(
            "edit", initial.bot_id, changes, expected_revision, request_id
        )
        with mutation_lock(self.home), self._connection(write=True) as db:
            if RuntimeLedger(self.home).has_adoption_request(request_id):
                raise ManagerError(
                    "identity_conflict", "Request UUID already belongs to an adoption."
                )
            old = db.execute(
                "SELECT * FROM spec_requests WHERE request_id=?", (request_id,)
            ).fetchone()
            result = replay_mutation(old, request)
            if result is not None:
                before = self._version(
                    db, initial.bot_id, result["receipt"]["prior_revision"]
                )
                expected = before.edited(changes)
                receipt = result["receipt"]
                if (
                    canonical(expected.to_dict()) != canonical(result["spec"])
                    or receipt["prior_hash"] != before.config_hash
                    or receipt["outcome"]
                    != ("skipped" if expected == before else "acknowledged")
                    or canonical(
                        self._version(
                            db, initial.bot_id, expected.config_revision
                        ).to_dict()
                    )
                    != canonical(expected.to_dict())
                ):
                    raise ManagerError(
                        "invalid_receipt",
                        "Edit receipt disagrees with immutable revisions.",
                        4,
                    )
                if expected.config_revision != before.config_revision:
                    version = db.execute(
                        "SELECT saved_at,request_id FROM spec_versions WHERE bot_id=? AND revision=?",
                        (initial.bot_id, expected.config_revision),
                    ).fetchone()
                    if (
                        receipt["accepted_at"] != version["saved_at"]
                        or request_id != version["request_id"]
                    ):
                        raise ManagerError(
                            "invalid_receipt",
                            "Edit receipt does not own its saved revision.",
                            4,
                        )
                return result
            row = db.execute(
                "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs WHERE bot_id=?",
                (initial.bot_id,),
            ).fetchone()
            before = self._checked_latest(db, row)
            check_revision(before, expected_revision)
            after = before.edited(changes)
            runtime = RuntimeLedger(self.home).get(before.bot_id)
            result = mutation_result(
                request,
                before,
                after,
                active_runtime_id=runtime["runtime_id"] if runtime else None,
                owner_generation=runtime["generation"] if runtime else None,
                input_snapshot_hash=runtime["input"]["snapshot_hash"]
                if runtime
                else None,
                reason="spec_revision_saved"
                if after != before
                else "settings_already_pinned",
                changed=after != before,
            )
            if after != before:
                self._insert_version(
                    db, after, result["receipt"]["accepted_at"], request_id
                )
                db.execute(
                    "UPDATE specs SET body=? WHERE bot_id=?",
                    (canonical(after.to_dict()), after.bot_id),
                )
                self._insert_event(
                    db,
                    {
                        "schema_version": 1,
                        "event_id": str(uuid4()),
                        "bot_id": after.bot_id,
                        "event_type": "spec.edited",
                        "occurred_at": result["receipt"]["accepted_at"],
                        "config_revision": after.config_revision,
                        "config_hash": after.config_hash,
                    },
                )
            save_mutation(db, "spec_requests", request, result)
            return result

    def record_research_proposal(self, proposal):
        """CAS a pending-shadow receipt; this never adopts settings or drops lots.

        The evidence owner and manager are separate databases. The owner stores
        its proposal first, this transaction stores a matching receipt, then the
        caller mirrors that receipt. A crash retries exactly this same proposal.
        """
        from uuid import UUID

        from .config import validate_delta
        from .domain import fingerprint

        required = {
            "version",
            "request_id",
            "run_id",
            "bot_id",
            "baseline_revision",
            "baseline_hash",
            "pins",
            "changes",
            "evidence_digest",
            "state",
            "automatic_promotion",
            "authority",
            "production_eligible",
            "reason",
        }
        if (
            not isinstance(proposal, dict)
            or set(proposal) != required
            or proposal["version"] != 2
            or proposal["state"] != "pending_shadow"
            or proposal["automatic_promotion"] is not False
            or type(proposal["production_eligible"]) is not bool
            or (
                proposal["production_eligible"]
                and proposal["authority"].get("isolation_mode") != "registered_clients"
            )
        ):
            raise ManagerError("invalid_receipt", "Unsupported research proposal.", 4)
        try:
            if str(UUID(proposal["request_id"])) != proposal["request_id"]:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ManagerError(
                "invalid_receipt", "Invalid proposal request UUID.", 4
            ) from exc
        encoded = canonical(proposal)
        with mutation_lock(self.home), self._connection(write=True) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS research_proposals (request_id TEXT PRIMARY KEY, proposal TEXT NOT NULL, receipt TEXT NOT NULL, checksum TEXT NOT NULL)"
            )
            old = db.execute(
                "SELECT * FROM research_proposals WHERE request_id=?",
                (proposal["request_id"],),
            ).fetchone()
            if old:
                receipt = json.loads(old["receipt"])
                if old["proposal"] != encoded or old["checksum"] != fingerprint(
                    {"proposal": proposal, "receipt": receipt}
                ):
                    raise ManagerError(
                        "invalid_receipt",
                        "Research proposal receipt conflicts or is corrupt.",
                        4,
                    )
                return receipt
            row = db.execute(
                "SELECT bot_id,display_name,source,owner,source_identity,body FROM specs WHERE bot_id=?",
                (proposal["bot_id"],),
            ).fetchone()
            if row is None:
                raise ManagerError(
                    "bot_not_found", "Research proposal bot was not found."
                )
            before = self._checked_latest(db, row)
            if (
                before.config_revision != proposal["baseline_revision"]
                or before.config_hash != proposal["baseline_hash"]
                or dict(before.user_overrides) != proposal["pins"]
            ):
                raise ManagerError(
                    "revision_conflict",
                    "Research proposal baseline or manual pins changed.",
                    3,
                )
            validate_delta(before.strategy_id, proposal["changes"])
            if set(proposal["changes"]) & set(before.user_overrides):
                raise ManagerError(
                    "manual_pin_conflict",
                    "Research proposal cannot replace manual pins.",
                    3,
                )
            receipt = {
                "version": 2,
                "request_id": proposal["request_id"],
                "proposal_digest": fingerprint(proposal),
                "authority": proposal["authority"],
                "production_eligible": proposal["production_eligible"],
                "evidence_digest": proposal["evidence_digest"],
                "baseline_revision": before.config_revision,
                "baseline_hash": before.config_hash,
                "state": "pending_shadow",
                "configuration_changed": False,
            }
            db.execute(
                "INSERT INTO research_proposals VALUES (?,?,?,?)",
                (
                    proposal["request_id"],
                    encoded,
                    canonical(receipt),
                    fingerprint({"proposal": proposal, "receipt": receipt}),
                ),
            )
        return receipt

    def _version(self, db, bot_id, revision):
        row = db.execute(
            "SELECT body FROM spec_versions WHERE bot_id=? AND revision=?",
            (bot_id, revision),
        ).fetchone()
        if row is None:
            raise ManagerError(
                "invalid_receipt",
                "Receipt references a missing specification revision.",
                4,
            )
        spec = self._decode(row["body"])
        if spec.bot_id != bot_id or spec.config_revision != revision:
            raise ManagerError(
                "invalid_receipt", "Receipt specification attribution is invalid.", 4
            )
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
        version = STORE_SCHEMA_VERSION
        if self.initialized:
            with self._connection() as db:
                version = db.execute("PRAGMA user_version").fetchone()[0]
        return {
            "schema_version": BACKUP_DESCRIPTOR_VERSION,
            "store_schema_version": version,
            "path": str(self.path),
            "initialized": self.initialized,
            "format": "sqlite3",
            "method": "sqlite_connection_backup",
            "contains": ["pinned_specs", "spec_versions", "spec_requests", "events"],
            "credentials": False,
        }

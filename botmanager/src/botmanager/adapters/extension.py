"""Browser-owner native registration and durable delegated paper-control mailbox.

No Chrome files are opened. Only the extension can report its singleton slot.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from ..domain import ManagerError, canonical, fingerprint
from ..receipts import CommandReceipt
from ..store import data_home

PROTOCOL = 1
STALE_SECONDS = 90.0
MAX_REQUESTS = 10000
MAX_INSTALLATIONS = 100
_MISSING = object()
SLOT = "grid"
SNAPSHOT_FIELDS = {
    "installation_id",
    "native_id",
    "generation",
    "config_revision",
    "config_hash",
    "runtime_id",
    "running",
    "mode",
    "armed",
    "kill_switch",
    "extension_version",
    "source_hash",
}
CONTROL_FIELDS = {
    "schema_version",
    "request_id",
    "installation_id",
    "native_id",
    "operation",
    "expected_generation",
    "expected_config_hash",
    "expected_config_revision",
    "expected_runtime_id",
    "sequence",
    "expires_at",
}
RECEIPT_FIELDS = {
    "request_id",
    "outcome",
    "reason",
    "generation",
    "runtime_id",
    "config_hash",
}


def _fail(code="invalid_browser_message"):
    return ManagerError(
        code, "Browser owner message is unavailable or incompatible.", 3
    )


def _uuid(value):
    try:
        return type(value) is str and str(UUID(value)) == value
    except ValueError:
        return False


def _sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _origin(value):
    return (
        type(value) is str
        and re.fullmatch(r"chrome-extension://[a-p]{32}/?", value) is not None
    )


def validate_snapshot(snapshot):
    try:
        if (
            type(snapshot) is not dict
            or set(snapshot) != SNAPSHOT_FIELDS
            or not _uuid(snapshot["installation_id"])
            or snapshot["native_id"] != SLOT
            or type(snapshot["generation"]) is not int
            or snapshot["generation"] < 0
            or type(snapshot["config_revision"]) is not int
            or snapshot["config_revision"] < 1
            or not _sha(snapshot["config_hash"])
            or not _sha(snapshot["source_hash"])
            or snapshot["runtime_id"] is not None
            and not _uuid(snapshot["runtime_id"])
            or any(
                type(snapshot[k]) is not bool
                for k in ("running", "armed", "kill_switch")
            )
            or snapshot["mode"] not in ("dry-run", "semi-auto", "full-auto")
            or re.fullmatch(r"\d+(?:\.\d+){1,3}", snapshot["extension_version"]) is None
            or snapshot["running"]
            and (
                snapshot["mode"] != "dry-run"
                or snapshot["armed"]
                or snapshot["kill_switch"]
                or snapshot["runtime_id"] is None
            )
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise _fail() from None


def _decode_json(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        raise _fail("corrupt_checkpoint") from None


class BrowserStore:
    def __init__(self, home=None):
        self.home = Path(home) if home is not None else data_home()
        self.path = self.home / "browser.sqlite3"

    @contextmanager
    def connection(self, write=False):
        db = None
        try:
            if write:
                self.home.mkdir(parents=True, exist_ok=True, mode=0o700)
                db = sqlite3.connect(self.path, timeout=1)
                self.path.chmod(0o600)
            else:
                db = sqlite3.connect(
                    self.path.absolute().as_uri() + "?mode=ro", uri=True, timeout=1
                )
                db.execute("PRAGMA query_only=ON")
            db.row_factory = sqlite3.Row
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0 and write:
                db.execute(
                    "CREATE TABLE owners (installation_id TEXT PRIMARY KEY, origin TEXT NOT NULL, snapshot TEXT NOT NULL, checksum TEXT NOT NULL, seen REAL NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE requests (sequence INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, installation_id TEXT NOT NULL, body TEXT NOT NULL, checksum TEXT NOT NULL, receipt TEXT NOT NULL, receipt_hash TEXT NOT NULL)"
                )
                db.execute("PRAGMA user_version=1")
                version = 1
            if version != 1:
                raise _fail("incompatible_store")
            yield db
            if write:
                db.commit()
        except (sqlite3.Error, OSError):
            raise _fail("store_unavailable") from None
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def _owner(self, row):
        if row is None:
            raise _fail("browser_owner_absent")
        snapshot = _decode_json(row["snapshot"])
        validate_snapshot(snapshot)
        if (
            fingerprint(snapshot) != row["checksum"]
            or snapshot["installation_id"] != row["installation_id"]
            or not _origin(row["origin"])
        ):
            raise _fail("corrupt_checkpoint")
        return snapshot

    def _request(self, row):
        body, receipt = _decode_json(row["body"]), _decode_json(row["receipt"])
        if (
            fingerprint(body) != row["checksum"]
            or fingerprint(receipt) != row["receipt_hash"]
        ):
            raise _fail("corrupt_checkpoint")
        CommandReceipt.from_dict(receipt)
        if (
            set(body) != CONTROL_FIELDS
            or body["schema_version"] != PROTOCOL
            or body["sequence"] != row["sequence"]
            or body["request_id"] != row["request_id"]
            or body["installation_id"] != row["installation_id"]
            or body["native_id"] != SLOT
            or body["operation"] not in ("start", "stop")
            or receipt["request_id"] != body["request_id"]
            or receipt["operation"] != body["operation"]
            or receipt["owner_id"] != body["installation_id"]
            or receipt["config_revision"] != body["expected_config_revision"]
            or receipt["metadata"]["config_hash"] != body["expected_config_hash"]
        ):
            raise _fail("corrupt_checkpoint")
        return body, receipt

    def _receipt(
        self, snapshot, body, outcome, reason, *, generation=None, runtime_id=_MISSING
    ):
        return CommandReceipt(
            schema_version=1,
            bot_id=str(
                uuid5(NAMESPACE_URL, f"browser:{snapshot['installation_id']}:grid")
            ),
            operation=body["operation"],
            request_id=body["request_id"],
            runtime_id=snapshot["runtime_id"] if runtime_id is _MISSING else runtime_id,
            owner_id=snapshot["installation_id"],
            owner_generation=snapshot["generation"]
            if generation is None
            else generation,
            config_revision=body["expected_config_revision"],
            outcome=outcome,
            reason=reason,
            metadata={"config_hash": body["expected_config_hash"]},
        ).to_dict()

    def poll(self, message, *, origin, allowed_origins, now=None):
        now = time.time() if now is None else now
        try:
            if (
                not _origin(origin)
                or origin.rstrip("/") not in {v.rstrip("/") for v in allowed_origins}
                or type(message) is not dict
                or set(message) != {"schema_version", "snapshot", "receipts"}
                or type(message["schema_version"]) is not int
                or message["schema_version"] != PROTOCOL
                or type(message["receipts"]) is not list
                or len(message["receipts"]) > 128
                or type(now) not in (float, int)
                or not math.isfinite(now)
            ):
                raise ValueError
            snapshot = message["snapshot"]
            validate_snapshot(snapshot)
        except (ValueError, TypeError, KeyError):
            raise _fail() from None
        identity = snapshot["installation_id"]
        with self.connection(True) as db:
            row = db.execute(
                "SELECT * FROM owners WHERE installation_id=?", (identity,)
            ).fetchone()
            if row is not None:
                prior = self._owner(row)
                if (
                    row["origin"].rstrip("/") != origin.rstrip("/")
                    or snapshot["generation"] < prior["generation"]
                    or snapshot["config_revision"] < prior["config_revision"]
                    or (
                        (
                            snapshot["source_hash"] != prior["source_hash"]
                            or snapshot["extension_version"]
                            != prior["extension_version"]
                        )
                        and snapshot["generation"] <= prior["generation"]
                    )
                    or (
                        snapshot["config_hash"] != prior["config_hash"]
                        and (
                            snapshot["config_revision"] <= prior["config_revision"]
                            or snapshot["generation"] <= prior["generation"]
                        )
                    )
                ):
                    raise _fail("browser_identity_changed")
            elif (
                db.execute("SELECT count(*) FROM owners").fetchone()[0]
                >= MAX_INSTALLATIONS
            ):
                raise _fail("resource_limit")
            db.execute(
                "INSERT INTO owners VALUES (?,?,?,?,?) ON CONFLICT(installation_id) DO UPDATE SET snapshot=excluded.snapshot,checksum=excluded.checksum,seen=excluded.seen",
                (identity, origin, canonical(snapshot), fingerprint(snapshot), now),
            )
            acknowledged = []
            for receipt in message["receipts"]:
                if type(receipt) is not dict or set(receipt) != RECEIPT_FIELDS:
                    raise _fail()
                saved = db.execute(
                    "SELECT * FROM requests WHERE request_id=?",
                    (receipt["request_id"],),
                ).fetchone()
                if saved is None or saved["installation_id"] != identity:
                    raise _fail("request_id_conflict")
                body, prior_receipt = self._request(saved)
                if (
                    receipt["outcome"]
                    not in ("acknowledged", "failed", "skipped", "unknown")
                    or receipt["reason"]
                    not in {
                        "paper_started",
                        "paper_stopped",
                        "already_running",
                        "already_stopped",
                        "browser_owner_context_changed",
                        "browser_paper_slot_unavailable",
                        "revoked_by_later_stop",
                        "outcome_unknown",
                        "browser_owner_expired",
                    }
                    or type(receipt["generation"]) is not int
                    or receipt["generation"] < body["expected_generation"]
                    or receipt["runtime_id"] is not None
                    and not _uuid(receipt["runtime_id"])
                    or receipt["config_hash"] != body["expected_config_hash"]
                ):
                    raise _fail()
                expected_outcomes = {
                    "paper_started": "acknowledged",
                    "paper_stopped": "acknowledged",
                    "already_running": "skipped",
                    "already_stopped": "skipped",
                    "revoked_by_later_stop": "skipped",
                    "browser_owner_context_changed": "failed",
                    "browser_paper_slot_unavailable": "failed",
                    "browser_owner_expired": "failed",
                    "outcome_unknown": "unknown",
                }
                if (
                    expected_outcomes[receipt["reason"]] != receipt["outcome"]
                    or receipt["generation"] > snapshot["generation"]
                    or receipt["reason"] in ("paper_started", "already_running")
                    and body["operation"] != "start"
                    or receipt["reason"] in ("paper_stopped", "already_stopped")
                    and body["operation"] != "stop"
                    or receipt["reason"] == "paper_started"
                    and (
                        receipt["runtime_id"] is None
                        or receipt["runtime_id"] == body["expected_runtime_id"]
                        or receipt["generation"] != body["expected_generation"] + 1
                    )
                ):
                    raise _fail()
                updated = self._receipt(
                    snapshot,
                    body,
                    receipt["outcome"],
                    receipt["reason"],
                    generation=receipt["generation"],
                    runtime_id=receipt["runtime_id"],
                )
                if (
                    prior_receipt["outcome"] != "pending"
                    and updated != prior_receipt
                    and prior_receipt["reason"] != "revoked_by_later_stop"
                ):
                    raise _fail("request_id_conflict")
                # If a start was already in flight when a later stop revoked its
                # queue entry, retain the owner's actual outcome. The later stop
                # remains queued and fences that known start in the browser.
                db.execute(
                    "UPDATE requests SET receipt=?,receipt_hash=? WHERE request_id=?",
                    (canonical(updated), fingerprint(updated), body["request_id"]),
                )
                acknowledged.append(body["request_id"])
            pending = []
            for request in db.execute(
                "SELECT * FROM requests WHERE installation_id=? ORDER BY sequence",
                (identity,),
            ):
                body, receipt = self._request(request)
                if receipt["outcome"] == "pending" and now > body["expires_at"]:
                    expired = self._receipt(
                        snapshot, body, "failed", "browser_owner_expired"
                    )
                    db.execute(
                        "UPDATE requests SET receipt=?,receipt_hash=? WHERE request_id=?",
                        (canonical(expired), fingerprint(expired), body["request_id"]),
                    )
                elif receipt["outcome"] == "pending":
                    pending.append(body)
                    if len(pending) == 32:
                        break
            return {
                "schema_version": 1,
                "controls": pending,
                "acknowledged": acknowledged,
                "origin": origin.rstrip("/"),
                "transfer": {
                    "available": False,
                    "reason": "owner_prepare_quiesce_snapshot_commit_unavailable",
                },
            }

    def discover(self, *, now=None):
        if not self.path.exists():
            return []
        now = time.time() if now is None else now
        records = []
        with self.connection() as db:
            for row in db.execute("SELECT * FROM owners ORDER BY installation_id"):
                snapshot = self._owner(row)
                age = now - row["seen"]
                fresh = 0 <= age <= STALE_SECONDS
                supported = snapshot["mode"] == "dry-run" and not snapshot["armed"]
                records.append(
                    {
                        "schema_version": 1,
                        "source": "browser",
                        "installation_id": row["installation_id"],
                        "state": ("available" if supported else "unsupported")
                        if fresh
                        else "offline",
                        "reason": (
                            None if supported else "browser_paper_slot_unavailable"
                        )
                        if fresh
                        else "browser_owner_expired",
                        "native_origin": row["origin"],
                        "snapshot": snapshot,
                        "last_seen": row["seen"],
                        "bots": [
                            {
                                "native_id": SLOT,
                                "bot_id": str(
                                    uuid5(
                                        NAMESPACE_URL,
                                        f"browser:{row['installation_id']}:grid",
                                    )
                                ),
                                "identity": f"browser:{row['installation_id']}:grid",
                                "owner": "browser",
                                "strategy": "grid",
                                "mode": "paper" if supported else snapshot["mode"],
                                "running": snapshot["running"] if supported else None,
                                "generation": snapshot["generation"],
                                "config_hash": snapshot["config_hash"],
                                "runtime_id": snapshot["runtime_id"],
                                "transfer_available": False,
                                "transfer_reason": "owner_prepare_quiesce_snapshot_commit_unavailable",
                            }
                        ],
                    }
                )
        return records

    def control(
        self,
        installation_id,
        operation,
        request_id,
        *,
        expected_generation,
        expected_config_hash,
        now=None,
    ):
        now = time.time() if now is None else now
        if not self.path.is_file():
            raise _fail("browser_owner_absent")
        try:
            if (
                not _uuid(installation_id)
                or not _uuid(request_id)
                or operation not in ("start", "stop")
                or type(expected_generation) is not int
                or expected_generation < 0
                or not _sha(expected_config_hash)
            ):
                raise ValueError
        except (ValueError, TypeError):
            raise _fail("invalid_input") from None
        with self.connection(True) as db:
            row = db.execute(
                "SELECT * FROM owners WHERE installation_id=?", (installation_id,)
            ).fetchone()
            snapshot = self._owner(row)
            old = db.execute(
                "SELECT * FROM requests WHERE request_id=?", (request_id,)
            ).fetchone()
            if old is not None:
                body, receipt = self._request(old)
                if (
                    body["installation_id"],
                    body["operation"],
                    body["expected_generation"],
                    body["expected_config_hash"],
                ) != (
                    installation_id,
                    operation,
                    expected_generation,
                    expected_config_hash,
                ):
                    raise _fail("request_id_conflict")
                return receipt
            if (
                db.execute("SELECT count(*) FROM requests").fetchone()[0]
                >= MAX_REQUESTS
            ):
                raise _fail("resource_limit")
            sequence = db.execute(
                "SELECT coalesce(max(sequence),0)+1 FROM requests"
            ).fetchone()[0]
            body = {
                "schema_version": 1,
                "request_id": request_id,
                "installation_id": installation_id,
                "native_id": SLOT,
                "operation": operation,
                "expected_generation": expected_generation,
                "expected_config_hash": expected_config_hash,
                "expected_config_revision": snapshot["config_revision"],
                "expected_runtime_id": snapshot["runtime_id"],
                "sequence": sequence,
                "expires_at": now + STALE_SECONDS,
            }
            outcome, reason = "pending", "browser_owner_delivery_pending"
            if not 0 <= now - row["seen"] <= STALE_SECONDS:
                outcome, reason = "failed", "browser_owner_expired"
            elif (
                snapshot["generation"] != expected_generation
                or snapshot["config_hash"] != expected_config_hash
            ):
                outcome, reason = "failed", "browser_owner_context_changed"
            elif (
                snapshot["mode"] != "dry-run"
                or snapshot["armed"]
                or operation == "start"
                and snapshot["kill_switch"]
            ):
                outcome, reason = "failed", "browser_paper_slot_unavailable"
            receipt = self._receipt(snapshot, body, outcome, reason)
            if operation == "stop" and outcome == "pending":
                for saved in db.execute(
                    "SELECT * FROM requests WHERE installation_id=? ORDER BY sequence",
                    (installation_id,),
                ).fetchall():
                    previous, pending = self._request(saved)
                    if (
                        previous["operation"] == "start"
                        and pending["outcome"] == "pending"
                    ):
                        revoked = self._receipt(
                            snapshot, previous, "skipped", "revoked_by_later_stop"
                        )
                        db.execute(
                            "UPDATE requests SET receipt=?,receipt_hash=? WHERE request_id=?",
                            (
                                canonical(revoked),
                                fingerprint(revoked),
                                previous["request_id"],
                            ),
                        )
            db.execute(
                "INSERT INTO requests VALUES (?,?,?,?,?,?,?)",
                (
                    sequence,
                    request_id,
                    installation_id,
                    canonical(body),
                    fingerprint(body),
                    canonical(receipt),
                    fingerprint(receipt),
                ),
            )
            return receipt

    def receipt(self, request_id):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM requests WHERE request_id=?", (request_id,)
            ).fetchone()
            if row is None:
                raise _fail("request_not_found")
            return self._request(row)[1]


def discover_browser(home=None):
    return BrowserStore(home).discover()


class BrowserAdapter:
    def __init__(self, installation_id, *, home=None):
        self.installation_id = installation_id
        self.store = BrowserStore(home)

    def discover(self):
        for item in self.store.discover():
            if item["installation_id"] == self.installation_id:
                return item
        raise _fail("browser_owner_absent")

    def control(
        self, operation, request_id, *, expected_generation, expected_config_hash
    ):
        return self.store.control(
            self.installation_id,
            operation,
            request_id,
            expected_generation=expected_generation,
            expected_config_hash=expected_config_hash,
        )


def resolve_browser(identity, *, home=None):
    if not isinstance(identity, str) or not identity.startswith("browser:"):
        return None
    parts = identity.split(":")
    if len(parts) != 3 or parts[2] != SLOT:
        raise _fail("bot_not_found")
    try:
        if not _uuid(parts[1]):
            raise ValueError
    except ValueError:
        raise _fail("bot_not_found") from None
    return BrowserAdapter(parts[1], home=home)


def browser_quiescent(home=None, *, now=None):
    """Require a fresh observed stopped slot and no unresolved owner operations."""
    store = BrowserStore(home)
    if not store.path.exists():
        return True
    records = store.discover(now=now)
    if any(
        record["state"] != "available" or record["snapshot"]["running"]
        for record in records
    ):
        return False
    with store.connection() as db:
        unresolved = []
        stopped_through = {}
        for row in db.execute("SELECT * FROM requests ORDER BY sequence"):
            body, receipt = store._request(row)
            if body["operation"] == "stop" and (
                receipt["outcome"] == "acknowledged"
                or receipt["reason"] == "already_stopped"
            ):
                stopped_through[body["installation_id"]] = row["sequence"]
            if receipt["outcome"] in ("pending", "unknown"):
                unresolved.append((body["installation_id"], row["sequence"]))
        if any(
            sequence > stopped_through.get(identity, 0)
            for identity, sequence in unresolved
        ):
            return False
    return True

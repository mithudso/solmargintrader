"""Transactional intent, generation fencing and reference-paper fill ledger.

The specification database and this separate runtime journal
has its own version and must be included in backups with the specifications.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from .data import validate_snapshot
from .domain import BotSpec, ManagerError, canonical, fingerprint
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
from .receipts import CommandReceipt
from .store import data_home

RESTART_DELAYS = (1.0, 5.0, 30.0)
FAILURE_WINDOW = 600.0
MAX_ACTIVE = 4
MAX_INSTANCES = 100
MAX_REQUESTS = 100000
# Once ordinary receipts fill, no new starts can enter. Reserve a stop receipt
# for every supported registered instance, including queued running intents.
# Accepted request IDs remain durable; no-op IDs cannot consume this reserve.
STOP_RECEIPT_RESERVE = MAX_INSTANCES
INTEGRITY_ERRORS = frozenset({"corrupt_checkpoint", "invalid_spec"})


class RuntimeLedger:
    def __init__(self, home: Path | None = None):
        self.home = Path(home).absolute() if home is not None else data_home()
        self.path = self.home / "runtime.sqlite3"

    @contextmanager
    def connection(
        self, write: bool = False, *, migrate_events: bool = True
    ) -> Iterator[sqlite3.Connection]:
        db = None
        try:
            if write:
                self.home.mkdir(mode=0o700, parents=True, exist_ok=True)
                db = sqlite3.connect(self.path, timeout=1)
                self.path.chmod(0o600)
            else:
                db = sqlite3.connect(
                    self.path.as_uri() + "?mode=ro", uri=True, timeout=1
                )
                db.execute("PRAGMA query_only=ON")
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA foreign_keys=ON")
            # Every multi-SELECT decoder must use one snapshot. Query-only mode
            # prevents writes but does not, by itself, pin a read transaction.
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0 and write:
                db.execute(
                    "CREATE TABLE runs (bot_id TEXT PRIMARY KEY, spec TEXT NOT NULL, input TEXT NOT NULL, runtime_id TEXT NOT NULL, desired TEXT NOT NULL, observed TEXT NOT NULL, generation INTEGER NOT NULL, owner TEXT, pid INTEGER, heartbeat REAL, tick_started REAL, evaluated REAL, cursor INTEGER NOT NULL, checkpoint TEXT, checkpoint_hash TEXT, failures TEXT NOT NULL, retry_at REAL NOT NULL, reason TEXT NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE fills (bot_id TEXT NOT NULL REFERENCES runs(bot_id), sequence INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(bot_id,sequence))"
                )
                db.execute(
                    "CREATE TABLE requests (request_id TEXT PRIMARY KEY, binding TEXT NOT NULL, receipt TEXT NOT NULL, checksum TEXT NOT NULL, acceptance TEXT)"
                )
                db.execute(
                    "CREATE TABLE events (sequence INTEGER PRIMARY KEY, bot_id TEXT NOT NULL, generation INTEGER NOT NULL, kind TEXT NOT NULL, cursor INTEGER NOT NULL, at REAL NOT NULL)"
                )
                db.execute("PRAGMA user_version=2")
                version = 2
            if version == 1 and write:
                # Historical acceptance context cannot be reconstructed from a
                # mutable receipt. Retain every legacy row and mark it unproven.
                db.execute("ALTER TABLE requests ADD COLUMN acceptance TEXT")
                db.execute("PRAGMA user_version=2")
                version = 2
            if version == 2 and write:
                db.execute(
                    "CREATE TABLE archives (runtime_id TEXT PRIMARY KEY, bot_id TEXT NOT NULL, body TEXT NOT NULL, checksum TEXT NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE adoption_requests (request_id TEXT PRIMARY KEY, request TEXT NOT NULL, result TEXT NOT NULL, checksum TEXT NOT NULL, acceptance TEXT NOT NULL)"
                )
                db.execute("PRAGMA user_version=3")
                version = 3
            if version == 3 and write and migrate_events:
                self._migrate_event_stream(db)
                db.execute("PRAGMA user_version=4")
                version = 4
            if version == 4 and write:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS segments (runtime_id TEXT NOT NULL, digest TEXT NOT NULL, body TEXT NOT NULL, fill_end INTEGER NOT NULL, PRIMARY KEY(runtime_id,digest))"
                )
                db.execute("PRAGMA user_version=5")
                version = 5
            if version not in (1, 2, 3, 4, 5):
                raise ManagerError(
                    "incompatible_store", "Runtime journal schema is incompatible.", 4
                )
            tables = {
                "runs": "bot_id spec input runtime_id desired observed generation owner pid heartbeat tick_started evaluated cursor checkpoint checkpoint_hash failures retry_at reason",
                "fills": "bot_id sequence body",
                "events": "sequence bot_id generation kind cursor at"
                + (" runtime_id origin_sequence origin" if version >= 4 else ""),
                "requests": "request_id binding receipt checksum"
                + (" acceptance" if version >= 2 else ""),
            }
            if version >= 3:
                tables.update(
                    archives="runtime_id bot_id body checksum",
                    adoption_requests="request_id request result checksum acceptance",
                )
            if version >= 5:
                tables["segments"] = "runtime_id digest body fill_end"
            validate_tables(db, tables)
            yield db
            if write:
                db.commit()
        except (sqlite3.Error, OSError) as exc:
            raise ManagerError(
                "store_unavailable", "Runtime journal is unavailable or corrupt.", 4
            ) from exc
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()

    def _migrate_event_stream(self, db):
        """Retain current cursors; import archived events without reusing IDs.

        Schema 3 removed events on adoption and could reuse their sequences.
        Archive imports therefore get new stream IDs above every known old ID;
        their exact original sequence and runtime remain separately attributable.
        Old archive bodies and all control/request rows stay byte-for-byte intact.
        """
        current = [
            dict(row) for row in db.execute("SELECT * FROM events ORDER BY sequence")
        ]
        archived = []
        for raw in db.execute("SELECT * FROM archives ORDER BY rowid"):
            archive = self._decode_archive(db, raw)
            archived.extend(
                (archive["runtime_id"], event) for event in archive["events"]
            )
        sequences = [event["sequence"] for event in current] + [
            event["sequence"] for _, event in archived
        ]
        if any(type(sequence) is not int or sequence < 1 for sequence in sequences):
            raise ManagerError(
                "incompatible_store", "Historical event sequences are invalid.", 4
            )
        next_sequence = max(sequences, default=0) + 1
        db.execute(
            "CREATE TABLE events_v4 (sequence INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT NOT NULL, generation INTEGER NOT NULL, kind TEXT NOT NULL, cursor INTEGER NOT NULL, at REAL NOT NULL, runtime_id TEXT NOT NULL, origin_sequence INTEGER, origin TEXT NOT NULL)"
        )
        fields = ("sequence", "bot_id", "generation", "kind", "cursor", "at")
        for event in current:
            run = db.execute(
                "SELECT runtime_id FROM runs WHERE bot_id=?", (event["bot_id"],)
            ).fetchone()
            if run is None or str(UUID(run["runtime_id"])) != run["runtime_id"]:
                raise ManagerError(
                    "incompatible_store",
                    "Current event runtime attribution is unavailable.",
                    4,
                )
            db.execute(
                "INSERT INTO events_v4 VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    *[event[key] for key in fields],
                    run["runtime_id"],
                    event["sequence"],
                    "legacy_current",
                ),
            )
        for runtime_id, event in archived:
            db.execute(
                "INSERT INTO events_v4 VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    next_sequence,
                    *[event[key] for key in fields[1:]],
                    runtime_id,
                    event["sequence"],
                    "legacy_archive",
                ),
            )
            next_sequence += 1
        db.execute("DROP TABLE events")
        db.execute("ALTER TABLE events_v4 RENAME TO events")

    @staticmethod
    def _event(db, row, kind):
        if db.execute("PRAGMA user_version").fetchone()[0] < 4:
            # A stop must not depend on validating or importing a historical
            # archive. Keep its old journal format until another writer migrates.
            db.execute(
                "INSERT INTO events(bot_id,generation,kind,cursor,at) VALUES (?,?,?,?,?)",
                (row["bot_id"], row["generation"], kind, row["cursor"], time.time()),
            )
            return

        run = db.execute(
            "SELECT runtime_id FROM runs WHERE bot_id=?", (row["bot_id"],)
        ).fetchone()
        db.execute(
            "INSERT INTO events(bot_id,generation,kind,cursor,at,runtime_id,origin_sequence,origin) VALUES (?,?,?,?,?,?,NULL,'native')",
            (
                row["bot_id"],
                row["generation"],
                kind,
                row["cursor"],
                time.time(),
                run["runtime_id"],
            ),
        )

    @staticmethod
    def _run_events(db, bot_id, runtime_id):
        if db.execute("PRAGMA user_version").fetchone()[0] >= 4:
            rows = db.execute(
                "SELECT * FROM events WHERE bot_id=? AND runtime_id=? ORDER BY sequence",
                (bot_id, runtime_id),
            )
        else:
            rows = db.execute(
                "SELECT * FROM events WHERE bot_id=? ORDER BY sequence", (bot_id,)
            )
        return [dict(row) for row in rows]

    def _decode(self, db, row, *, archived_fills=None):
        from .strategies import validate_checkpoint

        if row is None:
            return None
        try:
            result = dict(row)
            result["spec"] = json.loads(row["spec"])
            spec = BotSpec.from_dict(result["spec"])
            if spec.bot_id != row["bot_id"]:
                raise ValueError
            result["input"] = json.loads(row["input"])
            validate_snapshot(result["input"])
            result["failures"] = json.loads(row["failures"])
            if (
                str(UUID(row["runtime_id"])) != row["runtime_id"]
                or type(row["generation"]) is not int
                or row["generation"] < 0
                or type(row["cursor"]) is not int
                or row["cursor"] < 0
                or row["desired"] not in ("running", "stopped")
                or row["observed"]
                not in (
                    "stopped",
                    "stopping",
                    "pending",
                    "running",
                    "waiting",
                    "failed",
                    "blocked",
                    "recovering",
                )
                or not isinstance(result["failures"], list)
            ):
                raise ValueError
            checkpoint = (
                json.loads(row["checkpoint"]) if row["checkpoint"] is not None else None
            )
            result["checkpoint"] = checkpoint
            fill_base = 0
            if result["input"].get("prior_segment") is not None:
                digest = result["input"]["prior_segment"]
                head = True
                upper_cursor = row["cursor"] + 1
                expected_fill_end = None
                while digest is not None:
                    segment = db.execute(
                        "SELECT * FROM segments WHERE runtime_id=? AND digest=?",
                        (row["runtime_id"], digest),
                    ).fetchone()
                    if segment is None:
                        raise ValueError
                    body = json.loads(segment["body"])
                    segment_cursor = body["checkpoint"]["cursor"]
                    if fingerprint(body) != digest or segment_cursor > upper_cursor:
                        raise ValueError
                    prior_offset = body["input"].get("bar_offset", 0)
                    if prior_offset >= segment_cursor:
                        raise ValueError
                    upper_cursor = prior_offset
                    if segment_cursor != upper_cursor + len(body["input"]["bars"]):
                        raise ValueError
                    segment_fills = body["checkpoint"]["fills"]
                    segment_start = segment["fill_end"] - len(segment_fills)
                    if segment_start < 0 or (
                        expected_fill_end is not None
                        and segment["fill_end"] != expected_fill_end
                    ):
                        raise ValueError
                    saved_fills = (
                        archived_fills[segment_start : segment["fill_end"]]
                        if archived_fills is not None
                        else [
                            json.loads(f["body"])
                            for f in db.execute(
                                "SELECT body FROM fills WHERE bot_id=? AND sequence>=? AND sequence<? ORDER BY sequence",
                                (row["bot_id"], segment_start, segment["fill_end"]),
                            )
                        ]
                    )
                    if segment_fills != saved_fills:
                        raise ValueError
                    expected_fill_end = segment_start
                    if head:
                        fill_base = segment["fill_end"]
                        head = False
                    digest = body["input"].get("prior_segment")
                if expected_fill_end != 0:
                    raise ValueError
                result["fill_base"] = fill_base
            fills = (
                archived_fills[fill_base:]
                if archived_fills is not None
                else [
                    json.loads(f["body"])
                    for f in db.execute(
                        "SELECT body FROM fills WHERE bot_id=? AND sequence>=? ORDER BY sequence",
                        (row["bot_id"], fill_base),
                    )
                ]
            )
            if checkpoint is None:
                if row["cursor"] != 0 or fills or row["checkpoint_hash"] is not None:
                    raise ValueError
            elif (
                fingerprint(checkpoint) != row["checkpoint_hash"]
                or checkpoint["cursor"] != row["cursor"]
                or checkpoint["fills"] != fills
            ):
                raise ValueError
            if checkpoint is not None:
                validate_checkpoint(spec, result["input"], checkpoint)
            return result
        except (ValueError, KeyError, TypeError) as exc:
            raise ManagerError(
                "corrupt_checkpoint",
                "Runtime checkpoint and fill ledger do not reconcile.",
                4,
            ) from exc

    def get(self, bot_id: str):
        if not self.path.exists():
            return None
        with self.connection() as db:
            return self._decode(
                db,
                db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone(),
            )

    def get_many(self, bot_ids):
        """Capture all requested runtime rows and their fills in one snapshot."""
        if not self.path.exists():
            return {bot_id: None for bot_id in bot_ids}
        with self.connection() as db:
            return {
                bot_id: self._decode(
                    db,
                    db.execute(
                        "SELECT * FROM runs WHERE bot_id=?", (bot_id,)
                    ).fetchone(),
                )
                for bot_id in bot_ids
            }

    def ids(self):
        if not self.path.exists():
            return []
        with self.connection() as db:
            return [r[0] for r in db.execute("SELECT bot_id FROM runs ORDER BY bot_id")]

    def fills(self, bot_id):
        row = self.get(bot_id)
        if not row:
            return []
        with self.connection() as db:
            return [
                json.loads(r["body"])
                for r in db.execute(
                    "SELECT body FROM fills WHERE bot_id=? ORDER BY sequence", (bot_id,)
                )
            ]

    def events(self, bot_id, limit=100):
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ManagerError(
                "invalid_input", "Event limit must be between 1 and 1000."
            )
        if not self.path.exists():
            return []
        with self.connection() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM events WHERE bot_id=? ORDER BY sequence DESC LIMIT ?",
                    (bot_id, limit),
                )
            ]

    def register(self, spec: BotSpec, data: dict):
        from .store import ManagerStore
        from .strategies import validate_registration

        validate_registration(spec, data)
        with mutation_lock(self.home):
            saved = ManagerStore(self.home).get_spec(spec.bot_id)
            if saved is not None and saved.config_hash != spec.config_hash:
                raise ManagerError(
                    "stale_revision",
                    "Saved specification changed before input registration.",
                )
            return self._register(spec, data)

    def _register(self, spec: BotSpec, data: dict):
        from .strategies import validate_registration

        # Validate capability, sizing and economics before any durable registration.
        validate_registration(spec, data)
        with self.connection(True) as db:
            row = self._decode(
                db,
                db.execute(
                    "SELECT * FROM runs WHERE bot_id=?", (spec.bot_id,)
                ).fetchone(),
            )
            if row:
                if (
                    row["input"].get("origin_hash", row["input"]["snapshot_hash"])
                    != data.get("origin_hash", data["snapshot_hash"])
                    or row["spec"]["config_hash"] != spec.config_hash
                ):
                    raise ManagerError(
                        "identity_conflict",
                        "A reference run cannot adopt new input or configuration.",
                    )
                return {
                    "bot_id": spec.bot_id,
                    "snapshot_hash": data["snapshot_hash"],
                    "registered": True,
                }
            if db.execute("SELECT count(*) FROM runs").fetchone()[0] >= MAX_INSTANCES:
                raise ManagerError(
                    "resource_limit", "Reference instance capacity is exhausted.", 3
                )
            db.execute(
                "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    spec.bot_id,
                    canonical(spec.to_dict()),
                    canonical(data),
                    str(uuid4()),
                    "stopped",
                    "stopped",
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                    0,
                    None,
                    None,
                    "[]",
                    0.0,
                    "reference_input_registered",
                ),
            )
            self._event(
                db,
                {"bot_id": spec.bot_id, "generation": 0, "cursor": 0},
                "input.registered",
            )
        return {
            "bot_id": spec.bot_id,
            "snapshot_hash": data["snapshot_hash"],
            "registered": True,
        }

    @staticmethod
    def _accepted_receipt(context):
        required = {
            "schema_version",
            "request_id",
            "bot_id",
            "operation",
            "config_hash",
            "config_revision",
            "runtime_id",
            "owner_id",
            "owner_generation",
            "prior_generation",
            "prior_desired",
            "already",
        }
        if not isinstance(context, dict) or set(context) != required:
            raise ValueError
        if (
            type(context["schema_version"]) is not int
            or context["schema_version"] != 1
            or context["operation"] not in ("start", "stop")
            or type(context["already"]) is not bool
            or context["prior_desired"] not in ("running", "stopped")
            or type(context["prior_generation"]) is not int
            or context["prior_generation"] < 0
            or type(context["owner_generation"]) is not int
        ):
            raise ValueError
        desired = "running" if context["operation"] == "start" else "stopped"
        if context["already"] != (context["prior_desired"] == desired):
            raise ValueError
        generation = context["prior_generation"] + (
            1 if desired == "stopped" and not context["already"] else 0
        )
        if context["owner_generation"] != generation:
            raise ValueError
        return CommandReceipt(
            schema_version=1,
            bot_id=context["bot_id"],
            operation=context["operation"],
            request_id=context["request_id"],
            runtime_id=context["runtime_id"],
            owner_id=context["owner_id"],
            owner_generation=generation,
            config_revision=context["config_revision"],
            outcome="skipped" if context["already"] else "pending",
            reason="already_requested" if context["already"] else "desired_state_saved",
            metadata={"config_hash": context["config_hash"]},
        ).to_dict()

    def _replay_receipt(self, db, old, spec, operation, request_id, binding):
        if old["acceptance"] is None:
            raise ManagerError(
                "invalid_receipt",
                "Legacy runtime receipt lacks acceptance context; reconciliation is required.",
                4,
            )
        try:
            context = json.loads(old["acceptance"])
            receipt = json.loads(old["receipt"])
            if (
                context.get("bot_id") != spec.bot_id
                or context.get("operation") != operation
            ):
                raise ManagerError(
                    "identity_conflict",
                    "Request UUID already belongs to a different control.",
                )
            expected_receipt = self._accepted_receipt(context)
            run = db.execute(
                "SELECT spec,runtime_id FROM runs WHERE bot_id=?", (spec.bot_id,)
            ).fetchone()
            if run is None:
                raise ValueError
            if run["runtime_id"] != context["runtime_id"]:
                archive = db.execute(
                    "SELECT * FROM archives WHERE runtime_id=? AND bot_id=?",
                    (context["runtime_id"], spec.bot_id),
                ).fetchone()
                if archive is None:
                    raise ValueError
                archived = self._decode_archive(db, archive)
                run = {
                    "spec": canonical(archived["state"]["spec"]),
                    "runtime_id": archived["runtime_id"],
                }
            pinned = BotSpec.from_dict(json.loads(run["spec"]))
            binding = self._control_binding(pinned, operation, request_id)
            immutable = {
                "request_id": request_id,
                "bot_id": spec.bot_id,
                "operation": operation,
                "config_hash": pinned.config_hash,
                "config_revision": pinned.config_revision,
                "runtime_id": run["runtime_id"],
            }
            if (
                old["request_id"] != request_id
                or pinned.bot_id != spec.bot_id
                or old["binding"] != binding
                or canonical({key: context[key] for key in immutable})
                != canonical(immutable)
                or canonical(receipt) != canonical(expected_receipt)
                or fingerprint(
                    {"binding": binding, "acceptance": context, "receipt": receipt}
                )
                != old["checksum"]
            ):
                raise ValueError
            # Owner and generation belong to this immutable acceptance context,
            # not to the current worker after later stop/restart transitions.
            return expected_receipt
        except (KeyError, TypeError, ValueError, ManagerError) as exc:
            if isinstance(exc, ManagerError) and exc.code == "identity_conflict":
                raise
            raise ManagerError(
                "invalid_receipt",
                "Durable runtime receipt does not match its accepted request.",
                4,
            ) from exc

    @staticmethod
    def _control_binding(spec, operation, request_id):
        return fingerprint(
            {
                "request_id": request_id,
                "bot_id": spec.bot_id,
                "config_hash": spec.config_hash,
                "config_revision": spec.config_revision,
                "operation": operation,
            }
        )

    def control(self, spec: BotSpec, operation: str, request_id: str):
        try:
            if str(UUID(request_id)) != request_id or operation not in (
                "start",
                "stop",
            ):
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ManagerError(
                "invalid_input",
                "A canonical request UUID and supported operation are required.",
            ) from exc
        with self.connection(True, migrate_events=operation != "stop") as db:
            old = db.execute(
                "SELECT * FROM requests WHERE request_id=?", (request_id,)
            ).fetchone()
            if old:
                return self._replay_receipt(db, old, spec, operation, request_id, None)
            raw = db.execute(
                "SELECT * FROM runs WHERE bot_id=?", (spec.bot_id,)
            ).fetchone()
            if operation == "stop" and raw is not None:
                # A corrupt checkpoint must not prevent durable stop intent.
                # Validate identity independently; retain the corrupt bytes.
                row = dict(raw)
                try:
                    row["spec"] = BotSpec.from_dict(json.loads(row["spec"])).to_dict()
                    if (
                        row["spec"]["bot_id"] != spec.bot_id
                        or type(row["generation"]) is not int
                        or row["generation"] < 0
                    ):
                        raise ValueError
                except (ValueError, TypeError, KeyError) as exc:
                    raise ManagerError(
                        "corrupt_checkpoint",
                        "Runtime identity failed integrity validation.",
                        4,
                    ) from exc
            else:
                row = self._decode(db, raw)
            if row is None:
                raise ManagerError(
                    "runtime_not_available",
                    "Register explicit reference input before runtime control.",
                    3,
                )
            # Controls address the active run. A saved edit must not disable its stop.
            spec = BotSpec.from_dict(row["spec"])
            binding = self._control_binding(spec, operation, request_id)
            if operation == "start" and row["observed"] in ("failed", "blocked"):
                raise ManagerError(
                    "reconciliation_required",
                    "Failed or corrupt reference runs require investigation before restart.",
                    3,
                )
            prior_generation = row["generation"]
            prior_desired = row["desired"]
            desired = "running" if operation == "start" else "stopped"
            already = row["desired"] == desired
            capacity = MAX_REQUESTS + (
                STOP_RECEIPT_RESERVE if operation == "stop" and not already else 0
            )
            if db.execute("SELECT count(*) FROM requests").fetchone()[0] >= capacity:
                raise ManagerError(
                    "resource_limit", "Durable request capacity is exhausted.", 3
                )
            if not already:
                if (
                    desired == "running"
                    and db.execute(
                        "SELECT count(*) FROM runs WHERE desired='running'"
                    ).fetchone()[0]
                    >= MAX_INSTANCES
                ):
                    raise ManagerError(
                        "resource_limit",
                        "Reference instance admission capacity is exhausted.",
                        3,
                    )
                # Stop invalidates any tick already in flight before its acknowledgment.
                generation = row["generation"] + (1 if desired == "stopped" else 0)
                db.execute(
                    "UPDATE runs SET desired=?,generation=?,observed=?,reason=? WHERE bot_id=?",
                    (
                        desired,
                        generation,
                        "pending" if desired == "running" else "stopping",
                        "start_requested" if desired == "running" else "stop_requested",
                        spec.bot_id,
                    ),
                )
                row.update(generation=generation)
                self._event(db, row, operation + ".requested")
            acceptance = {
                "schema_version": 1,
                "request_id": request_id,
                "bot_id": spec.bot_id,
                "operation": operation,
                "config_hash": spec.config_hash,
                "config_revision": spec.config_revision,
                "runtime_id": row["runtime_id"],
                "owner_id": row["owner"],
                "owner_generation": row["generation"],
                "prior_generation": prior_generation,
                "prior_desired": prior_desired,
                "already": already,
            }
            receipt = self._accepted_receipt(acceptance)
            db.execute(
                "INSERT INTO requests(request_id,binding,receipt,checksum,acceptance) VALUES (?,?,?,?,?)",
                (
                    request_id,
                    binding,
                    canonical(receipt),
                    fingerprint(
                        {
                            "binding": binding,
                            "acceptance": acceptance,
                            "receipt": receipt,
                        }
                    ),
                    canonical(acceptance),
                ),
            )
            return receipt

    def quarantine_if_corrupt(self, bot_id: str) -> bool:
        """Confirm an integrity fault under the write lock before fencing a run."""
        with self.connection(True) as db:
            row = db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone()
            if row is None:
                return False
            try:
                self._decode(db, row)
            except ManagerError as exc:
                if exc.code not in INTEGRITY_ERRORS:
                    raise
                db.execute(
                    "UPDATE runs SET generation=generation+1,observed='blocked',reason='corrupt_checkpoint',pid=NULL WHERE bot_id=? AND observed!='blocked'",
                    (bot_id,),
                )
                return True
            return False

    def recover(self, owner: str):
        if not self.path.exists():
            return
        with self.connection(True) as db:
            for row in db.execute("SELECT * FROM runs").fetchall():
                try:
                    self._decode(db, row)
                except ManagerError as exc:
                    if exc.code not in INTEGRITY_ERRORS:
                        raise
                    db.execute(
                        "UPDATE runs SET generation=generation+1,observed='blocked',reason='corrupt_checkpoint',owner=?,pid=NULL,tick_started=NULL WHERE bot_id=?",
                        (owner, row["bot_id"]),
                    )
                    continue
                state = (
                    "stopped"
                    if row["desired"] == "stopped"
                    else row["observed"]
                    if row["observed"] in ("failed", "blocked")
                    else "recovering"
                )
                db.execute(
                    "UPDATE runs SET generation=generation+1,owner=?,pid=NULL,heartbeat=NULL,tick_started=NULL,observed=? WHERE bot_id=?",
                    (owner, state, row["bot_id"]),
                )

    def claim(self, bot_id: str, owner: str):
        with self.connection(True) as db:
            row = self._decode(
                db,
                db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone(),
            )
            if (
                not row
                or row["desired"] != "running"
                or row["observed"] in ("running", "waiting", "failed", "blocked")
                or row["retry_at"] > time.time()
            ):
                return None
            gen = row["generation"] + 1
            db.execute(
                "UPDATE runs SET generation=?,owner=?,observed='running',pid=NULL,heartbeat=?,tick_started=NULL,reason='worker_starting' WHERE bot_id=?",
                (gen, owner, time.time(), bot_id),
            )
            row.update(generation=gen)
            self._event(db, row, "worker.claimed")
            return gen

    @staticmethod
    def _fence(db, bot_id, generation):
        row = db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone()
        if (
            row is None
            or row["generation"] != generation
            or row["desired"] != "running"
            or row["observed"] in ("failed", "blocked")
        ):
            raise ManagerError(
                "stale_generation", "Worker no longer owns this runtime generation.", 3
            )
        return row

    def heartbeat(self, bot_id, generation, pid):
        with self.connection(True) as db:
            self._fence(db, bot_id, generation)
            db.execute(
                "UPDATE runs SET heartbeat=?,pid=? WHERE bot_id=?",
                (time.time(), pid, bot_id),
            )

    def mark_exhausted(self, bot_id, generation):
        """Restore an observed EOF after worker claim without another evaluation."""
        with self.connection(True) as db:
            row = self._decode(db, self._fence(db, bot_id, generation))
            if row["cursor"] != len(row["input"]["bars"]) or row["checkpoint"] is None:
                raise ManagerError(
                    "stale_cursor", "Reference input is not exhausted.", 3
                )
            if (
                row["observed"] != "waiting"
                or row["reason"] != "reference_input_exhausted"
            ):
                db.execute(
                    "UPDATE runs SET observed='waiting',reason='reference_input_exhausted',tick_started=NULL WHERE bot_id=?",
                    (bot_id,),
                )
                self._event(db, row, "worker.input_exhausted")

    def begin_tick(self, bot_id, generation):
        with self.connection(True) as db:
            row = self._fence(db, bot_id, generation)
            if row["tick_started"] is not None:
                raise ManagerError(
                    "tick_in_progress", "Only one tick per bot may execute.", 3
                )
            db.execute(
                "UPDATE runs SET tick_started=?,reason=? WHERE bot_id=?",
                (time.time(), "evaluating_reference_prefix", bot_id),
            )
            self._event(db, row, "tick.intent")

    def commit_tick(
        self, bot_id, generation, expected_cursor, checkpoint, *, before_commit=None
    ):
        from .strategies import validate_checkpoint

        with self.connection(True) as db:
            row = self._decode(db, self._fence(db, bot_id, generation))
            validate_checkpoint(
                BotSpec.from_dict(row["spec"]),
                row["input"],
                checkpoint,
                code="reconciliation_required",
            )
            if (
                row["cursor"] != expected_cursor
                or checkpoint["cursor"] <= expected_cursor
                or checkpoint["cursor"] > len(row["input"]["bars"])
            ):
                raise ManagerError(
                    "stale_cursor",
                    "Tick cursor no longer matches the durable checkpoint.",
                    3,
                )
            old = row["checkpoint"]["fills"] if row["checkpoint"] else []
            if checkpoint["fills"][: len(old)] != old:
                raise ManagerError(
                    "reconciliation_required",
                    "Replay results disagree with the durable run.",
                    4,
                )
            for i, fill in enumerate(checkpoint["fills"][len(old) :], len(old)):
                db.execute(
                    "INSERT INTO fills VALUES (?,?,?)", (bot_id, i, canonical(fill))
                )
            done = checkpoint["cursor"] == len(row["input"]["bars"])
            db.execute(
                "UPDATE runs SET cursor=?,checkpoint=?,checkpoint_hash=?,tick_started=NULL,evaluated=?,observed=?,reason=? WHERE bot_id=?",
                (
                    checkpoint["cursor"],
                    canonical(checkpoint),
                    fingerprint(checkpoint),
                    time.time(),
                    "waiting" if done else "running",
                    "reference_input_exhausted" if done else "reference_tick_completed",
                    bot_id,
                ),
            )
            row.update(cursor=checkpoint["cursor"])
            self._event(db, row, "tick.committed")
            if before_commit:
                before_commit()

    def commit_progress(
        self, bot_id, generation, expected_hash, data, checkpoint, *, before_commit=None
    ):
        """Commit a prospective source cursor and the account in one transaction."""
        from .strategies import validate_checkpoint

        validate_snapshot(data)
        with self.connection(True) as db:
            row = self._decode(db, self._fence(db, bot_id, generation))
            previous = row["input"]
            if previous["snapshot_hash"] != expected_hash:
                raise ManagerError(
                    "stale_cursor", "Prospective source cursor changed.", 3
                )
            old_state, new_state = previous["prospective"], data["prospective"]
            transition = data.get("prior_segment") != previous.get("prior_segment")
            if transition:
                from .oracle_data import rollover

                prepared = rollover(previous, row["checkpoint"])
                if prepared is previous or prepared.get("prior_segment") != data.get(
                    "prior_segment"
                ):
                    raise ManagerError(
                        "reconciliation_required",
                        "Segment transition differs from durable predecessor.",
                        4,
                    )
                segment_body = {"input": previous, "checkpoint": row["checkpoint"]}
                fill_end = db.execute(
                    "SELECT count(*) FROM fills WHERE bot_id=?", (bot_id,)
                ).fetchone()[0]
                db.execute(
                    "INSERT INTO segments VALUES (?,?,?,?)",
                    (
                        row["runtime_id"],
                        data["prior_segment"],
                        canonical(segment_body),
                        fill_end,
                    ),
                )
                comparison = prepared
            else:
                comparison = previous
            compared_state = comparison["prospective"]
            if (
                data["identity"] != previous["identity"]
                or data["descriptor"] != previous["descriptor"]
                or data["origin_hash"] != previous["origin_hash"]
                or data.get("bar_offset", 0) != comparison.get("bar_offset", 0)
                or data["bars"][: len(comparison["bars"])] != comparison["bars"]
                or new_state["observations"][: len(compared_state["observations"])]
                != compared_state["observations"]
                or new_state["evaluation_ranges"][
                    : len(compared_state["evaluation_ranges"])
                ]
                != compared_state["evaluation_ranges"]
                or new_state["cursor"] < old_state["cursor"]
            ):
                raise ManagerError(
                    "reconciliation_required",
                    "Prospective evidence cannot rewrite a pinned prefix.",
                    4,
                )
            cursor = checkpoint["cursor"] if checkpoint is not None else 0
            if (
                cursor != data.get("bar_offset", 0) + len(data["bars"])
                or cursor < row["cursor"]
            ):
                raise ManagerError(
                    "stale_cursor", "Prospective account and source bars disagree.", 3
                )
            old_fills = (
                row["checkpoint"]["fills"]
                if row["checkpoint"] and not transition
                else []
            )
            if checkpoint is not None:
                validate_checkpoint(BotSpec.from_dict(row["spec"]), data, checkpoint)
                if checkpoint["fills"][: len(old_fills)] != old_fills:
                    raise ManagerError(
                        "reconciliation_required",
                        "Prospective fills changed across restart.",
                        4,
                    )
                fill_end = db.execute(
                    "SELECT count(*) FROM fills WHERE bot_id=?", (bot_id,)
                ).fetchone()[0]
                for index, fill in enumerate(
                    checkpoint["fills"][len(old_fills) :], fill_end
                ):
                    db.execute(
                        "INSERT INTO fills VALUES (?,?,?)",
                        (bot_id, index, canonical(fill)),
                    )
            changed = cursor > row["cursor"]
            reason = new_state["health"]
            db.execute(
                "UPDATE runs SET input=?,cursor=?,checkpoint=?,checkpoint_hash=?,tick_started=NULL,evaluated=?,observed='waiting',reason=? WHERE bot_id=?",
                (
                    canonical(data),
                    cursor,
                    canonical(checkpoint) if checkpoint is not None else None,
                    fingerprint(checkpoint) if checkpoint is not None else None,
                    time.time() if changed else row["evaluated"],
                    reason,
                    bot_id,
                ),
            )
            row.update(cursor=cursor)
            if (
                changed
                or old_state["cursor"] != new_state["cursor"]
                or old_state["health"] != reason
            ):
                self._event(db, row, "prospective.committed")
            if before_commit:
                before_commit()

    def failed(self, bot_id, generation, reason):
        with self.connection(True) as db:
            row = db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone()
            if (
                row is None
                or row["generation"] != generation
                or row["desired"] != "running"
            ):
                return
            now = time.time()
            failures = [
                t for t in json.loads(row["failures"]) if now - t < FAILURE_WINDOW
            ] + [now]
            state = "failed" if len(failures) >= 3 else "recovering"
            db.execute(
                "UPDATE runs SET generation=generation+1,observed=?,reason=?,failures=?,retry_at=?,pid=NULL,tick_started=NULL WHERE bot_id=?",
                (
                    state,
                    reason,
                    canonical(failures),
                    now + RESTART_DELAYS[min(len(failures) - 1, 2)],
                    bot_id,
                ),
            )
            self._event(db, row, "worker.failed")

    def stopped(self, bot_id):
        with self.connection(True) as db:
            db.execute(
                "UPDATE runs SET observed='stopped',pid=NULL,tick_started=NULL,reason='stopped_positions_retained' WHERE bot_id=? AND desired='stopped'",
                (bot_id,),
            )

    def _decode_archive(self, db, archive):
        try:
            body = json.loads(archive["body"])
            if (
                set(body) != {"schema_version", "archived_at", "run", "fills", "events"}
                or type(body["schema_version"]) is not int
                or body["schema_version"] != 1
                or fingerprint(body) != archive["checksum"]
                or body["run"]["bot_id"] != archive["bot_id"]
                or body["run"]["runtime_id"] != archive["runtime_id"]
            ):
                raise ValueError
            fills = []
            for index, fill in enumerate(body["fills"]):
                if fill["bot_id"] != archive["bot_id"] or fill["sequence"] != index:
                    raise ValueError
                fills.append(json.loads(fill["body"]))
            state = self._decode(db, body["run"], archived_fills=fills)
            if any(event["bot_id"] != archive["bot_id"] for event in body["events"]):
                raise ValueError
            return {
                "schema_version": 1,
                "runtime_id": archive["runtime_id"],
                "archived": True,
                "archived_at": body["archived_at"],
                "source": "coinbase_proxy",
                "mode": "reference_paper",
                "state": state,
                "events": body["events"],
            }
        except (ValueError, KeyError, TypeError) as exc:
            raise ManagerError(
                "corrupt_checkpoint", "Archived runtime evidence does not reconcile.", 4
            ) from exc

    def has_adoption_request(self, request_id):
        if not self.path.exists():
            return False
        with self.connection() as db:
            return (
                db.execute("PRAGMA user_version").fetchone()[0] >= 3
                and db.execute(
                    "SELECT 1 FROM adoption_requests WHERE request_id=?", (request_id,)
                ).fetchone()
                is not None
            )

    def history(self, bot_id, revision=None):
        if not self.path.exists():
            return []
        with self.connection() as db:
            runs = []
            if db.execute("PRAGMA user_version").fetchone()[0] >= 3:
                runs = [
                    self._decode_archive(db, row)
                    for row in db.execute(
                        "SELECT * FROM archives WHERE bot_id=? ORDER BY rowid",
                        (bot_id,),
                    )
                ]
            row = self._decode(
                db,
                db.execute("SELECT * FROM runs WHERE bot_id=?", (bot_id,)).fetchone(),
            )
            if row:
                runs.append(
                    {
                        "schema_version": 1,
                        "runtime_id": row["runtime_id"],
                        "archived": False,
                        "archived_at": None,
                        "source": "coinbase_proxy",
                        "mode": "reference_paper",
                        "state": row,
                        "events": self._run_events(db, bot_id, row["runtime_id"]),
                    }
                )
            for run in runs:
                run["control_receipts"] = []
            by_runtime = {run["runtime_id"]: run for run in runs}
            for receipt_row in db.execute("SELECT * FROM requests"):
                try:
                    receipt = json.loads(receipt_row["receipt"])
                    if (
                        receipt.get("bot_id") == bot_id
                        and receipt.get("runtime_id") in by_runtime
                    ):
                        # Preserve legacy rows for inspection without granting them replay authority.
                        run = by_runtime[receipt["runtime_id"]]
                        acceptance = (
                            receipt_row["acceptance"]
                            if db.execute("PRAGMA user_version").fetchone()[0] >= 2
                            else None
                        )
                        if acceptance is not None:
                            self._replay_receipt(
                                db,
                                receipt_row,
                                BotSpec.from_dict(run["state"]["spec"]),
                                receipt["operation"],
                                receipt_row["request_id"],
                                None,
                            )
                        run["control_receipts"].append(
                            {
                                "receipt": receipt,
                                "replay_proven": acceptance is not None,
                            }
                        )
                except (ValueError, KeyError, TypeError) as exc:
                    raise ManagerError(
                        "invalid_receipt", "Historical control receipt is invalid.", 4
                    ) from exc
            return [
                run
                for run in runs
                if revision in (None, run["state"]["spec"]["config_revision"])
            ]

    @staticmethod
    def adoption_blockers(row, worker_alive=False):
        """Pure conservative UI projection; apply also verifies replay economics."""
        if row is None:
            return []
        blockers = []
        if row["desired"] != "stopped":
            blockers.append("runtime_not_stopped")
        if worker_alive:
            blockers.append("worker_lock_held")
        if row["observed"] in ("failed", "blocked"):
            blockers.append("runtime_requires_reconciliation")
        if row["tick_started"] is not None:
            blockers.append("unresolved_tick_intent")
        cp = row["checkpoint"]
        if cp is not None:
            if cp.get("lots") != [] or cp.get("exposure_quote") != 0:
                blockers.append("open_reference_exposure")
            required = (
                "equity_quote",
                "cash_quote",
                "realized_net_pnl_quote",
                "unrealized_net_pnl_quote",
                "fees_quote",
                "slippage_quote",
                "carry_paid_quote",
                "carry_accrued_quote",
            )
            import math

            if (
                any(
                    type(cp.get(key)) not in (int, float) or not math.isfinite(cp[key])
                    for key in required
                )
                or cp["carry_accrued_quote"] != 0
                or abs(cp["unrealized_net_pnl_quote"]) > 1e-9
            ):
                blockers.append("unresolved_reference_economics")
        return blockers

    def apply(
        self, identity, *, descriptor=None, expected_revision=None, request_id=None
    ):
        from .data import load_recording
        from .store import ManagerStore
        from .strategies import evaluate, validate_registration
        from .worker import lifetime_lock

        request_id = request_identity(request_id, expected_revision)
        store = ManagerStore(self.home)
        initial = store.get_spec(identity)
        if initial is None:
            raise ManagerError("bot_not_found", "Bot identity was not found.")
        if descriptor is not None and (
            not isinstance(descriptor, str) or not descriptor
        ):
            raise ManagerError("invalid_input", "Descriptor must be a file path.")
        changes = {
            "descriptor_ref": fingerprint(descriptor)
            if descriptor is not None
            else None
        }
        request = request_body(
            "apply", initial.bot_id, changes, expected_revision, request_id
        )
        with mutation_lock(self.home), self.connection(True) as db:
            if store.has_edit_request(request_id):
                raise ManagerError(
                    "identity_conflict", "Request UUID already belongs to an edit."
                )
            old = db.execute(
                "SELECT * FROM adoption_requests WHERE request_id=?", (request_id,)
            ).fetchone()
            replay = replay_mutation(old, request)
            if replay is not None:
                self._validate_adoption_receipt(db, replay, store)
                return replay
            spec = store.get_spec(initial.bot_id)
            check_revision(spec, expected_revision)
            raw = db.execute(
                "SELECT * FROM runs WHERE bot_id=?", (spec.bot_id,)
            ).fetchone()
            row = self._decode(db, raw)
            data = row["input"] if row else None
            if descriptor is not None:
                try:
                    with Path(descriptor).open("rb") as stream:
                        content = stream.read(65537)
                    if len(content) > 65536:
                        raise ValueError
                    data = load_recording(
                        json.loads(content), strategy_id=spec.strategy_id
                    )
                except (OSError, ValueError, TypeError) as exc:
                    raise ManagerError(
                        "input_unavailable",
                        "Input descriptor is missing or invalid.",
                        3,
                    ) from exc
            if (
                row
                and spec.config_hash == row["spec"]["config_hash"]
                and data["snapshot_hash"] == row["input"]["snapshot_hash"]
            ):
                result = mutation_result(
                    request,
                    spec,
                    spec,
                    active_runtime_id=row["runtime_id"],
                    owner_generation=row["generation"],
                    input_snapshot_hash=data.get("origin_hash", data["snapshot_hash"]),
                    reason="revision_already_active",
                    changed=False,
                )
            elif data is None:
                result = mutation_result(
                    request,
                    spec,
                    spec,
                    reason="draft_uses_saved_revision",
                    changed=False,
                )
            else:
                # A new prospective account needs a new explicit activation,
                # never the prior account's already observed bars.
                if data.get("prospective") is not None and (
                    descriptor is None or data["bars"]
                ):
                    raise ManagerError(
                        "incompatible_input",
                        "Prospective adoption requires a fresh explicit source activation.",
                        3,
                    )
                # Strict capture/cost/context checks precede archive or admission.
                try:
                    validate_registration(spec, data)
                except ManagerError as exc:
                    raise ManagerError(
                        "incompatible_input",
                        "Saved settings require compatible explicit input, capital, timeframe and reference costs.",
                        3,
                    ) from exc
                if row and self.adoption_blockers(row):
                    raise ManagerError(
                        "adoption_blocked",
                        "Adoption requires stopped intent, no worker, no exposure and fully reconciled reference economics.",
                        3,
                    )
                # A self-consistent checksum is not proof of a zero-exposure boundary.
                if (
                    row
                    and row["checkpoint"] is not None
                    and canonical(
                        evaluate(
                            BotSpec.from_dict(row["spec"]), row["input"], row["cursor"]
                        )
                    )
                    != canonical(row["checkpoint"])
                ):
                    raise ManagerError(
                        "corrupt_checkpoint",
                        "Reference economics do not match the pinned replay.",
                        4,
                    )
                try:
                    with lifetime_lock(self.home / "locks" / (spec.bot_id + ".lock")):
                        result = self._admit_revision(db, raw, row, spec, data, request)
                except BlockingIOError as exc:
                    raise ManagerError(
                        "adoption_blocked",
                        "The reference worker still holds its lifetime lock.",
                        3,
                    ) from exc
            save_mutation(db, "adoption_requests", request, result)
            return result

    def _admit_revision(self, db, raw, row, spec, data, request):
        generation = row["generation"] + 1 if row else 0
        prior_id = row["runtime_id"] if row else None
        if row:
            body = {
                "schema_version": 1,
                "archived_at": time.time(),
                "run": dict(raw),
                "fills": [
                    dict(fill)
                    for fill in db.execute(
                        "SELECT * FROM fills WHERE bot_id=? ORDER BY sequence",
                        (spec.bot_id,),
                    )
                ],
                "events": self._run_events(db, spec.bot_id, prior_id),
            }
            db.execute(
                "INSERT INTO archives VALUES (?,?,?,?)",
                (prior_id, spec.bot_id, canonical(body), fingerprint(body)),
            )
            db.execute("DELETE FROM fills WHERE bot_id=?", (spec.bot_id,))
            db.execute("DELETE FROM runs WHERE bot_id=?", (spec.bot_id,))
        elif db.execute("SELECT count(*) FROM runs").fetchone()[0] >= MAX_INSTANCES:
            raise ManagerError(
                "resource_limit", "Reference instance capacity is exhausted.", 3
            )
        runtime_id = str(uuid4())
        db.execute(
            "INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                spec.bot_id,
                canonical(spec.to_dict()),
                canonical(data),
                runtime_id,
                "stopped",
                "stopped",
                generation,
                None,
                None,
                None,
                None,
                None,
                0,
                None,
                None,
                "[]",
                0.0,
                "saved_revision_applied",
            ),
        )
        self._event(
            db,
            {"bot_id": spec.bot_id, "generation": generation, "cursor": 0},
            "revision.applied",
        )
        return mutation_result(
            request,
            spec,
            spec,
            active_runtime_id=runtime_id,
            prior_runtime_id=prior_id,
            owner_generation=generation,
            input_snapshot_hash=data.get("origin_hash", data["snapshot_hash"]),
            reason="saved_revision_applied",
            changed=True,
        )

    def _validate_adoption_receipt(self, db, result, store):
        receipt = result["receipt"]
        versions = store.history(receipt["bot_id"], receipt["accepted_revision"])
        if not versions or canonical(versions[0]["spec"]) != canonical(result["spec"]):
            raise ManagerError(
                "invalid_receipt",
                "Adoption receipt references an invalid specification.",
                4,
            )
        runtime_id = receipt["active_runtime_id"]
        if runtime_id is None:
            if (
                receipt["reason"] != "draft_uses_saved_revision"
                or receipt["outcome"] != "skipped"
            ):
                raise ManagerError(
                    "invalid_receipt", "Draft adoption receipt is inconsistent.", 4
                )
            return
        raw = db.execute(
            "SELECT * FROM runs WHERE bot_id=? AND runtime_id=?",
            (receipt["bot_id"], runtime_id),
        ).fetchone()
        if raw is not None:
            spec = BotSpec.from_dict(json.loads(raw["spec"]))
            input_data = json.loads(raw["input"])
            input_hash = input_data.get("origin_hash", input_data["snapshot_hash"])
        else:
            archive = db.execute(
                "SELECT * FROM archives WHERE bot_id=? AND runtime_id=?",
                (receipt["bot_id"], runtime_id),
            ).fetchone()
            if archive is None:
                raise ManagerError(
                    "invalid_receipt", "Adoption runtime evidence is missing.", 4
                )
            archived = self._decode_archive(db, archive)["state"]
            spec = BotSpec.from_dict(archived["spec"])
            input_hash = archived["input"].get(
                "origin_hash", archived["input"]["snapshot_hash"]
            )
        if (
            spec.config_hash != receipt["accepted_hash"]
            or spec.config_revision != receipt["accepted_revision"]
            or input_hash != receipt["input_snapshot_hash"]
        ):
            raise ManagerError(
                "invalid_receipt", "Adoption receipt disagrees with pinned runtime.", 4
            )
        if receipt["prior_runtime_id"] is not None:
            archive = db.execute(
                "SELECT * FROM archives WHERE bot_id=? AND runtime_id=?",
                (receipt["bot_id"], receipt["prior_runtime_id"]),
            ).fetchone()
            if (
                archive is None
                or self._decode_archive(db, archive)["state"]["generation"] + 1
                != receipt["owner_generation"]
            ):
                raise ManagerError(
                    "invalid_receipt",
                    "Adoption receipt disagrees with archived generation.",
                    4,
                )

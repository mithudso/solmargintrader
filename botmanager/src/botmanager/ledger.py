"""Transactional intent, generation fencing and reference-paper fill ledger.

The immutable specification database remains version 1. This separate journal
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


class RuntimeLedger:
    def __init__(self, home: Path | None = None):
        self.home = Path(home).absolute() if home is not None else data_home()
        self.path = self.home / "runtime.sqlite3"

    @contextmanager
    def connection(self, write: bool = False) -> Iterator[sqlite3.Connection]:
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
            if write:
                db.execute("BEGIN IMMEDIATE")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0 and write:
                db.execute(
                    "CREATE TABLE runs (bot_id TEXT PRIMARY KEY, spec TEXT NOT NULL, input TEXT NOT NULL, runtime_id TEXT NOT NULL, desired TEXT NOT NULL, observed TEXT NOT NULL, generation INTEGER NOT NULL, owner TEXT, pid INTEGER, heartbeat REAL, tick_started REAL, evaluated REAL, cursor INTEGER NOT NULL, checkpoint TEXT, checkpoint_hash TEXT, failures TEXT NOT NULL, retry_at REAL NOT NULL, reason TEXT NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE fills (bot_id TEXT NOT NULL REFERENCES runs(bot_id), sequence INTEGER NOT NULL, body TEXT NOT NULL, PRIMARY KEY(bot_id,sequence))"
                )
                db.execute(
                    "CREATE TABLE requests (request_id TEXT PRIMARY KEY, binding TEXT NOT NULL, receipt TEXT NOT NULL, checksum TEXT NOT NULL)"
                )
                db.execute(
                    "CREATE TABLE events (sequence INTEGER PRIMARY KEY, bot_id TEXT NOT NULL, generation INTEGER NOT NULL, kind TEXT NOT NULL, cursor INTEGER NOT NULL, at REAL NOT NULL)"
                )
                db.execute("PRAGMA user_version=1")
                version = 1
            if version != 1:
                raise ManagerError(
                    "incompatible_store", "Runtime journal schema is incompatible.", 4
                )
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

    @staticmethod
    def _event(db, row, kind):
        db.execute(
            "INSERT INTO events(bot_id,generation,kind,cursor,at) VALUES (?,?,?,?,?)",
            (row["bot_id"], row["generation"], kind, row["cursor"], time.time()),
        )

    def _decode(self, db, row):
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
            checkpoint = (
                json.loads(row["checkpoint"]) if row["checkpoint"] is not None else None
            )
            result["checkpoint"] = checkpoint
            fills = [
                json.loads(f["body"])
                for f in db.execute(
                    "SELECT body FROM fills WHERE bot_id=? ORDER BY sequence",
                    (row["bot_id"],),
                )
            ]
            if checkpoint is None:
                if row["cursor"] != 0 or fills or row["checkpoint_hash"] is not None:
                    raise ValueError
            elif (
                fingerprint(checkpoint) != row["checkpoint_hash"]
                or checkpoint["cursor"] != row["cursor"]
                or checkpoint["fills"] != fills
                or checkpoint["identity"]["config_hash"] != spec.config_hash
                or checkpoint["identity"]["snapshot_hash"]
                != result["input"]["snapshot_hash"]
            ):
                raise ValueError
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

    def ids(self):
        if not self.path.exists():
            return []
        with self.connection() as db:
            return [r[0] for r in db.execute("SELECT bot_id FROM runs ORDER BY bot_id")]

    def fills(self, bot_id):
        row = self.get(bot_id)
        return row["checkpoint"]["fills"] if row and row["checkpoint"] else []

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
        from .strategies.grid import evaluate

        # Validate capability, sizing and economics before any durable registration.
        evaluate(spec, data, 1)
        with self.connection(True) as db:
            row = self._decode(
                db,
                db.execute(
                    "SELECT * FROM runs WHERE bot_id=?", (spec.bot_id,)
                ).fetchone(),
            )
            if row:
                if (
                    row["input"]["snapshot_hash"] != data["snapshot_hash"]
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
        binding = fingerprint(
            {
                "bot_id": spec.bot_id,
                "config_hash": spec.config_hash,
                "operation": operation,
            }
        )
        with self.connection(True) as db:
            old = db.execute(
                "SELECT * FROM requests WHERE request_id=?", (request_id,)
            ).fetchone()
            if old:
                if old["binding"] != binding:
                    raise ManagerError(
                        "identity_conflict",
                        "Request UUID already belongs to a different control.",
                    )
                receipt = json.loads(old["receipt"])
                if (
                    fingerprint({"binding": binding, "receipt": receipt})
                    != old["checksum"]
                ):
                    raise ManagerError(
                        "invalid_receipt",
                        "Durable control receipt failed integrity validation.",
                        4,
                    )
                return CommandReceipt.from_dict(receipt).to_dict()
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
            if row["spec"]["config_hash"] != spec.config_hash:
                raise ManagerError(
                    "identity_conflict",
                    "Saved runtime configuration does not match the specification.",
                )
            if operation == "start" and row["observed"] in ("failed", "blocked"):
                raise ManagerError(
                    "reconciliation_required",
                    "Failed or corrupt reference runs require investigation before restart.",
                    3,
                )
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
                    >= MAX_ACTIVE
                ):
                    raise ManagerError(
                        "resource_limit",
                        "Four reference workers are already admitted.",
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
            receipt = CommandReceipt(
                schema_version=1,
                bot_id=spec.bot_id,
                operation=operation,
                request_id=request_id,
                runtime_id=row["runtime_id"],
                owner_id=row["owner"],
                owner_generation=row["generation"],
                config_revision=spec.config_revision,
                outcome="skipped" if already else "pending",
                reason="already_requested" if already else "desired_state_saved",
                metadata={"config_hash": spec.config_hash},
            ).to_dict()
            db.execute(
                "INSERT INTO requests VALUES (?,?,?,?)",
                (
                    request_id,
                    binding,
                    canonical(receipt),
                    fingerprint({"binding": binding, "receipt": receipt}),
                ),
            )
            return receipt

    def recover(self, owner: str):
        if not self.path.exists():
            return
        with self.connection(True) as db:
            for row in db.execute("SELECT * FROM runs").fetchall():
                try:
                    self._decode(db, row)
                except ManagerError:
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
        with self.connection(True) as db:
            row = self._decode(db, self._fence(db, bot_id, generation))
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
            if (
                checkpoint["fills"][: len(old)] != old
                or checkpoint["identity"]["config_hash"] != row["spec"]["config_hash"]
                or checkpoint["identity"]["snapshot_hash"]
                != row["input"]["snapshot_hash"]
            ):
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

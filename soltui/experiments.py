"""Durable simulation evidence, bounded search spaces and read-only external comparisons.

A run spec is immutable. A cell is a completed measurement, never a progress hint.
Holdout reservations are a separate temporal ledger so changing a search fingerprint
cannot reopen dates that another experiment has already inspected.
"""
from __future__ import annotations

import csv
import hashlib
import io
import itertools
import json
import math
import sqlite3
import statistics
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from . import config
from .evidence_identity import ExperimentError, canonical, fingerprint
from .manager_evidence import ManagerEvidence

_UNSET = object()


def _candidate_map(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for i, row in enumerate(spec.get("candidates", [])):
        if not isinstance(row, dict):
            raise ExperimentError("each candidate must be a configuration object")
        candidate_id = str(row.get("id", i)) if "config" in row else str(i)
        cfg = row.get("config", row)
        if not isinstance(cfg, dict) or not candidate_id or candidate_id in out:
            raise ExperimentError("candidate IDs must be unique and configurations must be objects")
        canonical(cfg)
        out[candidate_id] = cfg
    return out


def _timestamp(value: Any) -> float:
    if isinstance(value, bool) or value in (None, ""):
        raise ExperimentError("window start and end must be explicit timestamps")
    try:
        if isinstance(value, (float, int)):
            result = float(value)
        else:
            text = str(value)
            stamp = datetime.fromisoformat(text)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=UTC)
            result = stamp.timestamp()
    except (ValueError, OverflowError, OSError) as exc:
        raise ExperimentError(f"invalid window timestamp: {value!r}") from exc
    if not math.isfinite(result):
        raise ExperimentError("window timestamp must be finite")
    return result


class ExperimentStore(ManagerEvidence):
    """Short-lived SQLite connections permit safe thread/process use of one store.

    Callers coordinate expensive execution with a process lock. Transactions here
    independently protect evidence immutability and the global holdout ledger.
    """

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else config.CONFIG_DIR / "experiments"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "experiments.sqlite3"
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, spec TEXT NOT NULL, status TEXT NOT NULL,
                    summary TEXT, error TEXT, progress TEXT, frozen_candidate TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS cells (
                    run_id TEXT NOT NULL REFERENCES runs(id), candidate_id TEXT NOT NULL,
                    cell_key TEXT NOT NULL, record TEXT NOT NULL,
                    PRIMARY KEY (run_id, candidate_id, cell_key));
                CREATE TABLE IF NOT EXISTS holdouts (
                    bot TEXT NOT NULL, coin TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(id), candidate_id TEXT NOT NULL,
                    context TEXT NOT NULL, sealed_at REAL,
                    PRIMARY KEY (bot, coin, start, end));
                CREATE INDEX IF NOT EXISTS holdouts_dates ON holdouts(bot, coin, start, end);
                CREATE TABLE IF NOT EXISTS exposures (
                    bot TEXT NOT NULL, coin TEXT NOT NULL, start REAL NOT NULL, end REAL NOT NULL,
                    run_id TEXT NOT NULL REFERENCES runs(id),
                    PRIMARY KEY (bot, coin, start, end, run_id));
                CREATE INDEX IF NOT EXISTS exposures_dates ON exposures(bot, coin, start, end);
            """)
            self._manager_schema(db)
            # A durable seal survives the temporary lifecycle states used when
            # reviewing a completed run before adopting its frozen result.
            db.execute("BEGIN IMMEDIATE")
            columns = {row[1] for row in db.execute("PRAGMA table_info(holdouts)")}
            if "sealed_at" not in columns:
                db.execute("ALTER TABLE holdouts ADD COLUMN sealed_at REAL")
                db.execute("""UPDATE holdouts SET sealed_at=(SELECT updated_at FROM runs WHERE id=run_id)
                              WHERE run_id IN (SELECT id FROM runs WHERE status='completed')""")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def _run(row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            raise ExperimentError("experiment does not exist")
        result = dict(row)
        for key in ("spec", "summary", "progress"):
            result[key] = json.loads(result[key]) if result[key] is not None else None
        return result

    def create_run(self, spec: dict[str, Any], run_id: str | None = None) -> str:
        from .bots import BOTS

        if not isinstance(spec, dict) or spec.get("source") not in ("native", "tradingview"):
            raise ExperimentError("run source must be native or tradingview")
        if not isinstance(spec.get("bot"), str) or not spec["bot"]:
            raise ExperimentError("run requires a bot")
        if spec["source"] == "native" and spec["bot"] not in BOTS:
            raise ExperimentError("native experiment requires a known bot")
        if not _candidate_map(spec):
            raise ExperimentError("run requires at least one candidate")
        encoded = canonical(spec)
        run_id = run_id or uuid.uuid4().hex
        if not isinstance(run_id, str) or not run_id or len(run_id) > 200:
            raise ExperimentError("invalid experiment ID")
        now = time.time()
        with self._connect() as db:
            try:
                db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?)",
                           (run_id, encoded, "created", None, None, None, None, now, now))
            except sqlite3.IntegrityError:
                row = db.execute("SELECT spec FROM runs WHERE id=?", (run_id,)).fetchone()
                if row is None or row[0] != encoded:
                    raise ExperimentError("experiment ID already binds different evidence") from None
        return run_id

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as db:
            return self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())

    def list_runs(self, *, bot: str | None = None, source: str | None = None,
                  limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
            raise ExperimentError("run list limit must be in [1, 10000]")
        with self._connect() as db:
            filters, parameters = [], []
            for key, value in (("bot", bot), ("source", source)):
                if value is not None:
                    filters.append(f"json_extract(spec,'$.{key}')=?")
                    parameters.append(value)
            where = " WHERE " + " AND ".join(filters) if filters else ""
            rows = db.execute("SELECT * FROM runs" + where + " ORDER BY created_at DESC LIMIT ?",
                              (*parameters, limit)).fetchall()
        return [self._run(row) for row in rows]

    def update_run(self, run_id: str, *, status: str | None = None, summary: Any = None,
                   error: Any = _UNSET, progress: Any = None) -> dict[str, Any]:
        if status is not None and (not isinstance(status, str) or not status):
            raise ExperimentError("run status must be a nonempty string")
        fields: dict[str, Any] = {"updated_at": time.time()}
        for key, value in (("status", status), ("summary", summary), ("error", error), ("progress", progress)):
            if (key == "error" and value is not _UNSET) or (key != "error" and value is not None):
                if key == "error" and value is not None and not isinstance(value, str):
                    raise ExperimentError("run error must be a string or null")
                fields[key] = canonical(value) if key in ("summary", "progress") else value
        with self._connect() as db:
            cursor = db.execute("UPDATE runs SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
                                (*fields.values(), run_id))
            if cursor.rowcount != 1:
                raise ExperimentError("experiment does not exist")
        return self.get_run(run_id)

    def transition_run(self, run_id: str, status: str, *, expected: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
        """Compare-and-set lifecycle state without discarding a concurrent control request."""
        if not isinstance(status, str) or not status:
            raise ExperimentError("run status must be a nonempty string")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            applied = expected is None or run["status"] in expected
            if applied:
                db.execute("UPDATE runs SET status=?,updated_at=? WHERE id=?", (status, time.time(), run_id))
        return {**self.get_run(run_id), "transition_applied": applied}

    def settle_run(self, run_id: str, *, status: str | None = None,
                   expected: list[str] | tuple[str, ...] = (), error: Any = _UNSET) -> dict[str, Any]:
        """Acknowledge control or conditionally settle an exit in one transaction.

        Pause/cancel requests take precedence over an error or a dead-worker
        observation. Terminal states remain unchanged unless explicitly expected.
        """
        if status is not None and (not isinstance(status, str) or not status):
            raise ExperimentError("run status must be a nonempty string")
        if error is not _UNSET and error is not None and not isinstance(error, str):
            raise ExperimentError("run error must be a string or null")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            next_state = {"pause_requested": "paused", "cancel_requested": "cancelled"}.get(run["status"])
            if next_state is None and status is not None and run["status"] in expected:
                next_state = status
            if next_state is not None:
                if error is _UNSET:
                    db.execute("UPDATE runs SET status=?,updated_at=? WHERE id=?",
                               (next_state, time.time(), run_id))
                else:
                    db.execute("UPDATE runs SET status=?,error=?,updated_at=? WHERE id=?",
                               (next_state, error, time.time(), run_id))
        return self.get_run(run_id)

    def finalize_run(self, run_id: str, summary: dict[str, Any], *,
                     apply: Callable[[dict[str, Any]], dict[str, Any]] | None = None) -> dict[str, Any]:
        """Seal a final verdict and optional config write against control requests.

        The optional callback performs only a short, idempotent local config write.
        It must not write this store: the transaction serializes it with pause/cancel.
        The runner owns crash recovery between that file write and the SQL commit.
        """
        canonical(summary)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            if run["spec"]["source"] != "native":
                raise ExperimentError("imported evidence cannot finalize native optimization")
            state = run["status"]
            if state in ("pause_requested", "cancel_requested"):
                status = "paused" if state == "pause_requested" else "cancelled"
                db.execute("UPDATE runs SET status=?,updated_at=? WHERE id=?", (status, time.time(), run_id))
            elif state == "completed":
                pass  # Idempotent retry never applies a configuration twice.
            elif state not in ("running", "validating", "finalizing", "explored"):
                raise ExperimentError(f"cannot finalize an experiment in state {state!r}")
            else:
                result = apply(dict(summary)) if apply is not None else summary
                encoded = canonical(result)
                db.execute("UPDATE runs SET status='completed',summary=?,updated_at=? WHERE id=?",
                           (encoded, time.time(), run_id))
                db.execute("UPDATE holdouts SET sealed_at=COALESCE(sealed_at,?) WHERE run_id=?",
                           (time.time(), run_id))
        return self.get_run(run_id)

    def request_control(self, run_id: str, action: str) -> dict[str, Any]:
        """Condition a cooperative request on the current durable lifecycle state."""
        if action not in ("pause", "cancel"):
            raise ExperimentError("control action must be pause or cancel")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            terminal = {"completed", "complete", "finalized", "failed", "imported", "cancelled", "canceled"}
            applied = run["status"] not in terminal
            if applied:
                active = {"created", "running", "validating", "finalizing", "pause_requested", "cancel_requested"}
                status = (action + "_requested") if run["status"] in active else ("paused" if action == "pause" else "cancelled")
                if run["status"] == "cancel_requested":
                    status = "cancel_requested"
                db.execute("UPDATE runs SET status=?,updated_at=? WHERE id=?", (status, time.time(), run_id))
        return {**self.get_run(run_id), "control_applied": applied}

    def reserve_exploration(self, run_id: str, intervals: list[dict[str, Any]]) -> dict[str, Any]:
        """Record search exposure, protecting final evidence until its verdict is sealed.

        A sealed final becomes ordinary historical data for later exploration.
        Its permanent reservation still forbids another run's final validation.
        """
        normalized = self._intervals(intervals)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            self._manager_fence(db, normalized)
            if run["spec"]["source"] != "native":
                raise ExperimentError("only native runs reserve exploration dates")
            for coin, start, end in normalized:
                spent = db.execute("""SELECT run_id FROM holdouts
                                      WHERE bot=? AND coin=? AND start<? AND end>? AND sealed_at IS NULL""",
                                   (run["spec"]["bot"], coin, end, start)).fetchone()
                if spent is not None:
                    raise ExperimentError(f"exploration for {coin} overlaps reserved final dates; fresh evidence is required")
                db.execute("INSERT OR IGNORE INTO exposures VALUES (?,?,?,?,?)",
                           (run["spec"]["bot"], coin, start, end, run_id))
        return {"reserved": True, "run_id": run_id,
                "intervals": [{"coin": c, "start": s, "end": e} for c, s, e in normalized]}

    @staticmethod
    def _intervals(intervals: list[dict[str, Any]]) -> list[tuple[str, float, float]]:
        if not isinstance(intervals, list) or not intervals:
            raise ExperimentError("reservation requires explicit intervals")
        normalized = []
        for row in intervals:
            if not isinstance(row, dict) or not isinstance(row.get("coin"), str) or not row["coin"]:
                raise ExperimentError("interval requires a coin")
            start, end = _timestamp(row.get("start")), _timestamp(row.get("end"))
            if start >= end:
                raise ExperimentError("interval end must be after start (half-open dates)")
            normalized.append((row["coin"].upper(), start, end))
        return sorted(set(normalized))

    def record_cell(self, run_id: str, candidate_id: str, cell_key: str,
                    record: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(candidate_id)
        if not isinstance(record, dict) or not isinstance(cell_key, str) or not cell_key:
            raise ExperimentError("cell requires a record and a stable cell key")
        run = self.get_run(run_id)
        if run["spec"].get("protocol_version") == 2:
            raise ExperimentError("protocol2 cells require the immutable manager trial API")
        if candidate_id not in _candidate_map(run["spec"]):
            raise ExperimentError("cell candidate is not in the frozen run spec")
        row = {**record, "candidate_id": candidate_id, "cell_key": cell_key}
        if isinstance(row.get("coin"), str):
            row["coin"] = row["coin"].upper()
        if row.get("split") not in ("train", "validation", "holdout"):
            raise ExperimentError("cell split must be train, validation or holdout")
        if row.get("status") not in ("completed", "failed"):
            raise ExperimentError("cell status must be completed or failed")
        if not isinstance(row.get("coin"), str) or not row["coin"]:
            raise ExperimentError("cell requires a coin")
        start, end = _timestamp(row.get("start")), _timestamp(row.get("end"))
        if start > end:
            raise ExperimentError("cell end precedes start")
        if row["status"] == "failed" and not row.get("error"):
            raise ExperimentError("failed cell requires an explicit error")
        if not isinstance(row.get("metrics", {}), dict):
            raise ExperimentError("cell metrics must be an object")
        encoded = canonical(row)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            sealed = False
            if row["split"] == "holdout":
                if run["spec"]["source"] != "native" or candidate_id not in ("0", run["frozen_candidate"]):
                    raise ExperimentError("holdout cells require a native frozen candidate or baseline")
                reserved = db.execute("SELECT sealed_at FROM holdouts WHERE run_id=? AND coin=? AND start<=? AND end>=?",
                                      (run_id, row["coin"], start, end)).fetchone()
                if reserved is None:
                    raise ExperimentError("holdout dates must be reserved before evaluation")
                sealed = reserved[0] is not None
            elif run["spec"]["source"] == "native":
                exposed = db.execute("SELECT 1 FROM exposures WHERE run_id=? AND coin=? AND start<=? AND end>=?",
                                     (run_id, row["coin"], start, end)).fetchone()
                if exposed is None:
                    raise ExperimentError("exploration dates must be reserved before evaluation")
            old = db.execute("SELECT record FROM cells WHERE run_id=? AND candidate_id=? AND cell_key=?",
                             (run_id, candidate_id, cell_key)).fetchone()
            if old is not None:
                if old[0] == encoded:
                    return row
                if json.loads(old[0])["status"] == "completed":
                    raise ExperimentError("completed cell evidence is immutable")
            if sealed:
                raise ExperimentError("sealed holdout evidence cannot be evaluated again")
            db.execute("INSERT OR REPLACE INTO cells VALUES (?,?,?,?)", (run_id, candidate_id, cell_key, encoded))
        return row

    def cells(self, run_id: str, *, split: str | None = None, coin: str | None = None,
              candidate_id: str | None = None, include_holdout: bool = False) -> list[dict[str, Any]]:
        self.get_run(run_id)
        with self._connect() as db:
            rows = db.execute("SELECT record FROM cells WHERE run_id=? ORDER BY cell_key,candidate_id", (run_id,))
            result = [json.loads(row[0]) for row in rows]
        return [r for r in result if (include_holdout or r["split"] != "holdout")
                and (split is None or r["split"] == split) and (coin is None or r["coin"] == coin.upper())
                and (candidate_id is None or r["candidate_id"] == str(candidate_id))]

    def freeze_candidate(self, run_id: str, candidate_id: str) -> dict[str, Any]:
        candidate_id = str(candidate_id)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            if run["spec"]["source"] != "native":
                raise ExperimentError("imported results cannot freeze or promote a native candidate")
            if candidate_id not in _candidate_map(run["spec"]):
                raise ExperimentError("frozen candidate is not in run spec")
            if run["frozen_candidate"] not in (None, candidate_id):
                raise ExperimentError("final candidate is already frozen")
            db.execute("UPDATE runs SET frozen_candidate=?,updated_at=? WHERE id=?", (candidate_id, time.time(), run_id))
        return self.get_run(run_id)

    def reserve_holdout(self, run_id: str, candidate_id: str,
                        intervals: list[dict[str, Any]]) -> dict[str, Any]:
        candidate_id = str(candidate_id)
        normalized = self._intervals(intervals)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            run = self._run(db.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
            for coin, start, end in normalized:
                if db.execute("SELECT 1 FROM manager_final_dates WHERE coin=? AND start<? AND end>? AND run_id<>?", (coin,end,start,run_id)).fetchone():
                    raise ExperimentError("dates overlap spent manager final")
                if db.execute("SELECT 1 FROM manager_exposures WHERE coin=? AND start<? AND end>?", (coin,end,start)).fetchone():
                    raise ExperimentError("dates already exposed to shared research clients")
            if run["spec"].get("protocol_version") == 2:
                raise ExperimentError("protocol2 final requires manager_unseal")
            if run["spec"]["source"] != "native" or run["frozen_candidate"] != candidate_id:
                raise ExperimentError("reserve holdout only for the native frozen candidate")
            reservations = db.execute(
                "SELECT coin,start,end,candidate_id,context,sealed_at FROM holdouts WHERE run_id=?",
                (run_id,)).fetchall()
            existing = sorted((r["coin"], r["start"], r["end"]) for r in reservations)
            if existing and existing != normalized:
                raise ExperimentError("a frozen run cannot change its reserved holdout intervals")
            context = fingerprint(run["spec"])
            if any(r["candidate_id"] != candidate_id or r["context"] != context for r in reservations):
                raise ExperimentError("reserved holdout candidate or evidence context changed")
            sealed = bool(reservations) and all(r["sealed_at"] is not None for r in reservations)
            if sealed:
                # Public, sealed dates may since have entered another run's
                # search. Reuse only the already measured exact baseline/pick
                # pair; never reevaluate a failed or missing measurement.
                records = [json.loads(r[0]) for r in db.execute(
                    "SELECT record FROM cells WHERE run_id=?", (run_id,))]
                for coin, start, end in normalized:
                    completed = {r["candidate_id"] for r in records
                                 if r["split"] == "holdout" and r["status"] == "completed"
                                 and r["coin"] == coin and _timestamp(r["start"]) == start
                                 and _timestamp(r["end"]) == end}
                    if not {"0", candidate_id}.issubset(completed):
                        raise ExperimentError("sealed holdout requires complete frozen evidence; reevaluation refused")
            for coin, start, end in normalized:
                exposure = db.execute("SELECT run_id FROM exposures WHERE bot=? AND coin=? AND start<? AND end>?",
                                      (run["spec"]["bot"], coin, end, start)).fetchone()
                if exposure is not None and not sealed:
                    raise ExperimentError(f"holdout for {coin} overlaps dates already exposed to exploration; fresh evidence is required")
                conflict = db.execute("SELECT run_id FROM holdouts WHERE bot=? AND coin=? AND start<? AND end>? AND run_id<>?",
                                      (run["spec"]["bot"], coin, end, start, run_id)).fetchone()
                if conflict is not None:
                    raise ExperimentError(f"holdout for {coin} overlaps spent dates reserved by experiment {conflict[0]}; fresh evidence is required")
                db.execute("""INSERT OR IGNORE INTO holdouts
                              (bot,coin,start,end,run_id,candidate_id,context) VALUES (?,?,?,?,?,?,?)""",
                           (run["spec"]["bot"], coin, start, end, run_id, candidate_id, context))
        return {"reserved": True, "run_id": run_id, "candidate_id": candidate_id,
                "intervals": [{"coin": c, "start": s, "end": e} for c, s, e in normalized]}


def _number(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ExperimentError(f"{label} must be a finite number")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ExperimentError(f"{label} must be a finite number") from exc
    if not number.is_finite():
        raise ExperimentError(f"{label} must be a finite number")
    return number


def _values(name: str, spec: dict[str, Any], domain: tuple, max_values: int) -> list[Any]:
    if not isinstance(spec, dict):
        raise ExperimentError(f"{name}: search dimension must be an object")
    if "kind" in spec and "type" in spec:
        raise ExperimentError(f"{name}: specify kind only once")
    kind = spec.get("kind", spec.get("type"))
    if kind == "fixed":
        permitted = {"kind", "type", "value"}
        if "value" not in spec:
            raise ExperimentError(f"{name}: fixed requires value")
        values = [spec["value"]]
    elif kind in ("enum", "choice"):
        permitted = {"kind", "type", "values"}
        values = spec.get("values")
        if not isinstance(values, list) or not values:
            raise ExperimentError(f"{name}: enum requires nonempty values")
    elif kind == "range":
        permitted = {"kind", "type", "start", "stop", "step", "count", "scale"}
        low, high = _number(spec.get("start"), name), _number(spec.get("stop"), name)
        if low > high:
            raise ExperimentError(f"{name}: range start exceeds stop")
        scale = spec.get("scale", "linear")
        if scale in ("linear", "lin"):
            if "count" in spec:
                raise ExperimentError(f"{name}: linear range uses step, not count")
            step = _number(spec.get("step"), name)
            if step <= 0:
                raise ExperimentError(f"{name}: step must be positive")
            count = int((high - low) // step) + 1
            if count > max_values:
                raise ExperimentError(f"{name}: range exceeds candidate budget")
            values = [low + step * i for i in range(count)]
        elif scale == "log":
            if "step" in spec:
                raise ExperimentError(f"{name}: log range uses count, not step")
            count = spec.get("count")
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= max_values:
                raise ExperimentError(f"{name}: log count must be in [1, {max_values}]")
            if low <= 0 or high <= 0 or (count == 1 and low != high):
                raise ExperimentError(f"{name}: log endpoints must be positive and distinct endpoints need count >= 2")
            values = [low] if count == 1 else [Decimal(str(math.exp(math.log(float(low)) + i / (count - 1) *
                                                                             (math.log(float(high)) - math.log(float(low))))))
                                                       for i in range(count)]
            values[0], values[-1] = low, high
        else:
            raise ExperimentError(f"{name}: scale must be linear or log")
    else:
        raise ExperimentError(f"{name}: kind must be fixed, enum or range")
    if set(spec) - permitted:
        raise ExperimentError(f"{name}: unknown search fields {sorted(set(spec) - permitted)}")
    if len(values) > max_values:
        raise ExperimentError(f"{name}: dimension exceeds candidate budget")
    out = []
    for raw in values:
        if domain[0] == "choice":
            if raw not in domain[1]:
                raise ExperimentError(f"{name}: expected one of {domain[1]}")
            value = raw
        else:
            number = _number(raw, name)
            if number < Decimal(str(domain[1])) or number > Decimal(str(domain[2])):
                raise ExperimentError(f"{name}: value outside domain [{domain[1]}, {domain[2]}]")
            if domain[0] == "int":
                if number != number.to_integral_value():
                    raise ExperimentError(f"{name}: value must be an integer")
                value = int(number)
            else:
                value = float(number)
        if value not in out:
            out.append(value)
    return out


def preview_space(bot: str, baseline: dict[str, Any], space: dict[str, Any], *,
                  coins: int | list[str] = 1, windows: int = 6, max_candidates: int = 97,
                  max_evaluations: int = 20000) -> dict[str, Any]:
    """Enumerate valid configurations exactly, with a bounded preflight workload.

    Invalid leaf combinations are reported, not executed. Dimension/domain errors
    reject the specification. Numeric ranges use Decimal to avoid endpoint drift.
    """
    from . import bots
    if bot not in bots.DOMAINS:
        raise ExperimentError("unknown bot")
    for label, value, upper in (("max_candidates", max_candidates, bots.MAX_CANDIDATES),
                                 ("max_evaluations", max_evaluations, 20000), ("windows", windows, 24)):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= upper:
            raise ExperimentError(f"{label} must be in [1, {upper}]")
    coin_count = len(set(coins)) if isinstance(coins, (list, tuple)) else coins
    if isinstance(coin_count, bool) or not isinstance(coin_count, int) or coin_count < 1:
        raise ExperimentError("coins must contain at least one unique coin")
    if not isinstance(space, dict) or set(space) - set(bots.DOMAINS[bot]):
        raise ExperimentError("search contains unknown or unsupported parameters")
    try:
        current = bots.validate(bot, baseline)
    except (TypeError, ValueError) as exc:
        raise ExperimentError(str(exc)) from exc
    dimensions = {key: _values(key, spec, bots.DOMAINS[bot][key], max_candidates)
                  for key, spec in sorted(space.items())}
    product_count = math.prod(len(v) for v in dimensions.values())
    if product_count > 100000:
        raise ExperimentError("raw search product exceeds 100000 combinations; narrow the search")
    candidates = [current]
    seen = {canonical(current)}
    invalid = 0
    examples = []
    for combo in itertools.product(*dimensions.values()):
        raw = {**current, **dict(zip(dimensions, combo))}
        try:
            cfg = bots.validate(bot, raw)
        except (TypeError, ValueError) as exc:
            invalid += 1
            if len(examples) < 5:
                examples.append(str(exc))
            continue
        key = canonical(cfg)
        if key not in seen:
            candidates.append(cfg)
            seen.add(key)
            if len(candidates) > max_candidates:
                raise ExperimentError(f"valid configurations exceed candidate budget {max_candidates} (baseline included)")
    evaluations = len(candidates) * coin_count * windows
    if evaluations > max_evaluations:
        raise ExperimentError(f"workload {evaluations} evaluations exceeds budget {max_evaluations}")
    return {"bot": bot, "candidates": candidates, "candidate_count": len(candidates), "configs": len(candidates),
            "coins": coin_count, "windows": windows, "evaluations": evaluations, "raw_combinations": product_count,
            "invalid_combinations": invalid, "invalid_examples": examples, "dimensions": dimensions,
            "budget": {"max_candidates": max_candidates, "max_evaluations": max_evaluations},
            "estimated_seconds": None, "estimate_reason": "runtime is unknown until measured on this workload"}


METRIC_CONVENTIONS = {"max_drawdown": "nonnegative_loss_magnitude; fraction when units are known"}


def _metric(cell: dict[str, Any], name: str) -> float | None:
    metrics = cell.get("metrics", {})
    value = metrics.get(name, metrics.get("costs_usd") if name == "total_cost" else None)
    if not isinstance(value, (float, int)) or isinstance(value, bool) or not math.isfinite(value):
        return None
    # Native engine cells retain negative peak-to-trough returns. The observed
    # views use loss magnitude so native and explicitly normalized imports have
    # one risk direction. Unknown imported units already have a null metric.
    return abs(float(value)) if name == "max_drawdown" else float(value)


def candidate_summary(store: ExperimentStore, run_id: str) -> list[dict[str, Any]]:
    """Full configurations and observed exploration evidence; no holdout feedback."""
    run = store.get_run(run_id)
    cells = store.cells(run_id)
    if run["spec"]["source"] == "tradingview":
        cells = run["spec"].get("reported_rows", cells)
    rows = []
    for cid, cfg in _candidate_map(run["spec"]).items():
        mine = [c for c in cells if c["candidate_id"] == cid]
        metrics = sorted({name for c in mine for name in c.get("metrics", {})})
        if "costs_usd" in metrics and "total_cost" not in metrics:
            metrics.append("total_cost")
        aggregates = {}
        for name in metrics:
            values = [_metric(c, name) for c in mine if c["status"] == "completed"]
            values = [v for v in values if v is not None]
            aggregates[name] = {"median": statistics.median(values) if values else None,
                                "min": min(values) if values else None, "max": max(values) if values else None,
                                "stdev": statistics.pstdev(values) if values else None, "observations": len(values)}
        rows.append({"candidate_id": cid, "config": cfg, "completed": sum(c["status"] == "completed" for c in mine),
                     "failed": sum(c["status"] == "failed" for c in mine), "metrics": aggregates,
                     "metric_conventions": METRIC_CONVENTIONS,
                     "coins": sorted({c["coin"] for c in mine if c.get("coin")}),
                     "unbound": sum(not c.get("coin") or c.get("start") is None or c.get("end") is None for c in mine),
                     "undated": sum(c.get("start") is None or c.get("end") is None for c in mine), "splits": sorted({c["split"] for c in mine})})
    return rows


def sparse_heatmap(store: ExperimentStore, run_id: str, x: str, y: str, *, metric: str = "total_return",
                   fixed: dict[str, Any] | None = None, coin: str | None = None,
                   split: str | None = None) -> dict[str, Any]:
    """Observed two-axis slices, conditioned on every other configuration field."""
    if x == y or split not in (None, "train", "validation"):
        raise ExperimentError("heatmap needs distinct axes and train/validation evidence only")
    candidates = _candidate_map(store.get_run(run_id)["spec"])
    if not all(x in cfg and y in cfg for cfg in candidates.values()):
        raise ExperimentError("heatmap axes must exist in each configuration")
    cells = store.cells(run_id, coin=coin, split=split)
    groups: dict[str, dict[str, Any]] = {}
    for cid, cfg in candidates.items():
        condition = {k: v for k, v in cfg.items() if k not in (x, y)}
        if fixed is not None and any(condition.get(k) != v for k, v in fixed.items()):
            continue
        key = canonical(condition)
        group = groups.setdefault(key, {"fixed": condition, "points": {}, "x_values": [], "y_values": []})
        if cfg[x] not in group["x_values"]:
            group["x_values"].append(cfg[x])
        if cfg[y] not in group["y_values"]:
            group["y_values"].append(cfg[y])
        point_key = canonical([cfg[x], cfg[y]])
        point = group["points"].setdefault(point_key, {"x": cfg[x], "y": cfg[y], "candidate_ids": [], "values": [], "failed": 0})
        point["candidate_ids"].append(cid)
        for cell in cells:
            if cell["candidate_id"] != cid:
                continue
            value = _metric(cell, metric)
            if cell["status"] == "completed" and value is not None:
                point["values"].append(value)
            elif cell["status"] == "failed":
                point["failed"] += 1
    output = []
    for group in groups.values():
        points = []
        for point in group["points"].values():
            values = point.pop("values")
            point.update({"observations": len(values), "value": statistics.median(values) if values else None,
                          "stdev": statistics.pstdev(values) if values else None,
                          "min": min(values) if values else None, "max": max(values) if values else None})
            points.append(point)
        try:
            group["x_values"].sort()
            group["y_values"].sort()
        except TypeError:
            pass
        potential = len(group["x_values"]) * len(group["y_values"])
        observed = sum(p["observations"] > 0 for p in points)
        group.update({"points": points, "possible_points": potential, "observed_points": observed,
                      "coverage": observed / potential if potential else 0,
                      "missing": [{"x": a, "y": b} for a in group["x_values"] for b in group["y_values"]
                                  if not any(p["x"] == a and p["y"] == b and p["observations"] for p in points)]})
        output.append(group)
    return {"run_id": run_id, "x": x, "y": y, "metric": metric, "groups": output,
            "split": split or "train+validation", "interpolated": False, "holdout_included": False,
            "metric_conventions": METRIC_CONVENTIONS}


# Aliases deliberately distinguish currency profit from percentage return.
_COLUMN_ALIASES = {
    "candidate_id": ("candidate_id", "candidate", "index", "test", "test #", "iteration"),
    "coin": ("coin", "symbol", "ticker"), "start": ("start", "start_date", "start date", "from"),
    "end": ("end", "end_date", "end date", "to"), "split": ("split",),
    "total_return": ("total_return", "return", "net profit %", "net profit (%)", "net profit percent", "net profit_all_percent", "net profit all %", "netprofitpercentall"),
    "net_profit": ("net_profit", "net profit", "net profit usd", "net profit_all", "net profit all", "netprofitall"),
    "max_drawdown": ("max_drawdown", "max drawdown", "max. drawdown", "max drawdown %", "max drawdown (%)", "max equity drawdown_all", "max equity drawdown_all_percent",
                     "max equity drawdown all", "max equity drawdown all %", "maxequitydrawdownall", "maxequitydrawdownpercentall"),
    "trades": ("trades", "total trades", "total closed trades", "number of trades", "total trades_all", "total trades all", "totaltradesall"),
    "total_cost": ("total_cost", "total costs", "commission paid", "fees", "commission paid_all", "commission paid all", "commissionpaidall"),
    "sharpe": ("sharpe", "sharpe ratio", "sharpe ratio_all", "sharperatioall"), "profit_factor": ("profit_factor", "profit factor", "profit factor_all", "profitfactorall"),
}


def _csv_number(raw: str, label: str) -> float | None:
    if raw.strip() in ("", "N/A", "n/a", "—", "-"):
        return None
    cleaned = raw.strip().replace(",", "")
    if cleaned.endswith("%"):
        cleaned = cleaned[:-1].strip()
    return float(_number(cleaned, label))


def import_tradingview(store: ExperimentStore, csv_text: str,
                       metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    """Import reported metrics without treating unknown units as native returns.

    Input columns retain their raw spelling and values in every imported cell.
    Explicit metadata controls normalization. A percent sign or column label alone
    does not establish a model's costs, fill timing, dates or comparability.
    """
    if not isinstance(csv_text, str) or len(csv_text.encode()) > 10_000_000:
        raise ExperimentError("CSV must be text smaller than 10 MB")
    if metadata is not None and not isinstance(metadata, dict):
        raise ExperimentError("import metadata must be an object")
    metadata = dict(metadata or {})
    canonical(metadata)
    for key in ("return_unit", "drawdown_unit"):
        if metadata.get(key) not in (None, "fraction", "percent", "currency"):
            raise ExperimentError(f"{key} must be fraction, percent or currency")
    for key in ("fee_bps", "slippage_bps", "borrow_bps_per_day", "fill_delay"):
        if metadata.get(key) is not None:
            number = _number(metadata[key], key)
            if number < 0 or (key == "fill_delay" and number != number.to_integral_value()):
                raise ExperimentError(f"{key} must be nonnegative" + (" integer" if key == "fill_delay" else ""))
            metadata[key] = int(number) if key == "fill_delay" else float(number)
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")), strict=True)
    if not reader.fieldnames or len({n.strip().lower() for n in reader.fieldnames}) != len(reader.fieldnames):
        raise ExperimentError("CSV requires unique nonempty column names")
    if any(not name.strip() for name in reader.fieldnames):
        raise ExperimentError("CSV requires unique nonempty column names")
    lower = {name.strip().lower(): name for name in reader.fieldnames}
    mapping = {target: next((lower[a] for a in aliases if a in lower), None)
               for target, aliases in _COLUMN_ALIASES.items()}
    # Both absolute and percentage drawdown can appear in one optimizer export.
    # Select only the column matching explicitly supplied units.
    drawdown_aliases = _COLUMN_ALIASES["max_drawdown"]
    if metadata.get("drawdown_unit") == "percent":
        aliases = [a for a in drawdown_aliases if "%" in a or "percent" in a]
        mapping["max_drawdown"] = next((lower[a] for a in aliases if a in lower), mapping["max_drawdown"])
    elif metadata.get("drawdown_unit") == "currency":
        aliases = [a for a in drawdown_aliases if "%" not in a and "percent" not in a]
        mapping["max_drawdown"] = next((lower[a] for a in aliases if a in lower), mapping["max_drawdown"])
    if not any(mapping[k] for k in ("total_return", "net_profit", "max_drawdown", "trades")):
        raise ExperimentError("CSV has no recognized result columns")
    try:
        raw_rows = list(reader)
    except csv.Error as exc:
        raise ExperimentError(f"malformed CSV: {exc}") from exc
    candidates: dict[str, dict[str, Any]] = {}
    records = []
    for line, raw in enumerate(raw_rows, 2):
        if line > 10001:
            raise ExperimentError("CSV exceeds 10000 rows")
        if None in raw or any(value is None for value in raw.values()):
            raise ExperimentError(f"CSV row {line} has the wrong column count")
        cid = str(raw.get(mapping["candidate_id"] or "", "").strip() or len(candidates))
        cfg = {name.split(".", 1)[1]: value for name, value in raw.items()
               if name.lower().startswith(("param.", "input."))}
        recognized = {lower[a] for aliases in _COLUMN_ALIASES.values() for a in aliases if a in lower}
        # The optimizer exports input names as bare columns. Keep their strings;
        # importing a result must not coerce or execute an external strategy.
        cfg.update({name: value for name, value in raw.items()
                    if name not in recognized and not name.lower().startswith(("param.", "input."))})
        if cid in candidates and candidates[cid] != cfg:
            raise ExperimentError(f"candidate {cid!r} has conflicting input configurations")
        candidates[cid] = cfg
        coin = raw.get(mapping["coin"] or "", "").strip() or metadata.get("coin") or metadata.get("symbol")
        start = raw.get(mapping["start"] or "", "").strip() or metadata.get("start")
        end = raw.get(mapping["end"] or "", "").strip() or metadata.get("end")
        if coin is not None and (not isinstance(coin, str) or not coin.strip()):
            raise ExperimentError("import coin must be a nonempty string when supplied")
        coin = coin.upper() if coin else None
        for value in (start, end):
            if value is not None:
                _timestamp(value)
        # Unknown dates/coins are retained as unavailable provenance. Cells still
        # need an honest timestamp key, so store these rows in the import spec;
        # only bounded, dated rows become native-shaped evaluation cells.
        metrics: dict[str, Any] = {}
        reported = {}
        for name in ("total_return", "net_profit", "max_drawdown", "trades", "total_cost", "sharpe", "profit_factor"):
            column = mapping[name]
            if column is None:
                continue
            value = _csv_number(raw[column], f"CSV row {line} {column}")
            unit = metadata.get("return_unit" if name == "total_return" else "drawdown_unit")
            if name in ("total_return", "max_drawdown") and unit in ("fraction", "currency"):
                percent_column = "%" in column or "percent" in column.lower()
                if raw[column].strip().endswith("%") or percent_column:
                    raise ExperimentError(f"{column}: percentage evidence conflicts with declared {unit} units")
            reported[name] = value
            if name == "trades" and value is not None and (value < 0 or not value.is_integer()):
                raise ExperimentError("trades must be a nonnegative integer")
            if name in ("total_return", "max_drawdown"):
                unit = metadata.get("return_unit" if name == "total_return" else "drawdown_unit")
                metrics[name] = (value / 100 if unit == "percent" else value) if value is not None and unit in ("fraction", "percent") else None
                if name == "max_drawdown" and metrics[name] is not None:
                    metrics[name] = abs(metrics[name])
            else:
                metrics[name] = value
        split = raw.get(mapping["split"] or "", "").strip().lower() or "validation"
        if split not in ("train", "validation"):
            raise ExperimentError("import split must be train or validation; imported holdout cannot promote")
        if start is not None and end is not None and _timestamp(start) > _timestamp(end):
            raise ExperimentError("import end precedes start")
        records.append({"candidate_id": cid, "cell_key": f"import:{line - 1}", "coin": coin,
                        "start": start, "end": end, "split": split, "status": "completed", "metrics": metrics,
                        "reported_metrics": reported, "raw": raw, "error": None})
    if not records:
        raise ExperimentError("CSV contains no result rows")
    spec = {"source": "tradingview", "bot": str(metadata.get("bot") or "external"),
            "candidates": [{"id": cid, "config": cfg} for cid, cfg in candidates.items()],
            "provenance": metadata, "csv_sha256": hashlib.sha256(csv_text.encode()).hexdigest(),
            "reported_rows": records, "promotion_eligible": False, "metric_conventions": METRIC_CONVENTIONS}
    run_id = store.create_run(spec)
    dated = 0
    for row in records:
        if row["coin"] and row["start"] is not None and row["end"] is not None:
            store.record_cell(run_id, row["candidate_id"], row["cell_key"], row)
            dated += 1
    return store.update_run(run_id, status="imported", summary={"rows": len(records), "dated_cells": dated,
                            "undated_rows": len(records) - dated, "promotion_eligible": False,
                            "reason": "External reported evidence; import never promotes native configurations."})


def _comparison_context(run: dict[str, Any]) -> dict[str, Any]:
    spec = run["spec"]
    context = dict(spec.get("provenance") or {})
    for key in ("bot", "coin", "interval", "start", "end", "return_unit", "drawdown_unit", "fee_bps",
                "slippage_bps", "borrow_bps_per_day", "fill_delay", "currency", "strategy", "data_source"):
        if key not in context and key in spec:
            context[key] = spec[key]
    costs = spec.get("costs", {})
    if isinstance(costs, dict):
        for key in ("fee_bps", "slippage_bps", "borrow_bps_per_day", "fill_delay"):
            if key not in context and key in costs:
                context[key] = costs[key]
    return context


def compare_runs(store: ExperimentStore, left: str, right: str) -> dict[str, Any]:
    """Explicit compatibility diagnostics, never a native adoption instruction."""
    a, b = store.get_run(left), store.get_run(right)
    ca, cb = _comparison_context(a), _comparison_context(b)
    required = ("bot", "interval", "return_unit", "drawdown_unit", "fee_bps", "slippage_bps",
                "borrow_bps_per_day", "fill_delay", "currency", "strategy", "data_source")
    reasons = []
    for key in required:
        av, bv = ca.get(key), cb.get(key)
        if av in (None, "") or bv in (None, ""):
            reasons.append(f"{key}: missing provenance")
        elif key in ("start", "end"):
            if _timestamp(av) != _timestamp(bv):
                reasons.append(f"{key}: differs")
        elif av != bv:
            reasons.append(f"{key}: differs")
    def coverage(run: dict[str, Any], context: dict[str, Any]) -> set[tuple[str, str, str, float, float]]:
        rows = store.cells(run["id"])
        if run["spec"]["source"] == "tradingview":
            rows = run["spec"].get("reported_rows", rows)
        rows = [row for row in rows if row.get("status") == "completed" and _metric(row, "total_return") is not None]
        result = set()
        unbound = sum(not row.get("coin") or row.get("start") is None or row.get("end") is None for row in rows)
        if unbound:
            label = "left" if run["id"] == left else "right"
            reasons.append(f"{label}: {unbound} contributing rows lack explicit coin/date bounds")
        for row in rows:
            if row.get("coin") and row.get("start") is not None and row.get("end") is not None:
                result.add((str(row["coin"]).upper(), _timestamp(row["start"]), _timestamp(row["end"])))
        if not result:
            reasons.append(("left" if run["id"] == left else "right") + ": no explicit dated coin/window evidence")
        # A context label cannot overwrite actual cell dates or coin coverage.
        if result and context.get("coin") and any(c != str(context["coin"]).upper() for c, _, _ in result):
            reasons.append("declared coin conflicts with actual cell coverage")
        for name, index in (("start", 1), ("end", 2)):
            if result and context.get(name) is not None and any(row[index] != _timestamp(context[name]) for row in result):
                reasons.append(f"declared {name} conflicts with actual cell windows")
        # Candidate IDs and splits keep complementary failures from being
        # disguised by another candidate's successful measurement.
        return {(str(row.get("candidate_id")), row.get("split"), str(row["coin"]).upper(),
                 _timestamp(row["start"]), _timestamp(row["end"])) for row in rows
                if row.get("coin") and row.get("start") is not None and row.get("end") is not None}
    for label, run in (("left", a), ("right", b)):
        if not any(row["metrics"].get("total_return", {}).get("observations", 0)
                   for row in candidate_summary(store, run["id"])):
            reasons.append(f"{label}: no normalized total return observations")
    coverage_a, coverage_b = coverage(a, ca), coverage(b, cb)
    if coverage_a != coverage_b:
        reasons.append("coin/date window coverage differs")
    # Normalization is explicit. Equivalent percent/fraction inputs can be
    # compared once both declare units; currency P&L cannot become return.
    if ca.get("return_unit") in ("percent", "fraction") and cb.get("return_unit") in ("percent", "fraction"):
        reasons = [r for r in reasons if r != "return_unit: differs"]
    if ca.get("drawdown_unit") in ("percent", "fraction") and cb.get("drawdown_unit") in ("percent", "fraction"):
        reasons = [r for r in reasons if r != "drawdown_unit: differs"]
    elif ca.get("drawdown_unit") == cb.get("drawdown_unit") == "currency":
        reasons.append("currency drawdown is not a normalized risk metric")
    if ca.get("return_unit") == cb.get("return_unit") == "currency":
        reasons.append("currency profit is not a normalized total return")
    return {"left": left, "right": right, "comparable": not reasons, "reasons": reasons,
            "left_context": ca, "right_context": cb, "left_candidates": candidate_summary(store, left),
            "right_candidates": candidate_summary(store, right), "promotion_eligible": False,
            "metric_conventions": METRIC_CONVENTIONS}

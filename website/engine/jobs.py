"""Durable, idempotent pure-analysis jobs with immutable input snapshots."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .public_data import DataError, atomic
from .server import COINS, INTERVALS, MAX_CACHE_BYTES, Analysis, RequestError, finite
from .state import canonical

MAX_PENDING = 512
MAX_RESULT_BYTES = 2_000_000
JOB_TIMEOUT = 45


def validate_shape(request):
    """Reject malformed requests before an ID can become an accepted receipt."""
    if not isinstance(request, dict) or set(request) != {
        "coin",
        "strategy",
        "interval",
        "capital",
        "leverage",
    }:
        raise RequestError("invalid_backtest_request")
    if (
        any(
            not isinstance(request[key], str)
            or not request[key]
            or len(request[key]) > maximum
            for key, maximum in (("coin", 16), ("strategy", 100), ("interval", 16))
        )
        or not finite(request["capital"])
        or not finite(request["leverage"])
    ):
        raise RequestError("invalid_backtest_request")
    return request


def validate_request(request):
    from backtester.core.strategies import REGISTRY

    validate_shape(request)
    if (
        request["coin"] not in COINS
        or request["interval"] not in INTERVALS
        or not isinstance(request["strategy"], str)
        or request["strategy"] not in REGISTRY
    ):
        raise RequestError("unsupported_market_or_strategy")
    if (
        not finite(request["capital"])
        or not 1 <= request["capital"] <= 1_000_000
        or not finite(request["leverage"])
        or not 1 <= request["leverage"] <= 10
    ):
        raise RequestError("invalid_capital_or_leverage")
    return request


def valid_id(value):
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _calculate(root, row, destination):
    """Spawned child: only canonical simulation over the frozen public CSV."""
    try:
        request = json.loads(row["request_json"])
        source = (
            Path(root)
            / "inputs"
            / row["input_sha"]
            / f"{request['coin']}_{request['interval']}.csv"
        )
        if hashlib.sha256(source.read_bytes()).hexdigest() != row["input_sha"]:
            raise RequestError("job_input_integrity")
        result = Analysis(source.parent, Path(root) / "oracle").backtest(request)
        acquisition = json.loads(source.with_suffix(".json").read_bytes())
        if acquisition.get("sha256") != row["input_sha"]:
            raise RequestError("job_input_integrity")
        result["provenance"].update(
            source="coinbase_exchange_public_candles", acquisition=acquisition
        )
        result["limitations"] = [
            item
            for item in result["limitations"]
            if item != "cached_source_label_is_not_independent_market_provenance"
        ] + ["public_provider_candles_not_execution_quotes"]
        payload = {"result": result}
    except RequestError as error:
        payload = {"error": str(error)}
    except Exception:  # noqa: BLE001 - a failed pure calculation returns only a fixed public reason.
        payload = {"error": "calculation_failed"}
    raw = canonical(payload)
    if len(raw) > MAX_RESULT_BYTES:
        raw = canonical({"error": "result_too_large"})
    atomic(Path(destination), raw)


class Jobs:
    def __init__(self, root):
        self.root, self.path = Path(root), Path(root) / "jobs.sqlite3"
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute(
                "CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,request_hash TEXT NOT NULL,request_json TEXT NOT NULL,input_sha TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('queued','running','complete','failed')),created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,result_json TEXT,error TEXT)"
            )
        self.path.chmod(0o600)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def public(row):
        value = {
            "id": row["id"],
            "status": row["status"],
            "requestHash": row["request_hash"],
            "inputHash": row["input_sha"] or None,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
        if row["status"] == "complete":
            value["result"] = json.loads(row["result_json"])
        if row["status"] == "failed":
            value["error"] = row["error"]
        return value

    def get(self, identifier):
        if not valid_id(identifier):
            raise RequestError("invalid_job_id")
        with self.connection() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
        if not row:
            raise RequestError("job_not_found")
        return self.public(row)

    def enqueue(self, body):
        if (
            not isinstance(body, dict)
            or set(body) != {"id", "request"}
            or not valid_id(body["id"])
        ):
            raise RequestError("invalid_job_request")
        request = validate_shape(body["request"])
        raw = canonical(request)
        request_hash = hashlib.sha256(raw).hexdigest()
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM jobs WHERE id=?", (body["id"],)
            ).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise RequestError("job_idempotency_conflict")
                return self.public(existing), False
            status, input_sha, error = "queued", "", None
            try:
                validate_request(request)
                if (
                    db.execute(
                        "SELECT count(*) FROM jobs WHERE status IN ('queued','running')"
                    ).fetchone()[0]
                    >= MAX_PENDING
                ):
                    raise RequestError("job_capacity_reached")
                input_sha = self.freeze_input(request)
            except RequestError as refusal:
                # A valid accepted ID must never become a different job when
                # strategy registration, capacity or cache availability changes.
                status, input_sha, error = "failed", "", str(refusal)
            at = int(time.time())
            db.execute(
                "INSERT INTO jobs VALUES(?,?,?,?,?,?,?,NULL,?)",
                (
                    body["id"],
                    request_hash,
                    raw.decode(),
                    input_sha,
                    status,
                    at,
                    at,
                    error,
                ),
            )
        return self.get(body["id"]), True

    def freeze_input(self, request):
        """Validate and freeze inputs, exposing only symbolic admission failures."""
        try:
            source = self.root / "data" / f"{request['coin']}_{request['interval']}.csv"
            if (
                source.is_symlink()
                or not source.is_file()
                or source.stat().st_size > MAX_CACHE_BYTES
            ):
                raise RequestError("cached_history_unavailable")
            snapshot = source.read_bytes()
            if len(snapshot) > MAX_CACHE_BYTES:
                raise RequestError("cached_history_unavailable")
            input_sha = hashlib.sha256(snapshot).hexdigest()
            metadata_path = source.with_suffix(".json")
            if (
                metadata_path.is_symlink()
                or not metadata_path.is_file()
                or metadata_path.stat().st_size > 4096
            ):
                raise RequestError("public_provenance_unavailable")
            try:
                metadata = json.loads(metadata_path.read_bytes())
            except (OSError, ValueError):
                raise RequestError("public_provenance_unavailable") from None
            if (
                not isinstance(metadata, dict)
                or metadata.get("sha256") != input_sha
                or metadata.get("provider") != "https://api.exchange.coinbase.com"
                or metadata.get("product") != request["coin"] + "-USD"
                or metadata.get("interval") != request["interval"]
            ):
                raise RequestError("public_provenance_unavailable")
            pinned = self.root / "inputs" / input_sha / source.name
            if pinned.exists():
                if (
                    pinned.is_symlink()
                    or hashlib.sha256(pinned.read_bytes()).hexdigest() != input_sha
                ):
                    raise RequestError("job_input_integrity")
            else:
                atomic(pinned, snapshot)
            pinned_metadata = pinned.with_suffix(".json")
            if pinned_metadata.is_symlink():
                raise RequestError("job_input_integrity")
            if not pinned_metadata.exists():
                atomic(pinned_metadata, canonical(metadata))
            return input_sha
        except DataError:
            raise RequestError("job_input_integrity") from None
        except OSError:
            raise RequestError("input_freeze_unavailable") from None

    def recover(self):
        # These are pure calculations, not financial submissions. Every retry
        # keeps its original request and immutable public input snapshot.
        with self.connection() as db:
            return db.execute(
                "UPDATE jobs SET status='queued',updated_at=? WHERE status='running'",
                (int(time.time()),),
            ).rowcount

    def next(self, identifier=None):
        with self.connection() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' AND (? IS NULL OR id=?) ORDER BY created_at,id LIMIT 1",
                (identifier, identifier),
            ).fetchone()
            if row:
                db.execute(
                    "UPDATE jobs SET status='running',updated_at=? WHERE id=? AND status='queued'",
                    (int(time.time()), row["id"]),
                )
                return dict(row)
        return None

    def calculate(self, row, *, timeout=JOB_TIMEOUT):
        output = self.root / (".result-" + row["id"] + ".json")
        process = multiprocessing.get_context("spawn").Process(
            target=_calculate, args=(str(self.root), row, str(output))
        )
        process.start()
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join(3)
            if process.is_alive():
                process.kill()
                process.join(3)
            return {"error": "calculation_timeout"}
        try:
            if (
                process.exitcode != 0
                or not output.is_file()
                or output.stat().st_size > MAX_RESULT_BYTES
            ):
                return {"error": "calculation_failed"}
            return json.loads(output.read_bytes())
        finally:
            output.unlink(missing_ok=True)

    def finish(self, identifier, outcome):
        at = int(time.time())
        with self.connection() as db:
            if (
                set(outcome) == {"result"}
                and isinstance(outcome["result"], dict)
                and outcome["result"].get("status") == "complete"
            ):
                db.execute(
                    "UPDATE jobs SET status='complete',result_json=?,error=NULL,updated_at=? WHERE id=? AND status='running'",
                    (canonical(outcome["result"]).decode(), at, identifier),
                )
            else:
                reason = outcome.get("error")
                if (
                    not isinstance(reason, str)
                    or not reason.replace("_", "").isalnum()
                    or len(reason) > 80
                ):
                    reason = "calculation_failed"
                db.execute(
                    "UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=? AND status='running'",
                    (reason, at, identifier),
                )
        return self.get(identifier)

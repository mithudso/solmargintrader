"""Bounded, sanitized observations of manager events; never manager control.

The mirror is incremental and private. Original event journals and log files
remain with their existing owner. Free-form log content is never mirrored.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import plistlib
import re
import sqlite3
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from .registration import read_registrations

SCHEMA_VERSION = 1
APPLICATION_ID = 0x45545431
SOURCE_PAGE = 1000
MAX_LOG_TAIL = 65536
SOURCES = ("manager_spec", "manager_runtime")
KINDS = frozenset(
    {
        "spec.created",
        "input.registered",
        "start.requested",
        "stop.requested",
        "worker.claimed",
        "worker.input_exhausted",
        "tick.intent",
        "tick.committed",
        "worker.failed",
    }
)
SECRET_KEY = re.compile(
    r"api.?key|private.?key|wallet|password|passphrase|secret|token|authorization|credential",
    re.IGNORECASE,
)
STATES = frozenset(
    {
        "draft",
        "planned",
        "initializing",
        "starting",
        "running",
        "waiting",
        "stopped",
        "stopping",
        "recovering",
        "backtest",
        "forward",
        "paper",
        "live",
        "not_running",
        "unknown",
        "failed",
        "blocked",
        "quarantined",
        "exhausted",
    }
)
PHASES = STATES | {
    "not_initialized",
    "backtesting",
    "downloading",
    "acquiring",
    "forward_partial",
    "forward_waiting",
    "forward_partial_waiting",
    "complete",
    "completed",
}


def sanitize(value: Any, *, depth: int = 0) -> Any:
    """Omit untyped text and redact secret-bearing keys recursively.

    Typed source adapters below explicitly validate the few public string fields
    they publish. This generic helper never guesses that arbitrary prose is safe.
    """
    if depth > 8:
        return "[OMITTED_DEPTH]"
    if isinstance(value, dict):
        return {
            str(key)[:80]: "[REDACTED]"
            if SECRET_KEY.search(str(key))
            else sanitize(item, depth=depth + 1)
            for key, item in list(value.items())[:100]
        }
    if isinstance(value, list):
        return [sanitize(item, depth=depth + 1) for item in value[:100]]
    if isinstance(value, str):
        return "[OMITTED_TEXT]"
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    return "[OMITTED_VALUE]"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _home(manager_home: Path | None) -> Path:
    if manager_home is None:
        from botmanager.store import data_home

        manager_home = data_home()
    return Path(manager_home).expanduser().absolute()


def _path(home: Path) -> Path:
    return Path(home).expanduser().absolute() / "telemetry.sqlite3"


def _read(path: Path) -> sqlite3.Connection:
    if not path.is_file() or path.is_symlink():
        raise ValueError("source_unavailable")
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


@contextmanager
def _mirror(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("mirror_unavailable")
    with closing(sqlite3.connect(path, timeout=2)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            app_id = db.execute("PRAGMA application_id").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if not tables and version == 0 and app_id == 0:
                db.execute("CREATE TABLE meta(key TEXT PRIMARY KEY,body TEXT NOT NULL)")
                db.execute(
                    "CREATE TABLE events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,source TEXT NOT NULL,source_sequence INTEGER NOT NULL,body TEXT NOT NULL,UNIQUE(source,source_sequence))"
                )
                for action in ("UPDATE", "DELETE"):
                    db.execute(
                        f"CREATE TRIGGER events_no_{action.lower()} BEFORE {action} ON events BEGIN SELECT RAISE(ABORT,'immutable telemetry'); END"
                    )
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            elif version != SCHEMA_VERSION or app_id != APPLICATION_ID:
                raise ValueError("mirror_incompatible")
            path.chmod(0o600)
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


def _meta(db: sqlite3.Connection, key: str, fallback: Any = None) -> Any:
    row = db.execute("SELECT body FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else fallback


def _set(db: sqlite3.Connection, key: str, value: Any) -> None:
    db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, _json(value)))


def _uuid(value: Any) -> str:
    if type(value) is not str or str(UUID(value)) != value:
        raise ValueError
    return value


def _number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _event(source: str, row: dict) -> dict:
    sequence = row["sequence"]
    if type(sequence) is not int or sequence < 1:
        raise ValueError("invalid_source_sequence")
    # Even a filtered event has its exact source sequence. Cursors do not skip it.
    result = {
        "source": source,
        "source_sequence": sequence,
        "kind": "event.filtered",
        "filtered": True,
        "reason": "unsupported_or_invalid_event",
    }
    try:
        bot_id = _uuid(row["bot_id"])
        if source == "manager_runtime":
            kind, stamp = row["kind"], row["at"]
            if kind not in KINDS or not _number(stamp):
                return result
            if any(
                type(row[k]) is not int or row[k] < 0 for k in ("generation", "cursor")
            ):
                return result
            return {
                "source": source,
                "source_sequence": sequence,
                "kind": kind,
                "bot_id": bot_id,
                "occurred_at": stamp,
                "generation": row["generation"],
                "cursor": row["cursor"],
                "filtered": False,
            }
        body = json.loads(row["body"])
        if (
            not isinstance(body, dict)
            or body.get("event_type") not in KINDS
            or body.get("bot_id") != bot_id
        ):
            return result
        stamp = datetime.fromisoformat(body["occurred_at"])
        if stamp.tzinfo is None:
            return result
        event_id = _uuid(body["event_id"])
        result = {
            "source": source,
            "source_sequence": sequence,
            "kind": body["event_type"],
            "bot_id": bot_id,
            "event_id": event_id,
            "occurred_at": stamp.timestamp(),
            "filtered": False,
        }
        revision = body.get("config_revision")
        digest = body.get("config_hash")
        if type(revision) is int and revision > 0:
            result["config_revision"] = revision
        if type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest):
            result["config_hash"] = digest
        return result
    except (KeyError, ValueError, TypeError, OverflowError):
        return {
            "source": source,
            "source_sequence": sequence,
            "kind": "event.filtered",
            "filtered": True,
            "reason": "unsupported_or_invalid_event",
        }


def _public_event(body: Any, source: str, sequence: int) -> dict:
    source = source if source in SOURCES else "unknown"
    sequence = sequence if type(sequence) is int and sequence > 0 else None
    result = {
        "source": source,
        "source_sequence": sequence,
        "kind": "event.filtered",
        "filtered": True,
        "reason": "unsupported_or_invalid_event",
    }
    if (
        source not in SOURCES
        or not isinstance(body, dict)
        or body.get("filtered") is not False
    ):
        return result
    try:
        if body.get("kind") not in KINDS or not _number(body.get("occurred_at")):
            return result
        result = {
            "source": source,
            "source_sequence": sequence,
            "kind": body["kind"],
            "bot_id": _uuid(body.get("bot_id")),
            "occurred_at": body["occurred_at"],
            "filtered": False,
        }
        for field in ("generation", "cursor", "config_revision"):
            value = body.get(field)
            if type(value) is int and value >= 0:
                result[field] = value
        if "event_id" in body:
            result["event_id"] = _uuid(body["event_id"])
        digest = body.get("config_hash")
        if type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest):
            result["config_hash"] = digest
        return result
    except (TypeError, ValueError, KeyError):
        return {
            "source": source,
            "source_sequence": sequence,
            "kind": "event.filtered",
            "filtered": True,
            "reason": "unsupported_or_invalid_event",
        }


def _public_sources(value: Any) -> dict:
    if not isinstance(value, dict):
        return {}
    reasons = {
        "no_events",
        "source_journal_missing",
        "source_sequence_regressed",
        "source_journal_replaced",
        "source_journal_unavailable",
    }
    result = {}
    for source in SOURCES:
        row = value.get(source)
        if not isinstance(row, dict):
            continue
        public = {
            "status": "available"
            if row.get("status") == "available"
            else "unavailable",
            "reason": row.get("reason") if row.get("reason") in reasons else None,
            "has_more": row.get("has_more") is True,
        }
        for key in ("cursor", "high_watermark"):
            amount = row.get(key)
            if type(amount) is int and amount >= 0:
                public[key] = amount
        result[source] = public
    return result


def _source_page(manager_home: Path, source: str, after: int) -> dict:
    path = manager_home / (
        "runtime.sqlite3" if source == "manager_runtime" else "manager.sqlite3"
    )
    if not path.exists() or path.is_symlink():
        return {
            "status": "unavailable",
            "reason": "source_journal_missing",
            "rows": [],
            "has_more": False,
        }
    try:
        if source == "manager_runtime":
            from botmanager.ledger import RuntimeLedger

            context = RuntimeLedger(manager_home).connection()
        else:
            context = closing(_read(path))
        with context as db:
            if (
                source == "manager_spec"
                and db.execute("PRAGMA user_version").fetchone()[0] != 1
            ):
                raise ValueError
            fields = (
                "sequence,bot_id,generation,substr(kind,1,129) AS kind,cursor,at"
                if source == "manager_runtime"
                else "sequence,bot_id,CASE WHEN length(body)<=16384 THEN body ELSE NULL END AS body"
            )
            first = db.execute(
                f"SELECT {fields} FROM events ORDER BY sequence LIMIT 1"
            ).fetchone()
            high = db.execute("SELECT max(sequence) FROM events").fetchone()[0] or 0
            if high < after:
                return {
                    "status": "unavailable",
                    "reason": "source_sequence_regressed",
                    "rows": [],
                    "has_more": False,
                }
            rows = db.execute(
                f"SELECT {fields} FROM events WHERE sequence>? ORDER BY sequence LIMIT ?",
                (after, SOURCE_PAGE + 1),
            ).fetchall()
            marker = (
                hashlib.sha256(_json(dict(first)).encode()).hexdigest()
                if first
                else None
            )
            return {
                "status": "available",
                "reason": "no_events" if high == 0 else None,
                "rows": [dict(row) for row in rows[:SOURCE_PAGE]],
                "has_more": len(rows) > SOURCE_PAGE,
                "marker": marker,
                "high_watermark": high,
            }
    except Exception:  # noqa: BLE001 - owner failures must never halt the paper coordinator or expose raw errors
        return {
            "status": "unavailable",
            "reason": "source_journal_unavailable",
            "rows": [],
            "has_more": False,
        }


def sync(home: Path, manager_home: Path | None = None) -> dict:
    """Mirror one bounded page per source. Repeat while has_more is true."""
    try:
        manager_home = _home(manager_home)
        with _mirror(_path(home)) as db:
            binding = _meta(db, "manager_home")
            if binding is not None and binding != str(manager_home):
                raise ValueError("manager_home_conflict")
            _set(db, "manager_home", str(manager_home))
            added = filtered = 0
            sources = {}
            for source in SOURCES:
                cursor = _meta(db, f"cursor:{source}", 0)
                page = _source_page(manager_home, source, cursor)
                marker = _meta(db, f"marker:{source}")
                if (
                    marker is not None
                    and page.get("marker") is not None
                    and marker != page["marker"]
                ):
                    page = {
                        "status": "unavailable",
                        "reason": "source_journal_replaced",
                        "rows": [],
                        "has_more": False,
                    }
                for row in page["rows"]:
                    event = _event(source, row)
                    db.execute(
                        "INSERT OR IGNORE INTO events(source,source_sequence,body) VALUES(?,?,?)",
                        (source, row["sequence"], _json(event)),
                    )
                    added += db.execute("SELECT changes()").fetchone()[0]
                    filtered += int(event["filtered"])
                    cursor = row["sequence"]
                _set(db, f"cursor:{source}", cursor)
                if page.get("marker") is not None:
                    _set(db, f"marker:{source}", page["marker"])
                sources[source] = {
                    key: value
                    for key, value in page.items()
                    if key not in ("rows", "marker")
                }
                sources[source]["cursor"] = cursor
            _set(db, "sources", sources)
            _set(db, "last_sync", time.time())
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "available",
            "events_added": added,
            "filtered_events": filtered,
            "sources": sources,
            "has_more": any(row["has_more"] for row in sources.values()),
            "manager_mutations": False,
        }
    except Exception:  # noqa: BLE001 - telemetry is optional observation, never a reason to stop trading research
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "telemetry_sync_unavailable",
            "events_added": 0,
            "has_more": False,
            "manager_mutations": False,
        }


def _manager_status(manager_home: Path) -> dict:
    try:
        if (
            not (manager_home / "manager.sqlite3").is_file()
            and not (manager_home / "runtime.sqlite3").is_file()
        ):
            return {
                "status": "unavailable",
                "reason": "manager_not_initialized",
                "bots": [],
            }
        from botmanager.registry import CommandContext, dispatch

        result = dispatch("status", {}, CommandContext(home=manager_home))
        if result.get("ok") is not True:
            return {"status": "unavailable", "reason": "manager_status_unavailable"}
        data = result["data"]
        bots = []
        for row in data.get("bots", [])[:100]:
            bot = {"bot_id": _uuid(row["bot_id"])}
            for key in ("strategy_id", "mode", "lifecycle", "observed_state"):
                value = row.get(key)
                allowed = (
                    {"grid", "dca", "trend", "momentum", "council", "triangle"}
                    if key == "strategy_id"
                    else {"paper", "dry-run", "live"}
                    if key == "mode"
                    else STATES
                )
                bot[key] = value if value in allowed else "unknown"
            bot["armed"] = row.get("armed") if type(row.get("armed")) is bool else None
            financials = row.get("financials", {})
            bot["financials"] = {}
            for key in (
                "exposure_usd",
                "allocated_capital_usd",
                "realized_net_pnl_usd",
                "unrealized_net_pnl_usd",
                "costs_usd",
            ):
                metric = financials.get(key, {}) if isinstance(financials, dict) else {}
                value = metric.get("value") if isinstance(metric, dict) else None
                valid = type(value) in (int, float) and math.isfinite(value)
                bot["financials"][key] = {
                    "value": value if valid else None,
                    "reason": None if valid else "owner_metric_unavailable",
                }
            capital = row.get("configured_virtual_capital", {})
            amount = capital.get("value") if isinstance(capital, dict) else None
            bot["configured_virtual_capital"] = {
                "value": amount if _number(amount) else None,
                "currency": "USD",
                "reserved": False,
                "reason": "configured_virtual_capital_only",
            }
            bots.append(bot)
        return {
            "status": "available",
            "initialized": data.get("initialized") is True,
            "bots": bots,
            "truncated": len(data.get("bots", [])) > 100,
            "source": "botmanager.status",
        }
    except Exception:  # noqa: BLE001 - fixed public owner-boundary error, no submitted content
        return {"status": "unavailable", "reason": "manager_status_unavailable"}


def _logs(manager_home: Path) -> dict:
    """Inspect only an owner's explicit launchd log paths scoped to that home."""
    try:
        from botmanager.service import service

        state = service("status", manager_home)
        definition = Path(state["plist_path"])
        if (
            not state.get("definition_present")
            or not definition.is_file()
            or definition.stat().st_size > 65536
        ):
            return {
                "status": "unavailable",
                "reason": "manager_log_sink_not_configured",
                "files": [],
                "raw_content_mirrored": False,
            }
        payload = plistlib.loads(definition.read_bytes())
        files = []
        for key in ("StandardOutPath", "StandardErrorPath"):
            value = payload.get(key)
            if not isinstance(value, str):
                continue
            path = Path(value)
            if (
                not path.is_absolute()
                or path.is_symlink()
                or not path.resolve().is_relative_to(manager_home.resolve())
            ):
                continue
            try:
                with path.open("rb") as stream:
                    size = os.fstat(stream.fileno()).st_size
                    stream.seek(max(0, size - MAX_LOG_TAIL))
                    tail = stream.read(MAX_LOG_TAIL)
                files.append(
                    {
                        "channel": "stdout" if key == "StandardOutPath" else "stderr",
                        "status": "available",
                        "bytes": size,
                        "tail_bytes": len(tail),
                        "tail_sha256": hashlib.sha256(tail).hexdigest(),
                        "raw_text": "[OMITTED_PRIVATE_LOG_TEXT]",
                    }
                )
            except OSError:
                files.append(
                    {
                        "channel": "stdout" if key == "StandardOutPath" else "stderr",
                        "status": "unavailable",
                        "reason": "log_file_missing",
                    }
                )
        return {
            "status": "available" if files else "unavailable",
            "reason": None if files else "manager_log_sink_not_configured",
            "files": files,
            "raw_content_mirrored": False,
        }
    except Exception:  # noqa: BLE001 - optional file metadata must not stop the coordinator
        return {
            "status": "unavailable",
            "reason": "manager_logs_unavailable",
            "files": [],
            "raw_content_mirrored": False,
        }


def _bootstrap(home: Path) -> dict:
    try:
        path = Path(home) / "state.json"
        if not path.is_file() or path.stat().st_size > 1_048_576:
            raise ValueError
        state = json.loads(path.read_text())
        phase = state.get("phase")
        if phase not in PHASES:
            phase = "unknown"
        batch = state.get("batch_id")
        run = state.get("run_id")
        return {
            "status": "available",
            "phase": phase,
            "run_id": run
            if type(run) is str and re.fullmatch(r"[0-9a-f]{32}", run)
            else None,
            "batch_id": batch
            if type(batch) is str and re.fullmatch(r"[0-9a-f]{32}", batch)
            else None,
            "mode": "paper",
            "live_enabled": False,
        }
    except (OSError, ValueError, TypeError):
        return {"status": "unavailable", "reason": "bootstrap_state_unavailable"}


def report(
    home: Path, manager_home: Path | None = None, *, after: int = 0, limit: int = 100
) -> dict:
    """Read current owner status and a bounded page of sanitized mirrored events."""
    if (
        type(after) is not int
        or after < 0
        or type(limit) is not int
        or not 1 <= limit <= 1000
    ):
        raise ValueError("invalid_telemetry_page")
    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "as_of": time.time(),
        "after": after,
        "events": [],
        "next_after": after,
        "has_more": False,
        "bootstrap": _bootstrap(home),
        "registration_summary": {"status": "unavailable"},
    }
    registrations = read_registrations(home, limit=1)
    result["registration_summary"] = {
        "status": registrations["status"],
        "total": registrations.get("total"),
        "read_only": True,
    }
    try:
        manager_home = _home(manager_home)
        result["manager"] = _manager_status(manager_home)
        result["logs"] = _logs(manager_home)
    except (ImportError, OSError, ValueError, TypeError):
        result["manager"] = {
            "status": "unavailable",
            "reason": "manager_connection_unavailable",
        }
        result["logs"] = {
            "status": "unavailable",
            "reason": "manager_connection_unavailable",
            "files": [],
        }
    try:
        with closing(_read(_path(home))) as db:
            if (
                db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
                or db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
            ):
                raise ValueError
            binding = _meta(db, "manager_home")
            if binding != str(manager_home):
                raise ValueError("manager_home_conflict")
            rows = db.execute(
                "SELECT sequence,source,source_sequence,body FROM events WHERE sequence>? ORDER BY sequence LIMIT ?",
                (after, limit + 1),
            ).fetchall()
            result["sources"] = _public_sources(_meta(db, "sources", {}))
            stamp = _meta(db, "last_sync")
            result["last_sync"] = stamp if _number(stamp) else None
        result["events"] = [
            {
                "sequence": row["sequence"],
                **_public_event(
                    json.loads(row["body"]), row["source"], row["source_sequence"]
                ),
            }
            for row in rows[:limit]
        ]
        result["next_after"] = (
            rows[min(len(rows), limit) - 1]["sequence"] if rows else after
        )
        result["has_more"] = len(rows) > limit
        result["status"] = "available"
        result["reason"] = "no_events" if not rows else None
    except (OSError, ValueError, TypeError, sqlite3.Error):
        result.update(
            status="unavailable",
            reason="telemetry_mirror_unavailable",
            sources={},
            last_sync=None,
        )
    return result

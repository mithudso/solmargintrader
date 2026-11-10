"""Source-bound forward paper accounting, separate from the owner's journals.

Native returns already include costs. Each trial is its own non-overlapping
virtual account; capital is a frozen display basis, never allocated shared cash.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict
from contextlib import closing, contextmanager
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

APP_ID = 0x504E4C31
PAGE = 1000
MAX_ROWS = 100_000
IDENTITY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}\Z")
SECRET = re.compile(
    r"secret|password|credential|authorization|token|private.?key|api.?key|signer",
    re.IGNORECASE,
)
FIELDS = """c.rowid AS source_rowid,t.id AS trial_id,t.asset,t.label,t.minutes,t.execution,
 c.bar,c.issued,c.start,c.finish,c.generation,c.guesses,c.prediction,c.outcome,c.expired,
 c.traded,c.net_return,c.fees_bps,c.borrow_bps,c.slippage_bps,c.liquidated"""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _safe(value, depth=0):
    if depth > 15:
        return None
    if isinstance(value, dict):
        return {
            key: _safe(item, depth + 1)
            for key, item in value.items()
            if not SECRET.search(str(key))
        }
    if isinstance(value, list):
        return [_safe(item, depth + 1) for item in value[:100]]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _path(home):
    return Path(home).expanduser().absolute() / "paper-accounting.sqlite3"


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("source_unavailable")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA trusted_schema=OFF")
    return db


@contextmanager
def _writer(home):
    path = _path(home)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("accounting_store_unavailable")
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(path, timeout=3)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        try:
            app = db.execute("PRAGMA application_id").fetchone()[0]
            tables = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            if not tables and app == 0:
                for statement in (
                    "CREATE TABLE policy(revision INTEGER PRIMARY KEY,effective REAL,enabled INTEGER,created REAL)",
                    "CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT)",
                    "CREATE TABLE projection(source_rowid INTEGER PRIMARY KEY,trial TEXT,bar INTEGER,issued REAL,start REAL,finish REAL,enabled INTEGER,policy_revision INTEGER,identity_sha TEXT,body TEXT)",
                    "CREATE TABLE resolution(source_rowid INTEGER PRIMARY KEY,body TEXT,sha TEXT)",
                    "CREATE TABLE watch(source_rowid INTEGER PRIMARY KEY,last_checked REAL)",
                ):
                    db.execute(statement)
                db.execute("INSERT INTO policy VALUES(0,0,1,?)", (time.time(),))
                for table in ("policy", "projection", "resolution"):
                    for operation in ("UPDATE", "DELETE"):
                        db.execute(
                            f"CREATE TRIGGER no_{table}_{operation} BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT,'immutable accounting evidence'); END"
                        )
                db.execute(f"PRAGMA application_id={APP_ID}")
                db.execute("PRAGMA user_version=1")
            elif app != APP_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("accounting_store_incompatible")
            db.execute(
                "CREATE TABLE IF NOT EXISTS inspection(source_rowid INTEGER PRIMARY KEY,owner_resolved INTEGER,owner_expired INTEGER)"
            )
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


def _policy(row=None):
    return {
        "enabled": bool(row["enabled"]) if row is not None else True,
        "revision": row["revision"] if row is not None else 0,
        "effective_at": row["effective"] if row is not None else 0,
        "semantics": "prospective_by_native_issuance_time_preserve_prior_records",
        "initial_backfill": "existing_native_calls_included_under_default_on_policy",
        "owner_journal_unchanged": True,
    }


def recording(home) -> dict:
    path = _path(home)
    if not path.exists():
        return _policy()
    with closing(_read(path)) as db:
        app = db.execute("PRAGMA application_id").fetchone()[0]
        if (
            app == 0
            and not db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ):
            return _policy()
        if app != APP_ID:
            raise ValueError("accounting_store_incompatible")
        return _policy(
            db.execute("SELECT * FROM policy ORDER BY revision DESC LIMIT 1").fetchone()
        )


def set_recording(home, enabled: bool, expected_revision: int, *, now=None) -> dict:
    now = time.time() if now is None else now
    if (
        type(enabled) is not bool
        or type(expected_revision) is not int
        or expected_revision < 0
        or not _finite(now)
        or now <= 0
    ):
        raise ValueError("invalid_recording_policy")
    with _writer(home) as db:
        current = db.execute(
            "SELECT * FROM policy ORDER BY revision DESC LIMIT 1"
        ).fetchone()
        if current["revision"] != expected_revision:
            raise ValueError("recording_revision_conflict")
        if now < current["effective"]:
            raise ValueError("recording_clock_regressed")
        if bool(current["enabled"]) == enabled:
            return _policy(current)
        revision = current["revision"] + 1
        db.execute(
            "INSERT INTO policy VALUES(?,?,?,?)", (revision, now, int(enabled), now)
        )
        result = _policy(
            db.execute("SELECT * FROM policy WHERE revision=?", (revision,)).fetchone()
        )
    return result


def _batch(home, *, detail=True):
    home = Path(home).expanduser().absolute()
    state_path = home / "state.json"
    if state_path.is_symlink() or state_path.stat().st_size > 2_000_000:
        raise ValueError("batch_state_unavailable")
    state = json.loads(state_path.read_text())
    batch_id = state.get("batch_id")
    if type(batch_id) is not str or not re.fullmatch(r"[0-9a-f]{32}", batch_id):
        raise ValueError("batch_not_available")
    directory = home / "batches" / batch_id
    if directory.is_symlink() or directory.parent.is_symlink():
        raise ValueError("batch_path_unavailable")
    with closing(_read(directory / "batch.sqlite3")) as db:
        metadata = {
            row[0]: json.loads(row[1])
            for row in db.execute("SELECT key,value FROM meta")
        }
        if metadata.get("id") != batch_id or metadata.get("version") != 1:
            raise ValueError("batch_metadata_incompatible")
        quote = state.get("config", {}).get("quote")
        metadata["quote_currency"] = (
            quote
            if isinstance(quote, str) and re.fullmatch(r"[A-Z][A-Z0-9]{0,15}", quote)
            else None
        )
        if not detail:
            return batch_id, directory, metadata, [], {}
        cells = [
            dict(row)
            for row in db.execute("SELECT * FROM cell ORDER BY id LIMIT 10001")
        ]
        if len(cells) > 10000:
            raise ValueError("batch_report_limit_exceeded")
        attempts = defaultdict(list)
        for attempt_count, row in enumerate(
            db.execute(
                "SELECT cell,state,result FROM attempt ORDER BY cell,job_id LIMIT 100001"
            ),
            start=1,
        ):
            attempts[row["cell"]].append((row["state"], row["result"]))
            if attempt_count > MAX_ROWS:
                raise ValueError("attempt_report_limit_exceeded")
    return batch_id, directory, metadata, cells, attempts


def _identity(row, batch_id, now):
    row = dict(row)
    label = row["label"]
    if (
        not isinstance(label, str)
        or not label.startswith(f"f5:{batch_id}:")
        or not isinstance(row["trial_id"], str)
        or not IDENTITY.fullmatch(row["trial_id"])
        or not isinstance(row["asset"], str)
        or not re.fullmatch(r"[A-Z][A-Z0-9]{0,19}", row["asset"])
        or type(row["source_rowid"]) is not int
        or row["source_rowid"] < 1
        or type(row["bar"]) is not int
        or row["bar"] < 0
        or any(not _finite(row[key]) for key in ("issued", "start", "finish"))
        or not 0 <= row["issued"] <= now
        or not row["issued"] < row["start"] < row["finish"]
        or row["prediction"] not in (-1, 0, 1)
    ):
        raise ValueError("invalid_forward_evidence")
    material = {
        key: row[key]
        for key in (
            "source_rowid",
            "trial_id",
            "asset",
            "label",
            "minutes",
            "execution",
            "bar",
            "issued",
            "start",
            "finish",
            "generation",
            "guesses",
            "prediction",
        )
    }
    digest = hashlib.sha256(_json(material).encode()).hexdigest()
    body = {
        key: row[key]
        for key in (
            "trial_id",
            "asset",
            "label",
            "minutes",
            "issued",
            "start",
            "finish",
            "prediction",
        )
    }
    return row, digest, body


def _settled(row, now):
    if row["outcome"] is None or row["finish"] > now:
        return None
    if row["outcome"] not in (-1, 0, 1) or not row["execution"]:
        return None
    keys = ("net_return", "fees_bps", "slippage_bps", "borrow_bps")
    if any(not _finite(row[key]) for key in keys):
        return None
    if (
        row["net_return"] < -1
        or any(row[key] < 0 for key in keys[1:])
        or row["traded"] not in (0, 1)
        or row["liquidated"] not in (0, 1)
    ):
        raise ValueError("invalid_forward_economics")
    return {
        key: row[key]
        for key in (*keys, "outcome", "prediction", "traded", "liquidated", "finish")
    }


def sync(home, *, now=None) -> dict:
    """Project a bounded source page plus a bounded round-robin settlement page."""
    now = time.time() if now is None else now
    if not _finite(now) or now < 0:
        raise ValueError("invalid_accounting_clock")
    batch_id, directory, batch_metadata, _, _ = _batch(home, detail=False)
    source = directory / "forward.sqlite3"
    if not source.exists():
        return {
            "status": "unavailable",
            "reason": "forward_evidence_missing",
            "has_more": False,
        }
    with closing(_read(source)) as native, _writer(home) as db:
        native.execute("BEGIN")
        metadata = dict(db.execute("SELECT key,value FROM meta"))
        if metadata.get("batch_id", batch_id) != batch_id:
            raise ValueError("accounting_batch_changed")
        context_hash = hashlib.sha256(
            _json(
                {
                    key: batch_metadata.get(key)
                    for key in ("id", "code_id", "settings", "quote_currency")
                }
            ).encode()
        ).hexdigest()
        if metadata.get("context_hash", context_hash) != context_hash:
            raise ValueError("accounting_frozen_settings_changed")
        db.execute(
            "INSERT OR REPLACE INTO meta VALUES('context_hash',?)", (context_hash,)
        )
        cursor = int(metadata.get("cursor", "0"))
        high = native.execute(
            "SELECT coalesce(max(c.rowid),0) FROM call c JOIN trial t ON t.id=c.trial WHERE t.label LIKE ?",
            (f"f5:{batch_id}:%",),
        ).fetchone()[0]
        if high < cursor:
            raise ValueError("forward_source_regressed")
        first = native.execute(
            f"SELECT {FIELDS} FROM call c JOIN trial t ON t.id=c.trial WHERE t.label LIKE ? ORDER BY c.rowid LIMIT 1",
            (f"f5:{batch_id}:%",),
        ).fetchone()
        if first is not None:
            _, fingerprint, _ = _identity(first, batch_id, now)
            if metadata.get("first_identity", fingerprint) != fingerprint:
                raise ValueError("forward_source_replaced")
            db.execute(
                "INSERT OR REPLACE INTO meta VALUES('first_identity',?)", (fingerprint,)
            )
        policies = list(db.execute("SELECT * FROM policy ORDER BY effective,revision"))
        rows = native.execute(
            f"SELECT {FIELDS} FROM call c JOIN trial t ON t.id=c.trial WHERE t.label LIKE ? AND c.rowid>? ORDER BY c.rowid LIMIT ?",
            (f"f5:{batch_id}:%", cursor, PAGE),
        ).fetchall()
        for source_row in rows:
            row, identity, body = _identity(source_row, batch_id, now)
            policy = next(
                p for p in reversed(policies) if p["effective"] <= row["issued"]
            )
            db.execute(
                "INSERT INTO projection VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    row["source_rowid"],
                    row["trial_id"],
                    row["bar"],
                    row["issued"],
                    row["start"],
                    row["finish"],
                    policy["enabled"],
                    policy["revision"],
                    identity,
                    _json(body),
                ),
            )
            db.execute("INSERT INTO watch VALUES(?,0)", (row["source_rowid"],))
            cursor = row["source_rowid"]
        watched = db.execute(
            "SELECT source_rowid FROM watch ORDER BY last_checked,source_rowid LIMIT ?",
            (PAGE,),
        ).fetchall()
        for watched_row in watched:
            key = watched_row[0]
            source_row = native.execute(
                f"SELECT {FIELDS} FROM call c JOIN trial t ON t.id=c.trial WHERE c.rowid=?",
                (key,),
            ).fetchone()
            if source_row is None:
                raise ValueError("forward_source_record_missing")
            row, identity, _ = _identity(source_row, batch_id, now)
            projected = db.execute(
                "SELECT identity_sha,enabled FROM projection WHERE source_rowid=?",
                (key,),
            ).fetchone()
            if identity != projected["identity_sha"]:
                raise ValueError("forward_source_record_changed")
            settled = _settled(row, now) if projected["enabled"] else None
            db.execute(
                "INSERT OR REPLACE INTO inspection VALUES(?,?,?)",
                (
                    key,
                    int(row["outcome"] is not None and row["finish"] <= now),
                    int(bool(row["expired"]) and row["finish"] <= now),
                ),
            )
            recorded = db.execute(
                "SELECT body FROM resolution WHERE source_rowid=?", (key,)
            ).fetchone()
            if settled is not None:
                raw = _json(settled)
                if recorded is not None and recorded["body"] != raw:
                    raise ValueError("forward_settlement_changed")
                if recorded is None:
                    db.execute(
                        "INSERT INTO resolution VALUES(?,?,?)",
                        (key, raw, hashlib.sha256(raw.encode()).hexdigest()),
                    )
            elif recorded is not None:
                raise ValueError("forward_settlement_removed")
            db.execute(
                "UPDATE watch SET last_checked=? WHERE source_rowid=?", (now, key)
            )
        db.execute("INSERT OR REPLACE INTO meta VALUES('batch_id',?)", (batch_id,))
        db.execute("INSERT OR REPLACE INTO meta VALUES('cursor',?)", (str(cursor),))
        db.execute("INSERT OR REPLACE INTO meta VALUES('last_sync',?)", (str(now),))
    return {
        "status": "available",
        "has_more": high > cursor,
        "cursor": cursor,
        "high_watermark": high,
        "page_limit": PAGE,
    }


def _trial(rows, capital, recording_enabled, source_available, quote_currency):
    enabled = [row for row in rows if row["enabled"]]
    resolved = [
        json.loads(row["settled"]) for row in enabled if row["settled"] is not None
    ]
    excluded = len(rows) - len(enabled)
    pending = len(enabled) - len(resolved)
    missing_economics = sum(
        bool(row["owner_resolved"]) and row["settled"] is None for row in enabled
    )
    expired = sum(bool(row["owner_expired"]) for row in enabled)
    equity, costs = 1.0, {"fees_bps": 0.0, "slippage_bps": 0.0, "borrow_bps": 0.0}
    for row in resolved:
        for key in costs:
            costs[key] += equity * row[key]
        equity *= 1 + row["net_return"]
    valid = (
        bool(resolved)
        and not excluded
        and not missing_economics
        and not expired
        and source_available
        and math.isfinite(equity)
    )
    reason = (
        "unknown_unrecorded_periods"
        if excluded
        else "unknown_missing_economics"
        if missing_economics
        else "unknown_expired_outcomes"
        if expired
        else "unknown_no_resolved_economics"
        if not resolved
        else "unknown_source_unavailable"
        if not source_available
        else None
    )
    basis_known = _finite(capital) and capital > 0
    value = (equity - 1) * capital if valid and basis_known else None
    assessment = (
        reason
        or (
            "profit_on_resolved_calls"
            if equity > 1
            else "loss_on_resolved_calls"
            if equity < 1
            else "break_even_on_resolved_calls"
        )
        if valid or reason
        else "unknown_accounting_basis"
    )
    return {
        "status": "available" if valid else "unavailable",
        "recording_enabled": recording_enabled,
        "calls": len(rows),
        "recorded": len(enabled),
        "excluded": excluded,
        "resolved": len(resolved),
        "pending": pending,
        "missing_economics": missing_economics,
        "expired": expired,
        "economics_coverage": {
            "resolved_with_costs": len(resolved),
            "resolved_without_economics": missing_economics,
            "expired_outcomes": expired,
        },
        "quote_currency": quote_currency,
        "paper_capital_reference": capital if basis_known else None,
        "realized_pnl_reference": value if quote_currency else None,
        "paper_capital_usd": capital
        if basis_known and quote_currency == "USD"
        else None,
        "realized_pnl_usd": value if quote_currency == "USD" else None,
        "realized_return_percent": (equity - 1) * 100 if valid else None,
        "profit_assessment": assessment,
        "paper_trades": sum(row["traded"] for row in resolved),
        "liquidations": sum(row["liquidated"] for row in resolved),
        "fees_bps": costs["fees_bps"] if valid else None,
        "slippage_bps": costs["slippage_bps"] if valid else None,
        "borrow_bps": costs["borrow_bps"] if valid else None,
        "costs_already_in_net_return": True,
        "unrealized_pnl_usd": None,
        "capital_semantics": "frozen_independent_virtual_trial_basis_not_shared_allocated_cash",
        "semantics": "modelled_paper_net_returns_on_resolved_nonoverlapping_calls",
    }


def report(home, bot_id=None, *, now=None) -> dict:
    now = time.time() if now is None else now
    if bot_id is not None and (
        not isinstance(bot_id, str)
        or len(bot_id) > 200
        or not IDENTITY.fullmatch(bot_id)
    ):
        raise ValueError("invalid_research_bot_id")
    preference = recording(home)
    base = {
        "schema_version": 1,
        "as_of": now,
        "recording": preference,
        "semantics": "modelled_paper_accounts_not_live_profit",
        "coins": [],
    }
    try:
        batch_id, directory, metadata, cells, attempts = _batch(home)
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return {
            **base,
            "status": "unavailable",
            "reason": "backtest_evidence_unavailable",
            "summary": {"total": 0},
        }
    try:
        source = sync(home, now=now)
    except (OSError, ValueError, TypeError, sqlite3.Error):
        source = {
            "status": "unavailable",
            "reason": "forward_source_unavailable_or_changed",
            "has_more": False,
        }
    projection = defaultdict(list)
    path = _path(home)
    if path.exists():
        try:
            with closing(_read(path)) as db:
                rows = db.execute(
                    "SELECT p.*,r.body AS settled,coalesce(i.owner_resolved,0) AS owner_resolved,coalesce(i.owner_expired,0) AS owner_expired FROM projection p LEFT JOIN resolution r USING(source_rowid) LEFT JOIN inspection i USING(source_rowid) ORDER BY p.trial,p.bar LIMIT ?",
                    (MAX_ROWS + 1,),
                ).fetchall()
                if len(rows) > MAX_ROWS:
                    source = {
                        "status": "unavailable",
                        "reason": "accounting_report_limit_exceeded",
                        "has_more": True,
                    }
                else:
                    for row in rows:
                        projection[row["trial"]].append(row)
        except (OSError, ValueError, sqlite3.Error):
            source = {
                "status": "unavailable",
                "reason": "accounting_projection_unavailable",
                "has_more": False,
            }
    if bot_id:
        chosen = next(
            (
                row
                for row in cells
                if str(
                    uuid5(NAMESPACE_URL, f"solmargintrader:f5:{batch_id}:{row['id']}")
                )
                == bot_id
            ),
            None,
        )
        if chosen:
            cells = [
                row
                for row in cells
                if (row["strategy"], row["interval"], row["horizon"])
                == (chosen["strategy"], chosen["interval"], chosen["horizon"])
            ]
        else:
            cells = [row for row in cells if row["strategy"] == bot_id]
    trial_names = {}
    if (directory / "forward.sqlite3").is_file():
        try:
            with closing(_read(directory / "forward.sqlite3")) as db:
                for row in db.execute(
                    "SELECT id,asset,label,minutes FROM trial LIMIT 10001"
                ):
                    trial_names[(row["asset"], row["label"])] = row["id"]
        except sqlite3.Error:
            source["status"] = "unavailable"
    capital = metadata.get("settings", {}).get("capital")
    coins = []
    for cell in cells:
        selected = json.loads(cell["selected"]) if cell.get("selected") else None
        label = f"f5:{batch_id}:{cell['strategy']}:{cell['interval']}:{cell['horizon']}"
        trial = trial_names.get((cell["asset"], label))
        forward = _trial(
            projection.get(trial, []),
            capital,
            preference["enabled"],
            source["status"] == "available" and not source.get("has_more"),
            metadata["quote_currency"],
        )
        forward["trial_id"] = trial
        counts = Counter(state for state, _ in attempts[cell["id"]])
        median_return = None
        for state, raw in attempts[cell["id"]]:
            outcome = json.loads(raw)
            if (
                state == "evaluated"
                and selected
                and outcome.get("params") == selected.get("params")
                and _finite(outcome.get("median_return"))
            ):
                median_return = outcome["median_return"] * 100
                break
        coins.append(
            {
                "bot_id": str(
                    uuid5(NAMESPACE_URL, f"solmargintrader:f5:{batch_id}:{cell['id']}")
                ),
                "asset": cell["asset"],
                "strategy_id": cell["strategy"],
                "interval": cell["interval"],
                "horizon": cell["horizon"],
                "backtest": {
                    "state": cell["state"],
                    "score": cell["score"],
                    "score_semantics": "selected_CPCV_median_sharpe_not_independent_validation",
                    "selected_configuration": _safe(selected),
                    "reason": cell["reason"],
                    "attempts": dict(counts),
                    "median_return_percent": median_return,
                },
                "forward": forward,
            }
        )
    measured = [row for row in coins if row["forward"]["status"] == "available"]
    summary = {
        "total": len(coins),
        "measured_trials": len(measured),
        "profitable_trials": sum(
            row["forward"]["realized_return_percent"] > 0 for row in measured
        ),
        "losing_trials": sum(
            row["forward"]["realized_return_percent"] < 0 for row in measured
        ),
        "unavailable_trials": len(coins) - len(measured),
        "recorded_calls": sum(row["forward"]["recorded"] for row in coins),
        "resolved_calls": sum(row["forward"]["resolved"] for row in coins),
        "excluded_calls": sum(row["forward"]["excluded"] for row in coins),
        "portfolio_pnl_usd": None,
        "reason": "independent_virtual_accounts_have_no_shared_portfolio_allocation",
    }
    return {
        **base,
        "status": "available",
        "batch_id": batch_id,
        "coins": coins,
        "source": source,
        "summary": summary,
        "recording": recording(home),
    }

"""Versioned operator voter selection over unchanged prospective Oracle evidence."""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from oracle.feeds import validate_instrument
from oracle.reader import ReadOnlyOracle
from oracle.strategies import STRATEGY_IDS, StrategySet
from oracle.voting import Vote, aggregate

APP_ID = 0x56544531


def catalog() -> list[dict]:
    return StrategySet().catalog()


def _ids(ids) -> list[str]:
    allowed = set(STRATEGY_IDS)
    if (
        type(ids) is not list
        or len(ids) > 14
        or any(type(value) is not str or value not in allowed for value in ids)
        or len(set(ids)) != len(ids)
    ):
        raise ValueError("invalid_voter_selection")
    return sorted(ids)


def _path(home) -> Path:
    return Path(home).expanduser().absolute() / "voters.sqlite3"


def _read(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("voter_store_unavailable")
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    db.execute("PRAGMA query_only=ON")
    app = db.execute("PRAGMA application_id").fetchone()[0]
    if app != APP_ID and not (
        app == 0
        and not db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    ):
        db.close()
        raise ValueError("voter_store_incompatible")
    return db


def _row(row, instrument):
    if row is None:
        return {
            "instrument": instrument,
            "revision": 0,
            "selected_ids": sorted(STRATEGY_IDS),
            "updated_at": None,
        }
    return {
        "instrument": instrument,
        "revision": row[0],
        "selected_ids": _ids(json.loads(row[1])),
        "updated_at": row[2],
    }


def settings(home, instrument: str) -> dict:
    instrument = validate_instrument(instrument)
    path = _path(home)
    if not path.exists():
        return _row(None, instrument)
    with closing(_read(path)) as db:
        if db.execute("PRAGMA application_id").fetchone()[0] == 0:
            return _row(None, instrument)
        row = db.execute(
            "SELECT revision,selection,created FROM selection WHERE instrument=? ORDER BY revision DESC LIMIT 1",
            (instrument,),
        ).fetchone()
    return _row(row, instrument)


def set_voters(home, instrument: str, ids: list[str], expected_revision: int) -> dict:
    instrument, ids = validate_instrument(instrument), _ids(ids)
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("invalid_voter_revision")
    path = _path(home)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("voter_store_unavailable")
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(path, timeout=3)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        objects = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if not objects:
            db.execute(
                "CREATE TABLE selection(instrument TEXT,revision INTEGER,selection TEXT,created REAL,PRIMARY KEY(instrument,revision))"
            )
            for operation in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER no_{operation} BEFORE {operation} ON selection BEGIN SELECT RAISE(ABORT,'immutable voter history'); END"
                )
            db.execute(f"PRAGMA application_id={APP_ID}")
        elif db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("voter_store_incompatible")
        current = _row(
            db.execute(
                "SELECT revision,selection,created FROM selection WHERE instrument=? ORDER BY revision DESC LIMIT 1",
                (instrument,),
            ).fetchone(),
            instrument,
        )
        if current["revision"] != expected_revision:
            raise ValueError("voter_revision_conflict")
        revision = current["revision"] + 1
        now = time.time()
        db.execute(
            "INSERT INTO selection VALUES(?,?,?,?)",
            (instrument, revision, json.dumps(ids), now),
        )
    return {
        "instrument": instrument,
        "revision": revision,
        "selected_ids": ids,
        "updated_at": now,
    }


def report(
    home, instrument: str, selected_ids=None, *, now: float | None = None
) -> dict:
    instrument = validate_instrument(instrument)
    now = time.time() if now is None else now
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
        raise ValueError("invalid_oracle_clock")
    selection = settings(home, instrument)
    chosen = selection["selected_ids"] if selected_ids is None else _ids(selected_ids)
    cards = [{"strategy_id": key, "selected": key in chosen} for key in STRATEGY_IDS]
    base = {
        "schema_version": 1,
        "instrument": instrument,
        "as_of": now,
        "selection": selection,
        "selected_ids": chosen,
        "catalog": cards,
        "tradable": False,
        "percentage_semantics": "signed_weighted_vote_balance_not_probability",
    }
    path = (
        Path(home).expanduser().absolute()
        / "oracle"
        / instrument.split("/")[0]
        / "history.sqlite3"
    )
    try:
        if path.parent.is_symlink() or path.parent.parent.is_symlink():
            raise ValueError("oracle_archive_unavailable")
        engine = ReadOnlyOracle(path, instrument=instrument, archived_versions=True)
        prediction = engine.predictions(now)
        try:
            graph = engine.graph_history(limit=240)
        except (OSError, ValueError, TypeError, sqlite3.Error):
            graph = {
                "schema_version": 1,
                "status": "unavailable",
                "reason": "graph_history_invalid_or_unavailable",
                "instrument": instrument,
                "ticks": [],
            }
        base["catalog"] = [
            {
                **item,
                "selected": item["strategy_id"] in chosen,
                "metadata_source": "recorded_policy",
            }
            for item in engine.strategies()
        ]
    except (OSError, ValueError, TypeError, sqlite3.Error):
        return {
            **base,
            "status": "unavailable",
            "reason": "oracle_archive_unavailable_or_incompatible",
            "signal": None,
            "balance_percent": None,
            "strategies": [],
            "market": {"status": "unavailable"},
            "aggregate": {
                "status": "unavailable",
                "signal": None,
                "balance_percent": None,
                "included": [],
                "excluded": [],
                "expires_at": None,
            },
            "graph": {
                "schema_version": 1,
                "status": "unavailable",
                "reason": "oracle_archive_unavailable_or_incompatible",
                "instrument": instrument,
                "ticks": [],
            },
        }
    votes, disabled = [], []
    for row in prediction["strategies"]:
        row["selected"] = row["strategy_id"] in chosen
        if not row["selected"]:
            disabled.append(
                {"strategy_id": row["strategy_id"], "reason": "user_disabled"}
            )
        elif row.get("issued_at") is not None:
            votes.append(
                Vote(
                    row["strategy_id"],
                    row["direction"],
                    row["hits"],
                    row["resolved"],
                    row["issued_at"],
                    row["expires_at"],
                )
            )
        else:
            disabled.append(
                {
                    "strategy_id": row["strategy_id"],
                    "reason": row.get("reason", "warmup_required"),
                }
            )
    result = aggregate(votes, now=now, minimum_resolved=engine.minimum_resolved)
    result["excluded"].extend(disabled)
    if not chosen:
        result["reason"] = "no_selected_voters"
    elif not result["included"]:
        result["reason"] = "insufficient_current_voting_evidence"
    if prediction["market"]["status"] != "available":
        result.update(
            status="unavailable",
            signal=None,
            balance_percent=None,
            reason=prediction["market"].get("reason", "market_unavailable"),
        )
    included = {row["strategy_id"] for row in result["included"]}
    result["expires_at"] = min(
        (
            row["expires_at"]
            for row in prediction["strategies"]
            if row["strategy_id"] in included
        ),
        default=None,
    )
    return {
        **prediction,
        **base,
        "graph": graph,
        "status": result["status"],
        "reason": result.get("reason"),
        "signal": result["signal"],
        "balance_percent": result["balance_percent"],
        "aggregate": result,
        "preview": selected_ids is not None,
    }

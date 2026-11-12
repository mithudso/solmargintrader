"""Versioned operator voter selection over unchanged prospective Oracle evidence."""

from __future__ import annotations

import json
import math
import os
import re
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


def _warmup_reference(home, study, now):
    """Expose the carried policy output without crediting a prospective call."""
    winner = study.get("publication")
    if not winner or winner.get("available") or winner.get("reason") != "first_post_start_closed_bar":
        return study
    try:
        from backtester.core.zec_ensemble import candidate_id

        from .zec_forward import (
            INTERVALS,
            canonical,
            connection,
            digest,
            implementation,
        )

        pointer_path = Path(home).expanduser().absolute() / "zec-study.json"
        if pointer_path.is_symlink():
            return study
        pointer = json.loads(pointer_path.read_text())
        if pointer["selection_hash"] != study["selection_hash"]:
            return study
        with connection(pointer["home"]) as db:
            db.execute("BEGIN")
            metadata = {row[0]: row[1] for row in db.execute("SELECT key,value FROM metadata")}
            row = db.execute("SELECT * FROM candidates WHERE id=?", (winner["id"],)).fetchone()
            if row is None or metadata["implementation"] != canonical(implementation()):
                return study
            if metadata["selection_hash"] != study["selection_hash"]:
                return study
            interval = INTERVALS[row["interval"]]
            close = row["last_ts"] + interval
            heartbeat = float(metadata["heartbeat"])
            if (row["status"] != "waiting" or row["reason"] != "first_post_start_closed_bar"
                    or row["last_ts"] >= row["activation"]
                    or not 0 <= now - heartbeat <= 35
                    or not 0 <= now - row["updated"] <= 35
                    or not 0 <= now - close < interval):
                return study
            candidate = json.loads(row["config"])
            if (candidate_id(candidate["config"]) != winner["id"]
                    or digest(candidate["config"]) != winner["config_hash"]):
                return study
            raw = json.loads(row["state"])["strategy_state"]["inner"]["persistence"]["last"]
            if type(raw) not in (int, float) or not math.isfinite(raw) or not 0 <= raw <= 1:
                return study
            reference = {**winner, "available": True, "target": raw,
                         "issued_at": row["updated"], "decision_close": close,
                         "expires_at": close + interval, "reason": "historical_warmup_reference",
                         "historical_warmup": True, "prospective": False,
                         "source_basis_close": close}
        # Accounts, P&L, paper forecasts, and their activation remain untouched.
        return {**study, "publication": reference, "reference_kind": "historical_warmup"}
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        return study


def _report(
    home, instrument: str, selected_ids=None, *, now: float | None = None, display_strategy=None
) -> dict:
    instrument = validate_instrument(instrument)
    now = time.time() if now is None else now
    if type(now) not in (int, float) or not math.isfinite(now) or now < 0:
        raise ValueError("invalid_oracle_clock")
    from .zec_forward import oracle_view, publication

    study = publication(home, instrument, now=now, display_strategy=display_strategy)
    if study and study["selected"]:
        study = _warmup_reference(home, study, now)
        winner = study.get("publication")
        if winner:
            # Cash-only priming observations are not issued ensemble forecasts.
            study["history"] = [row for row in study.get("history", [])
                                if row["bar"] >= winner["activation"]]
        view = oracle_view(study, now=now)
        if study.get("reference_kind") == "historical_warmup":
            view.update(reference_kind="historical_warmup", prospective=False)
        return view
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
        "selected_experiment": study,
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
        base["native_interval"] = _interval_name(engine.bar_seconds)
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


def _interval_name(seconds):
    for suffix, scale in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if seconds % scale == 0:
            return str(seconds // scale) + suffix


def _unavailable_display(view, reason):
    return {**view, "status": "unavailable", "reason": reason, "signal": None,
            "balance_percent": None, "strategies": [],
            "market": {"status": "unavailable", "reason": reason},
            "aggregate": {"status": "unavailable", "reason": reason, "signal": None,
                          "balance_percent": None, "expires_at": None, "included": [], "excluded": []},
            "graph": {"status": "unavailable", "reason": reason, "instrument": view["instrument"], "ticks": []}}


def report(home, instrument: str, selected_ids=None, *, now=None, interval=None, strategy=None):
    """Display filters never change saved voters, worker policy, or native cadence."""
    if interval is not None and (not isinstance(interval, str) or not re.fullmatch(r"[1-9][0-9]{0,5}[smhd]", interval)):
        raise ValueError("invalid_oracle_display_interval")
    if strategy is not None and (not isinstance(strategy, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,120}", strategy)):
        raise ValueError("invalid_oracle_display_strategy")
    requested = strategy or "published"
    explicit = requested != "published"
    ids = [requested] if explicit and requested in STRATEGY_IDS else selected_ids
    view = _report(home, instrument, ids, now=now, display_strategy=requested)
    study = view.get("selected_experiment")
    selected_study = bool(study and study.get("selected"))
    if selected_study:
        accounts = study.get("accounts", [])
        strategies = [{"id": row["id"], "label": "#" + str(row["rank"]) + " " +
                       ", ".join(member["strategy"] for member in row["candidate"]["config"]["members"]) +
                       " (" + row["interval"] + ")", "interval": row["interval"]} for row in accounts]
        native = study.get("publication", {}).get("interval") if study.get("publication") else None
        available = sorted({row["interval"] for row in accounts})
    else:
        strategies = [{"id": row["strategy_id"], "label": row["strategy_id"]} for row in view.get("catalog", [])]
        native = view.get("native_interval")
        available = [native] if native else []
    display = {"instrument": view["instrument"], "interval": interval or native, "requested_interval": interval,
               "strategy": requested, "available_intervals": available, "strategies": strategies,
               "publication_instrument": study.get("instrument") if study else None,
               "published_strategy": study.get("accounts", [{}])[0].get("id") if selected_study else "published",
               "scope": "read_only_display_native_forecasts_no_resampling"}
    if explicit and requested not in {row["id"] for row in strategies}:
        view = _unavailable_display(view, "requested_strategy_unavailable_for_instrument")
    elif interval is not None and native != interval:
        view = _unavailable_display(view, "requested_interval_unavailable_no_native_forecasts")
    elif explicit and not selected_study:
        view["strategies"] = [row for row in view.get("strategies", []) if row["strategy_id"] == requested]
        graph = dict(view.get("graph", {}))
        graph["ticks"] = [{**row, "strategies": [entry for entry in row.get("strategies", []) if entry["strategy_id"] == requested],
                            "aggregate": None} for row in graph.get("ticks", [])]
        graph["hide_aggregate"] = True
        view["graph"] = graph
        view["preview"] = True
    view["display"] = display
    if "graph" in view:
        view["graph"]["view_key"] = view["instrument"] + ":" + str(display["interval"]) + ":" + requested
    return view

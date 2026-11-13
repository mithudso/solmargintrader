"""Versioned per-instrument display cadence, separate from research policies."""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from oracle.feeds import validate_instrument

MIN_SECONDS, MAX_SECONDS = 5, 300
APP_ID = 0x46525031


def path(home):
    return Path(home).expanduser().absolute() / "forecast-preferences.sqlite3"


def valid_seconds(value):
    return type(value) is int and MIN_SECONDS <= value <= MAX_SECONDS


def settings(home, instrument):
    instrument = validate_instrument(instrument)
    result = {"instrument": instrument, "seconds": 10, "revision": 0}
    source = path(home)
    if not source.exists():
        return result
    if source.is_symlink() or not source.is_file():
        raise ValueError("forecast_preferences_unavailable")
    with closing(
        sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=2)
    ) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("forecast_preferences_incompatible")
        row = db.execute(
            "SELECT seconds,revision FROM settings WHERE instrument=? ORDER BY revision DESC LIMIT 1",
            (instrument,),
        ).fetchone()
    if row:
        if not valid_seconds(row[0]) or type(row[1]) is not int or row[1] < 1:
            raise ValueError("forecast_preferences_invalid")
        result.update(seconds=row[0], revision=row[1])
    return result


def set_seconds(home, instrument, seconds, expected_revision):
    instrument = validate_instrument(instrument)
    if (
        not valid_seconds(seconds)
        or type(expected_revision) is not int
        or expected_revision < 0
    ):
        raise ValueError("invalid_forecast_seconds")
    source = path(home)
    source.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        source.parent.is_symlink()
        or source.is_symlink()
        or source.exists()
        and not source.is_file()
    ):
        raise ValueError("forecast_preferences_unavailable")
    fd = os.open(source, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    with closing(sqlite3.connect(source, timeout=3)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        objects = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if not objects:
            db.execute(
                "CREATE TABLE settings(instrument TEXT,seconds INTEGER,revision INTEGER,created REAL,PRIMARY KEY(instrument,revision))"
            )
            db.execute(f"PRAGMA application_id={APP_ID}")
            for operation in ("UPDATE", "DELETE"):
                db.execute(
                    f"CREATE TRIGGER immutable_{operation} BEFORE {operation} ON settings BEGIN SELECT RAISE(ABORT,'immutable display preference history'); END"
                )
        elif db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("forecast_preferences_incompatible")
        row = db.execute(
            "SELECT revision FROM settings WHERE instrument=? ORDER BY revision DESC LIMIT 1",
            (instrument,),
        ).fetchone()
        revision = row[0] if row else 0
        if revision != expected_revision:
            raise ValueError("forecast_preferences_revision_conflict")
        db.execute(
            "INSERT INTO settings VALUES(?,?,?,?)",
            (instrument, seconds, revision + 1, time.time()),
        )
    return {"instrument": instrument, "seconds": seconds, "revision": revision + 1}

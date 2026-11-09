"""Immutable, validated offline OHLCV snapshots backed by SQLite.

Source labels are supplied by the operator; they are not independently verified.
Import leaves the original file untouched. The caller owns independent backups.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import struct
from contextlib import closing

from .run_archive import ArchiveError, _connect

COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def _schema(db: sqlite3.Connection) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS history_snapshots (snapshot_id TEXT PRIMARY KEY, metadata TEXT NOT NULL, rows_sha256 TEXT NOT NULL, count INTEGER NOT NULL, first_ts INTEGER NOT NULL, last_ts INTEGER NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS history_bars (snapshot_id TEXT NOT NULL REFERENCES history_snapshots(snapshot_id), ts INTEGER NOT NULL, o REAL NOT NULL, h REAL NOT NULL, l REAL NOT NULL, c REAL NOT NULL, v REAL NOT NULL, PRIMARY KEY(snapshot_id, ts)) WITHOUT ROWID")


def _hash_row(digest, row: tuple) -> None:
    digest.update(struct.pack(">q5d", *row))


def import_history(archive: str | Path, csv_path: str | Path, *, instrument: str,
                   venue: str, source: str, interval_seconds: int) -> str:
    """Validate a contiguous CSV and atomically store an immutable revision.

    Timestamps are bar opens in UTC epoch seconds. Instrument, venue and source
    must be explicit. Identical content and metadata have the same identity.
    """
    if not all(isinstance(x, str) and x.strip() for x in (instrument, venue, source)):
        raise ArchiveError("instrument, venue and source are required")
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds <= 0:
        raise ArchiveError("interval_seconds must be a positive integer")
    metadata = json.dumps({"schema": 1, "instrument": instrument, "venue": venue,
                           "source": source, "interval_seconds": interval_seconds,
                           "timestamp_semantics": "utc_bar_open"}, sort_keys=True, separators=(",", ":"))
    # A temporary SQLite table bounds Python memory without publishing partial rows.
    with closing(_connect(Path(archive))) as db, db:
        _schema(db)
        db.execute("CREATE TEMP TABLE incoming (ts INTEGER PRIMARY KEY, o REAL, h REAL, l REAL, c REAL, v REAL)")
        digest = hashlib.sha256()
        count = 0
        first = last = None
        with Path(csv_path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != list(COLUMNS):
                raise ArchiveError("CSV columns must exactly match timestamp,open,high,low,close,volume")
            for record in reader:
                try:
                    if None in record or any(record[c] is None for c in COLUMNS):
                        raise ValueError("malformed row")
                    ts = int(record["timestamp"])
                    values = tuple(0.0 if float(record[c]) == 0 else float(record[c]) for c in COLUMNS[1:])
                except (ValueError, TypeError, OverflowError) as exc:
                    raise ArchiveError(f"invalid row {count + 2}") from exc
                o, h, low, c, volume = values
                if (ts < 0 or ts > 10_000_000_000 or ts % interval_seconds or
                    not all(math.isfinite(v) for v in values) or
                    min(o, h, low, c) <= 0 or volume < 0 or
                    h < max(o, low, c) or low > min(o, h, c) or
                    (last is not None and ts != last + interval_seconds)):
                    raise ArchiveError(f"invalid or noncontiguous bar at row {count + 2}")
                row = (ts, *values)
                _hash_row(digest, row)
                db.execute("INSERT INTO incoming VALUES (?, ?, ?, ?, ?, ?)", row)
                first = ts if first is None else first
                last = ts
                count += 1
        if not count:
            raise ArchiveError("empty history")
        rows_hash = digest.hexdigest()
        snapshot_id = hashlib.sha256((metadata + "\n" + rows_hash).encode()).hexdigest()
        db.commit()  # Commit only the connection-local staging table.
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute("SELECT 1 FROM history_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if existing:
            _verify(db, snapshot_id)
        else:
            db.execute("INSERT INTO history_snapshots VALUES (?, ?, ?, ?, ?, ?)", (snapshot_id, metadata, rows_hash, count, first, last))
            db.execute("INSERT INTO history_bars SELECT ?, ts, o, h, l, c, v FROM incoming", (snapshot_id,))
        return snapshot_id


def _verify(db: sqlite3.Connection, snapshot_id: str) -> dict:
    row = db.execute("SELECT metadata, rows_sha256, count, first_ts, last_ts FROM history_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
    if row is None:
        raise ArchiveError("snapshot not found")
    metadata, expected, count, first, last = row
    if hashlib.sha256((metadata + "\n" + expected).encode()).hexdigest() != snapshot_id:
        raise ArchiveError("snapshot metadata mismatch")
    try:
        info = json.loads(metadata)
        step = info["interval_seconds"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ArchiveError("invalid snapshot metadata") from exc
    digest = hashlib.sha256()
    n = 0
    prev = None
    for bar in db.execute("SELECT ts,o,h,l,c,v FROM history_bars WHERE snapshot_id=? ORDER BY ts", (snapshot_id,)):
        if prev is not None and bar[0] != prev + step:
            raise ArchiveError("snapshot cadence mismatch")
        if n == 0 and bar[0] != first:
            raise ArchiveError("snapshot start mismatch")
        _hash_row(digest, bar)
        prev = bar[0]
        n += 1
    if n != count or prev != last or digest.hexdigest() != expected:
        raise ArchiveError("snapshot content mismatch")
    return {**info, "count": count, "first_ts": first, "last_ts": last}


def snapshot_info(archive: str | Path, snapshot_id: str) -> dict:
    """Verify and describe a stored snapshot."""
    path = Path(archive)
    if not path.exists():
        raise ArchiveError("archive not found")
    with closing(_connect(path)) as db:
        db.execute("BEGIN")
        return _verify(db, snapshot_id)


def read_history(archive: str | Path, snapshot_id: str, start: int, end: int) -> tuple[dict, list[tuple]]:
    """Verify a snapshot and return an inclusive, fully covered UTC range."""
    path = Path(archive)
    if not path.exists():
        raise ArchiveError("archive not found")
    if isinstance(start, bool) or isinstance(end, bool) or not isinstance(start, int) or not isinstance(end, int) or start > end:
        raise ArchiveError("invalid requested range")
    with closing(_connect(path)) as db:
        db.execute("BEGIN")
        info = _verify(db, snapshot_id)
        step = info["interval_seconds"]
        if start < info["first_ts"] or end > info["last_ts"] or start % step or end % step:
            raise ArchiveError("requested range is not fully covered")
        rows = list(db.execute("SELECT ts,o,h,l,c,v FROM history_bars WHERE snapshot_id=? AND ts BETWEEN ? AND ? ORDER BY ts", (snapshot_id, start, end)))
        if len(rows) != (end - start) // step + 1:
            raise ArchiveError("requested range is incomplete")
        return info, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--instrument", required=True)
    parser.add_argument("--venue", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--interval-seconds", required=True, type=int)
    args = parser.parse_args()
    print(import_history(args.archive, args.csv, instrument=args.instrument, venue=args.venue,
                         source=args.source, interval_seconds=args.interval_seconds))


if __name__ == "__main__":
    main()

"""Resumable, source-preserving KuCoin spot candle collection.

Each completed time window commits its raw response and normalized observations
in one SQLite transaction. Missing candles remain missing; no prices are invented.
Only fully closed UTC minutes are requested. This module never trades.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import re
from pathlib import Path
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing

MINUTE = 60
WINDOW = 1440 * MINUTE  # below KuCoin's documented 1500-candle maximum
URL = "https://api.kucoin.com/api/v1/market/candles"
MAX_PAGE_BYTES = 2 * 1024 * 1024


class HistoryError(ValueError):
    pass


def decode_page(raw: bytes, start: int, end: int) -> list[tuple[int, float, float, float, float, float]]:
    """Parse the documented [time, open, close, high, low, volume, turnover] format."""
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict) or payload.get("code") != "200000" or not isinstance(payload.get("data"), list):
            raise ValueError("provider returned an error or malformed payload")
        if len(payload["data"]) > 1440:
            raise ValueError("page exceeds expected window capacity")
        result = {}
        for item in payload["data"]:
            if not isinstance(item, list) or len(item) != 7:
                raise ValueError("unexpected candle schema")
            timestamp = item[0]
            if not (type(timestamp) is int or isinstance(timestamp, str) and re.fullmatch(r"0|[1-9][0-9]*", timestamp)):
                raise ValueError("timestamp must be an exact integer")
            ts = int(timestamp); op, close, high, low, volume, turnover = map(float, item[1:])
            if (ts % MINUTE or not start <= ts < end or not all(math.isfinite(v) for v in (op, close, high, low, volume, turnover))
                    or min(op, close, high, low) <= 0 or volume < 0 or turnover < 0
                    or high < max(op, close, low) or low > min(op, close, high)):
                raise ValueError("invalid or out-of-window candle")
            row = (ts, op, high, low, close, volume)
            if ts in result:
                raise ValueError("duplicate timestamp in provider page")
            result[ts] = row
        return [result[k] for k in sorted(result)]
    except (ValueError, TypeError, OverflowError, KeyError) as exc:
        raise HistoryError(f"invalid KuCoin page: {exc}") from exc


def open_store(path: Path, symbol: str) -> sqlite3.Connection:
    if path.is_symlink():
        raise HistoryError("database path cannot be a symlink")
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    if not path.is_file() or path.stat().st_mode & 0o077:
        raise HistoryError("database must be a private regular file")
    db = sqlite3.connect(path, timeout=30)
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS pages (start INTEGER PRIMARY KEY, end INTEGER NOT NULL, fetched_at INTEGER NOT NULL, sha256 TEXT NOT NULL, raw BLOB NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS candles (ts INTEGER PRIMARY KEY, open REAL NOT NULL, high REAL NOT NULL, low REAL NOT NULL, close REAL NOT NULL, volume REAL NOT NULL, page_start INTEGER NOT NULL REFERENCES pages(start))")
        db.execute("CREATE INDEX IF NOT EXISTS candles_page ON candles(page_start,ts)")
        expected = {"schema": "2", "window_end": "exclusive", "venue": "kucoin", "symbol": symbol, "interval_seconds": "60", "timestamp": "utc_bar_open", "source": URL}
        existing = dict(db.execute("SELECT key,value FROM metadata"))
        if existing and existing != expected:
            raise HistoryError("database metadata does not match requested market")
        if not existing:
            db.executemany("INSERT INTO metadata VALUES (?,?)", expected.items())
            db.commit()
        return db
    except BaseException:
        db.close()
        raise


def _get(url: str, *, timeout: float = 15) -> bytes:
    lock_path = os.environ.get("KUCOIN_HTTP_LOCK")
    if not lock_path:
        return _get_unlocked(url, timeout=timeout)
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        if os.fstat(fd).st_mode & 0o077:
            raise HistoryError("shared HTTP lock must be private")
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            # The lock remains held through 429 retry/backoff, pausing peers.
            return _get_unlocked(url, timeout=timeout)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _get_unlocked(url: str, *, timeout: float = 15) -> bytes:
    for attempt in range(5):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "solmargintrader-research/1.0"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read(MAX_PAGE_BYTES + 1)
                if len(raw) > MAX_PAGE_BYTES:
                    raise HistoryError("provider page exceeds byte capacity")
                return raw
        except urllib.error.HTTPError as exc:
            if exc.code != 429 and exc.code < 500:
                raise
            if attempt == 4:
                raise
            try:
                wait = max(float(exc.headers.get("Retry-After", "0")), float(exc.headers.get("gw-ratelimit-reset", "0")) / 1000)
            except (TypeError, ValueError):
                wait = 0
            time.sleep(max(wait, min(30, 2 ** attempt)))
        except (urllib.error.URLError, TimeoutError):
            if attempt == 4:
                raise
            time.sleep(min(30, 2 ** attempt))
    raise AssertionError("unreachable")


def _verified_saved_page(db: sqlite3.Connection, lo: int, hi: int, saved: tuple) -> list[tuple]:
    if saved[0] != hi or hashlib.sha256(saved[2]).hexdigest() != saved[1]:
        raise HistoryError("existing page has mismatched bounds or checksum")
    expected = decode_page(saved[2], lo, hi)
    actual = db.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE page_start=? ORDER BY ts", (lo,)).fetchall()
    if expected != actual:
        raise HistoryError("existing normalized candles differ from source page")
    return expected


def collect(path: Path, symbol: str, start: int, end: int, *, base_url: str = URL,
            delay: float = 0.5) -> dict:
    """Collect [start,end) in fixed, crash-recoverable daily windows."""
    if (not symbol or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for c in symbol)
            or start < 0 or start >= end or start % MINUTE or end % MINUTE or end > int(time.time()) // MINUTE * MINUTE
            or delay < 0):
        raise HistoryError("invalid symbol, bounds, or delay")
    fetched = skipped = 0
    with closing(open_store(path, symbol)) as db:
        for lo in range(start, end, WINDOW):
            hi = min(lo + WINDOW, end)
            old = db.execute("SELECT end,sha256,raw FROM pages WHERE start=?", (lo,)).fetchone()
            if old:
                _verified_saved_page(db, lo, hi, old)
                skipped += 1
                continue
            query = urllib.parse.urlencode({"symbol": symbol, "type": "1min", "startAt": lo, "endAt": hi})
            raw = _get(base_url + "?" + query)
            rows = decode_page(raw, lo, hi)
            digest = hashlib.sha256(raw).hexdigest()
            with db:
                db.execute("BEGIN IMMEDIATE")
                raced = db.execute("SELECT end,sha256,raw FROM pages WHERE start=?", (lo,)).fetchone()
                if raced:
                    if _verified_saved_page(db, lo, hi, raced) != rows:
                        raise HistoryError("concurrent source response conflicts with stored page")
                    skipped += 1
                else:
                    db.execute("INSERT INTO pages VALUES (?,?,?,?,?)", (lo, hi, int(time.time()), digest, raw))
                    db.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?)", ((*row, lo) for row in rows))
                    fetched += 1
            if fetched and fetched % 50 == 0 and not raced:
                print(f"{symbol}: {fetched} pages fetched, {skipped} previously verified", flush=True)
            if delay:
                time.sleep(delay)
        bars = db.execute("SELECT count(*) FROM candles WHERE ts>=? AND ts<?", (start, end)).fetchone()[0]
    return {"symbol": symbol, "start": start, "end": end, "pages_fetched": fetched,
            "pages_reused": skipped, "bars": bars, "missing_slots": (end-start)//MINUTE-bars}


def read_range(path: Path, symbol: str, start: int, end: int) -> list[tuple]:
    """Verify source bytes and normalized rows, then refuse any missing minute."""
    if start < 0 or start >= end or start % MINUTE or end % MINUTE:
        raise HistoryError("invalid range")
    if not path.exists():
        raise HistoryError("database does not exist")
    with closing(open_store(path, symbol)) as db:
        db.execute("BEGIN")
        pages = list(db.execute("SELECT start,end,sha256,raw FROM pages WHERE start<? AND end>? ORDER BY start", (end, start)))
        cursor = start
        prior_end = None
        for lo, hi, digest, raw in pages:
            if prior_end is not None and lo < prior_end:
                raise HistoryError("overlapping source pages")
            prior_end = hi
            if lo > cursor or hashlib.sha256(raw).hexdigest() != digest:
                raise HistoryError("missing or corrupt source page")
            expected = decode_page(raw, lo, hi)
            actual = db.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE page_start=? ORDER BY ts", (lo,)).fetchall()
            if expected != actual:
                raise HistoryError("normalized candles differ from source page")
            cursor = max(cursor, hi)
        if cursor < end:
            raise HistoryError("requested range has uncollected windows")
        rows = db.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE ts>=? AND ts<? ORDER BY ts", (start, end)).fetchall()
        if len(rows) != (end - start) // MINUTE:
            raise HistoryError("requested range contains missing candles")
        return rows


def audit_store(path: Path, symbol: str, start: int, end: int, gap_file: Path) -> dict:
    """Verify committed pages and list absent intervals without inventing candles.

    The database is read in one snapshot. UNFETCHED means no page was committed;
    UNOBSERVED means a committed provider response omitted those minutes. The
    latter is not evidence that trading was quiet. End timestamps are exclusive.
    """
    if start < 0 or start >= end or start % MINUTE or end % MINUTE or not path.exists():
        raise HistoryError("invalid range or missing database")
    if gap_file.exists():
        raise HistoryError("refusing to overwrite gap ledger")
    temp = gap_file.with_name(gap_file.name + ".partial")
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    counts = {"pages_verified": 0, "pages_unfetched": 0, "bars": 0, "unobserved_slots": 0, "unfetched_slots": 0, "gap_runs": 0}
    try:
        with os.fdopen(fd, "w", newline="") as out, closing(open_store(path, symbol)) as db:
            db.execute("BEGIN")
            writer = csv.writer(out, lineterminator="\n")
            writer.writerow(["start_utc_epoch", "end_exclusive_utc_epoch", "status"])
            planned = {lo: min(lo + WINDOW, end) for lo in range(start, end, WINDOW)}
            for existing_lo, existing_hi in db.execute(
                    "SELECT start,end FROM pages WHERE start<? AND end>?", (end, start)):
                if planned.get(existing_lo) != existing_hi:
                    raise HistoryError("overlapping or differently bounded source page")
            pending = None
            def gap(lo: int, hi: int, status: str) -> None:
                nonlocal pending
                if lo >= hi:
                    return
                counts["unfetched_slots" if status == "UNFETCHED" else "unobserved_slots"] += (hi - lo) // MINUTE
                if pending and pending[1] == lo and pending[2] == status:
                    pending = (pending[0], hi, status)
                else:
                    if pending:
                        writer.writerow(pending); counts["gap_runs"] += 1
                    pending = (lo, hi, status)
            for lo in range(start, end, WINDOW):
                hi = min(lo + WINDOW, end)
                page = db.execute("SELECT end,sha256,raw FROM pages WHERE start=?", (lo,)).fetchone()
                if not page:
                    counts["pages_unfetched"] += 1; gap(lo, hi, "UNFETCHED"); continue
                if page[0] != hi or hashlib.sha256(page[2]).hexdigest() != page[1]:
                    raise HistoryError("page bounds or source checksum mismatch")
                expected = decode_page(page[2], lo, hi)
                actual = db.execute("SELECT ts,open,high,low,close,volume FROM candles WHERE page_start=? ORDER BY ts", (lo,)).fetchall()
                if expected != actual:
                    raise HistoryError("normalized candles differ from source page")
                counts["pages_verified"] += 1; counts["bars"] += len(actual)
                cursor = lo
                for row in actual:
                    gap(cursor, row[0], "UNOBSERVED"); cursor = row[0] + MINUTE
                gap(cursor, hi, "UNOBSERVED")
            if pending:
                writer.writerow(pending); counts["gap_runs"] += 1
            out.flush(); os.fsync(out.fileno())
        # Hard-link publication is atomic and refuses an existing destination.
        os.link(temp, gap_file)
        temp.unlink()
        return {"symbol": symbol, "start": start, "end": end, **counts}
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--start", required=True, type=int, help="inclusive UTC epoch seconds")
    parser.add_argument("--end", required=True, type=int, help="exclusive UTC epoch seconds")
    args = parser.parse_args()
    print(json.dumps(collect(args.database, args.symbol, args.start, args.end), sort_keys=True))


if __name__ == "__main__":
    main()

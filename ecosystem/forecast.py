"""Continuous, provisional price projections. No orders or account mutations.

The direction is the chosen price-only strategy's exposure sign on ten-second
reference bars. The target distance is the recent median absolute reference
move at the requested horizon. It is an indicative projection, not a fitted
expected return or a calibrated probability. Qualification of the original
Oracle ensemble remains entirely separate.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
import math
import os
import signal
import sqlite3
import stat
import statistics
import threading
import time
import zlib
from collections import defaultdict
from contextlib import closing, suppress
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

from oracle.feeds import validate_instrument
from oracle.strategies import STRATEGY_IDS, StrategySet

from .forecast_preferences import settings, valid_seconds

BAR_SECONDS = 10
REFRESH_SECONDS = 10
HORIZONS = (10, 60)
MAX_AGE = 15
APP_ID = 0x46524331
MAX_SNAPSHOT_BYTES = 1_048_576
LOGGER = logging.getLogger(__name__)
METHOD = "strategy_direction_times_recent_median_absolute_log_horizon_move"


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


@lru_cache(maxsize=1)
def policy_id():
    catalog = [
        {key: row[key] for key in ("strategy_id", "version", "parameters")}
        for row in StrategySet().catalog()
    ]
    material = Path(__file__).read_bytes() + canonical(catalog).encode()
    return hashlib.sha256(material).hexdigest()


def directory(home):
    return Path(home).expanduser().absolute() / "live-forecast" / policy_id()[:16]


def scope_id(home):
    return hashlib.sha256(str(Path(home).expanduser().absolute()).encode()).hexdigest()


def snapshot(raw, now):
    """Keep only exact, fresh observed pairs; never substitute USD/USDT/USDC."""
    if not isinstance(raw, dict) or not finite(raw.get("t")):
        return {}
    stamp = raw["t"]
    if not 0 <= now - stamp <= MAX_AGE or not isinstance(raw.get("q"), dict):
        return {}
    result = {}
    for product, quote in raw["q"].items():
        if (
            not isinstance(product, str)
            or not isinstance(quote, list)
            or len(quote) < 6
        ):
            continue
        try:
            instrument = validate_instrument(product.replace("-", "/"))
        except ValueError:
            continue
        bid, ask, observed = quote[0], quote[1], quote[5]
        if not all(finite(x) for x in (bid, ask, observed)):
            continue
        if (
            not 0 < bid <= ask
            or not 0 <= stamp - observed <= MAX_AGE
            or not 0 <= now - observed <= MAX_AGE
        ):
            continue
        result[instrument] = {
            "at": stamp,
            "observed_at": observed,
            "price": bid + (ask - bid) / 2,
        }
    return result


def history_tail(
    path, *, compressed_limit=4 * 1024 * 1024, decoded_limit=64 * 1024 * 1024
):
    """Read complete CRC-validated recorder members from a bounded file tail.

    Each recorder flush is a complete gzip member of complete JSONL records.
    An unfinished final member contributes no history. The recorder is never
    repaired, locked or changed by this reader.
    """
    with path.open("rb") as stream:
        stream.seek(max(0, path.stat().st_size - compressed_limit))
        raw = stream.read(compressed_limit)
    cursor, decoded = 0, 0
    while (start := raw.find(b"\x1f\x8b\x08", cursor)) >= 0:
        decoder = zlib.decompressobj(31)
        try:
            member = decoder.decompress(
                raw[start:], min(2 * 1024 * 1024, decoded_limit - decoded) + 1
            )
        except zlib.error:
            cursor = start + 3
            continue
        if not decoder.eof:
            cursor = start + 3
            continue
        decoded += len(member)
        if decoded > decoded_limit or len(member) > 2 * 1024 * 1024:
            return
        cursor = len(raw) - len(decoder.unused_data)
        for line in member.splitlines():
            try:
                row = json.loads(line)
            except (ValueError, UnicodeError):
                continue
            yield row


class Bars:
    def __init__(self):
        self.rows = defaultdict(dict)
        self.samples = defaultdict(dict)

    def add(self, instrument, quote):
        second = int(quote["at"])
        samples = self.samples[instrument]
        samples[second] = quote["price"]
        for key in list(samples):
            if key < second - 3600:
                del samples[key]
        bucket = int(quote["at"] // BAR_SECONDS) * BAR_SECONDS
        rows = self.rows[instrument]
        row = rows.setdefault(
            bucket,
            {
                "ts": bucket,
                "open": quote["price"],
                "high": quote["price"],
                "low": quote["price"],
                "close": quote["price"],
            },
        )
        row.update(
            high=max(row["high"], quote["price"]),
            low=min(row["low"], quote["price"]),
            close=quote["price"],
        )
        for key in list(rows):
            if key < bucket - 360 * BAR_SECONDS:
                del rows[key]

    def completed(self, instrument, now):
        rows, keys = self.rows[instrument], []
        cursor = int(now // BAR_SECONDS) * BAR_SECONDS - BAR_SECONDS
        while cursor in rows and len(keys) < 300:
            keys.append(cursor)
            cursor -= BAR_SECONDS
        return [dict(rows[key]) for key in reversed(keys)]

    def move_pairs(self, instrument, horizon):
        samples = self.samples[instrument]
        return [
            {
                "from_second": end - horizon,
                "to_second": end,
                "entry": samples[end - horizon],
                "exit": samples[end],
            }
            for end in sorted(samples)
            if end - horizon in samples
        ][-120:]


def connect(path, *, readonly=False):
    db = sqlite3.connect(
        path.as_uri() + "?mode=ro" if readonly else path, uri=readonly, timeout=2
    )
    db.row_factory = sqlite3.Row
    if readonly:
        db.execute("PRAGMA query_only=ON")
    return db


class Worker:
    def __init__(self, home, prices, *, strategies=None):
        self.home, self.prices = Path(home).expanduser().absolute(), Path(prices)
        self._source_state = None
        self.root = directory(home)
        if (
            self.home.is_symlink()
            or self.root.is_symlink()
            or self.root.parent.is_symlink()
        ):
            raise ValueError("forecast_directory_symlink")
        self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.path = self.root / "forecast.sqlite3"
        if self.path.is_symlink() or self.path.exists() and not self.path.is_file():
            raise ValueError("forecast_store_symlink")
        self.strategies = strategies or StrategySet()
        self.bars = Bars()
        with closing(connect(self.path)) as db, db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,body TEXT);
                CREATE TABLE IF NOT EXISTS frames(instrument TEXT,horizon INTEGER,body TEXT,PRIMARY KEY(instrument,horizon));
                CREATE TABLE IF NOT EXISTS selected(instrument TEXT,horizon INTEGER,strategy TEXT,body TEXT,PRIMARY KEY(instrument,horizon,strategy));
                CREATE TABLE IF NOT EXISTS input_traces(id TEXT PRIMARY KEY,instrument TEXT,issued REAL,body TEXT);
                CREATE TABLE IF NOT EXISTS source_state(instrument TEXT PRIMARY KEY,observed REAL,sampled REAL,owner_pid INTEGER);
                CREATE TABLE IF NOT EXISTS calls(id TEXT PRIMARY KEY,instrument TEXT,horizon INTEGER,strategy TEXT,issued REAL,target REAL,entry REAL,direction INTEGER,projected REAL,settled REAL,hit INTEGER);
                CREATE INDEX IF NOT EXISTS pending ON calls(instrument,settled,target);
                CREATE INDEX IF NOT EXISTS scores ON calls(instrument,horizon,strategy,issued);
            """)
            existing = db.execute(
                "SELECT body FROM metadata WHERE key='policy'"
            ).fetchone()
            if existing and existing[0] != policy_id():
                raise ValueError("forecast_policy_mismatch")
            db.execute(
                "INSERT OR IGNORE INTO metadata VALUES('policy',?)", (policy_id(),)
            )
            db.execute(f"PRAGMA application_id={APP_ID}")
        self.path.chmod(0o600)

    def bootstrap(self, now):
        today = datetime.fromtimestamp(now, UTC).date()
        for day in (today - timedelta(days=1), today):
            path = self.prices / (day.isoformat() + ".jsonl.gz")
            if not path.is_file() or path.is_symlink():
                continue
            for raw in history_tail(path):
                stamp = raw.get("t") if isinstance(raw, dict) else None
                if not finite(stamp) or not now - 3600 <= stamp <= now:
                    continue
                for instrument, quote in snapshot(raw, stamp).items():
                    self.bars.add(instrument, quote)

    def sample(self, now):
        try:
            with (self.prices / "latest.json").open("rb") as source:
                raw = source.read(MAX_SNAPSHOT_BYTES + 1)
            if len(raw) > MAX_SNAPSHOT_BYTES:
                quotes, source_state = {}, "oversized"
            else:
                quotes = snapshot(json.loads(raw), now)
                source_state = "current_quotes" if quotes else "no_current_quotes"
        except OSError:
            quotes, source_state = {}, "read_error"
        except (ValueError, RecursionError):
            quotes, source_state = {}, "invalid_json"
        if source_state != self._source_state:
            self._source_state = source_state
            level = logging.INFO if source_state == "current_quotes" else logging.WARNING
            # A failing diagnostic sink cannot change source eligibility or evaluation.
            with suppress(Exception):
                LOGGER.log(
                    level,
                    json.dumps({"event": "oraclebot.forecast_source", "state": source_state}),
                )
        for instrument, quote in quotes.items():
            self.bars.add(instrument, quote)
        with closing(connect(self.path)) as db, db:
            for instrument, quote in quotes.items():
                db.execute(
                    "INSERT OR REPLACE INTO source_state VALUES(?,?,?,?)",
                    (instrument, quote["observed_at"], now, os.getpid()),
                )
                # Resolve only an actual timely post-target quote. Missing outcomes
                # expire without being credited as either hits or misses.
                for call in db.execute(
                    "SELECT id,target,entry,direction FROM calls WHERE instrument=? AND settled IS NULL AND target<=?",
                    (instrument, quote["observed_at"]),
                ).fetchall():
                    timely = quote["observed_at"] - call["target"] <= 3
                    direction = (quote["price"] > call["entry"]) - (
                        quote["price"] < call["entry"]
                    )
                    hit = int(direction == call["direction"]) if timely else None
                    db.execute(
                        "UPDATE calls SET settled=?,hit=? WHERE id=?",
                        (quote["observed_at"], hit, call["id"]),
                    )
        return quotes

    def evaluate(self, quotes, now):
        with closing(connect(self.path)) as db, db:
            for instrument, quote in quotes.items():
                db.execute(
                    "INSERT OR REPLACE INTO source_state VALUES(?,?,?,?)",
                    (instrument, quote["observed_at"], now, os.getpid()),
                )
                preference = settings(self.home, instrument)
                due = []
                for horizon in sorted({*HORIZONS, preference["seconds"]}):
                    previous = db.execute(
                        "SELECT body FROM frames WHERE instrument=? AND horizon=?",
                        (instrument, horizon),
                    ).fetchone()
                    scheduled = now
                    if previous:
                        previous = json.loads(previous[0])
                        last = previous.get("scheduled_at", previous["issued_at"])
                        if now < last + horizon:
                            continue
                        scheduled = next_deadline(last, now - horizon, horizon)
                    due.append((horizon, scheduled))
                if not due:
                    continue
                bars = self.bars.completed(instrument, now)
                candidates = self.strategies.predict(bars)
                for horizon, scheduled in due:
                    pairs = self.bars.move_pairs(instrument, horizon)
                    distance = (
                        statistics.median(
                            [
                                abs(math.log(pair["exit"]) - math.log(pair["entry"]))
                                for pair in pairs
                            ]
                        )
                        if pairs
                        else None
                    )
                    rows = []
                    for item in candidates:
                        direction = item.get("direction")
                        if (
                            type(direction) is not int
                            or direction not in (-1, 0, 1)
                            or distance is None
                        ):
                            continue
                        scores = db.execute(
                            "SELECT hit FROM calls WHERE instrument=? AND horizon=? AND strategy=? AND hit IS NOT NULL ORDER BY issued DESC LIMIT 100",
                            (instrument, horizon, item["strategy_id"]),
                        ).fetchall()
                        resolved, hits = len(scores), sum(row[0] for row in scores)
                        try:
                            projected = quote["price"] * math.exp(direction * distance)
                        except OverflowError:
                            continue
                        if not finite(projected) or projected <= 0:
                            continue
                        projected_direction = (projected > quote["price"]) - (
                            projected < quote["price"]
                        )
                        row = {
                            "strategy_id": item["strategy_id"],
                            "version": item["version"],
                            "parameters": item["parameters"],
                            "direction": projected_direction,
                            "strategy_direction": direction,
                            "predicted_price": projected,
                            "resolved": resolved,
                            "hits": hits,
                            "accuracy_percent": 100 * hits / resolved
                            if resolved
                            else None,
                            "qualified": resolved >= 20 and hits / resolved > 0.5,
                            "ranking_basis": "recent_prospective_calls"
                            if resolved
                            else "warm_start_catalog_order",
                        }
                        rows.append(row)
                        identity = hashlib.sha256(
                            canonical(
                                [
                                    policy_id(),
                                    instrument,
                                    horizon,
                                    item["strategy_id"],
                                    scheduled,
                                ]
                            ).encode()
                        ).hexdigest()
                        db.execute(
                            "INSERT OR IGNORE INTO calls VALUES(?,?,?,?,?,?,?,?,?,NULL,NULL)",
                            (
                                identity,
                                instrument,
                                horizon,
                                item["strategy_id"],
                                now,
                                now + horizon,
                                quote["price"],
                                projected_direction,
                                projected,
                            ),
                        )
                        db.execute(
                            "DELETE FROM calls WHERE instrument=? AND horizon=? AND strategy=? AND id NOT IN (SELECT id FROM calls WHERE instrument=? AND horizon=? AND strategy=? ORDER BY issued DESC LIMIT 110)",
                            (
                                instrument,
                                horizon,
                                item["strategy_id"],
                                instrument,
                                horizon,
                                item["strategy_id"],
                            ),
                        )
                    if not rows:
                        continue
                    rows.sort(
                        key=lambda row: (
                            -(row["hits"] / row["resolved"] if row["resolved"] else -1),
                            -row["resolved"],
                            STRATEGY_IDS.index(row["strategy_id"]),
                        )
                    )
                    trace = {
                        "instrument": instrument,
                        "bar_seconds": BAR_SECONDS,
                        "horizon_seconds": horizon,
                        "bars": bars,
                        "move_pairs": pairs,
                        "quote": quote,
                    }
                    trace_body = canonical(trace)
                    trace_id = hashlib.sha256(trace_body.encode()).hexdigest()
                    db.execute(
                        "INSERT OR IGNORE INTO input_traces VALUES(?,?,?,?)",
                        (trace_id, instrument, now, trace_body),
                    )
                    frame = {
                        "schema_version": 1,
                        "policy": policy_id(),
                        "scope_id": scope_id(self.home),
                        "instrument": instrument,
                        "slot": int(scheduled // horizon) * horizon,
                        "scheduled_at": scheduled,
                        "issued_at": now,
                        "target_at": now + horizon,
                        "horizon_seconds": horizon,
                        "refresh_seconds": horizon,
                        "input_bar_seconds": BAR_SECONDS,
                        "reference_price": quote["price"],
                        "observed_at": quote["observed_at"],
                        "source": "coinbase_recorder",
                        "kind": "stream_snapshot_mid",
                        "method": METHOD,
                        "move_fraction": distance,
                        "input_bars": len(bars),
                        "input_trace_id": trace_id,
                        "issuer_pid": os.getpid(),
                        "strategies": rows,
                        "execution_authority": "none",
                        "limitations": [
                            "Provisional strategy projection; not a calibrated probability or executable quote.",
                            "Price distance uses recent median absolute log moves at this horizon; it is not a fitted expected return.",
                            "Reference-bar evaluation is separate from the historical study and qualified Oracle ensemble.",
                        ],
                    }
                    db.execute(
                        "INSERT OR REPLACE INTO frames VALUES(?,?,?)",
                        (instrument, horizon, canonical(frame)),
                    )
                    for row in rows:
                        db.execute(
                            "INSERT OR REPLACE INTO selected VALUES(?,?,?,?)",
                            (
                                instrument,
                                horizon,
                                row["strategy_id"],
                                canonical({**frame, "selected": row}),
                            ),
                        )
                pinned = {
                    json.loads(row[0])["input_trace_id"]
                    for row in db.execute(
                        "SELECT body FROM selected WHERE instrument=?", (instrument,)
                    )
                }
                old = db.execute(
                    "SELECT id FROM input_traces WHERE instrument=? ORDER BY issued DESC LIMIT -1 OFFSET 120",
                    (instrument,),
                ).fetchall()
                db.executemany(
                    "DELETE FROM input_traces WHERE id=?",
                    [(row[0],) for row in old if row[0] not in pinned],
                )


def report(home, instrument, *, horizon=10, strategy="published", now=None):
    instrument = validate_instrument(instrument)
    now = time.time() if now is None else now
    if type(horizon) is not int or not valid_seconds(horizon) or not finite(now):
        raise ValueError("invalid_forecast_request")
    preference = settings(home, instrument)
    if strategy not in (*STRATEGY_IDS, "published", "auto"):
        return {
            "status": "waiting",
            "reason": "selected_strategy_has_no_live_projection",
            "instrument": instrument,
            "settings": preference,
        }
    path = directory(home) / "forecast.sqlite3"
    absent = {
        "status": "waiting",
        "reason": "awaiting_first_source_bound_forecast",
        "instrument": instrument,
        "horizon_seconds": horizon,
        "refresh_seconds": horizon,
        "settings": preference,
    }
    if (
        not path.is_file()
        or path.is_symlink()
        or path.parent.is_symlink()
        or path.parent.parent.is_symlink()
    ):
        return absent
    try:
        with closing(connect(path, readonly=True)) as db:
            if db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
                return absent
            available = [
                row[0]
                for row in db.execute(
                    "SELECT DISTINCT instrument FROM frames ORDER BY instrument"
                )
            ]
            source = db.execute(
                "SELECT observed,sampled,owner_pid FROM source_state WHERE instrument=?",
                (instrument,),
            ).fetchone()
            row = (
                db.execute(
                    "SELECT body FROM frames WHERE instrument=? AND horizon=?",
                    (instrument, horizon),
                )
                if strategy in ("published", "auto")
                else db.execute(
                    "SELECT body FROM selected WHERE instrument=? AND horizon=? AND strategy=?",
                    (instrument, horizon, strategy),
                )
            ).fetchone()
        if not row:
            return {**absent, "available_instruments": available}
        frame = json.loads(row[0])
        if (
            frame["policy"] != policy_id()
            or frame.get("scope_id") != scope_id(home)
            or frame["instrument"] != instrument
            or frame["horizon_seconds"] != horizon
        ):
            return absent
        selected = next(
            (
                item
                for item in frame["strategies"]
                if strategy in ("published", "auto") or item["strategy_id"] == strategy
            ),
            None,
        )
        if not selected:
            return {**absent, "reason": "selected_strategy_warming_up"}
        age = now - frame["issued_at"]
        source_current = bool(
            source
            and 0 <= now - source[0] <= MAX_AGE
            and 0 <= now - source[1] <= MAX_AGE
        )
        fresh = (
            0 <= age <= horizon + 5
            and source_current
            and 0 <= frame["issued_at"] - frame["observed_at"] <= MAX_AGE
        )
        return {
            **frame,
            "status": "fresh" if fresh else "retained",
            "age_seconds": age,
            "reason": None if fresh else "last_forecast_retained_no_new_valid_inputs",
            "selected": selected,
            "requested_strategy": strategy,
            "available_instruments": available,
            "source_current": source_current,
            "source_observed_at": source[0] if source else None,
            "source_sampled_at": source[1] if source else None,
            "owner_pid": source[2] if source_current else None,
            "settings": preference,
        }
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        return absent


def read_trace(home, trace_id):
    if (
        not isinstance(trace_id, str)
        or len(trace_id) != 64
        or any(c not in "0123456789abcdef" for c in trace_id)
    ):
        raise ValueError("invalid_forecast_trace")
    path = directory(home) / "forecast.sqlite3"
    if (
        path.is_symlink()
        or not path.is_file()
        or path.parent.is_symlink()
        or path.parent.parent.is_symlink()
    ):
        raise ValueError("forecast_trace_unavailable")
    with closing(connect(path, readonly=True)) as db:
        if db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("forecast_trace_unavailable")
        row = db.execute(
            "SELECT body FROM input_traces WHERE id=?", (trace_id,)
        ).fetchone()
    if not row or hashlib.sha256(row[0].encode()).hexdigest() != trace_id:
        raise ValueError("forecast_trace_unavailable")
    return json.loads(row[0])


def next_deadline(previous, now, interval=REFRESH_SECONDS):
    """Fixed deadlines independent of work duration; skip missed periods."""
    return previous + max(1, math.floor((now - previous) / interval) + 1) * interval


def run(home, prices, stop=None):
    stop = stop or threading.Event()
    root = directory(home)
    if root.is_symlink() or root.parent.is_symlink() or Path(home).is_symlink():
        raise ValueError("forecast_directory_symlink")
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor = os.open(
        root / "owner.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("forecast_lock_not_regular")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        worker = Worker(home, prices)
        worker.bootstrap(time.time())
        while not stop.is_set():
            quotes = worker.sample(time.time())
            worker.evaluate(quotes, time.time())
            stop.wait(0.25)
    finally:
        os.close(descriptor)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--instrument", default="SOL/USD")
    parser.add_argument(
        "--prices", type=Path, default=Path.home() / ".config/soltui/prices"
    )
    args = parser.parse_args(argv)
    if args.status:
        try:
            seconds = settings(args.home, args.instrument)["seconds"]
            value = report(args.home, args.instrument, horizon=seconds)
        except ValueError:
            print(json.dumps({"ok": False, "error": "forecast_status_unavailable"}))
            return 3
        print(json.dumps({"ok": True, "data": value}))
        return 0
    stop = threading.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda *_: stop.set())
    return run(args.home, args.prices, stop)


if __name__ == "__main__":
    raise SystemExit(main())

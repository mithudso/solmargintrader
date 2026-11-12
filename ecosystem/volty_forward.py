"""Frozen, prospective Volty OHLC paper observation. Never signs or submits.

Closed public Binance ZECUSDT candles are reference data. Decisions are durable
before their first eligible bar, with one additional bar of observation delay.
An outage never backfills missing decisions. Restart resumes the same cohort.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import plistlib
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from dataclasses import asdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

from backtester.core import volty

APP_ID = 0x564C5432
STEPS = {"1m": 60, "5m": 300, "10m": 600, "1h": 3600, "1d": 86400}
FIELDS = ("timestamp", "open", "high", "low", "close", "volume")
API = "https://data-api.binance.vision/api/v3/klines"
MAX_BARS = 100_000
TERMINAL = {"missed_decision_window", "source_gap", "implementation_changed", "observation_limit", "unconfirmed_decision"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def implementation():
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in (
        ("ecosystem/volty_forward.py", Path(__file__)),
        ("backtester/core/volty.py", Path(volty.__file__)))}


def _path(home):
    path = Path(home).expanduser().absolute()
    if path.is_symlink():
        raise ValueError("unsafe_paper_home")
    return path / "volty-forward.sqlite3"


@contextmanager
def connection(home, *, write=False):
    path = _path(home)
    if path.is_symlink():
        raise ValueError("unsafe_paper_store")
    db = sqlite3.connect(path.as_uri() + "?mode=rw" if write else path.as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    try:
        if db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("incompatible_paper_store")
        if write:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
        else:
            db.execute("PRAGMA query_only=ON")
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def _arrays(rows):
    return {key: np.asarray([row[i] for row in rows], dtype="int64" if i == 0 else "float64")
            for i, key in enumerate(FIELDS)}


def fetch_closed(interval, after, now):
    """Read native bars, aggregating complete UTC pairs of 5m for 10m only."""
    step = STEPS[interval]
    native = "5m" if interval == "10m" else interval
    native_step = STEPS[native]
    params = {"symbol": "ZECUSDT", "interval": native, "endTime": int(now) * 1000, "limit": 1000}
    if after is not None:
        params["startTime"] = (after + step) * 1000
    with urlopen(Request(API + "?" + urlencode(params), headers={"User-Agent": "solmargintrader-volty-paper/1"}), timeout=10) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("feed_response_too_large")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError("invalid_feed")
    rows = []
    for value in data:
        if not isinstance(value, list) or len(value) < 7 or type(value[0]) is not int:
            raise ValueError("invalid_feed_candle")
        opened = value[0] // 1000
        if value[0] % 1000 or opened % native_step or int(value[6]) != (opened + native_step) * 1000 - 1:
            raise ValueError("invalid_feed_timestamp")
        if opened + native_step <= now:
            rows.append((opened, *(float(value[i]) for i in range(1, 6))))
    if interval == "10m":
        paired = []
        for i in range(len(rows) - 1):
            a, b = rows[i:i + 2]
            if a[0] % step == 0 and b[0] == a[0] + native_step:
                paired.append((a[0], a[1], max(a[2], b[2]), min(a[3], b[3]), b[4], a[5] + b[5]))
        rows = paired
    rows = [row for row in rows if after is None or row[0] > after]
    if not rows:
        return None
    arrays = _arrays(rows)
    # Two bars suffice for a feed batch; simulator validation needs three.
    if len(rows) > 1 and np.any(np.diff(arrays["timestamp"]) != step):
        raise ValueError("source_gap")
    o, h, low, close = (arrays[key] for key in ("open", "high", "low", "close"))
    if (not all(np.isfinite(values).all() for values in arrays.values()) or np.any(low <= 0)
            or np.any(h < np.maximum(o, close)) or np.any(low > np.minimum(o, close))
            or np.any(arrays["volume"] < 0)):
        raise ValueError("invalid_feed_prices")
    return arrays


def _levels(bars, config):
    # The appended value is never read by stop_levels for its final active stop.
    # Using the simulator's own arithmetic also binds rounding at a touched stop.
    padded = {key: np.r_[value, value[-1]] for key, value in bars.items()}
    upper, lower = volty.stop_levels(padded, config)
    return float(upper[-1]), float(lower[-1])


def _decision(db, row, arrays, now):
    bar, step = int(arrays["timestamp"][-1]), STEPS[row["interval"]]
    effective = bar + 2 * step
    if now >= effective:
        raise ValueError("missed_decision_window")
    upper, lower = _levels(arrays, volty.VoltyConfig(**json.loads(row["config"])))
    db.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?)", (row["id"], bar, now, effective, upper, lower))
    return row["id"], effective


def _confirm(home, decisions, durable_at):
    """Affirm data only after its first durable commit returned to this process.

    The immutable decision is already on disk. A later confirmation never edits
    its levels. A crash before this separate commit leaves it ineligible, even
    when its pre-commit issue timestamp looks early enough.
    """
    with connection(home, write=True) as db:
        for identity, effective in decisions:
            if durable_at >= effective:
                db.execute("UPDATE accounts SET status='blocked',reason='missed_decision_window' WHERE id=?", (identity,))
                continue
            db.execute("INSERT INTO decision_confirmations VALUES(?,?,?)", (identity, effective, durable_at))
            db.execute("UPDATE accounts SET status=CASE WHEN last_ts>=activation THEN 'running' ELSE 'waiting' END,reason=NULL WHERE id=?", (identity,))


def initialize(home, specs, *, now=None, fetcher=fetch_closed, clock=time.time):
    realtime = now is None
    now = clock() if now is None else now
    specs_bytes = Path(specs).read_bytes()
    value = json.loads(specs_bytes)
    if value.get("schema_version") != 1 or len(value.get("accounts", [])) != 5:
        raise ValueError("five_frozen_specs_required")
    plans = [{"label": "TradingView chart 5 / 1", "interval": "1m",
              "config": asdict(volty.VoltyConfig(length=5, atr_mult=1.0))}]
    for row in value["accounts"]:
        if row.get("interval") not in STEPS or row.get("paper_only") is not True:
            raise ValueError("invalid_frozen_spec")
        plans.append({"label": "Frozen study winner", "interval": row["interval"],
                      "config": asdict(volty.VoltyConfig(**row["config"]))})
    if sorted(row["interval"] for row in plans[1:]) != sorted(STEPS):
        raise ValueError("one_frozen_spec_per_interval_required")
    seeds = {}
    for interval, step in STEPS.items():
        arrays = fetcher(interval, None, now)
        if arrays is None:
            raise ValueError("seed_unavailable")
        arrays = {key: values[-32:] for key, values in arrays.items()}
        volty.validate(arrays, step)
        if int(arrays["timestamp"][-1]) + 2 * step <= now:
            raise ValueError("seed_stale")
        seeds[interval] = arrays
    if realtime:
        now = clock()
    if any(int(arrays["timestamp"][-1]) + 2 * STEPS[interval] <= now for interval, arrays in seeds.items()):
        raise ValueError("seed_stale_after_fetch")
    path = _path(home)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    decisions = []
    # Never delete a possibly committed cohort on failure. A crash between the
    # two commits must retain its unconfirmed decisions for explicit review.
    with closing(sqlite3.connect(path)) as db:
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE accounts(id TEXT PRIMARY KEY,label TEXT,interval TEXT,config TEXT,activation INTEGER,last_ts INTEGER,status TEXT,reason TEXT);
                CREATE TABLE candles(interval TEXT,bar INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL,PRIMARY KEY(interval,bar));
                CREATE TABLE decisions(id TEXT,source_bar INTEGER,issued REAL,effective INTEGER,upper REAL,lower REAL,PRIMARY KEY(id,effective));
                CREATE TABLE decision_confirmations(id TEXT,effective INTEGER,durable_at REAL NOT NULL,
                    PRIMARY KEY(id,effective),FOREIGN KEY(id,effective) REFERENCES decisions(id,effective),
                    CHECK(durable_at<effective));
                CREATE TABLE snapshots(id TEXT,bar INTEGER,observed REAL,metrics TEXT,PRIMARY KEY(id,bar));
                CREATE TRIGGER immutable_decision_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'immutable_paper_decision'); END;
                CREATE TRIGGER immutable_decision_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'immutable_paper_decision'); END;
                CREATE TRIGGER immutable_confirmation_update BEFORE UPDATE ON decision_confirmations BEGIN SELECT RAISE(ABORT,'immutable_paper_confirmation'); END;
                CREATE TRIGGER immutable_confirmation_delete BEFORE DELETE ON decision_confirmations BEGIN SELECT RAISE(ABORT,'immutable_paper_confirmation'); END;
            """)
            db.execute(f"PRAGMA application_id={APP_ID}")
            for key, item in {"created_at": now, "implementation": implementation(),
                              "specs_sha256": hashlib.sha256(specs_bytes).hexdigest(),
                              "source": "Binance spot ZECUSDT; reference OHLC paper, not GUM ZEC/USDC",
                              "execution": "1x, frozen costs, nearest OHLC path, one additional bar delay",
                              "funding": "synthetic carry scenario; actual GUM funding unavailable"}.items():
                db.execute("INSERT INTO metadata VALUES(?,?)", (key, canonical(item)))
            for interval, arrays in seeds.items():
                db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?)", [(interval, *values) for values in zip(*(arrays[key].tolist() for key in FIELDS))])
            for plan in plans:
                interval, config = plan["interval"], canonical(plan["config"])
                identity = hashlib.sha256(canonical(plan).encode()).hexdigest()[:24]
                step = STEPS[interval]
                activation = (int(now) // step + 2) * step
                last = int(seeds[interval]["timestamp"][-1])
                db.execute("INSERT INTO accounts VALUES(?,?,?,?,?,?,?,?)", (identity, plan["label"], interval, config, activation, last, "awaiting_confirmation", "decision_not_yet_durable"))
                decisions.append(_decision(db, {"id": identity, "interval": interval, "config": config}, seeds[interval], clock()))
            db.commit()
            durable_at = clock()
        except BaseException:
            db.rollback()
            raise
    _confirm(home, decisions, durable_at)
    return report(home, now=now)


def tick(home, *, now=None, fetcher=fetch_closed, clock=time.time):
    realtime = now is None
    now = clock() if now is None else now
    with connection(home) as db:
        accounts = [dict(row) for row in db.execute("SELECT * FROM accounts ORDER BY interval,label")]
        expected = json.loads(db.execute("SELECT value FROM metadata WHERE key='implementation'").fetchone()[0])
        pending = {row[0] for row in db.execute("SELECT d.id FROM decisions d LEFT JOIN decision_confirmations c ON d.id=c.id AND d.effective=c.effective WHERE c.id IS NULL")}
    if expected != implementation():
        with connection(home, write=True) as db:
            db.execute("UPDATE accounts SET status='blocked',reason='implementation_changed'")
        return report(home, now=now)
    fetched = {}
    for row in accounts:
        interval, step = row["interval"], STEPS[row["interval"]]
        if row["reason"] in TERMINAL:
            continue
        if row["id"] in pending:
            with connection(home, write=True) as db:
                db.execute("UPDATE accounts SET status='blocked',reason='unconfirmed_decision' WHERE id=?", (row["id"],))
            continue
        if now < row["last_ts"] + 2 * step + 3:
            continue
        try:
            key = (interval, row["last_ts"])
            if key not in fetched:
                fetched[key] = fetcher(interval, row["last_ts"], now)
            if realtime:
                now = clock()
            arrays = fetched[key]
            if arrays is None:
                raise ValueError("closed_candle_unavailable")
            count = len(arrays["timestamp"])
            if (count != 1 or int(arrays["timestamp"][0]) != row["last_ts"] + step):
                raise ValueError("missed_decision_window")
            bar = int(arrays["timestamp"][0])
            if bar + step > now or now >= bar + 2 * step:
                raise ValueError("missed_decision_window")
            with connection(home, write=True) as db:
                current = db.execute("SELECT last_ts FROM accounts WHERE id=?", (row["id"],)).fetchone()[0]
                if current != row["last_ts"]:
                    raise ValueError("concurrent_paper_writer")
                values = [float(arrays[key][0]) for key in FIELDS[1:]]
                old = db.execute("SELECT open,high,low,close,volume FROM candles WHERE interval=? AND bar=?", (interval, bar)).fetchone()
                if old is not None and list(old) != values:
                    raise ValueError("source_candle_changed")
                db.execute("INSERT OR IGNORE INTO candles VALUES(?,?,?,?,?,?,?)", (interval, bar, *values))
                observed = db.execute("SELECT bar,open,high,low,close,volume FROM candles WHERE interval=? ORDER BY bar", (interval,)).fetchall()
                if len(observed) > MAX_BARS:
                    raise ValueError("observation_limit")
                full = _arrays(observed)
                volty.validate(full, step)
                decision_to_confirm = _decision(db, row, full, clock())
                if bar >= row["activation"]:
                    decision = db.execute("SELECT c.durable_at FROM decisions d JOIN decision_confirmations c ON d.id=c.id AND d.effective=c.effective WHERE d.id=? AND d.effective=?", (row["id"], bar)).fetchone()
                    if decision is None or decision[0] >= bar:
                        raise ValueError("missed_decision_window")
                    start = int(np.searchsorted(full["timestamp"], row["activation"]))
                    result = volty.simulate(full, volty.VoltyConfig(**json.loads(row["config"])), step,
                                            start=start, close_at_end=False, signal_delay_bars=1)
                    metrics = {key: item for key, item in result.items() if key != "equity"}
                    db.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (row["id"], bar, now, canonical(metrics)))
                db.execute("UPDATE accounts SET last_ts=?,status='awaiting_confirmation',reason='decision_not_yet_durable' WHERE id=?", (bar, row["id"]))
            durable_at = clock()
            _confirm(home, [decision_to_confirm], durable_at)
        except (OSError, ValueError, TypeError, TimeoutError) as exc:
            reason = str(exc) if isinstance(exc, ValueError) and str(exc) in TERMINAL else "feed_or_paper_tick_failed"
            with connection(home, write=True) as db:
                db.execute("UPDATE accounts SET status='blocked',reason=? WHERE id=?", (reason, row["id"]))
    return report(home, now=now)


def report(home, *, now=None):
    now = time.time() if now is None else now
    with connection(home) as db:
        metadata = {row[0]: json.loads(row[1]) for row in db.execute("SELECT * FROM metadata")}
        accounts = []
        for row in db.execute("SELECT * FROM accounts ORDER BY interval,label"):
            item = dict(row)
            item["config"] = json.loads(item["config"])
            latest = db.execute("SELECT bar,observed,metrics FROM snapshots WHERE id=? ORDER BY bar DESC LIMIT 1", (row["id"],)).fetchone()
            item["latest"] = {"bar": latest[0], "observed_at": latest[1], "metrics": json.loads(latest[2])} if latest else None
            item["decisions"] = db.execute("SELECT count(*) FROM decisions WHERE id=?", (row["id"],)).fetchone()[0]
            item["confirmed_decisions"] = db.execute("SELECT count(*) FROM decision_confirmations WHERE id=?", (row["id"],)).fetchone()[0]
            item["stale"] = now >= row["last_ts"] + 3 * STEPS[row["interval"]] + 30
            accounts.append(item)
    return {"schema_version": 2, "paper_only": True, "as_of": now, "metadata": metadata, "accounts": accounts}


def run(home, poll=10):
    lock = _path(home).with_suffix(".lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    stop = False
    def terminate(*_):
        nonlocal stop
        stop = True
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, terminate)
        while not stop:
            try:
                value = tick(home)
                print(canonical({"at": value["as_of"], "paper_only": True,
                                 "accounts": [{"id": row["id"], "status": row["status"], "reason": row["reason"], "last_ts": row["last_ts"]} for row in value["accounts"]]}), flush=True)
            except (OSError, ValueError, sqlite3.Error):
                print(canonical({"status": "blocked", "reason": "paper_store_failed"}), flush=True)
            until = time.monotonic() + poll
            while not stop and time.monotonic() < until:
                time.sleep(min(1, max(0, until - time.monotonic())))
    finally:
        os.close(fd)


def install_service(home, python=sys.executable):
    if sys.platform != "darwin":
        raise ValueError("launchd_service_requires_macos")
    home = _path(home).parent
    report(home)
    python = Path(python).absolute()
    if not python.is_file() or "-wt-" in str(python) or "/worktrees/" in str(python):
        raise ValueError("stable_installed_python_required")
    label = "com.solmargintrader.volty-forward." + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    path = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    document = {"Label": label, "ProgramArguments": [str(python), "-I", "-m", "ecosystem.volty_forward", "--home", str(home), "run"],
                "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 10,
                "StandardOutPath": str(home / "daemon.log"), "StandardErrorPath": str(home / "daemon.log"),
                "WorkingDirectory": str(home)}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and plistlib.loads(path.read_bytes()) != document):
        raise ValueError("service_configuration_conflict")
    path.write_bytes(plistlib.dumps(document))
    path.chmod(0o600)
    domain = "gui/" + str(os.getuid())
    present = subprocess.run(["launchctl", "print", domain + "/" + label], capture_output=True, timeout=10, check=False)
    if present.returncode:
        subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True, capture_output=True, timeout=15)
    subprocess.run(["launchctl", "enable", domain + "/" + label], check=True, capture_output=True, timeout=10)
    return {"label": label, "path": str(path)}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Example: python -m ecosystem.volty_forward "
        "--home /path/to/existing-cohort status (read-only).",
    )
    parser.add_argument("--home", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--specs", required=True, type=Path)
    commands.add_parser("run")
    commands.add_parser("status")
    commands.add_parser("install-service")
    args = parser.parse_args(argv)
    if args.command == "init":
        value = initialize(args.home, args.specs)
    elif args.command == "run":
        return run(args.home)
    elif args.command == "install-service":
        value = install_service(args.home)
    else:
        value = report(args.home)
    print(canonical(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

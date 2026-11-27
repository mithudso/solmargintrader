"""Frozen, finite HYPE 1h RSI dip-buyer paper observation. Never signs or submits.

Candidate: RSI(14), buy below 30, exit above 55, long or cash, from
research/papers/results/hype_study_2026-11-27.md. Closed public Binance HYPEUSDT
1h candles are reference data. The rule is frozen at initialization. The sample
is finite (MAX_BARS closed bars after activation, plus a hard expiry) and the
run ends by itself. A source gap ends the sample; it is never backfilled.
Paper accounting from candle opens is not evidence of an executable fill.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import plistlib
import re
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import closing, contextmanager
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

from backtester.core import engine as engine_module
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.strategies.rsi import RsiMeanReversion
from backtester.core.types import CostConfig

APP_ID = 0x48595031
STEP = 3600
API = "https://data-api.binance.vision/api/v3/klines"
SYMBOL = "HYPEUSDT"
SEED_BARS = 200
MAX_BARS = 336  # 14 days of closed 1h bars after activation
EXPIRY_GRACE_BARS = 6
EXPIRY_STRIKES = 2  # consecutive polls past expiry; one bad clock read must not end a sample
CLOSE_SETTLE_S = 3  # a bar counts as closed only this long after its nominal close
STALE_GRACE_S = 30
MAX_SKEW_S = 60  # refuse a poll when the local clock disagrees with the venue's by more than this
MAX_STORE_ERRORS = 5  # consecutive failed polls before `run` exits non-zero so launchd surfaces it
LATE_AFTER = 2 * STEP  # a bar first seen later than this after its open is counted late
CAPITAL = 10_000.0
SLIPPAGE_BPS = 2.0
SPEC = {"strategy": "rsi", "period": 14, "oversold": 30.0, "exit_level": 55.0, "interval": "1h"}
# fill_delay 1 is the study convention: a zero-latency fill at the next open, an
# optimistic bound. fill_delay 2 fills one hour later, a pessimistic bound. The
# real poller sees a closed bar seconds after its close, so a live fill falls between.
ACCOUNTS = (
    {"id": "rsi-fill1-fee10", "kind": "rsi", "fill_delay": 1, "fee_bps": 10.0},
    {"id": "rsi-fill1-fee25", "kind": "rsi", "fill_delay": 1, "fee_bps": 25.0},
    {"id": "rsi-fill2-fee10", "kind": "rsi", "fill_delay": 2, "fee_bps": 10.0},
    {"id": "rsi-fill2-fee25", "kind": "rsi", "fill_delay": 2, "fee_bps": 25.0},
    {"id": "hold-fee10", "kind": "hold", "fill_delay": 1, "fee_bps": 10.0},
)
FIELDS = ("ts", "open", "high", "low", "close", "volume")
OWNER = re.compile(r"[a-z0-9][a-z0-9._-]{2,63}")
TERMINAL = {"completed", "expired", "blocked"}


class FeedError(ValueError):
    """A feed payload that cannot be trusted. Retried on the next poll."""


class SourceGap(FeedError):
    """Missing or non-contiguous closed bars. Ends the sample; never backfilled."""


class ConcurrentWriter(ValueError):
    """Another writer advanced the store between this poll's read and write."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def implementation():
    """Hash everything that decides a paper result, so a changed engine ends the run loudly."""
    core = Path(engine_module.__file__).parent
    result = {"backtester/core/" + str(path.relative_to(core)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(core.rglob("*.py"))}
    result["ecosystem/hype_forward.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    # Minor versions only: a patch upgrade of Python or numpy must not end a 14-day sample.
    result["runtime"] = {"numpy": ".".join(np.__version__.split(".")[:2]),
                         "python": f"{sys.version_info.major}.{sys.version_info.minor}"}
    return result


def _path(home):
    path = Path(home).expanduser().absolute()
    if path.is_symlink():
        raise ValueError("unsafe_paper_home")
    return path / "hype-forward.sqlite3"


def _connect(path, write):
    db = sqlite3.connect(path.as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    return db


@contextmanager
def connection(home, *, write=False):
    path = _path(home)
    if path.is_symlink():
        raise ValueError("unsafe_paper_store")
    db = _connect(path, write)
    try:
        try:
            application_id = db.execute("PRAGMA application_id").fetchone()[0]
        except sqlite3.OperationalError:
            if write:
                raise
            # A kill mid-commit leaves a hot journal that a read-only connection cannot
            # roll back. Only a write connection recovers it; every reader benefits.
            db.close()
            with closing(_connect(path, True)) as recovery:
                recovery.execute("BEGIN IMMEDIATE")
                recovery.rollback()
            db = _connect(path, False)
            application_id = db.execute("PRAGMA application_id").fetchone()[0]
        if application_id != APP_ID:
            raise ValueError("incompatible_paper_store")
        if write:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
        else:
            db.execute("PRAGMA query_only=ON")
            # One read transaction, so a report never mixes rows from two commits.
            db.execute("BEGIN")
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def fetch_closed(after, now, limit=1000, until=None):
    """Closed, contiguous, validated HYPEUSDT 1h bars after `after` (None = latest `limit`).

    `now` is the real local time and is what the skew check compares with the venue.
    `until` only bounds which bars may be returned, so it never affects that check.
    """
    horizon = now if until is None else min(now, until)
    params = {"symbol": SYMBOL, "interval": "1h", "endTime": int(horizon) * 1000, "limit": limit}
    if after is not None:
        params["startTime"] = (after + STEP) * 1000
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": "solmargintrader-hype-paper/1"})
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read(2_000_001)
            stamp = response.headers.get("Date")
    except http.client.HTTPException as exc:
        raise OSError("feed_http_error") from exc
    try:
        stamped = parsedate_to_datetime(stamp)
    except (TypeError, ValueError) as exc:
        raise FeedError("missing_server_time") from exc
    if stamped.tzinfo is None:
        raise FeedError("missing_server_time")  # a zone-less Date would be read as local time
    server_now = stamped.timestamp()
    if abs(now - server_now) > MAX_SKEW_S:
        raise FeedError("clock_skew")
    # A bar is closed only when it is closed on the venue's clock as well as ours, so
    # local clock skew can never store a still-forming candle in the immutable table.
    horizon = min(horizon, server_now)
    if len(raw) > 2_000_000:
        raise FeedError("feed_response_too_large")
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise FeedError("invalid_feed_json") from exc
    if not isinstance(data, list):
        raise FeedError("invalid_feed")
    rows = []
    for value in data:
        try:
            row = _candle(value, after, horizon)
        except (OverflowError, TypeError, ValueError) as exc:
            raise FeedError(str(exc) if isinstance(exc, FeedError) else "invalid_feed_candle") from exc
        if row is not None:
            rows.append(row)
    if not rows:
        return None
    arrays = _arrays(rows)
    steps = np.diff(arrays["ts"])
    if np.any(steps <= 0):
        raise FeedError("invalid_feed_order")  # a duplicate or reordered row is untrustworthy, not a gap
    if np.any(steps != STEP):
        first = int(np.flatnonzero(steps != STEP)[0])
        raise SourceGap(f"source_gap:after={int(arrays['ts'][first])},got={int(arrays['ts'][first + 1])}")
    return arrays


def _candle(value, after, now):
    """One validated closed bar, or None when it is still forming or already stored."""
    if not isinstance(value, list) or len(value) < 7 or type(value[0]) is not int:
        raise FeedError("invalid_feed_candle")
    opened = value[0] // 1000
    if value[0] % 1000 or opened % STEP or int(value[6]) != (opened + STEP) * 1000 - 1:
        raise FeedError("invalid_feed_timestamp")
    if opened + STEP + CLOSE_SETTLE_S > now or (after is not None and opened <= after):
        return None
    o, h, low, close, volume = (float(value[i]) for i in range(1, 6))
    prices = (o, h, low, close, volume)
    if (not all(np.isfinite(prices)) or low <= 0 or h < max(o, close)
            or low > min(o, close) or volume < 0):
        raise FeedError("invalid_feed_prices")
    return (opened, *prices)


def _arrays(rows):
    return {key: np.asarray([row[i] for row in rows], dtype="int64" if i == 0 else "float64")
            for i, key in enumerate(FIELDS)}


def _rows(arrays, observed):
    return [(*row, observed) for row in zip(*(arrays[key].tolist() for key in FIELDS))]


class ForwardRsi(RsiMeanReversion):
    """The frozen rule, forced flat before activation.

    The Wilder average still sees every stored bar, so the indicator has the same
    history it would have live. Only the holding state is held back, so no
    hypothetical pre-activation trade enters the paper account.
    """

    def __init__(self, activation):
        super().__init__(SPEC["period"], SPEC["oversold"], SPEC["exit_level"])
        self.activation = int(activation)

    def on_bar(self, history):
        target = super().on_bar(history)
        if history.bar().ts < self.activation:
            self._holding = False
            return 0.0
        return target


def _simulate(account, arrays, activation):
    strategy = ForwardRsi(activation) if account["kind"] == "rsi" else BuyAndHold()
    config = EngineConfig(interval="1h", fill_delay=account["fill_delay"], initial_capital=CAPITAL,
                          costs=CostConfig(fee_bps=account["fee_bps"], slippage_bps=SLIPPAGE_BPS))
    mask = arrays["ts"] >= activation if account["kind"] == "hold" else slice(None)
    window = {key: value[mask] for key, value in arrays.items()}
    if len(window["ts"]) < 3:
        return {"bars": len(window["ts"]), "total_return": 0.0, "trades": 0, "open": False, "max_drawdown": 0.0}
    result = run_backtest(strategy, window, config, close_at_end=False)
    equity = np.asarray(result.equity, dtype=float)
    after = np.asarray(result.timestamps) >= activation
    curve = equity[after]
    peak = np.maximum.accumulate(curve) if len(curve) else curve
    return {"bars": int(after.sum()),
            "total_return": float(equity[-1] / CAPITAL - 1.0),
            "trades": len(result.trades),
            "open": bool(result.exposure[-1] > 0),
            "max_drawdown": float(np.max(1.0 - curve / peak)) if len(curve) else 0.0}


def initialize(home, owner, *, now=None, fetcher=fetch_closed, clock=time.time):
    if not isinstance(owner, str) or not OWNER.fullmatch(owner):
        raise ValueError("invalid_owner_label: 3-64 characters of a-z 0-9 . _ -, first one a letter or digit")
    now = clock() if now is None else now
    path = _path(home)
    if path.exists():
        raise FileExistsError(str(path))  # refuse before any network call
    arrays = fetcher(None, now, SEED_BARS)
    if arrays is None or len(arrays["ts"]) < SEED_BARS // 2:
        raise ValueError("seed_unavailable")
    if int(arrays["ts"][-1]) + LATE_AFTER <= now:
        raise ValueError("seed_stale")
    activation = (int(now) // STEP + 1) * STEP
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = {"owner": owner, "created_at": now, "activation": activation,
                "last_sample_bar": activation + (MAX_BARS - 1) * STEP,
                "expires_at": activation + (MAX_BARS + EXPIRY_GRACE_BARS) * STEP,
                "max_bars": MAX_BARS, "spec": SPEC, "accounts": list(ACCOUNTS),
                "capital": CAPITAL, "slippage_bps": SLIPPAGE_BPS,
                "implementation": implementation(),
                "source": "Binance spot HYPEUSDT 1h closed candles; reference OHLC paper, not Hyperliquid HYPE",
                "execution": "long or cash, no leverage, no funded order; candle-open reference fills; "
                             "fill_delay 1 is the zero-latency study convention, 2 adds one hour",
                "evidence": "research/papers/results/hype_study_2026-11-27.md; no validated edge, lead candidate only"}
    # Build in a private file and publish it with a hard link, so a crash can never
    # leave a half-built store at the real path. A leftover .init file is safe to delete.
    staging = path.with_name(path.name + ".init")
    staging.unlink(missing_ok=True)
    os.close(os.open(staging, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
    try:
        with closing(sqlite3.connect(staging)) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),last_ts INTEGER NOT NULL,status TEXT NOT NULL,reason TEXT,late_bars INTEGER NOT NULL,strikes INTEGER NOT NULL);
                CREATE TABLE candles(bar INTEGER PRIMARY KEY,open REAL,high REAL,low REAL,close REAL,volume REAL,observed REAL NOT NULL);
                CREATE TABLE snapshots(account TEXT,bar INTEGER,observed REAL,metrics TEXT,PRIMARY KEY(account,bar));
                CREATE TRIGGER immutable_candle_update BEFORE UPDATE ON candles BEGIN SELECT RAISE(ABORT,'immutable_paper_candle'); END;
                CREATE TRIGGER immutable_candle_delete BEFORE DELETE ON candles BEGIN SELECT RAISE(ABORT,'immutable_paper_candle'); END;
            """)
            for key, value in metadata.items():
                db.execute("INSERT INTO metadata VALUES(?,?)", (key, canonical(value)))
            db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?)", _rows(arrays, now))
            db.execute("INSERT INTO state VALUES(1,?,?,?,0,0)", (int(arrays["ts"][-1]), "running", None))
            db.commit()
            db.execute(f"PRAGMA application_id={APP_ID}")
            db.commit()
        os.link(staging, path)
    finally:
        staging.unlink(missing_ok=True)
    return report(home, now=now)


def _terminal(home, status, reason):
    with connection(home, write=True) as db:
        # Only a running sample can end: a stale loser must never overwrite a finished one.
        db.execute("UPDATE state SET status=?,reason=? WHERE id=1 AND status='running'", (status, reason))


def _note(home, reason):
    with connection(home, write=True) as db:
        db.execute("UPDATE state SET reason=? WHERE id=1 AND status='running'", (reason,))


def _load(home):
    with connection(home) as db:
        state = db.execute("SELECT * FROM state").fetchone()
        meta = {row[0]: json.loads(row[1]) for row in db.execute("SELECT * FROM metadata")}
    if state is None or not meta:
        raise ValueError("incompatible_paper_store")
    return dict(state), meta


def _strike(home, count):
    with connection(home, write=True) as db:
        db.execute("UPDATE state SET strikes=? WHERE id=1 AND status='running'", (count,))


def _advance(home, state, meta, arrays, clock):
    """Persist new closed bars and one snapshot per account. Raises on a gap or a racing writer."""
    if int(arrays["ts"][0]) != state["last_ts"] + STEP:
        raise SourceGap(f"source_gap:expected={state['last_ts'] + STEP},got={int(arrays['ts'][0])}")
    keep = arrays["ts"] <= meta["last_sample_bar"]
    arrays = {key: value[keep] for key, value in arrays.items()}
    if not len(arrays["ts"]):
        return
    observed = clock()
    late = int(np.sum(observed > arrays["ts"] + LATE_AFTER))
    with connection(home, write=True) as db:
        if db.execute("SELECT last_ts FROM state").fetchone()[0] != state["last_ts"]:
            raise ConcurrentWriter("concurrent_paper_writer")
        db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?)", _rows(arrays, observed))
        full = _arrays(db.execute("SELECT bar,open,high,low,close,volume FROM candles ORDER BY bar").fetchall())
        latest = int(full["ts"][-1])
        for account in ACCOUNTS:
            db.execute("INSERT INTO snapshots VALUES(?,?,?,?)",
                       (account["id"], latest, observed, canonical(_simulate(account, full, meta["activation"]))))
        done = latest >= meta["last_sample_bar"]
        db.execute("UPDATE state SET last_ts=?,late_bars=late_bars+?,status=?,reason=?,strikes=0 WHERE id=1",
                   (latest, late, "completed" if done else "running", "sample_complete" if done else None))


def _poll(home, state, meta, now, fetcher, clock):
    try:
        # Never look past the frozen sample: a gap or bad bar after its last bar must not
        # turn a complete sample into a blocked one.
        arrays = fetcher(state["last_ts"], now, until=meta["last_sample_bar"] + STEP + CLOSE_SETTLE_S)
        if arrays is not None:
            _advance(home, state, meta, arrays, clock)
    except SourceGap as exc:
        _terminal(home, "blocked", str(exc)[:200])
    except ConcurrentWriter:
        pass  # the other writer's progress stands; the next poll re-reads it
    except (OSError, FeedError) as exc:
        # Transient by design: the next poll retries the same bar. Keep it visible.
        _note(home, f"feed_error:{type(exc).__name__}:{exc}"[:200])


def tick(home, *, now=None, fetcher=fetch_closed, clock=time.time):
    now = clock() if now is None else now
    state, meta = _load(home)
    if state["status"] in TERMINAL:
        return report(home, now=now)
    current = implementation()
    if meta["implementation"] != current:
        changed = sorted(key for key in current.keys() | meta["implementation"].keys()
                         if current.get(key) != meta["implementation"].get(key))
        _terminal(home, "blocked", ("implementation_changed:" + ",".join(changed))[:200])
    elif state["last_ts"] >= meta["last_sample_bar"]:
        _terminal(home, "completed", "sample_complete")
    elif now >= meta["expires_at"]:
        if state["strikes"] + 1 >= EXPIRY_STRIKES:
            _terminal(home, "expired", "hard_expiry_before_sample_complete")
        else:
            _strike(home, state["strikes"] + 1)
    else:
        if state["strikes"]:
            _strike(home, 0)  # strikes count consecutive polls; any poll before expiry clears them
        if now >= state["last_ts"] + 2 * STEP + CLOSE_SETTLE_S:
            _poll(home, state, meta, now, fetcher, clock)
    return report(home, now=now)


def report(home, *, now=None):
    now = time.time() if now is None else now
    with connection(home) as db:
        state = db.execute("SELECT * FROM state").fetchone()
        meta = {row[0]: json.loads(row[1]) for row in db.execute("SELECT * FROM metadata")}
        if state is None or not meta:
            raise ValueError("incompatible_paper_store")
        state = dict(state)
        bars = db.execute("SELECT count(*) FROM candles WHERE bar>=?", (meta["activation"],)).fetchone()[0]
        accounts = []
        for account in ACCOUNTS:
            row = db.execute("SELECT bar,observed,metrics FROM snapshots WHERE account=? ORDER BY bar DESC LIMIT 1", (account["id"],)).fetchone()
            accounts.append({**account, "latest": {"bar": row[0], "observed_at": row[1], "metrics": json.loads(row[2])} if row else None})
    return {"schema_version": 1, "paper_only": True, "as_of": now, "owner": meta["owner"],
            "status": state["status"], "reason": state["reason"], "last_ts": state["last_ts"],
            "late_bars": state["late_bars"], "sample_bars": bars, "max_bars": meta["max_bars"],
            "activation": meta["activation"], "expires_at": meta["expires_at"],
            "stale": state["status"] == "running" and now >= state["last_ts"] + 3 * STEP + STALE_GRACE_S,
            "metadata": meta, "accounts": accounts}


def run(home, poll=30):
    import fcntl
    report(home)  # fail fast on a missing or foreign store instead of polling it forever
    fd = os.open(_path(home).with_suffix(".lock"), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    stop = False

    def terminate(*_):
        nonlocal stop
        stop = True

    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(canonical({"status": "already_running"}), flush=True)
            return 0  # a clean exit, so launchd does not respawn a duplicate
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, terminate)
        failures = 0
        while not stop:
            try:
                value = tick(home)
                failures = 0
                print(canonical({"at": value["as_of"], "paper_only": True, "status": value["status"],
                                 "reason": value["reason"], "last_ts": value["last_ts"],
                                 "sample_bars": value["sample_bars"], "late_bars": value["late_bars"],
                                 "stale": value["stale"]}), flush=True)
                if value["status"] in TERMINAL:
                    return 0  # finite by design: a finished sample never restarts
            except (OSError, ValueError, sqlite3.Error) as exc:
                failures += 1
                print(canonical({"at": time.time(), "status": "store_error", "reason": "paper_store_failed",
                                 "failures": failures, "error": f"{type(exc).__name__}:{exc}"[:200]}), flush=True)
                if failures >= MAX_STORE_ERRORS:
                    return 2  # a permanent fault: fail loudly so launchd restarts and surfaces it
            until = time.monotonic() + poll
            while not stop and time.monotonic() < until:
                time.sleep(min(1, max(0, until - time.monotonic())))
    finally:
        os.close(fd)
    return 0


def install_service(home, python=sys.executable):
    if sys.platform != "darwin":
        raise ValueError("launchd_service_requires_macos")
    home = _path(home).parent
    stored = report(home)["metadata"]["implementation"]
    python = Path(python).absolute()
    if not python.is_file() or "-wt-" in str(python) or "/worktrees/" in str(python):
        raise ValueError("stable_installed_python_required: install the packages into a stable venv and pass --python")
    # -I ignores PYTHONPATH and the cwd, so the service only runs what that interpreter installed.
    probe = subprocess.run([str(python), "-I", "-c", "import json,ecosystem.hype_forward as m;print(json.dumps(m.implementation()))"],
                           capture_output=True, text=True, timeout=30, check=False)
    if probe.returncode:
        raise ValueError("installed_probe_failed: " + (probe.stderr or "")[-300:])
    try:
        installed = json.loads(probe.stdout)
    except ValueError as exc:
        raise ValueError("installed_probe_output_invalid") from exc
    if installed != stored:
        raise ValueError("installed_implementation_mismatch: reinstall ecosystem and backtester from the code that ran init")
    label = "com.solmargintrader.hype-forward." + hashlib.sha256(os.path.realpath(home).encode()).hexdigest()[:12]
    path = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    # Restart only after a crash: a finished or expired sample exits 0 and stays down.
    document = {"Label": label, "ProgramArguments": [str(python), "-I", "-m", "ecosystem.hype_forward", "--home", str(home), "run"],
                "RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 10,
                "StandardOutPath": str(home / "daemon.log"), "StandardErrorPath": str(home / "daemon.log"),
                "WorkingDirectory": str(home)}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and plistlib.loads(path.read_bytes()) != document):
        raise ValueError(f"service_configuration_conflict: review and remove {path} before reinstalling")
    path.write_bytes(plistlib.dumps(document))
    path.chmod(0o600)
    domain = "gui/" + str(os.getuid())
    try:
        present = subprocess.run(["launchctl", "print", domain + "/" + label], capture_output=True, timeout=10, check=False)
        if present.returncode:
            subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True, capture_output=True, timeout=15)
        subprocess.run(["launchctl", "enable", domain + "/" + label], check=True, capture_output=True, timeout=10)
    except subprocess.CalledProcessError as exc:
        raise ValueError("launchctl_failed: " + (exc.stderr or b"").decode(errors="replace")[:300]) from exc
    return {"label": label, "path": str(path)}


def _explain(exc, home):
    if isinstance(exc, sqlite3.OperationalError) and not _path(home).exists():
        return f"no store at {_path(home)}; run init --owner <label> first"
    if isinstance(exc, FileExistsError):
        return f"a store already exists at {exc}; use status, or choose a new --home"
    return f"{type(exc).__name__}: {exc}"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Example: python -m ecosystem.hype_forward --home /path/to/new-cohort init --owner my-label; "
        "then python -m ecosystem.hype_forward --home /path/to/new-cohort status (read-only).",
    )
    parser.add_argument("--home", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--owner", required=True, help="lowercase owner label, 3-64 chars of a-z 0-9 . _ -")
    commands.add_parser("run")
    commands.add_parser("status")
    service = commands.add_parser("install-service")
    service.add_argument("--python", type=Path, default=Path(sys.executable),
                         help="interpreter with ecosystem and backtester installed (not a worktree venv)")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            value = initialize(args.home, args.owner)
        elif args.command == "run":
            return run(args.home)
        elif args.command == "install-service":
            value = install_service(args.home, args.python)
        else:
            value = report(args.home)
    except (ValueError, OSError, sqlite3.Error) as exc:
        print("hype_forward: " + _explain(exc, args.home), file=sys.stderr)
        return 2
    print(canonical(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

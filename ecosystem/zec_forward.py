"""Independent, source-bound ZEC ensemble paper accounts and Oracle publication.

All decisions use closed Binance spot candles. The canonical engine applies an
issued target at the following observed candle open. This is reference paper
accounting, never evidence of an executable fill or a probability of profit.
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
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

from backtester.core.data import CsvLoader, frame_to_arrays
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import BarWindow, CostConfig, validate_bar_arrays

APP_ID = 0x5A454331
INTERVALS = {"1m": 60, "1h": 3600}
SOURCE = "binance_spot_public_market_data"
INSTRUMENT = "ZEC/USDT"
API = "https://data-api.binance.vision/api/v3/klines"


def _invalid_json():
    raise TypeError("unsupported_study_json_value")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=lambda value: value.item() if isinstance(value, np.generic) else _invalid_json())


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def implementation():
    from backtester.core import engine
    core = Path(engine.__file__).parent
    result = {"backtester/core/" + str(path.relative_to(core)): hashlib.sha256(path.read_bytes()).hexdigest()
              for path in sorted(core.rglob("*.py"))}
    result["ecosystem/zec_forward.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def _path(home):
    return Path(home).expanduser().absolute() / "zec-forward.sqlite3"


@contextmanager
def connection(home, *, write=False):
    path = _path(home)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("unsafe_study_path")
    if write:
        path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(fd)
        db = sqlite3.connect(path, timeout=5)
    else:
        if not path.is_file():
            raise ValueError("study_not_initialized")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
        db.execute("PRAGMA query_only=ON")
    db.row_factory = sqlite3.Row
    try:
        if not write and db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            raise ValueError("incompatible_study_store")
        yield db
        if write:
            db.commit()
    except BaseException:
        if write:
            db.rollback()
        raise
    finally:
        db.close()


def _publish_database(source, destination):
    """Publish a complete database exactly once; a foreign path is never replaced."""
    with source.open("rb") as handle:
        os.fsync(handle.fileno())
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    os.link(source, destination)
    fd = os.open(destination.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def atomic_store(home):
    destination = _path(home)
    with tempfile.TemporaryDirectory(prefix=".zec-init-", dir=destination.parent.parent) as tmp:
        temporary_home = Path(tmp)
        yield temporary_home
        source = _path(temporary_home)
        with connection(temporary_home) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("study_initialization_integrity_failed")
            if db.execute("SELECT count(*) FROM candidates").fetchone()[0] != 10:
                raise ValueError("study_initialization_incomplete")
        _publish_database(source, destination)


class ForwardStrategy:
    """Prime the exact policy while keeping all pre-start capital in cash."""
    def __init__(self, config, activation, full_history):
        from backtester.core.zec_ensemble import build_ensemble
        self.inner = build_ensemble(config)
        self.activation = activation
        self.full_history = full_history
        self.name = self.inner.name
        self.params = json.loads(canonical({**self.inner.params, "forward_activation": activation}))

    def warmup_bars(self):
        return self.inner.warmup_bars()

    def on_bar(self, history: BarWindow):
        timestamp = int(history.ts[-1])
        i = int(np.searchsorted(self.full_history["ts"], timestamp))
        if i >= len(self.full_history["ts"]) or int(self.full_history["ts"][i]) != timestamp:
            raise ValueError("forward_history_missing")
        a = self.full_history
        visible = BarWindow(a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], i)
        target = self.inner.on_bar(visible)
        return target if timestamp >= self.activation else 0.0

    def checkpoint_state(self):
        return {"inner": self.inner.checkpoint_state()}

    def restore_state(self, state):
        self.inner.restore_state(state["inner"])


def engine_config(row):
    costs = row.get("costs", {})
    if not {"fee_bps", "slippage_bps"} <= set(costs):
        raise ValueError("explicit_study_costs_required")
    execution = {"fill_delay": 1, "mode": "spot", "leverage": 1}
    if not isinstance(costs, dict) or set(costs) - (set(CostConfig.__dataclass_fields__) | set(execution)):
        raise ValueError("invalid_study_costs")
    if any(costs.get(key, value) != value for key, value in execution.items()):
        raise ValueError("unsupported_study_execution")
    costs = {key: value for key, value in costs.items() if key in CostConfig.__dataclass_fields__}
    return EngineConfig(interval=row["interval"], mode="spot", fill_delay=1,
                        initial_capital=10_000.0, allow_short=False,
                        rebalance_threshold=row["config"].get("rebalance_threshold", 0),
                        costs=CostConfig(**costs))


def validate_selection(value):
    if value.get("schema_version") != 1 or not isinstance(value.get("selected"), list):
        raise ValueError("invalid_selection")
    from backtester.core.zec_ensemble import candidate_id

    rows = value["selected"]
    if len(rows) != 10 or len({r.get("candidate_id") for r in rows}) != 10:
        raise ValueError("ten_unique_candidates_required")
    for row in rows:
        if (not isinstance(row.get("candidate_id"), str) or len(row["candidate_id"]) > 120
                or row.get("interval") not in INTERVALS
                or row.get("config", {}).get("interval") != row["interval"]):
            raise ValueError("invalid_candidate")
        if row["candidate_id"] != candidate_id(row["config"]):
            raise ValueError("candidate_configuration_changed")
        engine_config(row)
    return rows


def initialize(home, selection_path, seeds, *, now=None):
    path = _path(home)
    path.parent.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    lock = path.parent.parent / (".zec-init-" + hashlib.sha256(str(path).encode()).hexdigest()[:16] + ".lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return _initialize(home, selection_path, seeds, now=now)
    finally:
        os.close(fd)


def _initialize(home, selection_path, seeds, *, now=None):
    now = time.time() if now is None else now
    selection = json.loads(Path(selection_path).read_text())
    rows = validate_selection(selection)
    selection_hash = digest(selection)
    manifest = json.loads(Path(selection_path).with_name("manifest.json").read_text())
    expected_core = {key: value for key, value in manifest["fingerprint"]["code"].items() if key.startswith("backtester/core/")}
    installed_core = {key: value for key, value in implementation().items() if key.startswith("backtester/core/")}
    if (not expected_core or expected_core != installed_core
            or manifest.get("study_id") != selection.get("study_id")
            or manifest.get("top10_sha256") != hashlib.sha256(Path(selection_path).read_bytes()).hexdigest()):
        raise ValueError("study_manifest_implementation_or_selection_changed")
    path = _path(home)
    if path.exists():
        try:
            with connection(home) as db:
                identity = db.execute("SELECT value FROM metadata WHERE key='selection_hash'").fetchone()
                if identity is None:
                    raise ValueError("incompatible_study_store")
                if identity[0] != selection_hash:
                    raise ValueError("study_selection_changed")
            return report(home, now=now)
        except sqlite3.Error:
            raise ValueError("incompatible_study_store") from None
    prepared = []
    seed_candles = {}
    source_arrays = {}
    for row in rows:
        interval = row["interval"]
        file_hash = hashlib.sha256(Path(seeds[interval]).read_bytes()).hexdigest()
        if row.get("source_sha256") and row["source_sha256"] != file_hash:
            raise ValueError("study_seed_hash_changed")
        step = INTERVALS[interval]
        activation = (int(now) // step + 1) * step
        from backtester.core.zec_ensemble import build_ensemble
        policy = build_ensemble(row["config"])
        if interval not in source_arrays:
            frame = CsvLoader(Path(seeds[interval]), allow_gaps=True).load("ZEC", None, None, interval)
            arrays = frame_to_arrays(frame)
            arrays = {k: v[np.asarray(arrays["ts"]) + step <= now] for k, v in arrays.items()}
            # Native source gaps cannot become invented flat candles.
            gaps = np.flatnonzero(np.diff(arrays["ts"]) != step)
            if len(gaps):
                arrays = {k: v[int(gaps[-1]) + 1:] for k, v in arrays.items()}
            if not len(arrays["ts"]):
                raise ValueError("empty_seed")
            fresh = fetch_closed(interval, int(arrays["ts"][-1]), now)
            if fresh is not None:
                arrays = {k: np.concatenate((v, fresh[k])) for k, v in arrays.items()}
            validate_bar_arrays(arrays, interval)
            source_arrays[interval] = arrays
        full = source_arrays[interval]
        initial = row.get("initial_state")
        if initial is not None:
            if int(initial["origin_ts"]) != int(full["ts"][0]):
                raise ValueError("study_seed_origin_changed")
            strategy = ForwardStrategy(row["config"], activation, full)
            strategy.inner.restore_state(initial)
            i = len(full["ts"]) - 1
            strategy.inner.on_bar(BarWindow(full["ts"], full["open"], full["high"], full["low"], full["close"], full["volume"], i))
            arrays = {k: v[-(policy.warmup_bars() + 1):] for k, v in full.items()}
        else:
            length = max(2000, policy.warmup_bars() * 10)
            full = {k: v[-length:] for k, v in full.items()}
            arrays = full
            strategy = ForwardStrategy(row["config"], activation, full)
        seed_candles.setdefault(interval, {})
        for i, timestamp in enumerate(full["ts"]):
            seed_candles[interval][int(timestamp)] = [float(full[k][i]) for k in ("open", "high", "low", "close", "volume")]
        if len(arrays["ts"]) <= strategy.warmup_bars() or now - (int(arrays["ts"][-1]) + step) > step * 2:
            raise ValueError("fresh_contiguous_warmup_required")
        result = run_backtest(strategy, arrays, engine_config(row), close_at_end=False)
        if result.continuation is None or result.trades:
            raise ValueError("prospective_seed_failed")
        prepared.append((row, activation, result.continuation, {
            "source": SOURCE, "instrument": INSTRUMENT,
            "start": int(full["ts"][0]), "end": int(full["ts"][-1]) + step,
            "bars": len(full["ts"]), "path": str(Path(seeds[interval]).absolute()),
            "sha256": hashlib.sha256(Path(seeds[interval]).read_bytes()).hexdigest(),
        }))
    with atomic_store(home) as temporary_home, connection(temporary_home, write=True) as db:
        if db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
            raise ValueError("study_store_not_empty")
        db.executescript("""
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE candidates(id TEXT PRIMARY KEY,rank INTEGER,interval TEXT,config TEXT,activation INTEGER,seed TEXT,state TEXT,last_ts INTEGER,status TEXT,reason TEXT,updated REAL);
            CREATE TABLE forecasts(id TEXT,bar INTEGER,issued REAL,decision_close INTEGER,target REAL,equity REAL,exposure REAL,price REAL,trades TEXT,PRIMARY KEY(id,bar));
            CREATE TABLE candles(interval TEXT,bar INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL,PRIMARY KEY(interval,bar));
        """)
        db.execute(f"PRAGMA application_id={APP_ID}")
        for key, value in (("selection_hash", selection_hash), ("selection", canonical(selection)), ("created", str(now)), ("implementation", canonical(implementation()))):
            db.execute("INSERT INTO metadata VALUES(?,?)", (key, value))
        for interval, candles in seed_candles.items():
            db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?)", [(interval, ts, *values) for ts, values in candles.items()])
        for rank, (row, activation, state, seed) in enumerate(prepared, 1):
            db.execute("INSERT INTO candidates VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                row["candidate_id"], rank, row["interval"], canonical(row), activation,
                canonical(seed), canonical(state), state["last_ts"], "waiting", "first_post_start_closed_bar", now))
    return report(home, now=now)


def fetch_closed(interval, last_ts, now):
    params = {"symbol": "ZECUSDT", "interval": interval, "startTime": last_ts * 1000,
              "endTime": int(now) * 1000, "limit": 1000}
    request = Request(API + "?" + urlencode(params), headers={"User-Agent": "solmargintrader-paper/1"})
    with urlopen(request, timeout=15) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("feed_response_too_large")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError("feed_unavailable")
    rows = []
    step = INTERVALS[interval]
    for value in data:
        if not isinstance(value, list) or len(value) < 7:
            raise ValueError("invalid_feed_candle")
        ts = int(value[0]) // 1000
        if ts <= last_ts or ts + step > now:
            continue
        rows.append((ts, *(float(value[i]) for i in (1, 2, 3, 4, 5))))
    if not rows:
        return None
    arrays = {name: np.asarray([row[i] for row in rows], dtype="int64" if i == 0 else "float64")
              for i, name in enumerate(("ts", "open", "high", "low", "close", "volume"))}
    return validate_bar_arrays(arrays, interval)


def tick(home, *, now=None, fetcher=fetch_closed):
    now = time.time() if now is None else now
    with connection(home) as db:
        candidates = [dict(row) for row in db.execute("SELECT * FROM candidates ORDER BY rank")]
        expected = db.execute("SELECT value FROM metadata WHERE key='implementation'").fetchone()
    if expected is None or expected[0] != canonical(implementation()):
        with connection(home, write=True) as db:
            db.execute("UPDATE candidates SET status='blocked',reason='study_implementation_changed',updated=?", (now,))
        return report(home, now=now)
    fetched = {}
    for interval in {row["interval"] for row in candidates}:
        start = min(row["last_ts"] for row in candidates if row["interval"] == interval)
        try:
            fetched[interval] = fetcher(interval, start, now)
        except (OSError, ValueError, TypeError, TimeoutError):
            fetched[interval] = "feed_unavailable"
    for row in candidates:
        if row["reason"] in {"forward_source_gap", "missed_forward_bars_review_required"}:
            # Recovering transport health cannot authorize missing decisions.
            # Keep the preserved book blocked until an explicit review.
            continue
        step = INTERVALS[row["interval"]]
        value = fetched[row["interval"]]
        reason = None
        if isinstance(value, str):
            reason = value
        elif value is None:
            age = now - (row["last_ts"] + step)
            if age > step + 30:
                reason = "closed_candle_stale"
            elif 0 <= age < step and row["reason"] in {"feed_unavailable", "closed_candle_stale"}:
                # A successful poll need not contain a new native candle. Clear
                # only transport/staleness health; never alter the paper book.
                row["status"] = "waiting" if row["last_ts"] < row["activation"] else "running"
                row["reason"] = "first_post_start_closed_bar" if row["status"] == "waiting" else None
        else:
            arrays = {k: v[value["ts"] > row["last_ts"]] for k, v in value.items()}
            if not len(arrays["ts"]):
                continue
            elif (int(arrays["ts"][0]) != row["last_ts"] + step
                  or np.any(np.diff(arrays["ts"]) != step)):
                reason = "forward_source_gap"
            elif (now - (row["last_ts"] + step) > step * 2 + 30
                  or int(np.count_nonzero(arrays["ts"] >= row["activation"])) > 1):
                # Never manufacture prospective decisions for bars missed while
                # the owner was offline. Preserve the book for explicit review.
                reason = "missed_forward_bars_review_required"
            if reason is None:
                candidate = json.loads(row["config"])
                seed = json.loads(row["seed"])
                with connection(home) as db:
                    observed = db.execute("SELECT bar,open,high,low,close,volume FROM candles WHERE interval=? AND bar>=? AND bar<=? ORDER BY bar", (row["interval"], seed["start"], row["last_ts"])).fetchall()
                prefix = {key: np.asarray([r[i] for r in observed]) for i, key in enumerate(("ts", "open", "high", "low", "close", "volume"))}
                full = {k: np.concatenate((prefix[k], arrays[k])) for k in prefix}
                strategy = ForwardStrategy(candidate["config"], row["activation"], full)
                result = run_backtest(strategy, arrays, engine_config(candidate), close_at_end=False,
                                      continuation=json.loads(row["state"]))
                account = result.account
                target = next(iter(account.pending_targets.values()), 0.0)
                with connection(home, write=True) as db:
                    current = db.execute("SELECT last_ts FROM candidates WHERE id=?", (row["id"],)).fetchone()[0]
                    if current != row["last_ts"]:
                        raise ValueError("concurrent_forward_writer")
                    for i, ts in enumerate(result.timestamps):
                        values = [float(arrays[k][i]) for k in ("open", "high", "low", "close", "volume")]
                        old = db.execute("SELECT open,high,low,close,volume FROM candles WHERE interval=? AND bar=?", (row["interval"], int(ts))).fetchone()
                        if old is not None and list(old) != values:
                            raise ValueError("source_candle_changed")
                        db.execute("INSERT OR IGNORE INTO candles VALUES(?,?,?,?,?,?,?)", (row["interval"], int(ts), *values))
                        trades = [vars(t) for t in result.trades if int(t.ts) == int(ts)]
                        # Only the newest close is an actionable reference call.
                        db.execute("INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?,?)", (
                            row["id"], int(ts), now, int(ts) + step,
                            target if i == len(result.timestamps) - 1 else None,
                            float(result.equity[i]), float(result.exposure[i]), float(arrays["close"][i]), canonical(trades)))
                    db.execute("UPDATE candidates SET state=?,last_ts=?,status=?,reason=?,updated=? WHERE id=?", (
                        canonical(result.continuation), int(result.timestamps[-1]),
                        "running" if int(result.timestamps[-1]) >= row["activation"] else "waiting",
                        None if int(result.timestamps[-1]) >= row["activation"] else "first_post_start_closed_bar",
                        now, row["id"]))
                continue
        with connection(home, write=True) as db:
            db.execute("UPDATE candidates SET status=?,reason=?,updated=? WHERE id=?", (
                "blocked" if reason else row["status"], reason or row["reason"], now, row["id"]))
    with connection(home, write=True) as db:
        db.execute("INSERT OR REPLACE INTO metadata VALUES('heartbeat',?)", (str(now),))
    return report(home, now=now)


def report(home, *, now=None):
    now = time.time() if now is None else now
    with connection(home) as db:
        metadata = {row[0]: row[1] for row in db.execute("SELECT key,value FROM metadata")}
        rows = [dict(row) for row in db.execute("SELECT * FROM candidates ORDER BY rank")]
        implementation_matches = metadata.get("implementation") == canonical(implementation())
        accounts = []
        for row in rows:
            state = json.loads(row.pop("state"))
            candidate = json.loads(row.pop("config"))
            last = db.execute("SELECT * FROM forecasts WHERE id=? ORDER BY bar DESC LIMIT 1", (row["id"],)).fetchone()
            close = row["last_ts"] + INTERVALS[row["interval"]]
            fresh = now - float(metadata.get("heartbeat", 0)) <= 35 and 0 <= now - close < INTERVALS[row["interval"]]
            available = implementation_matches and fresh and row["last_ts"] >= row["activation"] and row["status"] == "running" and last is not None and last["target"] is not None
            accounts.append({**row, "seed": json.loads(row["seed"]), "candidate": {k: v for k, v in candidate.items() if k != "initial_state"},
                "config_hash": digest(candidate["config"]), "selection_hash": metadata["selection_hash"],
                "available": available, "target": last["target"] if available else None,
                "equity": last["equity"] if last else 10_000.0,
                "net_return": (last["equity"] / 10_000 - 1) if last else 0.0,
                "exposure": last["exposure"] if last else 0.0,
                "costs_paid": state["totals"],
                "decisions": db.execute("SELECT count(*) FROM forecasts WHERE id=? AND bar>=?", (row["id"],row["activation"])).fetchone()[0],
                "decision_close": close, "issued_at": last["issued"] if last else None,
                "expires_at": close + INTERVALS[row["interval"]],
                "reason": "study_implementation_changed" if not implementation_matches else row["reason"] if row["reason"] else None if available else "owner_or_candle_stale"})
        winner = accounts[0]
        history = [dict(row) for row in db.execute("SELECT bar,issued,target,equity,exposure,price FROM forecasts WHERE id=? ORDER BY bar DESC LIMIT 240", (winner["id"],))]
    return {"schema_version": 1, "instrument": INSTRUMENT, "source": SOURCE,
            "mode": "paper", "tradable": False, "selection_hash": metadata["selection_hash"],
            "implementation": json.loads(metadata["implementation"]),
            "created_at": float(metadata["created"]), "heartbeat": float(metadata.get("heartbeat", 0)),
            "accounts": accounts, "publication": winner, "history": list(reversed(history)),
            "scope": "independent_virtual_accounts_not_shared_capital", "as_of": now}


def publish(home, ui_home):
    snapshot = report(home)
    path = Path(ui_home).expanduser().absolute() / "zec-study.json"
    if path.is_symlink():
        raise ValueError("unsafe_publication_path")
    from ecosystem.runner import save
    save(path, {"schema_version": 1, "home": str(Path(home).expanduser().absolute()),
                "selection_hash": snapshot["selection_hash"], "instrument": INSTRUMENT})
    return {"path": str(path), "instrument": INSTRUMENT, "selection_hash": snapshot["selection_hash"]}


def publication(ui_home, instrument, *, now=None):
    path = Path(ui_home).expanduser().absolute() / "zec-study.json"
    if not path.exists():
        return None
    try:
        if path.is_symlink():
            raise ValueError("unsafe_publication_path")
        pointer = json.loads(path.read_text())
        snapshot = report(pointer["home"], now=now)
        if pointer["selection_hash"] != snapshot["selection_hash"]:
            raise ValueError("publication_selection_changed")
        return {**snapshot, "selected": instrument == INSTRUMENT}
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error):
        return {"instrument": INSTRUMENT, "selected": instrument == INSTRUMENT,
                "status": "unavailable", "reason": "selected_study_unavailable", "publication": None}


def oracle_view(snapshot, *, now=None):
    """Read the selected experiment without recasting exposure as confidence."""
    now = time.time() if now is None else now
    winner = snapshot.get("publication")
    available = bool(winner and winner.get("available"))
    interval = winner["interval"] if winner else None
    target = winner["target"] if available else None
    signal_name = ("Long" if target > 0 else "Flat") if available else None
    history = snapshot.get("history", [])
    latest = history[-1] if history else None
    observation = {"instrument": INSTRUMENT, "source": SOURCE, "venue": "binance_spot",
                   "kind": "closed_native_" + (interval or "unknown"),
                   "observed_at": winner["decision_close"] if winner else None,
                   "received_at": winner["issued_at"] if winner else None,
                   "price": latest["price"] if latest else None}
    reason = winner.get("reason") if winner else snapshot.get("reason", "selected_study_unavailable")
    aggregate = {"status": "available" if available else "unavailable", "signal": signal_name,
                 "balance_percent": target * 100 if available else None,
                 "expires_at": winner["expires_at"] if winner else None,
                 "included": [{"strategy_id": winner["id"]}] if winner else [], "excluded": [], "reason": reason}
    ticks = [{"tick_id": str(row["bar"]), "bar_index": i, "time": row["bar"] + INTERVALS[interval],
              "observed_at": row["bar"] + INTERVALS[interval], "received_at": row["issued"],
              "price": row["price"], "market_shape": None,
              "aggregate": {"signal": "Long" if (row["target"] or 0) > 0 else "Flat",
                            "balance_percent": row["target"] * 100 if row["target"] is not None else None,
                            "included": [{"strategy_id": winner["id"]}], "excluded": []},
              "strategies": [{"strategy_id": winner["id"], "direction": int((row["target"] or 0) > 0),
                              "accuracy_percent": None, "resolved": None, "vote_eligible": True,
                              "reason": "frozen_selected_paper_configuration"}]}
             for i, row in enumerate(history)]
    return {"schema_version": 1, "instrument": INSTRUMENT, "as_of": now,
            "status": aggregate["status"], "reason": reason, "signal": signal_name,
            "tradable": False, "percentage_semantics": "target_exposure_not_probability",
            "balance_percent": aggregate["balance_percent"], "aggregate": aggregate,
            "horizon_seconds": INTERVALS.get(interval), "strategies": [], "catalog": [],
            "selection": None, "selected_ids": [], "selected_experiment": snapshot,
            "market": {"status": aggregate["status"], "observation": observation, "reason": reason,
                       "limitations": ["reference_paper_next_open_fills", "no_profit_probability", "no_USD_quote_conversion"]},
            "graph": {"schema_version": 1, "instrument": INSTRUMENT,
                      "status": "available" if ticks else "unavailable", "ticks": ticks,
                      "aggregate_semantics": "target_exposure_not_probability"}}


def run(home, poll=10):
    path = _path(home).with_suffix(".lock")
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    stop = False
    def terminate(*_):
        nonlocal stop
        stop = True
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signal.signal(signal.SIGINT, terminate)
        signal.signal(signal.SIGTERM, terminate)
        while not stop:
            try:
                tick(home)
            except (OSError, ValueError, sqlite3.Error, KeyError):
                print(canonical({"status": "blocked", "reason": "paper_tick_failed"}), flush=True)
            until = time.monotonic() + poll
            while not stop and time.monotonic() < until:
                time.sleep(min(1, until - time.monotonic()))
    finally:
        os.close(fd)


def install_service(home, python=sys.executable):
    if sys.platform != "darwin":
        raise ValueError("launchd_service_requires_macos")
    home = Path(home).expanduser().absolute()
    report(home)
    label = "com.solmargintrader.zec-forward." + hashlib.sha256(str(home).encode()).hexdigest()[:12]
    path = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    log = str(home / "daemon.log")
    document = {"Label": label, "ProgramArguments": [str(Path(python).absolute()), "-I", "-m", "ecosystem.zec_forward", "--home", str(home), "run"],
                "RunAtLoad": True, "KeepAlive": True, "ThrottleInterval": 10,
                "StandardOutPath": log, "StandardErrorPath": log,
                "WorkingDirectory": str(home)}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and plistlib.loads(path.read_bytes()) != document:
        raise ValueError("service_configuration_conflict")
    path.write_bytes(plistlib.dumps(document))
    os.chmod(path, 0o600)
    domain = "gui/" + str(os.getuid())
    existing = subprocess.run(["launchctl", "print", domain + "/" + label], capture_output=True, timeout=10, check=False)
    if existing.returncode:
        subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True, capture_output=True, timeout=15)
    subprocess.run(["launchctl", "enable", domain + "/" + label], check=True, capture_output=True, timeout=10)
    return {"label": label, "path": str(path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--selection", type=Path, required=True)
    init.add_argument("--seed-1m", type=Path, required=True)
    init.add_argument("--seed-1h", type=Path, required=True)
    commands.add_parser("run")
    commands.add_parser("status")
    pub = commands.add_parser("publish")
    pub.add_argument("--ui-home", type=Path, required=True)
    commands.add_parser("install-service")
    args = parser.parse_args(argv)
    if args.command == "init":
        value = initialize(args.home, args.selection, {"1m": args.seed_1m, "1h": args.seed_1h})
    elif args.command == "run":
        return run(args.home)
    elif args.command == "publish":
        value = publish(args.home, args.ui_home)
    elif args.command == "install-service":
        value = install_service(args.home)
    else:
        value = report(args.home)
    print(canonical(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

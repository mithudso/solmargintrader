"""Isolated, frozen Coinbase hourly PAPER cohort. No signing or order interface.

Targets commit and receive a separate post-commit confirmation before their
eligible future candle. Closed candles are reference fills, not venue fills.
An outage blocks the cohort rather than backfilling missed decisions.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import signal
import sqlite3
import time
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import build
from backtester.core.types import BarWindow, CostConfig, validate_bar_arrays

APP_ID = 0x4D465731
STEP = 3600
ASSETS = ("BTC", "ETH", "ZEC")
KEYS = ("ts", "open", "high", "low", "close", "volume")
MAX_BARS = 100_000


def canonical(value):
    def convert(item):
        if isinstance(item, np.generic):
            return item.item()
        raise TypeError("unsupported_paper_json_value")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False,
                      default=convert)


def implementation():
    from backtester.core import engine
    core = Path(engine.__file__).parent
    result = {"backtester/core/" + str(p.relative_to(core)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(core.rglob("*.py"))}
    result["ecosystem/meta_forward.py"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def default_config(passive_zec_weight=None):
    accounts = []
    policies = [
        ("breakout_zec", [{"asset": "ZEC", "weight": 1, "strategy": "bb_breakout", "params": {"window": 40, "num_std": 2.5}}]),
        ("hold_zec", [{"asset": "ZEC", "weight": 1, "strategy": "buy_and_hold", "params": {}}]),
        ("hold_core", [{"asset": asset, "weight": 0.5, "strategy": "buy_and_hold", "params": {}} for asset in ("BTC", "ETH")]),
        ("cash", []),
    ]
    if passive_zec_weight is not None:
        if isinstance(passive_zec_weight, bool) or not math.isfinite(passive_zec_weight) or not 0 <= passive_zec_weight <= 1:
            raise ValueError("passive_zec_weight_must_be_in_unit_interval")
        sleeves = [{"asset": "ZEC", "weight": passive_zec_weight, "strategy": "buy_and_hold", "params": {}}] if passive_zec_weight else []
        policies.append(("sized_hold_zec", sleeves))
    for fee, scenario in ((90, "taker_primary"), (50, "maker_cost_sensitivity")):
        for name, sleeves in policies:
            accounts.append({"id": name + "_" + scenario, "label": name, "scenario": scenario,
                             "capital": 10000, "fee_bps": fee, "slippage_bps": 2, "sleeves": sleeves})
    return {"schema_version": 1, "paper_only": True, "interval": "1h", "accounts": accounts,
            "cost_basis": "Authenticated API fee scenarios; maker sensitivity does not model queue/nonfills"}


def validate_config(value):
    canonical(value)
    if not isinstance(value, dict):
        raise ValueError("frozen_hourly_paper_config_required")  # noqa: TRY004
    if value.get("schema_version") != 1 or value.get("paper_only") is not True or value.get("interval") != "1h":
        raise ValueError("frozen_hourly_paper_config_required")
    rows = value.get("accounts")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        raise ValueError("invalid_paper_account_count")
    identities = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) - {"id", "label", "scenario", "capital", "fee_bps", "slippage_bps", "sleeves"}:
            raise ValueError("invalid_paper_account_spec")
        identity = row.get("id")
        if not isinstance(identity, str) or not identity or identity in identities:
            raise ValueError("unique_paper_account_ids_required")
        identities.add(identity)
        for key in ("capital", "fee_bps", "slippage_bps"):
            number = row.get(key)
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
                raise ValueError("explicit_finite_paper_costs_required")
        if row["capital"] <= 0 or row["fee_bps"] >= 10000 or row["slippage_bps"] >= 10000:
            raise ValueError("invalid_paper_costs_or_capital")
        assets, total = set(), 0.0
        if not isinstance(row.get("sleeves"), list):
            raise ValueError("paper_sleeves_required")  # noqa: TRY004 -- frozen configuration refusal
        for sleeve in row["sleeves"]:
            asset = sleeve.get("asset")
            weight = sleeve.get("weight")
            if asset not in ASSETS or asset in assets or isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight) or not 0 < weight <= 1:
                raise ValueError("invalid_unlevered_paper_sleeve")
            if sleeve.get("strategy") not in ("bb_breakout", "buy_and_hold"):
                raise ValueError("unsupported_frozen_paper_strategy")
            params = sleeve.get("params", {})
            if not isinstance(params, dict) or (sleeve["strategy"] == "buy_and_hold" and params):
                raise ValueError("invalid_paper_strategy_parameters")
            if sleeve["strategy"] == "bb_breakout":
                window, deviation = params.get("window", 20), params.get("num_std", 2)
                if set(params) - {"window", "num_std"} or type(window) is not int or not 2 <= window <= 200:
                    raise ValueError("invalid_paper_strategy_parameters")
                if isinstance(deviation, bool) or not isinstance(deviation, (int, float)) or not math.isfinite(deviation) or not 0 < deviation <= 10:
                    raise ValueError("invalid_paper_strategy_parameters")
            strategy = build(sleeve["strategy"], **sleeve.get("params", {}))
            if strategy.warmup_bars() > 200:
                raise ValueError("paper_warmup_limit")
            assets.add(asset)
            total += weight
        if total > 1 + 1e-12:
            raise ValueError("paper_sleeves_exceed_capital")
    return value


def _path(home):
    home = Path(home).expanduser().absolute()
    if home.is_symlink():
        raise ValueError("unsafe_paper_home")
    path = home / "meta-forward.sqlite3"
    if path.is_symlink():
        raise ValueError("unsafe_paper_store")
    return path


@contextmanager
def owner(home):
    path = _path(home).with_suffix(".lock")
    fd = os.open(path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


@contextmanager
def connection(home, *, write=False):
    db = sqlite3.connect(_path(home).as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=5)
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


def arrays(rows):
    return {key: np.asarray([r[i] for r in rows], dtype="int64" if i == 0 else "float64") for i, key in enumerate(KEYS)}


def fetch_closed(asset, after, now):
    """Coinbase native1h candles. Never synthesize a missing observation."""
    if asset not in ASSETS:
        raise ValueError("unsupported_source_asset")
    end = int(now // STEP) * STEP
    start = int(after + STEP) if after is not None else end - 299 * STEP
    query = {"granularity": STEP, "end": datetime.fromtimestamp(end, UTC).isoformat(),
             "start": datetime.fromtimestamp(start, UTC).isoformat()}
    url = f"https://api.exchange.coinbase.com/products/{asset}-USD/candles?" + urlencode(query)
    with urlopen(Request(url, headers={"User-Agent": "solmargintrader-meta-paper/1"}), timeout=10) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("source_response_too_large")
    values = json.loads(raw)
    if not isinstance(values, list):
        raise ValueError("invalid_source_response")  # noqa: TRY004 -- stable feed refusal contract
    rows = {}
    for row in values:
        if not isinstance(row, list) or len(row) != 6:
            raise ValueError("invalid_source_candle")
        ts, low, high, opened, closed, volume = map(float, row)
        if not math.isfinite(ts) or ts != int(ts) or ts % STEP:
            raise ValueError("invalid_source_timestamp")
        candle = (int(ts), opened, high, low, closed, volume)
        if int(ts) in rows and rows[int(ts)] != candle:
            raise ValueError("source_candle_changed")
        if ts + STEP <= now and (after is None or ts > after):
            rows[int(ts)] = candle
    if not rows:
        return None
    return validate_bar_arrays(arrays([rows[k] for k in sorted(rows)]), "1h")


class RecordedTarget:
    """The canonical accounting engine executes a previously issued target."""
    name = "meta_forward_recorded_target"

    def __init__(self, identity, source_bar, target):
        self.params = {"frozen_identity": identity}
        self.source_bar, self.target = source_bar, target

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return self.target if int(history.ts[-1]) == self.source_bar else 0.0

    def checkpoint_state(self):
        return {}

    def restore_state(self, state):
        if state != {}:
            raise ValueError("invalid_recorded_target_state")


def _signal(sleeve, history, holding=None):
    strategy = build(sleeve["strategy"], **sleeve.get("params", {}))
    first = strategy.warmup_bars() if holding is None else len(history["ts"]) - 1
    if first >= len(history["ts"]):
        raise ValueError("insufficient_signal_warmup")
    if holding is not None and hasattr(strategy, "_holding"):
        strategy._holding = holding
    target = 0.0
    for i in range(first, len(history["ts"])):
        target = float(strategy.on_bar(BarWindow(*(history[k] for k in KEYS), i)))
    if not math.isfinite(target) or not 0 <= target <= 1:
        raise ValueError("invalid_unlevered_paper_target")
    return target, bool(getattr(strategy, "_holding", False))


def _account(spec, histories, source_bar, previous=None):
    books, signals, targets, trades = {}, {}, {}, []
    equity = spec["capital"] * (1 - sum(x["weight"] for x in spec["sleeves"]))
    cash, fees, slippage, notional = equity, 0.0, 0.0, 0.0
    for sleeve in spec["sleeves"]:
        asset = sleeve["asset"]
        history = histories[asset]
        old = previous["books"][asset] if previous else None
        holding = previous["signals"][asset] if previous else None
        target, signals[asset] = _signal(sleeve, history, holding)
        targets[asset] = target
        inputs = {k: value[-1:] for k, value in history.items()} if old else history
        strategy = RecordedTarget(spec["id"] + ":" + asset, source_bar, target)
        config = EngineConfig(mode="spot", leverage=1, interval="1h", fill_delay=2,
                              initial_capital=spec["capital"] * sleeve["weight"], allow_short=False,
                              costs=CostConfig(fee_bps=spec["fee_bps"], slippage_bps=spec["slippage_bps"]))
        result = run_backtest(strategy, inputs, config, close_at_end=False, continuation=old)
        books[asset] = result.continuation
        value = float(result.equity[-1])
        equity += value
        cash += float(result.account.cash)
        fees += float(result.account.fees_paid)
        slippage += float(result.account.slippage_paid)
        notional += float(result.exposure[-1]) * value
        trades.extend({"asset": asset, **vars(t)} for t in result.trades)
    return {"books": books, "signals": signals}, targets, {
        "equity": equity, "cash": cash, "fees": fees, "slippage": slippage,
        "exposure": notional / equity if equity > 0 else 0.0,
        "estimated_net_liquidation_equity": equity - notional * (spec["fee_bps"] + spec["slippage_bps"]) / 10000,
    }, trades


def _metadata(db):
    return {r[0]: json.loads(r[1]) for r in db.execute("SELECT * FROM metadata")}


def _definition_valid(db, metadata):
    raw = metadata["config_bytes"].encode()
    specs = [json.loads(row[0]) for row in db.execute("SELECT spec FROM accounts ORDER BY id")]
    expected = sorted(metadata["config"]["accounts"], key=lambda item: item["id"])
    return (hashlib.sha256(raw).hexdigest() == metadata["config_sha256"]
            and json.loads(raw) == metadata["config"] and specs == expected)


def _block(home, reason):
    with connection(home, write=True) as db:
        db.execute("UPDATE cohort SET status='blocked',reason=?", (reason,))


def _confirm(home, effective, durable_at):
    with connection(home, write=True) as db:
        if durable_at >= effective:
            db.execute("UPDATE cohort SET status='blocked',reason='missed_decision_window'")
        else:
            db.execute("INSERT INTO confirmations VALUES(?,?)", (effective, durable_at))
            db.execute("UPDATE cohort SET status='running',reason=NULL")


def _boundary(value):
    if value is None:
        return None
    if type(value) is int:
        result = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.timestamp() != int(parsed.timestamp()):
            raise ValueError("seed_boundary_requires_explicit_timezone")
        result = int(parsed.timestamp())
    else:
        raise ValueError("invalid_seed_boundary")
    if not 0 < result < 10_000_000_000 or result % STEP:
        raise ValueError("seed_boundary_requires_hour_alignment")
    return result


def initialize(home, config=None, *, passive_zec_weight=None, seed_not_before=None, now=None, fetcher=fetch_closed, clock=time.time):
    now = clock() if now is None else now
    if config is not None and passive_zec_weight is not None:
        raise ValueError("file_config_cannot_be_overridden")
    raw = Path(config).read_bytes() if config is not None else canonical(default_config(passive_zec_weight)).encode()
    specs = validate_config(json.loads(raw))
    seed_not_before = _boundary(seed_not_before)
    required = max([2, *(build(s["strategy"], **s.get("params", {})).warmup_bars() + 1 for account in specs["accounts"] for s in account["sleeves"])])
    seeds = {asset: fetcher(asset, seed_not_before - STEP if seed_not_before is not None else None, now) for asset in ASSETS}
    for asset, seed in seeds.items():
        if seed is None:
            raise ValueError("complete_indicator_warmup_required")
        if seed_not_before is not None:
            # Only timestamps select the allowed prefix. Neither OHLC sanity
            # checks nor indicator priming inspect the protected earlier rows.
            keep = np.asarray(seed["ts"]) >= seed_not_before
            seed = {k: np.asarray(seed[k])[keep] for k in KEYS}
        if len(seed["ts"]) < required:
            raise ValueError("complete_indicator_warmup_required")
        seeds[asset] = validate_bar_arrays(seed, "1h")
    lasts = {int(a["ts"][-1]) for a in seeds.values()}
    if len(lasts) != 1:
        raise ValueError("source_calendar_mismatch")
    last = lasts.pop()
    if not last + STEP <= now < last + 2 * STEP:
        raise ValueError("seed_stale")
    path = _path(home)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with owner(home):
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with closing(sqlite3.connect(path)) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""
                CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE cohort(id INTEGER PRIMARY KEY CHECK(id=1),status TEXT,reason TEXT,last_ts INTEGER,activation INTEGER);
                CREATE TABLE candles(asset TEXT,bar INTEGER,open REAL,high REAL,low REAL,close REAL,volume REAL,observed REAL,PRIMARY KEY(asset,bar));
                CREATE TABLE accounts(id TEXT PRIMARY KEY,spec TEXT NOT NULL,state TEXT,equity REAL,cash REAL,fees REAL,slippage REAL,exposure REAL);
                CREATE TABLE decisions(source_bar INTEGER PRIMARY KEY,issued REAL,effective INTEGER UNIQUE,targets TEXT NOT NULL);
                CREATE TABLE confirmations(effective INTEGER PRIMARY KEY,durable_at REAL NOT NULL,FOREIGN KEY(effective) REFERENCES decisions(effective),CHECK(durable_at<effective));
                CREATE TABLE snapshots(bar INTEGER,id TEXT,observed REAL,metrics TEXT,PRIMARY KEY(bar,id));
                CREATE TABLE trades(seq INTEGER PRIMARY KEY,id TEXT,bar INTEGER,details TEXT NOT NULL);
                CREATE TRIGGER immutable_metadata_update BEFORE UPDATE ON metadata BEGIN SELECT RAISE(ABORT,'immutable_paper_metadata'); END;
                CREATE TRIGGER immutable_metadata_delete BEFORE DELETE ON metadata BEGIN SELECT RAISE(ABORT,'immutable_paper_metadata'); END;
                CREATE TRIGGER immutable_decision_update BEFORE UPDATE ON decisions BEGIN SELECT RAISE(ABORT,'immutable_paper_decision'); END;
                CREATE TRIGGER immutable_decision_delete BEFORE DELETE ON decisions BEGIN SELECT RAISE(ABORT,'immutable_paper_decision'); END;
                CREATE TRIGGER immutable_confirmation_update BEFORE UPDATE ON confirmations BEGIN SELECT RAISE(ABORT,'immutable_paper_confirmation'); END;
                CREATE TRIGGER immutable_confirmation_delete BEFORE DELETE ON confirmations BEGIN SELECT RAISE(ABORT,'immutable_paper_confirmation'); END;
                CREATE TRIGGER immutable_candle_update BEFORE UPDATE ON candles BEGIN SELECT RAISE(ABORT,'immutable_paper_candle'); END;
                CREATE TRIGGER immutable_candle_delete BEFORE DELETE ON candles BEGIN SELECT RAISE(ABORT,'immutable_paper_candle'); END;
                CREATE TRIGGER immutable_account_spec BEFORE UPDATE OF id,spec ON accounts BEGIN SELECT RAISE(ABORT,'immutable_paper_account_spec'); END;
                CREATE TRIGGER immutable_account_delete BEFORE DELETE ON accounts BEGIN SELECT RAISE(ABORT,'immutable_paper_account_spec'); END;
            """)
            db.execute(f"PRAGMA application_id={APP_ID}")
            for key, value in {"prepared_at": clock(), "implementation": implementation(), "config": specs,
                               "config_bytes": raw.decode(), "config_sha256": hashlib.sha256(raw).hexdigest(),
                               "seed_not_before": seed_not_before,
                               "seed_bounds": {a: {"first": int(s["ts"][0]), "last": int(s["ts"][-1]), "bars": len(s["ts"])} for a, s in seeds.items()},
                               "source": "Coinbase Exchange public native USD1h; reference paper fills",
                               "execution": "Unlevered long/flat; two-bar target delay; no queue/nonfill model"}.items():
                db.execute("INSERT INTO metadata VALUES(?,?)", (key, canonical(value)))
            db.execute("INSERT INTO cohort VALUES(1,'prepared',NULL,?,NULL)", (last,))
            for asset, seed in seeds.items():
                db.executemany("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)", [(asset, *row, now) for row in zip(*(seed[k].tolist() for k in KEYS))])
            for spec in specs["accounts"]:
                db.execute("INSERT INTO accounts VALUES(?,?,NULL,?,?,0,0,0)", (spec["id"], canonical(spec), spec["capital"], spec["capital"]))
            db.commit()
    return report(home, now=now)


def _histories(db):
    result = {}
    for asset in ASSETS:
        rows = db.execute("SELECT bar,open,high,low,close,volume FROM candles WHERE asset=? ORDER BY bar", (asset,)).fetchall()
        if len(rows) > MAX_BARS:
            raise ValueError("observation_limit")
        result[asset] = validate_bar_arrays(arrays(rows), "1h")
    return result


def _advance(db, histories, clock, *, activating=False):
    source_bar = int(next(iter(histories.values()))["ts"][-1])
    effective = source_bar + 2 * STEP
    if clock() >= effective:
        raise ValueError("missed_decision_window")
    targets = {}
    for row in db.execute("SELECT * FROM accounts ORDER BY id").fetchall():
        spec = json.loads(row["spec"])
        previous = None if activating else json.loads(row["state"])
        state, targets[spec["id"]], metrics, trades = _account(spec, histories, source_bar, previous)
        db.execute("UPDATE accounts SET state=?,equity=?,cash=?,fees=?,slippage=?,exposure=? WHERE id=?",
                   (canonical(state), *(metrics[k] for k in ("equity", "cash", "fees", "slippage", "exposure")), spec["id"]))
        if not activating:
            db.execute("INSERT INTO snapshots VALUES(?,?,?,?)", (source_bar, spec["id"], clock(), canonical(metrics)))
        for trade in trades:
            record = {**trade, "reference_only": True, "observed_at": clock()}
            db.execute("INSERT INTO trades(id,bar,details) VALUES(?,?,?)", (spec["id"], source_bar, canonical(record)))
    if clock() >= effective:
        raise ValueError("missed_decision_window")
    document = {"targets": targets, "completed_bar_marks": {a: float(h["close"][-1]) for a, h in histories.items()}, "reference_only": True}
    db.execute("INSERT INTO decisions VALUES(?,?,?,?)", (source_bar, clock(), effective, canonical(document)))
    db.execute("UPDATE cohort SET status='awaiting_confirmation',reason='decision_not_yet_durable',last_ts=?", (source_bar,))
    return effective


def activate(home, *, now=None, clock=time.time):
    now = clock() if now is None else now
    with owner(home):
        with connection(home, write=True) as db:
            cohort = db.execute("SELECT * FROM cohort").fetchone()
            if cohort["status"] != "prepared":
                raise ValueError("cohort_already_activated_or_blocked")
            metadata = _metadata(db)
            if metadata["implementation"] != implementation():
                raise ValueError("implementation_changed")
            if not _definition_valid(db, metadata):
                raise ValueError("configuration_changed")
            if not cohort["last_ts"] + STEP <= now < cohort["last_ts"] + 2 * STEP:
                raise ValueError("prepared_seed_stale")
            effective = _advance(db, _histories(db), clock, activating=True)
            db.execute("UPDATE cohort SET activation=?", (effective,))
        _confirm(home, effective, clock())
    return report(home, now=now)


def _tick(home, *, now=None, fetcher=fetch_closed, clock=time.time):
    now = clock() if now is None else now
    with connection(home) as db:
        cohort = dict(db.execute("SELECT * FROM cohort").fetchone())
        metadata = _metadata(db)
        expected = metadata["implementation"]
        valid = _definition_valid(db, metadata)
        unconfirmed = db.execute("SELECT count(*) FROM decisions d LEFT JOIN confirmations c ON c.effective=d.effective WHERE c.effective IS NULL").fetchone()[0]
    if cohort["status"] in ("prepared", "blocked"):
        return report(home, now=now)
    if expected != implementation():
        _block(home, "implementation_changed")
        return report(home, now=now)
    if not valid:
        _block(home, "configuration_changed")
        return report(home, now=now)
    if unconfirmed:
        _block(home, "unconfirmed_decision")
        return report(home, now=now)
    last = cohort["last_ts"]
    if now < last + 2 * STEP + 3:
        return report(home, now=now)
    try:
        fetched = {asset: fetcher(asset, last - STEP, now) for asset in ASSETS}
        with connection(home, write=True) as db:
            if db.execute("SELECT last_ts FROM cohort").fetchone()[0] != last:
                raise ValueError("concurrent_paper_writer")
            for asset, data in fetched.items():
                if data is None:
                    raise ValueError("closed_candle_unavailable")
                data = validate_bar_arrays(data, "1h")
                previous = db.execute("SELECT open,high,low,close,volume FROM candles WHERE asset=? AND bar=?", (asset, last)).fetchone()
                old = np.flatnonzero(data["ts"] == last)
                if len(old) and [float(data[k][old[0]]) for k in KEYS[1:]] != list(previous):
                    raise ValueError("source_candle_changed")
                fresh = np.flatnonzero(data["ts"] > last)
                if len(fresh) != 1 or int(data["ts"][fresh[0]]) != last + STEP:
                    raise ValueError("missed_decision_window")
                bar = last + STEP
                if not bar + STEP <= clock() < bar + 2 * STEP:
                    raise ValueError("missed_decision_window")
                values = [float(data[k][fresh[0]]) for k in KEYS[1:]]
                db.execute("INSERT INTO candles VALUES(?,?,?,?,?,?,?,?)", (asset, bar, *values, clock()))
            # A confirmed decision must already authorize the current candle if
            # its open can carry exposure. Pending engine targets cannot bypass it.
            bar = last + STEP
            if bar >= cohort["activation"] and db.execute("SELECT 1 FROM confirmations WHERE effective=? AND durable_at<?", (bar, bar)).fetchone() is None:
                raise ValueError("unconfirmed_decision")
            effective = _advance(db, _histories(db), clock)
        _confirm(home, effective, clock())
    except (OSError, TimeoutError, ValueError, TypeError) as exc:
        transient = isinstance(exc, (OSError, TimeoutError)) or str(exc) == "closed_candle_unavailable"
        if transient and clock() < last + 3 * STEP:
            with connection(home, write=True) as db:
                db.execute("UPDATE cohort SET reason='feed_temporarily_unavailable'")
        else:
            _block(home, str(exc) if isinstance(exc, ValueError) else "feed_failed")
    return report(home, now=now)


def tick(home, **kwargs):
    with owner(home):
        return _tick(home, **kwargs)


def report(home, *, now=None):
    now = time.time() if now is None else now
    with connection(home) as db:
        metadata = _metadata(db)
        definition_valid = _definition_valid(db, metadata)
        cohort = dict(db.execute("SELECT * FROM cohort").fetchone())
        accounts = []
        for row in db.execute("SELECT id,spec,equity,cash,fees,slippage,exposure FROM accounts ORDER BY id"):
            value = dict(row)
            value["spec"] = json.loads(value["spec"])
            value["reference_return_pct"] = (value["equity"] / value["spec"]["capital"] - 1) * 100
            exit_cost = value["equity"] * value["exposure"] * (value["spec"]["fee_bps"] + value["spec"]["slippage_bps"]) / 10000
            value["estimated_net_liquidation_equity"] = value["equity"] - exit_cost
            value["estimated_net_liquidation_return_pct"] = (value["estimated_net_liquidation_equity"] / value["spec"]["capital"] - 1) * 100
            value["fills"] = db.execute("SELECT count(*) FROM trades WHERE id=?", (value["id"],)).fetchone()[0]
            accounts.append(value)
        counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("decisions", "confirmations", "snapshots", "trades")}
        latest = db.execute("SELECT d.source_bar,d.issued,d.effective,d.targets,c.durable_at FROM decisions d LEFT JOIN confirmations c ON c.effective=d.effective ORDER BY d.source_bar DESC LIMIT 1").fetchone()
        decision = {"source_bar": latest[0], "issued_at": latest[1], "effective": latest[2], "document": json.loads(latest[3]), "durable_at": latest[4]} if latest else None
    return {"schema_version": 1, "paper_only": True, "as_of": now, "source": metadata["source"],
            "execution": metadata["execution"], "config_sha256": metadata["config_sha256"], "configuration_valid": definition_valid,
            "seed_not_before": metadata["seed_not_before"], "seed_bounds": metadata["seed_bounds"],
            "cohort": cohort, "stale": now >= cohort["last_ts"] + 3 * STEP,
            "counts": counts, "accounts": accounts, "latest_decision": decision,
            "qualification": "prospective reference accounting; no live fills or profitability certification"}


def run(home, poll=15):
    stop = False
    def terminate(*_):
        nonlocal stop
        stop = True
    with owner(home):
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, terminate)
        while not stop:
            try:
                value = _tick(home)
                print(canonical({"paper_only": True, "at": value["as_of"], "cohort": value["cohort"], "counts": value["counts"]}), flush=True)
            except (OSError, ValueError, sqlite3.Error):
                print(canonical({"paper_only": True, "status": "blocked", "reason": "paper_store_failed"}), flush=True)
            until = time.monotonic() + poll
            while not stop and time.monotonic() < until:
                time.sleep(max(0, min(1, until - time.monotonic())))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", required=True, type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    init.add_argument("--config", type=Path)
    init.add_argument("--passive-zec-weight", type=float)
    init.add_argument("--seed-not-before", help="ISO8601 UTC/timezone boundary; exclude earlier warmup before all feature access")
    commands.add_parser("activate")
    commands.add_parser("tick")
    commands.add_parser("run")
    commands.add_parser("status")
    args = parser.parse_args(argv)
    if args.command == "run":
        return run(args.home)
    if args.command == "init":
        value = initialize(args.home, args.config, passive_zec_weight=args.passive_zec_weight, seed_not_before=args.seed_not_before)
    elif args.command == "activate":
        value = activate(args.home)
    elif args.command == "tick":
        value = tick(args.home)
    else:
        value = report(args.home)
    print(canonical(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

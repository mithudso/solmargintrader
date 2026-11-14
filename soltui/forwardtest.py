"""Prospective, paper-only trials of registered strategies on closed Coinbase minutes."""

from __future__ import annotations

import hashlib
import fcntl
import inspect
import json
import math
import os
import sqlite3
import time
import tempfile
from collections.abc import Callable
from contextlib import closing
from itertools import pairwise
from pathlib import Path
from threading import Event
from typing import Any

import numpy as np

from backtester.core import scorecard
from backtester.core.strategies import REGISTRY, build, build_composite
from backtester.core.types import INTERVAL_SECONDS, BarWindow, validate_bar_arrays

from . import compound, config, simulation
from .research_admission import admit_read, participating
from .source_epoch import SourceEpoch

_SOURCE_ROOT = Path(__file__).resolve().parents[1]
_SOURCE_EPOCH = SourceEpoch.capture(_SOURCE_ROOT)

HORIZONS = (1, 5, 10, 30)
HISTORY = 600
WARM_REPLAY = 128
KNOBS = scorecard.default_config()["aggregate"]
Spec = list[dict[str, Any]]


def revision() -> str:
    """Partition evidence if strategy code or the forecast/scoring contract changes."""
    _SOURCE_EPOCH.verify(_SOURCE_ROOT)
    return _disk_revision()


def _disk_revision() -> str:
    """Hash source bytes only; this does not attest loaded or historical code."""
    core = Path(scorecard.__file__).parent
    files = [Path(__file__), Path(compound.__file__), Path(simulation.__file__), *sorted(core.glob("*.py")),
             *sorted((core / "strategies").glob("*.py"))]
    return hashlib.sha256(b"".join(hashlib.sha256(p.read_bytes()).digest() for p in files)).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


_MIGRATIONS = {
    "trial": {"execution": "TEXT DEFAULT ''"},
    "call": {"confidence": "REAL", "traded": "INTEGER", "net_return": "REAL",
             "fees_bps": "REAL", "borrow_bps": "REAL", "slippage_bps": "REAL",
             "liquidated": "INTEGER"},
}


def _schema_current(db: sqlite3.Connection) -> bool:
    objects = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type IN ('table','index')")}
    if not {"candle", "session", "trial", "call", "adoption", "default_export", "call_pending", "call_training"} <= objects:
        return False
    return all(set(columns) <= {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
               for table, columns in _MIGRATIONS.items())


def _db(path: Path | None = None) -> sqlite3.Connection:
    """Open a writer, initializing journal mode and schema only when needed."""
    path = path or config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        # Writers establish WAL before opening a transaction. Readers never run
        # this initializer or request a journal-mode change.
        if db.execute("PRAGMA journal_mode").fetchone()[0].lower() != "wal":
            db.execute("PRAGMA journal_mode=WAL").fetchone()
        if _schema_current(db):
            return db
        db.execute("BEGIN IMMEDIATE")
        for statement in ("""
        CREATE TABLE IF NOT EXISTS candle (
            asset TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY(asset, ts)
        )""", """
        CREATE TABLE IF NOT EXISTS session (id INTEGER PRIMARY KEY CHECK(id=1), plan TEXT NOT NULL)
        """, """CREATE TABLE IF NOT EXISTS trial (
            id TEXT PRIMARY KEY, asset TEXT, label TEXT, mode TEXT, minutes INTEGER,
            cost REAL, active TEXT, generation INTEGER DEFAULT 0, moved INTEGER DEFAULT 0,
            note TEXT DEFAULT ''
        )""", """CREATE TABLE IF NOT EXISTS call (
            trial TEXT, bar INTEGER, issued REAL, start INTEGER, finish INTEGER,
            generation INTEGER, guesses TEXT, prediction INTEGER, outcome INTEGER,
            bps REAL, expired INTEGER DEFAULT 0, PRIMARY KEY(trial, bar)
        )""", """CREATE INDEX IF NOT EXISTS call_pending ON call(trial, finish)
            WHERE outcome IS NULL AND expired = 0
        """, """CREATE INDEX IF NOT EXISTS call_training ON call(trial, generation, bar)
            WHERE outcome IS NOT NULL
        """, """CREATE TABLE IF NOT EXISTS adoption (
            trial TEXT, at INTEGER, previous TEXT, next TEXT, confidence REAL,
            samples INTEGER, PRIMARY KEY(trial, at)
        )""", """CREATE TABLE IF NOT EXISTS default_export (
            trial TEXT, at INTEGER, document TEXT NOT NULL, PRIMARY KEY(trial, at)
        )"""):
            db.execute(statement)
        # Recheck under the migration lock: another writer may have migrated
        # between the initial schema read and BEGIN IMMEDIATE.
        for table, columns in _MIGRATIONS.items():
            existing = {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
            for column, declaration in columns.items():
                if column not in existing:
                    db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        db.commit()
    except BaseException:
        db.close()
        raise
    return db


def save_session(plan: dict | None) -> None:
    """Atomically persist the running plan alongside its evidence."""
    with closing(_db()) as db, db:
        if plan is None:
            db.execute("DELETE FROM session WHERE id=1")
        else:
            db.execute("INSERT OR REPLACE INTO session(id,plan) VALUES(1,?)", (_json(plan),))


def load_session() -> dict | None:
    path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    if not path.exists():
        return None
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        # A legacy evidence database can predate saved sessions. A status read
        # must not migrate it or contend for the active forward writer.
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='session'").fetchone() is None:
            return None
        row = db.execute("SELECT plan FROM session WHERE id=1").fetchone()
    if not row:
        return None
    plan = json.loads(row[0])
    plan["horizons"] = tuple(plan["horizons"])
    return plan


# -- saved defaults: a setting that tested superior becomes the trial's starting point -------------
#
# An adoption already needs a neighbour to beat the active setting on paired, resolved calls with
# posterior probability above `tune_confidence` (Compound's Beta comparison). When that happens with
# auto-optimize on, the adopted setting is also saved here, keyed by coin, trial label and horizon,
# so the next forward test of that trial starts from it even after a code revision partitions the
# evidence into new trial rows. The roster and the Signals defaults are not touched: a forward
# adoption at one horizon on one coin is not evidence for every other use of the strategy.


def defaults_path() -> Path:
    return config.CONFIG_DIR / "forwardtest" / "defaults.json"


def _default_key(asset: str, label: str, minutes: int) -> str:
    return f"{asset}|{label}|{int(minutes)}"


def load_defaults() -> dict[str, dict[str, Any]]:
    try:
        raw = json.loads(defaults_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return raw if isinstance(raw, dict) else {}


def save_default(asset: str, label: str, minutes: int, spec: Spec, previous: Spec, *,
                 probability: float, samples: int, bar: int) -> None:
    path = defaults_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.with_name(path.name + ".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = load_defaults()
        data[_default_key(asset, label, minutes)] = {
            "members": spec, "previous": previous, "probability": probability, "samples": samples,
            "bar": bar, "saved_at": time.time()}
        fd, name = tempfile.mkstemp(prefix=".defaults-", dir=path.parent)
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(json.dumps(data, indent=1, sort_keys=True, allow_nan=False))
                handle.flush()
                os.fsync(handle.fileno())
            tmp.replace(path)
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            tmp.unlink(missing_ok=True)


def _export_committed_defaults(db_path: Path | None) -> None:
    """Retry committed exports; a failed export remains durable for the next tick."""
    with closing(_db(db_path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for key, at, raw in db.execute("SELECT trial,at,document FROM default_export ORDER BY at,trial").fetchall():
            save_default(**json.loads(raw))
            db.execute("DELETE FROM default_export WHERE trial=? AND at=?", (key, at))


def saved_default(asset: str, label: str, minutes: int, defaults: dict | None = None) -> Spec | None:
    row = (load_defaults() if defaults is None else defaults).get(_default_key(asset, label, minutes))
    return row["members"] if isinstance(row, dict) and isinstance(row.get("members"), list) else None


def _usable_default(saved: Spec | None, seed: Spec, mode: str) -> Spec:
    """The saved default when it is a parameter variant of the same members that still builds; else the seed.

    A default naming other strategies, or a parameter the member does not take, is ignored rather
    than trusted: the file is plain JSON a person (or an older revision) may have written.
    """
    if not saved or len(saved) != len(seed):
        return seed
    for got, want in zip(saved, seed):
        if (not isinstance(got, dict) or got.get("name") != want["name"]
                or not isinstance(got.get("params"), dict) or set(got["params"]) - set(want["params"])):
            return seed
    try:
        _factory(saved, mode)
    except (ValueError, TypeError, OverflowError, KeyError):
        return seed
    return saved


def _factory(spec: Spec, mode: str):
    if len(spec) == 1:
        return build(spec[0]["name"], **spec[0]["params"])
    return build_composite([(m["name"], m["params"]) for m in spec], mode=mode)


def member(name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Fill constructor defaults so untweaked numeric parameters are eligible too."""
    if name.startswith("lev_"):
        wrapped = build(name, **params)
        return member(wrapped.base, json.loads(wrapped.params["base_params"] or "{}"))
    sig = inspect.signature(REGISTRY[name])
    bound = sig.bind_partial(**params)
    bound.apply_defaults()
    build(name, **params)
    return {"name": name, "params": dict(bound.arguments)}


def neighbours(spec: Spec, mode: str) -> list[Spec]:
    """A move changes one numeric parameter on one member. Constructor checks still apply."""
    out = [spec]
    for i, m in enumerate(spec):
        for key, value in sorted(m["params"].items()):
            # Leverage controls execution, not the forecast. Boolean flags are not numeric knobs.
            if type(value) not in (int, float) or not value or key in {"leverage", "direction"}:
                continue
            for sign in (-1, 1):
                v = value * (1 + sign * KNOBS["tune_step"])
                if type(value) is int:
                    v = round(v)
                    if v == value:
                        v += sign
                if value > 0 and v <= 0:
                    continue
                cand = [*spec]
                cand[i] = {**m, "params": {**m["params"], key: v}}
                try:
                    _factory(cand, mode)
                except (ValueError, TypeError, OverflowError):
                    continue
                if cand not in out:
                    out.append(cand)
    return out


def _predict(spec: Spec, mode: str, bars: dict[str, np.ndarray], *, allow_short: bool = False) -> int | None:
    strategy = simulation.prepare_strategy(_factory(spec, mode), allow_short)
    n = len(bars["ts"])
    warm = int(strategy.warmup_bars())
    if n <= warm:
        return None
    # Give stateful rules the same replay policy for the active and shadow settings.
    start = max(0, n - warm - WARM_REPLAY)
    arrays = [bars[k][start:] for k in ("ts", "open", "high", "low", "close", "volume")]
    for i in range(warm, len(arrays[0])):
        value = float(strategy.on_bar(BarWindow(*arrays, i)))
    if not math.isfinite(value):
        return None
    return int(value > 0) - int(value < 0)


def _choose(history: list[tuple], corrected: list, current: Spec) -> tuple | None:
    """Only a neighbor that fixed the newest miss can move, using paired prior calls."""
    best = None
    rows = [(start, finish, actual, {_json(spec): call for spec, call in guesses})
            for start, finish, actual, guesses in history]
    active_key = _json(current)
    for candidate, _ in corrected:
        if candidate == current:
            continue
        hits = [0, 0]
        samples = 0
        end = 0
        candidate_key = _json(candidate)
        for start, finish, actual, calls in rows:
            if start < end:
                continue
            a, b = calls.get(active_key), calls.get(candidate_key)
            if a is None or b is None:
                continue
            end = finish
            samples += 1
            hits[0] += a == actual
            hits[1] += b == actual
        if samples < KNOBS["tune_min_calls"]:
            continue
        means, variances = scorecard.beta_posterior(
            np.array(hits), np.full(2, samples), KNOBS["adaptive_prior"])
        probability = float(scorecard.p_better_than(means[1], variances[1], means[0], variances[0]))
        if probability > KNOBS["tune_confidence"] and (best is None or probability > best[1]):
            best = candidate, probability, samples
    return best


def _resolve(db: sqlite3.Connection, key: str, generation: int, active: Spec, moved: int,
             cost: float, candles: dict[int, tuple[float, float]], bar: int, minutes: int, tune: bool,
             on_adopt: Callable[[Spec, Spec, float, int], None] | None = None,
             expire_missing: bool = True, execution: dict | None = None) -> tuple[Spec, int]:
    misses: list = []
    latest = None
    for origin, start, finish, gen, raw, prediction in db.execute(
        """SELECT bar,start,finish,generation,guesses,prediction FROM call
           WHERE trial=? AND outcome IS NULL AND expired=0 AND finish<=? ORDER BY bar""",
        (key, bar + 60),
    ).fetchall():
        if not all(t in candles for t in range(start, finish, 60)):
            if expire_missing and start < min(candles):
                db.execute("UPDATE call SET expired=1 WHERE trial=? AND bar=?", (key, origin))
            continue
        bps = 10000 * math.log(candles[finish - 60][1] / candles[start][0])
        outcome = int(bps > cost) - int(bps < -cost)
        db.execute("UPDATE call SET outcome=?,bps=? WHERE trial=? AND bar=?", (outcome, bps, key, origin))
        if execution:
            profile = simulation.Execution(**execution)
            trade = db.execute("SELECT traded FROM call WHERE trial=? AND bar=?", (key, origin)).fetchone()[0]
            if trade:
                prices = db.execute("""SELECT open,high,low,close FROM candle WHERE asset=
                    (SELECT asset FROM trial WHERE id=?) AND ts>=? AND ts<? ORDER BY ts""",
                    (key, start, finish)).fetchall()
                if len(prices) != minutes:
                    raise ValueError("Missing retained OHLC candles for paper settlement")
                result = simulation.settle(profile, prediction, prices)
            else:
                result = {"net_return": 0.0, "fees_bps": 0.0, "borrow_bps": 0.0, "slippage_bps": 0.0, "liquidated": 0}
            db.execute("""UPDATE call SET net_return=:net_return,fees_bps=:fees_bps,
                borrow_bps=:borrow_bps,slippage_bps=:slippage_bps,liquidated=:liquidated
                WHERE trial=:trial AND bar=:bar""", dict(result, trial=key, bar=origin))
        if gen == generation:
            latest = origin
            misses = [(s, p) for s, p in json.loads(raw) if p == outcome] if outcome != prediction else []
    if not tune or latest is None or not misses or bar - moved < KNOBS["tune_cooldown"] * 300:
        return active, generation
    history = [(s, f, y, json.loads(g)) for s, f, y, g in db.execute(
        """SELECT start,finish,outcome,guesses FROM call
           WHERE trial=? AND generation=? AND outcome IS NOT NULL AND bar BETWEEN ? AND ?
           ORDER BY bar""", (key, generation, bar - KNOBS["adaptive_window"] * minutes * 60, latest))]
    choice = _choose(history, misses, active)
    if choice is None:
        return active, generation
    next_spec, probability, samples = choice
    db.execute("INSERT INTO adoption VALUES (?,?,?,?,?,?)",
               (key, bar, _json(active), _json(next_spec), probability, samples))
    db.execute("UPDATE trial SET active=?, generation=?, moved=? WHERE id=?",
               (_json(next_spec), generation + 1, bar, key))
    if on_adopt is not None:
        on_adopt(next_spec, active, probability, samples)
    return next_spec, generation + 1


@participating
def tick(asset: str, trials: list[dict], horizons: tuple[int, ...], cost: float, *,
         fetch: Callable | None = None, clock: Callable[[], float] = time.time,
         stop: Event | None = None, code: str | None = None, tune: bool = True,
         db_path: Path | None = None, history: int = HISTORY,
         signal_interval: str = "1m", signal_fetch: Callable | None = None,
         expire_missing: bool = True, execution: dict | None = None) -> dict:
    """Record only fresh calls, resolving past calls before computing the next forecast.

    With `tune` (auto-optimize) a trial whose newest call missed may move to a neighbouring
    setting that tested superior on paired calls, and that setting is saved as the trial's
    default (`save_default`). Without it settings stay fixed; calls are still recorded and scored.
    """
    _SOURCE_EPOCH.verify(_SOURCE_ROOT)
    profile = simulation.Execution(**execution) if execution else None
    fetch = fetch or compound.fetch_closed_candles
    stop = stop if stop is not None else Event()
    def check_stop() -> None:
        if stop.is_set():
            raise RuntimeError("Forwardtest stopped")

    def get(url: str):
        check_stop()
        return compound.http_json(url)

    check_stop()
    code = code or revision()
    observed = clock()
    admit_read(
        asset,
        source="forward:" + str(db_path or config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"),
        end=observed,
        attempts=len(trials) if tune else 0,
    )
    raw = fetch(asset, now=observed, bars=max(HISTORY, history), seconds=60, get=get, sleep=stop.wait)
    check_stop()
    mask = raw["ts"] + 60 <= observed
    raw = {k: v[mask] for k, v in raw.items()}
    ts = raw["ts"]
    if len(ts) == 0 or np.any(np.diff(ts) <= 0) or np.any(ts % 60):
        raise ValueError("No ordered closed one-minute candles")
    # Validate every received segment before persistence, including old rows
    # outside the latest contiguous signal segment. Gaps remain real gaps.
    breaks = np.flatnonzero(np.diff(ts) != 60)
    boundaries = [0, *(int(i) + 1 for i in breaks), len(ts)]
    for first, last in pairwise(boundaries):
        validate_bar_arrays({k: v[first:last] for k, v in raw.items()}, "1m")
    rows = [(asset, int(t), float(o), float(h), float(l), float(c), float(v))
            for t, o, h, l, c, v in zip(*(raw[k] for k in
                ("ts", "open", "high", "low", "close", "volume")), strict=True)]
    # Existing valid observations stay immutable. A malformed legacy row can
    # be replaced only by a newly validated candle for that exact asset/time.
    retained = []
    _SOURCE_EPOCH.verify(_SOURCE_ROOT)
    with closing(_db(db_path)) as db, db:
        for row in rows:
            old = db.execute("SELECT open,high,low,close,volume FROM candle WHERE asset=? AND ts=?",
                             row[:2]).fetchone()
            if old is not None:
                o, h, low, c, v = old
                valid = (all(isinstance(x, (int, float)) and math.isfinite(x) for x in old)
                         and min(o, h, low, c) > 0 and v >= 0
                         and h >= low and h >= max(o, c) - 1e-9 and low <= min(o, c) + 1e-9)
                if valid:
                    retained.append((row[1], *old))
                    continue
                db.execute("DELETE FROM candle WHERE asset=? AND ts=?", row[:2])
            db.execute("INSERT INTO candle VALUES (?,?,?,?,?,?,?)", row)
            retained.append(row[1:])
    # Forecasts and directional settlement must use the same immutable snapshot
    # that paper execution later reads, even if a provider revises an old candle.
    raw = {name: np.asarray([row[index] for row in retained],
                           dtype="int64" if name == "ts" else "float64")
           for index, name in enumerate(("ts", "open", "high", "low", "close", "volume"))}
    ts = raw["ts"]
    # Keep gaps visible for settlement. The signal itself sees only the latest contiguous segment.
    candles = {int(t): (float(o), float(c)) for t, o, c in zip(ts, raw["open"], raw["close"], strict=True)
               if math.isfinite(o) and math.isfinite(c) and o > 0 and c > 0}
    if not candles:
        raise ValueError("No valid one-minute prices")
    breaks = np.flatnonzero(np.diff(ts) != 60)
    tail = int(breaks[-1] + 1) if len(breaks) else 0
    bars = validate_bar_arrays({k: v[tail:] for k, v in raw.items()}, "1m")
    if signal_interval not in INTERVAL_SECONDS:
        raise ValueError("unsupported signal candle interval")
    if signal_interval != "1m":
        seconds = INTERVAL_SECONDS[signal_interval]
        signal_raw = (signal_fetch or fetch)(asset, now=observed, bars=HISTORY, seconds=seconds,
                                            get=get, sleep=stop.wait)
        check_stop()
        signal_mask = signal_raw["ts"] + seconds <= observed
        signal_raw = {k: v[signal_mask] for k, v in signal_raw.items()}
        st = signal_raw["ts"]
        if not len(st) or np.any(np.diff(st) <= 0) or int(st[-1]) != (int(observed) // seconds - 1) * seconds:
            raise ValueError(f"No current closed {signal_interval} signal candle")
        breaks = np.flatnonzero(np.diff(st) != seconds)
        tail_signal = int(breaks[-1] + 1) if len(breaks) else 0
        bars = validate_bar_arrays({k: v[tail_signal:] for k, v in signal_raw.items()}, signal_interval)
    bar = int(ts[-1])
    start = bar + 120  # next minute that has not opened yet
    forecasts: dict[tuple, int | None] = {}
    staged = []
    pending_windows = 0
    due_trials = 0
    active_keys = {}
    _export_committed_defaults(db_path)
    defaults = load_defaults()
    _SOURCE_EPOCH.verify(_SOURCE_ROOT)
    with closing(_db(db_path)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        for trial in trials:
            seed, mode, label = trial["members"], trial["mode"], trial["label"]
            for h in horizons:
                # The key stays the configured seed; a saved default only sets where a new trial starts.
                trial_cost = (profile.round_trip_bps + max(profile.borrow_long_bps_hour,
                              profile.borrow_short_bps_hour) * h / 60) if profile else cost
                # A period counts signal bars. Minute and five-minute inputs
                # cannot share a track record even when the label/settings match.
                identity = [code, asset, label, h, trial_cost, mode, seed, signal_interval]
                if execution:
                    identity.append(execution)
                key = hashlib.sha256(_json(identity).encode()).hexdigest()
                active_keys[key] = h
                start_spec = _usable_default(saved_default(asset, label, h, defaults), seed, mode)
                db.execute("INSERT OR IGNORE INTO trial(id,asset,label,mode,minutes,cost,active,execution) VALUES (?,?,?,?,?,?,?,?)",
                           (key, asset, label, mode, h, trial_cost, _json(start_spec), _json(execution) if execution else ""))
        # Settle all existing trials for the asset, including a horizon no longer selected.
        for key, raw_spec, mode, gen, moved, h, trial_cost, label, raw_execution in db.execute(
            "SELECT id,active,mode,generation,moved,minutes,cost,label,execution FROM trial WHERE asset=?", (asset,)
        ).fetchall():
            check_stop()

            def adopt(spec: Spec, previous: Spec, probability: float, samples: int,
                      label: str = label, h: int = h, key: str = key) -> None:
                _SOURCE_EPOCH.verify(_SOURCE_ROOT)
                document = dict(asset=asset, label=label, minutes=h, spec=spec, previous=previous,
                                probability=probability, samples=samples, bar=bar)
                db.execute("INSERT OR REPLACE INTO default_export VALUES (?,?,?)", (key, bar, _json(document)))

            active, gen = _resolve(db, key, gen, json.loads(raw_spec), moved, trial_cost, candles, bar,
                                   h, tune and key in active_keys, adopt, expire_missing=expire_missing,
                                   execution=json.loads(raw_execution) if raw_execution else None)
            if key not in active_keys or not bar + 60 <= observed < start:
                continue
            previous = db.execute("SELECT finish FROM call WHERE trial=? ORDER BY bar DESC LIMIT 1",
                                  (key,)).fetchone()
            # One call per non-overlapping window. A 30m move is one observation, not 30.
            if previous and start < previous[0]:
                pending_windows += 1
                continue
            due_trials += 1
            guesses = []
            note = ""
            for spec in (neighbours(active, mode) if tune else [active]):
                check_stop()
                ck = mode, _json(spec)
                try:
                    if ck not in forecasts:
                        forecasts[ck] = (_predict(spec, mode, bars, allow_short=True)
                                         if profile and profile.allow_short else _predict(spec, mode, bars))
                    call = forecasts[ck]
                except (ValueError, RuntimeError, TypeError, ArithmeticError) as exc:
                    if spec == active:
                        note = str(exc)
                    call = None
                guesses.append((spec, call))
            prediction = guesses[0][1]
            if prediction is None:
                note = note or "Waiting for contiguous warm-up bars"
            else:
                prior = db.execute("""SELECT prediction=outcome FROM call WHERE trial=? AND generation=?
                    AND outcome IS NOT NULL AND prediction!=0 AND finish<=? ORDER BY bar DESC LIMIT ?""",
                    (key, gen, start, simulation.CONFIDENCE_WINDOW)).fetchall()
                confidence = simulation.confidence_score(sum(r[0] for r in prior), len(prior))
                wiped_out = db.execute("""SELECT 1 FROM call WHERE trial=? AND net_return<=-1
                    AND finish<=? LIMIT 1""", (key, bar + 60)).fetchone()
                traded = int(profile.permits(prediction, confidence) and not wiped_out) if profile else None
                staged.append((key, bar, start, start + h * 60, gen, _json(guesses), prediction,
                               confidence, traded))
            db.execute("UPDATE trial SET note=? WHERE id=?", (note, key))
        check_stop()
        _SOURCE_EPOCH.verify(_SOURCE_ROOT)
        issued = clock()
        # The issuance deadline applies only to a calculated call. A poll that
        # merely checks an existing long window can cross a minute boundary
        # without missing any forecast opportunity.
        fresh = bar + 60 <= observed < start and (not staged or issued < start - 1)
        if fresh:
            db.executemany("""INSERT OR IGNORE INTO call
                (trial,bar,start,finish,generation,guesses,prediction,confidence,traded,issued) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ((*r, issued) for r in staged))
    _export_committed_defaults(db_path)
    return {"bar": bar if fresh else None, "recorded": len(staged) if fresh else 0,
            "message": ("Waiting for a fresh candle" if not bar + 60 <= observed < start
                        else "Forecast window elapsed during calculation" if not fresh
                        else "Waiting for existing forecast window" if pending_windows and not due_trials
                        else "Checked the latest closed minute"),
            "rows": status(asset, db_path=db_path)}


def status(asset: str, *, db_path: Path | None = None) -> list[dict]:
    path = db_path or config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    if not path.exists():
        return []
    defaults = load_defaults()
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        columns = {r[1] for r in db.execute("PRAGMA table_info(call)")}
        profiles = {}
        if "traded" in columns:
            for key, raw in db.execute("SELECT id,execution FROM trial WHERE asset=?", (asset,)).fetchall():
                calls = db.execute("SELECT net_return,traded,liquidated FROM call WHERE trial=? AND outcome IS NOT NULL ORDER BY bar", (key,)).fetchall()
                equity = 1.0
                for ret, _, _ in calls:
                    if ret is not None:
                        equity *= 1 + ret
                last = db.execute("SELECT confidence,traded FROM call WHERE trial=? ORDER BY bar DESC LIMIT 1", (key,)).fetchone()
                profiles[key] = {"execution": json.loads(raw) if raw else None,
                    "net_pct": equity - 1 if raw else None,
                    "paper_trades": sum(bool(r[1]) for r in calls),
                    "liquidations": sum(bool(r[2]) for r in calls),
                    "confidence": last[0] if last else None, "traded": bool(last[1]) if last else False}
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return [
            {"id": key, **profiles.get(key, {}), "asset": asset, "label": label, "minutes": minutes, "settings": json.loads(active),
             "saved_default": saved_default(asset, label, minutes, defaults) == json.loads(active),
             "changes": gen,
             "note": note, "resolved": resolved, "correct": hits or 0, "pending": pending or 0,
             "expired": expired or 0, "last_call": last_call, "last_issued": last_issued,
             "cost_bps": cost, "last_outcome": last_outcome}
            for key, label, minutes, active, gen, note, resolved, hits, pending, expired, last_call, last_issued, cost, last_outcome
            in db.execute("""
              SELECT t.id,t.label,t.minutes,t.active,t.generation,t.note,count(c.outcome),
                sum(c.outcome=c.prediction),sum(c.outcome IS NULL AND c.expired=0 AND c.bar IS NOT NULL),
                sum(c.expired),
                (SELECT prediction FROM call WHERE trial=t.id ORDER BY bar DESC LIMIT 1),
                max(c.issued), t.cost,
                (SELECT outcome FROM call WHERE trial=t.id AND outcome IS NOT NULL ORDER BY bar DESC LIMIT 1)
              FROM trial t LEFT JOIN call c ON t.id=c.trial WHERE t.asset=?
              GROUP BY t.id ORDER BY t.label,t.minutes,t.id
            """, (asset,))
        ]


def top_forward_predictions(asset: str, *, min_resolved: int = 1, limit: int = 50,
                            db_path: Path | None = None) -> list[dict[str, Any]]:
    """Rank current trial evidence per label/horizon before applying the display limit."""
    path = db_path or config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
    if not path.exists():
        return []
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        rows = db.execute("""
            WITH per_trial AS (
                SELECT t.id, t.label, t.minutes, t.active,
                       count(c.outcome) as resolved,
                       coalesce(sum(c.outcome=c.prediction),0) as hits,
                       (SELECT prediction FROM call WHERE trial=t.id ORDER BY bar DESC LIMIT 1) as last_call,
                       (SELECT issued FROM call WHERE trial=t.id ORDER BY bar DESC LIMIT 1) as last_issued,
                       max(c.bar) as last_bar
                FROM trial t JOIN call c ON t.id=c.trial
                WHERE t.asset=? AND t.minutes IN (1,5,10,30)
                GROUP BY t.id
            ), ranked AS (
                SELECT *, row_number() OVER (
                    PARTITION BY label,minutes ORDER BY last_issued DESC,last_bar DESC,id DESC
                ) as revision_rank FROM per_trial
            ), current AS (
                SELECT * FROM ranked WHERE revision_rank=1
            )
            SELECT label,
                   sum(resolved) as total_resolved,
                   sum(hits) as total_hits,
                   max(CASE WHEN minutes=1 THEN last_call END) as p1,
                   max(CASE WHEN minutes=5 THEN last_call END) as p5,
                   max(CASE WHEN minutes=10 THEN last_call END) as p10,
                   max(CASE WHEN minutes=30 THEN last_call END) as p30,
                   max(CASE WHEN minutes=1 THEN hits*100.0/nullif(resolved,0) END) as acc1,
                   max(CASE WHEN minutes=5 THEN hits*100.0/nullif(resolved,0) END) as acc5,
                   max(CASE WHEN minutes=10 THEN hits*100.0/nullif(resolved,0) END) as acc10,
                   max(CASE WHEN minutes=30 THEN hits*100.0/nullif(resolved,0) END) as acc30,
                   max(CASE WHEN minutes=1 THEN resolved ELSE 0 END) as n1,
                   max(CASE WHEN minutes=5 THEN resolved ELSE 0 END) as n5,
                   max(CASE WHEN minutes=10 THEN resolved ELSE 0 END) as n10,
                   max(CASE WHEN minutes=30 THEN resolved ELSE 0 END) as n30,
                   max(last_issued) as max_issued,
                   (SELECT active FROM current selected WHERE selected.label=cur.label
                    ORDER BY last_issued DESC,last_bar DESC,id DESC LIMIT 1) as active_json
            FROM current cur
            GROUP BY label
            HAVING total_resolved >= ?
            ORDER BY (CAST(total_hits AS REAL) / total_resolved) DESC, total_resolved DESC,label
            LIMIT ?
        """, (asset, min_resolved, limit)).fetchall()
        dirs = {1: "UP", -1: "DOWN", 0: "FLAT"}
        out = []
        for r in rows:
            acc = round(r[2] * 100.0 / r[1], 1) if r[1] else 0.0
            settings = []
            if r[16]:
                try:
                    settings = json.loads(r[16])
                except (ValueError, TypeError):
                    pass
            out.append({
                "label": r[0],
                "asset": asset,
                "resolved": r[1],
                "hits": r[2],
                "accuracy": acc,
                "pred_1m": dirs.get(r[3], "-"),
                "pred_5m": dirs.get(r[4], "-"),
                "pred_10m": dirs.get(r[5], "-"),
                "pred_30m": dirs.get(r[6], "-"),
                "acc_1m": round(r[7], 1) if r[7] is not None else None,
                "acc_5m": round(r[8], 1) if r[8] is not None else None,
                "acc_10m": round(r[9], 1) if r[9] is not None else None,
                "acc_30m": round(r[10], 1) if r[10] is not None else None,
                "resolved_1m": r[11],
                "resolved_5m": r[12],
                "resolved_10m": r[13],
                "resolved_30m": r[14],
                "last_issued": r[15],
                "settings": settings,
            })
        return out

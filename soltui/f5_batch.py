"""Durable, isolated all-strategy backtest and prospective forward runner.

The caller supplies the supported coin universe. The plan freezes it and the supported
intervals before work starts. A worker is started only by explicit `start`, never import.
All data stays under a run-specific directory and the existing queue is untouched.
"""
from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing
from itertools import pairwise
from pathlib import Path
from threading import Event
from typing import Any, Callable, Sequence

from backtester.core.strategies import REGISTRY
from backtester.core.strategy_cards import HORIZONS, load_all

from . import bgqueue, bgworker, config, forwardtest
from .runner import engine_config
from .research_admission import admit_read, participating
from .source_epoch import SourceEpoch, SourceEpochChanged

_REPO = Path(__file__).resolve().parent.parent
_SOURCE_EPOCH = SourceEpoch.capture(_REPO)

INTERVAL_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "6h": 360, "1d": 1440}
PHASES = {"planned", "backtesting", "stopped", "failed", "forward", "forward_partial"}


def _signal_response(cache, symbol, interval, fetch, **kwargs):
    seconds = int(kwargs["seconds"])
    now = float(kwargs["now"])
    closed = int(now // seconds)
    key = (symbol, interval, closed)
    if key not in cache:
        for old_key in list(cache):
            if old_key[0] != symbol or old_key[1] == interval:
                del cache[old_key]
        raw = fetch(symbol, cache=False, **kwargs)
        mask = raw["ts"] + seconds <= now
        bars = {name: values[mask] for name, values in raw.items()}
        timestamps = bars["ts"]
        if (not len(timestamps) or int(timestamps[-1]) != (closed - 1) * seconds
                or any(b <= a for a, b in pairwise(timestamps))):
            raise ValueError(f"No current closed {interval} signal candle")
        tail = 0
        for index in range(1, len(timestamps)):
            if timestamps[index] - timestamps[index - 1] != seconds:
                tail = index
        forwardtest.validate_bar_arrays({name: values[tail:] for name, values in bars.items()}, interval)
        cache[key] = raw
    return cache[key]


def _root(root: Path | None = None) -> Path:
    return Path(root or config.CONFIG_DIR / "f5-batches").expanduser().resolve()


def _directory(run_id: str, root: Path | None = None) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("invalid batch id")
    return _root(root) / run_id


def _connect(directory: Path) -> sqlite3.Connection:
    db = sqlite3.connect(directory / "batch.sqlite3", timeout=30)
    db.row_factory = sqlite3.Row
    return db


def _dump(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _meta(db: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def _set(db: sqlite3.Connection, key: str, value: Any) -> None:
    db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, _dump(value)))


def _code_id(sources: dict[str, str] | None = None) -> str:
    sources = sources if sources is not None else bgworker.evaluation_code_fingerprint()
    return hashlib.sha256(_dump(sources).encode()).hexdigest()


def _candidate_templates(names: Sequence[str], horizons: Sequence[str], asset: str,
                         interval: str) -> dict[str, Any]:
    """Validate once per preset; expand only labels and ids across the universe."""
    cards = _card_map()
    templates = {}
    for name in names:
        card = cards.get(name)
        if name.startswith("lev_") or card is None or not card.buildable or not card.data_available:
            continue
        for horizon in horizons:
            excluded: list[bgqueue.CandidateExclusion] = []
            jobs = bgqueue.jobs_for_card(card, horizon, asset, interval, max_tier=2,
                                          exclusions=excluded)
            def template(job: bgqueue.Job) -> dict[str, Any]:
                return {k: v for k, v in job.to_dict().items() if k not in ("asset", "interval")}
            templates[f"{name}:{horizon}"] = {
                "jobs": [template(job) for job in jobs],
                "exclusions": [{"job": template(item.job), "reason": item.reason,
                                "detail": item.detail} for item in excluded],
            }
    return templates


def _expand_candidates(template: dict[str, Any], asset: str,
                        interval: str) -> tuple[list[bgqueue.Job], list[bgqueue.CandidateExclusion]]:
    jobs = [bgqueue.Job(**item, asset=asset, interval=interval) for item in template["jobs"]]
    exclusions = [bgqueue.CandidateExclusion(
        bgqueue.Job(**item["job"], asset=asset, interval=interval), item["detail"], item["reason"])
        for item in template["exclusions"]]
    return jobs, exclusions


def _candidate_counts(templates: dict[str, Any], copies: int) -> dict[str, int]:
    eligible = sum(len(item["jobs"]) for item in templates.values()) * copies
    excluded = sum(len(item["exclusions"]) for item in templates.values()) * copies
    return {"requested": eligible + excluded, "eligible": eligible, "excluded": excluded}


def catalog_coins() -> tuple[list[str], dict[str, Any]]:
    """Freeze the complete retained Coinbase spot catalogue, without network access."""
    from . import coinbase_account

    path = coinbase_account.spot_pairs_path()
    try:
        raw = path.read_bytes()
        catalogue = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise ValueError("Complete Coinbase spot-pair catalog unavailable; refresh it before starting F5") from exc
    if not isinstance(catalogue, dict) or catalogue.get("complete") is not True or not isinstance(catalogue.get("products"), list):
        raise ValueError("Coinbase spot-pair catalog is incomplete; refresh it before starting F5")
    products = catalogue["products"]
    if catalogue.get("count") is not None and catalogue["count"] != len(products):
        raise ValueError("Coinbase spot catalog count does not match its retained products")
    assets: set[str] = set()
    ids: set[str] = set()
    excluded = {"non_usd": 0, "offline": 0, "disabled": 0}
    for product in products:
        if not isinstance(product, dict) or product.get("product_type") != "SPOT":
            raise ValueError("Coinbase spot catalog contains an invalid product")
        product_id = product.get("product_id")
        if not isinstance(product_id, str) or not product_id or product_id in ids:
            raise ValueError("Coinbase spot catalog has a missing or duplicate product id")
        ids.add(product_id)
        if product.get("quote_currency_id") != "USD":
            excluded["non_usd"] += 1
            continue
        asset = product.get("base_currency_id")
        if not isinstance(asset, str) or product_id != f"{asset}-USD":
            raise ValueError(f"Coinbase USD product {product_id} has an invalid base symbol")
        if not isinstance(product.get("status"), str) or type(product.get("trading_disabled")) is not bool:
            raise ValueError(f"Coinbase USD product {product_id} has unknown eligibility")
        if product["status"].lower() != "online":
            excluded["offline"] += 1
            continue
        if product["trading_disabled"]:
            excluded["disabled"] += 1
            continue
        try:
            assets.add(bgqueue.validate_asset(asset))
        except ValueError as exc:
            raise ValueError(f"Coinbase USD product {product_id} has an unsupported symbol") from exc
    if not assets:
        raise ValueError("Coinbase spot catalog contains no eligible USD markets")
    return sorted(assets), {"source": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                            "fetched_at": catalogue.get("fetched_at"), "eligible": len(assets),
                            "catalog_products": len(products), "excluded": excluded,
                            "selection": "online, enabled Coinbase spot markets quoted in USD"}


def create(settings: config.Settings, coins: Sequence[str] | None = None, *, root: Path | None = None,
           intervals: Sequence[str] = config.INTERVALS, strategies: Sequence[str] | None = None,
           horizons: Sequence[str] = HORIZONS, longest_contiguous: bool = False) -> dict[str, Any]:
    """Create a frozen plan. Missing series are recorded by the worker, not guessed.

    This may create a large plan; callers must run it off the UI thread. `start`
    is a separate explicit action and `create` does not run any tests.
    """
    _SOURCE_EPOCH.verify(_REPO)
    if coins is None:
        assets, universe = catalog_coins()
    else:
        if isinstance(coins, (str, bytes)):
            raise ValueError("coins must be a sequence of symbols")
        assets = sorted({bgqueue.validate_asset(c) for c in coins})
        universe = {"source": "explicit list", "eligible": len(assets)}
    intervals = tuple(dict.fromkeys(intervals))
    horizons = tuple(dict.fromkeys(horizons))
    names = sorted(set(strategies if strategies is not None else REGISTRY))
    if not assets or not intervals or not names or not horizons:
        raise ValueError("at least one coin, interval, strategy and preset horizon is required")
    if any(i not in INTERVAL_MINUTES for i in intervals) or any(h not in HORIZONS for h in horizons):
        raise ValueError("unsupported interval or preset horizon")
    if any(name not in REGISTRY for name in names):
        raise ValueError("unknown registered strategy")
    templates = _candidate_templates(names, horizons, assets[0], intervals[0])
    candidate_counts = _candidate_counts(templates, len(assets) * len(intervals))
    run_id = uuid.uuid4().hex
    directory = _directory(run_id, root)
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    from .simulation import FIELDS
    # Preserve the explicitly selected paper policy across the worker handoff.
    # Legacy plans omit these fields and retain Settings' original defaults.
    whitelist = ("capital", "fee_bps", "slippage_bps", "fill_delay", "cpcv_groups", "cpcv_k",
                 "fee_schedule", *FIELDS)
    frozen = {name: getattr(settings, name) for name in whitelist}
    frozen.update(start="", end="", data_dir=str(Path(settings.data_dir).expanduser().resolve()))
    code_sources = bgworker.evaluation_code_fingerprint()
    try:
        with closing(_connect(directory)) as db, db:
            db.executescript("""
              CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
              CREATE TABLE series(asset TEXT, interval TEXT, path TEXT, sha256 TEXT,
                                  PRIMARY KEY(asset,interval));
              CREATE TABLE cell(id INTEGER PRIMARY KEY, asset TEXT NOT NULL, interval TEXT NOT NULL,
                                strategy TEXT NOT NULL, horizon TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'pending',
                                reason TEXT NOT NULL DEFAULT '', selected TEXT, score REAL,
                                UNIQUE(asset,interval,strategy,horizon));
              CREATE TABLE attempt(cell INTEGER, job_id TEXT, state TEXT NOT NULL, result TEXT NOT NULL,
                                   PRIMARY KEY(cell,job_id));
              CREATE TABLE forward_check(asset TEXT, interval TEXT, at REAL, recorded INTEGER, total_recorded INTEGER,
                                         trials_expected INTEGER, trials_recorded INTEGER, error TEXT, message TEXT,
                                         PRIMARY KEY(asset,interval));
            """)
            for key, value in {"version": 1, "id": run_id, "phase": "planned", "created_at": time.time(),
                               "assets": assets, "intervals": intervals, "strategies": names, "horizons": horizons,
                               "longest_contiguous": longest_contiguous,
                               "candidate_templates": templates, "candidate_counts": candidate_counts,
                               "settings": frozen, "code_id": _code_id(code_sources), "code_sources": code_sources,
                               "current": "", "universe": universe,
                               "notice": "Jupiter Perps scenario simulation. Each input is frozen when its series is first processed; selection uses CPCV results and is not independent validation. Leverage tiers require a perp-aware runner and are reported unsupported. Unresolved forward outcomes older than seven days remain pending until minute data can be recovered."}.items():
                _set(db, key, value)
            db.executemany("INSERT INTO cell(asset,interval,strategy,horizon) VALUES(?,?,?,?)",
                           ((a, i, n, h) for a in assets for i in intervals for n in names for h in horizons))
            total = db.execute("SELECT count(*) FROM cell").fetchone()[0]
        os.chmod(directory / "batch.sqlite3", 0o600)
    except BaseException:
        # Leave any partially-created directory intact for diagnosis; it is never selected automatically.
        raise
    return {"run_id": run_id, "directory": str(directory), "cells": total,
            "assets": assets, "intervals": list(intervals), "strategies": len(names),
            "horizons": list(horizons), "phase": "planned", "universe": universe,
            "candidates": candidate_counts,
            "longest_contiguous": longest_contiguous}


def _lock(directory: Path) -> int | None:
    fd = os.open(directory / "worker.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def _global_lock(root: Path | None = None) -> int | None:
    path = _root(root) / "f5-worker.lock"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def start(run_id: str, *, root: Path | None = None) -> dict[str, Any]:
    """Start or resume exactly this batch; does not interact with other workers."""
    _SOURCE_EPOCH.verify(_REPO)
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    global_fd = _global_lock(root)
    if global_fd is None:
        raise RuntimeError("another F5 batch is already running")
    fd = None
    try:
        fd = _lock(directory)
        if fd is None:
            raise RuntimeError("this batch is already running")
        token = uuid.uuid4().hex
        (directory / "worker-token").write_text(token, encoding="ascii")
        with (directory / "worker.log").open("ab") as out:
            proc = subprocess.Popen([sys.executable, "-m", "soltui.f5_batch", "worker", "--id", run_id,
                                     "--root", str(_root(root)), "--lock-fd", str(fd),
                                     "--global-lock-fd", str(global_fd), "--token", token],
                                    cwd=str(Path(__file__).resolve().parent.parent),
                                    stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                    start_new_session=True, pass_fds=(fd, global_fd))
        # Reap on exit while this UI process lives. The daemon thread does not keep
        # the UI or the detached worker alive after the UI exits.
        threading.Thread(target=proc.wait, name=f"f5-reap-{run_id[:8]}", daemon=True).start()
        return {"run_id": run_id, "pid": proc.pid, "log": str(directory / "worker.log")}
    finally:
        if fd is not None:
            os.close(fd)
        os.close(global_fd)


def stop(run_id: str, *, root: Path | None = None) -> dict[str, Any]:
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    fd = _lock(directory)
    if fd is not None:
        os.close(fd)
        return {"run_id": run_id, "stopping": False}
    # Bind the request to the observed instance. A delayed stop cannot stop its successor.
    try:
        token = (directory / "worker-token").read_text(encoding="ascii").strip()
    except OSError:
        return {"run_id": run_id, "stopping": False, "error": "worker identity unavailable"}
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        return {"run_id": run_id, "stopping": False, "error": "worker identity invalid"}
    (directory / f"stop-{token}").touch(mode=0o600, exist_ok=True)
    return {"run_id": run_id, "stopping": True}


def _forward_backlog(directory: Path, now: float | None = None) -> dict[str, Any]:
    path = directory / "forward.sqlite3"
    if not path.exists():
        return {"due": 0, "oldest": None, "beyond_seven_days": 0}
    observed = time.time() if now is None else now
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            row = db.execute("SELECT count(*),min(start),sum(start<?) FROM call "
                             "WHERE outcome IS NULL AND expired=0 AND finish<=?",
                             (observed - 7 * 86400, observed)).fetchone()
        return {"due": int(row[0]), "oldest": row[1], "beyond_seven_days": int(row[2] or 0)}
    except sqlite3.Error as exc:
        return {"due": None, "oldest": None, "beyond_seven_days": None,
                "error": f"{type(exc).__name__}: {exc}"[:500]}


def status(run_id: str, *, root: Path | None = None) -> dict[str, Any]:
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    fd = _lock(directory)
    running = fd is None
    if fd is not None:
        os.close(fd)
    with closing(_connect(directory)) as db, db:
        counts = {r[0]: r[1] for r in db.execute("SELECT state,count(*) FROM cell GROUP BY state")}
        problems = [dict(r) for r in db.execute("SELECT asset,interval,strategy,horizon,state,reason FROM cell "
                                                "WHERE state IN ('failed','missing','unsupported','partial') ORDER BY id LIMIT 100")]
        checks = [dict(r) for r in db.execute("SELECT * FROM forward_check ORDER BY asset,interval")]
        phase = _meta(db, "phase", "failed")
        if phase in ("backtesting", "forward", "forward_partial", "forward_waiting", "forward_partial_waiting") and not running:
            phase = "interrupted"
        return {"run_id": run_id, "phase": phase, "running": running, "counts": counts,
                "total": sum(counts.values()), "current": _meta(db, "current", ""),
                "assets": _meta(db, "assets", []), "intervals": _meta(db, "intervals", []),
                "universe": _meta(db, "universe", {}),
                "longest_contiguous": _meta(db, "longest_contiguous", False),
                "candidates": _meta(db, "candidate_counts", None),
                "problems": problems, "problems_truncated": sum(counts.get(k, 0) for k in ("failed", "missing", "unsupported", "partial")) > len(problems),
                "forward_checks": checks, "forward_backlog": _forward_backlog(directory),
                "notice": _meta(db, "notice", ""),
                "error": _meta(db, "error", ""), "log": str(directory / "worker.log"),
                "forward_db": str(directory / "forward.sqlite3")}


def list_runs(*, root: Path | None = None) -> list[dict[str, Any]]:
    """Find saved runs after an app restart; invalid entries are reported, not deleted."""
    base = _root(root)
    if not base.exists():
        return []
    found = []
    for directory in sorted(base.iterdir()):
        if not directory.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", directory.name):
            continue
        try:
            found.append(status(directory.name, root=base))
        except (ValueError, OSError, sqlite3.Error) as exc:
            found.append({"run_id": directory.name, "phase": "unreadable", "running": False,
                          "error": f"{type(exc).__name__}: {exc}"[:500]})
    return found


def cells(run_id: str, *, root: Path | None = None, state: str | None = None,
          offset: int = 0, limit: int = 100) -> list[dict[str, Any]]:
    """Page the exact combinations rather than truncating coverage at a summary."""
    if limit < 1 or limit > 1000 or offset < 0:
        raise ValueError("invalid page")
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    with closing(_connect(directory)) as db, db:
        query = "SELECT * FROM cell" + (" WHERE state=?" if state else "") + " ORDER BY id LIMIT ? OFFSET ?"
        params = (state, limit, offset) if state else (limit, offset)
        rows = [dict(row) for row in db.execute(query, params)]
        templates = _meta(db, "candidate_templates", None)
        for row in rows:
            row["selected"] = json.loads(row["selected"]) if row["selected"] else None
            template = (templates or {}).get(f"{row['strategy']}:{row['horizon']}")
            row["candidates"] = (bgqueue.candidate_census(*_expand_candidates(
                template, row["asset"], row["interval"])) if template is not None else None)
        return rows


def attempts(run_id: str, cell_id: int, *, root: Path | None = None) -> list[dict[str, Any]]:
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    with closing(_connect(directory)) as db, db:
        rows = [dict(row) for row in db.execute("SELECT * FROM attempt WHERE cell=? ORDER BY job_id", (cell_id,))]
        for row in rows:
            row["result"] = json.loads(row["result"])
        return rows


def proof(run_id: str, asset: str, interval: str, *, root: Path | None = None) -> dict[str, Any]:
    """Return the exact immutable code, settings and per-series input binding."""
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    asset = bgqueue.validate_asset(asset)
    if interval not in INTERVAL_MINUTES:
        raise ValueError("unsupported interval")
    with closing(_connect(directory)) as db, db:
        series = db.execute("SELECT path,sha256 FROM series WHERE asset=? AND interval=?", (asset, interval)).fetchone()
        templates = _meta(db, "candidate_templates", None)
        candidate_plans = None
        if (templates is not None and asset in _meta(db, "assets", [])
                and interval in _meta(db, "intervals", [])):
            candidate_plans = []
            for template in templates.values():
                jobs, exclusions = _expand_candidates(template, asset, interval)
                candidate_plans.append({**bgqueue.candidate_census(jobs, exclusions),
                                        "jobs": [{"job_id": job.job_id, **job.to_dict()} for job in jobs]})
        return {"run_id": run_id, "settings": _meta(db, "settings", {}),
                "code_id": _meta(db, "code_id", ""), "code_sources": _meta(db, "code_sources", {}),
                "series": dict(series) if series else None, "universe": _meta(db, "universe", {}),
                "candidate_plans": candidate_plans,
                "data_selection": _meta(db, f"data_selection:{asset}:{interval}", None)}


def forward_results(run_id: str, asset: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    """Read the isolated forward ledger for one planned coin without creating it."""
    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    asset = bgqueue.validate_asset(asset)
    with closing(_connect(directory)) as db, db:
        if asset not in _meta(db, "assets", []):
            raise ValueError("coin is not in this batch")
    return forwardtest.status(asset, db_path=directory / "forward.sqlite3")


def _forward_history(directory: Path, asset: str, now: float) -> int:
    """Cover the oldest due prediction up to seven days, keeping older gaps pending."""
    path = directory / "forward.sqlite3"
    if not path.exists():
        return 1442
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        row = db.execute("SELECT min(c.start) FROM call c JOIN trial t ON t.id=c.trial "
                         "WHERE t.asset=? AND c.outcome IS NULL AND c.expired=0 AND c.finish<=?", (asset, now)).fetchone()
    if not row or row[0] is None:
        return 1442
    return max(1442, min(10080, math.ceil((now - int(row[0])) / 60) + 2))


def _card_map() -> dict[str, Any]:
    return {c.registry_key or c.id: c for c in load_all().values() if c.registry_key or c.id in REGISTRY}


def _settings(raw: dict[str, Any]) -> config.Settings:
    # Construct only simulation settings. Wallet addresses and keys are not stored in the ledger.
    return config.Settings(**raw)


def _finish_cell(db: sqlite3.Connection, cell_id: int, state: str, reason: str = "",
                 selected: dict[str, Any] | None = None, score: float | None = None) -> None:
    db.execute("UPDATE cell SET state=?,reason=?,selected=?,score=? WHERE id=?",
               (state, reason[:500], _dump(selected) if selected is not None else None, score, cell_id))
    db.commit()


def _series_hash(db: sqlite3.Connection, settings: config.Settings, asset: str, interval: str) -> str | None:
    path = (Path(settings.data_dir) / f"{asset}_{interval}.csv").resolve()
    try:
        digest = bgworker._file_hash(path)
    except FileNotFoundError:
        digest = None
    row = db.execute("SELECT path,sha256 FROM series WHERE asset=? AND interval=?", (asset, interval)).fetchone()
    if row is None:
        db.execute("INSERT INTO series VALUES(?,?,?,?)", (asset, interval, str(path), digest))
        db.commit()
    elif row[0] != str(path) or row[1] != digest:
        raise ValueError("price input changed after this series was frozen; start a separate batch")
    return digest


def _save_forward_check(db: sqlite3.Connection, asset: str, interval: str, recorded: int,
                        error: str = "", message: str = "", expected: int = 0, observed: int = 0) -> None:
    db.execute("""INSERT INTO forward_check(asset,interval,at,recorded,total_recorded,trials_expected,
                  trials_recorded,error,message) VALUES(?,?,?,?,?,?,?,?,?)
                  ON CONFLICT(asset,interval) DO UPDATE SET at=excluded.at, recorded=excluded.recorded,
                  total_recorded=forward_check.total_recorded+excluded.recorded,
                  trials_expected=excluded.trials_expected, trials_recorded=excluded.trials_recorded,
                  error=excluded.error, message=excluded.message""",
               (asset, interval, time.time(), recorded, recorded, expected, observed, error[:500], message[:500]))



def _run_cell(db: sqlite3.Connection, row: sqlite3.Row, settings: config.Settings,
              cards: dict[str, Any], cancelled: Callable[[], bool]) -> None:
    _SOURCE_EPOCH.verify(_REPO)
    from backtester.core.types import validate_bar_arrays

    cell_id, asset, interval, name, horizon = (row[k] for k in ("id", "asset", "interval", "strategy", "horizon"))
    # The shared CPCV runner is spot-only; it does not apply tier leverage,
    # funding or liquidation. Do not label its base signal as a leveraged test.
    if name.startswith("lev_"):
        _finish_cell(db, cell_id, "unsupported", "Leverage tiers need a perp-aware CPCV runner with funding and liquidation")
        return
    card = cards.get(name)
    if card is None or not card.buildable or not card.data_available:
        _finish_cell(db, cell_id, "unsupported", "No buildable, data-supported strategy card for this registry entry")
        return
    templates = _meta(db, "candidate_templates", None)
    template = (templates or {}).get(f"{name}:{horizon}")
    if templates is not None and template is None:
        raise ValueError(f"frozen candidate plan missing for {name} · {horizon}")
    exclusions: list[bgqueue.CandidateExclusion] = []
    if template is None:
        # Legacy plans remain readable; their code binding controls resumption.
        jobs = bgqueue.jobs_for_card(card, horizon, asset, interval, max_tier=2,
                                      exclusions=exclusions)
    else:
        jobs, exclusions = _expand_candidates(template, asset, interval)
    if not jobs:
        _finish_cell(db, cell_id, "unsupported", "No preset or required parameters are unavailable")
        return
    try:
        admit_read(
            asset,
            source="f5:" + str(Path(db.execute("PRAGMA database_list").fetchone()[2]).resolve()),
            attempts=len(jobs),
        )
        digest = _series_hash(db, settings, asset, interval)
        if digest is None:
            _finish_cell(db, cell_id, "missing", "No cached price series; fetching remains a separate action")
            return
        arrays = bgworker.ArrayCache(settings).get(asset, interval)
        if _series_hash(db, settings, asset, interval) != digest:
            raise ValueError("price input changed while loading")
        if _meta(db, "longest_contiguous", False):
            from .runner import select_contiguous
            arrays, selection = select_contiguous(arrays, interval, longest=True)
            _set(db, f"data_selection:{asset}:{interval}", selection)
            db.commit()
        else:
            # Existing plans keep their original strict input policy.
            validate_bar_arrays(arrays, interval)
    except Exception as exc:
        _finish_cell(db, cell_id, "failed", f"{type(exc).__name__}: {exc}")
        return
    for job in jobs:
        if cancelled():
            return
        prior = db.execute("SELECT 1 FROM attempt WHERE cell=? AND job_id=?", (cell_id, job.job_id)).fetchone()
        if prior:
            continue
        try:
            _SOURCE_EPOCH.verify(_REPO)
            result = bgworker.evaluate(job, arrays, engine_config(settings, interval), settings)
            _SOURCE_EPOCH.verify(_REPO)
            payload = dataclasses.asdict(result)
            attempt_state = "evaluated" if result.evaluable else "not_evaluable"
        except SourceEpochChanged:
            raise
        except Exception as exc:
            payload = {"reason": f"{type(exc).__name__}: {exc}"[:500], "params": dict(job.params)}
            attempt_state = "failed"
        db.execute("INSERT INTO attempt VALUES(?,?,?,?)", (cell_id, job.job_id, attempt_state, _dump(payload)))
        db.commit()  # A crash repeats at most the currently running configuration.
    outcomes = [dict(r) for r in db.execute("SELECT state,result FROM attempt WHERE cell=?", (cell_id,))]
    valid = [json.loads(r["result"]) for r in outcomes if r["state"] == "evaluated"]
    valid = [r for r in valid if isinstance(r.get("median_sharpe"), (int, float))
             and math.isfinite(r["median_sharpe"])]
    if not valid:
        _finish_cell(db, cell_id, "failed", "No parameter variant produced an evaluable result")
        return
    winner = max(valid, key=lambda r: r["median_sharpe"])
    bad = sum(r["state"] != "evaluated" for r in outcomes)
    selection = _meta(db, f"data_selection:{asset}:{interval}", None)
    reasons = [f"{bad} of {len(outcomes)} variants did not produce an evaluable result"] if bad else []
    if exclusions:
        reasons.append(f"{len(exclusions)} of {len(jobs) + len(exclusions)} requested candidates "
                       "excluded before evaluation: invalid_parameters. See batch.proof for exact parameters.")
    if selection:
        reasons.append(f"Longest continuous window: {selection['selected_bars']} of {selection['source_bars']} original bars; {selection['gaps_excluded']} gaps excluded. See batch.proof for timestamps.")
    _finish_cell(db, cell_id, "partial" if bad else "completed", " ".join(reasons),
                 {"name": name, "params": winner["params"], "selection": "highest CPCV median Sharpe; selected on these results",
                  "data_selection": selection},
                 float(winner["median_sharpe"]))


class _StopEvent(Event):
    """Expose an instance-scoped cooperative stop file to the forward reader."""

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path

    def is_set(self) -> bool:
        return self.path.exists() or super().is_set()

    def wait(self, timeout: float | None = None) -> bool:
        deadline = time.monotonic() + max(0.0, timeout or 0.0)
        while not self.is_set() and time.monotonic() < deadline:
            super().wait(min(0.25, deadline - time.monotonic()))
        return self.is_set()


@participating
def run(run_id: str, *, root: Path | None = None, max_cells: int | None = None,
        forward_cycles: int | None = None, tick: Callable[..., dict[str, Any]] | None = None,
        wait: Callable[[float], None] = time.sleep, token: str = "test") -> None:
    """Run or resume a batch under a caller-held lock; limits exist for deterministic tests."""
    _SOURCE_EPOCH.verify(_REPO)
    from . import compound

    directory = _directory(run_id, root)
    if not (directory / "batch.sqlite3").is_file():
        raise ValueError("batch does not exist")
    stop_event = _StopEvent(directory / f"stop-{token}")
    cancel = stop_event.is_set
    with closing(_connect(directory)) as db, db:
        if _meta(db, "code_id") != _code_id():
            _set(db, "phase", "failed")
            _set(db, "error", "Evaluation code changed since this batch was created; preserve it and create a new batch")
            db.commit()
            return
        settings = _settings(_meta(db, "settings"))
        cards = _card_map()
        _set(db, "phase", "backtesting")
        _set(db, "error", "")
        db.execute("UPDATE cell SET state='pending' WHERE state='running'")
        db.commit()
        done_now = 0
        while True:
            row = db.execute("SELECT * FROM cell WHERE state='pending' ORDER BY asset,interval,strategy,horizon LIMIT 1").fetchone()
            if row is None:
                break
            if cancel() or (max_cells is not None and done_now >= max_cells):
                _set(db, "phase", "stopped")
                db.commit()
                return
            db.execute("UPDATE cell SET state='running' WHERE id=?", (row["id"],))
            _set(db, "current", f"{row['asset']} {row['interval']} {row['strategy']} {row['horizon']}")
            db.commit()
            print(f"Backtest {row['asset']} {row['interval']} {row['strategy']} {row['horizon']}", flush=True)
            try:
                _run_cell(db, row, settings, cards, cancel)
            except SourceEpochChanged:
                raise
            except sqlite3.Error:
                raise  # A damaged or unwritable ledger is not an ordinary failed configuration.
            except Exception as exc:
                _finish_cell(db, row["id"], "failed", f"{type(exc).__name__}: {exc}")
            finished = db.execute("SELECT state,reason FROM cell WHERE id=?", (row["id"],)).fetchone()
            print(f"  {finished['state']}: {finished['reason']}", flush=True)
            if cancel():
                _set(db, "phase", "stopped")
                db.commit()
                return
            done_now += 1
        # All requested cells are terminal. Forward only cells that produced a usable configuration.
        problems = db.execute("SELECT count(*) FROM cell WHERE state != 'completed'").fetchone()[0]
        eligible = db.execute("SELECT count(*) FROM cell WHERE selected IS NOT NULL").fetchone()[0]
        if not eligible:
            _set(db, "phase", "failed")
            _set(db, "error", "No backtest produced a usable configuration; forward testing did not start")
            _set(db, "current", "")
            db.commit()
            return
        _set(db, "phase", "forward_partial_waiting" if problems else "forward_waiting")
        _set(db, "current", "")
        db.commit()
        from .simulation import from_settings
        tick = tick or forwardtest.tick
        cycle = 0
        cached: dict[str, Any] = {}
        signal_cache: dict[tuple[str, str, int], dict[str, Any]] = {}
        while not cancel():
            _SOURCE_EPOCH.verify(_REPO)
            pairs = db.execute("SELECT DISTINCT asset,interval FROM cell WHERE selected IS NOT NULL ORDER BY asset,interval").fetchall()
            for pair in pairs:
                if cancel():
                    break
                asset, interval = pair["asset"], pair["interval"]
                _set(db, "current", f"Forward check: {asset} {interval}")
                db.commit()
                selected = db.execute("SELECT strategy,horizon,selected FROM cell WHERE asset=? AND interval=? "
                                      "AND selected IS NOT NULL ORDER BY strategy,horizon", (asset, interval)).fetchall()
                trials = []
                member_errors = []
                for cell in selected:
                    config_row = json.loads(cell["selected"])
                    try:
                        member = forwardtest.member(config_row["name"], config_row["params"])
                    except Exception as exc:
                        member_errors.append(f"{cell['strategy']} {cell['horizon']}: {exc}")
                        continue
                    trials.append({"label": f"f5:{run_id}:{cell['strategy']}:{interval}:{cell['horizon']}",
                                   "mode": "all", "members": [member]})
                if not trials:
                    _save_forward_check(db, asset, interval, 0, "; ".join(member_errors), expected=len(selected))
                    db.commit()
                    continue
                minutes = INTERVAL_MINUTES[interval]
                try:
                    history = _forward_history(directory, asset, time.time())
                    # Fetch once per coin/minute without modifying other trainers' caches.
                    # Every call gets the longest settlement history, so a shorter interval
                    # cannot prematurely expire an outstanding one-day prediction.
                    def fetch(symbol: str, **kwargs: Any) -> dict[str, Any]:
                        minute_key = int(float(kwargs.get("now", time.time())) // 60)
                        if (cached.get("symbol") != symbol or cached.get("minute") != minute_key
                                or cached.get("bars", 0) < int(kwargs.get("bars", 0))):
                            cached.clear()
                            cached.update(symbol=symbol, minute=minute_key, bars=int(kwargs.get("bars", 0)),
                                          data=compound.fetch_closed_candles(symbol, cache=False, **kwargs))
                        return cached["data"]
                    def signal_fetch(symbol: str, _interval=interval, **kwargs: Any) -> dict[str, Any]:
                        return _signal_response(signal_cache, symbol, _interval, compound.fetch_closed_candles, **kwargs)
                    result = tick(asset, trials, (minutes,), 2 * (settings.fee_bps + settings.slippage_bps),
                                  tune=False, code=f"f5:{run_id}:{_meta(db, 'code_id')}",
                                  db_path=directory / "forward.sqlite3", history=history, fetch=fetch, stop=stop_event,
                                  signal_interval=interval, signal_fetch=signal_fetch, expire_missing=False,
                                  execution=from_settings(settings).to_dict())
                    _SOURCE_EPOCH.verify(_REPO)
                    recorded = int(result.get("recorded", 0))
                    wanted = {trial["label"] for trial in trials}
                    seen = {row["label"] for row in result.get("rows", [])
                            if row.get("label") in wanted and row.get("minutes") == minutes
                            and row.get("last_issued") is not None}
                    _save_forward_check(db, asset, interval, recorded, "; ".join(member_errors),
                                        str(result.get("message", "")), len(selected), len(seen))
                except SourceEpochChanged:
                    raise
                except Exception as exc:
                    _save_forward_check(db, asset, interval, 0, f"{type(exc).__name__}: {exc}",
                                        expected=len(selected))
                db.commit()
            coverage = db.execute("SELECT count(*), sum(total_recorded > 0), "
                                  "sum(error != '' OR trials_recorded < trials_expected) FROM forward_check").fetchone()
            observed = int(coverage[1] or 0)
            incomplete = problems or int(coverage[0]) < len(pairs) or int(coverage[2] or 0) or observed < len(pairs)
            _set(db, "phase", ("forward_partial" if incomplete else "forward") if observed else
                 ("forward_partial_waiting" if incomplete else "forward_waiting"))
            db.commit()
            cycle += 1
            if forward_cycles is not None and cycle >= forward_cycles:
                break
            for _ in range(60):
                if cancel():
                    break
                wait(1.0)
        if cancel():
            _set(db, "phase", "stopped")
            db.commit()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["worker"])
    parser.add_argument("--id", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--lock-fd", type=int, required=True)
    parser.add_argument("--global-lock-fd", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    directory = _directory(args.id, args.root)
    try:
        # Only the original inherited lock can protect this process from a concurrent resume.
        expected = os.stat(directory / "worker.lock")
        held = os.fstat(args.lock_fd)
        if (expected.st_dev, expected.st_ino) != (held.st_dev, held.st_ino):
            raise ValueError("worker lock descriptor does not match this batch")
        global_expected = os.stat(_root(args.root) / "f5-worker.lock")
        global_held = os.fstat(args.global_lock_fd)
        if (global_expected.st_dev, global_expected.st_ino) != (global_held.st_dev, global_held.st_ino):
            raise ValueError("global worker lock descriptor does not match")
        fcntl.flock(args.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(args.global_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not re.fullmatch(r"[0-9a-f]{32}", args.token) or (directory / "worker-token").read_text() != args.token:
            raise ValueError("worker instance identity does not match")
        run(args.id, root=args.root, token=args.token)
        with closing(_connect(directory)) as db, db:
            return 1 if _meta(db, "phase") == "failed" else 0
    except Exception as exc:
        try:
            with closing(_connect(directory)) as db, db:
                _set(db, "phase", "failed")
                _set(db, "error", f"{type(exc).__name__}: {exc}"[:500])
                db.commit()
        finally:
            print(f"Batch failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        os.close(args.lock_fd)
        os.close(args.global_lock_fd)


if __name__ == "__main__":
    raise SystemExit(main())

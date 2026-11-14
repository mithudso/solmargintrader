"""Durable native optimization over frozen local evidence.

Exploration never evaluates the final windows. Final validation freezes one train
winner and spends its temporal evidence before running either paired simulator.
The ledger records exposure as well as final reservations: changing window sizes
cannot turn dates already used for selection into an untouched final test.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import math
import platform
import statistics
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import bots
from .config import Settings
from .experiments import ExperimentError, ExperimentStore, preview_space
from .research_admission import native_authority, optimizer_lease, participating
from .source_epoch import SourceEpoch, SourceEpochChanged

_REPO = Path(__file__).resolve().parents[1]
_SOURCE_EPOCH = SourceEpoch.capture(_REPO)

SCHEMA_VERSION = 1
MAX_EVALUATIONS = 20_000


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _runtime_descriptor() -> dict[str, str]:
    """Bind measurements to the actual numerical runtime without host identity."""
    import pandas as pd

    return {"python": platform.python_version(), "implementation": sys.implementation.name,
            "machine": platform.machine(), "system": platform.system(),
            "numpy": np.__version__, "pandas": pd.__version__}


def _root(store: ExperimentStore) -> Path:
    return Path(store.root)


@contextmanager
def _lock(store: ExperimentStore, key: str) -> Iterator[None]:
    directory = _root(store) / "locks"
    directory.mkdir(parents=True, exist_ok=True)
    # Public run IDs never become path components. No stale PID file is an owner.
    path = directory / (hashlib.sha256(key.encode()).hexdigest() + ".lock")
    with path.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExperimentError("experiment already has an active worker") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def run_active(run_id: str, store: ExperimentStore | None = None) -> bool:
    """Check the operating-system run lock, including workers in other processes."""
    store = store or ExperimentStore()
    try:
        with _lock(store, "run:" + run_id):
            return False
    except ExperimentError:
        return True


def _disk_code_fingerprint() -> str:
    """Hash current path bytes; this helper alone makes no loaded-code claim."""
    root = Path(__file__).resolve().parents[1]
    paths = sorted((root / "backtester" / "core").rglob("*.py"))
    paths += [root / "soltui" / name for name in ("bots.py", "trend.py", "experiment_runner.py", "experiments.py")]
    h = hashlib.sha256()
    for path in paths:
        h.update(str(path.relative_to(root)).encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _code_fingerprint() -> str:
    """Admit current disk identity only within this fresh worker import epoch."""
    _SOURCE_EPOCH.verify(_REPO)
    return _disk_code_fingerprint()


def _settings(settings: Any = None) -> dict[str, Any]:
    costs = bots._costs(settings)
    return {"data_dir": str(bots.data_dir(settings).resolve()), "fee_bps": costs.fee_bps,
            "slippage_bps": costs.slippage_bps}


def _arrays_fingerprint(arrays: dict[str, np.ndarray]) -> str:
    h = hashlib.sha256()
    for key in ("ts", "open", "high", "low", "close"):
        array = np.asarray(arrays[key], dtype="<i8" if key == "ts" else "<f8")
        h.update(key.encode())
        h.update(str(array.shape).encode())
        h.update(array.tobytes())
    return h.hexdigest()


def _quotes_fingerprint(rows: list[tuple[float, dict]]) -> str:
    # Preserve exact parsed quote content, including unusable sizes. The digest is
    # evidence identity, not a numeric metric returned to callers.
    h = hashlib.sha256()
    for row in rows:
        h.update(json.dumps(row, sort_keys=True, separators=(",", ":")).encode())
        h.update(b"\n")
    return h.hexdigest()


def _split(index: int, count: int) -> str:
    explore = count - count // 2
    train = max(1, explore // 2)
    return "train" if index < train else "validation" if index < explore else "holdout"


def _stamp(value: float) -> str:
    return datetime.fromtimestamp(value, UTC).isoformat()


def _bar_windows(bot: str, settings: Any, coins: Sequence[str], count: int,
                 days: int) -> tuple[list[dict], dict[str, str], dict[str, str]]:
    windows, skipped, sources = [], {}, {}
    # A process may have cached a CSV with unchanged stat metadata. Evidence reads
    # deliberately bypass that optimization and hash the arrays actually replayed.
    bots._HOURLY_CACHE.clear()
    for coin in coins:
        try:
            arrays = bots.hourly(coin, settings)
            segments = bots.windows_for(arrays, count, days * 24)
        except (ValueError, OSError, RuntimeError) as exc:
            skipped[coin] = str(exc)
            continue
        if len(segments) < 2:
            skipped[coin] = f"only {len(segments)} usable {days}-day window(s) in its data"
            continue
        sources[coin] = arrays["source"]
        for i, seg in enumerate(segments):
            start, end = int(seg["ts"][0]), int(seg["ts"][-1]) + bots.BAR_SECONDS
            windows.append({"key": f"{coin}:{start}:{end}", "coin": coin, "start": start, "end": end,
                            "split": _split(i, len(segments)), "bars": int(seg["ts"].size),
                            "data_fingerprint": _arrays_fingerprint(seg), "data_source": arrays["source"]})
    return windows, skipped, sources


def _recorded_hours() -> Iterator[list[tuple[float, dict]]]:
    chunk: list[tuple[float, dict]] = []
    current: int | None = None
    # The recorder can still append to the current hour after a run freezes
    # its evidence. Only freeze completed hours so normal recording cannot
    # invalidate an in-progress triangle evaluation.
    first_open_hour = int(time.time() // bots.TRIANGLE_WINDOW_S)
    # A bounded ring of descriptors is built by callers; only one hour's quote
    # snapshots is retained here, including on long recordings.
    for t, q in bots._iter_recorded(0.0, None, last_days=bots.TRIANGLE_OPT_DAYS):
        hour = int(t // bots.TRIANGLE_WINDOW_S)
        if hour >= first_open_hour:
            continue
        if current is not None and hour != current:
            if len(chunk) >= bots.TRIANGLE_MIN_SNAPSHOTS:
                yield chunk
            chunk = []
        current = hour
        chunk.append((t, q))
    if len(chunk) >= bots.TRIANGLE_MIN_SNAPSHOTS:
        yield chunk


def _triangle_windows(count: int) -> tuple[list[dict], dict[str, str], dict[str, str], list[str]]:
    products = bots._triangle_products()
    triangles = bots.triangles_from_products(products)
    hours = []
    for chunk in _recorded_hours():
        start = int(chunk[0][0] // bots.TRIANGLE_WINDOW_S) * bots.TRIANGLE_WINDOW_S
        hours.append({"start": start, "end": start + bots.TRIANGLE_WINDOW_S,
                      "snapshots": len(chunk), "data_fingerprint": _quotes_fingerprint(chunk)})
        hours = hours[-count:]
    if len(hours) < 2 or not triangles:
        return [], {"recorded": "fewer than two usable recorded hour windows or no recorded triangle"}, {}, products
    windows = []
    for i, hour in enumerate(hours):
        for triangle in triangles:
            windows.append({**hour, "key": f"{triangle.name}:{hour['start']}:{hour['end']}",
                            "coin": triangle.name, "split": _split(i, len(hours)), "data_source": "recorded"})
    return windows, {}, {tri.name: "recorded" for tri in triangles}, products


def _limits(windows: Any, days: Any, max_candidates: Any, max_evaluations: Any) -> tuple[int, int, int, int]:
    values = []
    for name, value, lo, hi in (("windows", windows, 2, 24), ("window_days", days, 3, 365),
                                 ("max_candidates", max_candidates, 1, bots.MAX_CANDIDATES),
                                 ("max_evaluations", max_evaluations, 1, MAX_EVALUATIONS)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or not lo <= value <= hi:
            raise ExperimentError(f"{name} must be an integer in [{lo}, {hi}]")
        values.append(int(value))
    return tuple(values)


def _legacy_cutoff(store: ExperimentStore, bot: str) -> float | None:
    """Conservatively fence dates a pre-ledger optimizer could already have seen.

    Legacy aggregates cannot reconstruct every trial. Its execution timestamp is
    an upper bound on its historical observations, so only later windows can be
    called untouched. Brand-new installs have no such fence.
    """
    with _lock(store, "legacy:" + bot):
        path = _root(store) / ("legacy-exposure-" + bot + ".json")
        previous = json.loads(path.read_text()) if path.exists() else {"cutoff": None}
        cutoff = previous["cutoff"]
        hist = bots.optimize_history(bot)
        report = bots.latest_optimize(bot)
        legacy = [row for row in hist.get("log", []) if not row.get("experiment_id")]
        child_reports = report.get("reports") if isinstance(report, dict) else None
        ledger_batch = (isinstance(child_reports, dict) and report.get("source") == "per_coin_ledger_v1"
                        and all(isinstance(child, dict) and child.get("experiment_id")
                                for child in child_reports.values()))
        if report and not report.get("experiment_id") and not ledger_batch:
            legacy.append(report)
        if hist.get("runs", 0) and not hist.get("log"):
            legacy.append({})
        if legacy:
            dates = [float(row["at"]) for row in legacy if isinstance(row.get("at"), (int, float))
                     and math.isfinite(row["at"]) and row["at"] > 0]
            new = max(dates) if len(dates) == len(legacy) else (cutoff or time.time())
            cutoff = max(cutoff or 0.0, new)
        if not path.exists() or cutoff != previous["cutoff"]:
            temporary = path.with_suffix(".tmp")
            temporary.write_text(_canonical({"cutoff": cutoff, "reason": "legacy optimization has no per-cell exposure ledger"}))
            temporary.replace(path)
        return cutoff


@participating
def preview_experiment(bot: str, settings: Any = None, *, space: dict | None = None,
                       coins: Sequence[str] | None = None, windows: int = bots.OPTIMIZE_WINDOWS,
                       window_days: int = bots.OPTIMIZE_WINDOW_DAYS, max_candidates: int = bots.MAX_CANDIDATES,
                       max_evaluations: int = MAX_EVALUATIONS, store: ExperimentStore | None = None,
                       config_coin: str | None = None) -> dict[str, Any]:
    """Read local inputs and return the exact workload; never run a simulator."""
    _SOURCE_EPOCH.verify(_REPO)
    bot = bots._bot(bot)
    windows, window_days, max_candidates, max_evaluations = _limits(windows, window_days, max_candidates, max_evaluations)
    if config_coin is not None and (bot == "triangle" or not coins or len(coins) != 1
                                    or bots._config_coin(config_coin) != bots._config_coin(coins[0])):
        raise ExperimentError("per-coin optimization must target exactly that coin")
    baseline = bots.get_config(bot, config_coin)
    hist = bots.optimize_history(bot, config_coin)
    run_no = hist["runs"] + 1
    if space is None:
        configs = bots.candidates(bot, baseline, run_no, hist["tried"])
        if len(configs) > max_candidates:
            raise ExperimentError(f"{len(configs)} candidates exceed budget {max_candidates}")
        search = {"mode": "native adaptive", "run": run_no, "space": bots.SPACE[bot]}
    else:
        preview = preview_space(bot, baseline, space, coins=1, windows=1,
                                max_candidates=max_candidates, max_evaluations=max_evaluations)
        configs = preview["candidates"]
        search = {"mode": "typed", "space": space, "invalid": preview.get("invalid_combinations", 0), "invalid_examples": preview.get("invalid_examples", [])}
    selected = [] if bot == "triangle" else list(dict.fromkeys(str(c).strip().upper() for c in (coins or bots.available_coins(settings))))
    if any(not c or not c.replace("-", "").isalnum() for c in selected):
        raise ExperimentError("coin names must contain letters, digits or hyphens")
    native_authority(store, coins=selected or ["SOL"])
    if bot == "triangle":
        descriptors, skipped, sources, products = _triangle_windows(windows)
    else:
        descriptors, skipped, sources = _bar_windows(bot, settings, selected, windows, window_days)
        products = []
    explore = sum(w["split"] != "holdout" for w in descriptors)
    holdout = len(descriptors) - explore
    evaluations = explore * len(configs) + holdout * min(2, len(configs))
    if evaluations > max_evaluations:
        raise ExperimentError(f"{evaluations} evaluations exceed budget {max_evaluations}")
    return {"bot": bot, "config_coin": config_coin, "run": run_no, "baseline": baseline, "candidates": configs,
            "candidate_count": len(configs), "configs": len(configs), "windows": descriptors,
            "coins_requested": selected, "coins_used": list(sources), "sources": sources, "skipped": skipped,
            "products": products, "search": search, "settings": _settings(settings),
            "window_count": len(descriptors), "exploration_cells": explore * len(configs),
            "holdout_cells": holdout * min(2, len(configs)), "evaluations": evaluations,
            "budgets": {"max_candidates": max_candidates, "max_evaluations": max_evaluations},
            "ready": bool(descriptors), "window_days": window_days, "requested_windows": windows,
            "holdout_note": "newest half reserved; unseen until one train winner is frozen; fresh relative to recorded local history"}


def prepare_experiment(bot: str, settings: Any = None, **kwargs: Any) -> dict[str, Any]:
    """Persist a complete immutable experiment specification before evaluation."""
    _SOURCE_EPOCH.verify(_REPO)
    store = kwargs.pop("store", None) or ExperimentStore()
    preview = preview_experiment(bot, settings, store=store, **kwargs)
    spec = {**preview, "schema_version": SCHEMA_VERSION, "source": "native",
            "code_fingerprint": _code_fingerprint(), "runtime": _runtime_descriptor(),
            "costs": asdict(bots._costs(settings)),
            "fill_model": "bars:signal-close/next-bar-fill;triangle:later-recorded-quote/three-taker-fees",
            "metric": "pnl_usd" if preview["bot"] == "triangle" else "total_return",
            "metric_units": "USD" if preview["bot"] == "triangle" else "fraction",
            "legacy_cutoff": _legacy_cutoff(store, preview["bot"]),
            "provenance": {"bot": preview["bot"], "interval": "recorded-hour" if preview["bot"] == "triangle" else "1h",
                           "return_unit": "currency" if preview["bot"] == "triangle" else "fraction",
                           "drawdown_unit": "fraction", "currency": "USD", "strategy": preview["bot"] + " simulator",
                           "data_source": "recorded-bid-ask" if preview["bot"] == "triangle" else "cached-hourly-OHLC",
                           "fee_bps": None if preview["bot"] == "triangle" else preview["settings"]["fee_bps"],
                           "slippage_bps": None if preview["bot"] == "triangle" else preview["settings"]["slippage_bps"],
                           "borrow_bps_per_day": 0.0, "fill_delay": None if preview["bot"] == "triangle" else 1}}
    spec["data_fingerprint"] = _digest([{k: row[k] for k in ("key", "data_fingerprint")} for row in spec["windows"]])
    spec["fingerprint"] = _digest(spec)
    _SOURCE_EPOCH.verify(_REPO)
    run_id = store.create_run(spec)
    return store.get_run(run_id)


def _reload_bar(window: dict, settings: Any, loaded: dict[str, dict]) -> dict[str, np.ndarray]:
    coin = window["coin"]
    if coin not in loaded:
        loaded[coin] = bots.hourly(coin, settings)
    arrays = loaded[coin]
    ts = arrays["ts"]
    start = int(np.searchsorted(ts, window["start"], side="right")) - 1
    if start < 0:
        raise ExperimentError(f"historical evidence changed for {window['key']}")
    seg = bots.bridged(arrays, start, max_bars=int((window["end"] - int(ts[start])) // bots.BAR_SECONDS))["bars"]
    keep = (seg["ts"] >= window["start"]) & (seg["ts"] < window["end"])
    seg = {k: v[keep] for k, v in seg.items()}
    if _arrays_fingerprint(seg) != window["data_fingerprint"] or arrays["source"] != window["data_source"]:
        raise ExperimentError(f"historical evidence changed for {window['key']}")
    return seg


def _reload_triangle(window: dict) -> list[tuple[float, dict]]:
    rows = [(t, q) for t, q in bots._iter_recorded(float(window["start"]), float(window["end"]), last_days=None)
            if window["start"] <= t < window["end"]]
    if _quotes_fingerprint(rows) != window["data_fingerprint"]:
        raise ExperimentError(f"historical recorded evidence changed for {window['key']}")
    return rows


def _check_context(spec: dict, settings: Any) -> Any:
    if spec.get("source") != "native" or spec.get("schema_version") != SCHEMA_VERSION:
        raise ExperimentError("only native experiments with a supported schema may execute")
    if _code_fingerprint() != spec["code_fingerprint"]:
        raise ExperimentError("code fingerprint changed; resume refuses stale evidence")
    if _runtime_descriptor() != spec.get("runtime"):
        raise ExperimentError("runtime fingerprint changed; resume refuses evidence from another numerical runtime")
    if settings is None:
        settings = Settings(**spec["settings"])
    if _settings(settings) != spec["settings"] or asdict(bots._costs(settings)) != spec["costs"]:
        raise ExperimentError("settings or cost fingerprint changed; resume refuses stale evidence")
    return settings


def _metrics(bot: str, cfg: dict, data: Any, costs: Any, coin: str, products: list[str]) -> dict:
    if bot != "triangle":
        metrics = bots.run_bars(bot, cfg, data, bots.BACKTEST_INTERVAL, costs)["results"]
    else:
        triangles = [tri for tri in bots.triangles_from_products(products) if tri.name == coin]
        if len(triangles) != 1:
            raise ExperimentError(f"triangle {coin} is absent from frozen products")
        replay = bots.TriangleReplay(bots.TriangleConfig(**cfg), triangles)
        for t, quotes in data:
            replay.feed(t, quotes)
        result = replay.result()
        row = result.per_triangle[coin]
        metrics = {**row, "trades": row["executed"], "snapshots": result.snapshots,
                   "total_return": None, "max_drawdown": None, "sharpe": None,
                   "costs_usd": None, "taker_fee_bps_per_leg": cfg["taker_fee_bps"],
                   "cost_model": "three taker fees and bid/ask spread embedded in cycle edge; separate USD costs unknown",
                   "win_rate": row["wins"] / row["executed"] if row["executed"] else None}
    score = metrics.get("pnl_usd" if bot == "triangle" else "total_return")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
        raise ExperimentError("simulator returned no finite objective metric")
    # Many risk statistics are undefined for a no-trade series. Unknown stays
    # null, while the mandatory objective must be valid or the cell fails.
    return bots._json_safe({"total_return": None, "max_drawdown": None, "trades": None,
                           "costs_usd": None, "sharpe": None, **metrics})


def _halt(store: ExperimentStore, run_id: str) -> bool:
    return store.settle_run(run_id)["status"] in ("paused", "cancelled")


def _evaluate(store: ExperimentStore, run_id: str, spec: dict, settings: Any, descriptors: list[dict],
              indices: list[int], progress: Callable[[float, str], None] | None) -> bool:
    _SOURCE_EPOCH.verify(_REPO)
    completed = {(c["candidate_id"], c["cell_key"]): c for c in store.cells(run_id, include_holdout=True)}
    costs = bots._costs(settings)
    loaded: dict[str, dict] = {}
    last_hour: tuple[float, float] | None = None
    recorded = []
    total = max(1, len(descriptors) * len(indices))
    done = 0
    for window in descriptors:
        _SOURCE_EPOCH.verify(_REPO)
        if _halt(store, run_id):
            return False
        # Verify even fully checkpointed windows. A resumed report must not hide
        # that its historical source changed after those cells completed.
        if spec["bot"] == "triangle":
            hour = (window["start"], window["end"])
            if hour != last_hour:
                recorded = _reload_triangle(window)
                last_hour = hour
            elif _quotes_fingerprint(recorded) != window["data_fingerprint"]:
                raise ExperimentError("recorded window fingerprint mismatch")
            data = recorded
        else:
            data = _reload_bar(window, settings, loaded)
        for index in indices:
            _SOURCE_EPOCH.verify(_REPO)
            if _halt(store, run_id):
                return False
            candidate_id = str(index)
            if (candidate_id, window["key"]) not in completed or completed[(candidate_id, window["key"])]["status"] != "completed":
                record = {"coin": window["coin"], "split": window["split"], "start": window["start"],
                          "end": window["end"], "data_source": window["data_source"],
                          "data_fingerprint": window["data_fingerprint"], "code_fingerprint": spec["code_fingerprint"],
                          "cost_fingerprint": _digest(spec["costs"]), "status": "completed", "metrics": {}, "error": None}
                try:
                    record["metrics"] = _metrics(spec["bot"], spec["candidates"][index], data, costs,
                                                   window["coin"], spec["products"])
                    _SOURCE_EPOCH.verify(_REPO)
                except SourceEpochChanged:
                    raise
                except (ValueError, RuntimeError, ArithmeticError) as exc:
                    record.update(status="failed", metrics={}, error=f"{type(exc).__name__}: {exc}")
                store.record_cell(run_id, candidate_id, window["key"], record)
            done += 1
            fraction = done / total
            message = f"{window['coin']} {window['split']} {done}/{total}"
            store.update_run(run_id, progress={"fraction": fraction, "message": message,
                                               "completed": done, "total": total})
            if progress:
                progress(fraction, message)
    return not _halt(store, run_id)


def _score(cell: dict | None, metric: str) -> float | None:
    if not cell or cell["status"] != "completed":
        return None
    value = cell.get("metrics", {}).get(metric)
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _report(store: ExperimentStore, run_id: str, *, unseal: bool = False) -> dict:
    run = store.get_run(run_id)
    spec = run["spec"]
    cells = store.cells(run_id, include_holdout=unseal or run["status"] == "completed")
    metric = spec["metric"]
    by_key = {(c["cell_key"], c["candidate_id"]): c for c in cells}
    table = []
    for i, cfg in enumerate(spec["candidates"]):
        values = {split: [] for split in ("train", "validation", "holdout")}
        ranks = []
        failures = 0
        for window in spec["windows"]:
            cell = by_key.get((window["key"], str(i)))
            value = _score(cell, metric)
            failures += int(bool(cell and cell["status"] == "failed"))
            if value is not None:
                values[window["split"]].append(value)
            if window["split"] == "train":
                scores = [_score(by_key.get((window["key"], str(j))), metric) for j in range(len(spec["candidates"]))]
                ranks.append(bots._ranks([v if v is not None else -math.inf for v in scores])[i])
        table.append({"index": i, "id": str(i), "current": i == 0, "config": cfg,
                      "changes": {k: v for k, v in cfg.items() if spec["baseline"].get(k) != v},
                      "train_mean_rank": statistics.fmean(ranks) if ranks else None,
                      "train_median": _median(values["train"]), "validation_median": _median(values["validation"]),
                      "test_median": _median(values["holdout"]), "holdout_median": _median(values["holdout"]),
                      "failed_cells": failures, "completed_cells": sum(len(v) for v in values.values())})
    exploration = [w for w in spec["windows"] if w["split"] != "holdout"]
    def has_exploration(candidate_id: str) -> bool:
        present = [w for w in exploration if _score(by_key.get((w["key"], candidate_id)), metric) is not None]
        if spec.get("config_coin"):
            return (bool(exploration) and len(present) >= math.ceil(len(exploration) * 0.8)
                    and {"train", "validation"}.issubset({w["split"] for w in present}))
        return bool(exploration) and len(present) == len(exploration)
    eligible = [row for row in table if row["train_mean_rank"] is not None and row["train_median"] is not None
                and has_exploration(row["id"])]
    winner = min(eligible, key=lambda r: (r["train_mean_rank"], r["index"])) if eligible else table[0]
    best_index = int(run.get("frozen_candidate") or winner["id"])
    best = table[best_index]
    diffs = []
    per_coin = []
    for coin in spec["coins_used"]:
        own = [w for w in spec["windows"] if w["coin"] == coin]
        final = [w for w in own if w["split"] == "holdout"]
        own_diffs, current, picked = [], [], []
        for window in final:
            a = _score(by_key.get((window["key"], "0")), metric)
            b = _score(by_key.get((window["key"], str(best_index))), metric)
            if a is not None and b is not None:
                current.append(a)
                picked.append(b)
                own_diffs.append(b - a)
        diffs.extend(own_diffs)
        per_coin.append({"coin": coin, "data_source": spec["sources"].get(coin), "windows": len(own),
                         "train_windows": sum(w["split"] == "train" for w in own),
                         "validation_windows": sum(w["split"] == "validation" for w in own),
                         "test_windows": len(final), "first_window": _stamp(own[0]["start"]),
                         "last_window_end": _stamp(own[-1]["end"]), "current_test_median": _median(current),
                         "pick_test_median": _median(picked), "pick_wins": sum(d > 1e-12 for d in own_diffs),
                         "pick_losses": sum(d < -1e-12 for d in own_diffs), "coin_best_index": None})
    wins, losses = sum(d > 1e-12 for d in diffs), sum(d < -1e-12 for d in diffs)
    p = bots.sign_test_p(wins, losses)
    improvement = _median(diffs)
    expected = sum(w["split"] == "holdout" for w in spec["windows"])
    paired_exploration = [w for w in exploration
                          if _score(by_key.get((w["key"], "0")), metric) is not None
                          and _score(by_key.get((w["key"], str(best_index))), metric) is not None]
    required_exploration = math.ceil(len(exploration) * 0.8) if spec.get("config_coin") else len(exploration)
    exploration_complete = (has_exploration("0") and has_exploration(str(best_index))
                            and len(paired_exploration) >= required_exploration
                            and (not spec.get("config_coin") or {"train", "validation"}.issubset(
                                {w["split"] for w in paired_exploration})))
    failed = any(c["status"] != "completed" for c in cells)
    reliable = bool(best_index != 0 and run.get("frozen_candidate") is not None and expected > 0
                    and len(diffs) == expected and exploration_complete and len(paired_exploration) == len(exploration)
                    and wins + losses >= bots.MIN_DECIDED_CELLS and p < bots.SIGN_TEST_ALPHA
                    and improvement is not None and improvement > 0)
    incremental = bool(spec.get("config_coin") and best_index != 0 and run.get("frozen_candidate") is not None
                       and expected > 0 and len(diffs) >= math.ceil(expected * 0.8) and exploration_complete
                       and wins + losses >= bots.PER_COIN_MIN_DECIDED_CELLS and wins > losses
                       and improvement is not None and improvement > 0)
    reason = "exploration only: final holdout has not been evaluated"
    if run.get("frozen_candidate") is not None:
        if best_index == 0:
            reason = "the current configuration ranks best on the train windows"
        elif len(diffs) != expected and not incremental:
            reason = "final holdout is incomplete or failed; keep the baseline"
        elif not exploration_complete:
            reason = "the baseline or selected candidate has incomplete exploration evidence"
        elif incremental and not reliable:
            reason = (f"tentative incremental improvement: {wins} wins, {losses} losses across "
                      f"{len(diffs)}/{expected} matched holdout cells (p = {p:.4f}); not statistically confirmed")
        elif wins + losses < bots.MIN_DECIDED_CELLS:
            reason = f"only {wins + losses} test cells differ (need {bots.MIN_DECIDED_CELLS})"
        else:
            reason = f"frozen train winner won {wins}/{wins + losses} final cells (p = {p:.4f}, median {improvement:+.4f})"
    if failed and run.get("frozen_candidate") is None and not exploration_complete:
        reason = "the baseline or selected candidate has incomplete exploration evidence"
    if not spec["windows"]:
        reason = "not enough data to split into train, validation and final holdout windows"
    verdict = {"reliable": reliable, "promotion_eligible": reliable or incremental,
               "confidence": "statistically supported" if reliable else "tentative" if incremental else "insufficient",
               "adopted": False, "saved": False, "changes": [], "best_index": best_index,
               "best_config": best["config"], "best_changes": best["changes"], "test_cells": len(diffs),
               "wins": wins, "losses": losses, "ties": len(diffs) - wins - losses, "p_value": p,
               "median_improvement": improvement, "reason": reason}
    previous = run.get("summary") or {}
    if previous.get("verdict", {}).get("adopted"):
        verdict = previous["verdict"]
    return {"id": run_id, "experiment_id": run_id, "status": run["status"], "bot": spec["bot"], "run": spec["run"],
            "at": run["created_at"], "seconds": round(time.time() - float(run["created_at"]), 1),
            "universe": ("recorded triangles x hour windows" if spec["bot"] == "triangle" else
                         f"{len(spec['coins_requested'])} coins x up to {spec['requested_windows']} windows of {spec['window_days']} days (1h bars)"),
            "coins_requested": spec["coins_requested"], "coins_used": spec["coins_used"],
            "candidates": len(table), "new_candidates": max(0, len(table) - 1),
            "train_cells": sum(w["split"] == "train" for w in spec["windows"]),
            "validation_cells": sum(w["split"] == "validation" for w in spec["windows"]),
            "test_cells": expected, "skipped": spec["skipped"], "space": spec["search"],
            "current": spec["baseline"], "verdict": verdict, "per_coin": per_coin,
            "table": sorted(table, key=lambda r: (r["train_mean_rank"] is None, r["train_mean_rank"] or 0, r["index"])),
            "fingerprint": spec["fingerprint"], "source": "native", "metric": metric, "metric_units": spec["metric_units"],
            "promotion_ready": exploration_complete,
            "failed_cells": sum(c["status"] == "failed" for c in cells), "completed_cells": sum(c["status"] == "completed" for c in cells)}


def _publish(store: ExperimentStore, run_id: str, report: dict) -> dict:
    if store.get_run(run_id)["status"] != "completed":
        report = _report(store, run_id)
    store.update_run(run_id, summary=report)
    return report


@participating
def run_experiment(run_id: str, settings: Any = None, *, final: bool = False, adopt: bool = False,
                   store: ExperimentStore | None = None,
                   progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    """Run or explicitly resume an experiment, checkpointing every evaluation.

    Jobs set pause_requested/cancel_requested durably. The current evaluation
    finishes, commits and then acknowledges the request. A process death releases
    the OS lock and leaves exactly the committed cells available for resumption.
    """
    _SOURCE_EPOCH.verify(_REPO)
    store = store or ExperimentStore()
    native_authority(store)
    with optimizer_lease(store.root), _lock(store, "run:" + run_id):
        run = store.get_run(run_id)
        spec = run["spec"]
        if spec.get("source") != "native":
            raise ExperimentError("only native experiments may execute; imports cannot promote")
        try:
            settings = _check_context(spec, settings)
            if _halt(store, run_id):
                return _publish(store, run_id, _report(store, run_id))
            transition = store.transition_run(run_id, "running", expected=["created", "queued", "starting", "running", "explored", "completed", "failed", "interrupted"])
            if not transition["transition_applied"]:
                _halt(store, run_id)
                return _publish(store, run_id, _report(store, run_id))
            bots._HOURLY_CACHE.clear()
            exploration = [w for w in spec["windows"] if w["split"] != "holdout"]
            if exploration:
                store.reserve_exploration(run_id, [{"coin": w["coin"], "start": w["start"], "end": w["end"]} for w in exploration])
            if not _evaluate(store, run_id, spec, settings, exploration, list(range(len(spec["candidates"]))), progress):
                return _publish(store, run_id, _report(store, run_id))
            transition = store.transition_run(run_id, "explored", expected=["running"])
            if not transition["transition_applied"]:
                _halt(store, run_id)
                return _publish(store, run_id, _report(store, run_id))
            report = _report(store, run_id)
            if not final or not spec["windows"] or not report["promotion_ready"]:
                return _publish(store, run_id, report)
            with _lock(store, "finalization:" + spec["bot"]):
                if _halt(store, run_id):
                    return _publish(store, run_id, _report(store, run_id))
                transition = store.transition_run(run_id, "validating", expected=["explored"])
                if not transition["transition_applied"]:
                    _halt(store, run_id)
                    return _publish(store, run_id, _report(store, run_id))
                index = report["verdict"]["best_index"]
                store.freeze_candidate(run_id, str(index))
                holdout = [w for w in spec["windows"] if w["split"] == "holdout"]
                try:
                    recorded_legacy = _legacy_cutoff(store, spec["bot"])
                    cutoffs = [value for value in (spec.get("legacy_cutoff"), recorded_legacy) if value is not None]
                    legacy = max(cutoffs) if cutoffs else None
                    if legacy is not None and any(w["start"] <= legacy for w in holdout):
                        raise ExperimentError("final holdout is not fresh: legacy optimization already exposed historical dates; use dates after the legacy execution timestamp")
                    store.reserve_holdout(run_id, str(index), [{"coin": w["coin"], "start": w["start"], "end": w["end"]} for w in holdout])
                except ExperimentError as exc:
                    report = _report(store, run_id)
                    report["verdict"].update(reliable=False, reason=f"final holdout refused: {exc}")
                    finished = store.finalize_run(run_id, report)
                    report["status"] = finished["status"]
                    return _publish(store, run_id, report)
                if not _evaluate(store, run_id, spec, settings, holdout, sorted({0, index}), progress):
                    return _publish(store, run_id, _report(store, run_id))
                if _halt(store, run_id):
                    return _publish(store, run_id, _report(store, run_id))
                report = _report(store, run_id, unseal=True)

                def apply_final(candidate: dict) -> dict:
                    verdict = candidate["verdict"]
                    if verdict.get("promotion_eligible", verdict["reliable"]) and adopt and not verdict["adopted"]:
                        token = "experiment " + run_id
                        coin = spec.get("config_coin")
                        current = bots.get_config(spec["bot"], coin)
                        recovered = current == verdict["best_config"] and any(
                            row.get("bot") == spec["bot"] and row.get("coin") == coin and str(row.get("reason", "")).startswith(token + ":")
                            and row.get("config") == current for row in bots._all_configs().get("history", []))
                        if recovered:
                            verdict.update(adopted=True, saved=True, changes=bots._changes(spec["baseline"], current),
                                           saved_to=str(bots.config_path()), recovered=True)
                        elif current != spec["baseline"]:
                            verdict.update(reliable=False, reason="baseline changed since this experiment; adoption refused")
                        else:
                            try:
                                saved = bots.save_config(spec["bot"], verdict["best_config"], merge=False,
                                                         expected=spec["baseline"], reason=token + ": " + verdict["reason"], coin=coin)
                            except bots.BotError as exc:
                                verdict.update(reliable=False, reason=str(exc))
                            else:
                                verdict.update(adopted=True, saved=True, changes=bots._changes(spec["baseline"], saved),
                                               saved_to=str(bots.config_path()))
                    elif verdict.get("promotion_eligible", verdict["reliable"]) and not verdict["adopted"]:
                        verdict["changes_not_saved"] = bots._changes(spec["baseline"], verdict["best_config"])
                    candidate["status"] = "completed"
                    return candidate

                # SQLite serializes the last control request and promotion. A
                # crash after the atomic config write rolls the SQL back; the
                # exact config-history token recovers that receipt on resume.
                finished = store.finalize_run(run_id, report, apply=apply_final)
                if finished["status"] != "completed":
                    return _publish(store, run_id, _report(store, run_id))
                return finished["summary"]
        except Exception as exc:
            # Requests remain authoritative even when a simulator/source fails.
            store.settle_run(run_id, status="failed",
                             expected=["created", "queued", "starting", "running", "explored",
                                       "validating", "finalizing", "failed", "interrupted"],
                             error=f"{type(exc).__name__}: {exc}")
            raise


def optimize(bot: str, settings: Any = None, *, coins: Sequence[str] | None = None,
             windows: int = bots.OPTIMIZE_WINDOWS, window_days: int = bots.OPTIMIZE_WINDOW_DAYS,
             adopt: bool = True, progress: Callable[[float, str], None] | None = None,
             config_coin: str | None = None) -> dict[str, Any]:
    """Compatibility entry point: every legacy search uses the durable guard."""
    store = ExperimentStore()
    bot = bots._bot(bot)
    # Serialize legacy history numbering without holding the finalization lock.
    with _lock(store, "legacy-optimization:" + bot):
        run = prepare_experiment(bot, settings, coins=coins, windows=windows, window_days=window_days, store=store,
                                 config_coin=config_coin)
        run_id = run["id"]
        spec = run["spec"]
        started = time.time()
        cand_rows = [{"index": i, "changes": {k: v for k, v in cfg.items() if spec["baseline"].get(k) != v}}
                     for i, cfg in enumerate(spec["candidates"])]

        def report(frac: float, message: str) -> None:
            bots.runtime().progress[bot] = {"fraction": frac, "message": message, "at": time.time(),
                                           "run": spec["run"], "candidates": cand_rows, "started": started,
                                           "done": False, "experiment_id": run_id}
            if progress:
                progress(frac, message)

        report(0.0, f"run {spec['run']}: {len(cand_rows)} configurations")
        out = run_experiment(run_id, settings, final=True, adopt=adopt, store=store, progress=report)
        finished = out["status"] in ("completed", "explored")
        report(1.0 if finished else 0.0, out["verdict"]["reason"])
        bots.runtime().progress[bot]["done"] = finished
        if finished:
            hist = bots.optimize_history(bot, config_coin)
            hist["runs"] = spec["run"]
            hist["tried"] = list(dict.fromkeys(hist["tried"] + [bots._cfg_key(c) for c in spec["candidates"]]))[-5000:]
            hist["log"] = (hist["log"] + [{"run": spec["run"], "at": time.time(), "experiment_id": run_id,
                                           "candidates": len(cand_rows), "adopted": out["verdict"]["adopted"],
                                           "changes": out["verdict"]["changes"]}])[-100:]
            bots._write_json(bots.history_path(bot, config_coin), hist)
        bots._write_json(bots.optimize_path(bot), out)
        return out

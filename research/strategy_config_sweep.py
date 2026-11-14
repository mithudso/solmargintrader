"""Resumable, parallel CPCV sweep over every active cached coin and buildable card.

This command reads cached candles only. Use ``--plan`` first; fetching is a
separate, explicit command. Results are append-only JSONL under the selected
output directory and are flushed after every completed configuration.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from collections import OrderedDict
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import (
    CsvLoader,
    frame_to_arrays,
    resolve_data_dir,
    validate_bars,
)
from backtester.core.assets import REMOVED_ASSETS
from backtester.core.strategies import build
from backtester.core.strategy_cards import load_all
from soltui.bgqueue import Job, build_queue
from soltui.bgworker import evaluate, failed_result
from soltui.config import Settings
from soltui.runner import engine_config, select_contiguous

MIN_CONFIGURATIONS = 10
ASSET_FILE = re.compile(r"^([A-Z0-9][A-Z0-9._-]*)_(1m|1h|1d)\.csv$")
_ARRAYS: OrderedDict[tuple[str, str, str, str], dict[str, Any]] = OrderedDict()
_SELECTIONS: dict[tuple[str, str, str, str], dict[str, Any] | None] = {}
_OUTPUT_LOCK_HANDLE = None


def _hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temp_name = handle.name
            json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def discover_assets(data_dir: Path) -> dict[str, dict[str, Path]]:
    """Find active candle assets, excluding funding, unrelated, and removed symbols."""
    found: dict[str, dict[str, Path]] = {}
    if not data_dir.is_dir():
        return found
    for path in data_dir.iterdir():
        match = ASSET_FILE.fullmatch(path.name)
        if match and path.is_file():
            asset, interval = match.groups()
            if asset not in REMOVED_ASSETS:
                found.setdefault(asset, {})[interval] = path.resolve()
    return dict(sorted(found.items()))


def _derived_interval(source: Path, asset: str, interval: str, output_dir: Path) -> Path:
    """Aggregate only complete UTC 1m buckets; never fill or invent candles."""
    import pandas as pd

    target = output_dir / "derived" / f"{asset}_{interval}.csv"
    source_bytes = source.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    marker = target.with_suffix(target.suffix + ".source.json")
    try:
        saved = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError, AttributeError):
        saved = None
    if target.exists() or marker.exists():
        if (not isinstance(saved, dict) or saved.get("sha256") != source_hash
                or saved.get("aggregation_version") != 4 or not target.is_file()
                or saved.get("derived_sha256") != _hash(target)):
            raise ValueError("derived cache checksum or binding changed; choose a new output directory")
        return target
    raw = pd.read_csv(io.BytesIO(source_bytes))
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(raw.columns) or raw.empty:
        raise ValueError(f"invalid one-minute cache for {asset}")
    # The prior aggregator sorted the source before resampling. Preserve that
    # behavior and discard only byte-equivalent duplicate bars. Conflicting
    # rows at one timestamp remain invalid and fail the normal bar validator.
    source_rows = len(raw)
    raw = raw.drop_duplicates().reset_index(drop=True)
    raw = validate_bars(
        raw.sort_values("timestamp", kind="stable").reset_index(drop=True),
        "1m",
        strict_gaps=False,
    )
    if (raw["timestamp"] % 60 != 0).any():
        raise ValueError(f"one-minute cache has unaligned timestamps for {asset}")
    size = 60 if interval == "1h" else 1440
    bucket_seconds = 3600 if interval == "1h" else 86400
    raw["_bucket"] = raw["timestamp"] // bucket_seconds * bucket_seconds
    raw["_minute"] = (raw["timestamp"] - raw["_bucket"]) // 60
    counts = raw.groupby("_bucket")["_minute"].count()
    minimums = raw.groupby("_bucket")["_minute"].min()
    maximums = raw.groupby("_bucket")["_minute"].max()
    complete_buckets = counts.index[
        (counts == size) & (minimums == 0) & (maximums == size - 1)
    ]
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], unit="s", utc=True)
    raw = raw.set_index("timestamp").sort_index()
    # A fixed 24h frequency with epoch origin is explicitly UTC aligned; the
    # calendar-day alias ignores `origin` and emits a timezone warning.
    rule = "1h" if interval == "1h" else "24h"
    grouped = raw.resample(rule, origin="epoch", label="left", closed="left")
    bars = grouped.agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    bars = bars.loc[
        [int(stamp.timestamp()) in complete_buckets for stamp in bars.index]
    ].dropna()
    if bars.empty:
        raise ValueError(f"one-minute cache has no complete {interval} bars for {asset}")
    # pandas may store datetime64 at microsecond or nanosecond resolution.
    # Timestamp.timestamp() normalizes either representation to epoch seconds.
    bars.insert(0, "timestamp", [int(stamp.timestamp()) for stamp in bars.index])
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    derived_bytes = bars.to_csv(index=False).encode("utf-8")
    temp.write_bytes(derived_bytes)
    os.replace(temp, target)
    _atomic_json(marker, {"source": source.name, "sha256": source_hash, "interval": interval,
                          "aggregation_version": 4,
                          "derived_sha256": hashlib.sha256(derived_bytes).hexdigest(),
                          "aggregation": "complete UTC buckets only", "source_rows": source_rows,
                          "exact_duplicate_rows_removed": source_rows - len(raw),
                          "derived_rows": len(bars)})
    return target


def available_files(asset: str, files: dict[str, Path], output_dir: Path, *, derive: bool):
    available = {interval: files[interval] for interval in ("1h", "1d") if interval in files}
    unavailable = {}
    if derive and "1m" in files:
        for interval in ("1h", "1d"):
            if interval not in available:
                try:
                    available[interval] = _derived_interval(files["1m"], asset, interval, output_dir)
                except ValueError as exc:
                    unavailable[interval] = str(exc)
    elif "1m" in files:
        for interval in ("1h", "1d"):
            if interval not in available:
                available[interval] = output_dir / "derived" / f"{asset}_{interval}.csv"
    return available, unavailable


def _source_fingerprint() -> dict[str, str]:
    paths = [p for folder in ("backtester", "soltui", "research")
             for p in (REPO / folder).rglob("*.py") if "tests" not in p.relative_to(REPO).parts]
    return {str(p.relative_to(REPO)): _hash(p) for p in sorted(paths)}


def _historical_base_settings(data_dir: Path) -> dict[str, Any]:
    """Use history-independent settings for CPCV folds with empty gate state."""
    return asdict(Settings(data_dir=str(data_dir.resolve()), min_confidence=0.0))


def _profiles() -> list[tuple[str, dict[str, float | int]]]:
    """Conservative engine sensitivity cases for cards with too few tunables."""
    return [
        ("fill-delay-2", {"fill_delay": 2}), ("fill-delay-3", {"fill_delay": 3}),
        ("fees-1.5x", {"fee_bps": 9.0, "slippage_bps": 3.0}),
        ("fees-2x", {"fee_bps": 12.0, "slippage_bps": 4.0}),
        ("borrow-1.5x", {"borrow_long_bps_hour": 1.2, "borrow_short_bps_hour": 0.225}),
        ("borrow-2x", {"borrow_long_bps_hour": 1.6, "borrow_short_bps_hour": 0.3}),
        ("fees-1.5x-fill-2", {"fee_bps": 9.0, "slippage_bps": 3.0, "fill_delay": 2}),
        ("fees-2x-fill-2", {"fee_bps": 12.0, "slippage_bps": 4.0, "fill_delay": 2}),
        ("borrow-1.5x-fill-2", {"borrow_long_bps_hour": 1.2, "borrow_short_bps_hour": 0.225, "fill_delay": 2}),
        ("borrow-2x-fill-2", {"borrow_long_bps_hour": 1.6, "borrow_short_bps_hour": 0.3, "fill_delay": 2}),
    ]


def _config_id(job: Job, profile: str, overrides: dict[str, Any]) -> str:
    raw = json.dumps({"job_id": job.job_id, "profile": profile, "settings": overrides},
                     sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def build_jobs(assets: dict[str, dict[str, Path]], output_dir: Path, *, derive: bool = True):
    cards = load_all()
    jobs: list[dict[str, Any]] = []
    coverage: dict[str, dict[str, Any]] = {}
    for asset, source_files in assets.items():
        files, unavailable = available_files(asset, source_files, output_dir, derive=derive)
        if not files:
            coverage[asset] = {"state": "unsupported", "reason": "no usable complete hourly/daily series",
                               "unavailable_intervals": unavailable}
            continue
        candidates = build_queue(asset, cards=cards)
        runnable = []
        invalid = []
        for job in candidates:
            expected_interval = "1h" if job.interval == "1h" else "1d"
            if expected_interval not in files:
                continue
            try:
                build(job.strategy, **dict(job.params))
            except (ValueError, TypeError, KeyError) as exc:
                invalid.append({"strategy": job.strategy, "job_id": job.job_id,
                                "reason": f"{type(exc).__name__}: {exc}"[:200]})
                continue
            runnable.append((job, files[expected_interval]))
        by_strategy: dict[str, list[tuple[Job, Path]]] = {}
        for item in runnable:
            by_strategy.setdefault(item[0].strategy, []).append(item)
        coverage[asset] = {"state": "ready", "source_intervals": sorted(source_files),
                           "evaluation_intervals": sorted(files), "strategies": {},
                           "invalid_configurations": invalid, "unavailable_intervals": unavailable}
        for strategy in sorted(c.registry_key for c in cards.values() if c.buildable and c.data_available):
            variants = by_strategy.get(strategy, [])
            selected = [(job, path, "strategy-parameters", {}) for job, path in variants]
            base_count = len(selected)
            if selected and base_count < MIN_CONFIGURATIONS:
                template, data_path, _, _ = selected[0]
                seen = {_config_id(job, profile, setting) for job, _, profile, setting in selected}
                for profile, setting in _profiles():
                    config_id = _config_id(template, profile, setting)
                    if config_id in seen:
                        continue
                    selected.append((template, data_path, "engine-sensitivity:" + profile, setting))
                    seen.add(config_id)
                    if len(selected) >= MIN_CONFIGURATIONS:
                        break
            coverage[asset]["strategies"][strategy] = {
                "configurations": len(selected), "strategy_parameter_configurations": base_count,
                "engine_sensitivity_configurations": len(selected) - base_count,
                "state": "ready" if len(selected) >= MIN_CONFIGURATIONS else "insufficient_valid_configurations",
            }
            for job, data_path, profile, overrides in selected:
                job_data = {"strategy": job.strategy, "horizon": job.horizon, "asset": job.asset,
                            "interval": job.interval, "params": dict(job.params), "tier": job.tier,
                            "variation": job.variation, "likelihood": job.likelihood, "family": job.family}
                jobs.append({"job": job_data, "data_path": str(data_path),
                             "profile": profile, "setting_overrides": overrides,
                             "configuration_id": _config_id(job, profile, overrides)})
    return jobs, coverage


def _cached_arrays(task: dict[str, Any], settings: Settings):
    cache_key = (task["data_path"], task["job"]["asset"], task["job"]["interval"], settings.start + "|" + settings.end)
    arrays = _ARRAYS.get(cache_key)
    if arrays is None:
        job = task["job"]
        frame = CsvLoader(task["data_path"], allow_gaps=True).load(
            job["asset"], settings.start or None, settings.end or None, job["interval"])
        arrays, selection = select_contiguous(frame_to_arrays(frame), job["interval"], longest=True)
        _ARRAYS[cache_key] = arrays
        _SELECTIONS[cache_key] = selection
        while len(_ARRAYS) > 2:
            expired, _ = _ARRAYS.popitem(last=False)
            _SELECTIONS.pop(expired, None)
    else:
        _ARRAYS.move_to_end(cache_key)
    return arrays


def _evaluate_task(task: dict[str, Any], base_settings: dict[str, Any]) -> dict[str, Any]:
    job = Job(**task["job"])
    settings = replace(Settings(**base_settings), **task["setting_overrides"])
    try:
        arrays = _cached_arrays(task, settings)
        result = evaluate(job, arrays, engine_config(settings, job.interval), settings)
    except Exception as exc:  # noqa: BLE001 - each deterministic failure is a durable result
        result = failed_result(job, exc)
    value = asdict(result)
    metric_names = ("median_sharpe", "iqr", "frac_positive", "median_return", "seconds", "finished_at")
    non_finite = [name for name in metric_names
                  if isinstance(value.get(name), float) and not math.isfinite(value[name])]
    if non_finite:
        for name in non_finite:
            value[name] = None
        value["evaluable"] = False
        suffix = "non_finite_metric: " + ", ".join(non_finite)
        value["reason"] = (value.get("reason", "") + "; " + suffix).strip("; ")[:200]
    cache_key = (task["data_path"], job.asset, job.interval, settings.start + "|" + settings.end)
    value.update(configuration_id=task["configuration_id"], execution_profile=task["profile"],
                 setting_overrides=task["setting_overrides"], data_path=task["data_path"],
                 data_selection=_SELECTIONS.get(cache_key))
    return value


def _read_done(path: Path) -> set[str]:
    done: set[str] = set()
    if not path.exists():
        return done
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
                if isinstance(row.get("configuration_id"), str):
                    done.add(row["configuration_id"])
            except (ValueError, AttributeError):
                continue
    return done


def _record(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # An interrupted write may leave one incomplete final JSONL record. Keep
    # every newline-terminated result and remove only that uncommitted tail.
    if path.exists() and path.stat().st_size:
        with path.open("r+b") as handle:
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) != b"\n":
                position = path.stat().st_size
                while position:
                    start = max(0, position - 8192)
                    handle.seek(start)
                    chunk = handle.read(position - start)
                    newline = chunk.rfind(b"\n")
                    if newline >= 0:
                        handle.truncate(start + newline + 1)
                        break
                    position = start
                else:
                    handle.truncate(0)
                handle.flush()
                os.fsync(handle.fileno())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _preflight_manifest(path: Path, *, data_dir: Path, sources: dict[str, str],
                        code: dict[str, str], base_settings: dict[str, Any]) -> None:
    """Reject incompatible output before deriving or replacing cached inputs."""
    results_path = path.parent / "results.jsonl"
    if not path.exists():
        if results_path.exists() and results_path.stat().st_size:
            raise ValueError("existing results have no manifest; choose a new --output-dir")
        derived = path.parent / "derived"
        if derived.is_dir() and any(derived.rglob("*")):
            raise ValueError("existing derived artifacts have no manifest; choose a new --output-dir")
        return
    old = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 2,
        "data_dir": str(data_dir.resolve()),
        "sources": sources,
        "code": code,
        "base_settings": base_settings,
        "historical_confidence_policy": (
            "min_confidence=0 for CPCV: each historical fold starts with no resolved-outcome "
            "history, so the prospective confidence gate cannot warm up; confidence gating "
            "remains enabled for paper and forward testing"
        ),
        "forward_testing_started": False,
    }
    if any(old.get(key) != value for key, value in expected.items()):
        raise ValueError(f"existing manifest at {path} does not match current code/data/settings; choose a new --output-dir")


def _lock_output(path: Path) -> None:
    """Keep two invocations from evaluating and appending the same jobs."""
    global _OUTPUT_LOCK_HANDLE
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            if not handle.read(1):
                handle.seek(0)
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, BlockingIOError) as exc:
        handle.close()
        raise SystemExit(f"another sweep is using {path.parent}") from exc
    _OUTPUT_LOCK_HANDLE = handle


def _summarize(rows_path: Path, coverage: dict[str, Any], total: int) -> dict[str, Any]:
    rows = []
    if rows_path.exists():
        with rows_path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    counts = {"completed": len(rows), "evaluable": 0, "rankable": 0, "insufficient": 0, "failed": 0}
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        counts["evaluable"] += bool(row.get("evaluable"))
        can_rank = bool(row.get("evaluable")) and int(row.get("trades", 0)) >= 10
        counts["rankable"] += can_rank
        if can_rank:
            grouped.setdefault((row["asset"], row["strategy"]), []).append(row)
        elif row.get("reason", "").startswith(("FileNotFoundError:", "ValueError:", "TypeError:", "RuntimeError:", "KeyError:")):
            counts["failed"] += 1
        else:
            counts["insufficient"] += 1
    shortlist = []
    for (asset, strategy), candidates in sorted(grouped.items()):
        top = sorted(candidates, key=lambda row: row["median_sharpe"], reverse=True)[:3]
        shortlist.append({"asset": asset, "strategy": strategy, "candidates": [
            {"configuration_id": row["configuration_id"], "horizon": row["horizon"],
             "params": row["params"], "execution_profile": row["execution_profile"],
             "oos_cpcv_median_sharpe": row["median_sharpe"], "trades": row["trades"],
             "median_return": row["median_return"], "frac_positive": row["frac_positive"]}
            for row in top]})
    return {"schema_version": 1, "configurations_planned": total, "counts": counts,
            "coverage": coverage, "oos_shortlist": shortlist,
            "ranking_rule": "out-of-sample CPCV median Sharpe; minimum 10 trades; shortlist only, no forward test started"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=resolve_data_dir())
    parser.add_argument("--output-dir", type=Path,
                        default=Path.home() / ".local/share/solmargintrader/research/strategy-config-sweep")
    parser.add_argument("--assets", default="", help="comma-separated symbols; default discovers all cached 1m/1h/1d coins")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    parser.add_argument("--limit", type=int, default=None,
                        help="evaluate at most N pending configurations, then resume with the same command")
    parser.add_argument("--plan", action="store_true", help="show coverage and configuration count without writing or evaluating")
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be nonnegative")
    discovered = discover_assets(args.data_dir)
    requested = [part.strip().upper() for part in args.assets.split(",") if part.strip()]
    assets = {name: discovered[name] for name in requested if name in discovered} if requested else discovered
    missing = sorted(set(requested) - set(discovered))
    if missing:
        print("No cached candle data for: " + ", ".join(missing))
    if not assets:
        print(f"No supported candle caches found in {args.data_dir}")
        return 2
    if not args.plan:
        _lock_output(args.output_dir / ".sweep.lock")
    source_hashes = {str(path): _hash(path) for values in assets.values() for path in values.values()}
    source_code = _source_fingerprint()
    base_settings = _historical_base_settings(args.data_dir)
    manifest_path = args.output_dir / "manifest.json"
    if not args.plan:
        try:
            _preflight_manifest(manifest_path, data_dir=args.data_dir, sources=source_hashes,
                                code=source_code, base_settings=base_settings)
        except (OSError, ValueError, AttributeError, json.JSONDecodeError) as exc:
            print(str(exc))
            return 3
    # Planning does not write aggregate files. For minute-only coins it reports
    # potential intervals; execution validates complete-bucket availability.
    jobs, coverage = build_jobs(assets, args.output_dir, derive=not args.plan)
    manifest = {"schema_version": 2, "data_dir": str(args.data_dir.resolve()),
                "sources": source_hashes, "code": source_code, "jobs": jobs, "coverage": coverage,
                "base_settings": base_settings,
                "historical_confidence_policy": (
                    "min_confidence=0 for CPCV: each historical fold starts with no resolved-outcome "
                    "history, so the prospective confidence gate cannot warm up; confidence gating "
                    "remains enabled for paper and forward testing"
                ),
                "configuration_count": len(jobs), "minimum_per_strategy_coin": MIN_CONFIGURATIONS,
                "forward_testing_started": False}
    if args.plan:
        per_asset = sum(len(v.get("strategies", {})) for v in coverage.values())
        print(f"coins discovered: {len(assets)}; potential strategy/coin pairs: {per_asset}; "
              f"potential configurations: {len(jobs)}; workers: {args.workers}")
        for asset, detail in coverage.items():
            states = [v for v in detail.get("strategies", {}).values() if v["state"] != "ready"]
            print(f"  {asset}: {detail['state']}; {len(detail.get('evaluation_intervals', []))} intervals; "
                  f"{len(detail.get('strategies', {}))} strategies; under-floor pairs: {len(states)}")
        print("Minute-only derived intervals are checked for complete UTC buckets when execution starts; "
              "the final manifest records any skipped interval or coin.")
        return 0
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old != manifest:
            print(f"The existing manifest at {manifest_path} does not match current code/data/settings. Choose a new --output-dir; old results were preserved.")
            return 3
    else:
        _atomic_json(manifest_path, manifest)
    results_path = args.output_dir / "results.jsonl"
    done = _read_done(results_path)
    pending = [task for task in jobs if task["configuration_id"] not in done]
    if args.limit is not None:
        pending = pending[:args.limit]
    print(f"CPCV sweep: {len(jobs)} configurations; {len(done)} recorded; {len(pending)} pending; {args.workers} worker processes")
    base_settings = manifest["base_settings"]
    if pending:
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            iterator = iter(pending)
            inflight: dict[concurrent.futures.Future, dict[str, Any]] = {}
            for _ in range(min(len(pending), args.workers * 2)):
                task = next(iterator, None)
                if task is not None:
                    inflight[pool.submit(_evaluate_task, task, base_settings)] = task
            finished = len(done)
            while inflight:
                future = next(concurrent.futures.as_completed(inflight))
                task = inflight.pop(future)
                try:
                    row = future.result()
                except Exception as exc:  # noqa: BLE001 - preserve one failed result per task
                    job = Job(**task["job"])
                    row = asdict(failed_result(job, exc)) | {
                        "configuration_id": task["configuration_id"], "execution_profile": task["profile"],
                        "setting_overrides": task["setting_overrides"], "data_path": task["data_path"]}
                _record(results_path, row)
                finished += 1
                if finished % 100 == 0 or finished == len(jobs) or row.get("reason", "").startswith("FileNotFoundError:"):
                    print(f"[{finished}/{len(jobs)}] {row['asset']} {row['strategy']} {row['horizon']} "
                          f"{row['execution_profile']} — {'ok' if row['evaluable'] else 'not evaluable'}",
                          flush=True)
                next_task = next(iterator, None)
                if next_task is not None:
                    inflight[pool.submit(_evaluate_task, next_task, base_settings)] = next_task
    summary = _summarize(results_path, coverage, len(jobs))
    _atomic_json(args.output_dir / "summary.json", summary)
    print(f"Results: {results_path}\nSummary: {args.output_dir / 'summary.json'}")
    print(json.dumps(summary["counts"], sort_keys=True))
    return 0 if args.limit is not None or not pending or summary["counts"]["completed"] >= len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

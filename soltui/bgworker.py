"""The background backtest worker: a separate, low-priority process.

    python3 -m soltui.bgworker --asset SOL
    python3 -m soltui.bgworker --asset SOL --horizons medium --max-tier 1 --limit 50

Run directly it is a normal foreground script; the TUI launches it through
`bgcontrol.start()`, which is what applies the background scheduling policy.

## Why a process and not a thread

`runner.py` already runs a sweep on a worker thread, and that is right for a
sweep you start and wait for. This one is different: it is meant to grind for
hours while you use the machine for something else. Lowering priority is the
whole point, and priority on Unix is a property of a *process* -- calling
`os.nice()` on a thread inside the TUI would demote the UI along with the sweep.
A separate process also means a crash here cannot take the console down with it,
and the sweep survives closing the TUI.

## Restartability is the design constraint

A background job is never "finished", it is interrupted -- by a reboot, by a
laptop lid, by the user. So every job's result is flushed to disk the moment it
is computed. Startup skips existing ids only when their settings, price files,
and evaluation code still match the persisted proof. Batching writes would be
faster and would throw away an hour of work on a power cut.

## What this deliberately does not do

No network, no orders, no fetching. `CLAUDE.md` puts fetching behind an explicit
separate step (`backtester.core.fetch`), and a background process that quietly
pulled data would be exactly the kind of unattended network access that rule
exists to prevent. A missing price file is reported, never repaired.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import tempfile
import time
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import numpy as np  # noqa: E402

from backtester.core.data import CsvLoader, frame_to_arrays  # noqa: E402
from backtester.core.engine import EngineConfig  # noqa: E402
from backtester.core.strategies import build  # noqa: E402
from backtester.core.strategy_cards import HORIZONS  # noqa: E402

from . import bgcontrol, bgqueue  # noqa: E402
from .bgqueue import (  # noqa: E402
    PID_PATH,
    RESULTS_PATH,
    STATE_PATH,
    Job,
    JobResult,
    QueueState,
    append_result,
    build_queue,
    completed_ids,
    ensure_dir,
    pending,
    read_results,
    validate_asset,
    write_state,
)
from .config import Settings, load_settings  # noqa: E402
from .research_admission import admit_read, participating
from .runner import engine_config, run_cpcv  # noqa: E402

# The nicest a process can ask to be. Set unconditionally at startup rather than
# relying on the launcher, so a hand-run worker is polite too. Note this is only
# half the story on macOS -- see bgcontrol.start() for the QoS half.
NICE_LEVEL = 19


def evaluation_code_fingerprint() -> dict[str, str]:
    """Hash local execution sources without importing or running them."""
    sources = [path for component in ("backtester", "research", "soltui")
               for path in (REPO / component).rglob("*.py")
               if "tests" not in path.relative_to(REPO).parts]
    # These cards supply the queue's presets and therefore form part of its inputs.
    sources.extend((REPO / "backtester" / "strategy_cards").glob("*.md"))
    return {str(path.relative_to(REPO)): _file_hash(path) for path in sorted(sources)}


def _file_hash(path: Path) -> str:
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def evaluation_proof(settings: Settings, jobs: Sequence[Job]) -> dict[str, Any]:
    """The settings, exact price inputs, and source code behind one sweep."""
    data: dict[str, str | None] = {}
    for job in jobs:
        path = (Path(settings.data_dir) / f"{job.asset}_{job.interval}.csv").resolve()
        if str(path) not in data:
            try:
                data[str(path)] = _file_hash(path)
            except FileNotFoundError:
                data[str(path)] = None
    return {
        "settings": {
            name: getattr(settings, name)
            for name in (
                "start", "end", "capital", "fee_bps", "slippage_bps",
                "fill_delay", "cpcv_groups", "cpcv_k", "fee_schedule",
                "use_leverage", "leverage", "allow_short", "min_confidence",
                "borrow_long_bps_hour", "borrow_short_bps_hour",
            )
        },
        "data": data,
        "code": evaluation_code_fingerprint(),
    }


class EvaluationProofMismatch(ValueError):
    """A historical result cannot be combined with this evaluation context."""


def verify_evaluation_proof(
    asset: str, settings: Settings, jobs: Sequence[Job], results: Sequence[JobResult],
    results_path: Path, *, persist: bool = True,
) -> dict[str, Any]:
    """Refuse incompatible historical rows; atomically bind new rows to proof.

    Results stay append-only. An old file without proof needs a fresh output
    path; adopting it would falsely assert which code and inputs produced it.
    Each asset has its own proof because assets share the default results file.
    """
    proof = evaluation_proof(settings, jobs)
    evaluation_id = hashlib.sha256(
        json.dumps(proof, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    path = results_path.with_name(results_path.name + ".proof.json")
    manifest: dict[str, Any] = {"version": 1, "assets": {}}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        pass
    except (ValueError, OSError) as exc:
        raise EvaluationProofMismatch(f"unreadable evaluation proof at {path}; use --results-path for a fresh file") from exc
    if not isinstance(manifest, dict) or manifest.get("version") != 1 or not isinstance(manifest.get("assets"), dict):
        raise EvaluationProofMismatch(f"invalid evaluation proof at {path}; use --results-path for a fresh file")
    expected = {"evaluation_id": evaluation_id, "proof": proof}
    if any(row.asset == asset for row in results) and manifest["assets"].get(asset) != expected:
        raise EvaluationProofMismatch(
            f"evaluation proof is missing or differs for {asset} at {results_path}; "
            "preserve this history and use --results-path for a fresh file"
        )
    if persist and manifest["assets"].get(asset) != expected:
        manifest["assets"][asset] = expected
        ensure_dir(path.parent)
        temporary: str | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
                temporary = handle.name
                json.dump(manifest, handle, sort_keys=True, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
    return proof


def _validate_limit(limit: int | None) -> None:
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("limit must be a non-negative integer")


def _limit_argument(raw: str) -> int:
    try:
        value = int(raw)
        _validate_limit(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("limit must be a non-negative integer") from exc
    return value


class EvaluationContextChanged(ValueError):
    """The input file changed while the worker was loading its arrays."""


def _check_price_input(proof: dict[str, Any], job: Job, settings: Settings) -> None:
    path = (Path(settings.data_dir) / f"{job.asset}_{job.interval}.csv").resolve()
    try:
        actual = _file_hash(path)
    except FileNotFoundError:
        actual = None
    if proof["data"].get(str(path)) != actual:
        raise EvaluationContextChanged(f"evaluation context changed while loading {path}; restart with a fresh results path")


class _Stop:
    """Cooperative stop flag, set from a signal handler.

    A signal handler must do almost nothing, so it flips a bool and returns. The
    loop checks it at a job boundary, which is the only place stopping is
    coherent: killing mid-CPCV would leave a partial evaluation that could not be
    written and would be recomputed on resume anyway.
    """

    def __init__(self, control: bgcontrol.WorkerControl | None = None) -> None:
        self._requested = False
        self.control = control

    @property
    def requested(self) -> bool:
        if not self._requested and self.control is not None:
            self._requested = self.control.stop_requested()
        return self._requested

    @requested.setter
    def requested(self, value: bool) -> None:
        self._requested = value

    def install(self) -> None:
        """Catch the signals a supervisor or a Ctrl-C actually sends."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle)

    def _handle(self, signum: int, frame: Any) -> None:  # noqa: ARG002
        self.requested = True


def lower_priority(level: int = NICE_LEVEL) -> int:
    """Ask for the lowest priority the OS will grant, returning what it granted.

    `setpriority` rather than `os.nice`, because `nice()` is *relative* -- calling
    it twice, or calling it under a launcher that already adjusted the value,
    compounds rather than sets. An absolute target is what "as low as possible"
    actually means.

    The return value is a readback, not the request. The two can differ -- a
    scheduler is free to clamp -- and reporting the request would be reporting a
    wish. Using the relative `os.nice()` here instead is what made an earlier
    version land on 5 under `taskpolicy -b` while claiming 19.

    Never fatal: a sandbox that refuses the call should still get its backtests.
    """
    try:
        os.setpriority(os.PRIO_PROCESS, 0, level)
    except (OSError, AttributeError, ValueError):
        pass
    try:
        return os.getpriority(os.PRIO_PROCESS, 0)
    except (OSError, AttributeError):
        return 0


class ArrayCache:
    """Price arrays per (asset, interval), loaded once.

    The queue is ordered by promise, not by interval, so consecutive jobs jump
    between 1h and 1d. Re-reading and re-parsing a CSV per job would dominate the
    runtime of the cheap strategies.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[tuple[str, str], dict[str, np.ndarray]] = {}

    def get(self, asset: str, interval: str) -> dict[str, np.ndarray]:
        """Arrays for one series, loading on first use."""
        key = (asset.upper(), interval)
        if key not in self._cache:
            path = Path(self.settings.data_dir) / f"{key[0]}_{interval}.csv"
            if not path.exists():
                raise FileNotFoundError(
                    f"no price cache at {path} — run: python3 -m backtester.core.fetch "
                    f"--asset {key[0]} --interval {interval}"
                )
            loader = CsvLoader(path, allow_gaps=True)
            df = loader.load(
                key[0], self.settings.start or None, self.settings.end or None, interval
            )
            self._cache[key] = frame_to_arrays(df)
        return self._cache[key]


def evaluate(
    job: Job, arrays: dict[str, np.ndarray], cfg: EngineConfig, settings: Settings
) -> JobResult:
    """CPCV-evaluate one job into a writable result row.

    Mirrors `runner.SweepRunner._evaluate` on purpose: the background sweep and
    the in-app sweep must not disagree about what a given configuration scored,
    and the way to guarantee that is to call the same evaluator with the same
    geometry rather than to re-derive one here.
    """
    started = time.monotonic()
    res = run_cpcv(
        job.label,
        lambda: build(job.strategy, **job.params),
        arrays,
        cfg,
        settings,
    )
    return JobResult(
        job_id=job.job_id,
        strategy=job.strategy,
        horizon=job.horizon,
        asset=job.asset,
        interval=job.interval,
        params=dict(job.params),
        tier=job.tier,
        variation=job.variation,
        family=job.family,
        median_sharpe=float(res.median_sharpe),
        iqr=float(res.spread),
        frac_positive=float(res.frac_positive),
        median_return=float(res.median_return),
        trades=int(res.total_trades),
        evaluable=not res.insufficient,
        reason=res.reason,
        seconds=round(time.monotonic() - started, 3),
        finished_at=time.time(),
    )


def failed_result(job: Job, exc: BaseException) -> JobResult:
    """A result row recording that this job could not be evaluated.

    Written rather than skipped so a resumed worker does not retry a job that
    fails deterministically -- otherwise a single bad configuration blocks the
    queue on every restart. It is marked not-evaluable, so it can never reach the
    leaderboard.
    """
    return JobResult(
        job_id=job.job_id,
        strategy=job.strategy,
        horizon=job.horizon,
        asset=job.asset,
        interval=job.interval,
        params=dict(job.params),
        tier=job.tier,
        variation=job.variation,
        family=job.family,
        median_sharpe=0.0,
        iqr=0.0,
        frac_positive=0.0,
        median_return=0.0,
        trades=0,
        evaluable=False,
        reason=f"{type(exc).__name__}: {exc}"[:200],
        finished_at=time.time(),
    )


@participating
def run(
    asset: str,
    *,
    horizons: Sequence[str] = HORIZONS,
    max_tier: int = 2,
    limit: int | None = None,
    strategies: Sequence[str] | None = None,
    settings: Settings | None = None,
    results_path: Path = RESULTS_PATH,
    state_path: Path = STATE_PATH,
    stop: _Stop | None = None,
    recovered_from: str = "",
    recovery_note: str = "",
) -> QueueState:
    """Work the queue until it is empty, the limit is hit, or a stop is asked.

    Returns the final state, which is also the last thing written to disk.
    """
    _validate_limit(limit)
    settings = settings or load_settings()
    stop = stop or _Stop()
    ensure_dir(state_path.parent)

    # Validated before it can reach a file path; `build_queue` also validates,
    # but the symbol is used below to label state, so normalise it here too.
    asset = validate_asset(asset)
    jobs = build_queue(asset, horizons=horizons, max_tier=max_tier, strategies=strategies)
    results = read_results(results_path)
    admit_read(asset, source="bg:" + str(results_path.resolve()), attempts=len(jobs))
    proof = verify_evaluation_proof(asset, settings, jobs, results, results_path)
    already = completed_ids(results)
    todo = pending(jobs, already)
    if limit is not None:
        todo = todo[:limit]

    state = QueueState(
        phase="running",
        results_path=str(results_path),
        recovered_from=recovered_from,
        recovery_note=recovery_note,
        done=0,
        total=len(todo),
        asset=asset,
        pid=os.getpid(),
        started_at=time.time(),
        updated_at=time.time(),
    )
    write_state(state, state_path)
    if not todo:
        state.phase = "done"
        state.current = ""
        state.updated_at = time.time()
        write_state(state, state_path)
        return state

    cache = ArrayCache(settings)
    # Intervals whose price file is missing. The queue interleaves 1h and 1d
    # jobs by promise, so an absent SOL_1h.csv used to abort the entire sweep on
    # the first hourly job and abandon every runnable daily one. A missing series
    # disqualifies its own interval and nothing else.
    missing: dict[str, str] = {}
    checked_intervals: set[str] = set()
    evaluated = 0
    for index, job in enumerate(todo, start=1):
        if stop.requested:
            state.phase = "stopped"
            break
        state.done = index
        if job.interval in missing:
            continue
        state.current = job.label
        state.interval = job.interval
        state.updated_at = time.time()
        write_state(state, state_path)
        print(f"[{index}/{len(todo)}] backtesting {job.label} ({job.interval})", flush=True)
        try:
            if job.interval not in checked_intervals:
                _check_price_input(proof, job, settings)
            arrays = cache.get(job.asset, job.interval)
            if job.interval not in checked_intervals:
                _check_price_input(proof, job, settings)
                checked_intervals.add(job.interval)
            result = evaluate(job, arrays, engine_config(settings, job.interval), settings)
        except EvaluationContextChanged:
            raise
        except FileNotFoundError as exc:
            # Not this job's fault, and it will hit every job at this interval --
            # so record it once and skip the rest of that interval rather than
            # writing one identical failure row per job.
            missing[job.interval] = str(exc)
            state.error = "; ".join(sorted(missing.values()))
            print(f"  skipped {job.interval}: price data unavailable", flush=True)
            continue
        except Exception as exc:  # noqa: BLE001 - one bad config must not end the sweep
            result = failed_result(job, exc)
            print(f"  failed: {type(exc).__name__}", flush=True)
        else:
            print("  finished", flush=True)
        append_result(result, results_path)
        evaluated += 1
    else:
        # Reaching the end having evaluated nothing, because every interval's
        # data was missing, is a failed sweep -- not a successful sweep of zero
        # jobs. Reporting "done" there would show an empty leaderboard with no
        # indication that the cause was a missing file.
        state.phase = "error" if (missing and evaluated == 0) else "done"

    state.current = ""
    state.updated_at = time.time()
    write_state(state, state_path)
    return state


def build_parser() -> argparse.ArgumentParser:
    """CLI surface."""
    p = argparse.ArgumentParser(
        prog="python3 -m soltui.bgworker",
        description="Low-priority background backtest sweep, most promising first.",
    )
    p.add_argument("--asset", default="SOL", help="asset symbol (default: SOL)")
    p.add_argument(
        "--horizons",
        nargs="+",
        default=list(HORIZONS),
        choices=list(HORIZONS),
        help="parameter scales to sweep (default: all)",
    )
    p.add_argument(
        "--max-tier",
        type=int,
        default=2,
        help="0 = card presets only, 1 = +near variations, 2 = +half/double",
    )
    p.add_argument("--limit", type=_limit_argument, default=None, help="stop after N jobs")
    p.add_argument("--strategies", nargs="+", default=None, metavar="NAME",
                   help="only these registry names (default: every buildable card)")
    p.add_argument("--data-dir", type=Path, help="use this candle cache instead of Settings")
    p.add_argument("--results-path", type=Path, default=RESULTS_PATH,
                   help="append results here; choose a fresh file when evaluation proof differs")
    p.add_argument(
        "--plan",
        action="store_true",
        help="print the queue and exit without evaluating anything",
    )
    return p


def _prior_input_note(path: Path, asset: str) -> str:
    """Describe labeled synthetic inputs without inferring which results used them."""
    try:
        proof = json.loads(path.with_name(path.name + ".proof.json").read_text(encoding="utf-8"))
        inputs = proof["assets"][validate_asset(asset)]["proof"]["data"]
        labeled = [name for name in inputs if "synthetic" in name.lower()]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ""
    return ("Previous proof includes an input path labeled synthetic: " + ", ".join(labeled)) if labeled else ""


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point."""
    args = build_parser().parse_args(argv)

    settings = load_settings()
    if args.data_dir is not None:
        settings = replace(settings, data_dir=str(args.data_dir.resolve()))

    if args.plan:
        jobs = build_queue(args.asset, horizons=args.horizons, max_tier=args.max_tier,
                           strategies=args.strategies)
        results = read_results(args.results_path)
        verify_evaluation_proof(validate_asset(args.asset), settings, jobs, results,
                                args.results_path, persist=False)
        done = completed_ids(results)
        todo = pending(jobs, done)
        print(f"{len(jobs)} jobs, {len(jobs) - len(todo)} already done, {len(todo)} pending")
        for job in todo[:40]:
            print(f"  tier {job.tier}  {job.likelihood:<9}  {job.label}  {job.params}")
        if len(todo) > 40:
            print(f"  … and {len(todo) - 40} more")
        return 0

    # When spawned by `bgcontrol.start` the liveness lock is already held on an
    # inherited descriptor, and re-taking it here would DEADLOCK against
    # ourselves -- flock conflicts between two descriptors even inside one
    # process. Run by hand, we must take it, so that a hand-run sweep and a
    # TUI-run sweep cannot both append to one results file.
    lock_fd = bgcontrol.inherited_lock(os.environ.get(bgcontrol.LOCK_FD_ENV))
    owned_lock = lock_fd is None
    if owned_lock:
        lock_fd = bgcontrol.acquire_lock()
        if lock_fd is None:
            print(
                "a background sweep is already running — stop it before starting "
                "another, or they will both append to the same results file",
                file=sys.stderr,
            )
            return 1

    pid_written = False
    control: bgcontrol.WorkerControl | None = None
    try:
        level = lower_priority()
        ensure_dir()
        control = bgcontrol.inherited_control(
            lock_fd, os.environ.get(bgcontrol.CONTROL_FD_ENV), consume=True,
        )
        if control is None:
            control = bgcontrol.create_control(lock_fd)
        stop = _Stop(control=control)
        stop.install()
        PID_PATH.write_text(str(os.getpid()), encoding="utf-8")
        pid_written = True
        print(f"soltui background sweep — pid {os.getpid()}, priority {level}", flush=True)
        # Recover only the selected UI sweep. Explicit CLI paths keep their fail-closed contract.
        selected = not owned_lock and args.results_path == bgqueue.active_results_path()
        recovered_from = ""
        recovery_note = ""
        marker = args.results_path.with_name(args.results_path.name + ".recovery.json")
        try:
            recovery = json.loads(marker.read_text(encoding="utf-8"))
            recovered_from = str(recovery.get("recovered_from", ""))
            recovery_note = str(recovery.get("source_note", ""))
        except (OSError, ValueError, AttributeError):
            pass
        options = dict(horizons=args.horizons, max_tier=args.max_tier, limit=args.limit,
                       strategies=args.strategies, settings=settings, stop=stop)
        try:
            state = run(args.asset, results_path=args.results_path, recovered_from=recovered_from,
                        recovery_note=recovery_note, **options)
        except EvaluationProofMismatch:
            if not selected:
                raise
            old_path = args.results_path
            recovery_note = _prior_input_note(old_path, args.asset)
            args.results_path = bgcontrol.select_fresh_results(recovered_from=old_path, source_note=recovery_note)
            recovered_from = str(old_path)
            print(f"Evaluation proof changed. Preserved {old_path}; continuing separately at {args.results_path}",
                  flush=True)
            state = run(args.asset, results_path=args.results_path, recovered_from=str(old_path),
                        recovery_note=recovery_note, **options)
    except Exception as exc:  # noqa: BLE001 - report, never a bare traceback to a log
        write_state(
            QueueState(
                phase="error",
                results_path=str(args.results_path),
                recovered_from=locals().get("recovered_from", ""),
                recovery_note=locals().get("recovery_note", ""),
                error=f"{type(exc).__name__}: {exc}",
                pid=os.getpid(),
                updated_at=time.time(),
            )
        )
        traceback.print_exc()
        return 1
    finally:
        try:
            if pid_written:
                PID_PATH.unlink(missing_ok=True)
        finally:
            try:
                if control is not None:
                    control.close()
            finally:
                if owned_lock and lock_fd is not None:
                    os.close(lock_fd)
    print(f"{state.phase}: {state.done}/{state.total} evaluated", flush=True)
    return 0 if state.phase in ("done", "stopped") else 1


if __name__ == "__main__":
    raise SystemExit(main())

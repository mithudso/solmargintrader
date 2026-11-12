"""Explicit, recoverable optimization processes. No service starts on import.

A run survives closing its window or the console. Pause/cancel requests live in
SQLite and the runner acknowledges them after committing the current cell. The
launcher lease is inherited by the child, so process death releases ownership
without trusting a PID or a stale 'running' flag. A detached reaper never calls UI.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import re
import signal
import sqlite3
import subprocess
import sys
import threading
import traceback
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any

from . import config
from .config import Settings
from .experiments import ExperimentError, ExperimentStore

_ACTIVE = {"created", "running", "validating", "finalizing", "pause_requested", "cancel_requested"}
_TERMINAL = {"completed", "failed", "cancelled", "paused", "interrupted", "explored", "validated"}


def _paths(store: ExperimentStore, run_id: str) -> tuple[Path, Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
        raise ExperimentError("invalid experiment identifier")
    root = Path(store.root) / "jobs"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root / f"{run_id}.lease", root / f"{run_id}.log", root / f"{run_id}.settings.json"


def active(store: ExperimentStore, run_id: str) -> bool:
    store.get_run(run_id)
    lease, _, _ = _paths(store, run_id)
    with lease.open("a+b") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fh, fcntl.LOCK_UN)
    return False


@contextmanager
def _native_idle(store: ExperimentStore, run_id: str):
    # Direct runners acquire the native lock without the detached-job lease.
    # Keep that exclusion until reconciliation has finished its state mutation.
    from .experiment_runner import _lock

    with ExitStack() as ownership:
        try:
            ownership.enter_context(_lock(store, "run:" + run_id))
        except ExperimentError:
            busy = True
        else:
            busy = False
        yield busy


def status(store: ExperimentStore, run_id: str) -> dict[str, Any]:
    lease, log, settings_path = _paths(store, run_id)
    # Keep the lease while reconciling. A new launcher cannot acquire it
    # between our liveness observation and the stale-state update.
    with lease.open("a+b") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            busy = True
            run = store.get_run(run_id)
        else:
            with _native_idle(store, run_id) as busy:
                run = store.get_run(run_id)
                stale = run["status"] in {"running", "validating", "finalizing", "pause_requested", "cancel_requested"}
                stale = stale or (run["status"] == "created" and settings_path.exists())
                if stale and not busy:
                    state = {"pause_requested": "paused", "cancel_requested": "cancelled"}.get(run["status"], "interrupted")
                    message = run.get("error") or "worker no longer holds its process lease; completed cells were preserved"
                    if log.exists():
                        with log.open("rb") as output:
                            output.seek(max(0, log.stat().st_size - 2000))
                            message += "\n" + output.read().decode("utf-8", errors="replace").strip()
                    run = store.settle_run(run_id, status=state, expected=[run["status"]],
                                           error=message if state == "interrupted" else None)
            fcntl.flock(fh, fcntl.LOCK_UN)
    run["worker_active"] = busy
    run["log_path"] = str(log)
    if log.exists():
        with log.open("rb") as fh:
            fh.seek(max(0, log.stat().st_size - 8000))
            run["log_tail"] = fh.read().decode("utf-8", errors="replace")
    else:
        run["log_tail"] = ""
    return run


def request(store: ExperimentStore, run_id: str, action: str) -> dict[str, Any]:
    if action not in {"pause", "cancel"}:
        raise ExperimentError("control must be pause or cancel")
    run = status(store, run_id)
    if run["spec"].get("source", "native") != "native":
        raise ExperimentError("imported evidence has no native worker")
    # Store applies a compare-and-set transaction. A completion racing this
    # request remains completed rather than being reopened as pause_requested.
    store.request_control(run_id, action)
    return status(store, run_id)


def _settings(settings: Settings) -> dict[str, Any]:
    # Evaluation settings only: public wallet addresses and unrelated UI state
    # have no reason to appear in a process handoff or its logs.
    names = ("asset", "capital", "fee_bps", "slippage_bps", "fill_delay", "start", "end", "interval")
    return {**{name: getattr(settings, name) for name in names},
            "data_dir": str(Path(settings.data_dir).resolve())}


def _reap(proc: subprocess.Popen, store: ExperimentStore, run_id: str) -> None:
    code = proc.wait()
    try:
        lease, log, _ = _paths(store, run_id)
        with lease.open("a+b") as fh:
            try:
                fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return  # A later explicit launch now owns this experiment.
            with _native_idle(store, run_id) as busy:
                if busy:
                    return
                run = store.get_run(run_id)
                if run["status"] in _ACTIVE:
                    tail = ""
                    if log.exists():
                        with log.open("rb") as output:
                            output.seek(max(0, log.stat().st_size - 2000))
                            tail = output.read().decode("utf-8", errors="replace").strip()
                    message = f"worker exited with status {code}; completed cells remain available"
                    if tail:
                        message += "\n" + tail
                    store.settle_run(run_id, status="interrupted" if code else "failed",
                                     expected=tuple(_ACTIVE), error=message)
            fcntl.flock(fh, fcntl.LOCK_UN)
    except (OSError, sqlite3.Error, ExperimentError) as exc:
        # The OS lease still makes a later status query recover process death.
        logging.getLogger(__name__).warning("Could not persist experiment exit state: %s", exc)


def launch(store: ExperimentStore, run_id: str, settings: Settings, *, final: bool = False,
           adopt: bool = False) -> dict[str, Any]:
    run = store.get_run(run_id)
    if run["spec"].get("source", "native") != "native":
        raise ExperimentError("TradingView imports cannot execute or adopt native configurations")
    if adopt and not final:
        raise ExperimentError("adoption requires explicit final holdout validation")
    lease, log, settings_path = _paths(store, run_id)
    fd = os.open(lease, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ExperimentError("experiment already has an active worker") from None
        from .experiment_runner import run_active
        if run_active(run_id, store=store):
            raise ExperimentError("experiment already has an active native runner")
        run = store.get_run(run_id)
        if run["status"] in {"completed", "validated"}:
            verdict = (run.get("summary") or {}).get("verdict") or {}
            if not (final and adopt and verdict.get("reliable") and not verdict.get("adopted")):
                raise ExperimentError("this experiment is complete; only adopting its already validated reliable pick is allowed")
        previous = run["status"]
        settings_path.write_text(json.dumps(_settings(settings), allow_nan=False))
        settings_path.chmod(0o600)
        argv = [sys.executable, "-m", "soltui.experiment_jobs", "--worker", run_id,
                "--root", str(Path(store.root).resolve()), "--settings", str(settings_path.resolve()),
                "--lease-fd", str(fd)]
        if final:
            argv.append("--final")
        if adopt:
            argv.append("--adopt")
        claimed = store.transition_run(run_id, "created", expected=[previous])
        if not claimed["transition_applied"]:
            raise ExperimentError(f"launch superseded by {claimed['status']}; resume explicitly")
        store.update_run(run_id, error="")
        try:
            with log.open("ab") as output:
                output.write(b"\n--- explicit experiment worker launch ---\n")
                output.flush()
                if store.get_run(run_id)["status"] != "created":
                    raise ExperimentError("launch superseded by a pause/cancel request; resume explicitly")
                proc = subprocess.Popen(argv, cwd=Path(__file__).resolve().parent.parent,
                                        stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                                        start_new_session=True, pass_fds=(fd,),
                                        env={**os.environ, "SOLTUI_CONFIG_DIR": str(config.CONFIG_DIR.resolve())})
        except OSError as exc:
            # A control request arriving while Popen fails remains authoritative.
            store.transition_run(run_id, previous, expected=["created"])
            store.update_run(run_id, error=f"worker could not start: {exc}")
            raise ExperimentError(f"worker could not start: {exc}") from exc
        threading.Thread(target=_reap, args=(proc, store, run_id), daemon=True,
                         name=f"experiment-reap-{run_id[:12]}").start()
    finally:
        # Do NOT explicitly LOCK_UN here: parent and child share the same open
        # file description. Closing our copy leaves the child's lease held.
        os.close(fd)
    return status(store, run_id)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--settings", required=True)
    parser.add_argument("--lease-fd", type=int, required=True)
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--adopt", action="store_true")
    args = parser.parse_args(argv)
    store = ExperimentStore(Path(args.root))
    # The fd belongs to this worker until process exit; validate before any
    # state change so a direct malformed invocation cannot claim a run.
    os.fstat(args.lease_fd)

    def interrupted(signum: int, frame: Any) -> None:
        del signum, frame
        store.request_control(args.worker, "pause")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        from .experiment_runner import run_experiment
        settings = Settings(**json.loads(Path(args.settings).read_text()))
        run_experiment(args.worker, settings, final=args.final, adopt=args.adopt, store=store)
        return 0
    except Exception as exc:  # noqa: BLE001 - process boundary persists diagnostics before a nonzero exit
        store.settle_run(args.worker, status="failed", expected=tuple(_ACTIVE),
                         error=f"{type(exc).__name__}: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

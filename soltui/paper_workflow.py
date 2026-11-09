"""One explicit paper-workflow action, reusing independently owned shared jobs.

Status is a bounded file read. Only ensure launches the coordinator. Stopping
this coordinator does not stop previously existing Council, recorder, batch,
prediction or optimizer owners. It never arms or submits a live order.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import signal
import re
import json
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing

from . import config, live_tools

REPO = live_tools.REPO
FIELDS = ("asset", "capital", "fee_schedule", "fee_bps", "slippage_bps", "fill_delay", "cpcv_groups", "cpcv_k",
          "data_dir", "start", "end", "use_leverage", "leverage", "allow_short", "min_confidence",
          "borrow_long_bps_hour", "borrow_short_bps_hour", "enabled_strategies", "roster", "signal_defaults")


def root():
    return config.CONFIG_DIR / "paper-workflow"


def status(asset=None):
    value = live_tools.read(root() / "state.json", {}) or {"state": "stopped", "mode": "paper", "stages": {},
        "message": "Start the paper workflow to run assessments, forward tests and validated optimization."}
    value["running"] = live_tools.locked(root() / "worker.lock")
    if not value["running"] and value["state"] in ("starting", "running", "stopping"):
        value["state"] = "interrupted"
    value["requested_asset"] = asset
    cached = live_tools.read(root() / "batch-progress.json")
    if cached:
        value["batch"] = cached
    return value


def refresh_progress(asset=None):
    """Read-model work only: bounded real progress for the existing F5 owner."""
    from . import f5_batch
    value = status(asset)
    run_id = value.get("stages", {}).get("backtests_and_forward_batch", {}).get("result", {}).get("run_id")
    directories = []
    if run_id and re.fullmatch(r"[0-9a-f]{32}", str(run_id)):
        directories = [f5_batch._root() / run_id]
    elif f5_batch._root().exists():
        import itertools
        candidates = [p for p in itertools.islice(f5_batch._root().iterdir(), 128) if p.is_dir() and re.fullmatch(r"[0-9a-f]{32}", p.name)]
        directories = [p for p in candidates if live_tools.locked(p / "worker.lock")][:1]
    for directory in directories:
        path = directory / "batch.sqlite3"
        if not path.exists():
            continue
        try:
            with closing(live_tools.connect_readonly(path, budget=.5)) as db:
                metadata = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM meta WHERE key IN ('phase','assets','intervals','current','error','notice')")}
                counts = {state: count for state, count in db.execute("SELECT state,count(*) FROM cell GROUP BY state")}
                checks = [dict(zip(("asset", "interval", "at", "recorded", "error", "message"), row)) for row in db.execute(
                    "SELECT asset,interval,at,recorded,error,message FROM forward_check ORDER BY at DESC LIMIT 8")]
            running = live_tools.locked(directory / "worker.lock")
            result = {"run_id": directory.name, "as_of": time.time(), "running": running,
                      "phase": metadata.get("phase"), "counts": counts, "total": sum(counts.values()), "forward_checks": checks,
                      "assets": metadata.get("assets", []), "intervals": metadata.get("intervals", []),
                      "current": metadata.get("current"), "message": metadata.get("error") or metadata.get("notice"),
                      "source": str(path)}
            if not running and result["phase"] in ("backtesting", "forward", "forward_partial", "forward_waiting", "forward_partial_waiting"):
                result["phase"] = "interrupted"
            live_tools.write(root() / "batch-progress.json", result)
            value["batch"] = result
        except Exception as exc:
            value["batch_read_error"] = f"Batch progress unavailable ({type(exc).__name__})"
        break
    return value


def ensure(settings, asset, scope="all"):
    if scope not in ("all", "selected"):
        raise ValueError("Choose all or selected workflow scope")
    with live_tools.control(root()):
        if live_tools.locked(root() / "worker.lock"):
            return {**status(asset), "message": "A paper workflow coordinator already runs; no duplicate started."}
        previous = status(asset)
        reuse = previous.get("asset") == asset and previous.get("scope") == scope
        token = uuid.uuid4().hex
        state = {"mode": "paper", "state": "starting", "asset": asset, "scope": scope, "token": token,
                 "started_at": time.time(), "stages": previous.get("stages", {}) if reuse else {},
                 "message": "Starting paper assessments and reusing existing shared workers.",
                 "notice": "Historical backtests, forward paper results and wallet balances are separate. No profitability guarantee or live order."}
        if reuse and previous.get("grid_assessment"):
            state["grid_assessment"] = previous["grid_assessment"]
        handle = (root() / "worker.lock").open("a+b")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            live_tools.write(root() / "state.json", state)
            live_tools.write(root() / "control.json", {"stop": False})
            live_tools.write(root() / "settings.json", {key: getattr(settings, key) for key in FIELDS})
            with (root() / "worker.log").open("ab") as log:
                process = subprocess.Popen([sys.executable, "-m", "soltui.paper_workflow", "--lock-fd", str(handle.fileno()), "--token", token],
                    cwd=REPO, env={**os.environ, "SOLTUI_CONFIG_DIR": str(config.CONFIG_DIR.resolve())},
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, pass_fds=(handle.fileno(),))
        except BlockingIOError:
            return status(asset)
        except BaseException as exc:
            live_tools.write(root() / "state.json", {**state, "state": "failed", "message": f"Coordinator launch failed ({type(exc).__name__})"})
            raise
        finally:
            handle.close()
        threading.Thread(target=process.wait, daemon=True, name="paper-workflow-reaper").start()
        return status(asset)


def stop():
    with live_tools.control(root()):
        live_tools.write(root() / "control.json", {"stop": True})
    return {**status(), "message": "Coordinator will stop after the current assessment; independent shared workers continue."}


def run(settings, state, stopped):
    from . import bots, council, f5_batch, prediction_recovery, bot_scheduler, coinbase_account
    stages = state.setdefault("stages", {})
    def should_stop():
        if (live_tools.read(root() / "control.json", {}) or {}).get("stop"):
            stopped.set()
        return stopped.is_set()
    def publish():
        live_tools.write(root() / "state.json", state)
    def stage(name, function):
        if should_stop():
            return False
        state.update(state="running", current=name, message=f"Paper workflow: {name}.")
        stages[name] = {**stages.get(name, {}), "state": "running", "at": time.time()}
        publish()
        try:
            value = function()
            phase = "failed" if value.get("state") == "failed" else "waiting" if value.get("state") == "paused" or value.get("running") is False else "completed"
            stages[name] = {"state": phase, "at": time.time(), "result": value}
        except Exception as exc:
            stages[name] = {"state": "failed", "at": time.time(), "error": f"{type(exc).__name__}: {str(exc)[:200]}"}
        publish()
        return not should_stop()

    def batch():
        existing = next((r for r in f5_batch.list_runs() if r.get("running")), None)
        if existing:
            return {"run_id": existing["run_id"], "running": True, "reused": True, "phase": existing.get("phase"),
                    "assets": existing.get("assets", []), "message": "Existing batch preserved; no duplicate backtests started."}
        previous = stages.get("backtests_and_forward_batch", {}).get("result", {}).get("run_id")
        if previous:
            worker = f5_batch.start(previous)
            return {"run_id": previous, "running": True, "reused": True, "worker": worker,
                    "message": "Resuming the workflow's original frozen batch; no duplicate batch created."}
        if state["scope"] == "all":
            try:
                f5_batch.catalog_coins()
            except ValueError:
                coinbase_account.download_spot_pairs()
        plan = f5_batch.create(settings, coins=[state["asset"]] if state["scope"] == "selected" else None, longest_contiguous=True)
        worker = f5_batch.start(plan["run_id"])
        return {"run_id": plan["run_id"], "running": True, "reused": False, "assets": plan["assets"], "worker": worker,
                "message": "Backtests proceed on frozen original continuous windows, then prospective paper checks continue."}

    def predictions():
        from . import commands
        context = commands.Context.from_settings(settings, commands.Runtime())
        result = commands.dispatch("forwardtest.ensure", {"asset": state["asset"], "manual": True}, ctx=context, quiet=True)
        if not result["ok"]:
            raise RuntimeError(result["error"]["message"])
        return result["result"]

    def grid():
        existing = live_tools.grid_metadata()
        if existing:
            return {"reused": True, "session_id": existing.get("id"), "asset": existing.get("asset"),
                    "running": existing.get("stopped_at") is None,
                    "message": "Existing grid start, configuration and costs preserved; an explicit prior Stop is retained."}
        started = bots.forward_start("grid", state["asset"], settings, preserve_existing=True)
        record = started["forward"]
        return {"reused": started.get("reused", False), "session_id": record.get("id"), "asset": record.get("asset"),
                "running": record.get("stopped_at") is None,
                "message": "Existing grid preserved under its shared lock." if started.get("reused") else "Paper grid forward test started."}

    def assessment():
        session = live_tools.grid_metadata()
        asset = session["asset"] if session else state["asset"]
        cfg = session["config"] if session else bots.get_config("grid", asset)
        proof = {"asset": asset, "config": cfg, "fee_bps": session.get("fee_bps") if session else settings.fee_bps,
                 "slippage_bps": session.get("slippage_bps") if session else settings.slippage_bps,
                 "start": settings.start, "end": settings.end, "data_dir": str(settings.data_dir), "replay_revision": live_tools.REPLAY_REVISION}
        from pathlib import Path
        inputs = [Path(settings.data_dir) / f"{asset}_{interval}.csv" for interval in ("1h", "1m")]
        proof["inputs"] = {}
        for path in inputs:
            if path.exists():
                with path.open("rb") as handle:
                    proof["inputs"][str(path.resolve())] = hashlib.file_digest(handle, "sha256").hexdigest()
            else:
                proof["inputs"][str(path.resolve())] = None
        previous = state.get("grid_assessment")
        if previous and previous.get("proof") == proof:
            return {**previous["result"], "reused": True, "message": "Matching historical assessment retained; the saved forward test is independent."}
        # This stage evaluates the actual saved grid rather than substituting a
        # historical winning coin or overwriting the ongoing paper session.
        import dataclasses
        effective = dataclasses.replace(settings, fee_bps=proof["fee_bps"], slippage_bps=proof["slippage_bps"])
        result = bots.backtest("grid", asset, effective, config=cfg)
        after = {}
        for path in inputs:
            if path.exists():
                with path.open("rb") as handle:
                    after[str(path.resolve())] = hashlib.file_digest(handle, "sha256").hexdigest()
            else:
                after[str(path.resolve())] = None
        if after != proof["inputs"]:
            raise RuntimeError("Historical input changed during assessment; the workflow will not reuse an unbound result")
        compact = {key: result.get(key) for key in ("id", "bot", "asset", "start", "end", "interval", "results", "source", "message")}
        state["grid_assessment"] = {"proof": proof, "result": compact}
        return compact

    def optimizer():
        current = bot_scheduler.status()
        if current.get("running"):
            return {"reused": True, "running": True, "phase": current.get("phase"), "gates": live_tools.OPTIMIZER_GATES}
        started = bot_scheduler.start()
        return {"reused": False, "worker": {key: started.get(key) for key in ("running", "pid", "phase", "error")}, "gates": live_tools.OPTIMIZER_GATES}

    def council_start():
        before = council.status()
        result = before if before.get("running") else council.start()
        return {"reused": before.get("running", False), "mode": "paper", "state": result.get("state"),
                "running": result.get("running"), "message": result.get("message"), "owner": result.get("owner"),
                "asset": result.get("config", {}).get("asset"), "execution": result.get("config", {}).get("execution")}

    actions = (("backtests_and_forward_batch", batch), ("prediction_producer", predictions),
               ("grid_forward", grid), ("grid_historical_assessment", assessment),
               ("council_paper", council_start), ("validated_optimizer", optimizer))
    for name, function in actions:
        if not stage(name, function):
            break
    waiting = any(v["state"] == "waiting" for v in stages.values())
    state.update(state="stopped" if stopped.is_set() else "partial" if any(v["state"] == "failed" for v in stages.values()) else "waiting" if waiting else "ready",
                 current=None, finished_at=time.time(), message="Coordinator stopped; independent shared workers continue." if stopped.is_set()
                 else "Paper workflow prepared; a retained Stop or readiness condition is still waiting." if waiting
                 else "Paper workflow prepared. Live statuses show workers, coverage, confidence and optimization gates.")
    publish()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-fd", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    handle = os.fdopen(args.lock_fd, "a+b")
    actual, expected = os.fstat(handle.fileno()), (root() / "worker.lock").stat()
    state = live_tools.read(root() / "state.json", {}) or {}
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino) or state.get("token") != args.token:
        handle.close()
        return 1
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    settings = config.Settings(**(live_tools.read(root() / "settings.json", {}) or {}))
    stopped, done = threading.Event(), threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    def monitor():
        while not done.wait(.2):
            if (live_tools.read(root() / "control.json", {}) or {}).get("stop"):
                stopped.set()
    watcher = threading.Thread(target=monitor, daemon=True, name="paper-workflow-control")
    watcher.start()
    try:
        if (live_tools.read(root() / "control.json", {}) or {}).get("stop"):
            stopped.set()
        run(settings, state, stopped)
    finally:
        done.set()
        watcher.join(2)
        handle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

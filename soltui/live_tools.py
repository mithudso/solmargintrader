"""Bounded read-only rail snapshots and an independently owned read-model worker.

Polling never replays a bot, contacts a wallet provider or starts a trading/test
workflow. Explicit rail_refresh warms local caches from already saved activity.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import inspect
import json
import math
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing, contextmanager
from pathlib import Path

from . import config, bots, council, live_score, prediction_recovery, portfolio

REPO = Path(__file__).resolve().parent.parent
MAX_JSON = 512_000
REPLAY_REVISION = hashlib.sha256(Path(bots.__file__).read_bytes() + Path(inspect.getfile(bots.GridConfig)).read_bytes()).hexdigest()
OPTIMIZER_GATES = {"manual_mode_blocks_adoption": True, "tentative_min_decisions": 3,
    "tentative_min_coverage": .8, "tentative_positive_median": True,
    "tentative_more_wins_than_losses": True, "confirmed_min_decisions": 10, "confirmed_sign_test_p": .05,
    "notice": "Tentative adoption is not statistically confirmed. No profitability guarantee."}


def root():
    return config.CONFIG_DIR / "live-tools"


def read(path: Path, default=None):
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_JSON + 1)
        value = json.loads(raw) if len(raw) <= MAX_JSON else default
        return value if isinstance(value, dict) else default
    except (OSError, ValueError, RecursionError):
        return default


def write(path: Path, value):
    encoded = json.dumps(value, allow_nan=False, sort_keys=True)
    if len(encoded.encode()) > MAX_JSON:
        raise ValueError("Read-model record exceeds the bounded cache size")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(encoded, encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def control(directory: Path):
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "control.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def locked(path: Path):
    try:
        with path.open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return False
            except BlockingIOError:
                return True
    except FileNotFoundError:
        return False


def connect_readonly(path: Path, budget=.3):
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=.1)
    deadline = time.monotonic() + budget
    db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    return db


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _unavailable(message):
    return {"available": False, "state": "unavailable", "message": message}


def grid_metadata():
    records = read(bots.forward_path(), {}) or {}
    return records.get("grid") if isinstance(records, dict) else None


def grid_snapshot(*, now=None, refresh=False):
    now = time.time() if now is None else now
    session = grid_metadata()
    if not session:
        return {"available": False, "running": False, "state": "stopped", "message": "No saved grid forward session.", "pnl": None}
    saved = read(root() / "grid.json", {}) or {}
    matches = saved.get("session_id") == session.get("id") and saved.get("session") == session and saved.get("source", {}).get("replay_revision") == REPLAY_REVISION
    if refresh and (not matches or now - saved.get("as_of", 0) >= 30):
        result = bots.forward_status("grid", now=now)
        # Read the metadata again after replay: do not publish results belonging
        # to a session that a separate console replaced while we were reading.
        if grid_metadata() != session:
            return _unavailable("Grid session changed during assessment; retrying next refresh")
        values = result.get("results") or {}
        capital, equity, realized = session.get("config", {}).get("capital_usd"), values.get("final_equity"), values.get("realized_pnl_usd")
        net = equity - capital if _finite(equity) and _finite(capital) else None
        pnl = {"mode": "paper", "capital": capital, "equity": equity, "net_usd": net,
               "net_pct": values.get("total_return"), "realized_usd": realized,
               "unrealized_usd": net - realized if _finite(net) and _finite(realized) else None,
               "gross_captured_usd": values.get("gross_captured_usd"), "costs_usd": values.get("costs_usd"),
               "hold_return": values.get("hold_return"), "excess_return": values.get("excess_return"),
               "round_trips": values.get("round_trips"), "forced_exit_qty": values.get("forced_exit_qty"),
               "note": "Recorded-stream paper replay, not wallet profit. Terminal forced exits, when present, are simulator valuations."} if net is not None else None
        gap = result.get("stopped_at_gap")
        running = session.get("stopped_at") is None
        recorder = result.get("recorder") or {}
        input_wait = running and "live" in recorder and not recorder["live"]
        message = result.get("message") or (f"Coverage ended at recorded gap {gap}." if gap else
            "Waiting for a fresh recorded stream; the saved paper session is retained." if input_wait else "Recorded-stream paper forward test.")
        state = "stopped" if not running else "waiting" if gap or pnl is None or input_wait else "running"
        saved = {"available": pnl is not None, "running": running, "state": state, "message": message,
                 "session_id": session.get("id"), "session": session, "asset": session.get("asset"),
                 "started_at": session.get("started_at"), "as_of": now, "pnl": pnl,
                 "coverage": {k: result.get(k) for k in ("bars", "snapshots", "last_snapshot", "bridged_minutes", "stopped_at_gap")},
                 "recorder": recorder,
                 "source": {"kind": "recorded Coinbase bid/ask snapshots", "session_file": str(bots.forward_path()),
                            "recording_dir": str(config.CONFIG_DIR / "prices"), "fee_bps": session.get("fee_bps"),
                            "slippage_bps": session.get("slippage_bps"), "replay_revision": REPLAY_REVISION}}
        write(root() / "grid.json", saved)
        matches = True
    if not matches:
        return {"available": False, "running": session.get("stopped_at") is None, "state": "waiting" if session.get("stopped_at") is None else "stopped", "pnl": None,
                "session_id": session.get("id"), "asset": session.get("asset"), "started_at": session.get("started_at"),
                "message": "Saved grid session found; waiting for its matching paper replay assessment.", "source": str(bots.forward_path())}
    result = copy.deepcopy(saved)
    result["age_seconds"] = max(0, now - result["as_of"])
    result["stale"] = result["age_seconds"] > 120
    return result


def optimizer_snapshot():
    from . import bot_scheduler
    directory = bot_scheduler._root()
    path = directory / "schedule.sqlite3"
    result = {"available": False, "running": locked(directory / "worker.lock"), "state": "stopped", "gates": OPTIMIZER_GATES}
    if not path.exists():
        return result
    with closing(connect_readonly(path)) as db:
        state = {key: json.loads(value) for key, value in db.execute("SELECT key,value FROM state")}
        result.update(available=True, state=state.get("phase", "stopped"), current=state.get("current"),
                      last_result=state.get("last_result"), last_run=state.get("last_run"), next_run=state.get("next_run"),
                      message=state.get("error") or "Validated optimizer; manual configurations remain protected.")
        result["items"] = [dict(zip(("bot", "coin", "state", "finished", "error"), row)) for row in db.execute(
            "SELECT bot,coin,state,finished,error FROM item ORDER BY finished DESC LIMIT 8")]
    if not result["running"] and result["state"] in ("running", "starting", "waiting"):
        result["state"] = "interrupted"
    return result


def council_snapshot(limit=8):
    result = council.status()
    capital, equity = result["config"].get("capital"), result.get("equity")
    net = equity - capital if _finite(equity) and _finite(capital) else None
    result["pnl"] = {"mode": "paper", "capital": capital, "equity": equity, "net_usd": net,
                     "net_pct": net / capital if net is not None and capital else None,
                     "realized_usd": (result["position"]["initial_equity"] - capital) if result.get("position") else net,
                     "unrealized_usd": (equity - result["position"]["initial_equity"]) if result.get("position") else 0.,
                     "note": "Paper realized P&L comes from prior closed equity; open-position mark includes entry/estimated exit costs and borrow."}
    result["fills"] = result.get("fills", [])[:limit]
    # Full frozen vote evidence remains in council.status/its DB; the rail only
    # needs the latest score and time, not 34 repeated strategy documents.
    observed = result.get("last_observation")
    if observed:
        result["last_observation"] = {k: observed.get(k) for k in ("id", "observed_at", "aggregate", "confidence", "confidence_samples")}
    return result


def _local_actions(limit):
    from . import coinbase_manual, jupiter_manual
    out = []
    for venue, directory in (("coinbase", coinbase_manual._dir()), ("jupiter", jupiter_manual._storage_dir())):
        if not directory.exists():
            continue
        paths = directory.glob("*.json")
        for path in paths:
            value = read(path, {}) or {}
            stamp = value.get("submit_started_at")
            if not _finite(stamp):
                continue  # A preview is not a submitted wallet action.
            out.append({"id": f"{venue}:{path.stem}", "at": stamp, "mode": "live", "chain": venue,
                        "kind": "local order submission", "status": value.get("state"),
                        "summary": f"{venue} {value.get('side') or ''} {value.get('product_id') or ''}".strip(),
                        "source": str(path), "note": "Local submitted intent; confirmation is not assumed."})
    return sorted(out, key=lambda row: row["at"], reverse=True)[:limit]


def update(asset, settings=None, *, now=None, stop=None):
    supplied_clock = now is not None
    now = time.time() if now is None else now
    settings = settings or config.load_settings()
    errors = []
    def get(name, function):
        try:
            return function()
        except Exception as exc:
            message = f"{name} unavailable ({type(exc).__name__})"
            errors.append(message)
            return _unavailable(message)
    voting = get("Votes", lambda: live_score.prediction_snapshot(asset, limit=50,
        min_accuracy=settings.live_vote_min_accuracy, min_resolved=settings.live_vote_min_resolved))
    voting["raw_rows"] = voting.get("rows", [])[:50]
    voting["source_as_of"] = now if supplied_clock else time.time()
    voting["voting"] = {"min_accuracy": settings.live_vote_min_accuracy, "min_resolved": settings.live_vote_min_resolved}
    voting["rows"] = []  # Returned rows and agreement are evaluated on each rail read.
    voting["producer"] = get("Prediction producer", lambda: prediction_recovery.health(asset))
    council_state = get("Council", council_snapshot)
    grid = get("Grid", lambda: grid_snapshot(now=now, refresh=True))
    optimizer = get("Optimizer", optimizer_snapshot)
    wallet = get("Wallet valuation", portfolio.load_last_scan)
    if wallet and wallet.get("result"):
        source = wallet["result"]
        wallet = {"available": True, "mode": "wallet", "total_usd": source.get("total_usd"), "as_of": wallet.get("saved_at"),
                  "partial": source.get("partial"), "pnl": None, "owner_verified": False,
                  "message": "Saved valuation; owner addresses are not retained in this snapshot. Trading profit and current-owner matching are unverified."}
    else:
        wallet = {"available": False, "mode": "wallet", "pnl": None, "message": "No saved wallet valuation."}
    external = read(root() / "external-activity.json", {}) or {}
    owners = {name: getattr(settings, name, "") for name in ("solana_address", "base_address", "eth_address", "hyperliquid_address", "btc_xpub", "ltc_xpub", "doge_xpub")}
    owner_hash = hashlib.sha256(json.dumps(owners, sort_keys=True).encode()).hexdigest()
    if external.get("owner_hash") == owner_hash and now - external.get("cached_at", 0) < 30:
        activity = external["activity"]
    else:
        try:
            from . import wallet_activity
            activity = get("Wallet activity", lambda: wallet_activity.snapshot(settings, limit=8, stop=stop))
        except ImportError:
            activity = {"items": [], "coverage": [], "gaps": ["External wallet activity reader unavailable."]}
        if stop is not None and stop.is_set():
            raise RuntimeError("Rail refresh stopped")
        write(root() / "external-activity.json", {"cached_at": now, "owner_hash": owner_hash, "activity": activity})
    activity.setdefault("items", [])
    activity.setdefault("coverage", [])
    activity.setdefault("gaps", [])
    local = get("Local order activity", lambda: _local_actions(8))
    if isinstance(local, list):
        activity["items"].extend(local)
    for fill in council_state.get("fills", []):
        activity["items"].append({"id": f"council:{fill.get('at')}:{fill.get('side')}", "at": fill.get("at"), "mode": "paper",
            "chain": "Council", "kind": fill.get("side"), "status": "simulated", "summary": fill.get("reason"), "source": "Council paper ledger"})
    ordered = sorted((row for row in activity["items"] if isinstance(row, dict) and _finite(row.get("at"))), key=lambda r: r["at"], reverse=True)
    activity["wallet_items"] = [row for row in ordered if row.get("mode") in ("wallet", "live")][:8]
    activity["paper_items"] = [row for row in ordered if row.get("mode") == "paper"][:8]
    activity["items"] = ordered[:8]
    activity["gaps"].append("Local journals cover this app's submitted intents only; they do not prove all wallet activity or fill confirmations.")
    from . import paper_workflow
    completed = now if supplied_clock else time.time()
    value = {"observed_at": completed, "capture_started_at": now, "asset": asset, "voting": voting, "council": council_state, "grid": grid,
             "optimizer": optimizer, "wallet": wallet, "activity": activity, "workflow": paper_workflow.refresh_progress(asset), "errors": errors,
             "sources": {"paper": "Council ledger and saved-grid recorded-stream replay", "wallet": "saved valuation plus explicitly covered read-only activity sources"}}
    if stop is not None and stop.is_set():
        raise RuntimeError("Rail refresh stopped")
    write(root() / f"rail-{asset}.json", value)
    return value


def rail(asset, *, limit=8, now=None, min_accuracy=None, min_resolved=None):
    now = time.time() if now is None else now
    limit = max(1, min(20, int(limit)))
    value = read(root() / f"rail-{asset}.json")
    if not value:
        value = {"observed_at": None, "asset": asset, "voting": _unavailable("Waiting for saved voting snapshot"),
                 "council": _unavailable("Waiting for Council snapshot"), "optimizer": _unavailable("Waiting for optimizer snapshot"),
                 "wallet": _unavailable("Waiting for saved wallet valuation"), "activity": {"items": [], "coverage": [], "gaps": ["Activity has not been refreshed."]},
                 "workflow": {}, "errors": []}
    value["grid"] = grid_snapshot(now=now)  # Verify current session id before displaying cached P&L.
    value["age_seconds"] = max(0., now - value["observed_at"]) if value.get("observed_at") else None
    value["stale"] = value["age_seconds"] is None or value["age_seconds"] > 120
    value["read_model"] = {"running": locked(root() / "worker.lock"), **(read(root() / "worker.json", {}) or {})}
    voting = value.setdefault("voting", {})
    raw_rows = voting.pop("raw_rows", voting.get("rows", []))[:50]
    policy = voting.get("voting") or {"min_accuracy": 60., "min_resolved": 20}
    policy = {**policy}
    if min_accuracy is not None:
        policy["min_accuracy"] = min_accuracy
    if min_resolved is not None:
        policy["min_resolved"] = min_resolved
    voting["voting"] = policy
    voting["aggregate"] = live_score.aggregate_predictions(raw_rows, now=now, **policy)
    eligible_by_label = {}
    for row in raw_rows:
        if live_score.aggregate_predictions([row], now=now, **policy)["available"]:
            eligible_by_label.setdefault(row["label"], row)
    eligible = list(eligible_by_label.values())
    voting.update(rows=eligible[:limit], eligible_count=len(eligible), rows_truncated=len(eligible) > limit,
                  evaluated_at=now, source_limit=50)
    value["activity"]["items"] = value["activity"].get("items", [])[:limit]
    return value


def refresh(asset):
    with control(root()):
        requests = read(root() / "requests.json", {}) or {}
        requests[asset] = time.time()
        # Keep a bounded set of most recently viewed coins.
        requests = dict(sorted(requests.items(), key=lambda p: p[1], reverse=True)[:8])
        write(root() / "requests.json", requests)
        if locked(root() / "worker.lock"):
            return {"state": "running", "running": True, "asset": asset}
        handle = (root() / "worker.lock").open("a+b")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            token = uuid.uuid4().hex
            write(root() / "control.json", {"stop": False})
            write(root() / "worker.json", {"state": "starting", "token": token, "pid": os.getpid()})
            with (root() / "worker.log").open("ab") as log:
                process = subprocess.Popen([sys.executable, "-m", "soltui.live_tools", "--lock-fd", str(handle.fileno()), "--token", token],
                    cwd=REPO, env={**os.environ, "SOLTUI_CONFIG_DIR": str(config.CONFIG_DIR.resolve())}, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=log, start_new_session=True, pass_fds=(handle.fileno(),))
        except BlockingIOError:
            return {"state": "running", "running": True, "asset": asset}
        except BaseException as exc:
            write(root() / "worker.json", {"state": "failed", "message": f"Read-model launch failed ({type(exc).__name__})"})
            raise
        finally:
            handle.close()
        threading.Thread(target=process.wait, daemon=True, name="rail-reaper").start()
        return {"state": "starting", "running": True, "asset": asset}


def stop_refresh():
    """Cooperatively stop only this read-model owner; shared jobs are untouched."""
    with control(root()):
        write(root() / "control.json", {"stop": True})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-fd", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    handle = os.fdopen(args.lock_fd, "a+b")
    actual, expected = os.fstat(handle.fileno()), (root() / "worker.lock").stat()
    owner = read(root() / "worker.json", {}) or {}
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino) or owner.get("token") != args.token:
        handle.close()
        return 1
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    stopped = threading.Event()
    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())
    def monitor():
        while not done.wait(.2):
            if (read(root() / "control.json", {}) or {}).get("stop"):
                stopped.set()
    watcher = threading.Thread(target=monitor, daemon=True, name="rail-control")
    watcher.start()
    try:
        while not stopped.is_set():
            # Admission and idle release share the control lock. A request can
            # either keep this owner alive or acquire its released lease; it
            # cannot be acknowledged by an owner already committed to exit.
            with control(root()):
                requests = read(root() / "requests.json", {}) or {}
                active = [asset for asset, stamp in requests.items() if time.time() - stamp < 180]
                if not active:
                    write(root() / "worker.json", {**owner, "state": "stopped", "pid": os.getpid()})
                    handle.close()
                    handle = None
                    break
            for asset in active:
                if stopped.is_set():
                    break
                write(root() / "worker.json", {**owner, "state": "running", "pid": os.getpid(), "asset": asset})
                try:
                    update(asset, stop=stopped)
                except Exception as exc:
                    write(root() / "worker.json", {**owner, "state": "waiting", "pid": os.getpid(), "message": f"Refresh unavailable ({type(exc).__name__})"})
            stopped.wait(10)
    finally:
        done.set()
        watcher.join(2)
        if handle is not None:
            with control(root()):
                try:
                    if (read(root() / "worker.json", {}) or {}).get("token") == args.token:
                        write(root() / "worker.json", {**owner, "state": "stopped", "pid": os.getpid()})
                finally:
                    handle.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Prospective Council paper bot. No order, wallet, signing or live execution API.

Votes and their eligibility are frozen when observed. Jupiter quotes are USD
references. Fills use the first Coinbase minute open strictly after a decision,
confirmed only when that complete real bar is available. Missing bars never
become synthetic fills. Agreement is not the entry-confidence probability.
"""
from __future__ import annotations

import argparse
import dataclasses
import fcntl
import hashlib
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
from typing import Any

import numpy as np

from backtester.core import perps
from backtester.core.types import Side, validate_bar_arrays
from . import bgqueue, compound, config as app_config, forwardtest, live_price, live_score, simulation

REPO = Path(__file__).resolve().parent.parent
FILL_MODEL = "Paper: next-minute-open Coinbase OHLC proxy; Jupiter USD quote is reference only."
POLICY_VERSION = 1
COUNCIL_REVISION = hashlib.sha256(Path(__file__).read_bytes() + forwardtest.revision().encode()).hexdigest()


def root() -> Path:
    return app_config.CONFIG_DIR / "council"


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _read(name: str) -> dict:
    try:
        value = json.loads((root() / name).read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(name: str, value: dict) -> None:
    root().mkdir(parents=True, exist_ok=True, mode=0o700)
    target = root() / name
    temporary = root() / f".{name}.{uuid.uuid4().hex}.tmp"
    try:
        temporary.write_text(_json(value), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _control():
    root().mkdir(parents=True, exist_ok=True, mode=0o700)
    with (root() / "control.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def _locked() -> bool:
    try:
        with (root() / "worker.lock").open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
    except FileNotFoundError:
        pass
    return False


def config(changes: dict | None = None) -> dict:
    saved = {"asset": "SOL", "capital": 10000., "poll_seconds": 10., "min_accuracy": 60., "min_resolved": 20,
             "execution": simulation.Execution().to_dict(), **_read("config.json")}
    if changes is None:
        return saved
    if not isinstance(changes, dict) or set(changes) - set(saved):
        raise ValueError("Council accepts asset, capital, poll_seconds, min_accuracy, min_resolved and execution")
    with _control():
        if _locked():
            raise ValueError("Stop Council before changing its configuration")
        old = status()
        if old["position"] is not None or old.get("pending"):
            raise ValueError("Resume Council to close its paper position before changing configuration")
        updated = {**saved, **changes}
        updated["asset"] = bgqueue.validate_asset(updated["asset"])
        if "execution" in changes:
            if not isinstance(changes["execution"], dict):
                raise ValueError("execution must be an object")
            updated["execution"] = simulation.Execution(**{**saved["execution"], **changes["execution"]}).to_dict()
        for field in ("capital", "poll_seconds", "min_accuracy", "min_resolved"):
            value = updated[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{field} must be finite")
        if updated["capital"] <= 0 or not 1 <= updated["poll_seconds"] <= 3600:
            raise ValueError("Capital must be positive and poll_seconds must be between 1 and 3600")
        if not 0 <= updated["min_accuracy"] <= 100 or updated["min_resolved"] < 1 or int(updated["min_resolved"]) != updated["min_resolved"]:
            raise ValueError("Choose a 0–100 accuracy floor and a positive integer sample floor")
        _write("config.json", updated)
    return updated


def _policy_id(cfg: dict) -> str:
    return hashlib.sha256(_json({"version": POLICY_VERSION,
        "config": {k: v for k, v in cfg.items() if k != "poll_seconds"}}).encode()).hexdigest()


def _initial(cfg: dict) -> dict:
    return {"policy_id": _policy_id(cfg), "asset": cfg["asset"], "equity": cfg["capital"], "position": None, "pending": None,
            "last_bar": None, "last_observation": None, "confidence": None, "confidence_samples": 0,
            "halted": False, "last_action": None,
            "message": "Waiting for current votes and real closed-minute bars."}


def _db() -> sqlite3.Connection:
    root().mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(root() / "paper.sqlite3", timeout=5)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS observation(id TEXT PRIMARY KEY, asset TEXT, observed REAL, minute INTEGER, document TEXT);
            CREATE TABLE IF NOT EXISTS shadow(policy TEXT, asset TEXT, minute INTEGER, target INTEGER, direction INTEGER,
                observation TEXT, outcome INTEGER, PRIMARY KEY(policy,asset,minute));
            CREATE TABLE IF NOT EXISTS candle(asset TEXT, ts INTEGER, open REAL, high REAL, low REAL, close REAL, PRIMARY KEY(asset,ts));
            CREATE TABLE IF NOT EXISTS fill(id INTEGER PRIMARY KEY, at INTEGER, document TEXT);
        """)
        return db
    except BaseException:
        db.close()
        raise


def _state(db, cfg: dict) -> dict:
    row = db.execute("SELECT value FROM meta WHERE key='state'").fetchone()
    value = json.loads(row[0]) if row else _initial(cfg)
    if value["policy_id"] != _policy_id(cfg):
        if value["position"] or value["pending"]:
            raise ValueError("Council policy changed while a position was open")
        return _initial(cfg)
    return value


def status() -> dict:
    cfg, owner = config(), _read("worker.json")
    state, fills = _initial(cfg), []
    path = root() / "paper.sqlite3"
    if path.exists():
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            state = _state(db, cfg)
            fills = [json.loads(r[0]) for r in db.execute("SELECT document FROM fill ORDER BY id DESC LIMIT 100")]
    running = _locked()
    phase = owner.get("state", "stopped") if running else "failed" if owner.get("state") in ("starting", "running", "waiting", "failed") else "stopped"
    message = owner.get("message") if running or phase == "failed" else state["message"]
    if running and _read("control.json").get("stop"):
        phase, message = "waiting", "Stopping paper bot; its position is retained."
    return {"mode": "paper", "running": running, "state": phase,
            "config": cfg, **state, "message": message or state["message"], "fills": fills,
            "owner": {k: owner.get(k) for k in ("pid", "started_at")} if running else None,
            "price_source": "Jupiter USD reference", "fill_model": FILL_MODEL}


def target(direction: int, score: float | None, execution: simulation.Execution, confidence: float | None) -> int:
    """Hysteresis policy; entry confidence never prevents a risk-reducing exit."""
    if score is None:
        return direction
    entry = 1 if score >= 60 else -1 if score <= -60 else 0
    permitted = entry if execution.permits(entry, confidence) else 0
    if direction == 1:
        return permitted if score <= -20 else 1
    if direction == -1:
        return permitted if score >= 20 else -1
    return permitted


def _record_fill(db, state, at, kind, price, reason, observation, **details):
    value = {"at": int(at), "side": kind, "price": float(price), "reason": reason,
             "observation_id": observation, "equity": state["equity"], "fill_source": "Coinbase closed 1m OHLC proxy",
             "asset": state["asset"], "policy_id": state["policy_id"], "council_revision": COUNCIL_REVISION,
             "execution": state["position"]["execution"], "direction": state["position"]["direction"],
             **details}
    db.execute("INSERT INTO fill(at,document) VALUES(?,?)", (int(at), _json(value)))


def _close(db, state, price, at, reason, observation, *, liquidated=False):
    position = state["position"]
    execution = simulation.Execution(**position["execution"])
    exit_notional = position["notional"] * price / position["entry_price"]
    exit_fee = exit_notional * execution.fee_bps / 10000
    exit_slip = exit_notional * execution.slippage_bps / 10000
    pnl = position["direction"] * position["notional"] * (price / position["entry_price"] - 1)
    state["equity"] = 0. if liquidated else max(0., position["initial_equity"] + pnl - position["entry_fee"]
        - position["entry_slip"] - exit_fee - exit_slip - position["borrow"])
    _record_fill(db, state, at, "sell" if position["direction"] > 0 else "buy_to_cover", price, reason, observation,
                 notional=exit_notional, fees=exit_fee, slippage=exit_slip, borrow=position["borrow"], liquidated=liquidated)
    state["position"] = None
    if liquidated:
        state["halted"] = True


def _open(db, state, price, at, direction, execution, observation):
    equity = state["equity"]
    notional = equity / (1 / execution.effective_leverage + (execution.fee_bps + execution.slippage_bps) / 10000)
    fee, slip = notional * execution.fee_bps / 10000, notional * execution.slippage_bps / 10000
    state["position"] = {"direction": direction, "entry_price": float(price), "entered_at": int(at),
                         "notional": notional, "collateral": notional / execution.effective_leverage,
                         "initial_equity": equity, "entry_fee": fee, "entry_slip": slip, "borrow": 0.,
                         "execution": execution.to_dict(), "observation_id": observation}
    state["equity"] = equity - fee - slip
    _record_fill(db, state, at, "buy" if direction > 0 else "sell_short", price, "Strong Buy" if direction > 0 else "Strong Sell",
                 observation, notional=notional, fees=fee, slippage=slip, borrow=0., liquidated=False)


def _aggregate(observation, now):
    return live_score.aggregate_predictions(observation["rows"], now=now,
        min_accuracy=observation["policy"]["min_accuracy"], min_resolved=observation["policy"]["min_resolved"])


def _fill_allowed(db, pending, at, execution):
    row = db.execute("SELECT document FROM observation WHERE asset=? AND observed<=? ORDER BY observed DESC,id DESC LIMIT 1",
                     (pending["asset"], at)).fetchone()
    if row is None:
        return False, "No recorded eligible observation at the fill time"
    latest = json.loads(row[0])
    current = _aggregate(latest, at)
    direction = 1 if current["score"] is not None and current["score"] >= 60 else -1 if current["score"] is not None and current["score"] <= -60 else 0
    quote = latest.get("quote") or {}
    if not current["available"] or direction != pending["target"]:
        return False, "Entry evidence expired, became unavailable, or changed before the future open; 1m-only votes can expire before this fill model can enter"
    if not _usable_quote(quote, at, max_age=120):
        return False, "No fresh Jupiter reference at the fill decision"
    return execution.permits(direction, pending["confidence"]), "Entry confidence is below the configured floor"


def _usable_quote(quote, now, *, max_age=30):
    price, stamp = quote.get("price"), quote.get("fetched_at")
    return (not isinstance(price, bool) and isinstance(price, (int, float)) and math.isfinite(price) and price > 0
            and not isinstance(stamp, bool) and isinstance(stamp, (int, float)) and math.isfinite(stamp)
            and 0 <= now - stamp <= max_age and quote.get("source") == "jupiter")


def _process_bar(db, state, cfg, stamp, candle):
    op, high, low, close = (float(v) for v in candle)
    execution = simulation.Execution(**cfg["execution"])
    position = state["position"]
    if position:
        ex = simulation.Execution(**position["execution"])
        side = Side.LONG if position["direction"] > 0 else Side.SHORT
        liq = perps.liquidation_price(position["entry_price"], side, position["collateral"], position["notional"], position["borrow"], ex.costs())
        if perps.is_liquidated(side, liq, op, op):
            _close(db, state, op, stamp, "Liquidated at opening gap", position["observation_id"], liquidated=True)
            state["pending"] = None
    pending = state["pending"]
    if pending and pending["execute_bar"] == stamp:
        current = state["position"]["direction"] if state["position"] else 0
        if current and pending["target"] != current:
            _close(db, state, op, stamp, "Sell" if current > 0 else "Buy", pending["observation_id"])
        if pending["target"] and state["position"] is None and state["equity"] > 0:
            allowed, reason = _fill_allowed(db, pending, stamp, execution)
            if allowed:
                _open(db, state, op, stamp, pending["target"], execution, pending["observation_id"])
            else:
                state["message"] = reason
                state["last_action"] = {"at": stamp, "reason": reason, "target": pending["target"],
                                        "observation_id": pending["observation_id"], "action": "entry_declined"}
        state["pending"] = None
    position = state["position"]
    if position:
        ex = simulation.Execution(**position["execution"])
        side = Side.LONG if position["direction"] > 0 else Side.SHORT
        position["borrow"] += perps.accrue_borrow_fee(ex.costs(), side, position["notional"], 1 / 60)
        liq = perps.liquidation_price(position["entry_price"], side, position["collateral"], position["notional"], position["borrow"], ex.costs())
        if perps.is_liquidated(side, liq, low, high):
            price = min(op, liq.price) if position["direction"] > 0 else max(op, liq.price)
            _close(db, state, price, stamp, "Liquidated", position["observation_id"], liquidated=True)
            state["pending"] = None
            state["message"] = "Paper collateral liquidated; no further entries without new capital."
        else:
            exit_notional = position["notional"] * close / position["entry_price"]
            state["equity"] = max(0., position["initial_equity"] + position["direction"] * position["notional"] * (close / position["entry_price"] - 1)
                - position["entry_fee"] - position["entry_slip"] - position["borrow"]
                - exit_notional * (ex.fee_bps + ex.slippage_bps) / 10000)
    # One prior directional outcome per policy/asset/minute, regardless of polls.
    for policy, asset, minute, direction, raw in db.execute("""SELECT s.policy,s.asset,s.minute,s.direction,o.document
            FROM shadow s JOIN observation o ON o.id=s.observation
            WHERE s.asset=? AND s.target=? AND s.outcome IS NULL""", (cfg["asset"], stamp)).fetchall():
        observed = json.loads(raw)
        # Expiry prevents new entries, not learning a realized outcome from a
        # direction that qualified when it was prospectively observed.
        if _aggregate(observed, observed["observed_at"])["available"]:
            economics = simulation.settle(dataclasses.replace(simulation.Execution(**observed["execution"]), use_leverage=False), direction, [candle])
            db.execute("UPDATE shadow SET outcome=? WHERE policy=? AND asset=? AND minute=?",
                       (int(economics["net_return"] > 0), policy, asset, minute))
    state["last_bar"] = stamp


def step(*, now: float | None = None, snapshot: dict | None = None, quote: dict | None = None,
         bars: dict | None = None, stop: threading.Event | None = None, recover=None) -> dict:
    """One causal paper tick; injectable public reads keep offline tests deterministic."""
    stop = stop or threading.Event()
    cfg = config()
    known = status()
    error = ""
    if snapshot is None:
        try:
            snapshot = live_score.prediction_snapshot(cfg["asset"], min_accuracy=cfg["min_accuracy"], min_resolved=cfg["min_resolved"])
        except Exception as exc:
            snapshot, error = {"rows": []}, f"Predictions unavailable ({type(exc).__name__})"
    if quote is None:
        try:
            quote = live_price.jupiter(cfg["asset"])
        except Exception as exc:
            quote, error = {}, f"Jupiter reference unavailable ({type(exc).__name__})"
    clock = time.time() if now is None else now
    if bars is None:
        try:
            previous = known["last_bar"]
            # Recover the oldest outstanding page, rather than repeatedly
            # requesting a recent page that can never contain the missing start.
            fetch_clock = min(clock, previous + 10081 * 60) if previous is not None else clock
            count = max(600, min(10080, int((fetch_clock - previous) / 60) + 2)) if previous is not None else 600
            bars = compound.fetch_closed_candles(cfg["asset"], now=fetch_clock, bars=count, seconds=60, sleep=stop.wait)
        except Exception as exc:
            bars, error = {}, f"Closed Coinbase proxy bars unavailable ({type(exc).__name__})"
    observed_at = time.time() if now is None else now
    if stop.is_set():
        raise RuntimeError("Council stopped")
    closed = {}
    latest = int(observed_at // 60) * 60 - 60
    needed = min(known["last_bar"] + 60, latest) if known["last_bar"] is not None else latest
    if bars:
        try:
            # Older unrelated cache gaps do not invalidate the exact minutes
            # needed for this position and its prospectively queued decision.
            mask = (bars["ts"] + 60 <= observed_at) & (bars["ts"] >= needed)
            valid = validate_bar_arrays({k: v[mask] for k, v in bars.items()}, "1m")
            closed = {int(t): tuple(float(v) for v in row) for t, *row in zip(valid["ts"], valid["open"], valid["high"], valid["low"], valid["close"], strict=True)}
        except (ValueError, KeyError, TypeError):
            error = "Closed Coinbase proxy bars are missing, gapped, or invalid"
    aggregate = live_score.aggregate_predictions(snapshot.get("rows", []), now=observed_at,
        min_accuracy=cfg["min_accuracy"], min_resolved=cfg["min_resolved"])
    minute = int(observed_at // 60) * 60
    policy = {"min_accuracy": cfg["min_accuracy"], "min_resolved": cfg["min_resolved"]}
    identity = {"asset": cfg["asset"], "minute": minute, "rows": snapshot.get("rows", []), "policy_id": _policy_id(cfg),
                "strategy_revision": forwardtest.revision(), "council_revision": COUNCIL_REVISION}
    observation_id = hashlib.sha256(_json(identity).encode()).hexdigest()
    observation = {**identity, "id": observation_id, "observed_at": observed_at, "policy": policy,
                   "aggregate": aggregate, "execution": cfg["execution"], "quote": quote, "fill_model": FILL_MODEL,
                   "policy_version": POLICY_VERSION,
                   "confidence_method": "Beta(1,1) mean of up to 100 prior net Council directional outcomes; minimum 20. Agreement is not probability."}
    with closing(_db()) as db, db:
        db.execute("BEGIN IMMEDIATE")
        state = _state(db, cfg)
        latest = minute - 60
        first = state["last_bar"] + 60 if state["last_bar"] is not None else latest
        page_last = min(latest, max(closed)) if closed else first - 60
        if closed and first <= page_last and all(stamp in closed for stamp in range(first, page_last + 1, 60)):
            for stamp in range(first, page_last + 1, 60):
                if stop.is_set():
                    raise RuntimeError("Council stopped")
                candle = closed[stamp]
                old = db.execute("SELECT open,high,low,close FROM candle WHERE asset=? AND ts=?", (cfg["asset"], stamp)).fetchone()
                if old is not None and tuple(old) != candle:
                    raise ValueError("Recorded closed Council candle changed")
                db.execute("INSERT OR IGNORE INTO candle VALUES(?,?,?,?,?,?)", (cfg["asset"], stamp, *candle))
                _process_bar(db, state, cfg, stamp, candle)
            if page_last < latest:
                error = "Recovering missing closed Coinbase proxy minutes in bounded pages; new paper decisions wait"
        elif state["last_bar"] is not None or latest not in closed:
            error = "Waiting for every missing closed Coinbase proxy minute; position and pending decision retained"
        previous = db.execute("SELECT document FROM observation WHERE id=?", (observation_id,)).fetchone()
        results = db.execute("SELECT outcome FROM shadow WHERE policy=? AND asset=? AND outcome IS NOT NULL ORDER BY minute DESC LIMIT ?",
                             (_policy_id(cfg), cfg["asset"], simulation.CONFIDENCE_WINDOW)).fetchall()
        state["confidence_samples"] = len(results)
        state["confidence"] = simulation.confidence_score(sum(r[0] for r in results), len(results))
        if previous is None:
            score = aggregate["score"]
            direction = (score > 0) - (score < 0) if score is not None else 0
            if direction:
                db.execute("INSERT OR IGNORE INTO shadow VALUES(?,?,?,?,?,?,NULL)",
                           (_policy_id(cfg), cfg["asset"], minute, minute + 60, direction, observation_id))
            current = state["position"]["direction"] if state["position"] else 0
            execution = simulation.Execution(**cfg["execution"])
            desired = target(current, score, execution, state["confidence"])
            if state["halted"]:
                desired = current
            quote_ok = _usable_quote(quote, observed_at)
            if not quote_ok and desired != 0 and desired != current:
                desired = 0 if current and desired != current else current
            if state["pending"] is None and desired != current and state["last_bar"] == latest:
                state["pending"] = {"asset": cfg["asset"], "target": desired, "execute_bar": minute + 60,
                                    "observation_id": observation_id, "confidence": state["confidence"]}
                state["message"] = "Paper decision queued for the next future minute open."
            elif not aggregate["available"]:
                state["message"] = "Waiting for eligible current votes; existing position held."
            elif not quote_ok:
                state["message"] = "Waiting for a fresh Jupiter USD reference; new entries blocked."
            elif state["confidence"] is None and execution.min_confidence > 0 and current == 0:
                state["message"] = f"Confidence warmup: {len(results)}/{simulation.MIN_CONFIDENCE_SAMPLES} prior Council outcomes."
            elif desired == current:
                state["message"] = "Holding paper position." if current else "Waiting for a strong vote and entry confidence."
            observation.update(confidence=state["confidence"], confidence_samples=len(results),
                               current_direction=current, desired_direction=desired)
            db.execute("INSERT INTO observation VALUES(?,?,?,?,?)", (observation_id, cfg["asset"], observed_at, minute, _json(observation)))
            state["last_observation"] = observation
        if state["halted"]:
            state["message"] = "Paper collateral liquidated; configure new capital while stopped to begin a new policy."
        if error:
            state["message"] = error
        if stop.is_set():
            raise RuntimeError("Council stopped")
        db.execute("INSERT OR REPLACE INTO meta VALUES('state',?)", (_json(state),))
    if not aggregate["available"]:
        if recover is None:
            from . import commands
            recover = lambda asset: commands.dispatch("forwardtest.ensure", {"asset": asset}, quiet=True)
        recover(cfg["asset"])
    result = status()
    result["message"] = state["message"]
    return result


def _cancel_pending() -> None:
    if not (root() / "paper.sqlite3").exists():
        return
    cfg = config()
    with closing(_db()) as db, db:
        state = _state(db, cfg)
        if state["pending"]:
            state["last_action"] = {"at": time.time(), "reason": "Explicit Stop cancelled the unfilled paper decision", "action": "cancelled"}
        state.update(pending=None, message="Council stopped; paper position retained.")
        db.execute("INSERT OR REPLACE INTO meta VALUES('state',?)", (_json(state),))


def start() -> dict:
    with _control():
        if _locked():
            return status()
        cfg = config()
        _write("config.json", cfg)
        handle = (root() / "worker.lock").open("a+b")
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            handle.close()
            return status()
        owner = {"token": uuid.uuid4().hex, "pid": os.getpid(), "started_at": time.time(), "state": "starting", "message": "Starting Council paper bot."}
        try:
            _write("control.json", {"stop": False})
            _write("worker.json", owner)
            with (root() / "worker.log").open("ab") as log:
                process = subprocess.Popen([sys.executable, "-m", "soltui.council", "--lock-fd", str(handle.fileno()), "--token", owner["token"]],
                    cwd=REPO, env={**os.environ, "SOLTUI_CONFIG_DIR": str(app_config.CONFIG_DIR.resolve())},
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True, pass_fds=(handle.fileno(),))
        except BaseException as exc:
            _write("worker.json", {**owner, "state": "failed", "message": f"Could not start Council ({type(exc).__name__})"})
            raise
        finally:
            handle.close()
        threading.Thread(target=process.wait, daemon=True, name="council-reaper").start()
        return status()


def stop() -> dict:
    with _control():
        _write("control.json", {"stop": True})
        if not _locked():
            _cancel_pending()
    return status()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-fd", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    handle = os.fdopen(args.lock_fd, "a+b")
    actual, expected = os.fstat(handle.fileno()), (root() / "worker.lock").stat()
    if (actual.st_dev, actual.st_ino) != (expected.st_dev, expected.st_ino):
        handle.close()
        return 1
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    owner = _read("worker.json")
    if owner.get("token") != args.token:
        handle.close()
        return 1
    stopped = threading.Event()
    monitor_done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stopped.set())

    def monitor():
        while not monitor_done.wait(.2):
            if _read("control.json").get("stop"):
                stopped.set()

    watcher = threading.Thread(target=monitor, daemon=True, name="council-control")
    watcher.start()
    failure = None
    try:
        owner.update(pid=os.getpid(), state="running")
        _write("worker.json", owner)
        while not stopped.is_set():
            try:
                result = step(stop=stopped)
                owner.update(state="waiting" if "waiting" in result["message"].lower() or "warmup" in result["message"].lower() else "running",
                             message=result["message"])
            except Exception as exc:
                if stopped.is_set():
                    break
                owner.update(state="waiting", message=f"Council waiting ({type(exc).__name__}): {str(exc)[:180]}")
            _write("worker.json", owner)
            stopped.wait(config()["poll_seconds"])
    except Exception as exc:
        failure = f"{type(exc).__name__}: {str(exc)[:180]}"
    finally:
        monitor_done.set()
        watcher.join(2)
        try:
            if _read("control.json").get("stop"):
                _cancel_pending()
            _write("worker.json", {**owner, "state": "failed" if failure else "stopped", "message": failure or "Council stopped; paper position retained."})
        finally:
            handle.close()
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())

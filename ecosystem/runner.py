"""Durable paper-only supervisor over the existing F5 worker and recorder."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with tmp.open("x", encoding="utf-8") as handle:
            os.chmod(tmp, 0o600)
            handle.write(json.dumps(value, sort_keys=True, allow_nan=False))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        tmp.unlink(missing_ok=True)


PHASES = {
    "planned",
    "starting",
    "acquiring",
    "backtesting",
    "forward",
    "forward_partial",
    "forward_waiting",
    "forward_partial_waiting",
    "failed",
    "interrupted",
    "stopped",
    "offline_prepared",
}


def validate_config(config: dict) -> None:
    if not isinstance(config, dict):
        raise TypeError("invalid_bootstrap_config")
    for name in ("coins", "intervals", "horizons", "strategies"):
        values = config.get(name)
        if (
            type(values) is not list
            or not values
            or len(values) > 10000
            or any(type(v) is not str or not v or len(v) > 100 for v in values)
        ):
            raise ValueError("invalid_bootstrap_config")
    if any(type(config.get(name)) is not bool for name in ("offline", "recorder")):
        raise ValueError("invalid_bootstrap_config")
    if (
        config.get("mode") != "paper"
        or config.get("market_venue") != "coinbase_exchange"
        or config.get("quote") != "USD"
    ):
        raise ValueError("invalid_bootstrap_scope")
    for name in ("start", "end"):
        if not isinstance(config.get(name), str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", config[name]
        ):
            raise ValueError("invalid_history_bounds")
    if datetime.fromisoformat(config["start"]) >= datetime.fromisoformat(config["end"]):
        raise ValueError("invalid_history_bounds")
    from backtester.core.strategies import REGISTRY
    from backtester.core.strategy_cards import HORIZONS
    from soltui.config import INTERVALS

    if any(
        len(values) != len(set(values))
        for values in (
            config["coins"],
            config["intervals"],
            config["horizons"],
            config["strategies"],
        )
    ):
        raise ValueError("duplicate_bootstrap_selection")
    if (
        not set(config["strategies"]) <= set(REGISTRY)
        or not set(config["horizons"]) <= set(HORIZONS)
        or not set(config["intervals"]) <= set(INTERVALS)
    ):
        raise ValueError("invalid_bootstrap_selection")
    from oracle.feeds import validate_instrument

    for coin in config["coins"]:
        try:
            validate_instrument(f"{coin}/USD")
        except (TypeError, ValueError):
            raise ValueError("invalid_bootstrap_selection") from None
    if config.get("manager_home") is not None and (
        not isinstance(config["manager_home"], str)
        or not Path(config["manager_home"]).is_absolute()
    ):
        raise ValueError("invalid_manager_home")
    if "research_policy" in config or "research_min_confidence" in config:
        minimum = config.get("research_min_confidence")
        if (
            config.get("research_policy") != "costed-shadow-v1"
            or type(minimum) not in (int, float)
            or not math.isfinite(minimum)
            or not 0 <= minimum <= 1
        ):
            raise ValueError("invalid_research_policy")
    capital = config.get("research_capital", 10000.0)
    if (
        type(capital) not in (float, int)
        or not math.isfinite(capital)
        or not 0 < capital <= 100_000_000
    ):
        raise ValueError("invalid_research_capital")
    if type(config.get("embedded_ui", True)) is not bool:
        raise ValueError("invalid_ui_policy")
    if config.get("swap_provider", "reference") not in {"jupiter", "reference"}:
        raise ValueError("invalid_swap_provider")
    if config.get("cost_model") is not None:
        from .swaps import validate_cost_model

        if validate_cost_model(config["cost_model"]) != config["cost_model"]:
            raise ValueError("invalid_cost_model")


def load(home: Path) -> dict:
    try:
        value = json.loads((home / "state.json").read_text())
    except FileNotFoundError:
        return {"schema_version": 1, "phase": "not_initialized"}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid_bootstrap_state")
    if value.get("phase") not in PHASES or not re.fullmatch(
        r"[0-9a-f]{32}", value.get("run_id", "")
    ):
        raise ValueError("invalid_bootstrap_state")
    validate_config(value.get("config"))
    for name in ("batch_id", "supervisor_token"):
        if value.get(name) is not None and (
            not isinstance(value[name], str)
            or not re.fullmatch(r"[0-9a-f]{32}", value[name])
        ):
            raise ValueError("invalid_bootstrap_state")
    return value


@contextmanager
def lock(home: Path, *, wait_seconds: float = 0):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(home / "supervisor.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.05)
        yield
    finally:
        os.close(fd)


@contextmanager
def _generation_guard(home: Path, *, wait_seconds: float = 5):
    """Serialize only generation/stop intent; never hold the supervisor lease."""
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(
        home / "generation-intent.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("invalid_generation_lock")
        deadline = time.monotonic() + wait_seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)
        yield
    finally:
        os.close(fd)


def running(home: Path) -> bool:
    if not (home / "supervisor.lock").is_file():
        return False
    try:
        with lock(home):
            return False
    except BlockingIOError:
        return True


def plan(
    home: Path,
    *,
    coins: list[str],
    intervals: list[str],
    horizons: list[str],
    strategies: list[str],
    start: str,
    end: str,
    offline: bool = False,
    recorder: bool = True,
    manager_home: str | None = None,
    research_min_confidence: float = 0.0,
    research_capital: float = 10000.0,
    swap_provider: str = "reference",
    cost_model: dict | None = None,
    embedded_ui: bool = True,
) -> dict:
    from backtester.core.strategies import REGISTRY
    from backtester.core.strategy_cards import HORIZONS
    from soltui.bgqueue import validate_asset
    from soltui.config import INTERVALS

    if (
        any(
            type(v) is not list or not v or any(type(x) is not str for x in v)
            for v in (coins, intervals, horizons, strategies)
        )
        or type(offline) is not bool
        or type(recorder) is not bool
    ):
        raise ValueError("invalid_bootstrap_config")
    coins = sorted({validate_asset(asset.upper()) for asset in coins})
    if not coins or not strategies or not intervals or not horizons:
        raise ValueError("empty_bootstrap_matrix")
    if (
        not set(intervals) <= set(INTERVALS)
        or not set(horizons) <= set(HORIZONS)
        or not set(strategies) <= set(REGISTRY)
    ):
        raise ValueError("invalid_bootstrap_matrix")
    # Freeze date bounds once; resume never silently extends an experiment.
    if datetime.fromisoformat(start) >= datetime.fromisoformat(end):
        raise ValueError("invalid_history_bounds")
    config = {
        "coins": coins,
        "intervals": sorted(set(intervals)),
        "horizons": sorted(set(horizons)),
        "strategies": sorted(set(strategies)),
        "start": start,
        "end": end,
        "offline": bool(offline),
        "recorder": bool(recorder),
        "market_venue": "coinbase_exchange",
        "quote": "USD",
        "mode": "paper",
        "manager_home": manager_home,
        "research_policy": "costed-shadow-v1",
        "research_min_confidence": research_min_confidence,
        "research_capital": research_capital,
        "swap_provider": swap_provider,
        "cost_model": None,
        "embedded_ui": embedded_ui,
    }
    if cost_model is not None or swap_provider == "jupiter":
        from soltui.config import Settings

        from .swaps import validate_cost_model

        assumptions = Settings()
        config["cost_model"] = validate_cost_model(
            cost_model
            if cost_model is not None
            else {
                "source": "configured_scenario",
                "fee_bps": assumptions.fee_bps,
                "slippage_bps": assumptions.slippage_bps,
                "borrow_long_bps_hour": assumptions.borrow_long_bps_hour,
                "borrow_short_bps_hour": assumptions.borrow_short_bps_hour,
            }
        )
    validate_config(config)
    with lock(home):
        old = load(home)
        if old["phase"] != "not_initialized":
            previous = {
                "research_capital": 10000.0,
                "swap_provider": "reference",
                "cost_model": None,
                "embedded_ui": True,
                **old["config"],
            }
            if previous != config:
                raise ValueError("existing_plan_differs_use_new_home")
            return old
        state = {
            "schema_version": 1,
            "run_id": uuid.uuid4().hex,
            "phase": "planned",
            "created_at": time.time(),
            "config": config,
            "acquisitions": {},
            "batch_id": None,
            "oracle": {},
            "mode": "paper",
            "live_enabled": False,
        }
        save(home / "state.json", state)
        return state


def status(home: Path) -> dict:
    state = load(home)
    result = {**state, "supervisor_running": running(home)}
    if state.get("batch_id"):
        from soltui import f5_batch

        result["batch"] = f5_batch.status(state["batch_id"], root=home / "batches")
    if (home / "registrations.sqlite3").is_file():
        from .registration import read_registrations

        result["registrations"] = read_registrations(home, limit=100)
    return result


def start(home: Path) -> dict:
    with _generation_guard(home), lock(home):
        state = load(home)
        if state["phase"] == "not_initialized":
            raise ValueError("bootstrap_not_planned")
        if (
            state.get("phase") == "starting"
            and 0 <= time.time() - state.get("supervisor_started_at", 0) < 10
        ):
            return {
                "status": "start_in_progress",
                "run_id": state["run_id"],
                "home": str(home),
                "mode": "paper",
            }
        token = uuid.uuid4().hex
        state.update(
            supervisor_token=token, phase="starting", supervisor_started_at=time.time()
        )
        save(home / "state.json", state)
        with (home / "supervisor.log").open("ab") as log:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-m",
                    "ecosystem.cli",
                    "supervise",
                    "--home",
                    str(home),
                    "--token",
                    token,
                ],
                cwd="/tmp",
                stdout=log,
                stderr=log,
                start_new_session=True,
                close_fds=True,
                env={
                    **{
                        key: value
                        for key, value in os.environ.items()
                        if key not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}
                    },
                    "PYTHONNOUSERSITE": "1",
                },
            )
        # PID is diagnostic only; stop authority uses an instance token and locks.
        state["supervisor_pid"] = proc.pid
        save(home / "state.json", state)
    return {
        "status": "start_requested",
        "run_id": state["run_id"],
        "pid": proc.pid,
        "home": str(home),
        "mode": "paper",
    }


def prepare_foreground(home: Path) -> str | None:
    """Claim a new generation for an OS-supervised foreground process.

    An explicit stop belongs to its generation and remains stopped across login.
    A crash has no matching stop request and can be recovered. Historical batch
    and Oracle policy guards remain unchanged.
    """
    try:
        with _generation_guard(home, wait_seconds=0), lock(home):
            state = load(home)
            if state["phase"] == "not_initialized":
                raise ValueError("bootstrap_not_planned")
            previous = state.get("supervisor_token")
            if previous and (home / ("stop-" + previous)).exists():
                return None
            if (
                state["phase"] == "starting"
                and 0 <= time.time() - state.get("supervisor_started_at", 0) < 10
            ):
                return None
            token = uuid.uuid4().hex
            state.update(
                supervisor_token=token,
                supervisor_pid=os.getpid(),
                phase="starting",
                supervisor_started_at=time.time(),
            )
            state.pop("error", None)
            save(home / "state.json", state)
            return token
    except BlockingIOError:
        return None


def stop(home: Path) -> dict:
    with _generation_guard(home):
        state = load(home)
        token = state.get("supervisor_token")
        if token:
            (home / ("stop-" + token)).touch(mode=0o600, exist_ok=True)
        if state.get("batch_id"):
            from soltui import f5_batch

            f5_batch.stop(state["batch_id"], root=home / "batches")
        return {
            "status": "stop_requested",
            "retains_archives": True,
            "stops_shared_recorder": False,
        }


def publish(receipt: dict, home: Path, asset: str, interval: str) -> None:
    source = Path(receipt["path"])
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["sha256"]:
        raise ValueError("acquisition_hash_mismatch")
    target = home / "accepted" / f"{asset}_{interval}.csv"
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if target.exists():
        if target.read_bytes() != raw:
            raise ValueError("accepted_input_changed_use_new_home")
        return
    fd, temporary = tempfile.mkstemp(prefix=".accepted-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def supervise(home: Path, token: str, *, max_cycles: int | None = None) -> int:
    from oracle.engine import OracleEngine
    from oracle.feeds import FeedUnavailable, RecorderFeed
    from soltui import config, f5_batch, pricefeed

    from . import __version__
    from .control import recorder_recovery_enabled, recovery_guard, runtime_settings
    from .data import acquire
    from .performance import sync as sync_performance
    from .recovery import ensure_batch
    from .registration import sync_registrations

    with lock(home, wait_seconds=10):
        state = load(home)
        if token != state.get("supervisor_token"):
            raise ValueError("supervisor_generation_changed")
        stop_file = home / ("stop-" + token)
        cfg = state["config"]
        state["ecosystem_version"] = __version__
        state["control_contract_version"] = 1
        manager_home = Path(cfg["manager_home"]) if cfg.get("manager_home") else None
        from .ui_service import status as ui_status

        state["ui_url"] = (
            ui_status(home, manager_home).get("url")
            if cfg.get("embedded_ui", True)
            else None
        )
        save(home / "state.json", state)
        update_telemetry(state, home, manager_home)
        if not state.get("batch_id"):
            state["phase"] = "acquiring"
            save(home / "state.json", state)
            for asset in cfg["coins"]:
                for interval in cfg["intervals"]:
                    if stop_file.exists():
                        state["phase"] = "stopped"
                        save(home / "state.json", state)
                        return 0
                    key = f"{asset}:{interval}"
                    state.update(current=key, heartbeat_at=time.time())
                    save(home / "state.json", state)
                    receipt = acquire(
                        asset,
                        home / "downloads",
                        start=cfg["start"],
                        end=cfg["end"],
                        interval=interval,
                        offline=cfg["offline"],
                    )
                    state["acquisitions"][key] = receipt
                    if receipt.get("status") == "complete":
                        publish(receipt, home, asset, interval)
                    save(home / "state.json", state)
            (home / "accepted").mkdir(exist_ok=True)
            settings = config.Settings(
                data_dir=str(home / "accepted"),
                min_confidence=cfg.get("research_min_confidence", 0.80),
                capital=cfg.get("research_capital", 10000.0),
                **(
                    {
                        "fee_bps": cfg["cost_model"]["total_fee_bps"],
                        "slippage_bps": cfg["cost_model"]["slippage_bps"],
                        "borrow_long_bps_hour": cfg["cost_model"][
                            "borrow_long_bps_hour"
                        ],
                        "borrow_short_bps_hour": cfg["cost_model"][
                            "borrow_short_bps_hour"
                        ],
                    }
                    if cfg.get("cost_model")
                    else {}
                ),
            )
            batch = ensure_batch(settings, cfg, home / "batches")
            state["batch_id"] = batch["run_id"]
            state["batch_recovery"] = batch["recovery"]
            save(home / "state.json", state)
        batch_id = state["batch_id"]
        if cfg["offline"]:
            state["registration"] = sync_registrations(home, batch_id, home / "batches")
            state["phase"] = "offline_prepared"
            save(home / "state.json", state)
            return 0
        sync_registrations(home, batch_id, home / "batches")
        batch = f5_batch.status(batch_id, root=home / "batches")
        with recovery_guard(home) as allowed:
            if (
                allowed
                and runtime_settings(home)["batch_enabled"]
                and not batch["running"]
                and batch["phase"] != "failed"
            ):
                f5_batch.start(batch_id, root=home / "batches")
        feeds = {
            asset: RecorderFeed(instrument=f"{asset}/USD") for asset in cfg["coins"]
        }
        engines = {
            asset: OracleEngine(
                home / "oracle" / asset / "history.sqlite3", instrument=f"{asset}/USD"
            )
            for asset in cfg["coins"]
        }
        cycle = 0
        next_recorder_check = 0.0
        oracle_generation = runtime_settings(home)["oracle_generation"]
        while not stop_file.exists():
            now = time.time()
            runtime = runtime_settings(home)
            if runtime["oracle_generation"] != oracle_generation:
                feeds = {
                    asset: RecorderFeed(instrument=f"{asset}/USD")
                    for asset in cfg["coins"]
                }
                engines = {
                    asset: OracleEngine(
                        home / "oracle" / asset / "history.sqlite3",
                        instrument=f"{asset}/USD",
                    )
                    for asset in cfg["coins"]
                }
                oracle_generation = runtime["oracle_generation"]
            if (
                recorder_recovery_enabled(home)
                and cfg["recorder"]
                and not cfg["offline"]
                and now >= next_recorder_check
            ):
                # Reuse the existing singleton; never rewrite shared LaunchAgent settings.
                try:
                    with recovery_guard(home) as allowed:
                        if allowed and recorder_recovery_enabled(home):
                            outcome = pricefeed.ensure_recorder(install=False)
                            state["recorder"] = {
                                "running": bool(outcome.get("running"))
                            }
                except (OSError, RuntimeError, ValueError):
                    state["recorder"] = {
                        "running": False,
                        "reason": "recorder_unavailable",
                    }
                next_recorder_check = now + 60
            for asset, feed in feeds.items():
                if not runtime["oracle_enabled"]:
                    state["oracle"][asset] = {
                        "instrument": f"{asset}/USD",
                        "market": "unavailable",
                        "prediction": "unavailable",
                        "signal": None,
                        "reason": "oracle_paused",
                    }
                    continue
                try:
                    observation = feed.poll()
                    if observation is not None:
                        engines[asset].ingest(observation)
                    prediction = engines[asset].predictions()
                    market = prediction["market"]
                    observation = market.get("observation", {})
                    aggregate = prediction["aggregate"]
                    contributors = {row["strategy_id"] for row in aggregate["included"]}
                    expiries = [
                        row["expires_at"]
                        for row in prediction["strategies"]
                        if row["strategy_id"] in contributors
                    ]
                    state["oracle"][asset] = {
                        "market": market["status"],
                        "prediction": prediction["status"],
                        "signal": prediction.get("signal"),
                        "instrument": f"{asset}/USD",
                        "as_of": prediction["as_of"],
                        "horizon_seconds": prediction["horizon_seconds"],
                        "expires_at": min(expiries) if expiries else None,
                        "balance_percent": aggregate["balance_percent"],
                        "percentage_semantics": prediction["percentage_semantics"],
                        "reason": aggregate.get("reason") or market.get("reason"),
                        "included": aggregate["included"],
                        "excluded": aggregate["excluded"],
                        "age_seconds": market.get("age_seconds"),
                        "observed_at": observation.get("observed_at"),
                        "received_at": observation.get("received_at"),
                        "price": observation.get("price"),
                        "source": observation.get("source"),
                        "kind": observation.get("kind"),
                        "limitations": prediction["limitations"],
                    }
                except FeedUnavailable as exc:
                    state["oracle"][asset] = {
                        "market": "unavailable",
                        "prediction": "unavailable",
                        "reason": exc.code,
                        "instrument": f"{asset}/USD",
                    }
            batch = f5_batch.status(batch_id, root=home / "batches")
            state["phase"] = batch["phase"]
            state["registration"] = sync_registrations(home, batch_id, home / "batches")
            update_telemetry(state, home, manager_home)
            try:
                state["forward_accounting"] = sync_performance(home)
            except (OSError, ValueError, sqlite3.Error):
                state["forward_accounting"] = {
                    "status": "unavailable",
                    "reason": "accounting_unavailable",
                }
            state["heartbeat_at"] = now
            state["runtime_controls_observed"] = runtime
            save(home / "state.json", state)
            cycle += 1
            if (
                batch["phase"] in {"interrupted", "planned", "stopped"}
                and not batch["running"]
                and runtime["batch_enabled"]
                and state.get("batch_restart_attempts", 0) < 3
            ):
                try:
                    with recovery_guard(home) as allowed:
                        if allowed and runtime_settings(home)["batch_enabled"]:
                            state["batch_restart_attempts"] = (
                                state.get("batch_restart_attempts", 0) + 1
                            )
                            f5_batch.start(batch_id, root=home / "batches")
                            state["batch_restart_requested"] = True
                except (OSError, RuntimeError, ValueError):
                    state["batch_restart_error"] = "batch_owner_unavailable"
                save(home / "state.json", state)
            # Keep coordination and its UI available even if research is blocked.
            # Failed evaluations never become a successful forward handoff.
            if max_cycles is not None and cycle >= max_cycles:
                return 0
            for _ in range(20):
                if stop_file.exists():
                    break
                time.sleep(0.1)
        f5_batch.stop(batch_id, root=home / "batches")
        state["phase"] = "stopped"
        save(home / "state.json", state)
        return 0


def update_telemetry(state: dict, home: Path, manager_home: Path | None) -> None:
    from .telemetry import sync

    try:
        state["telemetry"] = sync(home, manager_home)
    except (OSError, RuntimeError, ValueError):
        state["telemetry"] = {
            "status": "unavailable",
            "reason": "telemetry_unavailable",
        }

"""Durable, paper-only controls delegated to the established component owners."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import sqlite3
import threading
import time
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from . import runner

APP_ID = 0x53435432
MANAGER_ACTIONS = {
    "create",
    "edit",
    "apply",
    "start",
    "stop",
    "service",
    "prepare-input",
    "register-input",
    "data-check",
    "cycle-check",
}
ACTIONS = {
    "pipeline.start",
    "pipeline.stop",
    "pipeline.restart",
    "backtest.start",
    "backtest.stop",
    "backtest.restart",
    "oracle.start",
    "oracle.stop",
    "oracle.restart",
    "recorder.start",
    "recorder.stop",
    "research.launch",
    "pnl.recording.set",
    "oracle.voters.set",
    *("manager." + command for command in MANAGER_ACTIONS),
}
SENSITIVE = re.compile(
    r"secret|password|private.?key|api.?key|credential|authorization|token|signer|wallet|mnemonic|seed.?phrase",
    re.IGNORECASE,
)


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def runtime_settings(home: Path) -> dict:
    path = home / "runtime-settings.json"
    if not path.exists():
        return {
            "schema_version": 1,
            "revision": 0,
            "oracle_enabled": True,
            "batch_enabled": True,
            "recorder_enabled": True,
            "oracle_generation": 0,
        }
    if path.is_symlink():
        raise ValueError("invalid_runtime_settings")
    result = json.loads(path.read_text())
    if (
        not isinstance(result, dict)
        or result.get("schema_version") != 1
        or type(result.get("revision")) is not int
        or result["revision"] < 0
        or type(result.get("oracle_generation")) is not int
        or any(
            type(result.get(k)) is not bool
            for k in ("oracle_enabled", "batch_enabled", "recorder_enabled")
        )
    ):
        raise ValueError("invalid_runtime_settings")
    return result


def recorder_recovery_enabled(home: Path) -> bool:
    """Respect the parent control family's explicit shared-recorder pause."""
    enabled = runtime_settings(home)["recorder_enabled"]
    if home.parent.name == "research":
        parent = home.parent.parent
        if (parent / "control.sqlite3").is_file():
            with database(parent) as db:
                owned = db.execute(
                    "SELECT 1 FROM experiment WHERE home=?", (str(home),)
                ).fetchone()
            if owned:
                enabled = enabled and runtime_settings(parent)["recorder_enabled"]
    return enabled


@contextmanager
def recovery_guard(home: Path):
    """Serialize automatic recovery with explicit actions in this control family."""
    root = home
    if home.parent.name == "research":
        candidate = home.parent.parent
        if (candidate / "control.sqlite3").is_file():
            with database(candidate) as db:
                if db.execute(
                    "SELECT 1 FROM experiment WHERE home=?", (str(home),)
                ).fetchone():
                    root = candidate
    fd = os.open(
        root / "control-action.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600
    )
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
        else:
            yield True
    finally:
        os.close(fd)


def _safe_input(value, depth=0):
    if depth > 12:
        raise ValueError("invalid_action_parameters")
    if isinstance(value, dict):
        if len(value) > 80 or any(
            not isinstance(k, str) or SENSITIVE.search(k) for k in value
        ):
            raise ValueError("credential_parameters_forbidden")
        for key, item in value.items():
            if (
                key == "mode" and item not in {"paper", "prospective", "historical"}
            ) or (key == "armed" and item is not False):
                raise ValueError("paper_only")
            _safe_input(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > 1000:
            raise ValueError("invalid_action_parameters")
        for item in value:
            _safe_input(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > 4096 or any(ord(c) < 32 for c in value):
            raise ValueError("invalid_action_parameters")
    elif (
        type(value) is float
        and not math.isfinite(value)
        or value is not None
        and type(value) not in (str, int, float, bool)
    ):
        raise ValueError("invalid_action_parameters")


@contextmanager
def database(home: Path):
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = home / "control.sqlite3"
    if path.is_symlink():
        raise ValueError("invalid_control_store")
    with closing(sqlite3.connect(path, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        app = db.execute("PRAGMA application_id").fetchone()[0]
        tables = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        if app == 0 and not tables:
            for statement in (
                """CREATE TABLE action(id TEXT PRIMARY KEY, action TEXT NOT NULL,
                    digest TEXT NOT NULL, params TEXT NOT NULL, state TEXT NOT NULL,
                    created REAL NOT NULL, finished REAL, result TEXT, error TEXT)""",
                """CREATE TABLE experiment(id TEXT PRIMARY KEY, name TEXT NOT NULL,
                    home TEXT UNIQUE NOT NULL, created REAL NOT NULL)""",
            ):
                db.execute(statement)
            db.execute(f"PRAGMA application_id={APP_ID}")
            db.execute("PRAGMA user_version=1")
        elif app != APP_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise ValueError("invalid_control_store")
        path.chmod(0o600)
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise


def _public(row) -> dict:
    return {
        "id": row["id"],
        "action": row["action"],
        "state": row["state"],
        "created_at": row["created"],
        "finished_at": row["finished"],
        "result": json.loads(row["result"]) if row["result"] else None,
        "error": row["error"],
    }


class ControlPlane:
    def __init__(self, home: Path, manager_home: Path | None = None):
        from botmanager.store import data_home

        self.home = Path(home).expanduser().absolute()
        self.manager_home = (
            Path(manager_home).expanduser().absolute() if manager_home else data_home()
        )
        self._closed = threading.Event()
        self._worker = threading.Thread(
            target=self._work, daemon=True, name="paper-controls"
        )
        self._worker.start()

    def register_legacy(self) -> bool:
        """Register only the known sibling producer; never start or mutate it."""
        path = self.home.parent / "ecosystem-paper-v1"
        if (
            self.home.name != "ecosystem-paper-v2"
            or not (path / "state.json").is_file()
            or path.is_symlink()
        ):
            return False
        with database(self.home) as db:
            db.execute(
                "INSERT OR IGNORE INTO experiment VALUES(?,?,?,?)",
                ("legacy-v1", "Legacy V1 recorded evidence", str(path), 0),
            )
        return True

    def close(self):
        self._closed.set()
        self._worker.join(timeout=2)

    def actions(self, identity: str | None = None) -> dict:
        if identity is not None and str(UUID(identity)) != identity:
            raise ValueError("invalid_request_id")
        if not (self.home / "control.sqlite3").is_file():
            return {"actions": [], "action": None}
        with database(self.home) as db:
            if identity:
                row = db.execute(
                    "SELECT * FROM action WHERE id=?", (identity,)
                ).fetchone()
                return {"action": _public(row) if row else None}
            rows = db.execute(
                "SELECT * FROM action ORDER BY created DESC LIMIT 50"
            ).fetchall()
            return {"actions": [_public(row) for row in rows]}

    def submit(self, action: str, request_id: str, params: dict) -> tuple[dict, bool]:
        if action not in ACTIONS or not isinstance(params, dict):
            raise ValueError("unknown_action_or_parameters")
        if not isinstance(request_id, str) or str(UUID(request_id)) != request_id:
            raise ValueError("invalid_request_id")
        _safe_input(params)
        raw = canonical(params)
        digest = hashlib.sha256((action + "\0" + raw).encode()).hexdigest()
        with database(self.home) as db:
            row = db.execute(
                "SELECT * FROM action WHERE id=?", (request_id,)
            ).fetchone()
            if row:
                if row["digest"] != digest:
                    raise ValueError("request_id_conflict")
                return _public(row), False
            if (
                db.execute(
                    "SELECT count(*) FROM action WHERE state IN ('queued','running')"
                ).fetchone()[0]
                >= 100
            ):
                raise ValueError("action_queue_full")
            db.execute(
                "INSERT INTO action VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    request_id,
                    action,
                    digest,
                    raw,
                    "queued",
                    time.time(),
                    None,
                    None,
                    None,
                ),
            )
            return _public(
                db.execute("SELECT * FROM action WHERE id=?", (request_id,)).fetchone()
            ), True

    def _work(self):
        while not self._closed.wait(0.2):
            if not (self.home / "control.sqlite3").is_file():
                continue
            fd = None
            try:
                fd = os.open(
                    self.home / "control-action.lock",
                    os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
                    0o600,
                )
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with database(self.home) as db:
                    # A free owner lock proves no old action handler remains active.
                    # Never replay a mutation whose result was lost during shutdown.
                    db.execute(
                        "UPDATE action SET state='interrupted',error='reconcile_owner_before_retry',finished=? WHERE state='running'",
                        (time.time(),),
                    )
                    row = db.execute(
                        "SELECT * FROM action WHERE state='queued' ORDER BY created LIMIT 1"
                    ).fetchone()
                    if row is None:
                        continue
                    db.execute(
                        "UPDATE action SET state='running' WHERE id=?", (row["id"],)
                    )
                try:
                    result = self._execute(
                        row["action"], json.loads(row["params"]), row["id"]
                    )
                    state, error = "succeeded", None
                except Exception as exc:  # noqa: BLE001 - persisted public error codes only
                    result, state = None, "failed"
                    code = str(exc)
                    error = (
                        code
                        if isinstance(exc, ValueError)
                        and re.fullmatch(r"[a-z_]{1,90}", code)
                        else "owner_operation_failed"
                    )
                with database(self.home) as db:
                    db.execute(
                        "UPDATE action SET state=?,result=?,error=?,finished=? WHERE id=?",
                        (state, canonical(result), error, time.time(), row["id"]),
                    )
            except (OSError, ValueError, sqlite3.Error):
                # Unavailable durable state never authorizes an unrecorded side effect.
                pass
            finally:
                if fd is not None:
                    os.close(fd)

    def _manager(self, command: str, params: dict) -> dict:
        from botmanager.registry import CommandContext, dispatch

        result = dispatch(
            command,
            params,
            CommandContext(home=self.manager_home, ecosystem_home=self.home),
        )
        if not result["ok"]:
            raise ValueError(result["error"]["code"])
        return result["data"]

    def _manager_input(self, command: str, params: dict, request_id: str) -> dict:
        identity = params.get("identity")
        if not isinstance(identity, str) or not identity or len(identity) > 100:
            raise ValueError("invalid_bot_identity")
        allowed = {"identity", "mode"} if command == "prepare-input" else {"identity"}
        if set(params) - allowed:
            raise ValueError("invalid_action_parameters")
        if command == "cycle-check":
            return {
                "status": "unavailable",
                "reason": "actual_cycle_evidence_unavailable",
                "live_eligible": False,
            }
        if command == "data-check":
            return self._manager(command, {"identity": identity})
        if command == "prepare-input":
            mode = params.get("mode", "prospective")
            if mode not in {"prospective", "historical"}:
                raise ValueError("invalid_input_mode")
            directory = self.home / "manager-inputs"
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if directory.is_symlink():
                raise ValueError("invalid_input_home")
            output = directory / (UUID(request_id).hex + ".json")
            return self._manager(
                command,
                {
                    "identity": identity,
                    "archive": "shared-sol-usd",
                    "reference": True,
                    "mode": mode,
                    "output": str(output),
                },
            )
        with database(self.home) as db:
            rows = db.execute(
                "SELECT params,result FROM action WHERE action='manager.prepare-input' AND state='succeeded' ORDER BY finished DESC"
            ).fetchall()
        for row in rows:
            if json.loads(row["params"]).get("identity") == identity:
                descriptor = Path(json.loads(row["result"])["descriptor_path"])
                if (
                    descriptor.parent != self.home / "manager-inputs"
                    or descriptor.is_symlink()
                ):
                    raise ValueError("invalid_input_home")
                return self._manager(
                    "register-input",
                    {"identity": identity, "descriptor": str(descriptor)},
                )
        raise ValueError("prepared_input_unavailable")

    def _runtime(self, home=None, **changes) -> dict:
        home = home or self.home
        current = runtime_settings(home)
        current.update(changes)
        current["revision"] += 1
        runner.save(home / "runtime-settings.json", current)
        return current

    def _stop_pipeline(self, home):
        result = runner.stop(home)
        until = time.monotonic() + 35
        while runner.running(home) and time.monotonic() < until:
            time.sleep(0.1)
        if runner.running(home):
            raise ValueError("pipeline_stop_not_observed")
        return result

    def _execute(self, action: str, params: dict, request_id: str) -> dict:
        from soltui import f5_batch, pricefeed

        params = dict(params)
        home = self.experiment_home(params.pop("run_id", None))

        if action.startswith("manager."):
            command = action.split(".", 1)[1]
            if "descriptor" in params:
                raise ValueError("arbitrary_descriptor_forbidden")
            if command in {
                "prepare-input",
                "register-input",
                "data-check",
                "cycle-check",
            }:
                return self._manager_input(command, params, request_id)
            if command != "service":
                params = (
                    {**params, "request_id": request_id}
                    if command in {"edit", "apply", "start", "stop"}
                    else params
                )
            return self._manager(command, params)
        if action == "research.launch":
            return self._launch(params, request_id)
        if action == "pnl.recording.set":
            from .performance import set_recording

            if set(params) != {"enabled", "expected_revision"}:
                raise ValueError("invalid_action_parameters")
            return set_recording(home, **params)
        if action == "oracle.voters.set":
            from .votes import set_voters

            if set(params) != {"instrument", "ids", "expected_revision"}:
                raise ValueError("invalid_action_parameters")
            return set_voters(home, **params)
        if home != self.home and home == self.home.parent / "ecosystem-paper-v1":
            raise ValueError("legacy_source_read_only")
        if action.startswith("recorder."):
            if action == "recorder.stop":
                if params != {"acknowledge_shared": True}:
                    raise ValueError("shared_recorder_acknowledgment_required")
                self._runtime(self.home, recorder_enabled=False)
                self._runtime(
                    home, recorder_enabled=False
                ) if home != self.home else None
                return {
                    **pricefeed.stop_recorder(),
                    "recovery_scope": "owned_control_family",
                    "external_owners_may_restart": True,
                }
            if params:
                raise ValueError("invalid_action_parameters")
            self._runtime(self.home, recorder_enabled=True)
            if home != self.home:
                self._runtime(home, recorder_enabled=True)
            return pricefeed.ensure_recorder(install=False)
        if params:
            raise ValueError("invalid_action_parameters")
        if action.startswith("pipeline."):
            if action == "pipeline.stop":
                return self._stop_pipeline(home)
            if action == "pipeline.restart":
                self._stop_pipeline(home)
            if runner.running(home):
                return {"status": "already_running"}
            return runner.start(home)
        if action.startswith("oracle."):
            if (
                runner.running(home)
                and runner.load(home).get("control_contract_version") != 1
            ):
                raise ValueError("current_pipeline_controls_unavailable")
            changes = {"oracle_enabled": action != "oracle.stop"}
            if action == "oracle.restart":
                changes["oracle_generation"] = (
                    runtime_settings(home)["oracle_generation"] + 1
                )
            return self._runtime(home, **changes)
        if action.startswith("backtest."):
            state = runner.load(home)
            if not state.get("batch_id"):
                raise ValueError("batch_unavailable")
            batch_id, root = state["batch_id"], home / "batches"
            self._runtime(home, batch_enabled=action != "backtest.stop")
            if action in {"backtest.stop", "backtest.restart"}:
                f5_batch.stop(batch_id, root=root)
                until = time.monotonic() + 35
                while (
                    f5_batch.status(batch_id, root=root)["running"]
                    and time.monotonic() < until
                ):
                    time.sleep(0.1)
                if f5_batch.status(batch_id, root=root)["running"]:
                    raise ValueError("batch_stop_not_observed")
            if action == "backtest.stop":
                return {"status": "stopped", "preserves_evidence": True}
            return f5_batch.start(batch_id, root=root)
        raise ValueError("unknown_action")

    def _launch(self, params: dict, request_id: str) -> dict:
        from .data import universe
        from .performance import set_recording

        allowed = {
            "name",
            "coins",
            "strategies",
            "intervals",
            "horizons",
            "start",
            "end",
            "capital",
            "record_pnl",
            "swap_provider",
            "cost_model",
        }
        if set(params) - allowed:
            raise ValueError("invalid_launch_parameters")
        name = params.get("name", "Paper experiment")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError("invalid_experiment_name")
        enabled = params.get("record_pnl", True)
        if type(enabled) is not bool:
            raise ValueError("invalid_recording_policy")
        if params.get("swap_provider", "jupiter") not in {"jupiter", "reference"}:
            raise ValueError("unsupported_swap_provider")
        capital = params.get("capital", 10000.0)
        if (
            type(capital) not in (float, int)
            or not math.isfinite(capital)
            or not 0 < capital <= 100_000_000
        ):
            raise ValueError("invalid_paper_capital")
        coins = params.get("coins", ["SOL"])
        if not isinstance(coins, list) or not set(coins) <= set(universe()):
            raise ValueError("invalid_coin_selection")
        directory = self.home / "research" / UUID(request_id).hex
        config = {
            "coins": coins,
            "intervals": params.get("intervals", ["1d"]),
            "horizons": params.get("horizons", ["medium"]),
            "strategies": params.get("strategies", ["rsi"]),
            "start": params.get("start", "2025-01-01"),
            "end": params.get("end", datetime.now(UTC).date().isoformat()),
            "manager_home": str(self.manager_home),
            "research_capital": float(capital),
            "swap_provider": params.get("swap_provider", "jupiter"),
            "cost_model": params.get("cost_model"),
            "embedded_ui": False,
        }
        state = runner.plan(directory, **config)
        with database(self.home) as db:
            db.execute(
                "INSERT OR IGNORE INTO experiment VALUES(?,?,?,?)",
                (state["run_id"], name.strip(), str(directory), time.time()),
            )
        if not enabled:
            set_recording(directory, False, 0)
        return {
            "experiment_id": state["run_id"],
            "home": str(directory),
            "name": name.strip(),
            **runner.start(directory),
        }

    def experiments(self) -> list[dict]:
        result = [{"id": "current", "name": "Current pipeline", "home": str(self.home)}]
        if (self.home / "control.sqlite3").is_file():
            with database(self.home) as db:
                result += [
                    dict(row)
                    for row in db.execute(
                        "SELECT id,name,home FROM experiment ORDER BY created DESC LIMIT 100"
                    )
                ]
        return result

    def experiment_home(self, identity: str | None) -> Path:
        if identity in (None, "current"):
            return self.home
        if (self.home / "control.sqlite3").is_file():
            with database(self.home) as db:
                row = db.execute(
                    "SELECT home FROM experiment WHERE id=?", (identity,)
                ).fetchone()
            if row:
                path = Path(row["home"])
                legacy = (
                    identity == "legacy-v1"
                    and self.home.name == "ecosystem-paper-v2"
                    and path == self.home.parent / "ecosystem-paper-v1"
                )
                if (
                    path.parent != self.home / "research" and not legacy
                ) or path.is_symlink():
                    raise ValueError("invalid_experiment_home")
                return path
        raise ValueError("unknown_experiment")

    def snapshot(self, run_id=None) -> dict:
        from backtester.core.strategies import REGISTRY
        from soltui import config, pricefeed

        from .data import universe
        from .performance import recording

        active_home = self.experiment_home(run_id)
        read_only_source = run_id == "legacy-v1"
        state = runner.status(active_home)
        prefs = runtime_settings(active_home)
        active = state["supervisor_running"]
        controls_ready = state.get("control_contract_version") == 1
        observed = state.get("runtime_controls_observed", {})
        initialized = state["phase"] != "not_initialized"

        def action(name, label, enabled=True, reason=None, **params):
            return {
                "action": name,
                "label": label,
                "enabled": enabled and not read_only_source,
                "reason": "legacy_source_read_only"
                if read_only_source
                else reason
                if not enabled
                else None,
                "params": {**params, **({"run_id": run_id} if run_id else {})},
            }

        servers = [
            {
                "id": "pipeline",
                "label": "Paper pipeline",
                "owner": "ecosystem.runner",
                "state": state["phase"],
                "running": active,
                "pid": state.get("supervisor_pid") if active else None,
                "heartbeat_at": state.get("heartbeat_at"),
                "actions": [
                    action(
                        "pipeline.start",
                        "Start pipeline",
                        initialized and not active,
                        "already_running_or_not_planned",
                    ),
                    action("pipeline.stop", "Stop pipeline", active, "not_running"),
                    action(
                        "pipeline.restart", "Restart pipeline", active, "not_running"
                    ),
                ],
            }
        ]
        batch = state.get("batch", {})
        servers.append(
            {
                "id": "backtest",
                "label": "Backtest / forward worker",
                "owner": "soltui.f5_batch",
                "state": batch.get("phase", "unavailable"),
                "running": batch.get("running", False),
                "actions": [
                    action(
                        "backtest." + name,
                        label,
                        bool(state.get("batch_id")),
                        "batch_unavailable",
                    )
                    for name, label in (
                        ("start", "Start worker"),
                        ("stop", "Stop worker"),
                        ("restart", "Restart worker"),
                    )
                ],
            }
        )
        servers.append(
            {
                "id": "oracle",
                "label": "Oracle forecasts",
                "owner": "ecosystem.runner / oracle",
                "state": "running"
                if active and observed.get("oracle_enabled")
                else "paused"
                if active and controls_ready
                else "unverified"
                if active
                else "stopped",
                "running": active and observed.get("oracle_enabled", False),
                "desired_enabled": prefs["oracle_enabled"],
                "version": state.get("ecosystem_version"),
                "heartbeat_at": state.get("heartbeat_at"),
                "actions": [
                    action(
                        "oracle." + name,
                        label,
                        active and controls_ready,
                        "restart_with_current_pipeline_first",
                    )
                    for name, label in (
                        ("start", "Start Oracle"),
                        ("stop", "Pause Oracle"),
                        ("restart", "Restart Oracle"),
                    )
                ],
            }
        )
        try:
            recorder = pricefeed.status()
            recorder = {
                k: recorder.get(k)
                for k in (
                    "running",
                    "pid",
                    "live",
                    "snapshot_age_s",
                    "messages",
                    "snapshots",
                    "reconnects",
                    "recorded_days",
                    "dir",
                )
            }
        except (OSError, ValueError, TypeError):
            recorder = {"running": False, "reason": "recorder_unavailable"}
        servers.append(
            {
                "id": "recorder",
                "label": "Shared market recorder",
                "owner": "soltui.pricefeed",
                "state": "running" if recorder["running"] else "stopped",
                **recorder,
                "recovery_enabled": recorder_recovery_enabled(active_home),
                "recovery_scope": "owned_control_family",
                "external_owners_may_restart": True,
                "actions": [
                    action("recorder.start", "Start recorder"),
                    action(
                        "recorder.stop", "Stop shared recorder", acknowledge_shared=True
                    ),
                ],
            }
        )
        try:
            manager = self._manager("status", {})
            schema = self._manager("schema", {})
            service = self._manager("service", {"action": "status"})
            configs = self._manager("list", {}).get("bots", [])
        except (ValueError, OSError):
            manager, schema, service, configs = {}, {}, {}, []
        servers.append(
            {
                "id": "manager",
                "label": "Bot Manager",
                "owner": "botmanager.suite"
                if service.get("suite_owner_lock_held")
                else "botmanager.service",
                "state": "running"
                if service.get("supervisor_lock_held")
                else "stopped",
                "running": bool(service.get("supervisor_lock_held")),
                "service": service,
                "actions": [
                    {
                        "action": "manager.service",
                        "label": "Install / start manager",
                        "enabled": service.get("platform") == "darwin"
                        and not service.get("managed_by_suite"),
                        "reason": "managed_by_suite"
                        if service.get("managed_by_suite")
                        else None
                        if service.get("platform") == "darwin"
                        else "macos_service_required",
                        "params": {"action": "install"},
                    },
                    {
                        "action": "manager.service",
                        "label": "Uninstall / stop manager",
                        "enabled": bool(service.get("definition_present"))
                        and not service.get("managed_by_suite"),
                        "reason": "managed_by_suite"
                        if service.get("managed_by_suite")
                        else None
                        if service.get("definition_present")
                        else "service_not_installed",
                        "params": {"action": "uninstall"},
                    },
                ],
            }
        )
        runs = []
        for row in self.experiments():
            try:
                current = runner.status(self.experiment_home(row["id"]))
                b = current.get("batch", {})
                total = b.get("total", 0)
                done = sum(
                    v
                    for k, v in b.get("counts", {}).items()
                    if k not in {"pending", "running"}
                )
                stages = [
                    {
                        "id": "acquisition",
                        "state": "complete"
                        if current.get("batch_id")
                        else current["phase"],
                        "done": len(current.get("acquisitions", {})),
                        "total": len(current.get("config", {}).get("coins", []))
                        * len(current.get("config", {}).get("intervals", [])),
                    },
                    {
                        "id": "backtest",
                        "state": "complete"
                        if total and done == total
                        else b.get("phase", "waiting"),
                        "done": done,
                        "total": total,
                    },
                    {
                        "id": "forward",
                        "state": b.get("phase", "waiting")
                        if total and done == total
                        else "waiting",
                        "done": sum(
                            x.get("trials_recorded", 0)
                            for x in b.get("forward_checks", [])
                        ),
                        "total": sum(
                            x.get("trials_expected", 0)
                            for x in b.get("forward_checks", [])
                        ),
                    },
                    {
                        "id": "live",
                        "state": "unavailable",
                        "done": 0,
                        "total": 1,
                        "reason": "separate_live_readiness_required",
                    },
                ]
                for stage in stages:
                    stage["percent"] = (
                        100 * stage["done"] / stage["total"] if stage["total"] else None
                    )
                runs.append(
                    {
                        **row,
                        "phase": current["phase"],
                        "running": current["supervisor_running"],
                        "progress": {
                            "done": done,
                            "total": total,
                            "percent": 100 * done / total if total else None,
                        },
                        "stages": stages,
                        "counts": b.get("counts", {}),
                        "config": current.get("config"),
                    }
                )
            except (OSError, ValueError, TypeError):
                runs.append({**row, "phase": "unavailable", "stages": []})
        try:
            recording_state = recording(active_home)
        except (OSError, ValueError, sqlite3.Error):
            recording_state = {
                "enabled": None,
                "revision": None,
                "status": "unavailable",
            }
        return {
            "schema_version": 1,
            "revision": prefs["revision"],
            "scope": "paper_controls",
            "active_run_id": run_id or "current",
            "read_only_source": read_only_source,
            "mutation_allowed": not read_only_source,
            "servers": servers,
            "configs": configs,
            "statuses": manager,
            "runs": runs,
            "recording": recording_state,
            "recent_actions": self.actions()["actions"],
            "catalog": {
                "coins": list(universe()),
                "strategies": [
                    {"id": name, "label": name.replace("_", " ")}
                    for name in sorted(REGISTRY)
                ],
                "intervals": list(config.INTERVALS),
                "horizons": ["short", "medium", "long"],
                "manager_schema": schema,
                "swap_provider": state.get("config", {}).get(
                    "swap_provider", "reference"
                ),
                "cost_model": state.get("config", {}).get("cost_model"),
            },
        }

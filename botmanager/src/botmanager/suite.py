"""One availability parent around the existing manager and control-room owner.

The suite does not create bot intent, record market data or start research. Its
OS service restarts availability; the existing Supervisor retains trading state.
"""

from __future__ import annotations

import argparse
import os
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from pathlib import Path
from uuid import uuid4

from . import machine_health
from .domain import ManagerError, canonical
from .supervisor import Supervisor
from .transport import _owner_path, _peer, _read
from .worker import lifetime_lock, lock_held

MAX_ALERTS = 256
ALERT_COOLDOWN_SECONDS = 300
STARTUP_SECONDS = 12
_ALERT_JOURNAL_LOCK = threading.Lock()
_ALERT_JOURNAL_LAST_OBSERVED: dict[tuple[str, str], float] = {}


def _directory(home):
    directory = home / ".suite"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ManagerError(
            "suite_config_unavailable", "Suite directory is unavailable.", 3
        )
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        directory.stat().st_uid != os.getuid()
        or stat.S_IMODE(directory.stat().st_mode) & 0o077
    ):
        raise ManagerError(
            "suite_config_unavailable", "Suite directory is not private.", 3
        )
    return directory


def _write(path, value):
    raw = canonical(value).encode()
    if len(raw) > machine_health.MAX_BYTES:
        raise ManagerError("suite_unavailable", "Suite record exceeds its bound.", 4)
    fd, temporary = tempfile.mkstemp(prefix=".suite-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_config(home, ecosystem_home):
    directory = _directory(home)
    wanted = {
        "schema_version": 1,
        "manager_home": str(home),
        "ecosystem_home": str(ecosystem_home),
    }
    try:
        current = machine_health.private_read(directory / "config.json", limit=16_384)
    except FileNotFoundError:
        current = None
    if current == wanted:
        return
    if current is not None and (
        lock_held(directory / "owner.lock") or lock_held(home / "supervisor.lock")
    ):
        raise ManagerError(
            "identity_conflict", "A running suite is bound to another configuration.", 3
        )
    _write(directory / "config.json", wanted)


def alerts(home=None, after=0, limit=100):
    home, _ = machine_health.homes(home)
    if (
        type(after) is not int
        or after < 0
        or type(limit) is not int
        or not 1 <= limit <= 100
    ):
        raise ManagerError("invalid_input", "Alert page arguments are invalid.")
    try:
        body = machine_health.private_read(home / ".suite" / "alerts.json")
    except FileNotFoundError:
        return {
            "schema_version": 1,
            "events": [],
            "next_after": after,
            "has_more": False,
            "oldest_sequence": None,
        }
    except (OSError, ValueError, TypeError) as exc:
        raise ManagerError(
            "suite_unavailable", "Component alert journal is unavailable.", 4
        ) from exc
    events = body.get("events")
    if (
        body.get("schema_version") != 1
        or not isinstance(events, list)
        or len(events) > MAX_ALERTS
    ):
        raise ManagerError(
            "suite_unavailable", "Component alert journal is unavailable.", 4
        )
    selected = []
    for row in events:
        if (
            not isinstance(row, dict)
            or type(row.get("sequence")) is not int
            or row.get("component") not in machine_health.COMPONENTS
            or row.get("state") not in machine_health.STATES
        ):
            raise ManagerError(
                "suite_unavailable", "Component alert journal is unavailable.", 4
            )
        if row["sequence"] > after:
            selected.append(row)
    page = selected[:limit]
    oldest = events[0]["sequence"] if events else None
    return {
        "schema_version": 1,
        "events": page,
        "next_after": page[-1]["sequence"] if page else after,
        "has_more": len(selected) > limit,
        "oldest_sequence": oldest,
        "history_truncated": oldest is not None and after < oldest - 1,
    }


class AlertJournal:
    def __init__(self, home):
        self.path = home / ".suite" / "alerts.json"

    def observe(self, snapshot):
        # Concurrent health publishes must not overwrite each other's durable
        # transitions. Suite ownership already excludes another process.
        observed_at = snapshot.get("observed_at")
        if (
            type(observed_at) not in (int, float)
            or not 0 <= observed_at < float("inf")
        ):
            raise ValueError("component_alert_snapshot_invalid")
        with _ALERT_JOURNAL_LOCK:
            stale_components = set()
            for name in snapshot["components"]:
                key = (str(self.path), name)
                previous = _ALERT_JOURNAL_LAST_OBSERVED.get(key)
                if previous is not None and observed_at <= previous:
                    stale_components.add(name)
            self._observe_locked(snapshot, stale_components)
            for name in snapshot["components"]:
                if name not in stale_components:
                    _ALERT_JOURNAL_LAST_OBSERVED[(str(self.path), name)] = observed_at

    def _observe_locked(self, snapshot, stale_components):
        try:
            body = machine_health.private_read(self.path)
        except FileNotFoundError:
            body = {"schema_version": 1, "next_sequence": 1, "events": [], "last": {}}
        if (
            body.get("schema_version") != 1
            or type(body.get("next_sequence")) is not int
            or body["next_sequence"] < 1
            or not isinstance(body.get("events"), list)
            or len(body["events"]) > MAX_ALERTS
            or not isinstance(body.get("last"), dict)
            or set(body["last"]) - set(machine_health.COMPONENTS)
        ):
            raise ValueError("component_alert_journal_invalid")
        changed = False
        for name, row in snapshot["components"].items():
            prior = body["last"].get(name)
            if prior is not None and (
                not isinstance(prior, dict)
                or type(prior.get("at")) not in (int, float)
                or not 0 <= prior["at"] < float("inf")
                or prior.get("state") not in machine_health.STATES
            ):
                raise ValueError("component_alert_journal_invalid")
            if name in stale_components or (
                prior is not None and snapshot["observed_at"] <= prior["at"]
            ):
                # A slower publisher can finish after a newer observation. Do
                # not let its stale state reverse the component's alert history.
                continue
            # An absent optional reference source is a readiness limitation,
            # not an invented recorder failure or a reason to start one.
            if (
                name == "market_data"
                and row["reason"] == "reference_archive_absent"
                and prior is None
            ):
                continue
            unhealthy = row["state"] != "up"
            now = snapshot["observed_at"]
            transition = prior is not None and (
                prior["state"],
                prior.get("reason"),
            ) != (row["state"], row["reason"])
            reminder = (
                unhealthy
                and prior is not None
                and now - prior["at"] >= ALERT_COOLDOWN_SECONDS
            )
            if (prior is None and unhealthy) or transition or reminder:
                event = {
                    "sequence": body["next_sequence"],
                    "observed_at": now,
                    "component": name,
                    "state": row["state"],
                    "reason": row["reason"],
                    "kind": "component_failure" if unhealthy else "component_recovered",
                }
                body["next_sequence"] += 1
                body["events"] = (body["events"] + [event])[-MAX_ALERTS:]
                body["last"][name] = {
                    "at": now,
                    "state": row["state"],
                    "reason": row["reason"],
                }
                print(canonical(event), file=sys.stderr, flush=True)
                changed = True
            elif prior is None:
                body["last"][name] = {
                    "at": now,
                    "state": row["state"],
                    "reason": row["reason"],
                }
                changed = True
        if changed:
            _write(self.path, body)


def _terminate(process):
    if process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=0.3)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=0.3)
        except subprocess.TimeoutExpired:
            return False
    return True


class UiMonitor:
    """Only the actual Popen supplied by ui_service can become an owned child."""

    def __init__(self, home, manager_home, ensure=None, probe=None):
        self.home, self.manager_home = home, manager_home
        self.ensure = ensure
        self.probe = probe
        self.stopping = threading.Event()
        self.lock = threading.Lock()
        self.child = None
        self.result = {
            "running": False,
            "reason": "control_start_pending",
            "occupied": False,
        }
        self.thread = None
        self.events = deque(maxlen=32)
        self.last_observed = None

    def _record(self, value):
        with self.lock:
            self.result = dict(value)
            row, _ = self._current_locked()
            state = row["state"], row["reason"]
            if state != self.last_observed:
                self.events.append(row)
                self.last_observed = state

    def drain_events(self):
        with self.lock:
            events = list(self.events)
            self.events.clear()
        return events

    def restore_events(self, events):
        with self.lock:
            self.events.extendleft(reversed(events))

    def _spawned(self, process):
        with self.lock:
            if not self.stopping.is_set():
                self.child = process
                return
        _terminate(process)

    def start(self):
        self.thread = threading.Thread(
            target=self._run, name="solbot-control-room-watch", daemon=True
        )
        self.thread.start()

    def _run(self):
        if self.ensure is None:
            from ecosystem.ui_service import ensure, status

            self.ensure = ensure
            self.probe = status
        failures = 0
        while not self.stopping.is_set():
            try:
                with self.lock:
                    owned = self.child
                if owned is not None and owned.poll() is not None:
                    self._record(
                        {
                            "running": False,
                            "reason": "control_process_exited",
                            "occupied": False,
                        }
                    )
                elif self.probe is not None:
                    self._record(self.probe(self.home, self.manager_home))
                value = self.ensure(
                    self.home, self.manager_home, on_spawn=self._spawned
                )
            except (OSError, RuntimeError, ValueError, TypeError):
                value = {
                    "running": False,
                    "reason": "control_server_start_failed",
                    "occupied": False,
                }
            self._record(value)
            with self.lock:
                owned = self.child
            if value.get("running"):
                failures = 0
            else:
                failures = min(failures + 1, 5)
                # A timed out or unresponsive process is restarted only when
                # this monitor owns its actual Popen; an adopted PID is inert.
                if (
                    owned is not None
                    and value.get("reason") != "control_checkpoint_pending"
                    and _terminate(owned)
                ):
                    with self.lock:
                        if self.child is owned:
                            self.child = None
            self.stopping.wait(min(2**failures, 30) if failures else 2)

    def current(self):
        with self.lock:
            return self._current_locked()

    def _current_locked(self):
        value = self.result
        ownership = "owned" if self.child is not None else "existing_owner"
        if value.get("running"):
            return machine_health.component(
                "up", "available", ready=True, ownership=ownership
            ), value.get("url")
        reason = value.get("reason") or "control_server_unavailable"
        if (
            not isinstance(reason, str)
            or len(reason) > 100
            or not reason.replace("_", "").isalnum()
        ):
            reason = "control_server_unavailable"
        return machine_health.component(
            "unknown" if value.get("occupied") else "down",
            reason,
            ready=False,
            ownership=ownership,
        ), None

    def close(self):
        self.stopping.set()
        with self.lock:
            child = self.child
        released = child is None or _terminate(child)
        if self.thread is not None:
            self.thread.join(timeout=0.5)
        with self.lock:
            late = self.child
        if late is not None and late is not child:
            released = _terminate(late) and released
        return released, child is None


class Suite:
    def __init__(
        self,
        home=None,
        ecosystem_home=None,
        *,
        supervisor_factory=Supervisor,
        ui_factory=UiMonitor,
    ):
        self.home, self.ecosystem_home = machine_health.homes(home, ecosystem_home)
        self.instance = uuid4().hex
        self.stopping = threading.Event()
        self.supervisor_factory, self.ui_factory = supervisor_factory, ui_factory
        self.supervisor = None
        self.ui = None
        self.socket = None
        self.lease = None
        self.last_write = 0.0
        self.monitor_ready = True
        self.ui_retained = False

    def open(self):
        directory = _directory(self.home)
        save_config(self.home, self.ecosystem_home)
        self.lease = lifetime_lock(directory / "owner.lock")
        try:
            self.lease.__enter__()
        except BlockingIOError as exc:
            self.lease = None
            raise ManagerError(
                "suite_owner_conflict", "Another suite owns this home.", 3
            ) from exc
        try:
            self.supervisor = self.supervisor_factory(self.home).open()
            path = directory / "control.sock"
            if path.exists():
                _owner_path(path)
                path.unlink()
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.bind(str(path))
            path.chmod(0o600)
            self.socket.listen(8)
            self.socket.setblocking(False)
            self.ui = self.ui_factory(self.ecosystem_home, self.home)
            self.ui.start()
            try:
                self.record_unclean_restart()
            except (OSError, ValueError, TypeError, ManagerError):
                self.monitor_ready = False
            self.publish()
            return self
        except BaseException:
            self.close()
            raise

    def record_unclean_restart(self):
        try:
            prior = machine_health.private_read(
                self.home / ".suite/state.json", limit=16_384
            )
        except FileNotFoundError:
            return
        if (
            prior.get("schema_version") == 1
            and prior.get("manager_home") == str(self.home)
            and prior.get("ecosystem_home") == str(self.ecosystem_home)
            and prior.get("instance") != self.instance
            and prior.get("state") in ("running", "starting")
        ):
            value = machine_health.snapshot(
                self.home,
                self.ecosystem_home,
                owned_suite=machine_health.component(
                    "down", "unclean_suite_exit", ready=False
                ),
                owned_manager=machine_health.component("up", "available", ready=True),
                ui=self.ui.current(),
            )
            AlertJournal(self.home).observe(value)

    def _poll(self):
        try:
            client, _ = self.socket.accept()
        except BlockingIOError:
            return
        with client:
            try:
                _peer(client)
                value = _read(client, 4096, time.monotonic() + 0.2)
                if (
                    not isinstance(value, dict)
                    or set(value) != {"operation", "instance"}
                    or value["instance"] != self.instance
                    or value["operation"] not in ("ping", "stop")
                ):
                    return
                result = {
                    "schema_version": 1,
                    "instance": self.instance,
                    "pid": os.getpid(),
                }
                if value["operation"] == "stop":
                    self.stopping.set()
                client.sendall((canonical(result) + "\n").encode())
            except (OSError, ValueError, ManagerError):
                return

    def publish(self):
        now = time.time()
        health = machine_health.snapshot(
            self.home,
            self.ecosystem_home,
            now=now,
            owned_suite=machine_health.component("up", "available", ready=True),
            owned_manager=machine_health.component("up", "available", ready=True),
            ui=self.ui.current(),
        )
        transitions = self.ui.drain_events() if hasattr(self.ui, "drain_events") else []
        try:
            for row in transitions:
                AlertJournal(self.home).observe(
                    {
                        **health,
                        "observed_at": time.time(),
                        "components": {**health["components"], "control_room": row},
                    }
                )
            AlertJournal(self.home).observe(health)
            self.monitor_ready = True
        except (OSError, ValueError, TypeError, ManagerError):
            self.monitor_ready = False
            if transitions:
                self.ui.restore_events(transitions)
        _write(
            self.home / ".suite/state.json",
            {
                "schema_version": 1,
                "instance": self.instance,
                "pid": os.getpid(),
                "manager_home": str(self.home),
                "ecosystem_home": str(self.ecosystem_home),
                "heartbeat": now,
                "state": "running" if health["ready"] else "starting",
                "monitor_ready": self.monitor_ready,
                "ui_url": health["ui_url"],
            },
        )
        self.last_write = time.monotonic()
        self.rotate_logs()

    def rotate_logs(self):
        for number, name in ((1, "suite.stdout.log"), (2, "suite.stderr.log")):
            path = self.home / ".suite" / name
            try:
                info, active = path.stat(), os.fstat(number)
                if (
                    (info.st_dev, info.st_ino) != (active.st_dev, active.st_ino)
                    or not stat.S_ISREG(active.st_mode)
                    or info.st_size <= 1024 * 1024
                ):
                    continue
                with path.open("rb") as handle:
                    handle.seek(max(0, info.st_size - 65536))
                    tail = handle.read(65536)
                backup = path.with_suffix(path.suffix + ".1")
                fd = os.open(
                    backup, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
                )
                with os.fdopen(fd, "wb") as handle:
                    handle.write(tail)
                os.ftruncate(number, 0)
                os.lseek(number, 0, os.SEEK_SET)
            except OSError:
                continue

    def step(self):
        self.supervisor.step()
        self._poll()
        if time.monotonic() - self.last_write >= 1:
            self.publish()

    def close(self):
        self.stopping.set()
        failure = None
        # Keep the existing Supervisor's reap-before-journal ordering ahead of
        # optional helper teardown, including when its SQLite journal is frozen.
        if self.supervisor is not None:
            try:
                self.supervisor.close()
            except ManagerError as exc:
                failure = exc
            self.supervisor = None
        if self.ui is not None:
            released, self.ui_retained = self.ui.close()
            if not released:
                failure = ManagerError(
                    "suite_unavailable", "Owned control-room release is unconfirmed.", 4
                )
            self.ui = None
        if self.lease is not None:
            try:
                _write(
                    self.home / ".suite/state.json",
                    {
                        "schema_version": 1,
                        "instance": self.instance,
                        "pid": os.getpid(),
                        "manager_home": str(self.home),
                        "ecosystem_home": str(self.ecosystem_home),
                        "heartbeat": time.time(),
                        "state": "stopped"
                        if failure is None
                        else "release_unconfirmed",
                        "monitor_ready": False,
                        "ui_retained": self.ui_retained if failure is None else None,
                        "release_confirmed": failure is None,
                    },
                )
            except (OSError, ManagerError):
                failure = failure or ManagerError(
                    "suite_unavailable", "Suite stop receipt could not be saved.", 4
                )
        if self.socket is not None:
            self.socket.close()
            self.socket = None
            path = self.home / ".suite/control.sock"
            if path.exists():
                _owner_path(path)
                path.unlink()
        if self.lease is not None:
            self.lease.__exit__(None, None, None)
            self.lease = None
        if failure is not None:
            raise failure

    def run(self):
        def stop(signum, frame):
            self.stopping.set()

        previous = {
            sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)
        }
        try:
            self.open()
            while not self.stopping.is_set():
                self.step()
                self.stopping.wait(0.05)
        finally:
            try:
                self.close()
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
        return {
            "state": "stopped",
            "desired_bot_intent_retained": True,
            "ui_retained": self.ui_retained,
        }


def status(home=None, ecosystem_home=None, *, include_service=True):
    home, ecosystem_home = machine_health.homes(home, ecosystem_home)
    health = machine_health.check(home, ecosystem_home)
    state = (
        "running"
        if health["components"]["suite"]["state"] == "up"
        else "stopped"
        if health["components"]["suite"]["state"] == "down"
        else "unknown"
    )
    result = {
        "schema_version": 1,
        "state": state,
        "ready": health["ready"],
        "components": health["components"],
        "ui_url": health["ui_url"],
        "manager_home": str(home),
        "ecosystem_home": str(ecosystem_home),
    }
    if include_service:
        from . import suite_service

        result["service"] = suite_service.operation("status", home, ecosystem_home)
    return result


def _start_locked(home, ecosystem_home):
    from . import suite_service
    from .service import installed_executable

    current = status(home, ecosystem_home, include_service=False)
    if current["state"] == "running":
        return {**current, "already_running": True}
    directory = _directory(home)
    with lifetime_lock(directory / "launch.lock"):
        current = status(home, ecosystem_home, include_service=False)
        if current["state"] == "running":
            return {**current, "already_running": True}
        if lock_held(directory / "owner.lock"):
            return {**current, "state": "pending", "reason": "suite_start_pending"}
        if lock_held(home / "supervisor.lock"):
            raise ManagerError(
                "suite_owner_conflict",
                "An independent manager owns this home; reconcile its service first.",
                3,
            )
        service = suite_service.operation("status", home, ecosystem_home)
        if service.get("installed"):
            suite_service.operation("start", home, ecosystem_home)
        else:
            executable = installed_executable()
            save_config(home, ecosystem_home)
            path = directory / "suite.stderr.log"
            fd = os.open(
                path,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
            )
            try:
                info = os.fstat(fd)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) & 0o077
                ):
                    raise OSError("suite_log_unverified")
                with os.fdopen(fd, "ab", closefd=False) as log:
                    subprocess.Popen(
                        [
                            str(executable),
                            "--ecosystem-home",
                            str(ecosystem_home),
                            "stack",
                            "run",
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=log,
                        cwd=str(Path.home()),
                        env={
                            **{
                                key: value
                                for key, value in os.environ.items()
                                if not key.startswith("PYTHON")
                            },
                            "SOLBOT_HOME": str(home),
                            "SOLBOT_ECOSYSTEM_HOME": str(ecosystem_home),
                            "PYTHONNOUSERSITE": "1",
                            "INDEX_NO_AUTO": "1",
                        },
                        start_new_session=True,
                        close_fds=True,
                    )
            finally:
                os.close(fd)
        deadline = time.monotonic() + STARTUP_SECONDS
        while time.monotonic() < deadline:
            current = status(home, ecosystem_home, include_service=False)
            if current["state"] == "running":
                return {**current, "already_running": False}
            time.sleep(0.05)
        return {**current, "state": "pending", "reason": "suite_start_pending"}


def _start(home, ecosystem_home):
    try:
        return _start_locked(home, ecosystem_home)
    except BlockingIOError:
        return {
            **status(home, ecosystem_home, include_service=False),
            "state": "pending",
            "reason": "suite_start_pending",
        }
    except OSError as exc:
        raise ManagerError(
            "suite_unavailable", "Suite start could not be confirmed.", 4
        ) from exc


def _checkpoint(home, ecosystem_home):
    try:
        value = machine_health.private_read(home / ".suite/state.json", limit=16_384)
        instance = value.get("instance")
        if (
            value.get("schema_version") == 1
            and value.get("manager_home") == str(home)
            and value.get("ecosystem_home") == str(ecosystem_home)
            and isinstance(instance, str)
            and len(instance) == 32
            and all(character in "0123456789abcdef" for character in instance)
        ):
            return value
    except (OSError, ValueError, TypeError):
        pass
    return None


def _stop_receipt(home, ecosystem_home, instance):
    final = _checkpoint(home, ecosystem_home)
    if (instance is not None and final is not None and final["instance"] == instance
            and (final.get("state") == "release_unconfirmed" or final.get("release_confirmed") is False)):
        raise ManagerError("suite_unavailable", "Child release is explicitly unconfirmed; reconcile before restarting.", 4)
    if (
        instance is not None
        and final is not None
        and final["instance"] == instance
        and final.get("state") == "stopped"
        and final.get("release_confirmed") is True
        and type(final.get("ui_retained")) is bool
    ):
        return final["ui_retained"]
    return None


def _stop(home, ecosystem_home):
    from . import suite_service

    saved = _checkpoint(home, ecosystem_home)
    instance = saved["instance"] if saved is not None else None
    service = suite_service.operation("status", home, ecosystem_home)
    service_managed = service.get("installed")
    if service_managed:
        suite_service.operation("stop", home, ecosystem_home)
    directory = home / ".suite"
    if not lock_held(directory / "owner.lock"):
        return {
            "state": "stopped",
            "desired_bot_intent_retained": True,
            "ui_retained": _stop_receipt(home, ecosystem_home, instance),
        }
    try:
        if saved is None:
            raise ValueError("suite_owner_unverified")
        path = directory / "control.sock"
        _owner_path(path)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(1)
            client.connect(str(path))
            _peer(client)
            client.sendall(
                (
                    canonical({"operation": "stop", "instance": saved["instance"]})
                    + "\n"
                ).encode()
            )
            result = _read(client, 4096, time.monotonic() + 1)
        if result.get("instance") != saved["instance"]:
            raise ValueError("suite_owner_changed")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        # A service manager may have delivered SIGTERM and removed the socket
        # before this probe. Only observed owner release establishes success.
        if not service_managed:
            raise ManagerError(
                "suite_unavailable",
                "Suite stop acknowledgement is unconfirmed; ownership was retained.",
                4,
            ) from exc
    try:
        deadline = time.monotonic() + 5
        while lock_held(directory / "owner.lock") and time.monotonic() < deadline:
            time.sleep(0.05)
        if lock_held(directory / "owner.lock"):
            raise ValueError("suite_owner_release_pending")
        return {
            "state": "stopped",
            "desired_bot_intent_retained": True,
            "ui_retained": _stop_receipt(home, ecosystem_home, instance),
        }
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ManagerError(
            "suite_unavailable",
            "Suite stop acknowledgement is unconfirmed; ownership was retained.",
            4,
        ) from exc


def operation(action, home=None, ecosystem_home=None, **fixed_options):
    if fixed_options:
        raise ManagerError("invalid_input", "Unknown suite options.")
    home, ecosystem_home = machine_health.homes(home, ecosystem_home)
    if action == "status":
        return status(home, ecosystem_home)
    if action == "run":
        return Suite(home, ecosystem_home).run()
    if action == "start":
        return _start(home, ecosystem_home)
    if action == "stop":
        return _stop(home, ecosystem_home)
    if action == "restart":
        _stop(home, ecosystem_home)
        return _start(home, ecosystem_home)
    if action in ("install", "uninstall"):
        from . import suite_service

        result = suite_service.operation(action, home, ecosystem_home)
        if action == "install":
            result["suite"] = _start(home, ecosystem_home)
        return result
    raise ManagerError("invalid_input", "Unknown suite action.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path)
    parser.add_argument("--ecosystem-home", type=Path)
    values = parser.parse_args(argv)
    try:
        operation("run", values.home, values.ecosystem_home)
        return 0
    except ManagerError as exc:
        print(canonical({"error": exc.code}), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

"""One cooperatively managed paper prediction producer across console processes.

The kernel-held lease, rather than a saved PID, controls ownership. Launchers
pass the already-held descriptor to a detached child, so popup exit cannot
create a gap or terminate its producer. Status reads never create files.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from . import config, forwardtest

COOLDOWN = 30.0
REPO = Path(__file__).resolve().parent.parent


def directory() -> Path:
    return config.CONFIG_DIR / "forwardtest"


class ControlUnavailable(ValueError):
    """An existing control record cannot authorize producer work."""


def _finite_time(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _read(name: str) -> dict:
    path = directory() / name
    try:
        if name == "control.json" and path.is_symlink():
            raise ControlUnavailable("prediction_control_unavailable")
        result = json.loads(path.read_text(encoding="utf-8"))
        if name == "control.json" and (
            not isinstance(result, dict)
            or ("paused" in result and type(result["paused"]) is not bool)
            or any(key in result and not isinstance(result[key], dict)
                   for key in ("requests", "last_requested"))
            or ("retry_after" in result and not _finite_time(result["retry_after"]))
            or any(not _finite_time(value) for value in result.get("last_requested", {}).values())
        ):
            raise ControlUnavailable("prediction_control_unavailable")
        return result if isinstance(result, dict) else {}
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, RecursionError):
        if name == "control.json":
            raise ControlUnavailable("prediction_control_unavailable") from None
        return {}


def _write(name: str, value: dict) -> None:
    root = directory()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = root / name
    temporary = target.with_name(f".{name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_text(json.dumps(value, allow_nan=False, sort_keys=True), encoding="utf-8")
        temporary.chmod(0o600)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def _control():
    directory().mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory() / "control.lock").open("a+b") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def paused() -> bool:
    return _read("control.json").get("paused") is True


def _locked() -> bool:
    try:
        with (directory() / "producer.lock").open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return True
            return False
    except FileNotFoundError:
        return False


def _legacy_owner() -> dict | None:
    # Older consoles and native hosts do not know the lease. Be conservative on the production
    # config until they have been upgraded; isolated configs cannot conflict.
    if config.CONFIG_DIR.resolve() != (Path.home() / ".config" / "soltui").resolve():
        return None
    try:
        result = subprocess.run(["ps", "-axo", "pid=,command="], capture_output=True,
                                text=True, timeout=2, check=True)
        for line in result.stdout.splitlines():
            pid, command = line.strip().split(None, 1)
            modules = {"soltui.tui": "legacy_console", "soltui.native_host": "legacy_host"}
            if int(pid) == os.getpid() or not any(f"-m {module}" in command for module in modules):
                continue
            words = shlex.split(command)
            module = next((words[i + 1] for i in range(len(words) - 1)
                           if words[i] == "-m" and words[i + 1] in modules), None)
            if module is not None:
                if _registered_console(int(pid)):
                    continue
                return {"pid": int(pid), "kind": modules[module], "started_at": None}
    except (OSError, ValueError, subprocess.SubprocessError):
        # Failure to inspect legacy processes must not authorize a second writer.
        return {"pid": None, "kind": "unverified_console", "started_at": None}
    return None


def _process_identity(pid: int) -> str | None:
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "lstart="], capture_output=True,
                                text=True, timeout=2, check=True)
        return result.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def register_console():
    """Register this console/host's lease protocol until its returned handle closes.

    The console or host owns this handle. A leftover marker cannot exempt a dead or
    reused PID: readers require both its held kernel lock and start identity.
    """
    identity = _process_identity(os.getpid())
    if identity is None:
        return None
    markers = directory() / "consoles"
    markers.mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = (markers / f"{os.getpid()}.json").open("a+b")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({"pid": os.getpid(), "protocol": 1, "identity": identity}).encode())
        handle.flush()
        return handle
    except BaseException:
        handle.close()
        raise


def _registered_console(pid: int) -> bool:
    try:
        with (directory() / "consoles" / f"{pid}.json").open("rb") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return False
            except BlockingIOError:
                marker = json.load(handle)
        return (marker.get("pid") == pid and marker.get("protocol") == 1
                and marker.get("identity") is not None and marker["identity"] == _process_identity(pid))
    except (OSError, ValueError, AttributeError):
        return False


def health(asset: str) -> dict[str, Any]:
    now = time.time()
    try:
        control = _read("control.json")
    except ControlUnavailable:
        return {"state": "failed", "running": _locked(), "busy": False, "paused": True,
                "can_start": False, "message": "Prediction control is unavailable; repair it before resuming.",
                "asset": asset, "assets": [], "current_asset": None, "queued": False,
                "owner": None, "cooldown_seconds": 0, "last_error": "prediction_control_unavailable", "last": {}}
    owner = _read("producer.json")
    locked = _locked()
    legacy = _legacy_owner() if not locked else None
    is_paused = control.get("paused") is True
    state = owner.get("state", "stopped")
    if is_paused:
        state, message = "paused", "Predictions paused. Start predictions to resume."
    elif locked:
        state = "starting" if state == "starting" else "running"
        message = "Starting predictions." if state == "starting" else "Predictions are running."
        if now - owner.get("heartbeat_at", now) > 30:
            state, message = "failed", "Prediction producer is unresponsive; its writer lease is still held."
    elif legacy:
        state, message = "failed", "An existing console or native host has no producer lease. Reopen it before starting predictions."
    elif state not in ("stopped", "failed"):
        state, message = "failed", "Prediction producer exited. Recovery can restart it."
    elif state == "failed":
        message = owner.get("last_error") or "Prediction producer failed. Recovery can restart it."
    else:
        state, message = "stopped", "Predictions are stopped."
    pinned = owner.get("pinned_asset") if locked else None
    if not locked and not legacy:
        plan = saved_plan()
        pinned = plan.get("asset") if plan and plan.get("source") else None
    refused = bool(pinned and asset != pinned)
    if refused:
        state, message = "failed", f"The saved plan is pinned to {pinned}. Open Forward Testing to choose another plan."
    requests = control.get("requests", {})
    current = owner.get("current_asset") if locked else None
    queued = asset in requests
    if locked and queued and not is_paused and not refused:
        message = f"{asset} queued after {current}." if current else f"{asset} queued for the next check."
    last = owner.get("last", {})
    error = last.get(asset, {}).get("error") or owner.get("last_error")
    cooldown = max(0.0, control.get("last_requested", {}).get(asset, 0) + COOLDOWN - now)
    if not locked:
        cooldown = max(cooldown, control.get("retry_after", 0) - now)
    public_owner = ({key: owner.get(key) for key in ("pid", "kind", "started_at")} if locked else legacy)
    return {"state": state, "running": locked, "busy": bool(locked and owner.get("busy")),
            "paused": is_paused, "can_start": not locked and not legacy and not refused,
            "message": message, "asset": asset, "assets": owner.get("assets", []),
            "current_asset": current, "queued": queued, "owner": public_owner,
            "cooldown_seconds": round(cooldown, 1), "last_error": error, "last": last}


def saved_plan() -> dict | None:
    plan = forwardtest.load_session() or _read("recovery-plan.json")
    if not plan:
        return None
    plan["horizons"] = tuple(plan["horizons"])
    return plan


def remember(plan: dict) -> None:
    _write("recovery-plan.json", plan)


def pause(plan: dict | None = None) -> None:
    # The pause is durable before any potentially slow evidence access.
    with _control():
        control = _read("control.json")
        control.update(paused=True, requests={})
        _write("control.json", control)
    if plan:
        remember(plan)


class Lease:
    def __init__(self, handle, token: str, metadata: dict):
        self.handle, self.token, self.metadata = handle, token, metadata
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.monitor: threading.Thread | None = None

    def update(self, **values) -> None:
        with self.lock:
            self.metadata.update(values, heartbeat_at=time.time())
            _write("producer.json", self.metadata)

    def watch(self, stop: threading.Event) -> None:
        def monitor():
            while not self.closed.wait(.5):
                try:
                    if paused():
                        stop.set()
                    self.update()
                except ControlUnavailable:
                    stop.set()
                    try:
                        self.update(state="failed", last_error="prediction_control_unavailable")
                    except OSError:
                        pass
                    return
                except OSError:
                    # Losing durable control/status access must stop the writer.
                    stop.set()
                    return
        self.monitor = threading.Thread(target=monitor, name="prediction-owner", daemon=True)
        self.monitor.start()

    def finish(self, *, error: str | None = None) -> None:
        if self.handle.closed:
            return
        if error is None and self.metadata.get("last_error") == "prediction_control_unavailable":
            error = "prediction_control_unavailable"
        self.closed.set()
        if self.monitor is not None:
            self.monitor.join(2)
        try:
            self.update(state="failed" if error else "stopped", busy=False, current_asset=None,
                        last_error=error)
        finally:
            self.handle.close()


def _acquire(plan: dict, kind: str) -> Lease | None:
    directory().mkdir(parents=True, exist_ok=True, mode=0o700)
    handle = (directory() / "producer.lock").open("a+b")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    token = uuid.uuid4().hex
    metadata = {"token": token, "pid": os.getpid(), "kind": kind, "state": "starting",
                "started_at": time.time(), "heartbeat_at": time.time(), "busy": False,
                "current_asset": None, "assets": list(plan["assets"]), "last": {}, "last_error": None,
                "pinned_asset": plan.get("asset") if plan.get("source") else None}
    lease = Lease(handle, token, metadata)
    try:
        lease.update()
    except BaseException:
        handle.close()
        raise
    return lease


def acquire(plan: dict, kind: str, *, manual: bool = False) -> Lease | None:
    with _control():
        try:
            control = _read("control.json")
        except ControlUnavailable:
            return None
        if _locked() or _legacy_owner() is not None:
            return None
        if control.get("paused") and not manual:
            return None
        lease = _acquire(plan, kind)
        if lease is not None and manual:
            try:
                control = _read("control.json")
                control.update(paused=False, retry_after=0)
                _write("control.json", control)
            except BaseException:
                lease.handle.close()
                raise
        return lease


def pending_assets() -> list[str]:
    return list(_read("control.json").get("requests", {}))


def consume(asset: str) -> None:
    with _control():
        control = _read("control.json")
        control.get("requests", {}).pop(asset, None)
        _write("control.json", control)


def _request(asset: str, control: dict, now: float, owner: dict) -> None:
    previous = control.setdefault("last_requested", {}).get(asset, 0)
    requests = control.setdefault("requests", {})
    if asset not in requests and owner.get("current_asset") != asset and now >= previous + COOLDOWN:
        requests[asset] = now
        control["last_requested"][asset] = now


def ensure(asset: str, fallback_plan, *, manual: bool = False) -> dict:
    with _control():
        try:
            control = _read("control.json")
        except ControlUnavailable:
            return health(asset)
        owner = _read("producer.json")
        now = time.time()
        if control.get("paused") and not manual:
            return health(asset)
        if _locked():
            if owner.get("pinned_asset") and owner["pinned_asset"] != asset:
                return health(asset)
            if not control.get("paused"):
                _request(asset, control, now, owner)
                _write("control.json", control)
            return health(asset)
        if _legacy_owner() is not None:
            return health(asset)
        if not manual and now < control.get("retry_after", 0):
            return health(asset)
        plan = saved_plan() or fallback_plan()
        if plan.get("source") and asset != plan.get("asset"):
            return health(asset)
        plan = {**plan, "assets": list(dict.fromkeys([*plan["assets"], asset])),
                "code": forwardtest.revision()}
        lease = _acquire(plan, "detached")
        if lease is None:
            return health(asset)
        try:
            control.update(paused=False, retry_after=now + COOLDOWN)
            _request(asset, control, now, {})
            _write("control.json", control)
            forwardtest.save_session(plan)
            remember(plan)
            with (directory() / "producer.log").open("ab") as log:
                process = subprocess.Popen(
                    [sys.executable, "-m", "soltui.prediction_recovery", "--lock-fd", str(lease.handle.fileno()),
                     "--token", lease.token], cwd=REPO,
                    env={**os.environ, "SOLTUI_CONFIG_DIR": str(config.CONFIG_DIR.resolve())},
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    start_new_session=True, pass_fds=(lease.handle.fileno(),))
        except Exception as exc:
            lease.finish(error=f"{type(exc).__name__}: {exc}"[:300])
        else:
            # The child now holds the same open-file-description lock. Closing
            # our copy must not explicitly unlock the inherited descriptor.
            lease.handle.close()
            threading.Thread(target=process.wait, name="prediction-reaper", daemon=True).start()
        return health(asset)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock-fd", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args(argv)
    handle = os.fdopen(args.lock_fd, "a+b")
    supplied = os.fstat(handle.fileno())
    expected = (directory() / "producer.lock").stat()
    if (supplied.st_dev, supplied.st_ino) != (expected.st_dev, expected.st_ino):
        handle.close()
        return 1
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    owner = _read("producer.json")
    if owner.get("token") != args.token:
        handle.close()
        return 1
    # Verify the inherited lease without releasing it; a second independent FD
    # must find the lock busy before this process is allowed to write evidence.
    if not _locked():
        handle.close()
        return 1
    plan = saved_plan()
    if not plan:
        handle.close()
        return 1
    from . import commands
    runtime = commands.Runtime()
    runtime.forward_plan = plan
    runtime.forward_started_at = owner["started_at"]
    runtime.forward_owner = Lease(handle, args.token, owner)
    runtime.forward_owner.update(pid=os.getpid(), state="running")
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: runtime.forward_stop.set())
    commands._forward_owned_runner(runtime)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

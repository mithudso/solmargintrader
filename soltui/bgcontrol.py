"""Start, stop and inspect the background sweep process.

Separated from `bgqueue` (which is pure logic) and from `bgworker` (which is the
work) because process lifecycle is the part with the OS-specific behaviour, and
keeping it in one small module is what lets the other two stay testable.

## "Low priority" means two different things on macOS

`nice` lowers scheduling priority, and the worker sets it on itself. That alone
is not enough on Darwin: a niced process still runs in the default QoS class, so
it competes for memory bandwidth and can keep the fans up and the efficiency
cores idle while the P-cores grind. The other half is the *task policy* --
`taskpolicy -b` puts the process in the background QoS class, which is what
actually routes it to the efficiency cores and throttles its I/O.

So the launcher prefers `taskpolicy -b`, and falls back to plain spawning when it
is unavailable (a non-macOS host, or a stripped image). The fallback is not
silent: `describe_priority()` reports which path was taken, so the pane can say
"background QoS" or "niced only" rather than claiming a policy it did not get.

## No launchd agent here, deliberately

`soltui-service` already owns the LaunchAgent surface, with documented
constraints (a flag file as the real on/off switch, and a refusal to run from a
worktree path). A second agent competing for that surface would be a second
source of truth for "is soltui running". This module spawns a plain child
process instead: it lives as long as it is useful. Stop queues a request on that
worker instance's private local control socket.

## Liveness is a lock, not a pid

An earlier version answered "is a sweep running?" by reading a pidfile and
calling `kill(pid, 0)`. That is wrong in a way that is quiet until it is very
loud: a worker killed with SIGKILL never removes its own pidfile, the OS later
recycles that pid to an unrelated process, and `stop()` then sends SIGTERM to
whatever inherited the number.

So liveness is an advisory `flock` instead. The lock is taken on a descriptor
the PARENT opens before spawning and the child inherits, which means it is held
from before the process exists until after it dies -- including a SIGKILL, since
the kernel closes the descriptor and drops the lock for us. There is no window
where a sweep is running but unlocked, and no stale lock to clean up. The pidfile
survives only as diagnostic information. A held lock does not prove that a
separate pidfile still names its owner. Stop never signals a recorded PID: the
launcher binds a unique control socket under the lock before spawning, and the
worker inherits its receiver. Requests carry that instance's nonce and are
consumed only at a job boundary. An old request cannot target a replacement.
"""

from __future__ import annotations

import fcntl
import json
import os
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

from . import bgqueue
from .bgqueue import BG_DIR, PID_PATH, ensure_dir

# Where the liveness lock lives, and the variable that tells a spawned worker the
# lock is already held on its behalf. A worker started by hand takes the lock
# itself; one started here inherits it, and must NOT try to re-take it -- flock
# conflicts between two descriptors even inside a single process.
LOCK_PATH = BG_DIR / "worker.lock"
LOCK_FD_ENV = "SOLTUI_BG_LOCK_FD"
CONTROL_FD_ENV = "SOLTUI_BG_CONTROL_FD"

# Where `taskpolicy` actually lives on macOS. It is /usr/sbin, NOT /usr/bin, and
# /usr/sbin is not always on a GUI-launched app's PATH -- so the known location is
# checked first and PATH second. Resolving the real path (rather than assuming
# one) is what stops a host that HAS the tool from spawning `/usr/bin/taskpolicy`
# and dying with ENOENT.
TASKPOLICY_PATHS = ("/usr/sbin/taskpolicy", "/usr/bin/taskpolicy")


def taskpolicy_path() -> str | None:
    """Absolute path to `taskpolicy`, or None when this host has no usable one."""
    if sys.platform != "darwin":
        return None
    for candidate in TASKPOLICY_PATHS:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    found = shutil.which("taskpolicy")
    return found if found and os.access(found, os.X_OK) else None


def taskpolicy_available() -> bool:
    """True when the macOS background-QoS launcher is usable."""
    return taskpolicy_path() is not None


def describe_priority() -> str:
    """How a worker started now would actually be prioritised.

    Phrased as what will happen, not what is intended: a pane that claims
    "background QoS" on a host without `taskpolicy` would be stating a fact that
    is not true.
    """
    # "requests" rather than "runs at": the worker tolerates a refused
    # setpriority (a sandbox may deny it), so promising a nice level here would
    # be asserting something this module never checked. The taskpolicy half IS
    # probed, so that half is stated flatly. The worker logs the level it was
    # actually granted at startup.
    if taskpolicy_available():
        return (
            "background QoS (taskpolicy -b) — efficiency cores, throttled I/O; "
            "requests nice 19"
        )
    return "requests nice 19 (no taskpolicy on this host, so no QoS demotion)"


def read_pid(path: Path | None = None) -> int | None:
    """The recorded worker pid, or None when there is no usable pidfile."""
    path = path or PID_PATH
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):
        return None
    try:
        pid = int(raw)
    except ValueError:
        return None
    return pid if pid > 0 else None


def acquire_lock(path: Path | None = None) -> int | None:
    """Take the worker lock, returning its fd, or None when someone else holds it.

    The fd is deliberately NOT closed by the caller on success: the lock lives as
    long as the descriptor does, so closing it would release the lock while the
    worker was still running.
    """
    path = path or LOCK_PATH
    ensure_dir(path.parent)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        os.close(fd)
        return None
    return fd


def inherited_lock(marker: str | None) -> int | None:
    """Adopt a descriptor only if it can hold the exact worker lock.

    The environment marker is a hint, not proof. A descriptor for another file
    must never be closed or unlocked here. Reasserting LOCK_EX on the inherited
    open-file description preserves its lock; a separately opened descriptor
    fails when a different worker owns the lock.
    """
    if marker is None:
        return None
    try:
        fd = int(marker)
        if fd < 0:
            return None
        supplied = os.fstat(fd)
        expected = LOCK_PATH.stat()
        if (supplied.st_dev, supplied.st_ino) != (expected.st_dev, expected.st_ino):
            return None
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (OSError, ValueError, OverflowError):
        return None
    return fd


class WorkerControl:
    """One worker instance's nonblocking cooperative stop receiver."""

    def __init__(self, receiver: socket.socket, owner: dict[str, Any]) -> None:
        self.receiver = receiver
        self.path = Path(owner["endpoint"])
        self.nonce = owner["nonce"]
        self.identity = (owner["endpoint_device"], owner["endpoint_inode"])

    def fileno(self) -> int:
        return self.receiver.fileno()

    def stop_requested(self) -> bool:
        # Bound work per job boundary even if another local caller floods the
        # socket. Invalid or old-instance messages never become stop requests.
        for _ in range(64):
            try:
                raw = self.receiver.recv(1024)
            except BlockingIOError:
                return False
            try:
                request = json.loads(raw)
            except (ValueError, UnicodeError):
                continue
            if request == {"command": "stop", "nonce": self.nonce}:
                return True
        return False

    def close(self, *, remove_endpoint: bool = True) -> None:
        self.receiver.close()
        if remove_endpoint:
            try:
                stat = self.path.stat()
                if (stat.st_dev, stat.st_ino) == self.identity:
                    self.path.unlink()
            except FileNotFoundError:
                pass


def read_control_owner(fd: int) -> dict[str, Any] | None:
    """Read bounded metadata from the same inode whose lock was inspected."""
    try:
        owner = json.loads(os.pread(fd, 4096, 0))
        stat = os.fstat(fd)
        if not isinstance(owner, dict) or owner.get("version") != 1:
            return None
        nonce = owner.get("nonce")
        if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in "0123456789abcdef" for c in nonce):
            return None
        if (owner.get("device"), owner.get("inode")) != (stat.st_dev, stat.st_ino):
            return None
        if not isinstance(owner.get("endpoint"), str):
            return None
        endpoint = Path(owner["endpoint"])
        if not endpoint.is_absolute() or endpoint.name != f".s-{nonce[:16]}":
            return None
        endpoint_stat = endpoint.stat()
        if (owner.get("endpoint_device"), owner.get("endpoint_inode")) != (endpoint_stat.st_dev, endpoint_stat.st_ino):
            return None
    except (OSError, ValueError, UnicodeError):
        return None
    return owner


def create_control(lock_fd: int) -> WorkerControl:
    """Publish a receiver before spawn, so early Stop requests queue safely."""
    if inherited_lock(str(lock_fd)) is None:
        raise RuntimeError("worker control requires the current worker lock")
    os.fchmod(lock_fd, 0o600)
    nonce = secrets.token_hex(16)
    path = LOCK_PATH.parent.resolve() / f".s-{nonce[:16]}"
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    bound = False
    try:
        receiver.bind(str(path))
        bound = True
        path.chmod(0o600)
        receiver.setblocking(False)
        stat = os.fstat(lock_fd)
        endpoint_stat = path.stat()
        owner = {
            "version": 1, "nonce": nonce, "endpoint": str(path),
            "device": stat.st_dev, "inode": stat.st_ino,
            "endpoint_device": endpoint_stat.st_dev, "endpoint_inode": endpoint_stat.st_ino,
        }
        payload = json.dumps(owner, separators=(",", ":")).encode()
        os.ftruncate(lock_fd, 0)
        os.lseek(lock_fd, 0, os.SEEK_SET)
        while payload:
            written = os.write(lock_fd, payload)
            if written == 0:
                raise OSError("worker control metadata write made no progress")
            payload = payload[written:]
        return WorkerControl(receiver, owner)
    except BaseException:
        receiver.close()
        if bound:
            path.unlink(missing_ok=True)
        raise


def inherited_control(
    lock_fd: int, marker: str | None, *, consume: bool = False,
) -> WorkerControl | None:
    """Validate a passed receiver without closing a foreign descriptor."""
    owner = read_control_owner(lock_fd)
    if marker is None or owner is None or Path(owner["endpoint"]).parent != LOCK_PATH.parent.resolve():
        return None
    duplicate: int | None = None
    receiver: socket.socket | None = None
    try:
        duplicate = os.dup(int(marker))
        receiver = socket.socket(fileno=duplicate)
        duplicate = None
        if receiver.family != socket.AF_UNIX or receiver.type != socket.SOCK_DGRAM or receiver.getsockname() != owner["endpoint"]:
            receiver.close()
            return None
        receiver.setblocking(False)
        if consume:
            # Only the child opts in to consuming its inherited copy. Probe
            # callers retain their descriptor, including every invalid marker.
            os.close(int(marker))
        return WorkerControl(receiver, owner)
    except (OSError, ValueError, OverflowError):
        if receiver is not None:
            receiver.close()
        if duplicate is not None:
            os.close(duplicate)
        return None


def is_running(path: Path | None = None) -> bool:
    """True when some process holds the worker lock.

    Probing by trying to take the lock ourselves, rather than by asking whether a
    recorded pid still exists: a pid can be recycled to an unrelated process, but
    a lock cannot outlive its holder.
    """
    fd = acquire_lock(path)
    if fd is None:
        return True
    # We got it, so nobody was running. Release immediately -- holding it here
    # would make the next `start()` refuse.
    os.close(fd)
    return False


def worker_command(
    asset: str,
    *,
    horizons: Sequence[str] | None = None,
    max_tier: int = 2,
    limit: int | None = None,
    strategies: Sequence[str] | None = None,
    python: str | None = None,
    results_path: Path | None = None,
) -> list[str]:
    """The argv that runs the worker, wrapped in the background-QoS launcher.

    `sys.executable` by default so the child runs the same interpreter as the
    TUI -- picking `python3` off PATH would be a different environment, and the
    failure shows up as a missing numpy rather than as a wrong interpreter.
    """
    cmd = [python or sys.executable, "-m", "soltui.bgworker", "--asset", asset]
    if results_path is not None:
        cmd += ["--results-path", str(results_path)]
    if horizons:
        cmd += ["--horizons", *horizons]
    cmd += ["--max-tier", str(max_tier)]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    if strategies:
        cmd += ["--strategies", *strategies]
    launcher = taskpolicy_path()
    return [launcher, "-b", *cmd] if launcher else cmd


def start(
    asset: str,
    *,
    horizons: Sequence[str] | None = None,
    max_tier: int = 2,
    limit: int | None = None,
    strategies: Sequence[str] | None = None,
    cwd: Path | None = None,
    log_path: Path | None = None,
    fresh: bool = False,
) -> subprocess.Popen[bytes]:
    """Spawn the worker. Refuses to start a second one.

    `start_new_session=True` detaches the child from the TUI's process group, so
    a Ctrl-C in the console -- or the console exiting -- does not take the sweep
    with it. That is the point of a background sweep: it should outlive the
    window you started it from.
    """
    ensure_dir(BG_DIR)
    repo = cwd or Path(__file__).resolve().parent.parent
    log = log_path or (BG_DIR / "worker.log")
    # Open the log BEFORE taking the lock. Everything after the lock is taken has
    # to be inside the try that releases it, and a failing `open` there (a
    # read-only dir, a full disk) would leave the lock held by the long-lived TUI
    # process forever -- after which every Start refuses as "already running" and
    # no Stop can find a worker to signal. The feature would wedge until restart.
    handle = log.open("ab")

    # Taking the lock IS the "already running?" check. Testing first and then
    # spawning would leave a window in which two Starts both saw "no worker" and
    # both spawned, producing two processes appending to one results file.
    try:
        lock_fd = acquire_lock()
    except BaseException:
        # `acquire_lock` can raise rather than return None (an unwritable lock
        # path). Without this the log handle opened just above leaks once per
        # Start press, and the condition that caused it tends to persist.
        handle.close()
        raise
    if lock_fd is None:
        handle.close()
        raise RuntimeError("a background sweep is already running")

    control: WorkerControl | None = None
    try:
        results_path = bgqueue.active_results_path()
        if fresh:
            # Reserve an unused file and publish its name atomically while holding
            # the worker lock. Existing files and proofs remain untouched.
            results_path = bgqueue.RESULTS_PATH.parent / f"results-{secrets.token_hex(16)}.jsonl"
            fd = os.open(results_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
            pointer = bgqueue.RESULTS_PATH.parent / "active-results"
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=pointer.parent,
                                                 delete=False) as out:
                    temporary = out.name
                    out.write(results_path.name + "\n")
                    out.flush()
                    os.fsync(out.fileno())
                os.replace(temporary, pointer)
            finally:
                if temporary is not None:
                    Path(temporary).unlink(missing_ok=True)
        control = create_control(lock_fd)
        proc = subprocess.Popen(  # noqa: S603 - argv list, no shell
            worker_command(asset, horizons=horizons, max_tier=max_tier, limit=limit,
                           strategies=strategies, results_path=results_path),
            cwd=str(repo),
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            # Hand the locked descriptor to the child. It inherits the lock, so
            # the sweep is protected from before it starts until the kernel
            # closes the fd on its death -- no gap, and no cleanup on a crash.
            pass_fds=(lock_fd, control.fileno()),
            env={**os.environ, LOCK_FD_ENV: str(lock_fd), CONTROL_FD_ENV: str(control.fileno())},
        )
        # Diagnostic only: Stop already has its private receiver before this
        # publication and never uses this number as a signal destination.
        PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    except BaseException:
        proc = locals().get("proc")
        try:
            if proc is not None:
                proc.kill()
        finally:
            try:
                if control is not None:
                    control.close()
            finally:
                try:
                    os.close(lock_fd)
                finally:
                    handle.close()
        raise
    # The child holds the lock and its own copy of the log fd now; both of the
    # parent's copies are dead weight, and leaking them per sweep would exhaust
    # the TUI's descriptors over a long session.
    os.close(lock_fd)
    control.close(remove_endpoint=False)
    handle.close()
    return proc


def fetch_command(asset: str, interval: str, python: str | None = None) -> list[str]:
    """The argv that fetches one missing price series."""
    return [
        python or sys.executable, "-m", "backtester.core.fetch",
        "--asset", asset, "--interval", interval,
    ]


def start_fetch(
    missing: Sequence[tuple[str, str]],
    *,
    cwd: Path | None = None,
    log_path: Path | None = None,
) -> subprocess.Popen[bytes]:
    """Fetch the given (asset, interval) series in the background.

    This is the ONE network path this package has, and it stays exactly what
    `CLAUDE.md` requires it to be: a separate, explicit step that writes a local
    cache. The engine still never reaches the network -- pressing this button
    runs `backtester.core.fetch`, the same command the pane prints, and nothing
    starts a sweep as a side effect of it finishing.

    Sequential, one interval at a time, in a plain shell loop: the fetches hit a
    public API, and firing them concurrently is how you earn a rate limit.
    """
    if not missing:
        raise ValueError("nothing to fetch")
    ensure_dir(BG_DIR)
    repo = cwd or Path(__file__).resolve().parent.parent
    log = log_path or (BG_DIR / "fetch.log")

    script = " && ".join(
        " ".join(shlex.quote(part) for part in fetch_command(asset, interval))
        for asset, interval in missing
    )
    handle = log.open("ab")
    try:
        return subprocess.Popen(  # noqa: S602 - argv built with shlex.quote
            ["/bin/sh", "-c", script],
            cwd=str(repo),
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    finally:
        # The child holds its own copy; the parent's would otherwise leak once
        # per press, exactly as it would in `start()`.
        handle.close()


def stop(path: Path | None = None, lock_path: Path | None = None) -> bool:
    """Queue this worker instance's stop request. True means queued, not exited.

    `path` remains accepted for callers using the old pidfile API, but PID data
    has no authority. A held lock and its private receiver identify the target.
    Exit or replacement races can refuse delivery; they cannot signal another
    process or deliver an old-instance request to a new worker.
    """
    lock_path = lock_path or LOCK_PATH
    fd: int | None = None
    try:
        fd = os.open(lock_path, os.O_RDONLY)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            pass
        else:
            return False
        owner = read_control_owner(fd)
        if owner is None or Path(owner["endpoint"]).parent != lock_path.parent.resolve():
            return False
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sender:
            sender.setblocking(False)
            sender.sendto(json.dumps({"command": "stop", "nonce": owner["nonce"]}).encode(), owner["endpoint"])
    except OSError:
        return False
    finally:
        if fd is not None:
            os.close(fd)
    return True

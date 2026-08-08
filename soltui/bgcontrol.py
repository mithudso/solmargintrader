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
process instead: it lives as long as it is useful, and stopping it is a signal.

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
survives only as the address to send the signal to, never as evidence of life.
"""

from __future__ import annotations

import fcntl
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .bgqueue import BG_DIR, PID_PATH, ensure_dir

# Where the liveness lock lives, and the variable that tells a spawned worker the
# lock is already held on its behalf. A worker started by hand takes the lock
# itself; one started here inherits it, and must NOT try to re-take it -- flock
# conflicts between two descriptors even inside a single process.
LOCK_PATH = BG_DIR / "worker.lock"
LOCK_FD_ENV = "SOLTUI_BG_LOCK_FD"

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
    python: str | None = None,
) -> list[str]:
    """The argv that runs the worker, wrapped in the background-QoS launcher.

    `sys.executable` by default so the child runs the same interpreter as the
    TUI -- picking `python3` off PATH would be a different environment, and the
    failure shows up as a missing numpy rather than as a wrong interpreter.
    """
    cmd = [python or sys.executable, "-m", "soltui.bgworker", "--asset", asset]
    if horizons:
        cmd += ["--horizons", *horizons]
    cmd += ["--max-tier", str(max_tier)]
    if limit is not None:
        cmd += ["--limit", str(limit)]
    launcher = taskpolicy_path()
    return [launcher, "-b", *cmd] if launcher else cmd


def start(
    asset: str,
    *,
    horizons: Sequence[str] | None = None,
    max_tier: int = 2,
    limit: int | None = None,
    cwd: Path | None = None,
    log_path: Path | None = None,
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

    try:
        proc = subprocess.Popen(  # noqa: S603 - argv list, no shell
            worker_command(asset, horizons=horizons, max_tier=max_tier, limit=limit),
            cwd=str(repo),
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            # Hand the locked descriptor to the child. It inherits the lock, so
            # the sweep is protected from before it starts until the kernel
            # closes the fd on its death -- no gap, and no cleanup on a crash.
            pass_fds=(lock_fd,),
            env={**os.environ, LOCK_FD_ENV: str(lock_fd)},
        )
        # Record the pid HERE rather than leaving it to the child, which takes a
        # few hundred ms to import numpy and reach its own write. Inside the try
        # so a failure to write it kills the child instead of orphaning a worker
        # that nothing can signal. `taskpolicy` execs in place, so the pid holds.
        PID_PATH.write_text(str(proc.pid), encoding="utf-8")
    except BaseException:
        proc = locals().get("proc")
        if proc is not None:
            proc.kill()
        os.close(lock_fd)
        handle.close()
        raise
    # The child holds the lock and its own copy of the log fd now; both of the
    # parent's copies are dead weight, and leaking them per sweep would exhaust
    # the TUI's descriptors over a long session.
    os.close(lock_fd)
    handle.close()
    return proc


def stop(path: Path | None = None, lock_path: Path | None = None) -> bool:
    """Ask the worker to finish its current job and exit. True when signalled.

    SIGTERM, never SIGKILL: the worker stops at a job boundary and writes its
    final state, and killing it outright would leave the state file reading
    "running" for a process that no longer exists.

    The lock is checked BEFORE the pid is used. Signalling on the strength of a
    pidfile alone is how a stale pid gets a SIGTERM sent to whatever unrelated
    process the OS has since given that number to.
    """
    if not is_running(lock_path):
        return False
    pid = read_pid(path)
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        return False
    return True

"""Explicit singleton backfill control; PIDs are diagnostic, never signal targets."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import uuid4


def parse_mode(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", nargs="?", choices=("start",), default="start")
    modes = parser.add_mutually_exclusive_group()
    for name in ("status", "tail", "stop"):
        modes.add_argument("--" + name, dest="action", action="store_const", const=name)
    args = parser.parse_args(argv)
    return args.action or args.mode


def _record(path):
    if path.is_symlink() or path.stat().st_size > 4096:
        raise ValueError("invalid_backfill_owner")
    value = json.loads(path.read_text())
    if (not isinstance(value, dict) or value.get("version") != 1
            or not re.fullmatch(r"[0-9a-f]{32}", value.get("run_id", ""))):
        raise ValueError("invalid_backfill_owner")
    return value


def _publish(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".backfill-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def held(path):
    try:
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
    except FileNotFoundError:
        return False
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False
    finally:
        os.close(fd)


def stop(logs):
    if not held(logs / "tick_backfill.lock"):
        return "not running"
    owner = _record(logs / "tick_backfill.owner.json")
    # A concurrent new run ignores the old token's marker. Never signal a PID.
    marker = logs / ("tick_backfill.stop-" + owner["run_id"])
    fd = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(fd)
    return "stop requested; it will checkpoint after the current page"


def start(repo, home, *, launch=subprocess.Popen):
    logs = home / "data/logs"
    if (logs / "tick_backfill.pid").exists():
        return "legacy PID ownership requires review; no worker started", 1
    logs.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(logs / "tick_backfill.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return "already running", 1
        identity = {"version": 1, "run_id": uuid4().hex}
        stop_path = logs / ("tick_backfill.stop-" + identity["run_id"])
        _publish(logs / "tick_backfill.owner.json", identity)
        prefix = ["taskpolicy", "-b"] if shutil.which("taskpolicy") else []
        command = [*prefix, "nice", "-n", "19", sys.executable, "-u",
                   str(repo / "research/tick_backfill.py"),
                   "--assets", os.environ.get("BACKFILL_ASSETS", "DOGE,ZEC,SOL,BTC,ETH"),
                   "--start", os.environ.get("BACKFILL_START", "2026-07-06"),
                   "--end", os.environ.get("BACKFILL_END", "2026-08-06"),
                   "--pause", os.environ.get("BACKFILL_PAUSE", "0.15"),
                   "--data-dir", str(home / "data"),
                   "--out-dir", str(home / "data/authoritative"),
                   "--checkpoint-dir", str(home / "data/checkpoints"),
                   "--report", os.environ.get("BACKFILL_REPORT", str(home / "research/TICK-BACKFILL-AUDIT.md")),
                   "--stop-file", str(stop_path), "--owner-lock-fd", str(fd)]
        log_fd = os.open(logs / "tick_backfill.log", os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(log_fd, "ab") as log:
                process = launch(command, cwd=repo, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True, pass_fds=(fd,))
        except Exception:
            (logs / "tick_backfill.owner.json").unlink(missing_ok=True)
            raise
        return f"started (pid {process.pid}; diagnostic only)", 0
    finally:
        # The same open description remains locked in the inherited worker.
        os.close(fd)


def main(argv=None):
    mode = parse_mode(argv)
    repo = Path(__file__).resolve().parents[1]
    home = Path(os.environ.get("BACKFILL_HOME", repo)).absolute()
    logs = home / "data/logs"
    if mode == "start":
        message, code = start(repo, home)
        print(message)
        return code
    if mode == "stop":
        try:
            print(stop(logs))
        except FileExistsError:
            print("stop already requested")
        return 0
    if mode == "tail":
        os.execvp("tail", ["tail", "-f", str(logs / "tick_backfill.log")])
    print("running" if held(logs / "tick_backfill.lock") else "not running")
    for path in sorted((home / "data/checkpoints").glob("*.json")):
        try:
            data = json.loads(path.read_text())
            print(f"{path.name}: {data['trades']} trades, {data['pages']} pages, done={data['done']}")
        except (OSError, ValueError, KeyError, TypeError):
            print(f"{path.name}: unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Detached, checkpointed recurring bot optimization; never submits orders.

The worker survives console exit. A dedicated launchd watchdog resumes an
enabled schedule after login or a crash. Stop disables watchdog recovery. The
optimizer itself owns its existing per-bot experiment lock.
"""
from __future__ import annotations

import fcntl
import json
import os
from pathlib import Path
import plistlib
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import closing, contextmanager
from typing import Any, Callable

from . import bots, config

DEFAULT_INTERVAL = 24 * 60 * 60
LABEL = "com.soltui.bot-optimizer-watchdog"


def _root(root: Path | None = None) -> Path:
    return Path(root) if root is not None else config.CONFIG_DIR / "bot-scheduler"


def _db(root: Path | None = None) -> sqlite3.Connection:
    directory = _root(root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    db = sqlite3.connect(directory / "schedule.sqlite3", timeout=30)
    db.execute("CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS item (bot TEXT, coin TEXT, state TEXT, started REAL, finished REAL, error TEXT, summary TEXT, PRIMARY KEY(bot,coin))")
    db.commit()
    os.chmod(directory / "schedule.sqlite3", 0o600)
    return db


def _get(db: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = db.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def _set(db: sqlite3.Connection, **values: Any) -> None:
    db.executemany("INSERT OR REPLACE INTO state VALUES (?,?)", ((k, json.dumps(v)) for k, v in values.items()))


def _lock(root: Path | None = None) -> int | None:
    directory = _root(root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(directory / "worker.lock", os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


@contextmanager
def _control(root: Path | None):
    directory = _root(root)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "control.lock").open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def status(*, root: Path | None = None) -> dict[str, Any]:
    with closing(_db(root)) as db:
        state = {k: json.loads(v) for k, v in db.execute("SELECT key,value FROM state")}
        state["items"] = [dict(zip(("bot", "coin", "state", "started", "finished", "error", "summary"), row))
                          for row in db.execute("SELECT bot,coin,state,started,finished,error,summary FROM item ORDER BY bot,coin")]
    fd = _lock(root)
    state["running"] = fd is None
    if fd is not None:
        os.close(fd)
    if not state["running"] and state.get("phase") in ("starting", "running", "waiting", "stopping"):
        state["phase"] = "interrupted"
    state.setdefault("phase", "stopped")
    state["log"] = str(_root(root) / "worker.log")
    state["watchdog_plist"] = str(_plist_path())
    state["watchdog_installed"] = _plist_path().exists()
    return state


def _plist_path() -> Path:
    return Path(os.environ.get("SOLTUI_LAUNCHAGENTS_DIR") or Path.home() / "Library" / "LaunchAgents") / f"{LABEL}.plist"


def _install_watchdog(root: Path | None) -> None:
    if sys.platform != "darwin":
        raise RuntimeError("automatic login recovery requires macOS launchd")
    path = _plist_path()
    spec = {"Label": LABEL,
            "ProgramArguments": [sys.executable, "-m", "soltui.bot_scheduler", "--watchdog", str(_root(root).resolve())],
            "WorkingDirectory": str(Path(__file__).resolve().parent.parent),
            "StartInterval": 300, "RunAtLoad": True,
            "StandardOutPath": str(_root(root).resolve() / "watchdog.log"),
            "StandardErrorPath": str(_root(root).resolve() / "watchdog.log")}
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with path.open("rb") as file:
            if plistlib.load(file) != spec:
                raise RuntimeError(f"existing watchdog configuration differs: {path}")
    else:
        # Publish a complete plist without replacing a concurrently installed agent.
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                temporary = Path(file.name)
                plistlib.dump(spec, file)
                file.flush()
                os.fsync(file.fileno())
            os.link(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    domain = f"gui/{os.getuid()}"
    current = subprocess.run(["launchctl", "print", f"{domain}/{LABEL}"], capture_output=True, text=True, timeout=30)
    if current.returncode:
        result = subprocess.run(["launchctl", "bootstrap", domain, str(path)], capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f"launchd bootstrap failed: {result.stderr.strip()}")


def watchdog(*, root: Path | None = None) -> None:
    with _control(root):
        with closing(_db(root)) as db, db:
            enabled = _get(db, "enabled", False)
            interval = _get(db, "interval_seconds", DEFAULT_INTERVAL)
            _set(db, watchdog_last_check=time.time())
        if enabled:
            fd = _lock(root)
            if fd is None:
                return
            os.close(fd)
            _start(interval, root)


def start(*, interval_seconds: int = DEFAULT_INTERVAL, root: Path | None = None) -> dict[str, Any]:
    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds < 60:
        raise ValueError("interval_seconds must be an integer of at least 60")
    with _control(root):
        if _lock_probe(root):
            raise RuntimeError("bot optimizer scheduler is already running")
        _install_watchdog(root)
        with closing(_db(root)) as db, db:
            _set(db, enabled=True)
        try:
            return _start(interval_seconds, root)
        except Exception:
            with closing(_db(root)) as db, db:
                _set(db, enabled=False)
            raise


def _lock_probe(root: Path | None) -> bool:
    fd = _lock(root)
    if fd is None:
        return True
    os.close(fd)
    return False


def _start(interval_seconds: int, root: Path | None) -> dict[str, Any]:
    fd = _lock(root)
    if fd is None:
        raise RuntimeError("bot optimizer scheduler is already running")
    directory = _root(root).resolve()
    try:
        with closing(_db(root)) as db, db:
            _set(db, phase="starting", stop_requested=False, interval_seconds=interval_seconds, error="")
        with (directory / "worker.log").open("a", encoding="utf-8") as log:
            proc = subprocess.Popen([sys.executable, "-m", "soltui.bot_scheduler", "--worker", str(fd), str(directory)],
                                    stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    pass_fds=(fd,), start_new_session=True)
        threading.Thread(target=proc.wait, daemon=True).start()
    except Exception as exc:
        with closing(_db(root)) as db, db:
            _set(db, phase="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        os.close(fd)
    return {"pid": proc.pid, "log": str(directory / "worker.log"), "phase": "starting"}


def stop(*, root: Path | None = None) -> dict[str, Any]:
    # The worker checks this only between optimization calls; no unrelated PID is signalled.
    with _control(root):
        fd = _lock(root)
        if fd is not None:
            os.close(fd)
        with closing(_db(root)) as db, db:
            _set(db, enabled=False, stop_requested=True, phase="stopping" if fd is None else "stopped")
    return status(root=root)


def _stop_requested(root: Path | None) -> bool:
    with closing(_db(root)) as db:
        return bool(_get(db, "stop_requested", False))


def run_cycle(*, root: Path | None = None, settings: Any = None,
              optimizer: Callable[..., dict[str, Any]] | None = None,
              coins: list[str] | None = None, now: Callable[[], float] = time.time) -> dict[str, Any]:
    """Run one cycle; only the owning worker calls this outside isolated tests."""
    settings = settings if settings is not None else config.load_settings()
    optimizer = optimizer or bots.optimize
    coins = list(dict.fromkeys(coins if coins is not None else bots.available_coins(settings)))
    work = [(bot, coin) for bot in ("grid", "dca") for coin in coins] + [("triangle", "")]
    with closing(_db(root)) as db, db:
        # A fresh cycle freezes its universe. A crash resumes the unfinished cycle.
        if not _get(db, "cycle_active", False):
            db.execute("DELETE FROM item")
            db.executemany("INSERT INTO item(bot,coin,state) VALUES (?,?,?)", ((b, c, "pending") for b, c in work))
            _set(db, cycle_active=True, cycle_started=now(), phase="running", error="", coin_count=len(coins))
        else:
            db.execute("UPDATE item SET state='pending' WHERE state='running'")
    while not _stop_requested(root):
        with closing(_db(root)) as db, db:
            row = db.execute("SELECT bot,coin FROM item WHERE state='pending' ORDER BY bot,coin LIMIT 1").fetchone()
            if row is None:
                break
            bot, coin = row
            db.execute("UPDATE item SET state='running',started=?,error='' WHERE bot=? AND coin=?", (now(), bot, coin))
            _set(db, current={"bot": bot, "coin": coin}, phase="running")
        adopt = bool(coin and getattr(bots, "PER_COIN_OPTIMIZE_ADOPTION_SAFE", False) is True)
        try:
            def progress(fraction: float, message: str) -> None:
                with closing(_db(root)) as db, db:
                    _set(db, progress={"fraction": fraction, "message": str(message), "at": now()})
            report = optimizer(bot, settings, coins=[coin] if coin else None, adopt=adopt, progress=progress)
            summary = json.dumps({"status": report.get("status"), "verdict": report.get("verdict"), "adopt_enabled": adopt}, default=str)
            error = ""
            state = "completed" if report.get("status") in ("completed", "explored") else "failed"
            if state == "failed":
                error = f"optimizer returned {report.get('status')!r}"
        except Exception as exc:
            state, error, summary = "failed", f"{type(exc).__name__}: {exc}", ""
        with closing(_db(root)) as db, db:
            db.execute("UPDATE item SET state=?,finished=?,error=?,summary=? WHERE bot=? AND coin=?", (state, now(), error, summary, bot, coin))
    with closing(_db(root)) as db, db:
        pending = db.execute("SELECT count(*) FROM item WHERE state IN ('pending','running')").fetchone()[0]
        failed = db.execute("SELECT count(*) FROM item WHERE state='failed'").fetchone()[0]
        if not pending:
            missing = _get(db, "coin_count", 0) == 0
            error = f"{failed} optimization(s) failed" if failed else ("no cached coins" if missing else "")
            _set(db, cycle_active=False, last_run=now(), next_run=now() + _get(db, "interval_seconds", DEFAULT_INTERVAL),
                 last_result="partial" if failed or missing else "completed", error=error, current=None)
        return {"pending": pending, "failed": failed}


def _worker(root: Path) -> None:
    try:
        while not _stop_requested(root):
            with closing(_db(root)) as db:
                due = _get(db, "next_run", 0)
                active = _get(db, "cycle_active", False)
            if active or time.time() >= due:
                run_cycle(root=root)
            else:
                with closing(_db(root)) as db, db:
                    _set(db, phase="waiting")
                time.sleep(min(1, max(0, due - time.time())))
        with closing(_db(root)) as db, db:
            _set(db, phase="stopped", current=None)
    except Exception as exc:
        with closing(_db(root)) as db, db:
            _set(db, phase="failed", error=f"{type(exc).__name__}: {exc}")
        raise


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--watchdog":
        watchdog(root=Path(sys.argv[2]))
        return
    if len(sys.argv) != 4 or sys.argv[1] != "--worker":
        raise SystemExit("internal worker only; use start()")
    fd = int(sys.argv[2])
    root = Path(sys.argv[3])
    stat = os.fstat(fd)
    lock_stat = (root / "worker.lock").stat()
    probe = _lock(root)
    if probe is not None:
        os.close(probe)
        raise SystemExit("worker lock is not held")
    if (stat.st_dev, stat.st_ino) != (lock_stat.st_dev, lock_stat.st_ino):
        raise SystemExit("worker lock descriptor does not match")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit("worker does not own the lock") from exc
    _worker(root)


if __name__ == "__main__":
    main()

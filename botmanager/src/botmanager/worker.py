"""One isolated reference-paper worker, holding its lock for its lifetime."""

from __future__ import annotations

import fcntl
import os
import stat
import threading
from contextlib import contextmanager
from pathlib import Path

from .domain import BotSpec, ManagerError
from .ledger import RuntimeLedger

HEARTBEAT_SECONDS = 5.0
STALE_SECONDS = 15.0
BARS_PER_TICK = 64


@contextmanager
def lifetime_lock(path: Path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def lock_held(path: Path) -> bool:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return False
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise OSError("Owner lock must be a regular file")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False
    finally:
        os.close(fd)


def prospective_tick(ledger, row, generation, *, now=None, before_commit=None):
    from .health import entries_paused
    from .oracle_data import advance, rollover
    from .strategies import evaluate

    # The independent heartbeat cannot attest that archive reads or economics
    # are progressing. Fence intent before either can block; atomic progress
    # clears it, including a completed no-data/held-source poll.
    ledger.begin_tick(row["bot_id"], generation)
    data = advance(rollover(row["input"], row["checkpoint"]), now=now)
    checkpoint = row["checkpoint"]
    total = data.get("bar_offset", 0) + len(data["bars"])
    if total > row["cursor"]:
        checkpoint = evaluate(
            BotSpec.from_dict(row["spec"]),
            data,
            total,
            previous=row["checkpoint"],
            entries_paused=entries_paused(
                ledger.home, row["bot_id"], row["runtime_id"]
            ),
        )
    elif data.get("prior_segment") != row["input"].get("prior_segment"):
        # A transition with no new completed bin still binds the same account.
        checkpoint = dict(checkpoint, fills=[], prior_segment=data.get("prior_segment"))
    ledger.commit_progress(
        row["bot_id"],
        generation,
        row["input"]["snapshot_hash"],
        data,
        checkpoint,
        before_commit=before_commit,
    )


def run_worker(home: str, bot_id: str, generation: int, parent_pid: int):
    ledger = RuntimeLedger(Path(home))
    done = threading.Event()

    def pulse():
        while not done.wait(HEARTBEAT_SECONDS):
            if os.getppid() != parent_pid:
                os._exit(0)
            try:
                ledger.heartbeat(bot_id, generation, os.getpid())
            except ManagerError:
                os._exit(0)

    try:
        with lifetime_lock(ledger.home / "locks" / (bot_id + ".lock")):
            if os.getppid() != parent_pid:
                return
            ledger.heartbeat(bot_id, generation, os.getpid())
            thread = threading.Thread(target=pulse, daemon=True)
            thread.start()
            from .health import entries_paused
            from .strategies import evaluate

            while os.getppid() == parent_pid:
                row = ledger.get(bot_id)
                if row["generation"] != generation or row["desired"] != "running":
                    break
                if row["input"].get("prospective") is not None:
                    prospective_tick(ledger, row, generation)
                    done.wait(1.0)
                    continue
                if row["cursor"] == len(row["input"]["bars"]):
                    if (
                        row["observed"] != "waiting"
                        or row["reason"] != "reference_input_exhausted"
                    ):
                        ledger.mark_exhausted(bot_id, generation)
                    done.wait(0.25)
                    continue
                ledger.begin_tick(bot_id, generation)
                state = evaluate(
                    BotSpec.from_dict(row["spec"]),
                    row["input"],
                    min(row["cursor"] + BARS_PER_TICK, len(row["input"]["bars"])),
                    previous=row["checkpoint"],
                    entries_paused=entries_paused(
                        ledger.home, bot_id, row["runtime_id"]
                    ),
                )
                ledger.commit_tick(bot_id, generation, row["cursor"], state)
                done.wait(0.05)
    except BlockingIOError:
        # A previous supervisor's child may still be exiting. Never compete.
        raise SystemExit(75)
    except ManagerError as exc:
        if exc.code == "stale_generation":
            return
        raise SystemExit(1) from None
    except Exception:  # noqa: BLE001 -- process boundary must sanitize every failure
        # Do not echo file contents, descriptor values or uncontrolled tracebacks.
        raise SystemExit(1) from None
    finally:
        done.set()

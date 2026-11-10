"""Explicit foreground daemon, four process slots, no unbounded tick queue."""

from __future__ import annotations

import multiprocessing
import os
import signal
import time
from pathlib import Path
from uuid import uuid4

from .domain import ManagerError
from .ledger import INTEGRITY_ERRORS, MAX_ACTIVE, RuntimeLedger
from .transport import CommandServer
from .worker import STALE_SECONDS, lifetime_lock, lock_held, run_worker


class Supervisor:
    def __init__(self, home: Path | None = None, *, worker_target=run_worker):
        self.ledger = RuntimeLedger(home)
        self.home = self.ledger.home
        self.owner = str(uuid4())
        self.children = {}
        self.worker_target = worker_target
        self.context = multiprocessing.get_context("spawn")
        self.server = None
        self._lock = None
        self._health_at = 0.0

    def open(self):
        if self._lock is not None:
            raise ManagerError("already_running", "Supervisor is already open.", 3)
        self._lock = lifetime_lock(self.home / "supervisor.lock")
        try:
            self._lock.__enter__()
        except BlockingIOError as exc:
            self._lock = None
            raise ManagerError(
                "already_running", "Another supervisor owns this home.", 3
            ) from exc
        try:
            self.ledger.recover(self.owner)
            self.server = CommandServer(self.home)
        except BaseException:
            self.close()
            raise
        return self

    @staticmethod
    def _terminate(process):
        if process.is_alive():
            process.terminate()
        process.join(timeout=0.2)
        if process.is_alive():
            process.kill()
            process.join(timeout=0.2)
        if process.is_alive():
            return False
        process.close()
        return True

    def step(self):
        if self.server is None:
            raise RuntimeError("Supervisor is not open")
        self.server.poll()
        recovering = set()
        if self.ledger.path.exists():
            with self.ledger.connection() as db:
                recovering = {
                    row[0]
                    for row in db.execute(
                        "SELECT bot_id FROM runs WHERE desired='running' AND observed='recovering' AND failures!='[]'"
                    )
                }
        check_health = time.monotonic() - self._health_at >= 1.0
        if check_health:
            self._health_at = time.monotonic()
        for bot_id in self.ledger.ids():
            try:
                row = self.ledger.get(bot_id)
            except ManagerError as exc:
                # Busy/unavailable reads are not proof of corrupt durable data.
                # Revalidate even an integrity error in a fresh write snapshot.
                if exc.code not in INTEGRITY_ERRORS:
                    continue
                try:
                    corrupt = self.ledger.quarantine_if_corrupt(bot_id)
                except ManagerError:
                    continue
                if corrupt:
                    child = self.children.get(bot_id)
                    if child and self._terminate(child[0]):
                        self.children.pop(bot_id)
                continue
            if check_health:
                from .health import HealthStore

                try:
                    HealthStore(self.home).observe(row, now=time.time())
                except ManagerError:
                    # The derived alert journal cannot prevent durable stop.
                    pass
            child = self.children.get(bot_id)
            if row["desired"] == "stopped":
                if child and self._terminate(child[0]):
                    self.children.pop(bot_id)
                if not lock_held(self.home / "locks" / (bot_id + ".lock")):
                    self.ledger.stopped(bot_id)
                continue
            if child:
                process, generation = child
                reason = None
                if not process.is_alive():
                    reason = "worker_exited"
                elif row["generation"] != generation:
                    reason = "generation_revoked"
                elif (
                    row["tick_started"] is not None
                    and time.time() - row["tick_started"] >= STALE_SECONDS - 1
                ):
                    reason = "tick_stalled"
                elif (
                    row["heartbeat"] is None
                    or time.time() - row["heartbeat"] >= STALE_SECONDS - 1
                ):
                    reason = "heartbeat_stale"
                if reason:
                    if reason != "generation_revoked":
                        self.ledger.failed(bot_id, generation, reason)
                        if self.ledger.get(bot_id)["observed"] == "recovering":
                            recovering.add(bot_id)
                    if self._terminate(process):
                        self.children.pop(bot_id)
                continue
            # A failed worker retains its slot during bounded retry delays.
            # Otherwise a queued EOF worker can occupy it forever and prevent
            # the original account from reconciling after a crash.
            reserved = recovering - self.children.keys()
            if bot_id not in reserved and len(self.children) >= MAX_ACTIVE - min(
                MAX_ACTIVE, len(reserved)
            ):
                continue
            if len(self.children) >= MAX_ACTIVE or lock_held(
                self.home / "locks" / (bot_id + ".lock")
            ):
                continue
            generation = self.ledger.claim(bot_id, self.owner)
            if generation is None:
                continue
            process = self.context.Process(
                target=self.worker_target,
                args=(str(self.home), bot_id, generation, os.getpid()),
                daemon=True,
            )
            try:
                process.start()
            except (OSError, RuntimeError, ValueError):
                self.ledger.failed(bot_id, generation, "worker_spawn_failed")
                process.close()
                continue
            self.children[bot_id] = (process, generation)

    def close(self):
        for bot_id, (process, generation) in list(self.children.items()):
            # Shutdown fences commits but preserves running intent for recovery.
            with self.ledger.connection(True) as db:
                db.execute(
                    "UPDATE runs SET generation=generation+1,observed=CASE WHEN desired='stopped' THEN 'stopping' ELSE 'recovering' END WHERE bot_id=? AND generation=?",
                    (bot_id, generation),
                )
            if self._terminate(process):
                self.children.pop(bot_id)
        if self.server is not None:
            self.server.close()
            self.server = None
        if self._lock is not None:
            self._lock.__exit__(None, None, None)
            self._lock = None

    def run(self):
        stopping = False

        def stop(signum, frame):
            nonlocal stopping
            stopping = True

        old = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
        try:
            self.open()
            while not stopping:
                self.step()
                time.sleep(0.05)
        finally:
            self.close()
            for sig, handler in old.items():
                signal.signal(sig, handler)
        return {"state": "stopped", "desired_intent_retained": True}

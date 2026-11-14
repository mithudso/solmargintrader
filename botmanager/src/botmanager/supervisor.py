"""Explicit foreground daemon, four process slots, no unbounded tick queue."""

from __future__ import annotations

import multiprocessing
import os
import signal
import sqlite3
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
        self._watchdogs = {}
        self._pending_failures = {}
        from .learning_job import DailyLearningJob

        self.learning_job = DailyLearningJob(self.home)

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

    def _remember_watchdog(self, bot_id, row):
        child = self.children.get(bot_id)
        if child is None or child[1] != row["generation"]:
            return
        # Monotonic deadlines survive a blocked journal and wall-clock changes.
        # Two seconds leave room for one SQLite timeout and forced termination.
        now, clock = time.monotonic(), time.time()
        heartbeat = row["heartbeat"]
        old = self._watchdogs.get(bot_id)
        same_owner = old is not None and old[:2] == child
        heartbeat_deadline = (
            old[6]
            if same_owner and old[4] == heartbeat
            else now + STALE_SECONDS - 2 - (
                max(0, clock - heartbeat) if heartbeat is not None else 0
            )
        )
        tick = row["tick_started"]
        tick_deadline = (
            None if tick is None
            else old[7] if same_owner and old[5] == tick
            else now + STALE_SECONDS - 2 - max(0, clock - tick)
        )
        deadline, reason = heartbeat_deadline, "heartbeat_stale"
        if tick_deadline is not None and tick_deadline < deadline:
            deadline, reason = tick_deadline, "tick_stalled"
        self._watchdogs[bot_id] = (
            child[0], child[1], deadline, reason, heartbeat, tick,
            heartbeat_deadline, tick_deadline,
        )

    def _journal_blocked(self, *, raise_nontransient=False):
        try:
            # Probe commit availability without the normal one-second timeout.
            # A frozen reader permits BEGIN IMMEDIATE but blocks its commit.
            # An exclusive probe detects readers and writers; rollback changes
            # no rows. mode=rw never creates a store.
            db = sqlite3.connect(
                self.ledger.path.as_uri() + "?mode=rw", uri=True, timeout=0
            )
            try:
                db.execute("BEGIN EXCLUSIVE")
                db.rollback()
            finally:
                db.close()
        except sqlite3.Error as exc:
            if raise_nontransient and (
                getattr(exc, "sqlite_errorcode", 0) & 0xFF
            ) not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
                raise ManagerError(
                    "store_unavailable", "Runtime journal probe is unavailable.", 4
                ) from exc
            return True
        return False

    def _reap_blocked_owners(self):
        for bot_id, child in list(self.children.items()):
            observation = self._watchdogs.get(bot_id)
            if observation is None or observation[:2] != child:
                continue
            process, generation, deadline, reason = observation[:4]
            if time.monotonic() < deadline or not self._journal_blocked():
                continue
            # A frozen owner may hold SQLite's exclusive lock. Kill that exact
            # owned process before attempting the generation-checked write.
            if self._terminate(process):
                self.children.pop(bot_id)
                self._watchdogs.pop(bot_id, None)
                self._pending_failures[bot_id] = (generation, reason)

    def _flush_failures(self):
        from .health import HealthStore

        for bot_id, (generation, reason) in list(self._pending_failures.items()):
            try:
                # failed() verifies the original generation and desired intent.
                # It never substitutes a guessed generation after a control.
                self.ledger.failed(bot_id, generation, reason)
                row = self.ledger.get(bot_id)
            except ManagerError:
                continue
            self._pending_failures.pop(bot_id)
            try:
                HealthStore(self.home).observe(row, now=time.time())
            except ManagerError:
                pass

    def step(self):
        if self.server is None:
            raise RuntimeError("Supervisor is not open")
        self._reap_blocked_owners()
        self._flush_failures()
        self.server.poll()
        # Owner learning runs in one separately bounded process; controls keep polling.
        try:
            self.learning_job.step()
        except (OSError, ManagerError):
            pass
        recovering = set()
        if self.ledger.path.exists():
            try:
                with self.ledger.connection() as db:
                    recovering = {
                        row[0]
                        for row in db.execute(
                            "SELECT bot_id FROM runs WHERE desired='running' AND observed='recovering' AND (failures!='[]' OR reason IN ('entry_pause_handoff','entry_resume_handoff'))"
                        )
                    }
            except ManagerError as exc:
                if exc.code != "store_unavailable":
                    raise
                # No admission or journal inference while reads are uncertain.
                # The cached owned-process watchdog still runs on every step.
                return
        check_health = time.monotonic() - self._health_at >= 1.0
        if check_health:
            self._health_at = time.monotonic()
        try:
            bot_ids = self.ledger.ids()
        except ManagerError as exc:
            if exc.code != "store_unavailable":
                raise
            return
        for bot_id in bot_ids:
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
            self._remember_watchdog(bot_id, row)
            if bot_id in self._pending_failures:
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
                    # A shared reader permits BEGIN IMMEDIATE but blocks commit.
                    # Avoid spending that busy timeout on a known-blocked peer;
                    # the next step must reach owned-process watchdogs first.
                    if self._journal_blocked(raise_nontransient=True):
                        return
                    try:
                        self.ledger.stopped(bot_id)
                    except ManagerError as exc:
                        cause = exc.__cause__
                        if (
                            exc.code != "store_unavailable"
                            or not isinstance(cause, sqlite3.OperationalError)
                            or (getattr(cause, "sqlite_errorcode", 0) & 0xFF)
                            not in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED)
                        ):
                            raise
                        # A frozen owner can block a stopped peer's commit.
                        # Defer that write, with no admission, so the next step
                        # reaches the cached owned-process watchdog first.
                        return
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
                if reason and self._terminate(process):
                    self.children.pop(bot_id)
                    self._watchdogs.pop(bot_id, None)
                    if reason != "generation_revoked":
                        # Reap before writing: this very owner may hold the
                        # writer lock. Retain the verified generation until the
                        # failure write succeeds; never admit its replacement
                        # from an uncertain journal outcome.
                        self._pending_failures[bot_id] = (generation, reason)
                        recovering.add(bot_id)
                        self._flush_failures()
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
            deadline = time.monotonic() + STALE_SECONDS - 2
            self._watchdogs[bot_id] = (
                process, generation, deadline, "heartbeat_stale",
                None, None, deadline, None,
            )

    def close(self):
        failure = None
        owners = list(self.children.items())
        # Reap every exact owned process before touching SQLite. A frozen
        # writer can hold even a schema read in its busy timeout; an attempted
        # pre-kill fence therefore cannot provide bounded owner release.
        for bot_id, (process, _) in owners:
            if self._terminate(process):
                self.children.pop(bot_id)
                self._watchdogs.pop(bot_id, None)
            else:
                failure = ManagerError(
                    "store_unavailable", "Owned process release remains unavailable.", 4
                )
        try:
            self.learning_job.close()
        except (OSError, ManagerError):
            # An optional scheduler receipt failure cannot hold worker ownership.
            pass
        for bot_id, (_, generation) in owners:
            try:
                # Retain the captured generation. A later control must never be
                # overwritten, and an uncommitted owner write rolls back on reap.
                self._shutdown_fence(bot_id, generation)
            except ManagerError as exc:
                failure = exc
        self._flush_failures()
        if self._pending_failures:
            failure = ManagerError(
                "store_unavailable",
                "Owners released; failure journal reconciliation remains unavailable.",
                4,
            )
        if self.server is not None:
            self.server.close()
            self.server = None
        if self._lock is not None:
            self._lock.__exit__(None, None, None)
            self._lock = None
        if failure is not None:
            raise failure

    def _shutdown_fence(self, bot_id, generation):
        with self.ledger.connection(True) as db:
            db.execute(
                "UPDATE runs SET generation=generation+1,observed=CASE WHEN desired='stopped' THEN 'stopping' ELSE 'recovering' END WHERE bot_id=? AND generation=?",
                (bot_id, generation),
            )

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

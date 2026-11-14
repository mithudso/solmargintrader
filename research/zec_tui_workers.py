"""Single-owner background reads with bounded, latest-request delivery.

Loaders must bound their own blocking operations and check ``cancelled`` between
them. Python threads cannot forcibly interrupt an arbitrary blocking call. This
helper never calls UI objects; the UI polls immutable completion envelopes.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class WorkerResult:
    generation: int
    value: Any = None
    error: str | None = None


class LatestWorker:
    """Run one loader at a time and retain only its latest requested successor.

    ``submit`` supersedes both pending work and unread results. A superseded
    loader may finish its current bounded operation, but its output and errors
    cannot become current. ``close`` discards everything and joins at most the
    specified timeout; ``alive`` truthfully exposes any still-finishing loader.
    """

    def __init__(
        self,
        loader: Callable[[Any, Callable[[], bool]], Any],
        *,
        name: str = "oracle-tui-worker",
    ) -> None:
        self._loader = loader
        self._condition = threading.Condition()
        self._stop_requested = False
        self._generation = 0
        self._active_generation: int | None = None
        self._pending: tuple[int, Any] | None = None
        self._result: WorkerResult | None = None
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()

    @property
    def generation(self) -> int:
        with self._condition:
            return self._generation

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    @property
    def busy(self) -> bool:
        """Let periodic refreshes skip redundant work instead of starving it."""
        with self._condition:
            return self._active_generation is not None or self._pending is not None

    def submit(self, request: Any) -> int:
        # The worker owns its copy even if the editor immediately changes a
        # nested member parameter after submission.
        owned_request = copy.deepcopy(request)
        with self._condition:
            if self._stop_requested:
                raise RuntimeError("worker_closed")
            self._generation += 1
            self._pending = (self._generation, owned_request)
            self._result = None
            self._condition.notify()
            return self._generation

    def poll(self) -> WorkerResult | None:
        with self._condition:
            result, self._result = self._result, None
            if (
                self._stop_requested
                or result is None
                or result.generation != self._generation
            ):
                return None
            return result

    def close(self, timeout: float = 0.3) -> None:
        if (
            type(timeout) not in (int, float)
            or not 0 <= timeout <= threading.TIMEOUT_MAX
        ):
            raise ValueError("invalid_close_timeout")
        with self._condition:
            self._stop_requested = True
            self._pending = None
            self._result = None
            self._condition.notify_all()
        if threading.current_thread() is not self._thread:
            self._thread.join(timeout)

    def _cancelled(self, generation: int) -> bool:
        with self._condition:
            return self._stop_requested or generation != self._generation

    def _run(self) -> None:
        while True:
            with self._condition:
                self._condition.wait_for(
                    lambda: self._stop_requested or self._pending is not None
                )
                if self._stop_requested:
                    return
                assert self._pending is not None
                generation, request = self._pending
                self._pending = None
                self._active_generation = generation
            try:
                value = self._loader(
                    request,
                    lambda generation=generation: self._cancelled(generation),
                )
                result = WorkerResult(generation=generation, value=value)
            except Exception:  # noqa: BLE001 - external loader errors must not leak source data.
                result = WorkerResult(generation=generation, error="worker_failed")
            with self._condition:
                self._active_generation = None
                if not self._stop_requested and generation == self._generation:
                    self._result = result

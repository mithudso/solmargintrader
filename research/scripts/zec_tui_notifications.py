"""Optional display-only notifications: bounded identities and owned playback."""

from __future__ import annotations

import math
import os
import selectors
import subprocess
import threading
import time
from collections import deque
from pathlib import Path

DEFAULT_SOUNDS = {"reversal": False, "two_up": False, "backend": "bell"}
AFPLAY = "/usr/bin/afplay"
SYSTEM_SOUND = "/System/Library/Sounds/Glass.aiff"


def sound_settings(value=None):
    if value is None:
        return dict(DEFAULT_SOUNDS)
    if not isinstance(value, dict) or set(value) - DEFAULT_SOUNDS.keys():
        raise ValueError("Invalid sound settings")
    result = {**DEFAULT_SOUNDS, **value}
    if any(type(result[k]) is not bool for k in ("reversal", "two_up")) or result[
        "backend"
    ] not in ("bell", "macos"):
        raise ValueError("Invalid sound settings")
    return result


class NotificationEvents:
    """Consume event identities even when muted; startup is a silent baseline."""

    def __init__(self):
        self.seen = set()
        self.order = deque()
        self.start_window = None
        self.high_window = -1
        self.reversal_ready = False
        self.config_window = None
        self.config_history_ready = self.config_reversal_ready = False

    def _consume(self, identity):
        if identity in self.seen:
            return False
        self.seen.add(identity)
        self.order.append(identity)
        while len(self.order) > 256:
            self.seen.remove(self.order.popleft())
        return True

    def observe(self, alert, settings, now, *, quiet=False):
        if type(now) not in (int, float) or not math.isfinite(now):
            return ()
        if quiet:
            # Applying preferences during a history outage must not replay the
            # window's existing setup when usable data finally arrives.
            self.config_window = int(now // 600) * 600
            self.config_history_ready = self.config_reversal_ready = False
        if not isinstance(alert, dict):
            return ()
        start, target = alert.get("current_start"), alert.get("target_at")
        count = alert.get("closed_up_count")
        if (
            type(start) is not int
            or start != int(now // 600) * 600
            or target != start + 600
            or start < self.high_window
            or type(count) is not int
            or count not in (0, 1, 2)
            or alert.get("stage") not in ("no_up_setup", "one_up_bar2", "two_up_bar3")
            or alert.get("data_status")
            in (
                "invalid_clock",
                "history_unavailable",
                "history_stale_or_future",
                "previous_constituent_missing",
            )
        ):
            return ()
        first = self.start_window is None
        if first:
            self.start_window = start
        self.high_window = start
        comparable = (
            count == 0
            or now - start < 300
            or (
                alert.get("data_status") == "ready"
                and alert.get("price") is not None
                and alert.get("true_open") is not None
            )
        )
        startup_reversal = not self.reversal_ready and start == self.start_window
        config_history = start == self.config_window and not self.config_history_ready
        config_reversal = start == self.config_window and not self.config_reversal_ready
        if start == self.config_window:
            self.config_history_ready = True
            if comparable:
                self.config_reversal_ready = True
        if comparable or start != self.start_window:
            self.reversal_ready = True
        conditions = []
        if count == 2 and alert.get("stage") == "two_up_bar3":
            conditions.append("two_up")
        if (
            alert.get("reversal_detected") is True
            and alert.get("state") == "observed_reversal"
            and alert.get("data_status") == "ready"
            and alert.get("direction") == "DOWN"
        ):
            conditions.append("reversal")
        emitted = []
        for event in conditions:
            fresh = self._consume((start, event))
            if (
                fresh
                and not first
                and not quiet
                and not config_history
                and not (event == "reversal" and config_reversal)
                and not (event == "reversal" and startup_reversal)
                and settings[event]
            ):
                emitted.append(event)
        return tuple(emitted)


class SoundPlayer:
    """One off-UI afplay child, no queue and no UI callbacks from its thread."""

    def __init__(self, *, popen=subprocess.Popen, timeout=5.0):
        self.popen = popen
        self.timeout = timeout
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.busy = False
        self.result = None

    def play(self):
        with self.lock:
            if self.stop.is_set() or self.busy:
                return False
            self.busy = True
            self.thread = threading.Thread(
                target=self._run, name="oracle-sound", daemon=True
            )
            self.thread.start()
        return True

    def poll(self):
        with self.lock:
            result, self.result = self.result, None
        return result

    @property
    def alive(self):
        return bool(self.thread and self.thread.is_alive())

    def _run(self):
        process = None
        selector = selectors.DefaultSelector()
        stderr = bytearray()
        error = None
        try:
            if not Path(AFPLAY).is_file() or not Path(SYSTEM_SOUND).is_file():
                raise OSError("System sound unavailable")
            if self.stop.is_set():
                return
            process = self.popen(
                [AFPLAY, SYSTEM_SOUND],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            selector.register(process.stderr, selectors.EVENT_READ)
            deadline = time.monotonic() + self.timeout
            while True:
                if self.stop.is_set() or time.monotonic() >= deadline:
                    if not self.stop.is_set():
                        error = "Sound playback timed out"
                    break
                for key, _ in selector.select(0.05):
                    chunk = os.read(key.fileobj.fileno(), 1024)
                    if chunk:
                        stderr.extend(chunk[: max(0, 4096 - len(stderr))])
                    else:
                        selector.unregister(key.fileobj)
                if process.poll() is not None:
                    if process.returncode:
                        error = f"Sound playback failed (exit {process.returncode})"
                    break
        except (OSError, ValueError, subprocess.SubprocessError):
            error = "System sound unavailable or playback failed"
        finally:
            if process is not None:
                if process.poll() is None:
                    try:
                        process.terminate()
                    except ProcessLookupError:
                        pass
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(timeout=0.2)
                        except subprocess.TimeoutExpired:
                            error = "Sound child did not exit after cancellation"
                if process.stderr:
                    process.stderr.close()
            selector.close()
            with self.lock:
                self.busy = False
                # Keep bounded stderr private; UI errors contain only a fixed
                # explanation and exit status, never arbitrary child output.
                self.result = (
                    {"error": error, "stderr": bytes(stderr)}
                    if not self.stop.is_set()
                    else None
                )

    def close(self, timeout=0.5):
        self.stop.set()
        thread = self.thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout)

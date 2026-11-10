"""One nonblocking daily canonical-owner helper inside an explicit daemon.

Status reads never start a schedule. The helper is the registered owner process
itself, so cancellation owns one process group and cannot orphan an adapter.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from .domain import ManagerError, canonical
from .research_owner import OwnerClient

STATUS_FILE = "learning-job.json"
OUTPUT_LIMIT = 256 * 1024
TIMEOUT_SECONDS = 120


def _read(path, limit=65536):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("document_unavailable")
    return json.loads(path.read_text())


def schedule_snapshot(home):
    """Read only the bounded local receipt; owner scope dedup stays canonical."""
    home = Path(home)
    path = home / STATUS_FILE
    if path.is_file():
        try:
            return _read(path)
        except (ValueError, OSError):
            return {"state": "unavailable", "reason": "schedule_status_unreadable"}
    return {
        "state": "unavailable",
        "reason": "reviewed_owner_descriptor_absent"
        if not (home / "research-owner.json").is_file()
        else "daemon_has_not_attempted_schedule",
        "last_attempt": None,
    }


class DailyLearningJob:
    def __init__(self, home):
        self.home = Path(home)
        self.process = None
        self.streams = {}
        self.started = None
        self.expected_identity = None
        self.receipt = schedule_snapshot(self.home)
        self._checked_at = 0.0

    def _save(self, state, reason, **values):
        self.receipt = {**self.receipt, "state": state, "reason": reason, **values}
        # The selected daemon is the only writer under its existing owner lock.
        path = self.home / STATUS_FILE
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=self.home, prefix=".learning-job-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                os.chmod(temporary, 0o600)
                stream.write(canonical(self.receipt) + "\n")
            temporary.replace(path)
            temporary = None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _stop(self):
        process = self.process
        if process is None:
            return
        try:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=1)
        finally:
            for stream in self.streams:
                stream.close()
            self.streams = {}
            self.process = None

    def _drain(self):
        for stream, buffer in self.streams.items():
            while True:
                try:
                    chunk = os.read(stream.fileno(), 16384)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                buffer.extend(chunk)
                if len(buffer) > OUTPUT_LIMIT:
                    raise ValueError("helper_output_limit")

    def _poll(self):
        try:
            self._drain()
            if time.monotonic() - self.started >= TIMEOUT_SECONDS:
                raise ValueError("helper_timeout")
            process = self.process
            code = process.poll()
            if code is None:
                return
            self._drain()
            raw = bytes(self.streams[process.stdout])
            stderr_bytes = len(self.streams[process.stderr])
            self._stop()
            response = json.loads(raw)
            result = response.get("result")
            if (
                code != 0
                or response.get("ok") is not True
                or response.get("command") != "research.protocol"
                or not isinstance(result, dict)
                or result.get("identity") != self.expected_identity
            ):
                raise ValueError("owner_daily_failed")
            self._save(
                "completed",
                result.get("reason", "canonical_daily_attempt_completed"),
                completed_at=time.time(),
                result=result.get("schedule"),
                stderr_bytes=stderr_bytes,
            )
        except (ValueError, OSError, subprocess.SubprocessError):
            self._stop()
            self._save(
                "failed",
                "owner_helper_failed_or_bounded_limit",
                completed_at=time.time(),
            )

    def step(self):
        """Polling never waits for owner work; one launch at most per UTC day."""
        if self.process is not None:
            self._poll()
            return
        monotonic = time.monotonic()
        if monotonic - self._checked_at < 1:
            return
        self._checked_at = monotonic
        now = time.time()
        day = datetime.fromtimestamp(now, UTC).date().isoformat()
        if self.receipt.get("day") == day:
            return
        descriptor_path = self.home / "research-owner.json"
        if not descriptor_path.is_file():
            return
        try:
            descriptor = _read(descriptor_path)
            OwnerClient(descriptor)  # Validate installation, without a subprocess.
            self.expected_identity = descriptor["expected_identity"]
            request = {
                "version": 2,
                "operation": "learning-daily",
                "authority": descriptor["authority"],
                "expected_identity": self.expected_identity,
                "params": {"manager_home": str(self.home.resolve())},
            }
            payload = canonical(request).encode()
            if len(payload) > OUTPUT_LIMIT:
                raise ValueError("helper_input_limit")
            self._save(
                "running",
                "canonical_daily_owner_attempt",
                day=day,
                last_attempt=now,
                completed_at=None,
            )
            environment = {
                "PATH": "/usr/bin:/bin",
                "LC_ALL": "C",
                "PYTHONDONTWRITEBYTECODE": "1",
                "SOLTUI_CONFIG_DIR": descriptor["config_root"],
            }
            if os.environ.get("SOLTUI_RESEARCH_REGISTRY"):
                environment["SOLTUI_RESEARCH_REGISTRY"] = os.environ[
                    "SOLTUI_RESEARCH_REGISTRY"
                ]
            with tempfile.TemporaryFile() as stdin:
                stdin.write(payload)
                stdin.seek(0)
                self.process = subprocess.Popen(
                    [
                        descriptor["interpreter"],
                        "-I",
                        "-B",
                        "-m",
                        "soltui.research_owner",
                    ],
                    stdin=stdin,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=descriptor["repository"],
                    env=environment,
                    close_fds=True,
                    start_new_session=True,
                )
            self.started = time.monotonic()
            self.streams = {
                self.process.stdout: bytearray(),
                self.process.stderr: bytearray(),
            }
            for stream in self.streams:
                os.set_blocking(stream.fileno(), False)
        except (ValueError, OSError, ManagerError, KeyError, TypeError):
            self._stop()
            self._save(
                "failed",
                "reviewed_owner_unavailable",
                day=day,
                last_attempt=now,
                completed_at=time.time(),
            )

    def close(self):
        if self.process is not None:
            self._stop()
            self._save(
                "cancelled", "daemon_closed_helper_reaped", completed_at=time.time()
            )

"""Chrome native-messaging host `com.mitchhudson.soltui`: the extension's door into the registry.

Speaks Chrome's framing on stdio: a 4-byte little-endian length, then that many bytes of UTF-8 JSON.
It serves many requests per connection (`connectNative`) or one (`sendNativeMessage`). Requests:

    {"id", "op": "ping"}
    {"id", "op": "list"}
    {"id", "op": "call", "command": "<name>", "params": {...}}
    {"id", "op": "buildHash"}

Each reply is `{"id": <echoed>, "response": <envelope>}`. The envelope is the registry's, rendered by
`commands.dumps`, so the bytes inside `response` equal what the CLI and API print for the same call.
`id` lives outside the envelope. `ping` and `buildHash` are host-level and not logged; `list` and
`call` go through `dispatch`, which writes the one call-log line.

Chrome refuses a host message over 1 MB, so a reply that large is replaced by a `failed` envelope
that says to use the CLI or API. Chrome allows 64 MiB the other way; a longer frame is refused and the
connection ends (the stream cannot be resynchronised).

`buildHash` lets the extension notice that its own source changed on disk: sha256 over the manifest
and every file under `src/` of the extension directory (default `<repo>/extension`, override with
`SOLTUI_EXTENSION_DIR`).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import sys
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, BinaryIO

from . import commands

HOST_NAME = "com.mitchhudson.soltui"
PROTOCOL = 1
MAX_REPLY_BYTES = 1024 * 1024
MAX_REQUEST_BYTES = 64 * 1024 * 1024
OVERSIZE_MESSAGE = ("reply exceeds Chrome's 1 MB native-messaging limit; "
                    "use the soltui CLI or API for this call")
_SUITE_ACTIONS = frozenset({"status", "health", "start"})
_SUITE_ORIGIN = re.compile(r"chrome-extension://[a-p]{32}/?\Z")
_SUITE_URL = re.compile(r"http://127\.0\.0\.1:([1-9][0-9]{0,4})/?\Z")
_suite_lock = threading.Lock()
_suite_replies: OrderedDict[str, tuple[str, dict[str, Any]]] = OrderedDict()
_suite_pending: dict[str, str] = {}


class FrameError(Exception):
    """The stream is not a valid frame sequence."""


def read_frame(stream: BinaryIO) -> bytes | None:
    """One frame body, or None at a clean end of stream."""
    header = stream.read(4)
    if not header:
        return None
    if len(header) < 4:
        raise FrameError("truncated length prefix")
    (length,) = struct.unpack("<I", header)
    if length > MAX_REQUEST_BYTES:
        raise FrameError(f"request of {length} bytes exceeds the {MAX_REQUEST_BYTES} byte limit")
    body = stream.read(length)
    if len(body) < length:
        raise FrameError("truncated frame body")
    return body


def write_frame(stream: BinaryIO, body: bytes) -> None:
    stream.write(struct.pack("<I", len(body)) + body)
    stream.flush()


def extension_dir() -> Path:
    return Path(os.environ.get("SOLTUI_EXTENSION_DIR") or commands.REPO / "extension")


def build_hash(root: Path | None = None) -> dict[str, Any]:
    """sha256 over manifest.json and every file under src/, by relative path then content."""
    root = (root or extension_dir()).resolve()
    files = [root / "manifest.json"] + sorted(
        p for p in (root / "src").rglob("*") if p.is_file() and not p.name.startswith("."))
    digest = hashlib.sha256()
    count = 0
    for path in files:
        try:
            data = path.read_bytes()
        except OSError as exc:
            raise commands.CommandError("failed", f"cannot read {path.relative_to(root)}: {exc}") from exc
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + data + b"\0")
        count += 1
    return {"hash": digest.hexdigest(), "files": count, "root": str(root)}


def _reply(request_id: Any, envelope: dict[str, Any]) -> bytes:
    encoded_id = json.dumps(request_id)
    if len(encoded_id) > 4096:
        encoded_id = "null"
        envelope = commands.error_envelope("", "bad_params", "request id exceeds the metadata limit")
    # JSON permits escaped unpaired surrogates. Preserve them as escapes instead
    # of allowing UTF-8 encoding to terminate the persistent connection.
    body = f'{{"id":{encoded_id},"response":{commands.dumps(envelope)}}}'.encode("utf-8", errors="backslashreplace")
    if len(body) > MAX_REPLY_BYTES:
        small = commands.error_envelope("", "failed", OVERSIZE_MESSAGE)
        body = json.dumps({"id": request_id if len(json.dumps(request_id)) <= 4096 else None,
                           "response": small}).encode("utf-8")
    if len(body) > MAX_REPLY_BYTES:
        body = json.dumps({"id": None, "response": commands.error_envelope("", "failed", OVERSIZE_MESSAGE)}).encode("utf-8")
    return body


def handle_request(raw: bytes) -> bytes:
    """Turn one request frame into one reply frame body. Never raises."""
    try:
        return _handle_request(raw)
    except Exception:  # noqa: BLE001 -- sanitize the native trust boundary
        return _reply(None, commands.error_envelope("", "failed", "request could not be processed"))


def browser_origin() -> str:
    # Chrome supplies this process argument. A JSON field is never an origin.
    return sys.argv[1] if len(sys.argv) > 1 else ""


def browser_manager(message):
    from botmanager.adapters.extension import BrowserStore

    from .native_host_install import allowed_origins

    return BrowserStore().poll(message, origin=browser_origin(), allowed_origins=allowed_origins())


def suite_control(action: str) -> dict[str, Any]:
    """Use only locally configured homes. Browser messages cannot select a process or path."""
    from botmanager import machine_health, suite

    snapshot = suite.operation("start" if action == "start" else "status")
    health = machine_health.check()
    # Even a corrupt checkpoint must not turn the extension into a URL launcher.
    url = health.get("ui_url")
    match = _SUITE_URL.fullmatch(url) if isinstance(url, str) else None
    snapshot = {key: snapshot[key] for key in ("schema_version", "state", "ready") if key in snapshot}
    snapshot["ui_url"] = url if match and 0 < int(match[1]) < 65536 else None
    health = {**health, "ui_url": snapshot["ui_url"]}
    return {"schema_version": 1, "capability": "control-room-v1",
            "status": snapshot, "health": health}


def _suite_request(request: dict[str, Any], raw: bytes) -> dict[str, Any]:
    """Authenticate before importing controllers; bound duplicate admission on this port."""
    from uuid import UUID

    from .native_host_install import allowed_origins

    identity, action = request.get("id"), request.get("action")
    try:
        valid_id = type(identity) is str and str(UUID(identity)) == identity
    except ValueError:
        valid_id = False
    if len(raw) > 4096 or set(request) != {"id", "op", "action"} or not valid_id or type(action) is not str or action not in _SUITE_ACTIONS:
        return commands.error_envelope("suite", "bad_params", "invalid suite request")
    origin = browser_origin()
    if not _SUITE_ORIGIN.fullmatch(origin) or origin.rstrip("/") not in {value.rstrip("/") for value in allowed_origins()}:
        return commands.error_envelope("suite", "forbidden", "native suite caller is not authorized")
    with _suite_lock:
        prior = _suite_replies.get(identity)
        if prior:
            return prior[1] if prior[0] == action else commands.error_envelope("suite", "bad_params", "request identity was already used")
        if identity in _suite_pending:
            return commands.error_envelope("suite", "busy", "suite request is already in progress")
        if action == "start" and "start" in _suite_pending.values():
            return commands.error_envelope("suite", "busy", "suite startup is already in progress; refresh health")
        _suite_pending[identity] = action
    try:
        try:
            envelope = commands.ok_envelope("suite", suite_control(action))
        except (ImportError, AttributeError):
            envelope = commands.error_envelope("suite", "incompatible_helper", "native helper needs the managed-suite runtime")
        except Exception:  # noqa: BLE001 -- no local paths or process errors cross this boundary
            envelope = commands.error_envelope("suite", "suite_failed", "managed suite request failed; inspect local solbot stack status")
        with _suite_lock:
            _suite_replies[identity] = (action, envelope)
            while len(_suite_replies) > 128:
                _suite_replies.popitem(last=False)
        return envelope
    finally:
        with _suite_lock:
            _suite_pending.pop(identity, None)


def _handle_request(raw: bytes) -> bytes:
    try:
        request = json.loads(raw.decode("utf-8"))
        if not isinstance(request, dict):
            raise ValueError("request must be an object")  # noqa: TRY004 -- public protocol error
    except ValueError:
        return _reply(None, commands.error_envelope("", "bad_params", "request is not a JSON object"))
    request_id = request.get("id")
    op = request.get("op")
    for value in (op, request.get("command", "")):
        if isinstance(value, str):
            try:
                if len(value.encode("utf-8")) <= 256:
                    continue
            except UnicodeEncodeError:
                pass
            return _reply(request_id, commands.error_envelope("", "bad_params", "invalid request operation or command"))
    if len(json.dumps(request_id)) > 4096:
        return _reply(None, commands.error_envelope("", "bad_params", "request id exceeds the metadata limit"))
    if op == "suite":
        env = _suite_request(request, raw)
        from uuid import UUID
        try:
            if type(request_id) is not str or str(UUID(request_id)) != request_id:
                request_id = None
        except ValueError:
            request_id = None
    elif op == "browserManager":
        if len(raw) > 65536:
            return _reply(None, commands.error_envelope("browserManager", "bad_params", "browser message exceeds the protocol bound"))
        from uuid import UUID
        try:
            if type(request_id) is not str or str(UUID(request_id)) != request_id:
                raise ValueError
        except ValueError:
            return _reply(None, commands.error_envelope("browserManager", "bad_params", "invalid browser request identity"))
        if set(request) != {"id", "op", "message"}:
            env = commands.error_envelope("browserManager", "bad_params", "invalid browser message fields")
        else:
            try:
                env = commands.ok_envelope("browserManager", browser_manager(request["message"]))
            except Exception:  # noqa: BLE001 -- sanitize the native trust boundary
                env = commands.error_envelope("browserManager", "failed", "browser owner registration refused")
    elif op == "ping":
        env = commands.ok_envelope("ping", {"pong": True, "host": HOST_NAME, "protocol": PROTOCOL})
    elif op == "list":
        env = commands.dispatch("list", {}, surface="native")
    elif op == "call":
        name = request.get("command")
        if not isinstance(name, str):
            env = commands.error_envelope("", "bad_params", 'call needs a string "command"')
        else:
            env = commands.dispatch(name, request.get("params") or {}, surface="native")
    elif op == "buildHash":
        try:
            env = commands.ok_envelope("buildHash", build_hash())
        except commands.CommandError as exc:
            env = commands.error_envelope("buildHash", exc.code, exc.message)
        except OSError as exc:
            env = commands.error_envelope("buildHash", "failed", str(exc))
    else:
        env = commands.error_envelope(str(op), "unknown_command", f'unknown op "{op}"')
    return _reply(request_id, env)


def serve(stdin: BinaryIO, stdout: BinaryIO) -> None:
    """Keep status and cancellation available during long calls on the same runtime.

    Only declared long-running commands leave the reader thread. The bounded
    admission gate refuses excess work rather than growing an unbounded queue.
    Each response carries its request id; the write lock keeps frames intact.
    """
    output_lock = threading.Lock()
    slots = threading.BoundedSemaphore(4)

    def send(body: bytes) -> None:
        with output_lock:
            write_frame(stdout, body)

    def run(raw: bytes) -> None:
        try:
            send(handle_request(raw))
        finally:
            slots.release()

    with ThreadPoolExecutor(max_workers=4, thread_name_prefix="soltui-native") as pool:
        while True:
            try:
                raw = read_frame(stdin)
            except FrameError as exc:
                send(_reply(None, commands.error_envelope("", "failed", str(exc))))
                return
            if raw is None:
                return
            try:
                request = json.loads(raw)
                cmd = commands.COMMANDS.get(request.get("command")) if isinstance(request, dict) else None
                is_suite_start = isinstance(request, dict) and request.get("op") == "suite" and request.get("action") == "start"
                is_long = is_suite_start or (isinstance(request, dict) and request.get("op") == "call" and cmd and cmd.long_running)
            except (ValueError, TypeError, RecursionError):
                is_long = False
            if not is_long:
                send(handle_request(raw))
            elif slots.acquire(blocking=False):
                pool.submit(run, raw)
            else:
                send(_reply(request.get("id"), commands.error_envelope(
                    cmd.name if cmd else "suite", "failed", "native host is busy with four long-running calls; request was not started")))


def main() -> int:
    from . import prediction_recovery

    # Chrome owns stdout; any stray print would corrupt the frame stream.
    real_out = sys.stdout.buffer
    try:
        registration = prediction_recovery.register_console()
    except OSError:
        # Read-only calls can still work without writable registration storage.
        # Other clients conservatively treat this process as an unknown host.
        registration = None
    sys.stdout = sys.stderr
    try:
        serve(sys.stdin.buffer, real_out)
        return 0
    finally:
        if registration is not None:
            registration.close()


if __name__ == "__main__":
    raise SystemExit(main())

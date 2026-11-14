"""HTTP surface: `soltui api [--port N]`. Stdlib `http.server`; mirrors extension/tools/api-server.js.

    GET  /v1/health            liveness, no auth
    GET  /v1/commands          the `list` envelope
    GET  /v1/<command>?a=1     read-only commands, args from the query string
    POST /v1/<command>         any command, args from a JSON object body

Command routes return the registry envelope exactly as `commands.dumps` renders it, so the body is
byte-identical to the CLI's output for the same call.

Access, in the order it is applied:

* binds 127.0.0.1 only; there is deliberately no option to widen it;
* any request carrying an `Origin` or `Sec-Fetch-Site` header is refused (403): a web page can post to
  localhost, so a token alone is not enough. No CORS headers are ever sent;
* every route but /v1/health needs `Authorization: Bearer <token>`, compared with
  `hmac.compare_digest`. The token lives in `<support dir>/api-token`, mode 600, created on first run;
* GET is limited to read-only commands.
"""

from __future__ import annotations

import argparse
import hmac
import json
import os
import re
import secrets
import stat
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from . import commands

HOST = "127.0.0.1"
DEFAULT_PORT = 8788
MAX_BODY_BYTES = 1024 * 1024
REJECT_DRAIN_TIMEOUT_S = 0.25
REQUEST_READ_TIMEOUT_S = 10.0

REQUEST_TIMEOUT_S = REQUEST_READ_TIMEOUT_S
MAX_CONNECTIONS = 16


class BoundedHTTPServer(ThreadingHTTPServer):
    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(MAX_CONNECTIONS)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(REQUEST_TIMEOUT_S)
        return request, address

    def process_request(self, request, client_address):
        if not self._slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


_ROUTE = re.compile(r"^/v1/([A-Za-z][A-Za-z0-9_.]*)$")
_STATUS = {"bad_params": 400, "unknown_command": 404, "forbidden": 403, "failed": 500, "timeout": 504}


def support_dir() -> Path:
    return Path(os.environ.get("SOLTUI_SUPPORT_DIR")
                or Path.home() / "Library" / "Application Support" / "soltui")


def token_path() -> Path:
    return support_dir() / "api-token"


def load_token(path: Path | None = None) -> str:
    """Read the bearer token, creating it (mode 600) on first run. Never printed or logged."""
    path = path or token_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_urlsafe(32) + "\n")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        os.chmod(path, 0o600)
    token = path.read_text().strip()
    if not token:
        raise RuntimeError(f"{path} is empty; delete it to have a new token generated")
    return token


def token_matches(provided: str, token: str) -> bool:
    if not token.strip() or not provided:
        return False
    return hmac.compare_digest(provided.encode(), token.encode())


def make_handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "soltui-api"
        protocol_version = "HTTP/1.1"

        def setup(self) -> None:
            super().setup()
            self.connection.settimeout(min(REQUEST_READ_TIMEOUT_S, REQUEST_TIMEOUT_S))

        def log_message(self, fmt: str, *args: Any) -> None:  # request lines carry query values
            pass

        def _send(self, status: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.send_header("x-content-type-options", "nosniff")
            self.send_header("cache-control", "no-store")
            if self.close_connection:
                self.send_header("connection", "close")
            self.end_headers()
            self.wfile.write(data)

        def _refuse(self, status: int, code: str, message: str, name: str = "") -> None:
            self._send(status, commands.dumps(commands.error_envelope(name, code, message)))

        def _handle(self, method: str) -> None:
            if method == "POST":
                self.close_connection = True
            try:
                length = self._body_length()
                if method == "GET" and length:
                    raise commands.CommandError("bad_params", "GET request bodies are not supported")
            except commands.CommandError as exc:
                self.close_connection = True
                self._refuse(413 if "too large" in exc.message else 400, exc.code, exc.message)
                return
            url = urlsplit(self.path)
            path = url.path.rstrip("/")
            if path == "/v1/health" and method == "GET":
                self._send(200, commands.dumps(
                    {"ok": True, "service": "soltui", "commands": len(commands.COMMANDS)}))
                return
            if self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site"):
                self._refuse(403, "forbidden",
                             "browser-originated requests are refused; use a CLI or server-side client")
                return
            auth = self.headers.get("Authorization", "")
            bearer = auth[7:] if auth.startswith("Bearer ") else ""
            if not token_matches(bearer, token):
                self._refuse(401, "forbidden", "missing or invalid bearer token")
                return
            if path == "/v1/commands" and method == "GET":
                self._send(200, commands.dumps(commands.dispatch("list", {}, surface="api")))
                return
            match = _ROUTE.match(path)
            if not match:
                self._refuse(404, "unknown_command", f"no route for {path}")
                return
            name = match.group(1)
            cmd = commands.COMMANDS.get(name)
            if cmd is None:
                # Goes through dispatch so the refusal is logged like every other call.
                env = commands.dispatch(name, {}, surface="api")
                self._send(404, commands.dumps(env))
                return
            try:
                if method == "GET":
                    if not cmd.read_only:
                        self._refuse(405, "forbidden", f'"{name}" changes state — use POST', name)
                        return
                    params = commands.coerce_pairs(name, dict(parse_qsl(url.query)))
                else:
                    params = self._read_json()
            except commands.CommandError as exc:
                self._refuse(413 if "too large" in exc.message else 400, exc.code, exc.message, name)
                return
            env = commands.dispatch(name, params, surface="api")
            code = (env["error"] or {}).get("code")
            self._send(200 if env["ok"] else _STATUS.get(code, 500), commands.dumps(env))

        def _body_length(self) -> int:
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get("Transfer-Encoding") is not None or len(lengths) > 1:
                raise commands.CommandError("bad_params", "unsupported or ambiguous request framing")
            text = lengths[0].strip() if lengths else "0"
            if not text.isascii() or not text.isdecimal():
                raise commands.CommandError("bad_params", "bad Content-Length")
            if len(text) > 12 or int(text) > MAX_BODY_BYTES:
                raise commands.CommandError("bad_params", "request body too large")
            return int(text)

        def _read_json(self) -> dict[str, Any]:
            if self.headers.get("Transfer-Encoding"):
                self.close_connection = True
                raise commands.CommandError("bad_params", "Transfer-Encoding is not supported")
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) > 1:
                self.close_connection = True
                raise commands.CommandError("bad_params", "ambiguous Content-Length")
            value = lengths[0].strip() if lengths else "0"
            try:
                if not value.isascii() or not value.isdecimal():
                    raise ValueError
                length = int(value)
            except ValueError:
                self.close_connection = True
                raise commands.CommandError("bad_params", "bad Content-Length") from None
            if length < 0:
                self.close_connection = True
                raise commands.CommandError("bad_params", "bad Content-Length")
            if length > MAX_BODY_BYTES:
                # Preserve a useful413 for clients already sending a body, but
                # never wait indefinitely for attacker-declared bytes.
                self.close_connection = True
                old_timeout = self.connection.gettimeout()
                try:
                    self.connection.settimeout(REJECT_DRAIN_TIMEOUT_S)
                    self.rfile.read(min(length, 4 * MAX_BODY_BYTES))
                except OSError:
                    pass  # Refused request: an incomplete/closed body is expected.
                finally:
                    try:
                        self.connection.settimeout(old_timeout)
                    except OSError:
                        pass  # The peer may already have closed the refused connection.
                raise commands.CommandError("bad_params", "request body too large")
            try:
                body = self.rfile.read(length) if length else b""
            except OSError:
                self.close_connection = True
                raise commands.CommandError("bad_params", "request body unavailable") from None
            if len(body) != length:
                self.close_connection = True
                raise commands.CommandError("bad_params", "incomplete request body")
            raw = body.decode("utf-8", "replace").strip()
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise commands.CommandError("bad_params", "body is not valid JSON") from None
            if not isinstance(parsed, dict):
                raise commands.CommandError("bad_params", "body must be a JSON object")
            return parsed

        def do_GET(self) -> None:  # noqa: N802 - http.server API
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle("POST")

        def _other(self) -> None:
            self._refuse(405, "forbidden", f"{self.command} not allowed")

        do_PUT = do_DELETE = do_PATCH = _other  # noqa: N815

    return Handler


def create_server(port: int = 0, token: str | None = None) -> ThreadingHTTPServer:
    """Build (without serving) a server bound to 127.0.0.1. `port=0` picks a free port."""
    server = BoundedHTTPServer((HOST, port), make_handler(token or load_token()))
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="soltui api", description="soltui HTTP API on 127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("SOLTUI_API_PORT", DEFAULT_PORT)))
    args = parser.parse_args(argv)
    server = create_server(args.port)
    print(f"soltui API on http://{HOST}:{server.server_address[1]}  token file: {token_path()}",
          file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

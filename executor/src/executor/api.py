"""HTTP surface: `executor api [--port N]`. Stdlib `http.server`; the same access model as extension/tools/api-server.js.

    GET  /v1/health            liveness, no auth
    GET  /v1/commands          the `list` envelope
    GET  /v1/<command>?a=1     read-only commands, args from the query string
    POST /v1/<command>         any command, args from a JSON object body

Command routes return the registry envelope exactly as `registry.dumps` renders it, so the body is byte-identical to
the CLI's output for the same call. Access, in the order it is applied:

* binds 127.0.0.1 only; there is deliberately no option to widen it;
* any request carrying an `Origin` or `Sec-Fetch-Site` header is refused (403): a web page can post to localhost, so
  a token alone is not enough. No CORS headers are ever sent;
* every route but /v1/health needs `Authorization: Bearer <token>`, compared with `hmac.compare_digest`. The token
  lives in `$EXECUTOR_HOME/api-token`, mode 600, created on first run;
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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from . import registry
from .config import home
from .errors import ExecutorError

HOST = "127.0.0.1"
DEFAULT_PORT = 8789
MAX_BODY_BYTES = 1024 * 1024

_ROUTE = re.compile(r"^/v1/([A-Za-z][A-Za-z0-9_.]*)$")
_STATUS = {
    "bad_params": 400,
    "unknown_command": 404,
    "forbidden": 403,
    "refused": 422,
    "failed": 500,
    "timeout": 504,
    "ambiguous": 409,
}


def token_path() -> Path:
    return home() / "api-token"


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
        server_version = "executor-api"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:  # request lines carry query values
            pass

        def _send(self, status: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.send_header("x-content-type-options", "nosniff")
            self.send_header("cache-control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _refuse(self, status: int, code: str, message: str, name: str = "") -> None:
            self._send(status, registry.dumps(registry.error_envelope(name, code, message)))

        def _handle(self, method: str) -> None:
            url = urlsplit(self.path)
            path = url.path.rstrip("/")
            if path == "/v1/health" and method == "GET":
                self._send(200, registry.dumps({"ok": True, "service": "executor", "commands": len(registry.COMMANDS)}))
                return
            if self.headers.get("Origin") or self.headers.get("Sec-Fetch-Site"):
                self._refuse(
                    403, "forbidden", "browser-originated requests are refused; use a CLI or server-side client"
                )
                return
            auth = self.headers.get("Authorization", "")
            bearer = auth[7:] if auth.startswith("Bearer ") else ""
            if not token_matches(bearer, token):
                self._refuse(401, "forbidden", "missing or invalid bearer token")
                return
            if path == "/v1/commands" and method == "GET":
                self._send(200, registry.dumps(registry.dispatch("list", {}, surface="api")))
                return
            match = _ROUTE.match(path)
            if not match:
                self._refuse(404, "unknown_command", f"no route for {path}")
                return
            name = match.group(1)
            cmd = registry.COMMANDS.get(name)
            if cmd is None:
                env = registry.dispatch(name, {}, surface="api")  # logged like every other call
                self._send(404, registry.dumps(env))
                return
            try:
                if method == "GET":
                    if not cmd.read_only:
                        self._refuse(405, "forbidden", f'"{name}" changes state; use POST', name)
                        return
                    params = registry.coerce_pairs(name, dict(parse_qsl(url.query)))
                else:
                    params = self._read_json()
            except ExecutorError as exc:
                self._refuse(413 if "too large" in exc.message else 400, exc.code, exc.message, name)
                return
            env = registry.dispatch(name, params, surface="api")
            code = (env["error"] or {}).get("code")
            self._send(200 if env["ok"] else _STATUS.get(code, 500), registry.dumps(env))

        def _read_json(self) -> dict[str, Any]:
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                raise ExecutorError("bad Content-Length", "bad_params") from None
            if length > MAX_BODY_BYTES:
                self.rfile.read(min(length, 4 * MAX_BODY_BYTES))  # drain (bounded) so the client reads the 413
                self.close_connection = True
                raise ExecutorError("request body too large", "bad_params")
            raw = self.rfile.read(length).decode("utf-8", "replace").strip() if length else ""
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
            except ValueError:
                raise ExecutorError("body is not valid JSON", "bad_params") from None
            if not isinstance(parsed, dict):
                raise ExecutorError("body must be a JSON object", "bad_params")
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
    server = ThreadingHTTPServer((HOST, port), make_handler(token or load_token()))
    server.daemon_threads = True
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="executor api", description="executor HTTP API on 127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("EXECUTOR_API_PORT", DEFAULT_PORT)))
    args = parser.parse_args(argv)
    server = create_server(args.port)
    print(f"executor API on http://{HOST}:{server.server_address[1]}  token file: {token_path()}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

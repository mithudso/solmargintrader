"""Read-only, loopback control room over the existing ecosystem owners.

``make_server`` binds before returning. The caller owns serving and shutdown, so
the supervisor can publish the actual ephemeral port without claiming liveness
before bind succeeds. This module never starts a recorder, worker, or order path.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from ecosystem import registration, runner

SCHEMA_VERSION = 1
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
}
SECRET_KEY = re.compile(
    r"secret|password|authorization|credential|private.?key|api.?key|token|signer",
    re.IGNORECASE,
)
MAX_RESPONSE = 8 * 1024 * 1024


def _redact(value, depth=0):
    """Bound JSON and redact credential-bearing fields before browser delivery."""
    if depth > 30:
        return "[unavailable]"
    if isinstance(value, dict):
        return {
            str(key): "[redacted]"
            if SECRET_KEY.search(str(key))
            else _redact(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item, depth + 1) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return "[unavailable]"


def _telemetry(home: Path, manager_home: Path | None, *, after=0, limit=100) -> dict:
    from ecosystem.telemetry import report

    return report(home, manager_home, after=after, limit=limit)


class ControlRoomServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False


def make_server(
    home: str | Path,
    manager_home: str | Path | None = None,
    *,
    port: int = 8768,
) -> ThreadingHTTPServer:
    """Bind a read-only HTTP server to 127.0.0.1; port 0 chooses a free port.

    GET/HEAD expose only bundled assets and owner-derived JSON. Host and Origin
    checks defend against DNS rebinding and cross-site reads. No CORS is enabled.
    Missing or unreadable owner data returns an explicit unavailable response.
    """
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_ui_port")
    home = Path(home).expanduser().absolute()
    manager_home = (
        Path(manager_home).expanduser().absolute() if manager_home is not None else None
    )
    assets = Path(__file__).with_name("web")
    started = time.monotonic()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        server_version = "SolControlRoom/1"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, format, *args):
            # Request targets and headers are untrusted and may contain secrets.
            return

        def _send(self, status, raw, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
            )
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

        def _json(self, status, data=None, error=None):
            body = {
                "schema_version": SCHEMA_VERSION,
                "ok": error is None,
                "data": _redact(data),
                "error": error,
            }
            raw = json.dumps(body, allow_nan=False, separators=(",", ":")).encode()
            if len(raw) > MAX_RESPONSE:
                self._json(503, error="owner_response_too_large")
                return
            self._send(status, raw, "application/json; charset=utf-8")

        def _authorized(self):
            actual_port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}
            host_values = self.headers.get_all("Host", [])
            origin_values = self.headers.get_all("Origin", [])
            if (
                self.client_address[0] != "127.0.0.1"
                or len(host_values) != 1
                or host_values[0] not in hosts
                or len(origin_values) > 1
                or (origin_values and origin_values[0] != f"http://{host_values[0]}")
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                self._json(403, error="local_origin_required")
                return False
            return True

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self._authorized():
                return
            if len(self.path) > 4096:
                self._json(414, error="request_target_too_long")
                return
            try:
                target = urlsplit(self.path)
                if target.scheme or target.netloc or target.fragment:
                    raise ValueError
                query = parse_qs(
                    target.query, keep_blank_values=True, strict_parsing=True
                )
                if (
                    target.path not in ("/api/registrations", "/api/telemetry")
                    and query
                ):
                    raise ValueError
                if target.path in STATIC:
                    name, content_type = STATIC[target.path]
                    self._send(200, (assets / name).read_bytes(), content_type)
                elif target.path == "/favicon.ico":
                    self._send(204, b"", "image/x-icon")
                elif target.path == "/health":
                    self._json(
                        200,
                        {
                            "status": "listening",
                            "read_only": True,
                            "bind": "127.0.0.1",
                            "port": self.server.server_address[1],
                            "uptime_seconds": round(time.monotonic() - started, 3),
                            "owner_health": "see_status_and_telemetry",
                        },
                    )
                elif target.path == "/api/status":
                    self._json(200, runner.status(home))
                elif target.path == "/api/registrations":
                    if set(query) - {"limit", "after"} or any(
                        len(values) != 1 for values in query.values()
                    ):
                        raise ValueError
                    limit = query.get("limit", ["100"])[0]
                    if not re.fullmatch(r"[1-9][0-9]{0,3}", limit):
                        raise ValueError
                    limit = int(limit)
                    if limit > 1000:
                        raise ValueError
                    after = query.get("after", [""])[0]
                    if after and str(UUID(after)) != after:
                        raise ValueError
                    self._json(
                        200,
                        registration.read_registrations(home, limit=limit, after=after),
                    )
                elif target.path == "/api/telemetry":
                    if set(query) - {"limit", "after"} or any(
                        len(values) != 1 for values in query.values()
                    ):
                        raise ValueError
                    limit = query.get("limit", ["100"])[0]
                    after = query.get("after", ["0"])[0]
                    if (
                        not re.fullmatch(r"[1-9][0-9]{0,3}", limit)
                        or int(limit) > 1000
                        or not re.fullmatch(r"0|[1-9][0-9]{0,17}", after)
                    ):
                        raise ValueError
                    self._json(
                        200,
                        _telemetry(
                            home, manager_home, after=int(after), limit=int(limit)
                        ),
                    )
                else:
                    self._json(404, error="not_found")
            except ValueError:
                self._json(400, error="invalid_request_or_owner_data")
            except (OSError, ImportError, RuntimeError):
                self._json(503, error="owner_data_unavailable")
            except Exception:  # noqa: BLE001 - fixed public owner boundary, never echo input
                # Owner exceptions never become an HTTP traceback or raw log.
                self._json(503, error="owner_data_unavailable")

        def _read_only(self):
            if self._authorized():
                self._json(405, error="read_only_interface")

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only

    return ControlRoomServer(("127.0.0.1", port), Handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--manager-home", type=Path)
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args(argv)
    try:
        server = make_server(args.home, args.manager_home, port=args.port)
    except (ValueError, OSError):
        print("control_room_bind_failed", file=sys.stderr)
        return 1
    with server:
        print(
            json.dumps(
                {
                    "status": "listening",
                    "url": f"http://127.0.0.1:{server.server_address[1]}",
                    "read_only": True,
                }
            ),
            flush=True,
        )
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Local paper controls and observability over the established ecosystem owners.

``make_server`` binds before returning. The caller owns serving and shutdown, so
the supervisor can publish the actual ephemeral port without claiming liveness
before bind succeeds. This module never starts a recorder, worker, or order path.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from ecosystem import __version__, registration, runner

SCHEMA_VERSION = 1
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/oracle-chart.js": ("oracle-chart.js", "text/javascript; charset=utf-8"),
    "/tradingview-chart.js": ("tradingview-chart.js", "text/javascript; charset=utf-8"),
    "/lightweight-charts.mjs": ("vendor/lightweight-charts-5.2.1.mjs", "text/javascript; charset=utf-8"),
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


def _component_health(home: Path, manager_home: Path | None) -> dict:
    """Read the compact collector contract without starting component owners."""
    from botmanager.machine_health import check

    return check(home=manager_home, ecosystem_home=home)


def _availability_ready(snapshot: dict) -> bool:
    # Source freshness and research certification are separate from server
    # availability. Unknown critical owners never produce a ready response.
    components = snapshot.get("components", {})
    return isinstance(components, dict) and all(
        isinstance(components.get(name), dict)
        and components[name].get("state") == "up"
        and components[name].get("ready") is True
        for name in ("suite", "manager", "control_room")
    )


class ControlRoomServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False

    def server_close(self):
        if hasattr(self, "controls"):
            self.controls.close()
        if getattr(self, "swap_server", None) is not None:
            self.swap_server.shutdown()
            self.swap_server.server_close()
        super().server_close()


def make_server(
    home: str | Path,
    manager_home: str | Path | None = None,
    *,
    port: int = 8768,
) -> ThreadingHTTPServer:
    """Bind paper controls to loopback, retaining strict origin isolation.

    GET/HEAD expose bundled assets and owner-derived JSON. Host and Origin
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
    csrf_nonce = secrets.token_urlsafe(32)
    swap_lock = threading.Lock()

    from .control import ControlPlane

    controls = ControlPlane(home, manager_home)
    try:
        controls.register_legacy()
    except BaseException:
        controls.close()
        raise

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
                "default-src 'self'; script-src 'self'; "
                "style-src 'self' 'sha256-3pRED1tOXas1FXFoPb9TGCjmYe9XQsmO9OV23khV2nY='; "
                "style-src-attr 'unsafe-inline'; "
                "connect-src 'self'; img-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'none'; "
                "frame-src http://127.0.0.1:* https://www.tradingview-widget.com",
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
                    target.path
                    not in (
                        "/api/status",
                        "/api/control",
                        "/api/registrations",
                        "/api/telemetry",
                        "/api/actions",
                        "/api/analytics",
                        "/api/oracle",
                        "/api/wiki",
                        "/api/wiki/page",
                        "/api/logs",
                    )
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
                            "read_only": False,
                            "scope": "paper_controls",
                            "orders_available": False,
                            "control_instance": self.server.control_instance,
                            "control_home": str(home),
                            "manager_home": str(controls.manager_home),
                            "ecosystem_version": __version__,
                            "bind": "127.0.0.1",
                            "port": self.server.server_address[1],
                            "uptime_seconds": round(time.monotonic() - started, 3),
                            "owner_health": "see_status_and_telemetry",
                        },
                    )
                elif target.path == "/healthz":
                    self._json(200, {"alive": True, "scope": "control_room_process"})
                elif target.path in ("/api/health", "/readyz", "/metrics"):
                    measurement = _component_health(home, manager_home)
                    if target.path == "/metrics":
                        from botmanager.machine_health import prometheus

                        self._send(
                            200,
                            prometheus(measurement).encode("utf-8"),
                            "text/plain; version=0.0.4; charset=utf-8",
                        )
                    elif target.path == "/readyz":
                        ready = _availability_ready(measurement)
                        self._json(
                            200 if ready else 503,
                            {**measurement, "availability_ready": ready},
                            error=None if ready else "components_not_ready",
                        )
                    else:
                        self._json(200, measurement)
                elif target.path == "/api/status":
                    values = self._query(query, {"run_id"})
                    self._json(
                        200,
                        runner.status(controls.experiment_home(values.get("run_id"))),
                    )
                elif target.path == "/api/session":
                    self._json(
                        200,
                        {
                            "csrf_nonce": csrf_nonce,
                            "scope": "paper_controls",
                            "expires_when": "server_restart",
                        },
                    )
                elif target.path == "/api/control":
                    values = self._query(query, {"run_id"})
                    snapshot = controls.snapshot(values.get("run_id"))
                    snapshot["servers"].insert(
                        0,
                        {
                            "id": "control",
                            "label": "Control server",
                            "owner": "ecosystem.web",
                            "state": "running",
                            "running": True,
                            "pid": os.getpid(),
                            "version": __version__,
                            "heartbeat_at": time.time(),
                            "uptime_seconds": time.monotonic() - started,
                            "actions": [],
                        },
                    )
                    self._json(200, snapshot)
                elif target.path == "/api/openapi":
                    self._send(
                        200,
                        Path(__file__)
                        .with_name("api")
                        .joinpath("control.openapi.json")
                        .read_bytes(),
                        "application/json",
                    )
                elif target.path == "/api/logs":
                    from .observability import logs

                    values = self._query(query, {"server", "limit", "run_id"})
                    self._json(
                        200,
                        logs(
                            controls.experiment_home(values.get("run_id")),
                            values.get("server", "pipeline"),
                            limit=int(values.get("limit", "100")),
                            manager_home=manager_home,
                        ),
                    )
                elif target.path == "/api/actions":
                    values = self._query(query, {"id"})
                    self._json(200, controls.actions(values.get("id")))
                elif target.path == "/api/analytics":
                    from .performance import report

                    values = self._query(query, {"bot_id", "run_id"})
                    self._json(
                        200,
                        report(
                            controls.experiment_home(values.get("run_id")),
                            values.get("bot_id"),
                        ),
                    )
                elif target.path == "/api/oracle":
                    from .votes import report

                    values = self._query(query, {"instrument", "run_id", "interval", "strategy"})
                    self._json(
                        200,
                        report(
                            controls.experiment_home(values.get("run_id")),
                            values.get("instrument", "SOL/USD"),
                            interval=values.get("interval"),
                            strategy=values.get("strategy"),
                        ),
                    )
                elif target.path in {"/api/wiki", "/api/wiki/page"}:
                    from . import wiki

                    values = self._query(
                        query,
                        {"id"}
                        if target.path.endswith("/page")
                        else {"q", "limit", "offset"},
                    )
                    if target.path.endswith("/page"):
                        result = wiki.page(values.get("id", ""))
                    else:
                        result = wiki.catalog(
                            values.get("q", ""),
                            int(values.get("limit", "100")),
                            int(values.get("offset", "0")),
                        )
                    self._json(200, result)
                elif target.path == "/api/swap":
                    from . import swap_web, swaps

                    with swap_lock:
                        if self.server.swap_server is None:
                            child = swap_web.make_server(port=0)
                            thread = threading.Thread(
                                target=child.serve_forever, daemon=True
                            )
                            thread.start()
                            self.server.swap_server = child
                    self._json(
                        200,
                        {
                            "url": f"http://127.0.0.1:{self.server.swap_server.server_port}",
                            "config": swaps.config(),
                            "scope": "manual_wallet_swap",
                        },
                    )
                elif target.path == "/api/registrations":
                    if set(query) - {"limit", "after", "run_id"} or any(
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
                        registration.read_registrations(
                            controls.experiment_home(query.get("run_id", [None])[0]),
                            limit=limit,
                            after=after,
                        ),
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
            except (ValueError, TypeError):
                self._json(400, error="invalid_request_or_owner_data")
            except (OSError, ImportError, RuntimeError):
                self._json(503, error="owner_data_unavailable")
            except Exception:  # noqa: BLE001 - fixed public owner boundary, never echo input
                # Owner exceptions never become an HTTP traceback or raw log.
                self._json(503, error="owner_data_unavailable")

        def _query(self, query, allowed):
            if set(query) - allowed or any(
                len(values) != 1 for values in query.values()
            ):
                raise ValueError("invalid_query")
            return {key: values[0] for key, values in query.items()}

        def do_POST(self):
            if not self._authorized():
                return
            if self.path != "/api/actions":
                self._json(404, error="not_found")
                return
            if self.headers.get(
                "Origin"
            ) != f"http://{self.headers.get('Host')}" or not secrets.compare_digest(
                self.headers.get("X-Sol-CSRF", ""), csrf_nonce
            ):
                self._json(403, error="control_session_required")
                return
            sizes = self.headers.get_all("Content-Length", [])
            if (
                self.headers.get("Transfer-Encoding")
                or len(sizes) != 1
                or not re.fullmatch(r"[1-9][0-9]{0,5}", sizes[0])
                or int(sizes[0]) > 65536
                or self.headers.get("Content-Type", "").split(";", 1)[0]
                != "application/json"
            ):
                self._json(400, error="invalid_action_body")
                return
            try:
                raw = self.rfile.read(int(sizes[0]))
                if len(raw) != int(sizes[0]):
                    raise ValueError
                body = json.loads(raw)
                if (
                    not isinstance(body, dict)
                    or set(body) != {"action", "request_id", "params"}
                    or not isinstance(body["action"], str)
                ):
                    raise ValueError
                action, created = controls.submit(
                    body["action"], body["request_id"], body["params"]
                )
                self._json(202 if created else 200, action)
            except (ValueError, TypeError, UnicodeError):
                self._json(400, error="invalid_action_or_conflicting_request")
            except (OSError, sqlite3.Error, TimeoutError):
                self._json(503, error="control_store_unavailable")

        def _read_only(self):
            if self._authorized():
                self._json(405, error="read_only_interface")

        do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _read_only

    try:
        server = ControlRoomServer(("127.0.0.1", port), Handler)
    except BaseException:
        controls.close()
        raise
    server.controls = controls
    server.control_instance = str(uuid4())
    server.swap_server = None
    return server


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, required=True)
    parser.add_argument("--manager-home", type=Path)
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument(
        "--persistent",
        action="store_true",
        help="Run the separately owned control service.",
    )
    args = parser.parse_args(argv)
    from . import ui_service

    home = args.home.expanduser().absolute()
    try:
        with (
            ui_service.lock(home),
            make_server(home, args.manager_home, port=args.port) as server,
        ):
            url = f"http://127.0.0.1:{server.server_port}"
            ui_service.checkpoint(home, server.control_instance, url, manager_home=args.manager_home)
            print(
                json.dumps(
                    {
                        "status": "listening",
                        "url": url,
                        "read_only": False,
                        "scope": "paper_controls",
                    }
                ),
                flush=True,
            )
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
            finally:
                ui_service.clear_checkpoint(home, server.control_instance)
        return 0
    except (ValueError, OSError):
        print("control_room_unavailable_or_owned", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

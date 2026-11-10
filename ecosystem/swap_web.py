"""A public-only loopback origin for manually loaded third-party wallet UI."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .swaps import config


class SwapServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False


def make_server(*, port: int = 0) -> ThreadingHTTPServer:
    """Bind an isolated public UI; no owner/session/path argument is accepted."""
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("invalid_swap_port")
    assets = Path(__file__).with_name("web")

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"
        server_version = "JupiterManualUI/1"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, format, *args):
            return  # Untrusted request targets and headers never enter a log.

        def _send(self, status, raw, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
            )
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; script-src 'self' https://plugin.jup.ag; "
                "style-src 'self' 'unsafe-inline' https:; img-src 'self' https: data:; "
                "font-src https: data:; connect-src 'self' https: wss:; "
                "frame-src https:; worker-src blob:; object-src 'none'; base-uri 'none'; "
                "form-action 'none'; frame-ancestors http://127.0.0.1:* http://localhost:*",
            )
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

        def _json(self, status, data=None, error=None):
            raw = json.dumps(
                {
                    "schema_version": 1,
                    "ok": error is None,
                    "data": data,
                    "error": error,
                },
                allow_nan=False,
            ).encode()
            self._send(status, raw, "application/json; charset=utf-8")

        def _authorized(self):
            hosts = {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }
            values = self.headers.get_all("Host", [])
            origins = self.headers.get_all("Origin", [])
            if (
                self.client_address[0] != "127.0.0.1"
                or len(values) != 1
                or values[0] not in hosts
                or len(origins) > 1
                or origins
                and origins[0] != f"http://{values[0]}"
                or self.headers.get("Sec-Fetch-Site") == "cross-site"
            ):
                self._json(403, error="local_swap_origin_required")
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
                    target.query,
                    keep_blank_values=True,
                    strict_parsing=True,
                    max_num_fields=4,
                )
                if target.path in ("/", "/config"):
                    if set(query) - {"asset"} or any(
                        len(values) != 1 for values in query.values()
                    ):
                        raise ValueError
                    public = config(query.get("asset", ["SOL"])[0])
                    if target.path == "/config":
                        self._json(200, public)
                    else:
                        self._send(
                            200,
                            (assets / "swap.html").read_bytes(),
                            "text/html; charset=utf-8",
                        )
                elif query:
                    raise ValueError
                elif target.path == "/swap.js":
                    self._send(
                        200,
                        (assets / "swap.js").read_bytes(),
                        "text/javascript; charset=utf-8",
                    )
                elif target.path == "/health":
                    self._json(
                        200,
                        {
                            "status": "listening",
                            "isolated_origin": True,
                            "public_configuration_only": True,
                            "owner_controls": False,
                            "server_can_sign_or_submit": False,
                            "port": self.server.server_port,
                        },
                    )
                elif target.path == "/favicon.ico":
                    self._send(204, b"", "image/x-icon")
                else:
                    self._json(404, error="not_found")
            except ValueError:
                self._json(400, error="invalid_swap_request")
            except OSError:
                self._json(503, error="swap_ui_unavailable")

        def _read_only(self):
            if self._authorized():
                self._json(405, error="public_swap_ui_only")

        do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_TRACE = _read_only

    return SwapServer(("127.0.0.1", port), Handler)

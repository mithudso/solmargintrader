"""TradingView signal reception with explicitly selected venue dispatch."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import signal
import sqlite3
import threading
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .http_limits import DeadlineReader
from .webhook_orders import database as open_database
from .webhook_orders import process_one, recover_planning

MAX_BODY = 4096
HTTP_TIMEOUT = 5
MAX_HTTP_WORKERS = 16
EVENT_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
SYMBOL = re.compile(r"[A-Z0-9:._/-]{1,80}\Z")


class _WebhookHTTPServer(ThreadingHTTPServer):
    """Refuse excess unauthenticated sockets before creating request threads."""

    def __init__(self, *args, **kwargs):
        self._request_slots = threading.BoundedSemaphore(MAX_HTTP_WORKERS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self._request_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._request_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._request_slots.release()


def accept_signal(
    database: Path,
    body: bytes,
    secret: str,
    *,
    now: float | None = None,
    mode: str = "inbox",
    portfolio_id: str | None = None,
) -> str:
    """Authenticate, validate and durably deduplicate a sender-provided event.

    The secret is never stored. A conflicting reuse of an event id is refused.
    """
    if mode != "inbox" and not portfolio_id:
        raise ValueError("portfolio_required")
    if mode not in ("inbox", "dry-run", "live"):
        raise ValueError("invalid_mode")
    if not secret or len(secret) < 32 or len(body) > MAX_BODY:
        raise ValueError("invalid_request")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_json_key")
            result[key] = value
        return result

    try:
        msg = json.loads(body, object_pairs_hook=unique)
    except (ValueError, UnicodeDecodeError, RecursionError):
        raise ValueError("invalid_request") from None
    if not isinstance(msg, dict) or set(msg) != {
        "secret",
        "event_id",
        "symbol",
        "side",
        "timestamp",
    }:
        raise ValueError("invalid_request")
    supplied = msg.pop("secret")
    if not isinstance(supplied, str) or not hmac.compare_digest(
        supplied.encode(), secret.encode()
    ):
        raise ValueError("invalid_request")
    event_id, symbol, side, timestamp = (
        msg[k] for k in ("event_id", "symbol", "side", "timestamp")
    )
    now = time.time() if now is None else now
    if isinstance(timestamp, str):
        try:
            parsed = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=UTC
            )
            timestamp = int(parsed.timestamp())
        except (ValueError, OverflowError, OSError):
            raise ValueError("invalid_request") from None
    if (
        not isinstance(event_id, str)
        or not EVENT_ID.fullmatch(event_id)
        or not isinstance(symbol, str)
        or not SYMBOL.fullmatch(symbol)
        or side not in ("buy", "sell")
        or type(timestamp) is not int
        or not now - 300 <= timestamp <= now + 30
    ):
        raise ValueError("invalid_request")
    msg["timestamp"] = timestamp
    digest = hashlib.sha256(
        json.dumps(msg, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    with open_database(database) as db, db:
        cursor = db.execute(
            "INSERT OR IGNORE INTO signals (event_id,digest,symbol,side,timestamp,status,mode,portfolio_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                digest,
                symbol,
                side,
                timestamp,
                "received" if mode == "inbox" else "queued",
                mode,
                portfolio_id,
            ),
        )
        if cursor.rowcount:
            return "received"
        old = db.execute(
            "SELECT digest FROM signals WHERE event_id = ?", (event_id,)
        ).fetchone()
        if old is None or not hmac.compare_digest(old[0], digest):
            raise ValueError("invalid_request")
        return "duplicate"


def serve(
    database: Path,
    secret: str,
    port: int,
    *,
    venue=None,
    portfolio_id=None,
    live=False,
    processor=process_one,
    recover=recover_planning,
) -> None:
    if len(secret) < 32 or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")

    if live and venue is None or venue is not None and not portfolio_id:
        raise ValueError("invalid_venue_configuration")
    mode = "live" if live else "dry-run" if venue is not None else "inbox"
    stop = threading.Event()
    failed = threading.Event()
    recover(database)

    def work():
        try:
            while not stop.is_set():
                processor(
                    database,
                    venue,
                    portfolio_id,
                    allow_live=live,
                    enabled=lambda: (
                        not stop.is_set() and not (database.parent / "KILL").exists()
                    ),
                )
                stop.wait(1)
        except Exception:  # noqa: BLE001 - stop reception if any dispatch worker dies
            failed.set()
            stop.set()

    class Handler(BaseHTTPRequestHandler):
        # StreamRequestHandler applies this before reading the request line/headers.
        timeout = HTTP_TIMEOUT

        def setup(self):
            super().setup()
            self.rfile = DeadlineReader(self.rfile, self.connection, HTTP_TIMEOUT)

        def log_message(self, format, *args):
            return  # Alert credentials must never enter access logs.

        def do_POST(self):
            try:
                if self.path != "/tradingview" or self.headers.get("Transfer-Encoding"):
                    raise ValueError("invalid_request")
                length = int(self.headers.get("Content-Length", ""))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("invalid_request")
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("invalid_request")
                status = accept_signal(
                    database, body, secret, mode=mode, portfolio_id=portfolio_id
                )
                code = 202
                result = {
                    "status": status,
                    "execution": "unavailable" if venue is None else mode,
                }
            except (ValueError, UnicodeError, TimeoutError):
                code, result = 400, {"error": "invalid_request"}
            except (OSError, sqlite3.Error):
                code, result = 503, {"error": "inbox_unavailable"}
            payload = json.dumps(result, separators=(",", ":")).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = _WebhookHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.timeout = 0.5
    old = {}
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            old[sig] = signal.signal(sig, lambda *_: stop.set())
    worker = threading.Thread(target=work, daemon=True) if venue is not None else None
    try:
        if worker:
            worker.start()
        while not stop.is_set():
            server.handle_request()
    finally:
        stop.set()
        server.server_close()
        if worker:
            worker.join(35)
        for sig, handler in old.items():
            signal.signal(sig, handler)
    if failed.is_set():
        raise RuntimeError("venue_worker_failed")

"""Local TradingView signal inbox. Receiving a signal never submits an order."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import closing
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 4096
EVENT_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
SYMBOL = re.compile(r"[A-Z0-9:._/-]{1,80}\Z")


def accept_signal(
    database: Path, body: bytes, secret: str, *, now: float | None = None
) -> str:
    """Authenticate, validate and durably deduplicate a sender-provided event.

    The secret is never stored. A conflicting reuse of an event id is refused.
    """
    if not secret or len(secret) < 32 or len(body) > MAX_BODY:
        raise ValueError("invalid_request")
    try:
        msg = json.loads(body)
    except (ValueError, UnicodeDecodeError):
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
    digest = hashlib.sha256(
        json.dumps(msg, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    database.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with closing(sqlite3.connect(database, timeout=5)) as db, db:
        os.chmod(database, 0o600)
        db.execute(
            "CREATE TABLE IF NOT EXISTS signals (event_id TEXT PRIMARY KEY, digest TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, timestamp INTEGER NOT NULL, status TEXT NOT NULL)"
        )
        cursor = db.execute(
            "INSERT OR IGNORE INTO signals VALUES (?, ?, ?, ?, ?, 'received')",
            (event_id, digest, symbol, side, timestamp),
        )
        if cursor.rowcount:
            return "received"
        old = db.execute(
            "SELECT digest FROM signals WHERE event_id = ?", (event_id,)
        ).fetchone()
        if old is None or not hmac.compare_digest(old[0], digest):
            raise ValueError("invalid_request")
        return "duplicate"


def serve(database: Path, secret: str, port: int) -> None:
    if len(secret) < 32 or not 1 <= port <= 65535:
        raise ValueError("invalid_configuration")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return  # Alert credentials must never enter access logs.

        def do_POST(self):
            try:
                if self.path != "/tradingview" or self.headers.get("Transfer-Encoding"):
                    raise ValueError("invalid_request")
                length = int(self.headers.get("Content-Length", ""))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("invalid_request")
                self.connection.settimeout(5)
                body = self.rfile.read(length)
                if len(body) != length:
                    raise ValueError("invalid_request")
                status = accept_signal(database, body, secret)
                code = 202
                result = {"status": status, "execution": "unavailable"}
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

    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()

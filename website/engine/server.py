"""Bearer-authenticated adapter to canonical local research engines.

Run behind an HTTPS private gateway. The edge website must never forward a
browser-selected URL or expose the local control room through this service.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import io
import json
import logging
import math
import os
import threading
import time
from collections import deque
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

COINS = ("SOL", "BTC", "ETH", "ZEC")
INTERVALS = ("1m", "5m", "15m", "1h", "6h", "1d")
MAX_BARS = 6000
MAX_CACHE_BYTES = 32 * 1024 * 1024
MAX_BODY = 4096
REQUEST_SECONDS = 10
MAX_HANDLERS = 16


class DeadlineReader:
    """Keep request parsing within one deadline even if bytes keep arriving."""

    def __init__(self, source, connection, *, clock=time.monotonic):
        self.source, self.connection, self.clock = source, connection, clock
        self.deadline = clock() + REQUEST_SECONDS

    def read(self, size=-1):
        if size < 0:
            raise ValueError("bounded request read required")
        data = bytearray()
        while len(data) < size:
            remaining = self.deadline - self.clock()
            if remaining <= 0:
                raise TimeoutError("request deadline exceeded")
            self.connection.settimeout(remaining)
            chunk = self.source.read(1)
            if not chunk:
                break
            data.extend(chunk)
        return bytes(data)

    def readline(self, size=-1):
        data = bytearray()
        limit = 65537 if size < 0 else size
        while len(data) < limit:
            byte = self.read(1)
            if not byte:
                break
            data.extend(byte)
            if byte == b"\n":
                break
        return bytes(data)

    def close(self):
        self.source.close()

LOGGER = logging.getLogger(__name__)
OPERATIONS = {
    "/v1/strategies": "strategies",
    "/v1/oracle": "oracle",
    "/v1/backtests": "backtests",
    "/health": "health",
    "/v1/jobs": "jobs",
    "/v1/signals": "signals",
}


class RequestError(ValueError):
    """A public symbolic error, never an upstream exception string."""


def finite(value):
    return type(value) is int or (type(value) is float and math.isfinite(value))


def record_event(event, *, level=logging.INFO, **fields):
    """Log fixed event metadata; callers must exclude raw inputs and exception text."""
    LOGGER.log(level, json.dumps({"event": event, **fields}, separators=(",", ":")))


def json_safe(value):
    """Metrics can be undefined; serialize them as null, never JSON NaN."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def catalogue():
    from backtester.core.strategies import REGISTRY
    from backtester.core.strategy_cards import load_all

    cards = {c.registry_key: c for c in load_all().values() if c.registry_key}
    rows = []
    for key in sorted(REGISTRY):
        card = cards.get(key)
        rows.append(
            {
                "id": key,
                "name": card.name if card else key.replace("_", " ").title(),
                "status": card.status if card else "implemented",
                "summary": card.summary
                if card
                else "Registered canonical exposure strategy.",
                "runner": "backtester.cli",
                "kind": "exposure-strategy",
            }
        )
    return {
        "strategies": rows,
        "scope": "canonical exposure-strategy registry; ladder, pair and event-replay runners remain separate",
    }


def choose_top(snapshot, coin):
    """Rank only current strategies admitted by the canonical voting policy."""
    included = {
        r["strategy_id"] for r in snapshot.get("aggregate", {}).get("included", [])
    }
    rows = []
    for row in snapshot.get("strategies", []):
        score = row.get("confidence_percent")
        direction = row.get("direction")
        if direction not in (-1, 0, 1) or type(direction) is not int:
            direction = None
        rows.append(
            {
                "id": row["strategy_id"],
                "name": row["strategy_id"].replace("_", " ").title(),
                "direction": {-1: "down", 0: "flat", 1: "up"}.get(direction),
                "score": score,
                "sampleSize": row.get("resolved", 0),
                "asOf": row.get("issued_at"),
                "expiresAt": row.get("expires_at"),
                "eligible": row["strategy_id"] in included,
            }
        )
    eligible = [
        r for r in rows if r["eligible"] and finite(r["score"]) and r["direction"]
    ]
    eligible.sort(key=lambda r: (-r["score"], -r["sampleSize"], r["id"]))
    available = snapshot.get("status") == "available" and bool(eligible)
    return {
        "coin": coin,
        "instrument": snapshot.get("instrument"),
        "status": "available" if available else "unavailable",
        "topStrategy": eligible[0] if available else None,
        "strategies": rows,
        "reason": None
        if available
        else snapshot.get("aggregate", {}).get("reason", "no_eligible_strategy"),
        "asOf": snapshot.get("as_of"),
        "horizonSeconds": snapshot.get("horizon_seconds"),
        "policyHash": snapshot.get("policy_hash"),
        "scoreSemantics": "prospective directional accuracy percent, not profit probability",
        "ranking": "accuracy descending, resolved sample size descending, strategy id ascending",
        "tradable": False,
    }


class Analysis:
    def __init__(self, data_dir: Path, oracle_dir: Path, *, oracle_quote="USD"):
        self.data_dir = data_dir.resolve()
        self.oracle_dir = oracle_dir.resolve()
        if oracle_quote not in ("USD", "USDC", "USDT"):
            raise ValueError("unsupported_oracle_quote")
        self.oracle_quote = oracle_quote
        self.slot = threading.BoundedSemaphore(1)

    def oracle(self, coin, now=None):
        if coin not in COINS:
            raise RequestError("unsupported_coin")
        path = self.oracle_dir / coin / "history.sqlite3"
        if path.is_symlink() or not path.is_file():
            return {
                "coin": coin,
                "status": "unavailable",
                "topStrategy": None,
                "strategies": [],
                "reason": "oracle_archive_unavailable",
            }
        from oracle.reader import ReadOnlyOracle

        try:
            reader = ReadOnlyOracle(path, instrument=f"{coin}/{self.oracle_quote}")
            return choose_top(reader.predictions(now=now), coin)
        except (ValueError, OSError) as exc:
            record_event(
                "analysis_oracle_unavailable",
                level=logging.WARNING,
                coin=coin,
                error_type=type(exc).__name__,
            )
            return {
                "coin": coin,
                "status": "unavailable",
                "topStrategy": None,
                "strategies": [],
                "reason": "oracle_evidence_unavailable",
            }

    def backtest(self, body):
        if not isinstance(body, dict) or set(body) - {
            "coin",
            "strategy",
            "interval",
            "capital",
            "leverage",
        }:
            raise RequestError("invalid_backtest_request")
        coin, strategy = body.get("coin"), body.get("strategy")
        interval, capital, leverage = (
            body.get("interval", "1h"),
            body.get("capital", 10000),
            body.get("leverage", 1),
        )
        if coin not in COINS or interval not in INTERVALS:
            raise RequestError("unsupported_market")
        if (
            not finite(capital)
            or not 1 <= capital <= 1_000_000
            or not finite(leverage)
            or not 1 <= leverage <= 10
        ):
            raise RequestError("invalid_capital_or_leverage")
        from backtester.core.strategies import REGISTRY, build

        if not isinstance(strategy, str) or strategy not in REGISTRY:
            raise RequestError("unsupported_strategy")
        if not self.slot.acquire(blocking=False):
            raise RequestError("engine_busy")
        try:
            return self._run(coin, strategy, interval, capital, leverage, build)
        finally:
            self.slot.release()

    def _run(self, coin, strategy, interval, capital, leverage, build):
        import pandas as pd

        from backtester.core.data import checksum_frame, frame_to_arrays, validate_bars
        from backtester.core.engine import EngineConfig, run_backtest
        from backtester.core.types import INTERVAL_SECONDS, CostConfig, Mode

        path = self.data_dir / f"{coin}_{interval}.csv"
        if path.is_symlink() or not path.is_file():
            raise RequestError("cached_history_unavailable")
        if path.stat().st_size > MAX_CACHE_BYTES:
            raise RequestError("history_cache_too_large")
        with path.open("rb") as source:
            raw = source.read(MAX_CACHE_BYTES + 1)
        if len(raw) > MAX_CACHE_BYTES:
            raise RequestError("history_cache_too_large")
        digest = hashlib.sha256(raw)
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        columns = ("timestamp", "open", "high", "low", "close", "volume")
        if reader.fieldnames != list(columns):
            raise RequestError("invalid_cached_history")
        try:
            cutoff = time.time()
            rows = deque(maxlen=MAX_BARS)
            for row in reader:
                timestamp = float(row["timestamp"])
                if not math.isfinite(timestamp):
                    raise ValueError("invalid timestamp")
                if timestamp + INTERVAL_SECONDS[interval] <= cutoff:
                    rows.append(row)
            if len(rows) < 2:
                raise RequestError("insufficient_history")
            numeric = pd.DataFrame(rows).apply(pd.to_numeric)
            numeric = numeric[
                numeric.timestamp + INTERVAL_SECONDS[interval] <= time.time()
            ]
            frame = validate_bars(numeric, interval, strict_gaps=True)
            config = EngineConfig(
                mode=Mode.PERP if leverage > 1 else Mode.SPOT,
                leverage=leverage,
                initial_capital=capital,
                interval=interval,
                fill_delay=1,
                allow_short=leverage > 1,
                costs=CostConfig(),
            )
            result = run_backtest(build(strategy), frame_to_arrays(frame), config)
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            raise RequestError("history_or_strategy_not_usable") from exc
        # Keep response bounded; chart downsampling never changes engine metrics.
        step = max(1, math.ceil(len(result.equity) / 500))
        indices = list(range(0, len(result.equity), step))
        if indices[-1] != len(result.equity) - 1:
            indices.append(len(result.equity) - 1)
        return json_safe(
            {
                "status": "complete",
                "coin": coin,
                "strategy": strategy,
                "interval": interval,
                "mode": result.mode,
                "leverage": leverage,
                "metrics": result.metrics.to_dict(),
                "grossMetrics": result.gross_metrics.to_dict(),
                "equity": [
                    {
                        "time": int(result.timestamps[i]),
                        "value": float(result.equity[i]),
                    }
                    for i in indices
                ],
                "costs": asdict(config.costs),
                "provenance": {
                    "engine": "backtester.core.engine.run_backtest",
                    "source": "operator_supplied_cached_OHLCV",
                    "sourceSha256": digest.hexdigest(),
                    "barsSha256": checksum_frame(frame),
                    "bars": len(frame),
                    "window": f"latest_at_most_{MAX_BARS}_completed_bars",
                    "start": int(frame.timestamp.iloc[0]),
                    "end": int(frame.timestamp.iloc[-1]),
                    "quote": "USD",
                    "fillDelay": 1,
                },
                "limitations": [
                    "historical_simulation_not_live_execution",
                    "default_model_costs_not_verified_account_fee_tier",
                    "cached_source_label_is_not_independent_market_provenance",
                    "perp_model_does_not_certify_venue_or_coin_support",
                ],
            }
        )


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16

    def __init__(self, *args, **kwargs):
        self.handler_slots = threading.BoundedSemaphore(MAX_HANDLERS)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        if not self.handler_slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.handler_slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.handler_slots.release()


def _validate_token(token):
    if not isinstance(token, str) or len(token) < 32:
        raise ValueError("ENGINE_TOKEN must contain at least 32 characters")


def make_server(analysis, token, host="127.0.0.1", port=8790):
    _validate_token(token)

    class Handler(BaseHTTPRequestHandler):
        server_version = "OraclebotAnalysis/1"
        sys_version = ""

        def setup(self):
            super().setup()
            self.rfile = DeadlineReader(self.rfile, self.connection)

        def log_message(self, *args):
            # Default access logs contain arbitrary URLs; respond() emits safe metadata.
            pass

        def respond(self, status, body):
            data = json.dumps(
                json_safe(body), allow_nan=False, separators=(",", ":")
            ).encode()
            record_event(
                "analysis_http_response",
                level=logging.WARNING if status >= 400 else logging.INFO,
                operation=getattr(self, "operation", "unknown"),
                status=status,
            )
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def handle_request(self):
            self.operation = "unknown"
            if self.headers.get("Origin"):
                return self.respond(403, {"error": "browser_origin_forbidden"})
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
                return self.respond(401, {"error": "authentication_required"})
            try:
                url = urlsplit(self.path)
                self.operation = OPERATIONS.get(url.path, "unknown")
                if (
                    self.command == "GET"
                    and url.path == "/health"
                    and not url.query
                    and hasattr(analysis, "health")
                ):
                    return self.respond(200, analysis.health())
                if (
                    self.command == "GET"
                    and url.path == "/v1/strategies"
                    and not url.query
                ):
                    return self.respond(
                        200,
                        analysis.strategies()
                        if hasattr(analysis, "strategies")
                        else catalogue(),
                    )
                if self.command == "GET" and url.path == "/v1/oracle":
                    params = parse_qs(url.query, strict_parsing=True)
                    if set(params) != {"coin"} or len(params["coin"]) != 1:
                        raise RequestError("invalid_oracle_query")
                    return self.respond(200, analysis.oracle(params["coin"][0]))
                if (
                    self.command == "GET"
                    and url.path.startswith("/v1/jobs/")
                    and not url.query
                    and hasattr(analysis, "job")
                ):
                    self.operation = "jobs"
                    return self.respond(
                        200, analysis.job(url.path.removeprefix("/v1/jobs/"))
                    )
                if (
                    self.command == "POST"
                    and url.path in ("/v1/backtests", "/v1/jobs", "/v1/signals")
                    and not url.query
                ):
                    if (
                        self.headers.get("Content-Type", "").split(";")[0]
                        != "application/json"
                    ):
                        return self.respond(415, {"error": "json_required"})
                    raw_length = self.headers.get("Content-Length", "")
                    if not raw_length.isdigit() or not 0 < int(raw_length) <= MAX_BODY:
                        return self.respond(413, {"error": "invalid_body_size"})
                    body = json.loads(self.rfile.read(int(raw_length)))
                    if url.path == "/v1/signals":
                        if not hasattr(analysis, "signal"):
                            return self.respond(404, {"error": "not_found"})
                        return self.respond(200, analysis.signal(body))
                    if url.path == "/v1/jobs" and hasattr(analysis, "submit_job"):
                        job = analysis.submit_job(body)
                        return self.respond(
                            200 if job["status"] in ("complete", "failed") else 202, job
                        )
                    if url.path == "/v1/jobs":
                        return self.respond(404, {"error": "not_found"})
                    return self.respond(200, analysis.backtest(body))
                return self.respond(404, {"error": "not_found"})
            except RequestError as exc:
                code = str(exc)
                status = (
                    429
                    if code in ("engine_busy", "job_capacity_reached")
                    else 503
                    if code
                    in (
                        "cached_history_unavailable",
                        "runtime_not_ready",
                        "public_provenance_unavailable",
                    )
                    else 409
                    if code == "job_idempotency_conflict"
                    else 404
                    if code == "job_not_found"
                    else 400
                )
                return self.respond(status, {"error": code})
            except (ValueError, json.JSONDecodeError):
                return self.respond(400, {"error": "invalid_request"})
            except Exception as exc:  # noqa: BLE001 - public HTTP boundary must not disclose internal exceptions
                record_event(
                    "analysis_request_failed",
                    level=logging.ERROR,
                    operation=self.operation,
                    error_type=type(exc).__name__,
                )
                return self.respond(503, {"error": "analysis_unavailable"})

        do_GET = handle_request
        do_POST = handle_request

    return Server((host, port), Handler)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Set ENGINE_DATA_DIR, ENGINE_ORACLE_DIR and ENGINE_TOKEN first. "
        "Example: python -m website.engine.server --host 127.0.0.1 --port 8790",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8790, type=int)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535")
    data = os.environ.get("ENGINE_DATA_DIR")
    archive = os.environ.get("ENGINE_ORACLE_DIR")
    if not data or not archive:
        parser.error(
            "ENGINE_DATA_DIR and ENGINE_ORACLE_DIR must name dedicated public-analysis inputs"
        )
    token = os.environ.get("ENGINE_TOKEN", "")
    try:
        _validate_token(token)
        analysis = Analysis(
            Path(data),
            Path(archive),
            oracle_quote=os.environ.get("ENGINE_ORACLE_QUOTE", "USD"),
        )
    except ValueError as exc:
        parser.error(str(exc))
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server = make_server(analysis, token, args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

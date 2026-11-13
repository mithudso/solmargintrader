"""Explicit, bounded public Coinbase USD acquisition; never called by an engine."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import time
from itertools import pairwise
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .server import COINS, INTERVALS, MAX_BARS
from .state import NoRedirect, canonical

SECONDS = dict(zip(INTERVALS, (60, 300, 900, 3600, 21600, 86400), strict=True))
ORIGIN = "https://api.exchange.coinbase.com"
MAX_RESPONSE = 1024 * 1024


class DataError(RuntimeError):
    pass


def _number(value, positive=True):
    if isinstance(value, bool):
        raise DataError("invalid_public_data")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise DataError("invalid_public_data") from None
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise DataError("invalid_public_data")
    return number


def atomic(path: Path, raw: bytes):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise DataError("data_symlink_refused")
    temporary = path.with_suffix(path.suffix + ".pending")
    with temporary.open("wb") as handle:
        os.chmod(temporary, 0o600)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


class PublicData:
    def __init__(self, root, *, transport=None, clock=time.time):
        self.root, self.transport, self.clock = Path(root), transport, clock
        self.last_request = 0.0
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)

    def get(self, path):
        if self.transport:
            return self.transport(path)
        # The shared Exchange public API permits3requests/s. Leave margin.
        time.sleep(max(0, 0.4 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        try:
            request = Request(
                ORIGIN + path, headers={"User-Agent": "oraclebot-public-analysis/1.0"}
            )
            with build_opener(NoRedirect()).open(request, timeout=8) as response:
                raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise DataError("public_data_too_large")
            return json.loads(raw)
        except DataError:
            raise
        except Exception:  # noqa: BLE001 - public transport failures must not expose upstream response details.
            raise DataError("public_data_unavailable") from None

    def ticker(self, coin):
        if coin not in COINS:
            raise DataError("unsupported_coin")
        body = self.get(f"/products/{coin}-USD/ticker")
        if (
            not isinstance(body, dict)
            or not isinstance(body.get("time"), str)
            or type(body.get("trade_id")) is not int
        ):
            raise DataError("invalid_ticker")
        try:
            parsed = dt.datetime.fromisoformat(body["time"])
            if parsed.tzinfo is None:
                raise ValueError("timezone_required")
            observed = parsed.timestamp()
        except (ValueError, OverflowError):
            raise DataError("invalid_ticker_time") from None
        received = self.clock()
        if not math.isfinite(observed) or not 0 <= observed <= received:
            raise DataError("invalid_ticker_time")
        price = _number(body.get("price"))
        return {
            "source": "coinbase_exchange_public",
            "instrument": coin + "/USD",
            "venue": "coinbase",
            "kind": "public_reference",
            "event_id": f"{coin}:trade:{body['trade_id']}",
            "observed_at": observed,
            "received_at": received,
            "price": price,
            "timestamp_semantics": "exchange_trade_time",
            "provider": "api.exchange.coinbase.com",
            "upstream_recency_verified": True,
        }

    def refresh(self, coin, interval):
        if coin not in COINS or interval not in SECONDS:
            raise DataError("unsupported_market")
        seconds, now = SECONDS[interval], self.clock()
        end = int(now // seconds) * seconds
        csv_path = self.root / f"{coin}_{interval}.csv"
        existing = {}
        if csv_path.exists():
            if csv_path.is_symlink() or csv_path.stat().st_size > 32 * 1024 * 1024:
                raise DataError("invalid_public_cache")
            with csv_path.open() as handle:
                for row in csv.DictReader(handle):
                    parsed = {
                        key: _number(value, key != "volume")
                        for key, value in row.items()
                    }
                    if not parsed["timestamp"].is_integer():
                        raise DataError("invalid_public_cache")
                    parsed["timestamp"] = int(parsed["timestamp"])
                    existing[parsed["timestamp"]] = parsed
        # First refresh obtains recent bars. Subsequent calls first fill missing
        # newest bars, then extend historical coverage one bounded page at a time.
        if existing and max(existing) >= end - seconds and len(existing) < MAX_BARS:
            end = min(existing)
        start = max(0, end - 300 * seconds)
        query = urlencode(
            {
                "granularity": seconds,
                "start": dt.datetime.fromtimestamp(start, dt.UTC).isoformat(),
                "end": dt.datetime.fromtimestamp(end - 1, dt.UTC).isoformat(),
            }
        )
        path = f"/products/{coin}-USD/candles?{query}"
        rows = self.get(path)
        if not isinstance(rows, list) or len(rows) > 300:
            raise DataError("invalid_candles")
        for row in rows:
            if not isinstance(row, list) or len(row) != 6:
                raise DataError("invalid_candles")
            timestamp, low, high, opening, closing, volume = (
                _number(v, i != 5) for i, v in enumerate(row)
            )
            if (
                not timestamp.is_integer()
                or int(timestamp) % seconds
                or low > high
                or not low <= opening <= high
                or not low <= closing <= high
            ):
                raise DataError("invalid_candles")
            if timestamp + seconds > now or not start <= timestamp <= end:
                continue
            existing[int(timestamp)] = {
                "timestamp": int(timestamp),
                "open": opening,
                "high": high,
                "low": low,
                "close": closing,
                "volume": volume,
            }
        ordered = [existing[key] for key in sorted(existing)[-MAX_BARS:]]
        if not ordered:
            raise DataError("public_history_empty")
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=("timestamp", "open", "high", "low", "close", "volume"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(ordered)
        raw = buffer.getvalue().encode()
        atomic(csv_path, raw)
        metadata = {
            "schemaVersion": 1,
            "provider": ORIGIN,
            "product": coin + "-USD",
            "quote": "USD",
            "interval": interval,
            "fetchedAt": now,
            "firstBar": ordered[0]["timestamp"],
            "lastBar": ordered[-1]["timestamp"],
            "bars": len(ordered),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "contiguous": all(
                b["timestamp"] - a["timestamp"] == seconds for a, b in pairwise(ordered)
            ),
        }
        atomic(csv_path.with_suffix(".json"), canonical(metadata))
        return metadata

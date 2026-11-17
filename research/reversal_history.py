"""Bounded, public historical inputs for the fixed cross-coin reversal study.

Commands emit JSON to stdout. They never modify caches, recorders or databases.
The caller archives each snapshot in MongoDB before creating local projections.
"""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import math
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import UTC, datetime
from pathlib import Path

COINS = ("HYPE", "ETH", "BTC", "SOL", "ZEC")
MAX_BYTES = 64 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pack(value):
    raw = canonical(value).encode()
    return {
        "encoding": "zlib+base64",
        "decoded_utf8_sha256": digest(raw),
        "decoded_utf8_bytes": len(raw),
        "body": base64.b64encode(zlib.compress(raw, 9)).decode(),
    }


def unpack(value):
    if value.get("encoding") != "zlib+base64":
        raise ValueError("unsupported_archive_encoding")
    size = value["decoded_utf8_bytes"]
    if type(size) is not int or not 0 < size <= MAX_BYTES:
        raise ValueError("invalid_archive_size")
    inflater = zlib.decompressobj()
    raw = inflater.decompress(base64.b64decode(value["body"], validate=True), size + 1)
    if (
        len(raw) != size
        or not inflater.eof
        or inflater.unused_data
        or digest(raw) != value["decoded_utf8_sha256"]
    ):
        raise ValueError("archive_integrity_mismatch")
    return json.loads(raw)


def read_archive(path):
    """Read a text snapshot or its lossless binary repository container."""
    path = Path(path)
    raw = path.read_bytes()
    if path.suffix == ".zlib":
        inflater = zlib.decompressobj()
        raw = inflater.decompress(raw, MAX_BYTES + 1)
        if len(raw) > MAX_BYTES or not inflater.eof or inflater.unused_data:
            raise ValueError("invalid_repository_container")
    return unpack(json.loads(raw))


def epoch(iso):
    return int(datetime.fromisoformat(iso).timestamp())


def iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat().replace("+00:00", "Z")


def validated_rows(rows):
    """Provider zero-volume rows remain explicit; no synthetic rows are added."""
    result = {}
    for row in rows:
        if len(row) != 6 or any(isinstance(x, bool) for x in row):
            raise ValueError("invalid_candle_shape")
        stamp, opening, high, low, close, volume = map(float, row)
        if (
            not all(
                math.isfinite(x) for x in (stamp, opening, high, low, close, volume)
            )
            or stamp != int(stamp)
            or int(stamp) % 60
            or min(opening, high, low, close) <= 0
            or volume < 0
            or not low <= min(opening, close) <= max(opening, close) <= high
        ):
            raise ValueError("invalid_candle_values")
        normalized = [int(stamp), opening, high, low, close, volume]
        if int(stamp) in result and result[int(stamp)] != normalized:
            raise ValueError("conflicting_duplicate_candle")
        result[int(stamp)] = normalized
    return sorted(result.values())


def local_snapshot(coin, root):
    inventory = json.loads((root / "backtest-ready/inventory.json").read_text())
    meta = inventory[coin]
    csv_path = root / f"backtest-ready/{coin}-USDC_1m.csv"
    raw_csv = csv_path.read_bytes()
    rows = validated_rows(list(csv.reader(io.StringIO(raw_csv.decode())))[1:])
    db_path = Path(meta["source_database"])
    if digest(db_path.read_bytes()) != meta["source_database_sha256"]:
        raise ValueError("raw_database_hash_mismatch")
    with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as db:
        db_rows = validated_rows(
            db.execute("SELECT ts,open,high,low,close,volume FROM candles ORDER BY ts")
        )
        if rows != db_rows:
            raise ValueError("normalized_csv_database_mismatch")
        pages = []
        for start, end, fetched, sha, raw in db.execute(
            "SELECT * FROM pages ORDER BY start"
        ):
            if digest(raw) != sha:
                raise ValueError("raw_page_hash_mismatch")
            pages.append(
                {
                    "start": start,
                    "end": end,
                    "fetched_at": fetched,
                    "sha256": sha,
                    "raw": raw.decode(),
                }
            )
        db_metadata = dict(db.execute("SELECT key,value FROM metadata"))
    if len(rows) != 43200 or rows[0][0] != 1791663600 or rows[-1][0] != 1794255540:
        raise ValueError("unexpected_fixed_archive_bounds")
    return {
        "schema": "reversal-history/v1",
        "coin": coin,
        "venue": "KuCoin",
        "quote": "USDC",
        "product": f"{coin}-USDC",
        "clock": "exchange UTC 1m bar open",
        "source_url": "https://api.kucoin.com/api/v1/market/candles",
        "study_start": 1791663600,
        "study_end_exclusive": 1794255600,
        "input_start": rows[0][0],
        "input_end_exclusive": rows[-1][0] + 60,
        "rows": rows,
        "csv_sha256": digest(raw_csv),
        "csv_text": raw_csv.decode(),
        "source_inventory": meta,
        "database_metadata": db_metadata,
        "pages": pages,
        "gap_telemetry": "unavailable; candle completeness only",
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("unexpected_provider_redirect")


def coinbase_snapshot(coin, get=None, pause=time.sleep):
    """Fetch the predeclared window; retain exact responses and every attempt."""
    if coin not in COINS:
        raise ValueError("unsupported_coin")
    start, stop = epoch("2026-11-12T04:40:00Z"), epoch("2026-11-13T05:20:00Z")
    opener = urllib.request.build_opener(NoRedirect())

    def request(url):
        with opener.open(
            urllib.request.Request(
                url, headers={"User-Agent": "Oraclebot-reversal-study/1"}
            ),
            timeout=8,
        ) as response:
            raw = response.read(1024 * 1024 + 1)
            if response.status != 200 or len(raw) > 1024 * 1024:
                raise ValueError("invalid_provider_response")
            return raw

    get = get or request
    rows, pages, attempts = [], [], []
    for left in range(start, stop, 299 * 60):
        right = min(stop, left + 299 * 60)
        url = (
            f"https://api.exchange.coinbase.com/products/{coin}-USD/candles?"
            + urllib.parse.urlencode(
                {"granularity": 60, "start": iso(left), "end": iso(right)}
            )
        )
        for attempt in range(3):
            try:
                raw = get(url)
                if len(raw) > 1024 * 1024:
                    raise ValueError("oversized_provider_response")
                values = json.loads(raw)
                if not isinstance(values, list) or len(values) > 300:
                    raise ValueError("invalid_provider_candle_array")
                normalized = validated_rows(
                    [
                        [r[0], r[3], r[2], r[1], r[4], r[5]]
                        for r in values
                        if len(r) == 6
                    ]
                )
                if len(normalized) != len(values):
                    raise ValueError("duplicate_or_malformed_provider_candles")
                rows.extend(r for r in normalized if left <= r[0] < right)
                attempts.append({"url": url, "attempt": attempt + 1, "status": "200"})
                pages.append(
                    {
                        "url": url,
                        "sha256": digest(raw),
                        "raw": raw.decode(),
                        "fetched_at": iso(int(time.time())),
                    }
                )
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                code = getattr(exc, "code", None)
                attempts.append(
                    {
                        "url": url,
                        "attempt": attempt + 1,
                        "status": str(code or type(exc).__name__),
                    }
                )
                if attempt == 2 or (code and code != 429 and code < 500):
                    raise
                pause(0.5 * (2**attempt))
        pause(0.35)
    return {
        "schema": "reversal-history/v1",
        "coin": coin,
        "venue": "Coinbase Exchange",
        "quote": "USD",
        "product": f"{coin}-USD",
        "clock": "exchange UTC 1m bar open",
        "source_url": f"https://api.exchange.coinbase.com/products/{coin}-USD/candles",
        "study_start": epoch("2026-11-12T05:00:00Z"),
        "study_end_exclusive": epoch("2026-11-13T05:00:00Z"),
        "input_start": start,
        "input_end_exclusive": stop,
        "rows": validated_rows(rows),
        "pages": pages,
        "attempts": attempts,
        "gap_telemetry": "unavailable; candle completeness only",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("local", "coinbase"))
    parser.add_argument("coin", choices=COINS)
    parser.add_argument("--archive-root", type=Path)
    args = parser.parse_args(argv)
    if args.mode == "local" and args.archive_root is None:
        parser.error("--archive-root is required for local inputs")
    source = (
        local_snapshot(args.coin, args.archive_root)
        if args.mode == "local"
        else coinbase_snapshot(args.coin)
    )
    print(
        canonical(
            {
                **pack(source),
                "source_summary": {
                    k: source[k]
                    for k in (
                        "coin",
                        "venue",
                        "quote",
                        "study_start",
                        "study_end_exclusive",
                    )
                },
            }
        )
    )


if __name__ == "__main__":
    main()

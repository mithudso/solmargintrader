"""Fetch long Coinbase Exchange candle history for pattern and level studies.

python -m research.coin_history --coins HYPE ZEC BTC --granularity 300 3600 86400 \
    --start 2026-02-05T00:00:00Z --end 2026-11-27T00:00:00Z --output /absolute/path/history

Public candles only: no keys, no account, no order path. Each file is one gzip CSV
per coin and granularity. manifest.json binds every file's SHA-256, row count,
first and last bar, missing grid slots and zero-volume bars, so a later study can
prove which bars it read. Missing bars are reported, never interpolated.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from research.coin_week_data import read_url

BASE = "https://api.exchange.coinbase.com"
PAGE = 300
LABELS = {60: "1m", 300: "5m", 900: "15m", 3600: "1h", 86400: "1d"}


def iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(value: str) -> int:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamps need an explicit timezone, e.g. 2026-02-05T00:00:00Z")
    return int(parsed.timestamp())


def page(product: str, granularity: int, left: int, right: int) -> list:
    url = (
        f"{BASE}/products/{product}/candles?granularity={granularity}"
        f"&start={iso(left)}&end={iso(right)}"
    )
    failure: Exception | None = None
    for attempt in range(4):
        try:
            rows = json.loads(read_url(url, max_bytes=2 * 1024 * 1024))
            if not isinstance(rows, list) or len(rows) > PAGE + 1:
                raise ValueError("unexpected candle page shape")
            return rows
        except (OSError, ValueError) as exc:
            failure = exc
            print(
                f"attempt {attempt + 1} of 4 failed: {product} {granularity}s "
                f"{iso(left)}..{iso(right)}: {exc}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"{product} {granularity}s {iso(left)}: {failure}")


def fetch(product: str, granularity: int, start: int, end: int) -> list[tuple]:
    bars: dict[int, tuple] = {}
    right = end
    while right > start:
        left = max(start, right - PAGE * granularity)
        for row in page(product, granularity, left, right):
            stamp, low, high, opened, closed, volume = row
            bars[int(stamp)] = (
                int(stamp),
                float(opened),
                float(high),
                float(low),
                float(closed),
                float(volume),
            )
        time.sleep(0.12)
        right = left
    return [bars[stamp] for stamp in sorted(bars) if start <= stamp < end]


def render(bars: list[tuple]) -> bytes:
    lines = ["unix,timestamp_utc,open,high,low,close,volume"]
    for stamp, opened, high, low, closed, volume in bars:
        lines.append(
            f"{stamp},{iso(stamp)},{opened!r},{high!r},{low!r},{closed!r},{volume!r}"
        )
    return ("\n".join(lines) + "\n").encode()


def audit(bars: list[tuple], granularity: int, start: int, end: int) -> dict:
    expected = range((start + granularity - 1) // granularity * granularity, end, granularity)
    present = {bar[0] for bar in bars}
    missing = [stamp for stamp in expected if stamp not in present]
    return {
        "rows": len(bars),
        "expected_slots": len(expected),
        "missing_slots": len(missing),
        "first_bar": iso(bars[0][0]) if bars else None,
        "last_bar": iso(bars[-1][0]) if bars else None,
        "zero_volume_bars": sum(1 for bar in bars if bar[5] == 0.0),
        "first_missing_slots": [iso(stamp) for stamp in missing[:5]],
    }


def run(coins: list[str], granularities: list[int], start: int, end: int, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest: dict = {
        "schema": "coinbase-history/v1",
        "source": BASE,
        "window_start": iso(start),
        "window_end_exclusive": iso(end),
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": {},
    }
    for coin in coins:
        product = f"{coin.upper()}-USD"
        for granularity in granularities:
            label = LABELS.get(granularity, f"{granularity}s")
            name = f"{coin.upper()}-USD_{label}.csv.gz"
            bars = fetch(product, granularity, start, end)
            raw = gzip.compress(render(bars), mtime=0)
            (output / name).write_bytes(raw)
            entry = {
                "product": product,
                "granularity_seconds": granularity,
                "sha256": hashlib.sha256(raw).hexdigest(),
                **audit(bars, granularity, start, end),
            }
            manifest["files"][name] = entry
            print(
                f"{name}: rows={entry['rows']} missing={entry['missing_slots']} "
                f"zero_volume={entry['zero_volume_bars']} {entry['first_bar']}..{entry['last_bar']}",
                flush=True,
            )
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coins", nargs="+", required=True)
    parser.add_argument("--granularity", nargs="+", type=int, default=[300, 3600, 86400])
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    start, end = parse_utc(args.start), parse_utc(args.end)
    if end <= start:
        raise ValueError("end must be after start")
    unsupported = [g for g in args.granularity if g not in LABELS]
    if unsupported:
        raise ValueError(f"granularity must be one of {sorted(LABELS)}")
    run(args.coins, args.granularity, start, end, args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

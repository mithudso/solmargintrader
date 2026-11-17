"""Explicit public candle acquisition for the weekly study; no execution access."""

from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from research.reversal_history import NoRedirect, canonical, iso, validated_rows

BASE = "https://api.exchange.coinbase.com"
BINANCE = "https://data-api.binance.vision/api/v3/klines"
PROVIDERS = {
    "coinbase": {
        "venue": "Coinbase Exchange spot",
        "quote": "USD",
        "base": BASE,
        "page_minutes": 299,
    },
    "binance": {
        "venue": "Binance spot",
        "quote": "USDT",
        "base": BINANCE,
        "page_minutes": 1000,
    },
}
MAX_BYTES = 1024 * 1024
COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def save(path: Path, value) -> None:
    raw = (canonical(value) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(zlib.compress(raw, 9) if path.suffix == ".zlib" else raw)
    temporary.replace(path)


def load(path: Path):
    raw = path.read_bytes()
    if path.suffix == ".zlib":
        decoder = zlib.decompressobj()
        raw = decoder.decompress(raw, 64 * 1024 * 1024 + 1)
        if len(raw) > 64 * 1024 * 1024 or not decoder.eof or decoder.unused_data:
            raise ValueError("invalid weekly snapshot container")
    return json.loads(raw)


def coin_symbol(value: str) -> str:
    value = value.upper()
    if not re.fullmatch(r"[A-Z0-9]{2,15}", value):
        raise ValueError("coin must be a bare ticker such as ETH")
    return value


def week_bounds(end: str | None = None, days: int = 7, *, now=None) -> tuple[int, int]:
    current = now or datetime.now(UTC)
    stop = int(current.timestamp()) // 60 * 60
    if end is not None:
        parsed = datetime.fromisoformat(end)
        if parsed.tzinfo is None:
            raise ValueError(
                "--end needs an explicit timezone, for example 2026-11-17T17:00:00Z"
            )
        stop = int(parsed.timestamp())
        if (
            parsed.microsecond
            or stop % 60
            or stop > int(current.timestamp()) // 60 * 60
        ):
            raise ValueError("end must be a completed UTC minute boundary")
    if type(days) is not int or not 1 <= days <= 31:
        raise ValueError("days must be an integer in [1,31]")
    return stop - days * 86400, stop


def read_url(url: str) -> bytes:
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        url, headers={"User-Agent": "solmargintrader-weekly-study/1"}
    )
    with opener.open(request, timeout=20) as response:
        raw = response.read(MAX_BYTES + 1)
        if response.status != 200 or len(raw) > MAX_BYTES:
            raise ValueError("invalid or oversized candle response")
        return raw


def page_rows(raw: bytes, left: int, right: int, provider: str = "coinbase") -> list:
    if len(raw) > MAX_BYTES:
        raise ValueError("oversized candle response")
    values = json.loads(raw)
    if provider == "coinbase":
        if not isinstance(values, list) or len(values) > 300:
            raise ValueError("expected at most 300 Coinbase candles")
        if any(not isinstance(row, list) or len(row) != 6 for row in values):
            raise ValueError("malformed Coinbase candle")
        # Coinbase's order is time, LOW, HIGH, OPEN, close, volume.
        normalized = validated_rows(
            [[r[0], r[3], r[2], r[1], r[4], r[5]] for r in values]
        )
    elif provider == "binance":
        if not isinstance(values, list) or len(values) > 1000:
            raise ValueError("expected at most 1000 Binance candles")
        converted = []
        for r in values:
            if (
                not isinstance(r, list)
                or len(r) < 7
                or type(r[0]) is not int
                or type(r[6]) is not int
                or r[0] % 60000
                or r[6] != r[0] + 59999
            ):
                raise ValueError("invalid Binance candle or closed-minute timestamp")
            converted.append([r[0] // 1000, *r[1:6]])
        normalized = validated_rows(converted)
    else:
        raise ValueError("unsupported candle provider")
    if len(normalized) != len(values):
        raise ValueError("duplicate candle within provider page")
    return [r for r in normalized if left <= r[0] < right]


def verify_snapshot(source: dict, coin: str, start: int, stop: int) -> list:
    if (source["coin"], source["input_start"], source["input_end_exclusive"]) != (
        coin,
        start,
        stop,
    ):
        raise ValueError("snapshot coin or window mismatch")
    provider = source.get("provider", "coinbase")
    meta = PROVIDERS[provider]
    product = f"{coin}-USD" if provider == "coinbase" else f"{coin}USDT"
    if (source["study_start"], source["study_end_exclusive"]) != (start, stop):
        raise ValueError("study window does not match acquisition")
    if (source["venue"], source["quote"], source["product"], source["source_url"]) != (
        meta["venue"],
        meta["quote"],
        product,
        meta["base"],
    ):
        raise ValueError("snapshot venue mismatch")
    expected = list(range(start, stop, meta["page_minutes"] * 60))
    if [p["start"] for p in source["pages"]] != expected:
        raise ValueError("incomplete acquisition page census")
    reproduced = []
    for page in source["pages"]:
        left, right = (
            page["start"],
            min(stop, page["start"] + meta["page_minutes"] * 60),
        )
        url = candle_url(coin, left, right, provider)
        raw = page["raw"].encode()
        if (
            page["url"] != url
            or page["end_exclusive"] != right
            or digest(raw) != page["sha256"]
        ):
            raise ValueError("raw candle page integrity mismatch")
        reproduced.extend(page_rows(raw, left, right, provider))
    rows = validated_rows(reproduced)
    if rows != source["rows"]:
        raise ValueError("normalized candles do not match archived responses")
    return rows


def candle_url(coin: str, left: int, right: int, provider: str = "coinbase") -> str:
    if provider == "binance":
        return (
            BINANCE
            + "?"
            + urllib.parse.urlencode(
                {
                    "symbol": f"{coin}USDT",
                    "interval": "1m",
                    "startTime": left * 1000,
                    "endTime": right * 1000 - 1,
                    "limit": 1000,
                }
            )
        )
    return f"{BASE}/products/{coin}-USD/candles?" + urllib.parse.urlencode(
        {"granularity": 60, "start": iso(left), "end": iso(right)}
    )


def download(
    coin: str,
    start: int,
    stop: int,
    path: Path,
    *,
    get=read_url,
    pause=time.sleep,
    provider="coinbase",
) -> dict:
    """Resume a frozen page census; archive bytes before advancing to another page."""
    coin = coin_symbol(coin)
    meta = PROVIDERS[provider]
    if start % 60 or stop % 60 or stop <= start:
        raise ValueError("invalid minute acquisition bounds")
    if path.exists():
        source = load(path)
        if source.get("provider", "coinbase") != provider:
            raise ValueError("snapshot provider mismatch; never mix venues")
        verify_snapshot(source, coin, start, stop)
        return source
    partial = path.with_name(path.name + ".partial")
    source = (
        load(partial)
        if partial.exists()
        else {
            "schema": "weekly-coin-candles/v1",
            "coin": coin,
            "provider": provider,
            "venue": meta["venue"],
            "quote": meta["quote"],
            "product": f"{coin}-USD" if provider == "coinbase" else f"{coin}USDT",
            "clock": "exchange UTC minute open; available after minute close",
            "source_url": meta["base"],
            "study_start": start,
            "study_end_exclusive": stop,
            "input_start": start,
            "input_end_exclusive": stop,
            "gap_telemetry": "unavailable; OHLCV completeness does not establish feed continuity",
            "fetched_at": datetime.now(UTC).isoformat(),
            "pages": [],
            "attempts": [],
            "rows": [],
        }
    )
    if (source["coin"], source["input_start"], source["input_end_exclusive"]) != (
        coin,
        start,
        stop,
    ):
        raise ValueError("partial acquisition belongs to another run")
    # A partial file is a checkpoint, never evidence until its pages revalidate.
    for page in source["pages"]:
        raw = page["raw"].encode()
        if digest(raw) != page["sha256"] or page["url"] != candle_url(
            coin, page["start"], page["end_exclusive"], provider
        ):
            raise ValueError("partial acquisition integrity mismatch")
    existing = {p["start"]: p for p in source["pages"]}
    for left in range(start, stop, meta["page_minutes"] * 60):
        right = min(stop, left + meta["page_minutes"] * 60)
        if left in existing:
            continue
        url = candle_url(coin, left, right, provider)
        for attempt in range(3):
            try:
                raw = get(url)
                page_rows(raw, left, right, provider)
                source["pages"].append(
                    {
                        "start": left,
                        "end_exclusive": right,
                        "url": url,
                        "sha256": digest(raw),
                        "raw": raw.decode(),
                        "fetched_at": datetime.now(UTC).isoformat(),
                    }
                )
                source["attempts"].append(
                    {"url": url, "attempt": attempt + 1, "status": "200"}
                )
                save(partial, source)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                code = getattr(exc, "code", None)
                source["attempts"].append(
                    {
                        "url": url,
                        "attempt": attempt + 1,
                        "status": str(code or type(exc).__name__),
                    }
                )
                save(partial, source)
                if attempt == 2 or (code and code != 429 and code < 500):
                    raise
                pause(0.5 * 2**attempt)
        pause(0.35)
    source["pages"].sort(key=lambda p: p["start"])
    source["rows"] = validated_rows(
        [
            r
            for p in source["pages"]
            for r in page_rows(
                p["raw"].encode(), p["start"], p["end_exclusive"], provider
            )
        ]
    )
    verify_snapshot(source, coin, start, stop)
    present = {r[0] for r in source["rows"]}
    source["coverage"] = {
        "expected_minutes": (stop - start) // 60,
        "observed_minutes": len(present),
        "missing_minutes": [t for t in range(start, stop, 60) if t not in present],
        "zero_volume_minutes": sum(r[5] == 0 for r in source["rows"]),
    }
    save(path, source)
    partial.unlink(missing_ok=True)
    return source


def frame_from(source: dict) -> pd.DataFrame:
    return pd.DataFrame(source["rows"], columns=COLUMNS)


def resample(frame: pd.DataFrame, step: int) -> pd.DataFrame:
    """Keep only complete UTC buckets, including for the custom ten-minute cadence."""
    if type(step) is not int or step < 60 or step % 60:
        raise ValueError("cadence must be a positive multiple of one minute")
    if frame.empty:
        return frame.copy()
    work = frame.copy()
    work["bucket"] = work.timestamp // step * step
    grouped = work.groupby("bucket", sort=True)
    out = grouped.agg(
        timestamp=("timestamp", "first"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    )
    out = out.loc[(grouped.size() == step // 60) & (out.timestamp == out.index)]
    return out.reset_index(drop=True)[list(COLUMNS)]


def arrays(frame: pd.DataFrame) -> dict:
    return {
        "ts": frame.timestamp.to_numpy(np.int64),
        **{k: frame[k].to_numpy(float) for k in COLUMNS[1:]},
    }

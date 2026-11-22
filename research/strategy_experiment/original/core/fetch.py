"""Explicit historical data fetch from the Coinbase Exchange public API.

Never called implicitly by a backtest. Run it once to populate the local CSV
cache, then every run and every test reads from disk.

Two hazards this module exists to handle:

  1. Coinbase returns rows as [time, low, high, open, close, volume] -- NOT in
     OHLCV order. Mapping it positionally as OHLCV silently corrupts every
     backtest downstream, so the mapping is explicit and named here.
  2. The endpoint caps a response at 300 candles, so any useful history needs
     backward pagination.

Binance is deliberately not supported: it returns
"Service unavailable from a restricted location" from this environment.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

from .data import validate_bars
from .types import BAR_COLUMNS, INTERVAL_SECONDS

COINBASE_BASE = "https://api.exchange.coinbase.com"
MAX_CANDLES_PER_REQUEST = 300
# Coinbase's documented row layout. The whole point of naming it.
COINBASE_ROW = ("time", "low", "high", "open", "close", "volume")

# Coinbase only accepts these granularities, in seconds.
SUPPORTED_GRANULARITIES = (60, 300, 900, 3600, 21600, 86400)


class FetchError(RuntimeError):
    """Raised when data could not be retrieved after retries."""


def _get_json(url: str, *, retries: int = 3, backoff: float = 1.5) -> list:
    """GET a URL and parse JSON, retrying transient failures then giving up."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "sol-backtester/0.1 (research)"}
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                payload = json.loads(resp.read().decode())
            if isinstance(payload, dict) and payload.get("message"):
                raise FetchError(f"API error: {payload['message']}")
            return payload
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(backoff * (attempt + 1))
    raise FetchError(
        f"failed to fetch after {retries} attempts: {last}. "
        "Check connectivity; do not substitute synthetic data for a real-data run."
    ) from last


def fetch_coinbase(
    product: str,
    start: str,
    end: str,
    interval: str,
    *,
    pause: float = 0.25,
    verbose: bool = True,
) -> pd.DataFrame:
    """Fetch candles for `product` between `start` and `end` (UTC dates).

    Paginates backward from `end` in windows of 300 candles.
    """
    granularity = INTERVAL_SECONDS[interval]
    if granularity not in SUPPORTED_GRANULARITIES:
        raise ValueError(
            f"Coinbase supports granularities {SUPPORTED_GRANULARITIES}s; "
            f"interval {interval} maps to {granularity}s"
        )

    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int(pd.Timestamp(end, tz="UTC").timestamp())
    if end_ts <= start_ts:
        raise ValueError(f"end ({end}) must be after start ({start})")

    chunks: list[np.ndarray] = []
    cursor = end_ts
    requests_made = 0

    while cursor > start_ts:
        window_start = max(start_ts, cursor - granularity * MAX_CANDLES_PER_REQUEST)
        params = urllib.parse.urlencode(
            {
                "granularity": granularity,
                "start": pd.Timestamp(window_start, unit="s", tz="UTC").isoformat(),
                "end": pd.Timestamp(cursor, unit="s", tz="UTC").isoformat(),
            }
        )
        url = f"{COINBASE_BASE}/products/{product}/candles?{params}"
        rows = _get_json(url)
        requests_made += 1

        if not rows:
            if verbose:
                print(
                    f"  no candles before {pd.Timestamp(cursor, unit='s', tz='UTC').date()}"
                    " -- stopping (likely start of listing)",
                    file=sys.stderr,
                )
            break

        arr = np.asarray(rows, dtype="float64")
        chunks.append(arr)
        oldest = int(arr[:, 0].min())
        if verbose:
            print(
                f"  {len(rows):>3} candles back to "
                f"{pd.Timestamp(oldest, unit='s', tz='UTC').date()}",
                file=sys.stderr,
            )

        if oldest >= cursor:
            # No backward progress; stop rather than loop forever.
            break
        cursor = oldest
        time.sleep(pause)

    if not chunks:
        raise FetchError(f"no candles returned for {product} in {start}..{end}")

    stacked = np.vstack(chunks)
    idx = {name: k for k, name in enumerate(COINBASE_ROW)}
    df = pd.DataFrame(
        {
            "timestamp": stacked[:, idx["time"]].astype("int64"),
            "open": stacked[:, idx["open"]],
            "high": stacked[:, idx["high"]],
            "low": stacked[:, idx["low"]],
            "close": stacked[:, idx["close"]],
            "volume": stacked[:, idx["volume"]],
        }
    )
    df = (
        df.drop_duplicates(subset="timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] <= end_ts)]

    if verbose:
        print(
            f"  {len(df)} unique bars in {requests_made} requests",
            file=sys.stderr,
        )
    return df.loc[:, list(BAR_COLUMNS)].reset_index(drop=True)


def default_cache_path(asset: str, interval: str) -> Path:
    """Conventional cache location for an asset/interval pair."""
    return Path("data") / f"{asset.upper()}_{interval}.csv"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the explicit fetch step."""
    ap = argparse.ArgumentParser(
        description="Fetch OHLCV candles from Coinbase into a local CSV cache."
    )
    ap.add_argument("--asset", default="SOL", help="base asset, e.g. SOL")
    ap.add_argument("--quote", default="USD", help="quote currency, default USD")
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument(
        "--end",
        default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"),
        help="inclusive end date, default today",
    )
    ap.add_argument("--interval", default="1d", choices=sorted(INTERVAL_SECONDS))
    ap.add_argument("--out", default=None, help="output CSV path")
    ap.add_argument(
        "--allow-gaps",
        action="store_true",
        help="write the file even if the series has missing bars",
    )
    args = ap.parse_args(argv)

    product = f"{args.asset.upper()}-{args.quote.upper()}"
    out = Path(args.out) if args.out else default_cache_path(args.asset, args.interval)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {product} {args.interval} {args.start}..{args.end}", file=sys.stderr)
    df = fetch_coinbase(product, args.start, args.end, args.interval)

    try:
        validate_bars(df, args.interval, strict_gaps=not args.allow_gaps)
    except Exception as exc:
        print(f"\nValidation failed: {exc}", file=sys.stderr)
        if not args.allow_gaps:
            print(
                "Re-run with --allow-gaps to accept an incomplete series.",
                file=sys.stderr,
            )
            return 1

    df.to_csv(out, index=False)
    first = pd.Timestamp(int(df["timestamp"].iloc[0]), unit="s", tz="UTC").date()
    last = pd.Timestamp(int(df["timestamp"].iloc[-1]), unit="s", tz="UTC").date()
    print(f"Wrote {len(df)} bars ({first} .. {last}) to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Explicit trade-tick fetch from the Coinbase Exchange public API.

Sibling of fetch.py, and deliberately separate from it. Candles and ticks are
different contracts: a tick frame is not a bar frame and must never be loaded
as one, so nothing here writes into the `data/<ASSET>_<interval>.csv` namespace
that CsvLoader reads. Ticks land under `data/ticks/`.

Three hazards this module exists to handle:

  1. `/products/<id>/trades` accepts NO time range. Passing `start`/`end` is
     silently ignored -- the API returns the newest trades and looks like it
     worked. Verified against the live endpoint; this is the whole reason the
     seek below is written by trade_id rather than by timestamp.
  2. Paging is by opaque cursor: the `cb-after` response header carries the
     next (older) trade_id, and `?after=<id>` returns trades strictly older
     than `<id>`. Walking a month of SOL ticks from the head is millions of
     trades, so the start of the window is located by bisecting on trade_id
     (ids are dense and monotonic in time) before any sequential paging.
  3. Coinbase reports `side` as the MAKER's side. A trade marked "sell" was a
     resting sell order that a buyer lifted -- i.e. an aggressive BUY. Signing
     order flow off this field without inverting it gets the sign of every
     trade backwards.
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import pandas as pd

from .data import validate_bars
from .fetch import COINBASE_BASE, FetchError, _get_json
from .types import BAR_COLUMNS, INTERVAL_SECONDS

MAX_TRADES_PER_REQUEST = 1000
TRADE_COLUMNS = ("timestamp", "trade_id", "price", "size", "side")


def _parse_trades(rows: list[dict]) -> pd.DataFrame:
    """Map raw trade dicts to the named tick contract.

    Named explicitly for the same reason fetch.COINBASE_ROW is: a positional
    or guessed mapping corrupts everything downstream and looks fine.
    """
    if not rows:
        return pd.DataFrame({c: [] for c in TRADE_COLUMNS})
    df = pd.DataFrame(
        {
            # format="ISO8601" (not a fixed format string) because Coinbase
            # mixes fractional-second precision across eras: recent trades
            # carry 6 digits, 2021-era trades carry 3.
            "timestamp": pd.to_datetime(
                [r["time"] for r in rows], utc=True, format="ISO8601"
            ).astype("int64")
            / 1e9,
            "trade_id": [int(r["trade_id"]) for r in rows],
            "price": [float(r["price"]) for r in rows],
            "size": [float(r["size"]) for r in rows],
            # Maker side. Aggressor is the opposite -- see module docstring.
            "side": [str(r["side"]) for r in rows],
        }
    )
    return df.loc[:, list(TRADE_COLUMNS)]


def _trade_page(product: str, *, after: int | None, limit: int) -> pd.DataFrame:
    """One page of trades, optionally older than `after`."""
    params: dict[str, object] = {"limit": limit}
    if after is not None:
        params["after"] = after
    url = f"{COINBASE_BASE}/products/{product}/trades?{urllib.parse.urlencode(params)}"
    # The `cb-after` response header carries the next cursor, but the smallest
    # trade_id on the page is the same value and needs no header plumbing, so
    # fetch._get_json is reused rather than duplicated for its headers.
    return _parse_trades(_get_json(url))


def newest_trade_id(product: str) -> int:
    """trade_id of the most recent trade, i.e. the top of the id range."""
    page = _trade_page(product, after=None, limit=1)
    if page.empty:
        raise FetchError(f"no trades returned for {product}")
    return int(page["trade_id"].iloc[0])


def seek_trade_id(
    product: str, target_ts: float, *, pause: float = 0.12, verbose: bool = True
) -> int:
    """Bisect the trade_id space for the oldest id whose time is >= target_ts.

    The API has no time filter (hazard 1), but ids are dense and monotonic in
    time, so a ~25-request bisection replaces millions of sequential pages.
    Returns 1 if the product's whole history is newer than target_ts.
    """
    lo, hi = 1, newest_trade_id(product)
    probes = 0
    while lo < hi:
        mid = (lo + hi) // 2
        # after=<id> yields trades strictly older, so probe at mid+1 to read
        # the trade *at* mid.
        page = _trade_page(product, after=mid + 1, limit=1)
        probes += 1
        if page.empty:
            # Gap or pruned id; treat as too old and search newer.
            lo = mid + 1
        elif float(page["timestamp"].iloc[0]) < target_ts:
            lo = mid + 1
        else:
            hi = mid
        time.sleep(pause)
    if verbose:
        print(f"  seek: id {lo} after {probes} probes", file=sys.stderr)
    return lo


def fetch_trades(
    product: str,
    start: str,
    end: str,
    *,
    max_trades: int = 500_000,
    pause: float = 0.12,
    verbose: bool = True,
) -> pd.DataFrame:
    """Fetch trades for `product` in [start, end), ascending by time.

    Walks backward by cursor from the trade at `end` until it passes `start`
    or `max_trades` is reached. `max_trades` is a guard, not a target: a month
    of SOL-USD is millions of trades, and a truncated window is reported
    rather than silently returned as if complete.
    """
    start_ts = pd.Timestamp(start, tz="UTC").timestamp()
    end_ts = pd.Timestamp(end, tz="UTC").timestamp()
    if end_ts <= start_ts:
        raise ValueError(f"end ({end}) must be after start ({start})")

    cursor = seek_trade_id(product, end_ts, pause=pause, verbose=verbose) + 1
    pages: list[pd.DataFrame] = []
    collected = 0
    truncated = False

    while True:
        page = _trade_page(product, after=cursor, limit=MAX_TRADES_PER_REQUEST)
        if page.empty:
            break
        pages.append(page)
        collected += len(page)
        oldest_id = int(page["trade_id"].min())
        oldest_ts = float(page["timestamp"].min())
        if verbose:
            print(
                f"  {len(page):>4} trades back to "
                f"{pd.Timestamp(oldest_ts, unit='s', tz='UTC')}",
                file=sys.stderr,
            )
        if oldest_ts < start_ts:
            break
        if oldest_id >= cursor:
            # No backward progress; stop rather than loop forever.
            break
        if collected >= max_trades:
            truncated = True
            break
        cursor = oldest_id
        time.sleep(pause)

    if not pages:
        raise FetchError(f"no trades returned for {product} in {start}..{end}")

    df = pd.concat(pages, ignore_index=True)
    df = df.drop_duplicates(subset="trade_id")
    # Sort on (timestamp, trade_id), never timestamp alone: Coinbase stamps
    # every fill of one aggressing order with the identical microsecond, so a
    # timestamp-only sort leaves those ties in arbitrary order and the open and
    # close of the bar they land in become non-deterministic.
    df = df.sort_values(["timestamp", "trade_id"])
    df = df[(df["timestamp"] >= start_ts) & (df["timestamp"] < end_ts)]
    df = df.reset_index(drop=True)

    # Truncation travels with the frame. Printing it only to stderr lets a
    # programmatic caller treat a short window as a complete one.
    df.attrs["truncated"] = truncated
    df.attrs["requested_window"] = (start, end)
    if truncated and verbose:
        print(
            f"  TRUNCATED at max_trades={max_trades}; window is incomplete at "
            "its start. Raise --max-trades or narrow the window.",
            file=sys.stderr,
        )
    if verbose:
        print(f"  {len(df)} trades in window", file=sys.stderr)
    return df


def trades_to_bars(trades: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Aggregate a tick frame into OHLCV bars on `interval` boundaries.

    Bars are labelled by the open of their window, matching the candle
    convention in fetch.py. Empty intervals are omitted rather than
    forward-filled -- inventing a bar where no trade happened is exactly the
    kind of confident wrong number the engine must not be fed.
    """
    seconds = INTERVAL_SECONDS[interval]
    if trades.empty:
        raise ValueError("cannot aggregate an empty tick frame")
    missing = [c for c in ("timestamp", "trade_id", "price", "size") if c not in trades]
    if missing:
        raise ValueError(f"tick frame missing required column(s): {missing}")

    # Sort here rather than trusting the caller. `open` and `close` are
    # first/last in row order, and the API hands back trades NEWEST first, so
    # aggregating a raw page would silently invert every bar's open and close.
    # (timestamp, trade_id) because same-microsecond ties are routine -- see
    # the sort in fetch_trades.
    ordered = trades.sort_values(["timestamp", "trade_id"])
    buckets = (ordered["timestamp"] // seconds).astype("int64") * seconds
    grouped = ordered.assign(bucket=buckets).groupby("bucket", sort=True)
    bars = pd.DataFrame(
        {
            "timestamp": grouped["price"].first().index.astype("int64"),
            "open": grouped["price"].first().to_numpy(),
            "high": grouped["price"].max().to_numpy(),
            "low": grouped["price"].min().to_numpy(),
            "close": grouped["price"].last().to_numpy(),
            "volume": grouped["size"].sum().to_numpy(),
        }
    )
    return bars.loc[:, list(BAR_COLUMNS)].reset_index(drop=True)


def default_tick_path(asset: str, start: str, end: str) -> Path:
    """Tick cache location, kept out of the bar-cache namespace on purpose."""
    return Path("data") / "ticks" / f"{asset.upper()}_trades_{start}_{end}.csv"


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the explicit tick fetch step."""
    ap = argparse.ArgumentParser(
        description="Fetch trade ticks from Coinbase into a local CSV cache."
    )
    ap.add_argument("--asset", default="SOL")
    ap.add_argument("--quote", default="USD")
    ap.add_argument("--start", required=True, help="inclusive UTC start, ISO 8601")
    ap.add_argument("--end", required=True, help="exclusive UTC end, ISO 8601")
    ap.add_argument(
        "--max-trades",
        type=int,
        default=500_000,
        help="guard against unbounded walks; a truncated window is reported",
    )
    ap.add_argument("--out", default=None, help="output CSV path")
    ap.add_argument(
        "--allow-truncated",
        action="store_true",
        help="write the file even though it covers less than the requested "
        "window; a disclosure, not a repair",
    )
    ap.add_argument(
        "--bars",
        default=None,
        choices=sorted(INTERVAL_SECONDS),
        help="also aggregate the ticks to bars at this interval",
    )
    ap.add_argument("--bars-out", default=None, help="output CSV path for --bars")
    args = ap.parse_args(argv)

    product = f"{args.asset.upper()}-{args.quote.upper()}"
    out = Path(args.out) if args.out else default_tick_path(args.asset, args.start, args.end)
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {product} trades {args.start}..{args.end}", file=sys.stderr)
    trades = fetch_trades(product, args.start, args.end, max_trades=args.max_trades)

    # A truncated frame carries `attrs`, but `to_csv` drops attrs, so on disk a
    # partial month is indistinguishable from a complete one -- and the file
    # name still claims the full window. Refuse by default and make the caller
    # disclose, exactly as the candle path does with --allow-gaps.
    if trades.attrs.get("truncated") and not args.allow_truncated:
        print(
            f"\nRefusing to write: the walk stopped at --max-trades="
            f"{args.max_trades}, so this covers only "
            f"{pd.Timestamp(float(trades['timestamp'].iloc[0]), unit='s', tz='UTC')}"
            f" .. {args.end}, not the window you asked for.\n"
            "Raise --max-trades, narrow the window, or pass --allow-truncated.",
            file=sys.stderr,
        )
        return 1

    trades.to_csv(out, index=False)
    print(f"Wrote {len(trades)} trades to {out}", file=sys.stderr)

    if args.bars:
        bars = trades_to_bars(trades, args.bars)
        # Ticks can leave empty intervals; the bar contract is checked but gaps
        # are permitted here, exactly as the candle path does with --allow-gaps.
        validate_bars(bars, args.bars, strict_gaps=False)
        bars_out = (
            Path(args.bars_out)
            if args.bars_out
            else out.with_name(out.stem + f"_{args.bars}_bars.csv")
        )
        bars.to_csv(bars_out, index=False)
        print(f"Wrote {len(bars)} {args.bars} bars to {bars_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

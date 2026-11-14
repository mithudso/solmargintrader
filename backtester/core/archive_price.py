"""Append-only spot-price archiver, for series nobody publishes history for.

    python -m backtester.core.archive_price --mint JLP --out data/JLP_spot.csv

Some cards are blocked on data that **cannot be fetched retroactively**. JLP is the
clearest case: Jupiter's Price API serves its current price keyless, no exchange
this repo can reach lists a JLP pair, and there is no charts endpoint. So the
history does not exist anywhere to download — it can only be accumulated from now
on, one observation at a time.

This is the tool that accumulates it. Run it on a schedule; each run appends one
row. It is deliberately **not** part of any backtest path: `fetch.py` remains the
only component that talks to a market data API for a backtest, and this writes a
file that no strategy reads until enough rows exist to be a series.

**What this cannot do.** It cannot give you yesterday's price. A card unblocked
this way is unblocked *going forward*, and until the file is long enough to cover
a `fit_window` plus a test window, the strategy that depends on it has nothing to
run on. The card says so rather than implying the gap is closed.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .market_diagnostics import market_request

PRICE_URL = "https://lite-api.jup.ag/price/v3?ids={ids}"

# Mints for the assets this repo has a documented reason to track. Sourced from
# the perps page's own hydration payload — see
# docs/trading-signals-concept-family.md section 10.
KNOWN_MINTS = {
    "JLP": "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",
    "SOL": "So11111111111111111111111111111111111111112",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
}

HEADER = ("timestamp", "iso", "mint", "usd_price", "source")


class ArchiveError(RuntimeError):
    """Raised when a price could not be read or the file could not be appended."""


def _validated_price(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArchiveError("price must be a finite positive number")
    try:
        price = float(value)
    except OverflowError as exc:
        raise ArchiveError("price must be a finite positive number") from exc
    if not math.isfinite(price) or price <= 0:
        raise ArchiveError("price must be a finite positive number")
    return price


def fetch_spot(mint: str, *, timeout: float = 10.0) -> float:
    """Current USD price for `mint`, or raise.

    Refuses a missing or non-positive price rather than writing a zero: a zero in a
    price archive is indistinguishable from a real observation later, and it would
    silently poison every spread computed from the file.
    """
    url = PRICE_URL.format(ids=mint)
    req = urllib.request.Request(url, headers={"User-Agent": "sol-backtester/0.1 (research)"})
    try:
        with market_request("spot_archive"), urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ArchiveError(f"could not read a price for {mint}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ArchiveError("price response must be an object")
    entry = payload.get(mint)
    if not isinstance(entry, dict):
        raise ArchiveError(f"response carried no price entry for {mint}")
    return _validated_price(entry.get("usdPrice"))


def append_observation(path: Path, mint: str, price: float, *, when: datetime | None = None) -> None:
    """Append one row, writing the header if the file is new."""
    price = _validated_price(price)
    when = when or datetime.now(timezone.utc)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", newline="", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0, 2)
        writer = csv.writer(handle)
        if handle.tell() == 0:
            writer.writerow(HEADER)
        writer.writerow(
            [int(when.timestamp()), when.isoformat(), mint, f"{price:.10g}", "jupiter-price-v3"]
        )
        handle.flush()


def count_rows(path: Path) -> int:
    """Observations already archived, excluding the header."""
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def main(argv: Sequence[str] | None = None) -> int:
    """Append one observation. Returns a process exit code."""
    ap = argparse.ArgumentParser(
        prog="python -m backtester.core.archive_price",
        description=(
            "Append one spot price to a CSV archive, for assets whose history "
            "cannot be fetched retroactively. NOT investment advice."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Example: python -m backtester.core.archive_price --mint JLP --dry-run\n"
            "This accumulates history going forward; it cannot recover the past.\n"
            "Schedule it (cron / launchd) if you want a usable series.\n"
        ),
    )
    ap.add_argument(
        "--mint",
        default="JLP",
        help=f"mint address, or one of {sorted(KNOWN_MINTS)}",
    )
    ap.add_argument("--out", default=None, help="CSV path (default data/<NAME>_spot.csv)")
    ap.add_argument("--dry-run", action="store_true", help="print the price, write nothing")
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))

    label = args.mint.upper()
    mint = KNOWN_MINTS.get(label, args.mint)
    out = Path(args.out) if args.out else Path("data") / f"{label}_spot.csv"

    try:
        price = fetch_spot(mint)
    except ArchiveError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"{label} {mint} = ${price:,.6f} (dry run, nothing written)")
        return 0

    try:
        append_observation(out, mint, price)
    except OSError as exc:
        print(f"error: could not append to {out}: {exc}", file=sys.stderr)
        return 1

    rows = count_rows(out)
    print(f"{label} ${price:,.6f} appended to {out} ({rows} observations)")
    if rows < 300:
        print(
            f"note: {rows} observations is not yet a backtestable series. A 250-bar "
            "fit window plus a test window needs several hundred.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

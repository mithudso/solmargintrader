"""Explicit historical **funding-rate** fetch, for the carry question `perps.py` cannot answer.

    python3 -m backtester.core.funding --plan-only
    python3 -m backtester.core.funding --assets BTC,ETH,SOL,DOGE,ZEC
    python3 -m backtester.core.funding --assets BTC --cross-check-okx

Never called implicitly by a backtest. Like `fetch.py` and `universe.py`, this is
the explicit step you run once; the engine reads the cache.

## Why this module exists at all

`core/perps.py` models a **borrow fee**: both sides pay it and it is floored at
zero. That is the correct model for Jupiter Perps and it is what this project's
leverage arithmetic runs on. It is *not* a funding rate.

A funding rate **changes sign** with the long/short imbalance. When it is
negative, shorts pay longs, and *receiving* it is the entire basis-carry trade.
No model built on a floored-at-zero fee can express a payment you receive, so
`research/RATIO-ROTATION.md` had to write the carry question up as unevaluable.
This module is what makes it evaluable: realised, per-interval, signed funding.

## Venue choice was decided by probing, not preference

| Venue | Result |
| --- | --- |
| **Hyperliquid** | works; **hourly** funding, ~27.8k rows/coin back to 2023-05-12 |
| OKX | works but serves only ~100 rows (~33 days at 8h); no `ZEC-USD-SWAP` |
| Bybit | HTTP 403 from this environment |
| Binance | HTTP 451 from this environment (matches `fetch.py`'s note) |

Hyperliquid is therefore primary and OKX is a **cross-check only** (`--cross-check-okx`),
which is worth having for a reason beyond redundancy: a carry signal visible on one
venue and absent on another is a statement about that venue's positioning, not
about the asset. Bybit and Binance are recorded above so the next person does not
re-probe them.

## What this module deliberately does NOT provide

**Open-interest history, and that is a real hole rather than an oversight.**
`RATIO-ROTATION.md` names OI imbalance as one of the inputs a carry study wants,
because imbalance is what drives funding's sign. Neither reachable venue serves it
at usable depth:

  * Hyperliquid's `metaAndAssetCtxs` returns `openInterest` for the **current
    instant only** -- a snapshot, with no history endpoint.
  * OKX's `rubik` OI series is aggregated **per currency, not per instrument**,
    and returned only ~180 daily points.

So a study built on this cache can ask "was funding positive or negative, and what
did receiving it earn" and cannot ask "did OI imbalance predict the sign". Anyone
extending this should treat the second question as still blocked, and say so.

## Hazards this module handles

1. **Hyperliquid funding is HOURLY; most CEX funding is 8-hourly.** Summing an
   hourly series and an 8-hourly one as though they were the same units overstates
   one by 8x. The cached interval is recorded in the filename (`_funding_1h`) and
   the cross-check converts explicitly rather than implicitly.
2. **The endpoint caps a response at 500 rows**, so any useful history needs
   forward pagination; a single unpaginated call silently returns six weeks.
3. **A paginated fetch can loop forever** if the venue stops advancing. Pagination
   stops when the newest timestamp fails to advance, not merely when a page is
   short.
4. **Reads time out under sustained pagination.** Probing this endpoint, BTC's 56
   pages succeeded and the next coin's first page timed out, so retries with
   backoff are mandatory rather than defensive.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from .fetch import FetchError

HYPERLIQUID_URL = "https://api.hyperliquid.xyz/info"
OKX_FUNDING_URL = "https://www.okx.com/api/v5/public/funding-rate-history"

# The venue caps a `fundingHistory` response at this many rows.
MAX_ROWS_PER_REQUEST = 500

# Hyperliquid funds hourly. Named rather than inlined because the whole
# unit-mismatch hazard in the docstring turns on this number.
FUNDING_INTERVAL_SECONDS = 3600
FUNDING_COLUMNS = ("timestamp", "funding_rate", "premium")

# Politeness delay between paginated requests.
REQUEST_SPACING_SECONDS = 0.08

# A funding rate outside this band per hour is treated as a venue error rather
# than a market event. Hyperliquid caps funding at 4% per hour; anything beyond
# that is a parse or unit bug, and silently accepting it would put a number in a
# P&L path that no venue ever charged.
MAX_PLAUSIBLE_HOURLY_RATE = 0.04

# Venues probed and rejected, kept as data so the next person does not re-probe.
REJECTED_VENUES: dict[str, str] = {
    "bybit": "HTTP 403 from this environment (/v5/market/funding/history)",
    "binance": "HTTP 451 from this environment (/fapi/v1/fundingRate), as with spot in fetch.py",
}

# Assets whose Hyperliquid listing date truncates any cross-asset carry study, in
# the same spirit as `universe.py`'s SHORT_HISTORY. The venue itself launched in
# 2023, so no coin here reaches the 2021 start the spot cache does.
SHORT_FUNDING_HISTORY: dict[str, str] = {
    "ZEC": "Hyperliquid funding for ZEC starts 2025-10-02, so a carry study including it is <1 year",
    "HYPE": "HYPE did not exist before its own venue; funding history starts late 2024",
    "BNB": "listed later than the majors on this venue; check the fetched span before using it",
}


class FundingFetchError(FetchError):
    """Raised when funding history could not be retrieved after retries."""


@dataclass(frozen=True)
class FundingOutcome:
    """Result of fetching one asset, including the reason it produced nothing."""

    asset: str
    rows: int
    path: Path | None
    span: str
    note: str = ""

    def describe(self) -> str:
        if self.rows == 0:
            return f"FAILED: {self.note}"
        return f"wrote {self.rows} rows to {self.path} ({self.span})"


def _post_json(payload: dict[str, Any], *, retries: int = 4, backoff: float = 1.6) -> Any:
    """POST JSON to the Hyperliquid info endpoint, retrying transient failures.

    Retries are not defensive padding. A sustained paginated fetch reliably
    produced a read timeout partway through, so a single-attempt implementation
    would abandon a 56-page download at page 40 and leave a truncated cache that
    looks complete.
    """
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                HYPERLIQUID_URL,
                data=json.dumps(payload).encode(),
                headers={
                    "User-Agent": "sol-backtester/0.1 (research)",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode())
            if isinstance(body, dict) and body.get("error"):
                raise FundingFetchError(f"API error: {body['error']}")
            return body
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            last = exc
            if attempt < retries - 1:
                time.sleep(backoff ** (attempt + 1))
    raise FundingFetchError(f"request failed after {retries} attempts: {last}")


def hyperliquid_universe() -> list[str]:
    """Coins the venue lists perps for."""
    meta = _post_json({"type": "meta"})
    return [entry["name"] for entry in meta.get("universe", [])]


def validate_funding(frame: pd.DataFrame) -> pd.DataFrame:
    """Reject a funding series that would silently corrupt a carry backtest.

    Mirrors `data.validate_bars`' posture: refuse rather than repair. A duplicate
    or out-of-order funding timestamp double-counts or reverses a payment, and
    unlike a bad price it produces no obvious artifact in an equity curve -- it
    just makes carry look better or worse than it was.
    """
    missing = [c for c in FUNDING_COLUMNS if c not in frame.columns]
    if missing:
        raise FundingFetchError(f"missing columns {missing}")
    if frame.empty:
        raise FundingFetchError("empty funding frame")

    ts = frame["timestamp"].to_numpy()
    if not pd.Series(ts).is_monotonic_increasing:
        raise FundingFetchError("funding timestamps are not strictly ascending")
    if pd.Series(ts).duplicated().any():
        raise FundingFetchError("duplicate funding timestamps")
    if (ts > 1e10).any():
        raise FundingFetchError("timestamps look like milliseconds; expected epoch seconds")

    rate = frame["funding_rate"].to_numpy(dtype=float)
    if not pd.Series(rate).notna().all():
        raise FundingFetchError("non-finite funding rate")
    if (abs(rate) > MAX_PLAUSIBLE_HOURLY_RATE).any():
        worst = float(abs(rate).max())
        raise FundingFetchError(
            f"funding rate {worst:.6f}/h exceeds the plausible cap "
            f"{MAX_PLAUSIBLE_HOURLY_RATE}; suspect a unit or parse bug"
        )
    return frame.reset_index(drop=True)


def fetch_hyperliquid_funding(
    coin: str,
    start: str | None = None,
    end: str | None = None,
    *,
    verbose: bool = False,
) -> pd.DataFrame:
    """Full hourly funding history for `coin`, paginated forward.

    Returns columns `FUNDING_COLUMNS` with `timestamp` in epoch **seconds** (the
    venue serves milliseconds; converted once, here, so nothing downstream has to
    remember which unit it is holding).

    `funding_rate` is the realised rate for that hour as a fraction, **signed**:
    positive means longs paid shorts. That sign is the entire point of the module
    and is preserved rather than absolute-valued anywhere in the path.
    """
    start_ms = 0 if start is None else int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = None if end is None else int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)

    rows: list[dict[str, Any]] = []
    cursor = start_ms
    newest_seen: int | None = None
    pages = 0

    while True:
        payload = {"type": "fundingHistory", "coin": coin, "startTime": cursor}
        if end_ms is not None:
            payload["endTime"] = end_ms
        page = _post_json(payload)
        if not isinstance(page, list) or not page:
            break

        pages += 1
        rows.extend(page)
        newest = int(page[-1]["time"])

        # Stop on failure to advance, not merely on a short page. A venue that
        # keeps returning the same final row would otherwise spin forever.
        if newest_seen is not None and newest <= newest_seen:
            break
        newest_seen = newest

        if verbose:
            stamp = pd.to_datetime(newest, unit="ms", utc=True).strftime("%Y-%m-%d %H:%M")
            print(f"  {coin}: {len(rows)} rows through {stamp}", file=sys.stderr)

        if len(page) < MAX_ROWS_PER_REQUEST:
            break
        cursor = newest + 1
        time.sleep(REQUEST_SPACING_SECONDS)

    if not rows:
        raise FundingFetchError(f"{coin}: venue returned no funding history")

    frame = pd.DataFrame(
        {
            "timestamp": [int(r["time"]) // 1000 for r in rows],
            "funding_rate": [float(r["fundingRate"]) for r in rows],
            "premium": [float(r.get("premium", "nan")) for r in rows],
        }
    )
    # Pagination boundaries can repeat a row; drop exact duplicates before the
    # validator, which treats a duplicate timestamp as fatal.
    frame = frame.drop_duplicates(subset="timestamp").sort_values("timestamp")
    return validate_funding(frame)


def fetch_okx_funding(inst_id: str) -> pd.DataFrame:
    """Recent funding from OKX, for cross-checking only.

    Deliberately not paginated. The endpoint serves ~100 rows at 8-hour intervals
    -- about a month -- which is far too shallow to backtest and is useful only to
    confirm that Hyperliquid's sign and rough magnitude are not venue artifacts.
    Presenting it as a history source would be the mistake this docstring exists
    to prevent.
    """
    url = f"{OKX_FUNDING_URL}?instId={inst_id}&limit=100"
    req = urllib.request.Request(url, headers={"User-Agent": "sol-backtester/0.1 (research)"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FundingFetchError(f"OKX request failed: {exc}") from exc

    if body.get("code") != "0" or not body.get("data"):
        raise FundingFetchError(f"OKX: {body.get('msg') or 'no data'} for {inst_id}")

    data = body["data"]
    frame = pd.DataFrame(
        {
            "timestamp": [int(r["fundingTime"]) // 1000 for r in data],
            "funding_rate": [float(r["realizedRate"]) for r in data],
            "premium": [float("nan")] * len(data),
        }
    ).sort_values("timestamp")
    return frame.reset_index(drop=True)


def default_funding_path(asset: str) -> Path:
    repo = Path(__file__).resolve().parents[2]
    return repo / "data" / f"{asset}_funding_1h.csv"


def fetch_funding_universe(
    assets: Sequence[str],
    start: str | None = None,
    end: str | None = None,
    out_dir: Path | None = None,
    *,
    skip_existing: bool = True,
    verbose: bool = False,
) -> dict[str, FundingOutcome]:
    """Fetch each asset, recording per-asset outcomes rather than aborting the batch.

    One asset failing does not abandon the rest, for the same reason
    `universe.py` gives: a partial cache nobody can reason about is worse than a
    reported failure.
    """
    listed = set(hyperliquid_universe())
    results: dict[str, FundingOutcome] = {}

    for asset in assets:
        if asset not in listed:
            results[asset] = FundingOutcome(asset, 0, None, "", "not listed on Hyperliquid")
            continue

        out = (out_dir / f"{asset}_funding_1h.csv") if out_dir else default_funding_path(asset)
        if skip_existing and out.exists():
            existing = pd.read_csv(out)
            results[asset] = FundingOutcome(
                asset, len(existing), out, _span(existing), "skipped (cached)"
            )
            continue

        try:
            frame = fetch_hyperliquid_funding(asset, start, end, verbose=verbose)
        except FundingFetchError as exc:
            results[asset] = FundingOutcome(asset, 0, None, "", str(exc))
            continue

        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        results[asset] = FundingOutcome(asset, len(frame), out, _span(frame))

    return results


def _span(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    lo = pd.to_datetime(int(frame["timestamp"].min()), unit="s").date()
    hi = pd.to_datetime(int(frame["timestamp"].max()), unit="s").date()
    return f"{lo}..{hi}"


def summarise(frame: pd.DataFrame) -> dict[str, float]:
    """Headline carry statistics for one asset's funding series.

    `share_negative` is the number that decides whether a carry trade is even
    worth modelling: if funding is positive almost always, the only way to
    harvest it is to be short, and that is a directional bet wearing a carry
    label.
    """
    rate = frame["funding_rate"].to_numpy(dtype=float)
    hours = len(rate)
    return {
        "hours": float(hours),
        "mean_hourly": float(rate.mean()),
        "annualised_pct": float(rate.mean() * 24 * 365 * 100.0),
        "share_negative": float((rate < 0).mean()),
        "max_hourly": float(rate.max()),
        "min_hourly": float(rate.min()),
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Fetch realised funding-rate history into the local cache.",
    )
    ap.add_argument("--assets", default="BTC,ETH,SOL,DOGE,ZEC")
    ap.add_argument("--start", default=None, help="UTC date; default is the venue's earliest")
    ap.add_argument("--end", default=None)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--refetch", action="store_true", help="re-fetch assets already cached")
    ap.add_argument("--plan-only", action="store_true", help="print listing status and stop")
    ap.add_argument("--summary", action="store_true", help="print carry statistics for the cache")
    ap.add_argument(
        "--cross-check-okx",
        action="store_true",
        help="compare recent Hyperliquid funding against OKX (shallow; sanity only)",
    )
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]

    for venue, why in REJECTED_VENUES.items():
        print(f"note: {venue} not used -- {why}", file=sys.stderr)
    print(
        "note: open-interest HISTORY is unavailable from either reachable venue; "
        "Hyperliquid serves a current snapshot only and OKX aggregates per currency. "
        "A study using this cache cannot ask whether OI imbalance predicted funding's sign.",
        file=sys.stderr,
    )

    try:
        listed = set(hyperliquid_universe())
    except FundingFetchError as exc:
        print(f"cannot reach Hyperliquid: {exc}", file=sys.stderr)
        return 1

    for asset in assets:
        if asset in SHORT_FUNDING_HISTORY:
            print(f"note: {asset} -- {SHORT_FUNDING_HISTORY[asset]}", file=sys.stderr)
    missing = [a for a in assets if a not in listed]
    if missing:
        print(f"WARNING: not listed on Hyperliquid: {', '.join(missing)}", file=sys.stderr)

    if args.plan_only:
        for asset in assets:
            print(f"  {'ok ' if asset in listed else '-- '}{asset}", file=sys.stderr)
        return 0

    if args.summary:
        rows = []
        for asset in assets:
            path = default_funding_path(asset)
            if not path.exists():
                continue
            rows.append({"asset": asset, **summarise(pd.read_csv(path))})
        if not rows:
            print("no cached funding series; run without --summary first", file=sys.stderr)
            return 1
        print(pd.DataFrame(rows).to_string(index=False))
        return 0

    results = fetch_funding_universe(
        assets,
        args.start,
        args.end,
        Path(args.out_dir) if args.out_dir else None,
        skip_existing=not args.refetch,
        verbose=args.verbose,
    )

    print("", file=sys.stderr)
    failures = 0
    for asset in assets:
        outcome = results.get(asset)
        if outcome is None:
            continue
        if outcome.rows == 0:
            failures += 1
        print(f"  {asset:<6} {outcome.describe()}", file=sys.stderr)

    if args.cross_check_okx:
        print("\nOKX cross-check (shallow, sanity only):", file=sys.stderr)
        for asset in assets:
            try:
                okx = fetch_okx_funding(f"{asset}-USD-SWAP")
            except FundingFetchError as exc:
                print(f"  {asset:<6} unavailable: {exc}", file=sys.stderr)
                continue
            # OKX funds 8-hourly; convert to an hourly rate before comparing, or
            # the two venues differ by a factor of 8 for purely clerical reasons.
            hourly = okx["funding_rate"].mean() / 8.0
            print(
                f"  {asset:<6} OKX mean {hourly:+.8f}/h over {len(okx)} eight-hour periods",
                file=sys.stderr,
            )

    if failures:
        print(f"\n{failures} asset(s) produced nothing.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

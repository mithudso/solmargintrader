"""Fetch a multi-asset universe into the local CSV cache.

`fetch.py` fetches one product. This fetches a named set of them and, more
importantly, is honest about the set it could not fetch.

The reason that matters more than the loop: **the venue does not list every asset
in the universe.** Of the ten largest non-pegged coins as of 2026-08-04
(`research/TOP_COINS.md`), Coinbase Exchange lists eight; TRX and RAIN are absent
from its product list entirely. A fetcher that quietly writes eight files hands
the next stage an eight-asset universe wearing a ten-asset name, and every
cross-sectional statistic computed on it — a rank, a breadth count, a
"top-N momentum" selection — is then computed over a survivorship-filtered set
chosen by *listing venue*, which is precisely the bias nobody notices.

So `plan_universe_fetch` is a pure function that returns the split, and the CLI
refuses to proceed on a partial universe unless `--allow-partial` is passed. The
refusal is the feature.

Nothing here is called by a backtest. Like `fetch.py`, it is the explicit step you
run once; the engine reads the cache.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .data import validate_bars
from .fetch import FetchError, default_cache_path, fetch_coinbase
from .types import INTERVAL_SECONDS

COINBASE_PRODUCTS_URL = "https://api.exchange.coinbase.com/products"

# The ten largest non-pegged coins by market cap, 2026-08-04, in rank order.
# Source and the reason pegged assets are excluded: research/TOP_COINS.md.
# Stablecoins are omitted deliberately -- USDT and USDC rank 3rd and 5th overall,
# and an asset whose design goal is not to move is not a directional candidate.
TOP10_NON_PEGGED = ("BTC", "ETH", "BNB", "XRP", "SOL", "TRX", "HYPE", "DOGE", "RAIN", "ZEC")

# The subset this project already holds history for.
ALREADY_CACHED = ("BTC", "ETH", "SOL")

# Assets whose market-cap rank does not survive contact with evidence, and why.
# Kept as data rather than silently dropped from TOP10_NON_PEGGED above: that constant
# states what market cap says, and this states why we decline to believe it. Both are
# true and a reader needs to see the disagreement.
EXCLUDED: dict[str, str] = {
    "RAIN": (
        "market-cap rank unreliable: CoinGecko #14 / CoinMarketCap #201 / DefiLlama #16 "
        "on the same day; ~0.24% turnover; total bid depth within 2% of mid across all "
        "venues ~$294k against an $8.6B nominal cap; ~66% of supply in vesting, treasury "
        "or one Nasdaq holder (ENLV, 6.9% held plus an option on 23.6% at 73% below "
        "market). Not listed on Coinbase either. See "
        "crypto-coin-intelligence/references/rain-rain.md"
    ),
}

# Assets whose *available history* is short enough to be its own evidence-floor problem,
# separate from whether the venue lists them at all. A strategy measured on six months of
# bars is not weakly evidenced, it is barely evidenced -- and the fetch succeeds silently,
# so nothing downstream flags it.
SHORT_HISTORY: dict[str, str] = {
    "HYPE": "HYPE-USD only listed on Coinbase 2026-02-05, so a fetch returns ~6 months",
    "TRX": (
        "not on Coinbase at all; the only reachable alternative serves a fixed ~721-bar "
        "window, capping TRX at ~2 years and truncating any cross-asset study including it"
    ),
    "DOGE": (
        "DOGE-USD starts 2021-06-03 on Coinbase, so a --start earlier than that is silently "
        "truncated rather than refused -- 1,890 bars, not the ~2,040 a 2021-01-01 request "
        "implies. Contiguous, but shorter than asked for"
    ),
    "BNB": (
        "BNB-USD returns ~288 daily bars from 2025-10-22 -- and they cover one monotone "
        "bull-to-bear leg ($1,073 to ~$603), so there are too few independent folds for "
        "walk-forward or CPCV to say anything"
    ),
}

# Series with a hole in the middle, which is a worse failure than a short series because a
# naive fetch concatenates across it and the join looks like an ordinary bar.
# `validate_bars(strict_gaps=True)` is what catches this, and it is why the CLI defaults to
# strict and requires --allow-gaps to be asked for explicitly.
KNOWN_GAPS: dict[str, str] = {
    "XRP": (
        "Coinbase suspended XRP on 2021-01-19 and relisted it on 2023-07-13, so the series "
        "has a ~30-month hole. Concatenated blind it becomes a single bar spanning two and "
        "a half years, and every return, volatility and drawdown computed across it is wrong"
    ),
}

# Quote-pair availability, where it is narrower than USD. Matters for anything needing a
# cross pair rather than a USD leg -- see triangular_arbitrage.md, which cannot be built
# from USD-quoted series at all.
USD_ONLY: dict[str, str] = {
    "ZEC": "Coinbase has delisted ZEC-BTC and ZEC-USDC; only ZEC-USD remains",
}

# What a directional strategy should actually be pointed at. Nine, not ten -- backfilling
# an eleventh to restore a round number would be choosing the number over the evidence.
TRADEABLE_UNIVERSE = tuple(a for a in TOP10_NON_PEGGED if a not in EXCLUDED)


@dataclass(frozen=True)
class FetchPlan:
    """What a universe fetch would do, before it does any of it."""

    available: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    products: dict[str, str] = field(default_factory=dict)

    @property
    def partial(self) -> bool:
        return bool(self.missing)

    def summary(self) -> str:
        line = f"{len(self.available)} of {len(self.available) + len(self.missing)} assets available"
        if self.missing:
            line += f"; not listed on this venue: {', '.join(self.missing)}"
        return line


def product_id(asset: str, quote: str = "USD") -> str:
    return f"{asset.upper()}-{quote.upper()}"


def plan_universe_fetch(
    assets: Iterable[str],
    listed_products: Iterable[str],
    quote: str = "USD",
) -> FetchPlan:
    """Split the requested universe into what the venue lists and what it does not.

    Pure: `listed_products` is whatever the venue's product endpoint returned, so
    this is testable without a network call and the CLI can print the plan before
    committing to it.
    """
    listed = set(listed_products)
    available: list[str] = []
    missing: list[str] = []
    products: dict[str, str] = {}
    for asset in assets:
        pid = product_id(asset, quote)
        if pid in listed:
            available.append(asset.upper())
            products[asset.upper()] = pid
        else:
            missing.append(asset.upper())
    return FetchPlan(tuple(available), tuple(missing), products)


def list_coinbase_products(get_json: Callable[[str], list] | None = None) -> tuple[str, ...]:
    """Every product id the venue currently lists and will trade.

    `trading_disabled` and a non-online status both mean a product that exists in
    the catalogue but cannot produce a usable series, so neither counts as listed.
    """
    if get_json is None:  # pragma: no cover - the network path
        from .fetch import _get_json

        get_json = _get_json
    payload = get_json(COINBASE_PRODUCTS_URL)
    out = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        if entry.get("trading_disabled") or entry.get("status") != "online":
            continue
        pid = entry.get("id")
        if pid:
            out.append(str(pid))
    return tuple(sorted(out))


def fetch_universe(
    plan: FetchPlan,
    start: str,
    end: str,
    interval: str,
    *,
    fetcher: Callable[..., pd.DataFrame] = fetch_coinbase,
    out_dir: Path | None = None,
    skip_existing: bool = True,
    strict_gaps: bool = True,
    verbose: bool = True,
) -> dict[str, str]:
    """Fetch every available asset in `plan`. Returns {asset: outcome}.

    One asset failing does not abandon the rest -- a universe fetch of ten assets
    that dies on the third leaves a cache in a state nobody can reason about. Each
    outcome is recorded and the caller decides.
    """
    results: dict[str, str] = {asset: "not-listed" for asset in plan.missing}

    for asset in plan.available:
        out = (out_dir / f"{asset}_{interval}.csv") if out_dir else default_cache_path(asset, interval)
        if skip_existing and out.exists():
            results[asset] = f"skipped (cached at {out})"
            continue
        try:
            frame = fetcher(plan.products[asset], start, end, interval, verbose=verbose)
        except (FetchError, ValueError) as exc:
            results[asset] = f"FAILED: {exc}"
            continue

        try:
            validate_bars(frame, interval, strict_gaps=strict_gaps)
        except Exception as exc:  # noqa: BLE001 - reported per asset, never fatal to the batch
            results[asset] = f"FAILED validation: {exc}"
            continue

        out.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(out, index=False)
        results[asset] = f"wrote {len(frame)} bars to {out}"

    return results


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Prints the plan, then refuses a partial universe by default."""
    ap = argparse.ArgumentParser(
        description="Fetch a multi-asset universe into the local CSV cache.",
    )
    ap.add_argument(
        "--assets",
        default=",".join(TRADEABLE_UNIVERSE),
        help=(
            "comma-separated base assets; defaults to the tradeable universe, which is the "
            "top-10 non-pegged set minus those in EXCLUDED (currently RAIN)"
        ),
    )
    ap.add_argument("--quote", default="USD")
    ap.add_argument("--start", default="2021-01-01")
    ap.add_argument("--end", default=pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d"))
    ap.add_argument("--interval", default="1d", choices=sorted(INTERVAL_SECONDS))
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--refetch", action="store_true", help="re-fetch assets already cached")
    ap.add_argument("--allow-gaps", action="store_true")
    ap.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "proceed when the venue does not list every requested asset. Off by default: "
            "a silently partial universe biases every cross-sectional statistic computed "
            "over it, and the filter is the listing venue rather than anything economic."
        ),
    )
    ap.add_argument("--plan-only", action="store_true", help="print the plan and stop")
    args = ap.parse_args(argv)

    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    listed = list_coinbase_products()
    plan = plan_universe_fetch(assets, listed, args.quote)

    for asset in assets:
        if asset in EXCLUDED:
            print(f"note: {asset} is in EXCLUDED -- {EXCLUDED[asset]}", file=sys.stderr)
        if asset in SHORT_HISTORY:
            print(f"note: {asset} short history -- {SHORT_HISTORY[asset]}", file=sys.stderr)
        if asset in USD_ONLY:
            print(f"note: {asset} USD-only -- {USD_ONLY[asset]}", file=sys.stderr)
        if asset in KNOWN_GAPS:
            print(f"WARNING: {asset} has a known gap -- {KNOWN_GAPS[asset]}", file=sys.stderr)
    print(f"Universe plan: {plan.summary()}", file=sys.stderr)
    for asset in assets:
        mark = "  ok " if asset in plan.available else "  -- "
        print(f"{mark}{asset}", file=sys.stderr)

    if args.plan_only:
        return 0

    if plan.partial and not args.allow_partial:
        print(
            f"\nRefusing a partial universe: {', '.join(plan.missing)} not listed on this venue.\n"
            "Any cross-sectional statistic over the remainder would be computed on a set\n"
            "filtered by listing venue, which is a survivorship bias nobody sees downstream.\n"
            "Re-run with --allow-partial to accept that knowingly, or name a different venue.",
            file=sys.stderr,
        )
        return 1

    results = fetch_universe(
        plan,
        args.start,
        args.end,
        args.interval,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        skip_existing=not args.refetch,
        strict_gaps=not args.allow_gaps,
    )

    print("", file=sys.stderr)
    failures = 0
    for asset in assets:
        outcome = results.get(asset, "not attempted")
        if outcome.startswith("FAILED"):
            failures += 1
        print(f"  {asset:<6} {outcome}", file=sys.stderr)

    if failures:
        print(f"\n{failures} asset(s) failed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

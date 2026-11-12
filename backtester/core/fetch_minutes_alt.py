"""1-minute candles for coins Coinbase does not list, from the venue that does.

    python3 -m backtester.core.fetch_minutes_alt --plan
    python3 -m backtester.core.fetch_minutes_alt --assets TRX,LEO --years 7

Like `fetch.py` and `fetch_minutes.py`, this is an explicit network step that writes the local
cache; no backtest calls it.

## Why a second fetcher

The 2026-11-07 probe found minute history on OKX, KuCoin, Bitget or WhiteBIT for assets in
the top-50 non-pegged screen that Coinbase does not list. The active venue map omits the
six assets the owner removed from coin lists; the dated screen remains historical evidence.

## What differs from the Coinbase cache, and how it is kept visible

* **Quote currency.** These are USDT pairs, not USD. USDT has tracked USD closely, but a price
  in USDT is not a price in USD, and a depeg would show up here as a move in the coin.
* **Venue.** Each file has a sidecar `data/<ASSET>_1m.source.json` naming the venue and pair, and
  the coverage manifest records the venue per asset. The compound backtest prints it with the
  data source, so a reader never mistakes a KuCoin series for a Coinbase one.
* **Column order.** KuCoin and WhiteBIT return [time, open, CLOSE, high, low, ...]; OKX and
  Bitget return [time, open, high, low, close, ...]. Mapping one as the other silently swaps the
  close with the high. Every parsed row is checked (high >= max(open, close) >= min(open, close)
  >= low), and a page where more than 1% of rows fail aborts the fetch instead of writing it.

## How the walk works

Each venue serves pages that end at a given time. The fetcher walks backward from now, one page
at a time, appending rows to the CSV as it goes and recording the oldest timestamp reached in a
`.alt-progress.json` sidecar, so an interrupted run resumes where it stopped. The walk ends when
it reaches `--years` back, or when several consecutive pages come back empty (before listing).
"""

from __future__ import annotations

import argparse
import json
import hashlib
import math
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .fetch_minutes import DATA, MANIFEST, coverage as candle_coverage, load_minutes, minute_path, render_coverage, write_manifest
from .types import BAR_COLUMNS

USER_AGENT = "solmargintrader-research/1.0 (read-only)"
EMPTY_PAGES_TO_STOP = 6
SANITY_FAIL_LIMIT = 0.01

Fetch = Callable[[str], object]


class AltFetchError(RuntimeError):
    """A venue answered in a way this module cannot use."""


@dataclass(frozen=True)
class Venue:
    """How to page one venue's 1m candles backward and parse its rows."""

    name: str
    page_seconds: int          # span one request covers
    per_second: float          # polite request rate for this host
    pair: Callable[[str], str]
    url: Callable[[str, int, int], str]  # (pair, start_s, end_s) -> URL
    rows: Callable[[object], list[list[float]]]  # payload -> [[ts_s, o, h, l, c, v], ...]


def _okx_rows(payload: object) -> list[list[float]]:
    if not isinstance(payload, dict) or str(payload.get("code")) != "0":
        raise AltFetchError(f"okx: {str(payload)[:160]}")
    # [ts_ms, o, h, l, c, vol(base), volCcy, volCcyQuote, confirm]
    return [[int(r[0]) // 1000, *(float(x) for x in r[1:6])] for r in payload.get("data") or []
            if str(r[8]) == "1"]  # confirm == 1: the candle has closed


def _kucoin_rows(payload: object) -> list[list[float]]:
    if not isinstance(payload, dict) or str(payload.get("code")) != "200000":
        raise AltFetchError(f"kucoin: {str(payload)[:160]}")
    # [time_s, open, CLOSE, high, low, volume(base), turnover] -- note close before high.
    return [[int(r[0]), float(r[1]), float(r[3]), float(r[4]), float(r[2]), float(r[5])]
            for r in payload.get("data") or []]


def _bitget_rows(payload: object) -> list[list[float]]:
    if not isinstance(payload, dict) or str(payload.get("code")) != "00000":
        raise AltFetchError(f"bitget: {str(payload)[:160]}")
    # [ts_ms, open, high, low, close, baseVol, usdtVol, quoteVol]
    return [[int(r[0]) // 1000, *(float(x) for x in r[1:6])] for r in payload.get("data") or []]


def _whitebit_rows(payload: object) -> list[list[float]]:
    if not isinstance(payload, dict) or not payload.get("success"):
        raise AltFetchError(f"whitebit: {str(payload)[:160]}")
    # [time_s, open, CLOSE, high, low, volume(stock), volume(money)] -- close before high.
    return [[int(r[0]), float(r[1]), float(r[3]), float(r[4]), float(r[2]), float(r[5])]
            for r in payload.get("result") or []]


VENUES: dict[str, Venue] = {
    "okx": Venue("okx", 100 * 60, 9.0, lambda a: f"{a}-USDT",
                 lambda p, s, e: (f"https://www.okx.com/api/v5/market/history-candles?instId={p}&bar=1m"
                                  f"&after={(e + 60) * 1000}&before={(s - 60) * 1000}&limit=100"), _okx_rows),
    "kucoin": Venue("kucoin", 1500 * 60, 5.0, lambda a: f"{a}-USDT",
                    lambda p, s, e: (f"https://api.kucoin.com/api/v1/market/candles?type=1min&symbol={p}"
                                     f"&startAt={s}&endAt={e}"), _kucoin_rows),
    "bitget": Venue("bitget", 200 * 60, 8.0, lambda a: f"{a}USDT",
                    lambda p, s, e: (f"https://api.bitget.com/api/v2/spot/market/history-candles?symbol={p}"
                                     f"&granularity=1min&endTime={(e + 60) * 1000}&limit=200"), _bitget_rows),
    "whitebit": Venue("whitebit", 1440 * 60, 5.0, lambda a: f"{a}_USDT",
                      lambda p, s, e: (f"https://whitebit.com/api/v1/public/kline?market={p}&interval=1m"
                                       f"&start={s}&end={e}&limit=1440"), _whitebit_rows),
}

# Venue per coin, chosen by the 2026-11-07 probes (deepest 1m history among reachable venues).
ASSET_VENUE: dict[str, str] = {
    "TRX": "okx", "LEO": "okx", "OKB": "okx", "CC": "okx", "GRAM": "okx",
    "BGB": "bitget", "M": "bitget", "BTW": "bitget",
}


def http_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 - fixed public hosts
        return json.loads(resp.read().decode())


class Pacer:
    """At most `per_second` requests to one host, shared by every asset on that venue."""

    def __init__(self, per_second: float, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.gap, self.clock, self.sleep = 1.0 / per_second, clock, sleep
        self.next_at = 0.0
        self.lock = threading.Lock()

    def wait(self) -> None:
        with self.lock:
            now = self.clock()
            if now < self.next_at:
                self.sleep(self.next_at - now)
            self.next_at = max(now, self.next_at) + self.gap


def sane(rows: Sequence[Sequence[float]]) -> tuple[list[list[float]], int]:
    """Rows whose OHLC is internally consistent, and how many were not."""
    good, bad = [], 0
    for r in rows:
        _, o, h, low, c, v = r
        if all(math.isfinite(value) for value in r) and min(o, h, low, c) > 0 and v >= 0 and h + 1e-12 >= max(o, c) and low - 1e-12 <= min(o, c):
            good.append(list(r))
        else:
            bad += 1
    return good, bad


def progress_path(asset: str) -> Path:
    return DATA / f"{asset.upper()}_1m.alt-progress.json"


def source_path(asset: str) -> Path:
    return DATA / f"{asset.upper()}_1m.source.json"


def fetch_asset(asset: str, venue: Venue, years: float, *, get: Fetch = http_json, pacer: Pacer | None = None,
                now: float | None = None, log: Callable[[str], None] = print) -> dict[str, object]:
    """Walk one coin's 1m candles backward to `years` ago (or listing), appending to its CSV."""
    a = asset.upper()
    pacer = pacer or Pacer(venue.per_second)
    now = time.time() if now is None else now
    end_bound = (int(now) // 60) * 60 - 60            # the last minute that has surely closed
    start_bound = end_bound - int(years * 365 * 86400)
    path, prog = minute_path(a), progress_path(a)
    state = json.loads(prog.read_text()) if prog.exists() else {}
    oldest = int(state.get("oldest", end_bound + 60))
    newest_done = int(state.get("newest", 0))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(",".join(BAR_COLUMNS) + "\n")
    pair = venue.pair(a)
    pages = empty = written = rejected = 0

    def page(start_s: int, end_s: int) -> list[list[float]]:
        nonlocal rejected
        pacer.wait()
        url = venue.url(pair, start_s, end_s)
        payload: object = None
        for attempt in range(4):
            try:
                payload = get(url)
                break
            except urllib.error.HTTPError as exc:
                if attempt == 3 or not (exc.code == 429 or exc.code >= 500):
                    raise AltFetchError(f"{venue.name} {pair}: HTTP {exc.code}") from exc
            except (urllib.error.URLError, OSError, ValueError) as exc:
                if attempt == 3:
                    raise AltFetchError(f"{venue.name} {pair}: {exc}") from exc
            pacer.sleep(2.0 ** attempt)
        rows = [r for r in venue.rows(payload) if start_s <= r[0] <= end_s]
        good, bad = sane(rows)
        if rows and bad / len(rows) > SANITY_FAIL_LIMIT:
            raise AltFetchError(
                f"{venue.name} {pair}: {bad} of {len(rows)} rows have OHLC that cannot be true "
                "(wrong column order?); nothing from this page was written")
        rejected += bad
        return good

    def append(rows: list[list[float]]) -> None:
        nonlocal written
        if rows:
            with path.open("a") as fh:
                fh.write("".join(f"{int(r[0])},{r[1]!r},{r[2]!r},{r[3]!r},{r[4]!r},{r[5]!r}\n" for r in rows))
            written += len(rows)

    def save() -> None:
        prog.write_text(json.dumps({"venue": venue.name, "pair": pair, "oldest": oldest,
                                    "newest": max(newest_done, end_bound),
                                    "requested_start": start_bound, "requested_end": end_bound,
                                    "complete": oldest <= start_bound,
                                    "cache_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}) + "\n")

    # 1) Catch up the minutes after the last run (a resumed or repeated fetch).
    if newest_done:
        cursor = end_bound
        while cursor > newest_done:
            s = max(newest_done + 60, cursor - venue.page_seconds + 60)
            append(page(s, cursor))
            pages += 1
            cursor = s - 60
    # 2) Walk backward from the oldest minute reached toward the start bound.
    cursor = oldest - 60
    while cursor > start_bound:
        s = max(start_bound, cursor - venue.page_seconds + 60)
        rows = page(s, cursor)
        pages += 1
        append(rows)
        empty = 0 if rows else empty + 1
        oldest = s
        cursor = s - 60
        if pages % 50 == 0:
            save()
            log(f"  {a} ({venue.name}): {pages} pages, {written:,} rows, back to "
                f"{time.strftime('%Y-%m-%d', time.gmtime(oldest))}")
        if empty >= EMPTY_PAGES_TO_STOP:
            log(f"  {a} ({venue.name}): {EMPTY_PAGES_TO_STOP} empty pages in a row; treating "
                f"{time.strftime('%Y-%m-%d', time.gmtime(oldest))} as before listing")
            break
    save()
    source_path(a).write_text(json.dumps({
        "asset": a, "venue": venue.name, "pair": pair, "quote": "USDT",
        "fetched_at": int(time.time()), "note": "USDT pair from a non-Coinbase venue; see fetch_minutes_alt.py",
    }, indent=2) + "\n")
    return {"asset": a, "venue": venue.name, "pages": pages, "rows": written, "rejected": rejected}


def finalise(asset: str) -> pd.DataFrame:
    """Sort and de-duplicate the appended CSV in place; return it."""
    path = minute_path(asset)
    df = pd.read_csv(path)
    df = df.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)
    from .fetch import atomic_csv
    atomic_csv(df, path)
    prog = progress_path(asset)
    if prog.exists():
        state = json.loads(prog.read_text())
        state["cache_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        prog.write_text(json.dumps(state) + "\n")
    return df


def coverage(asset: str, frame: pd.DataFrame, years: float):
    """Use this venue's durable receipt, never Coinbase's independent ledger."""
    out = candle_coverage(asset, frame, years)
    try:
        state = json.loads(progress_path(asset).read_text())
        valid = (state.get("complete") is True
                 and state.get("cache_sha256") == hashlib.sha256(minute_path(asset).read_bytes()).hexdigest())
    except (OSError, ValueError, TypeError):
        valid = False
    out.windows_total = 1
    out.windows_done = out.durable_windows = int(valid)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assets", default=",".join(ASSET_VENUE), help="comma list (default: every mapped coin)")
    ap.add_argument("--years", type=float, default=7.0)
    ap.add_argument("--plan", action="store_true", help="print the coin -> venue plan and exit")
    args = ap.parse_args(argv)
    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    unknown = [a for a in assets if a not in ASSET_VENUE]
    if unknown:
        ap.error(f"no venue mapped for {', '.join(unknown)}; known: {', '.join(ASSET_VENUE)}")
    by_venue: dict[str, list[str]] = {}
    for a in assets:
        by_venue.setdefault(ASSET_VENUE[a], []).append(a)
    for v, coins in by_venue.items():
        print(f"{v}: {', '.join(coins)}  ({VENUES[v].per_second:g} req/s, {VENUES[v].page_seconds // 60} min/page)")
    if args.plan:
        return 0
    results: dict[str, dict[str, object]] = {}
    errors: dict[str, str] = {}

    def run_venue(v: str, coins: list[str]) -> None:
        pacer = Pacer(VENUES[v].per_second)  # one pacer per host: the limit is per venue
        for a in coins:
            try:
                results[a] = fetch_asset(a, VENUES[v], args.years, pacer=pacer,
                                         log=lambda s: print(s, flush=True))
                finalise(a)
                print(f"{a} ({v}): done, {results[a]['rows']:,} rows, {results[a]['rejected']} rejected", flush=True)
            except Exception as exc:  # noqa: BLE001 -- surface each asset worker failure in CLI status
                errors[a] = str(exc)
                print(f"{a} ({v}): FAILED {exc}", flush=True)

    threads = [threading.Thread(target=run_venue, args=(v, c)) for v, c in by_venue.items()]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    covs = []
    for a in assets:
        if minute_path(a).exists():
            covs.append(coverage(a, load_minutes(a), args.years))
    if covs:
        print(render_coverage(covs))
        out = write_manifest(covs, MANIFEST)
        manifest = json.loads(out.read_text())
        for row in manifest["assets"]:
            if row.get("asset") in ASSET_VENUE and row.get("asset") in assets:
                row["venue"] = ASSET_VENUE[row["asset"]]
                row["pair_quote"] = "USDT"
        out.write_text(json.dumps(manifest, indent=2) + "\n")
    for a, e in errors.items():
        print(f"FAILED {a}: {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

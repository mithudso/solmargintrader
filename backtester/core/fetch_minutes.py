"""Resumable, parallel 1-minute candle fetch with an honest coverage manifest.

    python3 -m backtester.core.fetch_minutes --asset BTC --years 5
    python3 -m backtester.core.fetch_minutes --all --years 5 --workers 6

## Why this is not `fetch.py`

`fetch_coinbase` chains a cursor: each request's window start comes from the previous
response's oldest bar. That is right for 1,875 daily bars in seven requests. Five years
of minutes is ~2.6M bars per asset over ~8,760 requests, and two things break at that
scale.

**A chained cursor cannot be parallelised.** Request N+1's parameters are unknown until
request N returns. Measured against this endpoint that costs almost everything: the
median response is 0.20s, but ~15% of connections stall until whatever timeout they are
given. Sampling 40 requests gave a 0.20s median with 6 of 40 over a second, an effective
**1.36 req/s** — about five hours per asset. The stalls are per-connection and
independent, so issuing requests concurrently hides them almost entirely (32 requests
across 8 threads completed at ~45 req/s).

So the window list is computed up front from the minute grid instead of discovered. The
windows are deterministic — 300-minute blocks between the requested bounds — which makes
them independent, parallelisable, and individually skippable on resume.

**A long job gets interrupted.** Each completed window is appended to the CSV
immediately and its start recorded in a `.progress.json` sidecar, so a re-run skips what
it already has. Kill it and re-run; it continues. The sidecar tracks *attempted* windows
rather than inferring from the data, because a window legitimately returning fewer than
300 bars (a thin market, an outage) is indistinguishable from one never fetched if you
only look at what landed.

Appending out of order means the file is unsorted until `finalise` runs, so
`load_minutes` sorts defensively rather than trusting it.

## Why the manifest matters more than the CSV

The CSV is gitignored and regenerable. The record of what the venue actually had is not,
because at this granularity two different absences look identical in a bar count:

  * **Short history.** Coinbase serves 1m for BTC back to 2020-07-28, for XRP only to
    2023-07-14 (the relisting, not the asset's start) and for HYPE only to 2026-02-06.
    Pooling a 180-day series with a 2,199-day one and calling it "the top 10 at 1m" is a
    survivorship-filtered universe wearing a full one's name.
  * **Holes.** An outage, a halt, or simply no trade in a minute all yield a missing bar.
    Daily data hides this; minute data is full of it. Every lookback in the engine counts
    BARS, so a window spanning a hole is shorter in time than it claims — a 200-bar mean
    over a stretch missing 20% of its minutes is not a 200-minute mean, and nothing
    downstream can tell.

`coverage()` measures both against the expected grid, and the manifest records them per
asset so the next stage can refuse rather than average over the difference.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .fetch import COINBASE_BASE, COINBASE_ROW, MAX_CANDLES_PER_REQUEST, FetchError
from .types import BAR_COLUMNS

MINUTE = 60
WINDOW_SECONDS = MINUTE * MAX_CANDLES_PER_REQUEST

# Measured, not guessed. fetch.py waits 20s, which is right for seven requests and
# catastrophic for 8,760: a stalled connection is cheaper to abandon than to wait for.
# At a 20s timeout the effective rate was 0.24 req/s; at 3s it was 1.36 req/s
# sequentially, and concurrency takes it to the rate limit below.
REQUEST_TIMEOUT = 3.0
REQUEST_RETRIES = 5

# Coinbase Exchange documents ~10 req/s per IP for public endpoints. Enforced in one
# shared place: per-thread pauses do not bound an aggregate rate, so without this
# raising --workers would walk straight past the venue's limit.
RATE_LIMIT_PER_SECOND = 8.0

# How many consecutive empty windows to believe as "before the listing". One is not
# enough: this venue drops minutes routinely, and first_available's answer is cached.
EMPTY_RUN_TO_BELIEVE = 3

# Coinbase-listed members of the top-10 non-pegged universe. TRX and RAIN are absent
# from the venue entirely -- see backtester/core/universe.py, which documents that
# refusal, and research/TOP_COINS.md for the ranking this is drawn from.
MINUTE_ASSETS = ("BTC", "ETH", "SOL", "DOGE", "ZEC", "XRP", "BNB", "HYPE")

DATA = Path("data")
MANIFEST = Path("research/results/minute_coverage.json")


class RateLimiter:
    """Token bucket shared by every worker thread."""

    def __init__(self, per_second: float) -> None:
        self._min_interval = 1.0 / per_second
        self._lock = threading.Lock()
        self._next = 0.0

    def acquire(self) -> None:
        with self._lock:
            now = time.monotonic()
            wait = max(0.0, self._next - now)
            self._next = max(now, self._next) + self._min_interval
        if wait:
            time.sleep(wait)


def _retry_after(exc: urllib.error.HTTPError, attempt: int) -> float:
    """The venue's own Retry-After if it sent one, else a bounded geometric back-off."""
    header = exc.headers.get("Retry-After") if exc.headers else None
    if header:
        try:
            return min(30.0, float(header))
        except (TypeError, ValueError):
            pass
    return min(8.0, 0.5 * 2 ** attempt)


def get_candles(url: str, limiter: RateLimiter | None = None) -> list:
    """One candles request, with a short timeout and immediate retries.

    Deliberately not fetch._get_json: that waits 20s on a stall and then backs off,
    both of which are the wrong trade at this request count. No backoff here because
    the stall is per-connection -- a fresh attempt is normally served at once.
    """
    last: Exception | None = None
    for attempt in range(REQUEST_RETRIES):
        if limiter is not None:
            limiter.acquire()
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "solmargintrader-research/1.0"}
            )
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.load(response)
            if isinstance(payload, dict):
                # The venue reports errors as a JSON object, not an HTTP status.
                raise FetchError(f"venue refused the request: {payload.get('message')}")
            return payload
        except urllib.error.HTTPError as exc:
            # HTTPError subclasses URLError, so without this clause a 429 falls into the
            # no-backoff path below and is hammered five times in ~600ms -- which is how
            # a rate limit becomes a ban. A non-429 4xx will not change on retry.
            if exc.code != 429 and exc.code < 500:
                raise FetchError(
                    f"venue rejected the request ({exc.code}): {url}") from exc
            last = exc
            time.sleep(_retry_after(exc, attempt))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            # A transport stall is per-connection, so retry at once -- but not five times
            # in a row against a venue that may simply be unwell. Ramp gently.
            time.sleep(min(2.0, 0.1 * attempt))
    raise FetchError(
        f"failed after {REQUEST_RETRIES} attempts: {last}. Check connectivity; "
        "do not substitute synthetic data for a real-data run."
    ) from last


@dataclass
class Coverage:
    """What the venue actually served for one asset, as opposed to what was asked for."""

    asset: str
    bars: int = 0
    first: str = ""
    last: str = ""
    span_days: float = 0.0
    expected_bars: int = 0
    missing_bars: int = 0
    completeness: float = 0.0
    gaps_over_an_hour: int = 0
    largest_gap_minutes: int = 0
    requested_years: float = 0.0
    short_of_request_days: float = 0.0
    windows_done: int = 0
    windows_total: int = 0

    @property
    def complete_fetch(self) -> bool:
        """Every planned window attempted AND bars actually present.

        The bar check is not redundant. The ledger and the CSV are separate files, so a
        truncated or empty CSV beside a full sidecar would otherwise report "full" -- and
        because a full ledger makes the next run's `todo` empty, nothing would ever
        correct it. Distinct from covering the full request, which is span_days.
        """
        return (self.windows_total > 0
                and self.windows_done >= self.windows_total
                and self.bars > 0)

    def as_dict(self) -> dict:
        out = dict(self.__dict__)
        out["complete_fetch"] = self.complete_fetch
        return out


def minute_path(asset: str) -> Path:
    """Cache location for one asset's 1m bars."""
    return DATA / f"{asset.upper()}_1m.csv"


def progress_path(asset: str) -> Path:
    """Sidecar recording which windows have been attempted."""
    return DATA / f"{asset.upper()}_1m.progress.json"


def plan_windows(years: float, now: int | None = None) -> list[int]:
    """Window start timestamps, oldest first, on a fixed grid.

    Deterministic so that a resumed run plans exactly the same windows and can skip the
    ones already attempted. Anchored to the grid rather than to "now" for the same
    reason -- an anchor that moved between runs would make the sidecar meaningless.
    """
    end = (now if now is not None else int(pd.Timestamp.now(tz="UTC").timestamp()))
    # Floored to the WINDOW grid, not the minute. Flooring to the minute made the final
    # range element a window whose request end is up to five hours in the FUTURE: it came
    # back partial, was recorded done unconditionally, and was an interior member of every
    # later plan -- so its missing minutes were never refetched and no count revealed it.
    # Measured on disk before the fix: a BTC window holding 61 of 300 bars, marked done,
    # while the report said the fetch was full.
    end -= end % WINDOW_SECONDS
    start = end - int(years * 365 * 86400)
    start -= start % WINDOW_SECONDS
    return list(range(start, end, WINDOW_SECONDS))


def _candles_url(product: str, window_start: int) -> str:
    """The one place a candles request is spelled, so probe and fetch cannot diverge."""
    end = window_start + WINDOW_SECONDS
    return (f"{COINBASE_BASE}/products/{product}/candles?granularity={MINUTE}"
            f"&start={pd.Timestamp(window_start, unit='s', tz='UTC').isoformat()}"
            f"&end={pd.Timestamp(end, unit='s', tz='UTC').isoformat()}")


def first_available(asset: str, years: float, limiter: RateLimiter | None = None,
                    now: int | None = None) -> int:
    """Binary-search the oldest window the venue actually serves for this asset.

    Worth ~13 requests because the alternative is thousands of wasted ones. Planning
    five years for every asset means BNB (listed ~286 days ago), HYPE (~180) and XRP
    (~1,118, its relisting) would each have thousands of windows fetched only to return
    empty -- about 22,000 of 70,000 requests across the universe, roughly an hour.
    """
    windows = plan_windows(years, now)
    if not windows:
        return 0
    product = f"{asset.upper()}-USD"

    def has_data(window_start: int) -> bool:
        return bool(get_candles(_candles_url(product, window_start), limiter))

    def before_listing(index: int) -> bool:
        """True only when a RUN of consecutive windows from here is empty.

        A halt, or five quiet hours, returns the same empty list as "before the listing",
        and this function's answer is written to the sidecar -- so treating one empty
        window as the boundary discards history permanently. Erring low costs a couple of
        wasted requests, which is the cheap direction.
        """
        for offset in range(EMPTY_RUN_TO_BELIEVE):
            probe_index = index + offset
            if probe_index >= len(windows):
                break
            if has_data(windows[probe_index]):
                return False
        return True

    lo, hi = 0, len(windows) - 1
    if not before_listing(lo):
        return windows[lo]
    if before_listing(hi):
        raise FetchError(f"{asset}: the venue serves no 1m candles even for the most "
                         "recent window; check the product is listed")
    # Invariant: a run from windows[lo] is empty, windows[hi] is inside served history.
    while lo < hi - 1:
        mid = (lo + hi) // 2
        if before_listing(mid):
            lo = mid
        else:
            hi = mid
    return windows[hi]


def effective_windows(asset: str, years: float, limiter: RateLimiter | None = None,
                      now: int | None = None, probe: bool = True) -> list[int]:
    """The windows worth fetching: the planned grid from the listing start onward."""
    windows = plan_windows(years, now)
    if not probe or not windows:
        return windows
    cached = load_probe(asset)
    if cached is not None and cached[1] <= windows[0]:
        start = cached[0]
    else:
        # This plan reaches further back than the cached probe searched, so the cached
        # answer cannot rule anything out down here. One extra request beats capping the
        # run: an unprobed --years 6 would silently return five years and call it full.
        start = first_available(asset, years, limiter, now)
        save_listing_start(asset, start, windows[0])
    return [w for w in windows if w >= start]


def load_probe(asset: str) -> tuple[int, int] | None:
    """The probed listing start and the plan floor the probe searched from.

    The floor is load-bearing. `first_available` early-exits at `windows[0]`, so a probe
    made under `--years 1` can only report "there was data at the one-year floor". Reused
    by a `--years 5` run it caps that run at one year while `complete_fetch` still reports
    True -- five years requested, one delivered, nothing in the output saying so.
    """
    path = progress_path(asset)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        start, floor = data.get("listing_start"), data.get("probe_floor")
        if start is None or floor is None:
            return None
        return int(start), int(floor)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def load_listing_start(asset: str) -> int | None:
    """The probed listing start, ignoring a probe that searched no deeper than needed."""
    probe = load_probe(asset)
    return None if probe is None else probe[0]


def save_listing_start(asset: str, start: int, probe_floor: int) -> None:
    """Record the probe result and the floor it searched from."""
    _write_sidecar(asset, load_progress(asset), start, probe_floor)


def load_progress(asset: str) -> set[int]:
    """Window starts already attempted for this asset."""
    path = progress_path(asset)
    if not path.exists():
        return set()
    try:
        return {int(x) for x in json.loads(path.read_text()).get("windows_done", [])}
    except (json.JSONDecodeError, ValueError, TypeError):
        # A truncated sidecar must not abort the run; refetching is merely slower,
        # whereas crashing on it would strand a job that is otherwise fine.
        print(f"  {asset}: unreadable progress sidecar, refetching all windows",
              file=sys.stderr)
        return set()


def save_progress(asset: str, done: set[int]) -> None:
    """Persist attempted windows without discarding the probe result."""
    probe = load_probe(asset)
    _write_sidecar(asset, done, *(probe if probe is not None else (None, None)))


def _write_sidecar(asset: str, done: set[int], listing_start: int | None,
                   probe_floor: int | None = None) -> None:
    """Write the sidecar whole, then rename, so a crash cannot half-update it."""
    path = progress_path(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Per-process tmp name: two fetches of one asset would otherwise interleave their
    # write-then-rename and lose one another's windows.
    tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
    payload: dict = {"windows_done": sorted(done)}
    if listing_start is not None:
        payload["listing_start"] = int(listing_start)
        payload["probe_floor"] = int(
            probe_floor if probe_floor is not None else listing_start)
    tmp.write_text(json.dumps(payload))
    tmp.replace(path)


def load_minutes(asset: str) -> pd.DataFrame:
    """Read an asset's 1m cache, sorted and de-duplicated.

    Sorting here rather than trusting the file is deliberate: windows are appended as
    they complete, in whatever order they finish.
    """
    path = minute_path(asset)
    if not path.exists() or path.stat().st_size == 0:
        raise FetchError(f"no 1m cache for {asset}: run fetch_minutes --asset {asset}")
    df = pd.read_csv(path)
    return (
        df.drop_duplicates(subset="timestamp")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def coverage(asset: str, df: pd.DataFrame, requested_years: float) -> Coverage:
    """Measure the series against the minute grid it claims to cover."""
    out = Coverage(asset=asset, requested_years=requested_years)
    listing_start = load_listing_start(asset)
    planned = plan_windows(requested_years)
    if listing_start is not None:
        planned = [w for w in planned if w >= listing_start]
    out.windows_total = len(planned)
    out.windows_done = len({w for w in load_progress(asset) if w in set(planned)})
    if df.empty:
        return out
    ts = df["timestamp"].to_numpy(dtype="int64")
    out.bars = int(len(ts))
    out.first = str(pd.Timestamp(ts.min(), unit="s", tz="UTC"))
    out.last = str(pd.Timestamp(ts.max(), unit="s", tz="UTC"))
    span = int(ts.max() - ts.min())
    out.span_days = round(span / 86400.0, 1)
    out.expected_bars = span // MINUTE + 1          # inclusive of both ends
    out.missing_bars = max(0, out.expected_bars - out.bars)
    out.completeness = round(out.bars / out.expected_bars, 6) if out.expected_bars else 0.0
    deltas = np.diff(ts)
    if len(deltas):
        out.largest_gap_minutes = int(deltas.max() // MINUTE)
        out.gaps_over_an_hour = int((deltas > 3600).sum())
    out.short_of_request_days = round(max(0.0, requested_years * 365.0 - out.span_days), 1)
    return out


def _window_frame(rows: list) -> pd.DataFrame:
    """Coinbase's positional rows as a bar frame."""
    arr = np.asarray(rows, dtype="float64")
    idx = {name: k for k, name in enumerate(COINBASE_ROW)}
    frame = pd.DataFrame({
        "timestamp": arr[:, idx["time"]].astype("int64"),
        "open": arr[:, idx["open"]],
        "high": arr[:, idx["high"]],
        "low": arr[:, idx["low"]],
        "close": arr[:, idx["close"]],
        "volume": arr[:, idx["volume"]],
    }).sort_values("timestamp")
    return frame.loc[:, list(BAR_COLUMNS)]


def fetch_minutes(
    asset: str,
    years: float,
    *,
    workers: int = 6,
    limiter: RateLimiter | None = None,
    resume: bool = True,
    max_windows: int | None = None,
    verbose: bool = True,
) -> Coverage:
    """Fetch `years` of 1m candles for `asset` in parallel, appending as windows land.

    Returns coverage for whatever is on disk afterwards -- including when the venue ran
    out of history early, which is the common case and not an error.
    """
    product = f"{asset.upper()}-USD"
    path = minute_path(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    limiter = limiter or RateLimiter(RATE_LIMIT_PER_SECOND)

    planned = effective_windows(asset, years, limiter, probe=resume)
    done = load_progress(asset) if resume else set()
    todo = [w for w in planned if w not in done]
    if max_windows is not None:
        # Newest first when piloting: a partial run should hold recent data, which is
        # what a smoke test wants to look at.
        todo = sorted(todo, reverse=True)[:max_windows]
    if verbose:
        print(f"  {asset}: {len(planned):,} windows planned, {len(done):,} already done, "
              f"{len(todo):,} to fetch", file=sys.stderr)
    if not todo:
        return coverage(asset, load_minutes(asset) if path.exists()
                        else pd.DataFrame(columns=list(BAR_COLUMNS)), years)

    def fetch_one(window_start: int) -> tuple[int, pd.DataFrame | None]:
        end = window_start + WINDOW_SECONDS
        url = (f"{COINBASE_BASE}/products/{product}/candles?granularity={MINUTE}"
               f"&start={pd.Timestamp(window_start, unit='s', tz='UTC').isoformat()}"
               f"&end={pd.Timestamp(end, unit='s', tz='UTC').isoformat()}")
        rows = get_candles(url, limiter)
        return window_start, (_window_frame(rows) if rows else None)

    header_needed = not path.exists() or path.stat().st_size == 0
    empty = 0
    failed = 0
    t0 = time.time()
    completed = 0
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        with path.open("a") as handle:
            futures = {pool.submit(fetch_one, w): w for w in todo}
            try:
                for future in as_completed(futures):
                    try:
                        window_start, frame = future.result()
                    except FetchError:
                        # One window exhausting its retries must not lose the other 8,759.
                        # This is not hypothetical: the first full run died exactly here,
                        # on a single read timeout, two assets in. The window is left out
                        # of `done` so a later run retries it.
                        failed += 1
                        continue
                    done.add(window_start)
                    completed += 1
                    if frame is None:
                        empty += 1
                    else:
                        frame.to_csv(handle, header=header_needed, index=False)
                        header_needed = False
                    if completed % 500 == 0:
                        handle.flush()
                        save_progress(asset, done)
                        if verbose:
                            rate = completed / max(1e-9, time.time() - t0)
                            left = (len(todo) - completed) / max(1e-9, rate) / 60.0
                            print(f"  {asset}: {completed:,}/{len(todo):,} windows, "
                                  f"{rate:.1f}/s, {failed} failed, ~{left:.0f} min left",
                                  file=sys.stderr)
            finally:
                # Record what landed before anything else can leave this block. These rows
                # are already in the CSV; a ledger that omits them makes the next run
                # refetch up to a full checkpoint interval for no reason.
                handle.flush()
                save_progress(asset, done)
    finally:
        # Without cancel_futures every remaining window is still fetched before an
        # exception surfaces -- ~18 min of requests at 8,760 windows, against a venue that
        # just refused one. Workers touch only the limiter and the socket, never `handle`.
        pool.shutdown(wait=False, cancel_futures=True)

    df = finalise(asset)
    cov = coverage(asset, df, years)
    if verbose:
        print(f"  {asset}: {cov.bars:,} bars, {completed:,} windows "
              f"({empty:,} empty -- before listing, {failed:,} failed and left for a "
              f"re-run), {(time.time()-t0)/60:.1f} min, "
              f"{cov.completeness:.1%} of the minute grid", file=sys.stderr)
    return cov


def finalise(asset: str) -> pd.DataFrame:
    """Sort, de-duplicate and rewrite the cache atomically; return the clean frame.

    Renamed into place for the same reason as _write_sidecar, which needs it far less:
    an interrupted in-place rewrite leaves a stump that the sidecar still records as
    complete, so `todo` is empty on the next run, finalise never runs again, and the
    coverage report presents the stump as the venue's full history. There is no recovery
    path from that except deleting both files.
    """
    df = load_minutes(asset)
    path = minute_path(asset)
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    return df


def write_manifest(covs: list[Coverage], path: Path = MANIFEST) -> Path:
    """Record per-asset coverage next to the results the backtest will write."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "generated": str(pd.Timestamp.now(tz="UTC")),
        "interval": "1m",
        "venue": "coinbase-exchange",
        "note": (
            "span_days is calendar covered; completeness is how much of that calendar's "
            "minute grid is present. A bar count cannot tell short history from holes."
        ),
        "assets": [c.as_dict() for c in sorted(covs, key=lambda c: -c.span_days)],
    }, indent=2) + "\n")
    return path


def render_coverage(covs: list[Coverage]) -> str:
    """Coverage table, with the shortfall stated rather than left to be inferred."""
    lines = [
        f"{'asset':<6}{'bars':>12}{'first':>12}{'span d':>8}{'complete':>10}"
        f"{'gaps>1h':>9}{'max gap':>9}{'short by':>10}{'fetch':>8}",
        "-" * 84,
    ]
    for c in sorted(covs, key=lambda c: -c.span_days):
        short = f"{c.short_of_request_days:.0f}d" if c.short_of_request_days > 1 else "-"
        lines.append(
            f"{c.asset:<6}{c.bars:>12,}{c.first[:10]:>12}{c.span_days:>8.0f}"
            f"{c.completeness:>9.1%}{c.gaps_over_an_hour:>9,}"
            f"{c.largest_gap_minutes:>9,}{short:>10}"
            f"{'full' if c.complete_fetch else 'PARTIAL':>8}"
        )
    full = [c.asset for c in covs if c.short_of_request_days <= 1]
    shortfall = [c for c in covs if c.short_of_request_days > 1]
    partial = [c.asset for c in covs if not c.complete_fetch]
    lines += [
        "",
        f"cover the full request ({len(full)}): {', '.join(full) or 'none'}",
        f"short of it ({len(shortfall)}): " + (", ".join(
            f"{c.asset} by {c.short_of_request_days:.0f}d"
            for c in sorted(shortfall, key=lambda c: -c.short_of_request_days)) or "none"),
    ]
    if partial:
        lines.append(f"INCOMPLETE FETCH ({len(partial)}): {', '.join(partial)} -- re-run "
                     "to continue; these are not yet the venue's full history")
    lines += [
        "",
        "'short by' is missing CALENDAR (the venue has no more). 'complete' is missing",
        "MINUTES inside the calendar it does cover. They are different problems and",
        "a bar count alone cannot distinguish them.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Resumable parallel 1-minute candle fetch.")
    ap.add_argument("--asset", action="append", default=[],
                    help="asset symbol; repeatable")
    ap.add_argument("--all", action="store_true", help=f"fetch {', '.join(MINUTE_ASSETS)}")
    ap.add_argument("--years", type=float, default=5.0)
    ap.add_argument("--workers", type=int, default=6,
                    help="concurrent requests (default 6); the shared rate limit still "
                         f"caps aggregate throughput at {RATE_LIMIT_PER_SECOND:.0f}/s")
    ap.add_argument("--max-windows", type=int, default=None,
                    help="stop after N windows per asset; for piloting")
    ap.add_argument("--no-resume", action="store_true",
                    help="refetch every window, ignoring the progress sidecar")
    ap.add_argument("--coverage-only", action="store_true",
                    help="re-measure what is on disk; fetch nothing")
    args = ap.parse_args(argv)

    if args.years <= 0:
        ap.error("--years must be positive")
    if args.workers < 1:
        ap.error("--workers must be at least 1")
    if args.max_windows is not None and args.max_windows < 1:
        # Negative slices todo[:-n], which fetches everything EXCEPT the oldest n -- the
        # opposite of piloting. Zero fetches nothing and still rewrote the manifest.
        ap.error("--max-windows must be at least 1")

    assets = [a.upper() for a in args.asset] or (list(MINUTE_ASSETS) if args.all else [])
    if not assets:
        ap.error("pass --asset SYM (repeatable) or --all")
    unknown = [a for a in assets if a not in MINUTE_ASSETS]
    if unknown:
        ap.error(
            f"{', '.join(unknown)} not among the Coinbase-listed universe "
            f"({', '.join(MINUTE_ASSETS)}). TRX and RAIN are not listed on the venue at "
            "all -- see backtester/core/universe.py."
        )

    # One limiter across every asset: the venue limits per IP, not per asset.
    limiter = RateLimiter(RATE_LIMIT_PER_SECOND)
    covs = []
    for asset in assets:
        if args.coverage_only:
            frame = load_minutes(asset) if minute_path(asset).exists() else pd.DataFrame(
                columns=list(BAR_COLUMNS))
            covs.append(coverage(asset, frame, args.years))
            continue
        covs.append(fetch_minutes(
            asset, args.years, workers=args.workers, limiter=limiter,
            resume=not args.no_resume, max_windows=args.max_windows,
        ))

    print(render_coverage(covs))
    if args.max_windows is None:
        print(f"\nwrote {write_manifest(covs)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

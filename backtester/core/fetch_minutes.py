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
import hashlib
import json
import math
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
from .market_diagnostics import market_request
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


# Coinbase-listed members of the active screened universe. TRX is absent from the
# venue entirely -- see backtester/core/universe.py and research/TOP_COINS.md.
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
            delay = float(header)
            if math.isfinite(delay) and delay >= 0:
                return min(30.0, delay)
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
            with market_request("coinbase_minutes"), urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                payload = json.load(response)
            if isinstance(payload, dict):
                # The venue reports errors as a JSON object, not an HTTP status.
                raise FetchError(f"venue refused the request: {payload.get('message')}")
            if not isinstance(payload, list):
                raise FetchError("candle response must be a list; malformed window remains retryable")
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
    hours_behind_live: float = 0.0
    durable_windows: int = 0

    @property
    def complete_fetch(self) -> bool:
        """Every window in the plan AS PLANNED attempted, and bars actually present.

        "As planned" is load-bearing and was originally missing. plan_windows is anchored
        to `now`, so re-measuring hours later planned windows that did not exist when the
        fetch ran and flipped this to False for seven of eight assets with nothing wrong
        on disk -- and render_coverage turned that into "re-run to continue", which was
        simply false. The plan end is recorded at fetch time and reused, so the verdict is
        reproducible; how current the data is is reported separately as hours_behind_live.

        The bar check is not redundant. The ledger and the CSV are separate files, so a
        truncated or empty CSV beside a full sidecar would otherwise report "full" -- and
        because a full ledger makes the next run's `todo` empty, nothing would ever
        correct it. Distinct from covering the full request, which is span_days.
        """
        return (self.windows_total > 0
                and self.windows_done >= self.windows_total
                and self.durable_windows >= self.windows_total
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
    """Find the first served window without assuming outages are listing bounds.

    Only an exhaustively checked empty prefix can exclude older windows. Empty
    midpoint runs are not monotone evidence: venues also have internal outages.
    """
    windows = plan_windows(years, now)
    if not windows:
        return 0
    product = f"{asset.upper()}-USD"
    for window_start in windows:
        if get_candles(_candles_url(product, window_start), limiter):
            return window_start
    raise FetchError(f"{asset}: the venue serves no 1m candles in the requested windows; "
                     "check the product is listed")


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
        data = _progress_document(path)
        start, floor = data.get("listing_start"), data.get("probe_floor")
        if start is None or floor is None or data.get("probe_method") != "prefix-scan-v1":
            return None
        return int(start), int(floor)
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def load_planned_end(asset: str) -> int | None:
    """The plan end recorded when this asset was last fetched, if any."""
    path = progress_path(asset)
    if not path.exists():
        return None
    try:
        value = _progress_document(path).get("planned_end")
        return int(value) if value is not None else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def load_listing_start(asset: str) -> int | None:
    """The probed listing start, ignoring a probe that searched no deeper than needed."""
    probe = load_probe(asset)
    return None if probe is None else probe[0]


def save_listing_start(asset: str, start: int, probe_floor: int) -> None:
    """Record the probe result and the floor it searched from."""
    _write_sidecar(asset, load_progress(asset), start, probe_floor,
                   planned_end=load_planned_end(asset))


def load_progress(asset: str) -> set[int]:
    """Window starts already attempted for this asset."""
    path = progress_path(asset)
    if not path.exists():
        return set()
    try:
        return {int(x) for x in _progress_document(path).get("windows_done", [])}
    except (json.JSONDecodeError, ValueError, TypeError):
        # A truncated sidecar must not abort the run; refetching is merely slower,
        # whereas crashing on it would strand a job that is otherwise fine.
        print(f"  {asset}: unreadable progress sidecar, refetching all windows",
              file=sys.stderr)
        return set()


def _progress_document(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("progress sidecar must be an object")
    return data


def load_window_receipts(asset: str) -> dict[int, dict]:
    try:
        payload = json.loads(progress_path(asset).read_text()).get("window_rows", {})
        return {int(key): value for key, value in payload.items() if isinstance(value, dict)}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def observed_windows(frame: pd.DataFrame) -> dict[int, dict]:
    """Bind the exact observed minute timestamps, including sparse windows."""
    if frame.empty:
        return {}
    timestamps = frame["timestamp"].to_numpy(dtype="float64")
    if (not np.isfinite(timestamps).all() or (timestamps != np.floor(timestamps)).any()
            or (timestamps % MINUTE != 0).any()):
        return {}
    timestamps = np.unique(timestamps.astype("int64"))
    buckets, starts, counts = np.unique(timestamps // WINDOW_SECONDS * WINDOW_SECONDS,
                                        return_index=True, return_counts=True)
    return {int(bucket): {"count": int(count),
                         "timestamps_sha256": hashlib.sha256(timestamps[start:start + count].tobytes()).hexdigest()}
            for bucket, start, count in zip(buckets, starts, counts)}


def _empty_window() -> dict:
    return {"count": 0, "timestamps_sha256": hashlib.sha256(b"").hexdigest()}


def save_progress(asset: str, done: set[int], planned_end: int | None = None, *, receipts: dict | None = None) -> None:
    """Persist attempted windows without discarding the probe result or the plan end."""
    probe = load_probe(asset)
    _write_sidecar(asset, done, *(probe if probe is not None else (None, None)),
                   planned_end=planned_end if planned_end is not None
                   else load_planned_end(asset), receipts=receipts)


def _write_sidecar(asset: str, done: set[int], listing_start: int | None,
                   probe_floor: int | None = None,
                   planned_end: int | None = None, receipts: dict | None = None) -> None:
    """Write the sidecar whole, then rename, so a crash cannot half-update it."""
    path = progress_path(asset)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Per-process tmp name: two fetches of one asset would otherwise interleave their
    # write-then-rename and lose one another's windows.
    tmp = path.with_suffix(f".json.{os.getpid()}.tmp")
    payload: dict = {"windows_done": sorted(done),
                     "window_rows": load_window_receipts(asset) if receipts is None else receipts}
    if listing_start is not None:
        payload["probe_method"] = "prefix-scan-v1"
        payload["listing_start"] = int(listing_start)
        payload["probe_floor"] = int(
            probe_floor if probe_floor is not None else listing_start)
    if planned_end is not None:
        payload["planned_end"] = int(planned_end)
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
        df.drop_duplicates(subset="timestamp", keep="last")
        .sort_values("timestamp")
        .reset_index(drop=True)
    )


def coverage(asset: str, df: pd.DataFrame, requested_years: float,
             now: int | None = None) -> Coverage:
    """Measure the series against the minute grid it claims to cover.

    `now` defaults to the plan end recorded when the fetch ran, NOT to the wall clock --
    see Coverage.complete_fetch for why that distinction produced a false "PARTIAL".
    """
    out = Coverage(asset=asset, requested_years=requested_years)
    probe = load_probe(asset)
    if now is None:
        now = load_planned_end(asset)
    planned = plan_windows(requested_years, now)
    if probe is not None and planned and probe[1] <= planned[0]:
        planned = [w for w in planned if w >= probe[0]]
    out.windows_total = len(planned)
    planned_set = set(planned)
    done = {w for w in load_progress(asset) if w in planned_set}
    out.windows_done = len(done)
    receipts, observed = load_window_receipts(asset), observed_windows(df)
    out.durable_windows = sum(
        (receipts[w] == observed.get(w, _empty_window()) if w in receipts
         else observed.get(w, {}).get("count") == MAX_CANDLES_PER_REQUEST)
        for w in done)
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
    # Staleness as its own number rather than disguised as an incomplete fetch.
    live = int(pd.Timestamp.now(tz="UTC").timestamp())
    out.hours_behind_live = round(max(0.0, (live - int(ts.max())) / 3600.0), 1)
    return out


def _window_frame(rows: list) -> pd.DataFrame:
    """Coinbase's positional rows as a bar frame."""
    try:
        arr = np.asarray(rows, dtype="float64")
    except (TypeError, ValueError) as exc:
        raise FetchError("candle response must contain numeric OHLCV rows") from exc
    if arr.ndim != 2 or arr.shape[1] != len(COINBASE_ROW) or not np.isfinite(arr).all():
        raise FetchError("candle response must contain six finite values per row")
    stamps = arr[:, 0]
    if np.any(np.abs(stamps) > 10_000_000_000) or np.any(stamps != np.floor(stamps)) or np.any(stamps % MINUTE):
        raise FetchError("candle timestamps must be integral minute-aligned epoch seconds")
    idx = {name: k for k, name in enumerate(COINBASE_ROW)}
    frame = pd.DataFrame({
        "timestamp": arr[:, idx["time"]].astype("int64"),
        "open": arr[:, idx["open"]],
        "high": arr[:, idx["high"]],
        "low": arr[:, idx["low"]],
        "close": arr[:, idx["close"]],
        "volume": arr[:, idx["volume"]],
    }).sort_values("timestamp")
    if (frame[["open", "high", "low", "close"]] <= 0).any().any() or (frame["volume"] < 0).any():
        raise FetchError("candle prices must be positive and volume nonnegative")
    if ((frame["high"] < frame[["open", "close", "low"]].max(axis=1)) |
            (frame["low"] > frame[["open", "close"]].min(axis=1))).any():
        raise FetchError("candle high/low must contain the open and close")
    if frame["timestamp"].duplicated().any():
        raise FetchError("candle timestamps must be distinct")
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
    # The end of the plan AS PLANNED NOW. Recorded so a later coverage run measures
    # against this plan rather than against a plan that has since grown (see
    # Coverage.complete_fetch).
    plan_end = (planned[-1] + WINDOW_SECONDS) if planned else None
    receipts = load_window_receipts(asset) if resume else {}
    cached = load_minutes(asset) if path.exists() and path.stat().st_size else pd.DataFrame(columns=list(BAR_COLUMNS))
    observed = observed_windows(cached)
    done = {w for w in load_progress(asset)
            if (receipts[w] == observed.get(w, _empty_window()) if w in receipts
                else observed.get(w, {}).get("count") == MAX_CANDLES_PER_REQUEST)} if resume else set()
    todo = [w for w in planned if w not in done]
    if max_windows is not None:
        # Newest first when piloting: a partial run should hold recent data, which is
        # what a smoke test wants to look at.
        todo = sorted(todo, reverse=True)[:max_windows]
    if verbose:
        print(f"  {asset}: {len(planned):,} windows planned, {len(done):,} already done, "
              f"{len(todo):,} to fetch", file=sys.stderr)
    if not todo:
        if plan_end is not None:
            save_progress(asset, done, planned_end=plan_end, receipts=receipts)
        return coverage(asset, load_minutes(asset) if path.exists()
                        else pd.DataFrame(columns=list(BAR_COLUMNS)), years)

    def fetch_one(window_start: int) -> tuple[int, pd.DataFrame | None]:
        end = window_start + WINDOW_SECONDS
        url = (f"{COINBASE_BASE}/products/{product}/candles?granularity={MINUTE}"
               f"&start={pd.Timestamp(window_start, unit='s', tz='UTC').isoformat()}"
               f"&end={pd.Timestamp(end, unit='s', tz='UTC').isoformat()}")
        rows = get_candles(url, limiter)
        frame = _window_frame(rows) if rows else None
        # Coinbase may include the requested endpoint. It belongs to the next
        # window; discard it without allowing unrelated out-of-window history.
        if frame is not None:
            if ((frame["timestamp"] < window_start) | (frame["timestamp"] > end)).any():
                raise FetchError("candle response falls outside its requested window")
            frame = frame[frame["timestamp"] < end]
        return window_start, frame

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
                    if frame is None:
                        empty += 1
                    else:
                        # Roll a partial append back to its prior boundary so a
                        # resume cannot inherit a malformed half-row/header.
                        offset = handle.tell()
                        try:
                            frame.to_csv(handle, header=header_needed, index=False)
                            handle.flush()
                            os.fsync(handle.fileno())
                        except BaseException:
                            handle.seek(offset)
                            handle.truncate()
                            handle.flush()
                            raise
                        header_needed = False
                    receipts[window_start] = observed_windows(frame).get(window_start, _empty_window()) if frame is not None else _empty_window()
                    done.add(window_start)
                    completed += 1
                    if completed % 500 == 0:
                        handle.flush()
                        save_progress(asset, done, receipts=receipts)
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
                save_progress(asset, done, planned_end=plan_end, receipts=receipts)
    finally:
        # Without cancel_futures every remaining window is still fetched before an
        # exception surfaces -- ~18 min of requests at 8,760 windows, against a venue that
        # just refused one. Workers touch only the limiter and the socket, never `handle`.
        pool.shutdown(wait=False, cancel_futures=True)

    df = finalise(asset)
    cov = coverage(asset, df, years)
    if verbose:
        print(f"  {asset}: {cov.bars:,} bars, {completed:,} windows "
              f"({empty:,} empty responses, {failed:,} failed and left for a "
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
    path = minute_path(asset)
    df = load_minutes(asset) if path.exists() and path.stat().st_size else pd.DataFrame(columns=list(BAR_COLUMNS))
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    return df


def write_manifest(covs: list[Coverage], path: Path = MANIFEST) -> Path:
    """Record per-asset coverage next to the results the backtest will write.

    Entries for assets not in this run are KEPT: a run over three coins must not erase the
    record of the other thirty.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fresh = {c.asset: c.as_dict() for c in covs}
    kept: list[dict] = []
    if path.exists():
        try:
            kept = [a for a in json.loads(path.read_text()).get("assets", [])
                    if isinstance(a, dict) and a.get("asset") not in fresh]
        except (OSError, ValueError):
            kept = []
    rows = kept + list(fresh.values())
    path.write_text(json.dumps({
        "generated": str(pd.Timestamp.now(tz="UTC")),
        "interval": "1m",
        "venue": "coinbase-exchange",
        "note": (
            "span_days is calendar covered; completeness is how much of that calendar's "
            "minute grid is present. A bar count cannot tell short history from holes."
        ),
        "assets": sorted(rows, key=lambda a: -float(a.get("span_days") or 0)),
    }, indent=2) + "\n")
    return path


def render_coverage(covs: list[Coverage]) -> str:
    """Coverage table, with the shortfall stated rather than left to be inferred."""
    lines = [
        f"{'asset':<6}{'bars':>12}{'first':>12}{'span d':>8}{'complete':>10}"
        f"{'gaps>1h':>9}{'max gap':>9}{'short by':>10}{'behind':>9}{'fetch':>8}",
        "-" * 93,
    ]
    for c in sorted(covs, key=lambda c: -c.span_days):
        short = f"{c.short_of_request_days:.0f}d" if c.short_of_request_days > 1 else "-"
        lines.append(
            f"{c.asset:<6}{c.bars:>12,}{c.first[:10]:>12}{c.span_days:>8.0f}"
            f"{c.completeness:>9.1%}{c.gaps_over_an_hour:>9,}"
            f"{c.largest_gap_minutes:>9,}{short:>10}"
            f"{(str(round(c.hours_behind_live)) + 'h') if c.hours_behind_live >= 1 else '-':>9}"
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
        "",
        "'behind' is how far the newest bar is from live, which is NOT an incomplete",
        "fetch -- it just means time has passed. 'fetch' is measured against the plan as",
        "it stood when the fetch ran, so it does not drift as the clock advances.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description="Resumable parallel 1-minute candle fetch.",
                                 epilog="Example: python -m backtester.core.fetch_minutes --asset BTC --years 1 --max-windows 1")
    ap.add_argument("--asset", action="append", default=[],
                    help="asset symbol; repeatable")
    ap.add_argument("--all", action="store_true", help=f"fetch {', '.join(MINUTE_ASSETS)}")
    ap.add_argument("--assets", default="",
                    help="comma list of symbols; any coin Coinbase lists against USD is accepted")
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

    assets = [a.upper() for a in args.asset]
    assets += [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    if args.all:
        assets += list(MINUTE_ASSETS)
    assets = list(dict.fromkeys(assets))
    if not assets:
        ap.error("pass --asset SYM (repeatable), --assets A,B,C or --all")
    from .assets import REMOVED_ASSETS

    removed = sorted(set(assets) & REMOVED_ASSETS)
    if removed:
        ap.error(f"removed from active coin lists: {', '.join(removed)}")
    unknown = [a for a in assets if a not in MINUTE_ASSETS]
    if unknown and not args.coverage_only:
        # Beyond the core universe, accept whatever the venue actually lists against USD,
        # checked against its live product list rather than a hand-kept table.
        from .universe import list_coinbase_products

        listed = {p.split("-")[0] for p in list_coinbase_products() if p.endswith("-USD")}
        missing = [a for a in unknown if a not in listed]
        if missing:
            ap.error(
                f"{', '.join(missing)} not listed against USD on Coinbase, so there are no candles "
                "to fetch (TRX and RAIN, for example, are absent entirely -- backtester/core/universe.py)."
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

"""Long-history price structure for one coin: levels, level reactions, seasonality.

The weekly candle study (`research.coin_week`) covers one frozen week of minute
bars. This module answers the questions a week cannot: where the coin has
repeatedly turned, where volume traded, whether those levels changed what
happened next, and whether weekday or hour-of-day effects exist.

    python -m research.coin_structure fetch --coin HYPE --output /absolute/new-dir
    python -m research.coin_structure analyze --output /absolute/new-dir

Fetching is an explicit phase. `analyze` works offline: it checks the frozen
raw responses and CSVs against their hashes, rebuilds the bars from the raw
responses and writes `structure.json` and `structure.md`. Nothing here trades,
signs or changes a service.

Source: Hyperliquid's public `candleSnapshot` for the perpetual contract. It is
the venue with the longest continuous history for HYPE. The endpoint serves
only the most recent 5,000 candles per interval, so hourly history is shorter
than daily history and the report says how short.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import sys
import tempfile
import time
import urllib.request
import zlib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtester.core.data import validate_bars
from backtester.core.types import BAR_COLUMNS

SOURCE_URL = "https://api.hyperliquid.xyz/info"
VENUE = "Hyperliquid perpetual"
INTERVALS = {"1d": 86_400, "1h": 3_600}
EARLIEST_MS = 1_700_000_000_000  # before any Hyperliquid listing studied here
CANDLE_FIELDS = frozenset("tTiohlcv")
SYMBOL = re.compile(r"[A-Za-z0-9]{1,20}")
REQUEST_ATTEMPTS = 3
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class Settings:
    """The analysis parameters a reader may want to vary.

    `structure.json` records the values used. Fixed conventions (a 365-day
    year, the 5% and 10% day thresholds, the autocorrelation lags) stay in the
    code that applies them.
    """

    daily_pivot_span: int = 5
    hourly_pivot_span: int = 24
    daily_cluster_tolerance: float = 0.03
    hourly_cluster_tolerance: float = 0.012
    daily_touch_tolerance: float = 0.015
    hourly_touch_tolerance: float = 0.005
    daily_horizons: tuple[int, ...] = (5, 10)
    hourly_horizons: tuple[int, ...] = (24, 72)
    # Lines this far from each swing level, tested by the same rules, show what
    # a return to an arbitrary nearby price looked like.
    daily_placebo_offsets: tuple[float, ...] = (-0.06, 0.06)
    hourly_placebo_offsets: tuple[float, ...] = (-0.02, 0.02)
    daily_profile_step: float = 0.03
    recent_profile_step: float = 0.01
    recent_days: int = 90
    value_area: float = 0.70
    drawdown_minimum: float = 0.25
    hourly_level_window: float = 0.20
    moving_averages: tuple[int, ...] = (20, 50, 100, 200)
    minimum_reference_days: int = 30
    minimum_daily_bars: int = 60
    minimum_hourly_bars: int = 336


def iso(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%dT%H:%MZ")


def day(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), UTC).strftime("%Y-%m-%d")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def finite(value: float) -> float | None:
    """A statistic that could not be computed is absent, not NaN.

    NaN is not JSON, so one degenerate series would otherwise make the whole
    result file unreadable by a strict parser.
    """
    return float(value) if math.isfinite(value) else None


# ---------------------------------------------------------------- acquisition


def parse_candles(raw: bytes, symbol: str) -> list[dict[str, Any]]:
    """Accept only a non-empty list of complete candle objects.

    The endpoint answers an unknown coin with an empty list and an error with
    a body that is not a candle list. Either would otherwise fail later with an
    error that does not name the request.
    """
    try:
        rows = json.loads(raw)
    except ValueError:
        rows = None
    usable = (
        isinstance(rows, list)
        and rows
        and all(isinstance(r, dict) and r.keys() >= CANDLE_FIELDS for r in rows)
    )
    if not usable:
        raise ValueError(f"{symbol}: response is not a candle list: {raw[:120]!r}")
    return rows


def normalize_candles(
    rows: list[dict[str, Any]], interval: str, now_ms: int
) -> pd.DataFrame:
    """Map Hyperliquid candle objects to the backtester bar contract.

    A candle whose close time has not passed is still forming. Keeping it would
    let every later statistic read a bar that changes after the study freezes.
    """
    kept = [r for r in rows if int(r["T"]) < now_ms and r["i"] == interval]
    frame = pd.DataFrame(
        {
            "timestamp": [int(r["t"]) // 1000 for r in kept],
            "open": [float(r["o"]) for r in kept],
            "high": [float(r["h"]) for r in kept],
            "low": [float(r["l"]) for r in kept],
            "close": [float(r["c"]) for r in kept],
            "volume": [float(r["v"]) for r in kept],
        },
        columns=list(BAR_COLUMNS),
    )
    return validate_bars(frame, interval)


def _post(body: dict[str, Any]) -> bytes:
    request = urllib.request.Request(
        SOURCE_URL,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "user-agent": "research-client"},
    )
    label = f"{body['req']['coin']} {body['req']['interval']}"
    for attempt in range(1, REQUEST_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()
        except OSError as exc:  # network errors only; a bad payload must surface
            # A 4xx other than 429 is a wrong request; repeating it cannot help.
            status = getattr(exc, "code", None)
            refused = status is not None and status < 500 and status != 429
            if refused or attempt == REQUEST_ATTEMPTS:
                raise RuntimeError(f"{label}: candle request failed: {exc}") from exc
            print(f"{label}: retrying after {exc}", file=sys.stderr, flush=True)
            time.sleep(1.5 * attempt)
    raise AssertionError("unreachable")


def freeze_series(output: Path, name: str, raw: bytes, now_ms: int) -> dict[str, Any]:
    """Write one series' raw response and its normalized CSV; return both hashes."""
    symbol, interval = name.rsplit("_", 1)
    try:
        frame = normalize_candles(parse_candles(raw, symbol), interval, now_ms)
    except (ValueError, TypeError) as exc:
        # A gap, a null field or a bad number is reported by the bar contract
        # without saying which of the requested series it was found in.
        raise ValueError(f"{name}: unusable candles: {exc}") from exc
    (output / "inputs").mkdir(exist_ok=True)
    (output / "inputs" / f"{name}.json.zlib").write_bytes(zlib.compress(raw, 9))
    csv = frame.to_csv(index=False).encode()
    (output / f"{name}.csv").write_bytes(csv)
    return {
        "raw_sha256": sha256(raw),
        "csv_sha256": sha256(csv),
        "bars": len(frame),
        "first": iso(frame["timestamp"].iloc[0]),
        "last_open": iso(frame["timestamp"].iloc[-1]),
    }


def fetch(coin: str, references: list[str], output: Path) -> None:
    symbols = list(dict.fromkeys([coin, *references]))
    for symbol in symbols:
        # The symbol becomes a file name, and Hyperliquid symbols are
        # case-sensitive (kPEPE), so it is checked and never re-cased.
        if not SYMBOL.fullmatch(symbol):
            raise SystemExit(f"not a coin symbol: {symbol!r}")
    if output.exists():
        raise SystemExit(f"output exists; choose a new directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    now_ms = int(time.time() * 1000)
    source: dict[str, Any] = {
        "schema": "coin-structure-source/v1",
        "venue": VENUE,
        "source_url": SOURCE_URL,
        "coin": coin,
        "references": symbols[1:],
        "fetched_at": iso(now_ms / 1000),
        "fetched_at_ms": now_ms,
        "series": {},
    }
    wanted = [(coin, interval) for interval in INTERVALS] + [
        (ref, "1d") for ref in symbols[1:]
    ]
    # Built beside the target and renamed at the end: a failed request must
    # not leave a half-filled directory that blocks the retry.
    with tempfile.TemporaryDirectory(dir=output.parent, prefix=".fetching-") as tmp:
        staging = Path(tmp) / "study"
        staging.mkdir()
        for symbol, interval in wanted:
            body = {
                "type": "candleSnapshot",
                "req": {
                    "coin": symbol,
                    "interval": interval,
                    "startTime": EARLIEST_MS,
                    "endTime": now_ms,
                },
            }
            name = f"{symbol}_{interval}"
            meta = freeze_series(staging, name, _post(body), now_ms)
            source["series"][name] = {"request": body, **meta}
            print(f"fetched {name}: {meta['bars']} completed bars", flush=True)
        text = json.dumps(source, indent=2) + "\n"
        (staging / "source.json").write_text(text, encoding="utf-8")
        staging.rename(output)


def load(output: Path) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
    """Rebuild every series from its frozen raw response and check the CSV.

    The CSV is what the backtester reads, so a CSV that is not the
    normalization of the retained response would let the two analyses disagree
    about the same study without either noticing.
    """
    try:
        source = json.loads((output / "source.json").read_text())
    except FileNotFoundError as exc:
        raise ValueError(f"not a fetched study (no source.json): {output}") from exc
    frames: dict[str, pd.DataFrame] = {}
    for name, meta in source["series"].items():
        symbol, interval = name.rsplit("_", 1)
        try:
            packed = (output / "inputs" / f"{name}.json.zlib").read_bytes()
            raw = zlib.decompress(packed)
            data = (output / f"{name}.csv").read_bytes()
        except (OSError, zlib.error) as exc:
            raise ValueError(f"{name}: frozen input unreadable: {exc}") from exc
        if sha256(raw) != meta["raw_sha256"] or sha256(data) != meta["csv_sha256"]:
            raise ValueError(f"{name} does not match its frozen hash")
        frame = normalize_candles(
            parse_candles(raw, symbol), interval, source["fetched_at_ms"]
        )
        # Exact comparison is safe: pandas writes the shortest repr of each
        # float and parses it back to the same value.
        stored = pd.read_csv(io.BytesIO(data))
        if not np.array_equal(stored.to_numpy(), frame.to_numpy()):
            raise ValueError(f"{name}.csv is not the normalization of its response")
        frames[name] = frame
    return source, frames


# ------------------------------------------------------------------- analysis


def confirmed_pivots(
    high: np.ndarray, low: np.ndarray, span: int
) -> list[dict[str, Any]]:
    """Swing highs and lows that are the extreme of `span` bars each side.

    A pivot at bar i cannot be known before bar i + span closes. `confirm`
    records that bar so later tests never use a level before it existed.

    Equal extremes within `span` bars of each other give one pivot, at the
    earliest bar. A double top at one price is a level worth keeping, but
    counting each of its bars would report the same turn twice.
    """
    pivots: list[dict[str, Any]] = []
    latest: dict[str, dict[str, Any]] = {}
    for i in range(span, len(high) - span):
        for kind, series, pick in (("high", high, np.max), ("low", low, np.min)):
            price = float(series[i])
            if price != pick(series[i - span : i + span + 1]):
                continue
            previous = latest.get(kind)
            if (
                previous
                and previous["price"] == price
                and i - previous["index"] <= span
            ):
                continue
            latest[kind] = {
                "index": i,
                "kind": kind,
                "price": price,
                "confirm": i + span,
            }
            pivots.append(latest[kind])
    return pivots


def cluster_levels(
    pivots: list[dict[str, Any]], tolerance: float
) -> list[dict[str, Any]]:
    """Group pivots so that no group spans more than `tolerance`.

    Each group is anchored on its lowest price. Anchoring on a running mean
    would let a chain of close pivots stretch one group far past the tolerance.
    """
    clusters: list[list[dict[str, Any]]] = []
    for pivot in sorted(pivots, key=lambda p: p["price"]):
        if clusters and pivot["price"] / clusters[-1][0]["price"] - 1 <= tolerance:
            clusters[-1].append(pivot)
        else:
            clusters.append([pivot])
    levels = []
    for members in clusters:
        prices = [p["price"] for p in members]
        levels.append(
            {
                "level": sum(prices) / len(prices),
                "low": min(prices),
                "high": max(prices),
                "touches": len(members),
                "pivot_highs": sum(p["kind"] == "high" for p in members),
                "pivot_lows": sum(p["kind"] == "low" for p in members),
                "first_index": min(p["index"] for p in members),
                "last_index": max(p["index"] for p in members),
            }
        )
    return levels


def volume_profile(
    high: np.ndarray,
    low: np.ndarray,
    volume: np.ndarray,
    step: float,
    value_area: float = Settings.value_area,
) -> dict[str, Any]:
    """Spread each bar's volume evenly over its log-price range.

    Candles do not say where inside the bar volume traded. Uniform spreading is
    the neutral assumption; it blurs nodes by at most one bar range.
    """
    floor = math.log(float(low.min()))
    count = max(1, math.ceil((math.log(float(high.max())) - floor) / step + 1e-9))
    bins = np.zeros(count)
    for hi, lo, vol in zip(high, low, volume, strict=True):
        a, b = math.log(lo) - floor, math.log(hi) - floor
        first, last = min(int(a / step), count - 1), min(int(b / step), count - 1)
        if first == last or b <= a:
            bins[first] += vol
            continue
        for k in range(first, last + 1):
            overlap = min(b, (k + 1) * step) - max(a, k * step)
            bins[k] += vol * max(overlap, 0.0) / (b - a)
    centers = np.exp(floor + (np.arange(count) + 0.5) * step)
    poc = int(bins.argmax())
    lo_i = hi_i = poc
    inside, total = bins[poc], bins.sum()
    while inside < value_area * total and (lo_i > 0 or hi_i < count - 1):
        below = bins[lo_i - 1] if lo_i > 0 else -1.0
        above = bins[hi_i + 1] if hi_i < count - 1 else -1.0
        if above >= below:
            hi_i += 1
            inside += bins[hi_i]
        else:
            lo_i -= 1
            inside += bins[lo_i]
    nodes = [
        k
        for k in range(count)
        if bins[k] > np.median(bins) and bins[k] == bins[max(0, k - 2) : k + 3].max()
    ]
    return {
        "step": step,
        "value_area": value_area,
        "centers": centers.tolist(),
        "volume": bins.tolist(),
        "poc": float(centers[poc]),
        "value_area_low": float(math.exp(floor + lo_i * step)),
        "value_area_high": float(math.exp(floor + (hi_i + 1) * step)),
        "nodes": [
            {"level": float(centers[k]), "share": float(bins[k] / total)}
            for k in sorted(nodes, key=lambda k: -bins[k])
        ],
    }


def level_tests(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    pivots: list[dict[str, Any]],
    tolerance: float,
    horizon: int,
) -> dict[str, list[dict[str, float]]]:
    """Non-overlapping returns to already-confirmed levels, per side."""
    n = len(close)
    touches: dict[str, dict[int, dict[str, float]]] = {"support": {}, "resistance": {}}
    for pivot in pivots:
        level = pivot["price"]
        support = pivot["kind"] == "low"
        by_bar = touches["support" if support else "resistance"]
        for t in range(pivot["confirm"] + 1, n - horizon):
            if support:
                clear = close[t - 1] > level * (1 + tolerance)
                reached = low[t] <= level * (1 + tolerance)
                broken = close[t] < level * (1 - tolerance)
            else:
                clear = close[t - 1] < level * (1 - tolerance)
                reached = high[t] >= level * (1 - tolerance)
                broken = close[t] > level * (1 + tolerance)
            # A bar that reaches several levels tests the one price met first:
            # the nearest to the previous close. Which pivot happens to be
            # listed first must not decide whether the level "held".
            nearer = t not in by_bar or (level > by_bar[t]["level"]) == support
            if clear and reached and nearer:
                path = close[t : t + horizon + 1]
                held = (
                    path.min() >= level * (1 - tolerance)
                    if support
                    else path.max() <= level * (1 + tolerance)
                )
                by_bar[t] = {
                    "level": level,
                    "forward": float(close[t + horizon] / close[t] - 1),
                    "held": float(held),
                }
            if broken:
                break
    kept: dict[str, list[dict[str, float]]] = {}
    for side, by_bar in touches.items():
        kept[side], next_free = [], 0
        for t in sorted(by_bar):
            if t >= next_free:
                kept[side].append(by_bar[t])
                next_free = t + horizon
    return kept


def summarize_tests(tests: list[dict[str, float]]) -> dict[str, Any]:
    forward = np.array([e["forward"] for e in tests])
    held = np.array([e["held"] for e in tests])
    count = len(tests)
    return {
        "tests": count,
        "held_rate": float(held.mean()) if count else None,
        "mean_forward": float(forward.mean()) if count else None,
        "median_forward": float(np.median(forward)) if count else None,
        "up_rate": float((forward > 0).mean()) if count else None,
        "standard_error": float(forward.std(ddof=1) / math.sqrt(count))
        if count > 1
        else None,
    }


def level_reactions(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    pivots: list[dict[str, Any]],
    tolerance: float,
    horizon: int,
    placebo_offsets: tuple[float, ...] = (),
) -> dict[str, Any]:
    """What happened after price returned to a level that already existed.

    A pivot low is a support candidate from the bar after its confirmation
    until a close breaks it by `tolerance`. A test is a bar that reaches the
    level after the previous close sat clear of it. The outcome is measured from
    that bar's close, so the entry uses nothing later than the test bar. The
    level "held" when no close in the horizon went through it by `tolerance`.

    Tests on one side never overlap. A later test inside an earlier test's
    outcome window is dropped, and pivots stacked at one price give one test;
    otherwise one move would be counted several times and the standard error
    would shrink without any new evidence.

    The average of all bars is not a fair comparison: a test only happens after
    price has moved toward the level. `placebo` therefore applies the same rules
    to lines offset from each pivot, known from the same bar. A swing level
    that matters should hold more often than those lines do.
    """
    forward_all = close[horizon:] / close[:-horizon] - 1
    result: dict[str, Any] = {
        "tolerance": tolerance,
        "horizon_bars": horizon,
        "baseline_mean_forward": float(forward_all.mean()),
        "baseline_up_rate": float((forward_all > 0).mean()),
    }
    real = level_tests(high, low, close, pivots, tolerance, horizon)
    shifted = [
        {**pivot, "price": pivot["price"] * (1 + offset)}
        for offset in placebo_offsets
        for pivot in pivots
    ]
    placebo = level_tests(high, low, close, shifted, tolerance, horizon)
    for side in ("support", "resistance"):
        result[side] = summarize_tests(real[side])
        result[side]["placebo"] = summarize_tests(placebo[side])
    return result


def grouped_returns(
    returns: np.ndarray, keys: np.ndarray, labels: list[str]
) -> list[dict[str, Any]]:
    rows = []
    for key, label in enumerate(labels):
        sample = returns[keys == key]
        if len(sample) < 2:
            continue
        error = sample.std(ddof=1) / math.sqrt(len(sample))
        # A sample with no spread has no t-statistic. Dividing by float noise
        # would print an enormous one.
        measurable = error > 1e-12 * max(1.0, float(np.abs(sample).max()))
        rows.append(
            {
                "label": label,
                "n": len(sample),
                "mean": float(sample.mean()),
                "median": float(np.median(sample)),
                "up_rate": float((sample > 0).mean()),
                "t": float(sample.mean() / error) if measurable else None,
                "mean_abs": float(np.abs(sample).mean()),
            }
        )
    return rows


def autocorrelation(values: np.ndarray, lag: int) -> float | None:
    if len(values) <= lag + 1 or values[:-lag].std() == 0 or values[lag:].std() == 0:
        return None
    return finite(np.corrcoef(values[:-lag], values[lag:])[0, 1])


def drawdowns(
    ts: np.ndarray, high: np.ndarray, low: np.ndarray, minimum: float
) -> list[dict[str, Any]]:
    """Peak-to-trough declines of at least `minimum`, each ended by a new high.

    The low of the bar that set the peak is never the trough: a candle does not
    say whether its low came before or after its high.
    """
    episodes: list[dict[str, Any]] = []
    peak = 0
    trough: int | None = None
    for i in range(1, len(high)):
        if high[i] > high[peak]:
            if trough is not None and low[trough] / high[peak] - 1 <= -minimum:
                episodes.append(_episode(ts, high, low, peak, trough, i))
            peak, trough = i, None
        elif trough is None or low[i] < low[trough]:
            trough = i
    if trough is not None and low[trough] / high[peak] - 1 <= -minimum:
        episodes.append(_episode(ts, high, low, peak, trough, None))
    return episodes


def _episode(
    ts: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    peak: int,
    trough: int,
    recovered: int | None,
) -> dict[str, Any]:
    return {
        "peak_date": day(ts[peak]),
        "peak": float(high[peak]),
        "trough_date": day(ts[trough]),
        "trough": float(low[trough]),
        "depth": float(low[trough] / high[peak] - 1),
        "days_to_trough": int(trough - peak),
        "recovered_date": day(ts[recovered]) if recovered is not None else None,
    }


def next_bar_conditions(returns: np.ndarray) -> list[dict[str, Any]]:
    current, following = returns[:-1], returns[1:]
    rules = [
        ("all days", np.ones(len(current), dtype=bool)),
        ("after any up bar", current > 0),
        ("after any down bar", current < 0),
        ("after a gain of 5% or more", current >= 0.05),
        ("after a loss of 5% or more", current <= -0.05),
        ("after a gain of 10% or more", current >= 0.10),
        ("after a loss of 10% or more", current <= -0.10),
    ]
    rows = []
    for label, mask in rules:
        sample = following[mask]
        if len(sample) < 2:
            continue
        rows.append(
            {
                "condition": label,
                "n": len(sample),
                "next_mean": float(sample.mean()),
                "next_up_rate": float((sample > 0).mean()),
                "standard_error": float(sample.std(ddof=1) / math.sqrt(len(sample))),
            }
        )
    return rows


def reference_comovement(
    daily: pd.DataFrame, reference: pd.DataFrame, settings: Settings
) -> dict[str, Any] | None:
    """Correlation and beta on shared days, or None when too few are shared."""
    merged = daily[["timestamp", "close"]].merge(
        reference[["timestamp", "close"]], on="timestamp", suffixes=("", "_ref")
    )
    own = np.diff(np.log(merged["close"].to_numpy(dtype=float)))
    ref = np.diff(np.log(merged["close_ref"].to_numpy(dtype=float)))
    if len(own) < settings.minimum_reference_days:
        return None
    spans = {"full": len(own)}
    if len(own) > settings.recent_days:  # otherwise it would repeat "full"
        spans[f"last_{settings.recent_days}d"] = settings.recent_days
    windows = {}
    for window, span in spans.items():
        a, b = own[-span:], ref[-span:]
        variance = b.var(ddof=1)
        moving = bool(variance) and bool(a.var(ddof=1))
        windows[window] = {
            "days": len(a),
            "correlation": finite(np.corrcoef(a, b)[0, 1]) if moving else None,
            "beta": finite(np.cov(a, b)[0, 1] / variance) if variance else None,
        }
    return windows


def arrays(frame: pd.DataFrame) -> tuple[np.ndarray, ...]:
    columns = ("timestamp", "high", "low", "close", "volume")
    return tuple(frame[c].to_numpy(dtype=float) for c in columns)


def analyze(output: Path, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or Settings()
    source, frames = load(output)
    coin = source["coin"]
    daily, hourly = frames[f"{coin}_1d"], frames[f"{coin}_1h"]
    ts, high, low, close, volume = arrays(daily)
    hts, hhigh, hlow, hclose, hvolume = arrays(hourly)
    if len(close) < settings.minimum_daily_bars:
        raise ValueError(f"{coin}: {len(close)} daily bars are too few to analyze")
    if len(hclose) < settings.minimum_hourly_bars:
        raise ValueError(f"{coin}: {len(hclose)} hourly bars are too few to analyze")
    if hts[-1] < ts[-1]:
        # The endpoint is expected to serve the newest candles. Hourly history
        # that stops before the daily history means that assumption failed.
        raise ValueError(f"{coin}: hourly bars end before the last daily bar")
    returns = close[1:] / close[:-1] - 1
    log_returns = np.diff(np.log(close))
    hreturns = hclose[1:] / hclose[:-1] - 1
    last, hlast = float(close[-1]), float(hclose[-1])
    ath = int(high.argmax())
    true_range = np.maximum(high[1:], close[:-1]) - np.minimum(low[1:], close[:-1])

    summary = {
        "coin": coin,
        "venue": source["venue"],
        "daily_bars": len(close),
        "daily_first": day(ts[0]),
        "daily_last": day(ts[-1]),
        "hourly_bars": len(hclose),
        "hourly_first": iso(hts[0]),
        "hourly_last": iso(hts[-1]),
        "last_close": last,
        "last_hourly_close": hlast,
        "all_time_high": float(high[ath]),
        "all_time_high_date": day(ts[ath]),
        "from_all_time_high": float(last / high[ath] - 1),
        "window_low": float(low.min()),
        "window_low_date": day(ts[int(low.argmin())]),
        "annualized_volatility": float(log_returns.std(ddof=1) * math.sqrt(365)),
        "volatility_30d": float(log_returns[-30:].std(ddof=1) * math.sqrt(365)),
        "atr14_fraction": float(true_range[-14:].mean() / last),
        "moving_averages": {
            str(n): {
                "value": float(close[-n:].mean()),
                "close_vs": float(last / close[-n:].mean() - 1),
            }
            for n in settings.moving_averages
            if len(close) >= n
        },
    }

    daily_pivots = confirmed_pivots(high, low, settings.daily_pivot_span)
    hourly_pivots = confirmed_pivots(hhigh, hlow, settings.hourly_pivot_span)
    daily_levels = cluster_levels(daily_pivots, settings.daily_cluster_tolerance)
    hourly_levels = cluster_levels(hourly_pivots, settings.hourly_cluster_tolerance)
    # Every level is placed against the newest price. The hourly series runs
    # past the last completed daily bar, so the daily close can be a day stale
    # and would put a nearby level on the wrong side.
    for levels, stamps in ((daily_levels, ts), (hourly_levels, hts)):
        for level in levels:
            level["first"] = day(stamps[level.pop("first_index")])
            level["last"] = day(stamps[level.pop("last_index")])
            level["distance"] = level["level"] / hlast - 1
            level["role"] = "resistance" if level["level"] > hlast else "support"

    # Labelled with the days actually covered: a newly listed coin may have
    # less hourly history than the window asks for.
    recent_days = min(settings.recent_days, int((hts[-1] - hts[0]) // 86_400))
    recent = hts >= hts[-1] - recent_days * 86_400
    profiles = {
        "daily_full_history": volume_profile(
            high, low, volume, settings.daily_profile_step, settings.value_area
        ),
        f"hourly_last_{recent_days}d": volume_profile(
            hhigh[recent],
            hlow[recent],
            hvolume[recent],
            settings.recent_profile_step,
            settings.value_area,
        ),
    }
    for profile in profiles.values():
        for node in profile["nodes"]:
            node["distance"] = node["level"] / hlast - 1

    reactions = {}
    for horizon in settings.daily_horizons:
        reactions[f"daily_pivots_{horizon}bar_horizon"] = level_reactions(
            high,
            low,
            close,
            daily_pivots,
            settings.daily_touch_tolerance,
            horizon,
            settings.daily_placebo_offsets,
        )
    for horizon in settings.hourly_horizons:
        reactions[f"hourly_pivots_{horizon}bar_horizon"] = level_reactions(
            hhigh,
            hlow,
            hclose,
            hourly_pivots,
            settings.hourly_touch_tolerance,
            horizon,
            settings.hourly_placebo_offsets,
        )

    weekday = np.array([datetime.fromtimestamp(t, UTC).weekday() for t in ts[1:]])
    hour = np.array([datetime.fromtimestamp(t, UTC).hour for t in hts[1:]])
    hour_volume = np.array([hvolume[1:][hour == h].sum() for h in range(24)])
    hours = grouped_returns(hreturns, hour, [f"{h:02d}" for h in range(24)])
    for row in hours:
        share = hour_volume[int(row["label"])] / max(hour_volume.sum(), 1e-300)
        row["volume_share"] = float(share)

    correlations, skipped = {}, []
    for name, frame in frames.items():
        symbol, interval = name.rsplit("_", 1)
        if symbol != coin and interval == "1d":
            comovement = reference_comovement(daily, frame, settings)
            if comovement is None:
                skipped.append(symbol)
            else:
                correlations[symbol] = comovement

    result = {
        "schema": "coin-structure/v1",
        "source": {
            k: source[k] for k in ("venue", "source_url", "fetched_at", "series")
        },
        "settings": asdict(settings),
        "summary": summary,
        "drawdowns": drawdowns(ts, high, low, settings.drawdown_minimum),
        "daily_levels": daily_levels,
        "hourly_levels": hourly_levels,
        "volume_profiles": profiles,
        "level_reactions": reactions,
        "weekday": grouped_returns(returns, weekday, list(WEEKDAYS)),
        "hour_utc": hours,
        "daily_autocorrelation": {
            str(k): autocorrelation(returns, k) for k in range(1, 6)
        },
        "daily_abs_autocorrelation": {
            str(k): autocorrelation(np.abs(returns), k) for k in (1, 5)
        },
        "hourly_autocorrelation": {
            str(k): autocorrelation(hreturns, k) for k in (1, 2, 4, 24)
        },
        "next_day": next_bar_conditions(returns),
        "correlations": correlations,
        "skipped_references": skipped,
    }
    # allow_nan=False: an uncomputable statistic must fail here, not be
    # written as a NaN literal that strict JSON readers reject.
    text = json.dumps(result, indent=2, allow_nan=False)
    (output / "structure.json").write_text(text + "\n", encoding="utf-8")
    (output / "structure.md").write_text(render(result), encoding="utf-8")
    return result


# ------------------------------------------------------------------ rendering


def pct(value: float | None, digits: int = 2) -> str:
    return "n/a" if value is None else f"{value * 100:+.{digits}f}%"


def rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.0f}%"


def signed(value: float | None, digits: int) -> str:
    return "n/a" if value is None else f"{value:+.{digits}f}"


def usd(value: float) -> str:
    return f"${value:,.2f}"


def table(title: str, header: str, align: str, rows: list[str]) -> list[str]:
    cells = [f"| {row} |" for row in rows]
    return ["", f"## {title}", "", f"| {header} |", f"|{align}|", *cells]


def _standing(result: dict[str, Any]) -> list[str]:
    s = result["summary"]
    rows = [
        f"Last hourly close | {usd(s['last_hourly_close'])}",
        f"Last completed daily close | {usd(s['last_close'])}",
        (
            f"All-time high in this history | {usd(s['all_time_high'])} "
            f"on {s['all_time_high_date']}"
        ),
        f"Daily close against that high | {pct(s['from_all_time_high'])}",
        (
            f"Lowest low in this history | {usd(s['window_low'])} "
            f"on {s['window_low_date']}"
        ),
        f"Annualized volatility, all days | {rate(s['annualized_volatility'])}",
        f"Annualized volatility, last 30 days | {rate(s['volatility_30d'])}",
        f"Average true range, 14 days | {s['atr14_fraction'] * 100:.1f}% of price",
    ]
    rows += [
        f"{n}-day average close | {usd(ma['value'])} "
        f"(daily close is {pct(ma['close_vs'])})"
        for n, ma in s["moving_averages"].items()
    ]
    return table("Where price stands", "Measure | Value", "---|---:", rows)


def _drawdowns(result: dict[str, Any]) -> list[str]:
    rows = [
        f"{usd(d['peak'])} on {d['peak_date']} | {usd(d['trough'])} "
        f"on {d['trough_date']} | {pct(d['depth'], 1)} | {d['days_to_trough']} | "
        f"{d['recovered_date'] or 'not yet'}"
        for d in result["drawdowns"]
    ]
    title = f"Declines of {rate(result['settings']['drawdown_minimum'])} or more"
    header = "Peak | Trough | Depth | Days down | New high"
    return table(title, header, "---|---|---:|---:|---", rows)


def _levels(result: dict[str, Any]) -> list[str]:
    cfg = result["settings"]
    lines: list[str] = []
    for unit, key, span, tolerance, window in (
        (
            "day",
            "daily_levels",
            cfg["daily_pivot_span"],
            cfg["daily_cluster_tolerance"],
            None,
        ),
        (
            "hour",
            "hourly_levels",
            cfg["hourly_pivot_span"],
            cfg["hourly_cluster_tolerance"],
            cfg["hourly_level_window"],
        ),
    ):
        rows = [
            f"{usd(level['level'])} | {usd(level['low'])}–{usd(level['high'])} | "
            f"{level['role']} | {pct(level['distance'], 1)} | {level['touches']} "
            f"({level['pivot_highs']}/{level['pivot_lows']}) | "
            f"{level['first']} | {level['last']}"
            for level in sorted(result[key], key=lambda x: -x["level"])
            if window is None or abs(level["distance"]) <= window
        ]
        title = (
            f"{'Daily' if unit == 'day' else 'Hourly'} swing levels "
            f"({2 * span + 1}-{unit} pivots, groups no wider than "
            f"{tolerance * 100:g}%)"
        )
        if window is not None:
            title += f", within {rate(window)} of price"
        header = (
            "Level | Range | Role now | From last hourly close | "
            "Pivots (highs/lows) | First | Last"
        )
        lines += table(title, header, "---:|---|---|---:|---:|---|---", rows)
    return lines


def _profiles(result: dict[str, Any]) -> list[str]:
    lines = ["", "## Volume by price"]
    for name, profile in result["volume_profiles"].items():
        lines += [
            "",
            (
                f"**{name.replace('_', ' ')}** ({profile['step'] * 100:g}% price "
                f"bins): most-traded price {usd(profile['poc'])}; "
                f"{rate(profile['value_area'])} of volume between "
                f"{usd(profile['value_area_low'])} and "
                f"{usd(profile['value_area_high'])}."
            ),
            "",
            "| Volume node | Share of volume | From last hourly close |",
            "|---:|---:|---:|",
        ]
        lines += [
            f"| {usd(node['level'])} | {node['share'] * 100:.1f}% | "
            f"{pct(node['distance'], 1)} |"
            for node in profile["nodes"][:8]
        ]
    return lines


def _reactions(result: dict[str, Any]) -> list[str]:
    rows = []
    for name, study in result["level_reactions"].items():
        for side in ("support", "resistance"):
            real, placebo = study[side], study[side]["placebo"]
            rows.append(
                f"{name.replace('_', ' ')} | {side} | {real['tests']} | "
                f"{rate(real['held_rate'])} | {pct(real['mean_forward'])} | "
                f"{pct(real['standard_error'])} | {placebo['tests']} | "
                f"{rate(placebo['held_rate'])} | {pct(placebo['mean_forward'])} | "
                f"{pct(study['baseline_mean_forward'])}"
            )
    header = (
        "Study | Side | Tests | Held | Mean forward | Std. error | Placebo tests | "
        "Placebo held | Placebo mean forward | All bars mean"
    )
    lines = table(
        "Did earlier swing levels change what happened next?",
        header,
        "---|---|---:|---:|---:|---:|---:|---:|---:|---:",
        rows,
    )
    note = (
        "Each test is a return to a pivot that was already confirmed and unbroken. "
        "Tests on one side do not overlap. Forward return runs from the close of "
        "the test bar. A level held when no close in the horizon went through it "
        "by the touch tolerance. Placebo columns apply the same rules to lines "
        "offset from each pivot; they are the fair comparison, because every "
        "test follows a move toward the line. The all-bars mean is unconditional."
    )
    return [*lines[:3], note, "", *lines[3:]]


def _calendar(result: dict[str, Any]) -> list[str]:
    weekdays = [
        f"{row['label']} | {row['n']} | {pct(row['mean'])} | {pct(row['median'])} | "
        f"{rate(row['up_rate'])} | {signed(row['t'], 2)}"
        for row in result["weekday"]
    ]
    hours = [
        f"{row['label']} | {row['n']} | {pct(row['mean'], 3)} | "
        f"{rate(row['up_rate'])} | {signed(row['t'], 2)} | "
        f"{row['mean_abs'] * 100:.2f}% | {row['volume_share'] * 100:.1f}%"
        for row in result["hour_utc"]
    ]
    note = (
        "The t column tests each row alone. Seven weekdays need |t| near 2.7 and "
        "24 hours need |t| above 3 before one row counts as more than chance."
    )
    return [
        *table(
            "Weekday (UTC daily bars)",
            "Day | Days | Mean | Median | Up rate | t",
            "---|---:|---:|---:|---:|---:",
            weekdays,
        ),
        *table(
            "Hour of day (UTC hourly bars)",
            "Hour | Bars | Mean | Up rate | t | Mean absolute move | Volume share",
            "---|---:|---:|---:|---:|---:|---:",
            hours,
        ),
        "",
        note,
    ]


def _behaviour(result: dict[str, Any]) -> list[str]:
    rows = [
        f"{row['condition']} | {row['n']} | {pct(row['next_mean'])} | "
        f"{pct(row['standard_error'])} | {rate(row['next_up_rate'])}"
        for row in result["next_day"]
    ]
    daily = result["daily_autocorrelation"]
    absolute = result["daily_abs_autocorrelation"]
    hourly = result["hourly_autocorrelation"]
    note = (
        "Daily return autocorrelation, lags 1–5: "
        + ", ".join(signed(daily[str(k)], 3) for k in range(1, 6))
        + f". Absolute-return autocorrelation: lag 1 {signed(absolute['1'], 3)}, "
        f"lag 5 {signed(absolute['5'], 3)}. Hourly return autocorrelation: "
        + ", ".join(f"lag {k} {signed(v, 3)}" for k, v in hourly.items())
        + "."
    )
    header = "Condition | Days | Next-day mean | Std. error | Next-day up rate"
    return [
        *table("Day-to-day behaviour", header, "---|---:|---:|---:|---:", rows),
        "",
        note,
    ]


def _comovement(result: dict[str, Any]) -> list[str]:
    rows = [
        f"{symbol} | {window.replace('_', ' ')} | {row['days']} | "
        f"{signed(row['correlation'], 2)} | {signed(row['beta'], 2)}"
        for symbol, windows in result["correlations"].items()
        for window, row in windows.items()
    ]
    lines = table(
        "Co-movement with reference coins (daily log returns)",
        "Reference | Window | Days | Correlation | Beta",
        "---|---|---:|---:|---:",
        rows,
    )
    if result["skipped_references"]:
        dropped = ", ".join(result["skipped_references"])
        lines += ["", f"Left out for too few shared days: {dropped}."]
    return lines


def render(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        f"# {s['coin']} price structure",
        "",
        (
            f"Source: {s['venue']} candles, fetched {result['source']['fetched_at']}. "
            f"Daily bars {s['daily_first']} to {s['daily_last']} ({s['daily_bars']}); "
            f"hourly bars {s['hourly_first']} to {s['hourly_last']} ({s['hourly_bars']})."
        ),
        "",
        "Descriptive study of past candles. It does not qualify a trading edge.",
    ]
    for section in (
        _standing,
        _drawdowns,
        _levels,
        _profiles,
        _reactions,
        _calendar,
        _behaviour,
        _comovement,
    ):
        lines += section(result)
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("phase", choices=("fetch", "analyze"))
    parser.add_argument(
        "--coin", default="HYPE", help="fetch: coin symbol, exactly as listed"
    )
    parser.add_argument(
        "--references",
        default="BTC,ETH,SOL",
        help="fetch: comma-separated coins for daily co-movement",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="fetch: a new directory; analyze: a fetched directory",
    )
    args = parser.parse_args(argv)
    if args.phase == "fetch":
        references = [r for r in args.references.split(",") if r]
        fetch(args.coin, references, args.output)
    else:
        summary = analyze(args.output)["summary"]
        print(
            f"analyzed {summary['coin']}: {summary['daily_bars']} daily, "
            f"{summary['hourly_bars']} hourly bars"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fetch checksum-verified Binance ZECUSDT spot history without altering shared caches.

Explicit network step. Monthly/daily public ZIPs preserve publisher checksums; the
market-data-only API appends closed tail candles. Both intervals use the same venue
and quote currency. Missing bars remain missing and appear in a separate gap ledger.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from backtester.core.data import validate_bars

ARCHIVE_BASE = "https://data.binance.vision/data/spot"
API_BASE = "https://data-api.binance.vision/api/v3"
COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
STEPS = {"1m": 60, "1h": 3600}
DEFAULT_OUTPUT = Path.home() / ".local/share/solmargintrader/research/zec-ensembles-20261110/data"


def request_bytes(url: str, *, missing_ok: bool = False) -> bytes | None:
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "solmargintrader-research/1.0"})
            with urllib.request.urlopen(req, timeout=40) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            if attempt == 2 or exc.code in (400, 401, 403):
                raise
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(1 + attempt)
    raise RuntimeError("request exhausted")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_frame(frame: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Decode archive ms/us timestamps exactly; refuse subsecond/open-bar misalignment."""
    out = frame.loc[:, COLUMNS].copy()
    numeric = pd.to_numeric(out["timestamp"], errors="raise").to_numpy()
    raw = numeric.astype(np.int64)
    if not np.isfinite(numeric).all() or np.any(numeric != raw):
        raise ValueError("timestamp must be a finite integer")
    divisors = np.where(raw >= 100_000_000_000_000, 1_000_000,
                        np.where(raw >= 100_000_000_000, 1000, 1))
    if np.any(raw % divisors):
        raise ValueError("fractional-second candle timestamp")
    out["timestamp"] = raw // divisors
    if np.any(out["timestamp"].to_numpy() % STEPS[interval]):
        raise ValueError("candle open is not aligned to its interval")
    for col in COLUMNS[1:]:
        out[col] = pd.to_numeric(out[col], errors="raise")
    return validate_bars(out, interval, strict_gaps=False)


def archive_job(job: tuple[str, str, str], root: Path) -> dict[str, Any]:
    interval, period, label = job
    name = f"ZECUSDT-{interval}-{label}.zip"
    url = f"{ARCHIVE_BASE}/{period}/klines/ZECUSDT/{interval}/{name}"
    folder = root / "raw" / interval
    folder.mkdir(parents=True, exist_ok=True)
    checksum_path, archive_path = folder / f"{name}.CHECKSUM", folder / name
    checksum = checksum_path.read_bytes() if checksum_path.exists() else request_bytes(url + ".CHECKSUM", missing_ok=True)
    if checksum is None:
        return {"url": url, "interval": interval, "state": "unavailable", "http_status": 404}
    expected = checksum.decode("ascii").split()[0]
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError(f"invalid publisher checksum: {name}")
    data = archive_path.read_bytes() if archive_path.exists() else request_bytes(url)
    if data is None or digest(data) != expected:
        raise ValueError(f"publisher SHA-256 mismatch: {name}")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"ZIP CRC mismatch: {name}/{bad}")
        members = archive.namelist()
        if len(members) != 1 or not members[0].endswith(".csv"):
            raise ValueError(f"unexpected ZIP members: {name}")
    if not archive_path.exists():
        archive_path.write_bytes(data)
    if not checksum_path.exists():
        checksum_path.write_bytes(checksum)
    return {"url": url, "interval": interval, "state": "verified", "sha256": expected,
            "path": str(archive_path), "checksum_url": url + ".CHECKSUM", "bytes": len(data)}


def read_archive(path: Path, interval: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as archive, archive.open(archive.namelist()[0]) as member:
        frame = pd.read_csv(member, header=None, names=COLUMNS, usecols=range(6))
    return normalize_frame(frame, interval)


def combine_frames(frames: list[pd.DataFrame], interval: str) -> tuple[pd.DataFrame, int]:
    combined = pd.concat(frames, ignore_index=True)
    duplicates = combined[combined.duplicated("timestamp", keep=False)]
    if len(duplicates):
        counts = duplicates.groupby("timestamp")[COLUMNS[1:]].nunique(dropna=False)
        if (counts > 1).any(axis=None):
            raise ValueError("conflicting candles at duplicate timestamps")
    removed = int(combined.duplicated("timestamp").sum())
    combined = combined.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    return validate_bars(combined, interval, strict_gaps=False), removed


def coverage(frame: pd.DataFrame, interval: str) -> tuple[dict[str, Any], pd.DataFrame]:
    step = STEPS[interval]
    ts = frame["timestamp"].to_numpy(dtype=np.int64)
    splits = np.flatnonzero(np.diff(ts) != step) + 1
    boundaries = np.r_[0, splits, len(ts)]
    spans = [(int(a), int(b)) for a, b in pairwise(boundaries)]
    a, b = max(spans, key=lambda span: span[1] - span[0])
    gaps = [{"after_timestamp": int(ts[i-1]), "next_timestamp": int(ts[i]),
             "missing_bars": int((ts[i]-ts[i-1]) // step - 1)} for i in splits]
    ledger = pd.DataFrame(gaps, columns=["after_timestamp", "next_timestamp", "missing_bars"])
    def fmt(t: int) -> str:
        return datetime.fromtimestamp(int(t), UTC).isoformat()
    return {"rows": len(ts), "first_timestamp": int(ts[0]), "last_timestamp": int(ts[-1]),
            "first_utc": fmt(ts[0]), "last_bar_open_utc": fmt(ts[-1]),
            "gap_runs": len(gaps), "missing_bars": sum(g["missing_bars"] for g in gaps),
            "longest_contiguous": {"rows": b-a, "first_timestamp": int(ts[a]), "last_timestamp": int(ts[b-1]),
                                   "first_utc": fmt(ts[a]), "last_bar_open_utc": fmt(ts[b-1])}}, ledger


def api_tail(interval: str, start: int, end: int, root: Path) -> tuple[list[pd.DataFrame], list[dict[str, Any]]]:
    frames, receipts = [], []
    step = STEPS[interval]
    cursor = start
    while cursor < end:
        params = urllib.parse.urlencode({"symbol": "ZECUSDT", "interval": interval,
                                        "startTime": cursor*1000, "endTime": end*1000-1, "limit": 1000})
        url = f"{API_BASE}/klines?{params}"
        data = request_bytes(url)
        payload = json.loads(data)
        if not isinstance(payload, list):
            raise TypeError("API returned a non-list candle response")
        path = root / "raw" / interval / f"api-{cursor}-{end}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        receipts.append({"url": url, "path": str(path), "sha256": digest(data),
                         "observed_at": datetime.now(UTC).isoformat()})
        if not payload:
            break
        frame = normalize_frame(pd.DataFrame([row[:6] for row in payload], columns=COLUMNS), interval)
        frame = frame[(frame.timestamp >= start) & (frame.timestamp < end)]
        if frame.empty:
            break
        frames.append(frame)
        next_cursor = int(frame.timestamp.iloc[-1]) + step
        if next_cursor <= cursor:
            raise ValueError("API tail did not progress")
        cursor = next_cursor
        time.sleep(0.15)
    return frames, receipts


def jobs_between(start: datetime, now: datetime) -> list[tuple[str, str, str]]:
    month = datetime(start.year, start.month, 1, tzinfo=UTC)
    current_month = datetime(now.year, now.month, 1, tzinfo=UTC)
    labels: list[tuple[str, str]] = []
    while month < current_month:
        labels.append(("monthly", month.strftime("%Y-%m")))
        month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    day = max(current_month, start.replace(hour=0, minute=0, second=0, microsecond=0))
    while day.date() < now.date():
        labels.append(("daily", day.strftime("%Y-%m-%d")))
        day += timedelta(days=1)
    return [(interval, period, label) for interval in STEPS for period, label in labels]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--start", default="2020-01-01")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("workers must be between 1 and 8")
    start = datetime.fromisoformat(args.start).replace(tzinfo=UTC)
    server_data = request_bytes(f"{API_BASE}/time")
    now = datetime.fromtimestamp(json.loads(server_data)["serverTime"] / 1000, UTC)
    root = args.output.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    script_sha256 = digest(Path(__file__).read_bytes())
    jobs = jobs_between(start, now)
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(lambda job: archive_job(job, root), jobs):
            receipts.append(result)
            if len(receipts) % 12 == 0:
                print(f"archives {len(receipts)}/{len(jobs)}", flush=True)
    manifest: dict[str, Any] = {"version": 1, "venue": "binance", "market": "ZECUSDT", "quote": "USDT",
        "requested_start": start.isoformat(), "server_time": now.isoformat(), "archives": receipts,
        "fetch_script_sha256_at_start": script_sha256,
        "fetch_parameters": {"start": args.start, "workers": args.workers, "output": str(root)},
        "limitations": ["Spot USDT is not USD.", "Exchange candle history is not order-book or fill evidence.",
                        "Missing bars are not synthesized; backtests must respect contiguous segments."]}
    for interval, step in STEPS.items():
        frames = [read_archive(Path(r["path"]), interval) for r in receipts
                  if r["state"] == "verified" and r["interval"] == interval]
        if not frames:
            raise ValueError(f"no verified {interval} archives")
        end = int(now.timestamp()) // step * step
        tail, tail_receipts = api_tail(interval, int(max(f.timestamp.max() for f in frames)) + step, end, root)
        frame, removed = combine_frames(frames + tail, interval)
        frame = frame[(frame.timestamp >= int(start.timestamp())) & (frame.timestamp < end)].reset_index(drop=True)
        info, gaps = coverage(frame, interval)
        path = root / f"ZEC_{interval}.csv"
        frame.to_csv(path, index=False)
        gaps.to_csv(root / f"ZEC_{interval}.gaps.csv", index=False)
        info.update({"path": str(path), "sha256": digest(path.read_bytes()), "exact_duplicates_removed": removed,
                     "api_pages": tail_receipts, "interval_seconds": step,
                     "requested_end_exclusive": end,
                     "unobserved_boundary_bars": ((int(frame.timestamp.iloc[0]) - int(start.timestamp())) // step
                                                  + (end - step - int(frame.timestamp.iloc[-1])) // step)})
        manifest[interval] = info
        print(json.dumps({"interval": interval, **{k:v for k,v in info.items() if k != "api_pages"}}), flush=True)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

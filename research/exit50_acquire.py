"""Bounded public oracle acquisition for the frozen exit50 study.

Writes only private local transport, to be archived natively before scoring.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

from oracle_leverage.exit50 import prepare_signals, signal_at
from oracle_leverage.mtf_forward import FEEDS, PRICES_URL, MtfError, decode_samples
from research.reversal_history import canonical, read_archive
from research.reversal_shapes import boundaries


def census(asset, rows, model):
    prepared = prepare_signals(rows)
    start, _, _, stop = boundaries()
    out = []
    for t in range((start // 600 + 1) * 600, stop - 610 + 1, 600):
        for family, at in (("near_end", t - 60), ("confirmed_uu", t)):
            signal = signal_at(prepared, at, family, model)
            if signal["eligible"]:
                out.append(signal)
    return out


def fetch_one(job):
    asset, t, root = job
    path = root / f"{asset}-{t}.json.zlib"
    meta = root / f"{asset}-{t}.meta.json"
    if path.exists() and meta.exists():
        try:
            info = json.loads(meta.read_text())
            raw = zlib.decompress(path.read_bytes())
            if hashlib.sha256(raw).hexdigest() == info["sha256"]:
                return info
        except (ValueError, KeyError, zlib.error):
            pass
    url = (
        PRICES_URL
        + "?"
        + urllib.parse.urlencode(
            {"feedId": FEEDS[asset], "fromMs": (t - 60) * 1000, "toMs": (t + 60) * 1000}
        )
    )
    seen = {}
    conflicts = set()
    for attempt in range(3):
        raw = None
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "oracle-exit50-study/1",
                },
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                raw = response.read(2 * 1024 * 1024 + 1)
                status = response.status
                headers = dict(response.headers)
                actual_url = response.geturl()
            if actual_url != url:
                raise ValueError("unexpected_public_redirect")
            if len(raw) > 2 * 1024 * 1024:
                raise ValueError("response_too_large")
            try:
                payload = json.loads(raw)
                for row in payload.get("data", []):
                    if not isinstance(row, dict):
                        continue
                    stamp, price, exponent = (
                        row.get("publish_time"),
                        row.get("price"),
                        row.get("exponent"),
                    )
                    if (
                        type(stamp) is not int
                        or type(price) is not int
                        or price <= 0
                        or type(exponent) is not int
                        or not -12 <= exponent <= 0
                    ):
                        continue
                    value = Decimal(price) * (Decimal(10) ** exponent)
                    if stamp in seen and seen[stamp] != value:
                        conflicts.add(stamp)
                    seen[stamp] = value
            except (ValueError, AttributeError, TypeError):
                pass
            try:
                points = decode_samples(
                    json.loads(raw), asset, (t - 60) * 1_000_000, (t + 60) * 1_000_000
                )
                grid_status = "complete"
                point_count = len(points)
            except (MtfError, ValueError):
                grid_status = "partial_or_invalid"
                point_count = None

            if grid_status == "partial_or_invalid":
                attempt_path = root / f"{asset}-{t}.attempt{attempt + 1}.body.zlib"
                attempt_path.write_bytes(zlib.compress(raw, 6))
                (root / f"{asset}-{t}.attempt{attempt + 1}.meta.json").write_text(
                    canonical(
                        {
                            "status": status,
                            "headers": headers,
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw),
                            "grid_status": grid_status,
                        }
                    )
                )
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue

            info = {
                "asset": asset,
                "slot": t,
                "url": url,
                "status": status,
                "headers": headers,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "bytes": len(raw),
                "points": point_count,
                "grid_status": grid_status,
                "price_conflict_timestamps": sorted(conflicts),
                "attempts": attempt + 1,
            }
            path.write_bytes(zlib.compress(raw, 6))
            meta.write_text(canonical(info))
            return info
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                body = exc.read(2 * 1024 * 1024 + 1)
                attempt_path = root / f"{asset}-{t}.attempt{attempt + 1}.body.zlib"
                attempt_path.write_bytes(zlib.compress(body, 6))
                (root / f"{asset}-{t}.attempt{attempt + 1}.meta.json").write_text(
                    canonical(
                        {
                            "status": exc.code,
                            "headers": dict(exc.headers),
                            "sha256": hashlib.sha256(body).hexdigest(),
                            "bytes": len(body),
                        }
                    )
                )
            else:
                info = {
                    "status": "transport_error",
                    "error": str(exc),
                    "body_received": raw is not None,
                }
                if raw is not None:
                    (root / f"{asset}-{t}.attempt{attempt + 1}.body.zlib").write_bytes(
                        zlib.compress(raw, 6)
                    )
                    info.update(
                        {
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw),
                            "headers": headers,
                        }
                    )
                (root / f"{asset}-{t}.attempt{attempt + 1}.meta.json").write_text(
                    canonical(info)
                )
            if attempt == 2:
                info = {
                    "asset": asset,
                    "slot": t,
                    "url": url,
                    "status": "failed",
                    "error": str(exc),
                    "attempts": 3,
                }
                meta.write_text(canonical(info))
                return info
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-requests", type=int, default=None)
    args = parser.parse_args()
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    bundle = json.loads(
        Path("research/mtf-reversal-20261116/model-bundle.json").read_text()
    )
    jobs = []
    for asset in ("BTC", "ZEC"):
        source = read_archive(
            f"/Users/mitch/.local/state/reversal-leverage-2289/transport/{asset}-oracle-source.json"
        )
        signals = census(asset, source["rows"], bundle["models"][asset])
        (root / f"{asset}-census.json").write_text(canonical(signals))
        slots = sorted(
            {
                s["decision_s"] + 60 if s["family"] == "near_end" else s["decision_s"]
                for s in signals
            }
        )
        jobs.extend((asset, t, root) for t in slots)
    if args.max_requests is not None:
        jobs = jobs[: args.max_requests]
    completed = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i, info in enumerate(pool.map(fetch_one, jobs), 1):
            completed.append(info)
            if i % 50 == 0:
                (root / "manifest.json").write_text(
                    canonical({"planned": len(jobs), "completed": completed})
                )
                print(f"{i}/{len(jobs)}", flush=True)
    (root / "manifest.json").write_text(
        canonical({"planned": len(jobs), "completed": completed})
    )
    print(
        canonical(
            {
                "planned": len(jobs),
                "complete": sum(x["status"] == 200 for x in completed),
                "failed": sum(x["status"] != 200 for x in completed),
            }
        )
    )


if __name__ == "__main__":
    main()

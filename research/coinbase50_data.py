"""Explicit, resumable public-candle collection. Never connects to order APIs."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode

import numpy as np
import pandas as pd

from backtester.core.data import validate_bars
from backtester.core.fetch import COINBASE_BASE, _get_json

CUTOFF = "2026-11-11T12:00:00Z"
PLAN = {"1h": (3600, 366), "15m": (900, 120), "5m": (300, 28)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def universe(root):
    """Join by venue-specific coin_id; ticker text alone cannot establish identity."""
    root = Path(root)
    products = json.loads((root / "coinbase-products-mcp.json").read_text())["products"]
    markets = {x["id"]: x for x in json.loads((root / "coingecko-markets-page1.json").read_text())}
    products = {x["base_currency_id"]: x for x in products if x["quote_currency_id"] == "USD" and x["status"] == "online"}
    identities = {}
    for page in (1, 2, 3):
        for row in json.loads((root / f"coingecko-gdax-tickers-{page}.json").read_text())["tickers"]:
            if row["target"] == "USD" and row["base"] in products:
                identities.setdefault(row["base"], set()).add(row["coin_id"])
    matched, rejected = [], []
    for symbol, product in products.items():
        ids = identities.get(symbol, set())
        if len(ids) != 1 or next(iter(ids), None) not in markets:
            rejected.append({"symbol": symbol, "coin_ids": sorted(ids), "reason": "identity ambiguous or outside captured top250"})
            continue
        market = markets[next(iter(ids))]
        matched.append({"symbol": symbol, "coin_id": market["id"], "name": market["name"], "market_cap": market["market_cap"], "rank": market["market_cap_rank"], "product": product})
    matched.sort(key=lambda x: x["rank"])
    literal = matched[:50]
    # USDT is the only peg in the captured literal50. Keep it as a control.
    directional = [x for x in matched if x["symbol"] != "USDT"][:50]
    literal_symbols = {x["symbol"] for x in literal}
    directional_symbols = {x["symbol"] for x in directional}
    assets = [dict(x, literal50=x["symbol"] in literal_symbols, directional50=x["symbol"] in directional_symbols) for x in matched if x["symbol"] in literal_symbols | directional_symbols]
    if len({x["coin_id"] for x in assets}) != len(assets):
        raise ValueError("duplicate underlying coin identities in universe")
    return {"version": 1, "cutoff": CUTOFF, "definition": "Current online Coinbase USD spot assets ordered by CoinGecko market cap; survivor-conditioned, not point-in-time historical membership", "assets": assets, "unmatched": rejected, "sources": {x.name: sha(x) for x in sorted(root.glob("*.json")) if x.name not in ("universe.json", "protocol.json")}}


class RateLimit:
    def __init__(self, requests_per_second=6):
        self.lock = threading.Lock()
        self.last = 0.0
        self.period = 1 / requests_per_second

    def wait(self):
        with self.lock:
            delay = self.period - (time.monotonic() - self.last)
            if delay > 0:
                time.sleep(delay)
            self.last = time.monotonic()


def collect_cell(root, asset, interval, limiter):
    root = Path(root)
    symbol = asset["symbol"]
    seconds, days = PLAN[interval]
    end = int(pd.Timestamp(CUTOFF).timestamp())
    start = end - days * 86400
    cell = root / "chunks" / f"{symbol}_{interval}"
    cell.mkdir(parents=True, exist_ok=True)
    chunks, errors = [], []
    # Fixed windows, including empty windows: an empty response does not prove a listing date.
    for left in range(start, end, seconds * 299):
        right = min(end, left + seconds * 299)
        path = cell / f"{left}_{right}.json"
        query = urlencode({"granularity": seconds, "start": pd.Timestamp(left, unit="s", tz="UTC").isoformat(), "end": pd.Timestamp(right, unit="s", tz="UTC").isoformat()})
        url = f"{COINBASE_BASE}/products/{asset['product']['product_id']}/candles?{query}"
        validated = False
        try:
            if path.exists():
                evidence = json.loads(path.read_text())
                if evidence["url"] != url:
                    raise ValueError("cached request binding differs")
            else:
                limiter.wait()
                rows = _get_json(url)
                evidence = {"url": url, "retrieved_at": pd.Timestamp.now(tz="UTC").isoformat(), "rows": rows}
            rows = evidence["rows"]
            if not isinstance(rows, list) or any(not isinstance(x, list) or len(x) != 6 for x in rows):
                raise ValueError("invalid Coinbase candle response")
            values = np.asarray(rows, dtype=float).reshape((-1, 6))
            if (not np.isfinite(values).all() or (values[:, 0] % seconds != 0).any()
                    or (values[:, 1:5] <= 0).any() or (values[:, 5] < 0).any()
                    or (values[:, 2] < np.maximum(values[:, 3], values[:, 4])).any()
                    or (values[:, 1] > np.minimum(values[:, 3], values[:, 4])).any()):
                raise ValueError("invalid finite candle measurements or timestamp grid")
            validated = True
            if not path.exists():
                save(path, evidence)
            chunks.extend(rows)
        except Exception as exc:  # noqa: BLE001 -- preserve per-request failure evidence
            if not validated and path.exists():
                # Retain rejected evidence while allowing a fresh request on resume.
                quarantine = path.with_suffix(".invalid-" + sha(path)[:12])
                path.replace(quarantine)
            errors.append({"url": url, "error": str(exc)})
    frame = pd.DataFrame(chunks, columns=["timestamp", "low", "high", "open", "close", "volume"])
    if len(frame) and (frame.groupby("timestamp")[["open", "high", "low", "close", "volume"]].nunique() > 1).any().any():
        raise ValueError(f"conflicting overlapping candles for {symbol} {interval}")
    frame = frame.drop_duplicates("timestamp").sort_values("timestamp")
    frame = frame[(frame.timestamp >= start) & (frame.timestamp < end)]
    frame = frame[["timestamp", "open", "high", "low", "close", "volume"]]
    if len(frame):
        frame.timestamp = frame.timestamp.astype("int64")
        validate_bars(frame, interval, strict_gaps=False)
    out = root / f"{symbol}_{interval}.csv"
    frame.to_csv(out, index=False)
    result = {"symbol": symbol, "interval": interval, "requested_start": start, "requested_end_exclusive": end, "bars": len(frame), "expected_bars": (end - start) // seconds, "missing_bars": (end - start) // seconds - len(frame), "gaps": int(np.sum(np.diff(frame.timestamp) != seconds)), "first": int(frame.timestamp.iloc[0]) if len(frame) else None, "last": int(frame.timestamp.iloc[-1]) if len(frame) else None, "errors": errors, "csv": str(out.resolve()), "sha256": sha(out), "chunks": [{"path": str(p.resolve()), "sha256": sha(p)} for p in sorted(cell.glob("*.json"))]}
    save(root / f"{symbol}_{interval}.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    path = args.root / "universe.json"
    if not path.exists():
        save(path, universe(args.root))
    data = json.loads(path.read_text())
    limiter = RateLimit()
    jobs = [(asset, interval) for asset in data["assets"] for interval in PLAN]
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(collect_cell, args.root, a, i, limiter) for a, i in jobs]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{len(results)}/{len(jobs)} {result['symbol']} {result['interval']}: {result['bars']} bars; {result['missing_bars']} missing; {len(result['errors'])} errors", flush=True)
            save(args.root / "coverage.json", sorted(results, key=lambda x: (x["symbol"], x["interval"])))
    return int(any(x["errors"] for x in results))


if __name__ == "__main__":
    raise SystemExit(main())

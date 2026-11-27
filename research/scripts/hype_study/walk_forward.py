"""Rolling walk-forward of the HYPE RSI dip buyer on three real histories.

For each block: pick RSI (period, oversold, exit) on the trailing training window
only, then trade the next test window with that choice. Every test block starts flat
(cash), so no position or profit carries across blocks and nothing before the block
start can fill. Costs apply to every fill. The frozen forward-test rule RSI(14) 30/55,
MA 20/50 and holding are scored on exactly the same test blocks.

    python research/scripts/hype_study/walk_forward.py --out DIR

Reads public market data only (Binance spot klines, Hyperliquid candles). Writes
DIR/walk_forward.json and prints markdown tables. Never places an order.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies.ma_crossover import MaCrossover
from backtester.core.strategies.rsi import RsiMeanReversion
from backtester.core.types import CostConfig

CAPITAL = 10_000.0
SLIPPAGE_BPS = 2.0
FEES = (10.0, 25.0, 60.0)
MIN_TRAIN_TRADES = 3
GRID = [(p, o, x) for p, o, x in itertools.product((7, 14, 21), (20, 25, 30, 35), (45, 50, 55, 60, 65))]
FROZEN = (14, 30.0, 55.0)
FIELDS = ("ts", "open", "high", "low", "close", "volume")


def get(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {"User-Agent": "solmargintrader-research/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def binance_1h(first_ms):
    rows, start = [], first_ms
    now_ms = int(time.time() * 1000)
    while start < now_ms:
        page = get(f"https://data-api.binance.vision/api/v3/klines?symbol=HYPEUSDT&interval=1h&startTime={start}&limit=1000")
        if not page:
            break
        rows += page
        start = page[-1][0] + 3_600_000
        if len(page) < 1000:
            break
        time.sleep(0.2)
    closed = [r for r in rows if r[6] < now_ms]  # only bars whose close time has passed
    return [(r[0] // 1000, *map(float, r[1:6])) for r in closed]


def hyperliquid(interval, days):
    if interval not in ("1h", "1d"):
        raise ValueError("interval must be 1h or 1d")
    end = int(time.time() * 1000)
    start, rows = end - days * 86_400_000, []
    while start < end:
        page = get("https://api.hyperliquid.xyz/info", json.dumps({"type": "candleSnapshot", "req": {
            "coin": "HYPE", "interval": interval, "startTime": start, "endTime": end}}).encode(),
            {"content-type": "application/json"})
        if not page:
            break
        rows += page
        nxt = page[-1]["t"] + 1
        if nxt <= start or len(page) < 500:
            break
        start = nxt
        time.sleep(0.3)
    seen = {r["t"]: r for r in rows if r["T"] < end}  # drop the still-forming bar
    return [(t // 1000, float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"]), float(r["v"])) for t, r in sorted(seen.items())]


def longest_contiguous(rows, step):
    best, cur = [], []
    for row in sorted(rows):
        if cur and row[0] - cur[-1][0] != step:
            best = max(best, cur, key=len)
            cur = []
        cur.append(row)
    best = max(best, cur, key=len)
    return best, len(rows) - len(best)


def arrays(rows):
    return {key: np.asarray([r[i] for r in rows], dtype="int64" if i == 0 else "float64") for i, key in enumerate(FIELDS)}


class Gated:
    """Run any strategy over warm-up bars but hold cash, with no carried state, before `activation`."""

    def __init__(self, inner, activation):
        self.inner, self.activation = inner, activation
        self.name, self.params = inner.name, dict(inner.params)

    def warmup_bars(self):
        return self.inner.warmup_bars()

    def on_bar(self, history):
        target = self.inner.on_bar(history)
        if history.bar().ts < self.activation:
            if hasattr(self.inner, "_holding"):
                self.inner._holding = False
            return 0.0
        return target


def run(strategy, bars, interval, fee):
    config = EngineConfig(interval=interval, fill_delay=1, initial_capital=CAPITAL,
                          costs=CostConfig(fee_bps=fee, slippage_bps=SLIPPAGE_BPS))
    return run_backtest(strategy, bars, config, close_at_end=False)


def cut(bars, lo, hi):
    return {k: v[lo:hi] for k, v in bars.items()}


def block_return(strategy_factory, bars, lo, test_lo, hi, interval, fee):
    """Return of one test block, with history from `lo` for warm-up and flat before `test_lo`."""
    window = cut(bars, lo, hi)
    activation = int(bars["ts"][test_lo])
    result = run(Gated(strategy_factory(), activation), window, interval, fee)
    return float(result.equity[-1] / CAPITAL - 1.0), len(result.trades) + int(result.exposure[-1] > 0)


def walk(bars, interval, train, test, fee):
    n = len(bars["ts"])
    blocks, lo = [], 0
    while lo + train + test <= n:
        test_lo, hi = lo + train, lo + train + test
        scored = []
        for p, o, x in GRID:
            result = run(RsiMeanReversion(p, float(o), float(x)), cut(bars, lo, test_lo), interval, fee)
            trades = len(result.trades) + int(result.exposure[-1] > 0)
            if trades >= MIN_TRAIN_TRADES:
                scored.append((float(result.equity[-1] / CAPITAL - 1.0), (p, o, x)))
        pick = max(scored)[1] if scored else None
        selected, trades = (0.0, 0) if pick is None else block_return(
            lambda pick=pick: RsiMeanReversion(pick[0], float(pick[1]), float(pick[2])), bars, lo, test_lo, hi, interval, fee)
        frozen, frozen_trades = block_return(lambda: RsiMeanReversion(14, 30.0, 55.0), bars, lo, test_lo, hi, interval, fee)
        ma, _ = block_return(lambda: MaCrossover(20, 50), bars, max(0, test_lo - 50), test_lo, hi, interval, fee) if test_lo >= 50 else (0.0, 0)
        hold = float(bars["close"][hi - 1] / bars["open"][test_lo] - 1.0)
        # Every fixed grid choice on the same block: the control for "was the pick better than any rule".
        fixed = {f"{p}-{o}-{x}": block_return(lambda p=p, o=o, x=x: RsiMeanReversion(p, float(o), float(x)), bars, lo, test_lo, hi, interval, fee)[0]
                 for p, o, x in GRID}
        blocks.append({"grid": fixed, "test_start": int(bars["ts"][test_lo]), "test_end": int(bars["ts"][hi - 1]), "pick": pick,
                       "train_return": max(scored)[0] if scored else None, "selected": selected, "selected_trades": trades,
                       "frozen": frozen, "frozen_trades": frozen_trades, "ma20_50": ma, "hold": hold})
        lo += test
    return blocks


def chain(blocks, key):
    return float(np.prod([1.0 + b[key] for b in blocks]) - 1.0)


def summarize(blocks):
    out = {"blocks": len(blocks), "span_hold": float(np.prod([1.0 + b["hold"] for b in blocks]) - 1.0)}
    for key in ("selected", "frozen", "ma20_50"):
        values = np.asarray([b[key] for b in blocks])
        out[key] = {"chained": chain(blocks, key), "positive_blocks": int((values > 0).sum()), "flat_blocks": int((values == 0).sum()),
                    "beat_hold_blocks": int(sum(b[key] > b["hold"] for b in blocks)), "median": float(np.median(values)),
                    "worst": float(values.min()), "best": float(values.max())}
    fixed = {key: float(np.prod([1.0 + b["grid"][key] for b in blocks]) - 1.0) for key in blocks[0]["grid"]}
    values = np.asarray(sorted(fixed.values()))
    out["fixed_grid"] = {"median": float(np.median(values)), "best": float(values[-1]), "worst": float(values[0]),
                         "positive": int((values > 0).sum()), "combos": len(values),
                         "frozen_percentile": float((values < fixed["14-30-55"]).mean()),
                         "selected_percentile": float((values < out["selected"]["chained"]).mean()),
                         "best_combo": max(fixed, key=fixed.get)}
    picks = [b["pick"] for b in blocks if b["pick"] is not None]
    out["no_pick_blocks"] = len(blocks) - len(picks)
    out["frozen_picked"] = int(sum(p == FROZEN for p in picks))
    out["distinct_picks"] = len(set(picks))
    return out


def day(ts):
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    sets = {}
    for name, rows, interval, step, train, test in (
            ("Binance HYPEUSDT 1h", binance_1h(1_746_000_000_000), "1h", 3600, 720, 168),
            ("Hyperliquid HYPE perp 1h", hyperliquid("1h", 200), "1h", 3600, 720, 168),
            ("Hyperliquid HYPE perp 1d", hyperliquid("1d", 800), "1d", 86400, 180, 30)):
        rows, dropped = longest_contiguous(rows, step)
        sets[name] = (arrays(rows), interval, train, test, dropped)
    report = {"generated": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime()), "grid": GRID, "min_train_trades": MIN_TRAIN_TRADES,
              "slippage_bps": SLIPPAGE_BPS, "datasets": {}}
    for name, (bars, interval, train, test, dropped) in sets.items():
        entry = {"bars": len(bars["ts"]), "first": day(int(bars["ts"][0])), "last": day(int(bars["ts"][-1])),
                 "train_bars": train, "test_bars": test, "bars_outside_longest_run": dropped,
                 "hold_whole_series": float(bars["close"][-1] / bars["open"][0] - 1.0), "fees": {}}
        for fee in FEES:
            blocks = walk(bars, interval, train, test, fee)
            entry["fees"][str(int(fee))] = {"summary": summarize(blocks), "blocks": blocks}
            s = entry["fees"][str(int(fee))]["summary"]
            print(f"{name} fee {fee:g}bps: {s['blocks']} blocks  selected {s['selected']['chained']:+.1%}  frozen {s['frozen']['chained']:+.1%}  "
                  f"ma {s['ma20_50']['chained']:+.1%}  hold {s['span_hold']:+.1%}", flush=True)
        report["datasets"][name] = entry
    (args.out / "walk_forward.json").write_text(json.dumps(report, indent=1))
    compact = json.loads(json.dumps(report))
    for entry in compact["datasets"].values():
        for fee in entry["fees"].values():
            for block in fee["blocks"]:
                block.pop("grid")
    (args.out / "walk_forward_summary.json").write_text(json.dumps(compact, indent=1))


if __name__ == "__main__":
    main()

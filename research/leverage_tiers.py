"""Low / medium / high margin tiers across the existing strategies, CPCV out-of-sample.

    python3 -m research.leverage_tiers --asset SOL --interval 1d
    python3 -m research.leverage_tiers --asset SOL --interval 1d --tiers 2,5,20

Every registered strategy (at the sweep's horizon parameters) is run as a
Jupiter-Perps position at each tier's leverage, with fees, slippage, borrow
carry, maintenance margin and liquidation. Liquidation is checked on every held
bar and, where a finer layer covers the bar, on the 1m/1h bars inside it, so a
daily close cannot rescue a position that was liquidated intrabar.

Reported per tier, pooled over strategies and CPCV paths: median out-of-sample
path Sharpe, share of paths with positive Sharpe, liquidations, median and worst
max drawdown, and P(ruin) = share of paths whose equity touched <= RUIN_LEVEL of
the starting capital. Results go to research/results/leverage_tiers_*.
Simulation only: no keys, no network.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import cpcv_evaluate  # noqa: E402
from backtester.core.leverage import resolve_tiers, tier_config  # noqa: E402
from backtester.core.strategies import build  # noqa: E402
from backtester.core.types import IntrabarLayer, periods_per_year  # noqa: E402
from research.sweep import HORIZONS, data_dir, load_horizon  # noqa: E402

OUT = REPO / "research" / "results"
RUIN_LEVEL = 0.10  # equity at or below 10% of the start counts as ruin
# Hourly SOL has two disclosed gaps and the engine refuses gapped cadence, so the
# tier study is daily-only; 1h and 1m enter as intrabar layers, not as the series.
HORIZON_FOR = {"1d": "medium"}


def _layer(path: Path, interval: str) -> IntrabarLayer | None:
    if not path.exists():
        return None
    df = pd.read_csv(path).sort_values("timestamp").drop_duplicates("timestamp")
    return IntrabarLayer(interval, {
        "ts": df["timestamp"].to_numpy("int64"),
        "open": df["open"].to_numpy(float), "high": df["high"].to_numpy(float),
        "low": df["low"].to_numpy(float), "close": df["close"].to_numpy(float),
    })


def load_layers(asset: str, interval: str) -> list[IntrabarLayer]:
    """Finest first. 1d uses 1m then 1h. Missing files are skipped."""
    d = data_dir()
    wanted = {"1d": [("1m", f"{asset}_1m_last30d.csv"), ("1h", f"{asset}_1h.csv")]}.get(interval, [])
    return [l for l in (_layer(d / f, iv) for iv, f in wanted) if l is not None]


def path_stats(blocks, k: int) -> list[dict]:
    """One row per CPCV path: Sharpe, max drawdown, min equity, ruin, liquidations."""
    usable = [b for b in blocks if b.usable]
    rows = []
    for combo in itertools.combinations(range(len(usable)), k):
        parts = [usable[i] for i in sorted(combo)]
        r = np.concatenate([b.returns for b in parts])
        eq = np.concatenate([[1.0], np.cumprod(1.0 + r)])
        peak = np.maximum.accumulate(eq)
        rows.append({
            "max_dd": float(np.max(1.0 - eq / peak)),
            "min_equity": float(eq.min()),
            "ret": float(eq[-1] - 1.0),
            "liqs": sum(b.liquidations for b in parts),
            "trades": sum(b.trades for b in parts),
        })
    return rows


def run(asset: str, interval: str, tiers, groups: int, k: int):
    arrays, _ = load_horizon(HORIZON_FOR[interval], asset)
    params = HORIZONS[HORIZON_FOR[interval]]["params"]
    layers = load_layers(asset, interval)
    per, pooled = [], {}
    levels = [("1x", 1.0)] + [(t.name, t.leverage) for t in tiers]
    for tname, lev in levels:
        cfg = tier_config(lev, interval, intrabar=layers)
        pooled[tname] = {"sharpe": [], "pos": [], "dd": [], "ruin": [], "liq": [], "ret": [], "anyliq": []}
        for name, p in params.items():
            res = cpcv_evaluate(name, lambda n=name, q=p: build(n, **q), arrays, cfg,
                                n_groups=groups, k_test=k)
            if res.insufficient:
                continue
            st = path_stats(res.blocks, k)
            per.append({
                "tier": tname, "leverage": lev, "strategy": name,
                "median_sharpe": res.median_sharpe, "frac_positive": res.frac_positive,
                "median_return": res.median_return, "trades": res.total_trades,
                "liquidations": sum(s["liqs"] for s in st) / max(len(st), 1),
                "median_max_dd": float(np.median([s["max_dd"] for s in st])),
                "p_ruin": float(np.mean([s["min_equity"] <= RUIN_LEVEL for s in st])),
            })
            pz = pooled[tname]
            pz["sharpe"].append(res.median_sharpe)
            pz["pos"] += list(res.path_sharpes > 0)
            pz["dd"] += [s["max_dd"] for s in st]
            pz["ruin"] += [s["min_equity"] <= RUIN_LEVEL for s in st]
            pz["liq"] += [s["liqs"] for s in st]
            pz["anyliq"] += [s["liqs"] > 0 for s in st]
            pz["ret"] += [s["ret"] for s in st]
    summary = []
    for tname, lev in levels:
        z = pooled[tname]
        if not z["sharpe"]:
            continue
        summary.append({
            "tier": tname, "leverage": lev, "strategies": len(z["sharpe"]), "paths": len(z["pos"]),
            "oos_median_sharpe": float(np.nanmedian(z["sharpe"])),
            "pct_paths_positive": 100 * float(np.mean(z["pos"])),
            "median_path_return_pct": 100 * float(np.median(z["ret"])),
            "liquidations_per_path": float(np.mean(z["liq"])),
            "pct_paths_with_liquidation": 100 * float(np.mean(z["anyliq"])),
            "median_max_dd_pct": 100 * float(np.median(z["dd"])),
            "worst_max_dd_pct": 100 * float(np.max(z["dd"])),
            "p_ruin_pct": 100 * float(np.mean(z["ruin"])),
        })
    return pd.DataFrame(per), pd.DataFrame(summary), layers, arrays


def coverage_audit(arrays, layers) -> dict:
    """How much of the coarse series a finer layer covers, and where feeds disagree."""
    if not layers:
        return {"layers": []}
    ts = arrays["ts"]; span = int(ts[1] - ts[0])
    out = {"bars": int(len(ts)), "layers": []}
    for lay in layers:
        a = np.searchsorted(lay.ts, ts, "left"); b = np.searchsorted(lay.ts, ts + span, "left")
        full = (b - a) == span // lay.seconds
        mism = 0
        for i in np.where(full)[0]:
            if arrays["low"][i] < lay.low[a[i]:b[i]].min() * (1 - 5e-4):
                mism += 1
        out["layers"].append({"interval": lay.interval, "bars_fully_covered": int(full.sum()),
                              "daily_low_below_fine_low_by_5bps": mism})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--asset", default="SOL")
    ap.add_argument("--interval", default="1d", choices=sorted(HORIZON_FOR))
    ap.add_argument("--tiers", default=None, help="three ascending leverages, e.g. 2,5,20")
    ap.add_argument("--groups", type=int, default=8)
    ap.add_argument("--k", type=int, default=2)
    a = ap.parse_args(argv)
    per, summ, layers, arrays = run(a.asset.upper(), a.interval, resolve_tiers(a.tiers), a.groups, a.k)
    cov = coverage_audit(arrays, layers)
    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"leverage_tiers_{a.asset.lower()}_{a.interval}"
    per.to_csv(OUT / f"{stem}_per_strategy.csv", index=False)
    summ.to_csv(OUT / f"{stem}_summary.csv", index=False)
    (OUT / f"{stem}.json").write_text(json.dumps(
        {"coverage": cov, "summary": summ.to_dict("records"), "ruin_level": RUIN_LEVEL,
         "groups": a.groups, "k": a.k}, indent=2))
    pd.set_option("display.width", 200)
    print(summ.round(3).to_string(index=False))
    print("coverage:", json.dumps(cov))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

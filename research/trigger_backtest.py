"""Trade the mined triggers through the leverage tiers, out of sample only.

Called by `python3 -m research.triggers --backtest`. Takes the qualified
(reliable) triggers; if none qualified, takes the best near-misses and labels
every number EXPLORATORY. The stop for each trigger is its discovery-period MAE
(`stop_frac`), never a number chosen after seeing the validation period.

Runs only on the validation period (after the split and embargo), warmed from
earlier bars, so the discovery period never contributes to a result here:
  * one run of the validation block, per tier;
  * a 4-block CPCV over the validation period (C(4,2)=6 paths), per tier.
Costs, borrow carry, maintenance margin and intrabar liquidation come from
PR 1 (`backtester.core.leverage`).
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.cpcv import evaluate_block, _sharpe
from backtester.core.leverage import DEFAULT_TIERS, tier_config
from backtester.core.strategies import build
from backtester.core.types import periods_per_year

OUT = Path(__file__).resolve().parent / "results"
TOP_NEAR_MISSES = 5
VALIDATION_BLOCKS = 4


def select(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Reliable triggers if any, else the best OHLCV-only near-misses by discovery p-value (exploratory)."""
    ohlcv = df[~df["uses_funding"] & (df["direction"].isin(["long", "short"]))]
    rel = ohlcv[ohlcv["reliable"]]
    if len(rel):
        return rel, "qualified"
    # Ranked by DISCOVERY p-value only. Ranking by the validation result would
    # pick the luckiest validation and then "confirm" it on the same bars.
    nm = ohlcv[ohlcv["oos_n"] >= 10].sort_values("is_p").drop_duplicates(["direction", "horizon"]).head(TOP_NEAR_MISSES)
    return nm, "exploratory"


def run(asset: str, interval: str, df: pd.DataFrame, meta: dict) -> pd.DataFrame:
    from research.triggers import H_MAX, load_dataset, split_index
    from research.leverage_tiers import load_layers

    if interval != "1d":
        print("trigger backtest skipped: hourly SOL has gaps the engine refuses; use --interval 1d")
        return pd.DataFrame()
    chosen, label = select(df)
    if chosen.empty:
        print("trigger backtest: no trigger to trade")
        return pd.DataFrame()
    ds = load_dataset(asset, interval, with_funding=False)
    arrays = {"ts": ds.ts, "open": ds.o, "high": ds.h, "low": ds.l, "close": ds.c, "volume": ds.v}
    start = split_index(ds) + H_MAX
    end = len(ds.ts)
    bounds = np.linspace(start, end, VALIDATION_BLOCKS + 1).astype(int)
    layers = load_layers(asset, interval)
    ppy = periods_per_year(interval)
    rows = []
    for _, t in chosen.iterrows():
        spec = dict(conditions=t["conditions"], direction=1 if t["direction"] == "long" else -1,
                    horizon=int(t["horizon"]), stop=round(float(t["stop_frac"]), 4) if t["stop_frac"] == t["stop_frac"] else 0.0)
        for tier in [("1x", 1.0)] + [(x.name, x.leverage) for x in DEFAULT_TIERS]:
            cfg = tier_config(tier[1], interval, allow_short=True, intrabar=layers)
            make = lambda s=spec: build("trigger_trade", **s)
            blocks = [evaluate_block(make, arrays, int(a), int(b), cfg) for a, b in zip(bounds[:-1], bounds[1:])]
            blocks = [b for b in blocks if b.usable]
            full = evaluate_block(make, arrays, start, end, cfg)
            paths = []
            for combo in itertools.combinations(range(len(blocks)), 2):
                r = np.concatenate([blocks[i].returns for i in combo])
                eq = np.concatenate([[1.0], np.cumprod(1 + r)])
                paths.append((_sharpe(r, ppy), float(eq[-1] - 1), float((1 - eq / np.maximum.accumulate(eq)).max()),
                              sum(blocks[i].liquidations for i in combo)))
            eq_full = np.concatenate([[1.0], np.cumprod(1 + full.returns)]) if full.usable else np.ones(1)
            rows.append({
                "label": label, "conditions": spec["conditions"], "direction": t["direction"],
                "horizon": spec["horizon"], "stop": spec["stop"], "tier": tier[0], "leverage": tier[1],
                "oos_trades": full.trades, "oos_liquidations": full.liquidations,
                "oos_return": float(eq_full[-1] - 1), "oos_sharpe": _sharpe(full.returns, ppy) if full.usable else float("nan"),
                "oos_max_dd": float((1 - eq_full / np.maximum.accumulate(eq_full)).max()),
                "cpcv_paths": len(paths),
                "cpcv_median_sharpe": float(np.median([p[0] for p in paths])) if paths else float("nan"),
                "cpcv_pct_positive": float(np.mean([p[0] > 0 for p in paths])) if paths else float("nan"),
                "cpcv_median_return": float(np.median([p[1] for p in paths])) if paths else float("nan"),
                "cpcv_liquidations": int(sum(p[3] for p in paths)),
                "cpcv_p_ruin": float(np.mean([(p[2] >= 0.9) for p in paths])) if paths else float("nan"),
            })
    res = pd.DataFrame(rows)
    stem = f"trigger_backtest_{asset.lower()}_{interval}"
    res.to_csv(OUT / f"{stem}.csv", index=False)
    (OUT / f"{stem}.json").write_text(json.dumps({"label": label, "validation_start": meta["validation_events_start"],
                                                  "validation_end": meta["validation_end"], "triggers": len(chosen)}, indent=2))
    pd.set_option("display.width", 220)
    print(f"[{label.upper()}] trigger strategy, validation period only")
    print(res[["conditions", "direction", "horizon", "tier", "oos_trades", "oos_return", "oos_sharpe",
               "oos_liquidations", "cpcv_median_sharpe", "cpcv_pct_positive"]].round(3).to_string(index=False))
    return res

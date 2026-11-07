"""Run the predeclared ladder from research/results/grid_review_20261107.json on bars it never saw.

The review used a cache that ended 2026-08-04. This script scores the same configuration
(bounds 85%-115% of the first close, seven geometric rungs, $12 per rung, $144 account) on
bars from 2026-08-05 onward, at the review's costs and at twice those costs. Nothing is fitted.

    python3 -m backtester.core.fetch --asset SOL --interval 1d --start 2026-08-01 --out /tmp/SOL_1d_holdout.csv
    python3 research/grid_holdout.py /tmp/SOL_1d_holdout.csv --out research/results/grid_holdout_20261107.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backtester.core.data import frame_to_arrays, validate_bars  # noqa: E402
from backtester.core.gridsim import GridConfig, run_grid_backtest  # noqa: E402
from backtester.core.types import CostConfig  # noqa: E402

# First bar after the review's cache ended (2026-08-04). Anything earlier is not holdout.
HOLDOUT_START_TS = 1785888000  # 2026-08-05 00:00 UTC
# Exclusive end: the 2026-11-07 bar was still forming when this was fetched, so it is not a finished bar.
HOLDOUT_END_TS = 1794009600  # 2026-11-07 00:00 UTC
ACCOUNT_USD = 144.0


def run(csv_path: Path) -> dict:
    raw = pd.read_csv(csv_path)
    frame = validate_bars(
        raw[(raw.timestamp >= HOLDOUT_START_TS) & (raw.timestamp < HOLDOUT_END_TS)].reset_index(drop=True), "1d"
    )
    arrays = frame_to_arrays(frame)
    first = float(arrays["close"][0])
    out = {
        "schema": "grid-holdout/1",
        "data_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "bars": len(frame),
        "first_ts": int(arrays["ts"][0]),
        "last_ts": int(arrays["ts"][-1]),
        "first_close": first,
        "last_close": float(arrays["close"][-1]),
        "runs": {},
    }
    for label, mult in (("review_costs", 1), ("double_costs", 2)):
        costs = CostConfig(fee_bps=6 * mult, slippage_bps=2 * mult)
        cfg = GridConfig(lower=first * 0.85, upper=first * 1.15, rungs=7, notional_per_rung_usd=12)
        r = run_grid_backtest(cfg, arrays, initial_capital=ACCOUNT_USD, interval="1d", costs=costs)
        out["runs"][label] = {
            "grid_return": r.metrics.total_return,
            "hold_return": r.baseline_metrics.total_return,
            "round_trips": r.round_trips,
            "realized_pnl_usd": r.realized_pnl_usd,
            "fees_usd": r.fees_paid_usd,
            "slippage_usd": r.slippage_paid_usd,
            "bars_above_ladder": r.bars_above_grid,
            "bars_below_ladder": r.bars_below_grid,
            "max_drawdown": r.metrics.max_drawdown,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    result = run(args.csv)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

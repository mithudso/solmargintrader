"""Retrospective equal-notional MA comparison on the validated oracle window.

The common loader and order engine are independently owned. This wrapper never
claims Coinbase perpetual parity, an out-of-sample test, or live-net returns.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from research.oracle_common_window import aggregate, load_window
from research.oracle_compare import compare

from research.shape_study import protected_intervals, refuse_reserved
from research.tv_single_ma import SingleMovingAverage
from research.tv_two_ma import TwoMovingAverages


def run(strategy_name: str, source: Path, ledger: Path) -> dict:
    if strategy_name not in ("single", "two"):
        raise ValueError("strategy must be single or two")
    rows, metadata = load_window(source, ledger)
    frame = pd.DataFrame({"timestamp": [int(row[0]) for row in rows]})

    def check_reservations() -> None:
        refuse_reserved(frame, "1m", protected_intervals(ledger, ("ZEC", "BTC")))

    results = []
    for step in (600, 900):
        bars = aggregate(rows, step)
        strategy = SingleMovingAverage() if strategy_name == "single" else TwoMovingAverages()
        intents = [strategy.on_close(bar.close) for bar in bars]
        # The common function requires a default for its separate source-size
        # case. One unit is only a computational placeholder; discard that
        # case because the owner's strategy-tester sizing is unknown.
        runs = compare(bars, intents, default_qty=1, step_seconds=step,
                       before_run=check_reservations, after_run=check_reservations)
        for result in runs:
            if result["sizing"] == "equal_notional":
                results.append({"step_seconds": step, "bars": len(bars),
                                "entry_intents": sum(len(order) for order in intents),
                                "buy_and_hold_usd_pnl_before_costs":
                                    1000 * (bars[-1].close / bars[0].open - 1), **result})
    _, after = load_window(source, ledger)
    return {"strategy": strategy_name, "source": metadata,
            "post_source_sha256": after["source_sha256"], "results": results,
            "assumptions": "Retrospective Jupiter ZEC/USD oracle proxy; 1000 USD target at signal "
            "close, unit multiplier 1, 100000 USD initial cash, next-open market fill. No funding, "
            "spread, margin, liquidation, Coinbase perpetual parity or OOS claim."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy", choices=("single", "two"))
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.strategy, args.source, args.ledger), sort_keys=True))


if __name__ == "__main__":
    main()

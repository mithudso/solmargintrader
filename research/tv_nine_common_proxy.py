"""Reproduce nine source-strategy sensitivities on the frozen oracle window.

This is retrospective research, not TradingView or executable venue parity.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.oracle_common_window import aggregate, load_window
from research.oracle_compare import compare
from research.rs_zigzag_equal_proxy import run as zigzag_run
from research.tradingview_sar_pivot_proxy import run as sar_pivot_run
from research.tv_channel_breakout_intents import channel_breakout_intents
from research.tv_ma_proxy import run as ma_run
from research.tv_momentum_intents import momentum_intents
from research.tv_price_channel_intents import price_channel_intents
from research.tv_volty_close_intents import volty_close_intents


def run(source: Path, ledger: Path) -> dict:
    rows, metadata = load_window(source, ledger)
    results = []
    for step in (600, 900):
        bars = aggregate(rows, step)
        closes, highs, lows = [], [], []
        groups = {
            name: []
            for name in ("momentum", "price_channel", "channel_breakout", "volty_close")
        }
        for bar in bars:
            closes.append(bar.close)
            highs.append(bar.high)
            lows.append(bar.low)
            groups["momentum"].append(momentum_intents(closes, bar.high, bar.low, 0.01))
            groups["price_channel"].append(price_channel_intents(closes, highs, lows))
            groups["channel_breakout"].append(
                channel_breakout_intents(closes, highs, lows, 0.01)
            )
            groups["volty_close"].append(volty_close_intents(closes, highs, lows))

        def guard() -> None:
            load_window(source, ledger)

        for name, orders in groups.items():
            for case in compare(
                bars,
                orders,
                step_seconds=step,
                default_qty=1,
                before_run=guard,
                after_run=guard,
            ):
                if case["sizing"] == "equal_notional":
                    results.append({"strategy": name, "step_seconds": step, **case})
    return {
        "schema": "tv-nine-common-proxy/v1",
        "source": metadata,
        "momentum_channel_volty": results,
        "single_ma": ma_run("single", source, ledger),
        "two_ma": ma_run("two", source, ledger),
        "sar_pivot": sar_pivot_run(source, ledger),
        "zigzag": zigzag_run(source, ledger),
        "qualification": "Retrospective Jupiter oracle proxy; neither Coinbase perpetual nor out-of-sample. Legacy ZigZag leaks future data and is not rankable.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.source, args.ledger)
    with args.output.open("x") as output:
        json.dump(result, output, sort_keys=True, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()

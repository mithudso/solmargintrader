"""Retrospective SAR and Pivot equal-notional oracle sensitivities."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research.oracle_common_window import aggregate, load_window
from research.oracle_compare import compare
from research.tradingview_pivot_reversal import pivot_intents
from research.tradingview_sar import sar_intents


def run(source: Path, ledger: Path) -> dict:
    rows, before = load_window(source, ledger)
    result = []
    for step in (600, 900):
        bars = aggregate(rows, step)
        for strategy, tie in (("sar", None), ("pivot", "strict"),
                              ("pivot", "earliest"), ("pivot", "latest")):
            orders = (sar_intents(bars, step_seconds=step) if strategy == "sar" else
                      pivot_intents(bars, step_seconds=step, tick_size=.01, ties=tie))
            def guard() -> None:
                load_window(source, ledger)
            # Quantity 1 is an internal placeholder. The unverified source
            # sizing outputs are discarded and must not be reported as parity.
            cases = compare(bars, orders, step_seconds=step, default_qty=1,
                            before_run=guard, after_run=guard)
            result.extend({"strategy": strategy, "tie_policy": tie, "step_seconds": step, **case}
                          for case in cases if case["sizing"] == "equal_notional")
    _, after = load_window(source, ledger)
    return {"schema": "tv-sar-pivot-common-proxy/v1", "before": before, "after": after,
            "initial_capital_usd": 100000, "target_usd_per_signal": 1000,
            "pivot_tick_scenario": .01, "results": result,
            "limitations": ["Previously observed Jupiter ZEC/USD oracle proxy, not Coinbase perpetual or OOS.",
                            "Pivot tie semantics are unverified; three explicit sensitivity policies are shown.",
                            "The .01 tick is TradingView scanner metadata, not an observed oracle tick.",
                            "No funding, margin, liquidation or spread beyond slippage is modelled.",
                            "Common OHLC fill assumptions and one-unit multiplier are not venue/TV parity.",
                            "Unverified source-default order sizing outputs are intentionally withheld."]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    data = run(a.source, a.ledger)
    raw = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    with a.output.open("xb") as f:
        f.write(raw)
    print(json.dumps({"rows": len(data["results"]), "sha256": hashlib.sha256(raw).hexdigest()}))


if __name__ == "__main__":
    main()

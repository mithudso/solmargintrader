"""Common-window RS ZigZag sizing comparison; never TV or venue parity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from research.oracle_common_window import aggregate, load_window
from research.oracle_compare import compare
from research.pine_bar_emulator import Intent
from research.rs_zigzag import signals


def run(source: Path, ledger: Path) -> dict:
    rows, before = load_window(source, ledger)
    scenarios = []
    for step in (600, 900):
        bars = aggregate(rows, step)
        for mode in ("legacy", "confirmed"):
            flags = signals(bars, step, mode)
            orders = []
            for f in flags:
                group = []
                if f["buy_entry"]:
                    group.append(Intent("target01_buy", "entry", 1, qty=10000))
                if f["buy_close"]:
                    group.append(Intent("target01_buy", "close", 1))
                if f["sell_entry"]:
                    group.append(Intent("target01_sell", "entry", -1, qty=10000))
                if f["sell_close"]:
                    group.append(Intent("target01_sell", "close", -1))
                orders.append(group)
            def check_reservations() -> None:
                load_window(source, ledger)

            for item in compare(bars, orders, step_seconds=step, default_qty=1,
                                before_run=check_reservations, after_run=check_reservations):
                scenarios.append({"step_seconds": step, "mode": mode, **item})
    _, after = load_window(source, ledger)
    return {"schema": "rs-zigzag-common-window/v1", "before": before, "after": after,
            "initial_capital_usd": 100000, "target_usd": 1000,
            "source_qty": 10000, "scenarios": scenarios,
            "limitations": ["Retrospective Jupiter oracle USD proxy, not Coinbase USDC perpetual or OOS.",
                            "Legacy path deliberately leaks final HTF values on historical bars.",
                            "Fixed signal-close target quantity assumes one price unit per contract.",
                            "No margin, liquidation, funding or spread beyond slippage is modelled.",
                            "Source-sized uncollateralized account may go negative; not feasible ROI.",
                            "Exact Pine and TradingView fill parity remains unverified."]}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    data = run(args.source, args.ledger)
    raw = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    with args.output.open("xb") as out:
        out.write(raw)
    print(json.dumps({"rows": len(data["scenarios"]), "sha256": hashlib.sha256(raw).hexdigest()}))


if __name__ == "__main__":
    main()

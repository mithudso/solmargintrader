"""Frozen retrospective Jupiter-oracle sensitivity; never TV parity."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from research.reversal_history import read_archive, validated_rows
from research.rs_zigzag import Bar, ExecutionAssumptions, signals, simulate_decisions
from research.shape_study import protected_intervals, refuse_reserved

SOURCE_SHA256 = "8b5eb4f54851fad81c28137bda85e643e34c93da349c3c0178b8df271948b2bc"
SOURCE_ID = "art:daf887a414eb6078d63bbb2e557fbe6ebfc29433c43feaec69506a884bfda896"
START = int(datetime(2026, 10, 10, 21, tzinfo=UTC).timestamp())
STOP = int(datetime(2026, 11, 8, 19, tzinfo=UTC).timestamp())
ALIASES = ("ZEC", "ZECUSD", "ZECUSDC", "ZECUSDC.P")


def aggregate(rows: list[list[float]], step: int) -> list[Bar]:
    minutes = step // 60
    if step not in (600, 900) or len(rows) % minutes:
        raise ValueError("window must comprise complete 10- or 15-minute bars")
    result = []
    for i in range(0, len(rows), minutes):
        segment = rows[i:i+minutes]
        if segment[0][0] % step or any(segment[j][0] != segment[0][0]+60*j for j in range(minutes)):
            raise ValueError("unaligned or incomplete minute group")
        result.append(Bar(int(segment[0][0]), segment[0][1], max(x[2] for x in segment),
                          min(x[3] for x in segment), segment[-1][4]))
    return result


def run(source: Path, ledger: Path) -> dict:
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("native source SHA-256 mismatch")
    decoded = read_archive(source)
    if decoded.get("coin") != "ZEC" or decoded.get("venue") != "Jupiter fixed_rate@200ms oracle history":
        raise ValueError("unexpected source identity")
    rows = validated_rows(decoded["rows"])
    if len(rows) != 41680 or any(rows[i][0] != rows[0][0]+60*i for i in range(len(rows))):
        raise ValueError("source is not the frozen contiguous 41680-minute tape")
    rows = [row for row in rows if START <= row[0] < STOP]
    if len(rows) != (STOP-START)//60 or rows[0][0] != START or rows[-1][0] != STOP-60:
        raise ValueError("common whole-hour window incomplete")
    if not ledger.is_file():
        raise ValueError("holdout ledger missing")
    reservations = protected_intervals(ledger, ALIASES)
    frame = pd.DataFrame({"timestamp": [int(row[0]) for row in rows]})
    refuse_reserved(frame, "1m", reservations)
    scenarios = [("uncollateralized_zero_cost", 0., 0., None),
                 ("uncollateralized_cost_sensitivity", 10., 2., None),
                 ("one_x_margin_stress_zero_cost", 0., 0., 1.),
                 ("one_x_margin_stress_cost", 10., 2., 1.)]
    output = []
    for step in (600, 900):
        bars = aggregate(rows, step)
        for mode in ("legacy", "confirmed"):
            decisions = signals(bars, step, mode)
            for name, fee, slip, margin in scenarios:
                result = simulate_decisions(bars, step, decisions, ExecutionAssumptions(
                    initial_capital=100000, quantity=10000, fee_bps=fee,
                    slippage_bps=slip, margin_fraction=margin))
                equity = result.pop("equity_curve")
                peak, drawdown = 100000., 0.
                for value in equity:
                    peak = max(peak, value)
                    drawdown = max(drawdown, 1-value/peak)
                output.append({"seconds": step, "mode": mode, "scenario": name,
                               "bars": len(bars), "max_drawdown_fraction": drawdown, **result})
    final_reservations = protected_intervals(ledger, ALIASES)
    refuse_reserved(frame, "1m", final_reservations)
    return {"schema": "rs-zigzag-proxy/v1", "source_artifact_id": SOURCE_ID,
            "source_sha256": SOURCE_SHA256, "venue": decoded["venue"],
            "quote": "USD", "start": START, "stop_exclusive": STOP,
            "minutes": len(rows), "protected_before": reservations,
            "protected_after": final_reservations, "results": output,
            "limitations": ["Retrospective Jupiter oracle proxy; not Coinbase ZECUSDC.P.",
                            "Lookahead mode is deliberately biased; no source or fill parity established.",
                            "Uncollateralized scenarios ignore margin and can lose more than capital.",
                            "Unit multiplier 1 is assumed; actual chart instrument units unverified.",
                            "1x margin model rejects or liquidates conservatively; not venue rules.",
                            "Funding and spread are unavailable; costed scenarios are not fully net.",
                            "Previously observed sample; not an untouched holdout."]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = run(args.source, args.ledger)
    raw = (json.dumps(data, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    with args.output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"output_sha256": hashlib.sha256(raw).hexdigest(), "rows": len(data["results"])}))


if __name__ == "__main__":
    main()

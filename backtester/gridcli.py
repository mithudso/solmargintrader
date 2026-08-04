"""Ladder-grid backtest entry point.

    python -m backtester.gridcli --lower 60 --upper 90 --rungs 7 \
        --notional-per-rung 12 --synthetic 400

Separate from `backtester.cli` on purpose. That CLI runs `Strategy` objects — one
target exposure per bar — and this one runs the resting-ladder simulator, whose
config surface (lower/upper/rungs/notional) and execution model are different.
Folding the two together would imply the ladder is a drop-in comparison for an
exposure strategy on the same axis, which it is not.

Running with no arguments prints usage rather than starting a long fetch.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .core.data import CsvLoader, SyntheticLoader, checksum_frame, frame_to_arrays
from .core.gridsim import (
    SPACINGS,
    GridConfig,
    capital_requirement,
    grid_levels,
    run_grid_backtest,
    rung_width_bps,
)
from .core.types import INTERVAL_SECONDS, CostConfig


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    ap = argparse.ArgumentParser(
        prog="python -m backtester.gridcli",
        description=(
            "Backtest a resting-ladder grid — the strategy the extension trades. "
            "Historical simulation for research only, NOT investment advice."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Fetch data first:\n"
            "  python -m backtester.core.fetch --asset SOL --interval 1h "
            "--start 2024-01-01\n"
            "Then run:\n"
            "  python -m backtester.gridcli --lower 60 --upper 90 --rungs 7 "
            "--notional-per-rung 12 --interval 1h\n"
        ),
    )
    grid = ap.add_argument_group("ladder")
    grid.add_argument("--lower", type=float, required=True, help="lowest rung, USD")
    grid.add_argument("--upper", type=float, required=True, help="highest rung, USD")
    grid.add_argument("--rungs", type=int, default=7, help="number of rungs (>= 2)")
    grid.add_argument(
        "--notional-per-rung",
        type=float,
        default=12.0,
        help="USD per rung; the venue minimum is $10",
    )
    grid.add_argument(
        "--spacing", default="geom", choices=sorted(SPACINGS), help="rung spacing"
    )
    grid.add_argument(
        "--deadband-bps",
        type=float,
        default=25.0,
        help="suppress rungs this close to the market",
    )
    grid.add_argument(
        "--min-order-usd",
        type=float,
        default=10.0,
        help="venue minimum order size; rungs below it are never placed",
    )

    run = ap.add_argument_group("run")
    run.add_argument("--asset", default="SOL", help="base asset symbol")
    run.add_argument("--start", default="2021-01-01", help="inclusive UTC start date")
    run.add_argument("--end", default=None, help="inclusive UTC end date")
    run.add_argument("--capital", type=float, default=10_000.0, help="starting capital")
    run.add_argument(
        "--interval", default="1d", choices=sorted(INTERVAL_SECONDS), help="bar interval"
    )
    run.add_argument("--fee-bps", type=float, default=6.0, help="taker fee, bps")
    run.add_argument("--slippage-bps", type=float, default=2.0, help="slippage, bps")
    run.add_argument(
        "--carry-bps-per-hour",
        type=float,
        default=0.0,
        help=(
            "carry charged on held inventory. 0 is correct for spot Trigger V2; "
            "set it to model a borrowed-margin grid"
        ),
    )
    run.add_argument("--risk-free-rate", type=float, default=0.0, help="annual, decimal")
    run.add_argument("--data", default=None, help="path to a cached CSV")
    run.add_argument(
        "--synthetic",
        type=int,
        default=None,
        metavar="N",
        help="use N bars of seeded synthetic data instead of a CSV (offline demo)",
    )
    run.add_argument("--seed", type=int, default=42, help="synthetic-data seed")
    run.add_argument("--allow-gaps", action="store_true", help="accept an incomplete series")
    run.add_argument("--levels", action="store_true", help="print the ladder and exit")
    run.add_argument("--json", action="store_true", help="emit machine-readable output")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    """Run the grid CLI. Returns a process exit code."""
    ap = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        ap.print_help()
        return 0
    args = ap.parse_args(raw)

    try:
        cfg = GridConfig(
            lower=args.lower,
            upper=args.upper,
            rungs=args.rungs,
            notional_per_rung_usd=args.notional_per_rung,
            spacing=args.spacing,
            deadband_bps=args.deadband_bps,
            min_order_usd=args.min_order_usd,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    levels = grid_levels(cfg)
    if args.levels:
        # Quoting the requirement at the top rung is the useful case: that is the
        # price at which every rung is a bid and the ladder needs full funding.
        need = capital_requirement(cfg, levels[-1])
        payload = {
            "levels": levels,
            "rung_width_bps": rung_width_bps(cfg),
            "capital_requirement_at_upper": need,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            for i, level in enumerate(levels):
                print(f"  rung {i}  ${level:,.4f}")
            print(f"\nrung width       {payload['rung_width_bps']:,.1f} bps")
            print(f"capital required ${need['total_usd']:,.2f} at ${levels[-1]:,.2f}")
        return 0

    if args.synthetic:
        loader = SyntheticLoader(n_bars=args.synthetic, seed=args.seed)
    else:
        path = (
            Path(args.data)
            if args.data
            else Path("data") / f"{args.asset.upper()}_{args.interval}.csv"
        )
        loader = CsvLoader(path, allow_gaps=args.allow_gaps)

    try:
        df = loader.load(args.asset, args.start, args.end, args.interval)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error loading data: {exc}", file=sys.stderr)
        return 1

    try:
        result = run_grid_backtest(
            cfg,
            frame_to_arrays(df),
            initial_capital=args.capital,
            interval=args.interval,
            costs=CostConfig(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps),
            carry_bps_per_hour=args.carry_bps_per_hour,
            risk_free_rate=args.risk_free_rate,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "config": result.config,
                    "data_source": loader.describe(),
                    "data_checksum": checksum_frame(df),
                    "bar_count": int(len(df)),
                    "interval": args.interval,
                    "initial_capital": args.capital,
                    "carry_bps_per_hour": result.carry_bps_per_hour,
                    "rung_width_bps": result.rung_width_bps,
                    "capital_required_usd": result.capital_required_usd,
                    "round_trips": result.round_trips,
                    "gross_captured_usd": result.gross_captured_usd,
                    "realized_pnl_usd": result.realized_pnl_usd,
                    "fees_paid_usd": result.fees_paid_usd,
                    "slippage_paid_usd": result.slippage_paid_usd,
                    "carry_paid_usd": result.carry_paid_usd,
                    "buys_filled": result.buys_filled,
                    "sells_filled": result.sells_filled,
                    "orders_placed": result.orders_placed,
                    "orders_cancelled": result.orders_cancelled,
                    "unmatched_inventory_qty": result.unmatched_inventory_qty,
                    "forced_exit_qty": result.forced_exit_qty,
                    "bars_above_grid": result.bars_above_grid,
                    "bars_below_grid": result.bars_below_grid,
                    "skipped": result.skipped,
                    "grid_metrics": result.metrics.to_dict(),
                    "buy_and_hold_metrics": result.baseline_metrics.to_dict(),
                },
                indent=2,
                default=float,
            )
        )
        return 0

    print(
        f"\nladder ${cfg.lower:,.2f}-${cfg.upper:,.2f}, {cfg.rungs} rungs, "
        f"${cfg.notional_per_rung_usd:,.2f}/rung, {cfg.spacing} spacing"
    )
    print(f"data   {loader.describe()}  ({len(df)} bars @ {args.interval})\n")
    for line in result.summary_lines():
        print(f"  {line}")
    if result.skipped:
        print("\n  skipped (plan-time refusals, by reason):")
        for reason, count in sorted(result.skipped.items(), key=lambda kv: -kv[1]):
            print(f"    {count:6d}  {reason}")
    print(
        "\nA grid is short volatility: it earns its rung width in a range and "
        "accumulates losing inventory in a trend.\nNOT investment advice."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

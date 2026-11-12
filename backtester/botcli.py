"""Bot backtest entry point: the DCA safety-order bot and the triangular-arbitrage replay.

    python -m backtester.botcli dca --synthetic 500
    python -m backtester.botcli dca --asset SOL --interval 1h --start 2025-01-01 --take-profit-pct 2
    python -m backtester.botcli triangle --snapshots ~/.config/soltui/prices/2026-11-08.jsonl.gz

Separate from `backtester.cli` and `backtester.gridcli` on purpose: each bot owns an order
lifecycle that neither a target-exposure strategy nor the resting ladder expresses. The grid
bot runs through `backtester.gridcli`.

Like every backtester entry point this touches no network. The DCA bot reads a cached OHLCV
CSV; the triangle replay reads snapshot files recorded by `soltui/pricefeed.py`.
Running with no arguments prints usage.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Sequence

from .core.data import CsvLoader, SyntheticLoader, frame_to_arrays, resolve_data_dir
from .core.dcasim import DcaConfig, plan_deal, run_dca_backtest
from .core.trianglesim import (
    TriangleConfig,
    read_snapshot_files,
    run_triangle_backtest,
    triangles_from_products,
)
from .core.types import INTERVAL_SECONDS, CostConfig
from .gridcli import _json_safe

DISCLAIMER = (
    "A DCA bot buys more of a falling asset and needs a recovery to exit; a triangle cycle "
    "needs a dislocation that survives execution delay. Historical simulation only, "
    "NOT investment advice."
)


def _boolean(value):
    if value.lower() in ("1", "true", "yes"):
        return True
    if value.lower() in ("0", "false", "no"):
        return False
    raise argparse.ArgumentTypeError("expected true/false, yes/no, or 1/0")


def _add_dataclass_args(group: argparse._ArgumentGroup, cls: type) -> None:
    for f in dataclasses.fields(cls):
        flag = "--" + f.name.replace("_", "-")
        if f.type in ("bool", bool):
            group.add_argument(flag, type=_boolean, default=f.default)
        else:
            kind = int if f.type in ("int", int) else float
            group.add_argument(flag, type=kind, default=f.default)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m backtester.botcli",
                                 description="Backtest a DCA bot or replay triangular arbitrage. "
                                             "Historical simulation only, NOT investment advice.")
    sub = ap.add_subparsers(dest="bot")
    dca = sub.add_parser("dca", formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                         help="DCA safety-order bot over cached OHLCV")
    _add_dataclass_args(dca.add_argument_group("bot"), DcaConfig)
    run = dca.add_argument_group("run")
    run.add_argument("--asset", default="SOL")
    run.add_argument("--interval", default="1h", choices=sorted(INTERVAL_SECONDS))
    run.add_argument("--start", default=None, help="inclusive UTC start date: the bot starts here")
    run.add_argument("--end", default=None)
    run.add_argument("--capital", type=float, default=None, help="default: what one deal needs")
    run.add_argument("--fee-bps", type=float, default=6.0)
    run.add_argument("--slippage-bps", type=float, default=2.0)
    run.add_argument("--data", default=None, help="path to a cached CSV")
    run.add_argument("--synthetic", type=int, default=None, metavar="N")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--allow-gaps", action="store_true",
                     help="load a file with gaps; the simulated slice itself must still be complete")
    run.add_argument("--json", action="store_true")

    tri = sub.add_parser("triangle", formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                         help="triangular-arbitrage replay over recorded bid/ask snapshots")
    _add_dataclass_args(tri.add_argument_group("bot"), TriangleConfig)
    trun = tri.add_argument_group("run")
    trun.add_argument("--snapshots", nargs="+", required=True, help="recorded .jsonl.gz files")
    trun.add_argument("--json", action="store_true")
    return ap


def _dca(args: argparse.Namespace) -> int:
    try:
        cfg = DcaConfig(**{f.name: getattr(args, f.name) for f in dataclasses.fields(DcaConfig)})
        costs = CostConfig(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.synthetic is not None:
        df = SyntheticLoader(n_bars=args.synthetic, seed=args.seed).load(args.asset, None, None, args.interval)
    else:
        path = args.data or str(resolve_data_dir() / f"{args.asset.upper()}_{args.interval}.csv")
        try:
            df = CsvLoader(path, allow_gaps=args.allow_gaps).load(args.asset, args.start, args.end,
                                                                    args.interval)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}\nfetch first: python -m backtester.core.fetch --asset {args.asset} "
                  f"--interval {args.interval}", file=sys.stderr)
            return 1
    try:
        result = run_dca_backtest(cfg, frame_to_arrays(df), initial_capital=args.capital,
                                  interval=args.interval, costs=costs)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(_json_safe({**result.summary(), "disclaimer": DISCLAIMER}), indent=2, allow_nan=False))
    else:
        plan = result.first_plan or plan_deal(cfg, float(df["close"].iloc[0]))
        print(f"DCA bot on {args.asset} {args.interval}: first deal set at ${plan['base_price']:,.4f}")
        for row in plan["orders"]:
            print(f"  {row['order']:<10} ${row['price']:>12,.4f}  ${row['usd']:>9,.2f}  "
                  f"avg ${row['avg_entry']:,.4f}  take-profit ${row['take_profit']:,.4f}")
        print("\n".join(result.summary_lines()))
        print(DISCLAIMER)
    return 0


def _triangle(args: argparse.Namespace) -> int:
    try:
        cfg = TriangleConfig(**{f.name: getattr(args, f.name) for f in dataclasses.fields(TriangleConfig)})
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if any(not Path(path).is_file() for path in args.snapshots):
        print("error: every snapshot input must be an existing file", file=sys.stderr)
        return 1
    snaps = read_snapshot_files(args.snapshots)
    if not snaps:
        print("error: no usable snapshots", file=sys.stderr)
        return 1
    products = {p for _, quotes in snaps for p in quotes}
    tris = triangles_from_products(products)
    result = run_triangle_backtest(cfg, snaps, tris)
    payload = {**result.summary(), "triangles": [t.name for t in tris], "disclaimer": DISCLAIMER}
    if args.json:
        print(json.dumps(_json_safe(payload), indent=2, allow_nan=False))
    else:
        print(f"{result.snapshots} snapshots, {len(tris)} triangles, {result.executed} cycles executed, "
              f"{result.wins} profitable, P&L ${result.pnl_usd:,.4f}")
        for name, row in result.per_triangle.items():
            best = row["best_edge_bps"]
            print(f"  {name:<16} observed {row['observed']:>7}  best net edge "
                  f"{'-' if best is None else f'{best:,.1f} bps':>12}  executed {row['executed']}")
        print(DISCLAIMER)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    ap = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        ap.print_help()
        return 0
    args = ap.parse_args(raw)
    if args.bot == "dca":
        return _dca(args)
    if args.bot == "triangle":
        return _triangle(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Command-line entry point.

    python -m backtester.cli --asset SOL --strategy all --out results/

Running with no arguments prints usage rather than starting a long fetch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

from .core import plotting, report
from .core.data import CsvLoader, SyntheticLoader, checksum_frame, frame_to_arrays
from .core.engine import BacktestResult, EngineConfig, Strategy, run_backtest
from .core.metrics import compute_metrics
from .core.report import SplitResult
from .core.strategies import DEFAULT_SET, REGISTRY, build
from .core.types import CostConfig, INTERVAL_SECONDS, Mode, RunManifest, periods_per_year


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    ap = argparse.ArgumentParser(
        prog="python -m backtester.cli",
        description=(
            "Backtest crypto trading strategies (SOL-focused). "
            "Historical simulation for research only -- NOT investment advice."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Fetch data first:\n"
            "  python -m backtester.core.fetch --asset SOL --interval 1d "
            "--start 2021-01-01\n"
            "Then run:\n"
            "  python -m backtester.cli --strategy all --out results/\n"
        ),
    )
    ap.add_argument("--asset", default="SOL", help="base asset symbol")
    ap.add_argument("--start", default="2021-01-01", help="inclusive UTC start date")
    ap.add_argument("--end", default=None, help="inclusive UTC end date (default: all)")
    ap.add_argument("--capital", type=float, default=10_000.0, help="starting capital")
    ap.add_argument(
        "--strategy",
        action="append",
        default=None,
        help=f"repeatable; one of {sorted(REGISTRY)} or 'all'",
    )
    ap.add_argument(
        "--interval", default="1d", choices=sorted(INTERVAL_SECONDS), help="bar interval"
    )
    ap.add_argument(
        "--mode", default="spot", choices=[m.value for m in Mode], help="execution mode"
    )
    ap.add_argument("--leverage", type=float, default=1.0, help="perp leverage")
    ap.add_argument("--fee-bps", type=float, default=6.0, help="taker fee, bps")
    ap.add_argument("--slippage-bps", type=float, default=2.0, help="slippage, bps")
    ap.add_argument(
        "--fill-delay",
        type=int,
        default=1,
        help="0 = fill at this bar's close; N = fill at open of bar t+N",
    )
    ap.add_argument(
        "--rebalance-threshold",
        type=float,
        default=0.0,
        help="minimum exposure gap (fraction of equity) before rebalancing",
    )
    ap.add_argument(
        "--split",
        type=float,
        default=None,
        help="walk-forward in-sample fraction, e.g. 0.7",
    )
    ap.add_argument("--risk-free-rate", type=float, default=0.0, help="annual, decimal")
    ap.add_argument("--allow-short", action="store_true", help="permit short exposure (perp only)")
    ap.add_argument("--seed", type=int, default=0, help="seed recorded in the manifest")
    ap.add_argument("--data", default=None, help="path to a cached CSV")
    ap.add_argument(
        "--synthetic",
        type=int,
        default=None,
        metavar="N",
        help="use N bars of seeded synthetic data instead of a CSV (offline demo)",
    )
    ap.add_argument("--allow-gaps", action="store_true", help="accept an incomplete series")
    ap.add_argument("--no-charts", action="store_true", help="skip PNG output")
    ap.add_argument("--out", default=None, help="output directory")

    perp = ap.add_argument_group("perpetual borrow-fee model (Jupiter-style)")
    perp.add_argument(
        "--borrow-bps-long",
        type=float,
        default=1.6,
        help="max hourly borrow rate for longs, bps (1.6 == 0.016%%/hr)",
    )
    perp.add_argument(
        "--borrow-bps-short",
        type=float,
        default=0.3,
        help="max hourly borrow rate for shorts, bps",
    )
    perp.add_argument(
        "--utilization", type=float, default=0.5, help="pool utilization in [0,1]"
    )
    perp.add_argument(
        "--min-borrow-bps",
        type=float,
        default=0.0,
        help="hourly rate floor, bps (models the proposed dual-slope minimum)",
    )
    perp.add_argument(
        "--kink-utilization",
        type=float,
        default=None,
        help="enable the proposed dual-slope curve at this utilization",
    )
    return ap


def _trimmed_metrics(
    res: BacktestResult, skip: int, periods: float, risk_free: float
):
    """Recompute metrics over `equity[skip:]`, excluding warmup bars.

    Used for the out-of-sample leg, whose slice deliberately begins inside the
    in-sample region so indicators arrive warm. Those leading bars are flat and
    would otherwise dilute the out-of-sample Sharpe.
    """
    if skip <= 0 or skip >= len(res.equity):
        return res.metrics
    trades = [t for t in res.trades if t.bar_index >= skip]
    return compute_metrics(
        res.equity[skip:],
        res.timestamps[skip:],
        trades,
        res.exposure[skip:],
        periods,
        risk_free,
        res.liquidation_count,
    )


def _run_one(
    strategy_name: str,
    arrays: dict[str, np.ndarray],
    cfg: EngineConfig,
    split: float | None,
) -> SplitResult:
    """Run one strategy over the full range and, if asked, each split segment."""
    full = run_backtest(build(strategy_name), arrays, cfg)
    result = SplitResult(name=strategy_name, full=full)
    if split is None:
        return result

    n = len(arrays["close"])
    k = int(n * split)
    warmup = build(strategy_name).warmup_bars()
    if k <= warmup + 2 or n - k <= warmup + 2:
        print(
            f"  [{strategy_name}] split skipped: segments too short for a "
            f"{warmup}-bar warmup",
            file=sys.stderr,
        )
        return result

    is_arrays = {key: v[:k] for key, v in arrays.items()}
    result.in_sample = run_backtest(build(strategy_name), is_arrays, cfg)

    # Start the out-of-sample slice `warmup` bars early so the strategy's own
    # warmup consumes trailing in-sample bars and trading begins exactly at k.
    oos_start = max(0, k - warmup)
    oos_arrays = {key: v[oos_start:] for key, v in arrays.items()}
    oos = run_backtest(build(strategy_name), oos_arrays, cfg)
    oos.metrics = _trimmed_metrics(
        oos, k - oos_start, periods_per_year(cfg.interval), cfg.risk_free_rate
    )
    result.out_of_sample = oos
    return result


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Returns a process exit code."""
    ap = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        ap.print_help()
        return 0
    args = ap.parse_args(raw)

    mode = Mode(args.mode)
    if mode is Mode.SPOT and args.leverage != 1.0:
        print(
            "error: spot mode does not borrow; pass --mode perp for leverage > 1",
            file=sys.stderr,
        )
        return 2
    if not 0.0 <= args.utilization <= 1.0:
        print("error: --utilization must be in [0, 1]", file=sys.stderr)
        return 2
    if args.split is not None and not 0.1 <= args.split <= 0.9:
        print("error: --split must be between 0.1 and 0.9", file=sys.stderr)
        return 2

    # -- data ------------------------------------------------------------
    if args.synthetic:
        loader = SyntheticLoader(n_bars=args.synthetic, seed=args.seed or 42)
    else:
        path = Path(args.data) if args.data else Path("data") / f"{args.asset.upper()}_{args.interval}.csv"
        loader = CsvLoader(path, allow_gaps=args.allow_gaps)

    try:
        df = loader.load(args.asset, args.start, args.end, args.interval)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"error loading data: {exc}", file=sys.stderr)
        return 1

    arrays = frame_to_arrays(df)

    costs = CostConfig(
        fee_bps=args.fee_bps,
        slippage_bps=args.slippage_bps,
        perp_base_fee_bps=6.0,
        max_hourly_rate_bps_long=args.borrow_bps_long,
        max_hourly_rate_bps_short=args.borrow_bps_short,
        utilization=args.utilization,
        min_hourly_rate_bps=args.min_borrow_bps,
        kink_utilization=args.kink_utilization,
    )
    try:
        cfg = EngineConfig(
            mode=mode,
            leverage=args.leverage,
            initial_capital=args.capital,
            interval=args.interval,
            fill_delay=args.fill_delay,
            rebalance_threshold=args.rebalance_threshold,
            risk_free_rate=args.risk_free_rate,
            costs=costs,
            allow_short=args.allow_short,
            seed=args.seed,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    names = args.strategy or ["all"]
    if "all" in names:
        names = list(DEFAULT_SET)
    unknown = [n for n in names if n not in REGISTRY]
    if unknown:
        print(
            f"error: unknown strategy {unknown}; available: {sorted(REGISTRY)}",
            file=sys.stderr,
        )
        return 2
    # Buy-and-hold is the mandatory baseline; add it if the user left it out.
    if "buy_and_hold" not in names:
        names = ["buy_and_hold"] + names

    splits: list[SplitResult] = []
    for name in names:
        try:
            splits.append(_run_one(name, arrays, cfg, args.split))
        except ValueError as exc:
            print(f"error running {name}: {exc}", file=sys.stderr)
            return 1

    first_ts, last_ts = int(df["timestamp"].iloc[0]), int(df["timestamp"].iloc[-1])
    import pandas as pd

    manifest = RunManifest(
        asset=args.asset.upper(),
        start=str(pd.Timestamp(first_ts, unit="s", tz="UTC").date()),
        end=str(pd.Timestamp(last_ts, unit="s", tz="UTC").date()),
        interval=args.interval,
        mode=str(mode),
        leverage=args.leverage,
        initial_capital=args.capital,
        fill_delay=args.fill_delay,
        seed=args.seed,
        rebalance_threshold=args.rebalance_threshold,
        costs=vars(costs).copy(),
        strategies={s.name: s.full.params for s in splits},
        data_source=loader.describe(),
        data_checksum=checksum_frame(df),
        bar_count=len(df),
        split=args.split,
        library_versions=report.library_versions(),
        periods_per_year=periods_per_year(args.interval),
    )

    text = report.render_report(splits, manifest, configurations_evaluated=len(splits))
    print(text)

    if args.out:
        written = report.write_outputs(args.out, splits, manifest, text)
        if not args.no_charts:
            if plotting.charts_available():
                written += plotting.plot_comparison(
                    [s.full for s in splits], args.out, manifest.asset
                )
            else:
                print(
                    "note: matplotlib unavailable; charts skipped", file=sys.stderr
                )
        print("\nWrote:", file=sys.stderr)
        for p in written:
            print(f"  {p}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

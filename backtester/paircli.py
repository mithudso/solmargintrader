"""Peer-relative-value backtest entry point.

    python -m backtester.paircli --asset SOL --peer BTC --interval 1d --split 0.7

Separate from `backtester.cli` because this strategy needs **two** price series,
and the strategy registry builds from zero arguments. A registered
`PeerSpreadReversion` would have to default its peer to `None` and then silently
do nothing, which is a worse failure than a separate entry point.

Running with no arguments prints usage rather than starting a long fetch.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

from .core.cointegration import engle_granger
from .core.data import CsvLoader, frame_to_arrays
from .core.engine import EngineConfig, run_backtest
from .core.metrics import compute_metrics
from .core.pairs import PeerSpreadReversion, align_peer
from .core.types import INTERVAL_SECONDS, CostConfig, periods_per_year

DISCLAIMER = (
    "A pairs trade assumes a relation that can break. Convergence failure is how "
    "this strategy loses badly rather than slightly. Historical simulation only, "
    "NOT investment advice."
)


def _json_safe(value: Any) -> Any:
    """Replace non-finite floats with None so the output is strict JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    ap = argparse.ArgumentParser(
        prog="python -m backtester.paircli",
        description=(
            "Backtest peer-relative-value reversion on a cointegrated spread. "
            "Historical simulation for research only, NOT investment advice."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog=(
            "Fetch both legs first:\n"
            "  python -m backtester.core.fetch --asset SOL --interval 1d "
            "--start 2021-06-17\n"
            "  python -m backtester.core.fetch --asset BTC --interval 1d "
            "--start 2021-06-17\n"
        ),
    )
    ap.add_argument("--asset", default="SOL", help="traded asset")
    ap.add_argument("--peer", default="BTC", help="peer asset for the spread")
    ap.add_argument("--interval", default="1d", choices=sorted(INTERVAL_SECONDS))
    ap.add_argument("--start", default="2021-01-01", help="inclusive UTC start date")
    ap.add_argument("--end", default=None, help="inclusive UTC end date")
    ap.add_argument("--capital", type=float, default=10_000.0)
    ap.add_argument("--fit-window", type=int, default=250, help="bars per spread fit")
    ap.add_argument("--entry-z", type=float, default=-2.0)
    ap.add_argument("--exit-z", type=float, default=0.0)
    ap.add_argument("--stop-z", type=float, default=-3.0)
    ap.add_argument("--adf-max-p", type=float, default=0.05)
    ap.add_argument(
        "--no-cointegration-gate",
        action="store_true",
        help="trade the spread even when the ADF test rejects nothing (for contrast)",
    )
    ap.add_argument("--fee-bps", type=float, default=6.0)
    ap.add_argument("--slippage-bps", type=float, default=2.0)
    ap.add_argument("--split", type=float, default=None, help="walk-forward fraction")
    ap.add_argument("--data-dir", default="data", help="directory holding the CSVs")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    """Run the pair CLI. Returns a process exit code."""
    ap = build_parser()
    raw = list(sys.argv[1:] if argv is None else argv)
    if not raw:
        ap.print_help()
        return 0
    args = ap.parse_args(raw)

    if args.split is not None and not 0.1 <= args.split <= 0.9:
        print("error: --split must be between 0.1 and 0.9", file=sys.stderr)
        return 2
    if args.asset.upper() == args.peer.upper():
        print("error: --asset and --peer must differ", file=sys.stderr)
        return 2

    directory = Path(args.data_dir)
    paths = {
        name: directory / f"{name.upper()}_{args.interval}.csv"
        for name in (args.asset, args.peer)
    }
    frames = {}
    for name, path in paths.items():
        try:
            frames[name] = CsvLoader(path).load(name, args.start, args.end, args.interval)
        except FileNotFoundError:
            print(
                f"error: {path} not found. Fetch it first:\n"
                f"  python -m backtester.core.fetch --asset {name.upper()} "
                f"--interval {args.interval} --start {args.start}",
                file=sys.stderr,
            )
            return 1
        except Exception as exc:
            print(f"error loading {path}: {exc}", file=sys.stderr)
            return 1

    base = frame_to_arrays(frames[args.asset])
    peer = frame_to_arrays(frames[args.peer])
    try:
        peer_closes = align_peer(base["ts"], peer["ts"], peer["close"])
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    costs = CostConfig(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    cfg = EngineConfig(
        initial_capital=args.capital, interval=args.interval, costs=costs
    )

    def make() -> PeerSpreadReversion:
        return PeerSpreadReversion(
            peer_closes=peer_closes,
            peer_name=args.peer.upper(),
            fit_window=args.fit_window,
            entry_z=args.entry_z,
            exit_z=args.exit_z,
            stop_z=args.stop_z,
            adf_max_p=args.adf_max_p,
            require_cointegration=not args.no_cointegration_gate,
        )

    try:
        strategy = make()
        full = run_backtest(strategy, base, cfg)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    # Full-sample cointegration, reported for context rather than used to trade —
    # the strategy re-fits per bar on trailing data only.
    whole = engle_granger(base["close"], peer_closes)

    payload: dict[str, Any] = {
        "asset": args.asset.upper(),
        "peer": args.peer.upper(),
        "interval": args.interval,
        "bars": int(base["close"].size),
        "params": strategy.params,
        "full_sample_beta": whole.beta,
        "full_sample_adf_stat": whole.adf.statistic,
        "full_sample_adf_p": whole.adf.pvalue,
        "full_sample_cointegrated_5pct": whole.cointegrated_at_5pct,
        "bars_cointegrated": strategy.bars_cointegrated,
        "bars_screened_out": strategy.bars_screened_out,
        "full_metrics": full.metrics.to_dict(),
        "disclaimer": DISCLAIMER,
    }

    if args.split is not None:
        n = base["close"].size
        k = int(n * args.split)
        warm = make().warmup_bars()
        is_arrays = {key: v[:k] for key, v in base.items()}
        oos_start = max(0, k - warm)
        oos_arrays = {key: v[oos_start:] for key, v in base.items()}

        is_strategy = PeerSpreadReversion(
            peer_closes=peer_closes[:k], peer_name=args.peer.upper(),
            fit_window=args.fit_window, entry_z=args.entry_z, exit_z=args.exit_z,
            stop_z=args.stop_z, adf_max_p=args.adf_max_p,
            require_cointegration=not args.no_cointegration_gate,
        )
        oos_strategy = PeerSpreadReversion(
            peer_closes=peer_closes[oos_start:], peer_name=args.peer.upper(),
            fit_window=args.fit_window, entry_z=args.entry_z, exit_z=args.exit_z,
            stop_z=args.stop_z, adf_max_p=args.adf_max_p,
            require_cointegration=not args.no_cointegration_gate,
        )
        in_sample = run_backtest(is_strategy, is_arrays, cfg)
        oos = run_backtest(oos_strategy, oos_arrays, cfg)
        skip = k - oos_start
        trades = [t for t in oos.trades if t.bar_index >= skip]
        oos_metrics = compute_metrics(
            oos.equity[skip:], oos.timestamps[skip:], trades, oos.exposure[skip:],
            periods_per_year(args.interval), 0.0, 0,
        )
        payload["in_sample_metrics"] = in_sample.metrics.to_dict()
        payload["out_of_sample_metrics"] = oos_metrics.to_dict()

    if args.json:
        print(json.dumps(_json_safe(payload), indent=2, default=float, allow_nan=False))
        return 0

    print(f"\n{payload['asset']} vs {payload['peer']}  ({payload['bars']} bars @ {args.interval})")
    print(f"  full-sample beta        {whole.beta:,.4f}")
    print(
        f"  full-sample ADF         stat {whole.adf.statistic:,.3f}, "
        f"p~{whole.adf.pvalue:.3f}, cointegrated at 5%: {whole.cointegrated_at_5pct}"
    )
    print(
        f"  rolling gate            {strategy.bars_cointegrated} bars cointegrated, "
        f"{strategy.bars_screened_out} screened out"
    )
    m = payload["full_metrics"]
    print(f"  full-sample return      {m['total_return'] * 100:,.2f}%  Sharpe {m['sharpe']:,.3f}")
    if "out_of_sample_metrics" in payload:
        i_m, o_m = payload["in_sample_metrics"], payload["out_of_sample_metrics"]
        print(f"  in-sample               {i_m['total_return'] * 100:,.2f}%  Sharpe {i_m['sharpe']:,.3f}")
        print(
            f"  OUT-OF-SAMPLE           {o_m['total_return'] * 100:,.2f}%  "
            f"Sharpe {o_m['sharpe']:,.3f}  ({o_m['trade_count']} trades)"
        )
    print(f"\n{DISCLAIMER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

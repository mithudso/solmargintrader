"""Preliminary backtest of every registered strategy against every 1-minute series.

    python3 research/minute_sweep.py                      # default 500k-bar window
    python3 research/minute_sweep.py --all-bars           # full history, hours
    python3 research/minute_sweep.py --common-window      # one calendar for all assets
    python3 research/minute_sweep.py --param-scale 60     # wall-clock-preserving params

## This is preliminary, and the word is load-bearing

One pass per (asset, strategy) cell. **No CPCV, no PBO, no walk-forward.** This
repository's central finding is that a single pass is not evidence -- `RANKED_LISTS.md`
finding 1c measures in-sample rank as *anti-informative* at the daily horizons, and
finding 1f shows even the CPCV ordering is largely an artifact of the block count. So
nothing here establishes that a strategy works. What a single pass can do is tell you
which cells are worth the expense of a real protocol, and rule out the ones that are not.

The output header repeats this where a reader will actually see it.

## The parameter question, stated rather than buried

Strategy parameters are counts of BARS. `ma_crossover(fast=12, slow=48)` was tuned on
hourly bars, where it means 12 hours against 48 hours. Applied to minute bars the same
numbers mean 12 minutes against 48 minutes -- a different strategy, not the same one at
finer resolution. Two readings are defensible and they are different experiments:

  * **`--param-scale 1` (default): preserve the bar counts.** Tests fast intraday
    strategies. This is what the numbers literally say, and it is cheap to compute.
  * **`--param-scale 60`: preserve the wall-clock window.** A 48-bar slow average
    becomes 2,880 bars, so the strategy spans the same 48 hours it did on hourly data.
    Only keys in `BAR_KEYS` are scaled -- multiplying `num_std` or `target_vol` would
    change the strategy rather than its timescale. Be warned that this is expensive:
    measured on 20k bars, `macd` went from 0.1s to 29.6s, because the indicator cost is
    proportional to the window.

## What the costs do here, measured before this script was written

At one minute, fees and slippage are the dominant term and it is not close. On 100k bars
of BTC with `--param-scale 1`, 22 of 25 strategies lost between 79% and 100% of capital,
and total fees plus slippage ran $7,800-$9,900 against $10,000 of initial capital: the
account is consumed by round trips, not by direction. `macd` alone took 15,382 trades;
`ma_ribbon` 60,801. The one non-negative cell, `vwap_reversion` at +0.30%, took 8 trades.

That is why every row reports gross and net side by side and a cost share. If a reader
sees only a net Sharpe they will look for a signal problem, when the honest reading is
usually that there is no signal problem to find -- the strategy simply cannot pay the
spread at this frequency.

## Unequal histories are reported, never quietly averaged

Coinbase serves five years of minutes for BTC, ETH, SOL, DOGE and ZEC; 1,118 days for
XRP (its relisting, not the asset's start); 286 for BNB; 180 for HYPE. By default each
asset is backtested over its own most recent `--bars`, so **the cells are not on a common
calendar and a cross-asset comparison is not like-for-like.** `--common-window`
intersects the calendars instead, which is comparable but throws away everything before
the shortest asset's start. Both are legitimate; only one is right for a given question,
so the report always prints the window each asset actually used.
"""

from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import frame_to_arrays  # noqa: E402
from backtester.core.engine import EngineConfig, run_backtest  # noqa: E402
from backtester.core.fetch_minutes import (  # noqa: E402
    MINUTE_ASSETS,
    load_minutes,
    minute_path,
)
from backtester.core.strategies import build  # noqa: E402
from backtester.core.types import CostConfig  # noqa: E402
from research.sweep import HORIZONS  # noqa: E402

OUT = REPO / "research" / "results"

# Parameters measured in BARS, and therefore the only ones --param-scale may touch.
# Everything else is a threshold (`num_std`, `oversold`), a fraction (`target_vol`,
# `step`), or a count of series (`levels`, `windows`); scaling those would change the
# strategy rather than its timescale, which is the one thing the flag must not do.
BAR_KEYS = frozenset({
    "fast", "slow", "signal", "window", "entry_lookback", "exit_lookback", "ema_span",
    "atr_period", "period", "k_period", "d_period", "anchor_window", "ma_window",
    "trend_window", "vol_window", "formation", "skip", "adx_period", "base", "tenkan",
    "kijun", "senkou_b", "displacement", "fit_window", "max_half_life_bars", "lookback",
    "lag",
})

# Base grid: the hourly-tuned bar counts, taken from the sweep rather than restated so
# the two cannot drift apart.
BASE_PARAMS: dict[str, dict] = dict(HORIZONS["short"]["params"])

# Coinbase taker fee plus a slippage allowance, matching research/sweep.py so a 1m
# number and a 1h number are comparable on costs.
FEE_BPS = 6.0
SLIPPAGE_BPS = 2.0

DEFAULT_BARS = 500_000          # ~347 days of minutes
MINUTE = 60

# Sliced arrays are prepared once in the parent and cached to .npz, then loaded by the
# workers. The first version had each worker call load_minutes(), which re-parsed the
# same ~150MB CSV and copied it twice (drop_duplicates, then sort_values) -- roughly
# 400MB transient per worker. With 10 workers that killed the pool outright:
# `BrokenProcessPool: A process in the process pool was terminated abruptly`. Caching the
# slice bounds memory to the slice itself (500k rows x 6 float64 is ~24MB) and removes
# 200 redundant parses of the same file.
SLICES = Path(__file__).resolve().parent / "results" / ".slices"

_ARRAYS: dict[str, tuple[dict[str, np.ndarray], int, int]] = {}


@dataclass
class Cell:
    """One (asset, strategy) result."""

    asset: str
    strategy: str
    params: str
    bars: int
    first: str
    last: str
    trades: int
    net_return_pct: float
    gross_return_pct: float
    net_sharpe: float
    gross_sharpe: float
    max_drawdown_pct: float
    fees_usd: float
    borrow_fees_usd: float
    cost_share_of_capital: float
    exposure_fraction: float
    liquidations: int
    seconds: float
    error: str = ""


def scaled_params(strategy: str, scale: int) -> dict:
    """Base parameters with only the bar-count keys multiplied."""
    return {
        k: (max(1, int(round(v * scale))) if k in BAR_KEYS else v)
        for k, v in BASE_PARAMS[strategy].items()
    }


def available_assets() -> list[str]:
    """Assets with a 1m cache on disk, in universe order."""
    return [a for a in MINUTE_ASSETS if minute_path(a).exists()]


def asset_span(asset: str) -> tuple[int, int]:
    """First and last cached timestamp for an asset."""
    ts = load_minutes(asset)["timestamp"].to_numpy(dtype="int64")
    return int(ts.min()), int(ts.max())


def common_window(assets: list[str]) -> tuple[int, int]:
    """The calendar every asset covers -- the intersection, not the union."""
    spans = [asset_span(a) for a in assets]
    return max(s for s, _ in spans), min(e for _, e in spans)


def slice_key(asset: str, bars: int | None, window: tuple[int, int] | None) -> str:
    """Stable filename for one (asset, window) slice."""
    lo, hi = window if window else (0, 0)
    return f"{asset}_{bars or 'all'}_{lo}_{hi}"


def build_slice(asset: str, bars: int | None, window: tuple[int, int] | None) -> Path:
    """Parse the CSV once in the parent and write the sliced arrays to .npz."""
    SLICES.mkdir(parents=True, exist_ok=True)
    path = SLICES / f"{slice_key(asset, bars, window)}.npz"
    if path.exists():
        return path
    df = load_minutes(asset)
    if window is not None:
        lo, hi = window
        df = df[(df["timestamp"] >= lo) & (df["timestamp"] <= hi)]
    if bars is not None and len(df) > bars:
        df = df.tail(bars)
    df = df.reset_index(drop=True)
    np.savez(path, **{c: df[c].to_numpy() for c in df.columns})
    del df
    return path


def _arrays_for(asset: str, bars: int | None, window: tuple[int, int] | None):
    """The cached slice, loaded once per worker process.

    Loads the compact .npz the parent prepared rather than the CSV -- see SLICES above
    for why that distinction killed the first run.
    """
    key = slice_key(asset, bars, window)
    if key not in _ARRAYS:
        with np.load(SLICES / f"{key}.npz") as data:
            frame = pd.DataFrame({c: data[c] for c in data.files})
        ts = frame["timestamp"].to_numpy(dtype="int64")
        _ARRAYS.clear()          # one asset-slice per worker; keep memory flat
        _ARRAYS[key] = (frame_to_arrays(frame), int(ts.min()), int(ts.max()))
    return _ARRAYS[key]


def run_cell(job: tuple[str, str, int, int | None, tuple[int, int] | None]) -> dict:
    """Backtest one (asset, strategy) pair. Returns a Cell as a dict."""
    asset, strategy, scale, bars, window = job
    params = scaled_params(strategy, scale)
    started = time.time()
    try:
        arrays, first, last = _arrays_for(asset, bars, window)
        cfg = EngineConfig(
            interval="1m",
            fill_delay=1,
            initial_capital=10_000.0,
            costs=CostConfig(fee_bps=FEE_BPS, slippage_bps=SLIPPAGE_BPS),
        )
        result = run_backtest(build(strategy, **params), arrays, cfg)
        net, gross = result.metrics, result.gross_metrics
        costs = net.total_fees + net.total_borrow_fees
        return asdict(Cell(
            asset=asset, strategy=strategy,
            params=";".join(f"{k}={v}" for k, v in sorted(params.items())) or "-",
            bars=int(net.bars),
            first=str(pd.Timestamp(first, unit="s", tz="UTC")),
            last=str(pd.Timestamp(last, unit="s", tz="UTC")),
            trades=int(net.trade_count),
            net_return_pct=round(net.total_return * 100, 4),
            gross_return_pct=round(gross.total_return * 100, 4) if gross else float("nan"),
            net_sharpe=round(net.sharpe, 4),
            gross_sharpe=round(gross.sharpe, 4) if gross else float("nan"),
            max_drawdown_pct=round(net.max_drawdown * 100, 3),
            fees_usd=round(net.total_fees, 2),
            borrow_fees_usd=round(net.total_borrow_fees, 2),
            cost_share_of_capital=round(costs / 10_000.0, 4),
            exposure_fraction=round(net.exposure_fraction, 4),
            liquidations=int(net.liquidation_count),
            seconds=round(time.time() - started, 2),
        ))
    except Exception as exc:                     # noqa: BLE001 - reported, not swallowed
        # A failed cell is recorded as a failed cell. Dropping it would leave a hole in
        # the matrix that reads as "not run" and averages as "not there".
        return asdict(Cell(
            asset=asset, strategy=strategy,
            params=";".join(f"{k}={v}" for k, v in sorted(params.items())) or "-",
            bars=0, first="", last="", trades=0,
            net_return_pct=float("nan"), gross_return_pct=float("nan"),
            net_sharpe=float("nan"), gross_sharpe=float("nan"),
            max_drawdown_pct=float("nan"), fees_usd=0.0, borrow_fees_usd=0.0,
            cost_share_of_capital=float("nan"), exposure_fraction=float("nan"),
            liquidations=0, seconds=round(time.time() - started, 2),
            error=f"{type(exc).__name__}: {exc}"[:200],
        ))


LEGEND = """\
HOW TO READ THIS -- and what it is not
--------------------------------------
PRELIMINARY. One pass per cell: no CPCV, no PBO, no walk-forward, no out-of-sample
split. This repository's own finding 1c measures in-sample rank as ANTI-INFORMATIVE at
the daily horizons (PBO 0.700, above the 0.500 noise line), and finding 1f shows even
the CPCV ordering is largely an artifact of the block count. So a good number here is
not evidence that a strategy works. It is a reason to spend a real protocol on that
cell; a bad number is a reason not to.

net vs gross   net is after fees, slippage and borrow. gross is the same strategy with
               the cost path removed. At one minute the gap between them IS the result:
               if gross is near zero and net is -90%, the strategy has no edge to pay
               the spread with, which is a different diagnosis from a broken signal.
cost share     total fees + borrow as a fraction of the $10,000 starting capital. Above
               ~1.0 the account has been spent on round trips.
trades         a round trip is two fees. Tens of thousands of trades at 8bps a side is
               the whole story for most rows below.
window         each asset uses its own most recent bars unless --common-window was
               passed, so spans DIFFER and cross-asset rows are not like-for-like."""


def render(cells: pd.DataFrame, scale: int, window_mode: str) -> str:
    """The report, leading with costs because at this granularity they dominate."""
    lines = [
        "PRELIMINARY 1-MINUTE SWEEP -- all cached assets x all registered strategies",
        f"parameter scale: x{scale} "
        f"({'bar counts as written' if scale == 1 else 'wall-clock preserving'})   "
        f"window: {window_mode}   fees {FEE_BPS:.0f}bps + slippage {SLIPPAGE_BPS:.0f}bps",
        "",
        LEGEND,
        "",
    ]
    ok = cells[cells["error"] == ""]
    failed = cells[cells["error"] != ""]

    lines += ["PER-ASSET WINDOW ACTUALLY USED", "-" * 78,
              f"{'asset':<7}{'bars':>12}{'from':>13}{'to':>13}{'cells':>7}{'net>0':>7}"]
    for asset, grp in ok.groupby("asset"):
        lines.append(
            f"{asset:<7}{int(grp['bars'].max()):>12,}{grp['first'].min()[:10]:>13}"
            f"{grp['last'].max()[:10]:>13}{len(grp):>7}"
            f"{int((grp['net_return_pct'] > 0).sum()):>7}"
        )

    lines += ["", "EVERY CELL, WORST COST SHARE FIRST", "-" * 100,
              f"{'asset':<6}{'strategy':<17}{'trades':>8}{'net %':>10}{'gross %':>10}"
              f"{'net Sh':>9}{'gross Sh':>10}{'costs $':>10}{'cost/cap':>9}{'secs':>7}"]
    for _, r in ok.sort_values("cost_share_of_capital", ascending=False).iterrows():
        lines.append(
            f"{r['asset']:<6}{r['strategy'][:16]:<17}{int(r['trades']):>8,}"
            f"{r['net_return_pct']:>10.2f}{r['gross_return_pct']:>10.2f}"
            f"{r['net_sharpe']:>9.2f}{r['gross_sharpe']:>10.2f}"
            f"{r['fees_usd'] + r['borrow_fees_usd']:>10,.0f}"
            f"{r['cost_share_of_capital']:>9.2f}{r['seconds']:>7.1f}"
        )

    positive = ok[ok["net_return_pct"] > 0]
    lines += ["", "CELLS WITH A POSITIVE NET RETURN", "-" * 78]
    if positive.empty:
        lines.append("  none. Every cell lost money after costs.")
    else:
        for _, r in positive.sort_values("net_return_pct", ascending=False).iterrows():
            lines.append(
                f"  {r['asset']:<6}{r['strategy'][:18]:<19}"
                f"net {r['net_return_pct']:+8.2f}%  Sharpe {r['net_sharpe']:+7.2f}  "
                f"{int(r['trades']):>7,} trades  costs ${r['fees_usd']:>8,.0f}"
            )

    if not ok.empty:
        share = ok["cost_share_of_capital"]
        lines += [
            "", "WHAT THE COSTS DID", "-" * 78,
            f"  cells run                     : {len(ok)}",
            f"  cells with positive net return: {len(positive)} "
            f"({len(positive) / len(ok):.0%})",
            f"  cells whose costs exceeded capital: {int((share > 1.0).sum())}",
            f"  median cost share of capital  : {share.median():.2f}",
            f"  median trades per cell        : {int(ok['trades'].median()):,}",
        ]
        both = ok.dropna(subset=["gross_return_pct"])
        if not both.empty:
            better_gross = int((both["gross_return_pct"] > both["net_return_pct"]).sum())
            gross_pos = int((both["gross_return_pct"] > 0).sum())
            lines += [
                f"  cells better gross than net   : {better_gross} of {len(both)}",
                f"  cells positive BEFORE costs   : {gross_pos} "
                f"({gross_pos / len(both):.0%}) -- against "
                f"{len(positive)} after",
            ]

    if not failed.empty:
        lines += ["", f"FAILED CELLS ({len(failed)})", "-" * 78]
        for _, r in failed.iterrows():
            lines.append(f"  {r['asset']:<6}{r['strategy']:<18}{r['error']}")

    lines += [
        "", "NEXT STEP, IF ANY CELL SURVIVED", "-" * 78,
        "  A positive cell here has been selected by looking at the whole sample, which",
        "  is the definition of in-sample. Put it through CPCV before believing it:",
        "      python3 research/cpcv_sweep.py",
        "  and check it is not an artifact of one evaluation geometry:",
        "      python3 research/geometry.py --horizon long --blocks 6 12 --k 2",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(
        description="Preliminary 1-minute backtest of every strategy on every asset.")
    ap.add_argument("--asset", action="append", default=[], help="limit to these assets")
    ap.add_argument("--strategy", action="append", default=[],
                    help="limit to these strategies")
    ap.add_argument("--bars", type=int, default=DEFAULT_BARS,
                    help=f"most recent bars per asset (default {DEFAULT_BARS:,})")
    ap.add_argument("--all-bars", action="store_true",
                    help="use every cached bar; hours of CPU, see the docstring")
    ap.add_argument("--common-window", action="store_true",
                    help="intersect all assets' calendars so cells are comparable")
    ap.add_argument("--param-scale", type=int, default=1,
                    help="multiply bar-count parameters (60 preserves the hourly "
                         "wall-clock window; much slower)")
    # Default deliberately below cpu_count: each worker holds one asset slice plus the
    # engine's own arrays, and the first run died with BrokenProcessPool at 10.
    ap.add_argument("--workers", type=int,
                    default=min(6, max(1, (__import__("os").cpu_count() or 4) - 2)))
    ap.add_argument("--tag", default="", help="suffix for the output filenames")
    args = ap.parse_args(argv)

    if args.param_scale < 1:
        ap.error("--param-scale must be at least 1")
    if args.bars < 2:
        ap.error("--bars must be at least 2")

    assets = [a.upper() for a in args.asset] or available_assets()
    missing = [a for a in assets if not minute_path(a).exists()]
    if missing:
        ap.error(
            f"no 1m cache for {', '.join(missing)}. Fetch first:\n"
            f"    python3 -m backtester.core.fetch_minutes --asset "
            + " --asset ".join(missing)
        )
    if not assets:
        ap.error("no 1m caches found; run backtester.core.fetch_minutes --all first")

    strategies = args.strategy or sorted(BASE_PARAMS)
    unknown = [s for s in strategies if s not in BASE_PARAMS]
    if unknown:
        ap.error(f"unknown strategies: {', '.join(unknown)}")

    window = common_window(assets) if args.common_window else None
    bars = None if args.all_bars else args.bars
    window_mode = ("common calendar across assets" if args.common_window
                   else "each asset's own most recent bars")
    if bars is not None:
        window_mode += f", capped at {bars:,}"

    # Parse each CSV once here, not once per cell in each worker.
    print(f"preparing {len(assets)} asset slices (parsed once, not per cell) …",
          file=sys.stderr)
    for a in assets:
        path = build_slice(a, bars, window)
        print(f"  {a}: {path.stat().st_size / 1048576:.0f} MB slice", file=sys.stderr)

    jobs = [(a, s, args.param_scale, bars, window) for a in assets for s in strategies]
    print(f"{len(jobs)} cells: {len(assets)} assets x {len(strategies)} strategies, "
          f"{args.workers} workers", file=sys.stderr)
    if args.all_bars:
        print("  --all-bars: expect hours. rsi alone measured ~1.8h per asset at 2.6M "
              "bars.", file=sys.stderr)

    started = time.time()
    rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        # submit/as_completed rather than map: map propagates a BrokenProcessPool and
        # loses every completed result with it, which is how the first run ended with
        # nothing written after an hour of compute.
        futures = {pool.submit(run_cell, j): j for j in jobs}
        done = 0
        for future in as_completed(futures):
            done += 1
            try:
                row = future.result()
            except Exception as exc:                      # noqa: BLE001
                asset, strategy = futures[future][0], futures[future][1]
                row = asdict(Cell(
                    asset=asset, strategy=strategy, params="-", bars=0, first="", last="",
                    trades=0, net_return_pct=float("nan"), gross_return_pct=float("nan"),
                    net_sharpe=float("nan"), gross_sharpe=float("nan"),
                    max_drawdown_pct=float("nan"), fees_usd=0.0, borrow_fees_usd=0.0,
                    cost_share_of_capital=float("nan"), exposure_fraction=float("nan"),
                    liquidations=0, seconds=0.0,
                    error=f"worker died: {type(exc).__name__}: {exc}"[:200]))
            rows.append(row)
            if done % 10 == 0 or done == len(jobs):
                rate = done / max(1e-9, time.time() - started)
                print(f"  {done}/{len(jobs)} cells, {rate:.2f}/s, "
                      f"~{(len(jobs) - done) / max(1e-9, rate) / 60:.0f} min left",
                      file=sys.stderr)

    cells = pd.DataFrame(rows)
    text = render(cells, args.param_scale, window_mode)
    print(text)

    OUT.mkdir(parents=True, exist_ok=True)
    stem = f"minute_sweep_x{args.param_scale}{('_' + args.tag) if args.tag else ''}"
    (OUT / f"{stem}.txt").write_text(text + "\n")
    cells.to_csv(OUT / f"{stem}.csv", index=False)
    print(f"\nwrote {OUT}/{stem}.{{txt,csv}}  in {(time.time()-started)/60:.1f} min",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

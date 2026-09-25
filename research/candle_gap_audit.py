"""Audit -- and optionally repair -- gaps in Coinbase 1m candle data using ticks.

Why this exists. A missing 1m candle has two possible causes that look
identical in the file and have opposite consequences:

  * the minute genuinely had no trades (thin market), or
  * the minute traded and the candle endpoint dropped it.

The first is honest data. The second is data loss, and it does not stop at the
missing bar: the enclosing coarser bar is short the same volume and can report
a wrong high or low, which is exactly the number stop and liquidation logic
reads. Only the trades endpoint can tell them apart, so this script asks it.

`--sample N` classifies N randomly-chosen gap runs per asset (seeded, so a run
is reproducible). `--repair` rebuilds every affected minute from ticks and
writes a repaired series.

The repaired series is written to `data/repaired/` and never over the candle
cache: it is a MIXED-PROVENANCE file, candle bars everywhere except the
repaired windows, and that fact must travel with the filename rather than
living only in someone's memory.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import pandas as pd

# Running this file directly puts the script's own directory on sys.path, not
# the repo root -- same reason the other research/ scripts do this.
REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import validate_bars  # noqa: E402
from backtester.core.ticks import fetch_trades, trades_to_bars  # noqa: E402
from backtester.core.types import BAR_COLUMNS, INTERVAL_SECONDS  # noqa: E402

# A tick fetch pays a ~29-probe bisection to find its window, so windows are
# padded and merged rather than fetched one bar at a time. The padding also
# buys the comparison bars on each side of a gap, which is how understated
# (present but wrong) candles get caught.
PAD_BARS = 2


def gap_runs(df: pd.DataFrame, seconds: int) -> list[tuple[int, int]]:
    """Contiguous runs of missing bars as (first_missing_ts, last_missing_ts)."""
    ts = df["timestamp"].to_numpy()
    runs: list[tuple[int, int]] = []
    for i in range(len(ts) - 1):
        step = int(ts[i + 1] - ts[i])
        if step > seconds:
            runs.append((int(ts[i]) + seconds, int(ts[i + 1]) - seconds))
    return runs


def classify_run(
    product: str,
    run: tuple[int, int],
    seconds: int,
    *,
    verbose: bool = False,
) -> dict:
    """Fetch the ticks for one gap run and say why the candles are missing."""
    first, last = run
    trades = _fetch_window(product, first, last + seconds, verbose=verbose)
    missing = list(range(first, last + seconds, seconds))
    if trades is None or trades.empty:
        traded = 0
        volume = 0.0
    else:
        inside = trades[
            (trades["timestamp"] >= first) & (trades["timestamp"] < last + seconds)
        ]
        traded = len(inside)
        volume = float(inside["size"].sum())
    return {
        "start": pd.Timestamp(first, unit="s", tz="UTC"),
        "minutes": len(missing),
        "trades": traded,
        "volume": round(volume, 4),
        # The whole point of the script, in one field.
        "verdict": "DROPPED (traded)" if traded else "quiet (no trades)",
    }


def _fetch_window(
    product: str, start_ts: int, end_ts: int, *, verbose: bool = False
) -> pd.DataFrame | None:
    """Ticks for [start_ts, end_ts), or None if the endpoint returned nothing."""
    try:
        return fetch_trades(
            product,
            pd.Timestamp(start_ts, unit="s", tz="UTC").isoformat(),
            pd.Timestamp(end_ts, unit="s", tz="UTC").isoformat(),
            verbose=verbose,
        )
    except Exception as exc:  # network or empty window
        print(f"    fetch failed: {exc}", file=sys.stderr)
        return None


def repair_window(
    product: str,
    run: tuple[int, int],
    candles: pd.DataFrame,
    seconds: int,
    *,
    verbose: bool = False,
) -> tuple[pd.DataFrame, list[dict]]:
    """Rebuild a padded window from ticks; return its bars and any candle diffs.

    The padding matters: a dropped minute is not always the only damage. A
    candle that IS present next to one can still understate its volume, and
    that only shows up by comparing it against the ticks.
    """
    first, last = run
    w_start = first - PAD_BARS * seconds
    w_end = last + (PAD_BARS + 1) * seconds
    trades = _fetch_window(product, w_start, w_end, verbose=verbose)
    if trades is None or trades.empty:
        return pd.DataFrame(columns=list(BAR_COLUMNS)), []

    interval = {v: k for k, v in INTERVAL_SECONDS.items()}[seconds]
    bars = trades_to_bars(trades, interval)
    bars = bars[(bars["timestamp"] >= w_start) & (bars["timestamp"] < w_end)]

    diffs: list[dict] = []
    existing = candles.set_index("timestamp")
    for row in bars.itertuples(index=False):
        if row.timestamp not in existing.index:
            continue
        c = existing.loc[row.timestamp]
        for field in ("open", "high", "low", "close", "volume"):
            tick_v = float(getattr(row, field))
            cand_v = float(c[field])
            if abs(tick_v - cand_v) > 1e-8:
                diffs.append(
                    {
                        "minute": pd.Timestamp(row.timestamp, unit="s", tz="UTC"),
                        "field": field,
                        "candle": cand_v,
                        "ticks": tick_v,
                        "delta": round(tick_v - cand_v, 8),
                    }
                )
    return bars.reset_index(drop=True), diffs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assets", default="SOL")
    ap.add_argument("--quote", default="USD")
    ap.add_argument("--interval", default="1m", choices=sorted(INTERVAL_SECONDS))
    ap.add_argument("--suffix", default="_last30d", help="candle cache filename suffix")
    ap.add_argument("--data-dir", default="data")
    ap.add_argument(
        "--sample",
        type=int,
        default=0,
        help="classify N random gap runs per asset as dropped vs quiet",
    )
    ap.add_argument("--seed", type=int, default=0, help="sampling seed")
    ap.add_argument(
        "--repair",
        action="store_true",
        help="rebuild every gap window from ticks and write a repaired series",
    )
    ap.add_argument(
        "--max-runs",
        type=int,
        default=0,
        help="repair at most N gap runs (0 = all). Each run costs a tick fetch, "
        "so an illiquid asset with thousands of quiet minutes is not repairable "
        "in one pass; a capped repair is labelled PARTIAL, never presented whole",
    )
    ap.add_argument("--out-dir", default="data/repaired")
    ap.add_argument("--report", default=None, help="write a markdown report here")
    args = ap.parse_args(argv)

    seconds = INTERVAL_SECONDS[args.interval]
    lines: list[str] = []
    for asset in [a.strip().upper() for a in args.assets.split(",") if a.strip()]:
        path = Path(args.data_dir) / f"{asset}_{args.interval}{args.suffix}.csv"
        if not path.exists():
            print(f"{asset}: no candle cache at {path}, skipping", file=sys.stderr)
            continue
        candles = pd.read_csv(path)
        runs = gap_runs(candles, seconds)
        product = f"{asset}-{args.quote.upper()}"
        missing = sum((b - a) // seconds + 1 for a, b in runs)
        print(f"\n{asset}: {len(candles)} bars, {len(runs)} gap runs, "
              f"{missing} missing {args.interval} bars", file=sys.stderr)
        lines.append(f"\n## {asset}\n")
        lines.append(
            f"- {len(candles)} bars, **{len(runs)} gap runs**, {missing} missing bars\n"
        )

        if args.sample:
            rng = random.Random(args.seed)
            chosen = runs if len(runs) <= args.sample else rng.sample(runs, args.sample)
            chosen = sorted(chosen)
            rows = []
            for run in chosen:
                r = classify_run(product, run, seconds)
                rows.append(r)
                print(f"  {r['start']}  {r['minutes']}m  trades={r['trades']:>4}  "
                      f"{r['verdict']}", file=sys.stderr)
            tbl = pd.DataFrame(rows)
            dropped = int((tbl["verdict"].str.startswith("DROPPED")).sum())
            lines.append(
                f"- sampled **{len(tbl)}** of {len(runs)} gap runs (seed {args.seed}): "
                f"**{dropped} dropped** (the minute traded), "
                f"{len(tbl) - dropped} genuinely quiet\n\n"
            )
            lines.append(tbl.to_markdown(index=False) + "\n")

        if args.repair:
            rebuilt: list[pd.DataFrame] = []
            all_diffs: list[dict] = []
            targets = runs if not args.max_runs else runs[: args.max_runs]
            partial = len(targets) < len(runs)
            if partial:
                print(f"  PARTIAL repair: {len(targets)} of {len(runs)} gap runs",
                      file=sys.stderr)
            for run in targets:
                bars, diffs = repair_window(product, run, candles, seconds)
                if not bars.empty:
                    rebuilt.append(bars)
                all_diffs.extend(diffs)
            if not rebuilt:
                lines.append("- repair produced no bars (no ticks returned)\n")
                continue
            fill = pd.concat(rebuilt, ignore_index=True).drop_duplicates("timestamp")
            merged = pd.concat(
                [candles[~candles["timestamp"].isin(set(fill["timestamp"]))], fill],
                ignore_index=True,
            ).sort_values("timestamp").reset_index(drop=True)
            merged = merged.loc[:, list(BAR_COLUMNS)]
            validate_bars(merged, args.interval, strict_gaps=False)

            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            tag = "_PARTIAL" if partial else ""
            out = out_dir / f"{asset}_{args.interval}{args.suffix}_repaired{tag}.csv"
            merged.to_csv(out, index=False)
            recovered = len(merged) - len(candles)
            corrected = len({d["minute"] for d in all_diffs})
            print(f"  wrote {out}: +{recovered} recovered bars, "
                  f"{corrected} existing bars corrected", file=sys.stderr)
            scope = (
                f" (**PARTIAL** — {len(targets)} of {len(runs)} gap runs repaired; "
                "the remaining gaps are untouched and unclassified)"
                if partial
                else ""
            )
            lines.append(
                f"- repaired: `{out}` — **+{recovered} bars recovered**, "
                f"**{corrected} existing bars corrected** from ticks{scope}\n"
            )
            if all_diffs:
                d = pd.DataFrame(all_diffs)
                lines.append("\nCorrections to bars the endpoint *did* return:\n\n")
                lines.append(d.head(40).to_markdown(index=False) + "\n")
                if len(d) > 40:
                    lines.append(f"\n_({len(d)} corrections total, first 40 shown)_\n")

    if args.report:
        header = (
            "# Candle-gap audit\n\n"
            "Generated by `research/candle_gap_audit.py`. Every figure below comes "
            "from the Coinbase trades endpoint, compared against the 1m candle "
            "cache in `data/`.\n"
        )
        Path(args.report).write_text(header + "".join(lines))
        print(f"\nreport: {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

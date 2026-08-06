"""Long-running, resumable tick backfill and candle-integrity audit.

Built to run for hours at low priority in the background. See
`research/run_backfill.sh` for the wrapper that sets the priority.

Why a streaming walk instead of `candle_gap_audit.py`'s per-gap fetch. That
script pays a ~29-request bisection to locate each gap, which is fine for five
gaps and absurd for DOGE's 3,739 -- roughly 24,000 requests, most of them spent
finding the window rather than reading it. Walking the whole window once,
backward, costs `total_trades / 1000` requests and classifies *every* gap
instead of a sample. For a month of SOL that is ~5,600 requests, not ~24,000
per asset, and it yields an authoritative bar series as a by-product.

The audit it then runs answers the question the sampled audit could not: a
minute can be **present and still wrong**. Only a complete tick reconstruction
can show that, and only at that point can anyone say whether the 1h and 1d
series the research actually reads are affected.

Phases, each skippable and each checkpointed:

  1. `backfill` -- stream ticks for the window, aggregate to 1m, write an
     authoritative series. Resumable: interrupt it and it continues.
  2. `audit`    -- diff the authoritative series against the candle cache at
     1m, and against the coarser candle files the research reads. Classifies
     every gap as dropped or quiet, no sampling.
  3. `rerun`    -- re-run the decision path on repaired vs original inputs and
     diff the verdicts, so "the data changed" becomes "the answer changed" or
     "the answer held".
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import validate_bars  # noqa: E402
from backtester.core.fetch import COINBASE_BASE, FetchError, _get_json  # noqa: E402
from backtester.core.ticks import _parse_trades, seek_trade_id  # noqa: E402
from backtester.core.types import BAR_COLUMNS, INTERVAL_SECONDS  # noqa: E402

PAGE = 1000
CHECKPOINT_EVERY = 25  # pages between checkpoint writes

_stop = False


def _handle_stop(signum, frame):  # noqa: ARG001
    """Finish the current page, checkpoint, exit cleanly.

    A background job that cannot be stopped without losing hours of work is a
    job people kill with -9 and then re-run from zero.
    """
    global _stop
    _stop = True
    print("\n  stop requested; checkpointing after this page", file=sys.stderr)


class MinuteAggregator:
    """Incremental OHLCV per bar interval, so ticks are never all held at once."""

    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        self.bars: dict[int, dict] = {}

    def add(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        buckets = (df["timestamp"] // self.seconds).astype("int64") * self.seconds
        for bucket, group in df.assign(b=buckets).groupby("b", sort=False):
            # Pages arrive newest-first, so within a bucket the earliest trade
            # may be seen last. Ordering is resolved by (timestamp, trade_id),
            # never by arrival, or open and close come out swapped.
            g = group.sort_values(["timestamp", "trade_id"])
            cur = self.bars.get(int(bucket))
            first_ts = (float(g["timestamp"].iloc[0]), int(g["trade_id"].iloc[0]))
            last_ts = (float(g["timestamp"].iloc[-1]), int(g["trade_id"].iloc[-1]))
            if cur is None:
                self.bars[int(bucket)] = {
                    "open": float(g["price"].iloc[0]), "open_key": first_ts,
                    "close": float(g["price"].iloc[-1]), "close_key": last_ts,
                    "high": float(g["price"].max()), "low": float(g["price"].min()),
                    "volume": float(g["size"].sum()),
                }
                continue
            if first_ts < cur["open_key"]:
                cur["open"], cur["open_key"] = float(g["price"].iloc[0]), first_ts
            if last_ts > cur["close_key"]:
                cur["close"], cur["close_key"] = float(g["price"].iloc[-1]), last_ts
            cur["high"] = max(cur["high"], float(g["price"].max()))
            cur["low"] = min(cur["low"], float(g["price"].min()))
            cur["volume"] += float(g["size"].sum())

    def frame(self) -> pd.DataFrame:
        rows = [
            {
                "timestamp": ts, "open": b["open"], "high": b["high"],
                "low": b["low"], "close": b["close"], "volume": b["volume"],
            }
            for ts, b in sorted(self.bars.items())
        ]
        return pd.DataFrame(rows, columns=list(BAR_COLUMNS))

    def state(self) -> dict:
        return {str(k): v for k, v in self.bars.items()}

    def load(self, state: dict) -> None:
        self.bars = {
            int(k): {**v, "open_key": tuple(v["open_key"]), "close_key": tuple(v["close_key"])}
            for k, v in state.items()
        }


def _page(product: str, after: int | None) -> pd.DataFrame:
    params = f"limit={PAGE}" + (f"&after={after}" if after is not None else "")
    return _parse_trades(_get_json(f"{COINBASE_BASE}/products/{product}/trades?{params}"))


def backfill(
    asset: str, quote: str, start: str, end: str, interval: str,
    ck_dir: Path, out_dir: Path, *, pause: float, verbose: bool = True,
) -> Path | None:
    """Stream the whole window once, checkpointing, and write authoritative bars."""
    product = f"{asset}-{quote}"
    seconds = INTERVAL_SECONDS[interval]
    start_ts = pd.Timestamp(start, tz="UTC").timestamp()
    end_ts = pd.Timestamp(end, tz="UTC").timestamp()

    ck_dir.mkdir(parents=True, exist_ok=True)
    ck = ck_dir / f"{asset}_{interval}_{start}_{end}.json"
    agg = MinuteAggregator(seconds)
    cursor: int | None = None
    pages = trades_seen = 0
    done = False

    if ck.exists():
        state = json.loads(ck.read_text())
        agg.load(state["bars"])
        cursor = state["cursor"]
        pages, trades_seen = state["pages"], state["trades"]
        done = state.get("done", False)
        print(f"  resumed at cursor {cursor} ({trades_seen} trades, {pages} pages)",
              file=sys.stderr)
    if done:
        print(f"  {asset}: already complete", file=sys.stderr)
    else:
        if cursor is None:
            cursor = seek_trade_id(product, end_ts, pause=pause, verbose=verbose) + 1
        while not _stop:
            try:
                page = _page(product, cursor)
            except FetchError as exc:
                print(f"  fetch error, checkpointing: {exc}", file=sys.stderr)
                break
            if page.empty:
                done = True
                break
            agg.add(page[(page["timestamp"] >= start_ts) & (page["timestamp"] < end_ts)])
            pages += 1
            trades_seen += len(page)
            oldest_id = int(page["trade_id"].min())
            oldest_ts = float(page["timestamp"].min())
            if oldest_ts < start_ts or oldest_id >= cursor:
                done = True
                break
            cursor = oldest_id
            if pages % CHECKPOINT_EVERY == 0:
                _write_ck(ck, agg, cursor, pages, trades_seen, done)
                if verbose:
                    print(f"  {asset}: {pages} pages, {trades_seen} trades, "
                          f"at {pd.Timestamp(oldest_ts, unit='s', tz='UTC')}",
                          file=sys.stderr)
            time.sleep(pause)
        _write_ck(ck, agg, cursor, pages, trades_seen, done)

    if not done:
        print(f"  {asset}: INCOMPLETE (interrupted) — rerun to continue", file=sys.stderr)
        return None

    bars = agg.frame()
    if bars.empty:
        print(f"  {asset}: no bars built", file=sys.stderr)
        return None
    validate_bars(bars, interval, strict_gaps=False)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{asset}_{interval}_{start}_{end}_from_ticks.csv"
    bars.to_csv(out, index=False)
    print(f"  {asset}: wrote {len(bars)} authoritative bars to {out} "
          f"({trades_seen} trades)", file=sys.stderr)
    return out


def _write_ck(ck: Path, agg, cursor, pages, trades, done) -> None:
    tmp = ck.with_suffix(".tmp")
    tmp.write_text(json.dumps(
        {"cursor": cursor, "pages": pages, "trades": trades, "done": done,
         "bars": agg.state()}))
    tmp.replace(ck)  # atomic: a killed job never leaves a half-written checkpoint


def audit(asset: str, truth_path: Path, data_dir: Path, interval: str) -> list[str]:
    """Diff authoritative bars against the candle cache, at this and coarser intervals."""
    out: list[str] = []
    truth = pd.read_csv(truth_path)
    seconds = INTERVAL_SECONDS[interval]

    candle_path = data_dir / f"{asset}_{interval}_last30d.csv"
    if candle_path.exists():
        c = pd.read_csv(candle_path)
        missing = sorted(set(truth["timestamp"]) - set(c["timestamp"]))
        traded = [t for t in missing if float(truth.loc[truth["timestamp"] == t, "volume"].iloc[0]) > 0]
        present = c.merge(truth, on="timestamp", suffixes=("_c", "_t"))
        wrong = {
            f: int((abs(present[f + "_c"] - present[f + "_t"]) > 1e-8).sum())
            for f in ("open", "high", "low", "close", "volume")
        }
        out.append(
            f"- `{candle_path.name}`: {len(missing)} bars absent that ticks show "
            f"(**{len(traded)} of them traded**); of {len(present)} bars present, "
            + ", ".join(f"{n} wrong {f}" for f, n in wrong.items() if n) + "\n"
        )

    for coarse, cseconds in sorted(INTERVAL_SECONDS.items(), key=lambda kv: kv[1]):
        if cseconds <= seconds:
            continue
        cpath = data_dir / f"{asset}_{coarse}.csv"
        if not cpath.exists():
            continue
        c = pd.read_csv(cpath)
        b = (truth["timestamp"] // cseconds).astype("int64") * cseconds
        rebuilt = truth.assign(b=b).groupby("b").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"),
            close=("close", "last"), volume=("volume", "sum"))
        m = c.set_index("timestamp").join(rebuilt, rsuffix="_t", how="inner").dropna()
        if m.empty:
            continue
        wrong = {
            f: int((abs(m[f] - m[f + "_t"]) > 1e-6).sum())
            for f in ("open", "high", "low", "close", "volume")
        }
        worst = float(max((m[f] - m[f + "_t"]).abs().max() for f in ("high", "low")))
        out.append(
            f"- `{cpath.name}` over the overlap ({len(m)} bars): "
            + ", ".join(f"**{n} wrong {f}**" for f, n in wrong.items() if n)
            + f"; largest price error {worst:.6f}\n"
        )
    return out


def rerun_decision(asset: str, original: Path, repaired: Path, interval: str) -> str:
    """Run research/decide.py on both inputs and report whether the verdict moved.

    decide.py takes an explicit --data path, so this compares like for like
    without swapping anything under the candle cache.
    """
    def run(path: Path) -> dict | None:
        cmd = [sys.executable, str(REPO / "research" / "decide.py"),
               "--data", str(path), "--interval", interval, "--json"]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        except subprocess.TimeoutExpired:
            return None
        if r.returncode != 0:
            return None
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return None

    a, b = run(original), run(repaired)
    if a is None or b is None:
        return f"- {asset}: decision re-run unavailable (decide.py did not return JSON)\n"
    same = a == b
    return (
        f"- {asset}: decision on repaired input is "
        f"{'**unchanged**' if same else '**DIFFERENT** — the data error moved the answer'}\n"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assets", default="DOGE,ZEC")
    ap.add_argument("--quote", default="USD")
    ap.add_argument("--start", default="2026-07-06")
    ap.add_argument("--end", default="2026-08-06")
    ap.add_argument("--interval", default="1m", choices=sorted(INTERVAL_SECONDS))
    ap.add_argument("--data-dir", default=str(REPO / "data"))
    ap.add_argument("--out-dir", default=str(REPO / "data" / "authoritative"))
    ap.add_argument("--checkpoint-dir", default=str(REPO / "data" / "checkpoints"))
    ap.add_argument("--report", default=str(REPO / "research" / "TICK-BACKFILL-AUDIT.md"))
    ap.add_argument("--pause", type=float, default=0.15,
                    help="seconds between requests; keep under the public rate limit")
    ap.add_argument("--phases", default="backfill,audit,rerun")
    args = ap.parse_args(argv)

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    phases = {p.strip() for p in args.phases.split(",")}
    data_dir, out_dir = Path(args.data_dir), Path(args.out_dir)
    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    lines = [
        "# Tick backfill and candle-integrity audit\n\n",
        f"Generated by `research/tick_backfill.py` over {args.start} .. {args.end}.\n"
        "Every bar here is rebuilt from raw trades, so it is a census rather than "
        "the sampled estimate in `CANDLE-GAP-AUDIT.md`.\n",
    ]
    started = time.time()

    for asset in assets:
        print(f"\n=== {asset}", file=sys.stderr)
        lines.append(f"\n## {asset}\n\n")
        truth = out_dir / f"{asset}_{args.interval}_{args.start}_{args.end}_from_ticks.csv"

        if "backfill" in phases and not _stop:
            got = backfill(asset, args.quote.upper(), args.start, args.end,
                           args.interval, Path(args.checkpoint_dir), out_dir,
                           pause=args.pause)
            if got is None and not truth.exists():
                lines.append("- backfill incomplete; rerun to continue\n")
                continue
        if not truth.exists():
            lines.append("- no authoritative series yet\n")
            continue
        if "audit" in phases:
            lines.extend(audit(asset, truth, data_dir, args.interval))
        if "rerun" in phases:
            orig = data_dir / f"{asset}_{args.interval}_last30d.csv"
            if orig.exists():
                lines.append(rerun_decision(asset, orig, truth, args.interval))

    lines.append(f"\n_Run took {(time.time() - started) / 60:.1f} min._\n")
    Path(args.report).write_text("".join(lines))
    print(f"\nreport: {args.report}", file=sys.stderr)
    return 0 if not _stop else 130


if __name__ == "__main__":
    raise SystemExit(main())

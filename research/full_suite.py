"""Pull fresh data, then run every backtest: all coins, all strategies, all configurations.

    python3 research/full_suite.py --plan          # print every step; touches nothing
    python3 research/full_suite.py                 # fetch, then both sweeps (hours)
    python3 research/full_suite.py --skip-fetch    # re-run the sweeps on the cache you have
    python3 research/full_suite.py --fetch-only    # refresh the cache and stop

Run it with the soltui interpreter (it has numpy/pandas/Textual):

    /Users/mitch/.venvs/soltui/bin/python research/full_suite.py

## What "full" means here, and its size

1. **Fetch** (the only network step, explicit as CLAUDE.md requires): daily and hourly candles
   for the tradeable universe (`backtester.core.universe`), **1-minute candles back to each
   coin's earliest available minute** (`backtester.core.fetch_minutes`, resumable, with a
   coverage manifest), and Hyperliquid hourly funding (`backtester.core.funding`). Written to the main checkout's `data/` cache, never a worktree.
2. **Registry sweep**: `soltui.bgworker` per asset -- every strategy card, every horizon,
   perturbation tiers 0-2 (about 1,060 CPCV jobs per asset). Results land in the file the
   Strategies and Queue tabs read.
3. **Compound sweep**: `soltui.compound sweep --perturb --aggregate-grid` -- every coin in
   parallel, each with its own settings: the five-minute compound, each metric alone,
   one-at-a-time parameter variations and the threshold/gate/regime/leverage grid (about 300
   configurations per coin), on 5m bars built from the full 1-minute history. Results land in
   the file the Compound 5m tab reads.

Every configuration count is printed. That count is the multiple-testing denominator: the best
of 10,000 configurations will look good by luck, so read the leaderboards out-of-sample only.

## Why existing registry results are archived after a fetch

The background worker binds its results to a proof of the code, settings and price files that
produced them, and refuses to append rows computed on different data. Re-fetching changes the
price files, so the old `results.jsonl` (and its proof) is MOVED to `bg/archive/<stamp>/` --
never deleted -- before the new sweep starts. `--keep-results` skips that and lets the worker
refuse instead.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import resolve_data_dir  # noqa: E402
from backtester.core.fetch_minutes import MINUTE_ASSETS  # noqa: E402
from backtester.core.universe import EXCLUDED, TOP10_NON_PEGGED  # noqa: E402

DEFAULT_ASSETS = tuple(a for a in TOP10_NON_PEGGED if a not in EXCLUDED)
TOP50_RECORD = REPO / "research" / "results" / "top50-nonpegged-2026-11-07.json"


def top50() -> tuple[list[str], list[str]]:
    """(Coinbase-listed, other-venue) symbols from the dated top-50 record."""
    rec = json.loads(TOP50_RECORD.read_text())
    return list(rec["coinbase_listed"]), list(rec["not_on_coinbase"])


def fetch_steps(assets: list[str], data: Path, args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    """(description, argv) for the network step."""
    if args.skip_fetch:
        return []
    py = sys.executable
    start_5m = (datetime.now(timezone.utc).date() - timedelta(days=args.days_5m)).isoformat()
    from backtester.core.fetch_minutes_alt import ASSET_VENUE

    # Coinbase serves the 1d/1h/5m/1m candles for most coins; the rest come only as 1m candles
    # from the venue ASSET_VENUE names. Funding is Hyperliquid's, which skips what it lacks.
    minute_assets = [a for a in assets if a not in ASSET_VENUE]
    alt_assets = [a for a in assets if a in ASSET_VENUE]
    out: list[tuple[str, list[str]]] = []
    for interval, start in (("1d", "2021-01-01"), ("1h", args.start_1h)):
        if not minute_assets:
            break
        out.append((f"fetch {interval} candles", [
            py, "-m", "backtester.core.universe", "--assets", ",".join(minute_assets), "--interval", interval,
            "--start", start, "--out-dir", str(data), "--refetch", "--allow-partial", "--allow-gaps"]))
    # The finest history Coinbase serves: 1-minute candles back to each coin's earliest minute
    # (resumable; a re-run only fetches what is missing). The compound builds its 5m bars from
    # these, and they are what the backtests run on when they are the longest series cached.
    if minute_assets and args.minutes_years > 0:
        cmd = [py, "-m", "backtester.core.fetch_minutes", "--years", f"{args.minutes_years:g}", "--workers", "8",
               "--assets", ",".join(minute_assets)]
        out.append((f"fetch 1m candles from Coinbase for {len(minute_assets)} coins (up to {args.minutes_years:g} years)", cmd))
    if alt_assets and args.minutes_years > 0:
        out.append((f"fetch 1m candles from OKX/KuCoin/Bitget/WhiteBIT for {', '.join(alt_assets)}", [
            py, "-m", "backtester.core.fetch_minutes_alt", "--assets", ",".join(alt_assets),
            "--years", f"{args.minutes_years:g}"]))
    for a in minute_assets:
        if args.days_5m <= 0:
            break
        out.append((f"fetch {a} 5m candles since {start_5m}", [
            py, "-m", "backtester.core.fetch", "--asset", a, "--interval", "5m", "--start", start_5m,
            "--allow-gaps", "--out", str(data / f"{a}_5m.csv")]))
    out.append(("fetch Hyperliquid hourly funding", [
        py, "-m", "backtester.core.funding", "--assets", ",".join(assets), "--out-dir", str(data), "--refetch"]))
    return out


def sweep_steps(assets: list[str], data: Path, args: argparse.Namespace, *,
                planning: bool = False) -> list[tuple[str, list[str]]]:
    """(description, argv) for the two sweeps, over assets that actually have data.

    Built AFTER the fetch, from what is on disk, so an asset the venue does not list becomes a
    printed skip instead of a failing worker.
    """
    if args.fetch_only:
        return []
    py = sys.executable
    out: list[tuple[str, list[str]]] = []
    if not args.no_registry:
        for a in assets:
            if not planning and not (data / f"{a}_1d.csv").exists():
                print(f"  skip registry sweep {a}: no {a}_1d.csv in the cache", flush=True)
                continue
            out.append((f"registry sweep {a} (every card, horizon and tier)", [
                py, "-m", "soltui.bgworker", "--asset", a, "--max-tier", str(args.max_tier)]))
    if not args.no_compound:
        out.append(("compound 5m sweep (every metric, variation and asset with 5m data)", [
            py, "-m", "soltui.compound", "sweep", "--assets", ",".join(assets), "--perturb",
            "--aggregate-grid", "--workers", str(args.workers)]))
    return out


def listed_only(assets: list[str]) -> list[str]:
    """Drop assets Coinbase does not list, with a note. Keeps all of them if the check fails."""
    from backtester.core.universe import list_coinbase_products

    try:
        listed = {p.split("-")[0] for p in list_coinbase_products() if p.endswith("-USD")}
    except Exception as exc:  # noqa: BLE001 - a failed listing check must not stop the run
        print(f"  could not check Coinbase listings ({exc}); trying every asset", flush=True)
        return assets
    for a in assets:
        if a not in listed:
            print(f"  skip {a}: not listed on Coinbase (no candles to fetch)", flush=True)
    return [a for a in assets if a in listed]


def archive_registry_results(stamp: str) -> Path | None:
    """Move results.jsonl and its proof aside so the worker can bind fresh proof."""
    from soltui import bgcontrol, bgqueue

    if bgcontrol.is_running():
        raise SystemExit("a background sweep is running; stop it (Queue tab -> Stop) and re-run")
    files = [bgqueue.RESULTS_PATH, bgqueue.RESULTS_PATH.with_name(bgqueue.RESULTS_PATH.name + ".proof.json")]
    present = [f for f in files if f.exists()]
    if not present:
        return None
    dest = bgqueue.BG_DIR / "archive" / stamp
    dest.mkdir(parents=True, exist_ok=True)
    for f in present:
        shutil.move(str(f), str(dest / f.name))
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assets", default="",
                    help="comma list (default: the top 50 non-pegged coins in the dated record)")
    ap.add_argument("--days-5m", type=int, default=0,
                    help="also fetch N days of native 5m candles (default 0: the 1m history covers it)")
    ap.add_argument("--minutes-years", type=float, default=7.0,
                    help="years of 1-minute candles to fetch, capped by each coin's listing (default 7)")
    ap.add_argument("--start-1h", default="2023-01-01", help="first date of hourly candles")
    ap.add_argument("--max-tier", type=int, default=2, help="registry perturbation tiers (0-2)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2),
                    help="processes for the compound sweep")
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--fetch-only", action="store_true")
    ap.add_argument("--no-registry", action="store_true", help="skip the registry sweep")
    ap.add_argument("--no-compound", action="store_true", help="skip the compound 5m sweep")
    ap.add_argument("--keep-results", action="store_true", help="do not archive registry results after a fetch")
    ap.add_argument("--continue-on-fetch-error", action="store_true",
                    help="run the sweeps even if a fetch step failed (default: stop before them)")
    ap.add_argument("--plan", action="store_true", help="print the steps and exit")
    args = ap.parse_args(argv)
    if args.skip_fetch and args.fetch_only:
        ap.error("--skip-fetch and --fetch-only contradict each other")
    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    if not assets:
        listed, others = top50()
        assets = listed + others
    data = resolve_data_dir()
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    if args.plan:
        plan = fetch_steps(assets, data, args) + sweep_steps(assets, data, args, planning=True)
        print(f"full suite plan: {len(plan)} steps, data cache {data} "
              "(unlisted assets and assets without data are skipped at run time)")
        for i, (what, cmd) in enumerate(plan, 1):
            print(f"  {i:>2}. {what}\n      {' '.join(cmd)}")
        return 0
    env = {**os.environ, "PYTHONPATH": str(REPO) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    failures: list[str] = []

    def run(phase: list[tuple[str, list[str]]]) -> None:
        for i, (what, cmd) in enumerate(phase, 1):
            print(f"\n[{i}/{len(phase)}] {what}\n  {' '.join(cmd)}", flush=True)
            t0 = time.time()
            # fetch_minutes writes data/ relative to its working directory: run it where data/ lives.
            where = data.parent if any(m in cmd for m in ("backtester.core.fetch_minutes",
                                                          "backtester.core.fetch_minutes_alt")) else REPO
            code = subprocess.run(cmd, cwd=where, env=env).returncode  # noqa: S603 - fixed argv
            print(f"[{i}/{len(phase)}] exit {code} after {time.time() - t0:.0f}s", flush=True)
            if code != 0:
                failures.append(f"{what} (exit {code})")

    print(f"full suite {stamp}; data cache {data}", flush=True)
    if not args.skip_fetch:
        from backtester.core.fetch_minutes_alt import ASSET_VENUE

        # Coins from other venues are fetched by fetch_minutes_alt; only the rest need Coinbase.
        assets = listed_only([a for a in assets if a not in ASSET_VENUE]) + [a for a in assets if a in ASSET_VENUE]
        run(fetch_steps(assets, data, args))
        if failures and not args.continue_on_fetch_error:
            # Sweeping a partly refreshed cache mixes old and new data and would archive the
            # previous registry results for nothing. Stop here instead.
            print("\nA fetch step failed; stopping before the sweeps (nothing archived):")
            for f in failures:
                print(f"  - {f}")
            print("Fix it and re-run, or pass --continue-on-fetch-error.")
            return 1
    sweeps = sweep_steps(assets, data, args)
    if any(cmd[2] == "soltui.bgworker" for _, cmd in sweeps) and not args.skip_fetch and not args.keep_results:
        dest = archive_registry_results(stamp)
        if dest:
            print(f"archived previous registry results to {dest}", flush=True)
    run(sweeps)
    print("\nDone." if not failures else "\nFinished with failures:")
    for f in failures:
        print(f"  - {f}")
    print("View results: soltui -> Strategies / Queue tabs (registry), Compound 5m tab (5m compound),\n"
          "or: python3 -m soltui.compound status --asset SOL")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

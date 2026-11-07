"""Pull fresh data, then run every backtest: all coins, all strategies, all configurations.

    python3 research/full_suite.py --plan          # print every step; touches nothing
    python3 research/full_suite.py                 # fetch, then both sweeps (hours)
    python3 research/full_suite.py --skip-fetch    # re-run the sweeps on the cache you have
    python3 research/full_suite.py --fetch-only    # refresh the cache and stop

Run it with the soltui interpreter (it has numpy/pandas/Textual):

    /Users/mitch/.venvs/soltui/bin/python research/full_suite.py

## What "full" means here, and its size

1. **Fetch** (the only network step, explicit as CLAUDE.md requires): daily and hourly candles
   for the tradeable universe (`backtester.core.universe`), 5m candles for the last
   `--days-5m` days per asset (`backtester.core.fetch`), and Hyperliquid hourly funding
   (`backtester.core.funding`). Written to the main checkout's `data/` cache, never a worktree.
2. **Registry sweep**: `soltui.bgworker` per asset -- every strategy card, every horizon,
   perturbation tiers 0-2 (about 1,060 CPCV jobs per asset). Results land in the file the
   Strategies and Queue tabs read.
3. **Compound sweep**: `soltui.compound sweep --perturb --aggregate-grid` -- the saved
   five-minute compound, each metric alone, one-at-a-time parameter variations and the
   threshold/gate/regime/leverage grid (about 280 configurations per asset). Results land in
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
from backtester.core.universe import EXCLUDED, TOP10_NON_PEGGED  # noqa: E402

DEFAULT_ASSETS = tuple(a for a in TOP10_NON_PEGGED if a not in EXCLUDED)


def fetch_steps(assets: list[str], data: Path, args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    """(description, argv) for the network step."""
    if args.skip_fetch:
        return []
    py = sys.executable
    start_5m = (datetime.now(timezone.utc).date() - timedelta(days=args.days_5m)).isoformat()
    joined = ",".join(assets)
    out: list[tuple[str, list[str]]] = []
    for interval, start in (("1d", "2021-01-01"), ("1h", args.start_1h)):
        out.append((f"fetch {interval} candles", [
            py, "-m", "backtester.core.universe", "--assets", joined, "--interval", interval,
            "--start", start, "--out-dir", str(data), "--refetch", "--allow-partial", "--allow-gaps"]))
    for a in assets:
        out.append((f"fetch {a} 5m candles since {start_5m}", [
            py, "-m", "backtester.core.fetch", "--asset", a, "--interval", "5m", "--start", start_5m,
            "--allow-gaps", "--out", str(data / f"{a}_5m.csv")]))
    out.append(("fetch Hyperliquid hourly funding", [
        py, "-m", "backtester.core.funding", "--assets", joined, "--out-dir", str(data), "--refetch"]))
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
    ap.add_argument("--assets", default=",".join(DEFAULT_ASSETS),
                    help="comma list (default: the tradeable universe; unlisted ones are reported)")
    ap.add_argument("--days-5m", type=int, default=365, help="days of 5m history per asset (default 365)")
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
            code = subprocess.run(cmd, cwd=REPO, env=env).returncode  # noqa: S603 - fixed argv
            print(f"[{i}/{len(phase)}] exit {code} after {time.time() - t0:.0f}s", flush=True)
            if code != 0:
                failures.append(f"{what} (exit {code})")

    print(f"full suite {stamp}; data cache {data}", flush=True)
    if not args.skip_fetch:
        assets = listed_only(assets)
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

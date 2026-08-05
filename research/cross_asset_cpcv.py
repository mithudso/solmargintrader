"""Cross-asset CPCV: run the registered strategy set, unchanged, on another coin.

    python3 research/cross_asset_cpcv.py --self-test
    python3 research/cross_asset_cpcv.py --assets DOGE,ZEC
    python3 research/cross_asset_cpcv.py --assets DOGE,ZEC --horizon long
    python3 research/cross_asset_cpcv.py --top5 --assets DOGE,ZEC --skip-self-test

The last line is the second gate and is easy to miss, because `--help` shows only
this docstring's first line: `--top5` evaluates the five configurations of
`TOP5-RECOMMENDATION.md` instead of the 25 singles, and prepends SOL as a control
whose published medians it must reproduce. `--skip-self-test` drops the BTC/ETH
gate, `--no-control` drops the SOL control row, and `--out` names the output CSV
(a bare filename, written into `research/results/`).

Why this exists, and why it is a script rather than a notebook cell: the file
`research/results/cpcv_all25_btc_eth_1d.csv` is quoted in `TOP5-RECOMMENDATION.md`
and in two coin-intelligence spokes, but nothing in the repo re-derives it. A
number that cannot be regenerated is indistinguishable from a typo, so this
module first reproduces that file (`--self-test`) and only then extends the same
procedure to new assets.

**The parameters are not refitted.** Every configuration uses the SOL-tuned
parameters from `research/sweep.py`'s `HORIZONS`, deliberately. Refitting per
asset would answer "can this mechanism be made to fit DOGE", which — at a
measured PBO of 0.700 — is a question the search cannot answer honestly. Holding
the parameters fixed answers the narrower question this project actually needs:
*do the parameters chosen on SOL transfer?* A poor DOGE number is therefore
evidence about the parameters, **not** about DOGE.

Two confounds are reported rather than corrected, because correcting them would
require choices less defensible than disclosing them:

1. **The calendar windows differ.** SOL/BTC/ETH span 2021-06-17.., DOGE
   2021-06-03.., ZEC 2021-01-01.. — so block *i* is not the same period across
   assets, and asset is confounded with period. Aligning windows would discard
   real history and *still* leave the regimes unmatched.
2. **Usable blocks differ.** Warm-up consumes leading bars, so a slow
   configuration can lose a block and drop from 28 paths to 21. Fewer usable
   blocks is an evidence-floor problem (see the S3 pass of `/dso`), and the
   per-row counts are written to the CSV so no reader has to assume 28.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import cpcv_evaluate  # noqa: E402
from backtester.core.data import CsvLoader, frame_to_arrays  # noqa: E402
from backtester.core.engine import EngineConfig  # noqa: E402
from backtester.core.strategies import build, build_composite  # noqa: E402
from backtester.core.types import CostConfig  # noqa: E402
from research.sweep import HORIZONS  # noqa: E402

OUT = REPO / "research" / "results"

# The file this script must reproduce before its new rows can be trusted.
REFERENCE = OUT / "cpcv_all25_btc_eth_1d.csv"
REFERENCE_ASSETS = ("BTC", "ETH")

# The horizon the reference file was produced at. The gate is pinned to it rather
# than to `--horizon`, because the reference is one fixed file: run at `long` the
# same procedure legitimately disagrees with it by ~138 trades, so threading the
# operator's horizon through the gate turned every non-default horizon into a
# refusal and taught the operator to reach for --skip-self-test. What the gate
# certifies is the harness, which is horizon-independent.
REFERENCE_HORIZON = "medium"

# Columns, in the order the reference file already uses. Matching it exactly is
# what makes the self-test a comparison rather than an interpretation.
COLUMNS = [
    "asset",
    "strategy",
    "n_paths",
    "usable_blocks",
    "median_sharpe",
    "q1_sharpe",
    "q3_sharpe",
    "frac_paths_positive",
    "median_return",
    "total_trades",
]

# Tolerance for the self-test. Floating-point re-derivation through pandas and
# numpy is not bit-identical across versions; 1e-6 is far tighter than any
# difference that would change a conclusion, and loose enough not to fail on
# library drift.
TOLERANCE = 1e-6

# Tolerance for the SOL control in --top5 mode, four orders of magnitude looser
# than TOLERANCE for a reason: the control compares against the `sol_median`
# literals below, which TOP5-RECOMMENDATION.md quotes to three decimals, so
# rounding alone can contribute 5e-4. 0.01 leaves room for that and no room for
# a composite wired to the wrong member or a horizon's parameters having moved.
CONTROL_TOLERANCE = 0.01

# The cost and capital model. Named rather than inlined because these four values
# are what make a reproduction a reproduction: research/sweep.py builds the
# identical EngineConfig, and a one-sided edit to either copy would move the SOL
# control's medians away from the `sol_median` literals below with nothing in
# either file failing.
FILL_DELAY = 1
INITIAL_CAPITAL = 10_000.0
FEE_BPS = 6.0
SLIPPAGE_BPS = 2.0

# The five configurations of research/TOP5-RECOMMENDATION.md, with the SOL median
# path Sharpe that document reports. Three are composites and four are long
# horizon, so a singles-only medium-horizon sweep does not test them -- which is
# the reason this block exists rather than reusing the sweep above.
#
# `sol_median` is carried into the output so the transfer comparison is readable
# in the row itself, and so running --top5 on SOL alone re-derives a published
# number and thereby checks the composite wiring.
TOP5: tuple[dict, ...] = (
    {"rank": 1, "label": "all(dual_momentum+vol_regime)", "horizon": "long",
     "members": ("dual_momentum", "vol_regime"), "mode": "all", "sol_median": 1.345},
    {"rank": 2, "label": "any(hurst_switch+ou_reversion)", "horizon": "medium",
     "members": ("hurst_switch", "ou_reversion"), "mode": "any", "sol_median": 1.290},
    {"rank": 3, "label": "any(ou_reversion+obv_trend)", "horizon": "long",
     "members": ("ou_reversion", "obv_trend"), "mode": "any", "sol_median": 1.054},
    {"rank": 4, "label": "obv_trend_60", "horizon": "long",
     "members": ("obv_trend",), "mode": "all", "sol_median": 0.774},
    {"rank": 5, "label": "vol_regime_60_0.5", "horizon": "long",
     "members": ("vol_regime",), "mode": "all", "sol_median": 0.696},
)

TOP5_COLUMNS = [
    "asset", "rank", "label", "horizon", "sol_median_sharpe", "median_sharpe",
    "delta_vs_sol", "q1_sharpe", "q3_sharpe", "frac_paths_positive",
    "median_return", "total_trades", "n_paths", "usable_blocks",
]


def resolve_output_path(name: str) -> Path | None:
    """Resolve a CSV filename inside OUT, or return None if it must be refused.

    Two refusals, and both have to happen *before* any compute rather than after
    it, which is why this is a pure function called early rather than a check at
    the write site:

    1. **The reference file.** Regenerating it from this script would replace the
       only independent record of the numbers the script exists to check, so the
       gate would then pass against its own output. `--assets BTC,ETH` at the
       reference horizon derives exactly that filename, so this is reachable
       without anyone typing `--out`.
    2. **Anything outside OUT.** `--out` is joined onto a directory, and an
       absolute path or a `..` segment silently wins that join: `--out
       ../../data/SOL_1d.csv` landed on a price file that `.gitignore` excludes,
       i.e. an unrecoverable overwrite of an input every published number depends
       on. Only a bare filename is accepted.
    """
    if name != Path(name).name or not name:
        print(f"REFUSED: --out must be a bare filename inside research/results (got {name!r}).")
        return None
    dest = (OUT / name).resolve()
    if dest == REFERENCE.resolve():
        print(f"REFUSED: {name} is the reference file. Choose another --out.")
        return None
    if dest.parent != OUT.resolve():
        print(f"REFUSED: {name} resolves outside research/results ({dest}).")
        return None
    OUT.mkdir(parents=True, exist_ok=True)
    return dest


def missing_data_files(assets: list[str], horizons: list[str]) -> list[str]:
    """Which required price files are absent, checked before any compute.

    Without this, a typo'd or unfetched asset raises FileNotFoundError partway
    through the loop, and every asset already computed is discarded unwritten —
    the operator pays for the run and gets a traceback instead of the rows.
    """
    wanted = {
        REPO / "data" / f"{asset}_{HORIZONS[h]['interval']}.csv"
        for asset in assets
        for h in horizons
    }
    return sorted(str(p.relative_to(REPO)) for p in wanted if not p.exists())


def load_asset(asset: str, horizon: str) -> tuple[dict, EngineConfig, str]:
    """Load one asset's series at the horizon's interval and gap policy.

    The cost model is this module's (FEE_BPS/SLIPPAGE_BPS), not the horizon's —
    HORIZONS carries no costs. The path is derived from the interval rather than
    read from `spec["data"]`, which names SOL specifically; for SOL the two agree.

    Returns the arrays, the engine config, and a human-readable date window. The
    window is returned rather than logged so the caller can put it in the report
    — the windows differ per asset and that is a confound a reader must see.
    """
    spec = HORIZONS[horizon]
    interval = spec["interval"]
    path = REPO / "data" / f"{asset}_{interval}.csv"
    loader = CsvLoader(path, allow_gaps=spec["allow_gaps"])
    df = loader.load(asset, None, None, interval)
    ts = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    window = f"{len(df)} bars, {ts.iloc[0].date()}..{ts.iloc[-1].date()}"
    cfg = EngineConfig(
        interval=interval,
        fill_delay=FILL_DELAY,
        initial_capital=INITIAL_CAPITAL,
        costs=CostConfig(fee_bps=FEE_BPS, slippage_bps=SLIPPAGE_BPS),
    )
    return frame_to_arrays(df), cfg, window


def run_asset(
    asset: str, horizon: str, groups: int, k: int, verbose: bool = True
) -> tuple[list[dict], str]:
    """Evaluate every registered single strategy on one asset."""
    arrays, cfg, window = load_asset(asset, horizon)
    params = HORIZONS[horizon]["params"]
    rows: list[dict] = []

    for name, p in sorted(params.items()):
        res = cpcv_evaluate(
            name,
            lambda n=name, q=p: build(n, **q),
            arrays,
            cfg,
            n_groups=groups,
            k_test=k,
        )
        # Insufficient configurations are written with their real (zero) path
        # count rather than skipped: a missing row reads as "not tested", which
        # is a different and less useful fact than "tested, refused to report".
        rows.append(
            {
                "asset": asset,
                "strategy": name,
                "n_paths": res.n_paths,
                "usable_blocks": res.usable_blocks,
                "median_sharpe": res.median_sharpe,
                "q1_sharpe": res.q1_sharpe,
                "q3_sharpe": res.q3_sharpe,
                "frac_paths_positive": res.frac_positive,
                "median_return": res.median_return,
                "total_trades": res.total_trades,
            }
        )
        if verbose:
            flag = "  DROPPED" if res.insufficient else ""
            print(
                f"  {asset:5s} {name:18s} paths={res.n_paths:3d} "
                f"blocks={res.usable_blocks} median={res.median_sharpe:+.3f} "
                f"pos={res.frac_positive * 100:3.0f}% "
                f"ret={res.median_return * 100:+7.2f}% "
                f"trades={res.total_trades:5d}{flag}"
            )
    return rows, window


def make_top5_strategy(cfg_spec: dict) -> Callable[[], object]:
    """Build one top-5 configuration as a zero-argument factory.

    The horizon is read out of `cfg_spec` rather than passed alongside it. Two
    names for one fact is how a configuration ends up built with another
    configuration's parameters, and nothing here would have failed if they had
    disagreed — the wrong-horizon parameters produce a number, not an error.

    A single-member entry is built directly rather than wrapped in a Composite:
    a one-element `all(...)` is behaviourally the same signal, but going through
    the same path as the sweep keeps the singles comparable to the singles table.
    """
    params = HORIZONS[cfg_spec["horizon"]]["params"]
    members = cfg_spec["members"]
    if len(members) == 1:
        # `params[name]` is resolved here, not in the lambda's default list:
        # defaults are evaluated in the enclosing scope, so a later default
        # cannot reference an earlier one.
        name = members[0]
        member_params = params[name]
        return lambda n=name, q=member_params: build(n, **q)
    specs = [(m, params[m]) for m in members]
    return lambda s=specs, m=cfg_spec["mode"]: build_composite(list(s), mode=m)


def run_top5(
    assets: list[str], groups: int, k: int, verbose: bool = True
) -> tuple[pd.DataFrame, dict[str, str]]:
    """Evaluate the five recommended configurations on each asset.

    Config 2 is the medium horizon and the rest are long, but `medium` and `long`
    are the same 1d series and differ only in `params`, so the cache below is
    keyed on what actually determines the load — interval and gap policy — and
    the frame is read once per asset. Keying it on the horizon instead read the
    identical file twice while a docstring claimed otherwise.
    """
    rows: list[dict] = []
    windows: dict[str, str] = {}
    for asset in assets:
        if verbose:
            print(f"{asset}:")
        cache: dict[tuple[str, bool], tuple] = {}
        for spec in TOP5:
            horizon = spec["horizon"]
            hspec = HORIZONS[horizon]
            load_key = (hspec["interval"], hspec["allow_gaps"])
            if load_key not in cache:
                cache[load_key] = load_asset(asset, horizon)
            arrays, cfg, window = cache[load_key]
            windows[asset] = window
            res = cpcv_evaluate(
                spec["label"],
                make_top5_strategy(spec),
                arrays,
                cfg,
                n_groups=groups,
                k_test=k,
            )
            delta = res.median_sharpe - spec["sol_median"]
            rows.append(
                {
                    "asset": asset,
                    "rank": spec["rank"],
                    "label": spec["label"],
                    "horizon": horizon,
                    "sol_median_sharpe": spec["sol_median"],
                    "median_sharpe": res.median_sharpe,
                    "delta_vs_sol": delta,
                    "q1_sharpe": res.q1_sharpe,
                    "q3_sharpe": res.q3_sharpe,
                    "frac_paths_positive": res.frac_positive,
                    "median_return": res.median_return,
                    "total_trades": res.total_trades,
                    "n_paths": res.n_paths,
                    "usable_blocks": res.usable_blocks,
                }
            )
            if verbose:
                flag = "  DROPPED" if res.insufficient else ""
                print(
                    f"  #{spec['rank']} {spec['label']:32s} ({horizon:6s}) "
                    f"SOL {spec['sol_median']:+.3f} -> {res.median_sharpe:+.3f} "
                    f"({delta:+.3f})  pos={res.frac_positive * 100:3.0f}% "
                    f"ret={res.median_return * 100:+7.2f}% "
                    f"trades={res.total_trades:4d} paths={res.n_paths}{flag}"
                )
    return pd.DataFrame(rows, columns=TOP5_COLUMNS), windows


def summarise(df: pd.DataFrame) -> str:
    """Per-asset headline: how many strategies cleared zero, and by how much."""
    lines = []
    for asset, g in df.groupby("asset", sort=False):
        rankable = g[g["n_paths"] > 0]
        pos = int((rankable["median_sharpe"] > 0).sum())
        made_money = int((rankable["median_return"] > 0).sum())
        lines.append(
            f"  {asset:5s} {pos:2d}/{len(rankable)} positive median Sharpe, "
            f"{made_money:2d} made money, "
            f"median return across strategies "
            f"{rankable['median_return'].median() * 100:+.2f}%, "
            f"paths {rankable['n_paths'].min()}-{rankable['n_paths'].max()}, "
            f"blocks {rankable['usable_blocks'].min()}-{rankable['usable_blocks'].max()}"
        )
    return "\n".join(lines)


def self_test(groups: int, k: int) -> int:
    """Reproduce the reference BTC/ETH file at REFERENCE_HORIZON. Never writes it.

    This is the gate on the whole script. If the same procedure cannot
    regenerate numbers already published in the repo's own documents, then any
    new asset's numbers are unverified too, and the honest response is to report
    the divergence rather than to tune until it agrees.

    Returns 0 only when the comparison ran and agreed. A gate that could not run
    returns non-zero, because the caller's test is `!= 0`: returning 0 for "no
    reference on disk" made a gate that never executed indistinguishable from one
    that passed, and the run went on to write new asset rows anyway.
    """
    if not REFERENCE.exists():
        print(f"SELF-TEST SKIPPED: no reference at {REFERENCE}")
        print("  A gate that did not run is not a gate that passed; refusing.")
        return 2

    ref = pd.read_csv(REFERENCE)
    absent = [c for c in COLUMNS if c not in ref.columns]
    if absent:
        print(f"SELF-TEST FAILED: reference is missing columns {absent}")
        print("  Its schema has drifted from COLUMNS; the comparison cannot be made.")
        return 1

    gaps = missing_data_files(list(REFERENCE_ASSETS), [REFERENCE_HORIZON])
    if gaps:
        print(f"SELF-TEST SKIPPED: no price data for the reference assets ({', '.join(gaps)})")
        print("  A gate that did not run is not a gate that passed; refusing.")
        return 2

    rows: list[dict] = []
    for asset in REFERENCE_ASSETS:
        got, window = run_asset(asset, REFERENCE_HORIZON, groups, k, verbose=False)
        rows.extend(got)
        print(f"  {asset}: {window}")
    new = pd.DataFrame(rows, columns=COLUMNS)

    key = ["asset", "strategy"]
    merged = ref.merge(new, on=key, suffixes=("_ref", "_new"), how="outer", indicator=True)
    if (merged["_merge"] != "both").any():
        odd = merged[merged["_merge"] != "both"][key + ["_merge"]]
        print(f"SELF-TEST FAILED: row sets differ\n{odd.to_string(index=False)}")
        return 1

    numeric = [c for c in COLUMNS if c not in key]

    # Null-ness is compared before any subtraction, because a NaN difference
    # compares False against every threshold: a column that went from a number to
    # NaN leaves `worst` untouched and prints PASSED. That is reachable, not
    # hypothetical -- run_asset deliberately writes insufficient configurations
    # with NaN metrics, so this is the divergence the gate would most likely be
    # asked to catch.
    flipped = [
        c for c in numeric
        if not merged[f"{c}_ref"].isna().equals(merged[f"{c}_new"].isna())
    ]
    if flipped:
        print(f"SELF-TEST FAILED: {', '.join(flipped)} changed between a value and NaN")
        print("  The reference file was NOT overwritten. Investigate before trusting new rows.")
        return 1

    worst = 0.0
    worst_at = ""
    for c in numeric:
        diff = (merged[f"{c}_ref"] - merged[f"{c}_new"]).abs()
        largest = float(diff.max()) if diff.notna().any() else 0.0
        if largest > worst:
            worst = largest
            worst_at = f"{c} on {merged.loc[diff.idxmax(), 'asset']}/{merged.loc[diff.idxmax(), 'strategy']}"

    if worst > TOLERANCE:
        print(f"SELF-TEST FAILED: max abs diff {worst:.3e} ({worst_at}) > {TOLERANCE:.0e}")
        print("  The reference file was NOT overwritten. Investigate before trusting new rows.")
        return 1

    print(f"SELF-TEST PASSED: {len(ref)} rows reproduced, max abs diff {worst:.3e}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--assets", default="DOGE,ZEC", help="comma-separated, e.g. DOGE,ZEC")
    ap.add_argument("--horizon", default="medium", choices=list(HORIZONS))
    ap.add_argument("--groups", type=int, default=8, help="number of CPCV blocks")
    ap.add_argument("--k", type=int, default=2, help="blocks per test path")
    ap.add_argument("--self-test", action="store_true", help="reproduce the BTC/ETH reference and exit")
    ap.add_argument(
        "--top5",
        action="store_true",
        help="evaluate the five TOP5-RECOMMENDATION configurations instead of all 25 singles "
        "(includes SOL as a control unless --no-control)",
    )
    ap.add_argument("--no-control", action="store_true", help="omit the SOL control row from --top5")
    ap.add_argument("--out", default=None, help="output CSV name (default derived from assets)")
    ap.add_argument("--skip-self-test", action="store_true", help="run new assets without the gate")
    args = ap.parse_args(argv)

    # Validated before anything is printed or computed. --groups below 2 makes
    # make_groups raise, which cpcv_evaluate turns into zero-path rows, so the run
    # would write a CSV of zeros and report success; --k 0 reaches np.concatenate
    # with no arrays and dies on a traceback several frames away from the flag
    # that caused it. k == 1 is legitimate (single-block paths).
    if args.groups < 2:
        print(f"REFUSED: --groups must be >= 2 (got {args.groups}).")
        return 1
    if not 1 <= args.k < args.groups:
        print(f"REFUSED: --k must be >= 1 and < --groups (got k={args.k}, groups={args.groups}).")
        return 1
    # Checked here rather than at the write site so a bad name costs nothing: the
    # old placement burned the whole sweep before printing REFUSED.
    if args.out is not None and resolve_output_path(args.out) is None:
        return 1

    print(f"Horizon {args.horizon}, CPCV {args.groups} blocks, k={args.k}")
    print("Parameters are SOL-tuned and NOT refitted -- this measures transfer, not fit.\n")

    if args.self_test:
        print("Reproducing reference BTC/ETH run:")
        return self_test(args.groups, args.k)

    if not args.skip_self_test:
        print("Gate: reproducing reference BTC/ETH run first.")
        if args.horizon != REFERENCE_HORIZON:
            print(f"  (gate runs at {REFERENCE_HORIZON}, the horizon the reference was produced at)")
        if self_test(args.groups, args.k) != 0:
            print("\nRefusing to report new assets on an unreproducible harness.")
            print("Pass --skip-self-test to override deliberately.")
            return 1
        print()

    assets = [a.strip().upper() for a in args.assets.split(",") if a.strip()]
    if not assets:
        print(f"REFUSED: --assets named no assets (got {args.assets!r}).")
        return 1

    if args.top5:
        # SOL first and by default: reproducing its published medians is what
        # certifies the composite wiring, so a divergent control invalidates the
        # other assets' rows rather than merely being interesting.
        control = [] if args.no_control else ["SOL"]
        ordered = control + [a for a in assets if a != "SOL"]
        if not ordered:
            print("REFUSED: --no-control with only SOL requested leaves nothing to evaluate.")
            return 1
        # Resolved before the sweep, and before the cheaper data check, because
        # this is the destructive one: the branch used to write with no reference
        # check at all, so --top5 --out cpcv_all25_btc_eth_1d.csv replaced the
        # reference with 14-column data and left the gate permanently unrunnable.
        dest = resolve_output_path(
            args.out or f"cpcv_top5_{'_'.join(a.lower() for a in ordered)}_1d.csv"
        )
        if dest is None:
            return 1
        gaps = missing_data_files(ordered, sorted({s["horizon"] for s in TOP5}))
        if gaps:
            print(f"REFUSED: missing price data ({', '.join(gaps)}). Fetch it first.")
            return 1
        df, windows = run_top5(ordered, args.groups, args.k)
        df.to_csv(dest, index=False)

        print("\nDate windows (block i is NOT the same period across assets):")
        for asset, window in windows.items():
            print(f"  {asset:5s} {window}")

        diverged = False
        if not args.no_control:
            sol = df[df["asset"] == "SOL"]
            deltas = sol["delta_vs_sol"]
            # A partial control is not a passing control. `.abs().max()` skips NaN,
            # so four insufficient configurations and one agreeing one printed
            # PASSED on a fifth of the evidence.
            incomplete = len(sol) != len(TOP5) or bool(deltas.isna().any())
            worst = float(deltas.abs().max()) if deltas.notna().any() else float("nan")
            diverged = incomplete or not worst < CONTROL_TOLERANCE
            verdict = "DIVERGED" if diverged else "PASSED"
            print(
                f"\nCONTROL {verdict}: SOL reproduces its published medians to "
                f"max abs delta {worst:.4f}."
            )
            if incomplete:
                print(
                    f"  Only {int(deltas.notna().sum())} of {len(TOP5)} control configurations "
                    f"produced a delta; the rest were insufficient or missing."
                )
            if diverged:
                print("  Composite wiring or horizon params differ from the published run.")
                print("  Treat the other assets' rows as unverified until this is resolved.")

        print("\nTransfer summary (median Sharpe, SOL -> asset):")
        for asset, g in df.groupby("asset", sort=False):
            if asset == "SOL":
                continue
            # Zero-path configurations are excluded from both halves of the ratio,
            # matching summarise(). Counting them in the denominator only reported
            # "tested and failed to clear zero" for something that was never
            # testable -- the distinction run_asset's own comment turns on.
            rankable = g[g["n_paths"] > 0]
            held = int((rankable["median_sharpe"] > 0).sum())
            money = int((rankable["median_return"] > 0).sum())
            dropped = len(g) - len(rankable)
            note = f", {dropped} insufficient" if dropped else ""
            print(
                f"  {asset:5s} {held}/{len(rankable)} still positive, "
                f"{money}/{len(rankable)} still made money, "
                f"median delta {rankable['delta_vs_sol'].median():+.3f}{note}"
            )
        print(f"\nWrote {len(df)} rows to {dest.relative_to(REPO)}")
        # Non-zero on DIVERGED: CROSS-ASSET-TRANSFER.md treats this as one of two
        # gates, and an exit code of 0 made it one no script could check.
        return 1 if diverged else 0

    slug = args.out or f"cpcv_all25_{'_'.join(a.lower() for a in assets)}_{HORIZONS[args.horizon]['interval']}.csv"
    dest = resolve_output_path(slug)
    if dest is None:
        return 1
    gaps = missing_data_files(assets, [args.horizon])
    if gaps:
        print(f"REFUSED: missing price data ({', '.join(gaps)}). Fetch it first.")
        return 1

    rows: list[dict] = []
    windows: dict[str, str] = {}
    for asset in assets:
        print(f"{asset}:")
        got, window = run_asset(asset, args.horizon, args.groups, args.k)
        rows.extend(got)
        windows[asset] = window

    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(dest, index=False)

    print("\nDate windows (block i is NOT the same period across assets):")
    for asset, window in windows.items():
        print(f"  {asset:5s} {window}")
    print("\nPer-asset summary:")
    print(summarise(df))
    print(f"\nWrote {len(df)} rows to {dest.relative_to(REPO)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

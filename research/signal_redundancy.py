"""Measure how many independent bets the strategy registry actually contains.

    python3 research/signal_redundancy.py                          # SOL, medium
    python3 research/signal_redundancy.py --horizon short          # SOL hourly, slower
    python3 research/signal_redundancy.py --asset BTC --out auto   # BTC, canonical name
    python3 research/signal_redundancy.py --top 25                 # longer pair list

Why this script exists. `core.strategies.FAMILY` **asserts** a taxonomy --
"trend", "mean-reversion", "oscillator-reversion", "breakout" -- and
`sweep.py` builds pairs that are "cross-family by construction" on the strength
of those labels. A label is not a measurement. Two strategies sitting in
different asserted families can hold the same position on almost every bar, and
when they do, a "cross-family" pair is one bet counted twice while the sweep
reports it as diversification.

So this measures it. Each registered strategy is stepped over the same bars,
its target-exposure vector recorded, and the cohort reported three ways:
pairwise correlation, agreement rate, and the number of principal components
needed to span 90% of the variance -- the effective number of independent bets.

The first two are computed on **different transforms and are not two views of
one number.** Correlation is Pearson on the continuous exposure, so it is
scale-invariant: a sleeve holding 3% of a position and one holding 100% of the
same position correlate 1.00. Agreement is computed on `sign(exposure)` -- the
discrete long/flat/short state -- so it ignores size entirely. A pair showing
0.95 correlation AND 1.00 agreement therefore means "same entries and exits,
different position size", which is exactly the case worth catching.

Four design rules, each guarding a specific way this measurement can lie:

  * **The walk starts at bar 0, always.** Several strategies are stateful (a
    `_holding` flag derived from past decisions). Their exposure at bar k
    depends on every bar before k, so the walk cannot be started at the burn-in
    boundary -- doing so would fabricate an entry state. Burn-in is removed
    after the walk, never by shortening it.
  * **One common burn-in for the whole cohort.** Comparing strategy A over bars
    where its own indicator had not yet converged measures seed artifacts, not
    signal, and recursive smoothers converge rather than becoming exact. The
    cutoff is `max(warmup_bars())` across every strategy measured, so all
    columns describe the same bars.
  * **Agreement is reported twice, and only one of them is worth reading.**
    These strategies are long-only and flat much of the time, so the raw
    agreement rate is dominated by *joint flatness*: two strategies that never
    trade agree on 100% of bars and are not thereby redundant. `agree_active`
    restricts to bars where at least one of the pair holds a position.
  * **Constant columns are named, not silently dropped.** A strategy that never
    opens a position on this series carries no information about redundancy and
    cannot be standardised for PCA (its standard deviation is zero). It is
    excluded from the spectrum and listed explicitly, because "excluded" and
    "independent" are opposite conclusions and a silent drop confuses them.

What this does NOT measure. Redundancy is not performance -- two strategies can
be 0.95 correlated and one still be the better of the two. This script says how
many bets you hold, not whether any of them is any good. It also says nothing
about *why* two families co-move; the reference framing is that most technical
indicators are algebraic transforms of the same close series, so agreement
between them is arithmetic rather than evidence.

Scope caveat, stated because it changes what may be concluded. Structural
redundancy (two rules reading the same transform) reproduces on any series. The
specific magnitudes below are properties of THIS instrument over THIS window and
must be re-measured before being quoted anywhere else.
"""

from __future__ import annotations

import argparse
import itertools
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import CsvLoader, frame_to_arrays  # noqa: E402
from backtester.core.strategies import (  # noqa: E402
    FAMILY,
    REGISTRY,
    build,
    build_composite,
)
from backtester.core.types import BarWindow  # noqa: E402
# The shared names below are defined in sweep.py, not here, so the import stays
# one-directional -- this module already depends on that one for HORIZONS.
from research.sweep import (  # noqa: E402
    HORIZONS,
    REDUNDANT_AGREEMENT,
    REDUNDANT_CORR,
    combination_redundancy_filename,
    redundancy_filename,
)

OUT = REPO / "research" / "results"

# Variance share the retained principal components must span.
VARIANCE_TARGET = 0.90

# The registry's benchmark is a constant exposure of 1.0. It is not a signal,
# and including it would only exercise the constant-column path.
SKIP_FAMILIES = ("baseline",)


def exposure_matrix(
    arrays: dict[str, np.ndarray],
    params: dict[str, dict[str, Any]],
    *,
    skip_families: tuple[str, ...] = SKIP_FAMILIES,
    progress_every: int = 1000,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Step every registered strategy over the same bars and record exposures.

    Returns the raw exposure frame (no burn-in removed) and each strategy's
    self-declared warm-up. One instance per strategy, stepped from bar 0 in
    order, because stateful strategies derive their position from their own
    history -- see the module docstring's first design rule.
    """
    names = [n for n in REGISTRY if FAMILY.get(n) not in skip_families]
    strategies = {n: build(n, **params.get(n, {})) for n in names}
    warmups = {n: int(strategies[n].warmup_bars()) for n in names}

    n_bars = len(arrays["close"])
    columns = {n: np.full(n_bars, np.nan) for n in names}
    for i in range(n_bars):
        # Several strategies fit over a 250-bar trailing window on every bar, so
        # the hourly horizon is minutes of work. Progress goes to stderr, which
        # keeps `> report.txt` clean.
        if progress_every and i and i % progress_every == 0:
            print(f"  ... {i}/{n_bars} bars", file=sys.stderr, flush=True)
        window = BarWindow(
            arrays["ts"],
            arrays["open"],
            arrays["high"],
            arrays["low"],
            arrays["close"],
            arrays["volume"],
            i,
        )
        for name in names:
            columns[name][i] = float(strategies[name].on_bar(window))

    return pd.DataFrame(columns), warmups


def redundancy(signals: pd.DataFrame) -> dict[str, Any]:
    """Correlation, agreement and effective dimensionality of position vectors.

    Operates on the exposure vectors rather than the underlying indicator
    lines: two indicators can differ numerically while producing near-identical
    positions, and it is the positions that determine P&L. No shift is applied
    -- the engine delays every strategy's fill identically, so a common shift
    cannot change a pairwise correlation.
    """
    frame = signals.dropna()
    if frame.empty:
        raise ValueError("no bars left after dropping NaN rows")

    # One strategy returning NaN drops that row for EVERY column, so a single
    # misbehaving strategy silently shrinks the window for the whole cohort and
    # the measured bar count stops matching (total - burn_in) with no
    # explanation. Name the offenders instead.
    dropped_rows = int(len(signals) - len(frame))
    nan_columns = [c for c in signals.columns if bool(signals[c].isna().any())]

    constant = [c for c in frame.columns if float(frame[c].std(ddof=0)) == 0.0]
    live = [c for c in frame.columns if c not in constant]
    if len(live) < 2:
        raise ValueError(
            f"need >=2 varying strategies to measure redundancy, got {len(live)}"
        )
    values = frame[live]

    # sign() collapses continuous exposures (the volatility-targeted sleeves
    # hold fractional positions) onto the discrete long/flat/short state, which
    # is what "do these two agree" has to mean across mixed sizing schemes.
    state = np.sign(values)

    agree_all = pd.DataFrame(index=live, columns=live, dtype=float)
    agree_active = pd.DataFrame(index=live, columns=live, dtype=float)
    for a in live:
        for b in live:
            same = state[a] == state[b]
            agree_all.loc[a, b] = float(same.mean())
            active = (state[a] != 0) | (state[b] != 0)
            agree_active.loc[a, b] = (
                float(same[active].mean()) if bool(active.any()) else np.nan
            )

    standardised = (values - values.mean()) / values.std(ddof=0)
    eigenvalues = np.linalg.svd(standardised.to_numpy(), compute_uv=False) ** 2
    explained = eigenvalues / eigenvalues.sum()
    effective = int(np.searchsorted(np.cumsum(explained), VARIANCE_TARGET) + 1)

    return {
        "corr": values.corr(),
        "agree_all": agree_all,
        "agree_active": agree_active,
        "explained": explained,
        "effective": effective,
        "nominal": len(live),
        "constant": constant,
        "bars": len(frame),
        "dropped_rows": dropped_rows,
        "nan_columns": nan_columns,
    }


def pair_table(result: dict[str, Any]) -> pd.DataFrame:
    """One row per unordered pair, most redundant first.

    `cross_family` is the column that matters: a redundant pair whose asserted
    families differ is a case where the taxonomy in `FAMILY` promises
    diversification the data does not support.
    """
    corr, active, raw = result["corr"], result["agree_active"], result["agree_all"]
    names = list(corr.columns)
    rows = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            c = float(corr.loc[a, b])
            aa = float(active.loc[a, b])
            fam_a, fam_b = FAMILY.get(a, "?"), FAMILY.get(b, "?")
            rows.append(
                {
                    "a": a,
                    "b": b,
                    "family_a": fam_a,
                    "family_b": fam_b,
                    "cross_family": fam_a != fam_b,
                    "corr": c,
                    "agree_active": aa,
                    "agree_all": float(raw.loc[a, b]),
                    "redundant": bool(
                        c >= REDUNDANT_CORR
                        or (np.isfinite(aa) and aa >= REDUNDANT_AGREEMENT)
                    ),
                }
            )
    table = pd.DataFrame(rows)
    return table.sort_values("corr", ascending=False, ignore_index=True)


def per_strategy_table(
    signals: pd.DataFrame, warmups: dict[str, int], constant: list[str]
) -> pd.DataFrame:
    """Time in market and state changes per strategy.

    Exposure is reported because a strategy holding a position on 4% of bars
    cannot be meaningfully correlated with anything -- a near-zero correlation
    there means "never on at the same time", not "independent information".
    """
    rows = []
    for name in signals.columns:
        series = signals[name]
        state = np.sign(series)
        rows.append(
            {
                "strategy": name,
                "family": FAMILY.get(name, "?"),
                "warmup_bars": warmups.get(name, -1),
                "time_in_market": float((state != 0).mean()),
                "mean_exposure": float(series.mean()),
                "state_changes": int((state.diff().fillna(0) != 0).sum()),
                "constant": name in constant,
            }
        )
    return pd.DataFrame(rows).sort_values("strategy", ignore_index=True)


def family_verdict(pairs: pd.DataFrame) -> pd.DataFrame:
    """How often each asserted family pairing is actually redundant.

    This is the script's point: it scores `FAMILY` against the data rather than
    trusting it.
    """
    grouped = pairs.copy()
    # Built by zipping the two columns rather than apply(axis=1): a row-axis
    # apply is slow, and on a one-row frame -- a shape this legitimately sees,
    # when only two strategies vary -- its return type is pandas-version
    # sensitive.
    grouped["families"] = [
        " + ".join(sorted((a, b)))
        for a, b in zip(pairs["family_a"], pairs["family_b"])
    ]
    out = grouped.groupby("families").agg(
        pairs=("redundant", "size"),
        redundant=("redundant", "sum"),
        max_corr=("corr", "max"),
        mean_corr=("corr", "mean"),
    )
    out["redundant_share"] = out["redundant"] / out["pairs"]
    return out.sort_values("mean_corr", ascending=False).reset_index()


def twin_groups(
    names: Sequence[str], size: int, canonical: dict[str, str]
) -> list[list[tuple[str, ...]]]:
    """Combinations that the member-level rule would collapse into one.

    Grouping is by canonical key, so every group holds combinations built from
    interchangeable members -- `X+zscore` beside `X+bb_reversion`. A group of one
    has no twin and is dropped: there is nothing to measure.
    """
    grouped: dict[frozenset[str], list[tuple[str, ...]]] = {}
    for combo in itertools.combinations(names, size):
        key = frozenset(canonical.get(n, n) for n in combo)
        if len(key) < size:
            continue
        grouped.setdefault(key, []).append(combo)
    return [g for g in grouped.values() if len(g) > 1]


def combination_exposures(
    arrays: dict[str, np.ndarray],
    params: dict[str, Any],
    combos: Sequence[tuple[str, ...]],
    mode: str,
    *,
    progress_every: int = 2000,
) -> tuple[pd.DataFrame, int]:
    """Exposure vector per COMBINATION, stepped exactly like the singles walk.

    Composites are stateful for the same reason their members are, so each is
    stepped from bar 0 and the burn-in removed afterwards.
    """
    built = {c: build_composite([(n, params[n]) for n in c], mode=mode) for c in combos}
    warmup = max(int(s.warmup_bars()) for s in built.values())
    n_bars = len(arrays["close"])
    columns = {c: np.full(n_bars, np.nan) for c in combos}
    for i in range(n_bars):
        if progress_every and i and i % progress_every == 0:
            print(f"  ... {mode} {i}/{n_bars} bars", file=sys.stderr, flush=True)
        window = BarWindow(
            arrays["ts"], arrays["open"], arrays["high"],
            arrays["low"], arrays["close"], arrays["volume"], i,
        )
        for combo in combos:
            columns[combo][i] = float(built[combo].on_bar(window))
    frame = pd.DataFrame({"+".join(c): v for c, v in columns.items()})
    return frame, warmup


def combination_redundancy(
    asset: str, horizon: str, sizes: Sequence[int], modes: Sequence[str]
) -> pd.DataFrame:
    """Measure whether candidate twin COMBINATIONS are actually redundant.

    This is the correction to collapsing a redundancy class outright. Class
    membership is measured on a strategy's STANDALONE exposure: how often two
    signals hold the same position when each trades alone. A combination changes
    which bars its members are allowed to act on at all, so two signals that
    agree 85% of the time alone can disagree on exactly the bars a gate leaves
    live. Measured on SOL, `all(sma_regime+zscore)` and `all(sma_regime+bb_reversion)`
    score identically while `any(breakout+zscore)` and `any(breakout+bb_reversion)`
    differ by 42 percentage points of return and opposite signs -- from the same
    class, on the same threshold.

    So only the pairs measured redundant AS COMBINATIONS are reported here, and
    only those may be collapsed. Cost of the correction: both combinations must
    be built to decide whether to keep one, which makes the saving statistical --
    a smaller multiple-testing denominator -- rather than computational.
    """
    from research.sweep import COMBO_CANDIDATES, redundancy_classes

    arrays, params, note = load_series(asset, horizon)
    canonical, _ = redundancy_classes(horizon, asset)
    usable = [n for n in COMBO_CANDIDATES if n in params]
    rows: list[dict[str, Any]] = []

    for size in sizes:
        groups = twin_groups(usable, size, canonical)
        if not groups:
            continue
        flat = [c for g in groups for c in g]
        for mode in modes:
            print(
                f"[{horizon}] size-{size} {mode}: {len(flat)} combinations in "
                f"{len(groups)} twin groups",
                file=sys.stderr,
            )
            frame, warmup = combination_exposures(arrays, params, flat, mode)
            measured = frame.iloc[warmup:].reset_index(drop=True)
            for group in groups:
                for a, b in itertools.combinations(group, 2):
                    ka, kb = "+".join(a), "+".join(b)
                    va, vb = measured[ka], measured[kb]
                    flat = va.std(ddof=0) == 0 and vb.std(ddof=0) == 0
                    if va.std(ddof=0) == 0 or vb.std(ddof=0) == 0:
                        corr = float("nan")
                    else:
                        corr = float(va.corr(vb))
                    sa, sb = np.sign(va), np.sign(vb)
                    active = (sa != 0) | (sb != 0)
                    agree = float((sa == sb)[active].mean()) if active.any() else np.nan
                    # Correlation is undefined against a constant, but two
                    # composites that BOTH never move and hold the same value are
                    # plainly one experiment -- usually two `all(...)` triples
                    # whose members never agree. Leaving them uncollapsed would
                    # pad the search with pairs of configurations that do nothing.
                    identical_flat = bool(flat and va.equals(vb))
                    rows.append({
                        "horizon": horizon, "size": size, "mode": mode,
                        "a": f"{mode}({ka})", "b": f"{mode}({kb})",
                        "corr": corr, "agree_active": agree,
                        "both_flat": identical_flat,
                        "redundant": bool(
                            identical_flat
                            or (np.isfinite(corr) and corr >= REDUNDANT_CORR)
                            or (np.isfinite(agree) and agree >= REDUNDANT_AGREEMENT)
                        ),
                    })
    print(f"source: {note}", file=sys.stderr)
    return pd.DataFrame(rows)


def load_series(
    asset: str, horizon: str
) -> tuple[dict[str, np.ndarray], dict[str, Any], str]:
    """Price arrays, per-strategy parameters and a provenance note.

    Parameters come from `sweep.py`'s HORIZONS deliberately -- re-fitting them
    here would measure a different set of strategies than the ones whose
    performance the rest of `research/` reports.

    Two things are derived rather than read out of the horizon spec, following
    `cross_asset_cpcv.load_asset`: the path, because `spec["data"]` names SOL
    specifically, and the note, because `spec["note"]`'s bar count and date
    range describe SOL's history. Reusing that note for another asset would
    caption a BTC measurement with SOL's window -- and two assets never share a
    history window, which is a confound the reader has to see.

    Named `load_series` rather than `load_horizon` on purpose: `sweep.py`
    already exports a `load_horizon` with a different arity, and two functions
    sharing a name and a directory is a trap for whoever greps next.
    """
    spec = HORIZONS[horizon]
    interval = spec["interval"]
    loader = CsvLoader(
        REPO / "data" / f"{asset}_{interval}.csv", allow_gaps=spec["allow_gaps"]
    )
    frame = loader.load(asset, None, None, interval)
    stamps = pd.to_datetime(frame["timestamp"], unit="s", utc=True)
    note = (
        f"{len(frame):,} {interval} bars, "
        f"{stamps.iloc[0].date()}..{stamps.iloc[-1].date()}"
    )
    # Copied, not aliased: HORIZONS belongs to sweep.py, and handing a caller a
    # live reference into another module's constant means one careless mutation
    # here changes what every other research script in the process backtests.
    params = {name: dict(values) for name, values in spec["params"].items()}
    return frame_to_arrays(frame), params, note


def resolve_output_path(name: str, *, force: bool) -> Path:
    """Refuse to overwrite an existing result file unless asked twice.

    `research/results/` holds published evidence quoted in the markdown
    write-ups. A script that silently overwrites one of those files turns a
    citation into a claim about whatever was run last.
    """
    if Path(name).name != name:
        # SystemExit rather than ValueError: this is a CLI typo, and a traceback
        # is the wrong way to tell someone they wrote a path where a filename
        # belongs.
        raise SystemExit(f"--out takes a bare filename, got {name!r}")
    target = OUT / name
    if target.exists() and not force:
        raise SystemExit(
            f"refusing to overwrite {target} -- pass --force if that is intended"
        )
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--asset", default="SOL", help="ticker, e.g. SOL, BTC, ETH")
    parser.add_argument("--horizon", default="medium", choices=sorted(HORIZONS))
    parser.add_argument(
        "--top", type=int, default=15, help="rows of the redundant-pair table to print"
    )
    parser.add_argument(
        "--out",
        default=None,
        help="bare CSV filename under results/, or 'auto' for the canonical name",
    )
    parser.add_argument("--force", action="store_true", help="allow overwriting --out")
    parser.add_argument(
        "--combinations",
        action="store_true",
        help="measure twin COMBINATIONS instead of singles, and write the "
             "evidence sweep.py's gate collapses on",
    )
    args = parser.parse_args(argv)

    if args.combinations:
        table = combination_redundancy(
            args.asset, args.horizon, sizes=(2, 3), modes=("all", "any", "vote")
        )
        flagged = int(table["redundant"].sum()) if len(table) else 0
        print(f"\n=== combination redundancy: {args.asset} {args.horizon} ===")
        print(f"twin pairs measured : {len(table)}")
        print(f"measured redundant  : {flagged}")
        print(f"kept as distinct    : {len(table) - flagged}")
        if len(table):
            print("\n--- twin pairs the member-level rule would have collapsed ---")
            show = table.sort_values("corr", ascending=False)
            print(
                show[["mode", "a", "b", "corr", "agree_active", "redundant"]]
                .to_string(index=False, float_format=lambda v: f"{v:.3f}")
            )
        name = (
            combination_redundancy_filename(args.asset, args.horizon)
            if args.out in (None, "auto")
            else args.out
        )
        target = resolve_output_path(name, force=args.force)
        target.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(target, index=False)
        print(f"\nwrote {len(table)} rows to {target}")
        return 0

    arrays, params, note = load_series(args.asset, args.horizon)
    raw, warmups = exposure_matrix(arrays, params)

    burn_in = max(warmups.values())
    total_bars = len(raw)
    if burn_in >= total_bars:
        raise SystemExit(
            f"burn-in {burn_in} exceeds the {total_bars} bars available on "
            f"horizon {args.horizon!r}"
        )
    signals = raw.iloc[burn_in:].reset_index(drop=True)

    result = redundancy(signals)
    pairs = pair_table(result)
    per_strategy = per_strategy_table(signals, warmups, result["constant"])

    print(f"\n=== signal redundancy: {args.asset} {args.horizon} ===")
    print(f"source            : {note}")
    print(f"bars              : {total_bars} total, {result['bars']} measured")
    print(f"burn-in discarded : {burn_in} bars (max warmup across the cohort)")
    print(f"strategies        : {result['nominal']} varying", end="")
    if result["constant"]:
        print(f", {len(result['constant'])} constant: {', '.join(result['constant'])}")
    else:
        print()
    if result["dropped_rows"]:
        print(
            f"NaN rows dropped  : {result['dropped_rows']} "
            f"(from {', '.join(result['nan_columns'])}) -- this is why the "
            f"measured count is below total minus burn-in"
        )

    print("\n--- per strategy ---")
    print(per_strategy.to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print("\n--- effective dimensionality ---")
    print(f"nominal strategies            : {result['nominal']}")
    print(f"components for {VARIANCE_TARGET:.0%} of variance : {result['effective']}")
    shares = ", ".join(f"{v:.3f}" for v in result["explained"][:8])
    print(f"explained variance (first 8)  : [{shares}]")
    print(
        f"first component alone         : {result['explained'][0]:.1%} of variance"
    )

    print(f"\n--- most redundant pairs (top {args.top}) ---")
    print(
        pairs.head(args.top).to_string(
            index=False, float_format=lambda v: f"{v:.3f}"
        )
    )

    flagged = pairs[pairs["redundant"]]
    cross = flagged[flagged["cross_family"]]
    print(
        f"\nredundant pairs: {len(flagged)} of {len(pairs)} "
        f"(corr >= {REDUNDANT_CORR} or active agreement >= {REDUNDANT_AGREEMENT})"
    )
    print(
        f"of those, {len(cross)} are CROSS-FAMILY -- pairs the FAMILY taxonomy "
        f"treats as diversifying"
    )

    print("\n--- asserted family pairing vs measured correlation ---")
    print(
        family_verdict(pairs).to_string(
            index=False, float_format=lambda v: f"{v:.3f}"
        )
    )

    if args.out:
        name = (
            redundancy_filename(args.asset, args.horizon)
            if args.out == "auto"
            else args.out
        )
        target = resolve_output_path(name, force=args.force)
        target.parent.mkdir(parents=True, exist_ok=True)
        pairs.to_csv(target, index=False)
        print(f"\nwrote {len(pairs)} pair rows to {target}")

    print(
        "\nThresholds are reading conventions, not calibrated constants; the "
        "ordering is the claim, not the cutoff.\nMagnitudes are properties of "
        "this instrument and window -- re-measure before quoting them elsewhere."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

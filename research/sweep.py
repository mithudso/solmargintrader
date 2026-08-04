"""Reproduce every number in STRATEGIES.md and RANKED_LISTS.md.

    python3 research/sweep.py                 # everything
    python3 research/sweep.py --stage singles
    python3 research/sweep.py --horizon medium

Design rules this script exists to enforce:

  * **Rank on out-of-sample only**, always displaying in-sample beside it so the
    per-row decay is visible. Ranking on full-sample performance is the
    "liar's leaderboard" the whole exercise is meant to avoid.
  * **Count and print every configuration evaluated.** It is the denominator
    that makes a top row interpretable under multiple testing.
  * **Flag thin evidence.** A high Sharpe on 3 trades is noise, so rows below
    MIN_OOS_TRADES are listed but never ranked.
  * Pairs and triples are **cross-family by construction** -- combining two
    trend signals mostly measures the same thing twice.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.data import CsvLoader, frame_to_arrays  # noqa: E402
from backtester.core.engine import EngineConfig, run_backtest  # noqa: E402
from backtester.core.metrics import Metrics, compute_metrics  # noqa: E402
from backtester.core.strategies import (  # noqa: E402
    FAMILY,
    build,
    build_composite,
)
from backtester.core.types import CostConfig, periods_per_year  # noqa: E402

OUT_DIR = REPO / "research" / "results"

# A row needs at least this many out-of-sample trades to be ranked rather than
# merely listed. Three lucky trades can produce any Sharpe you like.
MIN_OOS_TRADES = 10

# Walk-forward in-sample fraction.
SPLIT = 0.70

# Signal parameters scaled per horizon. The SAME mechanism at a different scale
# is a different strategy and is reported separately -- that is the whole point
# of asking "short, medium, or long term".
HORIZONS: dict[str, dict[str, Any]] = {
    "short": {
        "data": "data/SOL_1h.csv",
        "interval": "1h",
        "allow_gaps": True,
        "note": "8,823 hourly bars, 2025-08-01..2026-08-04. Contains 2 disclosed gaps (largest 6h).",
        "params": {
            "buy_and_hold": {},
            "ma_crossover": {"fast": 12, "slow": 48},
            "macd": {"fast": 6, "slow": 13, "signal": 5},
            "ts_momentum": {"window": 24},
            "sma_regime": {"window": 168},
            "breakout": {"entry_lookback": 12, "exit_lookback": 6},
            "bb_breakout": {"window": 20, "num_std": 2.0},
            "keltner": {"ema_span": 12, "atr_period": 7, "mult": 2.0},
            "rsi": {"period": 7, "oversold": 30.0, "exit_level": 55.0},
            "stochastic": {"k_period": 14, "d_period": 3},
            "bb_reversion": {"window": 20, "num_std": 2.0},
            "zscore": {"window": 20, "entry_z": -2.0},
            "vwap_reversion": {"window": 20, "entry_discount": 0.01},
            "grid": {"anchor_window": 48, "levels": 4, "step": 0.03},
            "obv_trend": {"ma_window": 24},
            "voltarget": {"trend_window": 168, "vol_window": 24, "target_vol": 0.8},
            "dual_momentum": {"formation": 24, "skip": 2},
            "adx_trend": {"adx_period": 7, "adx_threshold": 25.0},
            "ma_ribbon": {"windows": 5, "base": 6},
            "ichimoku": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
            "ou_reversion": {"fit_window": 250, "entry_z": -2.0, "max_half_life_bars": 48},
            "hurst_switch": {"window": 250, "lag": 5, "trend_window": 168},
            "vol_regime": {"vol_window": 24, "lookback": 250, "trend_window": 168},
            "atr_sized": {"atr_period": 7, "trend_window": 168},
            "garch_voltarget": {"lam": 0.94, "target_vol": 0.8, "trend_window": 168},
        },
    },
    "medium": {
        "data": "data/SOL_1d.csv",
        "interval": "1d",
        "allow_gaps": False,
        "note": "1,875 daily bars, 2021-06-17..2026-08-04. Clean, passes gap validation.",
        "params": {
            "buy_and_hold": {},
            "ma_crossover": {"fast": 20, "slow": 50},
            "macd": {"fast": 12, "slow": 26, "signal": 9},
            "ts_momentum": {"window": 60},
            "sma_regime": {"window": 100},
            "breakout": {"entry_lookback": 20, "exit_lookback": 10},
            "bb_breakout": {"window": 20, "num_std": 2.0},
            "keltner": {"ema_span": 20, "atr_period": 14, "mult": 2.0},
            "rsi": {"period": 14, "oversold": 30.0, "exit_level": 50.0},
            "stochastic": {"k_period": 14, "d_period": 3},
            "bb_reversion": {"window": 20, "num_std": 2.0},
            "zscore": {"window": 20, "entry_z": -2.0},
            "vwap_reversion": {"window": 20, "entry_discount": 0.02},
            "grid": {"anchor_window": 50, "levels": 4, "step": 0.05},
            "obv_trend": {"ma_window": 20},
            "voltarget": {"trend_window": 100, "vol_window": 20, "target_vol": 0.6},
            "dual_momentum": {"formation": 12, "skip": 1},
            "adx_trend": {"adx_period": 14, "adx_threshold": 25.0},
            "ma_ribbon": {"windows": 5, "base": 10},
            "ichimoku": {"tenkan": 9, "kijun": 26, "senkou_b": 52, "displacement": 26},
            "ou_reversion": {"fit_window": 250, "entry_z": -2.0, "max_half_life_bars": 30},
            "hurst_switch": {"window": 250, "lag": 5, "trend_window": 100},
            "vol_regime": {"vol_window": 20, "lookback": 250, "trend_window": 100},
            "atr_sized": {"atr_period": 14, "trend_window": 100},
            "garch_voltarget": {"lam": 0.94, "target_vol": 0.6, "trend_window": 100},
        },
    },
    "long": {
        "data": "data/SOL_1d.csv",
        "interval": "1d",
        "allow_gaps": False,
        "note": "1,875 daily bars, 2021-06-17..2026-08-04. Slow parameter scale.",
        "params": {
            "buy_and_hold": {},
            "ma_crossover": {"fast": 50, "slow": 200},
            "macd": {"fast": 26, "slow": 52, "signal": 18},
            "ts_momentum": {"window": 200},
            "sma_regime": {"window": 200},
            "breakout": {"entry_lookback": 60, "exit_lookback": 30},
            "bb_breakout": {"window": 60, "num_std": 2.0},
            "keltner": {"ema_span": 50, "atr_period": 30, "mult": 2.0},
            "rsi": {"period": 30, "oversold": 35.0, "exit_level": 55.0},
            "stochastic": {"k_period": 40, "d_period": 5},
            "bb_reversion": {"window": 60, "num_std": 2.0},
            "zscore": {"window": 60, "entry_z": -2.0},
            "vwap_reversion": {"window": 60, "entry_discount": 0.05},
            "grid": {"anchor_window": 120, "levels": 4, "step": 0.10},
            "obv_trend": {"ma_window": 60},
            "voltarget": {"trend_window": 200, "vol_window": 60, "target_vol": 0.6},
            "dual_momentum": {"formation": 24, "skip": 1},
            "adx_trend": {"adx_period": 30, "adx_threshold": 25.0},
            "ma_ribbon": {"windows": 5, "base": 20},
            "ichimoku": {"tenkan": 18, "kijun": 52, "senkou_b": 104, "displacement": 52},
            "ou_reversion": {"fit_window": 250, "entry_z": -2.0, "hold_multiple": 3.0},
            "hurst_switch": {"window": 250, "lag": 10, "trend_window": 200},
            "vol_regime": {"vol_window": 60, "lookback": 250, "trend_window": 200},
            "atr_sized": {"atr_period": 30, "trend_window": 200},
            "garch_voltarget": {"lam": 0.97, "target_vol": 0.6, "trend_window": 200},
        },
    },
}

# Candidates offered to the pair/triple generator. Excludes buy_and_hold (it is
# the baseline, and "hold plus X" is just X with extra exposure) and voltarget
# (a sizing overlay, tested separately as a wrapper).
COMBO_CANDIDATES = (
    # trend
    "ma_crossover", "macd", "ma_ribbon", "ichimoku",
    # momentum
    "ts_momentum", "dual_momentum",
    # regime filters
    "sma_regime", "adx_trend", "hurst_switch", "vol_regime",
    # breakout
    "breakout", "bb_breakout", "keltner",
    # oscillator reversion
    "rsi", "stochastic",
    # mean reversion
    "bb_reversion", "zscore", "vwap_reversion", "ou_reversion",
    # volume flow
    "obv_trend",
)
# Risk overlays (voltarget, atr_sized, garch_voltarget) are deliberately absent:
# they change position SIZE, not direction, so a cross-family "pair" with one is
# really a wrapper test and belongs in its own experiment.


@dataclass
class Row:
    """One evaluated configuration."""

    label: str
    kind: str  # single | pair | triple
    horizon: str
    families: str
    mode: str
    full: Metrics
    in_sample: Metrics | None
    out_sample: Metrics | None
    members: list[str] = field(default_factory=list)

    @property
    def oos_sharpe(self) -> float:
        """Out-of-sample Sharpe, or -inf when unavailable (sorts last)."""
        return self.out_sample.sharpe if self.out_sample else float("-inf")

    @property
    def oos_trades(self) -> int:
        """Out-of-sample decided-trade count."""
        return self.out_sample.trade_count if self.out_sample else 0

    @property
    def rankable(self) -> bool:
        """Whether this row carries enough out-of-sample evidence to rank."""
        return self.out_sample is not None and self.oos_trades >= MIN_OOS_TRADES

    def to_dict(self) -> dict[str, Any]:
        """Flat record for CSV output."""
        rec: dict[str, Any] = {
            "label": self.label,
            "kind": self.kind,
            "horizon": self.horizon,
            "families": self.families,
            "mode": self.mode,
            "rankable": self.rankable,
        }
        for tag, m in (("full", self.full), ("is", self.in_sample), ("oos", self.out_sample)):
            if m is None:
                continue
            rec[f"{tag}_return"] = m.total_return
            rec[f"{tag}_sharpe"] = m.sharpe
            rec[f"{tag}_maxdd"] = m.max_drawdown
            rec[f"{tag}_trades"] = m.trade_count
            rec[f"{tag}_exposure"] = m.exposure_fraction
        return rec


def load_horizon(h: str) -> tuple[dict[str, np.ndarray], EngineConfig]:
    """Load the price series and engine config for a horizon."""
    spec = HORIZONS[h]
    loader = CsvLoader(REPO / spec["data"], allow_gaps=spec["allow_gaps"])
    df = loader.load("SOL", None, None, spec["interval"])
    cfg = EngineConfig(
        interval=spec["interval"],
        fill_delay=1,
        initial_capital=10_000.0,
        costs=CostConfig(fee_bps=6.0, slippage_bps=2.0),
    )
    return frame_to_arrays(df), cfg


def walk_forward(
    make_strategy, arrays: dict[str, np.ndarray], cfg: EngineConfig
) -> tuple[Metrics, Metrics | None, Metrics | None]:
    """Run full-sample, in-sample, and out-of-sample legs.

    The out-of-sample slice deliberately starts `warmup` bars BEFORE the split
    so indicators warm from trailing in-sample bars; trading therefore begins
    exactly at the split. Reading earlier history is not look-ahead, and
    starting cold would silently discard `warmup` bars of real out-of-sample
    data. Out-of-sample metrics are then computed over the post-split region
    only, so those flat warm-up bars do not dilute the Sharpe.
    """
    full = run_backtest(make_strategy(), arrays, cfg).metrics
    n = len(arrays["close"])
    k = int(n * SPLIT)
    warm = int(make_strategy().warmup_bars())

    if k <= warm + 5 or (n - k) <= warm + 5:
        return full, None, None

    is_arrays = {key: v[:k] for key, v in arrays.items()}
    is_metrics = run_backtest(make_strategy(), is_arrays, cfg).metrics

    oos_start = max(0, k - warm)
    oos_arrays = {key: v[oos_start:] for key, v in arrays.items()}
    oos_res = run_backtest(make_strategy(), oos_arrays, cfg)
    skip = k - oos_start
    trades = [t for t in oos_res.trades if t.bar_index >= skip]
    oos_metrics = compute_metrics(
        oos_res.equity[skip:],
        oos_res.timestamps[skip:],
        trades,
        oos_res.exposure[skip:],
        periods_per_year(cfg.interval),
        cfg.risk_free_rate,
        oos_res.liquidation_count,
    )
    return full, is_metrics, oos_metrics


def sweep_singles(horizon: str) -> list[Row]:
    """Every registered mechanism at this horizon's parameter scale."""
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    rows: list[Row] = []
    for name, p in params.items():
        try:
            full, ins, oos = walk_forward(lambda n=name, q=p: build(n, **q), arrays, cfg)
        except ValueError as exc:
            print(f"  skip {name}: {exc}", file=sys.stderr)
            continue
        rows.append(
            Row(
                label=build(name, **p).name,
                kind="single",
                horizon=horizon,
                families=FAMILY[name],
                mode="-",
                full=full,
                in_sample=ins,
                out_sample=oos,
                members=[name],
            )
        )
    return rows


def cross_family_combos(names: Sequence[str], size: int) -> list[tuple[str, ...]]:
    """Combinations whose members all come from different families."""
    out = []
    for combo in itertools.combinations(names, size):
        fams = {FAMILY[n] for n in combo}
        if len(fams) == size:
            out.append(combo)
    return out


def sweep_combos(
    horizon: str, size: int, modes: Iterable[str] = ("all", "any")
) -> list[Row]:
    """Cross-family combinations of `size` members, under each combine mode."""
    arrays, cfg = load_horizon(horizon)
    params = HORIZONS[horizon]["params"]
    candidates = [n for n in COMBO_CANDIDATES if n in params]
    rows: list[Row] = []
    for combo in cross_family_combos(candidates, size):
        specs = [(n, params[n]) for n in combo]
        for mode in modes:
            try:
                full, ins, oos = walk_forward(
                    lambda s=specs, m=mode: build_composite(list(s), mode=m), arrays, cfg
                )
            except ValueError:
                continue
            rows.append(
                Row(
                    label=f"{mode}({'+'.join(combo)})",
                    kind={2: "pair", 3: "triple"}.get(size, f"n{size}"),
                    horizon=horizon,
                    families="+".join(FAMILY[n] for n in combo),
                    mode=mode,
                    full=full,
                    in_sample=ins,
                    out_sample=oos,
                    members=list(combo),
                )
            )
    return rows


def fmt_table(rows: Sequence[Row], limit: int | None = None) -> str:
    """Markdown table ordered by out-of-sample Sharpe, in-sample shown beside."""
    ranked = sorted(
        [r for r in rows if r.rankable], key=lambda r: r.oos_sharpe, reverse=True
    )
    thin = [r for r in rows if not r.rankable]
    shown = ranked[:limit] if limit else ranked

    head = (
        "| # | configuration | families | OOS Sharpe | IS Sharpe | OOS return | "
        "IS return | OOS maxDD | OOS trades |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    body = ""
    for i, r in enumerate(shown, 1):
        o, s = r.out_sample, r.in_sample
        body += (
            f"| {i} | `{r.label}` | {r.families} | **{o.sharpe:.3f}** | "
            f"{s.sharpe:.3f} | {o.total_return * 100:.1f}% | "
            f"{s.total_return * 100:.1f}% | {o.max_drawdown * 100:.1f}% | "
            f"{o.trade_count} |\n"
        )
    out = head + body
    if thin:
        out += (
            f"\n_{len(thin)} configuration(s) excluded from the ranking for "
            f"fewer than {MIN_OOS_TRADES} out-of-sample trades: "
            + ", ".join(f"`{r.label}`" for r in thin[:12])
            + ("…" if len(thin) > 12 else "")
            + "._\n"
        )
    return out


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested sweep stages and write results."""
    ap = argparse.ArgumentParser(description="Strategy sweep for SOL.")
    ap.add_argument(
        "--stage",
        action="append",
        choices=["singles", "pairs", "triples"],
        default=None,
    )
    ap.add_argument("--horizon", action="append", choices=list(HORIZONS), default=None)
    ap.add_argument("--triple-top", type=int, default=6,
                    help="restrict triples to combos drawn from the top-N singles")
    args = ap.parse_args(argv)

    stages = args.stage or ["singles", "pairs", "triples"]
    horizons = args.horizon or list(HORIZONS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_rows: list[Row] = []
    counts: dict[str, int] = {}

    for h in horizons:
        if "singles" in stages:
            print(f"[{h}] singles…", file=sys.stderr)
            rows = sweep_singles(h)
            all_rows += rows
            counts[f"{h}/singles"] = len(rows)

        if "pairs" in stages:
            print(f"[{h}] pairs…", file=sys.stderr)
            rows = sweep_combos(h, 2)
            all_rows += rows
            counts[f"{h}/pairs"] = len(rows)

        if "triples" in stages:
            # Bound the triple space: cross-family triples over all candidates
            # would be hundreds of runs, and ranking that many by measured
            # performance is precisely the data-snooping this script warns about.
            singles = [r for r in all_rows if r.kind == "single" and r.horizon == h]
            top = [
                r.members[0]
                for r in sorted(
                    [r for r in singles if r.rankable],
                    key=lambda r: r.oos_sharpe,
                    reverse=True,
                )
                if r.members[0] in COMBO_CANDIDATES
            ][: args.triple_top]
            if len(top) >= 3:
                print(f"[{h}] triples from top-{len(top)} singles…", file=sys.stderr)
                arrays, cfg = load_horizon(h)
                params = HORIZONS[h]["params"]
                rows = []
                for combo in cross_family_combos(top, 3):
                    specs = [(n, params[n]) for n in combo]
                    for mode in ("all", "vote"):
                        try:
                            full, ins, oos = walk_forward(
                                lambda s=specs, m=mode: build_composite(list(s), mode=m),
                                arrays, cfg,
                            )
                        except ValueError:
                            continue
                        rows.append(Row(
                            label=f"{mode}({'+'.join(combo)})", kind="triple", horizon=h,
                            families="+".join(FAMILY[n] for n in combo), mode=mode,
                            full=full, in_sample=ins, out_sample=oos, members=list(combo),
                        ))
                all_rows += rows
                counts[f"{h}/triples"] = len(rows)

    df = pd.DataFrame([r.to_dict() for r in all_rows])
    df.to_csv(OUT_DIR / "sweep_results.csv", index=False)
    (OUT_DIR / "configuration_counts.json").write_text(
        json.dumps({**counts, "total": len(all_rows)}, indent=2, sort_keys=True) + "\n"
    )

    # Markdown fragments, one per (horizon, kind), consumed by the documents.
    frags: list[str] = []
    for h in horizons:
        for kind in ("single", "pair", "triple"):
            sub = [r for r in all_rows if r.horizon == h and r.kind == kind]
            if not sub:
                continue
            limit = None if kind == "single" else 15
            frags.append(
                f"\n### {h.upper()} horizon — {kind}s "
                f"({len(sub)} configurations evaluated)\n\n" + fmt_table(sub, limit)
            )
    (OUT_DIR / "tables.md").write_text("".join(frags))

    print(f"\nTotal configurations evaluated: {len(all_rows)}", file=sys.stderr)
    for k in sorted(counts):
        print(f"  {k}: {counts[k]}", file=sys.stderr)
    print(f"Wrote {OUT_DIR}/sweep_results.csv, tables.md, configuration_counts.json",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

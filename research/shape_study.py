"""Causal price-path geometry and unlevered spot research; never submits orders.

Run with local Coinbase USD candle files. The geometric rules are hypotheses,
not the unsupported effect sizes quoted in the earlier geometry dossier.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.data import frame_to_arrays, validate_bars
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import build
from backtester.core.types import INTERVAL_SECONDS, CostConfig
from backtester.core.zec_ensemble import component_signal_series

VERSION = 1
ASSETS = ("BTC", "ETH", "SOL", "XRP", "DOGE", "ZEC", "LINK", "AVAX")
SINGLES = ("macd", "breakout", "rsi", "bb_reversion", "ou_reversion", "adx_trend")
PAIRS = (("macd", "rsi"), ("breakout", "ou_reversion"), ("adx_trend", "bb_reversion"))
# Execution bps includes spread/slippage. These are scenarios, not venue quotes.
SCENARIOS = {
    "zero_2": (0, 2),
    "zero_10": (0, 10),
    "zero_25": (0, 25),
    "zero_50": (0, 50),
    "fee10_exec2": (10, 2),
}
SHAPES = (
    "unknown",
    "range",
    "trend_up",
    "trend_down",
    "v_rebound",
    "inverted_v",
    "bowl",
    "cap",
    "compression",
)
WINDOW = 48


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def _fit(series: np.ndarray, window: int, degree: int = 2):
    """Fixed-design trailing least squares; no centered time-series window."""
    x = np.linspace(-1, 1, window)
    design = np.vander(x, degree + 1)
    weights = np.linalg.pinv(design)
    coefficients = np.column_stack(
        [np.convolve(series, row[::-1], mode="valid") for row in weights]
    )
    sums = np.convolve(series, np.ones(window), mode="valid")
    squares = np.convolve(series * series, np.ones(window), mode="valid")
    explained = np.einsum("ij,jk,ik->i", coefficients, design.T @ design, coefficients)
    total = np.maximum(squares - sums * sums / window, 0)
    residual = np.maximum(squares - explained, 0)
    r2 = np.clip(1 - residual / np.maximum(total, 1e-12), 0, 1)
    return np.pad(
        coefficients, ((window - 1, 0), (0, 0)), constant_values=np.nan
    ), np.pad(r2, (window - 1, 0), constant_values=np.nan)


def detect_shapes(frame: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Label completed bars with observable geometry, never a future pivot.

    Position and age describe the observed window/episode. They do not estimate
    the eventual fraction of a pattern's life. Labels are ordered hypotheses.
    """
    if window < 12 or len(frame) < window:
        raise ValueError(
            "shape detector needs window >= 12 and at least one full window"
        )
    cadence = np.diff(frame.timestamp.to_numpy())
    if not np.all(cadence == cadence[0]) or cadence[0] <= 0:
        raise ValueError("shape detector requires contiguous completed bars")
    p = np.log(frame.close.to_numpy(float))
    coefficients, r2 = _fit(p, window)
    a, b, _ = coefficients.T
    hp, _ = _fit(np.log(frame.high.to_numpy(float)), window, 1)
    lp, _ = _fit(np.log(frame.low.to_numpy(float)), window, 1)
    close = frame.close.reset_index(drop=True)
    high = frame.high.reset_index(drop=True).rolling(window).max()
    low = frame.low.reset_index(drop=True).rolling(window).min()
    position = ((close - low) / (high - low).replace(0, np.nan)).fillna(0.5).clip(0, 1)
    path = pd.Series(np.abs(np.diff(p, prepend=p[0]))).rolling(window - 1).sum()
    net = pd.Series(p).diff(window - 1)
    efficiency = (net.abs() / path.replace(0, np.nan)).fillna(0).to_numpy()
    mid = window // 2
    left = pd.Series(p).shift(mid).diff(window - 1 - mid).to_numpy()
    right = pd.Series(p).diff(mid).to_numpy()
    rv = pd.Series(np.diff(p, prepend=p[0])).rolling(window).std().to_numpy()
    bend = np.abs(a) / np.maximum(rv * np.sqrt(window), 1e-12)
    vertex = -b / np.where(np.abs(2 * a) > 1e-12, 2 * a, np.nan)
    start_width = (hp[:, 1] - hp[:, 0]) - (lp[:, 1] - lp[:, 0])
    end_width = (hp[:, 1] + hp[:, 0]) - (lp[:, 1] + lp[:, 0])
    contraction = end_width / np.maximum(start_width, 1e-12)
    wedge = (
        (hp[:, 0] < 0)
        & (lp[:, 0] > 0)
        & (end_width > 0)
        & (contraction < 0.65)
        & (contraction > 0.1)
    )
    bowl = (a > 0) & (r2 >= 0.8) & (bend >= 0.15) & (vertex > -0.8) & (vertex < 0.8)
    cap = (a < 0) & (r2 >= 0.8) & (bend >= 0.15) & (vertex > -0.8) & (vertex < 0.8)
    v = (left < -2 * rv) & (right > 2 * rv) & (position.to_numpy() > 0.35)
    iv = (left > 2 * rv) & (right < -2 * rv) & (position.to_numpy() < 0.65)
    code = np.zeros(len(frame), dtype=int)
    code[efficiency < 0.25] = 1
    code[(efficiency >= 0.25) & (net.to_numpy() > 0)] = 2
    code[(efficiency >= 0.25) & (net.to_numpy() < 0)] = 3
    code[v] = 4
    code[iv] = 5
    code[bowl] = 6
    code[cap] = 7
    code[wedge] = 8
    code[: window - 1] = 0
    labels = np.asarray(SHAPES)[code]
    changes = np.r_[True, labels[1:] != labels[:-1]]
    starts = np.maximum.accumulate(np.where(changes, np.arange(len(code)), 0))
    # Linear-envelope extrapolation, in bars from now. This is not a forecast.
    convergence = hp[:, 0] - lp[:, 0]
    apex = np.divide(
        -end_width, convergence, out=np.zeros(len(code)), where=convergence < 0
    )
    apex = np.where(wedge, np.maximum(apex * (window - 1) / 2, 0), np.nan)
    zone = np.where(
        position < 1 / 3, "lower", np.where(position > 2 / 3, "upper", "middle")
    )
    phase = np.where(
        np.isfinite(vertex), np.where(vertex > 1, "before_turn", "after_turn"), "none"
    )
    previous_start = close.shift(window - 1)
    close_low = close.rolling(window).min()
    recovery = (close - close_low) / (previous_start - close_low).replace(0, np.nan)
    return pd.DataFrame(
        {
            "timestamp": frame.timestamp.to_numpy(),
            "available_at": frame.timestamp.to_numpy() + int(cadence[0]),
            "shape": labels,
            "zone": zone,
            "range_position": position,
            "episode_age_bars": np.arange(len(code)) - starts + 1,
            "quadratic_r2": r2,
            "curvature": a,
            "path_efficiency": efficiency,
            "turn_phase": phase,
            "estimated_apex_bars": apex,
            "current_wedge_position": np.where(
                wedge, (p - lp[:, 1] - lp[:, 0]) / np.maximum(end_width, 1e-12), np.nan
            ),
            "fitted_turn_bars_ago": np.where(
                np.isin(labels, ["bowl", "cap"]),
                (1 - vertex) * (window - 1) / 2,
                np.nan,
            ),
            "recovery_of_observed_drop": recovery,
            "shape_zone": np.char.add(np.char.add(labels, ":"), zone),
        }
    )


def complete_resample(
    frame: pd.DataFrame, source_seconds: int, interval: str
) -> pd.DataFrame:
    """Refuse partial buckets; never synthesize a missing trade/candle."""
    seconds = INTERVAL_SECONDS[interval]
    if seconds < source_seconds or seconds % source_seconds:
        raise ValueError("target cadence must be a multiple of source cadence")
    raw = frame.copy()
    raw.index = pd.to_datetime(raw.timestamp, unit="s", utc=True)
    grouped = raw.resample(f"{seconds}s", origin="epoch", closed="left", label="left")
    out = grouped.agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    out = out.loc[grouped.timestamp.count() == seconds // source_seconds].copy()
    # pandas 3 may store DatetimeIndex in microseconds; do not assume nanoseconds.
    out.insert(
        0, "timestamp", out.index.to_numpy(dtype="datetime64[s]").astype("int64")
    )
    return out.reset_index(drop=True)


def common_suffix(frames: dict[str, pd.DataFrame], interval: str):
    """One comparable calendar, with gaps removed by trimming, never filling."""
    seconds = INTERVAL_SECONDS[interval]
    common = sorted(set.intersection(*(set(f.timestamp) for f in frames.values())))
    if not common:
        raise ValueError("no common calendar")
    times = np.asarray(common)
    breaks = np.flatnonzero(np.diff(times) != seconds)
    if len(breaks):
        times = times[breaks[-1] + 1 :]
    if len(times) < 300:
        raise ValueError(
            f"insufficient common contiguous data at {interval}: {len(times)} bars"
        )
    return {
        a: validate_bars(
            f.loc[f.timestamp.isin(times)].reset_index(drop=True), interval
        )
        for a, f in frames.items()
    }


def protected_intervals(path: Path, assets: tuple[str, ...]):
    """Read only. Protect dates for a constituent coin even in a cross pair."""
    if not path.is_file():
        return []
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        rows = db.execute(
            "SELECT coin,start,end,run_id FROM holdouts WHERE sealed_at IS NULL"
        ).fetchall()
    return [
        {"coin": c, "start": s, "end": e, "run_id": r}
        for c, s, e, r in rows
        if any(a in c.split("-") for a in assets)
    ]


def refuse_reserved(
    frame: pd.DataFrame, interval: str, reservations: list[dict]
) -> None:
    start = int(frame.timestamp.iloc[0])
    end = int(frame.timestamp.iloc[-1]) + INTERVAL_SECONDS[interval]
    if any(start < r["end"] and end > r["start"] for r in reservations):
        raise ValueError("study overlaps a protected unsealed holdout")


class Targets:
    """Research-only adapter to the canonical next-open accounting engine."""

    name = "shape_study_targets"

    def __init__(self, values):
        self.params = {}
        self.values = np.asarray(values, dtype=float)
        if not np.all(np.isfinite(self.values)) or np.any(
            (self.values < 0) | (self.values > 1)
        ):
            raise ValueError("spot exposures must be finite and in [0,1]")

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return float(self.values[history.i])


def replay(arrays, target, interval, costs):
    return run_backtest(
        Targets(target),
        arrays,
        EngineConfig(
            interval=interval,
            fill_delay=1,
            costs=CostConfig(fee_bps=costs[0], slippage_bps=costs[1]),
        ),
    )


def candidate_targets(arrays, tags, interval):
    out = {"cash": np.zeros(len(tags))}
    for name in SINGLES:
        out[name] = component_signal_series(
            {"strategy": name, "params": {}}, arrays, interval
        )
    for left, right in PAIRS:
        out[f"mean_{left}_{right}"] = (out[left] + out[right]) / 2
    shape = tags["shape"].to_numpy()
    out["rule_shape"] = np.select(
        [
            np.isin(shape, ["trend_up", "bowl"]),
            np.isin(shape, ["range", "v_rebound"]),
            shape == "compression",
        ],
        [out["macd"], out["ou_reversion"], out["breakout"]],
        default=0,
    )
    for name, values in out.items():
        out[name] = np.clip(values, 0, 1)
    return out


def learn_routes(log_returns, keys, names, start, end, minimum=30, episodes=3):
    """Train with observed next-bar results only; exclude two boundary bars.

    This is conditional attribution from continuous arm books. Switching books
    have different turnover, so only the separate routed replay measures profit.
    """
    stop = end - 2
    if stop <= start:
        raise ValueError("training window too short")
    scores = log_returns[:, start + 1 : stop + 1]
    observed = np.asarray(keys)[start:stop]
    global_pick = int(np.argmax(scores.sum(axis=1)))
    picks = {}
    for key in np.unique(observed):
        mask = observed == key
        runs = int(np.sum(mask & np.r_[True, ~mask[:-1]]))
        if mask.sum() >= minimum and runs >= episodes:
            picks[str(key)] = names[int(np.argmax(scores[:, mask].mean(axis=1)))]
    return names[global_pick], picks


def _metrics(equity, ts, fills, costs_usd, turnover):
    daily = (
        pd.Series(equity, index=pd.to_datetime(ts, unit="s", utc=True))
        .resample("1D")
        .last()
    )
    daily_returns = np.r_[
        daily.iloc[0] / 10000 - 1, daily.pct_change().dropna().to_numpy()
    ]
    sd = daily_returns.std(ddof=1) if len(daily_returns) > 1 else 0
    peak = np.maximum.accumulate(np.r_[10000, equity])[1:]
    return {
        "return_pct": float((equity[-1] / 10000 - 1) * 100),
        "max_drawdown_pct": float(np.min(equity / peak - 1) * 100),
        "daily_sharpe": float(daily_returns.mean() / sd * np.sqrt(365))
        if sd > 1e-12
        else 0,
        "fills": int(fills),
        "cost_usd": float(costs_usd),
        "turnover_usd": float(turnover),
        "test_bars": len(equity),
        "test_start": int(ts[0]),
        "test_end": int(ts[-1]),
    }


def run_cell(frame, tags, interval, costs, asset, scenario, output, candidates=None):
    arrays = frame_to_arrays(frame)
    if candidates is None:
        candidates = candidate_targets(arrays, tags, interval)
    names = list(candidates)
    arm_names = [name for name in names if name != "rule_shape"]
    n = len(frame)
    # Warm every signal before selection starts; same date for every arm.
    warm = max(WINDOW, *(build(name).warmup_bars() for name in SINGLES))
    cuts = [int(n * x) for x in (0.4, 0.6, 0.8)] + [n]
    if cuts[0] < warm + 20:
        raise ValueError("insufficient selection history after warmup")
    curves, rows, picks, attributions = {}, [], [], []
    for name, values in candidates.items():
        curves[name] = replay(arrays, values, interval, costs).equity
    # A return at i+1 is attributed to the shape observable at close i.
    logs = np.stack(
        [np.r_[0, np.diff(np.log(np.maximum(curves[x], 1e-250)))] for x in arm_names]
    )
    null_names = [f"null_shape_{seed}" for seed in range(5)]
    policies = (
        names
        + ["fold_reset_hold", "selected_fixed", "shape_router", "shape_zone_router"]
        + null_names
    )
    equity_parts = {p: [] for p in policies}
    running = {p: 1.0 for p in policies}
    totals = {p: [0, 0.0, 0.0] for p in policies}
    decisions = []
    for fold, (lo, hi) in enumerate(itertools.pairwise(cuts), 1):
        fixed, route = learn_routes(logs, tags["shape"], arm_names, warm, lo)
        _, zone_route = learn_routes(logs, tags["shape_zone"], arm_names, warm, lo)
        null_routes = {}
        for seed, policy in enumerate(null_names):
            # Permute training labels only. No evaluation label or outcome is read.
            shuffled = np.random.default_rng(20261111 + 17 * fold + seed).permutation(
                tags["shape"].to_numpy()[:lo]
            )
            _, null_routes[policy] = learn_routes(logs, shuffled, arm_names, warm, lo)
        picks.append(
            {
                "asset": asset,
                "interval": interval,
                "scenario": scenario,
                "fold": fold,
                "train_start": int(frame.timestamp.iloc[warm]),
                "last_train_outcome": int(frame.timestamp.iloc[lo - 2]),
                "first_test_open": int(frame.timestamp.iloc[lo]),
                "fixed": fixed,
                "shape_routes": json.dumps(route, sort_keys=True),
                "shape_zone_routes": json.dumps(zone_route, sort_keys=True),
                "null_routes": json.dumps(null_routes, sort_keys=True),
            }
        )
        shape_values = np.array(
            [candidates[route.get(k, fixed)][i] for i, k in enumerate(tags["shape"])]
        )
        zone_values = np.array(
            [
                candidates[zone_route.get(k, fixed)][i]
                for i, k in enumerate(tags["shape_zone"])
            ]
        )
        targets = {
            **candidates,
            "fold_reset_hold": np.ones(n),
            "selected_fixed": candidates[fixed],
            "shape_router": shape_values,
            "shape_zone_router": zone_values,
        }
        for policy, mapping in null_routes.items():
            targets[policy] = np.array(
                [
                    candidates[mapping.get(k, fixed)][i]
                    for i, k in enumerate(tags["shape"])
                ]
            )
        sliced = {k: v[lo - 1 : hi] for k, v in arrays.items()}
        for policy in policies:
            result = replay(sliced, targets[policy][lo - 1 : hi], interval, costs)
            eq = result.equity[1:] * running[policy]
            running[policy] = float(eq[-1] / 10000)
            equity_parts[policy].append(eq)
            totals[policy][0] += len(result.trades)
            totals[policy][1] += result.metrics.total_fees * (
                eq[-1] / result.equity[-1]
            )
            totals[policy][2] += sum(abs(t.notional) for t in result.trades) * (
                eq[-1] / result.equity[-1]
            )
            # Full conditional table includes a denominator and episode count.
            log_r = np.log(result.equity[1:] / result.equity[:-1])
            keys = tags["shape"].to_numpy()[lo - 1 : hi - 1]
            for shape in np.unique(keys):
                mask = keys == shape
                episodes = int(np.sum(mask & np.r_[True, ~mask[:-1]]))
                attributions.append(
                    {
                        "asset": asset,
                        "interval": interval,
                        "scenario": scenario,
                        "fold": fold,
                        "policy": policy,
                        "shape": shape,
                        "bars": int(mask.sum()),
                        "episodes": episodes,
                        "log_return_sum": float(log_r[mask].sum()),
                        "mean_next_bar_bps": float(
                            np.expm1(log_r[mask]).mean() * 10000
                        ),
                    }
                )
        for i in range(lo - 1, hi - 1):
            decisions.append(
                {
                    "signal_timestamp": int(arrays["ts"][i]),
                    "fill_timestamp": int(arrays["ts"][i + 1]),
                    "fold": fold,
                    "shape": tags["shape"].iloc[i],
                    "shape_zone": tags["shape_zone"].iloc[i],
                    "fixed": fixed,
                    "shape_pick": route.get(tags["shape"].iloc[i], fixed),
                    "zone_pick": zone_route.get(tags["shape_zone"].iloc[i], fixed),
                }
            )
    times = arrays["ts"][cuts[0] :]
    equity_file = pd.DataFrame({"timestamp": times})
    for policy in policies:
        eq = np.concatenate(equity_parts[policy])
        equity_file[policy] = eq
        rows.append(
            {
                "asset": asset,
                "interval": interval,
                "scenario": scenario,
                "policy": policy,
                **_metrics(eq, times, *totals[policy]),
            }
        )
    # Continuous passive pays one entry and one final exit across all three folds.
    tail = {k: v[cuts[0] - 1 :] for k, v in arrays.items()}
    passive = replay(tail, np.ones(len(tail["ts"])), interval, costs)
    equity_file["buy_hold"] = passive.equity[1:]
    rows.append(
        {
            "asset": asset,
            "interval": interval,
            "scenario": scenario,
            "policy": "buy_hold",
            **_metrics(
                passive.equity[1:],
                times,
                len(passive.trades),
                passive.metrics.total_fees,
                sum(abs(t.notional) for t in passive.trades),
            ),
        }
    )
    equity_file.to_csv(
        output / f"{asset}_{interval}_{scenario}_equity.csv.gz", index=False
    )
    pd.DataFrame(decisions).to_csv(
        output / f"{asset}_{interval}_{scenario}_decisions.csv.gz", index=False
    )
    return rows, picks, attributions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--zec-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path.home() / ".config/soltui/experiments/experiments.sqlite3",
    )
    parser.add_argument("--assets", nargs="+", default=list(ASSETS), choices=ASSETS)
    parser.add_argument(
        "--intervals", nargs="+", default=["1h", "6h", "1d"], choices=["1h", "6h", "1d"]
    )
    args = parser.parse_args(argv)
    if args.output.exists():
        raise ValueError(
            "use a fresh output directory; completed evidence is immutable"
        )
    args.output.mkdir(parents=True)
    reservations = protected_intervals(args.ledger, tuple(args.assets))
    manifest = {
        "schema_version": VERSION,
        "status": "running",
        "assets": args.assets,
        "intervals": args.intervals,
        "window": WINDOW,
        "scenarios": SCENARIOS,
        "singles": SINGLES,
        "pairs": PAIRS,
        "folds": [0.4, 0.6, 0.8, 1.0],
        "mode": "spot",
        "leverage": 1,
        "fill_delay": 1,
        "protected_intervals": reservations,
        "source_sha256": digest(Path(__file__)),
        "code_sha256": {
            str(p.relative_to(Path(__file__).resolve().parents[1])): digest(p)
            for p in sorted(
                (Path(__file__).resolve().parents[1] / "backtester/core").rglob("*.py")
            )
        },
        "versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "null_control": "Five fixed-seed permutations of training labels; evaluation labels remain unchanged.",
        "inputs": [],
        "note": "Exploratory historical walk-forward; no untouched final validation or live evidence.",
    }
    write_json(args.output / "manifest.json", manifest)
    rows, picks, attribution, snapshots = [], [], [], []
    for interval in args.intervals:
        frames = {}
        for asset in args.assets:
            source_interval = "1d" if interval == "1d" else "1h"
            path = (
                args.zec_dir if asset == "ZEC" else args.data_dir
            ) / f"{asset}_{source_interval}.csv"
            raw = pd.read_csv(path)
            duplicate_rows = int(raw.timestamp.duplicated().sum())
            if duplicate_rows:
                conflicts = raw.groupby("timestamp").nunique().max().max() > 1
                if conflicts:
                    raise ValueError(f"conflicting duplicate bars: {path}")
                raw = raw.drop_duplicates("timestamp")
            raw = raw.sort_values("timestamp").reset_index(drop=True)
            raw = validate_bars(raw, source_interval, strict_gaps=False)
            first = int(
                pd.Timestamp(
                    "2023-07-15" if interval == "1d" else "2026-05-09", tz="UTC"
                ).timestamp()
            )
            end = int(pd.Timestamp("2026-11-07", tz="UTC").timestamp())
            frame = raw.loc[
                (raw.timestamp >= first)
                & (raw.timestamp + INTERVAL_SECONDS[source_interval] <= end)
            ]
            if interval != source_interval:
                frame = complete_resample(
                    frame, INTERVAL_SECONDS[source_interval], interval
                )
            frames[asset] = frame
            manifest["inputs"].append(
                {
                    "asset": asset,
                    "interval": interval,
                    "path": str(path),
                    "sha256": digest(path),
                    "provider": "Coinbase Exchange",
                    "quote": "USD",
                    "duplicates_removed": duplicate_rows,
                    "available_bars": len(frame),
                }
            )
        frames = common_suffix(frames, interval)
        for asset, frame in frames.items():
            refuse_reserved(frame, interval, reservations)
            frame.to_csv(args.output / f"{asset}_{interval}_bars.csv.gz", index=False)
            tags = detect_shapes(frame)
            candidates = candidate_targets(frame_to_arrays(frame), tags, interval)
            tags.to_csv(args.output / f"{asset}_{interval}_tags.csv.gz", index=False)
            groups = (tags["shape"] != tags["shape"].shift()).cumsum()
            segments = tags.groupby(groups).agg(
                shape=("shape", "first"),
                known_from=("available_at", "first"),
                last_observed_at=("available_at", "last"),
                bars=("timestamp", "size"),
                start_position=("range_position", "first"),
                end_position=("range_position", "last"),
            )
            segments.to_csv(
                args.output / f"{asset}_{interval}_shape_intervals.csv", index=False
            )
            snapshots.append(
                {
                    "asset": asset,
                    "interval": interval,
                    **json.loads(tags.iloc[-1].to_json()),
                    "close": float(frame.close.iloc[-1]),
                }
            )
            for scenario, costs in SCENARIOS.items():
                print(f"{asset} {interval} {scenario} {len(frame)} bars", flush=True)
                r, p, a = run_cell(
                    frame,
                    tags,
                    interval,
                    costs,
                    asset,
                    scenario,
                    args.output,
                    candidates,
                )
                rows.extend(r)
                picks.extend(p)
                attribution.extend(a)
                pd.DataFrame(rows).to_csv(args.output / "summary.csv", index=False)
    pd.DataFrame(picks).to_csv(args.output / "selection.csv", index=False)
    pd.DataFrame(attribution).to_csv(args.output / "by_shape.csv", index=False)
    write_json(args.output / "latest_historical_shapes.json", snapshots)
    manifest["status"] = "complete"
    manifest["summary_rows"] = len(rows)
    manifest["artifacts"] = {
        p.name: digest(p)
        for p in sorted(args.output.iterdir())
        if p.name != "manifest.json"
    }
    write_json(args.output / "manifest.json", manifest)
    print(f"complete: {len(rows)} policy cells", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

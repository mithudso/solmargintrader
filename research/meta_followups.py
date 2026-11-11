"""Fixed, costed reanalysis of examined history; never a fresh holdout test.

This module cannot trade. It reuses the canonical long/flat spot book and records
the exact common calendar, data, source and costs used by each comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from itertools import pairwise
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.data import frame_to_arrays, validate_bars
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.metrics import compute_metrics
from backtester.core.types import CostConfig, periods_per_year
from backtester.core.zec_ensemble import component_signal_series
from research.shape_study import protected_intervals, refuse_reserved

END_EXCLUSIVE = int(pd.Timestamp("2026-11-08T19:00:00Z").timestamp())
ASSETS = ("BTC", "ETH", "ZEC")
FEES_BPS = (10.0, 50.0, 90.0)
CAPITAL = 10000.0
STRATEGIES = {
    "bb_breakout_40_2.5": {"strategy": "bb_breakout", "params": {"window": 40, "num_std": 2.5}},
    "sma_regime_200": {"strategy": "sma_regime", "params": {"window": 200}},
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


class FrozenTargets:
    """Observable-bar targets; canonical engine alone decides fill timing."""

    name = "meta_followup_frozen_targets"

    def __init__(self, targets):
        self.values = np.asarray(targets, dtype=float)
        if self.values.ndim != 1 or not np.isfinite(self.values).all() or np.any((self.values < 0) | (self.values > 1)):
            raise ValueError("targets must be a finite long/flat exposure vector")
        self.params = {}

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return float(self.values[history.i])


def longest_common_calendar(frames, seconds=3600, minimum=500):
    """Choose the longest exact common run, never join across missing prices."""
    if not frames:
        raise ValueError("at least one frame is required")
    for frame in frames.values():
        ts = frame.timestamp.to_numpy()
        if len(ts) == 0 or np.any(np.diff(ts) <= 0):
            raise ValueError("ordered unique source timestamps required")
    times = np.array(sorted(set.intersection(*(set(f.timestamp) for f in frames.values()))), dtype=np.int64)
    if len(times) == 0:
        raise ValueError("no common calendar")
    boundaries = np.r_[0, np.flatnonzero(np.diff(times) != seconds) + 1, len(times)]
    segments = [times[a:b] for a, b in pairwise(boundaries)]
    # Ties favor the earlier window, rather than a favorable return or endpoint.
    selected = max(segments, key=len)
    if len(selected) < minimum:
        raise ValueError(f"insufficient common contiguous observations: {len(selected)}")
    return {symbol: validate_bars(f[f.timestamp.isin(selected)].reset_index(drop=True), "1h") for symbol, f in frames.items()}, {"common_observations_before_gap_trimming": len(times), "segments": [{"start": int(x[0]), "end_exclusive": int(x[-1]) + seconds, "bars": len(x)} for x in segments], "chosen_start": int(selected[0]), "chosen_end_exclusive": int(selected[-1]) + seconds, "chosen_bars": len(selected), "selection_rule": "longest common contiguous hourly run; earlier segment breaks a length tie"}


def replay(arrays, raw_targets, evaluation_start, fee_bps, execution_bps=2.0, capital=CAPITAL):
    """History before the evaluation boundary can inform only its first order."""
    if not isinstance(evaluation_start, int) or isinstance(evaluation_start, bool) or not 1 <= evaluation_start < len(arrays["ts"]):
        raise ValueError("evaluation_start must be an interior integer bar index")
    targets = np.asarray(raw_targets, dtype=float).copy()
    if targets.shape != arrays["close"].shape:
        raise ValueError("target and bar shapes differ")
    # A signal at the final training close may schedule the first evaluation open.
    targets[:evaluation_start - 1] = 0.0
    result = run_backtest(FrozenTargets(targets), arrays, EngineConfig(interval="1h", fill_delay=1, initial_capital=capital, mode="spot", leverage=1.0, allow_short=False, costs=CostConfig(fee_bps=fee_bps, slippage_bps=execution_bps)))
    if any(trade.bar_index < evaluation_start for trade in result.trades):
        raise AssertionError("training history changed the investment account")
    curve, exposure, ts = result.equity[evaluation_start:], result.exposure[evaluation_start:], result.timestamps[evaluation_start:]
    metrics = compute_metrics(curve, ts, result.trades, exposure, periods_per_year("1h"), 0, 0, initial_equity=capital)
    return result, {"return_pct": float(metrics.total_return * 100), "max_drawdown_pct": float(metrics.max_drawdown * 100), "mean_inventory_exposure": float(np.mean(np.abs(exposure))), "fees_usd": float(sum(t.fee for t in result.trades)), "slippage_usd": float(sum(t.slippage for t in result.trades)), "turnover_usd": float(sum(abs(t.notional) for t in result.trades)), "fills": len(result.trades), "completed_trades": metrics.trade_count, "final_equity": float(curve[-1]), "evaluation_bars": len(curve), "fee_bps_per_side": fee_bps, "execution_bps_per_side": execution_bps}


def portfolio_metrics(curve, ts, capital=CAPITAL):
    curve = np.asarray(curve, float)
    metrics = compute_metrics(curve, ts, [], np.zeros(len(curve)), periods_per_year("1h"), 0, 0, initial_equity=capital)
    return {"return_pct": float(metrics.total_return * 100), "max_drawdown_pct": float(metrics.max_drawdown * 100), "final_equity": float(curve[-1]), "evaluation_bars": len(curve)}


def fixed_slot_curve(curves, names, slots=10, removed_to_cash=()):
    """Remove named sleeves to cash without reallocating their fixed budget."""
    if not names or len(names) > slots or len(set(names)) != len(names):
        raise ValueError("distinct names must fit positive fixed slots")
    if any(name not in curves for name in names):
        raise ValueError("a selected sleeve is missing")
    first = np.asarray(curves[names[0]], dtype=float)
    unit = np.ones(first.shape, dtype=float)
    if first.ndim != 1 or not np.isfinite(first).all():
        raise ValueError("finite one dimensional curves required")
    for name in names:
        sleeve = np.asarray(curves[name], dtype=float)
        if sleeve.shape != first.shape or not np.isfinite(sleeve).all():
            raise ValueError("sleeve shapes or values differ")
        if name not in removed_to_cash:
            unit += (sleeve - 1.0) / slots
    return unit


def concentration(grid_root, output, bindings):
    selection_path = grid_root / "selection.json"
    bindings[str(selection_path)] = sha(selection_path)
    selection = json.loads(selection_path.read_text())
    reference_path = grid_root / "portfolio_curves.npz"
    bindings[str(reference_path)] = sha(reference_path)
    rows, saved = [], {}
    with np.load(reference_path) as reference:
        full_ts = reference["timestamp"]
        for scenario in ("zero_2", "zero_10", "zero_25", "fee10_2"):
            for mask in (0, 1, 31):
                caps = {"original": CAPITAL, "ZEC_to_cash": CAPITAL, "passive_original": CAPITAL, "passive_ZEC_to_cash": CAPITAL}
                histories = {name: [] for name in caps}
                for fold in range(3):
                    names = selection[fold]["selected" if mask & 1 else "marketcap_ten"]
                    curves, passives = {}, {}
                    for symbol in names:
                        path = grid_root / f"{symbol}_f{fold}_{scenario}.npz"
                        bindings[str(path)] = sha(path)
                        with np.load(path) as cell:
                            curves[symbol] = cell["equity"][mask >> 1]
                            passives[symbol] = cell["passive"]
                    for label, starting_capital in caps.items():
                        sleeve = passives if label.startswith("passive") else curves
                        removed = ("ZEC",) if "ZEC_to_cash" in label else ()
                        unit = fixed_slot_curve(sleeve, names, 10, removed)
                        curve = unit * starting_capital
                        histories[label].append(curve)
                        caps[label] = float(curve[-1])
                histories = {name: np.concatenate(curves) for name, curves in histories.items()}
                maximum_error = float(np.max(np.abs(histories["original"] - reference[f"{scenario}_m{mask:02d}"])))
                if maximum_error > 1e-7:
                    raise ValueError("original fixed-slot replay differs from accepted grid study")
                result = {name: portfolio_metrics(curve, full_ts) for name, curve in histories.items()}
                rows.append({"scenario": scenario, "mask": mask, "interpretation": "ZEC allocation remains cash, with all original selections, gate settings, other sleeves and fixed ten-slot weights unchanged", "original_replay_max_usd_error": maximum_error, "metrics": result, "ZEC_grid_contribution_pp": result["original"]["return_pct"] - result["ZEC_to_cash"]["return_pct"], "ZEC_passive_contribution_pp": result["passive_original"]["return_pct"] - result["passive_ZEC_to_cash"]["return_pct"]})
                for label, curve in histories.items():
                    saved[f"{scenario}_m{mask}_{label}"] = curve
    np.savez_compressed(output / "concentration_curves.npz", timestamp=full_ts, **saved)
    save(output / "concentration.json", rows)
    return rows


def run(data_root, grid_root, output, fees_path, ledger):
    if output.exists():
        raise ValueError("use a fresh output directory; do not overwrite accepted followups")
    output.mkdir(parents=True)
    protocol = {"version": 1, "classification": "exploratory fixed-parameter reanalysis of previously examined history, not fresh OOS or prospective profit evidence", "assets": list(ASSETS), "end_exclusive": END_EXCLUSIVE, "split": "first40percent of common contiguous history is indicator warmup only; last60percent investment account starts in cash", "strategies": STRATEGIES, "primary_fee_bps": 90, "sensitivity_fee_bps": list(FEES_BPS), "maker_rate_limit": "50bps assumes identical market fills only as a sensitivity. It does not certify maker execution, queue priority or nonfills.", "execution_bps_per_side": 2, "leverage": 1, "shorts": False, "capital": CAPITAL, "cash_return": 0, "concentration": "remove ZEC to cash at original fixed weights; no replacement coin or refitting"}
    save(output / "protocol.json", protocol)
    bindings = {str(fees_path): sha(fees_path)}
    frames = {}
    reservations = protected_intervals(ledger, ASSETS)
    for symbol in ASSETS:
        path = data_root / f"{symbol}_1h.csv"
        bindings[str(path)] = sha(path)
        sidecar = data_root / f"{symbol}_1h.json"
        bindings[str(sidecar)] = sha(sidecar)
        if json.loads(sidecar.read_text())["sha256"] != sha(path):
            raise ValueError("source CSV differs from its collection evidence")
        frame = pd.read_csv(path)
        frame = frame[frame.timestamp < END_EXCLUSIVE].reset_index(drop=True)
        refuse_reserved(frame, "1h", reservations)
        frames[symbol] = frame
    frames, calendar = longest_common_calendar(frames)
    n = len(frames["ZEC"])
    split = int(n * 0.4)
    if split < 201:
        raise ValueError("insufficient training observations for slow comparator")
    calendar.update(evaluation_start=int(frames["ZEC"].timestamp.iloc[split]), evaluation_end_exclusive=int(frames["ZEC"].timestamp.iloc[-1]) + 3600, training_bars=split, evaluation_bars=n - split)
    save(output / "calendar.json", calendar)
    arrays = {name: frame_to_arrays(frame) for name, frame in frames.items()}
    targets = {name: np.clip(component_signal_series(spec, arrays["ZEC"], "1h"), 0, 1) for name, spec in STRATEGIES.items()}
    records, saved = [], {}
    same_ts = arrays["ZEC"]["ts"][split:]
    for fee in FEES_BPS:
        passive_curves = {}
        for symbol in ASSETS:
            result, metrics = replay(arrays[symbol], np.ones(n), split, fee)
            curve = result.equity[split:]
            passive_curves[symbol] = curve
            saved[f"{symbol}_hold_fee{int(fee)}"] = curve
            records.append({"asset": symbol, "policy": "passive", **metrics})
            pd.DataFrame([asdict(trade) for trade in result.trades]).to_csv(output / f"{symbol}_hold_fee{int(fee)}_trades.csv", index=False)
        combined = (passive_curves["BTC"] + passive_curves["ETH"]) / 2
        saved[f"BTC_ETH_equal_hold_fee{int(fee)}"] = combined
        records.append({"asset": "BTC+ETH", "policy": "equal_initial_buy_and_hold_no_rebalancing", "fee_bps_per_side": fee, "execution_bps_per_side": 2, **portfolio_metrics(combined, same_ts)})
        for policy, values in targets.items():
            result, metrics = replay(arrays["ZEC"], values, split, fee)
            saved[f"ZEC_{policy}_fee{int(fee)}"] = result.equity[split:]
            records.append({"asset": "ZEC", "policy": policy, "same_coin_passive_return_pct": next(x["return_pct"] for x in records if x.get("asset") == "ZEC" and x.get("policy") == "passive" and x.get("fee_bps_per_side") == fee), **metrics})
            pd.DataFrame([asdict(trade) for trade in result.trades]).to_csv(output / f"ZEC_{policy}_fee{int(fee)}_trades.csv", index=False)
    # Breakeven is bounded and descriptive. It does not choose or optimize a rule.
    breakeven = []
    for policy, values in targets.items():
        endpoints = []
        for fee in (0, 250):
            _, metrics = replay(arrays["ZEC"], values, split, fee)
            endpoints.append(metrics["return_pct"])
        row = {"policy": policy, "fee_search_bps_per_side": [0, 250], "zero_fee_plus2execution_return_pct": endpoints[0], "250fee_plus2execution_return_pct": endpoints[1], "classification": "net-zero return threshold for frozen signal path; not a maker-fill or statistical alpha threshold"}
        if endpoints[0] <= 0:
            row["net_positive_fee_ceiling_bps"] = None
            row["reason"] = "not profitable even at zero commission plus execution drag"
        elif endpoints[1] > 0:
            row["net_positive_fee_ceiling_bps"] = None
            row["reason"] = "breakeven exceeds the bounded250bps search; no extrapolation"
        else:
            lo, hi = 0.0, 250.0
            for _ in range(18):
                mid = (lo + hi) / 2
                _, metrics = replay(arrays["ZEC"], values, split, mid)
                if metrics["return_pct"] > 0:
                    lo = mid
                else:
                    hi = mid
            row["net_positive_fee_ceiling_bps"] = (lo + hi) / 2
        breakeven.append(row)
    np.savez_compressed(output / "fee_replay_curves.npz", timestamp=same_ts, **saved)
    save(output / "fee_replays.json", records)
    save(output / "breakeven.json", breakeven)
    concentration(grid_root, output, bindings)
    for path, digest in bindings.items():
        if sha(path) != digest:
            raise ValueError("input changed during followup run")
    source = [Path(__file__).resolve(), Path("research/shape_study.py").resolve(), *Path("backtester/core").resolve().rglob("*.py")]
    manifest = {"schema_version": 1, "status": "complete", "classification": protocol["classification"], "source": {str(p): sha(p) for p in sorted(source)}, "inputs": bindings, "protected_intervals": reservations, "fees_evidence": json.loads(fees_path.read_text()), "artifacts": {str(p): sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    save(output / "manifest.json", manifest)
    return {"output": str(output), "fee_records": len(records), "concentration_records": 12, "calendar": calendar}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path.home() / ".local/share/solmargintrader/research"
    parser.add_argument("--data", type=Path, default=root / "coinbase50-20261111/input")
    parser.add_argument("--grid", type=Path, default=root / "coinbase50-20261111/run-v1")
    parser.add_argument("--fees", type=Path, default=root / "meta-analysis-20261111/authenticated-fees.json")
    parser.add_argument("--ledger", type=Path, default=Path.home() / ".config/soltui/experiments/experiments.sqlite3")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.grid, args.output, args.fees, args.ledger)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

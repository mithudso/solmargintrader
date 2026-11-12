"""Coinbase survivor-cohort study. Explicit data, no orders or runtime changes."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.types import CostConfig
from research.coinbase50_data import PLAN, save, sha
from research.coinbase50_grid import (
    SCENARIOS,
    causal_hour_features,
    grid_features,
    hourly_from_quarters,
    passive,
    performance,
    permissions,
    simulate,
)
from research.coinbase50_stats import (
    adjust_clock_family,
    clock_test,
    cycle_summary,
    daily_profiles,
    wavelength_windows,
)
from research.shape_study import protected_intervals, refuse_reserved
from research.zec_cycles import holm

STUDY_END = int(pd.Timestamp("2026-11-08T19:00:00Z").timestamp())
TRAIN_DAYS = 26


def binding(root, symbol, phase):
    root = Path(root)
    source = [Path("research") / f"coinbase50_{name}.py" for name in ("data", "grid", "stats", "study")]
    source += [Path("research/shape_study.py"), Path("research/zec_cycles.py")]
    source += sorted(Path("backtester/core").glob("*.py"))
    paths = source + [root / "protocol.json", root / "universe.json", root.parent / "dependencies.txt"]
    intervals = ("1h", "5m") if phase == "diagnostics" else ("15m",)
    for asset in sorted({symbol, "BTC"}):
        paths.extend(root / f"{asset}_{interval}.csv" for interval in intervals)
        paths.extend(root / f"{asset}_{interval}.json" for interval in intervals)
    return {str(p.resolve()): sha(p) for p in paths}


def read(root, symbol, interval):
    raw = (Path(root) / f"{symbol}_{interval}.csv").read_bytes()
    evidence = json.loads((Path(root) / f"{symbol}_{interval}.json").read_text())
    if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
        raise ValueError("source checksum changed")
    frame = pd.read_csv(io.BytesIO(raw))
    frame = frame[frame.timestamp < STUDY_END].reset_index(drop=True)
    if len(frame):
        reserved = protected_intervals(Path.home() / ".config/soltui/experiments/experiments.sqlite3", (symbol,))
        refuse_reserved(frame, interval, reserved)
    return frame


def admit_inputs(root, symbol, phase):
    # Reservation state can change independently of immutable file digests.
    for asset in sorted({symbol, "BTC"}):
        for interval in (("1h", "5m") if phase == "diagnostics" else ("15m",)):
            read(root, asset, interval)


def diagnostics(job):
    root, out, asset, replicates = job
    root, out = Path(root), Path(out)
    symbol = asset["symbol"]
    target = out / f"{symbol}_diagnostics.json"
    fingerprint = binding(root, symbol, "diagnostics")
    if target.exists():
        cached = json.loads(target.read_text())
        if cached.get("binding") != fingerprint:
            raise ValueError("diagnostics cache binding changed; use a fresh output directory")
        if cached.get("replicates") != replicates:
            raise ValueError("diagnostics cache replicates changed; use a fresh output directory")
        admit_inputs(root, symbol, "diagnostics")
        return cached
    clock_rows, cycle_rows = [], []
    for interval, days in (("5m", 2), ("1h", 7)):
        frame, btc = read(root, symbol, interval), read(root, "BTC", interval)
        if len(frame) >= 48:
            rows = wavelength_windows(frame, btc, PLAN[interval][0], days)
            cycle_rows.extend(dict(x, symbol=symbol, interval=interval) for x in rows)
    if asset["directional50"]:
        frame = read(root, symbol, "1h")
        for clock in ("UTC", "America/New_York"):
            for metric in ("direction", "absolute_return", "log_quote_volume"):
                profiles, excluded = daily_profiles(frame, clock, metric)
                result = clock_test(profiles, metric, replicates)
                clock_rows.append(dict(result, symbol=symbol, clock=clock, metric=metric, excluded_days=excluded))
    summary = []
    for interval in ("5m", "1h"):
        for mode in ("raw", "market_calendar_residual"):
            result = cycle_summary([x for x in cycle_rows if x["interval"] == interval and x["mode"] == mode])
            summary.append(dict(result, symbol=symbol, interval=interval, mode=mode))
    result = {"symbol": symbol, "clock": clock_rows, "cycles": cycle_rows, "cycle_summary": summary, "binding": fingerprint, "replicates": replicates}
    save(target, result)
    return result


def grid_coin(job):
    root, out, asset = job
    root, out = Path(root), Path(out)
    symbol = asset["symbol"]
    marker = out / f"{symbol}_grid.json"
    fingerprint = binding(root, symbol, "grid")
    if marker.exists():
        cached = json.loads(marker.read_text())
        if cached.get("binding") != fingerprint:
            raise ValueError("grid cache binding changed; use a fresh output directory")
        if any(sha(path) != checksum for path, checksum in cached.get("outputs", {}).items()):
            raise ValueError("grid artifact checksum changed")
        admit_inputs(root, symbol, "grid")
        return cached
    frame = read(root, symbol, "15m")
    end = STUDY_END
    expected = np.arange(end - (90 + TRAIN_DAYS) * 86400, end, 900)
    frame = frame[frame.timestamp >= expected[0]].reset_index(drop=True)
    if len(frame) != len(expected) or not np.array_equal(frame.timestamp, expected):
        result = {"symbol": symbol, "eligible": False, "reason": "complete116day15mcohort required; this asset stays cash in all50 controls", "bars": len(frame), "expected": len(expected), "binding": fingerprint}
        save(marker, result)
        return result
    btc = hourly_from_quarters(read(root, "BTC", "15m"))
    features = causal_hour_features(hourly_from_quarters(frame), btc)
    features.to_csv(out / f"{symbol}_hour_features.csv.gz", index=False)
    shape_path = out / f"{symbol}_shapes.csv.gz"
    from research.shape_study import detect_shapes
    detect_shapes(frame).to_csv(shape_path, index=False)
    folds = []
    for fold in range(3):
        left = end - (90 - 30 * fold) * 86400
        train = frame[(frame.timestamp >= left - TRAIN_DAYS * 86400) & (frame.timestamp < left)]
        test = frame[(frame.timestamp >= left) & (frame.timestamp < left + 30 * 86400)]
        both = pd.concat([train, test], ignore_index=True)
        gates, settings = permissions(both, features, left)
        gates = gates[-len(test):]
        rows = []
        for scenario, (fee, slip) in SCENARIOS.items():
            costs = CostConfig(fee_bps=fee, slippage_bps=slip)
            curves, exposures, details = [], [], []
            for mask in range(16):
                allowed = np.ones(len(test), bool)
                for factor in range(4):
                    if mask & (1 << factor):
                        allowed &= gates[:, factor]
                equity, exposure, detail, result = simulate(train, test, allowed, 200, costs, float(asset["product"]["quote_min_size"]))
                curves.append(equity / 200)
                exposures.append(exposure)
                detail = {k: v for k, v in detail.items() if k != "shape_of_gate"}
                detail["allowed_fraction"] = float(np.mean(allowed))
                details.append(detail)
                pd.DataFrame([vars(x) for x in result.trades]).to_csv(out / f"{symbol}_f{fold}_{scenario}_g{mask:02d}_trades.csv.gz", index=False)
            hold = passive(test, 200, costs) / 200
            matched = np.stack([passive(test, 200, costs, float(np.mean(x))) / 200 for x in exposures])
            path = out / f"{symbol}_f{fold}_{scenario}.npz"
            np.savez_compressed(path, timestamp=test.timestamp.to_numpy(), equity=np.asarray(curves), exposure=np.asarray(exposures), passive=hold, exposure_matched_passive=matched)
            rows.append({"scenario": scenario, "curves": str(path.resolve()), "sha256": sha(path), "gates": details})
        folds.append({"fold": fold, "train_start": int(train.timestamp.iloc[0]), "train_end": left, "test_end": left + 30 * 86400, "screen": grid_features(train), "settings": settings, "scenarios": rows})
    correlation = float(features[["H1", "raw_rv"]].corr().iloc[0, 1])
    result = {"symbol": symbol, "eligible": True, "folds": folds, "H1_rv_correlation": correlation if np.isfinite(correlation) else None, "binding": fingerprint, "outputs": {str(p.resolve()): sha(p) for p in out.glob(f"{symbol}_*") if p.is_file() and p != marker}}
    save(marker, result)
    return result


def bootstrap_differences(daily, replicates=9999):
    """Paired calendar blocks; one resample shared across all variants/coins."""
    daily = np.asarray(daily)
    n = len(daily)
    rng = np.random.default_rng(20261111)
    means = []
    for first in range(0, replicates, 256):
        starts = rng.integers(0, n, size=(min(256, replicates - first), int(np.ceil(n / 7))))
        indices = (starts[..., None] + np.arange(7)) % n
        indices = indices.reshape(len(starts), -1)[:, :n]
        means.append(daily[indices].mean(axis=1))
    draws = np.concatenate(means)
    observed = daily.mean(axis=0)
    null = draws - observed
    p = (1 + np.sum(np.abs(null) >= np.abs(observed), axis=0)) / (1 + replicates)
    return p, np.quantile(draws, [0.025, 0.975], axis=0)


def portfolios(out, assets, coin_results):
    eligible = {x["symbol"]: x for x in coin_results if x["eligible"]}
    marketcap_ten = [a["symbol"] for a in assets if a["symbol"] in eligible][:10]
    rows, coins, selection, comparisons = [], [], [], []
    curves_all, daily_all = {}, []
    end = STUDY_END
    ts = np.arange(end - 90 * 86400, end, 900)
    for scenario in SCENARIOS:
        accumulators = {mask: 10000.0 for mask in range(32)}
        hold_cap = {selected: 10000.0 for selected in (False, True)}
        history = {mask: [] for mask in range(32)}
        holds = {selected: [] for selected in (False, True)}
        matched_history = {mask: [] for mask in range(32)}
        matched_cap = {mask: 10000.0 for mask in range(32)}
        control_cap = {name: 10000.0 for name in ("all50_grid", "all50_hold", "eligible_grid", "eligible_hold")}
        control_history = {name: [] for name in control_cap}
        for fold in range(3):
            ranked = sorted(eligible, key=lambda a: (-eligible[a]["folds"][fold]["screen"]["score"], a))
            chosen = ranked[:10]
            if scenario == next(iter(SCENARIOS)):
                selection.append({"fold": fold, "selected": chosen, "marketcap_ten": marketcap_ten, "ranking": [{"symbol": a, **eligible[a]["folds"][fold]["screen"]} for a in ranked]})
            loaded = {}
            for symbol, result in eligible.items():
                cell = next(x for x in result["folds"][fold]["scenarios"] if x["scenario"] == scenario)
                if sha(cell["curves"]) != cell["sha256"]:
                    raise ValueError("grid curve checksum changed")
                loaded[symbol] = np.load(cell["curves"])
                for gate in range(16):
                    coins.append({"symbol": symbol, "scenario": scenario, "fold": fold, "gate": gate, **performance(loaded[symbol]["equity"][gate] * 200, 200), "mean_inventory_fraction": float(np.mean(loaded[symbol]["exposure"][gate])), "round_trips": cell["gates"][gate]["round_trips"]})
            for selected in (False, True):
                names, slots = (chosen, 10) if selected else (marketcap_ten, 10)
                unit_hold = np.ones(2880) * (1 - len(names) / slots)
                for name in names:
                    unit_hold += loaded[name]["passive"] / slots
                values = unit_hold * hold_cap[selected]
                holds[selected].append(values)
                hold_cap[selected] = float(values[-1])
            for mask in range(32):
                selected = bool(mask & 1)
                gate = mask >> 1
                names, slots = (chosen, 10) if selected else (marketcap_ten, 10)
                unit = np.ones(2880) * (1 - len(names) / slots)
                matched = unit.copy()
                for name in names:
                    unit += loaded[name]["equity"][gate] / slots
                    matched += loaded[name]["exposure_matched_passive"][gate] / slots
                values = unit * accumulators[mask]
                history[mask].append(values)
                accumulators[mask] = float(values[-1])
                matched_values = matched * matched_cap[mask]
                matched_history[mask].append(matched_values)
                matched_cap[mask] = float(matched_values[-1])
            for name, starting_capital in control_cap.items():
                slots = 50 if name.startswith("all50") else max(1, len(eligible))
                unit = np.ones(2880) * (1 - len(eligible) / slots)
                for sleeve_data in loaded.values():
                    sleeve = sleeve_data["passive"] if name.endswith("hold") else sleeve_data["equity"][0]
                    unit += sleeve / slots
                values = unit * starting_capital
                control_history[name].append(values)
                control_cap[name] = float(values[-1])
        baseline = np.concatenate(history[0])
        baseline_daily = np.diff(np.log(np.r_[10000, baseline[95::96]]))
        for mask in range(32):
            curve = np.concatenate(history[mask])
            matched = np.concatenate(matched_history[mask])
            hold = np.concatenate(holds[bool(mask & 1)])
            curve_key = f"{scenario}_m{mask:02d}"
            curves_all[curve_key] = curve
            curves_all[curve_key + "_matched"] = matched
            daily = np.diff(np.log(np.r_[10000, curve[95::96]]))
            daily_all.append(daily - baseline_daily)
            rows.append({"scenario": scenario, "mask": mask, "factors": [name for i, name in enumerate(("selection", "frequency", "shape", "time", "H1")) if mask & (1 << i)], **performance(curve), "matched_hold_return_pct": performance(matched)["return_pct"], "same_selection_hold_return_pct": performance(hold)["return_pct"], "gain_vs_unfiltered_grid_pp": performance(curve)["return_pct"] - performance(baseline)["return_pct"]})
        for selected in (False, True):
            curve = np.concatenate(holds[selected])
            curves_all[f"{scenario}_hold_{int(selected)}"] = curve
            comparisons.append({"scenario": scenario, "baseline": "selected_hold" if selected else "marketcap10_hold", **performance(curve)})
        for name in control_cap:
            curve = np.concatenate(control_history[name])
            curves_all[f"{scenario}_{name}"] = curve
            comparisons.append({"scenario": scenario, "baseline": name, **performance(curve)})
    p, intervals = bootstrap_differences(np.column_stack(daily_all))
    corrected = holm(p)
    for i, row in enumerate(rows):
        row.update(p_vs_grid=float(p[i]), holm_p_vs_grid=float(corrected[i]), daily_log_gain_95pct=intervals[:, i].tolist())
    np.savez_compressed(out / "portfolio_curves.npz", timestamp=ts, **curves_all)
    pd.DataFrame(coins).to_csv(out / "coin_fold_metrics.csv", index=False)
    save(out / "selection.json", selection)
    save(out / "portfolios.json", rows)
    save(out / "baselines.json", comparisons)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase", choices=("diagnostics", "grid", "aggregate"), required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    universe = json.loads((args.data / "universe.json").read_text())
    if args.phase == "diagnostics":
        with ProcessPoolExecutor(args.workers) as pool:
            futures = [pool.submit(diagnostics, (args.data, args.output, a, 9999)) for a in universe["assets"]]
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                print(f"diagnostics {i}/51 {result['symbol']}", flush=True)
        results = [json.loads((args.output / f"{a['symbol']}_diagnostics.json").read_text()) for a in universe["assets"]]
        save(args.output / "clock_tests.json", adjust_clock_family([row for x in results for row in x["clock"]]))
        save(args.output / "cycle_summary.json", [row for x in results for row in x["cycle_summary"]])
    elif args.phase == "grid":
        with ProcessPoolExecutor(args.workers) as pool:
            futures = [pool.submit(grid_coin, (args.data, args.output, a)) for a in universe["assets"] if a["directional50"]]
            for i, future in enumerate(as_completed(futures), 1):
                result = future.result()
                print(f"grid {i}/50 {result['symbol']} eligible={result['eligible']}", flush=True)
    else:
        for asset in universe["assets"]:
            diagnostics_result = json.loads((args.output / f"{asset['symbol']}_diagnostics.json").read_text())
            if diagnostics_result.get("binding") != binding(args.data, asset["symbol"], "diagnostics"):
                raise ValueError("diagnostic source/input binding changed")
            if diagnostics_result.get("replicates") != args.replicates:
                raise ValueError("diagnostic replicate contract changed")
            admit_inputs(args.data, asset["symbol"], "diagnostics")
        results = [json.loads((args.output / f"{a['symbol']}_grid.json").read_text()) for a in universe["assets"] if a["directional50"]]
        for result in results:
            if result.get("binding") != binding(args.data, result["symbol"], "grid"):
                raise ValueError("aggregation source/input binding changed")
            admit_inputs(args.data, result["symbol"], "grid")
            if any(sha(path) != checksum for path, checksum in result.get("outputs", {}).items()):
                raise ValueError("aggregation artifact checksum changed")
        portfolios(args.output, universe["assets"], results)
        source = [Path(__file__), Path(__file__).with_name("coinbase50_grid.py"), Path(__file__).with_name("coinbase50_stats.py"), Path(__file__).with_name("coinbase50_data.py"), Path("research/shape_study.py"), Path("research/zec_cycles.py"), *sorted(Path("backtester/core").glob("*.py"))]
        save(args.output / "manifest.json", {"version": 1, "status": "complete", "data": str(args.data.resolve()), "universe_sha256": sha(args.data / "universe.json"), "protocol_sha256": sha(args.data / "protocol.json"), "dependencies": {str((args.data.parent / "dependencies.txt").resolve()): sha(args.data.parent / "dependencies.txt")}, "cell_bindings": {x["symbol"]: x["binding"] for x in results}, "source": {str(x.resolve()): sha(x) for x in source}, "artifacts": {str(x.resolve()): sha(x) for x in sorted(args.output.iterdir()) if x.is_file() and x.name != "manifest.json"}, "grid_eligible": [x["symbol"] for x in results if x["eligible"]], "grid_excluded": [x for x in results if not x["eligible"]]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

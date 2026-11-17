"""Repeat the candle-supported ZEC study on a fresh, frozen week of another coin.

python -m research.coin_week --coin ETH --output /absolute/path/to/new-study
python -m research.coin_week --coin ETH --output /absolute/path/to/new-study --resume

Acquisition is an explicit phase; analysis and verification can run offline.
This module never changes a recorder, model owner, paper trial or live account.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import platform
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from research import coin_week_correlations as correlations
from research import zec_expanded as expanded
from research import zec_granular as granular
from research.coin_week_data import (
    PROVIDERS,
    analysis_window,
    arrays,
    coin_symbol,
    digest,
    download,
    frame_from,
    load,
    resample,
    save,
    verify_snapshot,
    week_bounds,
)
from research.reversal_history import iso
from research.zec_cycles import fit_forecast, holm, null_test
from research.zec_ensembles import batch_spot, canonical_replay, verify_batch_parity

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2.0.0"
STEPS = {"1m": 60, "5m": 300, "10m": 600, "1h": 3600}
FEES = (10, 15, 25, 60)
WINDOWS = ("full", "validation", "test")

# Each source study is mapped before results are seen. Similar numerical models
# are labelled transfers, rather than represented as captured execution replays.
STUDIES = (
    (
        "ensemble",
        "research/zec_ensembles.py",
        "transferred",
        "Full expanded catalogue includes the original ensembles; fixed chronological selection, next-open spot accounting and cash/passive controls. Daily DSR and ten prospective accounts are not established by this week.",
    ),
    (
        "expanded",
        "research/zec_expanded.py",
        "transferred",
        "All published spot templates, six causal shape/frequency/control modes, 1m/5m/10m/1h; OHLC next-open execution replaces the captured-book model explicitly.",
    ),
    (
        "fee_sensitivity",
        "research/zec_granular.py",
        "transferred",
        "10/15/25/60bps per fill plus 2bps execution cost; cash and passive pay the same modelled costs.",
    ),
    (
        "captured_book",
        "research/zec_granular.py",
        "unavailable_input",
        "Spot candles cannot reproduce receive-time trades, visible liquidity, connection telemetry, delayed book fills or book-conditioned exits.",
    ),
    (
        "volty",
        "backtester/core/volty.py",
        "transferred",
        "All 50 frozen Volty settings, all four cadences, all fee scenarios and three OHLC path sensitivities. Synthetic 1x long/short with declared carry, not actual perp execution.",
    ),
    (
        "grid_dca",
        "research/zec_lifecycle.py",
        "transferred",
        "All 20 frozen grid/DCA configurations use canonical pessimistic OHLC simulators on supported 1m/5m/1h bars. Captured-book gates and custom 10m lifecycle execution remain unavailable.",
    ),
    (
        "cycles",
        "research/zec_cycles.py",
        "transferred",
        "Whole-search price/return spectra against sign and block nulls, confirmed pivot spacings, and earlier-fitted harmonic/linear/persistence forecasts.",
    ),
    (
        "shape_routing",
        "research/shape_study.py",
        "insufficient_history",
        "The original 1h/6h/1d routing requires post-warmup selection history absent from one week; expanded causal shape gates still run on all four cadences.",
    ),
    (
        "reversal_excursions",
        "research/crosscoin_reversals.py",
        "transferred",
        "Frozen one/two-up-bar definitions, intrabar/midpoint/close policies, 5/10/20m horizons, positive-volume/all-present masks, nonoverlap controls and unconditional baselines.",
    ),
    (
        "reversal_shapes",
        "research/reversal_shapes.py",
        "transferred",
        "Frozen UU/DD and causal shape rules on 5/10/15/20m with train/validation/test selection and cost scenarios.",
    ),
    (
        "two_bar_reversal",
        "research/zec-two-bar-reversal-20261114/analysis.py",
        "transferred",
        "UU/DD conditional direction and shape counts are covered by the reusable reversal-shape study; no hindsight extrema become fills.",
    ),
    (
        "oracle_second_turn",
        "research/reversal_second_turn.py",
        "unavailable_input",
        "Independent Oracle USDC candles, 200ms barrier evidence and qualified execution are absent; USD spot candles cannot substitute for them.",
    ),
    (
        "oracle_mtf",
        "research/mtf_reversal.py",
        "unavailable_input",
        "The original Oracle-basis multi-timeframe model and barrier study require their own source history. Spot shape/reversal observations are reported separately.",
    ),
    (
        "exit50",
        "research/exit50_backtest.py",
        "unavailable_input",
        "200ms sub-minute samples, persisted quote/fee evidence and historical keeper paths are absent from minute spot OHLCV.",
    ),
    (
        "daily_cpcv",
        "research/cross_asset_cpcv.py",
        "insufficient_history",
        "Seven daily bars cannot reproduce the long-history fixed-SOL-parameter CPCV reference test. No timeframe relabelling or per-coin retuning is performed.",
    ),
    (
        "top50_factorial",
        "research/coinbase50_grid.py",
        "unavailable_universe",
        "One target plus BTC/ZEC is not the original historical eligible top50 universe. Coin ranking, portfolio topology and news-event studies need separate inputs.",
    ),
)


def identity() -> dict:
    paths = set((ROOT / "backtester/core").rglob("*.py"))
    paths.update((ROOT / "backtester/strategy_cards").rglob("*.md"))
    paths.update(ROOT / row[1] for row in STUDIES)
    paths.update(
        ROOT / p
        for p in (
            "research/coin_week.py",
            "research/coin_week_data.py",
            "research/coin_week_correlations.py",
            "research/coin_week_reports.py",
            "research/coin_week_batch.py",
            "soltui/bgqueue.py",
            "research/reversal_history.py",
            "research/zec_reversal_excursions.py",
            "backtester/voltycli.py",
        )
    )
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "files": {
            str(p.relative_to(ROOT)): digest(p.read_bytes())
            for p in sorted(paths)
            if p.is_file()
        },
    }


def coverage() -> list:
    return [
        {
            "study": name,
            "source": path,
            "source_sha256": digest((ROOT / path).read_bytes()),
            "status": status,
            "scope": note,
        }
        for name, path, status, note in STUDIES
    ]


def write_table(path: Path, rows: list) -> None:
    pd.DataFrame(rows).to_csv(
        path, index=False, compression={"method": "gzip", "mtime": 0}
    )


def input_hashes(output: Path) -> dict:
    return {
        str(p.relative_to(output)): digest(p.read_bytes())
        for p in sorted((output / "inputs").glob("*.json.zlib"))
    }


def frozen_inputs(output: Path) -> dict:
    """Freeze before loading data, and refuse any later input replacement."""
    path = output / "run-inputs.json"
    current = input_hashes(output)
    plan_hash = digest((output / "run-plan.json.zlib").read_bytes())
    if path.exists():
        frozen = load(path)
        if frozen["plan_sha256"] != plan_hash:
            raise ValueError("input ledger belongs to another frozen plan")
        if frozen["input_sha256"] != current:
            raise ValueError("checkpoint input snapshot changed")
    else:
        save(path, {"plan_sha256": plan_hash, "input_sha256": current})
    return current


def bind_files(output: Path, marker: Path, files: list[Path]) -> None:
    save(
        marker,
        {
            "plan_sha256": digest((output / "run-plan.json.zlib").read_bytes()),
            "input_sha256": frozen_inputs(output),
            "files": {
                str(p.relative_to(output)): digest(p.read_bytes()) for p in files
            },
        },
    )


def verify_binding(output: Path, marker: Path) -> bool:
    if not marker.exists():
        return False
    binding = load(marker)
    if binding["plan_sha256"] != digest((output / "run-plan.json.zlib").read_bytes()):
        raise ValueError("checkpoint belongs to another frozen plan")
    if binding["input_sha256"] != frozen_inputs(output):
        raise ValueError("checkpoint input snapshot changed")
    for name, sha in binding["files"].items():
        if digest((output / name).read_bytes()) != sha:
            raise ValueError(f"checkpoint artifact changed: {name}")
    return True


def evaluation_windows(frame: pd.DataFrame, plan: dict, step: int) -> dict:
    first, last = plan["start"], plan["end_exclusive"]
    span = last - first
    cuts = {
        "full": (first, last),
        "validation": (first + int(0.6 * span), first + int(0.8 * span)),
        "test": (first + int(0.8 * span), last),
    }
    result = {}
    for name, (left, right) in cuts.items():
        indices = np.flatnonzero(
            (frame.timestamp.to_numpy() >= left)
            & (frame.timestamp.to_numpy() + step <= right)
        )
        if len(indices) >= 3:
            result[name] = (int(indices[0]), int(indices[-1]) + 1)
    return result


def compute_signals(job):
    spec, bars, step = job
    return granular.member_signals(
        spec, bars, np.ones(len(bars["ts"]), dtype=bool), step
    )


def scalar_spot_check(values, bars, interval, threshold, multiplier):
    """Check pure spot arithmetic with the canonical single-policy engine.

    ArrayPolicy depends only on bar index. For custom 10m candles the check
    alone uses an artificial 1m clock, because the canonical engine has no 10m
    enum. No prices or targets change, no time-dependent cost is enabled, and
    no timestamp/annualized metric from this check is published as evidence.
    """
    if interval == "10m":
        bars = {**bars, "ts": int(bars["ts"][0]) + np.arange(len(values)) * 60}
        interval = "1m"
    return canonical_replay(
        values, bars, interval, threshold=threshold, cost_multiplier=multiplier
    )


def strategy_matrix(
    frame: pd.DataFrame, interval: str, plan: dict, output: Path, workers: int
) -> dict:
    """Reuse the frozen policy rules and the parity-tested vector spot accountant."""
    from concurrent.futures import ProcessPoolExecutor

    from backtester.core.zec_ensemble import spec_id
    from research.coin_week_reports import resolved_policy

    step = STEPS[interval]
    bars = arrays(frame)
    valid = np.ones(len(frame), dtype=bool)
    windows = evaluation_windows(frame, plan, step)
    candidates = plan["catalogue"]["candidates"]
    if plan["candidate_limit"]:
        candidates = candidates[: plan["candidate_limit"]]
    specs = {}
    for row in candidates:
        cfg = row["config"]
        for spec in [
            *cfg["members"],
            *([cfg["gate"]] if "gate" in cfg else []),
            *([cfg["fallback"]] if "fallback" in cfg else []),
        ]:
            specs[spec_id(spec)] = spec
    signals, eligible = {}, {}
    cache = output / f"signals-{interval}.npz"
    keys = list(specs)
    cache_proof = output / f"signals-{interval}-binding.json"
    if cache.exists() and verify_binding(output, cache_proof):
        with np.load(cache, allow_pickle=False) as data:
            for j, key in enumerate(keys):
                signals[key], eligible[key] = data[f"s{j}"], data[f"e{j}"]
    else:
        jobs = [(specs[k], bars, step) for k in keys]
        if workers == 1:
            computed = map(compute_signals, jobs)
            for key, (value, mask) in zip(keys, computed):
                signals[key], eligible[key] = value, mask
        else:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                for j, (key, (value, mask)) in enumerate(
                    zip(keys, pool.map(compute_signals, jobs, chunksize=4)), 1
                ):
                    signals[key], eligible[key] = value, mask
                    if j % 50 == 0:
                        print(f"{interval}: components {j}/{len(keys)}", flush=True)
        np.savez_compressed(
            cache,
            **{f"s{j}": signals[k] for j, k in enumerate(keys)},
            **{f"e{j}": eligible[k] for j, k in enumerate(keys)},
        )
        bind_files(output, cache_proof, [cache])
    contexts_path = output / f"contexts-{interval}.npz"
    fits_path = output / f"frequency-{interval}.json.zlib"
    contexts_proof = output / f"contexts-{interval}-binding.json"
    if (
        contexts_path.exists()
        and fits_path.exists()
        and verify_binding(output, contexts_proof)
    ):
        with np.load(contexts_path, allow_pickle=False) as data:
            ctx = dict(data)
        frequency = load(fits_path)
    else:
        print(f"{interval}: causal shapes and frozen cycle fits", flush=True)
        ctx, fits, tests = expanded.contexts(
            bars, valid, step, replicates=plan["replicates"]
        )
        frequency = {"fits": fits, "tests": tests}
        np.savez_compressed(contexts_path, **ctx)
        save(fits_path, frequency)
        bind_files(output, contexts_proof, [contexts_path, fits_path])
    raw, metadata, available = [], [], []
    for row in candidates:
        cfg = row["config"]
        # A data-derived committee weight must be fitted before validation starts.
        warm = max(
            (
                int(np.argmax(eligible[spec_id(s)]))
                if eligible[spec_id(s)].any()
                else len(frame)
            )
            for s in [
                *cfg["members"],
                *([cfg["gate"]] if "gate" in cfg else []),
                *([cfg["fallback"]] if "fallback" in cfg else []),
            ]
        )
        fitted_end = max(warm + 64, 256)
        if cfg.get("weighting") and fitted_end > windows.get("validation", (0, 0))[0]:
            values, mask = np.full(len(frame), np.nan), np.zeros(len(frame), dtype=bool)
        else:
            values, mask = granular.policy_signal(cfg, signals, eligible, valid)
        for mode in expanded.MODES:
            gate = expanded.gate_for(mode, ctx, cfg)
            ok = mask & np.isfinite(gate)
            raw.append(np.where(ok, values * np.nan_to_num(gate), 0.0))
            available.append(ok)
            metadata.append(
                {
                    "candidate_id": row["candidate_id"],
                    "family": row["family"],
                    "mode": mode,
                    "rebalance_threshold": cfg["rebalance_threshold"],
                }
            )
    for name, target in (("cash", 0.0), ("buy_and_hold", 1.0)):
        raw.append(np.full(len(frame), target))
        available.append(np.ones(len(frame), dtype=bool))
        metadata.append(
            {
                "candidate_id": name,
                "family": "benchmark",
                "mode": "baseline",
                "rebalance_threshold": 0.0,
            }
        )
    targets, masks = np.stack(raw), np.stack(available)
    del raw, available
    rows, selected = [], []
    thresholds = np.array([r["rebalance_threshold"] for r in metadata])
    for fee in FEES:
        by_split = {}
        for split, (left, right) in windows.items():
            print(
                f"{interval}: {len(metadata)} policies, {fee}bps fee, {split}",
                flush=True,
            )
            result = batch_spot(
                targets[:, left:right],
                {k: v[left:right] for k, v in bars.items()},
                "1m",
                thresholds=thresholds,
                cost_multiplier=(fee + 2) / 12,
            )
            records = []
            for j, metrics in enumerate(result):
                count = int(masks[j, left:right].sum())
                row = {
                    **metadata[j],
                    "interval": interval,
                    "fee_bps_per_fill": fee,
                    "slippage_bps_per_fill": 2,
                    "split": split,
                    "eligible_bars": count,
                    "status": "completed" if count >= 3 else "insufficient_history",
                    "total_return": metrics["total_return"],
                    "max_drawdown": metrics["max_drawdown"],
                    "trade_count": metrics["trade_count"],
                    "fills": metrics["fills"],
                    "total_cost_quote": metrics["total_fees"],
                    "bars": metrics["bars"],
                    "start": int(bars["ts"][left]),
                    "end_exclusive": int(bars["ts"][right - 1]) + step,
                }
                rows.append(row)
                records.append(row)
            by_split[split] = records
        if "validation" in by_split and "test" in by_split:
            eligible_rows = [
                (j, r)
                for j, r in enumerate(by_split["validation"])
                if r["status"] == "completed"
                and r["trade_count"] >= 10
                and r["family"] != "benchmark"
            ]
            if eligible_rows:
                j, winner = min(
                    eligible_rows,
                    key=lambda item: (
                        -item[1]["total_return"],
                        item[1]["candidate_id"],
                        item[1]["mode"],
                    ),
                )
                winner_config = next(
                    row["config"]
                    for row in candidates
                    if row["candidate_id"] == winner["candidate_id"]
                )
                selected.append(
                    {
                        "interval": interval,
                        "fee_bps_per_fill": fee,
                        "candidate_id": winner["candidate_id"],
                        "mode": winner["mode"],
                        "config": winner_config,
                        "resolved_config": resolved_policy(winner_config, step),
                        "selection": "validation net return; at least ten validation exits; deterministic tie-break; no test ranking",
                        "splits": {s: records[j] for s, records in by_split.items()},
                    }
                )
                # Bind one independently replayed final selection to the same
                # accounting path before treating its P&L as a result.
                lo, hi = windows["test"]
                canonical = scalar_spot_check(
                    targets[j, lo:hi],
                    {k: v[lo:hi] for k, v in bars.items()},
                    interval,
                    threshold=thresholds[j],
                    multiplier=(fee + 2) / 12,
                )
                if (
                    abs(canonical["total_return"] - by_split["test"][j]["total_return"])
                    > 1e-8
                ):
                    raise ValueError("selected policy canonical P&L mismatch")
    write_table(output / f"strategies-{interval}.csv.gz", rows)
    save(output / f"selected-{interval}.json", selected)
    paired = []
    lookup = {
        (r["candidate_id"], r["mode"], r["fee_bps_per_fill"], r["split"]): r
        for r in rows
    }
    for r in rows:
        control = {"shape": "shape_control", "frequency": "frequency_control"}.get(
            r["mode"]
        )
        if control:
            c = lookup[(r["candidate_id"], control, r["fee_bps_per_fill"], r["split"])]
            if r["status"] == c["status"] == "completed":
                paired.append(
                    {
                        "candidate_id": r["candidate_id"],
                        "mode": r["mode"],
                        "interval": interval,
                        "fee_bps_per_fill": r["fee_bps_per_fill"],
                        "split": r["split"],
                        "return_difference": r["total_return"] - c["total_return"],
                    }
                )
    write_table(output / f"paired-{interval}.csv.gz", paired)
    stats = []
    for mode in ("shape", "frequency"):
        for fee in FEES:
            diffs = [
                r["return_difference"]
                for r in paired
                if r["mode"] == mode
                and r["fee_bps_per_fill"] == fee
                and r["split"] == "test"
            ]
            if diffs:
                stats.append(
                    {
                        "interval": interval,
                        "mode": mode,
                        "fee_bps_per_fill": fee,
                        "pairs": len(diffs),
                        "median_test_return_difference": float(np.median(diffs)),
                        "fraction_positive": float(np.mean(np.array(diffs) > 0)),
                    }
                )
    return {
        "interval": interval,
        "bars": len(frame),
        "templates": len(candidates),
        "policies_including_controls": len(metadata),
        "rows": len(rows),
        "status_counts": dict(Counter(r["status"] for r in rows)),
        "selected": selected,
        "paired_test_descriptive": stats,
        "frequency_tests": frequency["tests"],
        "shape_counts": dict(Counter(ctx["shape"].tolist())),
    }


def cycle_study(frame: pd.DataFrame, interval: str, plan: dict) -> dict:
    step = STEPS[interval]
    if len(frame) < 64:
        return {
            "interval": interval,
            "status": "insufficient_history",
            "tests": [],
            "spectra": [],
            "reason": "At least 64 complete bars required for spectra and a disjoint frozen forecast.",
        }
    ts, y = frame.timestamp.to_numpy(float), np.log(frame.close.to_numpy(float))
    tests, spectra, spacings, points = null_test(
        ts,
        y,
        step,
        replicates=plan["replicates"],
        seed=correlations.SEED + step,
        spacing_reference=True,
    )
    cut = int(len(frame) * 0.6)
    train, future = frame.iloc[:cut], frame.iloc[cut:]
    curves = fit_forecast(train, future, step)
    actual = np.log(future.close.to_numpy(float))
    # fit_forecast predictions are in log-price units.
    forecasts = {
        k: {"log_price_rmse": float(np.sqrt(np.mean((curves[k] - actual) ** 2)))}
        for k in ("cycle", "linear", "persistence")
    }
    return {
        "interval": interval,
        "tests": tests,
        "spectra": spectra,
        "confirmed_pivot_spacing_descriptive": spacings,
        "pivots": points,
        "frozen_forecast": {
            "train_through": int(train.timestamp.iloc[-1]) + step,
            "test_from": int(future.timestamp.iloc[0]),
            "period_seconds": curves["period_seconds"],
            "metrics": forecasts,
        },
    }


def special_models(frame: pd.DataFrame, interval: str, plan: dict) -> dict:
    from backtester.core.dcasim import DcaConfig, run_dca_backtest
    from backtester.core.gridsim import GridConfig, run_grid_backtest
    from backtester.core.types import CostConfig
    from backtester.core.volty import VoltyConfig, simulate
    from research.zec_lifecycle import lifecycle_configs

    bars, step = arrays(frame), STEPS[interval]
    volty_bars = {"timestamp" if k == "ts" else k: v for k, v in bars.items()}
    windows = evaluation_windows(frame, plan, step)
    rows = []
    for fee in FEES:
        for split, (left, right) in windows.items():
            for length, multiple in granular.GRID:
                cfg = VoltyConfig(
                    length=length,
                    atr_mult=multiple,
                    fee_bps=fee,
                    slippage_bps=2,
                    carry_bps_hour=0.1,
                )
                for path in ("nearest", "high-first", "low-first"):
                    metrics = simulate(
                        volty_bars, cfg, step, start=left, end=right, path=path
                    )
                    rows.append(
                        {
                            "family": "volty_ohlc_synthetic_1x",
                            "interval": interval,
                            "split": split,
                            "fee_bps_per_fill": fee,
                            "length": length,
                            "atr_multiple": multiple,
                            "path": path,
                            **{k: v for k, v in metrics.items() if k != "equity"},
                        }
                    )
            if interval == "10m":
                continue  # The canonical lifecycle engines have no 10m cadence.
            for cfg in lifecycle_configs():
                # Grid limits use only pre-evaluation history. Full-window
                # reference limits are frozen after 48 warm-up bars.
                trade_left = (
                    max(left, 48) if cfg["kind"] == "ladder_grid_reference" else left
                )
                if right - trade_left < 3:
                    continue
                part = {k: v[trade_left:right] for k, v in bars.items()}
                costs = CostConfig(fee_bps=fee, slippage_bps=2)
                if cfg["kind"] == "ladder_grid_reference":
                    past = frame.iloc[max(0, trade_left - 48) : trade_left]
                    if cfg["band"] == "training_range":
                        low, high = float(past.low.min()), float(past.high.max())
                    else:
                        low, high = (
                            float(past.close.iloc[-1]) * 0.95,
                            float(past.close.iloc[-1]) * 1.05,
                        )
                    if high <= low:
                        continue
                    config = GridConfig(
                        low,
                        high,
                        cfg["rungs"],
                        10000 / cfg["rungs"],
                        spacing=cfg["spacing"],
                        deadband_bps=25,
                    )
                    result = run_grid_backtest(
                        config, part, interval=interval, costs=costs
                    )
                    trades = result.round_trips
                else:
                    config = DcaConfig(**cfg["params"])
                    result = run_dca_backtest(
                        config,
                        part,
                        initial_capital=10000,
                        interval=interval,
                        costs=costs,
                    )
                    trades = result.deals_completed
                rows.append(
                    {
                        "family": cfg["kind"] + "_ohlc",
                        "interval": interval,
                        "split": split,
                        "fee_bps_per_fill": fee,
                        "config": json.dumps(cfg, sort_keys=True),
                        "return": result.metrics.total_return,
                        "trades": trades,
                        "fees": result.fees_paid_usd,
                        "slippage": result.slippage_paid_usd,
                        "max_drawdown": result.metrics.max_drawdown,
                    }
                )
    return {
        "rows": rows,
        "limits": "OHLC reference models; no displayed depth, historical quote or keeper evidence; Volty fees/slippage and 0.1bps/hour carry are scenarios.",
    }


def legacy_text_report(summary: dict) -> str:
    p = summary["plan"]
    corr = summary["correlations"]
    lines = [
        f"# {p['coin']} weekly candle study",
        "",
        "Version: 1.0.0",
        f"UTC window: {iso(p['start'])} to {iso(p['end_exclusive'])} (exclusive).",
        f"Source: {p['venue']} {p['coin']}/{p['quote']}, {summary['minutes']:,} completed one-minute bars.",
        "",
        "This is an exploratory transfer of the ZEC candle studies. It does not qualify an executable edge or a live trading change.",
        "",
        "## Scope and controls",
        "",
        f"The frozen catalogue contains {p['templates']:,} spot templates. The run uses all six baseline/shape/frequency/control modes on 1m, 5m, 10m and 1h bars. Fees are 10/15/25/60bps per fill plus 2bps modelled execution cost. Decisions use closed bars and spot exposure fills at the next open. Fresh accounts evaluate the chronological 60/20/20 windows; the selected policy is chosen only by validation return with at least ten validation exits.",
        "",
        f"Strategy matrix: {summary['strategy_rows']:,} rows, including {summary['strategy_completed']:,} completed evaluations. Special Volty/grid/DCA models: {summary['special_rows']:,} rows. A completed evaluation is not evidence of profitability. Thousands of overlapping candidates are not independent trials.",
        "",
        "Captured receive-time book replay, Oracle second-turn/barrier/exit50 studies, the historical top50 universe and daily CPCV need unavailable inputs or longer history. The original hourly/six-hour/daily shape router also lacks its required selection history. Exact transferred scopes and exclusions are in coverage.json.",
        "",
        "## Correlations",
        "",
        f"Searched {len(corr['features'])} causal features across six future-return horizons. Outcomes do not overlap within a horizon and are purged at split ends. All validation and test feature/horizon tests share an approximate 60-minute block-permutation maximum-statistic correction ({p['replicates']:,} replicates). Spearman values and contemporaneous correlations are descriptive.",
        "",
        f"Corrected test associations at p <= 0.05: **{corr['corrected_test_findings']}**. These are associations under an approximate stationary null, not causal effects or net trading profits.",
        "",
        "| Same-minute return comparison | Pearson r | Observations |",
        "|---|---:|---:|",
    ]
    for row in corr["contemporaneous"]:
        lines.append(
            f"| {p['coin']} / {row['reference']} | {row['pearson_descriptive']:.4f} | {row['n']:,} |"
        )
    lines += [
        "",
        "Same-minute co-movement does not establish that the reference coin leads the target.",
        "",
        "The following shortlist was fixed by absolute training correlation, before inspecting validation or test:",
        "",
        "| Feature | Horizon | Train r | Validation r | Test r | Corrected test p |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in corr["training_only_shortlist"]:
        s = row["splits"]
        number = lambda x: "unavailable" if x is None else f"{x:.4f}"
        lines.append(
            f"| {row['feature']} | {row['horizon_minutes']}m | {number(s['train']['pearson'])} | {number(s['validation']['pearson'])} | {number(s['test']['pearson'])} | {number(s['test'].get('p_maxT_validation_and_test'))} |"
        )
    lines += [
        "",
        "## Frozen validation selections",
        "",
        "| Cadence | Fee bps/fill | Policy | Mode | Validation return | Test return | Test exits |",
        "|---|---:|---|---|---:|---:|---:|",
    ]
    for result in summary["strategies"]:
        for row in result["selected"]:
            a, b = row["splits"]["validation"], row["splits"]["test"]
            lines.append(
                f"| {row['interval']} | {row['fee_bps_per_fill']} | {row['candidate_id']} | {row['mode']} | {a['total_return']:.2%} | {b['total_return']:.2%} | {b['trade_count']} |"
            )
    lines += [
        "",
        "Rows without ten validation exits cannot select a winner. Test results are reported for the frozen selection and never used to rerank it. These short-window returns have no multiple-search profit qualification.",
        "",
        "## Cycles and causal controls",
        "",
        f"Across global spectra and rolling training-prefix fits, {summary['cycle_tests']:,} whole-search null tests received one Holm correction. Minimum corrected p-value: {summary['minimum_cycle_p_holm']:.6f}. The smallest attainable first Holm p-value with this test count and replicate budget is {summary['cycle_resolution_floor']:.6f}. This cycle significance result is resolution-limited and inconclusive when that floor exceeds 0.05; it is not evidence against a cycle. Short-window selected periods and retrospective pivot spacing do not establish a stable clock.",
        "",
        "## Limits and reproduction",
        "",
        "One week contains very few independent market regimes. Results reuse existing ZEC hypotheses and modelled costs; observed spreads, funding, depth, latency and fills are absent. Approximate permutation inference assumes sufficiently stable dependence. Monte Carlo resolution can prevent significance after broad corrections. Annualized Sharpe ratios are deliberately omitted from the weekly summary.",
        "",
        "Raw provider pages and normalized candles are retained together in inputs/*.json.zlib. run-plan.json.zlib freezes the complete card/queue census, templates, source hashes, options and exclusion mapping. manifest.json binds all generated artifacts. The script verifies raw-page normalization, immutable artifacts and report arithmetic offline.",
        "",
        "```bash",
        f"python -m research.coin_week --coin {p['coin']} --output /absolute/path/to/new-study",
        f"python -m research.coin_week --coin {p['coin']} --output /absolute/path/to/new-study --resume",
        "python -m research.coin_week --output /absolute/path/to/new-study --phase verify",
        "```",
        "",
    ]
    return "\n".join(lines)


def text_report(summary: dict) -> str:
    if summary.get("version", "1.0.0") == "1.0.0":
        return legacy_text_report(summary)
    from research.coin_week_reports import render_report

    return render_report(summary)


def plot_findings(
    primary: pd.DataFrame, sources: dict, corr: dict, output: Path
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(
        2,
        1,
        figsize=(12, 12),
        layout="constrained",
        gridspec_kw={"height_ratios": [1, 2]},
    )
    for coin, source in sources.items():
        frame = frame_from(source)
        axes[0].plot(
            pd.to_datetime(frame.timestamp, unit="s", utc=True),
            frame.close / frame.close.iloc[0] * 100,
            label=f"{coin}/{source['quote']}",
            linewidth=0.8,
        )
    axes[0].set(
        title="Actual analysis window: native market closes, first observed close = 100",
        ylabel="Rebased price",
    )
    axes[0].legend()
    names = corr["features"]
    matrix = np.full((len(names), len(correlations.HORIZONS)), np.nan)
    significant = np.zeros_like(matrix, dtype=bool)
    for row in corr["rows"]:
        if row["split"] == "test" and row["pearson"] is not None:
            i, j = (
                names.index(row["feature"]),
                correlations.HORIZONS.index(row["horizon_minutes"]),
            )
            matrix[i, j] = row["pearson"]
            significant[i, j] = row.get("p_familywise", 1) <= 0.05
    finite = np.abs(matrix[np.isfinite(matrix)])
    limit = max(0.1, float(finite.max()) if len(finite) else 0.1)
    heat = axes[1].imshow(matrix, aspect="auto", cmap="RdBu", vmin=-limit, vmax=limit)
    axes[1].set(
        yticks=range(len(names)),
        yticklabels=names,
        xticks=range(len(correlations.HORIZONS)),
        xticklabels=[f"{n}m" for n in correlations.HORIZONS],
        xlabel=f"Future {next(iter(sources))}/{next(iter(sources.values()))['quote']} return horizon",
        title="Final-window Pearson correlations (* batch-family corrected p <= 0.05)",
    )
    for i, j in zip(*np.where(significant)):
        axes[1].text(j, i, "*", ha="center", va="center")
    figure.colorbar(heat, ax=axes[1], label="Pearson r")
    figure.savefig(output / "correlations.png", dpi=160)
    plt.close(figure)


def verify_run(output: Path) -> dict:
    manifest = load(output / "manifest.json")
    for name, sha in manifest["artifacts"].items():
        if digest((output / name).read_bytes()) != sha:
            raise ValueError(f"artifact integrity mismatch: {name}")
    plan = load(output / "run-plan.json.zlib")
    for coin in [plan["coin"], *plan["references"]]:
        verify_snapshot(
            load(output / "inputs" / f"{coin}.json.zlib"),
            coin,
            plan["start"],
            plan["end_exclusive"],
            plan["quote"],
        )
    summary = load(output / "summary.json")
    if summary.get("version") == "2.0.0":
        expected_plan = {k: plan[k] for k in summary["plan"]}
        primary = load(output / "inputs" / f"{plan['coin']}.json.zlib")
        _, window = analysis_window(
            frame_from(primary),
            plan["start"],
            plan["end_exclusive"],
            plan["gap_policy"],
        )
        if (
            summary["plan"] != expected_plan
            or summary["analysis_window"] != window
            or summary["market"]
            != {
                "base": plan["coin"],
                "quote": plan["quote"],
                "product": primary["product"],
                "venue": plan["venue"],
                "kind": "native spot market candles",
                "initial_reference_equity_quote": 10000,
            }
        ):
            raise ValueError("summary market, plan or analysis window mismatch")
        result = load(output / "correlations.json.zlib")
        if summary["correlations"] != {k: v for k, v in result.items() if k != "rows"}:
            raise ValueError("correlation summary mismatch")
        for row in result["rows"]:
            if "p_maxT_validation_and_test" in row and row["p_familywise"] != min(
                1.0,
                row["p_maxT_validation_and_test"]
                * plan.get("correlation_family_multiplier", 1),
            ):
                raise ValueError("correlation batch correction mismatch")
        if result["corrected_test_findings"] != sum(
            r["split"] == "test" and r.get("p_familywise", 1) <= 0.05
            for r in result["rows"]
        ):
            raise ValueError("corrected correlation count mismatch")
    if (output / "report.md").read_text() != text_report(summary):
        raise ValueError("report no longer reproduces from bound summary")
    count = sum(len(pd.read_csv(output / f"strategies-{i}.csv.gz")) for i in STEPS)
    if count != summary["strategy_rows"]:
        raise ValueError("strategy result count mismatch")
    return {
        "status": "verified",
        "artifact_count": len(manifest["artifacts"]),
        "strategy_rows": count,
    }


def analyze(plan: dict, output: Path, workers: int) -> dict:
    if identity() != plan["identity"]:
        raise ValueError(
            "source/runtime changed since run plan; use a new output directory"
        )
    frozen_inputs(output)
    sources = {
        coin: load(output / "inputs" / f"{coin}.json.zlib")
        for coin in [plan["coin"], *plan["references"]]
    }
    for coin, source in sources.items():
        verify_snapshot(
            source, coin, plan["start"], plan["end_exclusive"], plan["quote"]
        )
        if source.get("provider", "coinbase") != plan["provider"]:
            raise ValueError("all comparison inputs must use the frozen provider")
    primary, used_window = analysis_window(
        frame_from(sources[plan["coin"]]),
        plan["start"],
        plan["end_exclusive"],
        plan.get("gap_policy", "strict"),
    )
    if len(primary) < plan.get("minimum_contiguous_minutes", 1440):
        raise ValueError(
            "at least 1440 consecutive real minutes are required; acquisition preserved"
        )
    frozen_inputs(output)
    analysis_plan = {
        **plan,
        "start": used_window["analysis_start"],
        "end_exclusive": used_window["analysis_end_exclusive"],
    }
    print(
        f"Backtest market: {plan['coin']}/{plan['quote']} ({plan['venue']}); requested {used_window['requested_minutes']} minutes, analyzing {used_window['analyzed_minutes']} real consecutive minutes",
        flush=True,
    )
    print(
        f"Actual test input: {iso(analysis_plan['start'])}..{iso(analysis_plan['end_exclusive'])}; gap policy: {used_window['policy']}",
        flush=True,
    )
    analysis_sources = {}
    for coin, source in sources.items():
        rows = [
            r
            for r in source["rows"]
            if analysis_plan["start"] <= r[0] < analysis_plan["end_exclusive"]
        ]
        analysis_sources[coin] = {
            **source,
            "rows": rows,
            "study_start": analysis_plan["start"],
            "study_end_exclusive": analysis_plan["end_exclusive"],
            "input_start": analysis_plan["start"],
            "input_end_exclusive": analysis_plan["end_exclusive"],
        }
    primary.to_csv(
        output / f"{plan['coin']}-{plan['quote']}_1m.csv.gz",
        index=False,
        compression={"method": "gzip", "mtime": 0},
    )
    verify_batch_parity()
    strategies, cycles, special = [], [], []
    for interval, step in STEPS.items():
        frame = resample(primary, step)
        for stage in ("strategies", "cycles", "special"):
            checkpoint = output / f"{stage}-{interval}.json.zlib"
            proof = output / f"{stage}-{interval}-binding.json"
            if checkpoint.exists() and verify_binding(output, proof):
                result = load(checkpoint)
            else:
                before = {p for p in output.iterdir() if p.is_file()}
                print(f"{interval}: {stage}, {len(frame)} complete bars", flush=True)
                if stage == "strategies":
                    result = strategy_matrix(
                        frame, interval, analysis_plan, output, workers
                    )
                elif stage == "cycles":
                    result = cycle_study(frame, interval, analysis_plan)
                else:
                    result = special_models(frame, interval, analysis_plan)
                    write_table(output / f"special-{interval}.csv.gz", result["rows"])
                    result = {"rows": len(result["rows"]), "limits": result["limits"]}
                save(checkpoint, result)
                created = [
                    p for p in output.iterdir() if p.is_file() and p not in before
                ]
                bind_files(output, proof, list({checkpoint, *created}))
            {"strategies": strategies, "cycles": cycles, "special": special}[
                stage
            ].append(result)
    print("candle reversal and feature correlation studies", flush=True)
    from research.crosscoin_reversals import analyze as reversal_excursions
    from research.reversal_shapes import analyze as reversal_shapes

    source = analysis_sources[plan["coin"]]
    for name, callback in (
        ("reversal-excursions", reversal_excursions),
        ("reversal-shapes", reversal_shapes),
    ):
        target = output / f"{name}.json.zlib"
        proof = output / f"{name}-binding.json"
        if not (target.exists() and verify_binding(output, proof)):
            save(target, callback(source))
            bind_files(output, proof, [target])
    target = output / "correlations.json.zlib"
    proof = output / "correlations-binding.json"
    if target.exists() and verify_binding(output, proof):
        corr = load(target)
    else:
        corr = correlations.analyze(
            primary,
            {
                k: frame_from(v)
                for k, v in analysis_sources.items()
                if k != plan["coin"]
            },
            plan["replicates"],
            family_multiplier=plan.get("correlation_family_multiplier", 1),
        )
        save(target, corr)
        bind_files(output, proof, [target])
    write_table(output / "correlations.csv.gz", corr["rows"])
    plot_findings(primary, analysis_sources, corr, output)
    all_tests = [
        {"interval": item["interval"], "scope": "global", **r}
        for item in cycles
        for r in item["tests"]
    ]
    all_tests += [
        {"interval": item["interval"], "scope": "training_prefix", **r}
        for item in strategies
        for r in item["frequency_tests"]
    ]
    for row, corrected in zip(
        all_tests, holm([r["p_conservative"] for r in all_tests])
    ):
        row["p_holm"] = float(corrected)
    save(output / "cycle-tests.json.zlib", all_tests)
    summary = {
        "version": VERSION,
        "plan": {
            k: plan[k]
            for k in (
                "coin",
                "provider",
                "venue",
                "quote",
                "start",
                "end_exclusive",
                "replicates",
                "templates",
                "candidate_limit",
            )
        },
        "minutes": len(primary),
        "analysis_window": used_window,
        "market": {
            "base": plan["coin"],
            "quote": plan["quote"],
            "product": sources[plan["coin"]]["product"],
            "venue": plan["venue"],
            "kind": "native spot market candles",
            "initial_reference_equity_quote": 10000,
        },
        "strategy_rows": sum(r["rows"] for r in strategies),
        "strategy_completed": sum(
            r["status_counts"].get("completed", 0) for r in strategies
        ),
        "special_rows": sum(r["rows"] for r in special),
        "strategies": [
            {k: v for k, v in r.items() if k != "frequency_tests"} for r in strategies
        ],
        "correlations": {k: v for k, v in corr.items() if k != "rows"},
        "cycle_tests": len(all_tests),
        "minimum_cycle_p_holm": min(r["p_holm"] for r in all_tests),
        "cycle_resolution_floor": min(1.0, len(all_tests) / (plan["replicates"] + 1)),
        "coverage": plan["coverage"],
        "source_coverage": {k: v["coverage"] for k, v in sources.items()},
    }
    save(output / "summary.json", summary)
    (output / "report.md").write_text(text_report(summary))
    if identity() != plan["identity"]:
        raise ValueError("source/runtime changed during run")
    frozen_inputs(output)
    artifacts = {
        str(p.relative_to(output)): digest(p.read_bytes())
        for p in sorted(output.rglob("*"))
        if p.is_file()
        and p.name not in {"manifest.json", "run.lock"}
        and not p.name.endswith((".log", ".tmp"))
    }
    save(
        output / "manifest.json",
        {
            "schema": "weekly-coin-manifest/v1",
            "version": VERSION,
            "artifacts": artifacts,
        },
    )
    return summary


def make_plan(
    *,
    coin: str,
    provider: str,
    quote: str,
    references: list[str],
    start: int,
    stop: int,
    days: int,
    replicates: int,
    candidate_limit: int,
    workers: int,
    gap_policy: str,
    family_multiplier: int = 1,
    catalogue: dict | None = None,
) -> dict:
    catalogue = catalogue or expanded.catalogue(ROOT)
    return {
        "schema": "weekly-coin-plan/v2",
        "version": VERSION,
        "coin": coin_symbol(coin),
        "provider": provider,
        "venue": PROVIDERS[provider]["venue"],
        "quote": coin_symbol(quote),
        "references": references,
        "start": start,
        "end_exclusive": stop,
        "days": days,
        "replicates": replicates,
        "candidate_limit": candidate_limit,
        "templates": min(candidate_limit, len(catalogue["candidates"]))
        if candidate_limit
        else len(catalogue["candidates"]),
        "fees_bps_per_fill": list(FEES),
        "slippage_bps_per_fill": 2,
        "workers": workers,
        "gap_policy": gap_policy,
        "minimum_contiguous_minutes": 1440,
        "correlation_family_multiplier": family_multiplier,
        "filter_definitions": {
            "shape_rules": expanded.SHAPE_RULE,
            "shape_window_bars": 48,
            "frequency_train_bars": expanded.TRAIN,
            "frequency_frozen_bars": expanded.BLOCK,
        },
        "selection": "60/20/20 chronological; validation-only net-return ranking; at least ten validation exits",
        "catalogue": catalogue,
        "identity": identity(),
        "coverage": coverage(),
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--coin", help="single base coin; default ETH")
    selection.add_argument(
        "--coins",
        nargs="+",
        help="comma- or space-separated coin list; test each distinct native pair plus cash markets",
    )
    parser.add_argument(
        "--venue",
        choices=tuple(PROVIDERS),
        help="default Binance/USDT for legacy single-coin mode; Coinbase/USD for coin lists",
    )
    parser.add_argument(
        "--quote",
        help="account/quote asset, e.g. USD, USDT or BTC; USD selects Coinbase by default",
    )
    parser.add_argument(
        "--gap-policy",
        choices=("strict", "longest"),
        help="strict requires the full window; longest uses only its longest real contiguous segment (minimum one day), prominently reported",
    )
    parser.add_argument(
        "--references",
        help="single-coin return comparisons (default BTC,ZEC); batch references come from its native markets",
    )
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument(
        "--end", help="exclusive UTC minute boundary; default latest completed minute"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--replicates", type=int, default=1999)
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=0,
        help="explicit smoke-test subset; zero means complete catalogue",
    )
    parser.add_argument(
        "--phase", choices=("all", "fetch", "analyze", "verify"), default="all"
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if args.coins or (output / "batch-plan.json.zlib").exists():
        from research.coin_week_batch import run_batch

        return run_batch(args, output)
    if args.phase == "verify":
        print(json.dumps(verify_run(output), indent=2))
        return 0
    if not 1 <= args.workers <= 16 or args.replicates < 199 or args.candidate_limit < 0:
        raise ValueError(
            "workers must be 1..16, null replicates >=199, candidate limit >=0"
        )
    output.mkdir(parents=True, exist_ok=True)
    with (output / "run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (output / "manifest.json").exists():
            if not args.resume:
                raise ValueError(
                    "finished study is immutable; use --resume to verify it or a new output directory"
                )
            print(json.dumps(verify_run(output), indent=2))
            return 0
        plan_path = output / "run-plan.json.zlib"
        if plan_path.exists():
            if not args.resume and args.phase != "analyze":
                raise ValueError(
                    "unfinished study exists; resume its frozen plan with --resume"
                )
            plan = load(plan_path)
            if args.coin is not None and args.coin.upper() != plan["coin"]:
                raise ValueError("resume coin does not match frozen plan")
            if args.quote is not None and args.quote.upper() != plan["quote"]:
                raise ValueError("resume quote does not match frozen plan")
        else:
            if args.phase == "analyze":
                raise ValueError("offline analysis needs an existing acquired plan")
            coin = coin_symbol(args.coin or "ETH")
            provider = args.venue or (
                "coinbase" if (args.quote or "").upper() == "USD" else "binance"
            )
            quote = coin_symbol(args.quote or PROVIDERS[provider]["quote"])
            start, stop = week_bounds(args.end, args.days)
            references = sorted(
                {
                    coin_symbol(c.strip())
                    for c in (
                        args.references if args.references is not None else "BTC,ZEC"
                    ).split(",")
                    if c.strip()
                }
                - {coin, quote}
            )
            plan = make_plan(
                coin=coin,
                provider=provider,
                quote=quote,
                references=references,
                start=start,
                stop=stop,
                days=args.days,
                replicates=args.replicates,
                candidate_limit=args.candidate_limit,
                workers=args.workers,
                gap_policy=args.gap_policy
                or (
                    "longest"
                    if args.quote is not None and provider == "coinbase"
                    else "strict"
                ),
            )
            save(plan_path, plan)
            save(output / "coverage.json", plan["coverage"])
        if args.phase in ("all", "fetch"):
            for coin in [plan["coin"], *plan["references"]]:
                print(
                    f"fetch {plan['venue']} {coin}/{plan['quote']} {iso(plan['start'])}..{iso(plan['end_exclusive'])}",
                    flush=True,
                )
                download(
                    coin,
                    plan["start"],
                    plan["end_exclusive"],
                    output / "inputs" / f"{coin}.json.zlib",
                    provider=plan["provider"],
                    quote=plan["quote"],
                )
        if args.phase in ("all", "analyze"):
            analyze(plan, output, args.workers)
            print(json.dumps(verify_run(output), indent=2))
            print(str(output / "report.md"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

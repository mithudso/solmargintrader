"""Reproducible ZEC ensemble study; public data is fetched separately.

The search uses fixed chronological windows, three validation folds, next-open
spot accounting and a reserved final fifth. Selection never reads holdout results.
Batch accounting is checked against the canonical event engine before a run and
selected results receive an independent canonical replay. Outputs stay outside Git.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import itertools
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backtester.core.data import frame_to_arrays, validate_bars
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import REGISTRY
from backtester.core.types import INTERVAL_SECONDS, CostConfig, periods_per_year
from backtester.core.zec_ensemble import (
    _Member,
    candidate_id,
    canonical_config,
    spec_id,
)

VERSION = 1
GUIDE = (
    "macd",
    "ppo",
    "ts_momentum",
    "swing_confluence",
    "vol_regime",
    "rsi",
    "bb_breakout",
    "voltarget",
)
COSTS = {
    "fee_bps": 10.0,
    "slippage_bps": 2.0,
    "fill_delay": 1,
    "mode": "spot",
    "leverage": 1.0,
}
_WORK_ARRAYS: dict[str, np.ndarray] = {}


def sha(path: Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def spec(strategy: str, **params: Any) -> dict[str, Any]:
    return {"strategy": strategy, "params": params}


def catalog(interval: str) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def add(family: str, mode: str, members: list[dict], **extra: Any):
        config = canonical_config(
            {
                "schema_version": 1,
                "interval": interval,
                "mode": mode,
                "members": members,
                **extra,
            }
        )
        rows.setdefault(
            candidate_id(config),
            {
                "candidate_id": candidate_id(config),
                "family": family,
                "interval": interval,
                "config": config,
            },
        )

    for name in REGISTRY:
        if name.startswith("lev_") or name == "trigger_trade":
            continue
        add("canonical-single", "single", [spec(name)])
    variants = {
        "macd": [
            {"fast": 6, "slow": 13, "signal": 5},
            {"fast": 24, "slow": 52, "signal": 18},
        ],
        "ppo": [
            {"fast": 6, "slow": 13, "signal": 5},
            {"fast": 24, "slow": 52, "signal": 18},
        ],
        "ts_momentum": [{"window": 12}, {"window": 48}, {"window": 96}],
        "swing_confluence": [
            {"breakout": 10, "exit_lookback": 5, "ma_window": 25},
            {"breakout": 40, "exit_lookback": 20, "ma_window": 100},
            {"min_confirms": 3},
        ],
        "vol_regime": [
            {"calm_quantile": 0.25},
            {"calm_quantile": 0.75},
            {"vol_window": 10, "lookback": 125, "trend_window": 50},
        ],
        "rsi": [{"period": 7, "oversold": 25}, {"period": 28, "oversold": 35}],
        "bb_breakout": [{"window": 10, "num_std": 1.5}, {"window": 40, "num_std": 2.5}],
        "voltarget": [{"target_vol": 0.15}, {"target_vol": 0.30}],
    }
    for name, configs in variants.items():
        for params in configs:
            add("parameter-sensitivity", "single", [spec(name, **params)])
    for size in (2, 3):
        for names in itertools.combinations(GUIDE, size):
            for mode in ("all", "any", "mean", "majority", "supermajority"):
                add(f"{size}-member-vote", mode, [spec(n) for n in names])
    groups = [
        GUIDE,
        GUIDE[:3],
        ("vol_regime", "ts_momentum", "swing_confluence"),
        ("macd", "swing_confluence", "vol_regime", "rsi"),
        ("macd", "ts_momentum", "swing_confluence", "vol_regime", "voltarget"),
        ("macd", "obv_trend", "adx_trend"),
        ("rsi", "zscore", "bb_reversion"),
    ]
    for names in groups:
        members = [spec(n) for n in names]
        for mode in ("all", "any", "mean", "majority", "supermajority"):
            add("guide-and-family-committee", mode, members)
        for threshold in (0.10, 0.25):
            add("turnover-deadband", "mean", members, rebalance_threshold=threshold)
        for persistence in (2, 3, 5):
            add(
                "confirmation-persistence", "majority", members, persistence=persistence
            )
        # Weights are fitted on the training prefix only, later frozen in config.
        add(
            "train-correlation-weighted",
            "weighted",
            members,
            weights=[1] * len(members),
            weighting="inverse-absolute-correlation",
        )
    gates = [spec("vol_regime", calm_quantile=q) for q in (0.25, 0.5, 0.75)] + [
        spec("adx_trend"),
        spec("sma_regime"),
    ]
    triggers = (
        "macd",
        "ts_momentum",
        "swing_confluence",
        "bb_breakout",
        "breakout",
        "obv_trend",
    )
    for gate in gates:
        for trigger in triggers:
            for persistence in (1, 2, 3):
                add(
                    "hierarchical-permission",
                    "gate",
                    [spec(trigger)],
                    gate=gate,
                    persistence=persistence,
                )
        for names in itertools.combinations(triggers, 2):
            for threshold in (0.0, 0.15):
                add(
                    "gate-then-soft-vote",
                    "gate",
                    [spec(n) for n in names],
                    gate=gate,
                    rebalance_threshold=threshold,
                )
        for trigger in ("ts_momentum", "swing_confluence", "macd"):
            for fallback in ("rsi", "bb_reversion", "zscore"):
                add(
                    "regime-routes-trend-or-reversion",
                    "switch",
                    [spec(trigger)],
                    gate=gate,
                    fallback=spec(fallback),
                )
    return list(rows.values())


def component_specs(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for row in rows:
        cfg = row["config"]
        for item in [
            *cfg["members"],
            *([cfg["gate"]] if "gate" in cfg else []),
            *([cfg["fallback"]] if "fallback" in cfg else []),
        ]:
            out[spec_id(item)] = item
    return out


def _init_worker(path: str):
    global _WORK_ARRAYS
    loaded = np.load(path)
    _WORK_ARRAYS = {k: loaded[k] for k in loaded.files}


def _compute_component(item: tuple[str, dict, str, str]):
    key, member_spec, filename, interval = item
    from backtester.core.types import BarWindow

    member = _Member(member_spec, interval=interval)
    a = _WORK_ARRAYS
    target = np.zeros(len(a["ts"]), dtype="float64")
    for i in range(len(target)):
        target[i] = member.step(
            BarWindow(
                a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], i
            )
        )
    np.save(filename, target)
    state = {
        "strategy": member.strategy.__dict__,
        "avg_gain": member.avg_gain,
        "avg_loss": member.avg_loss,
        "ewma_var": member.ewma_var,
        "obv": member.obv,
        "obv_tail": member.obv_tail,
    }
    atomic_json(
        Path(filename + ".json"),
        {
            "state": state,
            "warmup": member.strategy.warmup_bars(),
            "sha256": sha(Path(filename)),
            "state_sha256": hashlib.sha256(
                json.dumps(state, sort_keys=True).encode()
            ).hexdigest(),
        },
    )
    return key, filename


def component_cache(rows, arrays, output, workers, interval):
    output.mkdir(parents=True, exist_ok=True)
    npz = output / "arrays.npz"
    np.savez(npz, **arrays)
    specs = component_specs(rows)
    tasks, signals, states, warmups = [], {}, {}, {}
    for key, item in specs.items():
        path = output / (hashlib.sha256(key.encode()).hexdigest()[:20] + ".npy")
        if not path.is_file() or not path.with_suffix(".npy.json").is_file():
            tasks.append((key, item, str(path), interval))
        signals[key] = path
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers, initializer=_init_worker, initargs=(str(npz),)
    ) as pool:
        futures = {pool.submit(_compute_component, task): task[0] for task in tasks}
        for n, future in enumerate(concurrent.futures.as_completed(futures), 1):
            key, _ = future.result()
            print(
                f"{interval} component {n}/{len(tasks)} {json.loads(key)['strategy']}",
                flush=True,
            )
    for key, path in signals.items():
        saved = json.loads(path.with_suffix(".npy.json").read_text())
        if (
            sha(path) != saved["sha256"]
            or hashlib.sha256(
                json.dumps(saved["state"], sort_keys=True).encode()
            ).hexdigest()
            != saved["state_sha256"]
        ):
            raise ValueError("component cache integrity mismatch")
        signals[key] = np.load(path, mmap_mode="r")
        if signals[key].shape != (len(arrays["ts"]),) or not np.all(
            np.isfinite(signals[key])
        ):
            raise ValueError("component cache shape or finite values mismatch")
        states[key], warmups[key] = saved["state"], saved["warmup"]
    return signals, states, warmups


def targets(config, signals, warmups, train_end):
    values = np.stack([signals[spec_id(s)] for s in config["members"]])
    mode = config["mode"]
    if mode == "weighted" and config.get("weighting"):
        corr = np.nan_to_num(np.corrcoef(values[:, :train_end]), nan=0.0)
        corr = np.atleast_2d(corr)
        weights = 1.0 / np.maximum(np.abs(corr).sum(axis=1), 1.0)
        config["weights"] = (weights / weights.sum()).tolist()
    if mode in {"single", "all"}:
        raw = values.min(axis=0)
    elif mode == "any":
        raw = values.max(axis=0)
    elif mode == "majority":
        raw = ((values > 0).sum(axis=0) * 2 > len(values)).astype(float)
    elif mode == "supermajority":
        raw = ((values > 0).sum(axis=0) * 3 >= len(values) * 2).astype(float)
    elif mode == "weighted":
        raw = np.dot(np.asarray(config["weights"]), values)
    else:
        raw = values.mean(axis=0)
    keys = [spec_id(s) for s in config["members"]]
    if "gate" in config:
        key = spec_id(config["gate"])
        keys.append(key)
        permission = signals[key] > 0
        if mode == "switch":
            fk = spec_id(config["fallback"])
            keys.append(fk)
            raw = np.where(permission, raw, signals[fk])
        else:
            raw = np.where(permission, raw, 0.0)
    warmup = max(warmups[key] for key in keys)
    raw[:warmup] = 0
    persistence = {"pending": False, "count": 0, "active": False, "last": 0.0}
    if config["persistence"] > 1:
        from backtester.core.zec_ensemble import persist

        raw = np.concatenate(
            (
                np.zeros(warmup),
                np.array(
                    [
                        persist(float(x), persistence, config["persistence"])
                        for x in raw[warmup:]
                    ]
                ),
            )
        )
    else:
        active = raw > 0
        persistence = {
            "pending": bool(active[-1]),
            "active": bool(active[-1]),
            "last": float(raw[-1]),
            "count": 1,
        }
    return raw, persistence


def batch_spot(
    targets: np.ndarray,
    arrays: dict,
    interval: str,
    thresholds=None,
    cost_multiplier=1.0,
):
    """Vectorize across policies, retaining canonical spot cash/units accounting.

    No shorting or leverage. Every decision at close t fills at open t+1.
    Costs are on the incremental size change, cash is reserved before buying,
    and a final close settles the account exactly as run_backtest does.
    """
    if targets.ndim == 1:
        targets = targets[None, :]
    count, n = targets.shape
    cash = np.full(count, 10000.0)
    units = np.zeros(count)
    peak = np.full(count, 10000.0)
    maxdd = np.zeros(count)
    fees = np.zeros(count)
    exits = np.zeros(count, dtype=int)
    fills = np.zeros(count, dtype=int)
    sum_r = np.zeros(count)
    sum_r2 = np.zeros(count)
    previous = np.full(count, 10000.0)
    thresholds = np.maximum(
        np.asarray(thresholds if thresholds is not None else np.zeros(count)), 1e-12
    )
    cost = (COSTS["fee_bps"] + COSTS["slippage_bps"]) * cost_multiplier / 10000
    fee = COSTS["fee_bps"] * cost_multiplier / 10000
    daily_equities, daily_times = [], []
    for i in range(n):
        if i:
            price = arrays["open"][i]
            notional = units * price
            equity = cash + notional
            delta = targets[:, i - 1] * equity - notional
            trade = np.abs(delta) / np.maximum(equity, 1e-300) > thresholds
            bought = np.where(
                trade & (delta > 0),
                np.minimum(delta, np.maximum(cash, 0) / (1 + cost)),
                0,
            )
            sold = np.where(trade & (delta < 0), -delta, 0)
            cash = np.maximum(0.0, cash - bought * (1 + cost)) + sold * (1 - cost)
            units += (bought - sold) / price
            units = np.where(trade & (targets[:, i - 1] == 0), 0.0, units)
            fees += (bought + sold) * fee
            fills += (bought > 1e-12) | (sold > 1e-12)
            exits += sold > 1e-12
        if i == n - 1:
            value = units * arrays["close"][i]
            cash += value * (1 - cost)
            fees += value * fee
            fills += value > 1e-12
            exits += value > 1e-12
            units.fill(0)
        equity = cash + units * arrays["close"][i]
        peak = np.maximum(peak, equity)
        maxdd = np.minimum(maxdd, equity / peak - 1)
        if i:
            ret = equity / previous - 1
            sum_r += ret
            sum_r2 += ret * ret
        previous = equity
        if i == n - 1 or arrays["ts"][i + 1] // 86400 != arrays["ts"][i] // 86400:
            daily_equities.append(equity.copy())
            daily_times.append(int(arrays["ts"][i]))
    daily = np.stack(daily_equities, axis=1)
    daily = daily[:, 1:] / daily[:, :-1] - 1
    sample = max(n - 1, 1)
    mean = sum_r / sample
    variance = np.maximum((sum_r2 - sample * mean * mean) / max(sample - 1, 1), 0)
    sharpe = np.divide(
        mean, np.sqrt(variance), out=np.zeros(count), where=variance > 1e-24
    ) * math.sqrt(periods_per_year(interval))
    daily_std = daily.std(axis=1, ddof=1) if daily.shape[1] > 1 else np.zeros(count)
    daily_mean = daily.mean(axis=1) if daily.shape[1] else np.zeros(count)
    daily_sharpe = np.divide(
        daily_mean, daily_std, out=np.zeros(count), where=daily_std > 1e-12
    ) * math.sqrt(365)
    return [
        {
            "total_return": float(previous[j] / 10000 - 1),
            "final_equity": float(previous[j]),
            "sharpe": float(sharpe[j]),
            "daily_sharpe": float(daily_sharpe[j]),
            "max_drawdown": float(maxdd[j]),
            "trade_count": int(exits[j]),
            "fills": int(fills[j]),
            "total_fees": float(
                fees[j] * (COSTS["fee_bps"] + COSTS["slippage_bps"]) / COSTS["fee_bps"]
            ),
            "total_slippage": float(fees[j] * COSTS["slippage_bps"] / COSTS["fee_bps"]),
            "borrow_fees": 0.0,
            "bars": n,
            "from_ts": int(arrays["ts"][0]),
            "through_ts": int(arrays["ts"][-1]),
            "daily_returns": daily[j].tolist(),
        }
        for j in range(count)
    ]


class ArrayPolicy:
    def __init__(self, values):
        self.values = values
        self.name, self.params = "cached_causal_ensemble", {}

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return float(self.values[history.i])


def canonical_replay(values, arrays, interval, threshold=0.0, cost_multiplier=1.0):
    costs = CostConfig(fee_bps=10 * cost_multiplier, slippage_bps=2 * cost_multiplier)
    result = run_backtest(
        ArrayPolicy(values),
        arrays,
        EngineConfig(interval=interval, costs=costs, rebalance_threshold=threshold),
    )
    metrics = result.metrics.to_dict()
    # Canonical CAGR can overflow on one-minute toy fixtures; real studies use
    # fixed multiweek folds. Keep serialized metrics finite explicitly.
    return {
        key: value
        for key, value in metrics.items()
        if not isinstance(value, float) or math.isfinite(value)
    }


def verify_batch_parity():
    rng = np.random.default_rng(193)
    n = 900
    op = 100 * np.exp(np.cumsum(rng.normal(0, 0.002, n)))
    cl = op * np.exp(rng.normal(0, 0.001, n))
    arrays = {
        "ts": np.arange(n) * 3600 + 1_700_000_000,
        "open": op,
        "close": cl,
        "high": np.maximum(op, cl) * 1.001,
        "low": np.minimum(op, cl) * 0.999,
        "volume": np.ones(n),
    }
    signals = rng.choice([0, 0.25, 0.5, 1], size=(4, n))
    thresholds = [0, 0.1, 0.25, 0.5]
    results = batch_spot(signals, arrays, "1h", thresholds)
    for i, result in enumerate(results):
        ref = canonical_replay(signals[i], arrays, "1h", thresholds[i])
        for key in (
            "final_equity",
            "total_return",
            "sharpe",
            "max_drawdown",
            "total_fees",
            "trade_count",
        ):
            if not math.isclose(result[key], ref[key], rel_tol=1e-9, abs_tol=1e-8):
                raise AssertionError(f"batch parity {key}: {result[key]} != {ref[key]}")


def primary_data(path: Path, interval: str, days: int, output: Path):
    frame = validate_bars(pd.read_csv(path), interval, strict_gaps=False)
    if frame.empty:
        raise ValueError("no source bars")
    if days:
        frame = frame.loc[
            frame.timestamp >= frame.timestamp.iloc[-1] - days * 86400
        ].reset_index(drop=True)
    # Primary analysis is the latest complete block, chosen without any P&L.
    delta = frame.timestamp.diff()
    cuts = np.flatnonzero(delta.to_numpy()[1:] != INTERVAL_SECONDS[interval]) + 1
    start = int(cuts[-1]) if len(cuts) else 0
    excluded = len(frame.iloc[:start])
    frame = frame.iloc[start:].reset_index(drop=True)
    if len(frame) < 2000:
        raise ValueError(
            f"{interval} latest contiguous primary block has fewer than2000 bars"
        )
    frame.to_csv(output, index=False)
    return frame_to_arrays(frame), {
        "bars": len(frame),
        "first_ts": int(frame.timestamp.iloc[0]),
        "last_ts": int(frame.timestamp.iloc[-1]),
        "days_requested": days,
        "rows_excluded_before_latest_gap": excluded,
        "sha256": sha(output),
        "path": str(output),
    }


def deflated_sharpe(selected_returns, candidate_validation, trials):
    daily_sr = [
        np.mean(x) / np.std(x, ddof=1)
        for x in candidate_validation
        if len(x) > 2 and np.std(x, ddof=1) > 1e-12
    ]
    r = np.asarray(selected_returns)
    if len(r) < 10 or r.std(ddof=1) <= 1e-12 or len(daily_sr) < 2:
        return None
    sd = float(np.std(daily_sr, ddof=1))
    gamma = 0.5772156649
    normal = NormalDist()
    expected = sd * (
        (1 - gamma) * normal.inv_cdf(1 - 1 / max(trials, 2))
        + gamma * normal.inv_cdf(1 - 1 / (max(trials, 2) * math.e))
    )
    z = (r - r.mean()) / r.std(ddof=1)
    sr = float(r.mean() / r.std(ddof=1))
    denom = math.sqrt(
        max(
            1 - float(np.mean(z**3)) * sr + (float(np.mean(z**4)) - 1) / 4 * sr * sr,
            1e-12,
        )
    )
    return {
        "probability": normal.cdf((sr - expected) * math.sqrt(len(r) - 1) / denom),
        "trials": trials,
        "daily_observations": len(r),
        "assumption": "IID daily returns; all trials counted; correlation not treated as independent evidence",
    }


def selected_signal_parity(row, arrays, expected, initial_state):
    """Verify shared runtime policy against cached stateful targets, then bind seed."""
    from backtester.core.types import BarWindow
    from backtester.core.zec_ensemble import build_ensemble, signal_series

    length = min(len(arrays["ts"]), 4096)
    prefix = {key: value[:length] for key, value in arrays.items()}
    np.testing.assert_allclose(
        signal_series(row["config"], prefix), expected[:length], rtol=1e-12, atol=1e-12
    )
    restored = build_ensemble(row["config"])
    restored.restore_state(initial_state)
    actual = restored.on_bar(
        BarWindow(
            arrays["ts"],
            arrays["open"],
            arrays["high"],
            arrays["low"],
            arrays["close"],
            arrays["volume"],
            len(arrays["ts"]) - 1,
        )
    )
    if not math.isclose(actual, float(expected[-1]), rel_tol=1e-12, abs_tol=1e-12):
        raise AssertionError(
            "published initial state does not reproduce final cached signal"
        )


def historical_stress(selected, sources, output, workers):
    """Three predeclared older calendar windows; frozen policies, no reranking."""
    import copy

    for interval in ("1m", "1h"):
        current = [row for row in selected if row["interval"] == interval]
        if not current:
            continue
        full = validate_bars(
            pd.read_csv(sources[interval]), interval, strict_gaps=False
        )
        first_primary = current[0]["source"]["first_ts"]
        old = full.loc[full.timestamp < first_primary]
        for row in current:
            row["historical_stress"] = []
        for fraction in (0.25, 0.5, 0.75):
            if old.empty:
                for row in current:
                    row["historical_stress"].append(
                        {"state": "unavailable", "reason": "no earlier source history"}
                    )
                continue
            anchor = int(old.timestamp.iloc[int((len(old) - 1) * fraction)])
            frame = old.loc[
                (old.timestamp >= anchor) & (old.timestamp < anchor + 30 * 86400)
            ].reset_index(drop=True)
            gaps = (
                np.flatnonzero(np.diff(frame.timestamp) != INTERVAL_SECONDS[interval])
                + 1
            )
            if len(gaps):
                # Latest contiguous suffix is a fixed data-quality rule, not a
                # strategy-dependent choice. Missing bars are never bridged.
                frame = frame.iloc[int(gaps[-1]) :].reset_index(drop=True)
            directory = output / "stress" / interval / str(anchor)
            directory.mkdir(parents=True, exist_ok=True)
            if len(frame) < 600:
                for row in current:
                    row["historical_stress"].append(
                        {
                            "state": "insufficient",
                            "anchor_ts": anchor,
                            "bars": len(frame),
                        }
                    )
                continue
            arrays = frame_to_arrays(frame)
            signals, _, warmups = component_cache(
                current, arrays, directory, workers, interval
            )
            hold = canonical_replay(np.ones(len(frame)), arrays, interval)
            for row in current:
                frozen = copy.deepcopy(row["config"])
                frozen.pop("weighting", None)
                target, _ = targets(frozen, signals, warmups, 1)
                row["historical_stress"].append(
                    {
                        "state": "evaluated",
                        "anchor_ts": anchor,
                        "from_ts": int(arrays["ts"][0]),
                        "through_ts": int(arrays["ts"][-1]),
                        "bars": len(frame),
                        "policy": canonical_replay(
                            target, arrays, interval, frozen["rebalance_threshold"]
                        ),
                        "buy_and_hold": hold,
                        "cash_return": 0.0,
                        "notice": "fixed older 30-day stress window; not used for selection",
                    }
                )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--minute-days", type=int, default=180)
    parser.add_argument("--hour-days", type=int, default=0)
    parser.add_argument("--plan", action="store_true")
    args = parser.parse_args(argv)
    rows = catalog("1m") + catalog("1h")
    if args.plan:
        print(
            json.dumps(
                {
                    "configurations": len(rows),
                    "families": dict(Counter(row["family"] for row in rows)),
                    "components": len(component_specs(rows)),
                },
                indent=2,
            )
        )
        return 0
    args.output.mkdir(parents=True, exist_ok=True)
    import fcntl

    lock = (args.output / "study.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    sources = {
        interval: args.data_dir / f"ZEC_{interval}.csv" for interval in ("1m", "1h")
    }
    preflight = {}
    for interval in ("1m", "1h"):
        frame = validate_bars(pd.read_csv(sources[interval]), interval, strict_gaps=False)
        days = args.minute_days if interval == "1m" else args.hour_days
        if frame.empty:
            raise ValueError("empty primary source")
        if days:
            frame = frame[frame.timestamp >= frame.timestamp.iloc[-1] - days * 86400]
        cuts = np.flatnonzero(np.diff(frame.timestamp) != INTERVAL_SECONDS[interval]) + 1
        frame = frame.iloc[int(cuts[-1]) if len(cuts) else 0:]
        if len(frame) < 2000:
            raise ValueError("insufficient primary source")
        test_start = int(frame.timestamp.iloc[int(len(frame) * .8)])
        preflight[interval] = (test_start, int(frame.timestamp.iloc[-1]) + INTERVAL_SECONDS[interval])
    if max(v[0] for v in preflight.values()) >= min(v[1] for v in preflight.values()):
        raise ValueError("primary source holdout calendars do not overlap")
    verify_batch_parity()
    fingerprint = {
        "version": VERSION,
        "sources": {k: sha(v) for k, v in sources.items()},
        "minute_days": args.minute_days,
        "hour_days": args.hour_days,
        "costs": COSTS,
        "code": {
            str(p.relative_to(ROOT)): sha(p)
            for p in [Path(__file__), *sorted((ROOT / "backtester/core").rglob("*.py"))]
        },
    }
    manifest_path = args.output / "manifest.json"
    if (
        manifest_path.is_file()
        and json.loads(manifest_path.read_text())["fingerprint"] != fingerprint
    ):
        raise ValueError(
            "study source/code/settings changed; use a new output directory"
        )
    study_id = hashlib.sha256(
        json.dumps(fingerprint, sort_keys=True).encode()
    ).hexdigest()
    manifest = {
        "schema_version": 1,
        "status": "running",
        "study_id": study_id,
        "fingerprint": fingerprint,
        "selection": "median validation daily Sharpe - .5*std - 2*worst drawdown; training40%, three validation blocks40%, reserved test20%; no test reranking",
        "source_symbol": "ZECUSDT",
        "venue": "Binance spot",
        "configurations_planned": len(rows),
    }
    atomic_json(manifest_path, manifest)
    evaluated, interval_state, benchmarks = [], {}, {}
    for interval in ("1m", "1h"):
        primary = args.output / f"ZEC_primary_{interval}.csv"
        arrays, data = primary_data(
            sources[interval],
            interval,
            args.minute_days if interval == "1m" else args.hour_days,
            primary,
        )
        n = len(arrays["ts"])
        train_end, sealed = int(n * 0.4), int(n * 0.8)
        cuts = np.linspace(train_end, sealed, 4, dtype=int)
        folds = [(0, train_end), *[(int(cuts[i]), int(cuts[i + 1])) for i in range(3)]]
        current = [row for row in rows if row["interval"] == interval]
        cache_dir = args.output / "signals" / interval
        signals, states, warmups = component_cache(
            current, arrays, cache_dir, args.workers, interval
        )
        target_file = args.output / f"targets_{interval}.npy"
        matrix = np.lib.format.open_memmap(
            target_file, mode="w+", dtype="float64", shape=(len(current), n)
        )
        persistence_states = []
        for j, row in enumerate(current):
            matrix[j], state = targets(row["config"], signals, warmups, train_end)
            row["candidate_id"] = candidate_id(row["config"])
            persistence_states.append(state)
        matrix.flush()
        all_metrics = [[] for row in current]
        for start, end in folds:
            sliced = {k: v[start:end] for k, v in arrays.items()}
            metrics = batch_spot(
                matrix[:, start:end],
                sliced,
                interval,
                [row["config"]["rebalance_threshold"] for row in current],
            )
            for j, result in enumerate(metrics):
                all_metrics[j].append(result)
            print(
                f"{interval} evaluated {len(current)} policies on {end - start} bars",
                flush=True,
            )
        for j, row in enumerate(current):
            validations = all_metrics[j][1:]
            scores = [fold["daily_sharpe"] for fold in validations]
            eligible = (
                sum(x["trade_count"] for x in validations) >= 10
                and sum(x["trade_count"] > 0 for x in validations) >= 2
            )
            row.update(
                {
                    "train": all_metrics[j][0],
                    "validation": validations,
                    "eligible": bool(eligible),
                    "score": float(
                        np.median(scores)
                        - 0.5 * np.std(scores)
                        - 2 * abs(min(x["max_drawdown"] for x in validations))
                    ),
                    "validation_target_sha256": hashlib.sha256(
                        matrix[j, train_end:sealed].tobytes()
                    ).hexdigest(),
                    "source_path": str(primary),
                    "source_sha256": data["sha256"],
                    "source": data,
                    "costs": {"fee_bps": 10.0, "slippage_bps": 2.0},
                    "cache_index": j,
                }
            )
            evaluated.append(row)
        interval_state[interval] = (arrays, matrix, states, persistence_states, sealed)
        hold = {k: v[sealed:] for k, v in arrays.items()}
        benchmarks[interval] = {
            "cash": canonical_replay(np.zeros(len(hold["ts"])), hold, interval),
            "buy_and_hold": canonical_replay(np.ones(len(hold["ts"])), hold, interval),
        }
    trial_count = len(evaluated)
    ordered = sorted(
        (r for r in evaluated if r["eligible"]),
        key=lambda r: (-r["score"], r["candidate_id"]),
    )
    selected, seen = [], set()
    for row in ordered:
        identity = (row["interval"], row["validation_target_sha256"])
        if identity in seen:
            continue
        seen.add(identity)
        selected.append(row)
        if len(selected) == 10:
            break
    if len(selected) < 10:
        raise ValueError(
            f"only {len(selected)} behaviorally distinct eligible candidates; refuse fabricate10"
        )
    validation_returns = [
        list(
            itertools.chain.from_iterable(x["daily_returns"] for x in row["validation"])
        )
        for row in evaluated
    ]
    common_start = max(int(x[0]["ts"][x[4]]) for x in interval_state.values())
    common_start = (common_start + 3599) // 3600 * 3600
    common_end = min(
        int(x[0]["ts"][-1]) + INTERVAL_SECONDS[interval]
        for interval, x in interval_state.items()
    )
    common_end = common_end // 3600 * 3600
    for rank, row in enumerate(selected, 1):
        arrays, matrix, states, persistence_states, sealed = interval_state[
            row["interval"]
        ]
        index = row["cache_index"]
        hold = {k: v[sealed:] for k, v in arrays.items()}
        row["rank"] = rank
        row["holdout"] = canonical_replay(
            matrix[index, sealed:],
            hold,
            row["interval"],
            row["config"]["rebalance_threshold"],
        )
        row["holdout_double_cost"] = canonical_replay(
            matrix[index, sealed:],
            hold,
            row["interval"],
            row["config"]["rebalance_threshold"],
            2,
        )
        common = np.flatnonzero(
            (arrays["ts"] >= common_start)
            & (arrays["ts"] + INTERVAL_SECONDS[row["interval"]] <= common_end)
        )
        common_arrays = {k: v[common] for k, v in arrays.items()}
        row["common_calendar_holdout"] = canonical_replay(
            matrix[index, common],
            common_arrays,
            row["interval"],
            row["config"]["rebalance_threshold"],
        )
        row["common_calendar_buy_hold"] = canonical_replay(
            np.ones(len(common)), common_arrays, row["interval"]
        )
        row["validation_dsr"] = deflated_sharpe(
            list(
                itertools.chain.from_iterable(
                    x["daily_returns"] for x in row["validation"]
                )
            ),
            validation_returns,
            trial_count,
        )
        cfg = row["config"]
        keys = [
            spec_id(x)
            for x in [
                *cfg["members"],
                *([cfg["gate"]] if "gate" in cfg else []),
                *([cfg["fallback"]] if "fallback" in cfg else []),
            ]
        ]
        row["initial_state"] = {
            "origin_ts": int(arrays["ts"][0]),
            "last_ts": int(arrays["ts"][-1]),
            "persistence": persistence_states[index],
            "members": {key: states[key] for key in keys},
        }
    for row in selected:
        a, matrix, _, _, _ = interval_state[row["interval"]]
        selected_signal_parity(row, a, matrix[row["cache_index"]], row["initial_state"])
        row["signal_parity"] = {
            "first_prefix_bars": min(len(a["ts"]), 4096),
            "cached_vs_shared_builder": "passed",
            "initial_state_final_signal": "passed",
        }
    historical_stress(selected, sources, args.output, args.workers)
    if {name: sha(ROOT / name) for name in fingerprint["code"]} != fingerprint["code"]:
        raise ValueError(
            "study implementation changed during evaluation; refuse publication"
        )
    with (args.output / "results.jsonl").open("w") as f:
        for row in evaluated:
            f.write(json.dumps(row, allow_nan=False, sort_keys=True) + "\n")
    atomic_json(
        args.output / "top10.json",
        {
            "schema_version": 1,
            "study_id": study_id,
            "selection_rule": manifest["selection"],
            "trial_count": trial_count,
            "benchmarks": benchmarks,
            "selected": selected,
            "publication": {"candidate_id": selected[0]["candidate_id"], "rank": 1},
            "notice": "Experimental paper candidates; reserved holdout was not used for ranking; no guarantee of positive edge.",
        },
    )
    if {name: sha(ROOT / name) for name in fingerprint["code"]} != fingerprint["code"]:
        raise ValueError(
            "study implementation changed during evaluation; refuse publication"
        )
    manifest.update(
        {
            "status": "complete",
            "evaluated": trial_count,
            "eligible": len(ordered),
            "distinct_eligible": len(
                {(r["interval"], r["validation_target_sha256"]) for r in ordered}
            ),
            "selected_distinct": len(seen),
            "top10_sha256": sha(args.output / "top10.json"),
            "results_sha256": sha(args.output / "results.jsonl"),
        }
    )
    atomic_json(manifest_path, manifest)
    print(
        json.dumps(
            {
                "evaluated": trial_count,
                "selected": len(selected),
                "top": selected[0]["candidate_id"],
                "output": str(args.output),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Training-only grid selection and entry gates; canonical resting-order fills."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict

import numpy as np
import pandas as pd
from ripser import ripser

from backtester.core.data import frame_to_arrays
from backtester.core.gridsim import GridConfig, run_grid_backtest
from research.coinbase50_stats import harmonic_fit, market_calendar_residual
from research.shape_study import detect_shapes
from research.zec_cycles import pivots

FACTORS = ("selection", "frequency", "shape", "time", "H1")
SCENARIOS = {"zero_2": (0, 2), "zero_10": (0, 10), "zero_25": (0, 25), "fee10_2": (10, 2)}


def persistent_h1(cloud):
    """Vietoris-Rips H1 including 2-simplices, not a graph cycle count."""
    cloud = np.asarray(cloud, dtype=float)
    if cloud.ndim != 2 or len(cloud) < 3 or not np.isfinite(cloud).all():
        raise ValueError("finite point cloud required")
    cloud = cloud - cloud.mean(axis=0)
    scale = np.sqrt(np.mean(cloud**2))
    if scale < 1e-15:
        return 0.0
    cloud = cloud / scale
    result = ripser(cloud, maxdim=1, coeff=2, thresh=np.inf)
    diagram = result["dgms"][1]
    finite = diagram[np.isfinite(diagram[:, 1])]
    diameter = np.max(result["dperm2all"])
    return float(np.max(finite[:, 1] - finite[:, 0]) / diameter) if len(finite) and diameter > 0 else 0.0


def grid_features(train):
    p = np.log(train.close.to_numpy())
    travel = np.sum(np.abs(np.diff(p)))
    efficiency = abs(p[-1] - p[0]) / max(travel, 1e-15)
    points = pivots(p, 0.02)
    durations = [x["confirmed_index"] - x["index"] for x in points]
    lower, upper = np.quantile(train.close, [0.05, 0.95])
    occupancy = float(np.mean((train.close >= lower) & (train.close <= upper)))
    completed_swings = max(0, len(points) - 1)
    anchor, entered, durations_recovered, attempts = p[0], None, [], 0
    for i, price in enumerate(p[1:], 1):
        if entered is None:
            anchor = max(anchor, price)
            if price <= anchor - np.log(1.02):
                entered = (i, price)
                attempts += 1
        elif price >= entered[1] + np.log(1.02):
            durations_recovered.append(i - entered[0])
            entered, anchor = None, price
    days = (train.timestamp.iloc[-1] - train.timestamp.iloc[0] + 900) / 86400
    quote_volume = float(np.median(train.volume * train.close) * 96)
    # Liquidity is a weak tiebreaker, not executable depth or a profit promise.
    score = len(durations_recovered) / days * (1 - efficiency) * occupancy * np.log1p(quote_volume)
    return {"score": float(score), "completed_2pct_recoveries": len(durations_recovered), "recovery_attempts": attempts, "completion_fraction": len(durations_recovered) / attempts if attempts else 0.0, "median_recovery_hours": float(np.median(durations_recovered) / 4) if durations_recovered else None, "right_censored_recovery": entered is not None, "completed_2pct_swings": completed_swings, "efficiency": float(efficiency), "range_occupancy": occupancy, "median_confirmation_hours": float(np.median(durations) / 4) if durations else None, "quote_volume_per_day_proxy": quote_volume}


def hourly_from_quarters(frame):
    f = frame.copy()
    f["hour"] = f.timestamp // 3600 * 3600
    groups = f.groupby("hour", sort=True)
    out = groups.agg(timestamp=("timestamp", "first"), open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), volume=("volume", "sum"), bars=("close", "size"))
    return out[out.bars == 4].drop(columns="bars").reset_index(drop=True)


def causal_hour_features(hourly, btc):
    """Each row is available at timestamp+3600. No embedding crosses a gap."""
    frame = hourly.merge(btc[["timestamp", "open", "close"]], on="timestamp", suffixes=("", "_btc"))
    ts = frame.timestamp.to_numpy()
    r = np.log(frame.close.to_numpy() / frame.open.to_numpy())
    b = np.log(frame.close_btc.to_numpy() / frame.open_btc.to_numpy())
    n = len(frame)
    scores, cycles, periods, consistency, rv = [np.full(n, np.nan) for _ in range(5)]
    latest = None
    previous_period = None
    for i in range(167, n):
        left = i - 167
        if np.any(np.diff(ts[left:i + 1]) != 3600):
            latest = previous_period = None
            continue
        residual = market_calendar_residual(ts[left:i + 1], r[left:i + 1], b[left:i + 1])
        if np.std(residual) <= 1e-8 * np.std(r[left:i + 1]) + 1e-15:
            # Do not amplify OLS roundoff into a unit-variance point cloud.
            # BTC against itself is a deliberately unavailable control.
            latest = previous_period = None
            continue
        recent = residual[-96:]
        cloud = np.column_stack([recent[4:], recent[2:-2], recent[:-4]])
        scores[i] = persistent_h1(cloud)
        rv[i] = np.std(r[i - 95:i + 1])
        # Refit phase/frequency once per UTC day, using completed history only.
        if latest is None or ts[i] // 86400 != ts[i - 1] // 86400:
            values = np.cumsum(residual)
            try:
                period, _, coef = harmonic_fit(ts[left:i + 1], values, 3600, 6 * 3600, 42 * 3600)
            except ValueError:
                latest = previous_period = None
                continue
            consistent = previous_period is not None and abs(np.log2(period / previous_period)) <= 0.5
            latest = (period, coef, ts[left], consistent)
            previous_period = period
        period, coef, origin, consistent = latest
        # The permission applies to the coming hour; phase is extrapolated from
        # the completed fit, never fitted to that hour's eventual close.
        angle = 2 * np.pi * (ts[i] + 3600 - origin) / period
        wave = coef[2] * np.cos(angle) + coef[3] * np.sin(angle)
        derivative = -coef[2] * np.sin(angle) + coef[3] * np.cos(angle)
        cycles[i] = float(wave <= 0 and derivative > 0 and consistent)
        periods[i], consistency[i] = period / 3600, float(consistent)
    return pd.DataFrame({"available_at": ts + 3600, "H1": scores, "cycle_allowed": cycles, "period_hours": periods, "period_consistent": consistency, "raw_rv": rv})


def permissions(frame, features, train_end):
    """As-of join uses only fully completed observations at each bar opening."""
    shape = detect_shapes(frame)
    geometry = shape["shape"].isin(["range", "bowl", "v_rebound"]).to_numpy() & (shape.range_position.to_numpy() < 2 / 3)
    shape_allowed = np.r_[False, geometry[:-1]]
    joined = pd.merge_asof(frame[["timestamp"]].sort_values("timestamp"), features.sort_values("available_at"), left_on="timestamp", right_on="available_at", direction="backward", tolerance=3600)
    past = features[(features.available_at <= train_end) & (features.available_at >= frame.timestamp.iloc[0]) & np.isfinite(features.H1)]
    threshold = float(past.H1.median()) if len(past) else np.inf
    utc_hour = pd.to_datetime(frame.timestamp.to_numpy(), unit="s", utc=True).hour.to_numpy()
    train = frame[frame.timestamp < train_end].copy()
    train["day"] = train.timestamp // 86400
    train["hour"] = pd.to_datetime(train.timestamp, unit="s", utc=True).dt.hour
    train["r"] = np.log(train.close / train.open)
    train["r"] -= train.groupby("day").r.transform("mean")
    best_hours = train.groupby("hour").r.mean().sort_values(kind="stable").index.to_numpy()[-12:]
    return np.column_stack([joined.cycle_allowed.fillna(0).to_numpy() > 0, shape_allowed, np.isin(utc_hour, best_hours), joined.H1.fillna(-1).to_numpy() >= threshold]), {"H1_training_median": threshold if np.isfinite(threshold) else None, "time_hours": sorted(int(x) for x in best_hours)}


def normalized_arrays(frame, scale):
    f = frame.copy()
    for key in ("open", "high", "low", "close"):
        f[key] *= scale
    f["volume"] /= scale
    return frame_to_arrays(f)


def simulate(train, test, allowed, capital, costs, minimum=1.0, scale=None):
    """One fixed ladder/fold, preserving inventory until the costed fold exit."""
    scale = 100 / float(train.close.median()) if scale is None else scale
    lo, hi = np.quantile(train.close, [0.05, 0.95])
    last = float(train.close.iloc[-1])
    lo, hi = min(lo, last * 0.98), max(hi, last * 1.02)
    cfg = GridConfig(lower=float(lo * scale), upper=float(hi * scale), rungs=7, notional_per_rung_usd=capital * 0.1, deadband_bps=0, min_order_usd=minimum)
    # The preceding training close plans the initial resting ladder. No initial
    # historical trade fills because that one seed bar has no resting orders.
    seeded = pd.concat([train.tail(1), test], ignore_index=True)
    permission = np.r_[False, np.asarray(allowed, bool)]
    result = run_grid_backtest(cfg, normalized_arrays(seeded, scale), initial_capital=capital, interval="15m", costs=costs, entry_allowed=permission)
    details = {"scale": scale, "config": cfg.to_dict(), "costs": asdict(costs), "round_trips": result.round_trips, "fees": result.fees_paid_usd, "slippage": result.slippage_paid_usd, "forced_native_qty": result.forced_exit_qty * scale, "max_inventory_fraction": float(np.max(result.exposure)), "mean_inventory_fraction": float(np.mean(result.exposure[1:])), "ending_cash": result.continuation["book"]["cash"], "skipped": result.skipped, "buy_fills": result.buys_filled, "shape_of_gate": Counter(bool(x) for x in allowed)}
    return result.equity[1:], result.exposure[1:], details, result


def passive(test, capital, costs, exposure=1.0):
    fee, slip = costs.fee_bps / 10000, costs.slippage_bps / 10000
    notional = capital * exposure / (1 + fee)
    units = notional / (test.open.iloc[0] * (1 + slip))
    idle = capital * (1 - exposure)
    equity = idle + units * test.close.to_numpy()
    equity[-1] = idle + units * test.close.iloc[-1] * (1 - slip) * (1 - fee)
    return equity


def performance(equity, capital=10000):
    equity = np.asarray(equity)
    previous = np.r_[capital, equity[:-1]]
    returns = equity / previous - 1
    peak = np.maximum.accumulate(np.r_[capital, equity])[1:]
    drawdown = equity / peak - 1
    underwater = drawdown < -1e-12
    longest = current = 0
    for x in underwater:
        current = current + 1 if x else 0
        longest = max(longest, current)
    daily = equity[95::96]
    daily_r = np.diff(np.log(np.r_[capital, daily]))
    return {"return_pct": float((equity[-1] / capital - 1) * 100), "max_drawdown_pct": float(drawdown.min() * 100), "worst_bar_pct": float(returns.min() * 100), "worst_day_pct": float(np.expm1(daily_r.min()) * 100) if len(daily_r) else None, "longest_underwater_days": longest / 96, "final_equity": float(equity[-1])}

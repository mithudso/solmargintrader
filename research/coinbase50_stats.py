"""Clock and wavelength diagnostics, with later-time validation and controls."""

from __future__ import annotations

import numpy as np
import pandas as pd

from research.zec_cycles import Spectrum, holm

SEED = 20261111


def market_calendar_residual(ts, returns, btc_returns, fit=None):
    """Fit nuisance coefficients on fit rows only; never fit on forecast rows."""
    ts = np.asarray(ts)
    hours = pd.to_datetime(ts, unit="s", utc=True).hour.to_numpy()
    x = np.column_stack([np.ones(len(ts)), btc_returns, np.eye(24)[hours, :23]])
    mask = np.ones(len(ts), bool) if fit is None else np.asarray(fit)
    coefficients = np.linalg.lstsq(x[mask], np.asarray(returns)[mask], rcond=None)[0]
    return np.asarray(returns) - x @ coefficients


def harmonic_fit(ts, values, seconds, minimum=None, maximum=None):
    span = ts[-1] - ts[0] + seconds
    maximum_index = int(span // (6 * seconds))
    # Keep every Fourier bin in these short windows. A sparse rounded log grid
    # can omit an exact clock even when it has fewer than128 candidate bins.
    indices = np.arange(4, maximum_index + 1) if maximum_index <= 128 else np.unique(np.rint(np.geomspace(4, maximum_index, 128)).astype(int))
    basis = Spectrum(ts, seconds, periods=span / indices)
    residual = basis.detrend(values)
    if np.linalg.norm(residual) <= 1e-8 * np.linalg.norm(np.asarray(values) - np.mean(values)) + 1e-12:
        raise ValueError("degenerate non-oscillatory series")
    valid = np.ones(len(basis.periods), bool)
    if minimum is not None:
        valid &= basis.periods >= minimum
    if maximum is not None:
        valid &= basis.periods <= maximum
    if not valid.any():
        raise ValueError("no admissible periods")
    powers = basis.power(values)[0]
    best = int(np.argmax(np.where(valid, powers, -1)))
    period = float(basis.periods[best])
    elapsed = (np.asarray(ts) - ts[0]) / period
    design = np.column_stack([np.ones(len(ts)), elapsed, np.cos(2 * np.pi * elapsed), np.sin(2 * np.pi * elapsed)])
    coef = np.linalg.lstsq(design, values, rcond=None)[0]
    return period, float(powers[best]), coef


def wavelength_windows(frame, btc, seconds, days):
    """Selected periods are descriptive; forecasts select on the first half only."""
    data = frame.merge(btc[["timestamp", "open", "close"]], on="timestamp", suffixes=("", "_btc"))
    width = days * 86400
    end = int(data.timestamp.max()) + seconds
    start = end - ((end - int(data.timestamp.min())) // width) * width
    rows = []
    for left in range(start, end, width):
        block = data[(data.timestamp >= left) & (data.timestamp < left + width)]
        if len(block) < width / seconds * 0.9:
            continue
        ts = block.timestamp.to_numpy()
        raw = np.log(block.close.to_numpy())
        returns = np.log(block.close.to_numpy() / block.open.to_numpy())
        market = np.log(block.close_btc.to_numpy() / block.open_btc.to_numpy())
        train = ts < left + width / 2
        if min(np.sum(train), np.sum(~train)) < 24:
            continue
        for mode in ("raw", "market_calendar_residual"):
            residual = market_calendar_residual(ts, returns, market)
            if mode != "raw" and np.std(residual) <= 1e-8 * np.std(returns) + 1e-15:
                continue
            values = raw if mode == "raw" else np.cumsum(residual)
            try:
                period, power, _ = harmonic_fit(ts, values, seconds)
            except ValueError:
                continue
            # The controlled forecast residualization also freezes its nuisance fit.
            forecast_values = raw if mode == "raw" else np.cumsum(market_calendar_residual(ts, returns, market, train))
            try:
                predicted_period, _, coef = harmonic_fit(ts[train], forecast_values[train], seconds)
            except ValueError:
                continue
            elapsed = (ts[~train] - ts[0]) / predicted_period
            # Exclude the fitted trend from the cycle-only extrapolation. Anchor
            # at the last observed level so this cannot win by drifting freely.
            last = (ts[train][-1] - ts[0]) / predicted_period
            wave = coef[2] * np.cos(2 * np.pi * elapsed) + coef[3] * np.sin(2 * np.pi * elapsed)
            anchor = coef[2] * np.cos(2 * np.pi * last) + coef[3] * np.sin(2 * np.pi * last)
            prediction = forecast_values[train][-1] + wave - anchor
            actual = forecast_values[~train]
            error = float(np.mean((prediction - actual) ** 2))
            persistence = float(np.mean((forecast_values[train][-1] - actual) ** 2))
            rows.append({"start": left, "end": left + width, "mode": mode, "period_hours": period / 3600, "power": power, "forecast_period_hours": predicted_period / 3600, "forecast_mse": error, "persistence_mse": persistence, "forecast_win": error < persistence})
    return rows


def cycle_summary(rows):
    if len(rows) < 4:
        return {"windows": len(rows), "status": "insufficient windows"}
    periods = np.array([x["period_hours"] for x in rows])
    logs = np.log2(periods)
    ratios = [x["forecast_mse"] for x in rows]
    base = [x["persistence_mse"] for x in rows]
    return {"windows": len(rows), "status": "descriptive, not a validated natural clock", "period_median_hours": float(np.median(periods)), "period_iqr_hours": [float(x) for x in np.quantile(periods, [0.25, 0.75])], "log2_period_iqr": float(np.subtract(*np.quantile(logs, [0.75, 0.25]))), "median_adjacent_octave_change": float(np.median(np.abs(np.diff(logs)))), "forecast_wins": sum(x["forecast_win"] for x in rows), "forecast_mse_ratio": float(np.sum(ratios) / max(np.sum(base), 1e-24))}


def daily_profiles(frame, clock, metric):
    """A completed native candle's timestamp names its opening hour."""
    index = pd.to_datetime(frame.timestamp.to_numpy(), unit="s", utc=True).tz_convert(clock)
    if metric == "direction":
        values = np.log(frame.close.to_numpy() / frame.open.to_numpy())
    elif metric == "absolute_return":
        values = np.abs(np.log(frame.close.to_numpy() / frame.open.to_numpy()))
    elif metric == "log_quote_volume":
        values = np.log1p(frame.volume.to_numpy() * frame.close.to_numpy())
    else:
        raise ValueError(metric)
    table = pd.DataFrame({"day": index.strftime("%Y-%m-%d"), "hour": index.hour, "value": values})
    # A duplicated DST hour is not averaged into a synthetic 24-hour day.
    valid = table.groupby("day").size()
    good = valid[valid == 24].index
    table = table[table.day.isin(good)]
    table = table[~table.duplicated(["day", "hour"], keep=False)]
    profiles = table.pivot(index="day", columns="hour", values="value").reindex(columns=range(24)).dropna()
    return profiles, int(len(valid) - len(profiles))


def clock_test(profiles, metric, replicates=9999):
    """One max-hour test, not 24 separately selected hour claims.

    Shared seeds indexed by actual date keep null perturbations aligned across
    assets. Local-day rotations change hour labels; permuting days would not.
    """
    y = np.asarray(profiles, dtype=float)
    if y.ndim != 2 or y.shape[1] != 24 or not np.isfinite(y).all():
        raise ValueError("clock profiles must contain finite complete 24-hour days")
    if len(y) < 120:
        return {"status": "insufficient complete days", "p": 1.0, "days": len(y)}
    y = y - y.mean(axis=1, keepdims=True)
    dates = pd.to_datetime(profiles.index)
    day_id = (dates - pd.Timestamp("2025-01-01")).days.to_numpy()
    block = day_id // 7
    unique = np.unique(block)
    if metric == "direction":
        clustered = np.stack([y[block == b].sum(axis=0) for b in unique])
        denominator = np.sqrt(np.sum(clustered**2, axis=0))
    else:
        # One rotation-invariant scale. Hour-specific scales would have to be
        # recomputed for each relabeling to define the same test statistic.
        denominator = np.full(24, np.sqrt(np.sum(y**2) / 24))
    denominator = np.maximum(denominator, 1e-12)
    observed = float(np.max(np.abs(y.sum(axis=0) / denominator)))
    exceed, count = 0, 0
    max_day = int(day_id.max()) + 1
    # Seed per replicate, independent of a coin's listing start and missing days.
    for first in range(0, replicates, 128):
        nulls = []
        for rep in range(first, min(first + 128, replicates)):
            rng = np.random.default_rng(SEED + rep)
            if metric == "direction":
                signs = rng.choice([-1, 1], size=int(block.max()) + 1)[unique]
                nulls.append(signs @ clustered)
            else:
                rotations = rng.integers(0, 24, size=max_day)[day_id]
                nulls.append(y[np.arange(len(y))[:, None], (np.arange(24)[None, :] + rotations[:, None]) % 24].sum(axis=0))
        statistics = np.max(np.abs(np.asarray(nulls) / denominator), axis=1)
        exceed += int(np.sum(statistics >= observed - 1e-12))
        count += len(statistics)
    split = len(y) // 2
    train, test = y[:split].mean(axis=0), y[split:].mean(axis=0)
    selected = np.argsort(train)[-12:]
    correlation = float(np.corrcoef(train, test)[0, 1]) if min(np.std(train), np.std(test)) > 1e-15 else 0.0
    return {"status": "tested", "p": (1 + exceed) / (count + 1), "statistic": observed, "days": len(y), "seven_day_clusters": len(unique), "train_days": split, "test_days": len(y) - split, "profile": y.mean(axis=0).tolist(), "train_profile": train.tolist(), "test_profile": test.tolist(), "train_best_hour": int(np.argmax(train)), "test_best_hour": int(np.argmax(test)), "later_profile_correlation": correlation, "selected_train_hours_later_excess": float(test[selected].mean()), "later_max_minus_min": float(np.ptp(test))}


def adjust_clock_family(rows):
    adjusted = holm([x["p"] for x in rows])
    for row, value in zip(rows, adjusted, strict=True):
        row["holm_p"] = float(value)
    return rows

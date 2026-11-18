"""Test apparent ZEC rhythms against no-clock paths and frozen future forecasts.

Harmonic regression uses actual observation timestamps, including missing bars.
It never interpolates prices or treats a hindsight pivot as a live signal.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from backtester.core.data import validate_bars
from backtester.core.types import INTERVAL_SECONDS
from research.shape_study import protected_intervals, refuse_reserved

VERSION = 1
SEED = 20261111
INTERVALS = ("1m", "5m", "15m", "1h")
TZ = "America/New_York"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )


class Spectrum:
    """Nested sinusoidal regression after removing intercept and linear trend.

    Power is the fraction of detrended sum of squares explained by one harmonic.
    The basis is residualized too, so irregular samples do not invalidate it.
    """

    def __init__(self, timestamps, seconds, duration=None, periods=None):
        self.ts = np.asarray(timestamps, dtype=float)
        if len(self.ts) < 8 or np.any(np.diff(self.ts) <= 0):
            raise ValueError("spectrum needs ordered distinct timestamps")
        span = duration or self.ts[-1] - self.ts[0] + seconds
        if periods is None:
            maximum = int(span // (6 * seconds))
            if maximum < 4:
                raise ValueError("insufficient span for four cycles of six bars")
            indices = np.unique(
                np.rint(np.geomspace(4, maximum, min(128, maximum - 3))).astype(int)
            )
            periods = span / indices
        self.periods = np.asarray(periods, dtype=float)
        elapsed = self.ts - self.ts[0]
        self.x = np.column_stack([np.ones(len(elapsed)), elapsed / span])
        self.inverse = np.linalg.inv(self.x.T @ self.x)
        angle = 2 * np.pi * elapsed[None, :] / self.periods[:, None]
        self.c = self.detrend(np.cos(angle))
        self.s = self.detrend(np.sin(angle))
        self.cc = np.sum(self.c * self.c, axis=1)
        self.ss = np.sum(self.s * self.s, axis=1)
        self.cs = np.sum(self.c * self.s, axis=1)
        self.det = self.cc * self.ss - self.cs**2
        if np.any(self.det < 1e-10):
            raise ValueError("degenerate harmonic basis")

    def detrend(self, values):
        y = np.asarray(values)
        return y - ((y @ self.x) @ self.inverse) @ self.x.T

    def power(self, values):
        y = np.atleast_2d(self.detrend(values))
        u, v = y @ self.c.T, y @ self.s.T
        explained = (self.ss * u**2 - 2 * self.cs * u * v + self.cc * v**2) / self.det
        result = explained / np.maximum(np.sum(y * y, axis=1, keepdims=True), 1e-24)
        return np.clip(result, 0, 1)


def holm(values):
    """Family-wise adjustment valid even for dependent/overlapping windows."""
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    out = np.empty(len(p))
    out[order] = np.minimum(
        1, np.maximum.accumulate(p[order] * np.arange(len(p), 0, -1))
    )
    return out


def surrogate_paths(ts, prices, count, rng, mode):
    p = np.asarray(prices, dtype=float)
    dt = np.diff(ts)
    drift = (p[-1] - p[0]) / (ts[-1] - ts[0])
    increments = np.diff(p) - drift * dt
    if mode == "random_sign":
        returns = increments * rng.choice([-1, 1], size=(count, len(increments)))
    elif mode == "block_permutation":
        blocks = np.array_split(increments, int(np.ceil(len(increments) / 4)))
        returns = np.stack(
            [
                np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])
                for _ in range(count)
            ]
        )
    else:
        raise ValueError("unknown surrogate mode")
    returns += drift * dt
    return np.column_stack([np.full(count, p[0]), p[0] + np.cumsum(returns, axis=1)])


def pivots(log_prices, threshold):
    """Amplitude-only directional changes, with explicit confirmation indices.

    No minimum time separation is imposed; that would manufacture regularity.
    Pivot locations are retrospective. A pivot is known only at confirmation.
    """
    if threshold <= 0:
        raise ValueError("positive reversal threshold required")
    p = np.asarray(log_prices)
    if p.size < 2:
        return []
    high = low = p[0]
    ihigh = ilow = trend = 0
    out = []
    for i, price in enumerate(p[1:], 1):
        if trend >= 0 and price >= high:
            high, ihigh = price, i
        if trend <= 0 and price <= low:
            low, ilow = price, i
        if trend >= 0 and price <= high - threshold:
            if ihigh:
                out.append({"kind": "peak", "index": ihigh, "confirmed_index": i})
            trend, low, ilow = -1, price, i
        elif trend <= 0 and price >= low + threshold:
            if ilow:
                out.append({"kind": "dip", "index": ilow, "confirmed_index": i})
            trend, high, ihigh = 1, price, i
    return out


def spacing(ts, points, kind):
    locations = [
        row["index"] for row in points if kind == "alternating" or row["kind"] == kind
    ]
    differences = np.diff(np.asarray(ts)[locations]) / 60
    if len(differences) < 3:
        return None
    return {
        "intervals": len(differences),
        "median_minutes": float(np.median(differences)),
        "q25_minutes": float(np.quantile(differences, 0.25)),
        "q75_minutes": float(np.quantile(differences, 0.75)),
        "cv": float(differences.std(ddof=1) / differences.mean()),
    }


def null_test(
    ts,
    prices,
    seconds,
    replicates=1999,
    seed=SEED,
    duration=None,
    spacing_reference=False,
):
    price_basis = Spectrum(ts, seconds, duration)
    return_basis = Spectrum(ts[1:], seconds, duration, price_basis.periods)
    basis = {"log_price": price_basis, "log_return": return_basis}
    observed = {"log_price": prices, "log_return": np.diff(prices)}
    null_max = {key: {} for key in basis}
    references = []
    for model_index, mode in enumerate(("random_sign", "block_permutation")):
        rng = np.random.default_rng(seed + model_index)
        maxima = {key: [] for key in basis}
        for begin in range(0, replicates, 128):
            paths = surrogate_paths(ts, prices, min(128, replicates - begin), rng, mode)
            for key, projector in basis.items():
                y = paths if key == "log_price" else np.diff(paths, axis=1)
                maxima[key].append(projector.power(y).max(axis=1))
            if spacing_reference and mode == "random_sign" and begin < 199:
                references.extend(paths[: min(len(paths), 199 - begin)])
        for key in basis:
            null_max[key][mode] = np.concatenate(maxima[key])
    rows, spectra = [], []
    for key, projector in basis.items():
        powers = projector.power(observed[key])[0]
        index = int(np.argmax(powers))
        row = {
            "series": key,
            "observations": len(observed[key]),
            "period_minutes": float(projector.periods[index] / 60),
            "power": float(powers[index]),
            "searched_frequencies": len(powers),
            "replicates": replicates,
        }
        for mode, maxima in null_max[key].items():
            row["p_" + mode] = float(
                (1 + np.sum(maxima >= powers[index])) / (replicates + 1)
            )
        row["p_conservative"] = max(row["p_random_sign"], row["p_block_permutation"])
        row["null95_max_power"] = max(
            float(np.quantile(x, 0.95)) for x in null_max[key].values()
        )
        rows.append(row)
        spectra.extend(
            {
                "series": key,
                "period_minutes": float(period / 60),
                "power": float(power),
                "null95_max_power": row["null95_max_power"],
            }
            for period, power in zip(projector.periods, powers)
        )
    spacing_rows, points = [], []
    if spacing_reference:
        for threshold in (0.01, 0.02):
            detected = pivots(prices, threshold)
            points.extend(
                {
                    **r,
                    "threshold": threshold,
                    "timestamp": int(ts[r["index"]]),
                    "confirmed_at": int(ts[r["confirmed_index"]]) + seconds,
                    "price": float(np.exp(prices[r["index"]])),
                }
                for r in detected
            )
            for kind in ("peak", "dip", "alternating"):
                sample = spacing(ts, detected, kind)
                if sample is None:
                    continue
                null_cvs = [
                    s["cv"]
                    for path in references
                    if (s := spacing(ts, pivots(path, threshold), kind)) is not None
                ]
                spacing_rows.append(
                    {
                        "threshold": threshold,
                        "kind": kind,
                        **sample,
                        "null_paths": len(null_cvs),
                        "null_cv_q05": float(np.quantile(null_cvs, 0.05))
                        if null_cvs
                        else None,
                        "null_cv_median": float(np.median(null_cvs))
                        if null_cvs
                        else None,
                        "null_cv_q95": float(np.quantile(null_cvs, 0.95))
                        if null_cvs
                        else None,
                    }
                )
    return rows, spectra, spacing_rows, points


def fit_forecast(train, test, seconds):
    """Freeze the period, phase and trend before seeing any test price."""
    ts = train.timestamp.to_numpy(float)
    y = np.log(train.close.to_numpy(float))
    basis = Spectrum(ts, seconds)
    powers = basis.power(y)[0]
    period = float(basis.periods[np.argmax(powers)])
    scale = ts[-1] - ts[0] + seconds

    def design(times, harmonic):
        elapsed = np.asarray(times) - ts[0]
        cols = [np.ones(len(elapsed)), elapsed / scale]
        if harmonic:
            cols += [
                np.cos(2 * np.pi * elapsed / period),
                np.sin(2 * np.pi * elapsed / period),
            ]
        return np.column_stack(cols)

    forecast = {}
    for name, harmonic in (("cycle", True), ("linear", False)):
        coef = np.linalg.lstsq(design(ts, harmonic), y, rcond=None)[0]
        forecast[name] = design(test.timestamp.to_numpy(), harmonic) @ coef
    forecast["persistence"] = np.full(len(test), y[-1])
    forecast["period_seconds"] = period
    return forecast


def forecast_test(frame, interval, target):
    if len(frame) < 2:
        return [], []
    seconds = INTERVAL_SECONDS[interval]
    start = target - pd.Timedelta(days=6)
    end = min(
        target + pd.Timedelta(days=1, hours=6),
        pd.to_datetime(frame.timestamp.iloc[-1] + seconds, unit="s", utc=True),
    )
    cuts = pd.date_range(start, end, freq="6h")
    rows, curves = [], []
    for begin, finish in itertools.pairwise(cuts):
        lo, hi = int(begin.timestamp()), int(finish.timestamp())
        train = frame.loc[
            (frame.timestamp >= lo - 3 * 86400) & (frame.timestamp + seconds <= lo)
        ]
        test = frame.loc[(frame.timestamp >= lo) & (frame.timestamp + seconds <= hi)]
        if (
            len(train) < max(48, 0.95 * 3 * 86400 / seconds)
            or len(test) < 0.95 * 21600 / seconds
        ):
            continue
        pred = fit_forecast(train, test, seconds)
        actual = np.log(test.close.to_numpy(float))
        errors = {
            name: float(np.mean((actual - pred[name]) ** 2))
            for name in ("cycle", "linear", "persistence")
        }
        rows.append(
            {
                "interval": interval,
                "train_start": int(train.timestamp.iloc[0]),
                "last_train_close": int(train.timestamp.iloc[-1]) + seconds,
                "first_test_open": int(test.timestamp.iloc[0]),
                "test_end": hi,
                "period_minutes": pred["period_seconds"] / 60,
                "test_bars": len(test),
                **{name + "_mse": value for name, value in errors.items()},
            }
        )
        for i, ts in enumerate(test.timestamp):
            curves.append(
                {
                    "interval": interval,
                    "timestamp": int(ts),
                    "forecast_origin": lo,
                    "actual": float(actual[i]),
                    **{
                        k: float(pred[k][i]) for k in ("cycle", "linear", "persistence")
                    },
                }
            )
    return rows, curves


def run(input_dir, output, target_day="2026-11-10", replicates=1999):
    if output.exists():
        raise ValueError("use a fresh output directory")
    output.mkdir(parents=True)
    target = pd.Timestamp(target_day, tz=TZ)
    cutoff = int(pd.Timestamp("2026-11-11T11:40:00Z").timestamp())
    reservations = protected_intervals(
        Path.home() / ".config/soltui/experiments/experiments.sqlite3", ("ZEC",)
    )
    manifest = {
        "version": VERSION,
        "status": "running",
        "source_sha256": sha(__file__),
        "target_day": target_day,
        "timezone": TZ,
        "cutoff": cutoff,
        "replicates": replicates,
        "seed": SEED,
        "inputs": {},
        "versions": {"numpy": np.__version__, "pandas": pd.__version__},
        "missing_bars": "Use actual timestamps and native coarse candles; no interpolation.",
        "forecast": "3-day training, fixed period/phase/trend, non-overlapping 6-hour tests",
    }
    write_json(output / "manifest.json", manifest)
    rows, spectra, spacings, pivot_rows, coverage, forecasts, forecast_curves = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    windows = [
        (day.strftime("%Y-%m-%d"), day, day + pd.Timedelta(days=1))
        for day in pd.date_range(target - pd.Timedelta(days=6), target, freq="1D")
    ]
    windows.append(("previous_week", target - pd.Timedelta(days=7), target))
    for interval in INTERVALS:
        seconds = INTERVAL_SECONDS[interval]
        path = input_dir / f"ZEC_USD_{interval}.csv"
        raw = pd.read_csv(path).sort_values("timestamp").reset_index(drop=True)
        frame = validate_bars(raw, interval, strict_gaps=False) if len(raw) else raw.loc[:, ["timestamp", "open", "high", "low", "close", "volume"]]
        frame = frame.loc[frame.timestamp + seconds <= cutoff].reset_index(drop=True)
        refuse_reserved(frame, interval, reservations)
        manifest["inputs"][interval] = {
            "path": str(path),
            "sha256": sha(path),
            "bars": len(frame),
            "first": int(frame.timestamp.iloc[0]) if len(frame) else None,
            "last": int(frame.timestamp.iloc[-1]) if len(frame) else None,
        }
        frame.to_csv(output / f"ZEC_USD_{interval}_bars.csv.gz", index=False)
        for index, (label, begin, end) in enumerate(windows):
            lo, hi = int(begin.timestamp()), int(end.timestamp())
            part = frame.loc[
                (frame.timestamp >= lo) & (frame.timestamp + seconds <= hi)
            ]
            ratio = len(part) / ((hi - lo) / seconds)
            eligible = len(part) >= 48 and ratio >= 0.95
            coverage.append(
                {
                    "interval": interval,
                    "window": label,
                    "start": lo,
                    "end": hi,
                    "bars": len(part),
                    "coverage": ratio,
                    "eligible": eligible,
                    "max_gap_seconds": int(part.timestamp.diff().max()) if len(part) > 1 else None,
                }
            )
            if not eligible:
                continue
            print(
                f"{interval} {label}: {len(part)} bars, {replicates} null replicates per model",
                flush=True,
            )
            ts, prices = part.timestamp.to_numpy(), np.log(part.close.to_numpy(float))
            result, spec, spaces, points = null_test(
                ts,
                prices,
                seconds,
                replicates,
                SEED + index * 37 + seconds,
                duration=hi - lo,
                spacing_reference=label == target_day,
            )
            rows.extend({"interval": interval, "window": label, **r} for r in result)
            spectra.extend({"interval": interval, "window": label, **r} for r in spec)
            spacings.extend({"interval": interval, **r} for r in spaces)
            pivot_rows.extend({"interval": interval, **r} for r in points)
        f, c = forecast_test(frame, interval, target)
        forecasts.extend(f)
        forecast_curves.extend(c)
    stats = pd.DataFrame(rows)
    if stats.empty:
        stats = pd.DataFrame(columns=["interval", "window", "series", "p_conservative"])
    stats["p_holm"] = holm(stats.p_conservative.to_numpy())
    stats.to_csv(output / "spectral_tests.csv", index=False)
    for filename, values in (
        ("spectra.csv", spectra),
        ("spacing.csv", spacings),
        ("pivots.csv", pivot_rows),
        ("coverage.csv", coverage),
        ("forecasts.csv", forecasts),
        ("forecast_curves.csv", forecast_curves),
    ):
        pd.DataFrame(values).to_csv(output / filename, index=False)
    manifest["status"] = "complete" if len(stats) else "insufficient"
    manifest["tests"] = len(stats)
    manifest["artifacts"] = {
        p.name: sha(p) for p in sorted(output.iterdir()) if p.name != "manifest.json"
    }
    write_json(output / "manifest.json", manifest)
    print(f"complete: {len(stats)} corrected spectral tests", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-day", default="2026-11-10")
    parser.add_argument("--replicates", type=int, default=1999)
    args = parser.parse_args(argv)
    if args.replicates < 199:
        raise ValueError("at least 199 null replicates required")
    run(args.input_dir, args.output, args.target_day, args.replicates)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

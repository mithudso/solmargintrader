"""Data loading and validation.

Three loaders share one Protocol so the engine never depends on the network:
CsvLoader (primary, used by the engine and every test), SyntheticLoader
(seeded, deterministic, no network), and the explicit fetch path in fetch.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np
import pandas as pd

from .types import BAR_COLUMNS, INTERVAL_SECONDS


class DataValidationError(ValueError):
    """Raised when a loaded series violates the bar contract."""


@runtime_checkable
class DataLoader(Protocol):
    """Anything that can produce a validated OHLCV frame."""

    def load(
        self, asset: str, start: str | None, end: str | None, interval: str
    ) -> pd.DataFrame:
        """Return a validated frame with columns BAR_COLUMNS, ascending by time."""
        ...

    def describe(self) -> str:
        """Short human-readable source description for the run manifest."""
        ...


def validate_bars(df: pd.DataFrame, interval: str, *, strict_gaps: bool = True) -> pd.DataFrame:
    """Validate the bar contract, raising DataValidationError on any breach.

    Checks, in order: required columns present; timestamps integral, unique,
    and ascending; prices positive and finite; high >= max(open, close, low);
    low <= min(open, close); no gaps larger than one bar interval.

    Returns the frame with columns ordered as BAR_COLUMNS and a reset index.
    """
    missing = [c for c in BAR_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(
            f"missing required column(s): {missing}; expected exactly {list(BAR_COLUMNS)}"
        )

    out = df.loc[:, list(BAR_COLUMNS)].copy()

    if len(out) == 0:
        raise DataValidationError("series is empty; refusing to backtest zero bars")

    # -- timestamps ------------------------------------------------------
    ts = out["timestamp"]
    if ts.isna().any():
        raise DataValidationError("timestamp column contains null values")
    if not np.isfinite(ts.to_numpy(dtype="float64")).all():
        raise DataValidationError("timestamp column contains non-finite values")
    ts_int = ts.astype("int64")
    if not (ts_int.to_numpy() == ts.to_numpy()).all():
        raise DataValidationError(
            "timestamps must be integral UTC epoch seconds; got fractional values. "
            "Millisecond or ISO-8601 timestamps must be converted before loading."
        )
    out["timestamp"] = ts_int

    dupes = out["timestamp"].duplicated()
    if dupes.any():
        first = out.loc[dupes, "timestamp"].iloc[0]
        raise DataValidationError(
            f"{int(dupes.sum())} duplicate timestamp(s); first at epoch {int(first)}"
        )

    if not out["timestamp"].is_monotonic_increasing:
        bad = int((out["timestamp"].diff().fillna(1) <= 0).idxmax())
        raise DataValidationError(
            f"timestamps are not strictly ascending; first violation at row {bad}"
        )

    # Reject plausibly-millisecond timestamps outright: 1e12 epoch seconds is
    # the year 33658, so anything that large is a unit error, not a date.
    if int(out["timestamp"].max()) > 10_000_000_000:
        raise DataValidationError(
            "timestamps look like milliseconds, not seconds; divide by 1000 before loading"
        )

    # -- prices ----------------------------------------------------------
    price_cols = ["open", "high", "low", "close"]
    prices = out[price_cols].to_numpy(dtype="float64")
    if not np.isfinite(prices).all():
        raise DataValidationError("price columns contain NaN or infinite values")
    if (prices <= 0).any():
        row = int(np.argmax((prices <= 0).any(axis=1)))
        raise DataValidationError(
            f"non-positive price at row {row}: {out.iloc[row][price_cols].to_dict()}"
        )

    vol = out["volume"].to_numpy(dtype="float64")
    if not np.isfinite(vol).all():
        raise DataValidationError("volume column contains NaN or infinite values")
    if (vol < 0).any():
        raise DataValidationError("negative volume")

    hi, lo = out["high"].to_numpy(), out["low"].to_numpy()
    op, cl = out["open"].to_numpy(), out["close"].to_numpy()
    if (hi < lo).any():
        row = int(np.argmax(hi < lo))
        raise DataValidationError(
            f"high < low at row {row}: high={hi[row]}, low={lo[row]}"
        )
    bad_hi = hi < np.maximum(op, cl) - 1e-9
    if bad_hi.any():
        row = int(np.argmax(bad_hi))
        raise DataValidationError(
            f"high below open/close at row {row}: high={hi[row]}, "
            f"open={op[row]}, close={cl[row]}"
        )
    bad_lo = lo > np.minimum(op, cl) + 1e-9
    if bad_lo.any():
        row = int(np.argmax(bad_lo))
        raise DataValidationError(
            f"low above open/close at row {row}: low={lo[row]}, "
            f"open={op[row]}, close={cl[row]}"
        )

    # -- gaps ------------------------------------------------------------
    step = INTERVAL_SECONDS[interval]
    if len(out) > 1 and strict_gaps:
        deltas = np.diff(out["timestamp"].to_numpy())
        gaps = np.nonzero(deltas > step)[0]
        if gaps.size:
            worst = int(gaps[np.argmax(deltas[gaps])])
            raise DataValidationError(
                f"{gaps.size} gap(s) larger than one {interval} bar; largest after "
                f"epoch {int(out['timestamp'].iloc[worst])} "
                f"({int(deltas[worst])}s vs expected {step}s). "
                "Refetch the range or pass --allow-gaps to accept an incomplete series."
            )

    return out.reset_index(drop=True)


def _slice_dates(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    """Inclusive date filter on the UTC epoch-second timestamp column."""
    out = df
    if start:
        lo = int(pd.Timestamp(start, tz="UTC").timestamp())
        out = out[out["timestamp"] >= lo]
    if end:
        # End date is inclusive of the whole day when given as a bare date.
        end_ts = pd.Timestamp(end, tz="UTC")
        if end_ts.normalize() == end_ts:
            end_ts = end_ts + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        out = out[out["timestamp"] <= int(end_ts.timestamp())]
    return out.reset_index(drop=True)


def checksum_frame(df: pd.DataFrame) -> str:
    """Stable SHA-256 over the bar values, for the run manifest."""
    h = hashlib.sha256()
    for col in BAR_COLUMNS:
        h.update(col.encode())
        h.update(np.ascontiguousarray(df[col].to_numpy(dtype="float64")).tobytes())
    return h.hexdigest()[:16]


class CsvLoader:
    """Loads bars from a local CSV cache. This is the primary path.

    On-disk schema is exactly `timestamp,open,high,low,close,volume` with a
    header row, one row per bar, ascending, timestamp in UTC epoch seconds.
    """

    def __init__(self, path: str | Path, *, allow_gaps: bool = False) -> None:
        self.path = Path(path)
        self.allow_gaps = allow_gaps

    def load(
        self, asset: str, start: str | None, end: str | None, interval: str
    ) -> pd.DataFrame:
        """Read, validate, and date-slice the cached CSV."""
        if not self.path.exists():
            raise FileNotFoundError(
                f"no cached data at {self.path}. Fetch it first:\n"
                f"  python -m backtester.core.fetch --asset {asset} "
                f"--interval {interval} --out {self.path}"
            )
        raw = pd.read_csv(self.path)
        df = validate_bars(raw, interval, strict_gaps=not self.allow_gaps)
        df = _slice_dates(df, start, end)
        if len(df) == 0:
            raise DataValidationError(
                f"no bars in {self.path} between {start} and {end}; "
                "the cache does not cover the requested range"
            )
        return df

    def describe(self) -> str:
        """Source description for the manifest."""
        return f"csv:{self.path.name}"


class SyntheticLoader:
    """Deterministic seeded price series so tests need no network.

    Generates geometric Brownian motion and derives OHLC from an intrabar
    random walk, so that high/low genuinely bracket open/close.
    """

    def __init__(
        self,
        n_bars: int = 500,
        start_price: float = 100.0,
        annual_vol: float = 0.8,
        annual_drift: float = 0.2,
        seed: int = 42,
        start_ts: int = 1_600_000_000,
    ) -> None:
        self.n_bars = n_bars
        self.start_price = start_price
        self.annual_vol = annual_vol
        self.annual_drift = annual_drift
        self.seed = seed
        # Align to a whole bar boundary so timestamps are tidy.
        self.start_ts = start_ts

    def load(
        self, asset: str, start: str | None, end: str | None, interval: str
    ) -> pd.DataFrame:
        """Generate, validate, and date-slice a synthetic series."""
        step = INTERVAL_SECONDS[interval]
        bars_per_year = (365 * 86400) / step
        rng = np.random.default_rng(self.seed)

        dt = 1.0 / bars_per_year
        sigma = self.annual_vol * np.sqrt(dt)
        mu = (self.annual_drift - 0.5 * self.annual_vol**2) * dt

        shocks = rng.normal(mu, sigma, self.n_bars)
        closes = self.start_price * np.exp(np.cumsum(shocks))
        opens = np.empty(self.n_bars)
        opens[0] = self.start_price
        opens[1:] = closes[:-1]

        # Intrabar extremes: widen beyond the open/close envelope.
        spread = np.abs(rng.normal(0.0, sigma * 0.6, self.n_bars))
        highs = np.maximum(opens, closes) * (1.0 + spread)
        lows = np.minimum(opens, closes) * (1.0 - spread)
        volumes = rng.lognormal(10.0, 0.5, self.n_bars)

        ts = self.start_ts + np.arange(self.n_bars, dtype="int64") * step
        # Snap to the interval grid so gap validation is exact.
        ts = ts - (ts[0] % step)

        df = pd.DataFrame(
            {
                "timestamp": ts,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volumes,
            }
        )
        df = validate_bars(df, interval)
        return _slice_dates(df, start, end)

    def describe(self) -> str:
        """Source description for the manifest."""
        return f"synthetic:seed={self.seed},n={self.n_bars}"


def frame_to_arrays(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """Contiguous float64/int64 arrays for the engine's hot loop."""
    return {
        "ts": np.ascontiguousarray(df["timestamp"].to_numpy(dtype="int64")),
        "open": np.ascontiguousarray(df["open"].to_numpy(dtype="float64")),
        "high": np.ascontiguousarray(df["high"].to_numpy(dtype="float64")),
        "low": np.ascontiguousarray(df["low"].to_numpy(dtype="float64")),
        "close": np.ascontiguousarray(df["close"].to_numpy(dtype="float64")),
        "volume": np.ascontiguousarray(df["volume"].to_numpy(dtype="float64")),
    }

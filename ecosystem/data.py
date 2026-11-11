"""Source-bound OHLCV acquisition for the ecosystem bootstrap.

Acquisition is explicit. Backtests never fetch implicitly, unknown legacy files
are never relabelled, and every accepted input is frozen with a SHA-256 receipt.
Requested ranges are UTC bar-open times in [start, end); all requested bars must
be present and closed. The caller selects a fresh data directory for a new range.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any

import pandas as pd

from backtester.core.assets import require_active_asset
from backtester.core.data import DataValidationError, validate_bars
from backtester.core.fetch import SUPPORTED_GRANULARITIES, FetchError, fetch_coinbase
from backtester.core.types import BAR_COLUMNS, INTERVAL_SECONDS

OWNER_UNIVERSE = (
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "HYPE",
    "DOGE",
    "LINK",
    "NEAR",
    "SUI",
    "AVAX",
    "JITOSOL",
    "KMNO",
    "USDC",
)
ASSET_PATTERN = re.compile(r"[A-Z][A-Z0-9]{0,19}\Z")
SOURCE = "https://api.exchange.coinbase.com/products/{product}/candles"


def universe() -> tuple[str, ...]:
    """Return the owner's thirteen active assets, including explicit missing markets."""
    return OWNER_UNIVERSE


def _symbol(asset: str) -> str:
    if not isinstance(asset, str) or not ASSET_PATTERN.fullmatch(asset.upper()):
        raise ValueError("invalid_asset")
    try:
        return require_active_asset(asset)
    except ValueError as exc:
        raise ValueError("removed_asset") from exc


def _epoch(value: str) -> int:
    if not isinstance(value, str):
        raise ValueError("invalid_date")  # noqa: TRY004 - public validation returns one safe code
    stamp = pd.Timestamp(value)
    if pd.isna(stamp):
        raise ValueError("invalid_date")
    stamp = (
        stamp.tz_localize("UTC") if stamp.tzinfo is None else stamp.tz_convert("UTC")
    )
    seconds = stamp.timestamp()
    if not math.isfinite(seconds) or int(seconds) != seconds or seconds < 0:
        raise ValueError("invalid_date")
    return int(seconds)


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def file_sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _closed_frame(
    frame: pd.DataFrame, start: int, end: int, interval: str
) -> pd.DataFrame:
    step = INTERVAL_SECONDS[interval]
    result = frame.loc[(frame["timestamp"] >= start) & (frame["timestamp"] < end)]
    result = validate_bars(result, interval, strict_gaps=True)
    if len(result) > 2_000_000:
        raise DataValidationError("bounded_input_size_exceeded")
    if (result["timestamp"].to_numpy() % step).any():
        raise DataValidationError("unaligned_timestamps")
    if (
        int(result["timestamp"].iloc[0]) != start
        or int(result["timestamp"].iloc[-1]) + step != end
    ):
        raise DataValidationError("requested_boundary_not_covered")
    return result


def _publish(path: Path, raw: bytes) -> None:
    """Create one immutable artifact; never replace a frozen input."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink():
        raise ValueError("unsafe_cache_path")
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("frozen_input_conflict")
        return
    fd, temp = tempfile.mkstemp(prefix=".bootstrap-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != raw:
                raise ValueError("frozen_input_conflict") from None
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temp).unlink(missing_ok=True)


def _receipt_matches(
    receipt: dict, asset: str, path: Path, interval: str, start: int, end: int
) -> bool:
    return (
        receipt.get("schema_version") == 1
        and receipt.get("status") == "complete"
        and receipt.get("asset") == asset
        and receipt.get("instrument") == f"{asset}/USD"
        and receipt.get("venue") == "coinbase_exchange"
        and receipt.get("source") == SOURCE.format(product=f"{asset}-USD")
        and receipt.get("interval") == interval
        and receipt.get("requested_start") == start
        and receipt.get("requested_end_exclusive") == end
        and receipt.get("sha256") == file_sha256(path)
    )


def acquire(
    asset: str,
    output_dir: str | Path,
    *,
    start: str,
    end: str,
    interval: str = "1d",
    offline: bool = False,
) -> dict:
    """Acquire a fully covered Coinbase asset/USD series or report a blocked cell.

    Only an input with a matching receipt and byte digest is reusable offline.
    Existing bare CSVs remain unverified. Network responses are validated before
    publication, and neither raw data nor receipts overwrite earlier content.
    Quote/venue substitutions and gap filling are deliberately unsupported.
    """
    try:
        asset = _symbol(asset)
        if (
            interval not in INTERVAL_SECONDS
            or INTERVAL_SECONDS[interval] not in SUPPORTED_GRANULARITIES
        ):
            raise ValueError("unsupported_interval")
        if type(offline) is not bool:
            raise ValueError("invalid_offline_mode")
        lo, hi = _epoch(start), _epoch(end)
        step = INTERVAL_SECONDS[interval]
        if lo >= hi or lo % step or hi % step or (hi - lo) // step > 2_000_000:
            raise ValueError("invalid_requested_window")
        if hi > int(time.time() // step) * step:
            raise ValueError("requested_bars_not_closed")
    except (ValueError, TypeError, OverflowError) as exc:
        return {
            "status": "blocked",
            "asset": asset
            if isinstance(asset, str) and ASSET_PATTERN.fullmatch(asset)
            else None,
            "reason": "removed_asset" if str(exc) == "removed_asset" else "invalid_acquisition_request",
        }
    directory = Path(output_dir).expanduser().absolute()
    path = directory / f"{asset}_{interval}.csv"
    receipt_path = path.with_suffix(".receipt.json")
    base = {
        "schema_version": 1,
        "asset": asset,
        "instrument": f"{asset}/USD",
        "venue": "coinbase_exchange",
        "source": SOURCE.format(product=f"{asset}-USD"),
        "interval": interval,
        "interval_seconds": step,
        "path": str(path),
        "requested_start": lo,
        "requested_end_exclusive": hi,
        "timestamp_semantics": "utc_bar_open",
        "reason": None,
    }
    try:
        if path.is_symlink() or receipt_path.is_symlink():
            raise ValueError("unsafe_cache_path")
        if path.is_file() and receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text())
            if not isinstance(receipt, dict) or not _receipt_matches(
                receipt, asset, path, interval, lo, hi
            ):
                return {
                    **base,
                    "status": "blocked",
                    "reason": "cache_receipt_mismatch_use_new_directory",
                }
            frame = _closed_frame(pd.read_csv(path), lo, hi, interval)
            if receipt.get("coverage") != {
                "first_ts": int(frame["timestamp"].iloc[0]),
                "last_ts": int(frame["timestamp"].iloc[-1]),
                "bars": len(frame),
                "gaps": 0,
                "requested_window_complete": True,
            }:
                return {
                    **base,
                    "status": "blocked",
                    "reason": "cache_coverage_mismatch",
                }
            return {**receipt, "cache_reused": True}
        if offline:
            return {**base, "status": "blocked", "reason": "verified_cache_unavailable"}
        frame = fetch_coinbase(f"{asset}-USD", start, end, interval, verbose=False)
        frame = _closed_frame(frame, lo, hi, interval)
        raw = (
            frame.loc[:, list(BAR_COLUMNS)]
            .to_csv(index=False, lineterminator="\n")
            .encode()
        )
        receipt = {
            **base,
            "status": "complete",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "coverage": {
                "first_ts": int(frame["timestamp"].iloc[0]),
                "last_ts": int(frame["timestamp"].iloc[-1]),
                "bars": len(frame),
                "gaps": 0,
                "requested_window_complete": True,
            },
            "acquired_at": time.time(),
            "cache_reused": False,
        }
        _publish(path, raw)
        _publish(receipt_path, canonical(receipt))
        return receipt
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        FetchError,
        DataValidationError,
        OverflowError,
    ):
        return {
            **base,
            "status": "blocked",
            "reason": "source_unavailable_invalid_or_incomplete",
        }

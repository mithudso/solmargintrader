"""Read-only, bounded snapshots of an explicitly registered Coinbase recorder.

A sampled midpoint candle is a reference input, never an observed venue candle or
an executable Jupiter quote. Recorder format v1 does not record book/ticker
provenance. Preserve that uncertainty instead of inferring it from quote age.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import re
import time
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from .domain import ManagerError, fingerprint

MAX_BARS = 2048
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_SCAN_BYTES = 256 * 1024 * 1024


@lru_cache(maxsize=8)
def engine_identity(strategy_id: str = "grid") -> dict[str, Any]:
    import numpy

    import backtester
    from backtester.core import gridsim, metrics, types

    modules = [metrics, types]
    if strategy_id == "grid":
        modules += [gridsim]
    elif strategy_id == "dca":
        from backtester.core import dcasim

        modules += [dcasim]
    else:
        from backtester.core import engine, indicators, perps

        modules += [engine, indicators, perps]
        if strategy_id == "trend":
            from soltui import trend

            modules += [trend]
        elif strategy_id == "momentum":
            from backtester.core.strategies import signals

            modules += [signals]
        else:
            raise ManagerError(
                "capability_unavailable", "Unknown reference strategy.", 3
            )

    return {
        "package": "solmargintrader-backtester/" + backtester.__version__,
        "numpy": numpy.__version__,
        "modules": {
            module.__name__: hashlib.sha256(
                Path(module.__file__).read_bytes()
            ).hexdigest()
            for module in modules
        },
    }


def _number(value: Any, *, positive: bool = False) -> float:
    if (
        type(value) not in (int, float)
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        raise ValueError
    return float(value)


def load_recording(
    descriptor: dict[str, Any], *, strategy_id: str = "grid"
) -> dict[str, Any]:
    """Capture a fixed closed interval; refuse gaps, stale quotes and truncation.

    All costs and reference-account units are explicit. Source files are opened
    read-only. Neither this module nor its dependencies start a recorder.
    """
    if isinstance(descriptor, dict) and descriptor.get("source") == "oracle_archive":
        from .oracle_data import capture

        return capture(descriptor, strategy_id=strategy_id)
    try:
        required = {
            "schema_version",
            "installation_id",
            "source",
            "paths",
            "product",
            "quote_currency",
            "bar_seconds",
            "start_ts",
            "end_ts",
            "fee_bps",
            "slippage_bps",
            "carry_bps_per_hour",
            "min_order_quote",
            "capital_quote",
        }
        if (
            not isinstance(descriptor, dict)
            or not required <= descriptor.keys()
            or descriptor.keys()
            - required
            - {"max_bars", "max_quote_age_s", "max_sample_gap_s"}
        ):
            raise ValueError
        d = dict(descriptor)
        if (
            type(d["schema_version"]) is not int
            or d["schema_version"] != 1
            or d["source"] != "coinbase_exchange_recorder"
        ):
            raise ValueError
        if not isinstance(d["installation_id"], str) or not re.fullmatch(
            r"[a-zA-Z0-9_.-]{1,80}", d["installation_id"]
        ):
            raise ValueError
        if (
            d["product"] not in ("SOL-USD", "SOL-USDC")
            or d["quote_currency"] != d["product"].split("-")[1]
        ):
            raise ValueError
        if type(d["bar_seconds"]) is not int or d["bar_seconds"] != 60:
            raise ValueError
        for key in ("start_ts", "end_ts"):
            if type(d[key]) is not int or d[key] <= 0 or d[key] % 60:
                raise ValueError
        if d["end_ts"] > time.time():
            raise ValueError
        limit = d.setdefault("max_bars", MAX_BARS)
        if type(limit) is not int or not 1 <= limit <= MAX_BARS:
            raise ValueError
        n = (d["end_ts"] - d["start_ts"]) // 60
        if not 1 <= n <= limit:
            raise ManagerError(
                "resource_limit", "Reference input exceeds the bounded replay limit.", 3
            )
        for key in (
            "fee_bps",
            "slippage_bps",
            "carry_bps_per_hour",
            "min_order_quote",
            "capital_quote",
        ):
            d[key] = _number(
                d[key], positive=key in ("capital_quote", "min_order_quote")
            )
        if d["slippage_bps"] >= 10000 or d["fee_bps"] >= 10000:
            raise ValueError
        for key in ("max_quote_age_s", "max_sample_gap_s"):
            d[key] = _number(d.get(key, 5.0), positive=True)
            if d[key] > 5:
                raise ValueError
        paths = d["paths"]
        if (
            not isinstance(paths, list)
            or not 1 <= len(paths) <= 4
            or len(set(paths)) != len(paths)
        ):
            raise ValueError
        bars: list[dict] = []
        sources = []
        previous = None
        scan = 0
        max_age = 0.0
        samples = 0
        for name in paths:
            path = Path(name)
            if not path.is_absolute() or not path.is_file():
                raise ValueError
            with path.open("rb") as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise ManagerError(
                    "resource_limit", "Recording file exceeds the capture limit.", 3
                )
            sources.append(
                {
                    "path": str(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "byte_high_watermark": len(raw),
                }
            )
            stream = (
                gzip.GzipFile(fileobj=io.BytesIO(raw))
                if path.suffix == ".gz"
                else io.BytesIO(raw)
            )
            with stream:
                while True:
                    line = stream.readline(1024 * 1024 + 1)
                    if not line:
                        break
                    scan += len(line)
                    if len(line) > 1024 * 1024 or scan > MAX_SCAN_BYTES:
                        raise ManagerError(
                            "resource_limit",
                            "Recording scan exceeds the capture limit.",
                            3,
                        )
                    if not line.endswith(b"\n"):
                        raise ValueError
                    row = json.loads(line)
                    t = _number(row["t"], positive=True)
                    if t < d["start_ts"]:
                        continue
                    if t >= d["end_ts"]:
                        break
                    q = row["q"][d["product"]]
                    if not isinstance(q, list) or len(q) < 6:
                        raise ValueError
                    bid, ask, qt = (_number(q[i], positive=True) for i in (0, 1, 5))
                    age = t - qt
                    if ask < bid or age < 0 or age > d["max_quote_age_s"]:
                        raise ValueError
                    if previous is not None and (
                        t <= previous or t - previous > d["max_sample_gap_s"]
                    ):
                        raise ValueError
                    previous = t
                    max_age = max(age, max_age)
                    samples += 1
                    ts = int(t) // 60 * 60
                    price = (bid + ask) / 2
                    if not bars or bars[-1]["ts"] != ts:
                        if bars and ts != bars[-1]["ts"] + 60:
                            raise ValueError
                        bars.append(
                            {
                                "ts": ts,
                                "open": price,
                                "high": price,
                                "low": price,
                                "close": price,
                                "first_arrival": t,
                                "last_arrival": t,
                                "max_quote_age_s": age,
                            }
                        )
                    else:
                        bar = bars[-1]
                        bar.update(
                            high=max(bar["high"], price),
                            low=min(bar["low"], price),
                            close=price,
                            last_arrival=t,
                            max_quote_age_s=max(bar["max_quote_age_s"], age),
                        )
        if (
            len(bars) != n
            or bars[0]["ts"] != d["start_ts"]
            or bars[-1]["ts"] + 60 != d["end_ts"]
        ):
            raise ValueError
        if any(
            b["first_arrival"] - b["ts"] > d["max_sample_gap_s"]
            or b["ts"] + 60 - b["last_arrival"] > d["max_sample_gap_s"]
            for b in bars
        ):
            raise ValueError
        identity = {
            "schema_version": 1,
            "kind": "reference_paper",
            "venue": "coinbase_proxy",
            "source": d["source"],
            "installation_id": d["installation_id"],
            "product": d["product"],
            "quote_currency": d["quote_currency"],
            "base_currency": "SOL",
            "bar_seconds": 60,
            "execution_model": {
                "grid": "sampled_mid_ohlc_resting_ladder",
                "dca": "sampled_mid_safety_orders",
                "trend": "sampled_mid_next_open",
                "momentum": "sampled_mid_next_open",
            }[strategy_id],
            "volume": None,
            "volume_reason": "not_observed",
            "quote_provenance": "not_recorded_book_or_ticker_unknown",
            "quote_age_max_seconds": max_age,
            "samples": samples,
            "start_ts": d["start_ts"],
            "end_ts": d["end_ts"],
            "sources": sources,
            "costs": {
                k: d[k]
                for k in (
                    "fee_bps",
                    "slippage_bps",
                    "carry_bps_per_hour",
                    "min_order_quote",
                )
            },
            "capital_quote": d["capital_quote"],
            "engine": engine_identity(strategy_id)["package"],
            "engine_identity": engine_identity(strategy_id),
            "venue_compatibility_verified": False,
            "live_eligible": False,
            "arrival_policy": "recorded_arrivals_bounded_historical_replay",
        }
        result = {
            "schema_version": 1,
            "descriptor": d,
            "identity": identity,
            "bars": bars,
        }
        result["snapshot_hash"] = fingerprint(result)
        return result
    except ManagerError:
        raise
    except (
        OSError,
        EOFError,
        zlib.error,
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
    ) as exc:
        raise ManagerError(
            "input_unavailable",
            "Recording identity, costs, coverage or quotes are missing or invalid.",
            3,
        ) from exc


def validate_snapshot(data: dict[str, Any]) -> None:
    try:
        body = {k: v for k, v in data.items() if k != "snapshot_hash"}
        if (
            data["snapshot_hash"] != fingerprint(body)
            or not (0 if data.get("prospective") is not None else 1)
            <= len(data["bars"])
            <= MAX_BARS
        ):
            raise ValueError
    except (KeyError, ValueError, TypeError) as exc:
        raise ManagerError(
            "corrupt_checkpoint",
            "Pinned reference input failed integrity validation.",
            4,
        ) from exc

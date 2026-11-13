"""Canonical closed-bar spot decisions, never execution quotes or order authority."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import time
from collections import deque
from numbers import Integral
from pathlib import Path

from .server import COINS, INTERVALS, MAX_BARS, MAX_CACHE_BYTES, RequestError
from .state import canonical

ECONOMIC_VERSION = "canonical_spot_target_fill_delay_1_v1"
MAX_AGE = 15
MAX_COMPUTE_SECONDS = 5


class SignalUnavailable(ValueError):
    """A fixed public reason; never include upstream data or exception text."""


def validate_request(body):
    if not isinstance(body, dict) or set(body) != {"coin", "strategy", "interval"}:
        raise RequestError("invalid_signal_request")
    if any(
        not isinstance(body[key], str) or not body[key] or len(body[key]) > maximum
        for key, maximum in (("coin", 16), ("strategy", 100), ("interval", 16))
    ):
        raise RequestError("invalid_signal_request")
    return body


def supported(body):
    from backtester.core.strategies import REGISTRY

    return (
        body["coin"] in COINS
        and body["interval"] in INTERVALS
        and body["strategy"] in REGISTRY
    )


def strategy_revision(key, identity, *, strategy=None):
    from backtester.core.strategies import build

    strategy = strategy if strategy is not None else build(key)
    return hashlib.sha256(
        canonical(
            {
                "sourceIdentity": identity["sha256"],
                "strategy": key,
                "class": type(strategy).__module__ + "." + type(strategy).__qualname__,
                "parameters": strategy.params,
                "economicVersion": ECONOMIC_VERSION,
                "mode": "spot",
                "fillDelay": 1,
                "allowShort": False,
            }
        )
    ).hexdigest()


def unavailable(body, now, reason):
    return {
        **body,
        "status": "unavailable",
        "asOf": now,
        "reason": reason,
        "executionQuote": False,
    }


def closed_history(root, body, now):
    """Read bounded public provenance and exclude incomplete bars before replay."""
    import pandas as pd

    from backtester.core.data import frame_to_arrays, validate_bars
    from backtester.core.types import BAR_COLUMNS, INTERVAL_SECONDS, validate_bar_arrays

    path = Path(root) / f"{body['coin']}_{body['interval']}.csv"
    try:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.stat().st_size > MAX_CACHE_BYTES
        ):
            raise SignalUnavailable("cached_history_unavailable")
        with path.open("rb") as handle:
            raw = handle.read(MAX_CACHE_BYTES + 1)
        if len(raw) > MAX_CACHE_BYTES:
            raise SignalUnavailable("cached_history_unavailable")
        source_hash = hashlib.sha256(raw).hexdigest()
        provenance = path.with_suffix(".json")
        if (
            provenance.is_symlink()
            or not provenance.is_file()
            or provenance.stat().st_size > 4096
        ):
            raise SignalUnavailable("public_provenance_unavailable")
        metadata = json.loads(provenance.read_bytes())
        if (
            not isinstance(metadata, dict)
            or metadata.get("provider") != "https://api.exchange.coinbase.com"
            or metadata.get("product") != body["coin"] + "-USD"
            or metadata.get("interval") != body["interval"]
            or metadata.get("sha256") != source_hash
        ):
            raise SignalUnavailable("public_provenance_unavailable")
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")))
        if reader.fieldnames != list(BAR_COLUMNS):
            raise SignalUnavailable("invalid_cached_history")
        numeric = pd.DataFrame(deque(reader, maxlen=MAX_BARS)).apply(pd.to_numeric)
        if numeric.empty:
            raise SignalUnavailable("insufficient_strategy_history")
        seconds = INTERVAL_SECONDS[body["interval"]]
        frame = validate_bars(
            numeric[numeric.timestamp + seconds <= now],
            body["interval"],
            strict_gaps=True,
        )
        # validate_bars rejects large gaps; the simulation's array validator also
        # rejects sub-interval cadence. Every bar must use the venue UTC grid.
        validate_bar_arrays(frame_to_arrays(frame), body["interval"])
        if (frame.timestamp % seconds).any():
            raise SignalUnavailable("invalid_cached_history")
        if int(frame.timestamp.iloc[-1]) + seconds != int(now // seconds) * seconds:
            raise SignalUnavailable("stale_history")
        # Hash only selected completed bars. A changing future partial candle
        # cannot affect either the target or its immutable signal identity.
        input_hash = hashlib.sha256(
            frame.astype("float64").to_csv(index=False, lineterminator="\n").encode()
        ).hexdigest()
        return frame, input_hash, source_hash
    except SignalUnavailable:
        raise
    except (OSError, ValueError, TypeError, KeyError, OverflowError):
        raise SignalUnavailable("history_not_usable") from None


def current_observation(market, coin, now):
    observation = market.get("observation", {})
    if (
        market.get("status") != "available"
        or market.get("instrument") != coin + "/USD"
        or observation.get("instrument") != coin + "/USD"
        or observation.get("source") != "coinbase_exchange_public"
        or observation.get("provider") != "api.exchange.coinbase.com"
        or observation.get("timestamp_semantics") != "exchange_trade_time"
        or observation.get("upstream_recency_verified") is not True
    ):
        raise SignalUnavailable("fresh_market_observation_required")
    for key in ("observed_at", "received_at"):
        value = observation.get(key)
        if (
            type(value) not in (int, float)
            or not math.isfinite(value)
            or not 0 <= now - value <= MAX_AGE
        ):
            raise SignalUnavailable("fresh_market_observation_required")
    return observation


def calculate(body, history, market, identity, now, *, monotonic=time.monotonic):
    from backtester.core.data import frame_to_arrays
    from backtester.core.engine import _resolve_target
    from backtester.core.strategies import build
    from backtester.core.types import INTERVAL_SECONDS, BarWindow, Mode

    observation = current_observation(market, body["coin"], now)
    frame, input_hash, source_hash = history
    try:
        strategy = build(body["strategy"])
        revision = strategy_revision(body["strategy"], identity, strategy=strategy)
        warmup = strategy.warmup_bars()
        if (
            isinstance(warmup, bool)
            or not isinstance(warmup, Integral)
            or warmup < 0
            or warmup >= len(frame)
        ):
            raise SignalUnavailable("insufficient_strategy_history")
        arrays = frame_to_arrays(frame)
        began = monotonic()
        # Replay the same stateful strategy callbacks and structural no-lookahead
        # window as the canonical engine. Its final target is scheduled for the
        # following bar (fill_delay=1), never filled at this historical close.
        for i in range(warmup, len(frame)):
            if monotonic() - began > MAX_COMPUTE_SECONDS:
                raise SignalUnavailable("signal_compute_budget_exceeded")
            window = BarWindow(
                arrays["ts"],
                arrays["open"],
                arrays["high"],
                arrays["low"],
                arrays["close"],
                arrays["volume"],
                i,
            )
            target = _resolve_target(strategy.on_bar(window), Mode.SPOT, False)
        if target not in (0.0, 1.0):
            raise SignalUnavailable("unsupported_fractional_target")
    except SignalUnavailable:
        raise
    except Exception:  # noqa: BLE001 - trusted canonical strategy errors are sanitized at this boundary.
        raise SignalUnavailable("strategy_not_usable") from None
    seconds = INTERVAL_SECONDS[body["interval"]]
    start = int(frame.timestamp.iloc[-1])
    end = start + seconds
    expires = min(
        end + seconds,
        observation["observed_at"] + MAX_AGE,
        observation["received_at"] + MAX_AGE,
    )
    return {
        **body,
        "status": "available",
        "mode": "spot",
        "desiredExposure": int(target),
        "inputHash": input_hash,
        "sourceHash": source_hash,
        "sourceIdentity": identity,
        "strategyRevision": revision,
        "economicVersion": ECONOMIC_VERSION,
        "signalId": hashlib.sha256(
            canonical(
                {
                    **body,
                    "barStart": start,
                    "barEnd": end,
                    "inputHash": input_hash,
                    "strategyRevision": revision,
                    "economicVersion": ECONOMIC_VERSION,
                }
            )
        ).hexdigest(),
        "barStart": start,
        "barEnd": end,
        "asOf": now,
        "expiresAt": expires,
        "fillDelay": 1,
        "executionQuote": False,
        "marketObservation": {
            "observedAt": observation["observed_at"],
            "receivedAt": observation["received_at"],
            "eventId": observation["event_id"],
            "source": observation["source"],
        },
    }

"""Typed constructor snapshots, with exact-context learned-default adoption."""

from __future__ import annotations

import math
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from .domain import ManagerError, ResolvedConfig

SOURCE_REVISION = "78468489cc968e25b87786246a5aa3edf43d2277"
SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
STRATEGY_VERSIONS = MappingProxyType(
    {
        "grid": "grid-ladder-v1",
        "dca": "safety-order-v1",
        "trend": "sma-crossover-v1",
        "momentum": "ts-momentum-v1",
    }
)
MODELS = MappingProxyType(
    {
        "grid": "trigger_ladder",
        "dca": "safety_order_ladder",
        "trend": "next_open",
        "momentum": "next_open",
    }
)
DEFAULT_CONTEXT = MappingProxyType(
    {
        "venue": "jupiter",
        "base_mint": SOL_MINT,
        "quote_mint": USDC_MINT,
        "bar_seconds": 60,
    }
)
COMMON = MappingProxyType(
    {
        "mode": "paper",
        "armed": False,
        **DEFAULT_CONTEXT,
        "capital_usd": 1000.0,
        "timezone": "UTC",
        "lot_method": "FIFO",
    }
)
DEFAULTS = MappingProxyType(
    {
        "grid": MappingProxyType(
            {"range_pct": 15.0, "rungs": 7, "spacing": "geom", "deadband_bps": 25.0}
        ),
        "dca": MappingProxyType(
            {
                "base_order_usd": 100.0,
                "safety_order_usd": 100.0,
                "max_safety_orders": 5,
                "price_deviation_pct": 2.0,
                "step_scale": 1.0,
                "volume_scale": 1.0,
                "take_profit_pct": 2.0,
                "stop_loss_pct": 0.0,
                "cooldown_bars": 0,
                "min_order_usd": 10.0,
            }
        ),
        "trend": MappingProxyType(
            {"fast_period": 10, "slow_period": 30, "entry_buffer_bps": 10.0}
        ),
        "momentum": MappingProxyType({"window": 60, "threshold": 0.0}),
    }
)
SOURCE_FILES = {
    "grid": "soltui/bots.py:GRID_DEFAULTS",
    "dca": "backtester/core/dcasim.py:DcaConfig",
    "trend": "soltui/trend.py:TrendConfig",
    "momentum": "backtester/core/strategies/signals.py:TsMomentum",
}
SHARED_PROTECTED_FIELDS = frozenset(
    {
        "capital_usd",
        "base_order_usd",
        "safety_order_usd",
        "stop_loss_pct",
        "min_order_usd",
    }
)


def _invalid() -> ManagerError:
    # Do not interpolate user values or unknown keys: they may contain credentials.
    return ManagerError(
        "invalid_input", "Unknown, nonfinite, wrongly typed, or out-of-range settings."
    )


def _strategy(strategy_id: str) -> None:
    if not isinstance(strategy_id, str):
        raise _invalid()
    if strategy_id in ("arbitrage", "triangle"):
        raise ManagerError(
            "solana_adapter_unavailable", "Solana adapter unavailable.", 3
        )
    if strategy_id == "council":
        raise ManagerError(
            "external_only",
            "Council is external-only; use its advertised owner controls.",
            3,
        )
    if strategy_id not in DEFAULTS:
        raise _invalid()


def validate_values(strategy_id: str, values: Mapping[str, Any]) -> None:
    _strategy(strategy_id)
    defaults = {
        **COMMON,
        **DEFAULTS[strategy_id],
        "execution_model": MODELS[strategy_id],
    }
    if set(values) != set(defaults):
        raise _invalid()
    for key, default in defaults.items():
        value = values[key]
        if type(default) is float:
            try:
                finite = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise _invalid()
        elif type(value) is not type(default):
            raise _invalid()
    for key in (
        "mode",
        "armed",
        "venue",
        "base_mint",
        "quote_mint",
        "timezone",
        "lot_method",
        "execution_model",
    ):
        if values[key] != defaults[key]:
            raise _invalid()
    if values["bar_seconds"] < 1 or values["capital_usd"] <= 0:
        raise _invalid()
    if strategy_id == "grid":
        if not (
            0 < values["range_pct"] < 100
            and 2 <= values["rungs"] <= 500
            and values["spacing"] in ("geom", "arith")
            and 0 <= values["deadband_bps"] < 10000
        ):
            raise _invalid()
    elif strategy_id == "trend":
        if not (
            1 <= values["fast_period"] < values["slow_period"]
            and 0 <= values["entry_buffer_bps"] < 10000
        ):
            raise _invalid()
    elif strategy_id == "momentum":
        if values["window"] < 1:
            raise _invalid()
    elif strategy_id == "dca":
        if not (
            0 <= values["max_safety_orders"] <= 50
            and values["cooldown_bars"] >= 0
            and values["min_order_usd"] >= 0
            and values["base_order_usd"] >= max(values["min_order_usd"], 1e-9)
            and values["safety_order_usd"] >= 0
            and (
                not values["max_safety_orders"]
                or values["safety_order_usd"] >= max(values["min_order_usd"], 1e-9)
            )
            and values["price_deviation_pct"] > 0
            and values["step_scale"] > 0
            and values["volume_scale"] > 0
            and values["take_profit_pct"] > 0
            and 0 <= values["stop_loss_pct"] < 100
        ):
            raise _invalid()
        depth = 0.0
        step = values["price_deviation_pct"]
        size = values["safety_order_usd"]
        try:
            for _ in range(values["max_safety_orders"]):
                depth += step
                if depth >= 100 or not math.isfinite(size):
                    raise _invalid()
                step *= values["step_scale"]
                size *= values["volume_scale"]
        except OverflowError as exc:
            raise _invalid() from exc


def resolve_config(
    strategy_id: str,
    context: Mapping[str, Any] | None,
    overrides: Mapping[str, Any] | None,
    shared_snapshot: Mapping[str, Any] | None,
) -> ResolvedConfig:
    _strategy(strategy_id)
    context = {} if context is None else context
    overrides = {} if overrides is None else overrides
    if not isinstance(context, Mapping) or not isinstance(overrides, Mapping):
        raise _invalid()
    context_fields = {*DEFAULT_CONTEXT, "execution_model"}
    if not set(context) <= context_fields:
        raise _invalid()
    values = {**COMMON, **DEFAULTS[strategy_id], "execution_model": MODELS[strategy_id]}
    values.update(context)
    if not set(overrides) <= set(values):
        raise _invalid()
    # Identity/context fields are part of the compatibility key even when manually set.
    effective_context = {key: overrides.get(key, values[key]) for key in context_fields}
    values.update(effective_context)
    validate_values(strategy_id, values)
    compatibility: dict[str, Any] = {"accepted": False, "reason": "no_shared_snapshot"}
    if shared_snapshot is not None:
        if not isinstance(shared_snapshot, Mapping):
            raise _invalid()
        shared_context = shared_snapshot.get("context")
        compatible = (
            type(shared_snapshot.get("schema_version")) is int
            and shared_snapshot.get("schema_version") == 1
            and shared_snapshot.get("strategy_id") == strategy_id
            and shared_snapshot.get("strategy_version")
            == STRATEGY_VERSIONS[strategy_id]
            and isinstance(shared_context, Mapping)
            and shared_context == effective_context
            and all(
                type(shared_context[key]) is type(value)
                for key, value in effective_context.items()
            )
        )
        compatibility = {
            "accepted": compatible,
            "reason": "exact_semantics_match"
            if compatible
            else "incompatible_shared_context",
        }
    constructor_fields = set(DEFAULTS[strategy_id]) | (
        {"capital_usd"} if strategy_id in ("grid", "trend") else set()
    )
    provenance = {
        key: {
            "source": "context" if key in context else "packaged",
            "source_revision": SOURCE_REVISION
            if key in constructor_fields
            else "manager-defaults-v1",
            "reason": (
                "explicit_context"
                if key in context
                else "constructor_reference:" + SOURCE_FILES[strategy_id]
                if key in constructor_fields
                else "application_default"
            )
            + ";"
            + compatibility["reason"],
        }
        for key in values
    }
    if compatibility["accepted"]:
        shared_values = shared_snapshot.get("values")
        revision = shared_snapshot.get("revision")
        if (
            not isinstance(shared_values, Mapping)
            or not isinstance(revision, str)
            or not revision
        ):
            raise _invalid()
        # Learning must not alter manual operating or risk settings.
        if (
            not set(shared_values)
            <= set(DEFAULTS[strategy_id]) - SHARED_PROTECTED_FIELDS
        ):
            raise _invalid()
        candidate = {**values, **shared_values}
        validate_values(strategy_id, candidate)
        values = candidate
        for key in shared_values:
            provenance[key] = {
                "source": "shared",
                "source_revision": revision,
                "reason": "exact_semantics_match",
            }
    values.update(overrides)
    validate_values(strategy_id, values)
    for key in overrides:
        provenance[key] = {
            "source": "override",
            "source_revision": "creation-override-v1",
            "reason": "manual_pin;" + compatibility["reason"],
        }
    return ResolvedConfig(values, provenance, overrides, compatibility)

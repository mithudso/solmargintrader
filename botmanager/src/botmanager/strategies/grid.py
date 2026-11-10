"""Bounded prefix replay of the canonical ladder; no copied trading algorithm."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..data import engine_identity, validate_snapshot
from ..domain import BotSpec, ManagerError, fingerprint
from .base import compatible_engine

MAX_REFERENCE_RUNGS = 100
MAX_REFERENCE_RANGE_PCT = 95
REFERENCE_BAR_SECONDS = 60


def _configuration(spec: BotSpec, data: dict[str, Any]):
    from backtester.core.gridsim import GridConfig

    if (
        spec.strategy_id != "grid"
        or spec.mode != "paper"
        or spec.resolved_values["armed"]
        or spec.bar_seconds != REFERENCE_BAR_SECONDS
    ):
        raise ManagerError(
            "capability_unavailable",
            "Only disarmed one-minute grid reference replay is available.",
            3,
        )
    values = spec.resolved_values
    if values["rungs"] > MAX_REFERENCE_RUNGS:
        raise ManagerError(
            "resource_limit", "Reference replay supports at most 100 rungs.", 3
        )
    d = data["descriptor"]
    # A committed segment can have no active bars while waiting for its first
    # closed bin. Do not evaluate the first-bar fallback when the origin exists.
    if "origin_close" in data:
        mid = data["origin_close"]
    elif data["bars"]:
        mid = data["bars"][0]["close"]
    else:
        raise ManagerError("input_unavailable", "Grid origin price is unavailable.", 3)
    span = values["range_pct"] / 100
    if (
        values["range_pct"] >= MAX_REFERENCE_RANGE_PCT
        or d["capital_quote"] != values["capital_usd"]
        or d["capital_quote"] / values["rungs"] < d["min_order_quote"]
    ):
        raise ManagerError(
            "input_unavailable",
            "Reference sizing or range disagrees with the pinned constructor.",
            3,
        )
    return GridConfig(
        mid * (1 - span),
        mid * (1 + span),
        values["rungs"],
        d["capital_quote"] / values["rungs"],
        values["spacing"],
        values["deadband_bps"],
        d["min_order_quote"],
    )


def run_identity(spec: BotSpec, data: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct every immutable evidence field from the pinned run inputs."""
    return {
        "bot_id": spec.bot_id,
        "config_hash": spec.config_hash,
        "config_revision": spec.config_revision,
        "strategy_version": spec.strategy_version,
        "snapshot_hash": data.get("origin_hash", data["snapshot_hash"]),
        "reference": data["identity"],
        "target": {
            "venue": spec.venue,
            "base_mint": spec.base_mint,
            "quote_mint": spec.quote_mint,
            "execution_model": spec.execution_model,
        },
        "virtual_account": "independent_not_a_funded_wallet",
        "grid": _configuration(spec, data).to_dict(),
    }


def validate_checkpoint(
    spec: BotSpec,
    data: dict[str, Any],
    checkpoint: dict[str, Any],
    *,
    code: str = "corrupt_checkpoint",
    allow_prior=False,
) -> None:
    """A matching config alone cannot attribute a result to a virtual account."""
    try:
        expected = run_identity(spec, data)
        expected_hash = fingerprint(expected)
        cursor = checkpoint["cursor"]
        if (
            type(checkpoint["schema_version"]) is not int
            or checkpoint["schema_version"] != 1
            or type(cursor) is not int
            or not data.get("bar_offset", 0)
            <= cursor
            <= data.get("bar_offset", 0) + len(data["bars"])
            or (
                cursor > data.get("bar_offset", 0)
                and checkpoint["last_bar_ts"]
                != data["bars"][cursor - data.get("bar_offset", 0) - 1]["ts"]
            )
            or (
                not allow_prior
                and checkpoint.get("prior_segment") != data.get("prior_segment")
            )
            or checkpoint["quote_currency"] != data["identity"]["quote_currency"]
            or fingerprint(checkpoint["identity"]) != expected_hash
            or checkpoint["run_hash"] != expected_hash
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError, ManagerError) as exc:
        raise ManagerError(
            code, "Checkpoint identity does not match the pinned reference run.", 4
        ) from exc


def evaluate(
    spec: BotSpec,
    data: dict[str, Any],
    cursor: int,
    *,
    research=False,
    previous=None,
    entries_paused=False,
) -> dict[str, Any]:
    import numpy as np

    from backtester.core.gridsim import run_grid_backtest
    from backtester.core.types import CostConfig

    validate_snapshot(data)
    if not compatible_engine(data["identity"]["engine_identity"], engine_identity()):
        raise ManagerError(
            "engine_identity_changed",
            "Pinned simulation engine differs from the loaded engine.",
            3,
        )
    if type(cursor) is not int or not data.get("bar_offset", 0) <= cursor <= data.get(
        "bar_offset", 0
    ) + len(data["bars"]):
        raise ManagerError(
            "invalid_input", "Replay cursor is outside the immutable input."
        )
    offset = data.get("bar_offset", 0)
    start = previous["cursor"] - offset if previous else 0
    if start < 0 or start >= cursor - offset:
        raise ManagerError(
            "stale_cursor", "Continuation cursor does not advance the account.", 3
        )
    if previous:
        saved = previous.get("continuation")
        if (
            not isinstance(saved, dict)
            or saved.get("schema_version") != 1
            or saved.get("cursor") != previous["cursor"]
            or saved.get("last_ts") != previous["last_bar_ts"]
        ):
            raise ManagerError(
                "continuation_unavailable",
                "The prior account lacks compatible canonical continuation state.",
                3,
            )
        validate_checkpoint(spec, data, previous, allow_prior=True)
    cfg = _configuration(spec, data)
    d = data["descriptor"]
    arrays = {
        key: np.array([b[key] for b in data["bars"][start : cursor - offset]])
        for key in ("ts", "high", "low", "close")
    }
    result = run_grid_backtest(
        cfg,
        arrays,
        initial_capital=d["capital_quote"],
        interval="1m",
        costs=CostConfig(fee_bps=d["fee_bps"], slippage_bps=d["slippage_bps"]),
        carry_bps_per_hour=d["carry_bps_per_hour"],
        close_at_end=False,
        continuation=previous.get("continuation") if previous else None,
        entries_paused=entries_paused,
    )
    fills = (
        previous["fills"]
        if previous and previous.get("prior_segment") == data.get("prior_segment")
        else []
    ) + [asdict(t) for t in result.trades]
    if len(fills) > 200000:
        raise ManagerError(
            "resource_limit", "Reference replay fill capacity is exhausted.", 3
        )
    exposure = result.unmatched_inventory_qty * float(arrays["close"][-1])
    equity = float(result.equity[-1])
    identity = run_identity(spec, data)
    state = {
        "schema_version": 1,
        "continuation": result.continuation,
        "prior_segment": data.get("prior_segment"),
        "cursor": cursor,
        "last_bar_ts": int(arrays["ts"][-1]),
        "fills": fills,
        "lots": [asdict(lot) for lot in result.open_lots_at_end],
        "equity_quote": equity,
        "exposure_quote": exposure,
        "cash_quote": equity - exposure,
        "realized_net_pnl_quote": result.realized_pnl_usd,
        "unrealized_net_pnl_quote": equity
        - d["capital_quote"]
        - result.realized_pnl_usd,
        "fees_quote": result.fees_paid_usd,
        "slippage_quote": result.slippage_paid_usd,
        "carry_paid_quote": result.carry_paid_usd,
        "carry_accrued_quote": sum(
            lot.accrued_carry_usd for lot in result.open_lots_at_end
        ),
        "quote_currency": d["quote_currency"],
        "identity": identity,
        "run_hash": fingerprint(identity),
    }

    if research:
        from .base import research_metrics

        state["research_metrics"] = research_metrics(result, d["capital_quote"])
    import json

    return json.loads(json.dumps(state))

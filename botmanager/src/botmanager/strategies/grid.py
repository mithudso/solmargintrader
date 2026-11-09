"""Bounded prefix replay of the canonical ladder; no copied trading algorithm."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ..data import engine_identity, validate_snapshot
from ..domain import BotSpec, ManagerError, fingerprint


def evaluate(spec: BotSpec, data: dict[str, Any], cursor: int) -> dict[str, Any]:
    import numpy as np

    from backtester.core.gridsim import GridConfig, run_grid_backtest
    from backtester.core.types import CostConfig

    validate_snapshot(data)
    if data["identity"]["engine_identity"] != engine_identity():
        raise ManagerError(
            "engine_identity_changed",
            "Pinned simulation engine differs from the loaded engine.",
            3,
        )
    if (
        spec.strategy_id != "grid"
        or spec.mode != "paper"
        or spec.resolved_values["armed"]
        or spec.bar_seconds != 60
    ):
        raise ManagerError(
            "capability_unavailable",
            "Only disarmed one-minute grid reference replay is available.",
            3,
        )
    if type(cursor) is not int or not 1 <= cursor <= len(data["bars"]):
        raise ManagerError(
            "invalid_input", "Replay cursor is outside the immutable input."
        )
    values = spec.resolved_values
    if values["rungs"] > 100:
        raise ManagerError(
            "resource_limit", "Reference replay supports at most 100 rungs.", 3
        )
    d = data["descriptor"]
    mid = data["bars"][0]["close"]
    span = values["range_pct"] / 100
    if (
        values["range_pct"] >= 95
        or d["capital_quote"] != values["capital_usd"]
        or d["capital_quote"] / values["rungs"] < d["min_order_quote"]
    ):
        raise ManagerError(
            "input_unavailable",
            "Reference sizing or range disagrees with the pinned constructor.",
            3,
        )
    cfg = GridConfig(
        mid * (1 - span),
        mid * (1 + span),
        values["rungs"],
        d["capital_quote"] / values["rungs"],
        values["spacing"],
        values["deadband_bps"],
        d["min_order_quote"],
    )
    arrays = {
        key: np.array([b[key] for b in data["bars"][:cursor]])
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
    )
    fills = [asdict(t) for t in result.trades]
    if len(fills) > 200000:
        raise ManagerError(
            "resource_limit", "Reference replay fill capacity is exhausted.", 3
        )
    exposure = result.unmatched_inventory_qty * float(arrays["close"][-1])
    equity = float(result.equity[-1])
    identity = {
        "bot_id": spec.bot_id,
        "config_hash": spec.config_hash,
        "config_revision": spec.config_revision,
        "strategy_version": spec.strategy_version,
        "snapshot_hash": data["snapshot_hash"],
        "reference": data["identity"],
        "target": {
            "venue": spec.venue,
            "base_mint": spec.base_mint,
            "quote_mint": spec.quote_mint,
            "execution_model": spec.execution_model,
        },
        "virtual_account": "independent_not_a_funded_wallet",
        "grid": cfg.to_dict(),
    }
    return {
        "schema_version": 1,
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

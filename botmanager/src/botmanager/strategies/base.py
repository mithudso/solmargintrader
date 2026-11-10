"""Shared account normalization; strategy decisions belong to canonical engines."""

from __future__ import annotations

from dataclasses import asdict

from ..data import engine_identity, validate_snapshot
from ..domain import ManagerError, fingerprint


def compatible_engine(pinned, loaded):
    """A packaging-only version bump does not invalidate the economic code."""
    return (
        pinned.get("modules") is not None
        and pinned.get("modules") == loaded.get("modules")
        and pinned.get("numpy") == loaded.get("numpy")
    )


def validate_input(spec, data):
    validate_snapshot(data)
    if spec.mode != "paper" or spec.resolved_values["armed"] or spec.bar_seconds != 60:
        raise ManagerError(
            "capability_unavailable",
            "Only disarmed one-minute reference paper is available.",
            3,
        )
    d = data["descriptor"]
    if (
        d["capital_quote"] != spec.resolved_values["capital_usd"]
        or d["capital_quote"] < d["min_order_quote"]
    ):
        raise ManagerError(
            "input_unavailable",
            "Reference capital differs from the pinned configuration.",
            3,
        )
    if spec.strategy_id == "grid":
        from .grid import MAX_REFERENCE_RANGE_PCT, MAX_REFERENCE_RUNGS

        if spec.resolved_values["rungs"] > MAX_REFERENCE_RUNGS:
            raise ManagerError(
                "resource_limit", "Reference replay supports at most 100 rungs.", 3
            )
        if (
            spec.resolved_values["range_pct"] >= MAX_REFERENCE_RANGE_PCT
            or d["capital_quote"] / spec.resolved_values["rungs"] < d["min_order_quote"]
        ):
            raise ManagerError(
                "input_unavailable", "Grid range or order sizing is incompatible.", 3
            )
    if (
        spec.strategy_id == "dca"
        and spec.resolved_values["min_order_usd"] < d["min_order_quote"]
    ):
        raise ManagerError(
            "input_unavailable", "DCA minimum order differs from the input floor.", 3
        )
    if spec.strategy_id != "grid" and d["carry_bps_per_hour"] != 0:
        raise ManagerError(
            "input_unavailable", "Spot DCA and signal engines do not model carry.", 3
        )


def identity(spec, data):
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
        "strategy": spec.strategy_id,
    }


def evaluate_family(
    spec, data, cursor, *, research=False, previous=None, entries_paused=False
):
    import numpy as np

    from backtester.core.types import CostConfig

    validate_input(spec, data)
    if not compatible_engine(
        data["identity"]["engine_identity"], engine_identity(spec.strategy_id)
    ):
        raise ManagerError(
            "engine_identity_changed",
            "Pinned economic engine differs from loaded code.",
            3,
        )
    if type(cursor) is not int or not data.get("bar_offset", 0) < cursor <= data.get(
        "bar_offset", 0
    ) + len(data["bars"]):
        raise ManagerError("invalid_input", "Cursor is outside the reference input.")
    d = data["descriptor"]
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
        from . import validate_checkpoint

        validate_checkpoint(spec, data, previous, allow_prior=True)
    if entries_paused and spec.strategy_id not in ("dca",):
        raise ManagerError(
            "capability_unavailable",
            "Entry pause is unsupported for signal accounts.",
            3,
        )
    values = spec.resolved_values
    arrays = {
        key: np.array([b[key] for b in data["bars"][start : cursor - offset]])
        for key in ("ts", "open", "high", "low", "close")
    }
    costs = CostConfig(fee_bps=d["fee_bps"], slippage_bps=d["slippage_bps"])
    if spec.strategy_id == "dca":
        from backtester.core.dcasim import DcaConfig, run_dca_backtest

        from ..config import DEFAULTS

        cfg = DcaConfig(**{k: values[k] for k in DEFAULTS["dca"]})
        if values["min_order_usd"] < d["min_order_quote"]:
            raise ManagerError(
                "input_unavailable",
                "DCA minimum order is below explicit reference floor.",
                3,
            )
        result = run_dca_backtest(
            cfg,
            arrays,
            initial_capital=d["capital_quote"],
            interval="1m",
            costs=costs,
            close_at_end=False,
            continuation=previous.get("continuation") if previous else None,
            entries_paused=entries_paused,
        )
        lots = [result.open_deal_at_end] if result.open_deal_at_end else []
        exposure = sum(l["qty"] for l in lots) * arrays["close"][-1]
        realized, fees, slip = (
            result.realized_pnl_usd,
            result.fees_paid_usd,
            result.slippage_paid_usd,
        )
        pending = None  # Canonical replay reconstructs deal safety/TP/next-open intent.
    else:
        from backtester.core.engine import EngineConfig, run_backtest

        if spec.strategy_id == "trend":
            from soltui.trend import TrendConfig, TrendFollowing

            strategy = TrendFollowing(
                TrendConfig(
                    **{
                        k: values[k]
                        for k in (
                            "fast_period",
                            "slow_period",
                            "entry_buffer_bps",
                            "capital_usd",
                        )
                    }
                )
            )
        else:
            from backtester.core.strategies.signals import TsMomentum

            strategy = TsMomentum(values["window"], values["threshold"])
        result = run_backtest(
            strategy,
            arrays,
            EngineConfig(
                initial_capital=d["capital_quote"], interval="1m", costs=costs
            ),
            close_at_end=False,
            price_only=True,
            continuation=previous.get("continuation") if previous else None,
        )
        account = result.account
        lots = [asdict(account.position)] if account.position.is_open else []
        exposure = account.position.units * arrays["close"][-1]
        realized, fees, slip = (
            account.realized_pnl,
            account.fees_paid,
            account.slippage_paid,
        )
        pending = {str(k): v for k, v in account.pending_targets.items()}
    equity = float(result.equity[-1])
    run_identity = identity(spec, data)
    state = {
        "schema_version": 1,
        "continuation": result.continuation,
        "prior_segment": data.get("prior_segment"),
        "cursor": cursor,
        "last_bar_ts": int(arrays["ts"][-1]),
        "fills": (
            previous["fills"]
            if previous and previous.get("prior_segment") == data.get("prior_segment")
            else []
        )
        + [asdict(t) for t in result.trades],
        "lots": lots,
        "equity_quote": equity,
        "exposure_quote": float(exposure),
        "cash_quote": equity - float(exposure),
        "realized_net_pnl_quote": realized,
        "unrealized_net_pnl_quote": equity - d["capital_quote"] - realized,
        "fees_quote": fees,
        "slippage_quote": slip,
        "carry_paid_quote": 0.0,
        "carry_accrued_quote": 0.0,
        "pending_targets": pending,
        "quote_currency": d["quote_currency"],
        "identity": run_identity,
        "run_hash": fingerprint(run_identity),
    }

    def native(value):
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, dict):
            return {str(k): native(v) for k, v in value.items()}
        if isinstance(value, list):
            return [native(v) for v in value]
        return value

    if research:
        state["research_metrics"] = research_metrics(result, d["capital_quote"])
    import json

    return json.loads(json.dumps(native(state)))


def research_metrics(result, capital):
    """Metrics use the canonical costed equity curve, including open inventory."""
    peak = float(capital)
    drawdown = 0.0
    for value in result.equity:
        value = float(value)
        peak = max(peak, value)
        drawdown = max(drawdown, (peak - value) / peak if peak > 0 else 1.0)
    import statistics

    returns = [
        float(b) / float(a) - 1
        for a, b in zip(result.equity[:-1], result.equity[1:])
        if a > 0
    ]
    uncertainty = (
        statistics.stdev(returns) / len(returns) ** 0.5 if len(returns) > 1 else 0.0
    )
    if hasattr(result, "round_trips"):
        completed = result.round_trips
    elif hasattr(result, "deals_completed"):
        completed = result.deals_completed + result.deals_stopped
    else:
        completed = sum(
            t.side == "close" and t.reason != "final" for t in result.trades
        )
    return {
        "uncertainty": uncertainty,
        "net_return": float(result.equity[-1]) / capital - 1,
        "drawdown": drawdown,
        "turnover": sum(abs(t.notional) for t in result.trades) / capital,
        "trades": completed,
    }

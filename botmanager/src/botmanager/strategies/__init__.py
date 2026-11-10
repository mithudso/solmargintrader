"""One canonical strategy dispatcher for workers, ledger and command surfaces."""

from __future__ import annotations

from ..data import engine_identity
from ..domain import ManagerError, fingerprint
from . import grid
from .base import compatible_engine, evaluate_family, identity, validate_input


def evaluate(
    spec, data, cursor, *, research=False, previous=None, entries_paused=False
):
    if spec.strategy_id == "grid":
        return grid.evaluate(
            spec,
            data,
            cursor,
            research=research,
            previous=previous,
            entries_paused=entries_paused,
        )
    return evaluate_family(
        spec,
        data,
        cursor,
        research=research,
        previous=previous,
        entries_paused=entries_paused,
    )


def validate_registration(spec, data):
    validate_input(spec, data)
    if not compatible_engine(
        data["identity"]["engine_identity"], engine_identity(spec.strategy_id)
    ):
        raise ManagerError(
            "engine_identity_changed",
            "Pinned economic engine differs from loaded code.",
            3,
        )
    if data["bars"]:
        evaluate(spec, data, 1)
    elif data.get("prospective") is None:
        raise ManagerError("input_unavailable", "No completed reference bars.", 3)


def validate_checkpoint(
    spec, data, checkpoint, *, code="corrupt_checkpoint", allow_prior=False
):
    if spec.strategy_id == "grid":
        return grid.validate_checkpoint(
            spec, data, checkpoint, code=code, allow_prior=allow_prior
        )
    try:
        expected = identity(spec, data)
        cursor = checkpoint["cursor"]
        if (
            checkpoint["schema_version"] != 1
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
            or checkpoint["identity"] != expected
            or checkpoint["run_hash"] != fingerprint(expected)
        ):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise ManagerError(
            code, "Checkpoint differs from pinned reference run.", 4
        ) from exc


def rebind_checkpoint(spec, data, checkpoint, *, entries_paused):
    """Prepare a new immutable config identity without resetting economic history.

    The caller must atomically archive the old account and publish this checkpoint
    with the new specification. This pure helper performs no runtime mutation.
    """
    import copy

    from backtester.core.types import CostConfig

    validate_input(spec, data)
    if not entries_paused:
        raise ManagerError(
            "reconciliation_required", "Pause entries before adopting configuration.", 3
        )
    if (
        checkpoint["lots"]
        or checkpoint["exposure_quote"] != 0
        or checkpoint["run_hash"] != fingerprint(checkpoint["identity"])
        or checkpoint["identity"]["bot_id"] != spec.bot_id
        or checkpoint["identity"]["reference"] != data["identity"]
    ):
        raise ManagerError(
            "reconciliation_required",
            "Configuration adoption requires the same flat attributed account.",
            3,
        )
    if not compatible_engine(
        data["identity"]["engine_identity"], engine_identity(spec.strategy_id)
    ):
        raise ManagerError(
            "engine_identity_changed",
            "Loaded economic engine differs from the account identity.",
            3,
        )
    d = data["descriptor"]
    values = spec.resolved_values
    costs = CostConfig(fee_bps=d["fee_bps"], slippage_bps=d["slippage_bps"])
    saved = checkpoint.get("continuation")
    if not isinstance(saved, dict):
        raise ManagerError(
            "continuation_unavailable",
            "Account has no compatible canonical continuation.",
            3,
        )
    try:
        if spec.strategy_id == "grid":
            from backtester.core.gridsim import rebind_grid_state

            continuation = rebind_grid_state(
                saved,
                grid._configuration(spec, data),
                initial_capital=d["capital_quote"],
                interval="1m",
                costs=costs,
                carry_bps_per_hour=d["carry_bps_per_hour"],
            )
            new_identity = grid.run_identity(spec, data)
        elif spec.strategy_id == "dca":
            from backtester.core.dcasim import DcaConfig, rebind_dca_state

            from ..config import DEFAULTS

            cfg = DcaConfig(**{key: values[key] for key in DEFAULTS["dca"]})
            continuation = rebind_dca_state(
                saved,
                cfg,
                initial_capital=d["capital_quote"],
                interval="1m",
                costs=costs,
            )
            new_identity = identity(spec, data)
        else:
            from backtester.core.engine import EngineConfig, rebind_signal_state

            if spec.strategy_id == "trend":
                from soltui.trend import TrendConfig, TrendFollowing

                strategy = TrendFollowing(
                    TrendConfig(
                        **{
                            key: values[key]
                            for key in (
                                "fast_period",
                                "slow_period",
                                "entry_buffer_bps",
                                "capital_usd",
                            )
                        }
                    )
                )
            elif spec.strategy_id == "momentum":
                from backtester.core.strategies.signals import TsMomentum

                strategy = TsMomentum(values["window"], values["threshold"])
            else:
                raise ValueError("strategy configuration adoption is unsupported")
            continuation = rebind_signal_state(
                saved,
                strategy,
                EngineConfig(
                    initial_capital=d["capital_quote"], interval="1m", costs=costs
                ),
            )
            new_identity = identity(spec, data)
    except (ValueError, KeyError, TypeError) as exc:
        raise ManagerError("reconciliation_required", str(exc), 3) from exc
    result = copy.deepcopy(checkpoint)
    result.update(
        continuation=continuation,
        identity=new_identity,
        run_hash=fingerprint(new_identity),
    )
    return result

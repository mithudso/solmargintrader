"""Pure, versioned draft views; configuration is never a runtime observation."""

from __future__ import annotations

from typing import Any

from .domain import BotSpec, plain

STATUS_SCHEMA_VERSION = 1
RUNTIME_UNAVAILABLE = "runtime_not_available"
ACTION_SEMANTICS = {
    "inspect": "Read the saved configuration and available observations.",
    "start": "Request the specified bot's owner to start its worker.",
    "pause_entries": "Hold new entry intents; retain existing orders and positions.",
    "stop": "Stop the specified worker; retain positions, orders, arming and journals.",
    "cancel_orders": "Cancel only the specified bot's scoped venue orders.",
    "close_position": "Close the scoped position through verified execution.",
    "emergency_stop": "Request the engine's kill/disarm policy and report remaining exposure.",
}


def unavailable(reason: str) -> dict[str, Any]:
    return {"value": None, "reason": reason}


def _evidence() -> dict[str, Any]:
    # Each mode gets its own record. Absence never certifies another venue/model.
    return {
        "state": "untested",
        "reason": "evidence_not_available",
        "venue_compatibility_verified": False,
        **{
            key: unavailable("evidence_not_available")
            for key in (
                "dataset_hash",
                "proof_hash",
                "start_at",
                "end_at",
                "engine_version",
                "cost_model_id",
                "result_ref",
            )
        },
    }


def draft_snapshot(spec: BotSpec, *, why: bool = False) -> dict[str, Any]:
    """Normalize an immutable manager draft without clocks, owners or store access.

    `owner` remains the legacy spec-owner alias. It must never be interpreted as
    an actual runtime owner. No runtime exists for a manager draft in this slice.
    """
    snapshot = {
        "schema_version": STATUS_SCHEMA_VERSION,
        **{
            key: getattr(spec, key)
            for key in (
                "bot_id",
                "display_name",
                "source",
                "source_identity",
                "owner",
                "strategy_id",
                "strategy_version",
                "config_revision",
                "config_hash",
                "mode",
            )
        },
        "spec_owner": spec.owner,
        "runtime_id": None,
        "runtime_owner_id": None,
        "owner_generation": None,
        "runtime_reason": RUNTIME_UNAVAILABLE,
        "armed": spec.resolved_values["armed"],
        "lifecycle": "draft",
        "desired_state": "draft",
        "observed_state": "not_running",
        "input_quality": {"state": "missing", "reason": "market_data_not_observed"},
        "owner_reachability": {
            "state": "not_applicable",
            "reason": RUNTIME_UNAVAILABLE,
        },
        "heartbeat_age_seconds": unavailable(RUNTIME_UNAVAILABLE),
        "data_age_seconds": unavailable("market_data_not_observed"),
        "last_completed_evaluation": unavailable("no_completed_evaluation"),
        "latest_decision": unavailable("no_completed_evaluation"),
        "submission_certainty": unavailable("no_submission_observed"),
        "blockers": [RUNTIME_UNAVAILABLE],
        "next_trigger": unavailable(RUNTIME_UNAVAILABLE),
        "reason": RUNTIME_UNAVAILABLE,
        "capabilities": ["inspect"],
        "action_capabilities": {
            operation: {
                "available": operation == "inspect",
                "reason": "draft_inspection_available"
                if operation == "inspect"
                else RUNTIME_UNAVAILABLE,
                "semantics": semantics,
            }
            for operation, semantics in ACTION_SEMANTICS.items()
        },
        "financials": {
            key: unavailable(reason)
            for key, reason in (
                ("exposure_usd", "exposure_not_observed"),
                ("allocated_capital_usd", "allocation_not_observed"),
                ("realized_net_pnl_usd", "results_not_measured"),
                ("unrealized_net_pnl_usd", "results_not_measured"),
                ("costs_usd", "costs_not_measured"),
            )
        },
        "configured_virtual_capital": {
            "value": spec.resolved_values["capital_usd"],
            "currency": "USD",
            "reason": "configured_virtual_capital_only",
            "reserved": False,
        },
        "evidence_identity": {
            key: getattr(spec, key)
            for key in (
                "strategy_id",
                "strategy_version",
                "config_revision",
                "config_hash",
                "venue",
                "base_mint",
                "quote_mint",
                "bar_seconds",
                "execution_model",
            )
        },
        "evidence": {mode: _evidence() for mode in ("backtest", "paper", "live")},
        "manual_pins": {
            "config_revision": spec.config_revision,
            "config_hash": spec.config_hash,
            "values": plain(spec.user_overrides),
            "provenance": {
                key: plain(spec.provenance[key]) for key in spec.user_overrides
            },
        },
        "tuning": {
            "proposals": {
                "available": False,
                "read_only": True,
                "reason": "proposal_source_not_available",
            },
            "adoption": {
                "available": False,
                "reason": "versioned_adoption_not_available",
            },
            "automatic_edits": False,
        },
    }
    if why:
        snapshot["explanation"] = {
            "reason": RUNTIME_UNAVAILABLE,
            "summary": "This saved draft has no runtime, observations or measured results.",
            "remedy": "Inspect the pinned configuration; manager runtime controls are unavailable.",
        }
    return snapshot

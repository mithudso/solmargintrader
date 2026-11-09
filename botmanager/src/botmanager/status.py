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


def legacy_snapshot(
    installation: Any, observation: dict[str, Any], *, controls: bool
) -> dict[str, Any]:
    """Normalize allowlisted owner observations; reachability is not heartbeat."""
    from uuid import NAMESPACE_URL, uuid5

    family = observation["bot"]
    council = family == "council"
    guarded = controls and not council
    owner_id = installation.installation_id
    bot_id = str(uuid5(NAMESPACE_URL, owner_id + ":" + family))
    observed = (
        ("running" if observation["running"] else "not_running")
        if council
        else "unknown"
    )
    reason = "owner_lock_observed" if council else "owner_has_no_worker_heartbeat"
    actions = {
        operation: {
            "available": operation == "inspect"
            or (guarded and operation in ("start", "stop")),
            "reason": "owner_inspection_available"
            if operation == "inspect"
            else "guarded_delegation_available"
            if guarded and operation in ("start", "stop")
            else "capability_unavailable",
            "semantics": semantics,
        }
        for operation, semantics in ACTION_SEMANTICS.items()
    }
    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "bot_id": bot_id,
        "external_id": owner_id + ":" + family,
        "display_name": owner_id + ":" + family,
        "source": "soltui",
        "source_identity": owner_id + ":" + family,
        "owner": owner_id,
        "spec_owner": None,
        "spec_owner_reason": "externally_owned",
        "strategy_id": family,
        "strategy_version": None,
        "strategy_version_reason": "owner_does_not_version_strategies",
        "config_revision": None,
        "config_revision_unavailable_reason": "owner_does_not_version_configurations",
        "config_hash": observation["config_hash"],
        "config_hash_scope": "saved_effective_configuration",
        "active_config_hash": observation.get("session_config_hash"),
        "active_config_hash_reason": "owner_does_not_report_active_configuration"
        if observation.get("session_config_hash") is None
        else None,
        "config_path": str(
            installation.config_root
            / ("council/config.json" if council else "bots/config.json")
        ),
        "source_hash": observation.get("source_hash"),
        "source_hash_reason": "owner_does_not_report_loaded_identity"
        if observation.get("source_hash") is None
        else None,
        "runtime_id": observation["session_id"],
        "runtime_id_reason": "owner_session_unavailable"
        if council
        else "empty_family_slot"
        if observation["session_id"] is None
        else None,
        "runtime_owner_id": owner_id,
        "owner_generation": None,
        "runtime_reason": "owner_does_not_support_generation_fencing",
        "mode": "paper",
        "armed": False,
        "lifecycle": "observed" if council else "unknown",
        "desired_state": observation["requested_state"],
        "observed_state": observed,
        "asset": observation["asset"],
        "instance_scope": "one_instance_per_family",
        "venue": observation["venue"],
        "venue_reason": "owner_does_not_report_execution_context"
        if observation["venue"] is None
        else None,
        "bar_seconds": observation["bar_seconds"],
        "bar_seconds_reason": "event_driven_recorded_quotes"
        if family == "triangle" and observation["execution_model"] == "recorded_bid_ask"
        else "owner_does_not_report_execution_context"
        if observation["bar_seconds"] is None
        else None,
        "execution_model": observation["execution_model"],
        "execution_model_reason": "owner_does_not_report_execution_context"
        if observation["execution_model"] is None
        else None,
        "data_sources": {
            "reference_price": {
                "value": observation.get("reference_price_source"),
                "reason": "reported_reference_only"
                if observation.get("reference_price_source") is not None
                else "reference_price_source_not_observed",
            },
            "simulation_fills": {
                "value": "coinbase_next_minute_open_ohlc_proxy"
                if council and observation["execution_model"] is not None
                else observation["execution_model"],
                "reason": "simulation_model_only"
                if observation["execution_model"] is not None
                else "fill_source_not_observed",
            },
            "signal_inputs": unavailable("signal_inputs_not_observed"),
        },
        "input_quality": {"state": "unknown", "reason": "market_data_not_observed"},
        "owner_reachability": {"state": "reachable", "reason": "verified_soltui_api"},
        "heartbeat_age_seconds": unavailable("owner_has_no_worker_heartbeat"),
        "data_age_seconds": unavailable("market_data_not_observed"),
        "last_completed_evaluation": unavailable("evaluation_not_observed"),
        "latest_decision": unavailable("decision_not_observed"),
        "submission_certainty": unavailable("no_submission_observed"),
        "next_trigger": unavailable("owner_does_not_report_next_trigger"),
        "reason": reason,
        "blockers": [reason] if not council else [],
        "capabilities": [
            operation for operation, value in actions.items() if value["available"]
        ],
        "action_capabilities": actions,
        "expected_session": observation["session_id"],
        "expected_session_reason": "empty_family_slot"
        if observation["session_id"] is None and not council
        else "owner_session_unavailable"
        if council
        else None,
        "financials": {
            key: unavailable(why)
            for key, why in (
                ("exposure_usd", "exposure_not_observed"),
                ("allocated_capital_usd", "allocation_not_observed"),
                ("realized_net_pnl_usd", "results_not_measured"),
                ("unrealized_net_pnl_usd", "results_not_measured"),
                ("costs_usd", "costs_not_measured"),
            )
        },
        "configured_virtual_capital": unavailable(
            "owner_configured_capital_not_imported"
        ),
        "evidence_identity": {
            "strategy_id": family,
            "strategy_version": None,
            "config_revision": None,
            "config_hash": observation.get("session_config_hash"),
            "config_hash_reason": "owner_does_not_report_active_configuration"
            if observation.get("session_config_hash") is None
            else None,
            "venue": observation["venue"],
            "base_mint": None,
            "quote_mint": None,
            "bar_seconds": observation["bar_seconds"],
            "execution_model": observation["execution_model"],
            "unavailable_reason": "legacy_semantics_not_certified",
        },
        "evidence": {mode: _evidence() for mode in ("backtest", "paper", "live")},
        "manual_pins": unavailable("external_configuration_not_imported"),
        "tuning": {
            "proposals": {
                "available": False,
                "read_only": True,
                "reason": "proposal_source_not_available",
            },
            "adoption": {
                "available": False,
                "reason": "external_config_writes_forbidden",
            },
            "automatic_edits": False,
        },
    }

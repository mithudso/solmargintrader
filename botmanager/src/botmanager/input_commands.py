"""Versioned reference preparation and data diagnosis behind the command registry."""

from __future__ import annotations

import json
import time
from pathlib import Path

from .data import load_recording
from .domain import ManagerError, canonical
from .oracle_data import KNOWN_ARCHIVE, prepare_descriptor, read_page


def read_document(path, limit=65536):
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ValueError
        return json.loads(raw)
    except (ValueError, TypeError, OSError) as exc:
        raise ManagerError(
            "input_unavailable", "Input document is missing or invalid.", 3
        ) from exc


def prepare(spec, params, changes):
    if params.get("reference") is not True:
        raise ManagerError(
            "reference_consent_required",
            "Explicit reference consent is required for Coinbase USD versus Jupiter USDC.",
            3,
        )
    path = (
        KNOWN_ARCHIVE
        if params["archive"] == "shared-sol-usd"
        else Path(params["archive"])
    )
    descriptor = prepare_descriptor(
        path,
        capital_quote=spec.resolved_values["capital_usd"],
        strategy_id=spec.strategy_id,
        mode=params.get("mode", "prospective"),
        start_ts=params.get("start_ts"),
        end_ts=params.get("end_ts"),
    )
    allowed = {
        "fee_bps",
        "slippage_bps",
        "carry_bps_per_hour",
        "min_order_quote",
        "max_bars",
        "max_sample_gap_s",
        "max_quote_age_s",
        "max_source_age_s",
    }
    if not set(changes) <= allowed:
        raise ManagerError(
            "invalid_input", "Only documented cost and coverage assumptions may change."
        )
    descriptor.update(changes)
    if changes:
        descriptor["cost_provenance"] = (
            "explicit_user_reference_assumptions_not_observed_jupiter_fees"
        )
    data = load_recording(descriptor, strategy_id=spec.strategy_id)
    from .strategies import validate_registration

    validate_registration(spec, data)
    output = Path(params["output"]).expanduser().absolute()
    try:
        # A descriptor is an immutable selection: never overwrite an old activation.
        with output.open("x") as stream:
            stream.write(canonical(descriptor) + "\n")
    except FileExistsError as exc:
        raise ManagerError(
            "identity_conflict", "Descriptor output already exists; select a new path."
        ) from exc
    return {
        "schema_version": 1,
        "descriptor_path": str(output),
        "descriptor": descriptor,
        "starts_worker": False,
        "register_command": [
            "solbot",
            "register-input",
            spec.bot_id,
            "--descriptor",
            str(output),
        ],
        "reference_only": True,
        "live_eligible": False,
    }


def check(spec, *, descriptor_path=None, runtime=None):
    try:
        if descriptor_path:
            data = load_recording(
                read_document(descriptor_path), strategy_id=spec.strategy_id
            )
        elif runtime:
            data = runtime["input"]
        else:
            raise ManagerError(
                "input_unavailable",
                "Register or select explicit input before checking data.",
                3,
            )
        from .strategies import validate_registration

        validate_registration(spec, data)
        d = data["descriptor"]
        source = None
        if d["source"] == "oracle_archive":
            page = read_page(d["archive_path"], limit=1)
            if page["policy_hash"] != d["policy_hash"]:
                raise ManagerError(
                    "source_mismatch", "Selected source policy has changed.", 3
                )
            source = {
                k: page[k]
                for k in (
                    "high_watermark",
                    "latest_observed",
                    "latest_received",
                    "read_at",
                )
            }
            source["state"] = (
                "available"
                if page["latest_observed"] is not None
                and 0 <= time.time() - page["latest_observed"] <= d["max_source_age_s"]
                else "source_stale"
            )
        return {
            "schema_version": 1,
            "bot_id": spec.bot_id,
            "state": "reference_only",
            "compatible": True,
            "required_source": d["source"],
            "source": source,
            "actual_bars": len(data["bars"]),
            "start_ts": data["bars"][0]["ts"] if data["bars"] else None,
            "end_ts": data["bars"][-1]["ts"] + 60 if data["bars"] else None,
            "model": data["identity"]["execution_model"],
            "strategy": spec.strategy_id,
            "mode": d.get("mode", "historical"),
            "warmup_bars": spec.resolved_values.get(
                "slow_period", spec.resolved_values.get("window", 0)
            ),
            "costs": data["identity"]["costs"],
            "cost_kind": "explicit_assumptions",
            "volume": None,
            "missing_fields": [
                "actual_jupiter_routes",
                "actual_execution_fees",
                "fills",
                "volume",
            ],
            "target": {
                "venue": spec.venue,
                "base_mint": spec.base_mint,
                "quote_mint": spec.quote_mint,
            },
            "reference_units": d["quote_currency"],
            "live_eligible": False,
            "venue_compatibility_verified": False,
        }
    except ManagerError as exc:
        return {
            "schema_version": 1,
            "bot_id": spec.bot_id,
            "state": "incomplete",
            "compatible": False,
            "reason": exc.code,
            "live_eligible": False,
        }

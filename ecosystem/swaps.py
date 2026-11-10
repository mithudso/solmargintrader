"""Public manual-swap settings and explicit, provider-independent paper costs.

This module reads no credentials, wallets, owner stores or execution interfaces.
An assumed paper fee is never evidence of a live Jupiter route's actual costs.
"""

from __future__ import annotations

import math
import re

from oracle.feeds import SOL_MINT, USDC_MINT

ULTRA_REFERRAL_ACCOUNT = "9chjbn8wvLUbGCrWF3nYRF4xnhixnGHh5xrhvpQwrrQ9"
SWAP_TRIGGER_REFERRAL_ACCOUNT = "85vN9xt5wwXk3M4ikQ9amWs38QfFLu6kjqaz22wX9NsD"
DEFAULT_REFERRAL_FEE_BPS = 10
MINIMUM_REFERRAL_FEE_BPS = 50
MAXIMUM_REFERRAL_FEE_BPS = 255
PLUGIN_SRC = "https://plugin.jup.ag/plugin-v1.js"
ASSET = re.compile(r"[A-Z][A-Z0-9]{0,19}\Z")


def config(asset: str = "SOL") -> dict:
    """Return public settings; an installed interface is not execution readiness."""
    if not isinstance(asset, str) or not ASSET.fullmatch(asset.upper()):
        raise ValueError("invalid_swap_asset")
    asset = asset.upper()
    mints = {"SOL": SOL_MINT, "USDC": USDC_MINT}
    known = asset in mints
    return {
        "schema_version": 1,
        "status": "available",
        "provider": "jupiter",
        "mode": "manual_browser_wallet",
        "asset": asset,
        "asset_mapping_status": "available" if known else "unavailable",
        "asset_mapping_reason": None if known else "asset_mint_mapping_unverified",
        "initial_input_mint": mints.get(asset),
        "initial_output_mint": SOL_MINT if asset == "USDC" else USDC_MINT,
        "verified_default_assets": list(mints),
        "selected_referral_account": ULTRA_REFERRAL_ACCOUNT,
        "referral_accounts": {
            "ultra": ULTRA_REFERRAL_ACCOUNT,
            "swap_trigger": SWAP_TRIGGER_REFERRAL_ACCOUNT,
        },
        "referral_account_source": "Owner-recorded public account; KNOW-1062. Official Plugin FAQ links referral setup to Ultra.",
        "default_referral_fee_bps": DEFAULT_REFERRAL_FEE_BPS,
        "minimum_referral_fee_bps": MINIMUM_REFERRAL_FEE_BPS,
        "maximum_referral_fee_bps": MAXIMUM_REFERRAL_FEE_BPS,
        "default_fee_supported": False,
        "integration_status": "unavailable",
        "integration_reason": "configured_10bps_below_published_50bps_minimum",
        "fee_change_requires_user_action": True,
        "plugin_src": PLUGIN_SRC,
        "auto_connect": False,
        "wallet_passthrough": False,
        "live_ready": False,
        "server_can_sign_or_submit": False,
        "referral_accounts_verified_on_chain": False,
        "actual_quote_fees": None,
        "fee_components": {
            "configured_referral_bps": DEFAULT_REFERRAL_FEE_BPS,
            "provider_or_route_fee": "unknown_until_quote",
            "network_and_priority_fees": "unknown_until_quote_and_wallet",
            "token_account_rent": "unknown_until_quote_and_wallet",
            "slippage_and_price_impact": "unknown_until_quote",
        },
        "documentation_checked_on": "2026-11-10",
        "documentation": [
            "https://developers.jup.ag/docs/tool-kits/plugin",
            "https://developers.jup.ag/docs/tool-kits/plugin/faq",
            "https://developers.jup.ag/docs/swap/order-and-execute#referral-fees",
        ],
        "limitations": [
            "Reference-price provider selection does not verify a Jupiter swap quote.",
            "The configured 0.1% referral fee remains unchanged. No automatic increase is permitted.",
            "Actual referral eligibility and charged fee require provider quote evidence.",
            "Review every displayed fee and wallet transaction before explicit approval.",
            "CDN, wallet connection and funded trade readiness are not established by this configuration.",
        ],
    }


def validate_cost_model(value: dict) -> dict:
    """Normalize explicit per-side assumptions; validate again without doubling fees.

    ``fee_bps`` is the assumed base venue fee. ``total_fee_bps`` is the base plus
    the separately configured referral assumption, for the existing paper engine.
    Network, priority, rent and changing route costs remain outside this model.
    """
    required = {
        "source",
        "fee_bps",
        "slippage_bps",
        "borrow_long_bps_hour",
        "borrow_short_bps_hour",
    }
    allowed = required | {"referral_fee_bps", "total_fee_bps"}
    if (
        not isinstance(value, dict)
        or not required <= set(value)
        or set(value) - allowed
        or value.get("source") != "configured_scenario"
    ):
        raise ValueError("invalid_cost_model")
    result = {"source": "configured_scenario"}
    for name in sorted(allowed - {"source", "total_fee_bps"}):
        number = value.get(
            name, DEFAULT_REFERRAL_FEE_BPS if name == "referral_fee_bps" else None
        )
        if (
            type(number) not in (int, float)
            or not 0 <= number < 10000
            or not math.isfinite(number)
        ):
            raise ValueError("invalid_cost_model")
        result[name] = float(number)
    total = result["fee_bps"] + result["referral_fee_bps"]
    if total >= 10000:
        raise ValueError("invalid_cost_model")
    supplied_total = value.get("total_fee_bps")
    if "total_fee_bps" in value and (
        type(supplied_total) not in (int, float)
        or supplied_total != total
        or not math.isfinite(supplied_total)
    ):
        raise ValueError("invalid_cost_model")
    return {**result, "total_fee_bps": total}

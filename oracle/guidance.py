"""Read-only guide routing and conservative lifecycle/readiness summaries."""

from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
STAGES = ("backtest", "forward", "live")
GUIDES = {
    "backtest": (
        ("repository", "backtester/README.md"),
        ("repository", "docs/backtester-history-handoff.md"),
        (
            "skill",
            "trading-and-investing/references/signal-backtest-protocol-and-regime-evidence.md",
        ),
    ),
    "forward": (
        ("repository", "docs/COMPOUND-5M.md"),
        ("repository", "soltui/README.md"),
        ("skill", "trading-and-investing/references/crypto-bot-monitor-operations.md"),
        ("concept", "five-minute-sol-perps-task808-suite.family/llms.txt"),
    ),
    "live": (
        ("repository", "botmanager/README.md"),
        ("repository", "executor/README.md"),
        ("repository", "docs/OPERATIONS.md"),
        ("skill", "trading-and-investing/references/crypto-bot-monitor-evidence.md"),
    ),
}


def guidance(
    stage: str = "backtest", *, repo: Path | None = None, home: Path | None = None
) -> dict:
    if stage not in STAGES:
        raise ValueError("invalid lifecycle stage")
    home = home or Path.home()
    repo = repo or (REPO if (REPO / "CLAUDE.md").is_file() else None)
    roots = {
        "repository": repo,
        "skill": home / ".agents/skills",
        "concept": home / ".global-ai-hub/llms-concepts",
    }
    routes = []
    for origin, relative in GUIDES[stage]:
        root = roots[origin]
        path = root / relative if root is not None else None
        entry: dict[str, Any] = {
            "origin": origin,
            "path": str(path) if path else None,
            "relative_path": relative,
            "available": False,
            "sha256": None,
            "trust": "reference_content_only",
        }
        try:
            # Hash reference bytes only; their content never becomes executable policy.
            if path is not None and path.is_file() and path.stat().st_size <= 2_000_000:
                entry.update(
                    available=True, sha256=hashlib.sha256(path.read_bytes()).hexdigest()
                )
        except OSError:
            pass
        routes.append(entry)
    requirements = {
        "backtest": [
            "coin_and_strategy_version_bound_score",
            "dataset_and_cost_model_provenance",
            "out_of_sample_validation",
        ],
        "forward": [
            "approved_backtest_evidence",
            "prospective_paper_outcomes",
            "configured_sample_and_drawdown_policy",
            "no_real_money",
        ],
        "live": [
            "approved_forward_evidence",
            "independent_execution_verifier",
            "venue_credentials_verified",
            "risk_rails_and_reconciliation",
            "explicit_live_arming",
        ],
    }
    return {
        "stage": stage,
        "guides": routes,
        "requirements": requirements[stage],
        "automatic_promotion": False,
        "guides_prove_readiness": False,
        "next_stage": {"backtest": "forward", "forward": "live", "live": None}[stage],
    }


def manager_inventory(manager_home: Path | None = None) -> dict:
    """Use the manager's own read-only status interface if explicitly connected."""
    if manager_home is None:
        return {"status": "unavailable", "reason": "manager_not_connected", "bots": []}
    try:
        from botmanager.registry import CommandContext, dispatch

        response = dispatch("status", {}, CommandContext(home=manager_home))
        if not response.get("ok"):
            raise ValueError
        rows = response["data"]["bots"]
        allowed = (
            "bot_id",
            "strategy_id",
            "strategy_version",
            "lifecycle",
            "mode",
            "observed_state",
            "blockers",
            "evidence",
            "evidence_identity",
        )
        return {
            "status": "available",
            "owner": "botmanager",
            "bots": [
                {key: row[key] for key in allowed if key in row} for row in rows[:100]
            ],
            "truncated": len(rows) > 100,
        }
    except (ImportError, OSError, KeyError, TypeError, ValueError):
        return {
            "status": "unavailable",
            "reason": "manager_status_unavailable",
            "bots": [],
        }


def readiness(engine: Any, *, manager_home: Path | None = None) -> dict:
    market = engine.market()
    return {
        "live_ready": False,
        "order_capability": False,
        "market_available": market.get("status") == "available",
        "credentials": {
            "jupiter_api_key_configured": bool(os.environ.get("JUPITER_API_KEY")),
            "jupiter_api_key_verified": False,
            "signer_loaded": False,
        },
        "subscriptions": {
            "transport": "stdio",
            "authority": "local_process_owner",
            "network_authentication": "not_applicable",
        },
        "blockers": [
            "execution_verifier_not_integrated",
            "live_arming_not_owned_by_oracle",
            "forward_promotion_evidence_not_verified",
        ],
        "manager": manager_inventory(manager_home),
    }


def veto(engine: Any, *, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    market = engine.market(now=now)
    predictions = engine.predictions(now=now)
    signal = predictions.get("signal", predictions.get("aggregate", {}).get("signal"))
    available = (
        market.get("status") == "available" and predictions.get("status") == "available"
    )
    reason = (
        "prediction_or_market_unavailable"
        if not available
        else "live_readiness_not_verified"
    )
    return {
        "decision": "veto",
        "reason": reason,
        "signal": signal,
        "issued_at": now,
        "expires_at": now + 15,
        "enforcement": False,
        "scope": "advisory_new_entries",
        "order_capability": False,
        "remedy": "Executor must independently verify readiness and consume this decision before submitting.",
    }

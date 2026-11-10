"""Pure prospective-vote aggregation; inputs are not proof of their provenance."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Vote:
    strategy_id: str
    direction: int
    hits: int
    resolved: int
    issued_at: float
    expires_at: float


def aggregate(votes: list[Vote], *, now: float, minimum_resolved: int) -> dict:
    """Aggregate a single instrument and horizon from caller-verified evidence.

    A flat vote contributes to the denominator. Agreement is a signed weighted
    balance, not a probability. The caller must bind evidence to instrument,
    horizon and strategy version before invoking this pure function.
    """
    if (
        not isinstance(now, (float, int))
        or isinstance(now, bool)
        or not math.isfinite(now)
    ):
        raise ValueError("invalid clock")
    if type(minimum_resolved) is not int or minimum_resolved < 1:
        raise ValueError("minimum_resolved must be positive")
    if len(votes) > 14:
        raise ValueError("at most 14 strategy votes")
    seen: set[str] = set()
    included, excluded = [], []
    for vote in votes:
        if (
            not isinstance(vote, Vote)
            or not isinstance(vote.strategy_id, str)
            or not vote.strategy_id.strip()
        ):
            raise ValueError("invalid strategy identity")
        if vote.strategy_id in seen:
            raise ValueError("duplicate strategy identity")
        seen.add(vote.strategy_id)
        if type(vote.direction) is not int or vote.direction not in (-1, 0, 1):
            raise ValueError("invalid direction")
        if (
            type(vote.hits) is not int
            or type(vote.resolved) is not int
            or not 0 <= vote.hits <= vote.resolved
        ):
            raise ValueError("invalid evidence counts")
        if (
            any(
                isinstance(t, bool)
                or not isinstance(t, (float, int))
                or not math.isfinite(t)
                for t in (vote.issued_at, vote.expires_at)
            )
            or vote.expires_at <= vote.issued_at
        ):
            raise ValueError("invalid forecast timestamps")
        reason = None
        if vote.issued_at > now or vote.expires_at <= now:
            reason = "forecast_not_current"
        elif vote.resolved < minimum_resolved:
            reason = "insufficient_evidence"
        elif vote.hits / vote.resolved < 0.60:
            reason = "accuracy_below_threshold"
        if reason:
            excluded.append({"strategy_id": vote.strategy_id, "reason": reason})
            continue
        accuracy = vote.hits / vote.resolved
        weight = accuracy * (2 if vote.hits > 100 else 1)
        included.append(
            {
                "strategy_id": vote.strategy_id,
                "direction": vote.direction,
                "hits": vote.hits,
                "resolved": vote.resolved,
                "weight": weight,
            }
        )
    total = sum(v["weight"] for v in included)
    if not total:
        return {
            "status": "unavailable",
            "signal": None,
            "balance_percent": None,
            "included": included,
            "excluded": excluded,
        }
    balance = sum(v["direction"] * v["weight"] for v in included) / total
    signal = (
        "Strong Buy"
        if balance >= 0.6
        else "Buy"
        if balance >= 0.2
        else "Strong Sell"
        if balance <= -0.6
        else "Sell"
        if balance <= -0.2
        else "Flat"
    )
    return {
        "status": "available",
        "signal": signal,
        "balance_percent": balance * 100,
        "included": included,
        "excluded": excluded,
    }

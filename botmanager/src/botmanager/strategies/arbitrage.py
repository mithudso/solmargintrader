"""Conditional directed Solana quote-cycle diagnosis, never an order executor."""

from __future__ import annotations

import math

from ..domain import ManagerError, fingerprint


def diagnose_cycle(
    observations, assumptions, *, now, failed_leg, unwind=None, max_skew_s=1.0
):
    """Chain exact raw amounts at conservative minimum outputs; costs use start units.

    Costs are explicit model inputs, not observed fees. A quoted positive cycle
    never books profit. A failed leg needs an exact-size observed unwind quote.
    """
    from oracle.quotes import QuoteError, validate_observation

    try:
        if not isinstance(observations, list) or not 2 <= len(observations) <= 4:
            raise ValueError
        if (
            type(now) not in (int, float)
            or not math.isfinite(now)
            or type(max_skew_s) not in (int, float)
            or not 0 < max_skew_s <= 1
        ):
            raise ValueError
        quotes = [validate_observation(q) for q in observations]
        if failed_leg is not None and (
            type(failed_leg) is not int or not 0 <= failed_leg < len(quotes)
        ):
            raise ValueError
        start = quotes[0]["request"]["inputMint"]
        amount = quotes[0]["request"]["amount"]
        current_mint = start
        current = amount
        for q in quotes:
            if (
                q["request"]["inputMint"] != current_mint
                or q["request"]["amount"] != current
            ):
                raise ManagerError(
                    "quote_size_mismatch",
                    "Directed quotes do not chain at exact minimum-output sizes.",
                    3,
                )
            current_mint = q["request"]["outputMint"]
            current = int(q["response"]["otherAmountThreshold"])
        if current_mint != start:
            raise ValueError
        all_quotes = (
            quotes + [validate_observation(unwind)] if unwind is not None else quotes
        )
        if any(q["price_impact"]["state"] != "observed" for q in all_quotes):
            raise ManagerError(
                "incomplete_route_evidence",
                "Cycle diagnosis requires observed price-impact evidence for each quote.",
                3,
            )
        clocks = [q["received_at"] for q in all_quotes]
        if max(clocks) - min(clocks) > max_skew_s or any(
            not q["received_at"] <= now < q["expires_at"] for q in all_quotes
        ):
            raise ManagerError(
                "quote_time_mismatch",
                "Quote clocks are future, stale or not aligned.",
                3,
            )
        costs = {}
        for q in all_quotes:
            c = assumptions[q["observation_id"]]
            keys = {
                "network_fee_start_raw",
                "priority_fee_start_raw",
                "rent_start_raw",
                "failed_transaction_start_raw",
                "cost_currency_mint",
                "route_platform_fees_in_output",
                "fill_policy",
            }
            if (
                set(c) != keys
                or c["cost_currency_mint"] != start
                or c["route_platform_fees_in_output"] is not True
                or c["fill_policy"] != "minimum_output"
            ):
                raise ValueError
            if any(
                type(c[k]) is not int or c[k] < 0 for k in keys if k.endswith("_raw")
            ):
                raise ValueError
            costs[q["observation_id"]] = c

        def fee(q):
            c = costs[q["observation_id"]]
            return (
                c["network_fee_start_raw"]
                + c["priority_fee_start_raw"]
                + c["rent_start_raw"]
            )

        quoted_net = current - amount - sum(fee(q) for q in quotes)
        if failed_leg is None:
            if unwind is not None:
                raise ValueError
            net = quoted_net
        else:
            held_mint = (
                start
                if failed_leg == 0
                else quotes[failed_leg - 1]["request"]["outputMint"]
            )
            held = (
                amount
                if failed_leg == 0
                else int(quotes[failed_leg - 1]["response"]["otherAmountThreshold"])
            )
            spent = (
                sum(fee(q) for q in quotes[:failed_leg])
                + costs[quotes[failed_leg]["observation_id"]][
                    "failed_transaction_start_raw"
                ]
            )
            if held_mint != start:
                if unwind is None or unwind["request"] != {
                    **unwind["request"],
                    "inputMint": held_mint,
                    "outputMint": start,
                    "amount": held,
                }:
                    raise ManagerError(
                        "unwind_evidence_missing",
                        "A failed cycle requires a time-aligned exact-size unwind quote.",
                        3,
                    )
                held = int(unwind["response"]["otherAmountThreshold"])
                spent += fee(unwind)
            elif unwind is not None:
                raise ValueError
            net = held - amount - spent
        return {
            "schema_version": 1,
            "state": "conditional_paper_model",
            "source": "jupiter_swap_v1",
            "start_mint": start,
            "start_amount_raw": amount,
            "quoted_minimum_cycle_net_start_raw": quoted_net,
            "pessimistic_paper_net_start_raw": net,
            "booked_profit_start_raw": None,
            "failed_leg": failed_leg,
            "observations": [q["observation_id"] for q in all_quotes],
            "cost_assumptions": costs,
            "assumptions_hash": fingerprint(costs),
            "certified": False,
            "live_supported": False,
            "reasons": [
                "quote_not_execution",
                "costs_are_explicit_assumptions",
                "atomic_construction_and_verifier_unavailable",
            ],
        }
    except ManagerError:
        raise
    except (ValueError, TypeError, KeyError, QuoteError) as exc:
        raise ManagerError(
            "incomplete_route_evidence",
            "Exact directed routes, amounts, clocks and complete explicit costs are required.",
            3,
        ) from exc

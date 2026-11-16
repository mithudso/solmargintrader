"""Causal fixed-grid paper exit replay; inputs must be natively archived.

200 ms is observed sampling, not a guarantee of keeper-path completeness.
No OHLC price interpolation, signing, order placement, or fill assertion occurs.
"""

from __future__ import annotations

from oracle_leverage.exit50 import start_position, step_position

GRID_US = 200_000
MARGIN = 10_000_000
NOTIONAL = 1000 * MARGIN
HOLD_US = 15_000_000
POLICIES = ("fixed", "second_turn", "target", "target_momentum")


def replay(decision_us, cap_us, samples, minute_signals, policy, delay_seconds=10):
    """Replay one 10m SHORT; require a complete fresh grid through terminal.

    `samples` are (publish_us, integer price). `minute_signals` maps completed
    minute timestamps to booleans `momentum_exit` and `second_turn_exit`. The
    earliest target/exit intent is latched before the 15s hold elapses. The
    synthetic close fills on its deadline unless a prior/current sample touches
    the adverse boundary. This is an oracle-price counterfactual, not a fill.
    """
    if policy not in POLICIES or delay_seconds not in (0, 5, 10):
        raise ValueError("invalid frozen policy or delay")
    if (
        type(decision_us) is not int
        or type(cap_us) is not int
        or decision_us % GRID_US
        or cap_us % GRID_US
        or cap_us <= decision_us
    ):
        raise ValueError("invalid decision or cap timestamp")
    first = decision_us + GRID_US
    if not samples or len(samples[0]) != 2 or samples[0][0] != first:
        return {"status": "unscored", "reason": "missing_entry_sample"}
    try:
        state = start_position(first, samples[0][1], cap_us, policy, delay_seconds)
        for at, price in samples:
            state = step_position(state, at, price, minute_signals.get(at))
            if state["status"] != "open":
                return state
    except (ValueError, TypeError):
        return {"status": "unscored", "reason": "incomplete_or_invalid_grid"}
    return {"status": "unscored", "reason": "deadline_not_covered"}


def sparse_replay(
    decision_us,
    cap_us,
    entry_price,
    minute_bars,
    minute_signals,
    get_minute,
    policy,
    delay_seconds=10,
):
    """Replay with proven-safe OHLC minutes and exact grid for ambiguous minutes.

    minute_bars maps minute epoch seconds to original oracle OHLC arrays.
    get_minute(minute_s) returns the complete 300-point grid [(us, price_int)].
    Missing/invalid samples never imply a result. The caller is responsible for
    binding each OHLC bar and fetched sample body to its source receipt.
    """
    from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
    from math import inf, nextafter

    from oracle_leverage.exit50 import advance_proven

    entry_us = decision_us + GRID_US
    state = start_position(entry_us, entry_price, cap_us, policy, delay_seconds)
    state = step_position(state, entry_us, entry_price, minute_signals.get(entry_us))
    skipped = fetched = 0
    while state["status"] == "open":
        next_us = state["last_us"] + GRID_US
        minute_s = next_us // 60_000_000 * 60
        bar = minute_bars.get(minute_s)
        if bar is None:
            return {
                "status": "unscored",
                "reason": "missing_minute_bar",
                "at_us": next_us,
            }
        end_us = (minute_s + 60) * 1_000_000 - GRID_US
        low = int(
            (
                Decimal.from_float(nextafter(float(bar[3]), -inf)) * 10**12
            ).to_integral_value(rounding=ROUND_FLOOR)
        )
        high = int(
            (
                Decimal.from_float(nextafter(float(bar[2]), inf)) * 10**12
            ).to_integral_value(rounding=ROUND_CEILING)
        )
        flag_at_boundary = minute_signals.get(next_us, {})
        need_boundary = (
            policy == "target_momentum" and flag_at_boundary.get("momentum_exit", False)
        ) or (
            policy == "second_turn" and flag_at_boundary.get("second_turn_exit", False)
        )
        try:
            if need_boundary:
                raise ValueError("indicator_at_boundary")
            state = advance_proven(state, end_us, low, high)
            skipped += 1
            continue
        except ValueError:
            pass
        points = get_minute(minute_s)
        if points is None:
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": next_us,
            }
        fetched += 1
        try:
            for at, price in points:
                if at < next_us:
                    continue
                state = step_position(state, at, price, minute_signals.get(at))
                if state["status"] != "open":
                    state["proof_skipped_minutes"] = skipped
                    state["proof_fetched_minutes"] = fetched
                    return state
        except (ValueError, TypeError):
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": state["last_us"] + GRID_US,
            }
        if state["last_us"] != end_us:
            return {
                "status": "unscored",
                "reason": "incomplete_or_invalid_grid",
                "at_us": state["last_us"] + GRID_US,
            }

    return state


def fit_family_model(prepared, signals, asset, family):
    """Fit family-conditional bar-3 direction only on chronological training."""
    from research.reversal_shapes import boundaries, color

    train_start, train_end, _, _ = boundaries()
    ten, _, _ = prepared["frames"]["10"]
    by_start = {bar[0]: bar for bar in ten}
    contexts = {str(m): {} for m in (5, 10, 15, 20)}
    n = down = 0
    for signal in signals:
        if not signal["eligible"] or signal["family"] != family:
            continue
        target_start = signal["decision_s"] + (60 if family == "near_end" else 0)
        target = by_start.get(target_start)
        if (
            target is None
            or not train_start <= target_start
            or target_start + 600 > train_end
        ):
            continue
        frames = signal["context"]["frames"]
        if any(frames[str(m)]["shape"] == "unknown" for m in (5, 10, 15, 20)):
            continue
        outcome = color(target) == "DOWN"
        n += 1
        down += outcome
        for m in (5, 10, 15, 20):
            cells = contexts[str(m)]
            cell = cells.setdefault(frames[str(m)]["shape"], {"n": 0, "down": 0})
            cell["n"] += 1
            cell["down"] += outcome
    return {
        "schema": "mtf-reversal-model/v1",
        "asset": asset,
        "entry_family": family,
        "label": "bar3_close_below_open",
        "trained_through": train_end,
        "alpha": 20,
        "min_cell_n": 20,
        "min_components": 2,
        "base_models": {"10": {"n": n, "down": down, "contexts": contexts}},
        "selected": None,
    }


def select_policy(variants):
    """Rank eligible live policies on validation modeled ROE only."""
    eligible = [
        v
        for v in variants
        if v["delay_seconds"] == 10
        and v["exit"] == "target_momentum"
        and v["filter"] in ("shape", "shape_bop")
        and v["validation"]["n"] >= 30
        and v["validation"]["mean_roe"] is not None
    ]
    if not eligible:
        return {
            "id": "confirmed_uu/shape_bop/target_momentum/10",
            "family": "confirmed_uu",
            "filter": "shape_bop",
            "exit": "target_momentum",
            "delay_seconds": 10,
            "selection": "experimental_fallback",
        }
    from fractions import Fraction

    def ranking(v):
        val = v["validation"]
        mean = (
            Fraction(val["net_micro_sum"], val["n"] * 10_000_000)
            if "net_micro_sum" in val
            else Fraction(str(val["mean_roe"]))
        )
        return (-mean, -val["n"], v["id"])

    winner = min(eligible, key=ranking)
    return {
        **{key: winner[key] for key in ("family", "filter", "exit", "delay_seconds")},
        "id": winner["id"],
        "selection": "validation_selected_experimental",
    }

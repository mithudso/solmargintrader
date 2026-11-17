"""Pure official-client arithmetic for paper exit analysis.

This reproduces the saved frontend formula, not on-chain settlement or fills.
All money is integer micro-USD; entry and mark use the same integer price scale.
"""

from __future__ import annotations

import itertools

D = 1_000_000
A = 50_000
B = 7_259_685_000
K = 1_983_979


def quote_position(
    margin_micro_usd: int,
    notional_micro_usd: int,
    entry_price_int: int,
    mark_price_int: int,
    side: str,
    close_fee_ppm: int = 20,
    win_fee_ppm: int = 30_000,
    max_win_multiple: int = 25,
) -> dict:
    """Estimate payout from the saved frontend's integer arithmetic.

    The equality at an adverse liquidation boundary counts as a touch. A zero
    reserve still requires strictly adverse movement, matching the source branch.
    """
    values = (margin_micro_usd, notional_micro_usd, entry_price_int, mark_price_int)
    if any(type(x) is not int or x <= 0 for x in values):
        raise ValueError("margin, notional and prices must be positive integers")
    if side not in ("LONG", "SHORT"):
        raise ValueError("side must be LONG or SHORT")
    if any(type(x) is not int for x in (close_fee_ppm, win_fee_ppm, max_win_multiple)):
        raise ValueError("fee parameters must be integers")
    if not (
        0 <= close_fee_ppm <= D and 0 <= win_fee_ppm <= D and max_win_multiple >= 0
    ):
        raise ValueError("invalid fee parameters")
    margin, notional, entry, mark = values
    fee = min(margin, notional * close_fee_ppm // D)
    available = margin - fee
    signed_delta = mark - entry if side == "LONG" else entry - mark
    loss = gross = adjusted = win_fee = win_net = 0
    liquidatable = False
    if signed_delta < 0:
        adverse = -signed_delta
        liquidatable = notional * adverse >= available * entry
        loss = available if liquidatable else (notional * adverse + entry - 1) // entry
    elif signed_delta > 0:
        u = A * signed_delta - entry
        if u > 0:
            d = A * entry
            f = B * u + K * d
            gross = notional * 9 * u * u * B // (10 * d * f)
            adjusted = min(gross, margin * max_win_multiple)
            win_fee = adjusted * win_fee_ppm // D
            win_net = adjusted - win_fee
    payout = available - loss + win_net
    return {
        "close_fee": fee,
        "available_collateral": available,
        "loss": loss,
        "gross_profit": gross,
        "adjusted_profit": adjusted,
        "win_fee": win_fee,
        "win_net": win_net,
        "payout": payout,
        "liquidatable": liquidatable,
        "target_50": not liquidatable and 2 * payout >= 3 * margin,
    }


GRID_US = 200_000
HOLD_US = 15_000_000
PAPER_MARGIN = 10_000_000
PAPER_NOTIONAL = 1_000 * PAPER_MARGIN
POLICIES = ("fixed", "second_turn", "target", "target_momentum")


def start_position(
    entry_us, entry_price, cap_us, policy, delay_seconds=10, side="SHORT"
):
    """Start a paper SHORT at the first 200ms observation after the decision."""
    if (
        type(entry_us) is not int
        or entry_us % GRID_US
        or type(cap_us) is not int
        or cap_us % GRID_US
        or cap_us <= entry_us
        or type(entry_price) is not int
        or entry_price <= 0
        or policy not in POLICIES
        or delay_seconds not in (0, 5, 10)
        or side not in ("SHORT", "LONG")
    ):
        raise ValueError("invalid paper entry")
    return {
        "status": "open",
        "entry_us": entry_us,
        "entry_price": entry_price,
        "cap_us": cap_us,
        "policy": policy,
        "side": side,
        "delay_seconds": delay_seconds,
        "last_us": entry_us - GRID_US,
        "intent": None,
        "submit_us": None,
        "deadline_us": None,
        "target_first_us": None,
        "delay_liquidation": False,
        "exit_us": None,
        "exit_price": None,
        "payout": None,
        "target_filled": False,
    }


def step_position(state, at_us, price_int, flags=None):
    """Advance one contiguous observed grid point; return a new paper state."""
    s = dict(state)
    if (
        s["status"] != "open"
        or type(at_us) is not int
        or at_us != s["last_us"] + GRID_US
    ):
        raise ValueError("noncontiguous_or_terminal_sample")
    q = quote_position(
        PAPER_MARGIN, PAPER_NOTIONAL, s["entry_price"], price_int, s["side"]
    )
    s["last_us"] = at_us
    if q["target_50"] and s["target_first_us"] is None:
        s["target_first_us"] = at_us
    if q["liquidatable"]:
        s.update(
            status="liquidated",
            exit_us=at_us,
            exit_price=price_int,
            payout=0,
            delay_liquidation=s["deadline_us"] is not None
            and s["submit_us"] <= at_us <= s["deadline_us"],
        )
        return s
    flags = flags or {}
    if s["intent"] is None:
        if s["policy"] in ("target", "target_momentum") and q["target_50"]:
            s["intent"] = "target"
        elif s["policy"] == "target_momentum" and flags.get(
            "momentum_exit" if s["side"] == "SHORT" else "momentum_exit_long", False
        ):
            s["intent"] = "momentum"
        elif s["policy"] == "second_turn" and flags.get("second_turn_exit", False):
            s["intent"] = "second_turn"
        elif at_us >= s["cap_us"]:
            s["intent"] = "cap"
        if s["intent"] is not None:
            s["submit_us"] = max(at_us, s["entry_us"] + HOLD_US)
            s["deadline_us"] = s["submit_us"] + s["delay_seconds"] * 1_000_000
    if s["deadline_us"] is not None and at_us >= s["deadline_us"]:
        s.update(
            status="closed_proxy",
            exit_us=at_us,
            exit_price=price_int,
            payout=q["payout"],
            target_filled=q["target_50"],
            net_roe_ex_other_fees=(q["payout"] - PAPER_MARGIN) / PAPER_MARGIN,
        )
    return s


def minute_features(rows):
    """Compute causal completed 1m EMA/MACD and price-only BOP; reset at gaps."""
    import pandas as pd

    from research.reversal_history import validated_rows

    ordered = validated_rows(rows)
    result = {}
    starts = (
        [0]
        + [i for i in range(1, len(ordered)) if ordered[i][0] - ordered[i - 1][0] != 60]
        + [len(ordered)]
    )
    for left, right in itertools.pairwise(starts):
        chunk = ordered[left:right]
        if not chunk:
            continue
        close = pd.Series([r[4] for r in chunk], dtype=float)
        e9 = close.ewm(span=9, adjust=False).mean()
        e21 = close.ewm(span=21, adjust=False).mean()
        macd = (
            close.ewm(span=12, adjust=False).mean()
            - close.ewm(span=26, adjust=False).mean()
        )
        hist = macd - macd.ewm(span=9, adjust=False).mean()
        bop = (
            pd.Series(
                [(r[4] - r[1]) / (r[2] - r[3]) if r[2] != r[3] else 0.0 for r in chunk]
            )
            .rolling(3)
            .mean()
        )
        for j, row in enumerate(chunk):
            if j < 77:
                continue
            cross_ema = e9.iloc[j - 1] <= e21.iloc[j - 1] and e9.iloc[j] > e21.iloc[j]
            cross_hist = hist.iloc[j - 1] <= 0 < hist.iloc[j]
            cross_ema_down = (
                e9.iloc[j - 1] >= e21.iloc[j - 1] and e9.iloc[j] < e21.iloc[j]
            )
            cross_hist_down = hist.iloc[j - 1] >= 0 > hist.iloc[j]
            result[row[0] + 60] = {
                "momentum_exit_long": bool(cross_ema_down or cross_hist_down),
                "momentum_exit": bool(cross_ema or cross_hist),
                "ema_cross_up": bool(cross_ema),
                "macd_hist_cross_up": bool(cross_hist),
                "ema9": float(e9.iloc[j]),
                "ema21": float(e21.iloc[j]),
                "macd": float(macd.iloc[j]),
                "macd_signal": float((macd - hist).iloc[j]),
                "bop_sma3": float(bop.iloc[j]),
                "second_turn_exit": False,
            }
    return result


def prepare_signals(rows):
    """Precompute trailing-only features and shape frames once for a history."""
    from research.mtf_reversal import frame_index
    from research.reversal_history import validated_rows

    ordered = validated_rows(rows)
    return {
        "rows": {r[0]: r for r in ordered},
        "features": minute_features(ordered),
        "frames": frame_index(ordered),
    }


def signal_at(prepared, decision_s, family, model):
    """Evaluate a signal from a precomputed causal index at the decision."""
    import bisect

    from research.mtf_reversal import classify, context_at, score_context
    from research.reversal_shapes import color

    if type(decision_s) is not int or family not in ("confirmed_uu", "near_end"):
        raise ValueError("invalid signal request")
    features = prepared["features"].get(decision_s)
    context = context_at(prepared["frames"], decision_s)
    score = score_context(model, 10, context)
    ten, _, ends = prepared["frames"]["10"]
    i = bisect.bisect_right(ends, decision_s) - 1
    eligible = False
    partial_direction = None
    if family == "confirmed_uu" and decision_s % 600 == 0 and i >= 1:
        eligible = (
            ends[i] == decision_s
            and ten[i - 1][0] + 600 == ten[i][0]
            and color(ten[i - 1]) == color(ten[i]) == "UP"
        )
    elif family == "near_end" and decision_s % 600 == 540 and i >= 0:
        second_start = decision_s - 540
        recent = [prepared["rows"].get(second_start + j * 60) for j in range(9)]
        if all(r is not None for r in recent):
            partial_direction = (
                "UP"
                if recent[-1][4] > recent[0][1]
                else "DOWN"
                if recent[-1][4] < recent[0][1]
                else "FLAT"
            )
            eligible = (
                ends[i] == second_start
                and color(ten[i]) == "UP"
                and recent[-1][4] < recent[-1][1]
            )
    ready = features is not None
    return {
        "eligible": eligible and ready,
        "family": family,
        "decision_s": decision_s,
        "partial_second_direction": partial_direction,
        "features": features,
        "context": context,
        "score": score,
        "score_family": model.get("entry_family", "confirmed_uu"),
        "shape_filter": model.get("entry_family", "confirmed_uu") == family
        and score["status"] == "ready"
        and classify(score["score_down"], 0.525) == "DOWN",
        "bop_filter": bool(ready and features["bop_sma3"] < 0),
    }


def signal_snapshot(rows, decision_s, family, model):
    """Evaluate one 10m entry using only information available by decision."""
    return signal_at(prepare_signals(rows), decision_s, family, model)


def advance_proven(state, until_us, low_price_int, high_price_int):
    """Skip an observed OHLC interval that proves no target or barrier touch.

    Caller must establish a complete source minute covering every skipped grid
    point and ensure no unprocessed indicator decision within the interval.
    The OHLC bounds must be rounded outward into the common integer price scale.
    """
    s = dict(state)
    if (
        s["status"] != "open"
        or type(until_us) is not int
        or until_us % GRID_US
        or until_us <= s["last_us"]
        or type(low_price_int) is not int
        or type(high_price_int) is not int
        or low_price_int <= 0
        or high_price_int < low_price_int
    ):
        raise ValueError("invalid_bound_interval")
    if s["intent"] is None and s["cap_us"] <= until_us:
        raise ValueError("cap_inside_interval")
    if s["deadline_us"] is not None and s["deadline_us"] <= until_us:
        raise ValueError("deadline_inside_interval")
    low = quote_position(
        PAPER_MARGIN, PAPER_NOTIONAL, s["entry_price"], low_price_int, s["side"]
    )
    high = quote_position(
        PAPER_MARGIN, PAPER_NOTIONAL, s["entry_price"], high_price_int, s["side"]
    )
    if (
        low["liquidatable"]
        or high["liquidatable"]
        or low["target_50"]
        or high["target_50"]
    ):
        raise ValueError("target_or_liquidation_possible")
    s["last_us"] = until_us
    return s


def shape_tilts(model, context):
    """Return four family-conditional UP tilts with support and scoring status."""
    from research.mtf_reversal import score_context

    base = model["base_models"]["10"]
    n = base["n"]
    p = base["down"] / n if n else None
    scored = score_context(model, 10, context)
    supported = {str(c["minutes"]): c for c in scored["components"]}
    result = []
    for minutes in (5, 10, 15, 20):
        key = str(minutes)
        shape = context["frames"][key]["shape"]
        cell = base["contexts"][key].get(shape, {"n": 0, "down": 0})
        component = supported.get(key)
        result.append(
            {
                "minutes": minutes,
                "shape": shape,
                "n": cell["n"],
                "down": cell["down"],
                "supported": component is not None,
                "base_up": 1 - p if p is not None else None,
                "conditional_up": 1 - component["posterior_down"]
                if component
                else None,
                "up_tilt": p - component["posterior_down"] if component else None,
            }
        )
    return result


def graph_snapshot(rows, at_s, lookback=20):
    """10m previous and developing price-only OHLC from completed 1m rows.

    The lookback mean uses only full contiguous 10m bars preceding the current
    bar; a partial or missing current minute does not enter the display.
    """
    from research.reversal_history import validated_rows
    from research.reversal_second_turn import aggregate

    if type(at_s) is not int or type(lookback) is not int or lookback <= 0:
        raise ValueError("invalid graph request")
    closed = [r for r in validated_rows(rows) if r[0] + 60 <= at_s]
    start = at_s // 600 * 600
    completed = [
        b for b in aggregate(closed, 10, require_volume=False) if b[0] + 600 <= start
    ]
    previous = completed[-1] if completed and completed[-1][0] + 600 == start else None
    trailing = completed[-lookback:]
    if (
        len(trailing) != lookback
        or any(b[0] + 600 != c[0] for b, c in itertools.pairwise(trailing))
        or trailing[-1][0] + 600 != start
    ):
        mean_range = None
    else:
        mean_range = sum(b[2] - b[3] for b in trailing) / lookback
    current_rows = [r for r in closed if start <= r[0] < start + 600]
    if current_rows and all(r[0] == start + i * 60 for i, r in enumerate(current_rows)):
        current = [
            start,
            current_rows[0][1],
            max(r[2] for r in current_rows),
            min(r[3] for r in current_rows),
            current_rows[-1][4],
        ]
    else:
        current = None
    return {
        "bar_start": start,
        "elapsed_s": at_s - start,
        "previous": previous,
        "developing": current,
        "mean_range": mean_range,
        "range_lookback_bars": lookback,
    }

"""Pure fixed-ten-minute bearish checks; no I/O, orders or calibrated odds."""

from __future__ import annotations

import math

from research import zec_live as live
from research.zec_tui_metrics import STREAK_HASH

STEP = 600
HALF = 300
FRESH_SECONDS = 15


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _five(rows, stamp, end):
    bar = rows.get(stamp)
    if not isinstance(bar, dict) or bar.get("ts") != stamp or stamp + HALF > end:
        return None
    values = [bar.get(k) for k in ("open", "high", "low", "close", "volume")]
    if not all(_number(v) for v in values):
        return None
    opening, high, low, close, volume = values
    if not 0 < low <= min(opening, close) <= max(opening, close) <= high or volume < 0:
        return None
    return bar


def _ten(rows, stamp, end):
    first, second = _five(rows, stamp, end), _five(rows, stamp + HALF, end)
    if first is None or second is None:
        return None
    return {"open": first["open"], "close": second["close"], "ts": stamp}


def _price(snapshot, start, now):
    if not isinstance(snapshot, dict) or snapshot.get("connected") is not True:
        return None, "trade stream unavailable / disconnected"
    if snapshot.get("gap") is not False or snapshot.get("reason"):
        return None, "trade stream has a gap or unavailable current candle"
    receipt, event = snapshot.get("observed_at"), snapshot.get("event_at")
    if not all(_number(t) and 0 <= now - t <= FRESH_SECONDS for t in (receipt, event)):
        return None, "trade price stale / future clock"
    bar = snapshot.get("bar")
    if (
        not isinstance(bar, dict)
        or bar.get("ts") != start
        or not start <= event < start + STEP
    ):
        return None, "waiting for a trade in the current ten-minute candle"
    price = bar.get("close")
    if not _number(price) or price <= 0:
        return None, "invalid current trade price"
    return price, None


def _historical(reference):
    if not isinstance(reference, dict) or reference.get("source_sha256") != STREAK_HASH:
        return None
    count, total = reference.get("reversals"), reference.get("total")
    if (
        type(count) is not int
        or type(total) is not int
        or not 0 <= count <= total
        or total <= 0
    ):
        return None
    return {"reversals": count, "total": total, "source_sha256": STREAK_HASH}


def bearish_alert(context, snapshot, now):
    """Re-evaluate against the current target; never retain an expired signal.

    Current true open comes from the completed first five-minute constituent,
    never from a stream's partial-since-attachment opening observation.
    """
    result = {
        "state": "unavailable",
        "stage": "unknown",
        "closed_up_count": None,
        "current_bar_number": None,
        "older_bar_status": "unknown",
        "count_scope": "last_two_closed_bars_checked",
        "reversal_detected": False,
        "data_status": "invalid_clock",
        "direction": None,
        "qualified": False,
        "current_start": None,
        "target_at": None,
        "price": None,
        "true_open": None,
        "price_relation": None,
        "elapsed_seconds": None,
        "historical": None,
        "reason": "invalid_clock",
        "text": "10m · closed UP ? → bar ? · DATA UNAVAILABLE\nPrice / TRUE open unavailable · clock unavailable\nUTC window unavailable · NOT LIVE ODDS",
        "tooltip": "No valid current ten-minute target is available.",
    }
    if not _number(now) or now <= 0:
        return result
    start = int(now // STEP) * STEP
    elapsed = now - start
    result.update(current_start=start, target_at=start + STEP, elapsed_seconds=elapsed)
    beginning = live.iso(start)[11:19]
    target = live.iso(start + STEP)[11:19]

    def state(kind, data_status, detail, note, reason):
        count = result["closed_up_count"]
        setup = (
            "2 closed UP (UU) → bar 3"
            if count == 2
            else "1 closed UP confirmed → bar 2"
            if count == 1
            else "0 prior UP → bar ? (no UP setup)"
            if count == 0
            else "closed UP ? → bar ?"
        )
        unavailable = data_status not in ("ready", "midpoint_wait")
        status = (
            "REVERSAL DETECTED"
            if result["reversal_detected"]
            else "DATA UNAVAILABLE"
            if unavailable
            else "WATCHING"
        )
        price, opening = result["price"], result["true_open"]
        if price is not None and opening is not None:
            comparison = f"Price ${price:,.5f} {result['price_relation']} TRUE open ${opening:,.5f}"
        else:
            current = (
                f"Price ${price:,.5f}" if price is not None else "Price unavailable"
            )
            actual_open = (
                f"TRUE open ${opening:,.5f}"
                if opening is not None
                else "TRUE open pending (5m settle)"
                if data_status == "midpoint_wait"
                else "TRUE open unavailable"
            )
            comparison = f"{current} · {actual_open}"
        historical = result["historical"]
        history_note = ""
        if historical:
            count, total = historical["reversals"], historical["total"]
            history_note = (
                f" Historical UU reference: {count}/{total} = {100 * count / total:.1f}% "
                "next bar DOWN in one captured day. NOT LIVE ODDS; this does not measure "
                "the midpoint trigger or continued decline after detection."
            )
        result.update(
            state=kind,
            data_status=data_status,
            reason=reason,
            text=(
                f"10m · {setup} · {status}\n"
                f"{comparison} · elapsed {int(elapsed // 60)}m{int(elapsed % 60):02}s\n"
                f"UTC {beginning}–{target} · {note}"
            ),
            tooltip=(
                f"Current UTC ten-minute window: {live.iso(start)} → {live.iso(start + STEP)}. "
                f"{detail}. The count checks only the last two closed ten-minute bars; "
                "one confirmed UP does not prove an exact one-bar run when the older bar is missing. "
                f"Older bar status: {result['older_bar_status']}. "
                "Only bearish checks are enabled. The midpoint trigger still requires at least "
                "five minutes in the current bar, a completed first five-minute candle for its true "
                "open, and a fresh current trade below that open. Midpoint condition untested. "
                "Further decline after detection is unproven. NOT calibrated live odds. "
                "Screen context only; no trading action."
                f"{history_note}"
            ),
        )
        return result

    if not isinstance(context, dict) or context.get("error"):
        return state(
            "unavailable",
            "history_unavailable",
            "Completed five-minute history unavailable",
            "History unavailable · NOT LIVE ODDS",
            "history_unavailable",
        )
    end, calculated = context.get("end"), context.get("calculated_at")
    latest = int(now // HALF) * HALF
    settled = int((now - live.SETTLE_SECONDS) // HALF) * HALF
    if (
        type(end) is not int
        or end % HALF
        or end < settled
        or end > latest
        or not _number(calculated)
        or not 0 <= now - calculated
    ):
        return state(
            "unavailable",
            "history_stale_or_future",
            "History stale / future clock; awaiting refresh",
            "History stale / future · NOT LIVE ODDS",
            "history_stale_or_future",
        )
    rows = context.get("rows")
    if not isinstance(rows, dict):
        return state(
            "unavailable",
            "history_unavailable",
            "Completed history unavailable",
            "History unavailable · NOT LIVE ODDS",
            "history_unavailable",
        )
    previous = _ten(rows, start - STEP, end)
    if previous is None:
        return state(
            "waiting",
            "previous_constituent_missing",
            "Waiting for both halves of the previous full ten-minute candle",
            "Previous full candle missing · NOT LIVE ODDS",
            "previous_constituent_missing",
        )
    older = _ten(rows, start - 2 * STEP, end)
    older_up = bool(older is not None and older["close"] > older["open"])
    result["older_bar_status"] = (
        "unknown" if older is None else "up" if older_up else "not_up"
    )
    previous_up = previous["close"] > previous["open"]
    result["closed_up_count"] = 2 if previous_up and older_up else int(previous_up)
    result["current_bar_number"] = (
        result["closed_up_count"] + 1 if previous_up else None
    )
    result["stage"] = (
        "two_up_bar3"
        if previous_up and older_up
        else "one_up_bar2"
        if previous_up
        else "no_up_setup"
    )
    first_half = _five(rows, start, end) if elapsed >= HALF else None
    if first_half is not None:
        result["true_open"] = first_half["open"]
    price, error = _price(snapshot, start, now)
    if error:
        return state(
            "unavailable",
            "trade_unavailable",
            error,
            "Fresh trade unavailable · NOT LIVE ODDS",
            "trade_unavailable",
        )
    result["price"] = price
    if result["true_open"] is not None:
        result["price_relation"] = (
            "<"
            if price < result["true_open"]
            else ">"
            if price > result["true_open"]
            else "="
        )
    if not previous_up:
        return state(
            "none",
            "ready",
            "Previous full ten-minute candle is not UP",
            "No bearish setup; no DD → UP alert",
            "previous_not_up",
        )
    if first_half is not None:
        opening = first_half["open"]
        if price < opening:
            result.update(direction="DOWN", reversal_detected=True)
            return state(
                "observed_reversal",
                "ready",
                "Reversal detected: current trade is below this bar's TRUE open after at least five minutes",
                "Further decline unproven · NOT LIVE ODDS",
                None,
            )
    if older_up:
        reference = _historical(context.get("reference"))
        result.update(direction="DOWN", historical=reference)
        return state(
            "uu_watch",
            "ready"
            if first_half
            else "midpoint_wait"
            if elapsed < HALF
            else "true_open_unavailable",
            "Two closed UP candles establish the current bar 3 watch; no midpoint reversal is detected",
            "Further decline unproven · NOT LIVE ODDS",
            None,
        )
    if elapsed < HALF:
        return state(
            "waiting",
            "midpoint_wait",
            "Waiting until ≥5 minutes into the next ten-minute candle",
            "Trigger waits ≥5m · NOT LIVE ODDS",
            "before_midpoint",
        )
    if first_half is None:
        return state(
            "waiting",
            "true_open_unavailable",
            "Waiting for the completed first five-minute candle / true open",
            "TRUE open unavailable · NOT LIVE ODDS",
            "true_open_unavailable",
        )
    return state(
        "none",
        "ready",
        f"Fresh price ${price:,.5f} is not below TRUE open ${first_half['open']:,.5f}",
        "No reversal detected · NOT LIVE ODDS",
        "price_not_below_open",
    )

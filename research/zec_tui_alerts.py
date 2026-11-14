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
        "direction": None,
        "qualified": False,
        "current_start": None,
        "target_at": None,
        "price": None,
        "true_open": None,
        "historical": None,
        "reason": "invalid_clock",
        "text": "10m bearish check · no alert\nClock unavailable\nScreen context only · no trading action",
        "tooltip": "No valid current ten-minute target is available.",
    }
    if not _number(now) or now <= 0:
        return result
    start = int(now // STEP) * STEP
    result.update(current_start=start, target_at=start + STEP)
    target = live.iso(start + STEP)[11:19]

    def state(kind, title, detail, qualification, reason):
        result.update(
            state=kind,
            reason=reason,
            text=f"10m {title}\n{detail}\n{qualification}",
            tooltip=(
                f"Current UTC ten-minute window: {live.iso(start)} → {live.iso(start + STEP)}. "
                "Only bearish checks are enabled. Observed midpoint reversal is not a forecast probability. "
                "The historical UU fraction is one exploratory captured day with a different receipt clock."
            ),
        )
        return result

    if not isinstance(context, dict) or context.get("error"):
        return state(
            "unavailable",
            "bearish check · no alert",
            "Completed five-minute history unavailable",
            "Screen context only · no trading action",
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
            "bearish check · no alert",
            "History stale / future clock; awaiting refresh",
            "Screen context only · no trading action",
            "history_stale_or_future",
        )
    rows = context.get("rows")
    if not isinstance(rows, dict):
        return state(
            "unavailable",
            "bearish check · no alert",
            "Completed history unavailable",
            "Screen context only · no trading action",
            "history_unavailable",
        )
    previous = _ten(rows, start - STEP, end)
    if previous is None:
        return state(
            "waiting",
            "bearish check · no alert",
            "Waiting for both halves of the previous full ten-minute candle",
            "Missing candles are never filled",
            "previous_constituent_missing",
        )
    price, error = _price(snapshot, start, now)
    if error:
        return state(
            "unavailable",
            "bearish check · no alert",
            error,
            "Fresh actual trade required · no trading action",
            "trade_unavailable",
        )
    result["price"] = price
    if previous["close"] <= previous["open"]:
        return state(
            "none",
            "bearish check · no alert",
            "Previous full ten-minute candle is not UP",
            "Bearish-only · no DD → UP alert",
            "previous_not_up",
        )
    older = _ten(rows, start - 2 * STEP, end)
    uu = bool(older is not None and older["close"] > older["open"])
    elapsed = now - start
    first_half = _five(rows, start, end) if elapsed >= HALF else None
    if first_half is not None:
        opening = first_half["open"]
        result["true_open"] = opening
        if price < opening:
            result["direction"] = "DOWN"
            return state(
                "observed_reversal",
                "REVERSAL OBSERVED · prior full UP + current below TRUE open",
                f"${price:,.5f} < ${opening:,.5f} · {int(elapsed // 60)}m {int(elapsed % 60):02}s elapsed · ends {target} UTC",
                "Midpoint condition untested · NOT calibrated live odds",
                None,
            )
    if uu:
        reference = _historical(context.get("reference"))
        result.update(direction="DOWN", historical=reference)
        note = "Historical reference unavailable · NOT LIVE ODDS"
        if reference:
            count, total = reference["reversals"], reference["total"]
            note = f"History {count}/{total} = {100 * count / total:.1f}% · one captured day · NOT LIVE ODDS"
        return state(
            "uu_watch",
            "DOWN WATCH · two full UP candles (UU)",
            f"Current ten-minute window ends {target} UTC · next DOWN watch",
            note,
            None,
        )
    if elapsed < HALF:
        return state(
            "waiting",
            "bearish check · one full UP candle",
            "Waiting until ≥5 minutes into the next ten-minute candle",
            "Then compare fresh price with its TRUE open",
            "before_midpoint",
        )
    if first_half is None:
        return state(
            "waiting",
            "bearish check · one full UP candle",
            "Waiting for the completed first five-minute candle / true open",
            "Partial stream open is never substituted",
            "true_open_unavailable",
        )
    return state(
        "none",
        "bearish check · no midpoint reversal",
        f"Fresh price ${price:,.5f} is not below TRUE open ${first_half['open']:,.5f}",
        "No bearish alert · no trading action",
        "price_not_below_open",
    )

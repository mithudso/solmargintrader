"""Worker-owned market sessions for the editable read-only Oracle TUI."""

from __future__ import annotations

import copy
import time

from oracle.feeds import FeedUnavailable, RecorderFeed
from research import zec_live as live
from research.zec_tui_model import market_details


class Cancelled(RuntimeError):
    pass


class DataSession:
    """One worker owns every cache. Configuration changes never race a fetch."""

    def __init__(self, client=None, clock=time.time):
        self.client = client or live.Candles(pause=0)
        self.clock = clock
        self.windows = {}

    def fetch(self, step, start, end, cancelled):
        result = {}
        while start < end:
            if cancelled():
                raise Cancelled()
            stop = min(end, start + 299 * step)
            result.update(self.client.fetch(step, start, stop))
            start = stop
        if cancelled():
            raise Cancelled()
        return result

    def __call__(self, request, cancelled):
        interval, winners = request["interval"], request["rows"]
        step = live.STEPS[interval]
        base_step = 300 if step == 600 else step
        now = self.clock()
        end = int((now - live.SETTLE_SECONDS) // step) * step
        window = self.windows.setdefault(
            interval, {"raw": {}, "end": None, "attempt": -1e12, "cycle": {}}
        )
        raw = window["raw"]
        try:
            if raw and (end - min(raw)) // step > live.MAX_HISTORY:
                raise FeedUnavailable("history_capacity_exceeded")
            # Fixed seed: chart lookback and manual selection do not change a
            # stateful strategy's initial conditions or the cycle decision clock.
            if window["end"] != end and now - window["attempt"] >= 15:
                start = (
                    max(min(raw), max(raw) - 3 * base_step) if raw else end - 512 * step
                )
                window["attempt"] = now
                fetched = self.fetch(base_step, start, end, cancelled)
                raw.update(fetched)
                complete = (
                    live.aggregate(raw, base_step, step) if step != base_step else raw
                )
                if end - step in complete:
                    window["end"] = end
            rows = live.aggregate(raw, base_step, step) if step != base_step else raw
            if cancelled():
                raise Cancelled()
            evaluated = live.evaluate(
                interval, winners, rows, end, frozen_cycle=window["cycle"]
            )
            details = market_details(
                rows, interval, end, request["lookback"], [w["config"] for w in winners]
            )
            if cancelled():
                raise Cancelled()
            return {
                "interval": interval,
                "rows": evaluated,
                "details": details,
                "calculated_at": self.clock(),
                "error": None,
            }
        except Cancelled:
            window["attempt"] = -1e12
            raise
        except FeedUnavailable as exc:
            return {
                "interval": interval,
                "rows": [
                    {
                        **w,
                        "status": "unavailable",
                        "reason": exc.code,
                        "direction": None,
                    }
                    for w in winners
                ],
                "details": None,
                "calculated_at": self.clock(),
                "error": exc.code,
            }


class QuoteReader:
    def __init__(self, prices=None, feed=None):
        self.feed = feed or RecorderFeed(prices, instrument="ZEC/USD")
        self.last = None

    def __call__(self, request, cancelled):
        try:
            quote = self.feed.poll()
            if quote:
                self.last = quote
            return {"quote": self.last, "error": None}
        except FeedUnavailable as exc:
            return {"quote": None, "error": exc.code}


def live_view(frame, quote_result, now):
    """Age data against the current paint clock, independent of refresh cadence."""
    result = copy.deepcopy(frame)
    quote = (quote_result or {}).get("quote")
    error = (quote_result or {}).get("error")
    if not quote or not 0 <= now - quote["observed_at"] <= 15:
        quote, error = None, error or "quote_stale"
    result.update(quote=quote, quote_error=error, generated_at=now)
    for row in result["rows"]:
        if row.get("status") == "ready" and (error or now >= row["target_at"]):
            row.update(
                status="stale",
                last_direction=row["direction"],
                direction=None,
                reason=error or "completed_bar_prediction_expired",
            )
    details = result.get("details")
    if details:
        details["stale"] = bool(
            error or now >= details["asof"] + live.STEPS[result["interval"]]
        )
        shape = details["shape"]
        low, high = shape.get("range_low"), shape.get("range_high")
        if quote and high is not None and high > low:
            shape["live_range_position"] = (quote["price"] - low) / (high - low)
    return result

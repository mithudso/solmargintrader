"""Causal, display-only streaming indicators and captured-day streak context.

Developing trade bars never enter the authoritative winner or shape adapters.
Closed history is cached; a new trade computes only one provisional point.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from functools import lru_cache

import numpy as np

from research import zec_live as live
from research.zec_tui_model import market_indicators

STREAK_HASH = "83c4b4b15f990a8d7b7e4804f6c1d2ea15d3f784c2d500033cc4c94fc33734df"


@lru_cache(maxsize=1)
def streak_reference():
    path = live.ROOT / "research/zec-two-bar-reversal-20261114/results.json"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != STREAK_HASH:
        raise ValueError("streak_reference_hash_mismatch")
    return {
        row["interval_seconds"]: row
        for row in json.loads(raw)["results"]
        if row["mask"] == "gap_safe" and row["definition"] == "body"
    }


def two_bar_context(rows, interval, end):
    """A rolling color condition on closed, adjacent bars; never live confidence."""
    step = live.STEPS[interval]
    result = {
        "interval": interval,
        "asof": end,
        "target_at": end + step,
        "condition": None,
        "direction": None,
        "new_streak": None,
        "historical": None,
        "qualified": False,
        "source_sha256": STREAK_HASH,
        "text": "Two-bar reversal · awaiting two contiguous completed candles.",
    }
    bars = [rows.get(end - i * step) for i in (3, 2, 1)]

    def color(bar):
        if not bar:
            return None
        o, c = bar.get("open"), bar.get("close")
        if (
            type(o) not in (int, float)
            or type(c) not in (int, float)
            or not math.isfinite(o)
            or not math.isfinite(c)
            or min(o, c) <= 0
        ):
            return None
        return 1 if c > o else -1 if c < o else 0

    previous, first, second = map(color, bars)
    if first is None or second is None:
        return result
    clock = f"Closed {live.iso(end)} · next bar ends {live.iso(end + step)}"
    if not first or not second or first != second:
        result["text"] = (
            "Two-bar reversal · no same-color pair (flat / mixed bars).\n"
            + clock
            + " · research context only"
        )
        return result
    up = second == 1
    result.update(
        condition="UU" if up else "DD",
        direction="DOWN" if up else "UP",
        new_streak=previous == -second if previous is not None else None,
    )
    label = "two up → watch down" if up else "two down → watch up"
    try:
        reference = streak_reference()[step]
        stats = reference["conditional"]["up2" if up else "down2"]
        exact = reference["conditional"][
            ("up2" if up else "down2") + "_exact_after_opposite"
        ]
    except (OSError, KeyError, ValueError):
        result["text"] = (
            f"Two-bar reversal · {label}\n{clock}\n"
            "Historical reference unavailable · no calibrated probability."
        )
        return result
    count = stats["next_down" if up else "next_up"]
    exact_count = exact["next_down" if up else "next_up"]
    result["historical"] = {
        "reversals": count,
        "total": stats["n"],
        "flats": stats["next_flat"],
        "exact_reversals": exact_count,
        "exact_total": exact["n"],
        "capture": "2026-11-12 through 2026-11-13",
        "clock": "receipt-time historical capture; live candles use exchange time",
    }
    pct = 100 * count / stats["n"] if stats["n"] else 0
    exact_pct = 100 * exact_count / exact["n"] if exact["n"] else 0
    streak = (
        "new streak of exactly two"
        if result["new_streak"]
        else "rolling pair in a longer run"
        if result["new_streak"] is False
        else "preceding color unknown"
    )
    small = " · tiny sample" if stats["n"] < 10 else ""
    result["text"] = (
        f"Two-bar reversal · {label} · {streak}\n"
        f"Historical rolling: {count}/{stats['n']} = {pct:.1f}%"
        f" (flat {stats['next_flat']}){small}; new-streak: "
        f"{exact_count}/{exact['n']} = {exact_pct:.1f}%\n"
        f"{clock}\n"
        "ONE CAPTURED DAY · different clock/source · not live probability or a trade rule"
    )
    return result


def indicator_units(name):
    if name.startswith("EMA") or (name.startswith("BB") and "%B" not in name):
        return "USD", "price"
    if name.startswith("Volume"):
        return "ZEC", "separate"
    if name.startswith(("MACD", "ATR")):
        return "USD change", "separate"
    if name.startswith("Balance"):
        return "ratio", "separate"
    if name.startswith("Z-score"):
        return "σ", "separate"
    return "%", "separate"


def compact_two_bar(result):
    """Keep the narrow numeric panel readable; full provenance is in its tooltip."""
    target = live.iso(result["target_at"])[11:16]
    condition, stats = result["condition"], result["historical"]
    if condition is None:
        return (
            "Two-bar: no valid same-color pair\n"
            f"Target {target} UTC\n"
            "Completed candles only"
        )
    direction = "DOWN" if condition == "UU" else "UP"
    kind = (
        "new two"
        if result["new_streak"]
        else "rolling"
        if result["new_streak"] is False
        else "prefix?"
    )
    if stats is None:
        return f"{condition} → {direction}? ({kind})\nHistory unavailable\nNOT LIVE ODDS · {target} UTC"
    count, total = stats["reversals"], stats["total"]
    exact, exact_total = stats["exact_reversals"], stats["exact_total"]
    return (
        f"{condition} → {direction}? ({kind})\n"
        f"History {count}/{total} = {100 * count / total:.1f}% · flat {stats['flats']}\n"
        f"New-two {exact}/{exact_total} = {100 * exact / exact_total:.1f}%\n"
        "1 day · NOT LIVE ODDS"
        + (" · TINY n" if total < 10 else "")
        + f"\nTarget {target} UTC"
    )


def clean_bars(rows, step, end):
    bars, valid = live.arrays_for(rows, step, end)
    gaps = np.flatnonzero(~valid)
    start = int(gaps[-1]) + 1 if len(gaps) else 0
    return {k: v[start:] for k, v in bars.items()}


def valid_live_bar(snapshot, interval, end, now):
    """Return a genuine fresh, same-bucket bar; never bridge missing periods."""
    if not snapshot or not snapshot.get("connected"):
        return None, (snapshot or {}).get("reason") or "trade_stream_unavailable"
    if snapshot.get("gap"):
        return None, snapshot.get("reason") or "trade_stream_gap"
    observed = snapshot.get("observed_at")
    if type(observed) not in (int, float) or not 0 <= now - observed <= 15:
        return None, "trade_stream_stale"
    event_at = snapshot.get("event_at")
    if type(event_at) not in (int, float) or not 0 <= now - event_at <= 15:
        return None, "trade_event_stale"
    bar = snapshot.get("bar")
    if not isinstance(bar, dict) or bar.get("ts") != end:
        return None, "awaiting_contiguous_current_trade_bar"
    if int(now // live.STEPS[interval]) * live.STEPS[interval] != end:
        return None, "awaiting_completed_history_boundary"
    values = [bar.get(k) for k in ("open", "high", "low", "close", "volume")]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        return None, "invalid_trade_bar"
    o, h, low, c, v = values
    if not 0 < low <= min(o, c) <= max(o, c) <= h or v < 0:
        return None, "invalid_trade_bar"
    return bar, None


class IndicatorSession:
    """LatestWorker loader; no socket, UI, strategy evaluation or disk writes."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self._key = None
        self._closed = None

    def __call__(self, request, cancelled):
        interval, end = request["interval"], request["end"]
        lookback = request.get("lookback", 96)
        configs = request.get("configs", ())
        if lookback not in (48, 96, 192, 300):
            raise ValueError("invalid_indicator_lookback")
        rows = request["rows"]
        # Exclude future and forming rows from both the cache key and reference.
        closed = {int(k): v for k, v in rows.items() if int(k) < end}
        key = live.digest(
            live.canonical([interval, end, lookback, configs, closed]).encode()
        )
        if key != self._key:
            bars = clean_bars(closed, live.STEPS[interval], end)
            n = len(bars["ts"])
            series = {}
            for i in range(max(0, n - lookback), n):
                if cancelled():
                    raise RuntimeError("indicator_calculation_cancelled")
                point = market_indicators(
                    {k: v[: i + 1] for k, v in bars.items()}, configs
                )
                for item in point:
                    series.setdefault(item["name"], []).append(item["value"])
            values = market_indicators(bars, configs)
            result = {
                "interval": interval,
                "asof": end,
                "end": end,
                "lookback": lookback,
                "chart": bars["close"][-lookback:].tolist(),
                "times": bars["ts"][-lookback:].tolist(),
                "indicators": values,
                "series": series,
                "two_bar": two_bar_context(closed, interval, end),
            }
            if cancelled():
                raise RuntimeError("indicator_calculation_cancelled")
            self._key, self._closed = key, (bars, result)
        bars, cached = self._closed
        frame = copy.deepcopy(cached)
        frame["context"] = request.get("context")
        frame.update(live=False, partial=False, live_at=None, status="completed")
        snapshot = request.get("live") or {}
        now = self.clock()
        frame["stale"] = not end <= now < end + live.STEPS[interval]
        frame["two_bar"]["stale"] = frame["stale"]
        if frame["stale"]:
            frame["status"] = "stale"
            frame["two_bar"]["last_direction"] = frame["two_bar"]["direction"]
            frame["two_bar"]["direction"] = None
            frame["two_bar"]["text"] = (
                "RETAINED / EXPIRED · " + frame["two_bar"]["text"]
            )
        if not len(bars["ts"]):
            frame["status"] = "unavailable"
        bar, reason = valid_live_bar(snapshot, interval, end, now)
        frame["reason"] = reason
        if (
            bar is not None
            and len(bars["ts"])
            and bars["ts"][-1] + live.STEPS[interval] == end
        ):
            extended = {k: np.append(v, bar[k]) for k, v in bars.items()}
            readings = market_indicators(extended, configs)
            by_name = {item["name"]: item["value"] for item in readings}
            frame["chart"] = (frame["chart"] + [bar["close"]])[-lookback:]
            frame["times"] = (frame["times"] + [bar["ts"]])[-lookback:]
            for name, series in frame["series"].items():
                frame["series"][name] = (series + [by_name.get(name)])[-lookback:]
            frame["indicators"] = readings
            frame.update(
                live=True,
                partial=bool(snapshot.get("partial", True)),
                live_at=snapshot["observed_at"],
                status="live_partial"
                if snapshot.get("partial", True)
                else "live_developing",
                reason=None,
            )
        for item in frame["indicators"]:
            item["unit"], item["axis"] = indicator_units(item["name"])
        frame["two_bar"]["compact_text"] = compact_two_bar(frame["two_bar"])
        if cancelled():
            raise RuntimeError("indicator_calculation_cancelled")
        return frame

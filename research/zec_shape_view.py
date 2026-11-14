"""Explain observed geometry without changing the detector or strategy calls."""

from __future__ import annotations

import math
from itertools import pairwise

from research.zec_live import iso

# These sketches illustrate each label. They are never fitted or projected prices.
GUIDES = {
    "unknown": (
        "Shape unavailable",
        "?",
        "There is not enough usable geometry to describe a shape.",
        "Wait for 48 contiguous completed bars.",
        "No directional implication is available.",
    ),
    "range": (
        "Sideways range",
        "▂▇▂▆▃▇▂▆",
        "Price has moved back and forth with little net progress.",
        "Watch rejection at the edges or a break beyond them.",
        "A continuing move outside the range breaks this interpretation.",
    ),
    "trend_up": (
        "Upward trend",
        "▁▂▃▂▄▅▆▇",
        "The observed path makes net upward progress despite pullbacks.",
        "Watch whether a pullback holds and the climb resumes.",
        "A sustained reversal weakens the continuation interpretation.",
    ),
    "trend_down": (
        "Downward trend",
        "▇▆▅▆▄▃▂▁",
        "The observed path makes net downward progress despite bounces.",
        "Watch whether a bounce stalls and the decline resumes.",
        "A sustained rebound weakens the continuation interpretation.",
    ),
    "v_rebound": (
        "V-shaped rebound",
        "█▆▄▂▁▂▄▆",
        "A sharp decline has been followed by a sharp recovery.",
        "Watch whether the recovery holds its reclaimed ground.",
        "A return through the recent low breaks the rebound interpretation.",
    ),
    "inverted_v": (
        "Inverted V",
        "▁▂▄▆█▆▄▂",
        "A sharp rise has been followed by a sharp retreat.",
        "Watch whether the retreat continues after a bounce.",
        "A return through the recent high breaks the retreat interpretation.",
    ),
    "bowl": (
        "Rounded bottom (bowl)",
        "█▆▃▂▁▁▂▄",
        "The fitted path curves from falling toward rising.",
        "Watch whether recovery continues beyond the fitted low.",
        "A renewed decline through the recent low challenges the bottom.",
    ),
    "cap": (
        "Rounded top (cap)",
        "▁▃▆▇██▇▅",
        "The fitted path curves from rising toward falling.",
        "Watch whether weakness continues beyond the fitted high.",
        "A renewed rise through the recent high challenges the top.",
    ),
    "compression": (
        "Narrowing range (compression)",
        "▁█▂▇▃▆▄▅",
        "Fitted highs and lows converge into a narrower price band.",
        "Watch which boundary price breaks; either direction is possible.",
        "A widening band ends the compression interpretation.",
    ),
}


def range_readout(shape):
    position = shape.get("live_range_position", shape.get("range_position"))
    if position is None or not math.isfinite(position):
        return "Observed range position unavailable"
    source = "Live quote" if "live_range_position" in shape else "Last close"
    slot = min(16, max(0, round(position * 16)))
    gauge = "─" * slot + "●" + "─" * (16 - slot)
    return f"{source} in observed 48-bar range: {gauge} {position:.0%}"


def shape_summary(details):
    shape = details["shape"]
    title, sketch, meaning, watch, invalidation = GUIDES.get(
        shape.get("shape"), GUIDES["unknown"]
    )
    stale = "RETAINED / STALE · " if details.get("stale") else ""
    return "\n".join(
        (
            f"{stale}{title.upper()} · label age {shape.get('episode_age_bars', '—')} bars",
            f"Illustration: {sketch}  (time →; not the live chart)",
            meaning,
            range_readout(shape),
            watch,
            invalidation,
            "Observed geometry, not future completion · H: Shape guide",
        )
    )


def price_trace(prices, width=50, height=7):
    """Join only supplied observed closes; the dot marks the final supplied close."""
    if len(prices) != 48 or not all(math.isfinite(v) for v in prices):
        return "Actual trace unavailable: needs 48 contiguous completed closes."
    width = max(16, min(80, int(width)))
    lo, hi = min(prices), max(prices)
    grid = [[" " for _ in range(width)] for _ in range(height)]
    points = [
        (
            round(i * (width - 1) / 47),
            round((hi - value) / (hi - lo) * (height - 1)) if hi > lo else height // 2,
        )
        for i, value in enumerate(prices)
    ]
    for (x0, y0), (x1, y1) in pairwise(points):
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            grid[y][x] = "─" if y0 == y1 else "╱" if y1 < y0 else "╲"
    x, y = points[-1]
    grid[y][x] = "●"
    lines = []
    for i, line in enumerate(grid):
        value = hi - (hi - lo) * i / (height - 1)
        lines.append(f"{value:>10.3f} │" + "".join(line))
    return "\n".join(
        [
            *lines,
            "           └" + "─" * width,
            "            oldest" + " " * max(1, width - 23) + "last close →",
        ]
    )


def shape_guide(details, interval, width=50):
    if not details:
        return "Shape unavailable. Waiting for this window's completed candles."
    shape = details["shape"]
    title, sketch, meaning, watch, invalidation = GUIDES.get(
        shape.get("shape"), GUIDES["unknown"]
    )
    lines = [
        f"{title} · {interval} bars",
        "RETAINED / STALE DATA"
        if details.get("stale")
        else "Current completed-bar window",
        "",
        "WHAT THE LABEL MEANS",
        meaning,
        f"Illustrative sketch: {sketch}   time →",
        "This sketch is a teaching example, not a fitted or predicted path.",
        "",
        "WHAT TO WATCH NEXT (CONDITIONAL)",
        watch,
        "WHAT WOULD CHALLENGE THIS INTERPRETATION",
        invalidation,
        "",
        "ACTUAL OBSERVED CLOSES · 48 BARS · ● LAST COMPLETED CLOSE",
        price_trace(shape.get("trace", []), width),
    ]
    if shape.get("trace_start") is not None:
        lines.append(
            f"Bar opens {iso(shape['trace_start'])} → {iso(shape['trace_end'])}"
        )
    lines += [
        f"Completed data as of {iso(details['asof'])}",
        "",
        "WHERE WE ARE",
        range_readout(shape),
    ]
    low, high = shape.get("range_low"), shape.get("range_high")
    if low is not None and high is not None:
        lines.append(f"Observed candle low ${low:,.5f} / high ${high:,.5f}")
    if shape.get("zone") in ("lower", "middle", "upper"):
        lines.append(f"Last completed close: {shape['zone']} third of that range.")
    lines += [
        f"The rolling label has stayed the same for {shape.get('episode_age_bars', '—')} bars.",
        "Label age is not the duration or completion of the whole pattern.",
    ]
    ago = shape.get("fitted_turn_bars_ago")
    if shape.get("shape") in ("bowl", "cap") and ago is not None:
        turning = "low" if shape["shape"] == "bowl" else "high"
        lines.append(
            f"Fitted {turning}: {ago:.1f} bars before the last close; a past curve fit."
        )
    fit = shape.get("fit_r2")
    if shape.get("shape") in ("bowl", "cap") and fit is not None:
        lines.append(
            f"Curve fit R² {fit:.3f}: historical fit quality, not forecast confidence."
        )
    lines += [
        "",
        "These are visual checks to watch, not automatic trade triggers.",
        "",
        "HOW TO READ THIS WITH A STRATEGY",
        "The shape describes price geometry. The watchlist call comes from the selected strategy.",
        "Baseline rows use shape as context; shape-mode rows retain their existing fixed filter.",
        "Compression does not choose a breakout direction. A rebound does not guarantee another rise.",
        "No directional probability or future pattern-completion percentage is established.",
        "",
        "OTHER DETECTOR LABELS · ILLUSTRATIVE SKETCHES",
    ]
    lines.extend(
        f"{entry[0]}: {entry[1]}\n  {entry[2]}"
        for key, entry in GUIDES.items()
        if key != "unknown"
    )
    return "\n".join(lines)

"""Timestamp-aligned terminal price/indicator plots without a plotting dependency."""

from __future__ import annotations

import math

from rich.text import Text
from textual.widgets import Sparkline

from research import zec_live as live


def finite(value):
    return type(value) in (float, int) and math.isfinite(value)


def plot_text(frame, selected=None, *, width=80, height=10):
    """Price levels share USD scale; other measures use a named right scale."""
    if not frame or not frame.get("chart"):
        return Text("Price / indicator graph · waiting for valid candles", style="dim")
    prices, times = frame["chart"], frame["times"]
    if len(prices) != len(times) or not all(finite(p) for p in prices):
        return Text("Graph unavailable: unaligned prices / timestamps", style="yellow")
    width, height = max(24, width), max(6, height)
    items = {item["name"]: item for item in frame.get("indicators", [])}
    metric = items.get(selected)
    overlay = frame.get("series", {}).get(selected, []) if metric else []
    if overlay and len(overlay) != len(prices):
        return Text("Graph unavailable: unaligned indicator timestamps", style="yellow")
    separate = bool(metric and metric.get("axis") != "price")
    available = [v for v in overlay if finite(v)]
    price_values = prices + (available if not separate else [])

    def limits(values):
        low, high = min(values), max(values)
        if low == high:
            margin = max(abs(low) * 0.001, 0.001)
            return low - margin, high + margin
        return low, high

    low, high = limits(price_values)
    other_low, other_high = limits(available) if available else (0, 1)
    rows, cols = max(2, height - 4), max(4, width - 22)
    grid = [[("·", "#33475a") for _ in range(cols)] for _ in range(rows)]
    first, last = times[0], times[-1]

    def points(values, lo, hi, glyph, style):
        for stamp, value in zip(times, values):
            if not finite(value):
                continue
            x = (
                round((stamp - first) / (last - first) * (cols - 1))
                if last > first
                else cols - 1
            )
            y = round((hi - value) / (hi - lo) * (rows - 1))
            y = min(rows - 1, max(0, y))
            old = grid[y][x][0]
            grid[y][x] = (
                ("◎", "bold yellow") if old != "·" and old != glyph else (glyph, style)
            )

    points(prices, low, high, "●", "#68d7e3")
    if available:
        points(
            overlay,
            other_low if separate else low,
            other_high if separate else high,
            "◆",
            "#ff9bd0",
        )
    title = "USD price ●"
    if metric:
        value = metric["value"]
        rendered = f"{value:,.5g}" if finite(value) else "unavailable"
        title += f"  {selected} ◆ {rendered} {metric['unit']}"
    else:
        title += " · click an indicator to overlay"
    output = Text()
    headline = Text(title, style="bold")
    headline.truncate(width)
    output.append_text(headline)
    output.append("\n")
    scale = "USD left"
    if metric:
        scale += f" · {metric['unit']} {'right (independent scale)' if separate else 'shared USD scale'}"
    scale_line = Text(scale, style="dim")
    scale_line.truncate(width)
    output.append_text(scale_line)
    output.append("\n")
    for y, line in enumerate(grid):
        value = high - y / (rows - 1) * (high - low)
        output.append(f"{value:9.5g} │", style="#68d7e3")
        for char, style in line:
            output.append(char, style=style)
        output.append("│")
        if separate and available:
            value = other_high - y / (rows - 1) * (other_high - other_low)
            output.append(f"{value:9.5g}", style="#ff9bd0")
        output.append("\n")
    clock = f"{live.iso(first)[11:16]} → {live.iso(last)[11:16]} UTC · candle starts"
    if frame.get("live"):
        clock += " · last point developing"
    tail = Text(clock, style="dim")
    tail.truncate(width)
    output.append_text(tail)
    if metric and not available:
        note = Text(
            "\nSelected indicator is warming / unavailable; no line invented.",
            style="yellow",
        )
        note.truncate(width)
        output.append_text(note)
    return output


class MarketChart(Sparkline):
    """Retain Sparkline.data compatibility while rendering real numeric overlays."""

    def __init__(self, *args, **kwargs):
        self.frame = None
        self.selected_indicator = None
        super().__init__(*args, **kwargs)

    def set_frame(self, frame, selected_indicator=None):
        self.frame = frame
        self.selected_indicator = selected_indicator
        self.data = frame.get("chart", []) if frame else []
        self.refresh()

    def render(self):
        if self.frame is None and self.data:
            return super().render()
        return plot_text(
            self.frame,
            self.selected_indicator,
            width=self.size.width or 80,
            height=self.size.height or 10,
        )

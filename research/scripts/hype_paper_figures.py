"""Draw the two figures of the HYPE working paper from the frozen study data.

Reads only tracked evidence (the Hyperliquid candle CSVs, ``structure.json`` and
the paper's zone list) and writes deterministic SVG, so a figure can always be
rebuilt and compared with the committed one. No network, no plotting library.

    python -m research.hype_paper_figures            # write the figures
    python -m research.hype_paper_figures --check    # exit 1 if they are stale
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import UTC, datetime
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STRUCTURE = ROOT / "research/json/hype-structure-20261127"
OUTPUT = ROOT / "research/json/hype-paper-20261127"

INK = "#222e29"
MUTED = "#6e776d"
GRID = "#e1e5dc"
BAND = "#e6e9df"
LINE = "#173f35"
RESISTANCE = "#f47230"
SUPPORT = "#257de0"
FONT = "Helvetica, Arial, sans-serif"

WIDTH = 720
RECENT_HOURS = 90 * 24


def read_candles(path: Path) -> list[tuple[int, float, float, float]]:
    """Return (open time, high, low, close) rows in file order."""
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (int(row["timestamp"]), float(row["high"]), float(row["low"]), float(row["close"]))
            for row in csv.DictReader(handle)
        ]


def day(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC).timestamp())


def money(value: float) -> str:
    return f"${value:,.2f}"


def text(x: float, y: float, body: str, *, anchor: str = "start", size: float = 10, fill: str = INK,
         weight: str = "normal") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" font-size="{size:g}" '
            f'font-weight="{weight}" fill="{fill}">{escape(body)}</text>')


def polyline(points: list[tuple[float, float]], *, stroke: str, width: float) -> str:
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return (f'<polyline points="{path}" fill="none" stroke="{stroke}" stroke-width="{width:g}" '
            'stroke-linejoin="round" stroke-linecap="round"/>')


def svg(height: int, title: str, description: str, body: list[str]) -> str:
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" '
            f'height="{height}" role="img" font-family="{FONT}">')
    return "\n".join([head, f"<title>{escape(title)}</title>", f"<desc>{escape(description)}</desc>", *body,
                      "</svg>"]) + "\n"


def spread(wanted: list[float], gap: float, low: float, high: float) -> list[float]:
    """Move label positions apart until none is closer than ``gap``.

    Labels arrive sorted top to bottom. A forward pass pushes each one below its
    neighbour; a backward pass pulls the stack up again if it ran off the bottom.
    """
    placed = []
    for value in wanted:
        placed.append(max(value, placed[-1] + gap) if placed else max(value, low))
    overflow = placed[-1] - high if placed else 0.0
    if overflow > 0:
        placed[-1] = high
        for index in range(len(placed) - 2, -1, -1):
            placed[index] = min(placed[index], placed[index + 1] - gap)
    return placed


def month_ticks(first: int, last: int, months: tuple[int, ...]) -> list[tuple[int, str]]:
    ticks = []
    moment = datetime.fromtimestamp(first, UTC).replace(day=1, hour=0, minute=0, second=0)
    while moment.timestamp() <= last:
        if moment.timestamp() >= first and moment.month in months:
            label = moment.strftime("%b %Y") if moment.month == 1 or not ticks else moment.strftime("%b")
            ticks.append((int(moment.timestamp()), label))
        moment = moment.replace(year=moment.year + (moment.month == 12), month=moment.month % 12 + 1)
    return ticks


def declines_figure(daily: list[tuple[int, float, float, float]], structure: dict) -> str:
    height = 330
    left, right, top, bottom = 46, WIDTH - 14, 44, height - 30
    first, last = daily[0][0], daily[-1][0]
    low_price, high_price = 8.0, 120.0

    def x(moment: float) -> float:
        return left + (moment - first) / (last - first) * (right - left)

    def y(price: float) -> float:
        span = math.log(high_price) - math.log(low_price)
        return bottom - (math.log(price) - math.log(low_price)) / span * (bottom - top)

    body = []
    labels = []
    for decline in structure["drawdowns"]:
        start, end = x(day(decline["peak_date"])), x(day(decline["trough_date"]))
        body.append(f'<rect x="{start:.1f}" y="{top}" width="{max(end - start, 1.5):.1f}" '
                    f'height="{bottom - top}" fill="{BAND}"/>')
        labels.append(((start + end) / 2, f"−{abs(decline['depth']) * 100:.1f}%"))
    for price in (10, 20, 40, 80):
        body.append(f'<line x1="{left}" x2="{right}" y1="{y(price):.1f}" y2="{y(price):.1f}" '
                    f'stroke="{GRID}" stroke-width="1"/>')
        body.append(text(left - 6, y(price) + 3.5, f"${price}", anchor="end", size=10, fill=MUTED))
    for moment, label in month_ticks(first, last, (1, 4, 7, 10)):
        body.append(f'<line x1="{x(moment):.1f}" x2="{x(moment):.1f}" y1="{bottom}" y2="{bottom + 4}" '
                    f'stroke="{MUTED}" stroke-width="1"/>')
        body.append(text(x(moment), bottom + 16, label, anchor="middle", size=10, fill=MUTED))
    body.append(f'<line x1="{left}" x2="{right}" y1="{bottom}" y2="{bottom}" stroke="{MUTED}" stroke-width="1"/>')
    body.append(polyline([(x(moment), y(close)) for moment, _, _, close in daily], stroke=LINE, width=1.5))

    # Depth labels sit above the plot. Two short declines a fortnight apart would
    # print on top of each other, so a label that collides drops to a second row.
    previous_end = -math.inf
    row = 0
    for centre, label in labels:
        half = len(label) * 3.2
        row = 1 - row if centre - half < previous_end + 4 else 0
        body.append(text(centre, top - 22 + row * 13, label, anchor="middle", size=10.5, weight="bold"))
        previous_end = centre + half

    summary = structure["summary"]
    high_x, high_y = x(day(summary["all_time_high_date"])), y(summary["all_time_high"])
    low_x, low_y = x(day(summary["window_low_date"])), y(summary["window_low"])
    body.append(f'<circle cx="{high_x:.1f}" cy="{high_y:.1f}" r="3" fill="{LINE}" stroke="#fff" stroke-width="1.5"/>')
    body.append(text(high_x - 7, high_y + 1, f"High {money(summary['all_time_high'])}", anchor="end", size=10.5))
    body.append(f'<circle cx="{low_x:.1f}" cy="{low_y:.1f}" r="3" fill="{LINE}" stroke="#fff" stroke-width="1.5"/>')
    body.append(text(low_x + 7, low_y + 4, f"Low {money(summary['window_low'])}", size=10.5))
    return svg(height, "HYPE daily close with declines of 25% or more",
               "Line chart of the HYPE daily close on a logarithmic price axis from December 2024 to November 2026. "
               "Seven shaded bands mark each decline of 25% or more from its peak to its trough.", body)


def check_zones(zones: dict, structure: dict) -> None:
    """Refuse a zone the structure results do not support.

    The zone list is typed by hand from the paper's table. Without this check a
    mistyped price would be drawn as confidently as a real one. Each swing bound
    must be a swing-level bound, each volume bound a bound of the 90-day value
    area the caption names (not another window's), and a side must agree with
    the last close.
    """
    reference = zones["reference_close"]
    profile = structure["volume_profiles"]["hourly_last_90d"]
    # A zone may merge neighbouring levels, so its two bounds are checked one by
    # one, each against the bounds of its own kind.
    known = {
        "swing": {round(level[edge], 2) for level in structure["daily_levels"] + structure["hourly_levels"]
                  for edge in ("low", "high")},
        "volume": {round(profile["value_area_low"], 2), round(profile["value_area_high"], 2)},
    }
    problems = []
    for zone in zones["zones"]:
        label = f"{zone['low']}-{zone['high']}"
        if zone["kind"] not in known:
            problems.append(f"{label}: unknown kind {zone['kind']!r}")
            continue
        problems.extend(f"{label}: {bound} is not a {zone['kind']} bound in structure.json"
                        for bound in (zone["low"], zone["high"]) if round(bound, 2) not in known[zone["kind"]])
        on_side = {"resistance": zone["low"] >= reference, "support": zone["high"] <= reference}
        if not on_side.get(zone["side"], False):
            problems.append(f"{label}: is not on the {zone['side']} side of the last close {reference}")
    if problems:
        raise SystemExit("zones.json disagrees with structure.json: " + "; ".join(problems))


def levels_figure(hourly: list[tuple[int, float, float, float]], zones: dict) -> str:
    height = 410
    left, right, top, bottom = 46, 470, 12, height - 30
    recent = hourly[-RECENT_HOURS:]
    first, last = recent[0][0], recent[-1][0]
    low_price, high_price = 48.0, 100.0
    reference = zones["reference_close"]

    def x(moment: float) -> float:
        return left + (moment - first) / (last - first) * (right - left)

    def y(price: float) -> float:
        return bottom - (price - low_price) / (high_price - low_price) * (bottom - top)

    shown = [zone for zone in zones["zones"] if zone["kind"] == "swing" and zone["high"] > low_price]
    colour = {"resistance": RESISTANCE, "support": SUPPORT}
    body = []
    for price in range(50, 101, 10):
        body.append(f'<line x1="{left}" x2="{right}" y1="{y(price):.1f}" y2="{y(price):.1f}" '
                    f'stroke="{GRID}" stroke-width="1"/>')
        body.append(text(left - 6, y(price) + 3.5, f"${price}", anchor="end", size=10, fill=MUTED))
    for zone in shown:
        upper, lower = y(zone["high"]), y(zone["low"])
        body.append(f'<rect x="{left}" y="{upper:.1f}" width="{right - left}" height="{max(lower - upper, 2):.1f}" '
                    f'fill="{colour[zone["side"]]}" fill-opacity="0.26"/>')
    for moment, label in month_ticks(first, last, tuple(range(1, 13))):
        body.append(f'<line x1="{x(moment):.1f}" x2="{x(moment):.1f}" y1="{bottom}" y2="{bottom + 4}" '
                    f'stroke="{MUTED}" stroke-width="1"/>')
        body.append(text(x(moment), bottom + 16, label, anchor="middle", size=10, fill=MUTED))
    body.append(f'<line x1="{left}" x2="{right}" y1="{bottom}" y2="{bottom}" stroke="{MUTED}" stroke-width="1"/>')
    body.append(polyline([(x(moment), y(close)) for moment, _, _, close in recent], stroke=LINE, width=1.3))

    volume = next(zone for zone in zones["zones"] if zone["kind"] == "volume")
    bracket = right + 9
    body.append(f'<path d="M{bracket - 4},{y(volume["high"]):.1f} H{bracket} V{y(volume["low"]):.1f} H{bracket - 4}" '
                f'fill="none" stroke="{MUTED}" stroke-width="1.2"/>')

    label_x = right + 44
    rows = [(y((zone["low"] + zone["high"]) / 2), zone) for zone in shown]
    rows.append((y(reference), None))
    rows.sort(key=lambda row: row[0])
    for (anchor, zone), placed in zip(rows, spread([row[0] for row in rows], 14.5, top + 4, bottom - 2), strict=True):
        tone = INK if zone is None else colour[zone["side"]]
        body.append(f'<path d="M{right + 16},{anchor:.1f} L{label_x - 14},{placed:.1f} H{label_x - 5}" '
                    f'fill="none" stroke="{tone}" stroke-width="{1.2 if zone is None else 1}"/>')
        if zone is None:
            body.append(text(label_x, placed + 3.5, f"Last close {money(reference)}", size=10.5, weight="bold"))
            continue
        body.append(f'<rect x="{label_x}" y="{placed - 4:.1f}" width="8" height="8" rx="1.5" '
                    f'fill="{colour[zone["side"]]}"/>')
        body.append(text(label_x + 13, placed + 3.5,
                         f"{money(zone['low'])}–{zone['high']:.2f}  {zone['side'].capitalize()}", size=10.5))
    body.append(f'<line x1="{left}" x2="{right + 16}" y1="{y(reference):.1f}" y2="{y(reference):.1f}" '
                f'stroke="{INK}" stroke-width="1" stroke-dasharray="4 3"/>')
    # The bracket's caption goes beside its middle, the one stretch of the label
    # column that no zone label can reach.
    middle = y((volume["low"] + volume["high"]) / 2)
    for offset, line in ((-7, "70% of the last 90 days'"), (4, "volume traded here:"),
                         (15, f"{money(volume['low'])}–{volume['high']:.2f}")):
        body.append(text(bracket + 8, middle + offset, line, size=10, fill=MUTED))
    return svg(height, "HYPE hourly close with support and resistance zones",
               "Line chart of the HYPE hourly close over the last 90 days of the study. Shaded horizontal zones mark "
               "resistance above the last close and support below it; each zone's price range is labelled at the "
               "right.", body)


def build() -> dict[str, str]:
    structure = json.loads((STRUCTURE / "structure.json").read_text(encoding="utf-8"))
    zones = json.loads((OUTPUT / "zones.json").read_text(encoding="utf-8"))
    check_zones(zones, structure)
    if round(zones["reference_close"], 3) != round(structure["summary"]["last_hourly_close"], 3):
        raise SystemExit("zones.json reference_close differs from structure.json last_hourly_close")
    return {
        "fig1-declines.svg": declines_figure(read_candles(STRUCTURE / "HYPE_1d.csv"), structure),
        "fig2-levels.svg": levels_figure(read_candles(STRUCTURE / "HYPE_1h.csv"), zones),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if a committed figure is stale")
    args = parser.parse_args()
    # Bytes, not text: the figures are compared and written as UTF-8 with "\n"
    # line ends whatever the platform's default encoding or newline is.
    figures = {name: body.encode("utf-8") for name, body in build().items()}
    stale = [name for name, body in figures.items()
             if not (OUTPUT / name).is_file() or (OUTPUT / name).read_bytes() != body]
    if args.check:
        if stale:
            raise SystemExit("paper figures stale: " + ", ".join(stale))
        print(f"Paper figures current: {len(figures)} files")
        return
    for name, body in figures.items():
        (OUTPUT / name).write_bytes(body)
    print(f"Wrote {len(figures)} figures to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

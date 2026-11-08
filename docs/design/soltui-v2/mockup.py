#!/usr/bin/env python3
"""SolTUI v2 -- a clickable layout mockup on fixture data.

This is a design artefact, not a feature. It imports nothing from ``soltui/``,
reads no files, opens no sockets and runs no command: every number below is a
fixture lifted from committed result files (cited in ``DESIGN.md``) or made up to
look like them. Actions in the command palette only raise a toast that names the
real command they stand for.

Run it (needs Textual 8.2.8 and textual-plotext):

    python3 docs/design/soltui-v2/mockup.py              # interactive
    python3 docs/design/soltui-v2/mockup.py --shots DIR  # write one SVG per screen
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Group
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.theme import Theme
from textual.widgets import ContentSwitcher, DataTable, Digits, Footer, Input, Sparkline, Static
from textual_plotext import PlotextPlot

# --------------------------------------------------------------------------- tokens
# One source of colour truth. The up/down pair is the diverging pair for every
# signed quantity (calls, votes, P&L); it passed the dataviz validator on the dark
# surface (CVD dE 28.4). Status colours are reserved for system health and always
# travel with a glyph whose *shape* differs (● ▲ ✖ ⟳ ◌), because green and amber
# are close under protanopia -- colour is never the only cue.
TOK: dict[str, str] = {
    "bg": "#0b1018",
    "surface": "#121a26",
    "panel": "#1a2433",
    "rule": "#2a3547",
    "fg": "#d6deeb",
    "muted": "#7d8aa3",
    "dim": "#3a465a",
    "accent": "#7aa2ff",
    "up": "#3b8ef0",
    "down": "#d46d1c",
    "ok": "#2ea043",
    "warn": "#d29922",
    "err": "#e5534b",
    "idle": "#6e7681",
    "live": "#b48ead",
}

STATUS = {
    "ok": ("●", TOK["ok"]),
    "run": ("⟳", TOK["accent"]),
    "warn": ("▲", TOK["warn"]),
    "err": ("✖", TOK["err"]),
    "idle": ("◌", TOK["idle"]),
}

CALL = {"UP": ("▲", "UP", TOK["up"]), "DOWN": ("▼", "DOWN", TOK["down"]), "FLAT": ("─", "FLAT", TOK["muted"])}

NIGHT = Theme(
    name="soltui-night",
    primary=TOK["accent"],
    secondary=TOK["muted"],
    accent=TOK["accent"],
    foreground=TOK["fg"],
    background=TOK["bg"],
    surface=TOK["surface"],
    panel=TOK["panel"],
    success=TOK["ok"],
    warning=TOK["warn"],
    error=TOK["err"],
    dark=True,
    variables={k: TOK[k] for k in ("up", "down", "live", "muted", "dim", "rule", "idle")},
)


# --------------------------------------------------------------------------- glyph helpers
def status(kind: str, label: str, detail: str = "") -> Text:
    glyph, colour = STATUS[kind]
    return Text.assemble((f"{glyph} ", colour), (label, f"bold {TOK['fg']}"), (f" {detail}" if detail else "", TOK["muted"]))


def call_text(call: str, bold: bool = True) -> Text:
    glyph, label, colour = CALL[call]
    return Text.assemble((f"{glyph} ", colour), (label, f"{'bold ' if bold else ''}{TOK['fg']}"))


def call_badge(call: str, width: int = 14) -> Text:
    """Three rows tall: the call is the answer, so it must outweigh the composite digits."""
    glyph, label, colour = CALL[call]
    fill = f"bold {TOK['bg']} on {colour}"
    out = Text()
    out.append(" " * width + "\n", fill)
    out.append(f"{glyph} {label}".center(width) + "\n", fill)
    out.append(" " * width, fill)
    return out


def delta(value: float, fmt: str = "{:+.2f}", suffix: str = "") -> Text:
    """Colour sits on the glyph, the number stays in ink (dataviz: text wears text tokens)."""
    glyph, colour = ("▲", TOK["up"]) if value > 0 else ("▼", TOK["down"]) if value < 0 else ("─", TOK["muted"])
    return Text.assemble((f"{glyph} ", colour), (fmt.format(value) + suffix, TOK["fg"]))


def money(value: float, signed: bool = False) -> str:
    sign = "+" if signed and value > 0 else "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def div_bar(value: float, maxabs: float = 1.0, half: int = 9) -> Text:
    """Diverging bar at half-cell resolution: down grows left of the axis, up grows right."""
    cells = min(half * 2, round(abs(value) / maxabs * half * 2))
    full, part = divmod(cells, 2)
    if value >= 0:
        left, right = " " * half, ("█" * full + ("▌" if part else "")).ljust(half)
    else:
        left, right = (("▐" if part else "") + "█" * full).rjust(half), " " * half
    return Text.assemble((left, TOK["down"]), ("│", TOK["dim"]), (right, TOK["up"]))


def meter(frac: float, width: int, colour: str = TOK["accent"]) -> Text:
    n = max(0, min(width, round(frac * width)))
    return Text.assemble(("━" * n, colour), ("━" * (width - n), TOK["dim"]))


def range_strip(q1: float, med: float, q3: float, lo: float = -2.0, hi: float = 2.0, width: int = 17) -> Text:
    """A one-line box plot: IQR as a rule, median as a dot, zero as a tick."""

    def pos(x: float) -> int:
        return round((min(hi, max(lo, x)) - lo) / (hi - lo) * (width - 1))

    cells = [("·", TOK["dim"])] * width
    cells[pos(0.0)] = ("┊", TOK["muted"])
    for i in range(pos(q1), pos(q3) + 1):
        cells[i] = ("─", TOK["fg"])
    cells[pos(med)] = ("●", TOK["up"] if med >= 0 else TOK["down"])
    out = Text()
    for ch, style in cells:
        out.append(ch, style)
    return out


def spark(values: list[float]) -> str:
    bars = "▁▂▃▄▅▆▇█"
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1.0
    return "".join(bars[round((v - lo) / span * 7)] for v in values)


def right(text: str | Text, style: str = TOK["fg"]) -> Text:
    t = text if isinstance(text, Text) else Text(text, style=style)
    t.justify = "right"
    return t


def muted(text: str) -> Text:
    return Text(text, style=TOK["muted"])


def kv_table(rows: list[tuple[str, Text | str]], key_width: int = 14) -> Table:
    table = Table.grid(padding=(0, 1))
    table.add_column(width=key_width, style=TOK["muted"])
    table.add_column()
    for key, value in rows:
        table.add_row(key, value)
    return table


# --------------------------------------------------------------------------- fixtures
@dataclass
class Coin:
    sym: str
    price: float
    chg24: float
    call: str
    composite: float
    oos_hit: float
    oos_z: float
    fwd_hit: float | None
    fwd_calls: int
    trainer: str  # ok | run | idle | err
    verdict: str  # "costs eat it" | "no edge" | "possible edge"
    regime: str
    blocked: list[str] = field(default_factory=list)


# OOS hit and z for SOL/BTC/ETH/HYPE: research/results/compound-10coin-fullhistory-2026-11-07.json.
# Forward hit rates for SOL/DOGE: docs/COMPOUND-5M.md. Every coin returned -100% after
# 13 bps round-trip costs at 5x, so no verdict here may read better than "costs eat it".
COINS: list[Coin] = [
    Coin("SOL", 74.03, 0.8, "DOWN", -0.31, 0.5221, 10.63, 0.502, 184, "run", "costs eat it", "trend ↓ · late"),
    Coin("BTC", 101_420.0, -0.4, "FLAT", 0.06, 0.5173, 9.22, 0.497, 171, "run", "costs eat it", "range"),
    Coin("ETH", 3_318.5, 1.6, "UP", 0.27, 0.5306, 16.93, 0.531, 176, "run", "costs eat it", "trend ↑ · early"),
    Coin("XRP", 2.31, 2.9, "UP", 0.22, 0.5244, 11.80, 0.512, 160, "ok", "costs eat it", "squeeze"),
    Coin("DOGE", 0.1712, -1.2, "DOWN", -0.19, 0.5262, 12.40, 0.556, 158, "run", "costs eat it", "trend ↓ · mid"),
    Coin("AVAX", 21.84, -2.3, "FLAT", -0.04, 0.5120, 6.10, 0.488, 149, "idle", "no edge", "range"),
    Coin("LINK", 14.06, 0.3, "FLAT", 0.09, 0.5141, 7.30, None, 0, "idle", "no edge", "neutral", ["trend"]),
    Coin("HYPE", 38.77, 4.1, "UP", 0.35, 0.5068, 1.11, 0.441, 92, "err", "no edge", "trend ↑ · late"),
    Coin("ZEC", 61.20, -0.9, "FLAT", 0.02, 0.5099, 4.20, None, 0, "idle", "no edge", "range"),
    Coin("SUI", 3.44, 1.1, "DOWN", -0.12, 0.5187, 8.10, 0.503, 133, "ok", "costs eat it", "neutral"),
]

GATES = [
    ("cost", "edge > 13 bps round trip"),
    ("liquidation", "stop inside liq. distance"),
    ("shock", "no >3σ bar in last 12"),
    ("news", "no blackout window"),
    ("trend", "call agrees with 1h trend"),
    ("warm-up", "all metrics warm"),
    ("data", "complete minute bars"),
    ("spread", "book spread < 4 bps"),
]

METRICS = [
    "rsi", "vwap_dist", "mom_skip", "obv_slope", "macd_hist", "bb_pos", "funding", "oi_delta",
    "book_imb", "stoch_k", "ema_cross", "cci", "atr_regime", "vol_z", "williams_r", "news_sent",
    "adx", "kama_slope", "hurst", "zscore_20", "donchian_pos", "mfi", "taker_ratio", "basis",
]

# CPCV rows: research/results/cpcv_results.csv and cpcv_top5_sol_doge_zec_1d.csv (SOL, 1d).
# (label, family, horizon, median Sharpe, IQR, share of paths positive, median net %, trades)
LEADERBOARD = [
    ("all(dual_momentum+vol_regime)", "combo", "long", 1.35, 0.88, 0.87, 75.1, 52),
    ("any(hurst_switch+ou_reversion)", "combo", "long", 1.29, 0.71, 1.00, 68.9, 37),
    ("obv_trend_60", "volume-flow", "long", 0.77, 1.57, 0.81, 44.6, 98),
    ("hurst_switch_250_0.55_0.45", "regime", "medium", 0.70, 1.17, 0.93, 16.7, 24),
    ("vol_regime_60_0.5", "volatility", "long", 0.70, 0.82, 0.80, 36.1, 54),
    ("adx_trend_30_25", "trend", "long", 0.65, 2.29, 0.57, 26.2, 14),
    ("ou_reversion_20_2", "mean-rev", "medium", 0.52, 1.40, 0.71, 18.3, 41),
    ("donchian_55", "trend", "long", 0.41, 1.85, 0.62, 12.9, 19),
    ("rsi_revert_14_30_70", "mean-rev", "short", 0.12, 2.40, 0.52, 2.1, 211),
    ("macd_12_26_9", "momentum", "medium", -0.21, 1.66, 0.38, -7.4, 66),
    ("dual_momentum_24_2", "momentum", "short", -4.63, 2.09, 0.00, -39.2, 728),
]
BELOW_FLOOR = [
    ("kalman_trend_200", "trend", "long", 1.85, 3.30, 0.90, 51.0, 6),
    ("squeeze_break_20", "volatility", "medium", 1.12, 2.80, 0.76, 22.4, 8),
]

ACTIVITY = [
    ("08:15", "run", "Signal SOL ▼ DOWN −0.31 · 8/8 gates pass"),
    ("08:12", "ok", "Sweep finished obv_trend_60 · 1d · Sharpe 0.77 (ranked #3)"),
    ("08:10", "ok", "Autopilot adopted ETH config v14 → v15 (OOS sign test p 0.03)"),
    ("08:05", "warn", "LP state file stopped updating (last write 08:11)"),
    ("08:00", "ok", "Wallet snapshot · 6 chains · +$18.40 since 07:00"),
    ("07:58", "err", "HYPE trainer exited: 28.5% incomplete 5m bars"),
    ("07:41", "ok", "Forward test resolved 30 calls · 1m 51.0% · 5m 50.6%"),
    ("07:30", "idle", "Docs index rebuilt while idle (412 files)"),
]

CHAINS = [
    ("Solana", "ok", 612.40, 12.10, "SOL 7.91 · USDC 26.3"),
    ("Base", "ok", 388.15, 4.95, "WETH 0.081 · LP NFTs 2"),
    ("Ethereum", "ok", 201.77, 1.12, "ETH 0.061"),
    ("Bitcoin", "ok", 61.90, 0.21, "BTC 0.00061"),
    ("Litecoin", "warn", 12.04, 0.00, "timed out · cached"),
    ("Dogecoin", "ok", 7.94, 0.02, "DOGE 46.4"),
]

# liquidity/STATE_FILES.md example data.
LP_POSITIONS = [
    ("WETH/cbBTC", 0.0236, 0.0251, 0.0258, 43.10, 45.00, -1.92, -0.92, -12.3, "skip_unprofitable"),
    ("WETH/USDC", 3_180.0, 3_520.0, 3_318.5, 44.30, 44.00, 0.30, 0.12, 9.8, "hold"),
]
SCOUT = [
    ("WETH/wstETH", "$1.2M", "$3.4M", 3.1, 6.4, 0.2, 18.2, "$4.10", "high", ""),
    ("USDC/cbBTC", "$4.8M", "$2.1M", 1.4, 5.2, 0.6, 11.7, "$9.80", "medium", ""),
    ("AERO/WETH", "$0.9M", "$5.6M", 9.8, 14.1, 6.9, 15.3, "$2.20", "low", "IL-heavy"),
]

def _daily_pnl() -> list[float]:
    """30 daily nets that sum to the -$3.12 shown in the tiles, so tile and chart agree."""
    rng = random.Random(30)
    raw = [rng.gauss(-0.1, 0.45) for _ in range(30)]
    shift = (-3.12 - sum(raw)) / 30
    return [round(v + shift, 2) for v in raw]


DAILY_PNL = _daily_pnl()
CUM_PNL = [sum(DAILY_PNL[: i + 1]) for i in range(30)]


def cumulative(n: int, seed: int, step: float) -> list[float]:
    rng = random.Random(seed)
    out, x = [], 0.0
    for _ in range(n):
        x += rng.gauss(0, step)
        out.append(x)
    return out


def table(table_id: str) -> DataTable:
    # renderable priority keeps glyph colours (bars, ▲▼) visible under the row cursor.
    return DataTable(id=table_id, cursor_type="row", cursor_foreground_priority="renderable")


PALETTE_COMMANDS = [
    ("Backtest: run CPCV on roster", "Foreground run, cancellable", "backtest.run"),
    ("Backtest: cancel run", "Stops at the next configuration boundary", "backtest.cancel"),
    ("Sweep: start background sweep", "Low priority, ordered by promise", "queue.start"),
    ("Sweep: stop after current job", "One-time token on the control socket", "queue.stop"),
    ("Sweep: queue untested strategies", "Adds every strategy with no result", "queue.add_untested"),
    ("Data: fetch missing price series", "The only network fetch in the package", "data.fetch"),
    ("Roster: add all strategies", "", "roster.add_all"),
    ("Roster: toggle highlighted strategy", "", "roster.toggle"),
    ("Signal: call now for SOL", "Next 5m bar, every metric explained", "compound.call"),
    ("Signal: backtest all coins", "IS/OOS, perturbation optional", "compound.backtest"),
    ("Signal: start unattended training (all)", "Detached, survives closing the console", "compound.train_start"),
    ("Signal: autopilot off", "Stops the 300 s launch agent", "compound.autopilot"),
    ("Forward test: start 1/5/10/30 min test", "Runs while the console is open", "forwardtest.start"),
    ("Replay: step through a backtest", "Paper fills, no order path", "paper.start"),
    ("Dry run: launch extension dry-run", "extension/tools/dryrun.js", "live.dryrun"),
    ("Money: scan all wallets", "Read-only, 420 s budget", "wallet.scan"),
    ("Money: take wallet snapshot", "", "portfolio.snapshot"),
    ("LP: kill daemon", "Writes KILL — the one real-money write", "liquidity.kill"),
    ("LP: resume daemon", "Needs a second confirm", "liquidity.resume"),
    ("P&L: change window", "24h · 7d · 30d · 90d · YTD · all", "pnl.window"),
    ("Docs: search everything", "Keyword · semantic · hybrid", "docs.search"),
    ("Settings: open", "Asset, costs, CPCV split, wallets", "settings.open"),
]

EXPLAIN = {
    "signal": (
        "rsi  ·  vote −0.62",
        [
            ("What", "Relative Strength Index over 14 five-minute bars, mapped to −1..+1."),
            ("Score", "−0.62: RSI 71 reads overbought, so the metric votes DOWN."),
            ("Weight", "1.00 × regime 1.20 (trend) = 1.20 effective."),
            ("Learned", "Hit 53.1% on 9,812 resolved calls; p(better than a coin flip) 0.99."),
            ("Tuned", "length 14 · upper 70 · lower 30 (adopted v15, 08:10)."),
            ("Caveat", "A vote is not a trade: the composite must clear the cost gate (13 bps)."),
        ],
    ),
    "research": (
        "Median Sharpe (CPCV)",
        [
            ("What", "Median annualised Sharpe across all CPCV test paths, out of sample only."),
            ("Strip", "The rule spans the IQR, the dot is the median, the tick is zero."),
            ("Floor", "Rows under 10 trades are listed, never ranked (KNOW-678)."),
            ("Range", "Typical −4.6 .. +1.4 in committed results."),
        ],
    ),
    "money": (
        "LP net vs holding",
        [
            ("What", "Position value + fees − deposit, minus what holding the tokens would be worth."),
            ("Why", "A pool that earns fees can still lose to simply holding (LVR / IL)."),
            ("Source", "~/.aero-lp/status.json, read only; stale after 180 s."),
        ],
    ),
    "now": (
        "Needs you",
        [
            ("What", "Everything that is stale, failed or unseen, worst first."),
            ("Empty", "An empty list is the goal: it reads “All clear”."),
            ("Act", "Enter jumps to the place that fixes it."),
        ],
    ),
    "library": (
        "Search",
        [
            ("What", "One box over docs, glossary and findings."),
            ("Modes", "keyword · semantic · hybrid; semantic falls back to keyword and says why."),
        ],
    ),
}


# --------------------------------------------------------------------------- shared chrome
DESTINATIONS = [("now", "Now"), ("signal", "Signal"), ("research", "Research"), ("money", "Money"), ("library", "Library")]


class TopBar(Static):
    def show(self, active: str) -> None:
        bar = Text()
        bar.append(" ◆ SolTUI ", f"bold {TOK['bg']} on {TOK['accent']}")
        bar.append("  ")
        for i, (key, label) in enumerate(DESTINATIONS, 1):
            if key == active:
                bar.append(f" {i} {label} ", f"bold {TOK['fg']} on {TOK['panel']} underline")
            else:
                bar.append(f" {i} ", TOK["muted"])
                bar.append(f"{label} ", TOK["fg"])
        bar.append("     ")
        bar.append("SOL ", TOK["muted"])
        bar.append("$74.03 ", f"bold {TOK['fg']}")
        bar.append_text(delta(0.8, "{:+.1f}", "%"))
        bar.append(" 24h", TOK["muted"])
        pad = max(1, 160 - bar.cell_len - 34)
        bar.append(" " * pad)
        bar.append(" READ-ONLY · no order path ", f"{TOK['muted']} on {TOK['panel']}")
        bar.append("  08:15:42 ", TOK["muted"])
        self.update(bar)


class HealthStrip(Static):
    """Every background process, always visible, glyph + label + age."""

    def on_mount(self) -> None:
        sep = Text("   ", TOK["dim"])
        parts = [
            status("run", "Sweep", "412/3286 · eta 3h10"),
            status("run", "Trainers", "5/10"),
            status("ok", "Autopilot", "300 s"),
            status("warn", "LP daemon", "stale 4m"),
            status("ok", "Snapshots", "15m ago"),
            status("idle", "Fwd test", "off"),
            status("ok", "Data", "fresh 08:15"),
        ]
        line = Text(" ")
        for i, part in enumerate(parts):
            if i:
                line.append_text(sep)
            line.append_text(part)
        self.update(line)


class Card(Vertical):
    def __init__(self, title: str, *children, subtitle: str = "", **kwargs) -> None:
        super().__init__(*children, **kwargs)
        self.border_title = title
        if subtitle:
            self.border_subtitle = subtitle


class Tile(Vertical):
    """A stat tile: label, value, change, sparkline. The number is the chart."""

    def __init__(self, label: str, value: str, change: Text, series: list[float], **kwargs) -> None:
        super().__init__(classes="tile", **kwargs)
        self._label, self._value, self._change, self._series = label, value, change, series

    def compose(self) -> ComposeResult:
        yield Static(muted(self._label), classes="tile-label")
        yield Static(Text(self._value, style=f"bold {TOK['fg']}"), classes="tile-value")
        yield Static(self._change, classes="tile-change")
        yield Sparkline(self._series, summary_function=max)


def walk(n: int, start: float, vol: float, seed: int, drift: float = 0.0) -> list[float]:
    rng = random.Random(seed)
    out, x = [], start
    for _ in range(n):
        x *= 1 + rng.gauss(drift, vol)
        out.append(x)
    return out


# --------------------------------------------------------------------------- Now
class NowView(Horizontal):
    def compose(self) -> ComposeResult:
        with Vertical(classes="col"):
            yield Card("Needs you · 3", Static(id="needs"), classes="card needs", subtitle="↵ go to fix")
            yield Card("Signal · next 5m bar · all coins", table("now-coins"), classes="card coins",
                       subtitle="2 Signal for the why")
            yield Card("Activity", Static(id="activity"), classes="card grow")
        with Vertical(classes="col"):
            with Horizontal(classes="tiles"):
                yield Tile("Wallets", "$1,284.20", delta(18.40, "+${:.2f}", " 1h"), walk(42, 1250, 0.004, 1))
                yield Tile("LP · idle", "$87.40 · $45.60", delta(-1.62, "{:+.2f}", " net"), walk(42, 89, 0.006, 2))
                yield Tile("P&L 30d", "−$3.12", delta(-3.12, "{:+.2f}", " USD"), CUM_PNL)
                yield Tile("Sweep", "412 / 3286", Text.assemble(meter(412 / 3286, 10), (" 12.5%", TOK["muted"])), [1, 3, 2, 5, 4, 6, 5, 7, 6, 8])
            yield Card("SOL · 5m · last 6h", PlotextPlot(id="now-chart"), classes="card chart",
                       subtitle="next bar ▼ DOWN −0.31 · costs eat it")
            yield Card("Research · what changed", Static(id="research-sum"), classes="card")

    def on_mount(self) -> None:
        needs = Text()
        items = [
            ("warn", "LP daemon state is 4 min old", "status.json last written 08:11 · daemon may be down", "4 Money › LP"),
            ("err", "HYPE trainer stopped", "28.5% of 5m bars built from incomplete minutes", "2 Signal › HYPE"),
            ("run", "Wallet changed on Solana", "+0.42 SOL since the 07:00 snapshot · unseen", "4 Money › Wallets"),
        ]
        for i, (kind, title, detail, where) in enumerate(items):
            if i:
                needs.append("\n")
            needs.append_text(status(kind, title))
            needs.append(f"   → {where}\n", TOK["accent"])
            needs.append(f"  {detail}", TOK["muted"])
        self.query_one("#needs", Static).update(needs)

        coins = self.query_one("#now-coins", DataTable)
        coins.add_column("Coin", width=4)
        coins.add_column("Call", width=6)
        coins.add_column(Text("◀  lean  ▶", justify="center"), width=13)
        coins.add_column(right("OOS"), width=5)
        coins.add_column(right("Fwd"), width=5)
        coins.add_column("Verdict", width=14)
        coins.add_column("Train", width=6)
        for c in COINS:
            coins.add_row(
                Text(c.sym, style=f"bold {TOK['fg']}"),
                call_text(c.call),
                div_bar(c.composite, 0.5, 6),
                right(f"{c.oos_hit:.1%}"),
                right(f"{c.fwd_hit:.1%}" if c.fwd_hit else "—", TOK["fg"] if c.fwd_hit else TOK["muted"]),
                verdict_text(c.verdict),
                status(c.trainer, {"run": "on", "ok": "idle", "idle": "off", "err": "stop"}[c.trainer]),
            )

        act = Text()
        for i, (ts, kind, msg) in enumerate(ACTIVITY):
            glyph, colour = STATUS[kind]
            if i:
                act.append("\n")
            act.append(f"{ts}  ", TOK["muted"])
            act.append(f"{glyph} ", colour)
            act.append(msg, TOK["fg"])
        self.query_one("#activity", Static).update(act)

        summary = Table.grid(padding=(0, 2))
        summary.add_column(style=TOK["muted"], width=12)
        summary.add_column()
        summary.add_row("Evidence", Text.assemble(("3,286", f"bold {TOK['fg']}"), (" configs · ", TOK["muted"]),
                                                  ("1,212", f"bold {TOK['fg']}"), (" rankable ≥10 trades · ", TOK["muted"]),
                                                  ("665", f"bold {TOK['fg']}"), (" positive · ", TOK["muted"]),
                                                  ("96", f"bold {TOK['fg']}"), (" made money", TOK["muted"])))
        summary.add_row("Best", Text.assemble(("all(dual_momentum+vol_regime) ", TOK["fg"]), ("Sharpe 1.35 · 87% paths +", TOK["muted"])))
        summary.add_row("New today", Text.assemble(("obv_trend_60 ", TOK["fg"]), ("Sharpe 0.77 → ranked #3", TOK["muted"])))
        summary.add_row("Caution", Text("Top pick drops to 0.48 on DOGE: cross-asset check before trusting it", style=TOK["warn"]))
        self.query_one("#research-sum", Static).update(summary)

        plot = self.query_one("#now-chart", PlotextPlot).plt
        prices = walk(72, 74.9, 0.0016, 7, -0.00015)
        prices[-1] = 74.03
        plot.plot(list(range(72)), prices, marker="braille", color=(59, 142, 240))
        vwap = [sum(prices[: i + 1]) / (i + 1) for i in range(72)]
        plot.plot(list(range(72)), vwap, marker="braille", color=(125, 138, 163))
        plot.xticks([0, 24, 48, 71], ["02:15", "04:15", "06:15", "08:15"])
        plot.ylabel("USD")


def verdict_text(verdict: str) -> Text:
    glyph = {"possible edge": "◆", "costs eat it": "◐", "no edge": "○"}[verdict]
    colour = {"possible edge": TOK["accent"], "costs eat it": TOK["muted"], "no edge": TOK["dim"]}[verdict]
    return Text.assemble((f"{glyph} ", colour), (verdict, TOK["fg"] if verdict != "no edge" else TOK["muted"]))


# --------------------------------------------------------------------------- Signal
class SignalView(Horizontal):
    def compose(self) -> ComposeResult:
        yield Card("Coins", table("rail"), classes="card rail", subtitle="↑↓ choose")
        with Vertical(classes="main"):
            with Horizontal(classes="hero"):
                yield Card("Call · next 5m bar", Static(id="hero-call"), classes="card hero-call")
                yield Card("Composite", Digits("-0.31", id="hero-digits"), Static(id="hero-scale"), classes="card hero-comp")
                yield Card("Gates · 8/8 pass", Static(id="hero-gates"), classes="card hero-gates")
                yield Card("Context", Static(id="hero-ctx"), classes="card hero-ctx")
            with Horizontal(classes="mid"):
                yield Card("Why · metric votes, strongest first (18 of 37)", Static(id="votes"), classes="card votes",
                           subtitle="↵ metric detail · ? explain")
                with Vertical(classes="side"):
                    yield Card("Price · 6h · VWAP grey", PlotextPlot(id="sig-chart"), classes="card chart")
                    yield Card("Sizing · research only", Static(id="sizing"), classes="card sizing")
            yield Card("Evidence · does this call pay after costs?", Static(id="evidence"), classes="card evidence")

    def on_mount(self) -> None:
        rail = self.query_one("#rail", DataTable)
        rail.add_column("Coin", width=4)
        rail.add_column("Call", width=6)
        rail.add_column(right("Lean"), width=5)
        for c in COINS:
            rail.add_row(Text(c.sym, style=f"bold {TOK['fg']}"), call_text(c.call), right(f"{c.composite:+.2f}"), key=c.sym)
        self.show(COINS[0])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "rail" and event.row_key.value:
            self.show(next(c for c in COINS if c.sym == event.row_key.value))

    def show(self, c: Coin) -> None:
        hero = Text()
        hero.append_text(call_badge(c.call))
        hero.append("\n")
        hero.append(f"{c.sym} ", f"bold {TOK['fg']}")
        hero.append(f"${c.price:,.4g}  " if c.price < 10 else f"${c.price:,.2f}  ", TOK["fg"])
        hero.append_text(delta(c.chg24, "{:+.1f}", "% 24h"))
        hero.append("\nbar 08:15→08:20 · decided :03", TOK["muted"])
        self.query_one("#hero-call", Static).update(hero)

        self.query_one("#hero-digits", Digits).update(f"{c.composite:+.2f}")
        scale = Text("−1 ", TOK["muted"])
        scale.append_text(div_bar(c.composite, 1.0, 8))
        scale.append(" +1", TOK["muted"])
        self.query_one("#hero-scale", Static).update(scale)

        gates = Table.grid(padding=(0, 2))
        gates.add_column()
        gates.add_column()
        for i in range(0, len(GATES), 2):
            row = []
            for name, _ in GATES[i : i + 2]:
                blocked = name in c.blocked
                row.append(status("err" if blocked else "ok", name, "blocks" if blocked else ""))
            gates.add_row(*row)
        card = self.query_one(".hero-gates", Card)
        card.border_title = f"Gates · {8 - len(c.blocked)}/8 pass"
        self.query_one("#hero-gates", Static).update(gates)

        ctx = kv_table(
            [
                ("Regime", Text(c.regime, style=f"bold {TOK['fg']}")),
                ("Coverage", Text.assemble(meter(0.92, 10), ("  92%", TOK["fg"]))),
                ("Agreement", Text.assemble(meter(0.64, 10), ("  64%", TOK["fg"]))),
                ("Cost", Text("13 bps · 5x", style=TOK["fg"])),
            ],
            key_width=9,
        )
        self.query_one("#hero-ctx", Static).update(ctx)

        rng = random.Random(c.sym)
        rows = []
        for name in METRICS:
            score = max(-1.0, min(1.0, rng.gauss(c.composite * 1.4, 0.45)))
            eff = round(rng.uniform(0.4, 1.4), 2)
            rows.append((name, score, eff, rng.uniform(0.49, 0.545)))
        if c.sym == "SOL":
            rows[0] = ("rsi", -0.62, 1.20, 0.531)
        rows.sort(key=lambda r: abs(r[1] * r[2]), reverse=True)
        votes = Table(box=None, padding=(0, 1), header_style=TOK["muted"], show_edge=False, expand=True)
        votes.add_column("Metric", width=11)
        votes.add_column(Text("◀ DOWN   vote   UP ▶", justify="center"), width=19, justify="center")
        votes.add_column("Score", justify="right", width=6)
        votes.add_column("Weight", justify="right", width=6)
        votes.add_column("Hit", justify="right", width=6)
        votes.add_column("Trust", width=9)
        for name, score, eff, hit in rows[:18]:
            trust = "strong" if hit > 0.525 else "weak" if hit > 0.505 else "coin flip"
            votes.add_row(
                Text(name, style=TOK["fg"]),
                div_bar(score * eff, 1.2),
                f"{score:+.2f}",
                f"{eff:.2f}",
                f"{hit:.1%}",
                Text(trust, style=TOK["fg"] if trust == "strong" else TOK["muted"]),
            )
        folded = Text(f"\n+19 more metrics · net of the rest {c.composite / 4:+.2f} · 3 warming up · 0 errors", style=TOK["muted"])
        self.query_one("#votes", Static).update(Group(votes, folded))

        plot = self.query_one("#sig-chart", PlotextPlot)
        plt = plot.plt
        plt.clear_data()
        prices = walk(72, c.price * 1.012, 0.0016, len(c.sym) * 11, -0.00015 if c.composite < 0 else 0.00015)
        plt.plot(list(range(72)), prices, marker="braille", color=(59, 142, 240))
        vwap = [sum(prices[: i + 1]) / (i + 1) for i in range(72)]
        plt.plot(list(range(72)), vwap, marker="braille", color=(125, 138, 163))
        plt.xticks([0, 36, 71], ["02:15", "05:15", "08:15"])
        plot.refresh()

        sizing = kv_table(
            [
                ("Usable", Text("$45.60 wallet · 1 part", style=TOK["fg"])),
                ("Notional", Text("$228.00 at 5x · collateral $45.60", style=TOK["fg"])),
                ("Stop", Text("1.2% · loss at stop $2.74 (1% risk)", style=TOK["fg"])),
                ("Liquidation", Text.assemble(("long ", TOK["muted"]), ("$59.80", TOK["fg"]), ("  short ", TOK["muted"]), ("$88.30", TOK["fg"]))),
                ("Bound by", Text("risk 1% (not leverage)", style=TOK["fg"])),
                ("", Text("Display only: soltui has no order path.", style=TOK["live"])),
            ],
            key_width=11,
        )
        self.query_one("#sizing", Static).update(sizing)

        ev = Table.grid(padding=(0, 4), expand=True)
        for _ in range(3):
            ev.add_column(ratio=1)
        backtest = kv_table(
            [
                ("Backtest OOS", Text.assemble((f"{c.oos_hit:.1%} hit", f"bold {TOK['fg']}"), (f"  z {c.oos_z:.1f}", TOK["muted"]))),
                ("Gross / call", Text.assemble(("+0.03 bps", TOK["fg"]), ("  cost 13 bps", TOK["muted"]))),
                ("Return", Text.assemble(("−100%", TOK["fg"]), (" · fees 378%", TOK["muted"]))),
            ],
            key_width=13,
        )
        forward = kv_table(
            [
                ("Forward", Text.assemble((f"{c.fwd_hit:.1%} hit" if c.fwd_hit else "no calls yet", f"bold {TOK['fg']}"),
                                          (f"  {c.fwd_calls} resolved" if c.fwd_calls else "", TOK["muted"]))),
                ("Gates off", Text.assemble(("49.6% hit", TOK["fg"]), ("  gates +0.6 pt", TOK["muted"]))),
                ("Net / call", delta(-12.9, "{:+.1f}", " bps")),
            ],
            key_width=13,
        )
        verdict = Text()
        verdict.append_text(verdict_text(c.verdict))
        verdict.append("\nThe call beats a coin flip (z 10.6) but\nthe edge is ~400× smaller than the cost\nof one round trip. Treat as research.", TOK["muted"])
        ev.add_row(backtest, forward, verdict)
        self.query_one("#evidence", Static).update(ev)


# --------------------------------------------------------------------------- Research
SUBVIEWS = ["Leaderboard", "Roster 34", "Sweep ⟳", "Cross-asset", "Decide", "Replay", "Forward", "Bots"]


class ResearchView(Vertical):
    def compose(self) -> ComposeResult:
        yield Static(id="subnav")
        yield Static(id="filters")
        with Horizontal(classes="res-body"):
            yield Card("Leaderboard · ranked by OOS median Sharpe", table("board"),
                       classes="card board", subtitle="space roster · b backtest · p replay · d decide")
            with Vertical(classes="detail"):
                yield Card("#1 all(dual_momentum+vol_regime)", Static(id="detail-card"), classes="card detail-card")
                yield Card("21 CPCV paths · Sharpe distribution", Static(id="paths"), classes="card paths")
                yield Card("Cross-asset · same config", Static(id="xasset"), classes="card xasset")
        yield Card("Background sweep", Static(id="sweep"), classes="card sweep")

    def on_mount(self) -> None:
        nav = Text(" ")
        for i, name in enumerate(SUBVIEWS):
            if i == 0:
                nav.append(f" {name} ", f"bold {TOK['bg']} on {TOK['accent']}")
            else:
                nav.append(f" {name} ", TOK["fg"] if name != "Bots" else TOK["muted"])
            nav.append(" ")
        nav.append("   [ ] switch view", TOK["muted"])
        self.query_one("#subnav", Static).update(nav)

        filt = Text(" ")
        for key, value in [("asset", "SOL"), ("interval", "1d"), ("horizon", "all"), ("family", "all"), ("paths", "21")]:
            filt.append(f"{key} ", TOK["muted"])
            filt.append(f"{value} ▾", f"bold {TOK['fg']}")
            filt.append("   ")
        filt.append("☑ ", TOK["accent"])
        filt.append("show below-floor rows (unranked)", TOK["fg"])
        filt.append("     / filter by name", TOK["muted"])
        self.query_one("#filters", Static).update(filt)

        board = self.query_one("#board", DataTable)
        board.add_column(right("#"), width=2)
        board.add_column("Strategy", width=30)
        board.add_column("Horizon", width=7)
        board.add_column(right("Sharpe"), width=6)
        board.add_column(Text("−2     0     +2", style=TOK["muted"]), width=15)
        board.add_column(right("Paths+"), width=6)
        board.add_column(right("Net"), width=7)
        board.add_column(right("Trades"), width=6)
        for rank, (label, _fam, hor, sh, iqr, pos, net, trades) in enumerate(LEADERBOARD, 1):
            board.add_row(
                right(str(rank), TOK["muted"]),
                Text(label, style=f"bold {TOK['fg']}" if rank <= 3 else TOK["fg"]),
                muted(hor),
                right(f"{sh:+.2f}"),
                range_strip(sh - iqr / 2, sh, sh + iqr / 2, width=15),
                right(f"{pos:.0%}"),
                right(f"{net:+.1f}%"),
                right(str(trades)),
            )
        board.add_row(*(Text("") for _ in range(8)))
        board.add_row(Text(""), Text("under 10 trades · unranked", style=TOK["muted"]), *(Text("") for _ in range(6)))
        for label, _fam, hor, sh, iqr, pos, net, trades in BELOW_FLOOR:
            d = TOK["dim"]
            board.add_row(right("–", d), Text(label, style=d), Text(hor, style=d), right(f"{sh:+.2f}", d),
                          Text(range_strip(sh - iqr / 2, sh, sh + iqr / 2, width=15).plain, style=d), right(f"{pos:.0%}", d),
                          right(f"{net:+.1f}%", d), right(str(trades), d))

        self.query_one("#detail-card", Static).update(
            kv_table(
                [
                    ("Family", Text("combo · long horizon (1d)", style=TOK["fg"])),
                    ("Rule", Text("long only when BOTH members are long", style=TOK["fg"])),
                    ("Members", Text("dual_momentum_24_2 · vol_regime_60_0.5", style=TOK["fg"])),
                    ("Median", Text.assemble(("Sharpe 1.35", f"bold {TOK['fg']}"), ("  IQR 0.79–1.67", TOK["muted"]))),
                    ("Result", Text("+75.1% · 52 trades · 87% paths +", style=TOK["fg"])),
                    ("Costs in", Text("fees 10 · slip 5 bps · borrow .01%/d", style=TOK["muted"])),
                    ("Roster", status("ok", "on roster", "· tested 2026-11-07")),
                ],
                key_width=9,
            )
        )
        path_sharpes = [-0.42, -0.18, -0.05, 0.31, 0.62, 0.79, 0.88, 1.02, 1.15, 1.24, 1.35,
                        1.41, 1.48, 1.55, 1.61, 1.67, 1.74, 1.88, 2.05, 2.21, 2.46]
        edges = [x / 2 for x in range(-2, 7)]
        bins = [sum(1 for v in path_sharpes if lo <= v < lo + 0.5) for lo in edges]
        top, rows = max(bins), 4
        hist = Text()
        for level in range(rows, 0, -1):
            for lo, b in zip(edges, bins):
                filled = b and math.ceil(b / top * rows) >= level
                hist.append(" ██ " if filled else "    ", TOK["up"] if lo >= 0 else TOK["down"])
            hist.append("\n")
        hist.append("".join(f"{x:<4g}" if x == int(x) else "    " for x in edges), TOK["muted"])
        above = sum(1 for v in path_sharpes if v > 0)
        hist.append(f"\n{above} of 21 paths above zero · worst {min(path_sharpes):+.2f} · best {max(path_sharpes):+.2f}", TOK["muted"])
        self.query_one("#paths", Static).update(hist)

        xa = Table(box=None, padding=(0, 1), header_style=TOK["muted"], show_edge=False)
        xa.add_column("Asset", width=6)
        xa.add_column("Sharpe", justify="right", width=6)
        xa.add_column("vs SOL", justify="right", width=8)
        xa.add_column("Paths +", justify="right", width=7)
        xa.add_column("Net", justify="right", width=7)
        xa.add_row(Text("SOL", style=f"bold {TOK['fg']}"), "1.35", "—", "87%", "+75.1%")
        xa.add_row("DOGE", "0.48", delta(-0.87), "60%", "+12.1%")
        xa.add_row("ZEC", "0.71", delta(-0.64), "71%", "+20.4%")
        self.query_one("#xasset", Static).update(Group(xa, Text("\n▲ Edge shrinks off SOL: likely SOL-specific.", style=TOK["warn"])))

        sweep = Table.grid(padding=(0, 3), expand=True)
        sweep.add_column(ratio=2)
        sweep.add_column(ratio=3)
        sweep.add_column(ratio=2)
        sweep.add_row(
            Text.assemble(status("run", "Running", "· low priority"), ("\n", ""), meter(412 / 3286, 22), ("  412 / 3286", TOK["fg"])),
            Text.assemble(("Now  ", TOK["muted"]), ("rsi_revert_14_25_75 · 1h · tier 1 variation", TOK["fg"]),
                          ("\nNext ", TOK["muted"]), ("card presets done · near variations 61% · far 0%", TOK["fg"])),
            Text.assemble(("Missing data  ", TOK["muted"]), ("none", TOK["fg"]), ("\nStop takes effect between jobs", TOK["muted"])),
        )
        self.query_one("#sweep", Static).update(sweep)


# --------------------------------------------------------------------------- Money
class MoneyView(Vertical):
    def compose(self) -> ComposeResult:
        yield Static(id="live-banner")
        with Horizontal(classes="tiles"):
            yield Tile("Wallets · 6 chains", "$1,284.20", delta(18.40, "+${:.2f}", " since 07:00"), walk(42, 1250, 0.004, 1))
            yield Tile("LP deployed", "$87.40", delta(-1.62, "{:+.2f}", " USD net"), walk(42, 89, 0.006, 2))
            yield Tile("LP vs holding", "−$0.80", delta(-0.80, "{:+.2f}", " USD"), cumulative(42, 4, 0.05))
            yield Tile("Idle in LP wallet", "$45.60", Text("unchanged 2d", style=TOK["muted"]), [45.6] * 10)
            yield Tile("P&L 30d · all sources", "−$3.12", delta(-3.12, "{:+.2f}", " · win 46%"), CUM_PNL)
        with Horizontal(classes="money-body"):
            with Vertical(classes="col"):
                yield Card("Aero LP positions", table("lp"), classes="card lp",
                           subtitle="daemon ▲ stale 4m · mode live · not killed · K kill")
                yield Card("Pool scout · modelled, not quoted", table("scout"), classes="card scout")
            with Vertical(classes="col-narrow"):
                yield Card("P&L · daily net · 30d", PlotextPlot(id="pnl-chart"), classes="card chart",
                           subtitle="window 24h 7d [30d] 90d YTD all · source all ▾")
                yield Card("Wallets by chain", table("chains"), classes="card chains",
                           subtitle="s scan · 3 unpriced · 5 airdrops hidden")

    def on_mount(self) -> None:
        banner = Text()
        banner.append(" ◆ LIVE MONEY ", f"bold {TOK['bg']} on {TOK['live']}")
        banner.append("  Real balances, read only. The LP kill switch is the only write on this screen and asks twice.", TOK["live"])
        self.query_one("#live-banner", Static).update(banner)

        lp = self.query_one("#lp", DataTable)
        for label, width in [("Pair", 11), ("Range · price", 14), ("Value", 7), ("P&L", 8), ("vs hold", 8), ("APR", 7), ("Decision", 19)]:
            lp.add_column(right(label) if label in {"Value", "APR"} else label, width=width)
        for pair, lo, hi, px, value, dep, pnl, vs_hold, apr, decision in LP_POSITIONS:
            lp.add_row(
                Text(pair, style=f"bold {TOK['fg']}"),
                range_cell(lo, hi, px),
                right(money(value)),
                delta(pnl, "{:+.2f}"),
                delta(vs_hold, "{:+.2f}"),
                right(f"{apr:+.1f}%"),
                status("warn" if decision.startswith("skip") else "ok", decision),
            )
        lp.add_row(Text("idle", style=TOK["muted"]), Text("undeployed", style=TOK["muted"]), right("$45.60"), "", "", "", "")

        scout = self.query_one("#scout", DataTable)
        for label, width in [("Pool", 11), ("TVL", 6), ("Vol 24h", 7), ("Fee", 5), ("AERO", 5), ("LVR", 5), ("Net APR", 7), ("B/E dep.", 8), ("Conf.", 8)]:
            scout.add_column(label if label in {"Pool", "Conf."} else right(label), width=width)
        for pool, tvl, vol, fee, aero, lvr, net, be, conf, flag in SCOUT:
            scout.add_row(
                Text(pool, style=f"bold {TOK['fg']}"), right(tvl), right(vol), right(f"{fee:.1f}"), right(f"{aero:.1f}"),
                right(f"{lvr:.1f}"), right(f"{net:.1f}%"), right(be),
                status("warn", conf, flag) if flag else Text(conf, style=TOK["fg"] if conf == "high" else TOK["muted"]),
            )

        chains = self.query_one("#chains", DataTable)
        for label, width in [("Chain", 12), ("USD", 9), ("Δ 1h", 8), ("Holdings", 20)]:
            chains.add_column(right(label) if label in {"USD"} else label, width=width)
        for chain, kind, usd, chg, hold in CHAINS:
            chains.add_row(status(kind, chain), right(money(usd)), delta(chg, "{:+.2f}") if chg else muted("─ 0.00"), muted(hold))

        plt = self.query_one("#pnl-chart", PlotextPlot).plt
        daily = DAILY_PNL
        days = list(range(1, 31))
        plt.bar(days, [d if d > 0 else 0 for d in daily], color=(59, 142, 240), width=0.6)
        plt.bar(days, [d if d < 0 else 0 for d in daily], color=(212, 109, 28), width=0.6)
        plt.xticks([1, 10, 20, 30], ["Oct 10", "Oct 19", "Oct 29", "Nov 8"])
        plt.ylabel("USD")


def range_cell(lo: float, hi: float, px: float, width: int = 7) -> Text:
    """Where price sits relative to the LP range: [──●──] inside, ●[────] outside."""
    inside = lo <= px <= hi
    if inside:
        p = round((px - lo) / (hi - lo) * (width - 1))
        bar = "".join("●" if i == p else "─" for i in range(width))
        return Text.assemble(("[", TOK["muted"]), (bar, TOK["fg"]), ("] ", TOK["muted"]), ("in", TOK["fg"]))
    side = "●[" + "─" * width + "]" if px < lo else "[" + "─" * width + "]●"
    return Text.assemble((side, TOK["warn"]), (" out", TOK["warn"]))


# --------------------------------------------------------------------------- Library
class LibraryView(Horizontal):
    def compose(self) -> ComposeResult:
        with Vertical(classes="lib-left"):
            yield Input(value="sharpe", placeholder="Search docs, glossary and findings…", id="lib-search")
            yield Static(id="lib-mode")
            yield Card("Results · 14", Static(id="lib-results"), classes="card grow")
        yield Card("Glossary › Median Sharpe (CPCV)", Static(id="lib-reader"), classes="card reader",
                   subtitle="e edit (docs only) · o open in $EDITOR")

    def on_mount(self) -> None:
        self.query_one("#lib-mode", Static).update(
            Text.assemble((" mode ", TOK["muted"]), (" hybrid ", f"bold {TOK['bg']} on {TOK['accent']}"), ("  keyword  semantic", TOK["muted"]))
        )
        res = Text()
        groups = [
            ("Glossary", ["Median Sharpe (CPCV)", "Sharpe IQR", "Share of paths positive", "Deflated Sharpe"]),
            ("Findings", ["Combos beat single rules on SOL 1d", "Edge does not transfer to DOGE", "Costs dominate 5m calls"]),
            ("Docs", ["docs/COMPOUND-5M.md › Verdicts", "backtester/strategy_cards/obv_trend.md",
                      "docs/CONCEPTS.md › CPCV", "research/README.md › Floors"]),
            ("Strategy cards", ["dual_momentum.md", "vol_regime.md", "hurst_switch.md"]),
        ]
        for i, (group, items) in enumerate(groups):
            if i:
                res.append("\n")
            res.append(f"{group}\n", f"bold {TOK['muted']}")
            for j, item in enumerate(items):
                selected = i == 0 and j == 0
                res.append("▸ " if selected else "  ", TOK["accent"])
                res.append(f"{item}\n", f"bold {TOK['fg']}" if selected else TOK["fg"])
        self.query_one("#lib-results", Static).update(res)

        reader = Text()
        reader.append("Median Sharpe (CPCV)\n\n", f"bold {TOK['fg']}")
        reader.append(
            "Combinatorial purged cross-validation cuts one price history into N groups and tests every "
            "combination of k held-out groups, purging bars that overlap the training set. Each "
            "combination yields one out-of-sample path. The leaderboard reports the median annualised "
            "Sharpe across those paths, because the mean is pulled by one lucky path.\n\n",
            TOK["fg"],
        )
        reader.append("Read it with\n", f"bold {TOK['muted']}")
        reader.append("  · IQR — how much the paths disagree; wide means fragile.\n", TOK["fg"])
        reader.append("  · Paths positive — share of paths above zero.\n", TOK["fg"])
        reader.append("  · Trades — under 10 the row is listed, never ranked.\n\n", TOK["fg"])
        reader.append("Typical range in committed results: −4.6 … +1.4\n", TOK["muted"])
        reader.append("Seen on: Research › Leaderboard, Signal › Evidence, P&L\n", TOK["muted"])
        reader.append("Source: soltui/help.py · backtester/core/cpcv.py", TOK["muted"])
        self.query_one("#lib-reader", Static).update(reader)


# --------------------------------------------------------------------------- palette + app
class RegistryCommands(Provider):
    """The palette is the registry: every action is reachable by name from any screen."""

    def _commands(self) -> list[tuple[str, str, Callable[[], None]]]:
        app = self.app
        assert isinstance(app, SolTUIMockup)
        out: list[tuple[str, str, Callable[[], None]]] = []
        for i, (key, label) in enumerate(DESTINATIONS, 1):
            out.append((f"Go to {label}", f"key {i}", lambda k=key: app.goto(k)))
        for name, help_text, command in PALETTE_COMMANDS:
            out.append((name, f"{help_text}  ·  {command}".strip(" ·"), lambda c=command: app.notify(f"Mockup: would run `{c}`")))
        return out

    async def discover(self) -> Hits:
        for name, help_text, callback in self._commands():
            yield DiscoveryHit(name, callback, help=help_text)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for name, help_text, callback in self._commands():
            score = matcher.match(name)
            if score > 0:
                yield Hit(score, matcher.highlight(name), callback, help=help_text)


class SolTUIMockup(App):
    TITLE = "SolTUI v2 mockup"
    COMMANDS = App.COMMANDS | {RegistryCommands}
    BINDINGS = [
        Binding("1", "goto('now')", "Now"),
        Binding("2", "goto('signal')", "Signal"),
        Binding("3", "goto('research')", "Research"),
        Binding("4", "goto('money')", "Money"),
        Binding("5", "goto('library')", "Library"),
        Binding("ctrl+p", "command_palette", "Commands", show=True),
        Binding("question_mark", "explain", "Explain"),
        Binding("r", "refresh_all", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]
    CSS = """
    Screen { background: $background; layout: vertical; layers: base overlay; }
    TopBar { height: 1; background: $surface; }
    HealthStrip { height: 1; background: $background; color: $muted; border-bottom: hkey $rule; height: 2; }
    ContentSwitcher { height: 1fr; }
    ContentSwitcher > * { height: 1fr; }
    Footer { background: $surface; }

    .card {
        background: $surface;
        border: round $rule;
        border-title-color: $foreground;
        border-title-style: bold;
        border-subtitle-color: $muted;
        padding: 0 1;
        height: auto;
    }
    .card:focus-within { border: round $accent; }
    .grow { height: 1fr; }
    .col { width: 1fr; height: 1fr; }
    .col-narrow { width: 64; height: 1fr; }
    DataTable { background: $surface; height: auto; scrollbar-size-vertical: 1; scrollbar-size-horizontal: 0; }
    DataTable > .datatable--header { background: $surface; color: $muted; text-style: none; }
    DataTable > .datatable--cursor { background: $panel; }
    DataTable:focus > .datatable--cursor { background: $panel-lighten-1; }

    .tiles { height: 7; }
    .tile { width: 1fr; background: $surface; border: round $rule; padding: 0 1; height: 7; }
    .tile-label { height: 1; }
    .tile-value { height: 1; }
    .tile-change { height: 1; }
    Sparkline { height: 2; margin-top: 1; }
    Sparkline > .sparkline--max-color { color: $accent; }
    Sparkline > .sparkline--min-color { color: $dim; }

    PlotextPlot { height: 1fr; min-height: 8; background: $surface; }
    .chart { height: 1fr; }

    /* Now */
    NowView .coins { height: 15; }

    /* Signal */
    .rail { width: 30; height: 1fr; }
    .main { width: 1fr; }
    .hero { height: 8; }
    .hero-call { width: 34; height: 8; }
    .hero-comp { width: 28; height: 8; }
    Digits { width: auto; color: $foreground; }
    .hero-gates { width: 1fr; height: 8; }
    .hero-ctx { width: 34; height: 8; }
    .mid { height: 1fr; }
    .votes { width: 3fr; height: 1fr; }
    .side { width: 2fr; }
    .sizing { height: 10; }
    .evidence { height: 6; }

    /* Research */
    #subnav { height: 1; margin-top: 1; }
    #filters { height: 1; margin: 1 0 0 0; color: $muted; }
    .res-body { height: 1fr; }
    .board { width: 1fr; height: 1fr; }
    .detail { width: 58; }
    .paths { height: 9; }
    .xasset { height: 1fr; }
    .sweep { height: 5; }

    /* Money */
    #live-banner { height: 1; margin-top: 1; }
    .money-body { height: 1fr; }
    .lp { height: 8; }
    .scout { height: 1fr; }
    .chains { height: 11; }

    /* Library */
    .lib-left { width: 2fr; }
    #lib-search { margin-top: 1; border: tall $rule; background: $surface; }
    #lib-mode { height: 1; margin: 0 0 1 1; }
    .reader { width: 3fr; height: 1fr; padding: 1 2; }

    #explain {
        layer: overlay; dock: right; width: 46; height: 1fr; margin: 3 0 1 0; display: none;
        background: $panel; border-left: thick $accent; padding: 1 2;
    }
    #explain.open { display: block; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.register_theme(NIGHT)
        self.theme = NIGHT.name
        self.current = "now"

    def get_theme_variable_defaults(self) -> dict[str, str]:
        return {k: TOK[k] for k in ("up", "down", "live", "muted", "dim", "rule", "idle")}

    def compose(self) -> ComposeResult:
        yield TopBar(id="topbar")
        yield HealthStrip()
        with ContentSwitcher(initial="now", id="switch"):
            yield NowView(id="now")
            yield SignalView(id="signal")
            yield ResearchView(id="research")
            yield MoneyView(id="money")
            yield LibraryView(id="library")
        yield Static(id="explain")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(TopBar).show("now")

    def goto(self, key: str) -> None:
        self.current = key
        self.query_one("#switch", ContentSwitcher).current = key
        self.query_one(TopBar).show(key)
        if self.query_one("#explain").has_class("open"):
            self._fill_explain()

    def action_goto(self, key: str) -> None:
        self.goto(key)

    def action_explain(self) -> None:
        panel = self.query_one("#explain")
        panel.toggle_class("open")
        if panel.has_class("open"):
            self._fill_explain()

    def _fill_explain(self) -> None:
        title, rows = EXPLAIN[self.current]
        body = Text()
        body.append("EXPLAIN  ", f"bold {TOK['accent']}")
        body.append("? closes\n\n", TOK["muted"])
        body.append(f"{title}\n\n", f"bold {TOK['fg']}")
        for key, text in rows:
            body.append(f"{key}\n", f"bold {TOK['muted']}")
            body.append(f"{text}\n\n", TOK["fg"])
        body.append("Full entry: 5 Library › Glossary", TOK["accent"])
        self.query_one("#explain", Static).update(body)

    def action_refresh_all(self) -> None:
        self.notify("Mockup: every view re-reads its source; stale data dims, never blanks.")


# --------------------------------------------------------------------------- screenshots
SHOTS: list[tuple[str, list[str]]] = [
    ("01-now", ["1"]),
    ("02-signal", ["2"]),
    ("03-signal-explain", ["2", "question_mark"]),
    ("04-research", ["3"]),
    ("05-money", ["4"]),
    ("06-library", ["5"]),
    ("07-command-palette", ["1", "ctrl+p", "s", "w", "e", "e", "p"]),
]


async def take_shots(out: Path, size: tuple[int, int]) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for name, keys in SHOTS:
        app = SolTUIMockup()
        async with app.run_test(size=size) as pilot:
            await pilot.pause(0.2)
            for key in keys:
                await pilot.press(key)
                await pilot.pause(0.15)
            await pilot.pause(0.4)
            path = app.save_screenshot(filename=f"{name}.svg", path=str(out))
            print(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--shots", type=Path, help="write one SVG per screen into this directory and exit")
    parser.add_argument("--size", default="160x48", help="terminal size for --shots, COLSxROWS")
    args = parser.parse_args()
    if args.shots:
        cols, rows = (int(x) for x in args.size.lower().split("x"))
        asyncio.run(take_shots(args.shots, (cols, rows)))
    else:
        SolTUIMockup().run()


if __name__ == "__main__":
    main()

"""SolTUI v2 shell: five destinations, the health strip, the Now overview, the palette and Explain.

Design: docs/design/soltui-v2/DESIGN.md. The classic console grouped eighteen peer tabs; this module
groups the same panes by the question the owner brings (does anything need me, what is the call,
what works, what is my money doing, what does this mean). No pane is removed: every classic tab is a
sub-view of exactly one destination, and `COVERED_TABS` is asserted against the live app in the tests.

Presentation only. Every read goes through the command registry (the app's `_call`), exactly as the
CLI, API and extension do, and the builders here are pure functions of those results so they can be
tested without a terminal. Nothing here writes: the palette only runs read-only commands with no
required parameters, and sends every other command to the view whose button owns it, so confirm
steps (the LP resume, for one) stay where they are.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Iterable, Mapping

from rich.text import Text
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.events import Click
from textual.message import Message
from textual.theme import Theme
from textual.widgets import Static

# -- tokens -------------------------------------------------------------------------------------
# One source of colour truth. `up`/`down` is the diverging pair for every signed quantity; it passed
# the dataviz palette validator on the dark surface (CVD dE 28.4). Status colours are reserved for
# system health and always travel with a glyph whose *shape* differs, because green and amber are
# only dE 4.4 apart under protanopia: colour is never the only cue.
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

STATUS: dict[str, tuple[str, str]] = {
    "ok": ("●", TOK["ok"]),
    "run": ("⟳", TOK["accent"]),
    "warn": ("▲", TOK["warn"]),
    "err": ("✖", TOK["err"]),
    "idle": ("◌", TOK["idle"]),
}

CALL: dict[str, tuple[str, str, str]] = {
    "UP": ("▲", "UP", TOK["up"]),
    "DOWN": ("▼", "DOWN", TOK["down"]),
    "FLAT": ("─", "FLAT", TOK["muted"]),
}

THEME_VARIABLES = ("up", "down", "live", "muted", "dim", "rule", "idle")

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
    variables={k: TOK[k] for k in THEME_VARIABLES},
)


def theme_variable_defaults() -> dict[str, str]:
    """CSS parses before a theme can be applied, so the custom variables need defaults."""
    return {k: TOK[k] for k in THEME_VARIABLES}


# -- glyph helpers ------------------------------------------------------------------------------
def status_text(kind: str, label: str, detail: str = "") -> Text:
    glyph, colour = STATUS.get(kind, STATUS["idle"])
    out = Text()
    out.append(f"{glyph} ", colour)
    out.append(label, f"bold {TOK['fg']}")
    if detail:
        out.append(f" {detail}", TOK["muted"])
    return out


def call_badge(call: str, width: int = 14) -> Text:
    """Three rows tall: the call is the answer, so it must outweigh the numbers beside it."""
    glyph, label, colour = CALL.get(call, CALL["FLAT"])
    fill = f"bold {TOK['bg']} on {colour}"
    out = Text()
    out.append(" " * width + "\n", fill)
    out.append(f"{glyph} {label}".center(width) + "\n", fill)
    out.append(" " * width, fill)
    return out


def div_bar(value: float, maxabs: float = 1.0, half: int = 8) -> Text:
    """Diverging bar at half-cell resolution: down grows left of the axis, up grows right."""
    cells = min(half * 2, round(abs(value) / maxabs * half * 2)) if maxabs else 0
    full, part = divmod(cells, 2)
    if value >= 0:
        left, right = " " * half, ("█" * full + ("▌" if part else "")).ljust(half)
    else:
        left, right = (("▐" if part else "") + "█" * full).rjust(half), " " * half
    out = Text()
    out.append(left, TOK["down"])
    out.append("│", TOK["dim"])
    out.append(right, TOK["up"])
    return out


def meter(frac: float, width: int, colour: str = TOK["accent"]) -> Text:
    n = max(0, min(width, round(frac * width)))
    out = Text()
    out.append("━" * n, colour)
    out.append("━" * (width - n), TOK["dim"])
    return out


def fmt_age(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "?"
    if seconds < 90:
        return f"{seconds:.0f}s"
    if seconds < 5400:
        return f"{seconds / 60:.0f}m"
    if seconds < 172800:
        return f"{seconds / 3600:.0f}h"
    return f"{seconds / 86400:.0f}d"


def _num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None  # NaN reads as missing, never as a number


# -- navigation model ---------------------------------------------------------------------------
@dataclass(frozen=True)
class View:
    """One sub-view: a classic tab pane, optionally one section inside it."""

    tab: str
    label: str
    inner: str | None = None
    was: str = ""  # the classic tab name, so the palette still finds "Queue" after it became "Sweep"

    @property
    def key(self) -> str:
        return f"{self.tab}/{self.inner}" if self.inner else self.tab


@dataclass(frozen=True)
class Destination:
    key: str
    label: str
    hotkey: str
    question: str
    views: tuple[View, ...]
    live_money: bool = False


DESTINATIONS: tuple[Destination, ...] = (
    Destination("now", "Now", "1", "Does anything need me?", (View("tab-now", "Overview"),)),
    Destination("signal", "Signal", "2", "What is the next 5m call, why, and does it pay after costs?", (
        View("tab-compound", "Call & metrics", "cmp-call", "Compound 5m"),
        View("tab-compound", "Backtest", "cmp-backtest", "Compound 5m"),
        View("tab-compound", "Forward test", "cmp-forward", "Compound 5m"),
        View("tab-compound", "All coins", "cmp-coins", "Compound 5m"),
    )),
    Destination("research", "Research", "3", "Which strategies actually work, and how sure are we?", (
        View("tab-backtest", "Backtest"),
        View("tab-strategies", "Strategies"),
        View("tab-queue", "Sweep", was="Queue"),
        View("tab-cumulative", "Cumulative"),
        View("tab-top5", "Top 5"),
        View("tab-analyze", "Decide", was="Analyze"),
        View("tab-forwardtest", "Forward", was="Forwardtest"),
        View("tab-paper-experiments", "Experiments"),
        View("tab-bots", "Bots"),
        View("tab-execute", "Replay", was="Execute"),
        View("tab-liverun", "Dry run", was="Live Run"),
        View("tab-signals", "Indicators", was="Signals"),
    )),
    Destination("money", "Money", "4", "What is my real money doing?", (
        View("tab-pnl", "P&L"),
        View("tab-wallet", "Wallet"),
        View("tab-advanced-order", "Advanced order"),
    ), live_money=True),
    Destination("library", "Library", "5", "What does this word or number mean?", (
        View("tab-docs", "Docs"),
        View("tab-research", "Findings", was="Research"),
    )),
    Destination("archive", "Archive", "6", "What was retired?", (
        View("tab-liquidity", "Aero LP", was="Liquidity"),
    ), live_money=True),
    Destination("settings", "Settings", ",", "What data, costs and wallets does the research use?", (
        View("tab-settings", "Settings"),
    )),
)

DEST_BY_KEY: dict[str, Destination] = {d.key: d for d in DESTINATIONS}
COVERED_TABS: frozenset[str] = frozenset(v.tab for d in DESTINATIONS for v in d.views)

# Registry command prefix -> the classic tab that owns its controls. Used when no button maps a
# command directly (BUTTON_COMMANDS in tui.py is checked first).
COMMAND_HOME: dict[str, str] = {
    "settings": "tab-settings", "strategies": "tab-strategies", "roster": "tab-strategies",
    "paper_experiment": "tab-paper-experiments", "forwardtest": "tab-forwardtest", "signals": "tab-signals", "research": "tab-research",
    "backtest": "tab-backtest", "paper": "tab-execute", "live": "tab-liverun", "top5": "tab-top5",
    "analyze": "tab-analyze", "cumulative": "tab-cumulative", "queue": "tab-queue",
    "compound": "tab-compound", "liquidity": "tab-liquidity", "docs": "tab-docs", "pnl": "tab-pnl",
    "wallet": "tab-wallet", "portfolio": "tab-wallet", "bots": "tab-bots", "prices": "tab-bots",
}


def with_extra_views(panes: Iterable[tuple[str, str]],
                     base: tuple[Destination, ...] = DESTINATIONS) -> tuple[Destination, ...]:
    """Append panes this map does not know to Research, so a tab added later is never unreachable.

    Other work adds tabs to the classic TabbedContent (a new pane only needs a TabPane there); this
    keeps such a pane on the sub-view row under its own title until someone files it properly.
    """
    known = {v.tab for d in base for v in d.views}
    extra = tuple(View(tab, label, was=label) for tab, label in panes if tab not in known)
    if not extra:
        return base
    return tuple(replace(d, views=d.views + extra) if d.key == "research" else d for d in base)


def locate(tab: str, inner: str | None = None,
           dests: tuple[Destination, ...] = DESTINATIONS) -> tuple[Destination, int] | None:
    """The destination and view index that show `tab` (and its `inner` section when given)."""
    pairs = [(d, i, v) for d in dests for i, v in enumerate(d.views) if v.tab == tab]
    exact = next(((d, i) for d, i, v in pairs if v.inner == inner), None)
    return exact or (next(((d, i) for d, i, _ in pairs), None))


# -- clickable segment bar ----------------------------------------------------------------------
class SegmentBar(Static):
    """One line of clickable segments (destinations or sub-views).

    A single Static re-rendered in place, not a row of child widgets: re-rendering is synchronous,
    so the bar can never show a half-mounted state after a fast key press.
    """

    class Selected(Message):
        def __init__(self, bar: "SegmentBar", segment: str) -> None:
            super().__init__()
            self.bar = bar
            self.segment = segment

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("", *args, **kwargs)
        self._ranges: list[tuple[int, int, str]] = []

    def set_segments(self, segments: Iterable[tuple[Text | str, str | None]]) -> None:
        line, ranges = Text(), []
        for piece, target in segments:
            piece = piece if isinstance(piece, Text) else Text(piece)
            start = line.cell_len
            line.append_text(piece)
            if target:
                ranges.append((start, line.cell_len, target))
        self._ranges = ranges
        self.update(line)

    def target_at(self, x: int) -> str | None:
        return next((t for s, e, t in self._ranges if s <= x < e), None)

    def on_click(self, event: Click) -> None:
        target = self.target_at(event.x)
        if target:
            event.stop()
            self.post_message(self.Selected(self, target))


def topbar_segments(active: str, price: str, mode: str, clock: str,
                    width: int) -> list[tuple[Text | str, str | None]]:
    segs: list[tuple[Text | str, str | None]] = [
        (Text(" ◆ SolTUI ", f"bold {TOK['bg']} on {TOK['accent']}"), "dest:now"), ("  ", None)]
    for dest in DESTINATIONS:
        if dest.key == "settings":
            continue
        if dest.key == active:
            segs.append((Text(f" {dest.hotkey} {dest.label} ", f"bold {TOK['fg']} on {TOK['panel']} underline"),
                         f"dest:{dest.key}"))
        else:
            seg = Text()
            seg.append(f" {dest.hotkey} ", TOK["muted"])
            seg.append(f"{dest.label} ", TOK["fg"])
            segs.append((seg, f"dest:{dest.key}"))
    gear_style = f"bold {TOK['fg']} on {TOK['panel']}" if active == "settings" else TOK["muted"]
    segs.append((Text(" ⚙ Settings , ", gear_style), "dest:settings"))
    right = Text()
    if price:
        right.append("   ")
        right.append(price, TOK["fg"])
    right.append("   ")
    right.append(f" {mode} ", f"{TOK['muted']} on {TOK['panel']}")
    right.append(f"  {clock} ", TOK["muted"])
    used = sum((s if isinstance(s, Text) else Text(s)).cell_len for s, _ in segs) + right.cell_len
    if used > width:
        # Price and clock are secondary to the navigation and the no-order-path guarantee.
        segs = [(Text(" ◆ ", f"bold {TOK['accent']}"), "dest:now")]
        compact_mode = mode.replace(" only", "").replace("no live order path", "no order path")
        right = Text(f" {compact_mode} ", f"{TOK['muted']} on {TOK['panel']}")
        destinations = [d for d in DESTINATIONS if d.key != "settings"]
        full_width = sum(len(d.hotkey) + len(d.label) + 2 for d in destinations) + 6 + right.cell_len
        for dest in destinations:
            label = dest.label if full_width <= width else dest.label[:3]
            style = f"bold {TOK['fg']} on {TOK['panel']} underline" if dest.key == active else TOK['fg']
            segs.append((Text(f"{dest.hotkey} {label} ", style), f"dest:{dest.key}"))
        segs.append((Text(" , ", gear_style), "dest:settings"))
        used = sum((s if isinstance(s, Text) else Text(s)).cell_len for s, _ in segs) + right.cell_len
    segs.append((" " * max(0, width - used), None))
    segs.append((right, None))
    return segs


def subnav_segments(dest: Destination, index: int,
                    width: int | None = None) -> list[tuple[Text | str, str | None]]:
    segs: list[tuple[Text | str, str | None]] = [(Text(f" {dest.label} ", f"bold {TOK['accent']}"), None),
                                                  (Text("› ", TOK["muted"]), None)]
    for i, view in enumerate(dest.views):
        style = f"bold {TOK['bg']} on {TOK['accent']}" if i == index else TOK["fg"]
        segs.append((Text(f" {view.label} ", style), f"view:{i}"))
        segs.append((" ", None))
    if len(dest.views) > 1:
        segs.append((Text("  [ ] switch", TOK["muted"]), None))
    if width is not None and sum((s if isinstance(s, Text) else Text(s)).cell_len for s, _ in segs) > width:
        # A clipped selected label makes a successful keyboard move look like it failed.
        count = len(dest.views)
        segs = segs[:2] + [
            (Text(" ‹ ", TOK["accent"]), f"view:{(index - 1) % count}"),
            (Text(f" {dest.views[index].label} ", f"bold {TOK['bg']} on {TOK['accent']}"), f"view:{index}"),
            (Text(" › ", TOK["accent"]), f"view:{(index + 1) % count}"),
            (Text(f"  {index + 1}/{count} · [ ] switch", TOK["muted"]), None),
        ]
    return segs


# -- health -------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Health:
    kind: str
    label: str
    detail: str
    tab: str | None = None
    inner: str | None = None


def _ok(env: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not env or not env.get("ok"):
        return None
    result = env.get("result")
    return result if isinstance(result, dict) else None


def health_items(reads: Mapping[str, Mapping[str, Any] | None], *, forward_running: bool = False,
                 autopilot: Mapping[str, Any] | None = None, now: float | None = None) -> list[Health]:
    """Every background process as glyph + name + one fact. `reads` maps command -> envelope."""
    now = time.time() if now is None else now
    out: list[Health] = []

    bt = _ok(reads.get("backtest.status"))
    if bt and bt.get("running"):
        out.append(Health("run", "Backtest", f"{bt.get('done', 0)}/{bt.get('total', 0)}", "tab-backtest"))

    q = _ok(reads.get("queue.progress"))
    if q is not None:
        state = q.get("state") or {}
        phase, alive = str(state.get("phase") or "idle"), bool(q.get("alive"))
        done, total = state.get("done") or 0, state.get("total") or 0
        if phase == "running" and alive:
            out.append(Health("run", "Sweep", f"{done}/{total}", "tab-queue"))
        elif phase == "running":
            out.append(Health("warn", "Sweep", "stopped unexpectedly", "tab-queue"))
        elif phase == "error":
            out.append(Health("err", "Sweep", "error", "tab-queue"))
        elif phase == "done":
            out.append(Health("ok", "Sweep", f"done {done}/{total}", "tab-queue"))
        else:
            out.append(Health("idle", "Sweep", phase, "tab-queue"))

    if autopilot is not None:
        live, running = list(autopilot.get("live_coins") or []), list(autopilot.get("running") or [])
        stopped = [c for c in live if c not in running]
        kind = "err" if stopped else ("run" if running else "idle")
        out.append(Health(kind, "Trainers", f"{len(running)}/{len(live)}", "tab-compound", "cmp-coins"))
        out.append(Health("ok" if autopilot.get("autopilot") else "idle", "Autopilot",
                          "on" if autopilot.get("autopilot") else "off", "tab-compound", "cmp-coins"))

    pr = _ok(reads.get("prices.status"))
    if pr is not None:
        age = _num(pr.get("snapshot_age_s"))
        if not pr.get("running"):
            out.append(Health("idle", "Prices", "off", "tab-bots"))
        elif age is not None and age > 60:
            out.append(Health("warn", "Prices", f"stale {fmt_age(age)}", "tab-bots"))
        else:
            out.append(Health("ok", "Prices", "live", "tab-bots"))

    out.append(Health("run" if forward_running else "idle", "Fwd test", "on" if forward_running else "off",
                      "tab-forwardtest"))

    last = _ok(reads.get("portfolio.last"))
    if last is not None:
        saved = _num(last.get("saved_at"))
        result = last.get("result") or {}
        if saved is None:
            out.append(Health("idle", "Wallet", "never scanned", "tab-wallet"))
        else:
            age = now - saved
            partial = bool(result.get("partial"))
            kind = "warn" if partial or age > 7200 else "ok"
            out.append(Health(kind, "Wallet", f"{'partial · ' if partial else ''}{fmt_age(age)} ago", "tab-wallet"))
    return out


def health_text(items: Iterable[Health]) -> Text:
    line = Text(" ")
    for i, item in enumerate(items):
        if i:
            line.append("   ", TOK["dim"])
        line.append_text(status_text(item.kind, item.label, item.detail))
    return line


# -- Now ----------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Need:
    kind: str
    title: str
    detail: str
    tab: str
    inner: str | None = None

    @property
    def where(self) -> str:
        found = locate(self.tab, self.inner)
        if not found:
            return ""
        dest, i = found
        return f"{dest.hotkey} {dest.label} › {dest.views[i].label}"


_SEVERITY = {"err": 0, "warn": 1, "run": 2, "idle": 3, "ok": 4}


def needs(reads: Mapping[str, Mapping[str, Any] | None], *, autopilot: Mapping[str, Any] | None = None,
          notice: Mapping[str, Any] | None = None, now: float | None = None) -> list[Need]:
    """Everything stale, failed or unseen, worst first. An empty list is the goal."""
    now = time.time() if now is None else now
    out: list[Need] = []

    q = _ok(reads.get("queue.progress"))
    if q is not None:
        state = q.get("state") or {}
        phase = state.get("phase")
        if phase == "error":
            out.append(Need("err", "Background sweep stopped with an error",
                            str(state.get("error") or q.get("summary") or "see the Sweep view")[:160], "tab-queue"))
        elif phase == "running" and not q.get("alive"):
            out.append(Need("warn", "Background sweep stopped unexpectedly",
                            "its worker process is gone; press Start to resume", "tab-queue"))
    qs = _ok(reads.get("queue.status"))
    missing = (qs or {}).get("missing") or []
    if missing:
        names = ", ".join(f"{m.get('asset')} {m.get('interval')}" for m in missing[:4])
        out.append(Need("warn", f"{len(missing)} price series missing for the sweep", names, "tab-queue"))

    bt = _ok(reads.get("backtest.status"))
    if bt and bt.get("error"):
        out.append(Need("err", "Last backtest failed", str(bt["error"])[:160], "tab-backtest"))

    if autopilot is not None:
        live, running = list(autopilot.get("live_coins") or []), set(autopilot.get("running") or [])
        stopped = [c for c in live if c not in running]
        if autopilot.get("autopilot") and stopped:
            out.append(Need("err", f"Trainer stopped: {', '.join(stopped[:6])}",
                            "autopilot wants these coins training; the launch agent restarts them every 300 s",
                            "tab-compound", "cmp-coins"))
        agent = autopilot.get("agent") or {}
        if autopilot.get("autopilot") and agent and not agent.get("loaded"):
            out.append(Need("warn", "Autopilot launch agent is not loaded",
                            str(agent.get("label") or "compound autopilot"), "tab-compound", "cmp-coins"))

    pr = _ok(reads.get("prices.status"))
    if pr is not None:
        age = _num(pr.get("snapshot_age_s"))
        if not pr.get("running"):
            out.append(Need("warn", "Price recorder is not running",
                            "bot forward tests have no live prices", "tab-bots"))
        elif age is not None and age > 60:
            out.append(Need("warn", f"Price stream is {fmt_age(age)} old",
                            str(pr.get("last_error") or "no new snapshot")[:160], "tab-bots"))

    last = _ok(reads.get("portfolio.last"))
    if last is not None:
        result = last.get("result") or {}
        if result.get("partial"):
            out.append(Need("warn", "Last wallet scan was partial",
                            "some chains could not be read; totals exclude them", "tab-wallet"))
    if notice and notice.get("changed"):
        out.append(Need("run", "Wallet changed since your last look",
                        str(notice.get("line") or f"{notice.get('changes', 0)} change(s)")[:160], "tab-wallet"))

    out.sort(key=lambda n: _SEVERITY.get(n.kind, 9))
    return out


def need_prompt(need: Need) -> Text:
    out = status_text(need.kind, need.title)
    if need.where:
        out.append(f"   → {need.where}", TOK["accent"])
    if need.detail:
        out.append(f"\n  {need.detail}", TOK["muted"])
    return out


def tiles(reads: Mapping[str, Mapping[str, Any] | None], *, forward: Mapping[str, Any] | None = None,
          now: float | None = None) -> list[tuple[str, Text, Text]]:
    """Stat tiles: one number each, the fact that qualifies it, and nothing summed across sources."""
    now = time.time() if now is None else now
    out: list[tuple[str, Text, Text]] = []

    last = _ok(reads.get("portfolio.last"))
    if last is not None and last.get("result"):
        result = last["result"]
        total = _num(result.get("total_usd"))
        value = Text(f"${total:,.2f}" if total is not None else "—", f"bold {TOK['fg']}")
        bits = [f"{len(result.get('chains') or {})} chains"]
        if result.get("partial"):
            bits.append("partial")
        saved = _num(last.get("saved_at"))
        if saved is not None:
            bits.append(f"{fmt_age(now - saved)} ago")
        out.append(("Wallets", value, Text(" · ".join(bits), TOK["muted"])))
    else:
        out.append(("Wallets", Text("—", f"bold {TOK['fg']}"), Text("no scan yet", TOK["muted"])))

    q = _ok(reads.get("queue.progress"))
    if q is not None:
        state = q.get("state") or {}
        done, total = state.get("done") or 0, state.get("total") or 0
        frac = done / total if total else 0.0
        value = Text(f"{done} / {total}" if total else str(state.get("phase") or "idle"), f"bold {TOK['fg']}")
        out.append(("Sweep", value, meter(frac, 12)))

    if forward:
        comp = forward.get("compound") or {}
        hit, z = _num(comp.get("hit_rate")), _num(comp.get("z_vs_coinflip"))
        net = _num(comp.get("net_bps_per_call_if_one_bar"))
        value = Text(f"{hit:.1%} hit" if hit is not None else "no calls", f"bold {TOK['fg']}")
        sub = Text()
        if z is not None:
            sub.append(f"z {z:+.2f} · ", TOK["muted"])
        if net is not None:
            glyph, colour = ("▲", TOK["up"]) if net > 0 else ("▼", TOK["down"])
            sub.append(f"{glyph} ", colour)
            sub.append(f"{net:+.1f} bps/call net", TOK["fg"])
        out.append((f"{forward.get('asset', 'SOL')} forward test", value, sub))
    return out


def activity(autopilot: Mapping[str, Any] | None, reads: Mapping[str, Mapping[str, Any] | None],
             *, limit: int = 8) -> list[tuple[float, str, str]]:
    """Recent dated events from the sources that record a time; newest first."""
    events: list[tuple[float, str, str]] = []
    for a in (autopilot or {}).get("adoptions") or []:
        ts = _num(a.get("ts"))
        if ts:
            events.append((ts, "ok", f"Autopilot adopted tuned {a.get('metric', '?')} for {a.get('asset', '?')}"))
    last = _ok(reads.get("portfolio.last"))
    if last and _num(last.get("saved_at")):
        total = _num((last.get("result") or {}).get("total_usd"))
        events.append((float(last["saved_at"]), "ok",
                       "Wallet scan saved" + (f" · ${total:,.2f}" if total is not None else "")))
    qs = _ok(reads.get("queue.status"))
    for row in ((qs or {}).get("ranked") or [])[:50]:
        ts = _num(row.get("finished_at"))
        if ts:
            sharpe = _num(row.get("median_sharpe"))
            events.append((ts, "ok", f"Sweep finished {row.get('strategy', '?')} · {row.get('asset', '')} "
                                     f"{row.get('interval', '')}" + (f" · Sharpe {sharpe:+.2f}" if sharpe is not None else "")))
    q = _ok(reads.get("queue.progress"))
    state = (q or {}).get("state") or {}
    if state.get("phase") == "error" and _num(state.get("updated_at")):
        events.append((float(state["updated_at"]), "err", f"Sweep error: {str(state.get('error') or '')[:90]}"))
    events.sort(key=lambda e: e[0], reverse=True)
    return events[:limit]


def activity_text(events: Iterable[tuple[float, str, str]]) -> Text:
    out = Text()
    for i, (ts, kind, msg) in enumerate(events):
        glyph, colour = STATUS.get(kind, STATUS["idle"])
        if i:
            out.append("\n")
        out.append(time.strftime("%m-%d %H:%M  ", time.localtime(ts)), TOK["muted"])
        out.append(f"{glyph} ", colour)
        out.append(msg, TOK["fg"])
    if not out.plain:
        out.append("No dated events yet.", TOK["muted"])
    return out


def price_line(reads: Mapping[str, Mapping[str, Any] | None], products: tuple[str, ...] = ("SOL-USD",)) -> str:
    pr = _ok(reads.get("prices.status"))
    prices = (pr or {}).get("prices") or {}
    bits = []
    for product in products:
        quote = prices.get(product) or {}
        mid = _num(quote.get("mid")) or _num(quote.get("last"))
        if mid is not None:
            bits.append(f"{product.split('-')[0]} ${mid:,.2f}")
    return "  ".join(bits)


# -- Signal hero --------------------------------------------------------------------------------
def signal_hero(r: Mapping[str, Any]) -> Text:
    """The call first, its strength next, then what could veto it: the order a decision is made in."""
    call = str(r.get("call") or "FLAT").upper()
    out = call_badge(call)
    composite = _num(r.get("composite"))
    out.append("   ")
    if composite is not None:
        out.append(f"composite {composite:+.2f}  ", f"bold {TOK['fg']}")
        out.append_text(div_bar(composite, 1.0, 8))
    blocked = list(r.get("blocked_by") or [])
    gates = [row for row in (r.get("components") or []) if row.get("kind") == "gate" and row.get("enabled")]
    out.append("\n")
    out.append(" " * 17)
    if gates:
        passed = sum(1 for g in gates if not g.get("blocked"))
        out.append_text(status_text("err" if blocked else "ok", f"gates {passed}/{len(gates)} pass",
                                    ("blocked by " + ", ".join(blocked)) if blocked else ""))
    else:
        out.append_text(status_text("err" if blocked else "ok", "gates",
                                    ("blocked by " + ", ".join(blocked)) if blocked else "none blocking"))
    out.append("\n")
    out.append(" " * 17)
    bits = [f"{k} {r.get(k)}" for k in ("coverage", "agreement", "regime", "trend_stage") if r.get(k) is not None]
    if r.get("round_trip_bps") is not None:
        bits.append(f"round trip {r['round_trip_bps']} bps")
    out.append(" · ".join(bits), TOK["muted"])
    return out


# -- palette ------------------------------------------------------------------------------------
@dataclass
class PaletteEntry:
    name: str
    help: str
    run: Callable[[], Any]
    group: str = field(default="")


class SolCommands(Provider):
    """The palette is the registry: every destination, every view and every command by name.

    The app supplies the entries (`v2_palette_entries`) because only it knows which button owns a
    command and which pane holds that button.
    """

    def _entries(self) -> list[PaletteEntry]:
        builder = getattr(self.app, "v2_palette_entries", None)
        return list(builder()) if builder else []

    async def discover(self) -> Hits:
        for entry in self._entries():
            if entry.group in ("go", "action"):
                yield DiscoveryHit(entry.name, entry.run, help=entry.help)

    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        for entry in self._entries():
            score = max(matcher.match(entry.name), matcher.match(entry.help) * 0.6)
            if score > 0:
                yield Hit(score, matcher.highlight(entry.name), entry.run, help=entry.help)


def summarise(result: Any, limit: int = 220) -> str:
    """A one-line toast for a read-only command's result; the full result stays in its view."""
    if isinstance(result, dict):
        for key in ("summary", "title", "line", "message"):
            if isinstance(result.get(key), str) and result[key]:
                return result[key][:limit]
        parts = []
        for key, value in result.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                parts.append(f"{key}={value}")
            elif isinstance(value, (list, dict)):
                parts.append(f"{key}: {len(value)}")
            if len(", ".join(parts)) > limit:
                break
        return ", ".join(parts)[:limit]
    if isinstance(result, list):
        return f"{len(result)} item(s)"
    return str(result)[:limit]


# -- Explain ------------------------------------------------------------------------------------
def explain_text(title: str, body: str) -> Text:
    out = Text()
    out.append("EXPLAIN  ", f"bold {TOK['accent']}")
    out.append("? closes · F1 searchable glossary\n\n", TOK["muted"])
    out.append(f"{title}\n\n", f"bold {TOK['fg']}")
    out.append(body or "No explanation is recorded for this field yet. F1 opens the searchable glossary.",
               TOK["fg"])
    return out

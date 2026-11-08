"""Profit and loss over a variable window: the maths behind the P&L tab.

Pure functions over plain data, so every figure can be checked with a fixture and no event loop,
network or price file. The adapters at the bottom turn the real sources (backtest runs, a paper
replay, the extension's dry-run journal, the liquidity daemon's files) into the same two shapes:

* `Curve`: equity sampled over time, plus the fills that moved it;
* nothing else. The wallet scan has no P&L and lives in `wallet.py`.

## Rules this module keeps

* **Simulated and real money are never added together.** Every curve carries a `source`. Sections
  are built per source and `GROUPS` says which are simulated and which are real; no function here
  sums across sources, and the report has no grand total.
* **Every figure names its source.** A section's `label` and each percentage text carry the word
  (`backtest`, `paper`, `dry-run`, `live LP`).
* **Net % is `final / initial - 1`**, where *initial* is the equity at the start of the window
  (the last point before it, else the curve's starting capital). No base, no percentage: None.
* **Window edges are inclusive.** A point at exactly `start` or `end` is in the window. A custom
  `end` given as a date covers that whole UTC day. The P&L of the first day is measured against the
  equity before the window, so the days always add up to the window's net P&L.
* **Costs.** Gross P&L is net P&L plus the fees, slippage and borrow paid inside the window. Realized
  P&L is the sum of the net result of fills that closed risk in the window; unrealized is the rest
  (the mark on what is still open, net of the entry costs already paid on it).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

from .netpct import labelled, net_pct

UTC = timezone.utc
DAY_S = 86400.0

PRESETS = ("24h", "7d", "30d", "90d", "ytd", "all")
DEFAULT_PRESET = "30d"
_PRESET_SECONDS = {"24h": 86400.0, "7d": 7 * 86400.0, "30d": 30 * 86400.0, "90d": 90 * 86400.0}

SOURCES = ("backtest", "paper", "dry-run", "dry-run LP", "live LP", "reported LP", "wallet (live)")
# Which sources are simulations and which are real money. A dry-run liquidity daemon is simulated;
# the adapter picks the source word from the daemon's own mode, and `group_of` follows it.
GROUPS = {"backtest": "simulated", "paper": "simulated", "dry-run": "simulated",
          "dry-run LP": "simulated", "live LP": "real", "reported LP": "unclassified",
          "wallet (live)": "real"}
SOURCE_ALIASES = {"live-lp": "live LP", "live_lp": "live LP", "live lp": "live LP",
                  "dry-run-lp": "dry-run LP", "dry_run_lp": "dry-run LP", "lp": "live LP",
                  "wallet": "wallet (live)", "wallet-live": "wallet (live)"}

NOTICE = ("Simulated and real money are never summed: backtest, paper and dry-run figures are "
          "simulations; live LP and the wallet scan are real. Each section is its own number.")

LP_WORDS = {"live": "live LP", "dry-run": "dry-run LP"}


class PnlError(ValueError):
    """A window or source the caller named cannot be used."""


# -- window ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Window:
    """A closed interval of epoch seconds. `None` on a side means unbounded."""

    label: str
    start: float | None = None
    end: float | None = None

    def contains(self, ts: float) -> bool:
        return (self.start is None or ts >= self.start) and (self.end is None or ts <= self.end)

    def before(self, ts: float) -> bool:
        """True when `ts` lies strictly before the window starts."""
        return self.start is not None and ts < self.start

    def to_dict(self) -> dict[str, Any]:
        return {"label": self.label, "start": iso(self.start), "end": iso(self.end),
                "days": None if self.start is None or self.end is None
                else round((self.end - self.start) / DAY_S, 4)}


ALL = Window("all")


def iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, UTC).isoformat(timespec="seconds")


def parse_moment(text: str, *, end_of_day: bool = False) -> float:
    """Epoch seconds for `YYYY-MM-DD` or `YYYY-MM-DD[ T]HH:MM[:SS]`, always UTC.

    A date alone is the start of that day, or with `end_of_day` the last instant of it, so a custom
    window `2026-01-01 .. 2026-01-31` covers all of January 31.
    """
    raw = (text or "").strip().replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC).timestamp()
        except ValueError:
            continue
    try:
        day = datetime.strptime(raw, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
    except ValueError:
        raise PnlError(f"could not read {text!r} as a UTC date (YYYY-MM-DD) or time "
                       "(YYYY-MM-DD HH:MM)") from None
    return day + DAY_S - 1e-6 if end_of_day else day


def resolve_window(preset: str | None = None, start: str | None = None, end: str | None = None,
                   now: float | None = None) -> Window:
    """The window a request names. `start`/`end` (custom) win over `preset`.

    24h, 7d, 30d and 90d end now and reach back that long; ytd starts at 00:00 UTC on 1 January of
    the current year; all is unbounded. Custom needs at least one of start/end; a missing side is
    open.
    """
    now = datetime.now(UTC).timestamp() if now is None else now
    if start or end:
        s = parse_moment(start) if start else None
        e = parse_moment(end, end_of_day=True) if end else None
        if s is not None and e is not None and s > e:
            raise PnlError("custom window starts after it ends")
        return Window("custom", s, e)
    name = (preset or DEFAULT_PRESET).strip().lower()
    if name == "custom":
        raise PnlError("a custom window needs start and/or end (YYYY-MM-DD)")
    if name == "all":
        return Window("all", None, None)
    if name == "ytd":
        year = datetime.fromtimestamp(now, UTC).year
        return Window("ytd", datetime(year, 1, 1, tzinfo=UTC).timestamp(), now)
    if name in _PRESET_SECONDS:
        return Window(name, now - _PRESET_SECONDS[name], now)
    raise PnlError(f"unknown window {preset!r}; use one of {', '.join(PRESETS)} or give start/end")


def normalise_source(source: str | None) -> str | None:
    """`None` for all sources, else the canonical source word."""
    if source is None or str(source).strip().lower() in ("", "all"):
        return None
    raw = str(source).strip()
    canon = SOURCE_ALIASES.get(raw.lower(), raw)
    for s in SOURCES:
        if s.lower() == canon.lower():
            return s
    raise PnlError(f"unknown source {source!r}; use all or one of {', '.join(SOURCES)}")


# -- inputs ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Fill:
    """One execution. `realized` is the net result when it closed risk, else None (an opening fill)."""

    ts: float
    fee: float = 0.0
    slippage: float = 0.0
    borrow: float = 0.0
    realized: float | None = None

    @property
    def cost(self) -> float:
        return self.fee + self.slippage + self.borrow


@dataclass
class Curve:
    """Equity over time for one run of one strategy on one asset, from one source.

    `initial` is the equity before the first point (starting capital). `pct_ok` is False for a
    curve whose equity is a bare P&L total with no capital behind it, so no percentage is shown.
    """

    source: str
    strategy: str
    asset: str
    initial: float
    points: list[tuple[float, float]]
    fills: list[Fill] = field(default_factory=list)
    pct_ok: bool = True
    note: str = ""
    # False for a figure that is cumulative since the position opened, with no history to cut: the
    # window then cannot apply and the section says so instead of passing it off as a windowed P&L.
    windowed: bool = True
    # False when the fills are cash events, not round trips (win rate and expectancy mean nothing).
    has_trades: bool = True
    # True when the points are a *value*, not a P&L (a wallet balance): gross, realized and unrealized
    # have no meaning there and are reported as None rather than computed from it.
    value_only: bool = False

    def __post_init__(self) -> None:
        self.points = sorted((float(t), float(v)) for t, v in self.points
                             if math.isfinite(t) and math.isfinite(v))


@dataclass
class RunStats:
    """What one curve did inside one window."""

    source: str
    strategy: str
    asset: str
    base: float
    final: float
    net: float
    costs: dict[str, float]
    realized: float
    closes: list[float]
    pct_ok: bool
    value_only: bool = False

    @property
    def gross(self) -> float:
        return self.net + sum(self.costs.values())

    @property
    def unrealized(self) -> float:
        return self.net - self.realized

    @property
    def net_pct(self) -> float | None:
        return net_pct(self.final, self.base) if self.pct_ok else None


def _day(ts: float) -> date:
    return datetime.fromtimestamp(ts, UTC).date()


def run_stats(curve: Curve, window: Window) -> RunStats | None:
    """The curve's result inside `window`, or None when no point falls inside it (no data)."""
    window = window if curve.windowed else ALL
    inside = [(t, v) for t, v in curve.points if window.contains(t)]
    if not inside:
        return None
    prior = [v for t, v in curve.points if window.before(t)]
    base = prior[-1] if prior else curve.initial
    final = inside[-1][1]
    fills = [f for f in curve.fills if window.contains(f.ts)]
    closes = [f.realized for f in fills if f.realized is not None]
    return RunStats(
        source=curve.source, strategy=curve.strategy, asset=curve.asset, base=base, final=final,
        net=final - base,
        costs={"fees": sum(f.fee for f in fills), "slippage": sum(f.slippage for f in fills),
               "borrow": sum(f.borrow for f in fills)},
        realized=sum(closes), closes=closes if curve.has_trades else [], pct_ok=curve.pct_ok,
        value_only=curve.value_only)


def daily_equity(curve: Curve, window: Window) -> tuple[float, dict[date, float]] | None:
    """(base equity, {UTC day: equity at the day's last point}) for the days the curve spans.

    A day with no point carries the previous day's equity forward (nothing was observed, so no P&L
    is invented). None when no point is inside the window.
    """
    window = window if curve.windowed else ALL
    inside = [(t, v) for t, v in curve.points if window.contains(t)]
    if not inside:
        return None
    prior = [v for t, v in curve.points if window.before(t)]
    base = prior[-1] if prior else curve.initial
    last: dict[date, float] = {}
    for t, v in inside:
        last[_day(t)] = v
    out: dict[date, float] = {}
    d, stop, carry = min(last), max(last), base
    while d <= stop:
        carry = last.get(d, carry)
        out[d] = carry
        d += timedelta(days=1)
    return base, out


# -- series, drawdown, periods ---------------------------------------------------------------------


@dataclass
class Day:
    date: date
    equity: float
    pnl: float
    cumulative: float
    drawdown: float | None  # fraction below the running peak; None when the peak is not positive

    def to_dict(self, base: float, pct_ok: bool) -> dict[str, Any]:
        return {"date": self.date.isoformat(), "equity": self.equity, "pnl": self.pnl,
                "cumulative": self.cumulative,
                "cumulative_pct": net_pct(self.equity, base) if pct_ok else None,
                "drawdown": self.drawdown}


def combine_daily(curves: Sequence[Curve], window: Window) -> tuple[float, list[Day]] | None:
    """Sum the per-day equity of several curves of ONE source into one series.

    A curve that has not started yet counts at its base; one that has stopped carries its last
    value. None when no curve has a point inside the window.
    """
    parts = [d for d in (daily_equity(c, window) for c in curves) if d is not None]
    if not parts:
        return None
    first = min(min(days) for _, days in parts)
    last = max(max(days) for _, days in parts)
    base_total = sum(b for b, _ in parts)
    rows: list[Day] = []
    prev = base_total
    peak = base_total
    cur = first
    carried = [b for b, _ in parts]
    while cur <= last:
        total = 0.0
        for i, (b, days) in enumerate(parts):
            if cur in days:
                carried[i] = days[cur]
            total += carried[i]
        peak = max(peak, total)
        rows.append(Day(cur, total, total - prev, total - base_total,
                        (total / peak - 1.0) if peak > 0 else None))
        prev = total
        cur += timedelta(days=1)
    return base_total, rows


def drawdown_report(base: float, days: Sequence[Day]) -> dict[str, Any]:
    """Maximum drawdown of the daily equity (the base counts as the opening peak), and its recovery.

    `recovered` is the first day equity is back at the old peak, `recovery_days` the days from the
    trough to it, None while it has not recovered. The USD drawdown is reported beside the
    percentage because a series that starts at zero has no meaningful percentage.
    """
    if not days:
        return {"max_drawdown_pct": None, "max_drawdown_usd": 0.0, "peak_date": None,
                "trough_date": None, "recovered_date": None, "recovery_days": None,
                "recovered": None}
    peak_v, peak_d = base, None
    worst_usd, worst_pct = 0.0, None
    best = None  # (usd, peak_value, peak_date, trough_date)
    for d in days:
        if d.equity > peak_v:
            peak_v, peak_d = d.equity, d.date
        usd = peak_v - d.equity
        if usd > worst_usd + 1e-12:
            worst_usd = usd
            best = (usd, peak_v, peak_d, d.date)
    if best is None:
        return {"max_drawdown_pct": 0.0 if base > 0 else None, "max_drawdown_usd": 0.0,
                "peak_date": None, "trough_date": None, "recovered_date": None,
                "recovery_days": None, "recovered": None}
    usd, pk, pk_date, tr_date = best
    pct = -(usd / pk) if pk > 0 else None
    rec_date = next((d.date for d in days if d.date > tr_date and d.equity >= pk - 1e-12), None)
    return {
        "max_drawdown_pct": pct, "max_drawdown_usd": -usd,
        "peak_date": pk_date.isoformat() if pk_date else "window start",
        "trough_date": tr_date.isoformat(),
        "recovered_date": rec_date.isoformat() if rec_date else None,
        "recovery_days": (rec_date - tr_date).days if rec_date else None,
        "recovered": rec_date is not None,
    }


def _bucket(days: Sequence[Day], key) -> dict[str, float]:
    out: dict[str, float] = {}
    for d in days:
        out[key(d.date)] = out.get(key(d.date), 0.0) + d.pnl
    return out


def _week_key(d: date) -> str:
    monday = d - timedelta(days=d.weekday())
    return monday.isoformat()


def best_worst(days: Sequence[Day]) -> dict[str, Any]:
    """Best and worst day, ISO week (keyed by its Monday) and calendar month by summed P&L."""
    out: dict[str, Any] = {}
    for name, buckets in (("day", _bucket(days, lambda d: d.isoformat())),
                          ("week", _bucket(days, _week_key)),
                          ("month", _bucket(days, lambda d: d.strftime("%Y-%m")))):
        if not buckets:
            out[name] = None
            continue
        best_k = max(buckets, key=lambda k: buckets[k])
        worst_k = min(buckets, key=lambda k: buckets[k])
        out[name] = {"best": {"period": best_k, "pnl": buckets[best_k]},
                     "worst": {"period": worst_k, "pnl": buckets[worst_k]}, "periods": len(buckets)}
    return out


# -- sections --------------------------------------------------------------------------------------


def group_of(source: str) -> str:
    return GROUPS.get(source, "simulated")


def trade_stats(closes: Sequence[float]) -> dict[str, Any]:
    """Win rate and expectancy over closed fills. Zero results count as closed, not as wins."""
    if not closes:
        return {"closed_trades": 0, "win_rate": None, "expectancy_usd": None, "avg_win": None,
                "avg_loss": None, "profit_factor": None}
    wins = [c for c in closes if c > 0]
    losses = [c for c in closes if c < 0]
    loss_sum = -sum(losses)
    return {
        "closed_trades": len(closes), "win_rate": len(wins) / len(closes),
        "expectancy_usd": statistics.fmean(closes),
        "avg_win": statistics.fmean(wins) if wins else None,
        "avg_loss": statistics.fmean(losses) if losses else None,
        "profit_factor": (sum(wins) / loss_sum) if loss_sum > 0 else None,
    }


def _run_row(r: RunStats, section_net: float, section_base: float) -> dict[str, Any]:
    word = r.source
    return {
        "strategy": r.strategy, "asset": r.asset, "base": r.base, "final": r.final,
        "net_usd": r.net, "gross_usd": None if r.value_only else r.gross,
        "costs_usd": sum(r.costs.values()),
        "net_pct": r.net_pct, "net_pct_text": labelled(r.net_pct, word),
        "realized_usd": None if r.value_only else r.realized,
        "unrealized_usd": None if r.value_only else r.unrealized,
        # Percentage points this run adds to the section's net %: they sum to it exactly.
        "contribution_pts": (r.net / section_base) if section_base > 0 and r.pct_ok else None,
        "share_of_net": (r.net / section_net) if abs(section_net) > 1e-9 else None,
    }


def _group_by(rows: Sequence[RunStats], key, section_net: float, section_base: float):
    groups: dict[str, list[RunStats]] = {}
    for r in rows:
        groups.setdefault(key(r), []).append(r)
    out = []
    for name in sorted(groups):
        rs = groups[name]
        net = sum(r.net for r in rs)
        base = sum(r.base for r in rs)
        pct_ok = all(r.pct_ok for r in rs)
        word = rs[0].source
        pct = net_pct(base + net, base) if pct_ok else None
        out.append({"name": name, "runs": len(rs), "net_usd": net, "base": base,
                    "net_pct": pct, "net_pct_text": labelled(pct, word),
                    "gross_usd": None if all(r.value_only for r in rs) else sum(r.gross for r in rs),
                    "costs_usd": sum(sum(r.costs.values()) for r in rs),
                    "contribution_pts": (net / section_base) if section_base > 0 and pct_ok else None,
                    "share_of_net": (net / section_net) if abs(section_net) > 1e-9 else None})
    return out


def build_section(source: str, curves: Sequence[Curve], window: Window,
                  notes: Sequence[str] = ()) -> dict[str, Any]:
    """Everything the P&L tab shows for one source over one window."""
    group = group_of(source)
    stamps = [t for c in curves for t, _ in c.points]
    data_range = [iso(min(stamps)), iso(max(stamps))] if stamps else None
    head = {"source": source, "group": group, "label": f"{source} ({group})",
            "window": window.to_dict(), "notes": list(notes), "data_range": data_range}
    runs = [s for s in (run_stats(c, window) for c in curves) if s is not None]
    if not runs:
        covers = f" (its data covers {data_range[0][:10]} to {data_range[1][:10]})" if data_range else ""
        return {**head, "status": "no_data", "runs": 0,
                "message": f"no {source} data inside the {window.label} window{covers}"}
    base = sum(r.base for r in runs)
    net = sum(r.net for r in runs)
    pct_ok = all(r.pct_ok for r in runs)
    pct = net_pct(base + net, base) if pct_ok else None
    costs = {k: sum(r.costs[k] for r in runs) for k in ("fees", "slippage", "borrow")}
    value_only = all(r.value_only for r in runs)
    combined = combine_daily([c for c in curves if run_stats(c, window) is not None], window)
    days = combined[1] if combined else []
    closes = [x for r in runs for x in r.closes]
    windowed = all(c.windowed for c in curves)
    if not windowed:
        head["notes"] = head["notes"] + [
            "not windowed: this source holds a cumulative figure since each position opened, "
            "with no history to cut by date"]
    return {
        **head, "status": "ok", "runs": len(runs), "windowed": windowed,
        "totals": {
            "initial": base, "final": base + net, "net_usd": net,
            "gross_usd": None if value_only else net + sum(costs.values()), "fees_usd": costs["fees"],
            "slippage_usd": costs["slippage"], "borrow_funding_usd": costs["borrow"],
            "costs_usd": sum(costs.values()), "net_pct": pct, "net_pct_text": labelled(pct, source),
            "realized_usd": None if value_only else sum(r.realized for r in runs),
            "unrealized_usd": None if value_only else sum(r.unrealized for r in runs),
            **trade_stats(closes),
        },
        "drawdown": drawdown_report(combined[0], days) if combined else None,
        "best_worst": best_worst(days),
        "days": [d.to_dict(combined[0], pct_ok) for d in days] if combined else [],
        "by_strategy": [_run_row(r, net, base) for r in runs],
        "by_asset": _group_by(runs, lambda r: r.asset, net, base),
    }


def build_report(inputs: Iterable[tuple[str, Sequence[Curve], Sequence[str]]],
                 window: Window) -> dict[str, Any]:
    """One section per source. There is deliberately no total across sections."""
    sections = [build_section(src, curves, window, notes) for src, curves, notes in inputs]
    return {"window": window.to_dict(), "sections": sections, "notice": NOTICE,
            "groups": {g: [s["source"] for s in sections if s["group"] == g]
                       for g in ("simulated", "real", "unclassified")
                       if g != "unclassified" or any(s["group"] == g for s in sections)}}


# -- adapters: real sources to curves --------------------------------------------------------------


def curves_from_backtest(result: Any, source: str, strategy: str, asset: str,
                         initial: float) -> Curve:
    """A `BacktestResult` (or a paper replay's result sliced to the cursor) as a curve."""
    ts = [float(t) for t in result.timestamps]
    eq = [float(v) for v in result.equity]
    fills = []
    for t in result.trades:
        closing = t.side == "close" or t.reason == "resize_down"
        fills.append(Fill(ts=float(t.ts), fee=float(t.fee), slippage=float(t.slippage),
                          borrow=float(t.borrow_fee_settled),
                          realized=float(t.realized_pnl) if closing else None))
    return Curve(source, strategy, asset, initial, list(zip(ts, eq)), fills)


def curve_from_paper(session: Any, strategy: str, asset: str) -> Curve:
    """The paper replay up to its cursor: later bars have not 'happened' yet."""
    res = session.result
    cut = session.cursor + 1
    ts = [float(t) for t in session._ts[:cut]]
    eq = [float(v) for v in res.equity[:cut]]
    sliced = type("Cut", (), {})()
    sliced.timestamps, sliced.equity = ts, eq
    sliced.trades = [t for t in res.trades if t.bar_index <= session.cursor]
    return curves_from_backtest(sliced, "paper", strategy, asset, session.starting_equity)


def curves_from_journal(doc: Any, label_note: str = "") -> list[Curve]:
    """The extension's dry-run journal (`~/.solmargintrader/journal.json`) as one P&L curve.

    The journal holds fills and carry costs but no capital and no equity series, so the curve is
    the running *net realized P&L* (FIFO round trips, fees and carry deducted) starting at zero and
    `pct_ok=False`: a percentage would need a capital base the journal does not record. Open lots
    are not marked (no price is stored), so unrealized P&L is not available from this source.
    """
    if not isinstance(doc, dict):
        return []
    fills_raw = doc.get("fills") or {}
    carry_raw = doc.get("carry") or {}
    fills = sorted((f for f in (fills_raw.values() if isinstance(fills_raw, dict) else fills_raw)
                    if isinstance(f, dict) and _num(f.get("tsMs")) is not None),
                   key=lambda f: f["tsMs"])
    if not fills:
        return []
    lots: list[list[float]] = []  # [qty, price, fee_per_unit]
    events: list[tuple[float, float, Fill | None]] = []  # (ts, pnl delta, fill)
    asset = "SOL"
    for f in fills:
        ts = f["tsMs"] / 1000.0
        qty, px, fee = _num(f.get("baseQty")), _num(f.get("priceUsd")), _num(f.get("feeUsd")) or 0.0
        if qty is None or px is None or qty <= 0:
            continue
        if f.get("side") == "buy":
            lots.append([qty, px, fee / qty])
            events.append((ts, -fee, Fill(ts, fee=fee)))
            continue
        left, gross, entry_fee = qty, 0.0, 0.0
        while left > 1e-12 and lots:
            take = min(left, lots[0][0])
            gross += take * (px - lots[0][1])
            entry_fee += take * lots[0][2]
            lots[0][0] -= take
            left -= take
            if lots[0][0] <= 1e-12:
                lots.pop(0)
        net = gross - fee - entry_fee
        events.append((ts, gross - fee, Fill(ts, fee=fee, realized=net)))
    for c in (carry_raw.values() if isinstance(carry_raw, dict) else carry_raw):
        if isinstance(c, dict) and _num(c.get("tsMs")) is not None and _num(c.get("costUsd")) is not None:
            ts = c["tsMs"] / 1000.0
            events.append((ts, -c["costUsd"], Fill(ts, borrow=c["costUsd"])))
    events.sort(key=lambda e: e[0])
    running, points = 0.0, []
    for ts, delta, _ in events:
        running += delta
        points.append((ts, running))
    return [Curve("dry-run", "extension grid (journal)", asset, 0.0, points,
                  [e[2] for e in events if e[2] is not None], pct_ok=False,
                  note=label_note or "no capital base in the journal: net % unavailable; "
                  "open lots are not marked")]


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


# -- liquidity daemon -------------------------------------------------------------------------------


def lp_source(mode: Any) -> str:
    """`live LP` only when the daemon says live; `dry-run LP` when it says dry-run; else `reported LP`.

    Never guess live from an unknown mode, and never fold an unknown one into the simulated group.
    """
    return LP_WORDS.get(mode, "reported LP")


def curve_from_lp_status(status: dict[str, Any]) -> Curve | None:
    """The daemon's `status.json` as one *cumulative* point: P&L since each position opened.

    `status.json` is a snapshot. It cannot be cut by date, so the curve is marked `windowed=False`.
    Realized is rewards less gas (cash earned and paid); unrealized is the rest of `pnl_usd`
    (the mark on the liquidity still deployed).
    """
    positions = [p for p in (status.get("positions") or []) if isinstance(p, dict)]
    if not positions:
        return None
    pnl = sum(_num(p.get("pnl_usd")) or 0.0 for p in positions)
    deposited = sum(_num(p.get("deposited_usd")) or 0.0 for p in positions)
    gas = sum(_num(p.get("gas_usd")) or 0.0 for p in positions)
    rewards = sum(_num(p.get("rewards_usd")) or 0.0 for p in positions)
    ts = _num(status.get("generated_at")) or 0.0
    source = lp_source(status.get("mode"))
    fill = Fill(ts, fee=gas, realized=rewards - gas)
    return Curve(source, "aero-lp (all positions)", "LP pairs", deposited,
                 [(ts, deposited + pnl)], [fill], pct_ok=deposited > 0, windowed=False,
                 has_trades=False,
                 note="cumulative since each position opened; fees column is gas")


def curve_from_lp_ledger(conn: Any, mode: Any) -> Curve | None:
    """The daemon's `ledger.sqlite` (opened read-only by the caller) as a windowed P&L curve.

    P&L at each snapshot time = value of all positions (value + unclaimed) - net deposits + claimed
    rewards - gas. Equity is that P&L on top of the total ever deposited, held constant, so a
    window's net is exactly the P&L change inside it and a later deposit is not mistaken for profit.
    Returns None when the ledger has no snapshots (nothing to draw a history from).
    """
    snaps = conn.execute("SELECT slot, ts, value_usd, unclaimed_usd FROM snapshots ORDER BY ts").fetchall()
    if not snaps:
        return None
    flows = conn.execute("SELECT ts, kind, usd FROM flows ORDER BY ts").fetchall()
    events = conn.execute("SELECT ts, kind, gas_usd, reward_usd FROM events ORDER BY ts").fetchall()
    basis = sum(usd for _, kind, usd in flows if kind in ("deposit", "topup"))
    latest: dict[str, float] = {}
    points: list[tuple[float, float]] = []
    for ts in sorted({r[1] for r in snaps}):
        for slot, t, value, unclaimed in snaps:
            if t == ts:
                latest[slot] = (value or 0.0) + (unclaimed or 0.0)
        net_flow = sum((usd if kind in ("deposit", "topup") else -usd)
                       for t, kind, usd in flows if t <= ts)
        claimed = sum(r for t, kind, g, r in events if t <= ts and kind in ("claim", "collect"))
        gas = sum(g for t, kind, g, r in events if t <= ts)
        points.append((ts, basis + sum(latest.values()) - net_flow + claimed - gas))
    fills = [Fill(t, fee=g or 0.0,
                  realized=((r if kind in ("claim", "collect") else 0.0) or 0.0) - (g or 0.0))
             for t, kind, g, r in events if (g or r)]
    return Curve(lp_source(mode), "aero-lp (all positions)", "LP pairs", basis, points, fills,
                 pct_ok=basis > 0, has_trades=False,
                 note="history from ledger.sqlite snapshots; fees column is gas")


# -- wallet scans --------------------------------------------------------------------------------------


def curve_from_wallet_history(rows: Sequence[dict[str, Any]]) -> Curve | None:
    """The wallet's value at each recorded scan, as a curve. None when no scan has been recorded.

    This is a *value change*, not a trading P&L: deposits, withdrawals and price moves are all in it,
    and nothing in a scan can tell them apart. It is shown only in the `wallet (live)` section (real
    money), never beside a simulation, and the section's note says what it is. The first scan is the
    starting value, so a single scan has no change to report.
    """
    pts = [(float(r["ts"]), float(r["total_usd"])) for r in rows
           if _num(r.get("ts")) is not None and _num(r.get("total_usd")) is not None]
    if not pts:
        return None
    pts.sort()
    return Curve("wallet (live)", "all holdings", "wallet", pts[0][1], pts, [], pct_ok=pts[0][1] > 0,
                 has_trades=False, value_only=True,
                 note="value change between scans: includes deposits, withdrawals and price moves; "
                      "it is not trading P&L")

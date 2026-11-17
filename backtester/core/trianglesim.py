"""Triangular-arbitrage event replay over top-of-book quote snapshots.

`guides/triangular_arbitrage.md` specifies the mechanism; this module is the
event replay it calls for. A triangle is USD plus two coins A and B with three markets:
`A-USD`, `B-USD` and the cross `A-B` (quoted in B per A). With `r_XY` the units of Y
received per unit of X sold, at the touch:

    sell BASE for QUOTE:  rate = bid          buy BASE with QUOTE:  rate = 1 / ask

    forward  USD -> A -> B -> USD   M = (1 / ask[A-USD]) * bid[A-B] * bid[B-USD]
    reverse  USD -> B -> A -> USD   M = (1 / ask[B-USD]) * (1 / ask[A-B]) * bid[A-USD]
    net      M_net = M * (1 - fee)^3,   edge_bps = 10000 * (M_net - 1)

Execution model, chosen to be pessimistic rather than flattering:

* **Detect on one snapshot, execute on a later one.** A cycle seen at time *t* executes
  at the first snapshot at or after `t + latency_s`, at *that* snapshot's quotes, for all
  three legs. A dislocation that vanished in the meantime is executed anyway and its
  realized edge is reported, usually negative. Executing at the detecting snapshot would be
  the classic arbitrage-backtest lie: it assumes the dislocation is still there when the
  orders land.
* **Every leg pays the taker fee and crosses the spread.** No maker rebates, no mid fills.
* **Size is capped by the displayed top-of-book size** of every leg when the snapshot
  carries sizes. Depth beyond the touch is unknown, so it is not used.
* **Quotes older than `max_quote_age_s` are not used**, because a stale leg makes a
  dislocation out of nothing.

What this cannot show, and therefore does not claim: queue position, partial fills,
the order in which three separate orders actually fill, and competition from faster
participants. A positive result here is a necessary condition, not a sufficient one.

Two data sources feed it, and the result carries which one was used:

* `recorded` -- bid/ask snapshots recorded from the live Coinbase ticker stream by
  `soltui/pricefeed.py`. This is the honest input.
* `candle-proxy` -- one-minute closes with an assumed half-spread on each side. Closes are
  not synchronous within the minute and carry no bid or ask, so a proxy edge is an upper
  bound on noise, not evidence of an opportunity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

SOURCE_RECORDED = "recorded"
SOURCE_CANDLE_PROXY = "candle-proxy"

# (bid, ask, bid_size, ask_size, quote_time); sizes may be None when the source has none.
Quote = tuple[float, float, float | None, float | None, float]


def _finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


@dataclass(frozen=True)
class Triangle:
    """USD, coin `a` and coin `b`, joined by the cross market `a-b` (b per a)."""

    a: str
    b: str
    quote: str = "USD"

    @property
    def name(self) -> str:
        return f"{self.quote}-{self.a}-{self.b}"

    @property
    def products(self) -> tuple[str, str, str]:
        return (f"{self.a}-{self.quote}", f"{self.b}-{self.quote}", f"{self.a}-{self.b}")


def triangles_from_products(products: Iterable[str], quote: str = "USD") -> list[Triangle]:
    """Every triangle whose three markets are all in `products`."""
    have = set(products)
    out = []
    for p in sorted(have):
        base, _, q = p.partition("-")
        if q in ("", quote):
            continue
        tri = Triangle(base, q, quote)
        if all(leg in have for leg in tri.products):
            out.append(tri)
    return out


@dataclass(frozen=True)
class TriangleConfig:
    """Thresholds and execution assumptions. Field names match the card's params."""

    min_edge_bps: float = 35.0
    taker_fee_bps: float = 10.0
    latency_s: float = 1.0
    notional_usd: float = 100.0
    max_quote_age_s: float = 5.0
    cooldown_s: float = 5.0
    use_displayed_size: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.use_displayed_size, bool):
            raise ValueError("use_displayed_size must be a boolean")
        for name in ("min_edge_bps", "taker_fee_bps", "latency_s", "notional_usd",
                     "max_quote_age_s", "cooldown_s"):
            _finite(name, getattr(self, name))
        if not 0 <= self.taker_fee_bps < 10_000:
            raise ValueError("taker_fee_bps must be in [0, 10000)")
        if self.latency_s < 0 or self.max_quote_age_s <= 0 or self.cooldown_s < 0:
            raise ValueError("latency_s and cooldown_s cannot be negative; max_quote_age_s must be > 0")
        if not self.notional_usd > 0:
            raise ValueError("notional_usd must be > 0")

    def to_dict(self) -> dict[str, Any]:
        return {"min_edge_bps": self.min_edge_bps, "taker_fee_bps": self.taker_fee_bps,
                "latency_s": self.latency_s, "notional_usd": self.notional_usd,
                "max_quote_age_s": self.max_quote_age_s, "cooldown_s": self.cooldown_s,
                "use_displayed_size": self.use_displayed_size}


def _usable(q: Quote | None, now: float, max_age: float) -> bool:
    if q is None:
        return False
    try:
        bid, ask, bid_size, ask_size, quote_time = q
        if any(isinstance(value, bool) for value in (bid, ask, quote_time)):
            return False
        sizes_valid = all(size is None or (not isinstance(size, bool) and math.isfinite(size) and size > 0)
                          for size in (bid_size, ask_size))
        return (math.isfinite(now) and math.isfinite(quote_time) and math.isfinite(bid)
                and math.isfinite(ask) and 0 < bid <= ask and sizes_valid
                and 0 <= now - quote_time <= max_age)
    except (TypeError, ValueError, OverflowError):
        return False


def cycle_edges_bps(tri: Triangle, quotes: Mapping[str, Quote], fee_bps: float,
                    now: float | None = None, max_age: float = math.inf) -> tuple[float, float] | None:
    """(forward, reverse) net edge in bps at these quotes, or None when a leg is unusable."""
    p_a, p_b, p_ab = tri.products
    qa, qb, qab = quotes.get(p_a), quotes.get(p_b), quotes.get(p_ab)
    if qa is None or qb is None or qab is None:
        return None
    t = now if now is not None else max(qa[4], qb[4], qab[4])
    if not all(_usable(q, t, max_age) for q in (qa, qb, qab)):
        return None
    keep = (1.0 - fee_bps / 10_000.0) ** 3
    fwd = (1.0 / qa[1]) * qab[0] * qb[0] * keep
    rev = (1.0 / qb[1]) * (1.0 / qab[1]) * qa[0] * keep
    edges = 10_000.0 * (fwd - 1.0), 10_000.0 * (rev - 1.0)
    return edges if all(math.isfinite(edge) for edge in edges) else None


def _size_cap_usd(tri: Triangle, direction: str, quotes: Mapping[str, Quote], fee_bps: float = 0.0) -> float:
    """USD the touch can absorb on every leg, or inf when sizes are not known."""
    p_a, p_b, p_ab = tri.products
    qa, qb, qab = quotes[p_a], quotes[p_b], quotes[p_ab]
    keep = 1.0 - fee_bps / 10_000.0
    # Each size names BASE units consumed at that leg, before that leg's fee.
    # Reverse every preceding conversion to express its cap in starting USD.
    if direction == "forward":
        factors = ((qa[3], qa[1]), (qab[2], qa[1] / keep),
                   (qb[2], qa[1] / (qab[0] * keep**2)))
    else:
        factors = ((qb[3], qb[1]), (qab[3], qab[1] * qb[1] / keep),
                   (qa[2], qb[1] * qab[1] / keep**2))
    caps = [size * scale for size, scale in factors if size is not None]
    return min(caps) if caps else math.inf



@dataclass
class TriangleRunResult:
    """What one replay found, per triangle and in total."""

    config: dict[str, Any]
    source: str
    snapshots: int
    start_ts: float | None
    end_ts: float | None
    per_triangle: dict[str, dict[str, Any]]
    cycles: list[dict[str, Any]]

    @property
    def executed(self) -> int:
        return len(self.cycles)

    @property
    def pnl_usd(self) -> float:
        return float(sum(c["pnl_usd"] for c in self.cycles))

    @property
    def wins(self) -> int:
        return sum(1 for c in self.cycles if c["pnl_usd"] > 0)

    def summary(self) -> dict[str, Any]:
        return {"config": self.config, "source": self.source, "snapshots": self.snapshots,
                "start_ts": self.start_ts, "end_ts": self.end_ts, "executed": self.executed,
                "wins": self.wins, "pnl_usd": self.pnl_usd,
                "per_triangle": self.per_triangle, "cycles": self.cycles[-50:]}


class TriangleReplay:
    """Streaming form of the replay: `feed` snapshots in time order, read `result()` any time.

    A forward test feeds each newly recorded snapshot as it arrives instead of re-reading the
    whole recording; feeding the same snapshots in one go or in pieces gives the same result
    (`test_streaming_equals_batch`). A detected cycle waits in `pending` until the first
    snapshot at or after its execution time.
    """

    def __init__(self, cfg: TriangleConfig, triangles: Sequence[Triangle], *,
                 source: str = SOURCE_RECORDED) -> None:
        if source not in (SOURCE_RECORDED, SOURCE_CANDLE_PROXY):
            raise ValueError(f"unknown source {source!r}")
        self.cfg = cfg
        self.triangles = list(triangles)
        self.source = source
        self.book: dict[str, Quote] = {}
        self.snapshots = 0
        self.start_ts: float | None = None
        self.end_ts: float | None = None
        self.per: dict[str, dict[str, Any]] = {
            tri.name: {"observed": 0, "best_edge_bps": None, "signals": 0, "executed": 0, "wins": 0,
                       "pnl_usd": 0.0, "realized_edge_sum_bps": 0.0}
            for tri in self.triangles
        }
        self.cycles: list[dict[str, Any]] = []
        self.next_allowed = {tri.name: -math.inf for tri in self.triangles}
        # (exec_after, triangle, direction, signal_ts, signal_edge)
        self.pending: list[tuple[float, Triangle, str, float, float]] = []

    def feed(self, now: float, quotes: Mapping[str, Quote]) -> None:
        now = _finite("snapshot time", now)
        if self.end_ts is not None and now < self.end_ts:
            raise ValueError("snapshots must be in ascending time order")
        self.book = {**self.book, **quotes}
        self.snapshots += 1
        self.start_ts = now if self.start_ts is None else self.start_ts
        self.end_ts = now
        cfg = self.cfg
        # Execute what was waiting for this moment, at THIS snapshot's quotes.
        due = [p for p in self.pending if p[0] <= now]
        self.pending = [p for p in self.pending if p[0] > now]
        for _, tri, direction, signal_ts, signal_edge in due:
            self._execute(tri, direction, signal_ts, signal_edge, now)
        for tri in self.triangles:
            edges = cycle_edges_bps(tri, self.book, cfg.taker_fee_bps, now, cfg.max_quote_age_s)
            if edges is None:
                continue
            row = self.per[tri.name]
            row["observed"] += 1
            best = max(edges)
            if row["best_edge_bps"] is None or best > row["best_edge_bps"]:
                row["best_edge_bps"] = best
            if best < cfg.min_edge_bps or now < self.next_allowed[tri.name]:
                continue
            if any(p[1] == tri for p in self.pending):
                continue
            row["signals"] += 1
            direction = "forward" if edges[0] >= edges[1] else "reverse"
            if cfg.latency_s <= 0:
                self._execute(tri, direction, now, best, now)
            else:
                self.pending.append((now + cfg.latency_s, tri, direction, now, best))

    def _execute(self, tri: Triangle, direction: str, signal_ts: float, signal_edge: float, now: float) -> None:
        cfg = self.cfg
        self.next_allowed[tri.name] = now + cfg.cooldown_s
        exec_edges = cycle_edges_bps(tri, self.book, cfg.taker_fee_bps, now, cfg.max_quote_age_s)
        if exec_edges is None:
            return  # a leg went stale before execution; nothing traded
        realized = exec_edges[0] if direction == "forward" else exec_edges[1]
        notional = cfg.notional_usd
        if cfg.use_displayed_size:
            notional = min(notional, _size_cap_usd(tri, direction, self.book, cfg.taker_fee_bps))
        if not math.isfinite(notional) or notional <= 0:
            return
        pnl = notional * realized / 10_000.0
        if notional <= 0 or not math.isfinite(pnl):
            return
        row = self.per[tri.name]
        row["executed"] += 1
        row["wins"] += int(pnl > 0)
        row["pnl_usd"] += pnl
        row["realized_edge_sum_bps"] += realized
        self.cycles.append({"triangle": tri.name, "direction": direction, "signal_ts": signal_ts,
                            "exec_ts": now, "signal_edge_bps": signal_edge, "realized_edge_bps": realized,
                            "notional_usd": notional, "pnl_usd": pnl})

    def result(self) -> "TriangleRunResult":
        per = {}
        for name, row in self.per.items():
            out = dict(row)
            total = out.pop("realized_edge_sum_bps")
            out["mean_realized_edge_bps"] = total / out["executed"] if out["executed"] else None
            per[name] = out
        return TriangleRunResult(self.cfg.to_dict(), self.source, self.snapshots, self.start_ts,
                                 self.end_ts, per, list(self.cycles))


def run_triangle_backtest(
    cfg: TriangleConfig,
    snapshots: Sequence[tuple[float, Mapping[str, Quote]]],
    triangles: Sequence[Triangle],
    *,
    source: str = SOURCE_RECORDED,
) -> TriangleRunResult:
    """Replay snapshots (ascending time) and execute every cycle that clears `min_edge_bps`.

    Each snapshot is (time, {product: quote}); a product missing from a snapshot keeps its
    last quote, whose own timestamp then ages it out after `max_quote_age_s`. A cycle still
    waiting for its execution time when the snapshots end never trades.
    """
    replay = TriangleReplay(cfg, triangles, source=source)
    for t, quotes in snapshots:
        replay.feed(t, quotes)
    return replay.result()


def snapshots_from_closes(
    closes: Mapping[str, Sequence[tuple[float, float]]],
    half_spread_bps: Mapping[str, float] | float,
) -> list[tuple[float, dict[str, Quote]]]:
    """Candle proxy: {product: [(ts, close), ...]} -> snapshots with an assumed spread.

    A product contributes a quote only at the minutes it has a candle, stamped with that
    minute. Thin cross pairs skip many minutes, so requiring every product at every minute
    would leave almost nothing; instead the replay's `max_quote_age_s` rule pairs only legs
    quoted in the same minute, and a leg carried forward from an earlier minute is stale.
    """
    by_time: dict[float, dict[str, Quote]] = {}
    for p, rows in closes.items():
        hs = half_spread_bps.get(p, 0.0) if isinstance(half_spread_bps, Mapping) else half_spread_bps
        h = float(hs) / 10_000.0
        for t, close in rows:
            px = float(close)
            if not (math.isfinite(px) and px > 0):
                continue
            by_time.setdefault(float(t), {})[p] = (px * (1 - h), px * (1 + h), None, None, float(t))
    return sorted(by_time.items())


# -- recorded snapshot files ------------------------------------------------------------------
#
# `soltui/pricefeed.py` writes one JSON object per line, gzip-compressed, one file per UTC day:
#
#     {"t": <epoch seconds>, "q": {"SOL-USD": [bid, ask, last, bid_size, ask_size, quote_time], ...}}
#
# The reader lives here, beside the replay it feeds, so the backtester never imports soltui.
# Each recorder flush is its own gzip member; a crash can truncate the last one, and the
# reader keeps every complete line before the damage instead of discarding the day.


def parse_snapshot_line(line: str, *, require_quote_time: bool = False) -> tuple[float, dict[str, Quote]] | None:
    """Parse one snapshot. Forward replay requires measured product timestamps.

    Historical readers retain the legacy snapshot-time fallback by default.
    """
    import json

    try:
        row = json.loads(line)
        if isinstance(row["t"], bool):
            return None
        t = float(row["t"])
        raw = row["q"]
    except (ValueError, KeyError, TypeError, OverflowError):
        return None
    if not math.isfinite(t) or not isinstance(raw, dict):
        return None
    quotes: dict[str, Quote] = {}
    for product, v in raw.items():
        try:
            if not isinstance(v, (list, tuple)) or len(v) < 2 or any(isinstance(value, bool) for value in v):
                continue
            bid, ask = float(v[0]), float(v[1])
            bsz = float(v[3]) if len(v) > 3 and v[3] is not None else None
            asz = float(v[4]) if len(v) > 4 and v[4] is not None else None
            if require_quote_time and (len(v) <= 5 or v[5] is None or isinstance(v[5], bool)):
                continue
            qt = float(v[5]) if len(v) > 5 and v[5] is not None else t
            if not math.isfinite(qt) or qt > t:
                continue
            if any(size is not None and (not math.isfinite(size) or size <= 0) for size in (bsz, asz)):
                continue
        except (TypeError, ValueError, IndexError, OverflowError):
            continue
        if math.isfinite(bid) and math.isfinite(ask) and 0 < bid <= ask:
            quotes[str(product)] = (bid, ask, bsz, asz, qt)
    return t, quotes


def iter_snapshot_files(paths: Sequence[str | Any], *, start_ts: float | None = None,
                        end_ts: float | None = None):
    """Yield usable snapshots from `paths` (gzip or plain JSONL) one at a time, file by file.

    Streaming on purpose: a day of one-second snapshots across two dozen markets is millions of
    quotes, and a multi-day replay must not hold them all. Files are read in name order (the
    recorder names them by UTC day); lines within a file are in time order.
    """
    import gzip
    import zlib
    from pathlib import Path

    for path in sorted(Path(p) for p in paths):
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8") as fh:
                while True:
                    try:
                        line = fh.readline()
                    except (EOFError, OSError, zlib.error):
                        break  # a truncated final member: keep what came before it
                    if not line:
                        break
                    parsed = parse_snapshot_line(line)
                    if parsed is None:
                        continue
                    if start_ts is not None and parsed[0] < start_ts:
                        continue
                    if end_ts is not None and parsed[0] > end_ts:
                        continue
                    yield parsed
        except OSError:
            continue


def read_snapshot_files(paths: Sequence[str | Any], *, start_ts: float | None = None,
                        end_ts: float | None = None) -> list[tuple[float, dict[str, Quote]]]:
    """Every usable snapshot in `paths`, ascending, within [start, end]."""
    out = list(iter_snapshot_files(paths, start_ts=start_ts, end_ts=end_ts))
    out.sort(key=lambda row: row[0])
    return out

"""Prospective, read-only GUM Volty comparison on shared executable quotes."""

from __future__ import annotations

import argparse
import json
import math
import os
import signal
import sqlite3
import stat
import threading
import time
from contextlib import closing
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode

from .cli import owner
from .gum_orders import GumError, _decimal, _market, _quote_fresh
from .zec_volty_signal import (
    GumVoltySource,
    VoltyDataError,
    VoltyObservation,
    VoltySignalEngine,
    _get_json,
    _validate_observation,
)

D = Decimal
ZERO = D(0)
INITIAL = D("2.01")
MAX_OPEN = D("6")
LEVERAGE = D(25)
ALLOCATION = D("0.50")
SLIP = D("0.0015")
LOT = D("0.001")
TICK = D("0.01")
HOUR = 3600
MAX_FUNDING_MARK_GAP = 20
MAX_PLAN_AGE = 5
ARMS = ("funded-rules", "short-only", "close-and-wait")
METHOD = "zec-volty-shared-gum-v1"
GUM = "https://api.gum.ag"


@dataclass(frozen=True)
class PaperTick:
    observation: VoltyObservation
    received_at: float
    market: dict
    bid: Decimal
    bid_size: Decimal
    ask: Decimal
    ask_size: Decimal
    funding_bps: Decimal | None = None

    def top(self, side):
        return (self.ask, self.ask_size) if side == "buy" else (self.bid, self.bid_size)

    def terms(self, side):
        mark = _decimal(self.market["markPrice"])
        bid = _decimal(self.market["bestBid"])
        ask = _decimal(self.market["bestAsk"])
        if side == "buy":
            cap = (ask * (1 + SLIP)).quantize(TICK, rounding=ROUND_FLOOR)
            adverse = max(D(0), cap - min(mark, bid))
        else:
            cap = (bid * (1 - SLIP)).quantize(TICK, rounding=ROUND_CEILING)
            adverse = max(mark, ask, cap) - cap
        risk_price = max(mark, bid, ask, cap)
        fee = _decimal(self.market["takerFeeBps"], zero=True) / 10000
        return cap, risk_price, risk_price / LEVERAGE + fee * risk_price + adverse, fee


class GumPaperFeed:
    """Read public GET routes only, with the same bands and venue terms as the owner."""

    def __init__(self):
        self.source = GumVoltySource()

    def read(self, prior_at: int | None) -> PaperTick:
        observation = self.source.read()
        if prior_at is not None and observation.mark_at <= prior_at:
            raise VoltyDataError("gum_no_distinct_paper_mark")
        market = _market(_get_json(f"{GUM}/perps/market/ZEC"))
        market_received = time.monotonic()
        book = _get_json(f"{GUM}/perps/orderbook/ZEC")
        book_received = time.monotonic()
        now = time.time()
        _validate_observation(observation, now)
        stamp = book.get("timestamp")
        if (
            book.get("symbol") != "ZEC" or type(stamp) is not int or not 0 <= now - stamp <= 5
            or _decimal(book.get("lastUpdatedMs"), zero=True) > 5000
            or market["timestamp"] > now
        ):
            raise VoltyDataError("gum_stale_paper_book")
        bid, bid_size = map(_decimal, book["bids"][0])
        ask, ask_size = map(_decimal, book["asks"][0])
        if bid > ask:
            raise VoltyDataError("gum_crossed_paper_book")
        rate = None
        if prior_at is not None and prior_at // HOUR != observation.mark_at // HOUR:
            boundary = observation.mark_at // HOUR * HOUR
            if boundary - prior_at <= MAX_FUNDING_MARK_GAP and observation.mark_at - boundary <= MAX_FUNDING_MARK_GAP:
                rate = self._funding(boundary)
        now = time.time()
        _validate_observation(observation, now)
        _quote_fresh(market, market_received)
        book_age = D(str(time.monotonic() - book_received)) * 1000 + _decimal(book["lastUpdatedMs"], zero=True)
        if now - stamp > 5 or book_age > 5000:
            raise VoltyDataError("gum_stale_paper_book")
        return PaperTick(observation, now, market, bid, bid_size, ask, ask_size, rate)

    @staticmethod
    def _funding(boundary: int) -> Decimal | None:
        query = urlencode({"startTime": boundary, "endTime": boundary, "limit": 2})
        try:
            payload = _get_json(f"{GUM}/app/perps/fundingRate/ZEC/history?{query}")
            entries = payload["entries"]
            if len(entries) == 1 and entries[0]["symbol"] == "ZEC" and entries[0]["timestamp"] == boundary:
                rate = D(str(entries[0]["rateBps1h"]))
                if rate.is_finite() and abs(rate) < 10000:
                    return rate
        except (VoltyDataError, TypeError, KeyError, ValueError, InvalidOperation):
            return None
        return None


@dataclass
class Position:
    side: str
    quantity: Decimal
    price: Decimal
    margin: Decimal
    entry_fee: Decimal
    funding: Decimal = ZERO

    @property
    def direction(self):
        return 1 if self.side == "buy" else -1

    def gross(self, mark):
        return self.direction * self.quantity * (mark - self.price)


@dataclass
class Plan:
    side: str
    close: bool
    quantity: Decimal
    cap: Decimal
    margin: Decimal
    window: int
    planned_at: float


@dataclass
class Book:
    balance: Decimal = INITIAL
    realized: Decimal = ZERO
    fees: Decimal = ZERO
    funding: Decimal = ZERO
    closed: int = 0
    wins: int = 0
    funding_charged: int = 0
    funding_missing: int = 0
    peak: Decimal = INITIAL
    max_drawdown: Decimal = ZERO
    margin_breach: bool = False
    refusals: dict[str, int] = field(default_factory=dict)
    position: Position | None = None
    pending: Plan | None = None
    reverse: tuple[str, int] | None = None

    def refuse(self, reason):
        self.refusals[reason] = self.refusals.get(reason, 0) + 1

    def apply_funding(self, tick, hours):
        if self.position is None or self.margin_breach or not hours:
            return
        if tick.funding_bps is None or hours != 1:
            self.funding_missing += hours
            return
        cost = -self.position.direction * self.position.quantity * D(str(tick.observation.mark)) * tick.funding_bps / 10000
        self.position.funding += cost
        self.funding += cost
        self.balance += cost
        self.funding_charged += 1

    def submit(self, tick):
        plan = self.pending
        self.pending = None
        if plan.window != tick.observation.window_start or not 0 <= tick.received_at - plan.planned_at <= MAX_PLAN_AGE:
            return self.refuse("plan_expired")
        fresh_cap, risk_price, unit_budget, fee_rate = tick.terms(plan.side)
        risk = risk_price * plan.quantity
        if (plan.side == "buy" and fresh_cap < plan.cap) or (plan.side == "sell" and fresh_cap > plan.cap):
            return self.refuse("price_cap_widened")
        if not _within_limits(tick.market, plan.quantity, risk, close=plan.close):
            return self.refuse("venue_order_limits")
        if not plan.close:
            if risk > MAX_OPEN or plan.margin < plan.quantity * unit_budget:
                return self.refuse("opening_budget_changed")
            if _risk_tier(tick.market, risk)["maxLeverage"] < LEVERAGE:
                return self.refuse("venue_leverage_limit")
        price, depth = tick.top(plan.side)
        if (
            plan.quantity > depth
            or (plan.side == "buy" and price > plan.cap)
            or (plan.side == "sell" and price < plan.cap)
        ):
            return self.refuse("fok_top_of_book")
        fee = price * plan.quantity * fee_rate
        self.fees += fee
        self.balance -= fee
        if plan.close:
            position = self.position
            gross = position.gross(price)
            net = gross - position.entry_fee - fee + position.funding
            self.balance += gross
            self.realized += net
            self.closed += 1
            self.wins += net > 0
            self.position = None
            return plan.side, plan.window
        self.position = Position(plan.side, plan.quantity, price, plan.margin, fee)
        return None

    def prepare(self, tick, side, kind):
        close = self.position is not None
        if close and side == self.position.side:
            return
        if not close and kind == "short-only" and side == "buy":
            return
        cap, risk_price, budget, _ = tick.terms(side)
        if close:
            quantity, margin = self.position.quantity, D(0)
        else:
            free = max(D(0), self.balance)
            allocated = (free * ALLOCATION).quantize(D("0.000001"), rounding=ROUND_FLOOR)
            affordable = (allocated / budget).quantize(LOT, rounding=ROUND_FLOOR)
            bounded = (MAX_OPEN / risk_price).quantize(LOT, rounding=ROUND_FLOOR)
            quantity = min(affordable, bounded)
            margin = allocated
            if bounded < affordable:
                reserve = quantity * (budget + risk_price * SLIP)
                margin = min(allocated, reserve.quantize(D("0.000001"), rounding=ROUND_CEILING))
        notional = risk_price * quantity
        if not _within_limits(tick.market, quantity, notional, close=close):
            return self.refuse("venue_order_limits")
        if not close and _risk_tier(tick.market, notional)["maxLeverage"] < LEVERAGE:
            return self.refuse("venue_leverage_limit")
        self.pending = Plan(side, close, quantity, cap, margin, tick.observation.window_start, tick.received_at)

    def equity(self, tick):
        mark = D(str(tick.observation.mark))
        return self.balance + (self.position.gross(mark) if self.position else 0)

    def measure_drawdown(self, tick):
        equity = self.equity(tick)
        self.peak = max(self.peak, equity)
        self.max_drawdown = max(self.max_drawdown, self.peak - equity)

    def advance(self, kind, tick, event, hours):
        if self.margin_breach:
            return
        self.apply_funding(tick, hours)
        self.measure_drawdown(tick)
        if self.position:
            mark = D(str(tick.observation.mark))
            notional = mark * self.position.quantity
            tier = _risk_tier(tick.market, notional)
            maintenance = max(D(0), notional * _decimal(tier["maintenanceMarginRatioBps"]) / 10000
                              - _decimal(tier["maintenanceAmount"], zero=True))
            collateral = (self.position.margin + self.position.gross(mark)
                          - self.position.entry_fee + self.position.funding)
            if collateral <= maintenance:
                self.margin_breach = True
                self.pending = None
                self.reverse = None
                return
        if self.pending:
            reverse = self.submit(tick)
            self.measure_drawdown(tick)
            if reverse and kind != "close-and-wait":
                if event is None or event.side == reverse[0]:
                    self.reverse = reverse
                else:
                    self.reverse = event.side, tick.observation.window_start
            return
        if event:
            self.reverse = None
            self.prepare(tick, event.side, kind)
        elif self.reverse:
            side, window = self.reverse
            self.reverse = None
            # The next distinct tick stands in for collateral settlement.
            if window == tick.observation.window_start:
                self.prepare(tick, side, kind)

    def summary(self, tick):
        comparable = not self.funding_missing and not self.margin_breach
        return {
            "net_pnl_usdc": float(self.equity(tick) - INITIAL) if comparable else None,
            "realized_net_usdc": float(self.realized) if comparable else None,
            "max_drawdown_usdc": float(self.max_drawdown) if comparable else None,
            "closed": self.closed,
            "profitable": self.wins if comparable else None,
            "fees_usdc": float(self.fees),
            "funding_usdc": float(self.funding),
            "funding_charged": self.funding_charged,
            "funding_missing": self.funding_missing,
            "margin_breach": self.margin_breach,
            "position": self.position.side if self.position else None,
            "pending": self.pending.side if self.pending else None,
            "refusals": self.refusals,
        }


def _within_limits(market, quantity, notional, *, close):
    limits = market["orderLimitConfig"]["market"]
    suffix = "Close" if close else "Open"
    return (
        _decimal(limits["minOrderQty"]) <= quantity <= _decimal(limits[f"max{suffix}OrderQty"])
        and _decimal(limits["minOrderNotional"]) <= notional <= min(
            _decimal(limits[f"max{suffix}OrderNotional"]), _decimal(market["maxAccountPositionNotional"])
        )
    )


def _risk_tier(market, notional):
    tiers = market["riskTiers"]
    return next((tier for tier in tiers if notional < _decimal(tier["notionalCap"])), tiers[-1])


def _decode_book(raw):
    for name in ("balance", "realized", "fees", "funding", "peak", "max_drawdown"):
        raw[name] = D(raw[name])
    position = raw["position"]
    if position:
        for name in ("quantity", "price", "margin", "entry_fee", "funding"):
            position[name] = D(position[name])
        raw["position"] = Position(**position)
    # A process start has no continuous venue observations for an in-flight plan.
    raw["pending"] = None
    raw["reverse"] = None
    return Book(**raw)


def _connect(path: Path):
    fd = os.open(path, os.O_CREAT | os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise OSError("paper journal must be private")
    finally:
        os.close(fd)
    return sqlite3.connect(path, timeout=5)


class PaperSession:
    def __init__(self, db):
        self.db = db
        self.engine = VoltySignalEngine()
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS paper_ticks (mark_at INTEGER PRIMARY KEY, observation TEXT NOT NULL, checkpoint TEXT NOT NULL)"
        )
        latest = db.execute("SELECT mark_at, checkpoint FROM paper_ticks ORDER BY mark_at DESC LIMIT 1").fetchone()
        self.last = None
        self.total = 0
        self.first = None
        self.books = {name: Book() for name in ARMS}
        if latest:
            self.last, payload = latest
            checkpoint = json.loads(payload)
            if checkpoint["method"] != METHOD or set(checkpoint["books"]) != set(ARMS):
                raise ValueError("paper checkpoint method mismatch")
            self.total = checkpoint["ticks"]
            self.first = checkpoint["first_mark_at"]
            self.books = {name: _decode_book(checkpoint["books"][name]) for name in ARMS}

    def gap(self):
        self.engine.reset()
        for book in self.books.values():
            if book.pending:
                book.refuse("feed_gap")
            book.pending = None
            book.reverse = None

    def observe(self, tick):
        mark_at = tick.observation.mark_at
        if self.last is not None and mark_at <= self.last:
            raise VoltyDataError("gum_no_distinct_paper_mark")
        engine, books = deepcopy(self.engine), deepcopy(self.books)
        event = engine.observe(tick.observation, now=tick.received_at)
        hours = 0 if self.last is None else mark_at // HOUR - self.last // HOUR
        for kind, book in books.items():
            book.advance(kind, tick, event, hours)
        first = self.first if self.first is not None else mark_at
        status = {
            "mode": "paper",
            "method": METHOD,
            "ticks": self.total + 1,
            "first_mark_at": first,
            "last_mark_at": mark_at,
            "variants": {name: book.summary(tick) for name, book in books.items()},
        }
        checkpoint = {**status, "books": {name: asdict(book) for name, book in books.items()}}
        observation = {**asdict(tick), "signal": None if event is None else asdict(event)}
        with self.db:
            self.db.execute("INSERT INTO paper_ticks VALUES (?,?,?)", (
                mark_at, json.dumps(observation, default=str, allow_nan=False, separators=(",", ":")),
                json.dumps(checkpoint, default=str, allow_nan=False, separators=(",", ":")),
            ))
        self.engine, self.books, self.first, self.last, self.total = engine, books, first, mark_at, self.total + 1
        return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".soltui" / "zec-volty-paper")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=2)
    args = parser.parse_args(argv)
    if not math.isfinite(args.interval) or not 1 <= args.interval <= 30:
        parser.error("interval must be between 1 and 30 seconds")
    directory = args.state_dir
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = directory.lstat()
    if (
        not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077
        or os.path.lexists(directory / "live.sqlite3")
    ):
        parser.error("paper state requires a separate private directory")
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    journal = directory / "paper.sqlite3"
    with owner(journal), closing(_connect(journal)) as db:
        session, feed = PaperSession(db), GumPaperFeed()
        last_error = None
        last_report = float("-inf")
        while not stop.is_set():
            try:
                status = session.observe(feed.read(session.last))
                now = time.monotonic()
                if not args.watch or last_error or now - last_report >= 60:
                    print(json.dumps(status), flush=True)
                    last_report = now
                last_error = None
            except (VoltyDataError, GumError, KeyError, ValueError, TypeError, IndexError, AttributeError, InvalidOperation) as error:
                duplicate = isinstance(error, VoltyDataError) and str(error) == "gum_no_distinct_paper_mark"
                if duplicate and args.watch:
                    stop.wait(args.interval)
                    continue
                if not duplicate:
                    session.gap()
                code = "awaiting_new_mark" if duplicate else "awaiting_valid_gum_market"
                if code != last_error:
                    print(json.dumps({"mode": "paper", "state": code, "ticks": session.total}), flush=True)
                last_error = code
                if not args.watch:
                    return 3
            if not args.watch:
                break
            stop.wait(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

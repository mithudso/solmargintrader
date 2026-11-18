"""Offline Pine-style order sensitivity; not a TradingView parity claim.

Callers emit ordered close-time intent lists. Orders become eligible on the
next bar. Historical OHLC order is assumed rather than observed. Quantity is
explicit and has a one-price-unit contract multiplier. Funding, spread, margin
and liquidation are not modelled.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    id: str
    action: str
    side: int
    kind: str = "market"
    stop: float | None = None
    qty: float | None = None

    def __post_init__(self) -> None:
        if not self.id or self.action not in ("entry", "cancel", "close"):
            raise ValueError("invalid intent id or action")
        if type(self.side) is not int or self.side not in (-1, 1):
            raise ValueError("side must be -1 or 1")
        if self.kind not in ("market", "stop"):
            raise ValueError("kind must be market or stop")
        if self.action != "entry" and (self.kind != "market" or self.stop is not None or self.qty is not None):
            raise ValueError("cancel and close must not specify a price or quantity")
        if self.action == "entry" and self.kind == "stop":
            if self.stop is None or not math.isfinite(self.stop) or self.stop <= 0:
                raise ValueError("stop must be a positive finite price")
        elif self.stop is not None:
            raise ValueError("market intents cannot specify stop")
        if self.qty is not None and (not math.isfinite(self.qty) or self.qty <= 0):
            raise ValueError("quantity must be positive and finite")


@dataclass(frozen=True)
class Bar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float


def simulate(bars: Sequence[Bar], intents: Sequence[Sequence[Intent]], *,
             default_qty: float, step_seconds: int, initial_capital: float = 100_000.0,
             fee_bps: float = 0.0, slippage_bps: float = 0.0,
             tie_policy: str = "low-first") -> dict[str, object]:
    """Return marked equity and order/fill events under explicit assumptions.

    Market orders fill next open. Stop orders trigger at an open that has
    already crossed the threshold or at their level within the assumed path;
    an adverse interbar gap fills at open. Long/short entries reverse positions
    and same-side entries do not pyramid. At an equal open-to-extrema distance,
    `tie_policy` selects an explicit sensitivity; the source docs do not settle
    this case. Entry rejections and venue risk rules are not simulated.
    """
    if type(step_seconds) is not int or step_seconds <= 0:
        raise ValueError("step_seconds must be a positive integer")
    if len(bars) != len(intents):
        raise ValueError("each bar needs an ordered intent list")
    if (not math.isfinite(default_qty) or default_qty <= 0 or
            not math.isfinite(initial_capital) or initial_capital <= 0 or
            not math.isfinite(fee_bps) or fee_bps < 0 or
            not math.isfinite(slippage_bps) or not 0 <= slippage_bps < 10_000):
        raise ValueError("invalid size, capital or costs")
    if tie_policy not in ("low-first", "high-first"):
        raise ValueError("unknown equal-distance policy")
    for i, b in enumerate(bars):
        if (not isinstance(b.timestamp, int) or
                any(not math.isfinite(v) or v <= 0 for v in (b.open, b.high, b.low, b.close)) or
                b.low > min(b.open, b.close) or b.high < max(b.open, b.close) or
                (i and b.timestamp - bars[i-1].timestamp != step_seconds)):
            raise ValueError("invalid ordered OHLC bar")
    cash, position, entry = initial_capital, 0.0, 0.0
    position_id: str | None = None
    pending_stops: dict[str, Intent] = {}
    pending_market: list[Intent] = []
    fills, equity = [], []
    fee_rate, slip = fee_bps/10_000, slippage_bps/10_000

    def fill(order: Intent, raw: float, ts: int) -> None:
        nonlocal cash, position, entry, position_id
        direction = order.side
        if order.action == "close":
            if not position or position_id != order.id:
                return
            direction = -1 if position > 0 else 1
        if position and (order.action == "close" or (position > 0) != (direction > 0)):
            price = raw * (1 + direction * slip)
            amount = abs(position)
            charge = amount * price * fee_rate
            cash += position * (price-entry) - charge
            fills.append({"timestamp": ts, "id": position_id, "event": "close", "side": direction,
                          "quantity": amount, "price": price, "fee": charge})
            position, position_id = 0.0, None
        if order.action == "entry" and not position:
            price = raw * (1 + direction * slip)
            quantity = order.qty if order.qty is not None else default_qty
            charge = quantity * price * fee_rate
            cash -= charge
            position, entry, position_id = direction * quantity, price, order.id
            fills.append({"timestamp": ts, "id": order.id, "event": "open", "side": direction,
                          "quantity": quantity, "price": price, "fee": charge})

    for i, bar in enumerate(bars):
        for order in pending_market:
            fill(order, bar.open, bar.timestamp)
        pending_market = []
        # Orders already crossed at the open trigger there, before intrabar path.
        for key, order in list(pending_stops.items()):
            assert order.stop is not None
            if (order.side == 1 and bar.open >= order.stop) or (order.side == -1 and bar.open <= order.stop):
                fill(order, bar.open, bar.timestamp)
                del pending_stops[key]
        high_first = (bar.high - bar.open < bar.open - bar.low or
                      (bar.high - bar.open == bar.open - bar.low and tie_policy == "high-first"))
        for side in ((1, -1) if high_first else (-1, 1)):
            ordered = sorted(pending_stops.items(), key=lambda pair: (pair[1].stop or 0) * side)
            for key, order in ordered:
                assert order.stop is not None
                if order.side == side and ((side == 1 and bar.high >= order.stop) or
                                           (side == -1 and bar.low <= order.stop)):
                    fill(order, order.stop, bar.timestamp)
                    del pending_stops[key]
        equity.append(cash + position * (bar.close-entry))
        for intent in intents[i]:
            if not isinstance(intent, Intent):
                raise TypeError("intent list must contain Intent objects")
            if intent.action == "cancel":
                pending_stops.pop(intent.id, None)
                pending_market = [x for x in pending_market if x.id != intent.id]
            elif intent.action == "close":
                if position and position_id == intent.id:
                    pending_market.append(intent)
            elif intent.kind == "market":
                pending_market.append(intent)
            else:
                assert intent.stop is not None
                # A stop already favorable relative to the creation close
                # activates immediately; its market order fills next tick.
                better = ((intent.side == 1 and intent.stop <= bar.close) or
                          (intent.side == -1 and intent.stop >= bar.close))
                if better:
                    pending_stops.pop(intent.id, None)
                    pending_market.append(Intent(intent.id, "entry", intent.side, qty=intent.qty))
                else:
                    pending_stops[intent.id] = intent
    final = equity[-1] if equity else initial_capital
    return {"final_equity": final, "return_fraction": final/initial_capital - 1,
            "open_quantity": position, "equity_curve": equity, "fills": fills,
            "pending_stops": sorted(pending_stops), "unfilled_final_market": len(pending_market),
            "model_limits": "OHLC path simulation; unit multiplier 1; no spread, funding, margin or liquidation"}

"""Pure accounting over the journal: per-strategy position (cost basis) and realized P&L per UTC day.

Only confirmed, on-chain outcomes count. The quote asset is always USDC, so cost and proceeds are exact USDC amounts
taken from the transaction itself; the base-asset quantity is the transaction's measured delta.

A position is long or flat: `qty_raw` never goes below zero, and a sell larger than the open quantity is refused by
`rails.py` before it is built. Average-cost method: a sell realizes proceeds minus average cost times the amount sold.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .tokens import QUOTE_MINT


@dataclass
class Position:
    qty_raw: int = 0
    cost_usd: Decimal = Decimal(0)


def _confirmed_trades(states: dict[str, dict[str, Any]]):
    rows = []
    for st in states.values():
        out = st.get("outcome")
        intent = st.get("intent")
        if not out or not intent or out.get("status") != "confirmed":
            continue
        rows.append((out.get("ts", 0), intent, out))
    rows.sort(key=lambda r: r[0])
    return rows


def positions(states: dict[str, dict[str, Any]], strategy: str) -> dict[str, Position]:
    """Open position by base mint for one strategy."""
    book: dict[str, Position] = {}
    for _ts, intent, out in _confirmed_trades(states):
        if intent.get("strategy") != strategy:
            continue
        side, base = intent.get("side"), intent.get("base_mint")
        if not base or side not in ("buy", "sell"):
            continue
        pos = book.setdefault(base, Position())
        qty, usdc = int(out["base_raw"]), Decimal(out["quote_usd"])
        if side == "buy":
            pos.qty_raw += qty
            pos.cost_usd += usdc
        else:
            sold = min(qty, pos.qty_raw)
            avg = pos.cost_usd / pos.qty_raw if pos.qty_raw else Decimal(0)
            pos.cost_usd -= avg * sold
            pos.qty_raw -= sold
            if pos.qty_raw == 0:
                pos.cost_usd = Decimal(0)
    return book


def utc_day(ts: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def realized_pnl_usd(states: dict[str, dict[str, Any]], day: str, strategy: str | None = None) -> Decimal:
    """Realized P&L minus network fees (in USD) of confirmed trades on one UTC day. Loss is negative."""
    total = Decimal(0)
    books: dict[tuple[str, str], Position] = {}
    for ts, intent, out in _confirmed_trades(states):
        s = intent.get("strategy")
        base, side = intent.get("base_mint"), intent.get("side")
        if not base or side not in ("buy", "sell"):
            continue
        pos = books.setdefault((s, base), Position())
        qty, usdc = int(out["base_raw"]), Decimal(out["quote_usd"])
        realized = Decimal(0)
        if side == "buy":
            pos.qty_raw += qty
            pos.cost_usd += usdc
        else:
            sold = min(qty, pos.qty_raw)
            avg = pos.cost_usd / pos.qty_raw if pos.qty_raw else Decimal(0)
            matched_share = Decimal(sold) / Decimal(qty) if qty else Decimal(0)
            realized = usdc * matched_share - avg * sold  # proceeds of an unmatched sell are not profit
            pos.cost_usd -= avg * sold
            pos.qty_raw -= sold
            if pos.qty_raw == 0:
                pos.cost_usd = Decimal(0)
        if utc_day(ts) == day and (strategy is None or s == strategy):
            total += realized - Decimal(out.get("fee_usd", "0"))
    return total


def trades_notional_usd(states: dict[str, dict[str, Any]], strategy: str, since_ts: float) -> Decimal:
    """USD notional of sends for one strategy since `since_ts`, counting anything that may have landed."""
    total = Decimal(0)
    for st in states.values():
        intent = st.get("intent")
        if not intent or intent.get("strategy") != strategy or st["state"] in ("intent",):
            continue
        if intent.get("ts", 0) >= since_ts:
            total += Decimal(intent.get("in_usd", "0"))
    return total


def is_quote(mint: str) -> bool:
    return mint == QUOTE_MINT

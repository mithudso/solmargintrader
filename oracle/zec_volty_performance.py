"""Publish verified, realized Volty performance without running the funded owner."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .cli import owner
from .gum_orders import GumError, _decimal
from .gum_webhook_orders import VENUE, client_order_id
from .zec_volty import (
    LivePolicy,
    VoltyVenue,
    _leg_rows,
    _private_state,
    _read_inbox,
    _verify_inbox_binding,
    _write_status,
)

PAGE_SIZE = 500
MAX_PAGES = 100
_USDC_LIMIT = Decimal("1e12")


@dataclass(frozen=True)
class FilledLeg:
    side: str
    size: Decimal
    first_at: int
    last_at: int
    notional: Decimal
    fees: Decimal


def _at(value, now: int) -> int:
    if type(value) is not int or not 0 < value <= now + 30:
        raise GumError("volty_performance_unverified_time")
    return value


def _usdc(value) -> Decimal:
    if not isinstance(value, str) or len(value) > 40:
        raise GumError("volty_performance_invalid_usdc")
    result = Decimal(value)
    if not result.is_finite() or abs(result) > _USDC_LIMIT or result.as_tuple().exponent < -18:
        raise GumError("volty_performance_invalid_usdc")
    return result


def _filled_leg(plan: dict, receipt: dict, now: int) -> FilledLeg:
    times, signatures = [], set()
    size = notional = fees = Decimal(0)
    for tx in receipt["transactions"]:
        if tx["type"] != "fill":
            continue
        if tx["signature"] in signatures:
            raise GumError("volty_performance_duplicate_fill")
        signatures.add(tx["signature"])
        times.append(_at(tx["timestamp"], now))
        quantity = _decimal(tx["size"])
        size += quantity
        notional += quantity * _decimal(tx["price"])
        fees += _decimal(tx["fee"], zero=True)
    if (
        not times or size != _decimal(receipt["filled_quantity"]) or size != _decimal(plan["quantity"])
        or fees != _decimal(receipt["actual_fee_usdc"], zero=True)
    ):
        raise GumError("volty_performance_incomplete_fills")
    return FilledLeg(plan["side"], size, min(times), max(times), notional, fees)


def _journal_trades(venue: VoltyVenue, now: int) -> tuple[set, dict]:
    identity = {"owner": venue.owner, "account_id": venue.account_id, "subaccount_id": venue.subaccount_id, "symbol": "ZEC"}
    orders, trades = set(), {}
    opened = None
    with _read_inbox(venue.path) as db:
        # A read transaction freezes the binding and all durable legs at the same revision.
        db.execute("BEGIN")
        _verify_inbox_binding(db, venue.binding)
        for row in _leg_rows(db):
            state = json.loads(row["plan"])
            binding = row["portfolio_id"]
            if state["binding"] != binding or state["venue"] != VENUE:
                raise GumError("volty_performance_unverified_plan")
            for index, leg in enumerate(state["legs"]):
                receipt = leg.get("receipt") or {}
                if leg["state"] != "filled":
                    if _decimal(receipt.get("filled_quantity", "0"), zero=True):
                        raise GumError("volty_performance_pending_fill")
                    continue
                plan = leg["plan"]
                action = plan["action"]
                order = (receipt["order_id"], receipt["client_order_id"])
                if (
                    action not in ("open", "close") or plan["side"] not in ("buy", "sell")
                    or plan["binding"] != binding or receipt["status"] != "filled" or order in orders
                    or leg["client_order_id"] != client_order_id(binding, row["event_id"], index)
                    or order[1] != leg["client_order_id"] or receipt["side"] != plan["side"]
                    or plan["reduce_only"] is not (action == "close")
                    or receipt["reduce_only"] is not (action == "close") or receipt["isolated"] is not True
                    or any(values[key] != expected for values in (plan, receipt) for key, expected in identity.items())
                ):
                    raise GumError("volty_performance_unverified_fill")
                orders.add(order)
                filled = _filled_leg(plan, receipt, now)
                if action == "open":
                    if opened is not None:
                        raise GumError("volty_performance_overlapping_open")
                    opened = filled
                    continue
                if (
                    opened is None or filled.side == opened.side or filled.size != opened.size
                    or filled.first_at < opened.last_at or receipt["settled"] is not True
                ):
                    raise GumError("volty_performance_unverified_close")
                side = "Bid" if opened.side == "buy" else "Ask"
                gross = filled.notional - opened.notional if side == "Bid" else opened.notional - filled.notional
                key = (side, opened.first_at, filled.last_at, filled.size)
                if key in trades:
                    raise GumError("volty_performance_ambiguous_trade")
                trades[key] = (gross, opened.fees + filled.fees)
                opened = None
    return orders, trades


def _closed_positions(venue: VoltyVenue):
    for page in range(MAX_PAGES):
        data = venue._get(
            f"/tradingAccount/{venue.account_id}/positionHistory?symbol=ZEC&limit={PAGE_SIZE}&offset={page * PAGE_SIZE}"
        )
        if not isinstance(data, dict) or not isinstance(data.get("entries"), list) or len(data["entries"]) > PAGE_SIZE:
            raise GumError("volty_performance_invalid_history")
        yield from data["entries"]
        if len(data["entries"]) < PAGE_SIZE:
            return
    raise GumError("volty_performance_incomplete_pagination")


def performance_snapshot(venue: VoltyVenue, *, now: int | None = None) -> dict:
    """Match indexed closed positions to bot-owned fills before using venue funding."""
    now = int(time.time()) if now is None else now
    orders, expected = _journal_trades(venue, now)
    venue._account()
    if venue.filled_order_identifiers() != orders:
        raise GumError("volty_performance_unverified_order_history")
    gross = net = Decimal(0)
    wins = closed = 0
    for row in _closed_positions(venue):
        if row["symbol"] != "ZEC" or row["isolated"] is not True or row["closeReason"] != "trade":
            raise GumError("volty_performance_foreign_position")
        key = (row["side"], _at(row["openedAt"], now), _at(row["closedAt"], now), _decimal(row["closedSize"]))
        realized, fees, funding, after_costs = (_usdc(row[field]) for field in ("realizedPnl", "fees", "funding", "netPnl"))
        if expected.pop(key, None) != (realized, fees) or after_costs != realized - fees + funding:
            raise GumError("volty_performance_unmatched_position")
        gross += realized
        net += after_costs
        wins += after_costs > 0
        closed += 1
    if expected or abs(gross) > _USDC_LIMIT or abs(net) > _USDC_LIMIT:
        raise GumError("volty_performance_incomplete_history")
    return {"schema": 1, "updated_at": now, "gross_pnl_usdc": float(gross), "net_pnl_usdc": float(net),
            "closed_trades": closed, "profitable_trades": wins}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--state-dir", type=Path, default=Path.home() / ".soltui" / "zec-volty")
    args = parser.parse_args(argv)
    try:
        state = _private_state(args.state_dir, create=False)
        path = state / "performance.json"
        with owner(path):
            venue = VoltyVenue(LivePolicy.load(args.config), state / "live.sqlite3")
            _write_status(path, performance_snapshot(venue))
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, InvalidOperation, sqlite3.Error):
        # Leave the last verified snapshot and its original timestamp available.
        print("Volty performance could not be verified.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

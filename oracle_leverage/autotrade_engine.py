"""Observed-path paper execution models; no claim of venue fills or settlement."""

from __future__ import annotations

import copy
import math

from oracle_leverage.exit50 import quote_position

PRICE_SCALE = 100_000_000
MONEY_SCALE = 1_000_000


def _number(value, *, positive=False):
    return (
        type(value) in (int, float)
        and math.isfinite(value)
        and (not positive or value > 0)
    )


def _mark(price):
    value = round(price * PRICE_SCALE)
    if value <= 0:
        raise ValueError("paper price below integer precision")
    return value


def _yolo(plan, price):
    return quote_position(
        plan["margin_micro"],
        plan["notional_micro"],
        plan["entry_int"],
        _mark(price),
        plan["direction"].upper(),
        20,
        30_000,
        25,
    )


def worst_loss(collateral, leverage):
    """Conservative reserve for collateral, two fees and max modeled holding."""
    if leverage == 1000:
        return collateral * (1 + 2 * 1000 * 0.00002 + 1000 * 0.000001 * 914 / 3600)
    if leverage == 10:
        return collateral * (1 + 2 * 10 * 0.0005 + 10 * 0.0001 * 914 / 3600)
    raise ValueError("unsupported paper leverage")


def _target_1000(plan):
    """Find observed-price proxy reaching 50% after stated modeled extra costs."""
    entry = plan["entry_int"]
    margin = plan["margin_micro"]
    slip = plan["slippage_rate"]
    sign = 1 if plan["direction"] == "long" else -1
    extra = plan["entry_fee_usd"] + plan["max_borrow_usd"]

    def reached(observed):
        mark = max(1, round(observed * (1 - sign * slip)))
        q = quote_position(
            margin,
            plan["notional_micro"],
            entry,
            mark,
            plan["direction"].upper(),
            20,
            30_000,
            25,
        )
        return (
            not q["liquidatable"]
            and (q["payout"] - margin) / MONEY_SCALE - extra
            >= plan["collateral_usd"] * 0.5
        )

    if sign == 1:
        low, high = entry, entry * 100
        if not reached(high):
            raise ValueError("modeled target unreachable")
        while low < high:
            mid = (low + high) // 2
            if reached(mid):
                high = mid
            else:
                low = mid + 1
        return low / PRICE_SCALE
    low, high = 1, entry
    if not reached(low):
        raise ValueError("modeled target unreachable")
    while low < high:
        mid = (low + high + 1) // 2
        if reached(mid):
            low = mid
        else:
            high = mid - 1
    return low / PRICE_SCALE


def make_plan(*, at, price, direction, collateral, leverage=10.0):
    if not all(_number(x, positive=True) for x in (at, price, collateral, leverage)):
        raise ValueError("invalid plan input")
    if direction not in ("long", "short") or leverage not in (10, 1000):
        raise ValueError("invalid paper direction or leverage")
    sign = 1 if direction == "long" else -1
    slip = 0.00001 if leverage == 1000 else 0.0005
    fee = 0.00002 if leverage == 1000 else 0.0005
    borrow_rate = 0.000001 if leverage == 1000 else 0.0001
    fill = price * (1 + sign * slip)
    plan = {
        "version": 2,
        "model_version": "exit50-proxy-v1" if leverage == 1000 else "linear-10x-v1",
        "created_at": at,
        "direction": direction,
        "reference_price": price,
        "target_entry": price,
        "entry_fill": fill,
        "collateral_usd": collateral,
        "leverage": leverage,
        "minimum_hold_seconds": 15,
        "max_hold_seconds": 900,
        "close_delay_seconds": 10,
        "max_observation_gap_seconds": 2,
        "fee_rate_per_side": fee,
        "slippage_rate": slip,
        "borrow_rate_per_hour": borrow_rate,
        "entry_fee_usd": collateral * leverage * fee,
        "max_borrow_usd": collateral * leverage * borrow_rate * 914 / 3600,
        "price_basis": "jupiter-oracle-usd",
        "entry_latency_seconds": 0,
        "cost_scope": "modeled open fee, close fee, slippage and borrow; excludes network/keeper and any unknown venue costs",
        "assumptions": "Observed-path paper proxy only; provider can coalesce updates; not venue fill or settlement",
    }
    if leverage == 1000:
        margin = round(collateral * MONEY_SCALE)
        if margin <= 0:
            raise ValueError("collateral below integer precision")
        plan.update(
            margin_micro=margin, notional_micro=margin * 1000, entry_int=_mark(fill)
        )
        q = _yolo(plan, fill)
        adverse = (
            q["available_collateral"] * plan["entry_int"] + plan["notional_micro"] - 1
        ) // plan["notional_micro"]
        liq_int = (
            plan["entry_int"] - adverse if sign == 1 else plan["entry_int"] + adverse
        )
        if liq_int <= 0:
            raise ValueError("invalid modeled liquidation")
        plan["liquidation_price"] = liq_int / PRICE_SCALE
        plan["stop_price"] = (fill + plan["liquidation_price"]) / 2
        plan["target_price"] = _target_1000(plan)
    else:
        target_return = 0.5 / leverage + 0.001 + 0.0001 * 914 / 3600
        plan.update(
            target_price=fill * (1 + sign * target_return) / (1 - sign * slip),
            stop_price=fill * (1 - sign * 0.04),
            liquidation_price=fill * (1 - sign / leverage),
        )
    return plan


def open_position(plan, at):
    if at != plan["created_at"]:
        raise ValueError("plan must be frozen at entry")
    return {
        "plan": copy.deepcopy(plan),
        "state": "open",
        "opened_at": at,
        "last_at": at,
        "last_price": plan["reference_price"],
        "close_at": None,
        "submit_at": None,
        "trigger": None,
        "trigger_price": None,
        "exit_price": None,
        "net_pnl_usd": None,
        "outcome": None,
        "pnl_scope": "modeled net excludes unknown network, keeper, and venue costs",
    }


def step(position, *, at, price, basis="jupiter-oracle-usd", max_gap=2.0, stop=False):
    p = copy.deepcopy(position)
    if p["state"] not in ("open", "closing"):
        raise ValueError("position already terminal")
    if (
        not _number(at, positive=True)
        or not _number(price, positive=True)
        or basis != p["plan"]["price_basis"]
        or at <= p["last_at"]
        or at - p["last_at"] > max_gap
    ):
        p.update(
            state="unknown",
            outcome="unknown",
            reason="invalid, missing, stale, out-of-order or wrong-basis observation",
        )
        return p
    plan = p["plan"]
    sign = 1 if plan["direction"] == "long" else -1
    p["last_at"], p["last_price"] = at, price
    touched = (
        _yolo(plan, price)["liquidatable"]
        if plan["leverage"] == 1000
        else sign * (price - plan["liquidation_price"]) <= 0
    )
    if touched:
        borrow = (
            plan["collateral_usd"]
            * plan["leverage"]
            * plan["borrow_rate_per_hour"]
            * (at - p["opened_at"])
            / 3600
        )
        p.update(
            state="liquidated",
            outcome="failure",
            exit_price=price,
            fees_usd=plan["entry_fee_usd"],
            borrow_usd=borrow,
            net_pnl_usd=-plan["collateral_usd"] - plan["entry_fee_usd"] - borrow,
            exited_at=at,
        )
        return p
    elapsed = at - p["opened_at"]
    if p["state"] == "open":
        trigger = (
            "stop_requested"
            if stop
            else "stop_loss"
            if sign * (price - plan["stop_price"]) <= 0
            else "take_profit"
            if sign * (price - plan["target_price"]) >= 0
            else "max_hold"
            if elapsed >= plan["max_hold_seconds"]
            else None
        )
        if trigger:
            submit_at = max(at, p["opened_at"] + plan["minimum_hold_seconds"])
            p.update(
                state="closing",
                trigger=trigger,
                trigger_price=price,
                submit_at=submit_at,
                close_at=submit_at + plan["close_delay_seconds"],
            )
    elif at >= p["close_at"]:
        exit_fill = price * (1 - sign * plan["slippage_rate"])
        notional = plan["collateral_usd"] * plan["leverage"]
        borrow = notional * plan["borrow_rate_per_hour"] * elapsed / 3600
        if (
            plan["leverage"] == 10
            and sign * (exit_fill - plan["liquidation_price"]) <= 0
        ):
            p.update(
                state="liquidated",
                outcome="failure",
                exit_price=exit_fill,
                fees_usd=plan["entry_fee_usd"],
                borrow_usd=borrow,
                net_pnl_usd=-plan["collateral_usd"] - plan["entry_fee_usd"] - borrow,
                exited_at=at,
            )
            return p
        if plan["leverage"] == 1000:
            q = _yolo(plan, exit_fill)
            if q["liquidatable"]:
                p.update(
                    state="liquidated",
                    outcome="failure",
                    exit_price=exit_fill,
                    fees_usd=plan["entry_fee_usd"],
                    borrow_usd=borrow,
                    net_pnl_usd=-plan["collateral_usd"]
                    - plan["entry_fee_usd"]
                    - borrow,
                    exited_at=at,
                )
                return p
            gross = (q["adjusted_profit"] - q["loss"]) / MONEY_SCALE
            fees = plan["entry_fee_usd"] + (q["close_fee"] + q["win_fee"]) / MONEY_SCALE
            net = gross - fees - borrow
            p["modeled_payout_usd"] = q["payout"] / MONEY_SCALE
            p["modeled_close_fee_usd"] = q["close_fee"] / MONEY_SCALE
            p["modeled_win_fee_usd"] = q["win_fee"] / MONEY_SCALE
        else:
            gross = notional * sign * (exit_fill / plan["entry_fill"] - 1)
            fees = 2 * plan["entry_fee_usd"]
            net = gross - fees - borrow
        if net < -worst_loss(plan["collateral_usd"], plan["leverage"]) - 1e-9:
            p.update(
                state="unknown",
                outcome="unknown",
                reason="modeled loss exceeded reserved risk",
            )
            return p
        p.update(
            state="closed",
            outcome="win" if net > 0 else "loss",
            exit_price=exit_fill,
            exit_observed_price=price,
            exited_at=at,
            gross_pnl_usd=gross,
            fees_usd=fees,
            borrow_usd=borrow,
            net_pnl_usd=net,
        )
    return p

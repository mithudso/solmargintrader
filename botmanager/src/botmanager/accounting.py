"""Pure cash-flow and FIFO accounting; unavailable inputs never become zero.

Exact ledgers use decimal strings. Canonical simulator checkpoints retain their
original float lineage and are never silently re-priced by the FIFO projection.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any


def measurement(value, reason=None):
    return {
        "value": str(value) if isinstance(value, Decimal) else value,
        "reason": reason,
    }


def _decimal(value):
    if isinstance(value, bool) or value is None or isinstance(value, float):
        raise ValueError("exact_decimal_required")
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("invalid_decimal") from None
    if not result.is_finite():
        raise ValueError("invalid_decimal")
    return result


def _reference(run):
    cp = run.get("checkpoint") or {}
    descriptor = run.get("input", {}).get("descriptor", {})
    starting = descriptor.get("capital_quote")
    fields = {
        "cash": cp.get("cash_quote"),
        "marked_inventory": cp.get("exposure_quote"),
        "equity": cp.get("equity_quote"),
        "realized_net_pnl": cp.get("realized_net_pnl_quote"),
        "unrealized_net_pnl": cp.get("unrealized_net_pnl_quote"),
        "fees": cp.get("fees_quote"),
        "slippage": cp.get("slippage_quote"),
        "carry_paid": cp.get("carry_paid_quote"),
        "carry_accrued": cp.get("carry_accrued_quote"),
        "starting_equity": starting,
    }
    fields["net_pnl"] = (
        fields["equity"] - starting
        if fields["equity"] is not None and starting is not None
        else None
    )
    return {
        "schema_version": 1,
        "arithmetic": "canonical_simulator_float",
        "currency": cp.get("quote_currency", descriptor.get("quote_currency")),
        "account_scope": "independent_virtual_account_not_funded_wallet",
        **{
            k: measurement(
                v, None if v is not None else "checkpoint_measurement_unavailable"
            )
            for k, v in fields.items()
        },
        "realized_gross_pnl": measurement(
            None, "simulator_does_not_attribute_gross_fifo"
        ),
        "deposits": measurement(0, "reference_account_has_no_external_cashflows"),
        "withdrawals": measurement(0, "reference_account_has_no_external_cashflows"),
        "residuals": cp.get("lots"),
    }


def accounting_snapshot(run: Mapping[str, Any]) -> dict[str, Any]:
    """Project an exact event ledger or a pinned reference checkpoint.

    Exact input: starting_equity, currency, fills[{side,quantity,price,fee}],
    cashflows[{kind,amount}] and marks[asset]. Fills default to asset ``base``.
    Cashflow kinds: deposit, withdrawal, expense, rent_lock, rent_refund.
    Fees are quote-denominated and mandatory on every fill, including zero.
    """
    if "input" in run and "spec" in run:
        return _reference(run)
    with localcontext() as context:
        context.prec = 80
        return _exact(run)


def _exact(run):
    reasons = []
    unknown_cost = False
    try:
        starting = _decimal(run.get("starting_equity"))
        cash = starting
    except ValueError:
        starting = cash = None
        reasons.append("starting_equity_unavailable")
    zero = Decimal(0)
    deposits = withdrawals = fees = expenses = rent = realized = realized_gross = zero
    lots = {}
    try:
        for event in run.get("cashflows", []):
            amount = _decimal(event.get("amount"))
            if amount < 0:
                raise ValueError("negative_cashflow")
            kind = event.get("kind")
            if kind == "deposit":
                deposits += amount
            elif kind == "withdrawal":
                withdrawals += amount
            elif kind == "expense":
                expenses += amount
            elif kind == "rent_lock":
                rent += amount
            elif kind == "rent_refund" and amount <= rent:
                rent -= amount
            else:
                raise ValueError("cashflow_kind_or_rent_invalid")
            if cash is not None:
                cash += amount if kind in ("deposit", "rent_refund") else -amount
        for fill in run.get("fills", []):
            quantity, price = (
                _decimal(fill.get("quantity")),
                _decimal(fill.get("price")),
            )
            if quantity <= 0 or price <= 0:
                raise ValueError("invalid_fill_size_or_price")
            try:
                fee = _decimal(fill.get("fee"))
                if fee < 0:
                    raise ValueError("invalid_fee")
            except ValueError:
                unknown_cost = True
                reasons.append("fill_fee_unavailable")
                fee = zero  # Arithmetic placeholder; every affected net value is null below.
            fees += fee
            asset = fill.get("asset", "base")
            inventory = lots.setdefault(asset, [])
            notional = quantity * price
            if fill.get("side") == "buy":
                inventory.append([quantity, price, fee])
                if cash is not None:
                    cash -= notional + fee
            elif fill.get("side") == "sell":
                remaining, basis, entry_fee = quantity, zero, zero
                while remaining and inventory:
                    lot = inventory[0]
                    used = min(remaining, lot[0])
                    allocated = lot[2] * used / lot[0]
                    basis += used * lot[1]
                    entry_fee += allocated
                    lot[0] -= used
                    lot[2] -= allocated
                    remaining -= used
                    if not lot[0]:
                        inventory.pop(0)
                if remaining:
                    raise ValueError("sell_exceeds_known_inventory")
                realized_gross += notional - basis
                realized += notional - basis - entry_fee - fee
                if cash is not None:
                    cash += notional - fee
            else:
                raise ValueError("invalid_fill_side")
    except (ValueError, TypeError, KeyError) as exc:
        reasons.append(
            str(exc) if isinstance(exc, ValueError) else "invalid_accounting_event"
        )
        unknown_cost = True
        cash = None
    traded, basis, retained_fees = zero, zero, zero
    missing_mark = False
    residuals = []
    for asset, inventory in lots.items():
        quantity = sum((lot[0] for lot in inventory), zero)
        basis += sum((lot[0] * lot[1] for lot in inventory), zero)
        retained_fees += sum((lot[2] for lot in inventory), zero)
        if quantity:
            try:
                mark = _decimal(run.get("marks", {}).get(asset))
                if mark <= 0:
                    raise ValueError("invalid_mark")
                traded += quantity * mark
            except ValueError:
                missing_mark = True
                reasons.append("inventory_mark_unavailable:" + str(asset))
            residuals.append({"asset": asset, "quantity": str(quantity)})
    marked = None if missing_mark else traded + rent
    equity = (
        cash + marked
        if cash is not None and marked is not None and not unknown_cost
        else None
    )
    net = (
        equity - starting - deposits + withdrawals
        if equity is not None and starting is not None
        else None
    )
    reason = ";".join(dict.fromkeys(reasons)) or None
    values = {
        "starting_equity": starting,
        "cash": cash if not unknown_cost else None,
        "marked_inventory": marked,
        "traded_inventory": None if missing_mark else traded,
        "refundable_rent_asset": rent,
        "equity": equity,
        "net_pnl": net,
        "realized_gross_pnl": realized_gross if not unknown_cost else None,
        "realized_net_pnl": realized if not unknown_cost else None,
        "unrealized_net_pnl": None
        if missing_mark or unknown_cost
        else traded - basis - retained_fees,
        "deposits": deposits,
        "withdrawals": withdrawals,
        "fees": None if unknown_cost else fees,
        "transaction_expense": expenses,
    }
    return {
        "schema_version": 1,
        "arithmetic": "decimal",
        "currency": run.get("currency"),
        "account_scope": run.get("account_scope", "single_account"),
        **{k: measurement(v, reason if v is None else None) for k, v in values.items()},
        "residuals": residuals,
        "uncertainties": list(dict.fromkeys(reasons)),
    }

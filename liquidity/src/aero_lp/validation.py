"""Shared numeric validation for safety settings. Never coerce TOML strings or booleans."""

from __future__ import annotations

import math


def finite_number(value: object, name: str, *, positive: bool = False, integer: bool = False) -> None:
    """Require a finite nonnegative number, or a positive one; integer fields require int."""
    try:
        finite = isinstance(value, int | float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not finite
        or (integer and not isinstance(value, int))
        or (value <= 0 if positive else value < 0)
    ):
        domain = "positive" if positive else "nonnegative"
        kind = "integer" if integer else "number"
        raise ValueError(f"{name} must be a finite {domain} {kind}")


def measured_gas(values: dict[str, int]) -> int:
    """Require nonempty, positive measured gas for every simulated transaction label."""
    if not values:
        raise RuntimeError("simulation did not report gas usage")
    try:
        for gas in values.values():
            finite_number(gas, "simulated gas", positive=True, integer=True)
    except ValueError as error:
        raise RuntimeError(f"invalid measured simulation gas: {error}") from error
    return sum(values.values())

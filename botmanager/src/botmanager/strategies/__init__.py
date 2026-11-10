"""One canonical strategy dispatcher for workers, ledger and command surfaces."""

from __future__ import annotations

from ..data import engine_identity
from ..domain import ManagerError, fingerprint
from . import grid
from .base import compatible_engine, evaluate_family, identity, validate_input


def evaluate(spec, data, cursor):
    if spec.strategy_id == "grid":
        return grid.evaluate(spec, data, cursor)
    return evaluate_family(spec, data, cursor)


def validate_registration(spec, data):
    validate_input(spec, data)
    if not compatible_engine(
        data["identity"]["engine_identity"], engine_identity(spec.strategy_id)
    ):
        raise ManagerError(
            "engine_identity_changed",
            "Pinned economic engine differs from loaded code.",
            3,
        )
    if data["bars"]:
        evaluate(spec, data, 1)
    elif data.get("prospective") is None:
        raise ManagerError("input_unavailable", "No completed reference bars.", 3)


def validate_checkpoint(spec, data, checkpoint, *, code="corrupt_checkpoint"):
    if spec.strategy_id == "grid":
        return grid.validate_checkpoint(spec, data, checkpoint, code=code)
    try:
        expected = identity(spec, data)
        cursor = checkpoint["cursor"]
        if (
            checkpoint["schema_version"] != 1
            or type(cursor) is not int
            or not 1 <= cursor <= len(data["bars"])
            or checkpoint["last_bar_ts"] != data["bars"][cursor - 1]["ts"]
            or checkpoint["quote_currency"] != data["identity"]["quote_currency"]
            or checkpoint["identity"] != expected
            or checkpoint["run_hash"] != fingerprint(expected)
        ):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise ManagerError(
            code, "Checkpoint differs from pinned reference run.", 4
        ) from exc

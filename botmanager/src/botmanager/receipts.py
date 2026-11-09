"""Validated per-bot control records, separate from transport success envelopes.

No receipt is produced by draft controls. Actual owners must supply outcomes in
the delegated-control milestone. Acknowledgment is not proof of cleared exposure.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

from .domain import ManagerError, freeze, plain

RECEIPT_SCHEMA_VERSION = 1
ControlOperation = Literal[
    "start",
    "pause_entries",
    "stop",
    "cancel_orders",
    "close_position",
    "emergency_stop",
]
ControlOutcome = Literal["acknowledged", "pending", "skipped", "failed", "unknown"]
ConfigRevisionUnavailableReason = Literal["owner_does_not_version_configurations"]
OPERATIONS = (
    "start",
    "pause_entries",
    "stop",
    "cancel_orders",
    "close_position",
    "emergency_stop",
)
OUTCOMES = ("acknowledged", "pending", "skipped", "failed", "unknown")


def _reference(value: Any) -> bool:
    return (
        type(value) is str
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}", value) is not None
    )


def _invalid() -> ManagerError:
    # Never reflect owner response bodies, submitted values or parser exceptions.
    return ManagerError(
        "invalid_receipt", "The control receipt is invalid or incompatible.", 4
    )


@dataclass(frozen=True, kw_only=True)
class CommandReceipt:
    schema_version: int
    bot_id: str
    operation: ControlOperation
    request_id: str
    runtime_id: str | None
    owner_id: str | None
    owner_generation: int | None
    config_revision: int | None
    outcome: ControlOutcome
    reason: str
    config_revision_unavailable_reason: ConfigRevisionUnavailableReason | None = None
    metadata: Mapping[str, str | int | float] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        try:
            if (
                type(self.schema_version) is not int
                or self.schema_version != RECEIPT_SCHEMA_VERSION
            ):
                raise ValueError
            for identity in (self.bot_id, self.request_id):
                if type(identity) is not str or str(UUID(identity)) != identity:
                    raise ValueError
            if type(self.operation) is not str or self.operation not in OPERATIONS:
                raise ValueError
            if type(self.outcome) is not str or self.outcome not in OUTCOMES:
                raise ValueError
            for identity in (self.runtime_id, self.owner_id):
                if identity is not None and not _reference(identity):
                    raise ValueError
            if self.owner_generation is not None and (
                type(self.owner_generation) is not int or self.owner_generation < 0
            ):
                raise ValueError
            if self.config_revision is None:
                if (
                    type(self.config_revision_unavailable_reason) is not str
                    or self.config_revision_unavailable_reason
                    != "owner_does_not_version_configurations"
                ):
                    raise ValueError
            elif (
                type(self.config_revision) is not int
                or self.config_revision < 1
                or self.config_revision_unavailable_reason is not None
            ):
                raise ValueError
            if (
                type(self.reason) is not str
                or re.fullmatch(r"[a-z][a-z0-9_]{0,99}", self.reason) is None
            ):
                raise ValueError
            if not isinstance(self.metadata, Mapping):
                raise TypeError
            # A reference-only allowlist prevents arbitrary owner bodies or keys
            # from becoming a durable receipt or leaking through serialization.
            for key, value in self.metadata.items():
                if type(key) is not str:
                    raise ValueError
                if key in ("detail_ref", "reconciliation_ref", "owner_revision"):
                    if not _reference(value):
                        raise ValueError
                elif key == "config_hash":
                    if (
                        type(value) is not str
                        or re.fullmatch(r"[0-9a-f]{64}", value) is None
                    ):
                        raise ValueError
                elif key == "elapsed_seconds":
                    if (
                        type(value) not in (int, float)
                        or not math.isfinite(value)
                        or value < 0
                    ):
                        raise ValueError
                else:
                    raise ValueError
        except (ValueError, TypeError, AttributeError, OverflowError) as exc:
            raise _invalid() from exc
        object.__setattr__(self, "metadata", freeze(self.metadata))

    @property
    def safe_to_retry(self) -> bool:
        # No outcome alone proves replay safety. The owner must first reconcile.
        return False

    @property
    def reconciliation_required(self) -> bool:
        return self.outcome == "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            **{key: plain(getattr(self, key)) for key in self.__dataclass_fields__},
            "safe_to_retry": self.safe_to_retry,
            "reconciliation_required": self.reconciliation_required,
        }

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> CommandReceipt:
        try:
            if not isinstance(body, Mapping):
                raise TypeError
            fields = set(cls.__dataclass_fields__)
            flags = {"safe_to_retry", "reconciliation_required"}
            if not set(body) <= fields | flags:
                raise ValueError
            receipt = cls(
                **{key: value for key, value in body.items() if key in fields}
            )
            for key in flags & set(body):
                if type(body[key]) is not bool or body[key] != getattr(receipt, key):
                    raise ValueError
            return receipt
        except (ValueError, TypeError) as exc:
            raise _invalid() from exc

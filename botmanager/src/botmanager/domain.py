"""Versioned immutable specifications; no owner imports or state access."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from uuid import UUID, uuid4

SCHEMA_VERSION = 1


class ManagerError(Exception):
    """Only fixed, credential-free messages may cross the command boundary."""

    def __init__(self, code: str, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.exit_code = exit_code


def plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(item) for item in value)
    return value


def canonical(value: Any) -> str:
    return json.dumps(
        plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class ResolvedConfig:
    values: Mapping[str, Any]
    provenance: Mapping[str, Mapping[str, Any]]
    user_overrides: Mapping[str, Any]
    shared_compatibility: Mapping[str, Any]

    def __post_init__(self) -> None:
        for field in ("values", "provenance", "user_overrides", "shared_compatibility"):
            object.__setattr__(self, field, freeze(getattr(self, field)))


@dataclass(frozen=True)
class BotSpec:
    schema_version: int
    bot_id: str
    display_name: str
    source: str
    owner: str
    source_identity: str
    strategy_id: str
    strategy_version: str
    mode: str
    venue: str
    base_mint: str
    quote_mint: str
    bar_seconds: int
    execution_model: str
    config_revision: int
    config_hash: str
    resolved_values: Mapping[str, Any]
    provenance: Mapping[str, Mapping[str, Any]]
    user_overrides: Mapping[str, Any]
    shared_compatibility: Mapping[str, Any]
    created_at: str

    def __post_init__(self) -> None:
        from .config import STRATEGY_VERSIONS, validate_values

        try:
            if (
                self.schema_version != SCHEMA_VERSION
                or type(self.schema_version) is not int
            ):
                raise ValueError
            if str(UUID(self.bot_id)) != self.bot_id:
                raise ValueError
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._-]{0,79}", self.display_name):
                raise ValueError
            # Names cannot shadow another bot's UUID lookup.
            if re.fullmatch(r"[0-9a-fA-F-]{36}", self.display_name):
                raise ValueError
            if (
                self.source != "manager"
                or self.owner != "manager"
                or self.source_identity != self.bot_id
            ):
                raise ValueError
            if self.strategy_version != STRATEGY_VERSIONS[self.strategy_id]:
                raise ValueError
            if type(self.config_revision) is not int or self.config_revision < 1:
                raise ValueError
            validate_values(self.strategy_id, self.resolved_values)
            for key in (
                "mode",
                "venue",
                "base_mint",
                "quote_mint",
                "bar_seconds",
                "execution_model",
            ):
                if getattr(self, key) != self.resolved_values[key]:
                    raise ValueError
            if set(self.resolved_values) != set(self.provenance):
                raise ValueError
            if not set(self.user_overrides) <= set(self.resolved_values):
                raise ValueError
            for value in self.provenance.values():
                if set(value) != {"source", "source_revision", "reason"}:
                    raise ValueError
                if value["source"] not in ("packaged", "shared", "override", "context"):
                    raise ValueError
                if not all(isinstance(item, str) and item for item in value.values()):
                    raise ValueError
            if self.config_hash != fingerprint(self._config_body()):
                raise ValueError
            datetime.fromisoformat(self.created_at)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ManagerError(
                "invalid_spec",
                "The stored bot specification is invalid or incompatible.",
                4,
            ) from exc
        for key in (
            "resolved_values",
            "provenance",
            "user_overrides",
            "shared_compatibility",
        ):
            object.__setattr__(self, key, freeze(getattr(self, key)))

    def _config_body(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_version": self.strategy_version,
            "config_revision": self.config_revision,
            "resolved_values": self.resolved_values,
            "provenance": self.provenance,
            "user_overrides": self.user_overrides,
            "shared_compatibility": self.shared_compatibility,
        }

    @classmethod
    def create(
        cls, display_name: str, strategy_id: str, resolved: ResolvedConfig
    ) -> BotSpec:
        from .config import STRATEGY_VERSIONS

        bot_id = str(uuid4())
        body = {
            "strategy_id": strategy_id,
            "strategy_version": STRATEGY_VERSIONS[strategy_id],
            "config_revision": 1,
            "resolved_values": resolved.values,
            "provenance": resolved.provenance,
            "user_overrides": resolved.user_overrides,
            "shared_compatibility": resolved.shared_compatibility,
        }
        metadata = {
            key: resolved.values[key]
            for key in (
                "mode",
                "venue",
                "base_mint",
                "quote_mint",
                "bar_seconds",
                "execution_model",
            )
        }
        return cls(
            schema_version=1,
            bot_id=bot_id,
            display_name=display_name,
            source="manager",
            owner="manager",
            source_identity=bot_id,
            config_hash=fingerprint(body),
            created_at=utc_now(),
            **body,
            **metadata,
        )

    def to_dict(self) -> dict[str, Any]:
        return {key: plain(getattr(self, key)) for key in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> BotSpec:
        try:
            return cls(**body)
        except (TypeError, ValueError) as exc:
            raise ManagerError(
                "invalid_spec",
                "The stored bot specification is invalid or incompatible.",
                4,
            ) from exc

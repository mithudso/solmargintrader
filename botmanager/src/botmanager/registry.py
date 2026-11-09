"""One application registry, shared by CLI and future local transports."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import resolve_config
from .domain import BotSpec, ManagerError
from .store import ManagerStore


@dataclass(frozen=True)
class CommandContext:
    home: Path | None = None
    shared_snapshot: Mapping[str, Any] | None = None
    installations: tuple[Any, ...] = ()
    owner_adapters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CommandSpec:
    name: str
    description: str
    handler: Callable[[Mapping[str, Any], CommandContext], dict[str, Any]]
    arguments: tuple[tuple[tuple[str, ...], dict[str, Any]], ...] = ()


def _store(context: CommandContext) -> ManagerStore:
    return ManagerStore(context.home)


def _identity(params: Mapping[str, Any], context: CommandContext) -> BotSpec:
    identity = params.get("identity")
    if not isinstance(identity, str) or not identity:
        raise ManagerError("invalid_input", "A bot identity is required.")
    spec = _store(context).get_spec(identity)
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    return spec


def _settings(params: Mapping[str, Any]) -> dict[str, Any]:
    overrides = params.get("overrides", {})
    if not isinstance(overrides, Mapping):
        raise ManagerError("invalid_input", "Settings must be a mapping.")
    result = dict(overrides)
    settings = params.get("set", [])
    if not isinstance(settings, (list, tuple)):
        raise ManagerError("invalid_input", "Settings must use key=value syntax.")
    for item in settings:
        if not isinstance(item, str) or "=" not in item:
            raise ManagerError("invalid_input", "Settings must use key=value syntax.")
        key, raw = item.split("=", 1)
        if not key or key in result:
            raise ManagerError(
                "invalid_input", "Duplicate or empty setting names are invalid."
            )
        try:
            value = json.loads(raw)
        except (ValueError, TypeError):
            value = raw
        result[key] = value
    return result


def _create(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    name = params.get("name")
    if not isinstance(name, str):
        raise ManagerError("invalid_input", "A valid display name is required.")
    strategy = params.get("strategy")
    if not isinstance(strategy, str):
        raise ManagerError("invalid_input", "A strategy is required.")
    resolved = resolve_config(
        strategy,
        params.get("config_context", {}),
        _settings(params),
        context.shared_snapshot,
    )
    try:
        spec = BotSpec.create(name, strategy, resolved)
    except ManagerError as exc:
        if exc.code == "invalid_spec":
            raise ManagerError(
                "invalid_input", "A valid unique display name is required."
            ) from exc
        raise
    return _store(context).create_spec(spec).to_dict()


def _list(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    store = _store(context)
    return {
        "initialized": store.initialized,
        "bots": [spec.to_dict() for spec in store.list_specs()],
    }


def _config(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    return _identity(params, context).to_dict()


def _view(spec: BotSpec) -> dict[str, Any]:
    return {
        "bot_id": spec.bot_id,
        "display_name": spec.display_name,
        "source": spec.source,
        "owner": spec.owner,
        "strategy_id": spec.strategy_id,
        "mode": spec.mode,
        "armed": spec.resolved_values["armed"],
        "config_hash": spec.config_hash,
        "desired_state": "draft",
        "observed_state": "not_running",
        "capabilities": ["inspect"],
        "reason": "runtime_not_available",
    }


def _status(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    if params.get("identity"):
        return _view(_identity(params, context))
    store = _store(context)
    return {
        "initialized": store.initialized,
        "bots": [_view(spec) for spec in store.list_specs()],
        "runtime": "not_available",
    }


def _runtime(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    _identity(params, context)
    raise ManagerError(
        "runtime_not_available",
        "Manager drafts have no runtime; start and stop are unavailable.",
        3,
    )


def _help(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    return {
        "commands": [
            {"name": spec.name, "description": spec.description}
            for spec in COMMANDS.values()
        ],
        "scope": "paper, disarmed Solana SOL/USDC drafts; no autonomous runtime",
        "strategies": {
            "grid": "draft",
            "dca": "draft",
            "trend": "draft",
            "momentum": "draft",
            "arbitrage": "Solana adapter unavailable",
            "council": "external-only",
        },
    }


IDENTITY = ((("identity",), {"help": "Bot UUID or unique display name"}),)
COMMANDS = {
    "create": CommandSpec(
        "create",
        "Create a pinned paper/disarmed draft.",
        _create,
        (
            (("strategy",), {"help": "grid, dca, trend, momentum"}),
            (("--name",), {"required": True}),
            (("--set",), {"action": "append", "default": [], "metavar": "KEY=VALUE"}),
        ),
    ),
    "list": CommandSpec("list", "List durable drafts without creating state.", _list),
    "config": CommandSpec(
        "config",
        "Inspect the pinned effective settings and provenance.",
        _config,
        IDENTITY + ((("--effective",), {"action": "store_true"}),),
    ),
    "status": CommandSpec(
        "status",
        "Inspect observed state without starting services.",
        _status,
        ((("identity",), {"nargs": "?"}),),
    ),
    "start": CommandSpec(
        "start",
        "Request owner start only when advertised; drafts have no runtime.",
        _runtime,
        IDENTITY,
    ),
    "stop": CommandSpec(
        "stop",
        "Request owner stop only when advertised; drafts have no runtime.",
        _runtime,
        IDENTITY,
    ),
    "help": CommandSpec("help", "Show commands and current capability limits.", _help),
}
ERROR_EXIT_CODES = {
    "runtime_not_available": 3,
    "solana_adapter_unavailable": 3,
    "external_only": 3,
    "store_unavailable": 4,
    "incompatible_store": 4,
    "invalid_spec": 4,
    "operational_failure": 4,
}


def dispatch(
    name: str, params: Mapping[str, Any], context: CommandContext | None = None
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "schema_version": 1,
        "request_id": str(uuid4()),
        "ok": False,
        "data": None,
        "error": None,
    }
    try:
        if name not in COMMANDS or not isinstance(params, Mapping):
            raise ManagerError(
                "invalid_input", "Unknown command or invalid parameters."
            )
        command = COMMANDS[name]
        allowed = {
            options.get("dest", flags[0].lstrip("-").replace("-", "_"))
            for flags, options in command.arguments
        } | {"overrides", "config_context"}
        if not set(params) <= allowed:
            raise ManagerError("invalid_input", "Unknown command parameters.")
        envelope["data"] = command.handler(params, context or CommandContext())
        envelope["ok"] = True
    except ManagerError as exc:
        envelope["error"] = {
            "code": exc.code,
            "message": exc.message,
            "retryable": False,
            "detail_ref": None,
        }
    except (ValueError, TypeError, KeyError, OverflowError):
        envelope["error"] = {
            "code": "invalid_input",
            "message": "Invalid command input.",
            "retryable": False,
            "detail_ref": None,
        }
    return envelope

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
from .status import draft_snapshot
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


def _external(params: Mapping[str, Any], context: CommandContext):
    from .adapters import default_installations
    from .adapters.soltui import LegacyAdapter

    identity = params.get("identity")
    if not isinstance(identity, str) or ":" not in identity:
        return None
    installation_id, family = identity.split(":", 1)
    installations = context.installations or default_installations()
    for installation in installations:
        if (
            installation.installation_id == installation_id
            and installation.source == "soltui"
        ):
            adapter = context.owner_adapters.get(installation_id) or LegacyAdapter(
                installation, home=context.home
            )
            return adapter, family
    raise ManagerError("bot_not_found", "The external installation is not registered.")


def _discover(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    from .adapters import discover_installations

    return discover_installations(
        context.installations or None,
        home=context.home,
        owner_adapters=context.owner_adapters,
    ).to_dict()


def _status(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    why = params.get("why", False)
    if type(why) is not bool:
        raise ManagerError("invalid_input", "The explanation option must be a boolean.")
    if params.get("identity"):
        external = _external(params, context)
        if external is not None:
            adapter, family = external
            snapshot = adapter.discover().to_dict()
            if snapshot["bots"] is None:
                raise ManagerError(
                    snapshot["state"],
                    "The configured owner cannot provide inventory.",
                    3,
                )
            for row in snapshot["bots"]:
                if row["strategy_id"] == family:
                    return row
            raise ManagerError("bot_not_found", "External identity was not found.")
        return draft_snapshot(_identity(params, context), why=why)
    store = _store(context)
    return {
        "initialized": store.initialized,
        "bots": [draft_snapshot(spec, why=why) for spec in store.list_specs()],
        "runtime": "not_available",
        "installations": _discover({}, context)["installations"],
    }


def _runtime(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    _identity(params, context)
    raise ManagerError(
        "runtime_not_available",
        "Manager drafts have no runtime; start and stop are unavailable.",
        3,
    )


def _delegated(
    params: Mapping[str, Any], context: CommandContext, operation: str
) -> dict[str, Any]:
    external = _external(params, context)
    if external is None:
        return _runtime(params, context)
    adapter, family = external
    if any(
        params.get(key) is None
        for key in ("expected_session", "expected_config_hash", "request_id")
    ):
        raise ManagerError(
            "expected_observation_required",
            "Supply the inspected session (or none), config hash and a request UUID.",
            3,
        )
    session = (
        None if params["expected_session"] == "none" else params["expected_session"]
    )
    return adapter.control(
        family,
        operation,
        params["request_id"],
        None,
        expected_session=session,
        expected_config_hash=params["expected_config_hash"],
    ).to_dict()


def _start(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    return _delegated(params, context, "start")


def _stop(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    return _delegated(params, context, "stop")


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
CONTROL_GUARDS = (
    (
        ("--expected-session",),
        {"help": "Inspected session ID, or none for an empty slot"},
    ),
    (("--expected-config-hash",), {"help": "Inspected owner configuration hash"}),
    (
        ("--request-id",),
        {"help": "Canonical UUID; repeat only to inspect its durable receipt"},
    ),
)
COMMANDS = {
    "discover": CommandSpec(
        "discover",
        "Read configured owner inventory without starting services.",
        _discover,
    ),
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
        (
            (("identity",), {"nargs": "?"}),
            (
                ("--why",),
                {"action": "store_true", "help": "Include the state explanation"},
            ),
        ),
    ),
    "start": CommandSpec(
        "start",
        "Request owner start only when advertised; drafts have no runtime.",
        _start,
        IDENTITY + CONTROL_GUARDS,
    ),
    "stop": CommandSpec(
        "stop",
        "Request owner stop only when advertised; drafts have no runtime.",
        _stop,
        IDENTITY + CONTROL_GUARDS,
    ),
    "help": CommandSpec("help", "Show commands and current capability limits.", _help),
}
ERROR_EXIT_CODES = {
    "runtime_not_available": 3,
    "expected_observation_required": 3,
    "owner_unreachable": 3,
    "incompatible_owner": 3,
    "credentials_unavailable": 3,
    "capability_unavailable": 3,
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

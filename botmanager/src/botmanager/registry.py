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
    ecosystem_home: Path | None = None


@dataclass(frozen=True)
class CommandSpec:
    name: str
    description: str
    handler: Callable[[Mapping[str, Any], CommandContext], dict[str, Any]]
    arguments: tuple[tuple[tuple[str, ...], dict[str, Any]], ...] = ()
    api_parameters: tuple[str, ...] = ()


GLOBAL_ARGUMENTS = (
    (
        ("--ecosystem-home",),
        {
            "dest": "ecosystem_home",
            "type": Path,
            "default": None,
            "help": "Read registered external paper trials from this explicit ecosystem home.",
        },
    ),
)


def _argument_schema(arguments):
    return [
        {
            "flags": list(flags),
            **{
                key: value.__name__ if key == "type" else value
                for key, value in options.items()
            },
        }
        for flags, options in arguments
    ]


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
    from .adapters.ecosystem import discover_ecosystem

    return {
        "ecosystem": discover_ecosystem(context.ecosystem_home),
        "initialized": store.initialized,
        "bots": [spec.to_dict() for spec in store.list_specs()],
    }


def _config(params: Mapping[str, Any], context: CommandContext) -> dict[str, Any]:
    return _identity(params, context).to_dict()


def _edit(params, context):
    identity = params.get("identity")
    if not isinstance(identity, str) or not identity:
        raise ManagerError("invalid_input", "A bot identity is required.")
    return _store(context).edit(
        identity,
        _settings(params),
        expected_revision=params.get("expected_revision"),
        request_id=params.get("request_id"),
    )


def _history(params, context):
    return _store(context).capture_view(
        params.get("identity"), history=True, revision=params.get("revision")
    )


def _apply(params, context):
    from .ledger import RuntimeLedger

    identity = params.get("identity")
    if not isinstance(identity, str) or not identity:
        raise ManagerError("invalid_input", "A bot identity is required.")
    return RuntimeLedger(context.home).apply(
        identity,
        descriptor=params.get("descriptor"),
        expected_revision=params.get("expected_revision"),
        request_id=params.get("request_id"),
    )


def _schema(params, context):
    from .config import STRATEGY_VERSIONS, _strategy, field_metadata
    from .strategies.grid import (
        MAX_REFERENCE_RANGE_PCT,
        MAX_REFERENCE_RUNGS,
        REFERENCE_BAR_SECONDS,
    )

    strategy = params.get("strategy")
    if strategy is not None:
        _strategy(strategy)
    strategies = {
        key: {
            "version": version,
            "fields": field_metadata(key),
            "runtime": "recorded_reference_only" if key == "grid" else "draft_only",
            "live_available": False,
            "prospective_data_certified": False,
            "cross_field_constraints": ["fast_period < slow_period"]
            if key == "trend"
            else [
                "base_order_usd >= max(min_order_usd, 1e-9)",
                "max_safety_orders > 0 requires safety_order_usd >= max(min_order_usd, 1e-9)",
                "cumulative safety deviation < 100 percent; scaled sizes finite",
            ]
            if key == "dca"
            else [],
            "runtime_constraints": {
                "bar_seconds": REFERENCE_BAR_SECONDS,
                "maximum_rungs": MAX_REFERENCE_RUNGS,
                "exclusive_maximum_range_pct": MAX_REFERENCE_RANGE_PCT,
                "capital": "must_equal_explicit_descriptor_capital_quote",
                "minimum_order": "capital_quote / rungs >= explicit_min_order_quote",
                "venue": "coinbase_proxy",
            }
            if key == "grid"
            else None,
        }
        for key, version in STRATEGY_VERSIONS.items()
        if strategy in (None, key)
    }
    return {
        "schema_version": 1,
        "strategies": strategies,
        "unavailable_strategies": {
            "arbitrage": "solana_adapter_unavailable",
            "triangle": "solana_adapter_unavailable",
            "council": "external_only",
        },
        "protected_identity_fields": [
            "bot_id",
            "source",
            "owner",
            "source_identity",
            "strategy_id",
            "strategy_version",
            "created_at",
            "display_name",
        ],
        "mutation_contract": {
            "explicit_delta_only": True,
            "expected_revision": "optional_compare_and_swap",
            "omitted_revision": "latest_inside_serialized_mutation",
            "request_id": "durable_replay_only",
            "edit_starts_worker": False,
            "apply_starts_worker": False,
        },
        "global_arguments": _argument_schema(GLOBAL_ARGUMENTS),
        "commands": {
            name: {
                "description": command.description,
                "api_parameters": list(command.api_parameters),
                "arguments": _argument_schema(command.arguments),
            }
            for name, command in COMMANDS.items()
        },
    }


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
        captured = _store(context).capture_view(params["identity"])
        spec, row = captured["bots"][0]
        return _manager_status(spec, row, context, why=why)
    from .adapters.ecosystem import discover_ecosystem

    captured = _store(context).capture_view()
    return {
        "ecosystem": discover_ecosystem(context.ecosystem_home),
        "initialized": captured["initialized"],
        "bots": [
            _manager_status(spec, row, context, why=why)
            for spec, row in captured["bots"]
        ],
        "runtime": "reference_paper_available",
        "installations": _discover({}, context)["installations"],
    }


def _manager_status(spec, row, context, *, why=False):
    import time

    from .ledger import RuntimeLedger
    from .status import runtime_snapshot
    from .worker import lock_held

    ledger = RuntimeLedger(context.home)
    return runtime_snapshot(
        spec,
        row,
        now=time.time(),
        worker_alive=lock_held(ledger.home / "locks" / (spec.bot_id + ".lock")),
        supervisor_alive=lock_held(ledger.home / "supervisor.lock"),
        why=why,
    )


def _runtime(params, context, operation):
    from .ledger import RuntimeLedger

    spec = _identity(params, context)
    ledger = RuntimeLedger(context.home)
    if spec.bot_id not in ledger.ids():
        raise ManagerError(
            "runtime_not_available",
            "Register explicit reference input before runtime control.",
            3,
        )
    if (
        params.get("expected_session") is not None
        or params.get("expected_config_hash") is not None
    ):
        raise ManagerError(
            "invalid_input",
            "External-owner guards cannot be applied to manager runtime controls.",
        )
    return ledger.control(spec, operation, params.get("request_id") or str(uuid4()))


def _register_input(params, context):
    from .data import load_recording
    from .ledger import RuntimeLedger

    spec = _identity(params, context)
    try:
        path = Path(params["descriptor"])
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError
        descriptor = json.loads(raw)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ManagerError(
            "input_unavailable", "Input descriptor is missing or invalid.", 3
        ) from exc
    return RuntimeLedger(context.home).register(spec, load_recording(descriptor))


def _events(params, context):
    from .ledger import RuntimeLedger

    spec = _identity(params, context)
    return {
        "bot_id": spec.bot_id,
        "events": RuntimeLedger(context.home).events(
            spec.bot_id, params.get("limit", 100)
        ),
    }


def _daemon(params, context):
    from .supervisor import Supervisor

    return Supervisor(context.home).run()


def _service(params, context):
    from .service import service

    return service(params["action"], context.home)


def _delegated(
    params: Mapping[str, Any], context: CommandContext, operation: str
) -> dict[str, Any]:
    external = _external(params, context)
    if external is None:
        return _runtime(params, context, operation)
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
        "scope": "paper/disarmed drafts and bounded Coinbase grid reference replay; no live execution",
        "strategies": {
            "grid": "reference_paper_with_explicit_input",
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
MUTATION_GUARDS = (
    (
        ("--expected-revision",),
        {"type": int, "help": "Compare the saved revision atomically"},
    ),
    (
        ("--request-id",),
        {"help": "Canonical UUID; repeats return the original accepted mutation"},
    ),
)
COMMANDS = {
    "edit": CommandSpec(
        "edit",
        "Save an immutable settings revision; active workers stay pinned.",
        _edit,
        IDENTITY
        + ((("--set",), {"action": "append", "default": [], "metavar": "KEY=VALUE"}),)
        + MUTATION_GUARDS,
        api_parameters=("overrides",),
    ),
    "history": CommandSpec(
        "history",
        "Read exact saved revisions and attributable current/archived runtime evidence.",
        _history,
        IDENTITY + ((("--revision",), {"type": int}),),
    ),
    "apply": CommandSpec(
        "apply",
        "Adopt saved settings at a stopped zero-exposure boundary without starting.",
        _apply,
        IDENTITY
        + MUTATION_GUARDS
        + (
            (
                ("--descriptor",),
                {"help": "Optional compatible recorded-input descriptor"},
            ),
        ),
    ),
    "schema": CommandSpec(
        "schema",
        "Read versioned editor fields, constraints and command arguments.",
        _schema,
        ((("strategy",), {"nargs": "?"}),),
    ),
    "register-input": CommandSpec(
        "register-input",
        "Pin explicit recorded input and simulation costs.",
        _register_input,
        IDENTITY + ((("--descriptor",), {"required": True}),),
    ),
    "events": CommandSpec(
        "events",
        "Read runtime events without starting workers.",
        _events,
        IDENTITY + ((("--limit",), {"type": int, "default": 100}),),
    ),
    "daemon": CommandSpec(
        "daemon", "Explicitly run the local reference-paper supervisor.", _daemon
    ),
    "service": CommandSpec(
        "service",
        "Explicit launchd install/uninstall or inert status.",
        _service,
        ((("action",), {"choices": ("install", "uninstall", "status")}),),
    ),
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
        api_parameters=("overrides", "config_context"),
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
        "Persist manager reference start or request guarded external start.",
        _start,
        IDENTITY + CONTROL_GUARDS,
    ),
    "stop": CommandSpec(
        "stop",
        "Persist manager stop retaining positions or request guarded external stop.",
        _stop,
        IDENTITY + CONTROL_GUARDS,
    ),
    "help": CommandSpec("help", "Show commands and current capability limits.", _help),
}
ERROR_EXIT_CODES = {
    "read_conflict": 4,
    "adoption_blocked": 3,
    "incompatible_input": 3,
    "invalid_receipt": 4,
    "input_unavailable": 3,
    "resource_limit": 3,
    "stable_install_required": 3,
    "already_running": 3,
    "supervisor_unreachable": 3,
    "reconciliation_required": 3,
    "corrupt_checkpoint": 4,
    "service_unavailable": 4,
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
        } | set(command.api_parameters)
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
    except OSError:
        envelope["error"] = {
            "code": "operational_failure",
            "message": "The requested local operation could not be completed.",
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

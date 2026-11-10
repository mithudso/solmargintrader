"""Registry definitions for explicit operational actions."""

from __future__ import annotations

import time

from .domain import ManagerError
from .health import HealthStore, entries_paused, health_snapshot
from .ledger import RuntimeLedger
from .store import ManagerStore


def _spec(params, context):
    spec = ManagerStore(context.home).get_spec(params.get("identity", ""))
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    return spec


def health_command(params, context):
    spec = _spec(params, context)
    ledger = RuntimeLedger(context.home)
    row = ledger.get(spec.bot_id)
    if row is None:
        raise ManagerError(
            "runtime_not_available", "No runtime has been registered.", 3
        )
    return {
        "bot_id": spec.bot_id,
        "runtime_id": row["runtime_id"],
        "health": health_snapshot(row, now=time.time()),
        "entries_paused": entries_paused(ledger.home, spec.bot_id, row["runtime_id"]),
    }


def alerts_command(params, context):
    spec = _spec(params, context) if params.get("identity") else None
    return HealthStore(context.home).page(
        bot_id=spec.bot_id if spec else None,
        after=params.get("after", 0),
        limit=params.get("limit", 100),
    )


def entry_control(params, context, operation):
    spec = _spec(params, context)
    ledger = RuntimeLedger(context.home)
    row = ledger.get(spec.bot_id)
    if row is None:
        raise ManagerError(
            "runtime_not_available", "No runtime has been registered.", 3
        )
    return HealthStore(ledger.home).pause(row, operation, params.get("request_id"))


def backup_command(params, context):
    from .backup import create_backup

    return create_backup(ManagerStore(context.home).home, params["destination"])


def restore_command(params, context):
    from .backup import restore_backup

    return restore_backup(params["backup"], params["destination"])


def command_specs(command_type):
    identity = ((("identity",), {}),)
    return (
        command_type(
            "health",
            "Read independent process, input and evaluation health.",
            health_command,
            identity,
        ),
        command_type(
            "alerts",
            "Read bounded attributable health alerts.",
            alerts_command,
            (
                (("identity",), {"nargs": "?"}),
                (("--after",), {"type": int, "default": 0}),
                (("--limit",), {"type": int, "default": 100}),
            ),
        ),
        command_type(
            "pause",
            "Pause entries; retain account and continue existing exits.",
            lambda p, c: entry_control(p, c, "pause"),
            identity + ((("--request-id",), {"required": True}),),
        ),
        command_type(
            "resume",
            "Resume entries under the pinned account policy.",
            lambda p, c: entry_control(p, c, "resume"),
            identity + ((("--request-id",), {"required": True}),),
        ),
        command_type(
            "backup",
            "Explicitly capture stopped manager state; never copy authority.",
            backup_command,
            ((("destination",), {}),),
        ),
        command_type(
            "restore",
            "Restore into a new stopped home; retain canonical authority.",
            restore_command,
            ((("backup",), {}), (("destination",), {})),
        ),
    )

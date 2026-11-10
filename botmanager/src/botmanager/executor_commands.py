"""Manager registry exports for guarded executor delegation; never signs or enrolls capital."""

from __future__ import annotations

from .adapters.executor import ExecutorAdapter, prepare_descriptor
from .domain import ManagerError
from .input_commands import read_document
from .ledger import RuntimeLedger
from .store import ManagerStore, data_home


def _adapter(params):
    return ExecutorAdapter(read_document(params["executor"]))


def _request(params, context):
    request = read_document(params["request"])
    spec = ManagerStore(context.home).get_spec(params["identity"])
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    row = RuntimeLedger(context.home).get(spec.bot_id)
    if row is None:
        raise ManagerError(
            "executor_runtime_unavailable",
            "An exact versioned runtime is required for delegation.",
            3,
        )
    pinned = row["spec"]
    if not isinstance(request, dict) or not isinstance(request.get("scope"), dict):
        raise ManagerError(
            "invalid_input", "An exact executor intent scope is required.", 3
        )
    scope = request["scope"]
    expected = {
        "bot_id": spec.bot_id,
        "runtime_id": row["runtime_id"],
        "generation": row["generation"],
        "strategy": pinned["strategy_id"],
        "strategy_version": pinned["strategy_version"],
        "config_hash": pinned["config_hash"],
        "revision": pinned["config_revision"],
        "timeframe": pinned["bar_seconds"],
        "execution_model": pinned["execution_model"],
    }
    if any(scope.get(key) != value for key, value in expected.items()):
        raise ManagerError(
            "executor_scope_changed",
            "Request does not bind the exact current runtime configuration.",
            3,
        )
    return request


def _operation(params, context, command):
    return _adapter(params).call(command, {"request": _request(params, context)})


def command_specs(command_type):
    descriptor = ((("--executor",), {"required": True}),)
    request = (
        ((("identity",), {}),) + descriptor + ((("--request",), {"required": True}),)
    )
    return (
        command_type(
            "executor-setup",
            "Probe installed executor identity and write a reviewed descriptor; never enroll or arm.",
            lambda p, c: prepare_descriptor(
                p["interpreter"],
                p["home"],
                p.get("output") or (c.home or data_home()) / "executor-owner.json",
            ),
            (
                (("--interpreter",), {"required": True}),
                (("--home",), {"required": True}),
                (("--output",), {}),
            ),
        ),
        command_type(
            "executor-capabilities",
            "Read the reviewed installed executor capability identity.",
            lambda p, c: _adapter(p).capabilities(),
            descriptor,
        ),
        command_type(
            "executor-admit",
            "Check exact research/shadow/runtime admission without signing.",
            lambda p, c: _operation(p, c, "manager.admit"),
            request,
        ),
        command_type(
            "executor-intent",
            "Delegate one exact caller intent to the guarded executor; never retry unknown sends.",
            lambda p, c: _operation(p, c, "manager.swap"),
            request,
        ),
        command_type(
            "executor-status",
            "Read one executor-owned durable caller receipt.",
            lambda p, c: _adapter(p).call(
                "manager.status", {"request_id": p["request_id"]}
            ),
            descriptor + ((("--request-id",), {"required": True}),),
        ),
        command_type(
            "executor-reconcile",
            "Ask the existing executor to reconcile shared wallet sends without retry.",
            lambda p, c: _adapter(p).call("reconcile", {}),
            descriptor,
        ),
    )

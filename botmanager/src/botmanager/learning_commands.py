"""Registry-owned learning commands; no client clocks or outcome-count inputs."""

from __future__ import annotations

from .domain import ManagerError
from .input_commands import read_document
from .learning import reconcile_transition, record_owner_view
from .research_owner import OwnerClient
from .store import ManagerStore


def _owner(params):
    return OwnerClient(read_document(params["owner"]))


def _labels(params, context):
    store = ManagerStore(context.home)
    spec = store.get_spec(params["identity"])
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    return _owner(params).call(
        "learning-labels", {"manager_home": str(store.home), "bot_id": spec.bot_id}
    )


def _propose(params, context):
    store = ManagerStore(context.home)
    spec = store.get_spec(params["identity"])
    if spec is None:
        raise ManagerError("bot_not_found", "Bot identity was not found.")
    result = _owner(params).call(
        "learning-propose",
        {
            "manager_home": str(store.home),
            "bot_id": spec.bot_id,
            "run_id": params["run_id"],
        },
    )
    record_owner_view(store, result)
    return result


def _inspect(params, context):
    result = _owner(params).call(
        "learning-inspect", {"proposal_id": params["proposal_id"]}
    )
    # Inspection remains a read; updating local pointers is explicit proposal/shadow work.
    return result


def _shadow(params, context):
    result = _owner(params).call(
        "learning-shadow", {"proposal_id": params["proposal_id"]}
    )
    record_owner_view(ManagerStore(context.home), result)
    return result


def _promote(params, context):
    return reconcile_transition(
        ManagerStore(context.home),
        _owner(params),
        params["proposal_id"],
        operation="promote",
        request_id=params.get("request_id"),
    )


def _rollback(params, context):
    return reconcile_transition(
        ManagerStore(context.home),
        _owner(params),
        params["proposal_id"],
        operation="rollback",
        request_id=params.get("request_id"),
    )


def command_specs(command_type):
    owner = (
        ("--owner",),
        {"required": True, "help": "Reviewed canonical research owner descriptor."},
    )
    identity = (("identity",), {})
    proposal = (("proposal_id",), {})
    request = (("--request-id",), {"required": True})
    return (
        command_type(
            "learning-labels",
            "Collect all attributable outcome cohorts through the research owner.",
            _labels,
            arguments=(identity, owner),
            api_parameters=("identity", "owner"),
        ),
        command_type(
            "learning-propose",
            "Stage an accepted M4 proposal after canonical label and daily gates.",
            _propose,
            arguments=(identity, (("--run-id",), {"required": True}), owner),
            api_parameters=("identity", "run_id", "owner"),
        ),
        command_type(
            "learning-proposal",
            "Inspect canonical proposal gates and actual shadow progress.",
            _inspect,
            arguments=(proposal, owner),
            api_parameters=("proposal_id", "owner"),
        ),
        command_type(
            "learning-shadow",
            "Start paired prospective paper runs under existing worker ownership.",
            _shadow,
            arguments=(proposal, owner),
            api_parameters=("proposal_id", "owner"),
        ),
        command_type(
            "learning-promote",
            "Authorize and reconcile account-preserving learned adoption.",
            _promote,
            arguments=(proposal, request, owner),
            api_parameters=("proposal_id", "request_id", "owner"),
        ),
        command_type(
            "learning-rollback",
            "Stage a verified prior configuration at the same safe account boundary.",
            _rollback,
            arguments=(proposal, request, owner),
            api_parameters=("proposal_id", "request_id", "owner"),
        ),
    )

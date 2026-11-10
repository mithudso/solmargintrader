"""Bounded JSON transport for the existing owner command registry; no UI startup."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

MAX_IO = 1024 * 1024


def identity():
    import importlib.metadata
    import platform

    from .research_admission import source_identity

    modules = source_identity()
    modules["research_owner.py"] = hashlib.sha256(
        Path(__file__).read_bytes()
    ).hexdigest()
    from botmanager import learning, research

    from . import learning_owner

    modules["soltui.learning_owner"] = hashlib.sha256(
        Path(learning_owner.__file__).read_bytes()
    ).hexdigest()
    modules["botmanager.learning"] = hashlib.sha256(
        Path(learning.__file__).read_bytes()
    ).hexdigest()

    modules["botmanager.research"] = hashlib.sha256(
        Path(research.__file__).read_bytes()
    ).hexdigest()
    return {
        "protocol_version": 2,
        "distributions": {
            name: importlib.metadata.version(name)
            for name in ("solmargintrader-research-runtime", "solbot-manager")
        },
        "modules": modules,
        "python": platform.python_version(),
        "owner_path": str(Path(__file__).resolve()),
        "manager_path": str(Path(research.__file__).resolve()),
    }


def handle(request):
    """Only the registered research.protocol handler calls this application API."""
    from .experiments import ExperimentError, ExperimentStore, fingerprint
    from .manager_evidence import exact
    from .research_admission import (
        known_clients,
        optimizer_lease,
        register_authority,
        registered_authority,
    )

    exact(request, ("version", "operation", "authority", "params", "expected_identity"))
    if type(request["version"]) is not int or request["version"] != 2:
        raise ExperimentError("unsupported owner protocol")
    configured = os.environ.get("SOLTUI_CONFIG_DIR")
    if not configured or not Path(configured).is_absolute():
        raise ExperimentError("explicit reviewed owner configuration root required")
    loaded = identity()
    if request["operation"] == "describe":
        exact(request["params"], ())
        if request["authority"] is not None or request["expected_identity"] is not None:
            raise ExperimentError("describe is an inert identity discovery request")
        from .research_admission import registry_path

        path = registry_path()
        record = json.loads(path.read_text()) if path.is_file() else None
        if record is not None and record.get("version") != 2:
            raise ExperimentError("unsupported authority namespace")
        return {
            "identity": loaded,
            "canonical_authority": {k: record[k] for k in ("id", "root")}
            if record
            else None,
        }
    if request["expected_identity"] != loaded:
        raise ExperimentError(
            "loaded owner identity differs from reviewed installation"
        )
    authority = request["authority"]
    exact(authority, ("id", "root", "known_clients", "inventory_complete"))
    root = Path(authority["root"])
    from uuid import UUID

    if (
        str(UUID(authority["id"])) != authority["id"]
        or not root.is_absolute()
        or authority["inventory_complete"] is not True
        or not isinstance(authority["known_clients"], list)
    ):
        raise ExperimentError(
            "explicit canonical authority and complete registered client inventory required"
        )
    for client in authority["known_clients"]:
        exact(client, ("root", "kind", "active"))
        if (
            not isinstance(client["root"], str)
            or not Path(client["root"]).is_absolute()
            or client["kind"] not in ("native", "f5", "bg", "forward")
            or type(client["active"]) is not bool
        ):
            raise ExperimentError("invalid known owner root")
    operation = request["operation"]
    params = request["params"]
    allowed = {
        "status": ("run_id",),
        "backtest": ("spec", "descriptor"),
        "research": ("spec", "descriptor", "options"),
        "proposal": ("run_id",),
        "receipt": ("run_id", "receipt"),
        "recover": ("run_id",),
        "cancel": ("run_id",),
        "register": ("accept_registered_roots_only", "initialize_first"),
        "learning-daily": ("manager_home",),
        "learning-labels": ("manager_home", "bot_id"),
        "learning-propose": ("manager_home", "bot_id", "run_id"),
        "learning-inspect": ("proposal_id",),
        "learning-shadow": ("proposal_id",),
        "learning-promote": ("proposal_id", "request_id"),
        "learning-rollback": ("proposal_id", "request_id"),
        "learning-reconcile": ("proposal_id", "request_id", "manager_receipt"),
    }
    if operation not in allowed:
        raise ExperimentError("unknown owner research action")
    exact(params, allowed[operation])
    if operation == "register":
        return {
            "identity": loaded,
            "registration": register_authority(
                authority,
                configured,
                consent=params["accept_registered_roots_only"],
                initialize_first=params["initialize_first"],
            ),
        }
    binding = Path(configured) / "research-authority.json"
    expected_binding = {
        "version": 2,
        "id": authority["id"],
        "root": str(root.resolve()),
    }
    if binding.exists() and json.loads(binding.read_text()) != expected_binding:
        raise ExperimentError(
            "canonical authority identity mismatch for this owner installation"
        )
    path = root / "experiments.sqlite3"
    # Inert status does not create either the directory or ExperimentStore.
    if operation == "status" and not path.is_file():
        return {
            "identity": loaded,
            "coverage": "registered_roots_only",
            "initialized": False,
            "run": None,
        }
    if not path.is_file():
        raise ExperimentError(
            "existing canonical ExperimentStore required; do not create a per-manager authority"
        )
    registration = registered_authority(authority, configured)
    registered_clients = {
        client["root"]: client for client in registration["known_clients"]
    }
    # A caller can discover another required participant after freezing a run.
    # Inspecting a proposal must not silently ignore that new requirement, or
    # mutate registration merely to report that the receipt is stale.
    participation_changed = any(
        registered_clients.get(str(Path(client["root"]).resolve()))
        != {**client, "root": str(Path(client["root"]).resolve())}
        for client in authority["known_clients"]
    )
    if operation == "learning-inspect":
        from .learning_owner import ReadOnlyResearch

        store = ReadOnlyResearch(root)
    else:
        store = ExperimentStore(root)
    # Authority ID is bound once to this existing ledger, never manager home.
    if not binding.is_file():
        raise ExperimentError(
            "authority_registration_required: unknown owner configuration-root history"
        )
    bound = json.loads(binding.read_text())
    if bound != {"version": 2, "id": authority["id"], "root": str(root.resolve())}:
        raise ExperimentError("canonical authority identity mismatch")
    if operation.startswith("learning-"):
        from .learning_owner import LearningOwner

        learner = LearningOwner(root, registration, store)
        if participation_changed:
            raise ExperimentError("research authority participation changed")
        if operation == "learning-daily":
            with optimizer_lease(root):
                result = {
                    "schedule": learner.daily(params["manager_home"]),
                    "reason": "canonical_daily_attempt_completed",
                }
        elif operation == "learning-labels":
            result = learner.collect(params["manager_home"], params["bot_id"])
        elif operation == "learning-propose":
            with optimizer_lease(root):
                result = learner.propose(
                    params["manager_home"], params["bot_id"], params["run_id"]
                )
        elif operation == "learning-inspect":
            result = learner.inspect(params["proposal_id"])
        elif operation == "learning-shadow":
            result = learner.start_shadow(params["proposal_id"])
        elif operation in ("learning-promote", "learning-rollback"):
            result = {
                "receipt": learner.authorize(
                    params["proposal_id"],
                    operation.removeprefix("learning-"),
                    params["request_id"],
                )
            }
        else:
            result = learner.reconcile(
                params["proposal_id"], params["request_id"], params["manager_receipt"]
            )
        return {
            "identity": loaded,
            **(result if isinstance(result, dict) else {"result": result}),
        }
    if operation == "status":
        return {
            "identity": loaded,
            "coverage": "registered_roots_only",
            "initialized": True,
            "authority": {
                k: registration[k]
                for k in (
                    "namespace_id",
                    "isolation_mode",
                    "initialization_history",
                    "initialization_epoch",
                )
            },
            "coverage_report": store.manager_coverage(),
            "runs": [
                store.manager_status(run["id"])
                for run in store.list_runs(limit=100)
                if run["spec"].get("protocol_version") == 2
            ],
            "run": store.manager_status(params["run_id"]) if params["run_id"] else None,
        }
    if operation == "cancel":
        store.request_control(params["run_id"], "cancel")
        return {"identity": loaded, "run": store.manager_status(params["run_id"])}
    if operation == "recover":
        with optimizer_lease(root):
            state = store.manager_status(params["run_id"])
            if state["state"] != "finished":
                state = store.manager_finish(
                    params["run_id"],
                    {
                        "outcome": "retained_incumbent",
                        "reason": "interrupted_attempt_reconciled",
                        "proposal": None,
                    },
                )
        return {"identity": loaded, "run": state}
    if operation == "proposal":
        state = store.manager_status(params["run_id"])
        proposal = store.manager_read_artifact(params["run_id"], "proposal")
        if (
            state["state"] != "finished"
            or not state["outcome"]
            or state["outcome"]["outcome"] != "proposal_pending_shadow"
        ):
            proposal = None
        if proposal is not None and (
            participation_changed
            or proposal["authority"]["roster_revision"] != fingerprint(registration)
            or proposal["authority"]["history_revision"]
            != store.manager_history_revision(exclude_run=params["run_id"])
        ):
            return {
                "identity": loaded,
                "proposal": proposal,
                "reconcilable": False,
                "reason": "research_authority_roster_or_history_changed",
            }
        return {
            "identity": loaded,
            "proposal": proposal,
            "reconcilable": proposal is not None,
        }
    if operation == "receipt":
        proposal = store.manager_read_artifact(params["run_id"], "proposal")
        receipt = params["receipt"]
        if (
            proposal is None
            or participation_changed
            or proposal["authority"]["roster_revision"] != fingerprint(registration)
            or proposal["authority"]["history_revision"]
            != store.manager_history_revision(exclude_run=params["run_id"])
            or receipt.get("proposal_digest") != fingerprint(proposal)
            or receipt.get("request_id") != proposal["request_id"]
            or receipt.get("state") != "pending_shadow"
        ):
            raise ExperimentError("receipt does not bind accepted evidence proposal")
        store.manager_artifact(params["run_id"], "adoption_receipt", receipt)
        return {"identity": loaded, "receipt": receipt}
    from botmanager.domain import BotSpec, ManagerError
    from botmanager.research import candidates
    from botmanager.strategies import validate_runtime_config

    spec = BotSpec.from_dict(params["spec"])
    try:
        validate_runtime_config(spec)
        if operation == "research":
            candidates(spec, params["options"]["ranges"])
    except ManagerError as exc:
        raise ExperimentError(
            "manager runtime configuration refused: " + exc.code
        ) from None
    discovered, unknown_source = known_clients(configured, params["descriptor"])
    registered_roots = {
        str(Path(c["root"]).resolve()) for c in registration["known_clients"]
    }
    additional = [
        c
        for c in [*discovered, *authority["known_clients"]]
        if str(Path(c["root"]).resolve()) not in registered_roots
    ]
    if additional:
        register_authority(
            {
                **authority,
                "known_clients": [*registration["known_clients"], *additional],
            },
            configured,
            consent=True,
        )
        registration = registered_authority(authority, configured)
    with optimizer_lease(root):
        if unknown_source:
            store.manager_mark_history_gap(
                "oracle-owner-context:"
                + fingerprint(params["descriptor"].get("archive_path")),
                "selected Oracle archive has no verified registered owner context",
            )
        for client in registration["known_clients"]:
            store.manager_register_client(client)
        from botmanager.data import load_recording
        from botmanager.research import backtest, execute

        descriptor = params["descriptor"]
        if operation == "backtest":
            # Descriptive backtests consume all inspected dates, including failures.
            intervals = [
                {
                    "coin": "SOL",
                    "start": descriptor["start_ts"],
                    "end": descriptor["end_ts"],
                }
            ]
            from uuid import uuid4

            store.manager_import(
                "manager-backtest",
                uuid4().hex,
                fingerprint(descriptor),
                intervals,
                attempts=1,
            )
        store.manager_pre_read(
            [
                {
                    "coin": "SOL",
                    "start": descriptor["start_ts"],
                    "end": descriptor["end_ts"],
                }
            ]
        )
        data = load_recording(descriptor, strategy_id=spec.strategy_id)
        if operation == "backtest":
            return {"identity": loaded, "report": backtest(spec, data)}
        return {
            "identity": loaded,
            "coverage": "registered_roots_only",
            "globally_fresh": False,
            "automatic_promotion": False,
            "run": execute(
                store,
                spec,
                data,
                params["options"],
                authority_context={
                    k: registration[k]
                    for k in (
                        "namespace_id",
                        "isolation_mode",
                        "coverage",
                        "initialization_epoch",
                    )
                }
                | {"roster_revision": fingerprint(registration)},
            ),
        }


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_IO + 1)
        if len(raw) > MAX_IO:
            raise ValueError
        request = json.loads(raw)
        # Use the same registered action as HTTP/CLI/native-host. Supplying an
        # inert Context avoids reading default config, keys or creating call logs.
        from . import commands
        from .config import Settings
        from .roster import Roster
        from .signals import SignalDefaults

        if any(
            name == "textual" or name.startswith("textual.") for name in sys.modules
        ):
            raise ValueError("headless owner imported a UI runtime")
        ctx = commands.Context(Settings(), Roster([]), SignalDefaults())
        envelope = commands.dispatch(
            "research.protocol",
            {"request": request},
            surface="stdio",
            ctx=ctx,
            quiet=True,
        )
        if not envelope["ok"]:
            envelope["error"] = {
                "code": "research_refused",
                "message": "Owner refused invalid, incompatible or unavailable research evidence.",
            }
        output = json.dumps(envelope, allow_nan=False).encode()
        if len(output) > MAX_IO:
            raise ValueError
        sys.stdout.buffer.write(output + b"\n")
        return 0 if envelope["ok"] else 3
    except (ValueError, TypeError, OSError):
        print(
            '{"ok":false,"error":{"code":"research_refused","message":"Invalid bounded owner request."},"result":null,"command":"research.protocol"}'
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

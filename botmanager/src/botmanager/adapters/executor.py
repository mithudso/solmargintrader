"""Optional, bounded installed executor transport. The manager never imports a signer."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from ..blind import bounded_process
from ..domain import ManagerError, canonical

COMMANDS = frozenset(
    (
        "wallet.capabilities",
        "manager.admit",
        "manager.swap",
        "manager.status",
        "reconcile",
    )
)


class ExecutorAdapter:
    def __init__(self, descriptor):
        if (
            not isinstance(descriptor, dict)
            or set(descriptor) != {"version", "interpreter", "home", "identity"}
            or type(descriptor["version"]) is not int
            or descriptor["version"] != 1
        ):
            raise ManagerError(
                "executor_descriptor_invalid",
                "Invalid reviewed executor installation descriptor.",
                3,
            )
        for key in ("interpreter", "home"):
            if (
                not isinstance(descriptor[key], str)
                or not Path(descriptor[key]).is_absolute()
            ):
                raise ManagerError(
                    "executor_descriptor_invalid", "Executor paths must be absolute.", 3
                )
        if not Path(descriptor["interpreter"]).is_file() or not isinstance(
            descriptor["identity"], dict
        ):
            raise ManagerError(
                "executor_unavailable",
                "Reviewed executor installation is unavailable.",
                3,
            )
        identity = descriptor["identity"]
        if (
            set(identity)
            != {
                "protocol",
                "wallet",
                "source_digest",
                "installation_digest",
                "config_digest",
                "venue",
            }
            or type(identity["protocol"]) is not int
            or identity["protocol"] != 1
            or identity["venue"] != "jupiter-swap-v1"
            or not isinstance(identity["wallet"], str)
            or not identity["wallet"]
            or any(
                not isinstance(identity[key], str)
                or re.fullmatch("[0-9a-f]{64}", identity[key]) is None
                for key in ("source_digest", "installation_digest", "config_digest")
            )
        ):
            raise ManagerError(
                "executor_descriptor_invalid",
                "Exact reviewed executor identity required.",
                3,
            )
        self.descriptor = descriptor

    def _call(self, command, params):
        if command not in COMMANDS:
            raise ManagerError(
                "executor_command_unsupported",
                "Unsupported delegated executor command.",
                3,
            )
        environment = {
            key: os.environ[key]
            for key in ("HOME", "PATH", "TMPDIR")
            if key in os.environ
        }
        environment["EXECUTOR_HOME"] = self.descriptor["home"]
        environment["EXECUTOR_LOG_DIR"] = str(Path(self.descriptor["home"]) / "logs")
        # Use the selected regular installation, never PYTHONPATH or checkout fallback.
        try:
            status, output, _ = bounded_process(
                [
                    self.descriptor["interpreter"],
                    "-I",
                    "-B",
                    "-m",
                    "executor.cli",
                    "call",
                    command,
                    "--json",
                    canonical(params),
                ],
                b"",
                cwd="/",
                env=environment,
                timeout=90,
                limit=262144,
            )
            result = json.loads(output)
            if (
                status not in (0, 1)
                or not isinstance(result, dict)
                or set(result) != {"ok", "command", "result", "error"}
                or result["command"] != command
                or type(result["ok"]) is not bool
            ):
                raise ValueError
            if not result["ok"]:
                if not isinstance(result["error"], dict):
                    raise ValueError
                code = result["error"].get("code")
                raise ManagerError(
                    "executor_"
                    + (
                        code
                        if code in ("refused", "ambiguous", "bad_params")
                        else "unavailable"
                    ),
                    "Executor refused or cannot certify this exact request; inspect executor evidence and reconciliation status.",
                    3,
                )
            if not isinstance(result["result"], dict) or result["error"] is not None:
                raise ValueError
            return result["result"]
        except ManagerError:
            raise
        except (OSError, ValueError, TypeError, RecursionError):
            raise ManagerError(
                "executor_outcome_unknown"
                if command == "manager.swap"
                else "executor_unavailable",
                "Installed executor response unavailable; never retry an accepted intent.",
                3,
            ) from None

    def capabilities(self):
        result = self._call("wallet.capabilities", {})
        expected = self.descriptor["identity"]
        if (
            not isinstance(result, dict)
            or any(result.get(key) != value for key, value in expected.items())
            or not expected
        ):
            raise ManagerError(
                "executor_identity_changed",
                "Executor installation, source or configuration changed.",
                3,
            )
        return result

    def call(self, command, params):
        self.capabilities()
        return self._call(command, params)


def prepare_descriptor(interpreter, home, output):
    """Probe the chosen regular installation without loading keys or enrolling capital."""
    identity_fields = {
        "protocol",
        "wallet",
        "source_digest",
        "installation_digest",
        "config_digest",
        "venue",
    }
    seed = {
        "version": 1,
        "interpreter": interpreter,
        "home": home,
        "identity": {
            "protocol": 1,
            "wallet": "unbound-probe",
            "source_digest": "0" * 64,
            "installation_digest": "0" * 64,
            "config_digest": "0" * 64,
            "venue": "jupiter-swap-v1",
        },
    }
    probe = ExecutorAdapter(seed)._call("wallet.capabilities", {})
    if not isinstance(probe, dict) or not identity_fields <= set(probe):
        raise ManagerError(
            "executor_unavailable",
            "Installed executor does not provide the required capabilities.",
            3,
        )
    descriptor = {**seed, "identity": {key: probe[key] for key in identity_fields}}
    ExecutorAdapter(descriptor)
    from ..research_owner import write_document

    return {
        "descriptor_path": write_document(output, descriptor),
        "descriptor": descriptor,
        "authority_initialized": False,
        "live_enabled": False,
    }

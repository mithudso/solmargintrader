"""Explicit reviewed owner installation adapter; no source-path injection."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .blind import bounded_process
from .domain import ManagerError


class OwnerClient:
    def __init__(self, descriptor):
        required = {
            "version",
            "interpreter",
            "repository",
            "config_root",
            "authority",
            "expected_identity",
        }
        if (
            not isinstance(descriptor, dict)
            or set(descriptor) != required
            or type(descriptor["version"]) is not int
            or descriptor["version"] != 2
        ):
            raise ManagerError(
                "invalid_input", "Owner descriptor must use strict protocol2."
            )
        for field in ("interpreter", "repository", "config_root"):
            if (
                not isinstance(descriptor[field], str)
                or not Path(descriptor[field]).is_absolute()
            ):
                raise ManagerError(
                    "invalid_input", "Owner paths must be explicit and absolute."
                )
        if (
            not Path(descriptor["interpreter"]).is_file()
            or not os.access(descriptor["interpreter"], os.X_OK)
            or not Path(descriptor["repository"]).is_dir()
        ):
            raise ManagerError(
                "research_unavailable", "Reviewed owner installation is unavailable.", 3
            )
        self.descriptor = descriptor

    def call(self, operation, params):
        d = self.descriptor
        request = {
            "version": 2,
            "operation": operation,
            "authority": d["authority"],
            "params": params,
            "expected_identity": d["expected_identity"],
        }
        env = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "PYTHONDONTWRITEBYTECODE": "1",
            "SOLTUI_CONFIG_DIR": d["config_root"],
        }
        if os.environ.get("SOLTUI_RESEARCH_REGISTRY"):
            env["SOLTUI_RESEARCH_REGISTRY"] = os.environ["SOLTUI_RESEARCH_REGISTRY"]
        try:
            code, out, _ = bounded_process(
                [d["interpreter"], "-I", "-B", "-m", "soltui.research_owner"],
                json.dumps(request, allow_nan=False).encode(),
                cwd=d["repository"],
                env=env,
                timeout=120,
            )
            envelope = json.loads(out)
            if (
                code != 0
                or set(envelope) != {"ok", "command", "result", "error"}
                or envelope["ok"] is not True
                or envelope["command"] != "research.protocol"
            ):
                raise ValueError
            result = envelope["result"]
            if not isinstance(result, dict):
                raise TypeError
            if (
                operation != "describe"
                and result.get("identity") != d["expected_identity"]
            ):
                raise ValueError
            return result
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise ManagerError(
                "research_unavailable",
                "Reviewed owner protocol refused or failed; evidence remains retained.",
                3,
            ) from exc


def write_document(path, body):
    """Create an immutable setup artifact; exact repeat is idempotent."""
    path = Path(path).expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.exists():
        if json.loads(path.read_text()) != body:
            raise ManagerError(
                "identity_conflict",
                "Output already exists with different reviewed content; select a new path.",
            )
        return str(path)
    with path.open("x") as stream:
        os.chmod(path, 0o600)
        json.dump(body, stream, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return str(path)


def prepare_descriptor(params, home):
    import sys
    from uuid import UUID, uuid4

    output = Path(params.get("output") or Path(home) / "research-owner.json")
    prior = json.loads(output.read_text()) if output.is_file() else None
    config_root = (
        Path(
            params.get("config_root")
            or os.environ.get("SOLTUI_CONFIG_DIR")
            or Path.home() / ".config/soltui"
        )
        .expanduser()
        .absolute()
    )
    descriptor = {
        "version": 2,
        "interpreter": str(
            Path(params.get("interpreter") or sys.executable).absolute()
        ),
        "repository": str(Path(params.get("repository") or sys.prefix).absolute()),
        "config_root": str(config_root),
        "authority": None,
        "expected_identity": None,
    }
    described = OwnerClient(descriptor).call("describe", {})
    canonical = described["canonical_authority"]
    selected = canonical or (prior["authority"] if prior else None)
    root = str(
        Path(
            params.get("authority_root")
            or (selected["root"] if selected else config_root / "experiments")
        ).resolve()
    )
    authority_id = params.get("authority_id") or (
        selected["id"] if selected else str(uuid4())
    )
    if str(UUID(authority_id)) != authority_id or (
        canonical and (canonical["root"] != root or canonical["id"] != authority_id)
    ):
        raise ManagerError(
            "identity_conflict",
            "Selected authority conflicts with the canonical namespace.",
        )
    descriptor["authority"] = {
        "id": authority_id,
        "root": root,
        "known_clients": [],
        "inventory_complete": True,
    }
    descriptor["expected_identity"] = described["identity"]
    return {
        "descriptor_path": write_document(output, descriptor),
        "descriptor": descriptor,
        "initializes_authority": False,
        "registration_required": True,
        "register_command": [
            "solbot",
            "research-register",
            "--owner",
            str(output.absolute()),
            "--accept-registered-roots-only",
        ],
    }

"""Installation discovery is read-only and never spawns an owner/native host."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .soltui import Installation, LegacyAdapter

# Reviewed source baseline; live implementations separately report their loaded
# module hash. A descriptor pin does not certify a running process's revision.
SOURCE_REVISION = "39140e748cc23453aef7423a8e53e15ce85b9f38"


def default_installations() -> tuple[Installation, ...]:
    return (
        Installation(
            installation_id="soltui-local",
            source="soltui",
            working_directory=Path(
                os.environ.get("SOLBOT_SOLTUI_REPO", "/Users/mitch/dev/solmargintrader")
            ),
            interpreter=Path(
                os.environ.get(
                    "SOLTUI_PYTHON", str(Path.home() / ".venvs/soltui/bin/python")
                )
            ),
            pinned_revision=SOURCE_REVISION,
            config_root=Path(
                os.environ.get("SOLTUI_CONFIG_DIR", str(Path.home() / ".config/soltui"))
            ),
            endpoint=os.environ.get("SOLBOT_SOLTUI_ENDPOINT", "http://127.0.0.1:8788"),
        ),
    )


@dataclass(frozen=True)
class Inventory:
    installations: tuple[dict[str, Any], ...]
    schema_version: int = 1

    def to_dict(self):
        return {
            "schema_version": self.schema_version,
            "installations": list(self.installations),
            "complete": False,
            "reason": "unregistered_sources_remain",
        }


def discover_installations(
    installations=None, *, home=None, owner_adapters=None
) -> Inventory:
    adapters = owner_adapters or {}
    records = []
    for item in default_installations() if installations is None else installations:
        if item.source == "soltui":
            adapter = adapters.get(item.installation_id) or LegacyAdapter(
                item, home=home
            )
            records.append(adapter.discover().to_dict())
        else:
            records.append(
                {
                    "schema_version": 1,
                    "installation_id": item.installation_id,
                    "source": item.source,
                    "descriptor": item.to_dict(),
                    "state": "registration_required"
                    if item.source == "browser"
                    else "discovery_unavailable",
                    "reason": "owner_registration_unavailable",
                    "bots": None,
                }
            )
    for source, identity, state in (
        ("browser", "browser-unregistered", "registration_required"),
        ("node_filestore", "node-filestore-unregistered", "discovery_unavailable"),
    ):
        if not any(item["source"] == source for item in records):
            records.append(
                {
                    "schema_version": 1,
                    "installation_id": identity,
                    "source": source,
                    "state": state,
                    "reason": "owner_registration_unavailable",
                    "bots": None,
                }
            )
    return Inventory(tuple(records))

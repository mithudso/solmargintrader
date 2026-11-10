"""Explicit read-only discovery of externally owned ecosystem paper trials."""

from __future__ import annotations

from pathlib import Path


def discover_ecosystem(
    home: str | Path | None = None,
    *,
    limit: int = 100,
    after: str = "",
    batch_id: str | None = None,
) -> dict:
    """Do not bind a default home, initialize a store, or seize an external bot."""
    if home is None:
        return {
            "status": "unavailable",
            "reason": "ecosystem_not_connected",
            "bots": [],
            "read_only": True,
            "controls_available": False,
            "ownership_transfer": False,
        }
    try:
        from ecosystem.registration import read_registrations

        result = read_registrations(home, limit=limit, after=after, batch_id=batch_id)
    except ImportError:
        result = {
            "status": "unavailable",
            "reason": "ecosystem_adapter_unavailable",
            "bots": [],
        }
    return {
        **result,
        "read_only": True,
        "controls_available": False,
        "ownership_transfer": False,
    }

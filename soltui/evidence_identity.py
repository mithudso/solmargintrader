"""Shared finite JSON identities without importing either evidence store."""

from __future__ import annotations

import hashlib
import json
from typing import Any


class ExperimentError(ValueError):
    """Invalid, conflicting or unavailable experiment evidence."""


def canonical(value: Any) -> str:
    """One finite, deterministic JSON representation for identities and evidence."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ExperimentError(f"evidence must be finite JSON: {exc}") from exc


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()

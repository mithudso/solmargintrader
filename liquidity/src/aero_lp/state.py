"""Small JSON state file: which NFT currently represents each managed slot, plus hysteresis counters.

A rebalance burns the old NFT and mints a new one, so the bot tracks positions by *slot*
(the token id it was first configured with) and follows the chain of replacements.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .validation import finite_number


@dataclass
class SlotState:
    current_token_id: int
    edge_checks: int = 0
    last_rebalance_ts: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        finite_number(self.current_token_id, "current_token_id", positive=True, integer=True)
        finite_number(self.edge_checks, "edge_checks", integer=True)
        if self.last_rebalance_ts is not None:
            finite_number(self.last_rebalance_ts, "last_rebalance_ts")
        if not isinstance(self.history, list) or not all(isinstance(item, dict) for item in self.history):
            raise ValueError("slot history must be a list of records")

    def minutes_since_rebalance(self, now: float | None = None) -> float | None:
        if self.last_rebalance_ts is None:
            return None
        return ((time.time() if now is None else now) - self.last_rebalance_ts) / 60


def home() -> Path:
    """State directory: $AERO_LP_HOME or ~/.aero-lp."""
    return Path(os.environ.get("AERO_LP_HOME", "~/.aero-lp")).expanduser()


def atomic_write_json(path: Path, doc: Any) -> None:
    """Write JSON so a reader never sees a half-written file (temp file in the same dir + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(doc, f, indent=2, default=str, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _sync_directory(path.parent)
    finally:
        Path(tmp).unlink(missing_ok=True)


def _sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class State:
    def __init__(self, path: Path):
        self.path = path
        self.slots: dict[str, SlotState] = {}
        if path.exists():
            raw = json.loads(path.read_text())
            if not isinstance(raw, dict) or not isinstance(raw.get("slots"), dict):
                raise ValueError("state must contain a slots mapping")
            if not all(
                isinstance(k, str) and k.isdecimal() and int(k) > 0 and isinstance(v, dict)
                for k, v in raw["slots"].items()
            ):
                raise ValueError("state slots must be positive token IDs and records")
            self.slots = {k: SlotState(**v) for k, v in raw.get("slots", {}).items()}

    def slot(self, configured_token_id: int) -> SlotState:
        key = str(configured_token_id)
        if key not in self.slots:
            self.slots[key] = SlotState(current_token_id=configured_token_id)
        return self.slots[key]

    def save(self) -> None:
        atomic_write_json(self.path, {"slots": {k: asdict(v) for k, v in self.slots.items()}})

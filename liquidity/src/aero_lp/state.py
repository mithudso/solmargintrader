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


@dataclass
class SlotState:
    current_token_id: int
    edge_checks: int = 0
    last_rebalance_ts: float | None = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def minutes_since_rebalance(self, now: float | None = None) -> float | None:
        if self.last_rebalance_ts is None:
            return None
        return ((now or time.time()) - self.last_rebalance_ts) / 60


def home() -> Path:
    """State directory: $AERO_LP_HOME or ~/.aero-lp."""
    return Path(os.environ.get("AERO_LP_HOME", "~/.aero-lp")).expanduser()


def atomic_write_json(path: Path, doc: Any) -> None:
    """Write JSON so a reader never sees a half-written file (temp file in the same dir + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(fd, "w") as f:
        json.dump(doc, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    _sync_directory(path.parent)


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
            self.slots = {k: SlotState(**v) for k, v in raw.get("slots", {}).items()}

    def slot(self, configured_token_id: int) -> SlotState:
        key = str(configured_token_id)
        if key not in self.slots:
            self.slots[key] = SlotState(current_token_id=configured_token_id)
        return self.slots[key]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({"slots": {k: asdict(v) for k, v in self.slots.items()}}, indent=2)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".state.")
        with os.fdopen(fd, "w") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
        _sync_directory(self.path.parent)  # atomic: a crash never leaves a half-written state file

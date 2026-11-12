"""Prospective source admission for a supported fresh worker import epoch.

This detects production source edits after capture. It does not capture compiled
code, validate modules imported before capture, or establish historical identity.
Callers keep their separate evidence manifests and immutable archive fences.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


class SourceEpochChanged(RuntimeError):
    """The worker must restart before admitting another evaluation."""


def _manifest(root: Path) -> tuple[tuple[str, str], ...]:
    sources = [path for component in ("backtester", "research", "soltui")
               for path in (root / component).rglob("*.py")
               if "tests" not in path.relative_to(root).parts]
    sources.extend((root / "backtester" / "strategy_cards").glob("*.md"))
    return tuple((str(path.relative_to(root)), hashlib.sha256(path.read_bytes()).hexdigest())
                 for path in sorted(sources))


@dataclass(frozen=True)
class SourceEpoch:
    root: Path
    manifest: tuple[tuple[str, str], ...]

    @classmethod
    def capture(cls, root: Path) -> SourceEpoch:
        resolved = root.resolve(strict=True)
        return cls(resolved, _manifest(resolved))

    def verify(self, root: Path) -> None:
        try:
            resolved = root.resolve(strict=True)
            unchanged = resolved == self.root and _manifest(resolved) == self.manifest
        except OSError:
            unchanged = False
        if not unchanged:
            raise SourceEpochChanged("Production source changed after worker startup; restart the worker before evaluation")

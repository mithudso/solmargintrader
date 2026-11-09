from __future__ import annotations

from typing import Any, Protocol

from ..domain import BotSpec


class ReferenceEvaluator(Protocol):
    def __call__(
        self, spec: BotSpec, data: dict[str, Any], cursor: int
    ) -> dict[str, Any]: ...

"""Buy-and-hold: the mandatory baseline every other strategy must beat."""

from __future__ import annotations

from typing import Any

from ..types import BarWindow


class BuyAndHold:
    """Fully invested from the first bar, forever.

    This is the reference implementation for the engine's known-answer test:
    with zero costs and fill_delay=0, its total return must equal
    `last_close / first_close - 1` exactly.
    """

    def __init__(self) -> None:
        self.name = "buy_and_hold"
        self.params: dict[str, Any] = {}

    def warmup_bars(self) -> int:
        """No indicator, so no warmup."""
        return 0

    def on_bar(self, history: BarWindow) -> float:
        """Always fully long."""
        return 1.0

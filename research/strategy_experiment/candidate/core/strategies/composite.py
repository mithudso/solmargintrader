"""Combine several signals into one strategy.

This is what makes pair and multi-signal testing possible without writing a
bespoke class per combination. Four combination modes, because the choice
materially changes what is being tested:

  * ``all``  -- min of member exposures. Every member must agree. Cuts trade
                count hard and raises precision at the cost of recall.
  * ``any``  -- max of member exposures. Any member can trigger. Raises
                exposure and trade count; usually raises drawdown too.
  * ``vote`` -- fraction of members that are long, so exposure scales with
                agreement. Sits between ``all`` and ``any``.
  * ``mean`` -- arithmetic mean of member exposures, preserving continuous
                sizing from members like VolTargetTrend that emit a fraction.

``all`` uses min rather than a product so that combining continuous members
does not shrink exposure multiplicatively (0.5 and 0.5 means "both are
half-sized", not "one quarter").
"""

from __future__ import annotations

from typing import Any, Sequence

from ..types import BarWindow

COMBINE_MODES = ("all", "any", "vote", "mean")


class Composite:
    """Combine member strategies under one Protocol-compatible interface.

    Members are consulted on every bar once the LONGEST member warm-up has
    elapsed, so no member is ever asked for a signal it cannot yet compute.
    That is deliberately conservative: gating on the longest warm-up costs
    early bars but guarantees every member is fully defined whenever the
    composite emits a non-zero target.
    """

    def __init__(
        self,
        members: Sequence[Any],
        mode: str = "all",
        name: str | None = None,
    ) -> None:
        if not members:
            raise ValueError("Composite needs at least one member strategy")
        if mode not in COMBINE_MODES:
            raise ValueError(f"mode must be one of {COMBINE_MODES}, got {mode!r}")
        self.members = list(members)
        self.mode = mode
        self.name = name or f"{mode}({'+'.join(m.name for m in self.members)})"
        self.params: dict[str, Any] = {
            "mode": mode,
            "members": {m.name: dict(m.params) for m in self.members},
        }

    def warmup_bars(self) -> int:
        """Longest member warm-up, so every member is defined when we act."""
        return max(int(m.warmup_bars()) for m in self.members)

    def on_bar(self, history: BarWindow) -> float:
        """Combine member targets under the configured mode."""
        targets = [float(m.on_bar(history)) for m in self.members]
        if self.mode == "all":
            return min(targets)
        if self.mode == "any":
            return max(targets)
        if self.mode == "vote":
            return sum(1.0 for t in targets if t > 0.0) / len(targets)
        return sum(targets) / len(targets)

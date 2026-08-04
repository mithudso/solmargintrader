"""The user's strategy roster: which strategies are active, with what parameters.

Backs the Strategies tab. Kept pure so add/remove is testable without a UI.

Two invariants worth stating, because both prevent a class of confusing failure
later rather than at the point of the mistake:

1. **You cannot enable a strategy that does not exist.** `add()` validates against
   the backtester's own `REGISTRY`, so a typo fails immediately with the list of
   valid names instead of surfacing as a KeyError three screens later when a
   sweep starts.
2. **You cannot add a strategy with parameters it will reject.** `add()`
   instantiates it once and discards the instance. A bad window or an inverted
   fast/slow pair raises here, where the user is looking at the form, rather than
   mid-sweep.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backtester.core.strategies import FAMILY, REGISTRY, build


class RosterError(ValueError):
    """Raised when an entry would be invalid or duplicated."""


@dataclass(frozen=True)
class RosterEntry:
    """One configured strategy the user has enabled."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)

    @property
    def family(self) -> str:
        """Taxonomy family, used by the UI to group and to reason about pairing."""
        return FAMILY.get(self.name, "unknown")

    @property
    def label(self) -> str:
        """The strategy's own generated name, e.g. 'ma_crossover_20_50'.

        Built by instantiating it, so the label always matches what a sweep will
        report rather than being reconstructed by string formatting here.
        """
        return str(build(self.name, **self.params).name)

    @property
    def warmup(self) -> int:
        """Bars this configuration needs before it can trade."""
        return int(build(self.name, **self.params).warmup_bars())

    def to_dict(self) -> dict[str, Any]:
        """Serialisable form."""
        return {"name": self.name, "params": dict(self.params)}


class Roster:
    """An ordered, de-duplicated collection of RosterEntry."""

    def __init__(self, entries: list[RosterEntry] | None = None) -> None:
        self._entries: list[RosterEntry] = []
        for e in entries or []:
            self.add(e.name, **e.params)

    # -- inspection ------------------------------------------------------

    def __len__(self) -> int:
        """How many strategies are enabled."""
        return len(self._entries)

    def __iter__(self):
        """Iterate entries in insertion order."""
        return iter(self._entries)

    @property
    def entries(self) -> list[RosterEntry]:
        """A copy of the entry list, so callers cannot mutate internals."""
        return list(self._entries)

    @property
    def labels(self) -> list[str]:
        """Generated labels for every entry."""
        return [e.label for e in self._entries]

    @property
    def families(self) -> set[str]:
        """Distinct families represented. Useful for cross-family pairing."""
        return {e.family for e in self._entries}

    def max_warmup(self) -> int:
        """Longest warm-up across the roster; 0 when empty."""
        return max((e.warmup for e in self._entries), default=0)

    # -- mutation --------------------------------------------------------

    def add(self, name: str, **params: Any) -> RosterEntry:
        """Enable `name` with `params`. Validates existence and constructability."""
        if name not in REGISTRY:
            raise RosterError(
                f"unknown strategy {name!r}. Available: {', '.join(sorted(REGISTRY))}"
            )
        try:
            build(name, **params)
        except TypeError as exc:
            raise RosterError(f"{name}: bad parameter names — {exc}") from exc
        except ValueError as exc:
            raise RosterError(f"{name}: invalid parameters — {exc}") from exc

        entry = RosterEntry(name=name, params=dict(params))
        if any(e.label == entry.label for e in self._entries):
            raise RosterError(f"{entry.label} is already in the roster")
        self._entries.append(entry)
        return entry

    def remove(self, label: str) -> RosterEntry:
        """Disable the entry whose generated label matches. Returns what was removed."""
        for i, e in enumerate(self._entries):
            if e.label == label:
                return self._entries.pop(i)
        raise RosterError(
            f"{label!r} is not in the roster. Present: {', '.join(self.labels) or '(none)'}"
        )

    def clear(self) -> None:
        """Remove every entry."""
        self._entries.clear()

    # -- serialisation ---------------------------------------------------

    def to_list(self) -> list[dict[str, Any]]:
        """Serialisable form of the whole roster."""
        return [e.to_dict() for e in self._entries]

    @classmethod
    def from_list(cls, raw: list[dict[str, Any]]) -> Roster:
        """Rebuild from `to_list()` output, skipping entries that no longer load.

        Skipping rather than raising means a roster saved against an older build
        still opens; the caller can report what was dropped.
        """
        roster = cls()
        for item in raw or []:
            try:
                roster.add(item.get("name", ""), **(item.get("params") or {}))
            except RosterError:
                continue
        return roster

    @classmethod
    def default(cls) -> Roster:
        """The four strategies the backtester ships as its default comparison set."""
        roster = cls()
        for name in ("buy_and_hold", "ma_crossover", "rsi", "breakout"):
            roster.add(name)
        return roster


def available_strategies() -> list[tuple[str, str]]:
    """(name, family) for every registered strategy, for the Strategies tab list."""
    return sorted((name, FAMILY.get(name, "unknown")) for name in REGISTRY)

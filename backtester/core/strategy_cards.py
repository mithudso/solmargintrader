"""Strategy cards: one self-contained file per strategy or signal.

A card is a Markdown file with YAML-subset frontmatter under
`backtester/strategy_cards/`. The frontmatter is the machine-readable contract —
registry key, parameters with defaults, per-horizon presets, data requirements,
evaluation provenance — and the body is the human half: the equations, the
reasoning, the limitations, the caveats.

Why cards at all, when the code already exists: the parameters a strategy was
actually run with, the reason anyone believed it would work, and the reason it
failed are three different kinds of knowledge that otherwise live in three
different places (a constructor signature, a research doc, a git commit). A card
puts them in one editable, shareable, diffable file that both a person and an
agent can read, and `tests/test_strategy_cards.py` makes the machine-readable
half **verified rather than asserted**: a default that drifts from its
constructor fails the suite.

Two directions of drift are checked, because both are silent:

* a card whose declared defaults no longer match the code, and
* a registry entry with no card, or a card naming a registry key that is gone.

**No YAML dependency.** `pyyaml` is deliberately absent from
`requirements.txt` (see its "Deliberately NOT required" list), so this module
parses a strict, documented subset by hand and **refuses** anything outside it
rather than guessing. A card that uses unsupported syntax fails loudly at load
time, which is the only safe behaviour for a file that supplies numbers to a
backtest.

Supported frontmatter subset:

    key: scalar                  # null | true/false | int | float | "quoted" | bare
    key: [a, b, c]               # flow sequence of scalars
    key: {a: 1, b: two}          # flow mapping of scalars
    key:                         # block mapping, exactly one level deep,
      sub: scalar                #   whose values are scalars or flow collections
      sub2: {a: 1}

Block sequences (`- item`) and deeper nesting are rejected on purpose: every
card in this repo fits the subset, and a parser that silently accepts more is a
parser nobody can predict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CARD_DIR = Path(__file__).resolve().parent.parent / "strategy_cards"

FRONTMATTER_FENCE = "---"

# `measured` means this repo has run it and the card carries the numbers.
# `spec-only` means the mechanism is specified but never implemented.
STATUSES = ("measured", "spec-only")

# How the thing is executed. An exposure strategy implements the `Strategy`
# protocol in core/engine.py; a ladder is a resting-order grid run by
# core/gridsim.py, which has a different execution model entirely.
KINDS = ("exposure-strategy", "ladder")

# Which entry point runs the card. `null` means nothing does yet (spec-only).
RUNNERS = ("backtester.cli", "backtester.gridcli")

REQUIRED_FIELDS = (
    "id",
    "name",
    "kind",
    "status",
    "family",
    "summary",
    "data_required",
    "data_available",
)

# Every horizon key a card may declare a preset for, matching research/sweep.py.
HORIZONS = ("short", "medium", "long")


class CardError(ValueError):
    """A card is malformed, or uses syntax outside the supported subset."""


def _parse_scalar(raw: str, *, where: str) -> Any:
    """Parse one scalar. Unquoted `null`, booleans and numbers are typed."""
    text = raw.strip()
    if text == "":
        return ""
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1]
    lowered = text.lower()
    if lowered in ("null", "~", "none"):
        return None
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    if text[0] in "[{":
        raise CardError(f"{where}: unterminated flow collection {text!r}")
    return text


def _split_flow(body: str, *, where: str) -> list[str]:
    """Split a flow collection's interior on top-level commas."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    quote: str | None = None
    for ch in body:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            current.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth < 0:
                raise CardError(f"{where}: unbalanced brackets")
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    if quote:
        raise CardError(f"{where}: unterminated quote")
    if depth != 0:
        raise CardError(f"{where}: unbalanced brackets")
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


def _parse_value(raw: str, *, where: str) -> Any:
    """Parse a scalar, a flow sequence, or a flow mapping."""
    text = raw.strip()
    if text.startswith("["):
        if not text.endswith("]"):
            raise CardError(f"{where}: flow sequence must end with ']'")
        return [_parse_scalar(p, where=where) for p in _split_flow(text[1:-1], where=where)]
    if text.startswith("{"):
        if not text.endswith("}"):
            raise CardError(f"{where}: flow mapping must end with '}}'")
        out: dict[str, Any] = {}
        for pair in _split_flow(text[1:-1], where=where):
            if ":" not in pair:
                raise CardError(f"{where}: flow mapping entry {pair!r} has no ':'")
            k, v = pair.split(":", 1)
            out[k.strip()] = _parse_scalar(v, where=where)
        return out
    return _parse_scalar(text, where=where)


def parse_frontmatter(text: str, *, where: str = "<card>") -> tuple[dict[str, Any], str]:
    """Split a card into (frontmatter mapping, body).

    Deliberately strict: anything outside the documented subset raises rather
    than being skipped, because a silently-dropped parameter is a wrong number
    in a backtest.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_FENCE:
        raise CardError(f"{where}: must open with a '{FRONTMATTER_FENCE}' frontmatter fence")

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_FENCE:
            end = i
            break
    if end is None:
        raise CardError(f"{where}: frontmatter is never closed")

    data: dict[str, Any] = {}
    current_key: str | None = None
    for lineno, line in enumerate(lines[1:end], start=2):
        if "\t" in line:
            raise CardError(f"{where}:{lineno}: tabs are not allowed in frontmatter")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.lstrip().startswith("- "):
            raise CardError(
                f"{where}:{lineno}: block sequences are unsupported; use a flow "
                f"sequence like [a, b]"
            )

        indent = len(line) - len(line.lstrip(" "))
        if ":" not in line:
            raise CardError(f"{where}:{lineno}: expected 'key: value', got {line.strip()!r}")
        key, raw = line.split(":", 1)
        key = key.strip()

        if indent == 0:
            value = raw.strip()
            if value == "":
                data[key] = {}
                current_key = key
            else:
                data[key] = _parse_value(value, where=f"{where}:{lineno}")
                current_key = None
        else:
            if current_key is None:
                raise CardError(f"{where}:{lineno}: indented line has no parent key")
            if indent > 2:
                raise CardError(
                    f"{where}:{lineno}: nesting deeper than one level is unsupported"
                )
            parent = data[current_key]
            if not isinstance(parent, dict):
                raise CardError(f"{where}:{lineno}: cannot nest under scalar {current_key!r}")
            parent[key] = _parse_value(raw, where=f"{where}:{lineno}")

    return data, "\n".join(lines[end + 1 :]).strip()


@dataclass
class StrategyCard:
    """One strategy or signal, as declared by its card."""

    id: str
    name: str
    kind: str
    status: str
    family: str
    summary: str
    data_required: list[str]
    data_available: bool
    path: Path
    body: str
    registry_key: str | None = None
    runner: str | None = None
    warmup_bars: int | None = None
    evaluation: str | None = None
    params: dict[str, dict[str, Any]] = field(default_factory=dict)
    presets: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def implemented(self) -> bool:
        """True when something in this repo runs it.

        Keyed on `runner`, not `registry_key`, because the ladder grid is
        implemented and has no registry key — it is not a `Strategy` at all, it
        runs through `backtester.gridcli` against `core/gridsim.py`.
        """
        return self.runner is not None

    @property
    def buildable(self) -> bool:
        """True when `build_from_card` can construct it from the registry."""
        return self.registry_key is not None

    def defaults(self) -> dict[str, Any]:
        """The card's declared default parameter values."""
        return {name: spec["default"] for name, spec in self.params.items()}

    def preset(self, horizon: str) -> dict[str, Any]:
        """Parameters for one horizon, falling back to the declared defaults."""
        if horizon not in HORIZONS:
            raise KeyError(f"unknown horizon {horizon!r}; expected one of {HORIZONS}")
        return dict(self.presets.get(horizon) or self.defaults())

    def cli_args(self, horizon: str = "medium") -> list[str]:
        """The `--strategy`/param flags this card's preset corresponds to.

        Emitted for copy-paste and for an agent assembling a command; the
        backtester CLI takes strategy parameters positionally through the
        registry rather than as flags, so this is the strategy name plus a
        readable parameter echo.
        """
        if not self.implemented:
            raise CardError(f"{self.id}: {self.status} cards cannot be run")
        args = ["--strategy", self.registry_key]
        for key, value in self.preset(horizon).items():
            args.append(f"# {key}={value}")
        return args


def load_card(path: str | Path) -> StrategyCard:
    """Parse one card file."""
    path = Path(path)
    data, body = parse_frontmatter(path.read_text(encoding="utf-8"), where=path.name)

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise CardError(f"{path.name}: missing required field(s): {', '.join(missing)}")
    if data["status"] not in STATUSES:
        raise CardError(f"{path.name}: status must be one of {STATUSES}, got {data['status']!r}")
    if data["kind"] not in KINDS:
        raise CardError(f"{path.name}: kind must be one of {KINDS}, got {data['kind']!r}")
    if not isinstance(data["data_required"], list):
        raise CardError(f"{path.name}: data_required must be a flow sequence")
    if not isinstance(data["data_available"], bool):
        raise CardError(f"{path.name}: data_available must be true or false")

    params = data.get("params") or {}
    if not isinstance(params, dict):
        raise CardError(f"{path.name}: params must be a block mapping")
    for name, spec in params.items():
        if not isinstance(spec, dict):
            raise CardError(f"{path.name}: param {name!r} must be a flow mapping")
        if "default" not in spec:
            raise CardError(f"{path.name}: param {name!r} has no 'default'")

    presets = data.get("presets") or {}
    if not isinstance(presets, dict):
        raise CardError(f"{path.name}: presets must be a block mapping")
    for horizon, values in presets.items():
        if horizon not in HORIZONS:
            raise CardError(
                f"{path.name}: unknown preset horizon {horizon!r}; expected {HORIZONS}"
            )
        if not isinstance(values, dict):
            raise CardError(f"{path.name}: preset {horizon!r} must be a flow mapping")
        unknown = set(values) - set(params)
        if unknown:
            raise CardError(
                f"{path.name}: preset {horizon!r} sets undeclared param(s): "
                f"{', '.join(sorted(unknown))}"
            )

    runner = data.get("runner")
    if runner is not None and runner not in RUNNERS:
        raise CardError(f"{path.name}: runner must be one of {RUNNERS} or null, got {runner!r}")

    if data["status"] == "spec-only":
        if data.get("registry_key") is not None:
            raise CardError(
                f"{path.name}: a spec-only card cannot claim registry_key "
                f"{data['registry_key']!r} — nothing implements it"
            )
        if runner is not None:
            raise CardError(
                f"{path.name}: a spec-only card cannot claim runner {runner!r}"
            )
        if not data["data_required"]:
            raise CardError(
                f"{path.name}: a spec-only card must state what data it would need"
            )
    else:
        if runner is None:
            raise CardError(f"{path.name}: a measured card must name its runner")
        if data["kind"] == "exposure-strategy":
            if data.get("registry_key") is None:
                raise CardError(
                    f"{path.name}: a measured exposure-strategy must name its registry_key"
                )
            if runner != "backtester.cli":
                raise CardError(
                    f"{path.name}: an exposure-strategy runs through backtester.cli"
                )
        elif data["kind"] == "ladder":
            if data.get("registry_key") is not None:
                raise CardError(
                    f"{path.name}: a ladder is not a Strategy and has no registry_key; "
                    "it runs through core/gridsim.py"
                )
            if runner != "backtester.gridcli":
                raise CardError(f"{path.name}: a ladder runs through backtester.gridcli")

    return StrategyCard(
        id=data["id"],
        name=data["name"],
        kind=data["kind"],
        status=data["status"],
        family=data["family"],
        summary=data["summary"],
        data_required=data["data_required"],
        data_available=data["data_available"],
        path=path,
        body=body,
        registry_key=data.get("registry_key"),
        runner=data.get("runner"),
        warmup_bars=data.get("warmup_bars"),
        evaluation=data.get("evaluation"),
        params=params,
        presets=presets,
        raw=data,
    )


def load_all(card_dir: str | Path | None = None) -> dict[str, StrategyCard]:
    """Every card, keyed by id. Raises on a duplicate id."""
    directory = Path(card_dir) if card_dir else CARD_DIR
    if not directory.is_dir():
        raise CardError(f"card directory not found: {directory}")
    cards: dict[str, StrategyCard] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name.upper().startswith("README"):
            continue
        card = load_card(path)
        if card.id in cards:
            raise CardError(f"duplicate card id {card.id!r} in {path.name}")
        if card.id != path.stem:
            raise CardError(
                f"{path.name}: id {card.id!r} does not match the filename; the "
                "filename is the stable slug"
            )
        cards[card.id] = card
    return cards


def build_from_card(
    card: StrategyCard, horizon: str = "medium", **overrides: Any
) -> Any:
    """Instantiate the strategy a card describes.

    This is the point of the whole schema: a card is not documentation about a
    strategy, it is enough to construct one.
    """
    if not card.buildable:
        detail = (
            f"it runs through {card.runner}, not the strategy registry"
            if card.implemented
            else f"it is {card.status} and needs: {', '.join(card.data_required)}"
        )
        raise CardError(f"{card.id} cannot be built from the registry — {detail}")
    # Imported here rather than at module scope so that parsing and validating
    # cards — which the tests and any tooling do constantly — never depends on
    # the strategy package importing cleanly.
    from .strategies import build

    params = card.preset(horizon)
    params.update(overrides)
    return build(card.registry_key, **params)


def implementable_today(cards: dict[str, StrategyCard] | None = None) -> list[StrategyCard]:
    """Spec-only cards whose data this repo already has.

    The useful filter for "what could be built next without a new data source",
    and the reason `data_available` is a frontmatter field rather than prose.
    """
    cards = cards if cards is not None else load_all()
    return [
        c
        for c in cards.values()
        if c.status == "spec-only" and c.data_available
    ]


def _format_inventory(cards: dict[str, StrategyCard]) -> str:
    """A table of every card. Printed rather than committed, so it cannot go stale."""
    rows = [("id", "status", "kind", "family", "runner", "data")]
    for card in sorted(cards.values(), key=lambda c: (c.status, c.family, c.id)):
        rows.append(
            (
                card.id,
                card.status,
                card.kind,
                card.family,
                card.runner or "-",
                ",".join(card.data_required) + ("" if card.data_available else " (MISSING)"),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for i, row in enumerate(rows):
        out.append("  ".join(cell.ljust(widths[j]) for j, cell in enumerate(row)).rstrip())
        if i == 0:
            out.append("  ".join("-" * w for w in widths))
    measured = sum(1 for c in cards.values() if c.status == "measured")
    spec = len(cards) - measured
    ready = len(implementable_today(cards))
    out.append("")
    out.append(
        f"{len(cards)} cards: {measured} measured, {spec} spec-only "
        f"({ready} of those need no new data source)"
    )
    return "\n".join(out)


if __name__ == "__main__":
    print(_format_inventory(load_all()))

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

Supported frontmatter subset — scalars are `null`, `true`/`false`, a finite int or
float, a quoted string, or a bare string:

    key: scalar
    key: [a, b, c]
    key: {a: 1, b: two}
    key:
      sub: scalar
      sub2: {a: 1}

A block mapping is exactly one level deep and its values are scalars or flow
collections. Everything else is rejected on purpose: block sequences (`- item`),
deeper nesting, nested flow collections, tabs, duplicate keys, non-finite floats
(`nan`, `inf`), and **trailing `#` comments after a value** — a full-line comment
is fine, but `rungs: 7  # seven` would parse as the string `"7  # seven"`, so it
raises instead. Every card here fits the subset, and a parser that silently
accepts more is a parser nobody can predict.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CARD_DIR = Path(__file__).resolve().parent.parent / "strategy_cards"

FRONTMATTER_FENCE = "---"

# `measured`     this repo has run it and the card carries the numbers.
# `implemented`   the code exists and is tested, but no data exists to measure it
#                 on — the JLP case, where the history cannot be fetched
#                 retroactively and can only be accumulated going forward.
# `spec-only`     the mechanism is specified and nothing has been built.
#
# The middle state exists because collapsing it into either neighbour would lie:
# calling it spec-only hides working code, and calling it measured invents a result.
STATUSES = ("measured", "implemented", "spec-only")

# How the thing is executed. An exposure strategy implements the `Strategy`
# protocol in core/engine.py; a ladder is a resting-order grid run by
# core/gridsim.py, which has a different execution model entirely.
KINDS = ("exposure-strategy", "ladder")

# Which entry point runs the card. `null` means nothing does yet (spec-only).
RUNNERS = ("backtester.cli", "backtester.gridcli", "backtester.paircli")

REQUIRED_FIELDS = (
    "id",
    "name",
    "kind",
    "status",
    "family",
    "summary",
    "data_required",
    "data_available",
    "success_likelihood",
    "success_basis",
)

# How likely this is to make money after costs, on a scale that refuses to
# flatter. There is deliberately **no `high`**: across 311 rankable
# configurations in this repo's own sweep, 14% had a positive out-of-sample
# Sharpe and 9% made money, so `high` would be a claim the evidence base cannot
# support for anything.
#
#   very-low  measured negative out-of-sample, or the mechanism's known failure
#             mode is the dominant feature of this market
#   low       plausible mechanism, no confirming evidence here — or evidence at
#             or below the 10-trade evidence floor
#   moderate  a documented edge in the literature AND either out-of-sample
#             evidence above the floor here, or a premise that is structural
#             (an arbitrage, a fee) rather than statistical
SUCCESS_LIKELIHOODS = ("very-low", "low", "moderate")

# Where the belief comes from, so a reader can weigh it without reading prose.
#   measured-oos  this repo ran it and the out-of-sample number drives the rating
#   base-rate     rated from the sweep's overall hit rate, not its own result
#   a-priori      never run here; rated from mechanism and literature only
SUCCESS_BASES = ("measured-oos", "base-rate", "a-priori")

# Every horizon key a card may declare a preset for, matching research/sweep.py.
HORIZONS = ("short", "medium", "long")

# Frontmatter is allow-listed rather than merely required-checked: a `warmpu_bars`
# typo would otherwise be dropped in silence, which is exactly the
# silently-missing-parameter failure this module exists to prevent.
ALLOWED_FIELDS = REQUIRED_FIELDS + (
    "registry_key",
    "runner",
    "warmup_bars",
    "evaluation",
    "params",
    "presets",
)

ALLOWED_PARAM_KEYS = ("default", "type", "desc", "required", "min", "max")

# `type` is declared per parameter, so it is enforced per parameter.
TYPE_CHECKS = {
    "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "float": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "bool": lambda v: isinstance(v, bool),
    "str": lambda v: isinstance(v, str),
}


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
        value = float(text)
    except ValueError:
        pass
    else:
        if not math.isfinite(value):
            # `float("nan")` and `float("inf")` both succeed. A NaN parameter would
            # reach a constructor and then the P&L path, and this repo's rule is that
            # a NaN must never silently disable anything.
            raise CardError(f"{where}: {text!r} is not a finite number")
        return value
    if text[0] in "[{":
        raise CardError(
            f"{where}: nested flow collections are unsupported inside {text!r}; "
            "flatten it or use a block mapping"
        )
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
            key = k.strip()
            if key in out:
                raise CardError(f"{where}: duplicate key {key!r} in flow mapping")
            out[key] = _parse_scalar(v, where=where)
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
            # Last-one-wins on a duplicate is how a reader sees `fast: 12` while the
            # backtest runs 21. Real YAML errors here too.
            if key in data:
                raise CardError(f"{where}:{lineno}: duplicate key {key!r}")
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
            if key in parent:
                raise CardError(
                    f"{where}:{lineno}: duplicate key {key!r} under {current_key!r}"
                )
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
    success_likelihood: str
    success_basis: str
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
        """Declared defaults, excluding parameters marked `required`.

        A required parameter has no default anywhere in the code either — the ladder
        grid's `lower` and `upper` are the examples — so inventing one here would put
        an example value where a reader expects a fact.
        """
        return {
            name: spec["default"]
            for name, spec in self.params.items()
            if "default" in spec
        }

    def required_params(self) -> list[str]:
        """Parameters the caller must supply; they have no default."""
        return sorted(n for n, spec in self.params.items() if spec.get("required") is True)

    def preset(self, horizon: str) -> dict[str, Any]:
        """Parameters for one horizon, layered over the declared defaults.

        A preset that names only some parameters means "these, plus the defaults for
        the rest" — five real cards declare partial presets, and returning only the
        named subset would silently drop the others from anything that echoed the
        result.
        """
        if horizon not in HORIZONS:
            raise KeyError(f"unknown horizon {horizon!r}; expected one of {HORIZONS}")
        merged = self.defaults()
        merged.update(self.presets.get(horizon) or {})
        return merged

def load_card(path: str | Path) -> StrategyCard:
    """Parse one card file."""
    path = Path(path)
    data, body = parse_frontmatter(path.read_text(encoding="utf-8"), where=path.name)

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        raise CardError(f"{path.name}: missing required field(s): {', '.join(missing)}")
    unknown = sorted(set(data) - set(ALLOWED_FIELDS))
    if unknown:
        raise CardError(
            f"{path.name}: unknown frontmatter field(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(sorted(ALLOWED_FIELDS))}"
        )
    for field_name in ("id", "name", "family", "summary"):
        if not isinstance(data[field_name], str):
            raise CardError(
                f"{path.name}: {field_name} must be a string, got "
                f"{type(data[field_name]).__name__}"
            )
    if data["status"] not in STATUSES:
        raise CardError(f"{path.name}: status must be one of {STATUSES}, got {data['status']!r}")
    if data["kind"] not in KINDS:
        raise CardError(f"{path.name}: kind must be one of {KINDS}, got {data['kind']!r}")
    if data["success_likelihood"] not in SUCCESS_LIKELIHOODS:
        raise CardError(
            f"{path.name}: success_likelihood must be one of {SUCCESS_LIKELIHOODS}, "
            f"got {data['success_likelihood']!r}. There is no 'high' on purpose."
        )
    if data["success_basis"] not in SUCCESS_BASES:
        raise CardError(
            f"{path.name}: success_basis must be one of {SUCCESS_BASES}, "
            f"got {data['success_basis']!r}"
        )
    if data["status"] == "implemented" and data["success_basis"] == "measured-oos":
        raise CardError(
            f"{path.name}: status 'implemented' has no measured result to cite"
        )
    if data["success_basis"] == "measured-oos" and data["status"] != "measured":
        raise CardError(
            f"{path.name}: success_basis 'measured-oos' claims an out-of-sample "
            f"result, but status is {data['status']!r}"
        )
    if data["status"] == "spec-only" and data["success_basis"] == "measured-oos":
        raise CardError(f"{path.name}: a spec-only card has no measured result")
    if not isinstance(data["data_required"], list):
        raise CardError(f"{path.name}: data_required must be a flow sequence")
    for item in data["data_required"]:
        if not isinstance(item, str):
            raise CardError(
                f"{path.name}: data_required entries must be strings, got {item!r}"
            )
    if not isinstance(data["data_available"], bool):
        raise CardError(f"{path.name}: data_available must be true or false")

    # `in` rather than `or`, so a falsy wrong type (`params: []`) reaches the
    # isinstance check instead of being coerced to an empty mapping.
    params = data["params"] if "params" in data else {}
    if not isinstance(params, dict):
        raise CardError(f"{path.name}: params must be a block mapping")
    for name, spec in params.items():
        if not isinstance(spec, dict):
            raise CardError(f"{path.name}: param {name!r} must be a flow mapping")
        stray = sorted(set(spec) - set(ALLOWED_PARAM_KEYS))
        if stray:
            raise CardError(
                f"{path.name}: param {name!r} has unknown key(s): {', '.join(stray)}"
            )
        if "default" not in spec and spec.get("required") is not True:
            raise CardError(
                f"{path.name}: param {name!r} needs either a 'default' or "
                "'required: true'"
            )
        if "default" in spec and spec.get("required") is True:
            raise CardError(
                f"{path.name}: param {name!r} is marked required and also has a "
                "default; pick one"
            )
        declared_type = spec.get("type")
        if "default" in spec and declared_type in TYPE_CHECKS:
            if not TYPE_CHECKS[declared_type](spec["default"]):
                raise CardError(
                    f"{path.name}: param {name!r} declares type {declared_type} but "
                    f"its default {spec['default']!r} is "
                    f"{type(spec['default']).__name__}"
                )

    presets = data["presets"] if "presets" in data else {}
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
            raise CardError(f"{path.name}: a {data['status']} card must name its runner")
        if data["status"] == "implemented" and data.get("evaluation") is not None:
            raise CardError(
                f"{path.name}: status 'implemented' means nothing has been measured "
                f"yet, so evaluation must be null, got {data['evaluation']!r}"
            )
        if data["kind"] == "exposure-strategy" and runner == "backtester.cli":
            if data.get("registry_key") is None:
                raise CardError(
                    f"{path.name}: a card running through backtester.cli must name "
                    "its registry_key"
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
        success_likelihood=data["success_likelihood"],
        success_basis=data["success_basis"],
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
    claimed: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name.upper().startswith("README"):
            continue
        card = load_card(path)
        # Two cards claiming one registry key is the collision that matters: the drift
        # test keys cards by registry_key, so the second would silently shadow the
        # first and its declared defaults would never be checked against anything.
        if card.registry_key is not None:
            if card.registry_key in claimed:
                raise CardError(
                    f"{path.name}: registry_key {card.registry_key!r} is already "
                    f"claimed by {claimed[card.registry_key]}"
                )
            claimed[card.registry_key] = path.name
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
    rows = [("id", "status", "odds", "basis", "family", "runner", "data")]
    order = {v: i for i, v in enumerate(reversed(SUCCESS_LIKELIHOODS))}
    for card in sorted(
        cards.values(), key=lambda c: (order[c.success_likelihood], c.status, c.id)
    ):
        rows.append(
            (
                card.id,
                card.status,
                card.success_likelihood,
                card.success_basis,
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
    # Counted per status rather than measured-vs-everything-else: lumping
    # `implemented` in with `spec-only` would hide working code, which is the exact
    # distinction that status was added to make.
    by_status = {k: sum(1 for c in cards.values() if c.status == k) for k in STATUSES}
    ready = len(implementable_today(cards))
    out.append("")
    out.append(
        f"{len(cards)} cards: "
        + ", ".join(f"{n} {k}" for k, n in by_status.items() if n)
        + f" ({ready} spec-only need no new data source)"
    )
    return "\n".join(out)


if __name__ == "__main__":
    print(_format_inventory(load_all()))

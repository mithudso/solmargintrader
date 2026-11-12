"""Generate docs-only operation/tool inventories from authoritative source metadata.

Run ``python3 scripts/build_operation_inventories.py --check`` in CI. This
stdlib-only tool parses source; it never imports an application, executes a
handler, starts a service, signs an order or installs a dependency.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import tomllib
from itertools import pairwise
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = ("backtester", "oracle", "botmanager", "soltui", "ecosystem", "liquidity", "executor")
REGISTRIES = (("soltui", "soltui/commands.py", "soltui/tests/test_bridge_parity.py"),
              ("executor", "executor/src/executor/registry.py", "executor/tests"))
MANUAL_TOOLS = (
    ("backtester-tools", "backtester/run.py", "python3 backtester/run.py --help"),
    ("soltui", "soltui/bin/soltui", "soltui/bin/soltui --help"),
    ("soltui-service", "soltui/soltui-service", "soltui/soltui-service --help"),
    ("aero-lp-service", "liquidity/scripts/aero-lp-service", "liquidity/scripts/aero-lp-service --help"),
    ("design-fixture", "design/soltui-v2/mockup.py", "python3 design/soltui-v2/mockup.py --help"),
    ("published-design-fixture", "docs/design/soltui-v2/mockup.py", "python3 docs/design/soltui-v2/mockup.py --help"),
    ("icon-generator", "soltui/make_icon.py", "python3 soltui/make_icon.py --help"),
    ("operation-inventories", "scripts/build_operation_inventories.py", "python3 scripts/build_operation_inventories.py --help"),
)


class InventoryError(ValueError):
    """Source metadata is unsupported or internally inconsistent."""


def _literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError) as exc:
        raise InventoryError("registry metadata must use literal names, descriptions and flags") from exc


def python_commands(source: str) -> list[dict]:
    """Read decorator metadata without importing handlers or their dependencies."""
    tree = ast.parse(source)
    definitions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "command"]
    if len(definitions) != 1:
        raise InventoryError("Python registry must declare exactly one command decorator")
    args = definitions[0].args
    defaults = {arg.arg: _literal(value) for arg, value in zip(args.kwonlyargs, args.kw_defaults)
                if arg.arg in ("read_only", "requires_confirm", "long_running") and value is not None}
    result = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "command"):
                continue
            if not 2 <= len(decorator.args) <= 3 or any(isinstance(arg, ast.Starred) for arg in decorator.args):
                raise InventoryError("command metadata requires a name and description")
            flags = dict(defaults)
            seen_keywords = set()
            for keyword in decorator.keywords:
                if keyword.arg not in ("params", "read_only", "requires_confirm", "long_running") or keyword.arg in seen_keywords:
                    raise InventoryError("expanded, unknown or duplicate command keywords are unsupported")
                if keyword.arg == "params" and len(decorator.args) == 3:
                    raise InventoryError("command parameter metadata is duplicated")
                seen_keywords.add(keyword.arg)
                if keyword.arg in ("read_only", "requires_confirm", "long_running"):
                    flags[keyword.arg] = _literal(keyword.value)
            if any(type(flags.get(key)) is not bool for key in ("read_only", "requires_confirm", "long_running")):
                raise InventoryError("command flags must be explicit literal booleans")
            result.append({"name": _literal(decorator.args[0]), "description": _literal(decorator.args[1]),
                           "symbol": node.name, "line": decorator.lineno, **flags})
    return _unique(result)


def _object_properties(source: str) -> list[dict]:
    """Split literal object properties while keeping nested values opaque.

    This is a constrained registry reader, not a JavaScript evaluator. Quoted,
    computed, shorthand and spread keys refuse. Nested expressions are never run.
    """
    mask = list(source)
    stack = []
    quote = None
    comment = None
    escaped = False
    index = 0
    pairs = {"}": "{", "]": "[", ")": "("}
    while index < len(source):
        character = source[index]
        following = source[index:index + 2]
        if comment is not None:
            mask[index] = " "
            if comment == "line" and character == "\n":
                comment = None
            elif comment == "block" and following == "*/":
                mask[index:index + 2] = [" ", " "]
                index += 1
                comment = None
        elif quote is not None:
            mask[index] = " "
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif following in ("//", "/*"):
            mask[index:index + 2] = [" ", " "]
            comment = "line" if following == "//" else "block"
            index += 1
        elif character in ("'", '"', "`"):
            quote = character
            mask[index] = " "
        elif character == "\\" and index + 1 < len(source):
            # Escaped punctuation inside an opaque nested regex is not syntax.
            mask[index:index + 2] = [" ", " "]
            index += 1
        elif character in "{[(":
            stack.append(character)
            mask[index] = " "
        elif character in "}])":
            if not stack or stack.pop() != pairs[character]:
                raise InventoryError("unsupported or unbalanced registry expression")
            mask[index] = " "
        elif stack:
            mask[index] = " "
        index += 1
    if stack or quote is not None or comment == "block":
        raise InventoryError("unterminated registry expression")
    visible = "".join(mask)
    boundaries = [-1, *[i for i, character in enumerate(visible) if character == ","], len(source)]
    result = []
    seen = set()
    for left, right in pairwise(boundaries):
        start = left + 1
        segment = visible[start:right]
        if not segment.strip():
            continue
        match = re.match(r"\s*([A-Za-z_$][\w$]*)\s*:", segment)
        if match:
            name = match.group(1)
            value = source[start + match.end():right].strip()
        elif re.fullmatch(r"\s*(?:async\s+)?handler\s*", segment):
            name, value = "handler", source[start:right].strip()
        else:
            raise InventoryError("expanded, computed, alias or shorthand registry properties are unsupported")
        if name in seen:
            raise InventoryError("duplicate registry properties are unsupported")
        seen.add(name)
        position = start + match.start(1) if match else start
        result.append({"name": name, "value": value, "start": position})
    return result


def javascript_commands(source: str) -> list[dict]:
    """Read supported literal registry entries without importing application JS."""
    match = re.search(r"^export const COMMANDS = \{\n(.*?)^\};", source, re.MULTILINE | re.DOTALL)
    if not match:
        raise InventoryError("extension COMMANDS literal registry not found")
    result = []
    for entry in _object_properties(match.group(1)):
        value = entry["value"]
        if not (value.startswith("{") and value.endswith("}")):
            raise InventoryError("extension entries must be literal objects")
        fields = {field["name"]: field["value"] for field in _object_properties(value[1:-1])}
        if "describe" not in fields or "handler" not in fields:
            raise InventoryError("extension command description or handler is missing")
        description = _javascript_text(ast.parse("(" + fields["describe"] + ")", mode="eval").body)
        flags = {}
        for key in ("readOnly", "destructive"):
            if key in fields and fields[key] not in ("true", "false"):
                raise InventoryError("extension command flags must be literal booleans")
            flags[key] = fields.get(key) == "true"
        result.append({"name": entry["name"], "description": description,
                       "symbol": "COMMANDS." + entry["name"] + ".handler",
                       "line": source[:match.start(1) + entry["start"]].count("\n") + 1,
                       "read_only": flags["readOnly"], "destructive": flags["destructive"]})
    if not result:
        raise InventoryError("extension registry contains no supported command entries")
    return _unique(result)


def _javascript_text(node) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _javascript_text(node.left) + _javascript_text(node.right)
    raise InventoryError("JavaScript descriptions must be literal strings or their concatenation")


def _unique(rows):
    names = [row["name"] for row in rows]
    if any(not isinstance(name, str) or not name for name in names):
        raise InventoryError("command names must be nonempty strings")
    if len(names) != len(set(names)):
        raise InventoryError("command names must be nonempty and unique within a registry")
    if any(not isinstance(row["description"], str) for row in rows):
        raise InventoryError("command descriptions must be strings")
    return sorted(rows, key=lambda row: row["name"])


def _read(root: Path, relative: str, sources: dict) -> str:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        raise InventoryError("inventory source must exist within the repository: " + relative)
    raw = path.read_bytes()
    sources[relative] = {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}
    return raw.decode("utf-8")


def _financial_policy(registry: str, name: str, read_only: bool) -> dict:
    known = ((registry == "executor" and name in ("swap", "manager.swap"))
             or (registry == "soltui" and name in ("coinbase.order_submit", "coinbase.order_quick",
                 "coinbase.order_percent_quick", "coinbase.order_conditional_quick", "jupiter.order_submit", "jupiter.order_quick"))
             or (registry == "extension" and name in ("tick", "cancelOrder")))
    return {"financial_signing_or_submit": "conditional-guarded-capability" if known else "not-inferred-from-registry-metadata",
            "side_effects": "read-only declaration; external reads may occur" if read_only else "may mutate state; inspect handler and runtime gates",
            "ambiguity_policy": "Never infer an automatic retry. A possibly submitted financial write requires journal/venue reconciliation.",
            "classification_limit": "Documentation metadata; no runtime enforcement or exhaustive call-graph proof."}


def build(root: Path = ROOT) -> dict[str, dict]:
    """Build stable JSON values; never execute registered commands or tools."""
    sources = {}
    operations = []
    registry_specs = [(name, path, gate, python_commands) for name, path, gate in REGISTRIES]
    registry_specs.append(("extension", "extension/src/core/commands.js", "extension/test", javascript_commands))
    for registry, path, gate, parser in registry_specs:
        for row in parser(_read(root, path, sources)):
            operations.append({"id": registry + ":" + row["name"], "registry": registry, "source": path,
                               "gate_refs": [gate], "help_reference": "Authoritative registry description and surface discovery; no handler executed.",
                               **row, **_financial_policy(registry, row["name"], row["read_only"])})
    tools = []
    for component in COMPONENTS:
        manifest = component + "/pyproject.toml"
        project = tomllib.loads(_read(root, manifest, sources)).get("project", {})
        for name, entrypoint in sorted(project.get("scripts", {}).items()):
            module, symbol = entrypoint.split(":", 1)
            candidate = module.replace(".", "/") + ".py"
            candidates = (candidate, component + "/src/" + candidate)
            location = next((value for value in candidates if (root / value).is_file()), None)
            if location is None:
                raise InventoryError("declared entrypoint source is missing: " + name)
            _read(root, location, sources)
            tools.append({"id": "python:" + name, "kind": "installed-python-entrypoint", "manifest": manifest,
                          "source": location, "symbol": symbol, "help_command": name + " --help",
                          "side_effects": "command-specific; help parsing does not authorize execution",
                          "signing": "not inferred; inspect guarded command registry/runtime", "ambiguity": "no automatic financial-write retry",
                          "gate_refs": [component + "/tests"]})
    for name, source, help_command in MANUAL_TOOLS:
        _read(root, source, sources)
        tools.append({"id": "tool:" + name, "kind": "explicit-source-tool", "source": source,
                      "symbol": "main or documented script entry", "help_command": help_command,
                      "side_effects": "tool-specific; service/build tools can mutate local state when explicitly invoked",
                      "signing": "not inferred; this inventory never invokes the tool", "ambiguity": "no financial retry inferred",
                      "gate_refs": [".cdo/reviews-2026-11-12/coverage.json"]})
    for relative in ("package.json", "extension/package.json", "website/package.json"):
        if not (root / relative).is_file():
            continue
        package = json.loads(_read(root, relative, sources))
        for name, command in sorted(package.get("scripts", {}).items()):
            tools.append({"id": relative + ":" + name, "kind": "npm-script", "source": relative,
                          "symbol": "scripts." + name, "declared_command": command, "help_command": None,
                          "side_effects": "script-specific; inspect declared command before invoking",
                          "signing": "not inferred from npm metadata", "ambiguity": "no financial retry inferred",
                          "gate_refs": [relative]})
    tool_ids = [tool["id"] for tool in tools]
    if len(tool_ids) != len(set(tool_ids)):
        raise InventoryError("tool IDs must be unique across manifests and explicit tools")
    common = {"schema_version": "1.0.0", "version": "1.0.0", "delta": "Initial source-bound docs-only inventory.",
              "generator": "scripts/build_operation_inventories.py",
              "scope": "Three authoritative command registries, declared Python entrypoints, explicit source tools and existing npm scripts.",
              "limits": ["Not an exhaustive list of every internal function, external call, research script or runtime operation.",
                         "No shared runtime error schema, generic retry or remediation implementation is claimed.",
                         "Source/help/gate references are navigation; they do not establish live signing, installation or production acceptance."],
              "sources": [sources[name] for name in sorted(sources)]}
    return {"docs/operations-registry.json": {**common, "operations": sorted(operations, key=lambda row: row["id"])},
            "docs/tool-inventory.json": {**common, "tools": sorted(tools, key=lambda row: row["id"])}}


def materialize(root: Path, *, check: bool = False) -> list[str]:
    """Return drifted paths; --check leaves every byte unchanged."""
    drift = []
    for relative, value in build(root).items():
        path = root / relative
        if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise InventoryError("generated inventory destination must remain inside the repository")
        expected = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
        if not path.is_file() or path.read_text() != expected:
            drift.append(relative)
            if not check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(expected)
    return drift


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="refuse missing/stale inventories without writing")
    args = parser.parse_args(argv)
    try:
        drift = materialize(ROOT, check=args.check)
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"Inventory generation refused ({type(exc).__name__}); inspect declared source metadata.", file=sys.stderr)
        return 2
    if args.check and drift:
        print("Inventory drift: " + ", ".join(drift) + ". Regenerate with python3 scripts/build_operation_inventories.py", file=sys.stderr)
        return 1
    print("Operation/tool inventories are current." if args.check else "Operation/tool inventories generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

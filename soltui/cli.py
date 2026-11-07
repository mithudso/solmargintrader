"""Command-line surface: `soltui call <name> [--param k=v ...] [--json '{...}']` and `soltui list`.

Prints the registry envelope (`commands.dumps`) on stdout, one line, and exits 0 when `ok` else 1.
No logic of its own: parsing arguments into params is all it does; `dispatch` does the rest, including
the call log.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, TextIO

from . import commands


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="soltui", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="verb", required=True)
    sub.add_parser("list", help="every command with its parameters")
    call = sub.add_parser("call", help="run one command")
    call.add_argument("name", help="dotted command name, e.g. roster.list")
    call.add_argument("--param", "-p", action="append", default=[], metavar="K=V",
                      help="a parameter; typed from the command's declaration (repeatable)")
    call.add_argument("--json", dest="json_params", default=None, metavar="OBJECT",
                      help="parameters as one JSON object (merged under --param)")
    return parser


def params_from_args(name: str, pairs: list[str], json_params: str | None) -> dict[str, Any]:
    """Build the params object. Raises CommandError(bad_params) for malformed input."""
    params: dict[str, Any] = {}
    if json_params is not None:
        try:
            parsed = json.loads(json_params)
        except ValueError:
            raise commands.CommandError("bad_params", "--json is not valid JSON") from None
        if not isinstance(parsed, dict):
            raise commands.CommandError("bad_params", "--json must be a JSON object")
        params.update(parsed)
    strings: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise commands.CommandError("bad_params", f"expected K=V, got {pair!r}")
        strings[key] = value
    params.update(commands.coerce_pairs(name, strings))
    return params


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    out = out or sys.stdout
    args = _build_parser().parse_args(argv)
    if args.verb == "list":
        env = commands.dispatch("list", {}, surface="cli")
    else:
        try:
            params = params_from_args(args.name, args.param, args.json_params)
        except commands.CommandError as exc:
            # Parsing failed before dispatch; still log it the same way every other refusal is.
            env = commands.error_envelope(args.name, exc.code, exc.message)
            commands._log_call("cli", args.name, env, 0, [])
        else:
            env = commands.dispatch(args.name, params, surface="cli")
    out.write(commands.dumps(env) + "\n")
    out.flush()
    return 0 if env["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

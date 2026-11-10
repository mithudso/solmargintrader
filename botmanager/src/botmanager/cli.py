"""Parse, dispatch, render, and select an exit code; no application logic."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from .registry import (
    COMMANDS,
    ERROR_EXIT_CODES,
    GLOBAL_ARGUMENTS,
    CommandContext,
    dispatch,
)
from .walkthrough import render as render_walkthrough


class InputError(Exception):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse normally repeats every unrecognised argument, including secrets.
        raise InputError


def parser() -> argparse.ArgumentParser:
    root = SafeParser(
        prog="solbot",
        description="Manage saved paper bot drafts and bounded reference paper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=render_walkthrough(),
    )
    for flags, options in GLOBAL_ARGUMENTS:
        root.add_argument(*flags, **options)
    subcommands = root.add_subparsers(dest="command", required=True)
    for command in COMMANDS.values():
        child = subcommands.add_parser(
            command.name, help=command.description, description=command.description
        )
        for flags, options in command.arguments:
            child.add_argument(*flags, **options)
    return root


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    root = parser()
    if not arguments:
        root.print_help()
        return 0
    try:
        args = vars(root.parse_args(arguments))
        command = args.pop("command")
        context_args = {
            options["dest"]: args.pop(options["dest"])
            for _, options in GLOBAL_ARGUMENTS
        }
        envelope = dispatch(command, args, CommandContext(**context_args))
    except InputError:
        envelope = dispatch("__invalid_input__", {})
    if (
        envelope["ok"]
        and (
            command == "metrics"
            or (command == "report" and args.get("format") in ("human", "csv"))
        )
    ):
        print(envelope["data"]["rendered"])
    else:
        print(json.dumps(envelope, sort_keys=True, allow_nan=False))
    return 0 if envelope["ok"] else ERROR_EXIT_CODES.get(envelope["error"]["code"], 2)

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
        epilog=(
            "Start here (creating a draft starts no worker):\n"
            "  solbot create grid --name my-grid\n"
            "  solbot config my-grid --effective\n"
            "  solbot status my-grid --why\n\n"
            "Running a bot requires explicit input, a start request,\n"
            "and an explicitly running 'solbot daemon' or installed service.\n"
            "Edit saved settings with solbot edit; solbot apply explicitly adopts them.\n"
            "Current runtime: bounded historical/prospective reference families. Learning\n"
            "and executor entries retain source, sample, clock and authority gates.\n\n"
            "Working example and exact steps:\n"
            "https://github.com/mithudso/solmargintrader/blob/master/docs/bot-manager-quickstart.md"
        ),
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
        and command == "report"
        and args.get("format") in ("human", "csv")
    ):
        print(envelope["data"]["rendered"])
    else:
        print(json.dumps(envelope, sort_keys=True, allow_nan=False))
    return 0 if envelope["ok"] else ERROR_EXIT_CODES.get(envelope["error"]["code"], 2)

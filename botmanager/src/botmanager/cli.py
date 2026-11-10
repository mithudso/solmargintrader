"""Parse, dispatch, render, and select an exit code; no application logic."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .registry import COMMANDS, ERROR_EXIT_CODES, CommandContext, dispatch


class InputError(Exception):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse normally repeats every unrecognised argument, including secrets.
        raise InputError


def parser() -> argparse.ArgumentParser:
    root = SafeParser(
        prog="solbot",
        description="Manage saved paper bot drafts and recorded grid replay.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Start here (creating a draft starts no worker):\n"
            "  solbot create grid --name my-grid\n"
            "  solbot config my-grid --effective\n"
            "  solbot status my-grid --why\n\n"
            "Running a grid requires registered recorded input, a start request,\n"
            "and an explicitly running 'solbot daemon' or installed service.\n"
            "Edit saved settings with solbot edit; solbot apply explicitly adopts them.\n"
            "Current runtime: recorded Coinbase grid replay only. Real-time Jupiter\n"
            "trading, the other strategy runtimes and learning remain unfinished.\n\n"
            "Working example and exact steps:\n"
            "https://github.com/mithudso/solmargintrader/blob/master/docs/bot-manager-quickstart.md"
        ),
    )
    root.add_argument(
        "--ecosystem-home",
        type=Path,
        help="Read registered external paper trials from this explicit ecosystem home.",
    )
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
        ecosystem_home = args.pop("ecosystem_home", None)
        envelope = dispatch(
            command, args, CommandContext(ecosystem_home=ecosystem_home)
        )
    except InputError:
        envelope = dispatch("__invalid_input__", {})
    print(json.dumps(envelope, sort_keys=True, allow_nan=False))
    return 0 if envelope["ok"] else ERROR_EXIT_CODES.get(envelope["error"]["code"], 2)

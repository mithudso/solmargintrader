"""Parse, dispatch, render, and select an exit code; no application logic."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .registry import COMMANDS, ERROR_EXIT_CODES, dispatch


class InputError(Exception):
    pass


class SafeParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse normally repeats every unrecognised argument, including secrets.
        raise InputError


def parser() -> argparse.ArgumentParser:
    root = SafeParser(
        prog="solbot", description="Persistent paper/disarmed Solana bot drafts."
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
    try:
        args = vars(parser().parse_args(argv))
        command = args.pop("command")
        envelope = dispatch(command, args)
    except InputError:
        envelope = dispatch("__invalid_input__", {})
    print(json.dumps(envelope, sort_keys=True, allow_nan=False))
    return 0 if envelope["ok"] else ERROR_EXIT_CODES.get(envelope["error"]["code"], 2)

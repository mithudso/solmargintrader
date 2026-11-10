from __future__ import annotations

import os
import re
import shlex
import subprocess
import unittest
from unittest.mock import patch
from uuid import UUID

from botmanager.cli import parser
from botmanager.registry import COMMANDS
from botmanager.walkthrough import SETUP, STAGES, render, workflow

FIXTURE_ENV = {
    "HOME": "/tmp/solbot-walkthrough",
    "SOLBOT_HOME": "/tmp/solbot-walkthrough/manager",
    "SOLBOT_ECOSYSTEM_HOME": "/tmp/solbot-walkthrough/ecosystem",
    "PAPER_RUN_ID": "5c19f574-f1a6-41f2-947b-9f15690a05bf",
    "RUN_ID": "91ba29a8-01ba-441f-9c82-fe91494f8dc0",
    "PROPOSAL_ID": "proof-from-canonical-owner",
    "BROWSER_ID": "browser:970aeedc-2179-4b46-8960-ab6c76c29a4c:grid",
    "BROWSER_GENERATION": "2",
    "BROWSER_HASH": "a" * 64,
    "EXECUTOR_PYTHON": "/tmp/solbot-walkthrough/executor/bin/python",
    "EXECUTOR_REQUEST_ID": "0dbdaffd-e3af-4666-b4f1-52f1f2ab95f9",
}


def command_examples():
    for stage in STAGES:
        for line in (*stage.before, *stage.commands, *stage.shell):
            if line.startswith("solbot "):
                yield line


class WalkthroughTests(unittest.TestCase):
    def test_every_published_solbot_example_parses_against_actual_registry(self):
        root = parser()
        seen = set()
        choices = {}
        with patch.dict(os.environ, FIXTURE_ENV):
            for line in command_examples():
                with self.subTest(command=line):
                    self.assertIsNone(re.search(r"<[A-Z_]+>", line))
                    expanded = os.path.expandvars(line)
                    self.assertNotRegex(expanded, r"\$[A-Z_]+")
                    argv = shlex.split(expanded)
                    if ">" in argv:
                        argv = argv[: argv.index(">")]
                    args = root.parse_args(argv[1:])
                    seen.add(args.command)
                    for key, value in vars(args).items():
                        if isinstance(value, str):
                            choices.setdefault((args.command, key), set()).add(value)
                    if getattr(args, "request_id", None):
                        self.assertEqual(str(UUID(args.request_id)), args.request_id)
        self.assertEqual(
            seen, set(COMMANDS), "New commands need ordered runnable help examples."
        )
        for name, argument in (
            ("stack", "action"),
            ("ui", "action"),
            ("service", "action"),
            ("browser-control", "operation"),
            ("prepare-input", "mode"),
            ("report", "format"),
        ):
            options = next(
                options
                for flags, options in COMMANDS[name].arguments
                if flags == (argument,)
                or options.get("dest") == argument
                or flags == ("--" + argument,)
            )
            self.assertEqual(choices[(name, argument)], set(options["choices"]))

    def test_stage_numbers_have_recommended_order(self):
        numbers = [int(re.match(r"\d+", stage.title)[0]) for stage in STAGES]
        self.assertEqual(numbers, sorted(numbers))

    def test_all_shell_recipes_are_valid_posix_shell_syntax(self):
        script = "\n".join(
            (
                *SETUP,
                *(
                    line
                    for stage in STAGES
                    for line in (*stage.before, *stage.commands, *stage.shell)
                ),
            )
        )
        run = subprocess.run(
            ["/bin/sh", "-n"], input=script, text=True, capture_output=True, check=False
        )
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_structured_and_terminal_help_keep_the_same_examples(self):
        body = workflow()
        text = render()
        self.assertEqual(len(body["stages"]), len(STAGES))
        for command in command_examples():
            self.assertIn(command, text)
        for phrase in (
            "verified URL",
            "actual seven-day",
            "never recreate",
            "flat boundary",
            "Native Windows",
            "user login",
        ):
            self.assertIn(phrase.lower(), text.lower())

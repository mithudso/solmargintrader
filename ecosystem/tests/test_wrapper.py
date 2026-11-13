from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.bootstrap_ecosystem import REPO, main


class WrapperTests(unittest.TestCase):
    def test_invalid_flag_never_installs(self):
        with (
            patch("ecosystem.installation.install_environment") as install,
            redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            main(["start", "--unknown-flag"])
        install.assert_not_called()

    def test_option_value_cannot_become_command(self):
        with (
            patch(
                "ecosystem.installation.install_environment",
                return_value={"status": "failed"},
            ) as install,
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(main(["--coins", "stop"]), 2)
        install.assert_called_once()

    def test_offline_does_not_install_or_download(self):
        with (
            patch("ecosystem.installation.install_environment") as install,
            patch(
                "ecosystem.installation.verify_environment",
                return_value={"status": "failed"},
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                main(["start", "--offline", "--venv", "/missing/ecosystem-env"]), 2
            )
        install.assert_not_called()

    def test_constraints_are_explicit_install_arguments_not_forwarded_cli_flags(self):
        with (
            patch("ecosystem.installation.install_environment",
                  return_value={"status": "complete"}) as install,
            patch("scripts.bootstrap_ecosystem.subprocess.run",
                  return_value=SimpleNamespace(returncode=0)) as run,
        ):
            code = main(["start", "--venv", "/private/new-env", "--constraints", "/private/pins.txt",
                         "--coins", "SOL"])
        self.assertEqual(code, 0)
        install.assert_called_once_with(REPO, Path("/private/new-env"),
                                         constraints_file=Path("/private/pins.txt"))
        self.assertEqual(run.call_args.args[0], ["/private/new-env/bin/python", "-I", "-m",
                                                "ecosystem.cli", "start", "--coins", "SOL"])

    def test_no_constraints_preserves_the_original_install_call(self):
        with (
            patch("ecosystem.installation.install_environment",
                  return_value={"status": "complete"}) as install,
            patch("scripts.bootstrap_ecosystem.subprocess.run",
                  return_value=SimpleNamespace(returncode=0)),
        ):
            self.assertEqual(main(["start", "--venv", "/private/new-env"]), 0)
        install.assert_called_once_with(REPO, Path("/private/new-env"))

    def test_help_documents_constraints_without_installing(self):
        output = io.StringIO()
        with (
            patch("ecosystem.installation.install_environment") as install,
            redirect_stdout(output),
            self.assertRaises(SystemExit) as result,
        ):
            main(["--help"])
        self.assertEqual(result.exception.code, 0)
        self.assertIn("--constraints", output.getvalue())
        self.assertIn("SHA-256", output.getvalue())
        install.assert_not_called()

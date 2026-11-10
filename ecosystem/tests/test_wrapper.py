from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from scripts.bootstrap_ecosystem import main


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

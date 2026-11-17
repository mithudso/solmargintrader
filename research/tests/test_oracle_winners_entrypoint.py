"""The advertised TUI command must route its alias, not pass it to argparse."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import oracle_winners


class EntryPoint(unittest.TestCase):
    def test_advertised_tui_alias_and_existing_no_alias_share_the_same_arguments(self):
        for argv in (
            ["oracle_winners.py", "tui", "--refresh", "10"],
            ["oracle_winners.py", "--refresh", "10"],
        ):
            with (
                self.subTest(argv=argv),
                patch("sys.argv", argv),
                patch("research.zec_tui.main", return_value=0) as run,
            ):
                self.assertEqual(oracle_winners.main(), 0)
                run.assert_called_once_with(["--refresh", "10"])

    def test_plain_mode_compatibility_is_retained(self):
        with (
            patch("sys.argv", ["oracle_winners.py", "--plain", "--frames", "1"]),
            patch("research.zec_live.main", return_value=0) as run,
        ):
            self.assertEqual(oracle_winners.main(), 0)
            run.assert_called_once_with(["--frames", "1"])

    def test_unknown_positional_is_not_silently_discarded(self):
        with (
            patch("sys.argv", ["oracle_winners.py", "unknown"]),
            patch("research.zec_tui.main", return_value=0) as run,
        ):
            self.assertEqual(oracle_winners.main(), 0)
            run.assert_called_once_with(["unknown"])


if __name__ == "__main__":
    unittest.main()

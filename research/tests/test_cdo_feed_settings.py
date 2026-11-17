"""Damaged saved preferences must not silently reactivate feeds."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.zec_feed_settings import load_feeds


class FeedPreferencesTests(unittest.TestCase):
    def test_new_install_uses_existing_enabled_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                load_feeds(Path(directory) / "missing.json"),
                {"jupiter": True, "coinbase": True},
            )

    def test_invalid_or_unreadable_preferences_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preferences.json"
            path.write_text("{")
            with self.assertLogs("research.zec_feed_settings", level="WARNING"):
                self.assertEqual(
                    load_feeds(path), {"jupiter": False, "coinbase": False}
                )
            with (
                patch.object(Path, "lstat", side_effect=PermissionError("fixture")),
                self.assertLogs("research.zec_feed_settings", level="WARNING"),
            ):
                self.assertEqual(
                    load_feeds(path), {"jupiter": False, "coinbase": False}
                )

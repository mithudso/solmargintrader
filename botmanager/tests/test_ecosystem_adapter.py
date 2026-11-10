from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from botmanager.adapters.ecosystem import discover_ecosystem


class EcosystemAdapterTests(unittest.TestCase):
    def test_absent_configuration_is_explicit_and_inert(self):
        result = discover_ecosystem()
        self.assertEqual(result["reason"], "ecosystem_not_connected")
        self.assertFalse(result["controls_available"])
        self.assertFalse(result["ownership_transfer"])

    def test_missing_configured_home_does_not_create_state(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root) / "missing"
            result = discover_ecosystem(home)
            self.assertEqual(result["status"], "unavailable")
            self.assertFalse(home.exists())
            self.assertTrue(result["read_only"])


if __name__ == "__main__":
    unittest.main()

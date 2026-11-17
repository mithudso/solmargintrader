"""Malformed component identifiers must leave the panel usable."""

import unittest

from research.zec_leverage_panel import mtf_tilt_text


class ComponentValidationTests(unittest.TestCase):
    def test_unhashable_component_minutes_are_unknown(self):
        for minutes in ([], {}):
            with self.subTest(minutes=minutes):
                result = mtf_tilt_text({"10": {"components": [{"minutes": minutes}]}})
                self.assertIn("5m ?", result)
                self.assertIn("10m ?", result)

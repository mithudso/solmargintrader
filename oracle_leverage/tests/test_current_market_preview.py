"""Current YOLO market-preview disclosures; no signing or network."""

import tempfile
import unittest
from pathlib import Path

from oracle_leverage.console import VENUES, Console
from oracle_leverage.tests.test_console import FakeCLI, FakeSDK


class CurrentMarketPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cli = FakeCLI()
        self.sdk = FakeSDK()
        original = self.sdk.call

        def call(payload):
            result = original(payload)
            if payload["action"] == "service-build-open":
                result["checked"].update(
                    verification="current_observed_subset",
                    simulatedEntryPrice="65100000000000000",
                    priceScale="1000000000000",
                )
            return result

        self.sdk.call = call
        self.console = Console(Path(self.tmp.name) / "home", cli=self.cli, sdk=self.sdk)

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_market_preview_discloses_nonbinding_price_and_close_gap(self):
        result = self.console.preview("BTC", VENUES[1], "long", "5")
        self.assertEqual(result["status"], "ready")
        self.assertIn("Market order; simulated entry $65100", result["message"])
        self.assertIn("indicative and may change", result["message"])
        self.assertIn("close is unavailable in this client", result["message"])
        self.assertIn("failed transaction can incur up to 0.01 SOL", result["message"])
        self.assertEqual(self.cli.signed, 0)

    def test_current_market_preview_rejects_missing_simulated_price(self):
        old = self.sdk.call

        def call(payload):
            result = old(payload)
            if payload["action"] == "service-build-open":
                result["checked"].pop("simulatedEntryPrice")
            return result

        self.sdk.call = call
        result = self.console.preview("BTC", VENUES[1], "long", "5")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(self.cli.signed, 0)

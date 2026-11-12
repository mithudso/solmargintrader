"""Read-only market failures retain safe diagnostics without transport secrets."""
from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from soltui import current_signal, live_price, spot_prices
from soltui.wallet import WalletHttpError


class MarketDiagnosticTests(unittest.TestCase):
    def events(self, captured):
        return [json.loads(record.getMessage()) for record in captured.records]

    def test_jupiter_attempt_outcome_and_error_redaction(self):
        secret = "PRIVATE_TRANSPORT_FIXTURE"
        with patch.dict("os.environ", {"JUPITER_API_KEY": secret}), patch.object(
            live_price.urllib.request, "urlopen", side_effect=OSError(secret)
        ), self.assertLogs("soltui.market", level="INFO") as captured:
            with self.assertRaises(ValueError):
                live_price._get("/price/v3", {"ids": secret})
        events = self.events(captured)
        self.assertEqual([row["outcome"] for row in events], ["started", "failed"])
        self.assertEqual(events[-1]["error_type"], "OSError")
        self.assertNotIn(secret, str(events))
        with patch.object(live_price.urllib.request, "urlopen", return_value=io.BytesIO(b'{"ok":true}')), self.assertLogs("soltui.market", level="INFO") as success:
            self.assertEqual(live_price._get("/price/v3", {}), {"ok": True})
        self.assertEqual([row["outcome"] for row in self.events(success)], ["started", "completed"])

    def test_missing_coinbase_price_is_logged_without_raw_error_text(self):
        def missing(_url):
            raise WalletHttpError(404, "PRIVATE_COINBASE_FIXTURE")
        with self.assertLogs("soltui.market", level="INFO") as captured:
            prices, errors = spot_prices.spot_prices(missing, ["SOL"])
        self.assertEqual(prices, {"SOL": None})
        self.assertEqual(errors, [])
        events = self.events(captured)
        self.assertEqual([row["outcome"] for row in events], ["started", "unavailable"])
        self.assertNotIn("PRIVATE_COINBASE_FIXTURE", str(events))

    def test_manual_assessment_failure_keeps_fixed_operation_context(self):
        def failed(*_args, **_kwargs):
            raise OSError("PRIVATE_ASSESSMENT_FIXTURE")
        with self.assertLogs("soltui.market", level="INFO") as captured:
            with self.assertRaises(OSError):
                current_signal.check("SOL", [], fetch=failed, clock=lambda: 10)
        events = self.events(captured)
        self.assertEqual([row["outcome"] for row in events], ["started", "failed"])
        self.assertEqual(events[-1]["operation"], "signal.current_check")
        self.assertNotIn("PRIVATE_ASSESSMENT_FIXTURE", str(events))

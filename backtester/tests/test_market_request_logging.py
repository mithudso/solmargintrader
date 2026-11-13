"""Request diagnostics stay useful without copying private provider content."""

from contextlib import contextmanager
import io
import unittest
from unittest.mock import patch

from backtester.core import archive_price, fetch, fetch_minutes, fetch_minutes_alt, kucoin_history
from backtester.core.market_diagnostics import market_request


class MarketRequestLoggingTests(unittest.TestCase):
    def test_dynamic_label_is_refused_without_logging_its_content(self):
        with self.assertNoLogs("backtester.market"), self.assertRaisesRegex(ValueError, "unknown market request operation"):
            with market_request("PRIVATE_CANARY"):
                self.fail("unknown operation entered the request body")

    def _calls(self):
        return [
            ("coinbase", lambda: fetch._get_json("https://example.invalid/?token=PRIVATE_CANARY", retries=1), b"[]"),
            ("coinbase_minutes", lambda: fetch_minutes.get_candles("https://example.invalid/?token=PRIVATE_CANARY"), b"[]"),
            ("alternate_candles", lambda: fetch_minutes_alt.http_json("https://example.invalid/?token=PRIVATE_CANARY"), b"{}"),
            ("kucoin_history", lambda: kucoin_history._get_unlocked("https://example.invalid/?token=PRIVATE_CANARY"), b"{}"),
            ("spot_archive", lambda: archive_price.fetch_spot("fixture"), b'{"fixture":{"usdPrice":1.25}}'),
        ]

    def test_each_successful_request_emits_fixed_operation_and_outcome(self):
        for operation, call, body in self._calls():
            @contextmanager
            def response(*_args, **_kwargs):
                yield io.BytesIO(body)
            with self.subTest(operation=operation), patch("urllib.request.urlopen", response):
                with self.assertLogs("backtester.market", level="INFO") as records:
                    call()
                self.assertEqual([r.outcome for r in records.records], ["attempt", "success"])
                self.assertEqual([r.operation for r in records.records], [operation, operation])
                self.assertNotIn("PRIVATE_CANARY", " ".join(records.output))

    def test_each_request_failure_records_only_exception_class(self):
        for operation, call, _body in self._calls():
            with self.subTest(operation=operation), patch("urllib.request.urlopen", side_effect=RuntimeError("PRIVATE_CANARY")):
                with self.assertLogs("backtester.market", level="INFO") as records:
                    with self.assertRaises(RuntimeError):
                        call()
                self.assertEqual([r.outcome for r in records.records], ["attempt", "failed"])
                self.assertEqual(records.records[-1].levelname, "WARNING")
                self.assertEqual(records.records[-1].error_type, "RuntimeError")
                self.assertNotIn("PRIVATE_CANARY", repr([r.__dict__ for r in records.records]))


if __name__ == "__main__":
    unittest.main()

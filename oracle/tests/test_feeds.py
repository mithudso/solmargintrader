from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from oracle.feeds import (
    JUPITER_PRICE_URL,
    MAX_RESPONSE_BYTES,
    SOL_MINT,
    USDC_MINT,
    FeedUnavailable,
    JupiterPriceFeed,
    RecorderFeed,
    _get_json,
    _NoRedirect,
)


class RecorderFeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.feed = RecorderFeed(self.root, clock=lambda: 100)

    def write(self, *, pair="SOL-USDC", stamp=99, quoted=98, bid=99, ask=101):
        (self.root / "latest.json").write_text(
            json.dumps({"t": stamp, "q": {pair: [bid, ask, 100, 1, 1, quoted]}})
        )

    def test_exact_pair_read_only_snapshot_and_duplicate(self):
        self.write()
        before = (self.root / "latest.json").read_bytes()
        out = self.feed.poll()
        self.assertEqual(out["instrument"], "SOL/USDC")
        self.assertEqual(out["venue"], "coinbase_exchange")
        self.assertEqual(out["price"], 100)
        self.assertEqual(out["observed_at"], 98)
        self.assertIsNone(self.feed.poll())
        self.assertEqual((self.root / "latest.json").read_bytes(), before)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_usd_market_is_not_substituted(self):
        self.write(pair="SOL-USD")
        with self.assertRaisesRegex(FeedUnavailable, "instrument_unavailable"):
            self.feed.poll()

    def test_stale_snapshot_or_quote_or_future_clock_refused(self):
        for kwargs in ({"stamp": 80}, {"quoted": 80}, {"stamp": 101}, {"quoted": 101}):
            self.write(**kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(FeedUnavailable):
                self.feed.poll()

    def test_missing_or_malformed_refused(self):
        with self.assertRaisesRegex(FeedUnavailable, "recorder_unavailable"):
            self.feed.poll()
        for raw in ("{", "null", "[]", '{"q":{}}'):
            (self.root / "latest.json").write_text(raw)
            with self.subTest(raw=raw), self.assertRaises(FeedUnavailable):
                self.feed.poll()

    def test_invalid_spread_and_nan_refused(self):
        for bid, ask in ((102, 101), (float("nan"), 101), (True, 101), (0, 101)):
            self.write(bid=bid, ask=ask)
            with self.subTest(bid=bid), self.assertRaises(FeedUnavailable):
                self.feed.poll()


class JupiterFeedTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"JUPITER_API_KEY": "test-secret-not-real"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.now = 100
        self.payload = {
            SOL_MINT: {"usdPrice": 150, "blockId": 1000},
            USDC_MINT: {"usdPrice": 0.999, "blockId": 1001},
        }
        self.calls = []

        def transport(url, headers, timeout, max_bytes):
            self.calls.append((url, headers, timeout, max_bytes))
            return self.payload

        self.feed = JupiterPriceFeed(clock=lambda: self.now, transport=transport)

    def test_reference_ratio_and_timestamp_limit_are_explicit(self):
        out = self.feed.poll()
        self.assertEqual(out["kind"], "polled_reference_ratio")
        self.assertAlmostEqual(out["price"], 150 / 0.999)
        self.assertFalse(out["upstream_recency_verified"])
        self.assertIn("upstream_event_time_unknown", out["timestamp_semantics"])
        self.assertNotIn("test-secret", json.dumps(out))
        self.assertEqual(self.calls[0][0], JUPITER_PRICE_URL)
        self.assertEqual(self.calls[0][3], MAX_RESPONSE_BYTES)
        self.assertIsNone(self.feed.poll())

    def test_missing_credentials_refuse_before_transport(self):
        for value in ("", "\nsecret", "secret\r\nHeader: value"):
            with (
                patch.dict(os.environ, {"JUPITER_API_KEY": value}),
                self.assertRaisesRegex(
                    FeedUnavailable, "credentials_missing_or_invalid"
                ),
            ):
                self.feed.poll()
        self.assertEqual(self.calls, [])

    def test_restart_same_payload_is_a_new_receipt_sample(self):
        first = self.feed.poll()
        restarted = JupiterPriceFeed(
            clock=lambda: 101, transport=lambda *args: self.payload
        )
        second = restarted.poll()
        self.assertNotEqual(first["event_id"], second["event_id"])
        self.assertEqual(first["provider_block_ids"], second["provider_block_ids"])
        self.assertEqual(second["observed_at"], 101)

    def test_missing_mint_is_unavailable(self):
        del self.payload[USDC_MINT]
        with self.assertRaisesRegex(FeedUnavailable, "instrument_unavailable"):
            self.feed.poll()

    def test_nonfinite_boolean_and_nonpositive_prices_refused(self):
        for value in (float("nan"), float("inf"), True, 0, -1, "150", 10**400):
            self.payload[SOL_MINT]["usdPrice"] = value
            with self.subTest(value=value), self.assertRaises(FeedUnavailable):
                self.feed.poll()

    def test_stalled_and_regressing_blocks_fail_closed(self):
        self.feed.poll()
        self.now = 116
        with self.assertRaisesRegex(FeedUnavailable, "upstream_block_stalled"):
            self.feed.poll()
        self.now = 105
        self.payload[SOL_MINT]["blockId"] = 999
        with self.assertRaisesRegex(FeedUnavailable, "upstream_block_regressed"):
            self.feed.poll()

    def test_one_frozen_mint_cannot_be_hidden_by_other_progress(self):
        self.feed.poll()
        self.now = 116
        self.payload[SOL_MINT]["blockId"] += 50
        with self.assertRaisesRegex(FeedUnavailable, "upstream_block_stalled"):
            self.feed.poll()
        self.now = 117
        self.payload[SOL_MINT]["blockId"] = 1001
        self.payload[USDC_MINT]["blockId"] = 1002
        self.assertIsNotNone(self.feed.poll())

    def test_receipt_clock_is_sampled_after_transport(self):
        def transport(*_):
            self.now += 5
            return self.payload

        self.feed.transport = transport
        result = self.feed.poll()
        self.assertEqual(result["received_at"], self.now)
        self.assertEqual(result["observed_at"], self.now)

    def test_transport_exception_does_not_leak_secret(self):
        def unsafe(*args):
            raise RuntimeError("test-secret-not-real")

        feed = JupiterPriceFeed(transport=unsafe)
        with self.assertRaises(FeedUnavailable) as caught:
            feed.poll()
        self.assertEqual(str(caught.exception), "provider_unavailable")
        self.assertIsNone(caught.exception.__cause__)

    def test_redirect_is_never_followed(self):
        self.assertIsNone(
            _NoRedirect().redirect_request(
                None, None, 302, "found", {}, "https://invalid.example"
            )
        )

    def test_http_auth_error_is_sanitized(self):
        class Opener:
            def open(self, *args, **kwargs):
                raise HTTPError("https://secret.example", 401, "secret", {}, None)

        with (
            patch("oracle.feeds.build_opener", return_value=Opener()),
            self.assertRaisesRegex(FeedUnavailable, "^provider_auth_failed$"),
        ):
            _get_json(JUPITER_PRICE_URL, {"x-api-key": "test-secret"}, 1, 100)

    def test_response_size_is_bounded(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, n):
                return b"x" * n

        class Opener:
            def open(self, *args, **kwargs):
                return Response()

        with (
            patch("oracle.feeds.build_opener", return_value=Opener()),
            self.assertRaisesRegex(FeedUnavailable, "^provider_response_too_large$"),
        ):
            _get_json(JUPITER_PRICE_URL, {}, 1, 100)


if __name__ == "__main__":
    unittest.main()

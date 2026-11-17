"""Actual loopback HTTP tests; no public network or venue actions."""

from __future__ import annotations

import json
import threading
import time
import unittest
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from oracle_leverage.market import LiveMarket, MarketError, parse_minutes

NOW = 1_800_000_000


def iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat().replace("+00:00", "Z")


class Server:
    def __init__(self):
        self.calls = []
        self.payload = {"bid": "100", "ask": "102", "time": iso(NOW - 1)}
        self.raw = None
        self.status = 200
        self.delay = 0
        self.candles = True
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                fixture.calls.append(self.path)
                if fixture.delay:
                    time.sleep(fixture.delay)
                parsed = urlsplit(self.path)
                if fixture.status == 302:
                    self.send_response(302)
                    self.send_header("Location", fixture.base + "/redirect-target")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if fixture.candles and parsed.path.endswith("/candles"):
                    query = parse_qs(parsed.query)
                    left, right = [
                        int(datetime.fromisoformat(query[key][0]).timestamp())
                        for key in ("start", "end")
                    ]
                    payload = [
                        [t, 99, 102, 100, 101, 2] for t in range(left, right + 60, 60)
                    ]
                else:
                    payload = fixture.payload
                body = (
                    fixture.raw
                    if fixture.raw is not None
                    else json.dumps(payload).encode()
                )
                self.send_response(fixture.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(
            target=lambda: self.server.serve_forever(poll_interval=0.02), daemon=True
        )
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(1)


class MarketTests(unittest.TestCase):
    def setUp(self):
        self.server = Server()
        self.addCleanup(self.server.close)
        self.now = [float(NOW)]

    def client(self, **kwargs):
        return LiveMarket(
            base_url=self.server.base, clock=lambda: self.now[0], **kwargs
        )

    def test_ticker_uses_fresh_bid_ask_midpoint_and_real_source_identity(self):
        quote = self.client().quote("ZEC")
        self.assertEqual(quote["price"], 101)
        self.assertEqual(quote["asset"], "ZEC")
        self.assertEqual(quote["product"], "ZEC-USD")
        self.assertEqual(quote["quote_currency"], "USD")
        self.assertEqual(quote["event_at"], NOW - 1)
        self.assertEqual(
            quote["source_url"], self.server.base + "/products/ZEC-USD/ticker"
        )
        self.assertIn("fixture", quote["venue"])

    def test_bootstrap_paginates_and_subsequent_fetch_is_incremental(self):
        client = self.client()
        rows = client.history("BTC", 20)
        self.assertGreaterEqual(len(rows), 52 * 20)
        calls = len(self.server.calls)
        self.assertEqual(calls, 4)
        for call in self.server.calls:
            query = parse_qs(urlsplit(call).query)
            left, right = [
                datetime.fromisoformat(query[key][0]).timestamp()
                for key in ("start", "end")
            ]
            self.assertLessEqual((right - left) / 60, 299)
        client.history("BTC", 20)
        self.assertEqual(len(self.server.calls), calls)
        self.now[0] += 61
        client.history("BTC", 20)
        self.assertEqual(len(self.server.calls), calls + 1)
        self.assertEqual(client.cache_status("BTC")["last_minute"], NOW)

    def test_future_stale_missing_time_and_crossed_tickers_are_refused(self):
        for patch in (
            {"time": iso(NOW + 1)},
            {"time": iso(NOW - 16)},
            {"time": None},
            {"time": "2026-01-01T00:00:00"},
            {"bid": "103", "ask": "102"},
            {"bid": "NaN"},
            {"bid": True},
        ):
            self.server.payload = {
                "bid": "100",
                "ask": "102",
                "time": iso(NOW - 1),
                **patch,
            }
            with self.subTest(patch=patch), self.assertRaises(MarketError):
                self.client().quote("BTC")

    def test_redirect_never_follows_to_another_request(self):
        self.server.status = 302
        with self.assertRaisesRegex(MarketError, "redirect_refused"):
            self.client().quote("BTC")
        self.assertEqual(len(self.server.calls), 1)

    def test_http_non_json_duplicate_keys_and_size_limit(self):
        for status, body in (
            (503, b"temporarily unavailable"),
            (200, b"not-json"),
            (200, b'{"bid":"1","bid":"2"}'),
            (200, b"x" * 1000),
        ):
            self.server.status, self.server.raw = status, body
            with (
                self.subTest(status=status, body=body[:20]),
                self.assertRaises(MarketError),
            ):
                self.client(max_bytes=128).quote("BTC")

    def test_socket_timeout_is_bounded(self):
        self.server.delay = 0.3
        started = time.monotonic()
        with self.assertRaises(MarketError):
            self.client(timeout=0.05).quote("BTC")
        self.assertLess(time.monotonic() - started, 0.5)

    def test_cancelled_bootstrap_sends_no_http(self):
        with self.assertRaisesRegex(MarketError, "cancelled"):
            self.client().history("BTC", 20, cancelled=lambda: True)
        self.assertEqual(self.server.calls, [])

    def test_cache_survives_provider_failure_and_respects_backoff(self):
        client = self.client()
        before = client.history("ZEC", 5)
        self.now[0] += 60
        self.server.status = 503
        cached = client.history("ZEC", 5)
        self.assertEqual(cached, before)
        calls = len(self.server.calls)
        self.assertEqual(
            client.cache_status("ZEC")["candle_error"], "market_http_error"
        )
        self.now[0] += 5
        client.history("ZEC", 5)
        self.assertEqual(len(self.server.calls), calls)

    def test_minute_parser_refuses_conflicts_and_preserves_explicit_zero_volume(self):
        row = [NOW - 60, 99, 102, 100, 101, 0]
        parsed = parse_minutes([row], NOW - 60, NOW)
        self.assertEqual(parsed[NOW - 60], [NOW - 60, 100, 102, 99, 101, 0])
        for bad in (
            [row, [NOW - 60, 99, 102, 100, 100.5, 0]],
            [[NOW - 59, 99, 102, 100, 101, 1]],
            [[NOW - 60, 103, 102, 100, 101, 1]],
            [row] * 301,
        ):
            with self.subTest(bad=bad[:2]), self.assertRaises(MarketError):
                parse_minutes(bad, NOW - 60, NOW)

    def test_only_fixed_provider_or_explicit_loopback_fixture_is_allowed(self):
        for url in (
            "http://example.com",
            "https://user:secret@api.exchange.coinbase.com",
            "https://api.exchange.coinbase.com?key=fake",
            "file:///tmp/input",
        ):
            with self.subTest(url=url), self.assertRaises(MarketError):
                LiveMarket(base_url=url)
        with self.assertRaises(MarketError):
            self.client().quote("ETH")


if __name__ == "__main__":
    unittest.main()

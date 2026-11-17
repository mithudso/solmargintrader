"""Real public wire samples and loopback streams; never a wallet or trading venue."""

from __future__ import annotations

import copy
import gzip
import json
import socket
import struct
import tempfile
import threading
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from oracle_leverage import quotes
from soltui.pricefeed import WebSocket, accept_key, parse_frame

NOW = 1794812037.1
# Captured from the public endpoint on 2026-11-16; timestamps are microseconds.
JUPITER_FRAME = '{"type":"streamUpdated","subscriptionId":1,"parsed":{"timestampUs":"1794812037000000","priceFeeds":[{"priceFeedId":1,"price":"6462451871808","exponent":-8,"feedUpdateTimestamp":1794812037000000},{"priceFeedId":66,"price":"88985037336","exponent":-8,"feedUpdateTimestamp":1794812037000000}]}}'


def iso(stamp):
    return datetime.fromtimestamp(stamp, UTC).isoformat()


def book(product="BTC-USD", stamp=NOW):
    return {
        "type": "snapshot",
        "product_id": product,
        "time": iso(stamp),
        "bids": [["100", "2"], ["99", "3"]],
        "asks": [["102", "4"], ["103", "5"]],
    }


class Decoders(unittest.TestCase):
    def test_actual_jupiter_frame_uses_microseconds_and_the_two_exact_feed_ids(self):
        values = quotes.decode_jupiter(quotes.decode_json(JUPITER_FRAME), NOW)
        self.assertEqual([v["asset"] for v in values], ["BTC", "ZEC"])
        self.assertAlmostEqual(values[0]["price"], 64624.51871808)
        self.assertAlmostEqual(values[1]["price"], 889.85037336)
        self.assertEqual(values[0]["exchange_at"], 1794812037)
        self.assertEqual(values[0]["endpoint"], quotes.JUPITER_URL)

    def test_wrong_feed_future_stale_nonfinite_and_untrusted_json_are_rejected(self):
        base = json.loads(JUPITER_FRAME)
        for key, value in (
            ("priceFeedId", 2),
            ("price", "NaN"),
            ("price", "9007199254740992"),
            ("exponent", -13),
            ("exponent", True),
            ("feedUpdateTimestamp", int((NOW + 2) * 1e6)),
            ("feedUpdateTimestamp", int((NOW - 2) * 1e6)),
            ("feedUpdateTimestamp", "1794812037000000"),
        ):
            message = copy.deepcopy(base)
            message["parsed"]["priceFeeds"][0][key] = value
            with (
                self.subTest(key=key, value=value),
                self.assertRaises(quotes.QuoteError),
            ):
                quotes.decode_jupiter(message, NOW)
        for raw in (
            '{"x":NaN}',
            '{"x":1,"x":2}',
            "[]",
            "{} trailing",
            "x" * (quotes.MAX_JSON_BYTES + 1),
        ):
            with self.subTest(raw=raw[:20]), self.assertRaises(quotes.QuoteError):
                quotes.decode_json(raw)

    def test_synced_book_midpoint_changes_without_any_trade_and_rejects_ticker(self):
        state = quotes.CoinbaseBooks()
        first = state.apply(book(), NOW)[0]
        self.assertEqual(first["price"], 101)
        changed = state.apply(
            {
                "type": "l2update",
                "product_id": "BTC-USD",
                "time": iso(NOW + 0.1),
                "changes": [["buy", "100", "0"], ["sell", "102", "0"]],
            },
            NOW + 0.1,
        )[0]
        self.assertEqual(
            (changed["bid"], changed["ask"], changed["price"]), (99, 103, 101)
        )
        self.assertEqual(
            state.apply(
                {
                    "type": "ticker",
                    "product_id": "BTC-USD",
                    "price": "999",
                    "best_bid": "998",
                    "best_ask": "1000",
                },
                NOW + 0.2,
            ),
            [],
        )
        self.assertEqual(
            state.apply(
                {
                    "type": "l2update",
                    "product_id": "BTC-USD",
                    "time": iso(NOW - 0.1),
                    "changes": [["buy", "999", "1"]],
                },
                NOW + 0.2,
            ),
            [],
        )
        heartbeat = state.apply(
            {"type": "heartbeat", "product_id": "BTC-USD", "time": iso(NOW + 0.2)},
            NOW + 0.2,
        )[0]
        self.assertEqual(heartbeat["price"], 101)
        self.assertAlmostEqual(heartbeat["book_exchange_at"], NOW + 0.1, places=5)
        self.assertAlmostEqual(heartbeat["exchange_at"], NOW + 0.2, places=5)
        self.assertEqual(
            quotes.CoinbaseBooks().apply(
                {"type": "heartbeat", "product_id": "BTC-USD", "time": iso(NOW)}, NOW
            ),
            [],
        )

    def test_invalid_crossed_or_future_book_never_becomes_a_quote(self):
        invalid = []
        for field, value in (
            ("bids", [["104", "1"]]),
            ("asks", []),
            ("bids", [["NaN", "1"]]),
            ("asks", [["102", "-1"]]),
            ("time", iso(NOW + 5)),
            ("time", "2026-11-16T00:00:00"),
            ("product_id", "SOL-USD"),
        ):
            invalid.append({**book(), field: value})
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(quotes.QuoteError):
                quotes.CoinbaseBooks().apply(value, NOW)


class Durability(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.home = Path(self.directory.name) / "home"
        self.now = NOW
        self.worker = quotes.DualQuotes(self.home, clock=lambda: self.now)
        self.worker.acquire()
        self.addCleanup(self.worker.close)

    def tick(self):
        return quotes.decode_jupiter(json.loads(JUPITER_FRAME), NOW)[0]

    def test_duplicates_out_of_order_reconnect_and_restart_do_not_refresh_a_tick(self):
        worker = self.worker
        worker.apply(("connected", "jupiter", None))
        self.assertTrue(worker.apply(("tick", "jupiter", self.tick())))
        self.assertFalse(
            worker.apply(("tick", "jupiter", {**self.tick(), "received_at": NOW + 0.5}))
        )
        self.assertFalse(
            worker.apply(("tick", "jupiter", {**self.tick(), "exchange_at": NOW - 1}))
        )
        worker.apply(("connected", "jupiter", None))
        self.assertFalse(worker.apply(("tick", "jupiter", self.tick())))
        self.assertEqual(worker.feeds["jupiter"], {})
        newer = {**self.tick(), "exchange_at": NOW + 0.2, "received_at": NOW + 0.2}
        worker.apply(("tick", "jupiter", newer))
        worker.close()
        restarted = quotes.DualQuotes(self.home, clock=lambda: NOW + 0.3)
        restarted.acquire()
        self.addCleanup(restarted.close)
        restarted.apply(("connected", "jupiter", None))
        self.assertFalse(restarted.apply(("tick", "jupiter", newer)))
        rows = [
            json.loads(row)
            for path in (self.home / "dual-quotes").glob("*.gz")
            for row in gzip.decompress(path.read_bytes()).splitlines()
        ]
        self.assertEqual(len(rows), 2)

    def test_exact_freshness_limits_and_disconnect_do_not_silently_fall_back(self):
        self.worker.apply(("connected", "jupiter", None))
        self.worker.apply(("tick", "jupiter", self.tick()))
        self.now = 1794812037.9
        self.assertTrue(self.worker.snapshot()["feeds"]["jupiter"]["BTC"]["fresh"])
        self.now = 1794812038.01
        self.assertFalse(self.worker.snapshot()["feeds"]["jupiter"]["BTC"]["fresh"])
        self.worker.apply(("error", "jupiter", "quote_connection_failed"))
        self.now = NOW
        snap = self.worker.snapshot()
        self.assertFalse(snap["feeds"]["jupiter"]["BTC"]["fresh"])
        self.assertEqual(snap["feeds"]["coinbase"], {})

    def test_same_exchange_timestamp_price_correction_is_retained_with_receipt_time(
        self,
    ):
        self.worker.apply(("connected", "jupiter", None))
        self.worker.apply(("tick", "jupiter", self.tick()))
        correction = {
            **self.tick(),
            "price": self.tick()["price"] + 0.01,
            "raw_price": "6462452871808",
            "received_at": NOW + 0.1,
        }
        self.assertTrue(self.worker.apply(("tick", "jupiter", correction)))
        self.assertFalse(
            self.worker.apply(
                ("tick", "jupiter", {**correction, "received_at": NOW + 0.2})
            )
        )
        self.assertEqual(self.worker.feeds["jupiter"]["BTC"]["received_at"], NOW + 0.1)
        self.worker.log.flush()
        rows = [
            json.loads(row)
            for path in self.worker.log.root.glob("*.gz")
            for row in gzip.decompress(path.read_bytes()).splitlines()
        ]
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["exchange_at"], rows[1]["exchange_at"])
        self.assertNotEqual(rows[0]["price"], rows[1]["price"])

    def test_single_home_lock_released_only_after_shutdown(self):
        other = quotes.DualQuotes(self.home)
        with self.assertRaisesRegex(quotes.QuoteError, "already_running"):
            other.acquire()
        self.worker.close()
        other.acquire()
        other.close()

    def test_hourly_private_logs_retain_only_owned_files_after_seven_days(self):
        logger = self.worker.log
        logger.append("jupiter", self.tick())
        logger.append("jupiter", {**self.tick(), "received_at": NOW + 3600})
        logger.flush()
        paths = list(logger.root.glob("*.gz"))
        self.assertEqual(len(paths), 2)
        self.assertTrue(all(path.stat().st_mode & 0o077 == 0 for path in paths))
        unrelated = logger.root / "other-recorder.jsonl.gz"
        unrelated.write_bytes(b"keep")
        logger.retain(NOW + 9 * 86400)
        self.assertEqual(list(logger.root.glob("dual-quotes-*.gz")), [])
        self.assertTrue(unrelated.exists())


class Loopback(unittest.TestCase):
    def test_two_real_websockets_subscribe_decode_log_and_stop_without_orphans(self):
        with tempfile.TemporaryDirectory() as directory:
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            listener.listen(2)
            listener.settimeout(3)
            self.addCleanup(listener.close)
            subscribed, failures, peers = [], [], []
            stop_server = threading.Event()

            def frame(message):
                body = json.dumps(message).encode()
                return (
                    bytes([0x81, len(body)])
                    if len(body) < 126
                    else bytes([0x81, 126]) + struct.pack("!H", len(body))
                ) + body

            def serve_peer(peer):
                try:
                    with peer:
                        peer.settimeout(2)
                        header = bytearray()
                        while b"\r\n\r\n" not in header:
                            header.extend(peer.recv(4096))
                        key = (
                            bytes(header)
                            .split(b"Sec-WebSocket-Key: ")[1]
                            .split(b"\r\n")[0]
                            .decode()
                        )
                        peer.sendall(
                            (
                                "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: "
                                + accept_key(key)
                                + "\r\n\r\n"
                            ).encode()
                        )
                        buf = bytearray()
                        while parse_frame(buf) is None:
                            buf.extend(peer.recv(4096))
                        subscription = json.loads(parse_frame(buf)[2])
                        subscribed.append(subscription)
                        messages = (
                            [json.loads(JUPITER_FRAME)]
                            if "subscriptionId" in subscription
                            else [book(), book("ZEC-USD")]
                        )
                        data = b"".join(frame(value) for value in messages)
                        peer.sendall(data[:10])
                        time.sleep(0.03)
                        peer.sendall(data[10:])
                        while not stop_server.is_set():
                            if not peer.recv(4096):
                                break
                except (OSError, ValueError) as error:
                    if not stop_server.is_set():
                        failures.append(type(error).__name__)

            def serve():
                for _ in range(2):
                    peer = listener.accept()[0]
                    thread = threading.Thread(
                        target=serve_peer, args=(peer,), daemon=True
                    )
                    peers.append(thread)
                    thread.start()

            server = threading.Thread(target=serve, daemon=True)
            server.start()
            url = f"ws://127.0.0.1:{listener.getsockname()[1]}"
            worker = quotes.DualQuotes(
                Path(directory) / "home",
                clock=lambda: NOW,
                ws_factory=lambda *a, **kw: WebSocket(url, timeout=1),
            )
            runner = threading.Thread(target=worker.run, daemon=True)
            runner.start()
            try:
                deadline = time.monotonic() + 5
                while worker.store.meta("dual_quotes", {}).get("status") != "streaming":
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.02)
                self.assertCountEqual(
                    subscribed,
                    [quotes.JUPITER_SUBSCRIPTION, quotes.COINBASE_SUBSCRIPTION],
                )
            finally:
                stop_server.set()
                worker.stop_event.set()
                runner.join(3)
                server.join(2)
                for thread in peers:
                    thread.join(2)
            self.assertFalse(runner.is_alive())
            self.assertTrue(
                all(not thread.is_alive() for thread in worker._threads + peers)
            )
            self.assertFalse(failures)
            final = worker.store.meta("dual_quotes")
            self.assertEqual(final["status"], "stopped")
            self.assertFalse(final["feeds"]["jupiter"]["BTC"]["fresh"])
            records = [
                json.loads(row)
                for path in (worker.store.home / "dual-quotes").glob("*.gz")
                for row in gzip.decompress(path.read_bytes()).splitlines()
            ]
            self.assertEqual(
                {(r["venue"], r["asset"]) for r in records},
                {
                    ("jupiter", "BTC"),
                    ("jupiter", "ZEC"),
                    ("coinbase", "BTC"),
                    ("coinbase", "ZEC"),
                },
            )


if __name__ == "__main__":
    unittest.main()

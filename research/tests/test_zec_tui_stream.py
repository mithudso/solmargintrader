"""Actual trade folding, bounded session ownership and loopback RFC6455 tests."""

from __future__ import annotations

import json
import queue
import socket
import struct
import threading
import time
import unittest
from datetime import UTC, datetime

from oracle.feeds import FeedUnavailable
from research.tests.test_zec_tui_model import original
from research.zec_tui_source import DataSession
from research.zec_tui_stream import (
    PRODUCT,
    SUBSCRIPTION,
    DisabledStream,
    TradeAccumulator,
    TradeStream,
)
from soltui.pricefeed import PriceFeedError, WebSocket, accept_key, parse_frame


def event(identity=1, price=100, size=2, stamp=121, kind="match"):
    return {
        "type": kind,
        "product_id": PRODUCT,
        "trade_id": identity,
        "price": str(price),
        "size": str(size),
        "time": datetime.fromtimestamp(stamp, UTC).isoformat(),
    }


class Accumulator(unittest.TestCase):
    def test_real_trade_ohlcv_dedup_and_initial_snapshot_is_not_a_new_trade(self):
        state = TradeAccumulator()
        state.connect(120.5)
        state.apply(event(50, 99, 9, 120, "last_match"), 120.6)
        self.assertIsNone(state.snapshot("1m", 120.6)["bar"])
        state.apply(event(51, 100, 2, 121), 121.1)
        state.apply(event(52, 103, 3, 122), 122.1)
        state.apply(event(52, 103, 3, 122), 122.2)
        state.apply(event(53, 98, 4, 123), 123.1)
        snapshot = state.snapshot("1m", 123.2)
        self.assertEqual(
            snapshot["bar"],
            {"ts": 120, "open": 100, "high": 103, "low": 98, "close": 98, "volume": 9},
        )
        self.assertEqual(snapshot["received_trades"], 3)
        self.assertTrue(snapshot["partial"])
        self.assertFalse(snapshot["gap"])

    def test_id_gap_marks_current_bucket_and_clean_next_boundary_recovers(self):
        state = TradeAccumulator()
        state.connect(120.5)
        state.apply(event(1, stamp=121), 121.1)
        state.apply(event(3, stamp=122), 122.1)
        self.assertTrue(state.snapshot("1m", 123)["gap"])
        state.apply(event(4, stamp=180.2), 180.3)
        current = state.snapshot("1m", 180.4)
        self.assertFalse(current["gap"])
        self.assertFalse(current["partial"])
        self.assertEqual(current["bar"]["ts"], 180)
        # The hour containing that same missing trade remains partial.
        self.assertTrue(state.snapshot("1h", 180.4)["gap"])

    def test_heartbeat_reveals_missing_trade_without_manufacturing_volume(self):
        state = TradeAccumulator()
        state.connect(120.5)
        state.apply(event(1, stamp=121), 121.1)
        heartbeat = event(stamp=122, kind="heartbeat")
        heartbeat["last_trade_id"] = 3
        state.apply(heartbeat, 122.1)
        snapshot = state.snapshot("1m", 123)
        self.assertTrue(snapshot["gap"])
        self.assertEqual(snapshot["bar"]["volume"], 2)

    def test_stale_disconnect_reconnect_and_wrong_bucket_are_explicit(self):
        state = TradeAccumulator()
        state.connect(120.5)
        state.apply(event(stamp=121), 121.1)
        self.assertFalse(state.snapshot("1m", 140)["connected"])
        self.assertEqual(state.snapshot("1m", 140)["reason"], "stream_stale")
        state.disconnect()
        self.assertFalse(state.snapshot("1m", 122)["connected"])
        state.connect(180.5)
        self.assertIsNone(state.snapshot("1m", 181)["bar"])
        state.apply(event(10, stamp=181), 181.1)
        self.assertTrue(state.snapshot("1m", 181.2)["partial"])
        self.assertEqual(state.snapshot("1m", 241)["reason"], "stream_stale")

    def test_foreign_nonfinite_invalid_and_future_events_do_not_create_a_bar(self):
        variants = [
            {"product_id": "BTC-USD"},
            {"price": "nan"},
            {"price": "inf"},
            {"size": "-2"},
            {"trade_id": True},
            {"time": "2026-11-14T00:00:00"},
            {"time": datetime.fromtimestamp(200, UTC).isoformat()},
        ]
        for patch in variants:
            with self.subTest(patch=patch):
                state = TradeAccumulator()
                state.connect(120.5)
                with self.assertRaises((TypeError, ValueError)):
                    state.apply({**event(), **patch}, 121.1)
                self.assertIsNone(state.snapshot("1m", 122)["bar"])

    def test_out_of_order_time_advances_no_candle_and_marks_gap(self):
        state = TradeAccumulator()
        state.connect(120.5)
        state.apply(event(1, stamp=123), 123.1)
        state.apply(event(2, price=999, size=99, stamp=122), 124)
        snapshot = state.snapshot("1m", 124.1)
        self.assertEqual(snapshot["bar"]["close"], 100)
        self.assertEqual(snapshot["bar"]["volume"], 2)
        self.assertTrue(snapshot["gap"])


class SourceRefresh(unittest.TestCase):
    class Client:
        def __init__(self):
            self.calls = 0
            self.fail = False

        def fetch(self, step, start, end):
            self.calls += 1
            if self.fail:
                raise FeedUnavailable("candle_rate_limited")
            return {
                t: {
                    "ts": t,
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "volume": 3,
                }
                for t in range(start, end, step)
            }

    def test_force_refetches_actual_overlap_without_reseeding_completed_history(self):
        client = self.Client()
        session = DataSession(client, clock=lambda: 100_005)
        request = {"interval": "1m", "rows": [original()], "lookback": 48}
        first = session(request, lambda: False)
        calls = client.calls
        cached = session(request, lambda: False)
        self.assertEqual(client.calls, calls)
        refreshed = session({**request, "force": True}, lambda: False)
        self.assertEqual(client.calls, calls + 1)
        self.assertEqual(first["market_token"], cached["market_token"])
        self.assertEqual(first["market_token"], refreshed["market_token"])
        self.assertEqual(
            first["rows"][0]["input_start_at"], refreshed["rows"][0]["input_start_at"]
        )
        self.assertTrue(all(t < refreshed["end"] for t in refreshed["market_rows"]))

    def test_force_preserves_provider_failure_backoff_and_recovers_after_deadline(self):
        now = [100_005.0]
        client = self.Client()
        session = DataSession(client, clock=lambda: now[0])
        request = {"interval": "1m", "rows": [original()], "lookback": 48}
        session(request, lambda: False)
        client.fail = True
        failed = session({**request, "force": True}, lambda: False)
        calls = client.calls
        self.assertEqual(failed["error"], "candle_rate_limited")
        for _ in range(5):
            self.assertEqual(
                session({**request, "force": True}, lambda: False)["error"],
                "candle_rate_limited",
            )
        self.assertEqual(client.calls, calls)
        client.fail = False
        now[0] += 15
        recovered = session({**request, "force": True}, lambda: False)
        self.assertIsNone(recovered["error"])
        self.assertEqual(client.calls, calls + 1)


class FakeConnection:
    def __init__(self, script):
        self.script = queue.Queue()
        for item in script:
            self.script.put(item)
        self.closed = threading.Event()
        self.sent = []

    def open(self):
        pass

    def settimeout(self, value):
        self.timeout = value

    def send_text(self, value):
        self.sent.append(json.loads(value))

    def recv_text(self):
        if self.closed.is_set():
            raise PriceFeedError("closed")
        try:
            item = self.script.get(timeout=0.03)
        except queue.Empty:
            raise TimeoutError from None
        if isinstance(item, BaseException):
            raise item
        return json.dumps(item)

    def close(self):
        self.closed.set()


class StreamLifecycle(unittest.TestCase):
    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while not predicate():
            self.assertLess(time.monotonic(), deadline)
            threading.Event().wait(0.005)

    def test_reconnect_clears_prior_bar_and_close_reaps_owned_thread(self):
        first = FakeConnection(
            [event(10, kind="last_match"), event(11), PriceFeedError("lost")]
        )
        second = FakeConnection([event(20, kind="last_match"), event(21, price=200)])
        connections = iter([first, second])
        stream = TradeStream(
            clock=lambda: 121.5,
            ws_factory=lambda *a, **k: next(connections),
            retry_seconds=0.01,
        )
        self.addCleanup(stream.close, 1)
        stream.start()
        self.wait_for(lambda: stream.snapshot("1m")["received_trades"] == 2)
        snapshot = stream.snapshot("1m")
        self.assertEqual(snapshot["bar"]["close"], 200)
        self.assertEqual(snapshot["bar"]["volume"], 2)
        self.assertTrue(snapshot["partial"])
        self.assertFalse(snapshot["gap"])
        self.assertEqual(first.sent, [SUBSCRIPTION])
        self.assertEqual(second.sent, [SUBSCRIPTION])
        stream.close(1)
        self.assertFalse(stream.alive)
        self.assertTrue(first.closed.is_set() and second.closed.is_set())
        stream.close(1)

    def test_disabled_stream_never_starts_a_thread_or_socket(self):
        stream = DisabledStream()
        stream.start()
        stream.refresh()
        self.assertFalse(stream.alive)
        self.assertIsNone(stream.snapshot("1m")["bar"])
        stream.close()

    def test_real_local_websocket_handshake_subscription_frames_and_owner_stop(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(3)
        self.addCleanup(listener.close)
        subscribed, server_done = [], threading.Event()
        failure = []

        def server_frame(payload):
            body = json.dumps(payload).encode()
            header = (
                bytes([0x81, len(body)])
                if len(body) < 126
                else bytes([0x81, 126]) + struct.pack("!H", len(body))
            )
            return header + body

        def serve():
            try:
                with listener.accept()[0] as peer:
                    peer.settimeout(2)
                    raw = bytearray()
                    while b"\r\n\r\n" not in raw:
                        raw.extend(peer.recv(4096))
                    key = (
                        bytes(raw)
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
                    raw.clear()
                    while parse_frame(raw) is None:
                        raw.extend(peer.recv(4096))
                    _, _, payload, _ = parse_frame(raw)
                    subscribed.append(json.loads(payload))
                    peer.sendall(
                        server_frame(event(10, kind="last_match"))
                        + server_frame(event(11))
                        + server_frame(event(12, price=101, size=3))
                    )
                    while peer.recv(4096):
                        pass
            except (OSError, ValueError, IndexError, PriceFeedError) as exc:
                failure.append(exc)
            finally:
                server_done.set()

        server = threading.Thread(target=serve, daemon=True)
        server.start()
        url = f"ws://127.0.0.1:{listener.getsockname()[1]}"
        stream = TradeStream(
            clock=lambda: 121.5, ws_factory=lambda *a, **k: WebSocket(url, timeout=1)
        )
        self.addCleanup(stream.close, 1)
        stream.start()
        self.wait_for(lambda: stream.snapshot("1m")["received_trades"] == 2)
        self.assertEqual(subscribed, [SUBSCRIPTION])
        self.assertEqual(stream.snapshot("1m")["bar"]["volume"], 5)
        stream.refresh()
        self.assertEqual(stream.snapshot("1m")["bar"]["volume"], 5)
        stream.close(1)
        self.assertFalse(stream.alive)
        self.assertTrue(server_done.wait(2))
        server.join(1)
        self.assertFalse(server.is_alive())
        self.assertFalse(failure)


if __name__ == "__main__":
    unittest.main()

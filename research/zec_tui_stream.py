"""Session-owned public trade stream for provisional indicator readings.

This is an in-memory subscriber, never a recorder or a trading connection. A
first candle starts at the first trade actually observed; it cannot claim the
unobserved open, high, low or volume from before attachment or a reconnect.
"""

from __future__ import annotations

import copy
import json
import math
import threading
import time
from datetime import datetime

from research import zec_live as live
from soltui.pricefeed import PriceFeedError, WebSocket

WS_URL = "wss://ws-feed.exchange.coinbase.com"
PRODUCT = "ZEC-USD"
SUBSCRIPTION = {
    "type": "subscribe",
    "product_ids": [PRODUCT],
    "channels": ["matches", "heartbeat"],
}
STALE_SECONDS = 15.0


def _positive(value):
    if isinstance(value, bool):
        raise TypeError("invalid_trade_number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError("invalid_trade_number")
    return number


def _trade_id(value):
    if type(value) is not int or value < 0:
        raise ValueError("invalid_trade_id")
    return value


def _timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("invalid_trade_time")
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError("invalid_trade_time")
    result = stamp.timestamp()
    if not math.isfinite(result) or result <= 0:
        raise ValueError("invalid_trade_time")
    return result


class TradeAccumulator:
    """Fold ordered actual matches; keep at most one candle per timeframe."""

    def __init__(self):
        self.connected = False
        self.started_at = None
        self.last_received = None
        self.observed_at = None
        self.event_at = None
        self.last_trade_id = None
        self.gap_at = None
        self.bars = {}
        self.reason = "stream_connecting"
        self.version = 0
        self.received_trades = 0

    def connect(self, now):
        self.connected = True
        self.started_at = self.last_received = now
        self.observed_at = self.event_at = self.last_trade_id = None
        self.gap_at = None
        self.bars.clear()
        self.reason = "waiting_for_trade"
        self.version += 1

    def disconnect(self, reason="stream_disconnected"):
        self.connected = False
        self.reason = reason
        self.version += 1

    def _gap(self, received):
        self.gap_at = received
        self.reason = "trade_gap_candidate"
        self.version += 1

    def apply(self, message, received):
        if not isinstance(message, dict):
            raise TypeError("invalid_stream_message")
        kind = message.get("type")
        if kind in {"subscriptions"}:
            return False
        if kind == "error":
            raise ValueError("stream_subscription_refused")
        if kind not in {"match", "last_match", "heartbeat"}:
            return False
        if message.get("product_id") != PRODUCT:
            raise ValueError("unexpected_trade_product")
        stamp = _timestamp(message.get("time"))
        if stamp > received + 5:
            raise ValueError("future_trade_time")
        if not self.connected:
            return False
        self.last_received = received
        if kind == "heartbeat":
            identity = _trade_id(message.get("last_trade_id"))
            if self.last_trade_id is not None and identity > self.last_trade_id:
                self._gap(received)
            return False
        identity = _trade_id(message.get("trade_id"))
        price, volume = _positive(message.get("price")), _positive(message.get("size"))
        # last_match is a historical subscription snapshot, not a new trade.
        if kind == "last_match":
            if self.last_trade_id is None:
                self.last_trade_id = identity
            return False
        if self.last_trade_id is not None and identity <= self.last_trade_id:
            return False
        if self.last_trade_id is not None and identity > self.last_trade_id + 1:
            self._gap(received)
        self.last_trade_id = identity
        if self.event_at is not None and stamp < self.event_at:
            self._gap(received)
            return False
        self.observed_at, self.event_at = received, stamp
        self.received_trades += 1
        for interval, step in live.STEPS.items():
            start = int(stamp // step) * step
            previous = self.bars.get(interval)
            if previous is None or previous["ts"] != start:
                self.bars[interval] = {
                    "ts": start,
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "volume": volume,
                }
            else:
                previous["high"] = max(previous["high"], price)
                previous["low"] = min(previous["low"], price)
                previous["close"] = price
                previous["volume"] += volume
        self.reason = None
        self.version += 1
        return True

    def snapshot(self, interval, now):
        step = live.STEPS[interval]
        bar = self.bars.get(interval)
        fresh = (
            self.connected
            and self.last_received is not None
            and 0 <= now - self.last_received <= STALE_SECONDS
        )
        gap = bool(bar and self.gap_at is not None and self.gap_at >= bar["ts"])
        partial = bool(
            bar and (self.started_at is None or self.started_at > bar["ts"] or gap)
        )
        reason = self.reason
        if self.connected and not fresh:
            reason = "stream_stale"
        elif bar and bar["ts"] != int(now // step) * step:
            reason = "waiting_for_current_bar_trade"
        elif gap:
            reason = "trade_gap_candidate"
        return {
            "bar": copy.deepcopy(bar),
            "observed_at": self.observed_at,
            "event_at": self.event_at,
            "connected": fresh,
            "partial": partial,
            "gap": gap,
            "started_at": self.started_at,
            "reason": reason,
            "version": self.version,
            "received_trades": self.received_trades,
        }


class DisabledStream:
    """Deterministic no-network default for injected app/test loaders."""

    alive = False

    def start(self):
        pass

    def refresh(self):
        pass

    def close(self, timeout=0.3):
        pass

    def snapshot(self, interval):
        return {
            "bar": None,
            "connected": False,
            "partial": False,
            "gap": False,
            "observed_at": None,
            "event_at": None,
            "started_at": None,
            "reason": "stream_not_attached",
            "version": 0,
        }


class TradeStream:
    """One foreground-session thread; bounded I/O, no UI callbacks or files."""

    def __init__(self, *, clock=time.time, ws_factory=WebSocket, retry_seconds=2.0):
        self.clock, self.ws_factory = clock, ws_factory
        self.retry_seconds = retry_seconds
        self._lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._state = TradeAccumulator()
        self._socket = None
        self._thread = None

    @property
    def alive(self):
        return bool(self._thread and self._thread.is_alive())

    def start(self):
        if self._thread is not None or self._stop.is_set():
            return
        self._thread = threading.Thread(
            target=self._run, name="oracle-indicator-trades", daemon=True
        )
        self._thread.start()

    def snapshot(self, interval):
        with self._lock:
            return self._state.snapshot(interval, self.clock())

    def refresh(self):
        # An explicit refresh wakes a disconnected retry. It never destroys a
        # healthy stream's current candle or fabricates a new trade observation.
        self._wake.set()

    def close(self, timeout=0.3):
        self._stop.set()
        self._wake.set()
        with self._lock:
            connection = self._socket
        if connection is not None:
            self._close_socket(connection)
        if self._thread and threading.current_thread() is not self._thread:
            self._thread.join(timeout)

    def _close_socket(self, connection):
        # recv may fail concurrently with owner shutdown. Serialize the two
        # close paths because the existing transport clears its socket field.
        with self._close_lock:
            try:
                connection.close()
            except (OSError, PriceFeedError):
                pass

    def _run(self):
        while not self._stop.is_set():
            connection = None
            try:
                connection = self.ws_factory(WS_URL, timeout=3.0)
                with self._lock:
                    self._socket = connection
                connection.open()
                connection.settimeout(0.25)
                if self._stop.is_set():
                    break
                connection.send_text(json.dumps(SUBSCRIPTION))
                with self._lock:
                    self._state.connect(self.clock())
                while not self._stop.is_set():
                    try:
                        raw = connection.recv_text()
                    except TimeoutError:
                        with self._lock:
                            activity = self._state.last_received
                        if (
                            activity is not None
                            and self.clock() - activity > STALE_SECONDS
                        ):
                            raise PriceFeedError("stream_idle")
                        continue
                    if len(raw) > 65_536:
                        raise ValueError("stream_message_too_large")
                    message = json.loads(raw)
                    with self._lock:
                        self._state.apply(message, self.clock())
            except Exception:  # noqa: BLE001 - provider payloads must never leak through the UI.
                if not self._stop.is_set():
                    with self._lock:
                        self._state.disconnect("stream_disconnected")
            finally:
                if connection is not None:
                    self._close_socket(connection)
                with self._lock:
                    self._socket = None
                    if self._stop.is_set():
                        self._state.disconnect("stream_stopped")
            if self._stop.is_set():
                break
            self._wake.wait(self.retry_seconds)
            self._wake.clear()

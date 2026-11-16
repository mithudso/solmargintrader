"""Independent public Jupiter oracle and Coinbase synced-book comparison stream.

This collector never imports trading adapters. The frozen paper worker and the
shared price recorder keep their own data, locks, settings, and lifecycles.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import gzip
import json
import math
import os
import queue
import re
import signal
import threading
import time
import uuid
from datetime import UTC, datetime

from oracle_leverage.store import Store, default_home
from soltui.pricefeed import Book, PriceFeedError, WebSocket

JUPITER_URL = "wss://perps-api.jup.ag/v1/pyth/stream"
COINBASE_URL = "wss://ws-feed.exchange.coinbase.com"
JUPITER_SUBSCRIPTION = {
    "type": "subscribe",
    "subscriptionId": 1,
    "channel": "fixed_rate@200ms",
    "priceFeedIds": [1, 66],
    "properties": ["price", "exponent", "feedUpdateTimestamp"],
    "formats": [],
    "ignoreInvalidFeeds": False,
}
COINBASE_SUBSCRIPTION = {
    "type": "subscribe",
    "product_ids": ["BTC-USD", "ZEC-USD"],
    "channels": ["level2_batch", "heartbeat"],
}
URLS = {"jupiter": JUPITER_URL, "coinbase": COINBASE_URL}
MAX_AGE = {"jupiter": 1.0, "coinbase": 3.0}
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_LEVELS = 100_000
META_SECONDS = 0.25
LOG_SECONDS = 1.0


class QuoteError(RuntimeError):
    """A fixed safe code, never an untrusted provider response."""


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise QuoteError("duplicate_json_key")
        result[key] = value
    return result


def decode_json(raw):
    if not isinstance(raw, str) or len(raw) > MAX_JSON_BYTES:
        raise QuoteError("quote_message_size_limit")
    try:
        value = json.loads(
            raw,
            object_pairs_hook=_unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, TypeError, RecursionError):
        raise QuoteError("invalid_quote_json") from None
    if not isinstance(value, dict):
        raise QuoteError("invalid_quote_json")
    return value


def _number(value, *, zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise QuoteError("invalid_quote_number")
    if isinstance(value, str) and len(value) > 64:
        raise QuoteError("invalid_quote_number")
    try:
        result = float(value)
    except (ValueError, OverflowError):
        raise QuoteError("invalid_quote_number") from None
    if not math.isfinite(result) or (result < 0 if zero else result <= 0):
        raise QuoteError("invalid_quote_number")
    return result


def _time(value):
    if not isinstance(value, str) or len(value) > 64:
        raise QuoteError("invalid_exchange_timestamp")
    try:
        stamp = datetime.fromisoformat(value)
        if stamp.tzinfo is None:
            raise ValueError()
        return _number(stamp.timestamp())
    except (ValueError, OverflowError):
        raise QuoteError("invalid_exchange_timestamp") from None


def _timely(stamp, received, source):
    if not -0.25 <= received - stamp <= MAX_AGE[source]:
        raise QuoteError("future_or_stale_exchange_timestamp")


def decode_jupiter(message, received):
    if message.get("type") == "subscriptionError":
        raise QuoteError("jupiter_subscription_refused")
    if message.get("type") != "streamUpdated":
        return []
    parsed = message.get("parsed")
    if message.get("subscriptionId") != 1 or not isinstance(parsed, dict):
        raise QuoteError("unexpected_jupiter_subscription")
    feeds = parsed.get("priceFeeds")
    if not isinstance(feeds, list) or len(feeds) > 8:
        raise QuoteError("invalid_jupiter_price_feeds")
    result = []
    for feed in feeds:
        if not isinstance(feed, dict) or type(feed.get("priceFeedId")) is not int:
            raise QuoteError("invalid_jupiter_feed")
        asset = {1: "BTC", 66: "ZEC"}.get(feed["priceFeedId"])
        if asset is None:
            raise QuoteError("unexpected_jupiter_feed")
        price, exponent, stamp = (
            feed.get(key) for key in ("price", "exponent", "feedUpdateTimestamp")
        )
        if (
            not isinstance(price, str)
            or re.fullmatch(r"[0-9]{1,16}", price) is None
            or int(price) > 2**53 - 1
            or type(exponent) is not int
            or not -12 <= exponent <= 0
            or type(stamp) is not int
            or not 0 < stamp <= 2**53 - 1
        ):
            raise QuoteError("invalid_jupiter_price_or_timestamp")
        exchange = stamp / 1_000_000
        _timely(exchange, received, "jupiter")
        result.append(
            {
                "asset": asset,
                "price": _number(int(price) * 10.0**exponent),
                "exchange_at": exchange,
                "received_at": received,
                "source": "Jupiter Pyth oracle USD",
                "endpoint": JUPITER_URL,
                "feed_id": feed["priceFeedId"],
                "quote_currency": "USD",
                "kind": "oracle",
                "raw_price": price,
                "exponent": exponent,
            }
        )
    return result


class CoinbaseBooks:
    def __init__(self):
        self.books, self.times = {}, {}

    def apply(self, message, received):
        kind = message.get("type")
        if kind == "error":
            raise QuoteError("coinbase_subscription_refused")
        if kind not in ("snapshot", "l2update", "heartbeat"):
            return []  # A ticker/last trade never becomes a live book quote.
        product = message.get("product_id")
        if product not in ("BTC-USD", "ZEC-USD"):
            raise QuoteError("unexpected_coinbase_product")
        stamp = _time(message.get("time"))
        _timely(stamp, received, "coinbase")
        if stamp < self.times.get(product, 0):
            return []
        if kind == "snapshot":
            sides = []
            for name in ("bids", "asks"):
                rows = message.get(name)
                if not isinstance(rows, list) or not 0 < len(rows) <= MAX_LEVELS:
                    raise QuoteError("coinbase_book_size_limit")
                side = []
                for row in rows:
                    if not isinstance(row, list) or len(row) != 2:
                        raise QuoteError("invalid_coinbase_book_level")
                    side.append((_number(row[0]), _number(row[1])))
                sides.append(side)
            book = Book()
            book.load(*sides, stamp)
            self.books[product] = book
        elif product not in self.books:
            return []  # Await a new snapshot after every reconnect.
        elif kind == "l2update":
            rows = message.get("changes")
            if not isinstance(rows, list) or len(rows) > MAX_LEVELS:
                raise QuoteError("coinbase_changes_size_limit")
            changes = []
            for row in rows:
                if (
                    not isinstance(row, list)
                    or len(row) != 3
                    or row[0] not in ("buy", "sell")
                ):
                    raise QuoteError("invalid_coinbase_book_change")
                changes.append((row[0], _number(row[1]), _number(row[2], zero=True)))
            book = self.books[product]
            for side, price, size in changes:
                book.change(side, price, size, stamp)
            if len(book.bids) > MAX_LEVELS or len(book.asks) > MAX_LEVELS:
                raise QuoteError("coinbase_book_size_limit")
        book = self.books[product]
        top = book.top()
        if top is None:
            raise QuoteError("coinbase_book_empty_or_crossed")
        self.times[product] = stamp
        bid, ask, bid_size, ask_size = top
        return [
            {
                "asset": product[:-4],
                "price": (bid + ask) / 2,
                "bid": bid,
                "ask": ask,
                "bid_size": bid_size,
                "ask_size": ask_size,
                "exchange_at": stamp,
                "received_at": received,
                "book_exchange_at": book.updated,
                "source": "Coinbase Exchange synced level2 midpoint",
                "endpoint": COINBASE_URL,
                "product": product,
                "quote_currency": "USD",
                "kind": "synced_book_midpoint",
                "event": kind,
            }
        ]


class TickLog:
    """New private gzip members per flush; unique run files avoid damaged-tail reuse."""

    def __init__(self, home):
        self.root = home / "dual-quotes"
        self.root.mkdir(mode=0o700, exist_ok=True)
        stat = self.root.lstat()
        if self.root.is_symlink() or stat.st_uid != os.getuid() or stat.st_mode & 0o077:
            raise QuoteError("quote_log_permissions_invalid")
        self.run_id = uuid.uuid4().hex
        self.pending = []
        self.bytes = 0

    def append(self, source, tick):
        body = (
            json.dumps(
                {"venue": source, **tick}, allow_nan=False, separators=(",", ":")
            ).encode()
            + b"\n"
        )
        if self.bytes + len(body) > 1024 * 1024:
            self.flush()
        self.pending.append((tick["received_at"], body))
        self.bytes += len(body)

    def flush(self):
        groups = {}
        for stamp, body in self.pending:
            hour = datetime.fromtimestamp(stamp, UTC).strftime("%Y%m%dT%H")
            groups.setdefault(hour, bytearray()).extend(body)
        for hour, body in groups.items():
            path = self.root / f"dual-quotes-{hour}-{self.run_id}.jsonl.gz"
            fd = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(fd, "ab") as stream:
                stream.write(gzip.compress(body, compresslevel=3, mtime=0))
                stream.flush()
                os.fsync(stream.fileno())
        self.pending.clear()
        self.bytes = 0

    def retain(self, now):
        cutoff = now - 7 * 86400
        for path in self.root.iterdir():
            match = re.fullmatch(
                r"dual-quotes-([0-9]{8}T[0-9]{2})-[0-9a-f]{32}\.jsonl\.gz", path.name
            )
            if match and path.is_file() and not path.is_symlink():
                stamp = (
                    datetime.strptime(match[1], "%Y%m%dT%H")
                    .replace(tzinfo=UTC)
                    .timestamp()
                )
                if stamp + 3600 < cutoff and path.stat().st_uid == os.getuid():
                    path.unlink()


class DualQuotes:
    def __init__(self, home, *, ws_factory=WebSocket, clock=time.time, stop_event=None):
        self.store = Store(home)
        self.ws_factory, self.clock = ws_factory, clock
        self.stop_event = stop_event or threading.Event()
        self.events = queue.Queue(maxsize=4096)
        self.feeds = {source: {} for source in URLS}
        self.connected = dict.fromkeys(URLS, False)
        self.errors = dict.fromkeys(URLS, "connecting")
        self._sockets, self._threads = {}, []
        self._socket_lock, self._close_lock = threading.Lock(), threading.Lock()
        self._lock = None
        self.log = None
        self.ticks = dict.fromkeys(URLS, 0)
        self._watermarks = {source: {} for source in URLS}

    def acquire(self):
        descriptor = os.open(
            self.store.home / "dual-quotes.lock",
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
            0o600,
        )
        lock = os.fdopen(descriptor, "a+")
        try:
            stat = os.fstat(descriptor)
            if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
                raise QuoteError("quote_lock_permissions_invalid")
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise QuoteError("dual_quotes_already_running") from None
            self.log = TickLog(self.store.home)
            saved = self.store.meta("dual_quotes", {})
            if isinstance(saved, dict) and isinstance(saved.get("feeds"), dict):
                for source in URLS:
                    rows = saved["feeds"].get(source, {})
                    if isinstance(rows, dict):
                        self._watermarks[source] = rows
            self._lock = lock
        except BaseException:
            lock.close()
            raise

    def _post(self, event):
        while not self.stop_event.is_set():
            try:
                self.events.put(event, timeout=0.1)
                return
            except queue.Full:
                continue  # Bounded backpressure; accepted ticks are never sampled.

    def _close(self, connection):
        with self._close_lock:
            try:
                connection.close()
            except (OSError, PriceFeedError, AttributeError):
                pass

    def _source(self, source):
        attempt = 0
        while not self.stop_event.is_set():
            connection = None
            try:
                connection = self.ws_factory(URLS[source], timeout=3.0)
                with self._socket_lock:
                    self._sockets[source] = connection
                connection.open()
                connection.settimeout(0.25)
                if self.stop_event.is_set():
                    break
                connection.send_text(
                    json.dumps(
                        JUPITER_SUBSCRIPTION
                        if source == "jupiter"
                        else COINBASE_SUBSCRIPTION
                    )
                )
                self._post(("connected", source, None))
                books = CoinbaseBooks()
                last_activity = time.monotonic()
                while not self.stop_event.is_set():
                    try:
                        raw = connection.recv_text()
                    except TimeoutError:
                        if time.monotonic() - last_activity > 8:
                            raise QuoteError("quote_stream_idle")
                        continue
                    received = self.clock()
                    message = decode_json(raw)
                    last_activity = time.monotonic()
                    ticks = (
                        decode_jupiter(message, received)
                        if source == "jupiter"
                        else books.apply(message, received)
                    )
                    for tick in ticks:
                        self._post(("tick", source, tick))
                    if ticks:
                        attempt = 0
            except Exception as error:  # noqa: BLE001 - raw provider errors never enter metadata/logs.
                if not self.stop_event.is_set():
                    self._post(
                        (
                            "error",
                            source,
                            str(error)
                            if isinstance(error, QuoteError)
                            else "quote_connection_failed",
                        )
                    )
            finally:
                if connection is not None:
                    self._close(connection)
                with self._socket_lock:
                    self._sockets.pop(source, None)
            if self.stop_event.wait(min(10, 0.25 * 2 ** min(attempt, 6))):
                break
            attempt += 1

    def apply(self, event):
        kind, source, value = event
        if kind == "connected":
            self.connected[source], self.errors[source] = True, None
            self.feeds[source].clear()  # Reconnection requires a new source quote/book.
        elif kind == "error":
            self.connected[source], self.errors[source] = False, value
        elif kind == "tick":
            previous = self._watermarks[source].get(value["asset"])
            if previous is not None:
                if value["exchange_at"] < previous["exchange_at"]:
                    return False
                if value["exchange_at"] == previous["exchange_at"] and (
                    all(
                        value.get(key) == previous.get(key)
                        for key in (
                            "price",
                            "raw_price",
                            "exponent",
                            "bid",
                            "ask",
                            "bid_size",
                            "ask_size",
                        )
                    )
                ):
                    return False
            self.feeds[source][value["asset"]] = value
            self._watermarks[source][value["asset"]] = value
            self.ticks[source] += 1
            self.log.append(source, value)
            return True
        return False

    def snapshot(self, status=None):
        now = self.clock()
        feeds = copy.deepcopy(self.feeds)
        for source, values in feeds.items():
            for tick in values.values():
                tick["fresh"] = self.connected[source] and all(
                    0 <= now - tick[key] <= MAX_AGE[source]
                    for key in ("exchange_at", "received_at")
                )
        ready = all(
            feeds[source].get(asset, {}).get("fresh", False)
            for source in URLS
            for asset in ("BTC", "ZEC")
        )
        return {
            "at": now,
            "pid": os.getpid(),
            "status": status or ("streaming" if ready else "degraded"),
            "feeds": feeds,
            "errors": dict(self.errors),
            "connected": dict(self.connected),
            "ticks": dict(self.ticks),
            "freshness_seconds": MAX_AGE,
            "metadata_seconds": META_SECONDS,
            "log_directory": str(self.store.home / "dual-quotes"),
        }

    def close(self):
        self.stop_event.set()
        with self._socket_lock:
            connections = list(self._sockets.values())
        for connection in connections:
            self._close(connection)
        for thread in self._threads:
            thread.join(4)
            if thread.is_alive():
                raise QuoteError("quote_thread_shutdown_incomplete")
        while not self.events.empty():
            self.apply(self.events.get_nowait())
        if self.log is not None:
            self.log.flush()
        if self._lock is not None:
            self.connected = dict.fromkeys(URLS, False)
            self.store.put_meta("dual_quotes", self.snapshot("stopped"))
            self._lock.close()
            self._lock = None

    def run(self):
        self.acquire()
        next_meta = next_log = next_retain = 0.0
        try:
            for source in URLS:
                thread = threading.Thread(
                    target=self._source,
                    args=(source,),
                    name=f"oracle-quotes-{source}",
                    daemon=True,
                )
                self._threads.append(thread)
                thread.start()
            while not self.stop_event.is_set():
                try:
                    self.apply(self.events.get(timeout=0.05))
                except queue.Empty:
                    pass
                now = time.monotonic()
                if now >= next_meta:
                    self.store.put_meta("dual_quotes", self.snapshot())
                    next_meta = now + META_SECONDS
                if now >= next_log:
                    self.log.flush()
                    next_log = now + LOG_SECONDS
                if now >= next_retain:
                    self.log.retain(self.clock())
                    next_retain = now + 3600
        finally:
            self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=default_home())
    args = parser.parse_args(argv)
    worker = DualQuotes(args.home)
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, lambda *_: worker.stop_event.set())
    try:
        worker.run()
    except QuoteError as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()

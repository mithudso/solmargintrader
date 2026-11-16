"""Session-owned read-only Jupiter oracle feed, using existing parser contracts."""

from __future__ import annotations

import json
import queue
import threading
import time

from oracle_leverage.quotes import (
    COINBASE_SUBSCRIPTION,
    COINBASE_URL,
    JUPITER_SUBSCRIPTION,
    JUPITER_URL,
    CoinbaseBooks,
    QuoteError,
    decode_json,
    decode_jupiter,
)
from soltui.pricefeed import WebSocket


class ExecutionFeed:
    def __init__(self):
        self.events = queue.Queue(maxsize=4096)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.comparison_thread = threading.Thread(target=self._comparison, daemon=True)
        self.socket = None
        self.comparison_socket = None

    def start(self):
        self.thread.start()
        self.comparison_thread.start()

    def _emit(self, item):
        while not self.stop_event.is_set():
            try:
                self.events.put(item, timeout=0.1)
                return
            except queue.Full:
                continue

    def _run(self):
        ws = None
        try:
            ws = WebSocket(JUPITER_URL, timeout=3.0)
            self.socket = ws
            ws.open()
            ws.settimeout(0.25)
            ws.send_text(json.dumps(JUPITER_SUBSCRIPTION))
            self._emit(("connected", None))
            while not self.stop_event.is_set():
                try:
                    raw = ws.recv_text()
                except TimeoutError:
                    continue
                received = time.time()
                for tick in decode_jupiter(decode_json(raw), received):
                    self._emit(("tick", tick))
        except Exception:  # noqa: BLE001 - provider failures become safe fixed codes
            # Never persist provider error strings or raw messages.
            self._emit(("error", "jupiter_feed_disconnected_or_invalid"))
        finally:
            if ws is not None:
                try:
                    ws.close()
                except (OSError, QuoteError):
                    pass

    def _comparison(self):
        ws = None
        try:
            ws = WebSocket(COINBASE_URL, timeout=3.0)
            self.comparison_socket = ws
            ws.open()
            ws.settimeout(0.25)
            ws.send_text(json.dumps(COINBASE_SUBSCRIPTION))
            books = CoinbaseBooks()
            while not self.stop_event.is_set():
                try:
                    raw = ws.recv_text()
                except TimeoutError:
                    continue
                received = time.time()
                for tick in books.apply(decode_json(raw), received):
                    self._emit(("comparison", tick))
        except Exception:  # noqa: BLE001 - provider failures become safe fixed codes
            self._emit(("comparison_error", "coinbase_comparison_unavailable"))
        finally:
            if ws is not None:
                try:
                    ws.close()
                except (OSError, QuoteError):
                    pass

    def close(self):
        self.stop_event.set()
        if self.socket is not None:
            try:
                self.socket.close()
            except (OSError, QuoteError):
                pass
        if self.comparison_socket is not None:
            try:
                self.comparison_socket.close()
            except (OSError, QuoteError):
                pass
        self.thread.join(4)
        self.comparison_thread.join(4)
        if self.thread.is_alive() or self.comparison_thread.is_alive():
            raise RuntimeError("execution feed shutdown incomplete")

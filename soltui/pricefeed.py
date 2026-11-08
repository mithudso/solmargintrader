"""Streaming coin prices: the public Coinbase Exchange `ticker` channel, recorded to disk.

    python -m soltui.pricefeed record            # the recorder loop (the console starts it detached)
    python -m soltui.pricefeed status            # what is recorded, and the latest prices

Before this module the console polled prices (Coinbase REST spot, closed 5m candles) and kept
nothing between bars. The Bots tab's forward tests need a continuous record of what the market
did, and triangular arbitrage needs bid and ask, which no candle carries. The ticker channel
gives both, keyless, for every market at once.

What it does:

* **Subscribes** to `wss://ws-feed.exchange.coinbase.com` for every USD market of the cached
  coins that Coinbase lists plus every cross pair among them (`stream_products`), on two
  public channels. `level2_batch` sends a book snapshot and then batched changes every 50 ms;
  `Book` keeps each product's book, which gives the true best bid and ask with their sizes.
  `ticker` arrives on each trade and gives the last price.
  The ticker's own best bid/ask is **not** used for a book that is synced: it only changes on
  a trade, and on 2026-11-08 the SOL-BTC ticker quote was 89 minutes old while its book had
  moved (ticker bid 0.001176 vs book bid 0.0011740). Thin cross pairs trade rarely, which is
  exactly where triangular arbitrage would have to look.
* **Samples** every product once per second into one snapshot line:
  ``{"t": <epoch s>, "q": {"SOL-USD": [bid, ask, last, bid_size, ask_size, quote_time]}}``.
  `quote_time` is the snapshot time for a synced book (the book is live as of then) and the
  exchange trade time for a ticker-only quote, so a reader ages a stale touch out instead of
  trusting it. After a disconnect every book is dropped and rebuilt from a fresh snapshot.
* **Records** snapshots to `<config dir>/prices/YYYY-MM-DD.jsonl.gz` (UTC day). Each flush is
  one gzip member, so a crash loses at most the unflushed batch and the reader
  (`backtester.core.trianglesim.read_snapshot_files`) keeps every complete line before it.
* **Publishes** the newest snapshot to `<config dir>/prices/latest.json` (atomic replace),
  which is how the console shows live prices without holding the socket itself.

Exactly one recorder runs: it holds `fcntl.flock` on `<config dir>/prices/recorder.lock`.
Recording is always on, because the recording is the data the bots backtest and train on.
`ensure_recorder` (the console calls it at start and every minute) installs a LaunchAgent,
`com.mitchhudson.soltui.pricefeed` (RunAtLoad, KeepAlive), which keeps the recorder alive across
a closed console, a crash or a reboot. Where it cannot install one (a git worktree, no launchctl)
it starts a detached process instead. The agent's process waits on the lock (`--wait-lock`)
rather than exiting, so a detached recorder and the agent never record twice and never thrash.

Boundaries: public market data only. No key, no account, no order path. The WebSocket client
is a minimal RFC 6455 implementation on the standard library; soltui deliberately adds no
dependency for one text-frame subscription.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import math
import os
import socket
import ssl
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence
from urllib.parse import urlsplit

from . import config as config_mod

WS_URL = "wss://ws-feed.exchange.coinbase.com"
PRODUCTS_URL = "https://api.exchange.coinbase.com/products"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
REPO = Path(__file__).resolve().parent.parent

# Used when the products endpoint cannot be reached: the markets Coinbase listed on 2026-11-08
# for the coins this repo caches. A product that has since been delisted is refused by the
# subscription and simply never quotes.
FALLBACK_PRODUCTS = (
    "ADA-USD", "AVAX-USD", "BNB-USD", "BTC-USD", "DOGE-USD", "ETH-USD", "HYPE-USD", "LINK-USD",
    "NEAR-USD", "SOL-USD", "SUI-USD", "XLM-USD", "XRP-USD", "ZEC-USD",
    "ADA-BTC", "ADA-ETH", "AVAX-BTC", "DOGE-BTC", "ETH-BTC", "LINK-BTC", "LINK-ETH", "SOL-BTC",
    "SOL-ETH", "XLM-BTC",
)

SNAPSHOT_SECONDS = 1.0
FLUSH_SECONDS = 10.0
RECV_TIMEOUT_S = 1.0
MAX_FRAME_BYTES = 8 * 1024 * 1024


class PriceFeedError(RuntimeError):
    """A user-facing price-stream failure (bad handshake, closed socket, unreadable file)."""


class ConnectionClosed(PriceFeedError):
    """The server closed the WebSocket."""


# -- paths -------------------------------------------------------------------------------------


def prices_dir() -> Path:
    return config_mod.CONFIG_DIR / "prices"


def day_path(ts: float, root: Path | None = None) -> Path:
    day = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
    return (root or prices_dir()) / f"{day}.jsonl.gz"


def recorded_files(root: Path | None = None) -> list[Path]:
    base = root or prices_dir()
    return sorted(base.glob("????-??-??.jsonl.gz")) if base.exists() else []


# -- RFC 6455 framing (pure, so it is testable without a socket) --------------------------------

OP_CONT, OP_TEXT, OP_BINARY, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA


def accept_key(key: str) -> str:
    """The Sec-WebSocket-Accept value a server must return for this client key."""
    return base64.b64encode(hashlib.sha1((key + WS_GUID).encode()).digest()).decode()  # noqa: S324


def encode_frame(opcode: int, payload: bytes, mask: bytes | None = None, fin: bool = True) -> bytes:
    """One client frame. Clients MUST mask (RFC 6455 5.3), so a mask is generated when absent."""
    mask = os.urandom(4) if mask is None else mask
    if len(mask) != 4:
        raise ValueError("a mask is four bytes")
    head = bytes([(0x80 if fin else 0) | opcode])
    n = len(payload)
    if n < 126:
        head += bytes([0x80 | n])
    elif n < 1 << 16:
        head += bytes([0x80 | 126]) + struct.pack("!H", n)
    else:
        head += bytes([0x80 | 127]) + struct.pack("!Q", n)
    return head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


def parse_frame(buf: bytes | bytearray) -> tuple[bool, int, bytes, int] | None:
    """(fin, opcode, payload, bytes consumed) for the first complete frame in `buf`, else None.

    Restartable by design: a socket timeout mid-frame leaves the partial bytes in the caller's
    buffer, and the next call simply finds the frame incomplete again.
    """
    if len(buf) < 2:
        return None
    b0, b1 = buf[0], buf[1]
    fin, opcode, masked, n = bool(b0 & 0x80), b0 & 0x0F, bool(b1 & 0x80), b1 & 0x7F
    pos = 2
    if n == 126:
        if len(buf) < pos + 2:
            return None
        n = struct.unpack("!H", bytes(buf[pos:pos + 2]))[0]
        pos += 2
    elif n == 127:
        if len(buf) < pos + 8:
            return None
        n = struct.unpack("!Q", bytes(buf[pos:pos + 8]))[0]
        pos += 8
    if n > MAX_FRAME_BYTES:
        raise PriceFeedError(f"frame of {n} bytes exceeds the {MAX_FRAME_BYTES}-byte limit")
    mask = b""
    if masked:
        if len(buf) < pos + 4:
            return None
        mask = bytes(buf[pos:pos + 4])
        pos += 4
    if len(buf) < pos + n:
        return None
    payload = bytes(buf[pos:pos + n])
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return fin, opcode, payload, pos + n


class WebSocket:
    """A minimal client: TLS, the upgrade handshake, text frames, ping/pong, close."""

    def __init__(self, url: str = WS_URL, *, timeout: float = 20.0,
                 connect: Callable[..., socket.socket] = socket.create_connection) -> None:
        self.url = url
        self.timeout = timeout
        self._connect = connect
        self.sock: Any = None
        self._buf = bytearray()
        self._parts: list[bytes] = []

    def open(self) -> None:
        parts = urlsplit(self.url)
        if parts.scheme not in ("ws", "wss") or not parts.hostname:
            raise PriceFeedError(f"not a WebSocket URL: {self.url}")
        port = parts.port or (443 if parts.scheme == "wss" else 80)
        raw = self._connect((parts.hostname, port), timeout=self.timeout)
        sock = ssl.create_default_context().wrap_socket(raw, server_hostname=parts.hostname) \
            if parts.scheme == "wss" else raw
        key = base64.b64encode(os.urandom(16)).decode()
        path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
        sock.sendall((f"GET {path} HTTP/1.1\r\nHost: {parts.hostname}\r\nUpgrade: websocket\r\n"
                      f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                      "Sec-WebSocket-Version: 13\r\nUser-Agent: soltui-pricefeed\r\n\r\n").encode())
        head = bytearray()
        while b"\r\n\r\n" not in head:
            chunk = sock.recv(4096)
            if not chunk:
                raise PriceFeedError("connection closed during the WebSocket handshake")
            head += chunk
            if len(head) > 65536:
                raise PriceFeedError("oversized handshake response")
        header, _, rest = bytes(head).partition(b"\r\n\r\n")
        lines = header.decode("latin-1").split("\r\n")
        if not lines or " 101 " not in f"{lines[0]} ":
            raise PriceFeedError(f"WebSocket upgrade refused: {lines[0] if lines else '?'}")
        fields = {k.strip().lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])}
        if fields.get("sec-websocket-accept") != accept_key(key):
            raise PriceFeedError("WebSocket handshake returned the wrong Sec-WebSocket-Accept")
        self.sock = sock
        self._buf = bytearray(rest)

    def send_text(self, text: str) -> None:
        self.sock.sendall(encode_frame(OP_TEXT, text.encode("utf-8")))

    def recv_text(self) -> str:
        """The next complete text message. Raises socket.timeout when none arrives in time."""
        while True:
            frame = parse_frame(self._buf)
            if frame is None:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ConnectionClosed("server closed the connection")
                self._buf += chunk
                continue
            fin, opcode, payload, used = frame
            del self._buf[:used]
            if opcode == OP_PING:
                self.sock.sendall(encode_frame(OP_PONG, payload))
            elif opcode == OP_CLOSE:
                raise ConnectionClosed("server sent a close frame")
            elif opcode in (OP_TEXT, OP_BINARY, OP_CONT):
                self._parts.append(payload)
                if fin:
                    text = b"".join(self._parts).decode("utf-8", errors="replace")
                    self._parts = []
                    return text

    def settimeout(self, seconds: float) -> None:
        self.sock.settimeout(seconds)

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.sock.sendall(encode_frame(OP_CLOSE, b""))
        except OSError:
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None


# -- products ------------------------------------------------------------------------------------


def stream_coins() -> list[str]:
    """Every coin the repo caches (data/<COIN>_1m.csv or _1h.csv) plus the Compound universe."""
    from backtester.core.data import resolve_data_dir
    from backtester.core.universe import COMPOUND_5M_UNIVERSE

    coins: set[str] = set(COMPOUND_5M_UNIVERSE)
    data = resolve_data_dir()
    if data.exists():
        for path in data.glob("*_1[mh].csv"):
            coins.add(path.name.split("_", 1)[0].upper())
    return sorted(coins)


def select_products(listing: Iterable[dict[str, Any]], coins: Iterable[str]) -> list[str]:
    """USD markets of `coins` plus every cross pair whose base and quote are both in `coins`."""
    want = {c.upper() for c in coins}
    out = []
    for p in listing:
        if not isinstance(p, dict) or p.get("status", "online") != "online" or p.get("trading_disabled"):
            continue
        base, quote = str(p.get("base_currency", "")).upper(), str(p.get("quote_currency", "")).upper()
        if base in want and (quote == "USD" or quote in want):
            out.append(f"{base}-{quote}")
    return sorted(set(out))


def stream_products(fetch: Callable[[str], Any] | None = None, *, root: Path | None = None,
                    max_age_s: float = 86_400.0) -> list[str]:
    """The product list to subscribe to, cached for a day in `<prices>/products.json`."""
    base = root or prices_dir()
    cache = base / "products.json"
    try:
        cached = json.loads(cache.read_text())
        if time.time() - float(cached["at"]) < max_age_s and cached["products"]:
            return list(cached["products"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        listing = (fetch or _get_json)(PRODUCTS_URL)
        products = select_products(listing, stream_coins())
    except (OSError, ValueError, PriceFeedError):
        products = []
    if not products:
        return list(FALLBACK_PRODUCTS)
    base.mkdir(parents=True, exist_ok=True)
    _atomic_write(cache, json.dumps({"at": time.time(), "products": products}))
    return products


def _get_json(url: str) -> Any:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "soltui-pricefeed"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 - fixed https URL
        return json.loads(resp.read().decode())


# -- the recorder ---------------------------------------------------------------------------------


def _iso_to_epoch(text: Any) -> float | None:
    if not isinstance(text, str) or not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) and x > 0 else None


def apply_ticker(state: dict[str, list[Any]], msg: dict[str, Any], received: float) -> bool:
    """Fold one ticker message into `state`; True when it was a usable quote."""
    if msg.get("type") != "ticker":
        return False
    product = msg.get("product_id")
    bid, ask, last = _num(msg.get("best_bid")), _num(msg.get("best_ask")), _num(msg.get("price"))
    if not isinstance(product, str) or bid is None or ask is None or bid > ask:
        return False
    qt = _iso_to_epoch(msg.get("time")) or received
    state[product] = [bid, ask, last, _num(msg.get("best_bid_size")), _num(msg.get("best_ask_size")),
                      round(qt, 3)]
    return True


class Book:
    """One product's level-2 book from a `snapshot` plus `l2update` changes."""

    __slots__ = ("bids", "asks", "updated")

    def __init__(self) -> None:
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}
        self.updated = 0.0

    def load(self, bids: Iterable[Sequence[Any]], asks: Iterable[Sequence[Any]], now: float) -> None:
        self.bids = {float(p): float(q) for p, q, *_ in bids if float(q) > 0}
        self.asks = {float(p): float(q) for p, q, *_ in asks if float(q) > 0}
        self.updated = now

    def change(self, side: str, price: Any, size: Any, now: float) -> None:
        book = self.bids if side == "buy" else self.asks if side == "sell" else None
        if book is None:
            return
        px, qty = float(price), float(size)
        if qty > 0:
            book[px] = qty
        else:
            book.pop(px, None)
        self.updated = now

    def top(self) -> tuple[float, float, float, float] | None:
        """(bid, ask, bid_size, ask_size), or None for an empty or crossed book."""
        if not self.bids or not self.asks:
            return None
        bid, ask = max(self.bids), min(self.asks)
        if not (math.isfinite(bid) and math.isfinite(ask) and 0 < bid < ask):
            return None
        return bid, ask, self.bids[bid], self.asks[ask]


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _try_lock(path: Path) -> int | None:
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(fd)
        return None
    return fd


class Recorder:
    """Owns the socket and the files. `run` is the loop; everything it decides is testable."""

    def __init__(self, products: Sequence[str], *, root: Path | None = None,
                 snapshot_s: float = SNAPSHOT_SECONDS, flush_s: float = FLUSH_SECONDS,
                 clock: Callable[[], float] = time.time,
                 ws_factory: Callable[[], WebSocket] = WebSocket) -> None:
        self.products = list(products)
        self.root = root or prices_dir()
        self.snapshot_s = snapshot_s
        self.flush_s = flush_s
        self.clock = clock
        self.ws_factory = ws_factory
        self.state: dict[str, list[Any]] = {}
        self.books: dict[str, Book] = {}
        self.last_trade: dict[str, float] = {}
        self.pending: list[str] = []
        self.messages = 0
        self.snapshots = 0
        self.reconnects = 0
        self.last_error = ""
        self.connected_at: float | None = None
        self._next_snapshot = 0.0
        self._next_flush = 0.0
        self.stopping = False

    def snapshot(self, now: float) -> str | None:
        """One snapshot line from the current state, or None before the first quote."""
        if not self.state:
            return None
        return json.dumps({"t": round(now, 3), "q": self.state}, separators=(",", ":"))

    def refresh_from_books(self, now: float) -> None:
        """A synced book's top replaces the ticker's touch; it is live as of `now`."""
        for product, book in self.books.items():
            top = book.top()
            if top is None:
                continue
            bid, ask, bsz, asz = top
            last = self.last_trade.get(product)
            self.state[product] = [bid, ask, last if last is not None else (bid + ask) / 2, bsz, asz,
                                   round(now, 3)]

    def maybe_snapshot(self, now: float) -> None:
        if now < self._next_snapshot:
            return
        self._next_snapshot = now + self.snapshot_s
        self.refresh_from_books(now)
        line = self.snapshot(now)
        if line is None:
            return
        self.pending.append(line)
        self.snapshots += 1
        self.write_latest(now)
        if now >= self._next_flush:
            self.flush(now)

    def write_latest(self, now: float) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        _atomic_write(self.root / "latest.json", json.dumps({
            "t": round(now, 3), "pid": os.getpid(), "products": self.products, "q": self.state,
            "messages": self.messages, "snapshots": self.snapshots, "reconnects": self.reconnects,
            "connected_at": self.connected_at, "last_error": self.last_error}, separators=(",", ":")))

    def flush(self, now: float) -> None:
        """Append pending lines as one gzip member to their UTC day files."""
        self._next_flush = now + self.flush_s
        if not self.pending:
            return
        by_day: dict[Path, list[str]] = {}
        for line in self.pending:
            t = json.loads(line)["t"]
            by_day.setdefault(day_path(t, self.root), []).append(line)
        self.root.mkdir(parents=True, exist_ok=True)
        for path, lines in by_day.items():
            with gzip.open(path, "at", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
        self.pending = []

    def handle(self, text: str, now: float) -> None:
        try:
            msg = json.loads(text)
        except ValueError:
            return
        if not isinstance(msg, dict):
            return
        kind, product = msg.get("type"), msg.get("product_id")
        try:
            if kind == "error":
                self.last_error = str(msg.get("message") or msg.get("reason") or "error")[:300]
            elif kind == "snapshot" and isinstance(product, str):
                self.books.setdefault(product, Book()).load(msg.get("bids") or [], msg.get("asks") or [], now)
                self.messages += 1
            elif kind == "l2update" and isinstance(product, str) and product in self.books:
                book = self.books[product]
                for side, price, size in msg.get("changes") or []:
                    book.change(side, price, size, now)
                self.messages += 1
            elif kind == "ticker":
                last = _num(msg.get("price"))
                if isinstance(product, str) and last is not None:
                    self.last_trade[product] = last
                # A ticker quote stands in only where no synced book exists.
                if product not in self.books and apply_ticker(self.state, msg, now):
                    pass
                self.messages += 1
        except (TypeError, ValueError):
            return  # one malformed message never ends the recording

    def run_once(self, max_seconds: float | None = None) -> None:
        """One connection: subscribe, then read until it fails or `max_seconds` pass."""
        ws = self.ws_factory()
        ws.open()
        # A new connection starts from fresh book snapshots; a book carried across a gap would
        # have missed every change made while disconnected.
        self.books.clear()
        ws.send_text(json.dumps({"type": "subscribe", "product_ids": self.products,
                                 "channels": ["level2_batch", "ticker"]}))
        ws.settimeout(RECV_TIMEOUT_S)
        self.connected_at = self.clock()
        started = self.clock()
        try:
            while not self.stopping:
                try:
                    text = ws.recv_text()
                    self.handle(text, self.clock())
                except (socket.timeout, TimeoutError):
                    pass
                now = self.clock()
                self.maybe_snapshot(now)
                if max_seconds is not None and now - started >= max_seconds:
                    return
        finally:
            ws.close()

    def run(self, *, max_seconds: float | None = None, sleep: Callable[[float], None] = time.sleep) -> int:
        """Reconnect forever (with backoff) until stopped; always flush what is pending."""
        backoff = 1.0
        started = self.clock()
        try:
            while not self.stopping:
                remaining = None if max_seconds is None else max_seconds - (self.clock() - started)
                if remaining is not None and remaining <= 0:
                    break
                try:
                    self.run_once(remaining)
                    backoff = 1.0
                except (OSError, PriceFeedError, ValueError) as exc:
                    self.last_error = f"{type(exc).__name__}: {exc}"[:300]
                    self.reconnects += 1
                    self.connected_at = None
                    print(f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} reconnect in {backoff:.0f}s: "
                          f"{self.last_error}", flush=True)
                    self.flush(self.clock())
                    sleep(backoff)
                    backoff = min(backoff * 2, 60.0)
        finally:
            self.flush(self.clock())
        return 0


# -- process control (the console's view) -------------------------------------------------------


def paths(root: Path | None = None) -> dict[str, Path]:
    base = root or prices_dir()
    return {"lock": base / "recorder.lock", "pid": base / "recorder.pid", "log": base / "recorder.log",
            "latest": base / "latest.json"}


def recorder_running(root: Path | None = None) -> bool:
    fd = _try_lock(paths(root)["lock"])
    if fd is None:
        return True
    os.close(fd)
    return False


def read_latest(root: Path | None = None) -> dict[str, Any] | None:
    try:
        data = json.loads(paths(root)["latest"].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def status(root: Path | None = None, now: float | None = None) -> dict[str, Any]:
    """Recorder state, recorded coverage and the newest prices (mid of bid/ask)."""
    now = time.time() if now is None else now
    latest = read_latest(root) or {}
    files = recorded_files(root)
    age = now - float(latest["t"]) if "t" in latest else None
    prices = {}
    for product, q in (latest.get("q") or {}).items():
        try:
            bid, ask, last = q[0], q[1], q[2]
            prices[product] = {"bid": bid, "ask": ask, "last": last, "mid": (bid + ask) / 2,
                               "spread_bps": 10_000 * (ask - bid) / ((ask + bid) / 2),
                               "quote_age_s": round(now - float(q[5]), 1)}
        except (TypeError, ValueError, IndexError, ZeroDivisionError):
            continue
    pid = None
    try:
        pid = int(paths(root)["pid"].read_text().strip())
    except (OSError, ValueError):
        pass
    running = recorder_running(root)
    return {"running": running, "pid": pid if running else None, "snapshot_age_s": age,
            "live": bool(running and age is not None and age < 10),
            "messages": latest.get("messages"), "snapshots": latest.get("snapshots"),
            "reconnects": latest.get("reconnects"), "last_error": latest.get("last_error") or "",
            "products": latest.get("products") or [], "prices": prices,
            "files": [{"name": p.name, "bytes": p.stat().st_size} for p in files[-14:]],
            "recorded_days": len(files), "dir": str(root or prices_dir())}


def start_recorder(root: Path | None = None) -> dict[str, Any]:
    """Spawn the recorder detached at background priority, unless one already runs."""
    import subprocess

    from . import bgcontrol

    p = paths(root)
    if recorder_running(root):
        return {"started": False, "already_running": True, "log": str(p["log"])}
    cmd = [sys.executable, "-m", "soltui.pricefeed", "record"]
    launcher = bgcontrol.taskpolicy_path()
    if launcher:
        cmd = [launcher, "-b", *cmd]
    env = {**os.environ, "PYTHONPATH": str(REPO) + os.pathsep + os.environ.get("PYTHONPATH", ""),
           "SOLTUI_CONFIG_DIR": str(config_mod.CONFIG_DIR)}
    p["log"].parent.mkdir(parents=True, exist_ok=True)
    with p["log"].open("ab") as log:
        proc = subprocess.Popen(cmd, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,  # noqa: S603
                                stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):  # up to 5 s for the child to take its lock
        time.sleep(0.1)
        if recorder_running(root) or proc.poll() is not None:
            break
    return {"started": recorder_running(root), "already_running": False, "pid": proc.pid,
            "log": str(p["log"])}


def stop_recorder(root: Path | None = None) -> dict[str, Any]:
    import signal

    p = paths(root)
    if not recorder_running(root):
        return {"stopping": False, "message": "no recorder is running"}
    try:
        pid = int(p["pid"].read_text().strip())
        os.kill(pid, signal.SIGTERM)
    except (OSError, ValueError) as exc:
        return {"stopping": False, "message": f"could not signal the recorder: {exc}"}
    return {"stopping": True, "pid": pid}


def _wait_lock(path: Path) -> int:
    """Block until the lock is free, then hold it (the LaunchAgent's mode)."""
    import fcntl

    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def record_main(root: Path | None = None, max_seconds: float | None = None, *, wait_lock: bool = False) -> int:
    """The recorder process: hold the lock, write the pid, record until SIGTERM.

    With `wait_lock` it waits for another recorder to exit instead of giving up, which is what
    the LaunchAgent runs: KeepAlive would otherwise relaunch an exiting process every ten seconds.
    """
    import signal

    p = paths(root)
    if wait_lock:
        fd = _try_lock(p["lock"])
        if fd is None:
            print("another recorder holds the lock; waiting for it to exit", flush=True)
            fd = _wait_lock(p["lock"])
    else:
        fd = _try_lock(p["lock"])
    if fd is None:
        print("another recorder holds the lock; exiting", flush=True)
        return 1
    p["pid"].write_text(f"{os.getpid()}\n")
    products = stream_products(root=root)
    rec = Recorder(products, root=root)

    def on_term(signum: int, frame: Any) -> None:
        rec.stopping = True

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    print(f"{datetime.now(timezone.utc):%Y-%m-%dT%H:%M:%SZ} recording {len(products)} products "
          f"to {rec.root}", flush=True)
    try:
        return rec.run(max_seconds=max_seconds)
    finally:
        p["pid"].unlink(missing_ok=True)
        os.close(fd)


# -- the LaunchAgent: recording survives a closed console, a crash and a reboot -------------------

AGENT_LABEL = "com.mitchhudson.soltui.pricefeed"


def agents_dir() -> Path:
    return Path(os.environ.get("SOLTUI_LAUNCHAGENTS_DIR") or Path.home() / "Library" / "LaunchAgents")


def agent_plist_path() -> Path:
    return agents_dir() / f"{AGENT_LABEL}.plist"


def agent_log_path() -> Path:
    return Path.home() / "Library" / "Logs" / "soltui" / "pricefeed.log"


def is_worktree(repo: Path) -> bool:
    """A linked git worktree has a `.git` FILE; the main checkout has a `.git` directory."""
    return (repo / ".git").is_file()


def agent_plist(python: Path, repo: Path = REPO) -> dict[str, Any]:
    return {
        "Label": AGENT_LABEL,
        "ProgramArguments": [str(python), "-m", "soltui.pricefeed", "record", "--wait-lock"],
        "WorkingDirectory": str(repo),
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 30,
        "ProcessType": "Background",
        "Nice": 10,
        "StandardOutPath": str(agent_log_path()),
        "StandardErrorPath": str(agent_log_path()),
        # launchd starts with no LANG (US-ASCII) and no PYTHONPATH; the config dir is pinned so the
        # agent records where the console reads.
        "EnvironmentVariables": {"PYTHONUTF8": "1", "LANG": "en_US.UTF-8", "PYTHONPATH": str(repo),
                                 "SOLTUI_CONFIG_DIR": str(config_mod.CONFIG_DIR)},
    }


def _launchctl(*args: str) -> Any:
    import subprocess

    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=30)


def _domain() -> str:
    return f"gui/{os.getuid()}"


def install_agent(python: Path | None = None, repo: Path = REPO) -> dict[str, Any]:
    """Write and load the LaunchAgent. Refuses a git worktree, which can be deleted at any time."""
    import plistlib

    python = Path(python or sys.executable)
    if not python.exists():
        raise PriceFeedError(f"interpreter not found: {python}")
    if is_worktree(repo):
        raise PriceFeedError(f"{repo} is a git worktree; the recorder agent must run from the main checkout")
    path = agent_plist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    agent_log_path().parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(agent_plist(python, repo)))
    path.chmod(0o644)
    _launchctl("bootout", f"{_domain()}/{AGENT_LABEL}")
    boot = _launchctl("bootstrap", _domain(), str(path))
    out: dict[str, Any] = {"plist": str(path), "label": AGENT_LABEL, "bootstrap": boot.returncode}
    if boot.returncode:
        out["bootstrap_error"] = (boot.stderr or "").strip()[:200]
    return out


def uninstall_agent() -> dict[str, Any]:
    _launchctl("bootout", f"{_domain()}/{AGENT_LABEL}")
    path = agent_plist_path()
    existed = path.exists()
    path.unlink(missing_ok=True)
    return {"plist": str(path), "removed": existed}


def agent_status() -> dict[str, Any]:
    info: dict[str, Any] = {"label": AGENT_LABEL, "installed": agent_plist_path().exists(), "loaded": False}
    try:
        printed = _launchctl("print", f"{_domain()}/{AGENT_LABEL}")
    except Exception:  # noqa: BLE001 - no launchctl (Linux CI) or it hung: report not loaded
        return info
    info["loaded"] = printed.returncode == 0
    return info


def ensure_recorder(root: Path | None = None, *, repo: Path = REPO, install: bool = True) -> dict[str, Any]:
    """Keep recording on: install the LaunchAgent if it is missing, else start a detached recorder.

    Idempotent and cheap when a recorder already runs; the console calls it at start and every
    minute, so a recorder that died comes back without anyone pressing anything.
    """
    out: dict[str, Any] = {"running": recorder_running(root)}
    agent = agent_status()
    out["agent"] = agent
    if install and root is None and not (agent["installed"] and agent["loaded"]):
        try:
            out["installed"] = install_agent(repo=repo)
        except PriceFeedError as exc:
            out["agent_error"] = str(exc)
    if not recorder_running(root):
        for _ in range(30):  # the agent's process takes a moment to take the lock
            if out.get("installed", {}).get("bootstrap") != 0:
                break
            time.sleep(0.1)
            if recorder_running(root):
                break
    if not recorder_running(root):
        out["started"] = start_recorder(root)
    out["running"] = recorder_running(root)
    return out


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m soltui.pricefeed")
    sub = ap.add_subparsers(dest="cmd")
    rec = sub.add_parser("record", help="record the stream until SIGTERM")
    rec.add_argument("--seconds", type=float, default=None, help="stop after this long (testing)")
    rec.add_argument("--wait-lock", action="store_true", help="wait for another recorder instead of exiting")
    sub.add_parser("status", help="recorder state and the newest prices")
    sub.add_parser("install", help="install and load the always-on LaunchAgent")
    sub.add_parser("uninstall", help="unload and remove the LaunchAgent")
    sub.add_parser("ensure", help="install the agent if missing and make sure a recorder runs")
    args = ap.parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.cmd == "record":
        return record_main(max_seconds=args.seconds, wait_lock=args.wait_lock)
    if args.cmd in ("status", "install", "uninstall", "ensure"):
        fn = {"status": lambda: {**status(), "agent": agent_status()}, "install": install_agent,
              "uninstall": uninstall_agent, "ensure": ensure_recorder}[args.cmd]
        print(json.dumps(fn(), indent=2))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

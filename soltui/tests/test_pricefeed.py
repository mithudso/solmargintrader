"""The streaming price recorder: RFC 6455 framing, the handshake, books, snapshots and files.

No network: every socket here is a fake, and every file lives in a temporary directory.
"""

from __future__ import annotations

import gzip
import json
import socket
import struct
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from backtester.core.trianglesim import read_snapshot_files
from soltui import pricefeed as pf


class FakeSock:
    """Replays scripted server bytes; records what the client sent."""

    def __init__(self, chunks: list[bytes | type[Exception]]) -> None:
        self.chunks = list(chunks)
        self.sent = bytearray()
        self.closed = False

    def sendall(self, data: bytes) -> None:
        self.sent += data

    def recv(self, n: int) -> bytes:
        if not self.chunks:
            return b""
        item = self.chunks.pop(0)
        if isinstance(item, type) and issubclass(item, Exception):
            raise item()
        return item  # type: ignore[return-value]

    def settimeout(self, s: float) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def server_frame(opcode: int, payload: bytes, fin: bool = True) -> bytes:
    """An unmasked server frame, as servers send them."""
    n = len(payload)
    head = bytes([(0x80 if fin else 0) | opcode])
    if n < 126:
        head += bytes([n])
    elif n < 65536:
        head += bytes([126]) + struct.pack("!H", n)
    else:
        head += bytes([127]) + struct.pack("!Q", n)
    return head + payload


def connected(chunks: list) -> tuple[pf.WebSocket, FakeSock]:
    ws = pf.WebSocket("ws://example.test/")
    sock = FakeSock(chunks)
    ws.sock = sock
    return ws, sock


class Framing(unittest.TestCase):
    def test_accept_key_matches_rfc6455_example(self) -> None:
        self.assertEqual(pf.accept_key("dGhlIHNhbXBsZSBub25jZQ=="), "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")

    def test_client_frames_are_masked_and_round_trip(self) -> None:
        for size in (0, 5, 125, 126, 70_000):
            payload = bytes(range(256)) * (size // 256 + 1)
            payload = payload[:size]
            frame = pf.encode_frame(pf.OP_TEXT, payload, mask=b"\x01\x02\x03\x04")
            self.assertTrue(frame[1] & 0x80, "client frames must set the mask bit")
            fin, op, out, used = pf.parse_frame(frame)
            self.assertEqual((fin, op, out, used), (True, pf.OP_TEXT, payload, len(frame)))

    def test_an_incomplete_frame_waits_for_more_bytes(self) -> None:
        frame = server_frame(pf.OP_TEXT, b"x" * 300)
        for cut in (1, 3, 100, len(frame) - 1):
            self.assertIsNone(pf.parse_frame(frame[:cut]))

    def test_an_oversized_frame_is_refused(self) -> None:
        head = bytes([0x81, 127]) + struct.pack("!Q", pf.MAX_FRAME_BYTES + 1)
        with self.assertRaises(pf.PriceFeedError):
            pf.parse_frame(head)


class Client(unittest.TestCase):
    def test_handshake_checks_the_accept_header(self) -> None:
        sent = {}

        def fake_connect(addr, timeout):
            sock = FakeSock([])

            def respond(n: int) -> bytes:
                key = sent["req"].split(b"Sec-WebSocket-Key: ")[1].split(b"\r\n")[0].decode()
                accept = sent.get("accept") or pf.accept_key(key)
                return (f"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Accept: {accept}\r\n\r\n").encode() + server_frame(pf.OP_TEXT, b"hi")

            sock.recv = respond  # type: ignore[method-assign]
            sock.sendall = lambda data: sent.__setitem__("req", bytes(data))  # type: ignore[method-assign]
            return sock

        ws = pf.WebSocket("ws://example.test/feed", connect=fake_connect)
        ws.open()
        self.assertIn(b"GET /feed HTTP/1.1", sent["req"])
        self.assertEqual(ws.recv_text(), "hi")  # bytes after the headers are the first frame
        sent["accept"] = "wrong"
        with self.assertRaises(pf.PriceFeedError):
            pf.WebSocket("ws://example.test/", connect=fake_connect).open()

    def test_ping_is_answered_and_fragments_are_joined(self) -> None:
        ws, sock = connected([server_frame(pf.OP_PING, b"p") + server_frame(pf.OP_TEXT, b"ab", fin=False),
                              server_frame(pf.OP_CONT, b"cd")])
        self.assertEqual(ws.recv_text(), "abcd")
        fin, op, payload, _ = pf.parse_frame(sock.sent)
        self.assertEqual((op, payload), (pf.OP_PONG, b"p"))

    def test_a_timeout_mid_frame_keeps_the_partial_bytes(self) -> None:
        frame = server_frame(pf.OP_TEXT, b'{"type":"ticker"}')
        ws, _ = connected([frame[:5], socket.timeout, frame[5:]])
        with self.assertRaises(socket.timeout):
            ws.recv_text()
        self.assertEqual(ws.recv_text(), '{"type":"ticker"}')

    def test_close_frame_and_eof_end_the_connection(self) -> None:
        ws, _ = connected([server_frame(pf.OP_CLOSE, b"")])
        with self.assertRaises(pf.ConnectionClosed):
            ws.recv_text()
        ws, _ = connected([])
        with self.assertRaises(pf.ConnectionClosed):
            ws.recv_text()


class Products(unittest.TestCase):
    LISTING = [
        {"base_currency": "SOL", "quote_currency": "USD", "status": "online"},
        {"base_currency": "SOL", "quote_currency": "ETH", "status": "online"},
        {"base_currency": "SOL", "quote_currency": "EUR", "status": "online"},
        {"base_currency": "ETH", "quote_currency": "USD", "status": "online"},
        {"base_currency": "ZZZ", "quote_currency": "USD", "status": "online"},
        {"base_currency": "BTC", "quote_currency": "USD", "status": "delisted"},
    ]

    def test_usd_markets_and_crosses_among_known_coins(self) -> None:
        self.assertEqual(pf.select_products(self.LISTING, ["SOL", "ETH", "BTC"]), ["ETH-USD", "SOL-ETH", "SOL-USD"])

    def test_select_products_omits_removed_assets(self) -> None:
        listing = [{"id": f"{asset}-USD", "base_currency": asset, "quote_currency": "USD"}
                   for asset in ("SOL", "RAIN", "WBT", "HTX", "JST", "MNT", "XMR")]
        self.assertEqual(pf.select_products(listing, [p["base_currency"] for p in listing]),
                         ["SOL-USD"])

    def test_cached_for_a_day_and_falls_back_offline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(pf, "stream_coins", return_value=["SOL", "ETH"]):
                got = pf.stream_products(lambda url: self.LISTING, root=root)
                self.assertEqual(got, ["ETH-USD", "SOL-ETH", "SOL-USD"])
                self.assertEqual(pf.stream_products(lambda url: 1 / 0, root=root), got)  # cache, no fetch
            with tempfile.TemporaryDirectory() as tmp2:
                def offline(url):
                    raise OSError("offline")
                self.assertEqual(pf.stream_products(offline, root=Path(tmp2)), list(pf.FALLBACK_PRODUCTS))

    def test_cached_product_list_drops_removed_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "products.json").write_text(json.dumps({
                "at": time.time(), "products": ["SOL-USD", "XMR-USD", "ETH-MNT"]
            }))
            self.assertEqual(pf.stream_products(root=root), ["SOL-USD"])


class Books(unittest.TestCase):
    def test_snapshot_changes_and_top(self) -> None:
        book = pf.Book()
        book.load([["10.0", "1"], ["9.5", "2"]], [["10.5", "3"], ["11", "1"]], 0.0)
        self.assertEqual(book.top(), (10.0, 10.5, 1.0, 3.0))
        book.change("buy", "10.0", "0", 1.0)   # the best bid is pulled
        book.change("sell", "10.2", "4", 1.0)  # a better ask arrives
        self.assertEqual(book.top(), (9.5, 10.2, 2.0, 4.0))
        book.change("buy", "10.3", "1", 2.0)   # crossed: refuse rather than report it
        self.assertIsNone(book.top())

    def test_book_top_replaces_the_stale_ticker_touch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rec = pf.Recorder(["SOL-ETH", "SOL-USD"], root=Path(tmp))
            rec.handle(json.dumps({"type": "ticker", "product_id": "SOL-ETH", "price": "0.0400",
                                   "best_bid": "0.0399", "best_ask": "0.0401", "time": "2026-11-08T00:00:00Z"}), 100.0)
            rec.handle(json.dumps({"type": "snapshot", "product_id": "SOL-ETH", "bids": [["0.0398", "5"]],
                                   "asks": [["0.0399", "6"]]}), 101.0)
            rec.handle(json.dumps({"type": "ticker", "product_id": "SOL-USD", "price": "89",
                                   "best_bid": "88.99", "best_ask": "89.01", "best_bid_size": "2",
                                   "time": "2026-11-08T00:00:00Z"}), 101.0)
            rec.handle("not json", 101.0)
            rec.handle(json.dumps({"type": "l2update", "product_id": "SOL-ETH", "changes": [["buy", "x", "1"]]}), 101.0)
            rec.refresh_from_books(102.0)
            self.assertEqual(rec.state["SOL-ETH"], [0.0398, 0.0399, 0.04, 5.0, 6.0, 102.0])
            self.assertEqual(rec.state["SOL-USD"][:4], [88.99, 89.01, 89.0, 2.0])


class Recording(unittest.TestCase):
    def test_snapshots_flush_to_day_files_readable_by_the_backtester(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rec = pf.Recorder(["ETH-USD"], root=root, snapshot_s=1.0, flush_s=100.0)
            rec.maybe_snapshot(1.0)  # nothing quoted yet: no line
            self.assertEqual(rec.snapshots, 0)
            rec.state["ETH-USD"] = [3000.0, 3001.0, 3000.5, 1.0, 2.0, 1.0]
            day_end = 1_794_095_999.0  # 2026-11-07 23:59:59 UTC
            for t in (day_end - 1, day_end, day_end + 1):
                rec.maybe_snapshot(t)
            rec.flush(day_end + 2)
            files = pf.recorded_files(root)
            self.assertEqual([f.name for f in files], ["2026-11-07.jsonl.gz", "2026-11-08.jsonl.gz"])
            snaps = read_snapshot_files(files)
            self.assertEqual([t for t, _ in snaps], [day_end - 1, day_end, day_end + 1])
            latest = json.loads((root / "latest.json").read_text())
            self.assertEqual(latest["q"]["ETH-USD"][0], 3000.0)
            # A second flush appends a new gzip member to the same day's file.
            rec.maybe_snapshot(day_end + 5)
            rec.flush(day_end + 6)
            with gzip.open(files[1], "rt") as fh:
                self.assertEqual(len(fh.read().splitlines()), 2)

    def test_run_once_subscribes_to_both_channels_and_records(self) -> None:
        clock = iter(float(t) for t in range(100, 200))

        class FakeWS:
            sent: list[str] = []

            def open(self) -> None:
                pass

            def send_text(self, text: str) -> None:
                FakeWS.sent.append(text)

            def settimeout(self, s: float) -> None:
                pass

            msgs = [json.dumps({"type": "snapshot", "product_id": "ETH-USD", "bids": [["3000", "1"]],
                                "asks": [["3001", "1"]]}), socket.timeout]

            def recv_text(self) -> str:
                item = self.msgs.pop(0) if self.msgs else socket.timeout
                if item is socket.timeout:
                    raise socket.timeout()
                return item

            def close(self) -> None:
                pass

        with tempfile.TemporaryDirectory() as tmp:
            rec = pf.Recorder(["ETH-USD"], root=Path(tmp), clock=lambda: next(clock), ws_factory=FakeWS,
                              flush_s=0.0)
            rec.run_once(max_seconds=5)
            sub = json.loads(FakeWS.sent[0])
            self.assertEqual(sub["channels"], ["level2_batch", "ticker", "heartbeat"])
            self.assertGreater(rec.snapshots, 0)
            self.assertTrue(pf.recorded_files(Path(tmp)))

    def test_run_reconnects_with_backoff_and_flushes(self) -> None:
        attempts = []

        class Failing:
            def open(self) -> None:
                attempts.append(1)
                raise OSError("network down")

            def close(self) -> None:
                pass

        ticks = iter(float(t) for t in range(0, 1000, 10))
        sleeps: list[float] = []
        with tempfile.TemporaryDirectory() as tmp:
            rec = pf.Recorder(["ETH-USD"], root=Path(tmp), clock=lambda: next(ticks), ws_factory=Failing)
            rec.run(max_seconds=45, sleep=sleeps.append)
            self.assertGreaterEqual(len(attempts), 2)
            self.assertEqual(sleeps[:3], [1.0, 2.0, 4.0][: len(sleeps[:3])])
            self.assertIn("network down", rec.last_error)


class Status(unittest.TestCase):
    def test_status_reads_latest_and_reports_spread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            empty = pf.status(root, now=10.0)
            self.assertFalse(empty["running"])
            self.assertEqual(empty["prices"], {})
            (root / "latest.json").write_text(json.dumps(
                {"t": 9.0, "q": {"SOL-USD": [99.0, 101.0, 100.0, 1, 1, 8.0]}, "products": ["SOL-USD"]}))
            st = pf.status(root, now=10.0)
            self.assertAlmostEqual(st["prices"]["SOL-USD"]["spread_bps"], 200.0)
            self.assertAlmostEqual(st["prices"]["SOL-USD"]["quote_age_s"], 2.0)
            self.assertFalse(st["live"], "a snapshot with no running recorder is not live")

    def test_one_recorder_holds_the_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(pf.recorder_running(root))
            fd = pf._try_lock(pf.paths(root)["lock"])
            try:
                self.assertTrue(pf.recorder_running(root))
                self.assertEqual(pf.record_main(root, max_seconds=0), 1)  # refuses a second recorder
                self.assertEqual(pf.start_recorder(root)["already_running"], True)
            finally:
                import os
                os.close(fd)
            self.assertEqual(pf.stop_recorder(root)["stopping"], False)

    def test_record_main_waits_for_the_lock_in_agent_mode(self) -> None:
        import os
        import threading

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fd = pf._try_lock(pf.paths(root)["lock"])
            threading.Timer(0.3, os.close, args=(fd,)).start()  # the other recorder exits shortly
            with mock.patch.object(pf, "stream_products", return_value=["ETH-USD"]), \
                    mock.patch.object(pf.Recorder, "run", return_value=0) as run:
                self.assertEqual(pf.record_main(root, max_seconds=0, wait_lock=True), 0)
            run.assert_called_once()
            self.assertFalse(pf.paths(root)["pid"].exists(), "the pid file is removed on exit")

    def test_the_module_never_touches_key_files(self) -> None:
        src = Path(pf.__file__).read_text()
        for needle in ("wallet.private", "solana.private", ".ssh", "load_signer"):
            self.assertNotIn(needle, src)



class Agent(unittest.TestCase):
    """The always-on LaunchAgent; launchctl is never really called."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        env = mock.patch.dict("os.environ", {"SOLTUI_LAUNCHAGENTS_DIR": str(self.root / "agents")})
        env.start()
        self.addCleanup(env.stop)
        self.calls: list[tuple] = []

        def fake_launchctl(*args):
            self.calls.append(args)
            return mock.Mock(returncode=0, stderr="", stdout="")

        lc = mock.patch.object(pf, "_launchctl", side_effect=fake_launchctl)
        lc.start()
        self.addCleanup(lc.stop)

    def repo(self, worktree: bool) -> Path:
        repo = self.root / ("wt" if worktree else "main")
        repo.mkdir()
        if worktree:
            (repo / ".git").write_text("gitdir: /elsewhere\n")
        else:
            (repo / ".git").mkdir()
        return repo

    def test_plist_keeps_the_recorder_alive_and_waits_for_the_lock(self) -> None:
        d = pf.agent_plist(Path("/py"), Path("/repo"))
        self.assertEqual(d["ProgramArguments"], ["/py", "-m", "soltui.pricefeed", "record", "--wait-lock"])
        self.assertIs(d["KeepAlive"], True)
        self.assertIs(d["RunAtLoad"], True)
        self.assertEqual(d["WorkingDirectory"], "/repo")
        self.assertIn("SOLTUI_CONFIG_DIR", d["EnvironmentVariables"])
        self.assertEqual(d["EnvironmentVariables"]["PYTHONPATH"], "/repo")

    def test_install_writes_and_bootstraps_but_refuses_a_worktree(self) -> None:
        import plistlib
        import sys

        out = pf.install_agent(Path(sys.executable), self.repo(worktree=False))
        self.assertEqual(out["bootstrap"], 0)
        plist = plistlib.loads(pf.agent_plist_path().read_bytes())
        self.assertEqual(plist["Label"], pf.AGENT_LABEL)
        self.assertIn(("bootstrap", pf._domain(), str(pf.agent_plist_path())), self.calls)
        with self.assertRaisesRegex(pf.PriceFeedError, "worktree"):
            pf.install_agent(Path(sys.executable), self.repo(worktree=True))
        self.assertTrue(pf.uninstall_agent()["removed"])

    def test_ensure_does_nothing_when_a_recorder_and_the_agent_run(self) -> None:
        with mock.patch.object(pf, "recorder_running", return_value=True), \
                mock.patch.object(pf, "agent_status", return_value={"installed": True, "loaded": True}), \
                mock.patch.object(pf, "install_agent") as install, mock.patch.object(pf, "start_recorder") as start:
            self.assertTrue(pf.ensure_recorder()["running"])
        install.assert_not_called()
        start.assert_not_called()

    def test_ensure_falls_back_to_a_detached_recorder_when_the_agent_cannot_install(self) -> None:
        state = {"running": False}
        with mock.patch.object(pf, "recorder_running", side_effect=lambda root=None: state["running"]), \
                mock.patch.object(pf, "agent_status", return_value={"installed": False, "loaded": False}), \
                mock.patch.object(pf, "install_agent", side_effect=pf.PriceFeedError("is a git worktree")), \
                mock.patch.object(pf, "start_recorder", side_effect=lambda root=None: state.update(running=True) or
                                  {"started": True}):
            out = pf.ensure_recorder(repo=self.repo(worktree=True))
        self.assertTrue(out["running"])
        self.assertIn("worktree", out["agent_error"])
        self.assertEqual(out["started"], {"started": True})


if __name__ == "__main__":
    unittest.main()

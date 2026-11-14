"""History coverage, source isolation and the real read-only transport boundaries."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from soltui import config, wallet, wallet_activity as activity


class WalletActivity(unittest.TestCase):
    def setUp(self):
        self.settings = config.Settings()
        self.owner = self.settings.base_address.lower()
        self.peer = "0x" + "a" * 40
        self.tx = "0x" + "1" * 64
        self.signature = "5" * 88
        self.usdc = wallet.KNOWN_BASE_TOKENS[1][0].lower()

    def query(self, sql, timeout):
        self.assertGreater(timeout, 0)
        self.assertIn("INTERVAL 14 DAY", sql)
        self.assertIn("HAVING sum", sql)
        if "base.transactions" in sql:
            self.assertIn("max(timestamp) AS occurred_at", sql)
            self.assertNotIn(" AS timestamp", sql)
            self.assertNotIn(" AS from_address", sql)
            return [{"transaction_hash": self.tx, "occurred_at": "2026-11-08T23:00:00Z",
                     "sender": self.owner, "recipient": self.usdc, "chain_action": 1}]
        self.assertIn("sum(toInt8(action))", sql)
        return [{"log_id": "receipt", "tx_hash": self.tx, "occurred_at": "2026-11-08T23:00:00Z",
                 "sender": self.peer, "recipient": self.owner, "token_address": self.usdc, "chain_action": 1}]

    def rpc(self, method, params, timeout):
        self.assertGreater(timeout, 0)
        if method == "getSignaturesForAddress":
            self.assertEqual(params[0], self.settings.solana_address)
            self.assertEqual(params[1]["commitment"], "finalized")
            return [{"signature": self.signature, "blockTime": 1794182400, "err": None}]
        self.assertEqual(method, "getTransaction")
        self.assertEqual(params[1]["maxSupportedTransactionVersion"], 0)
        return {"transaction": {"message": {"accountKeys": [{"pubkey": self.peer, "signer": True}]}}, "meta": {"err": None}}

    def test_external_senders_and_paper_wallet_separation(self):
        result = activity.snapshot(self.settings, query=self.query, rpc=self.rpc)
        self.assertEqual(len(result["items"]), 3)
        self.assertTrue(all(i["mode"] == "wallet" for i in result["items"]))
        transfer = next(i for i in result["items"] if i["kind"] == "token_transfer")
        self.assertEqual(transfer["actor"], self.peer)
        self.assertEqual(transfer["summary"], "Received USDC transfer")
        self.assertTrue(transfer["url"].startswith("https://basescan.org/tx/"))
        sol = next(i for i in result["items"] if i["chain"] == "solana")
        self.assertEqual(sol["summary"], "Incoming / related Solana transaction")
        self.assertFalse(any(c["complete"] for c in result["coverage"]))
        self.assertEqual(result["gaps"], [])

    def test_missing_source_preserves_independent_wallet_activity(self):
        def unavailable(*args):
            raise RuntimeError("credential material must never appear")
        result = activity.snapshot(self.settings, query=unavailable, rpc=self.rpc)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["chain"], "solana")
        self.assertEqual(result["coverage"][0]["state"], "unavailable")
        self.assertNotIn("credential material", json.dumps(result))

    def test_untrusted_contracts_reorgs_and_unsafe_links_are_rejected(self):
        def query(sql, timeout):
            if "base.transactions" in sql:
                return [{"transaction_hash": "javascript:alert(1)", "from_address": self.owner,
                         "to_address": self.peer, "chain_action": 1},
                        {"transaction_hash": self.tx, "from_address": self.owner, "to_address": self.peer,
                         "chain_action": 0}]
            return [{"log_id": "spam", "transaction_hash": self.tx, "from_address": self.peer,
                     "to_address": self.owner, "address": "0x" + "b" * 40, "chain_action": 1}]
        result = activity.snapshot(self.settings, query=query, rpc=lambda *a: [])
        self.assertEqual(result["items"], [])

    def test_unknown_time_is_not_fabricated_and_details_can_fail(self):
        def rpc(method, params, timeout):
            if method == "getSignaturesForAddress":
                return [{"signature": self.signature, "blockTime": None, "err": {"InstructionError": [0, "Error"]}}]
            return None
        result = activity.snapshot(self.settings, query=lambda *a: [], rpc=rpc)
        self.assertIsNone(result["items"][0]["at"])
        self.assertEqual(result["items"][0]["status"], "failed")
        self.assertEqual(result["coverage"][1]["state"], "partial")

    def test_invalid_owners_and_cancelled_reads_make_no_requests(self):
        calls = []
        def forbidden(*args):
            calls.append(args)
            raise AssertionError("No network call is allowed")
        self.settings.base_address = "0x'; SELECT secret"
        self.settings.solana_address = "invalid"
        result = activity.snapshot(self.settings, query=forbidden, rpc=forbidden)
        self.assertEqual(result["items"], [])
        self.settings = config.Settings()
        stopped = threading.Event(); stopped.set()
        result = activity.snapshot(self.settings, query=forbidden, rpc=forbidden, stop=stopped)
        self.assertEqual(result["items"], [])

        self.assertEqual(calls, [], "invalid or cancelled reads must not reach either transport")

    def test_cdp_transport_uses_fixed_argv_and_redacts_failures(self):
        error = subprocess.CompletedProcess([], 1, "", "Authorization: PRIVATE")
        with patch.object(activity.shutil, "which", return_value="/fake/cdp"), \
             patch.object(activity.subprocess, "run", return_value=error) as run:
            with self.assertRaisesRegex(RuntimeError, "^CDP history unavailable$"):
                activity._cdp_query("SELECT 1", 2)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ["/fake/cdp", "data", "query", "run"])
        self.assertNotIn("shell", run.call_args.kwargs)
        self.assertIs(run.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_real_shebang_transport_finds_its_runtime_under_native_host_path(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            cdp = root / "cdp"
            cdp.write_text("#!/usr/bin/env node\nignored fake CLI input\n")
            runtime = root / "node"
            runtime.write_text(f'#!/bin/sh\nexec "{sys.executable}" -c \'print("{{\\"result\\":[{{\\"ok\\":1}}]}}")\'\n')
            cdp.chmod(0o700); runtime.chmod(0o700)
            restricted = "/usr/bin:/bin:/usr/sbin:/sbin"
            with patch.dict(os.environ, {"PATH": restricted}), patch.object(activity.shutil, "which", return_value=str(cdp)):
                self.assertEqual(activity._cdp_query("SELECT fixture", 3), [{"ok": 1}])
                self.assertEqual(os.environ["PATH"], restricted, "Child launch must not mutate the native host environment")

    def test_real_http_transport_only_posts_documented_read_methods(self):
        requests = []
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append(payload)
                body = json.dumps({"jsonrpc": "2.0", "id": 1, "result": []}).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(body)
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        try:
            with patch.object(wallet, "SOLANA_RPC", f"http://127.0.0.1:{server.server_port}"):
                result = activity.snapshot(self.settings, query=lambda *a: [])
                self.assertEqual(result["items"], [])
                with self.assertRaisesRegex(ValueError, "only history reads"):
                    activity._rpc("sendTransaction", ["never"], 1)
        finally:
            server.shutdown(); server.server_close(); worker.join(2)
        self.assertEqual([r["method"] for r in requests], ["getSignaturesForAddress"])

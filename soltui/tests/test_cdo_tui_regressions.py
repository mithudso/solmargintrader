"""Offline safety regressions for the reviewed manual paths and paper state."""
from __future__ import annotations

import io
import json
import os
import stat
import struct
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

from soltui import bots, coinbase_manual as cm, commands, config, forwardtest, live_score
from soltui import jupiter_manual as jm, native_host, native_host_install
from soltui.tests.test_bots import write_hourly, write_snapshots, tri_quotes
from soltui.tests.test_coinbase_manual import Venue
from soltui.tests.test_hdwallet import V2_M
from soltui.tests.test_jupiter_manual import MockHttpClient, OWNER, OTHER_MINT


class Isolated(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.enterContext(mock.patch.object(config, "CONFIG_DIR", self.root / "config"))
        self.enterContext(mock.patch.object(jm, "_storage_dir", return_value=self.root / "jupiter"))


class JupiterSafety(Isolated):
    def preview(self, **updates):
        p = {"product_id": "SOL-USDC", "side": "BUY", "size": "1", "size_currency": "quote"}
        return jm.order_preview(p | updates, OWNER, http_client=self.http)

    def setUp(self):
        super().setUp()
        self.http = MockHttpClient(OWNER)

    def test_submission_refuses_before_key_loading_signing_network_or_state_change(self):
        prev = self.preview()
        before = jm._preview_path(prev["preview_id"]).read_bytes()
        self.http.calls.clear()
        with mock.patch.object(jm, "load_keypair", side_effect=AssertionError("key must not be read")) as key:
            with self.assertRaisesRegex(ValueError, "economic verification"):
                jm.order_submit(prev["preview_id"], "/not-an-owner-key", OWNER, http_client=self.http)
        key.assert_not_called()
        self.assertEqual(self.http.calls, [])
        self.assertEqual(jm._preview_path(prev["preview_id"]).read_bytes(), before)

    def test_preview_truthfully_reports_structural_only_verification(self):
        prev = self.preview()
        self.assertIn("structural", prev["notice"].lower())
        self.assertFalse(prev["submission_available"])
        self.assertEqual(jm._read(jm._preview_path(prev["preview_id"]))["verification"], "structural_only")

    def test_quick_submission_refuses_before_fetching_a_preview(self):
        ctx = commands.Context.from_settings(config.Settings())
        params = {"product_id": "SOL-USDC", "side": "BUY", "size": "1",
                  "size_currency": "quote", "skip_confirm": True}
        with mock.patch.object(commands, "jupiter_order_preview", side_effect=AssertionError("no quote network")) as preview:
            with self.assertRaisesRegex(ValueError, "economic verification"):
                commands.jupiter_order_quick(ctx, params)
        preview.assert_not_called()

    def test_historical_unknowns_never_clear_on_time_alone(self):
        for signature in (None, "historical-signature"):
            with self.subTest(signature=signature):
                pid = "a" * 32
                record = {"preview_id": pid, "state": "unknown", "submit_started_at": 1}
                if signature:
                    record["signature"] = signature
                jm._save(jm._preview_path(pid), record)
                with mock.patch.object(jm.time, "time", return_value=10000), mock.patch.object(
                        self.http, "rpc", return_value={"result": {"value": [None]}}):
                    result = jm.order_reconcile(pid, http_client=self.http)
                self.assertEqual(result["state"], "unknown")
                self.assertTrue(result["unresolved"])

    def test_missing_nonfinite_zero_and_boolean_input_prices_refused_before_network(self):
        for price in (None, 0, float("nan"), float("inf"), True):
            with self.subTest(price=price), mock.patch.object(jm, "_resolve_token", side_effect=[
                {"mint": OTHER_MINT, "symbol": "BONK", "decimals": 6, "usdPrice": price},
                {"mint": jm.USDC_MINT, "symbol": "USDC", "decimals": 6, "usdPrice": 1},
            ]):
                self.http.calls.clear()
                with self.assertRaisesRegex(ValueError, "verified price"):
                    self.preview(product_id="BONK-USDC", side="SELL", size_currency="base")
                self.assertEqual(self.http.calls, [])

    def test_base_buy_converts_both_usd_prices_and_caps_input(self):
        base = {"mint": OTHER_MINT, "symbol": "BONK", "decimals": 6, "usdPrice": 2}
        quote = {"mint": jm.WSOL_MINT, "symbol": "SOL", "decimals": 9, "usdPrice": 100}
        with mock.patch.object(jm, "_resolve_token", side_effect=[base, quote]):
            prev = self.preview(product_id="BONK-SOL", size_currency="base")
        record = jm._read(jm._preview_path(prev["preview_id"]))
        self.assertEqual(record["in_amount_raw"], 20_000_000)
        with mock.patch.object(jm, "_resolve_token", side_effect=[quote, base]):
            with self.assertRaisesRegex(ValueError, "exceeds"):
                self.preview(product_id="SOL-BONK", side="SELL", size="1.01", size_currency="base")


class CoinbaseRecovery(Isolated):
    def test_only_exact_client_product_and_side_bind_unknown_submissions(self):
        for status, changed, resolves in (("FILLED", {}, True), ("OPEN", {}, False),
                ("FILLED", {"client_order_id": "unrelated"}, False),
                ("FILLED", {"client_order_id": None}, False),
                ("FILLED", {"product_id": "BTC-USDC"}, False),
                ("FILLED", {"side": "SELL"}, False)):
            with self.subTest(status=status, changed=changed):
                with tempfile.TemporaryDirectory(dir=self.root) as tmp, mock.patch.object(config, "CONFIG_DIR", Path(tmp)):
                    venue = Venue()
                    prev = cm.preview("SOL-USDC", "BUY", "2.00", "quote", venue)
                    venue.create_error = True
                    with self.assertRaises(RuntimeError):
                        cm.submit(prev["preview_id"], venue)
                    rec = cm._read(cm._path(prev["preview_id"]))
                    outcome = {"order_id": "order-1", "client_order_id": rec["client_order_id"],
                               "product_id": "SOL-USDC", "side": "BUY", "status": status} | changed
                    result = cm.status("order-1", lambda args: outcome)
                    saved = cm._read(cm._path(prev["preview_id"]))
                    self.assertEqual(result["unresolved"], not resolves)
                    if not changed:
                        self.assertEqual(saved["order_id"], "order-1")
                        self.assertEqual(saved["state"], "complete" if resolves else "pending")
                    else:
                        self.assertIsNone(saved.get("order_id"))
                    self.assertEqual(sum(c[:2] == ["orders", "create"] for c in venue.calls), 1)


class NativeSafety(unittest.TestCase):
    def test_large_metadata_cannot_make_an_oversized_fallback(self):
        for request in ({"id": "x" * native_host.MAX_REPLY_BYTES, "op": "ping"},
                        {"id": 2, "op": "call", "command": "x" * native_host.MAX_REPLY_BYTES}):
            with self.subTest(keys=list(request)), mock.patch.object(commands, "dispatch", side_effect=lambda name, *a, **k:
                    commands.error_envelope(name, "unknown_command", "unknown")):
                body = native_host.handle_request(json.dumps(request).encode())
                self.assertLessEqual(len(body), native_host.MAX_REPLY_BYTES)
                self.assertFalse(json.loads(body)["response"]["ok"])

    def test_surrogate_request_keeps_connection_alive_for_following_ping(self):
        raw = json.dumps({"id": 1, "op": "call", "command": "\ud800"}).encode()
        ping = b'{"id":2,"op":"ping"}'
        incoming = io.BytesIO(b"".join(struct.pack("<I", len(x)) + x for x in (raw, ping)))
        outgoing = io.BytesIO()
        with mock.patch.object(commands, "dispatch", side_effect=lambda name, *a, **k:
                commands.error_envelope(name, "unknown_command", "unknown")):
            native_host.serve(incoming, outgoing)
        outgoing.seek(0)
        first = json.loads(native_host.read_frame(outgoing))
        second = json.loads(native_host.read_frame(outgoing))
        self.assertFalse(first["response"]["ok"])
        self.assertTrue(second["response"]["result"]["pong"])

    def test_installer_preserves_literal_shell_special_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / 'repo $(printf ALT) `printf TICK` "quote"'
            repo.mkdir()
            python = root / 'python $(printf ALT) `printf TICK` "quote"'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "literal-interpreter"\n')
            python.chmod(0o700)
            result = subprocess.run(["/bin/sh"], input=native_host_install.wrapper_text(repo, python),
                                    text=True, capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [str(repo), "literal-interpreter"])


class PaperEvidence(Isolated):
    def test_compound_status_hash_uses_requested_and_settings_asset(self):
        ctx = commands.Context.from_settings(config.Settings(asset="BTC"))
        for params in ({"asset": "SOL", "current_only": True}, {"current_only": True}):
            asset = params.get("asset", "BTC")
            with self.subTest(asset=asset), mock.patch.object(commands.compound_mod, "load_state", return_value={"config": {"coin": asset}}) as load, mock.patch.object(
                    commands.compound_mod, "forward_status", return_value={}) as status:
                commands.compound_forward_status(ctx, params)
                load.assert_called_once_with(asset)
                from backtester.core import scorecard
                status.assert_called_once_with(asset, scorecard.config_hash({"coin": asset}))

    def test_ranking_limits_current_trials_and_binds_current_settings(self):
        path = self.root / "trials.sqlite3"
        db = forwardtest._db(path)
        with db:
            for key, label, hits, count, issued, window in (("old-a", "A", 10, 10, 100, 99),
                    ("new-a", "A", 0, 1, 200, 5), ("b", "B", 5, 6, 210, 8)):
                active = json.dumps([{"name": "sma_regime", "params": {"window": window}}])
                db.execute("INSERT INTO trial(id,asset,label,mode,minutes,cost,active) VALUES(?,'SOL',?,'all',1,1,?)", (key,label,active))
                for bar in range(count):
                    db.execute("INSERT INTO call(trial,bar,issued,start,finish,prediction,outcome) VALUES(?,?,?,?,?,1,?)",
                               (key,bar,issued+bar,bar,issued+1000,1 if bar < hits else -1))
        db.close()
        result = live_score.prediction_snapshot("SOL", now=220, limit=1, db_path=path)
        self.assertEqual([r["label"] for r in result["rows"]], ["B"])
        all_rows = {r["label"]: r for r in forwardtest.top_forward_predictions("SOL", db_path=path)}
        self.assertEqual(all_rows["A"]["settings"][0]["params"]["window"], 5)
        self.assertEqual(all_rows["A"]["resolved"], 1)

    def test_cursor_defers_future_samples_across_member_and_refresh_boundaries(self):
        root = self.root / "prices"
        start = 1_700_000_000
        write_snapshots(root, [(start, tri_quotes(start)), (start+1, tri_quotes(start+1))])
        cursor = bots.SnapshotCursor(start, root)
        first = cursor.read_new(end_ts=start)
        self.assertEqual([r[0] for r in first], [start])
        self.assertEqual(cursor.read_new(end_ts=start), [])
        write_snapshots(root, [(start+2, tri_quotes(start+2)), (start+3, tri_quotes(start+3))])
        second = cursor.read_new(end_ts=start+2)
        last = cursor.read_new(end_ts=start+4)
        self.assertEqual([r[0] for r in second], [start+1, start+2])
        fresh = bots.SnapshotCursor(start, root).read_new(end_ts=start+4)
        self.assertEqual(first + second + last, fresh)

    def test_empty_hourly_source_reports_error_and_continues_batch(self):
        data = self.root / "data"
        data.mkdir()
        (data / "EMPTY_1h.csv").write_text("timestamp,open,high,low,close,volume\n")
        write_hourly(data, "SOL", n=48)
        result = bots.backtest_many("grid", ["EMPTY", "SOL"], config.Settings(data_dir=str(data)))
        self.assertIn("EMPTY", result["errors"])
        self.assertEqual(result["ran"], 1)

    def test_concurrent_forward_updates_preserve_other_successful_bots(self):
        bots.runtime().sessions.clear()
        original_read, original_write = bots._forward_all, bots._write_json
        first_read, second_read = threading.Event(), threading.Event()
        writes = threading.Lock()
        def read():
            raw = original_read()
            if threading.current_thread().name.endswith("_0"):
                first_read.set()
                second_read.wait(0.25)
            else:
                second_read.set()
            return raw
        def write(*args):
            with writes:
                original_write(*args)
        with mock.patch.object(bots, "_triangle_products", return_value=["SOL-USD"]), mock.patch.object(
                bots, "_forward_all", side_effect=read), mock.patch.object(bots, "_write_json", side_effect=write):
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="forward-test") as pool:
                one = pool.submit(bots.forward_start, "grid", "SOL", ensure_recorder=False)
                self.assertTrue(first_read.wait(2))
                two = pool.submit(bots.forward_start, "dca", "SOL", ensure_recorder=False)
                one.result(timeout=3)
                two.result(timeout=3)
        self.assertEqual(set(original_read()), {"grid", "dca"})
        # A start racing a stop must retain both updates.
        first_read.clear(); second_read.clear()
        with mock.patch.object(bots, "_triangle_products", return_value=["SOL-USD"]), mock.patch.object(
                bots, "_forward_all", side_effect=read), mock.patch.object(bots, "_write_json", side_effect=write):
            with ThreadPoolExecutor(max_workers=2, thread_name_prefix="forward-test") as pool:
                one = pool.submit(bots.forward_start, "triangle", "ALL", ensure_recorder=False)
                self.assertTrue(first_read.wait(2))
                two = pool.submit(bots.forward_stop, "grid", now=123)
                one.result(timeout=3)
                two.result(timeout=3)
        raw = original_read()
        self.assertIn("triangle", raw)
        self.assertEqual(raw["grid"]["stopped_at"], 123)


class SettingsSafety(Isolated):
    def test_failed_save_keeps_previous_complete_file(self):
        target = self.root / "config.json"
        config.save_settings(config.Settings(asset="BTC"), target)
        before = target.read_bytes()
        original_fdopen = os.fdopen
        class FailingWriter:
            def __init__(self, *args, **kwargs):
                self.file = original_fdopen(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.file.close()
            def write(self, text):
                self.file.write(text[:10])
                raise OSError(28, "synthetic disk full")
        with mock.patch.object(config.os, "fdopen", FailingWriter), self.assertRaises(OSError):
            config.save_settings(config.Settings(asset="ETH"), target)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(config.load_settings(target).asset, "BTC")
        self.assertEqual(list(self.root.iterdir()), [target])

    def test_sensitive_replacement_is_private_before_any_write(self):
        target = self.root / "config.json"
        target.write_text("{}")
        target.chmod(0o644)
        original_fdopen = os.fdopen
        modes = []
        def checked_fdopen(fd, *args, **kwargs):
            modes.append(stat.S_IMODE(os.fstat(fd).st_mode))
            self.assertEqual(modes[-1], 0o600)
            return original_fdopen(fd, *args, **kwargs)
        with mock.patch.object(config.os, "fdopen", side_effect=checked_fdopen):
            config.save_settings(config.Settings(btc_xpub=V2_M), target)
        self.assertEqual(modes, [0o600])
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)

    def test_json_fallback_skips_yaml_only_when_parser_unavailable(self):
        yaml_path, json_path = self.root / "config.yaml", self.root / "config.json"
        yaml_path.write_text("asset: BTC\n")
        config.save_settings(config.Settings(asset="ETH"), json_path)
        with mock.patch.object(config, "CONFIG_PATH", yaml_path), mock.patch.object(config, "CONFIG_PATH_JSON", json_path), mock.patch.object(config, "_yaml", return_value=None):
            self.assertEqual(config.load_settings().asset, "ETH")
            json_path.unlink()
            with self.assertRaisesRegex(config.ConfigError, "YAML"):
                config.load_settings()

    def test_invalid_capital_cadence_and_execution_geometry_refused(self):
        for kwargs in ({"capital": float("nan")}, {"capital": float("inf")}, {"capital": True},
                {"poll_interval_seconds": float("nan")}, {"poll_interval_seconds": True},
                {"fill_delay": 1.5}, {"fill_delay": True}, {"cpcv_groups": 8.5},
                {"cpcv_groups": True}, {"cpcv_k": 1.5}, {"cpcv_k": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(config.ConfigError):
                config.validate(config.Settings(**kwargs))

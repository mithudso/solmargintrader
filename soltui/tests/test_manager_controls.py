"""Safe delegated forward controls use isolated files and never launch a recorder."""

from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from soltui import bots, commands, config
from soltui.config import Settings


def _process_control(root, params, queue):
    config.CONFIG_DIR = Path(root)
    with patch.object(bots, "_triangle_products", return_value=["SOL-USD"]):
        queue.put(bots.manager_control(settings=Settings(), **params))


class ManagerControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "config"
        self.patcher = patch.object(config, "CONFIG_DIR", self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.settings = Settings()
        self.products = patch.object(
            bots, "_triangle_products", return_value=["SOL-USD", "BTC-USD"]
        )
        self.products.start()
        self.addCleanup(self.products.stop)
        self.recorder = patch.object(
            bots.pricefeed,
            "ensure_recorder",
            side_effect=AssertionError("must not launch"),
        )
        self.recorder.start()
        self.addCleanup(self.recorder.stop)

    def snapshot(self):
        return bots.manager_snapshot(self.settings)

    def request(self, bot="grid", operation="start", **changes):
        row = next(r for r in self.snapshot()["bots"] if r["bot"] == bot)
        return {
            "bot": bot,
            "operation": operation,
            "asset": row["asset"],
            "request_id": str(uuid.uuid4()),
            "expected_session": row["session_id"],
            "expected_config_hash": row["config_hash"],
            **changes,
        }

    def control(self, **p):
        return bots.manager_control(settings=self.settings, **p)

    def test_snapshot_is_inert_and_explicit(self):
        result = self.snapshot()
        self.assertEqual(result["protocol_version"], 1)
        self.assertEqual(len(result["source_hash"]), 64)
        self.assertFalse(self.root.exists())
        self.assertIsNone(result["bots"][0]["session_id"])
        self.assertFalse(result["bots"][0]["heartbeat_available"])

    def test_malformed_present_forward_state_refuses_without_overwriting(self):
        request = self.request()
        valid = bots._new_forward_record("grid", "SOL", self.settings, 10.0)
        invalid_records = [
            None,
            [],
            False,
            {},
            {**valid, "id": ""},
            {**valid, "bot": "trend"},
            {**valid, "asset": None},
            {**valid, "config": []},
            {**valid, "config": {}},
            {**valid, "started_at": None},
            {**valid, "stopped_at": "10"},
            {**valid, "fee_bps": True},
            {**valid, "slippage_bps": -1},
        ]
        invalid_records += [
            {k: v for k, v in valid.items() if k != field} for field in valid
        ]
        documents = [
            json.dumps(value).encode()
            for value in ([], [valid], None, 1, "CANARY_SECRET", False)
        ]
        documents += [
            json.dumps({"grid": record}).encode() for record in invalid_records
        ]
        documents += [
            b'{"CANARY_SECRET":',
            b"\xffCANARY_SECRET",
            json.dumps({"grid": {**valid, "started_at": float("nan")}}).encode(),
        ]
        bots.home().mkdir(parents=True)
        for document in documents:
            with self.subTest(document=document):
                bots.forward_path().write_bytes(document)
                before = (
                    bots.forward_path().read_bytes(),
                    bots.forward_path().stat().st_mtime_ns,
                )
                with self.assertRaisesRegex(
                    bots.BotError, "^saved forward state is incompatible$"
                ):
                    self.snapshot()
                self.assertEqual(
                    before,
                    (
                        bots.forward_path().read_bytes(),
                        bots.forward_path().stat().st_mtime_ns,
                    ),
                )
                self.assertEqual(list(bots.home().iterdir()), [bots.forward_path()])
                for operation in ("start", "stop"):
                    with self.assertRaisesRegex(
                        bots.BotError, "^saved forward state is incompatible$"
                    ):
                        self.control(**{**request, "operation": operation})
                    self.assertEqual(bots.forward_path().read_bytes(), document)
                    self.assertFalse((bots.home() / "manager-requests.json").exists())
                # Only the guarded protocol is strict. Raw legacy readers retain
                # their established handling of valid non-object JSON.
                if document in (b"[]", b"null", b"1", b'"CANARY_SECRET"', b"false"):
                    self.assertEqual(bots._forward_all(), {})
                for lock in ("forward.lock", "config.lock"):
                    (bots.home() / lock).unlink(missing_ok=True)

    def test_control_rechecks_present_state_before_start_or_stop(self):
        request = self.request()
        bots.home().mkdir(parents=True)
        for document in (b"[]", b"null", b'{"grid": null}', b'{"CANARY_SECRET":'):
            for operation in ("start", "stop"):
                with self.subTest(document=document, operation=operation):
                    bots.forward_path().write_bytes(document)
                    try:
                        with self.assertRaisesRegex(
                            bots.BotError, "^saved forward state is incompatible$"
                        ):
                            self.control(**{**request, "operation": operation})
                        self.assertEqual(bots.forward_path().read_bytes(), document)
                        self.assertFalse(
                            (bots.home() / "manager-requests.json").exists()
                        )
                    finally:
                        (bots.home() / "manager-requests.json").unlink(missing_ok=True)

    def test_valid_legacy_family_record_keeps_its_exact_observed_identity(self):
        result = bots.forward_start(
            "grid", "SOL", self.settings, ensure_recorder=False, now=10.0
        )
        record = result["forward"]
        before = bots.forward_path().read_bytes()
        row = next(row for row in self.snapshot()["bots"] if row["bot"] == "grid")
        self.assertEqual(row["session_id"], record["id"])
        self.assertEqual(row["requested_state"], "running")
        self.assertEqual(bots.forward_path().read_bytes(), before)
        self.assertEqual(self.control(**self.request())["reason"], "already_running")

    def test_guarded_start_uses_exact_empty_coin_config_and_compared_costs(self):
        bots.home().mkdir(parents=True)
        bots.config_path().write_text(
            json.dumps({"grid": {"range_pct": 12}, "per_coin": {"grid": {"SOL": {}}}})
        )
        before = next(row for row in self.snapshot()["bots"] if row["bot"] == "grid")
        self.assertEqual(before["config"]["range_pct"], 15)
        request = self.request()
        # The compared values are the authority. No permissive UI getter or
        # second settings/cost resolution may change what the owner starts.
        original_record = bots._new_forward_record

        def changed_settings(*args, **kwargs):
            self.settings.fee_bps = 99
            self.settings.slippage_bps = 77
            return original_record(*args, **kwargs)

        with (
            patch.object(
                bots, "get_config", side_effect=AssertionError("config reread")
            ),
            patch.object(bots, "_new_forward_record", side_effect=changed_settings),
        ):
            response = self.control(**request)
        self.assertEqual(response["outcome"], "acknowledged")
        record = bots._forward_all()["grid"]
        self.assertEqual(record["config"], before["config"])
        self.assertEqual(record["fee_bps"], before["fee_bps"])
        self.assertEqual(record["slippage_bps"], before["slippage_bps"])
        after = next(row for row in self.snapshot()["bots"] if row["bot"] == "grid")
        self.assertEqual(after["session_config_hash"], before["config_hash"])

    def test_start_replay_and_fresh_same_session_skip_without_restart(self):
        p = self.request()
        first = self.control(**p)
        self.assertEqual(first["outcome"], "acknowledged")
        session = first["session_id"]
        self.assertEqual(self.control(**p), first)
        again = self.control(**self.request())
        self.assertEqual(
            (again["outcome"], again["reason"], again["session_id"]),
            ("skipped", "already_running", session),
        )
        self.assertEqual(bots._forward_all()["grid"]["id"], session)

    def test_cross_market_slot_and_stale_session_cannot_replace(self):
        old = self.request()
        first = self.control(**old)
        changed = self.request(asset="BTC")
        # Equal defaults on two markets do not mean two independent worker slots.
        refused = self.control(**changed)
        self.assertEqual(refused["reason"], "family_slot_occupied")
        stale = self.control(**{**old, "request_id": str(uuid.uuid4())})
        self.assertEqual(stale["reason"], "owner_session_changed")
        self.assertEqual(bots._forward_all()["grid"]["id"], first["session_id"])

    def test_expected_configuration_and_stop_session_are_atomic(self):
        stale = self.request()
        bots.save_config("grid", {"range_pct": 12}, coin="SOL")
        self.assertEqual(self.control(**stale)["reason"], "configuration_changed")
        first = self.control(**self.request())
        stop = self.request(operation="stop")
        bots.forward_start("grid", "SOL", self.settings, ensure_recorder=False)
        self.assertEqual(self.control(**stop)["reason"], "owner_session_changed")
        self.assertNotEqual(bots._forward_all()["grid"]["id"], first["session_id"])
        self.assertIsNone(bots._forward_all()["grid"]["stopped_at"])
        ack = self.control(**self.request(operation="stop"))
        self.assertEqual(ack["reason"], "stop_recorded_exposure_unknown")
        self.assertIsNotNone(bots._forward_all()["grid"]["stopped_at"])

    def test_same_request_wrong_payload_conflicts_and_pending_never_retries(self):
        p = self.request()
        first = self.control(**p)
        conflict = self.control(**{**p, "operation": "stop"})
        self.assertEqual(conflict["reason"], "request_id_conflict")
        self.assertEqual(bots._forward_all()["grid"]["id"], first["session_id"])
        # A crash after durable intent cannot be replayed, even across process state.
        q = self.request(operation="stop")
        original = bots._write_json
        calls = []

        def fail(path, body):
            calls.append(path.name)
            if path == bots.forward_path():
                raise OSError("simulated interruption")
            return original(path, body)

        with (
            patch.object(bots, "_write_json", side_effect=fail),
            self.assertRaises(OSError),
        ):
            self.control(**q)
        self.assertIn("manager-requests.json", calls)
        replay = self.control(**q)
        self.assertEqual(
            (replay["outcome"], replay["reason"]), ("unknown", "outcome_unknown")
        )
        self.assertIsNone(bots._forward_all()["grid"]["stopped_at"])
        # New IDs are not an escape hatch around an unresolved family intent.
        another = self.control(**self.request(operation="stop"))
        self.assertEqual(
            (another["outcome"], another["reason"]), ("unknown", "outcome_unknown")
        )
        self.assertIsNone(bots._forward_all()["grid"]["stopped_at"])

    def test_invalid_saved_config_never_silently_starts_default_values(self):
        bots.home().mkdir(parents=True)
        bots.config_path().write_text(json.dumps({"grid": {"range_pct": -1}}))
        with self.assertRaises(bots.BotError):
            self.snapshot()
        self.assertFalse(bots.forward_path().exists())

    def test_corrupt_owner_receipt_never_escapes_or_allows_a_replay(self):
        request = self.request()
        self.control(**request)
        path = bots.home() / "manager-requests.json"
        journal = json.loads(path.read_text())
        journal["requests"][request["request_id"]]["result"]["secret"] = "CANARY_SECRET"
        path.write_text(json.dumps(journal))
        ctx = commands.Context.from_settings(self.settings)
        envelope = commands.dispatch(
            "bots.manager_control", request, ctx=ctx, quiet=True
        )
        self.assertFalse(envelope["ok"])
        self.assertNotIn("CANARY_SECRET", json.dumps(envelope))

    def test_registered_protocol_and_old_controls_remain(self):
        self.assertTrue(commands.COMMANDS["bots.manager_snapshot"].read_only)
        self.assertFalse(commands.COMMANDS["bots.manager_control"].read_only)
        ctx = commands.Context.from_settings(self.settings)
        env = commands.dispatch("bots.manager_snapshot", {}, ctx=ctx, quiet=True)
        self.assertTrue(env["ok"])
        self.assertIn("result", env)
        request = self.request()
        envelope = commands.dispatch(
            "bots.manager_control", request, ctx=ctx, quiet=True
        )
        self.assertEqual(envelope["result"]["outcome"], "acknowledged")
        # The owner still supports its old clients' explicit restart semantics.
        before = bots._forward_all()["grid"]["id"]
        bots.forward_start("grid", "SOL", self.settings, ensure_recorder=False)
        self.assertNotEqual(bots._forward_all()["grid"]["id"], before)

    def test_competing_starts_only_one_session_and_stale_snapshot_refuses(self):
        import concurrent.futures

        requests = [self.request(), self.request()]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda p: self.control(**p), requests))
        self.assertEqual(
            sorted(r["outcome"] for r in results), ["acknowledged", "failed"]
        )
        self.assertEqual(
            next(r for r in results if r["outcome"] == "failed")["reason"],
            "owner_session_changed",
        )
        self.assertEqual(
            bots._forward_all()["grid"]["id"],
            next(r for r in results if r["outcome"] == "acknowledged")["session_id"],
        )

    def test_separate_processes_cannot_both_start_the_empty_family(self):
        import multiprocessing

        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        processes = [
            context.Process(
                target=_process_control, args=(str(self.root), self.request(), queue)
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        try:
            results = [queue.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            queue.close()
        self.assertEqual(
            sorted(r["outcome"] for r in results), ["acknowledged", "failed"]
        )
        self.assertEqual(
            next(r for r in results if r["outcome"] == "failed")["reason"],
            "owner_session_changed",
        )

    def test_cost_and_asset_context_changes_conflict_and_semantics_are_explicit(self):
        before = self.request()
        self.settings.fee_bps = 99
        self.assertEqual(self.control(**before)["reason"], "configuration_changed")
        before = self.request()
        before["asset"] = "BTC"
        self.assertEqual(self.control(**before)["reason"], "configuration_changed")
        for row in self.snapshot()["bots"]:
            self.assertEqual(row["venue"], "coinbase")
            self.assertEqual(row["mode"], "paper")
            self.assertEqual(
                row["bar_seconds"], None if row["bot"] == "triangle" else 60
            )
            self.assertIn(
                row["execution_model"], ("recorded_bid_ask", "recorded_1m_ohlc_replay")
            )

    def test_snapshot_existing_files_are_unchanged_and_owner_errors_are_sanitized(self):
        self.control(**self.request())
        before = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.snapshot()
        after = {
            p: (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.root.rglob("*")
            if p.is_file()
        }
        self.assertEqual(before, after)
        with patch.object(
            bots, "manager_snapshot", side_effect=OSError("CANARY_SECRET")
        ):
            env = commands.dispatch(
                "bots.manager_snapshot",
                {},
                ctx=commands.Context.from_settings(self.settings),
                quiet=True,
            )
        self.assertNotIn("CANARY_SECRET", json.dumps(env))
        with patch.object(
            bots, "manager_control", side_effect=OSError("CANARY_SECRET")
        ):
            env = commands.dispatch(
                "bots.manager_control",
                self.request(),
                ctx=commands.Context.from_settings(self.settings),
                quiet=True,
            )
        self.assertNotIn("CANARY_SECRET", json.dumps(env))

    def test_actual_http_owner_advertises_and_runs_atomic_protocol(self):
        import threading
        import urllib.request

        from soltui import api

        server = api.create_server(0, token="fixture-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            ctx = commands.Context.from_settings(self.settings)
            with (
                patch.object(commands.Context, "load", return_value=ctx),
                patch.object(commands, "_log_call"),
            ):

                def call(name, params=None):
                    request = urllib.request.Request(
                        f"http://127.0.0.1:{server.server_port}/v1/{name}",
                        data=None if params is None else json.dumps(params).encode(),
                        headers={
                            "Authorization": "Bearer fixture-token",
                            "Content-Type": "application/json",
                        },
                    )
                    with urllib.request.urlopen(request, timeout=5) as response:
                        return json.load(response)

                envelope = call("commands")
                self.assertEqual(set(envelope), {"ok", "command", "result", "error"})
                descriptor = next(
                    r for r in envelope["result"] if r["name"] == "bots.manager_control"
                )
                self.assertFalse(descriptor["read_only"])
                snapshot = call("bots.manager_snapshot")["result"]
                self.assertFalse(self.root.exists())
                row = next(r for r in snapshot["bots"] if r["bot"] == "grid")
                request = {
                    "bot": "grid",
                    "operation": "start",
                    "asset": "SOL",
                    "request_id": str(uuid.uuid4()),
                    "expected_session": row["session_id"],
                    "expected_config_hash": row["config_hash"],
                }
                first = call("bots.manager_control", request)["result"]
                second = call("bots.manager_control", request)["result"]
                self.assertEqual(first, second)
                self.assertEqual(first["outcome"], "acknowledged")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_receipt_file_contains_no_raw_settings_and_invalid_ids_refuse(self):
        self.control(**self.request())
        body = json.loads((bots.home() / "manager-requests.json").read_text())
        self.assertNotIn("range_pct", json.dumps(body))
        with self.assertRaises(bots.BotError):
            self.control(**self.request(request_id="invalid"))

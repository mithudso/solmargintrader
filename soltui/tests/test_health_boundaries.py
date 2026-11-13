"""Offline stream bounds and test-owner isolation; no sockets or application jobs."""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import io
import json
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


class ApiError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def isolated_api():
    """Load the real HTTP handler with an inert registry, avoiding app imports."""
    import soltui

    filename = Path(__file__).resolve().parents[1] / "api.py"
    spec = importlib.util.spec_from_file_location(
        "soltui._health_api_fixture", filename
    )
    module = importlib.util.module_from_spec(spec)
    with mock.patch.object(
        soltui, "commands", SimpleNamespace(CommandError=ApiError), create=True
    ):
        spec.loader.exec_module(module)
    return module


class HttpBodyBoundaryTests(unittest.TestCase):
    def handler(self, length, body=b"{}"):
        api = isolated_api()
        handler_type = api.make_handler("fixture")
        handler = handler_type.__new__(handler_type)
        handler.headers = {"Content-Length": str(length)}
        handler.rfile = mock.Mock(wraps=io.BytesIO(body))
        handler.close_connection = False
        handler.connection = mock.Mock()
        handler.connection.gettimeout.return_value = 7.0
        return api, handler

    def test_negative_content_length_refuses_before_any_unbounded_read(self):
        _, handler = self.handler(-1)
        with self.assertRaisesRegex(ApiError, "Content-Length"):
            handler._read_json()
        handler.rfile.read.assert_not_called()
        self.assertTrue(handler.close_connection)

    def test_oversized_refusal_has_a_strict_drain_deadline(self):
        api, handler = self.handler(2 * 1024 * 1024)
        with self.assertRaisesRegex(ApiError, "too large"):
            handler._read_json()
        self.assertGreater(2 * 1024 * 1024, api.MAX_BODY_BYTES)
        handler.rfile.read.assert_called_once_with(2 * 1024 * 1024)
        self.assertEqual(
            handler.connection.settimeout.call_args_list,
            [mock.call(0.25), mock.call(7.0)],
        )
        self.assertTrue(handler.close_connection)

    def test_oversized_refusal_survives_an_incomplete_slow_body(self):
        _api, handler = self.handler(2 * 1024 * 1024)
        handler.rfile.read.side_effect = TimeoutError("private transport canary")
        with self.assertRaisesRegex(ApiError, "too large") as result:
            handler._read_json()
        self.assertNotIn("private transport canary", result.exception.message)
        self.assertEqual(
            handler.connection.settimeout.call_args_list,
            [mock.call(0.25), mock.call(7.0)],
        )
        self.assertTrue(handler.close_connection)

    def test_declared_body_length_must_be_complete(self):
        _, handler = self.handler(100, b"{}")
        with self.assertRaisesRegex(ApiError, "incomplete"):
            handler._read_json()
        self.assertTrue(handler.close_connection)

    def test_unsupported_transfer_encoding_cannot_be_silently_ignored(self):
        _, handler = self.handler(0)
        handler.headers["Transfer-Encoding"] = "chunked"
        with self.assertRaisesRegex(ApiError, "Transfer-Encoding"):
            handler._read_json()
        handler.rfile.read.assert_not_called()
        self.assertTrue(handler.close_connection)

    def test_body_timeout_has_a_fixed_error_and_closes_connection(self):
        _, handler = self.handler(2)
        handler.rfile.read.side_effect = TimeoutError("private read canary")
        with self.assertRaisesRegex(ApiError, "unavailable") as result:
            handler._read_json()
        self.assertNotIn("private read canary", result.exception.message)
        self.assertTrue(handler.close_connection)

    def test_each_connection_has_a_header_and_body_deadline(self):
        api, handler = self.handler(2)
        with mock.patch.object(api.BaseHTTPRequestHandler, "setup") as setup:
            handler.setup()
        setup.assert_called_once()
        handler.connection.settimeout.assert_called_once_with(10.0)

    def test_legitimate_empty_object_and_invalid_json_remain_distinct(self):
        _, handler = self.handler(2)
        self.assertEqual(handler._read_json(), {})
        handler.rfile.read.assert_called_once_with(2)
        _, handler = self.handler(1, b"{")
        with self.assertRaisesRegex(ApiError, "valid JSON"):
            handler._read_json()


class TestOwnerBootstrapTests(unittest.TestCase):
    def test_inherited_owner_roots_never_become_the_suite_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = (
                "SOLTUI_CONFIG_DIR",
                "SOLTUI_LOG_DIR",
                "SOLTUI_SUPPORT_DIR",
                "SOLMARGINTRADER_STORAGE",
                "SOLBOT_HOME",
                "SOLBOT_ECOSYSTEM_HOME",
                "AERO_LP_HOME",
                "SOLMT_DATA_DIR",
                "SOLTUI_KEY_DIR",
            )
            env = dict(os.environ)
            sentinels = {}
            for name in names:
                path = root / name.lower()
                path.mkdir()
                sentinel = path / "owner-sentinel"
                sentinel.write_bytes(b"preserve owner state")
                sentinels[name] = (path, sentinel)
                env[name] = str(path)
            program = (
                "import json, os; import soltui.tests; print(json.dumps({k:os.environ[k] for k in "
                + repr(names)
                + "}))"
            )
            result = subprocess.run(
                [sys.executable, "-B", "-c", program],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            selected = json.loads(result.stdout)
            for name, (owner, sentinel) in sentinels.items():
                with self.subTest(name=name):
                    self.assertNotEqual(Path(selected[name]), owner)
                    self.assertEqual(sentinel.read_bytes(), b"preserve owner state")


def isolated_service(available=True):
    filename = Path(__file__).resolve().parents[1] / "soltui-service"
    loader = importlib.machinery.SourceFileLoader(
        "soltui_health_service_fixture", str(filename)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    if available:
        fake = ModuleType("launchd_supervisor")
        fake.__path__ = []
        fake.ServiceSpec = lambda **kwargs: SimpleNamespace(**kwargs)
        fake.atomic_write = lambda path, body: path.write_bytes(body)
        fake.render_plist = lambda spec: b"<plist/>"
        fake.manage = SimpleNamespace(
            is_loaded=lambda spec: False, reload_agent=lambda spec: True
        )
        plist = ModuleType("launchd_supervisor.plist")
        plist.plist_dict = lambda spec: {}
        with mock.patch.dict(
            sys.modules, {"launchd_supervisor": fake, "launchd_supervisor.plist": plist}
        ):
            loader.exec_module(module)
    else:
        import builtins

        real_import = builtins.__import__

        def refused(name, *args, **kwargs):
            if name.startswith("launchd_supervisor"):
                raise ImportError("fixture missing prerequisite")
            return real_import(name, *args, **kwargs)

        with mock.patch.object(builtins, "__import__", refused):
            loader.exec_module(module)
    return module


class ServiceOwnerBoundaryTests(unittest.TestCase):
    def test_failed_publish_restores_or_retains_the_only_old_bundle(self):
        for rollback_fails in (False, True):
            with self.subTest(rollback_fails=rollback_fails), tempfile.TemporaryDirectory() as directory:
                service = isolated_service()
                root = Path(directory)
                repo = root / "repo"
                repo.mkdir()
                dist = root / "dist/SolTUI.app"
                dist.mkdir(parents=True)
                (dist / "candidate").write_bytes(b"new application")
                bundle = root / "apps/SolTUI.app"
                bundle.mkdir(parents=True)
                (bundle / "preserved").write_bytes(b"installed application")
                original_rename = Path.rename
                def rename(path, target, rollback_fails=rollback_fails, original_rename=original_rename):
                    if path.name == "candidate.app" or (rollback_fails and path.name == "previous.app"):
                        raise OSError("fixture publish failure")
                    return original_rename(path, target)
                with mock.patch.multiple(service, REPO=repo, DIST_BUNDLE=dist,
                                         APPS_DIR=bundle.parent, BUNDLE=bundle), \
                        mock.patch.object(Path, "rename", rename), redirect_stdout(io.StringIO()), \
                        self.assertRaises(OSError):
                    service.install()
                if rollback_fails:
                    saved = list(bundle.parent.glob(".soltui-install-*/previous.app/preserved"))
                    self.assertEqual(len(saved), 1)
                    self.assertEqual(saved[0].read_bytes(), b"installed application")
                else:
                    self.assertEqual((bundle / "preserved").read_bytes(), b"installed application")
                    self.assertEqual(list(bundle.parent.glob(".soltui-install-*")), [])

    def test_failed_candidate_copy_preserves_the_installed_bundle(self):
        service = isolated_service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "repo"
            repo.mkdir()
            dist = root / "dist/SolTUI.app"
            dist.mkdir(parents=True)
            bundle = root / "apps/SolTUI.app"
            bundle.mkdir(parents=True)
            sentinel = bundle / "preserved"
            sentinel.write_bytes(b"installed application")
            with mock.patch.multiple(service, REPO=repo, DIST_BUNDLE=dist,
                                     APPS_DIR=bundle.parent, BUNDLE=bundle), \
                    mock.patch.object(service.shutil, "copytree", side_effect=OSError("fixture full disk")), \
                    redirect_stdout(io.StringIO()), self.assertRaises(OSError):
                service.install()
            self.assertEqual(sentinel.read_bytes(), b"installed application")

    def test_missing_supervisor_keeps_help_available_and_gives_isolated_remedy(self):
        try:
            service = isolated_service(False)
        except SystemExit as error:
            self.fail(
                "A missing prerequisite exited before argument parsing: " + str(error)
            )
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as result:
            service.main(["--help"])
        self.assertEqual(result.exception.code, 0)
        with (
            mock.patch.object(service.sys, "platform", "darwin"),
            mock.patch.object(
                service, "status", side_effect=AssertionError("service boundary")
            ),
            redirect_stderr(io.StringIO()) as error,
        ):
            self.assertEqual(service.main(["status"]), 3)
        self.assertIn("macos-launchd-supervisor", error.getvalue())
        self.assertIn("uv pip install --python", error.getvalue())
        self.assertNotIn("\n    pip install", error.getvalue())

    def test_linked_worktree_install_cannot_replace_an_existing_bundle(self):
        service = isolated_service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "linked"
            repo.mkdir()
            (repo / ".git").write_text("gitdir: fixture")
            dist = root / "dist/SolTUI.app"
            dist.mkdir(parents=True)
            (dist / "candidate").write_text("future source")
            bundle = root / "apps/SolTUI.app"
            bundle.mkdir(parents=True)
            sentinel = bundle / "owner"
            sentinel.write_bytes(b"preserved")
            with (
                mock.patch.multiple(
                    service,
                    REPO=repo,
                    DIST_BUNDLE=dist,
                    APPS_DIR=bundle.parent,
                    BUNDLE=bundle,
                    SUPPORT=root / "support",
                    LOG=root / "log",
                    AGENT=root / "agent",
                ),
                mock.patch.object(service, "reload_agent", return_value=True),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(service.install(), 1)
            self.assertEqual(sentinel.read_bytes(), b"preserved")
            self.assertFalse((root / "agent").exists())

    def test_failed_stop_remains_unconfirmed(self):
        service = isolated_service()
        with tempfile.TemporaryDirectory() as directory:
            flag = Path(directory) / "supervise.enabled"
            flag.touch()
            with (
                mock.patch.object(service, "FLAG", flag),
                mock.patch.object(
                    service,
                    "run",
                    return_value=subprocess.CompletedProcess(
                        [], 1, "", "fixture failure"
                    ),
                ),
                mock.patch.object(service, "is_loaded", return_value=True),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(service.stop(), 1)
            self.assertFalse(flag.exists())

    def test_uninstall_keeps_artifacts_until_the_job_is_proven_unloaded(self):
        for returncode in (0, 1):
            with (
                self.subTest(bootout_returncode=returncode),
                tempfile.TemporaryDirectory() as directory,
            ):
                service = isolated_service()
                root = Path(directory)
                agent = root / "agent"
                agent.write_bytes(b"preserved agent")
                bundle = root / "SolTUI.app"
                bundle.mkdir()
                sentinel = bundle / "owner"
                sentinel.write_bytes(b"preserved bundle")
                with (
                    mock.patch.multiple(service, AGENT=agent, BUNDLE=bundle),
                    mock.patch.object(service, "stop", return_value=0),
                    mock.patch.object(
                        service,
                        "run",
                        return_value=subprocess.CompletedProcess(
                            [], returncode, "", ""
                        ),
                    ),
                    mock.patch.object(service, "is_loaded", return_value=True),
                    mock.patch.object(
                        service,
                        "time",
                        SimpleNamespace(
                            monotonic=mock.Mock(side_effect=[0.0, 100.0]),
                            sleep=mock.Mock(),
                        ),
                        create=True,
                    ),
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO()),
                ):
                    self.assertEqual(service.uninstall(), 1)
                self.assertEqual(agent.read_bytes(), b"preserved agent")
                self.assertEqual(sentinel.read_bytes(), b"preserved bundle")


class ForwardIdentityBoundaryTests(unittest.TestCase):
    def test_different_signal_intervals_cannot_share_a_trial_track_record(self):
        import numpy as np

        from soltui import config, forwardtest
        from soltui.tests.test_forwardtest import BASE, candles

        timestamps = BASE + np.arange(-200, 0) * 300
        signal = {
            "ts": timestamps,
            "open": np.full(200, 100.0),
            "high": np.full(200, 102.0),
            "low": np.full(200, 99.0),
            "close": np.full(200, 101.0),
            "volume": np.ones(200),
        }
        trial = {
            "label": "same label",
            "mode": "all",
            "members": [forwardtest.member("buy_and_hold", {})],
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(config, "CONFIG_DIR", Path(directory)),
            mock.patch.object(forwardtest, "_predict", return_value=1),
        ):
            options = {
                "fetch": lambda *a, **kw: candles(0),
                "clock": lambda: BASE + 4,
                "code": "synthetic-code",
                "tune": False,
            }
            first = forwardtest.tick(
                "SOL", [trial], (1,), 16.0, signal_interval="1m", **options
            )
            second = forwardtest.tick(
                "SOL",
                [trial],
                (1,),
                16.0,
                signal_interval="5m",
                signal_fetch=lambda *a, **kw: signal,
                **options,
            )
            self.assertEqual(len(first["rows"]), 1)
            self.assertEqual(len(second["rows"]), 2)
            self.assertEqual(len({row["id"] for row in second["rows"]}), 2)
            self.assertEqual(first["recorded"], second["recorded"])

    def test_settlement_uses_the_same_retained_candles_as_its_evidence(self):
        import math
        import sqlite3

        from soltui import config, forwardtest
        from soltui.tests.test_forwardtest import BASE, candles

        trial = {
            "label": "retained input",
            "mode": "all",
            "members": [forwardtest.member("buy_and_hold", {})],
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(config, "CONFIG_DIR", Path(directory)),
            mock.patch.object(forwardtest, "_predict", return_value=1),
        ):

            def advance(minute, revised=False):
                rows = candles(minute)
                if revised:
                    target = rows["ts"] == BASE + 60
                    for field, value in (
                        ("open", 200.0),
                        ("close", 201.0),
                        ("high", 202.0),
                        ("low", 199.0),
                    ):
                        rows[field][target] = value
                return forwardtest.tick(
                    "SOL",
                    [trial],
                    (5,),
                    16.0,
                    tune=False,
                    fetch=lambda *a, **kw: rows,
                    clock=lambda: BASE + minute * 60 + 4,
                    code="synthetic-code",
                )

            advance(0)
            advance(2)
            advance(6, revised=True)
            path = config.CONFIG_DIR / "forwardtest" / "trials.sqlite3"
            with sqlite3.connect(path) as database:
                self.assertEqual(
                    database.execute(
                        "SELECT open FROM candle WHERE asset=? AND ts=?",
                        ("SOL", BASE + 60),
                    ).fetchone()[0],
                    100.0,
                )
                bps, outcome = database.execute(
                    "SELECT bps,outcome FROM call WHERE outcome IS NOT NULL"
                ).fetchone()
            self.assertAlmostEqual(bps, 10000 * math.log(102.0 / 100.0))
            self.assertEqual(outcome, 1)


class WalletReadBoundaryTests(unittest.TestCase):
    def test_unavailable_solana_balance_is_unknown_instead_of_zero(self):
        from soltui import wallet
        from soltui.tests.test_wallet import SOL_ADDR, Fake

        for value in (None, "invalid", -1, True):
            with self.subTest(value=value):
                fetch = Fake()
                fetch.lamports = value
                result = wallet.scan_solana(SOL_ADDR, fetch).to_dict()
                self.assertIsNone(result["native"])
                self.assertFalse(result["total_complete"])
                self.assertTrue(
                    any(e["source"] == "solana getBalance" for e in result["errors"])
                )

    def test_unvalued_position_prevents_a_complete_wallet_total(self):
        from soltui import wallet

        result = wallet.ChainScan("base", "synthetic owner")
        result.positions = [{"protocol": "fixture", "token_id": 1, "value_usd": None}]
        self.assertFalse(result.to_dict()["total_complete"])

    def test_paper_daemon_values_never_enter_live_wallet_totals(self):
        from soltui import wallet
        from soltui.tests.test_wallet import BASE_ADDR, Fake

        daemon = wallet.daemon_context(
            {"mode": "dry-run", "positions": [{"token_id": 1, "value_usd": 1000000.0}]},
            [],
        )
        result = wallet.scan_base(BASE_ADDR, Fake(), daemon=daemon).to_dict()
        self.assertIsNone(result["positions"][0]["value_usd"])
        self.assertFalse(result["total_complete"])

    def test_live_daemon_valuation_requires_the_requested_owner(self):
        from soltui import wallet
        from soltui.tests.test_wallet import BASE_ADDR, Fake

        for owner in (None, "0x" + "12" * 20, BASE_ADDR):
            with self.subTest(owner=owner):
                daemon = wallet.daemon_context(
                    {
                        "mode": "live",
                        "owner": owner,
                        "positions": [{"token_id": 1, "value_usd": 10.0}],
                    },
                    [],
                )
                result = wallet.scan_base(BASE_ADDR, Fake(), daemon=daemon).to_dict()
                self.assertEqual(
                    result["positions"][0]["value_usd"],
                    10.0 if owner == BASE_ADDR else None,
                )

    def test_transport_diagnostics_do_not_expose_provider_or_uri_canaries(self):
        import urllib.error

        from soltui import wallet

        fetch = wallet.HttpFetcher(retries=0)
        with (
            mock.patch.object(wallet.urllib.request, "urlopen", side_effect=urllib.error.URLError("PRIVATE_CANARY")),
            self.assertLogs("soltui.wallet", level="DEBUG") as logs,
            self.assertRaises(wallet.WalletHttpError) as failure,
        ):
            fetch("https://user:PRIVATE_CANARY@provider.invalid/read?key=PRIVATE_CANARY")
        self.assertNotIn("PRIVATE_CANARY", str(failure.exception))
        self.assertEqual([r.phase for r in logs.records], ["request", "failure"])
        self.assertTrue(all(r.exc_info is None for r in logs.records))
        self.assertNotIn("PRIVATE_CANARY", str([r.__dict__ for r in logs.records]))

    def test_response_body_has_a_size_bound_before_json_parsing(self):
        from soltui import wallet

        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b" " * 9
        with (
            mock.patch.object(wallet, "MAX_HTTP_BYTES", 8, create=True),
            mock.patch.object(wallet.urllib.request, "urlopen", return_value=response),
            self.assertRaisesRegex(wallet.WalletHttpError, "limit"),
        ):
            wallet.HttpFetcher(retries=0)("https://provider.invalid")
        response.read.assert_called_once_with(9)

    def test_rpc_error_body_is_not_returned_to_the_console(self):
        from soltui import wallet

        with self.assertRaises(wallet.WalletHttpError) as failure:
            wallet._rpc(
                lambda *_: {"error": {"message": "PRIVATE_CANARY"}},
                "https://provider.invalid",
                "getBalance",
                [],
            )
        self.assertNotIn("PRIVATE_CANARY", str(failure.exception))


class CompoundProcessBoundaryTests(unittest.TestCase):
    def test_forward_paper_metrics_use_each_recorded_calls_cost(self):
        from soltui import compound

        ledger = []
        for index, cost in enumerate((10.0, 50.0)):
            ledger.append(
                {
                    "type": "call",
                    "id": str(index),
                    "call": "UP",
                    "ungated": 1,
                    "bar_ts": index * 300,
                    "price": 100.0,
                    "round_trip_bps": cost,
                    "notional_usd": 1000.0,
                    "scores": {"fixture": 1.0},
                    "entry": 0.25,
                }
            )
            ledger.append({"type": "resolve", "id": str(index), "ret_bps": 40.0})
        with mock.patch.object(compound, "read_ledger", return_value=ledger):
            result = compound.forward_status("SOL")
        self.assertEqual(result["compound"]["net_bps_per_call_if_one_bar"], 10.0)
        self.assertEqual(
            result["compound_ungated"]["net_bps_per_call_if_one_bar"], 10.0
        )
        self.assertEqual(
            result["components"]["fixture"]["net_bps_per_call_if_one_bar"], 10.0
        )
        self.assertEqual(result["paper"]["net_usd"], 2.0)
        self.assertEqual(result["paper"]["costs_usd"], 6.0)

    def test_stale_pid_never_receives_a_stop_signal(self):
        from soltui import compound, config

        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(config, "CONFIG_DIR", Path(directory)),
            mock.patch.object(compound, "autopilot_enabled", return_value=False),
            mock.patch.object(os, "kill") as kill,
        ):
            paths = compound.unattended_paths("SOL")
            descriptor = compound._try_lock(paths["lock"])
            self.assertIsNotNone(descriptor)
            try:
                paths["pid"].write_text("424242\n")
                result = compound.stop_unattended("SOL")
                self.assertTrue(result["stopping"])
                self.assertTrue(paths["stop"].exists())
                self.assertTrue(compound.unattended_status("SOL")["running"])
                kill.assert_not_called()
            finally:
                os.close(descriptor)


class RecordedQuoteBoundaryTests(unittest.TestCase):
    def test_ticker_without_exchange_time_cannot_invent_a_fresh_quote(self):
        from soltui import pricefeed

        for stamp in (None, "", "invalid time"):
            with self.subTest(stamp=stamp):
                state = {}
                message = {
                    "type": "ticker",
                    "product_id": "SOL-USD",
                    "best_bid": "99",
                    "best_ask": "101",
                    "price": "100",
                    "time": stamp,
                }
                self.assertFalse(pricefeed.apply_ticker(state, message, 1000.0))
                self.assertEqual(state, {})

    def test_fragmented_message_has_one_total_size_budget(self):
        from soltui import pricefeed
        from soltui.tests.test_pricefeed import connected, server_frame

        first = server_frame(pricefeed.OP_TEXT, b"123456", fin=False)
        second = server_frame(pricefeed.OP_CONT, b"123456", fin=True)
        ws, _ = connected([first + second])
        with (mock.patch.object(pricefeed, "MAX_FRAME_BYTES", 10),
              self.assertRaisesRegex(pricefeed.PriceFeedError, "message.*limit")):
            ws.recv_text()
        self.assertEqual(ws._parts, [])


class ResultEvidenceBoundaryTests(unittest.TestCase):
    def test_corrupt_evidence_never_becomes_rankable(self):
        from soltui import bgqueue
        from soltui.tests.test_bgqueue import _result

        for field, value in (
            ("evaluable", "false"),
            ("median_sharpe", float("inf")),
            ("median_return", float("nan")),
            ("median_sharpe", "bad"),
        ):
            with self.subTest(field=field, value=value):
                payload = json.loads(_result().to_json())
                payload[field] = value
                row = bgqueue.JobResult.from_dict(payload)
                self.assertFalse(row.ranked_ok)
                self.assertFalse(row.evaluable)
        for value in (float("inf"), float("nan")):
            self.assertFalse(_result(median_sharpe=value).ranked_ok)

    def test_infinite_count_cannot_crash_the_result_or_state_reader(self):
        from soltui import bgqueue
        from soltui.tests.test_bgqueue import _result

        payload = json.loads(_result().to_json())
        payload["trades"] = float("inf")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text(
                json.dumps(payload) + "\n" + _result(job_id="valid").to_json() + "\n"
            )
            rows = bgqueue.read_results(path)
            self.assertEqual(
                [row.job_id for row in bgqueue.leaderboard(rows)[0]], ["valid"]
            )
            state = Path(directory) / "state.json"
            state.write_text('{"done":Infinity,"total":20}')
            self.assertEqual(bgqueue.read_state(state).done, 0)


class BrowserConsoleBoundaryTests(unittest.TestCase):
    def probe(self, host, origin=None, path="/ws"):
        from aiohttp import web
        from textual_serve.server import Server

        from soltui import serve

        observed = {"entered": False, "refused": False, "response": None}

        def exercise(server):
            async def go():
                application = await server._make_app()
                headers = {"Host": host}
                if origin is not None:
                    headers["Origin"] = origin
                request = SimpleNamespace(headers=headers, path=path)

                async def handler(request):
                    observed["entered"] = True
                    return web.Response(text="inert application handler")

                current = handler
                for middleware in reversed(application.middlewares):
                    previous = current

                    async def current(
                        request, middleware=middleware, previous=previous
                    ):
                        return await middleware(request, previous)

                try:
                    observed["response"] = await current(request)
                except web.HTTPForbidden:
                    observed["refused"] = True

            asyncio.run(go())

        with (
            mock.patch.object(Server, "serve", exercise),
            mock.patch.object(serve, "port_is_free", return_value=True),
            mock.patch.object(
                serve.webbrowser, "open", side_effect=AssertionError("no browser")
            ),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(serve.serve(port=8899, open_browser=False), 0)
        return observed

    def test_foreign_missing_and_rebound_origins_never_enter_the_app(self):
        for host, origin in (
            ("127.0.0.1:8899", "https://foreign.invalid"),
            ("127.0.0.1:8899", None),
            ("rebound.invalid:8899", "http://rebound.invalid:8899"),
        ):
            with self.subTest(host=host, origin=origin):
                observed = self.probe(host, origin)
                self.assertFalse(
                    observed["entered"],
                    "Untrusted browser reached the application handler",
                )
                self.assertTrue(observed["refused"])

    def test_same_origin_websocket_and_unframed_index_are_available(self):
        observed = self.probe("127.0.0.1:8899", "http://127.0.0.1:8899")
        self.assertTrue(observed["entered"])
        self.assertFalse(observed["refused"])
        index = self.probe("127.0.0.1:8899", path="/")
        self.assertTrue(index["entered"])
        self.assertEqual(index["response"].headers["X-Frame-Options"], "DENY")
        self.assertIn(
            "frame-ancestors 'none'",
            index["response"].headers["Content-Security-Policy"],
        )

    def test_interpreter_paths_are_shell_quoted(self):
        from soltui import serve

        with mock.patch.object(serve.sys, "executable", "/tmp/fixture env/python"):
            self.assertEqual(
                shlex.split(serve.app_command()),
                ["/tmp/fixture env/python", "-m", "soltui.tui"],
            )

    def test_incompatible_server_refuses_before_opening_or_starting(self):
        from textual_serve.server import Server

        from soltui import serve

        with (
            mock.patch.object(Server, "_make_app", None),
            mock.patch.object(Server, "serve", side_effect=AssertionError("no server")),
            mock.patch.object(
                serve.webbrowser, "open", side_effect=AssertionError("no browser")
            ),
            redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(serve.serve(port=8899), 2)


class ConsoleFailureBoundaryTests(unittest.TestCase):
    def test_coinbase_balance_rows_cannot_override_verified_portfolio_identity(self):
        from soltui import coinbase_account, config

        def call(args):
            if args[0] == "portfolios":
                return (
                    {"portfolios": [{"uuid": "verified", "name": "Verified"}]}
                    if args[1] == "list"
                    else {"portfolio": {"uuid": "verified"}}
                )
            return {
                "portfolio_id": "verified",
                "accounts": [
                    {
                        "currency": "SOL",
                        "portfolio_id": "unrelated",
                        "portfolio_name": "Unrelated",
                    }
                ],
                "has_next": False,
            }

        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(config, "CONFIG_DIR", Path(directory)),
        ):
            result = coinbase_account.sync_account(call)
        self.assertEqual(result["accounts"][0]["portfolio_id"], "verified")
        self.assertEqual(result["accounts"][0]["portfolio_name"], "Verified")

    def test_entrypoint_help_never_launches_the_gui_or_a_wallet_snapshot(self):
        from soltui import app, commands, portfolio

        for module in (app, portfolio):
            with (
                self.subTest(module=module.__name__),
                mock.patch.object(
                    app, "build_app", side_effect=AssertionError("GUI boundary")
                ),
                mock.patch.object(
                    commands,
                    "dispatch",
                    side_effect=AssertionError("Snapshot boundary"),
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as result:
                    module.main(["--help"])
                self.assertEqual(result.exception.code, 0)

    def test_failed_forward_stop_preserves_running_state(self):
        from soltui.tui import SolTuiApp

        status = mock.Mock()
        app = SimpleNamespace(
            _forward_running=True,
            _forward_busy=False,
            _call=mock.Mock(
                return_value={"ok": False, "error": {"message": "Stop unavailable"}}
            ),
            _msg=lambda env: env["error"]["message"],
            _forward_controls=mock.Mock(),
            _forward_show_running=mock.Mock(),
            query_one=lambda *args: status,
        )
        SolTuiApp._forward_stop(app)
        self.assertTrue(app._forward_running)
        self.assertIn("Stop unavailable", str(status.update.call_args))
        app._forward_show_running.assert_not_called()

    def test_requested_forward_stop_does_not_claim_the_worker_has_exited(self):
        from soltui.tui import SolTuiApp

        status = mock.Mock()
        app = SimpleNamespace(
            _forward_running=True,
            _forward_busy=False,
            _call=mock.Mock(return_value={"ok": True, "result": {"stopping": True}}),
            _forward_controls=mock.Mock(),
            _forward_show_running=mock.Mock(),
            query_one=lambda *args: status,
        )
        SolTuiApp._forward_stop(app)
        self.assertTrue(app._forward_running)
        self.assertIn("Stopping", str(status.update.call_args))
        app._forward_show_running.assert_not_called()

    def test_unexpected_registry_failures_have_fixed_diagnostics(self):
        from soltui import commands

        for failure in (OSError("PRIVATE_CANARY"), LookupError("PRIVATE_CANARY")):
            with self.subTest(kind=type(failure).__name__):
                command = commands.Command(
                    "health.fixture",
                    "Inert failure fixture",
                    mock.Mock(side_effect=failure),
                )
                with (mock.patch.dict(commands.COMMANDS, {"health.fixture": command}),
                      self.assertLogs("soltui.commands", level="WARNING") as logs):
                    result = commands.dispatch("health.fixture", {}, ctx=object(), quiet=True)
                self.assertFalse(result["ok"])
                self.assertNotIn("PRIVATE_CANARY", json.dumps(result))
                self.assertNotIn(
                    "PRIVATE_CANARY", str([r.__dict__ for r in logs.records])
                )
                self.assertEqual(logs.records[0].operation, "health.fixture")
                self.assertTrue(all(r.exc_info is None for r in logs.records))

    def test_drawdown_display_pairs_dollars_with_the_corresponding_percentage(self):
        from soltui.tui import SolTuiApp

        widgets = {}

        def widget(selector, *args):
            return widgets.setdefault(selector, mock.Mock())

        totals = {
            "net_pct_text": "paper net 0%",
            "net_usd": 0.0,
            "gross_usd": 0.0,
            "fees_usd": 0.0,
            "slippage_usd": 0.0,
            "borrow_funding_usd": 0.0,
            "realized_usd": 0.0,
            "unrealized_usd": 0.0,
            "win_rate": None,
        }
        drawdown = {
            "max_drawdown_usd": -200.0,
            "max_drawdown_pct": -0.5,
            "percent_at_max_drawdown_usd": -0.2,
            "recovered": False,
            "peak_date": "dollar peak",
            "trough_date": "dollar trough",
            "percentage_peak_date": "percent peak",
            "percentage_trough_date": "percent trough",
        }
        section = {
            "source": "paper",
            "label": "Paper",
            "notes": [],
            "status": "ok",
            "totals": totals,
            "drawdown": drawdown,
        }
        summary = {
            "window": {"label": "all", "start": None, "end": None},
            "notice": "Fixture",
            "sections": [section],
        }
        envs = {
            "pnl.summary": {"ok": True, "result": summary},
            "pnl.series": {"ok": True, "result": {"sections": []}},
            "pnl.breakdown": {"ok": True, "result": {"sections": []}},
        }
        app = SimpleNamespace(
            query_one=widget, _usd=SolTuiApp._usd, _pts=SolTuiApp._pts
        )
        SolTuiApp._render_pnl(app, envs)
        output = widgets["#pnl-summary"].update.call_args.args[0]
        self.assertIn("-200.00 (paper -20.0%", output)
        self.assertIn("max percentage drawdown", output)
        self.assertIn("-50.0%", output)
        self.assertIn("percent peak", output)


class JupiterRedirectBoundaryTests(unittest.TestCase):
    def test_authenticated_reads_refuse_redirects_without_forwarding_the_key(self):
        import urllib.request
        import urllib.response
        from email.message import Message

        from soltui import config, jupiter_manual, jupiter_tokens

        opened = []

        class FixtureHttps(urllib.request.HTTPSHandler):
            def https_open(self, request):
                opened.append((request.full_url, request.get_header("X-api-key")))
                headers = Message()
                if request.host == "api.jup.ag":
                    headers["Location"] = "https://foreign.invalid/stolen"
                    response = urllib.response.addinfourl(
                        io.BytesIO(b""), headers, request.full_url, 302
                    )
                    response.msg = "Found"
                else:
                    response = urllib.response.addinfourl(
                        io.BytesIO(b"[]"), headers, request.full_url, 200
                    )
                    response.msg = "OK"
                return response

        real_builder = urllib.request.build_opener

        def builder(*handlers):
            return real_builder(*handlers, FixtureHttps())

        baseline_opener = builder()
        for operation in ("discovery", "unsigned quote"):
            with (
                self.subTest(operation=operation),
                tempfile.TemporaryDirectory() as directory,
                mock.patch.object(config, "CONFIG_DIR", Path(directory)),
                mock.patch.dict(os.environ, {"JUPITER_API_KEY": "PRIVATE_CANARY"}),
                mock.patch.object(
                    urllib.request, "urlopen", side_effect=baseline_opener.open
                ),
                mock.patch.object(urllib.request, "build_opener", side_effect=builder),
                mock.patch.object(
                    jupiter_manual, "_get_solana_balance", return_value=1_000_000_000
                ),
            ):
                opened.clear()
                try:
                    if operation == "discovery":
                        jupiter_tokens.get("/tokens/v2/search", {"query": "SOL"})
                    else:
                        jupiter_manual.order_preview(
                            {
                                "product_id": "SOL-USDC",
                                "side": "BUY",
                                "size": "1",
                                "size_currency": "quote",
                            },
                            "EMTK62aecgScjEuZqbqeGquk8cBoQF9Z4DnxQZxn8myV",
                        )
                except (ValueError, RuntimeError):
                    pass  # Redirect refusal remains an ordinary unavailable-provider error.
                self.assertEqual(
                    len(opened),
                    1,
                    "A redirected authenticated read reached a foreign host",
                )
                self.assertEqual(opened[0][1], "PRIVATE_CANARY")


class SourceEpochBoundaryTests(unittest.TestCase):
    def test_forward_epoch_refuses_before_provider_or_evidence_admission(self):
        from soltui import forwardtest

        epoch = mock.Mock()
        epoch.verify.side_effect = RuntimeError("Source changed; restart the worker")
        with (
            mock.patch.object(forwardtest, "_SOURCE_EPOCH", epoch),
            mock.patch.object(forwardtest, "admit_read") as admission,
            mock.patch.object(forwardtest, "_db") as database,
        ):
            fetch = mock.Mock()
            with self.assertRaisesRegex(RuntimeError, "restart"):
                forwardtest.tick(
                    "SOL", [], (1,), 16.0, code="explicit future code", fetch=fetch
                )
            fetch.assert_not_called()
            admission.assert_not_called()
            database.assert_not_called()
            with self.assertRaisesRegex(RuntimeError, "restart"):
                forwardtest.revision()

    def test_mid_forecast_source_change_rolls_back_trial_and_call_evidence(self):
        import sqlite3

        from soltui import forwardtest
        from soltui.source_epoch import SourceEpochChanged
        from soltui.tests.test_forwardtest import BASE, candles

        epoch = mock.Mock()
        epoch.verify.side_effect = [
            None,
            None,
            None,
            SourceEpochChanged("restart the worker"),
        ]
        trial = {
            "label": "fixture",
            "mode": "all",
            "members": [forwardtest.member("buy_and_hold", {})],
        }
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(forwardtest, "_SOURCE_EPOCH", epoch),
            mock.patch.object(forwardtest, "_predict", return_value=1),
        ):
            path = Path(directory) / "trials.sqlite3"
            with self.assertRaisesRegex(SourceEpochChanged, "restart"):
                forwardtest.tick(
                    "SOL",
                    [trial],
                    (1,),
                    16.0,
                    code="fixture",
                    tune=False,
                    fetch=lambda *args, **kwargs: candles(0),
                    clock=lambda: BASE + 4,
                    db_path=path,
                )
            with sqlite3.connect(path) as database:
                self.assertEqual(
                    database.execute("SELECT count(*) FROM trial").fetchone()[0], 0
                )
                self.assertEqual(
                    database.execute("SELECT count(*) FROM call").fetchone()[0], 0
                )

    def test_epoch_rejects_edits_additions_deletions_and_a_different_root(self):
        from soltui.source_epoch import SourceEpoch, SourceEpochChanged

        for mutation in ("edit", "add", "delete", "different root"):
            with (
                self.subTest(mutation=mutation),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                source = root / "soltui" / "fixture.py"
                source.parent.mkdir()
                source.write_text("VALUE = 1\n")
                epoch = SourceEpoch.capture(root)
                epoch.verify(root)
                candidate = root
                if mutation == "edit":
                    source.write_text("VALUE = 2\n")
                elif mutation == "add":
                    (source.parent / "new.py").write_text("VALUE = 3\n")
                elif mutation == "delete":
                    source.unlink()
                else:
                    candidate = root / "elsewhere"
                    candidate.mkdir()
                with self.assertRaisesRegex(SourceEpochChanged, "restart"):
                    epoch.verify(candidate)

    def test_changed_startup_epoch_refuses_before_admission_or_output(self):
        from soltui import bgworker, config

        epoch = mock.Mock()
        epoch.verify.side_effect = RuntimeError("Source changed; restart the worker")
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.object(bgworker, "_SOURCE_EPOCH", epoch, create=True),
            mock.patch.object(bgworker, "ensure_dir") as ensure,
            mock.patch.object(bgworker, "admit_read") as admission,
            mock.patch.object(bgworker, "build_queue", return_value=[]),
            mock.patch.object(bgworker, "read_results", return_value=[]),
            mock.patch.object(bgworker, "verify_evaluation_proof", return_value={}),
            mock.patch.object(bgworker, "write_state") as output,
        ):
            with self.assertRaisesRegex(RuntimeError, "restart"):
                bgworker.run(
                    "SOL",
                    settings=config.Settings(),
                    results_path=Path(directory) / "results.jsonl",
                    state_path=Path(directory) / "state.json",
                )
            ensure.assert_not_called()
            admission.assert_not_called()
            output.assert_not_called()


class ExternalReadDiagnosticTests(unittest.TestCase):
    def test_account_cli_outcomes_never_log_command_output_or_arguments(self):
        from soltui import coinbase_account

        for fails in (False, True):
            with self.subTest(fails=fails), \
                    mock.patch.object(coinbase_account.Path, "is_file", return_value=False), \
                    mock.patch.object(coinbase_account.shutil, "which", return_value="fixture-cli"), \
                    mock.patch.object(coinbase_account.subprocess, "run",
                        return_value=subprocess.CompletedProcess([], 0, "{}", "PRIVATE_CANARY"),
                        side_effect=OSError("PRIVATE_CANARY") if fails else None), \
                    self.assertLogs("soltui.diagnostics", level="DEBUG") as logs:
                try:
                    coinbase_account._cli(["balance", "PRIVATE_CANARY"])
                except ValueError:
                    self.assertTrue(fails)
            self.assertEqual([r.phase for r in logs.records],
                             ["request", "failure" if fails else "success"])
            self.assertNotIn("PRIVATE_CANARY", str([r.__dict__ for r in logs.records]))

    def test_direct_market_reads_emit_fixed_request_and_outcome_events(self):
        from soltui import coinbase_account, compound, jupiter_manual, pricefeed

        reads = (
            lambda: compound.http_json("https://provider.invalid/?key=PRIVATE_CANARY"),
            lambda: compound.http_text("https://provider.invalid/?key=PRIVATE_CANARY"),
            lambda: pricefeed._get_json("https://provider.invalid/?key=PRIVATE_CANARY"),
            lambda: coinbase_account._get("https://provider.invalid/?key=PRIVATE_CANARY"),
            coinbase_account._global_instruments,
            lambda: jupiter_manual._get_rpc_account_info("https://provider.invalid/?key=PRIVATE_CANARY", "PRIVATE_CANARY"),
        )
        for read in reads:
            for fails in (False, True):
                with self.subTest(read=reads.index(read), fails=fails):
                    response = mock.MagicMock()
                    response.__enter__.return_value = response
                    response.read.return_value = b"{}"
                    with mock.patch("urllib.request.urlopen", return_value=response,
                                    side_effect=OSError("PRIVATE_CANARY") if fails else None), \
                            self.assertLogs("soltui.diagnostics", level="DEBUG") as logs:
                        try:
                            read()
                        except OSError:
                            self.assertTrue(fails)
                    self.assertEqual([r.phase for r in logs.records],
                                     ["request", "failure" if fails else "success"])
                    self.assertNotIn("PRIVATE_CANARY", str([r.__dict__ for r in logs.records]))
                    self.assertTrue(all(r.exc_info is None for r in logs.records))


if __name__ == "__main__":
    unittest.main()

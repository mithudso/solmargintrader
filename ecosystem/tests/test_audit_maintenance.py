"""Disposable regressions for accepted maintenance defects; no owner operations."""

from __future__ import annotations

import fcntl
import io
import json
import os
import plistlib
import signal
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from ecosystem import (
    cli,
    installation,
    observability,
    recovery,
    runner,
    telemetry,
    volty_forward,
    web,
)
from ecosystem.tests import test_setup as setup_fixture


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def test_multiline_environment_secret_fragments_are_redacted(self):
        log = self.home / "owner.log"
        log.write_text("prefix abc\ndef suffix\nordinary message\n")
        with patch.dict(os.environ, {"AUDIT_API_SECRET": "abc\ndef"}):
            result = observability._tail(log, 20)
        text = json.dumps(result)
        self.assertNotIn("abc", text)
        self.assertNotIn("def suffix", text)
        self.assertIn("ordinary message", text)

    def test_bootstrap_non_object_json_is_controlled(self):
        for value in ([], None, 2, "text"):
            with self.subTest(value=value):
                (self.home / "state.json").write_text(json.dumps(value))
                self.assertEqual(
                    telemetry._bootstrap(self.home)["status"], "unavailable"
                )

    def test_missing_recovery_lock_is_acquired_on_stable_inode(self):
        path = self.home / "worker.lock"
        with recovery._idle(path):
            self.assertTrue(path.is_file())
            fd = os.open(path, os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally:
                os.close(fd)
        self.assertTrue(path.is_file())
        with recovery._idle(path):
            pass

    def test_telemetry_refuses_fifo_without_blocking_open(self):
        log = self.home / "owner.log"
        os.mkfifo(log)
        definition = self.home / "service.plist"
        definition.write_bytes(plistlib.dumps({"StandardOutPath": str(log)}))
        real_open = os.open

        def guarded(path, flags, *args):
            if Path(path) == log:
                self.assertTrue(flags & os.O_NONBLOCK)
            return real_open(path, flags, *args)

        with (
            patch(
                "botmanager.service.service",
                return_value={
                    "definition_present": True,
                    "plist_path": str(definition),
                },
            ),
            patch.object(os, "open", side_effect=guarded),
        ):
            result = telemetry._logs(self.home)
        self.assertFalse(any(row["status"] == "available" for row in result["files"]))

    def test_cli_uses_saved_manager_binding_and_disabled_ui(self):
        config = {"manager_home": str(self.home / "manager"), "embedded_ui": False}
        with (
            patch.object(runner, "load", return_value={"config": config}),
            patch.object(runner, "status", return_value={}),
            patch.object(cli, "emit"),
            patch("ecosystem.ui_service.status", return_value={}) as status,
        ):
            self.assertEqual(cli.main(["status", "--home", str(self.home)]), 0)
            self.assertEqual(status.call_args.args[1], Path(config["manager_home"]))
        with (
            patch.object(runner, "load", return_value={"config": config}),
            patch.object(runner, "running", return_value=True),
            patch.object(cli, "emit") as emit,
            patch("ecosystem.ui_service.ensure") as ensure,
        ):
            self.assertEqual(cli.main(["start", "--home", str(self.home)]), 0)
            ensure.assert_not_called()
            self.assertEqual(
                emit.call_args.args[0]["data"]["ui"]["reason"], "embedded_ui_disabled"
            )

    def test_registration_failure_closes_control_worker(self):
        controls = MagicMock()
        controls.register_legacy.side_effect = RuntimeError(
            "fixture registration failure"
        )
        with (
            patch("ecosystem.control.ControlPlane", return_value=controls),
            self.assertRaises(RuntimeError),
        ):
            web.make_server(self.home, manager_home=self.home / "manager", port=0)
        controls.close.assert_called_once()

    def test_termination_reaps_group_after_leader_exits(self):
        process = MagicMock(pid=123456789)
        process.wait.return_value = 0
        with patch.object(installation.os, "killpg") as kill:
            installation._terminate(process)
        kill.assert_any_call(process.pid, signal.SIGTERM)
        kill.assert_any_call(process.pid, signal.SIGKILL)

    def test_invalid_native_candle_cannot_hide_inside_aggregate(self):
        # The first native close exceeds its high, but the second high masks it.
        rows = [
            [0, "10", "11", "9", "15", "1", 299999],
            [300000, "10", "20", "9", "10", "1", 599999],
        ]
        with (
            patch.object(
                volty_forward,
                "urlopen",
                return_value=io.BytesIO(json.dumps(rows).encode()),
            ),
            self.assertRaisesRegex(ValueError, "invalid_feed_prices"),
        ):
            volty_forward.fetch_closed("10m", None, 600)

    def test_nonfinite_stop_levels_refused_before_decision_publication(self):
        arrays = {k: np.arange(3, dtype=float) + 10 for k in volty_forward.FIELDS}
        from backtester.core.volty import VoltyConfig

        with self.assertRaisesRegex(ValueError, "seed_history_insufficient"):
            volty_forward._levels(arrays, VoltyConfig(length=32))


class InstallationMaintenanceTests(setup_fixture.SetupTests):
    def test_shipped_mjs_changes_source_fingerprint(self):
        path = self.repo / "ecosystem" / "module.mjs"
        path.write_text("export const value = 1;")
        first = installation.source_fingerprint(self.repo)
        path.write_text("export const value = 2;")
        self.assertNotEqual(first, installation.source_fingerprint(self.repo))

    def test_receipt_is_rechecked_after_lock_acquisition(self):
        self.venv.mkdir()
        expected = {
            "schema_version": 1,
            "source_fingerprint": installation.source_fingerprint(self.repo),
            "projects": installation._manifests(self.repo),
        }
        installation._write_receipt(self.venv / installation.OWNER_NAME, expected)

        @contextmanager
        def finish_during_lock(_):
            installation._write_receipt(self.venv / installation.RECEIPT_NAME, expected)
            yield

        with (
            patch.object(
                installation, "_installation_lock", side_effect=finish_during_lock
            ),
            patch.object(
                installation, "verify_environment", return_value=self.fake_health()
            ),
            patch.object(installation, "_run") as run,
        ):
            result = installation.install_environment(self.repo, self.venv)
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["reused"])
        run.assert_not_called()


class AdditionalMaintenanceTests(unittest.TestCase):
    setUp = MaintenanceTests.setUp

    def test_coin_contract_refused_before_plan_writes(self):
        for coin in ("USD", "A" * 17):
            with self.subTest(coin=coin), self.assertRaises(ValueError):
                runner.plan(
                    self.home / "pipeline",
                    coins=[coin],
                    intervals=["1d"],
                    horizons=["medium"],
                    strategies=["buy_and_hold"],
                    start="2020-01-01",
                    end="2020-02-01",
                    offline=True,
                    recorder=False,
                    manager_home=str(self.home / "manager"),
                )
        self.assertFalse((self.home / "pipeline").exists())

    def test_health_body_drip_cannot_extend_absolute_budget(self):
        import http.server
        import threading
        import time

        from ecosystem import ui_service

        class Slow(http.server.BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                for _ in range(20):
                    try:
                        self.wfile.write(b" ")
                        self.wfile.flush()
                    except OSError:
                        break
                    time.sleep(0.02)

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            before = time.monotonic()
            self.assertFalse(
                ui_service._health(
                    {"url": f"http://127.0.0.1:{server.server_port}"},
                    deadline=before + 0.07,
                )
            )
            self.assertLess(time.monotonic() - before, 0.3)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(2)

    def test_backtest_card_change_never_receipts_new_defaults(self):
        from dataclasses import replace

        from backtester.core.strategy_cards import load_all
        from ecosystem import backtests, data
        from ecosystem.tests import test_backtests as fixtures

        cards = load_all()
        card = next(c for c in cards.values() if c.registry_key == "buy_and_hold")
        path = self.home / "card.md"
        path.write_bytes(card.path.read_bytes())
        card = replace(card, path=path)

        def load(*, read_text):
            read_text(path)
            return {"fixture": card}

        original = backtests.run_backtest

        def evaluate(*args):
            result = original(*args)
            path.write_bytes(path.read_bytes() + b"\nChanged defaults snapshot\n")
            return result

        with (
            patch.object(data, "fetch_coinbase", return_value=fixtures.frame()),
            patch.object(backtests, "load_all", side_effect=load),
            patch.object(backtests, "run_backtest", side_effect=evaluate),
        ):
            receipt = data.acquire(
                "SOL", self.home / "data", start=fixtures.START, end=fixtures.END
            )
            result = backtests.backtest(
                "SOL", "buy_and_hold", receipt, self.home / "results"
            )
        self.assertEqual(result["reason"], "strategy_card_changed")
        self.assertFalse((self.home / "results").exists())

    def test_warmup_history_is_sized_from_frozen_config(self):
        from dataclasses import asdict

        from backtester.core.volty import VoltyConfig
        from ecosystem.tests import test_volty_forward as fixture

        specs = self.home / "specs.json"
        specs.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "accounts": [
                        {
                            "interval": i,
                            "paper_only": True,
                            "config": asdict(VoltyConfig(length=40)),
                        }
                        for i in volty_forward.STEPS
                    ],
                }
            )
        )
        now = 864000 + 10
        seeds = {
            i: fixture.bars(int(now // step) * step - step, count=45, step=step)
            for i, step in volty_forward.STEPS.items()
        }
        volty_forward.initialize(
            self.home / "cohort",
            specs,
            now=now,
            fetcher=lambda i, *_: seeds[i],
            clock=lambda: now,
        )
        with volty_forward.connection(self.home / "cohort") as db:
            self.assertEqual(
                db.execute("SELECT count(*) FROM decision_confirmations").fetchone()[0],
                6,
            )
            self.assertTrue(
                all(
                    np.isfinite(row[0]) and np.isfinite(row[1])
                    for row in db.execute("SELECT upper,lower FROM decisions")
                )
            )

    def test_meta_poll_crossing_deadline_never_sleeps_negative(self):
        from contextlib import nullcontext

        from ecosystem import meta_forward

        callbacks = []

        def sleep(seconds):
            self.assertGreaterEqual(seconds, 0)
            callbacks[0]()

        with (
            patch.object(meta_forward, "owner", return_value=nullcontext()),
            patch.object(
                meta_forward,
                "_tick",
                return_value={"as_of": 0, "cohort": "fixture", "counts": {}},
            ),
            patch.object(
                meta_forward.signal,
                "signal",
                side_effect=lambda _, fn: callbacks.append(fn),
            ),
            patch.object(meta_forward.time, "monotonic", side_effect=[0, 0.9, 1.1]),
            patch.object(meta_forward.time, "sleep", side_effect=sleep),
            patch("builtins.print"),
        ):
            meta_forward.run(self.home, poll=1)

    def test_wiki_fixture_ignores_inherited_git_template(self):
        from ecosystem.tests import test_wiki

        template = self.home / "unsafe-template"
        template.mkdir()
        (template / "owner-canary").write_text("must not copy")
        fixture = test_wiki.WikiTests(
            "test_page_preserves_exact_text_hash_and_commit_provenance"
        )
        before = dict(os.environ)
        with patch.dict(
            os.environ,
            {
                "GIT_TEMPLATE_DIR": str(template),
                "GIT_CONFIG_GLOBAL": str(self.home / "inherited-config"),
            },
        ):
            fixture.setUp()
            try:
                self.assertFalse((fixture.repo / ".git/owner-canary").exists())
                fixture.test_page_preserves_exact_text_hash_and_commit_provenance()
            finally:
                fixture.doCleanups()
        self.assertEqual(dict(os.environ), before)

    def test_published_candidate_uses_one_pointer_snapshot(self):
        from ecosystem import votes
        from ecosystem import zec_forward as z
        from ecosystem.tests import test_zec_forward

        fixture = test_zec_forward.ZecForwardTests(
            "test_candidate_display_uses_own_forecasts_without_changing_publication"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.initialize()
        fixture.next(fixture.now, fixture.now + 61)
        fixture.next(fixture.now + 60, fixture.now + 121)
        ui = self.home / "ui"
        z.publish(fixture.home, ui)
        selected = fixture.value["selected"][1]["candidate_id"]
        original = z.report

        def replace_pointer(*args, **kwargs):
            snapshot = original(*args, **kwargs)
            (ui / "zec-study.json").write_text(
                json.dumps(
                    {
                        "home": str(self.home / "unrelated"),
                        "selection_hash": "different",
                    }
                )
            )
            return snapshot

        with patch.object(z, "report", side_effect=replace_pointer):
            view = votes.report(
                ui, "ZEC/USDT", strategy=selected, now=fixture.now + 121
            )
        self.assertEqual(view["selected_experiment"]["publication"]["id"], selected)
        self.assertNotEqual(
            view["reason"], "selected_study_unavailable"
        ) if "reason" in view else None

    def test_report_queries_share_read_transaction_during_concurrent_commit(self):
        import sqlite3

        from ecosystem import zec_forward as z
        from ecosystem.tests import test_zec_forward

        fixture = test_zec_forward.ZecForwardTests(
            "test_exact_canonical_continuation_no_warmup_fills_and_next_open_only"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.initialize()
        fixture.next(fixture.now, fixture.now + 61)
        fixture.next(fixture.now + 60, fixture.now + 121)
        before = z.report(fixture.home, now=fixture.now + 121)
        path = fixture.home / "zec-forward.sqlite3"
        # Ask the actual connection for its path rather than infer owner layout.
        original = z.connection
        with original(fixture.home, write=True) as db:
            path = Path(db.execute("PRAGMA database_list").fetchone()[2])
        with sqlite3.connect(path) as db:
            db.execute("PRAGMA journal_mode=WAL")
        wrote = []

        @contextmanager
        def intercept(home, **kwargs):
            with original(home, **kwargs) as db:

                class Proxy:
                    def execute(self, sql, args=()):
                        if sql.startswith("SELECT * FROM forecasts") and not wrote:
                            wrote.append(True)
                            with sqlite3.connect(path) as writer:
                                current = writer.execute(
                                    "SELECT * FROM forecasts ORDER BY bar DESC LIMIT 1"
                                ).fetchone()
                                writer.execute(
                                    "INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?,?)",
                                    (
                                        current[0],
                                        current[1] + 60,
                                        current[2] + 60,
                                        current[3] + 60,
                                        current[4],
                                        20000,
                                        current[6],
                                        current[7],
                                        current[8],
                                    ),
                                )
                                writer.execute(
                                    "UPDATE candidates SET last_ts=last_ts+60 WHERE id=?",
                                    (current[0],),
                                )
                        return db.execute(sql, args)

                yield Proxy()

        with patch.object(z, "connection", side_effect=intercept):
            actual = z.report(fixture.home, now=fixture.now + 121)
        self.assertTrue(wrote)
        self.assertEqual(actual["accounts"], before["accounts"])
        self.assertEqual(actual["history"], before["history"])

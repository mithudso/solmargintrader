"""F5 UI orchestration uses mocked batches and never launches a real sweep."""
import asyncio
import unittest
from unittest import mock

from textual.widgets import TabbedContent

from soltui.tests.test_tui import TEST_SIZE, make_settings, offline_console_reads
from soltui.tui import SolTuiApp


def envelope(result):
    return {"ok": True, "result": result, "error": None}


async def settle_batch(app, pilot):
    """Wait for the requested batch worker and its UI completion callback."""
    async with asyncio.timeout(10):
        await pilot.pause()
        while True:
            workers = [worker for worker in app.workers if worker.group == "all-market-batch"]
            if not workers:
                return
            for worker in workers:
                await worker.wait()

class BatchUiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(offline_console_reads())

    async def test_start_status_stop_recover_and_fresh(self):
        app = SolTuiApp(make_settings())
        state = {"runs": [], "running": False}
        calls = []
        original = app._call
        def call(name, params=None, **kwargs):
            if not name.startswith("batch."):
                return original(name, params, **kwargs)
            p = params or {}
            calls.append((name, dict(p)))
            if name == "batch.list":
                return envelope({"runs": [{"run_id": rid, "running": state["running"]} for rid in state["runs"]]})
            if name == "batch.create":
                rid = f"run-{len(state['runs']) + 1}"
                state["runs"].insert(0, rid)
                return envelope({"run_id": rid})
            if name == "batch.start":
                state["running"] = True
                return envelope({"run_id": p["run_id"]})
            if name == "batch.stop":
                state["running"] = False
                return envelope({"run_id": p["run_id"], "stopping": True})
            if name == "batch.cells":
                return envelope({"rows": [{"state": p["state"], "asset": "ETH", "interval": "1m",
                                           "strategy": "rsi", "horizon": "short", "reason": "sample"}]})
            return envelope({"run_id": p["run_id"], "phase": "backtesting" if state["running"] else "stopped",
                             "running": state["running"], "counts": {"failed": 1, "missing": 1, "unsupported": 1},
                             "total": 3, "current": "SOL 1m", "problems": [{"state": "missing", "asset": "SOL",
                             "interval": "1m", "strategy": "rsi", "horizon": "short", "reason": "no bars"}],
                             "forward_checks": [{"asset":"SOL", "interval":"1m", "error":"feed unavailable"}],
                             "forward_backlog": {"pending": 2}, "log": "/tmp/mock-batch-worker.log"})
        with mock.patch.object(app, "_call", side_effect=call):
            async with app.run_test(size=TEST_SIZE) as pilot:
                await settle_batch(app, pilot)
                await pilot.press("f5")
                await settle_batch(app, pilot)
                self.assertEqual(app._batch_id, "run-1")
                self.assertEqual(sum(n == "batch.create" for n, _ in calls), 1)
                self.assertEqual(sum(n == "batch.start" for n, _ in calls), 1)
                logs = app._test_logs[app._batch_log_key]["text"]
                self.assertIn("missing=1", logs)
                self.assertIn("no bars", logs)
                self.assertIn("unsupported: ETH", logs)
                self.assertIn("failed: ETH", logs)
                self.assertIn("feed unavailable", logs)
                app._batch_request("fresh")
                await settle_batch(app, pilot)
                self.assertEqual(sum(n == "batch.create" for n, _ in calls), 1)
                app.query_one(TabbedContent).active = "tab-backtest"
                await pilot.pause()
                app._batch_status_pressed()
                await settle_batch(app, pilot)
                self.assertIn("run-1", app._test_logs[app._batch_log_key]["text"])
                app._batch_stop_pressed()
                await settle_batch(app, pilot)
                self.assertIn(("batch.stop", {"run_id": "run-1"}), calls)
                app._batch_resume_pressed()
                await settle_batch(app, pilot)
                self.assertTrue(state["running"])
                app._batch_stop_pressed()
                await settle_batch(app, pilot)
                app._batch_fresh_pressed()
                await settle_batch(app, pilot)
                self.assertEqual(app._batch_id, "run-2")
                self.assertEqual(state["runs"], ["run-2", "run-1"])
        # A new UI instance finds an existing worker without creating or starting one.
        recovered = SolTuiApp(make_settings())
        before = len(calls)
        with mock.patch.object(recovered, "_call", side_effect=call):
            async with recovered.run_test(size=TEST_SIZE) as pilot:
                await settle_batch(recovered, pilot)
                self.assertEqual(recovered._batch_id, "run-2")
                self.assertFalse(any(n in ("batch.create", "batch.start") for n, _ in calls[before:]))

    async def test_slow_create_does_not_block_and_failed_start_retains_run(self):
        import threading
        app = SolTuiApp(make_settings())
        entered, release = threading.Event(), threading.Event()
        finished, timed_out = threading.Event(), threading.Event()
        calls = []
        original = app._call
        def call(name, params=None, **kwargs):
            if not name.startswith("batch."):
                return original(name, params, **kwargs)
            calls.append(name)
            if name == "batch.list":
                return envelope({"runs": []})
            if name == "batch.create":
                entered.set()
                if not release.wait(30):
                    timed_out.set()
                finished.set()
                return envelope({"run_id": "created-1"})
            if name == "batch.start":
                return {"ok": False, "error": {"message": "start refused"}}
            return envelope({"run_id": "created-1", "phase": "planned", "running": False, "counts": {}})
        try:
            with mock.patch.object(app, "_call", side_effect=call):
                async with app.run_test(size=TEST_SIZE) as pilot:
                    await pilot.pause(.3)
                    app.action_batch_everything()
                    for _ in range(20):
                        if entered.is_set():
                            break
                        await pilot.pause(.05)
                    self.assertTrue(entered.is_set())
                    app.query_one(TabbedContent).active = "tab-forwardtest"
                    await pilot.pause()
                    self.assertEqual(app.query_one(TabbedContent).active, "tab-forwardtest")
                    # CDO-2464451480: the UI switched while create is still held,
                    # not after a synchronous call merely timed out.
                    self.assertFalse(timed_out.is_set())
                    self.assertFalse(finished.is_set())
                    self.assertFalse(release.is_set())
                    self.assertTrue(app._batch_busy)
                    app.action_batch_everything()
                    self.assertEqual(calls.count("batch.create"), 1)
                    release.set()
                    await pilot.pause(.4)
                    self.assertEqual(app._batch_id, "created-1")
                    self.assertIn("start refused", app._test_logs[app._batch_log_key]["text"])
        finally:
            release.set()


class BatchRegistryTests(unittest.TestCase):
    def test_commands_dispatch_to_backend_without_real_workers(self):
        from soltui import commands, f5_batch
        ctx = commands.Context.from_settings(make_settings(), commands.Runtime())
        run_id = "a" * 32
        with mock.patch.object(f5_batch, "create", return_value={"run_id": run_id}) as create, \
             mock.patch.object(f5_batch, "start", return_value={"run_id": run_id}) as start, \
             mock.patch.object(f5_batch, "status", return_value={"run_id": run_id}) as status, \
             mock.patch.object(f5_batch, "stop", return_value={"run_id": run_id}) as stop:
            self.assertTrue(commands.dispatch("batch.create", {}, ctx=ctx, quiet=True)["ok"])
            for name in ("batch.start", "batch.status", "batch.stop"):
                self.assertTrue(commands.dispatch(name, {"run_id": run_id}, ctx=ctx, quiet=True)["ok"])
            create.assert_called_once_with(ctx.settings)
            start.assert_called_once_with(run_id)
            status.assert_called_once_with(run_id)
            stop.assert_called_once_with(run_id)

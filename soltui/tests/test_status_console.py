"""Status views reconnect to each job without taking over unrelated editor work."""
from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from textual.widgets import Button, TabbedContent, TextArea

from soltui import bgqueue
from soltui.tests.test_tui import TEST_SIZE, make_settings
from soltui.tui import SolTuiApp


class StatusConsoleTests(unittest.IsolatedAsyncioTestCase):
    async def test_every_test_surface_has_a_status_button(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            for name in app._TEST_STATUS:
                self.assertEqual(app.query_one(f"#{name}", Button).label.plain, "Test status")

    async def test_reopen_after_navigation_keeps_concurrent_logs(self):
        app = SolTuiApp(make_settings())
        with TemporaryDirectory() as d, mock.patch.object(bgqueue, "BG_DIR", Path(d)):
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                first = app._start_log("Compound backtest", "SOL starting")
                second = app._start_log("Compound backtest", "BTC starting")
                app._append_log(first, "SOL halfway")
                app._append_log(second, "BTC halfway")
                app._show_preview("other", "other content")
                app._set_editor_open(False, persist=False)
                app._open_test_status(Button.Pressed(app.query_one("#status-compound-backtest", Button)))
                view = app.query_one("#docs-view", TextArea)
                self.assertTrue(app.query_one("#editor-panel").display)
                self.assertIn("SOL halfway", view.text)
                self.assertIn("BTC halfway", view.text)
                app.query_one(TabbedContent).active = "tab-strategies"
                await pilot.pause()
                app._show_preview("other", "other content")
                app.query_one(TabbedContent).active = "tab-compound"
                app._open_test_status(Button.Pressed(app.query_one("#status-compound-backtest", Button)))
                app._append_log(first, "SOL finished")
                app._refresh_open_test_status()
                self.assertIn("SOL finished", view.text)
                self.assertIn("BTC halfway", view.text)

    async def test_missing_worker_log_is_explained_without_starting_work(self):
        app = SolTuiApp(make_settings())
        with TemporaryDirectory() as d, mock.patch.object(bgqueue, "BG_DIR", Path(d)):
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                original = app._call
                with mock.patch.object(app, "_call", side_effect=lambda name, *a, **k:
                        {"ok": True, "result": {"summary": "Stopped"}} if name == "queue.progress"
                        else original(name, *a, **k)) as called:
                    app._open_test_status(Button.Pressed(app.query_one("#status-queue", Button)))
                self.assertIn("Worker log unavailable", app.query_one("#docs-view", TextArea).text)
                self.assertTrue(all(call.args[0] != "queue.start" for call in called.call_args_list))

    async def test_status_does_not_discard_unsaved_editor_text(self):
        app = SolTuiApp(make_settings())
        async with app.run_test(size=TEST_SIZE) as pilot:
            await pilot.pause()
            view = app.query_one("#docs-view", TextArea)
            app._docs_current_path = "/tmp/my-unsaved-file"
            app._docs_loaded_text = "before"
            view.read_only = False
            view.text = "unsaved text"
            app._open_test_status(Button.Pressed(app.query_one("#status-compound-backtest", Button)))
            self.assertEqual(view.text, "unsaved text")
            self.assertIn("unsaved", str(app.query_one("#docs-view-status").content))

    async def test_previous_worker_log_stops_following_before_a_new_run(self):
        from soltui import bgcontrol
        from soltui.backtest_log import BacktestLog
        app = SolTuiApp(make_settings())
        with TemporaryDirectory() as d:
            path = Path(d) / "worker.log"
            path.write_text("earlier\n")
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                key = app._start_log("Strategy backtest", "first", BacktestLog(path))
                with path.open("a") as out:
                    out.write("first completed\n")
                with mock.patch.object(bgcontrol, "is_running", return_value=False):
                    app._close_finished_worker_logs()
                with path.open("a") as out:
                    out.write("second run\n")
                app._poll_backtest_log()
                self.assertIn("first completed", app._test_logs[key]["text"])
                self.assertNotIn("second run", app._test_logs[key]["text"])

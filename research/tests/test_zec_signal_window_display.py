"""Ended signal windows distinguish elapsed and observed time."""

import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from textual.widgets import Static

from research.tests.test_zec_tui import Client
from research.zec_tui import OracleWinnersApp, ended_signal_window_text
from research.zec_tui_source import DataSession, QuoteReader
from research.zec_tui_stream import DisabledStream


class EndedSignalWindowDisplayTest(unittest.TestCase):
    def test_elapsed_time_does_not_imply_sustained_observations(self):
        text = ended_signal_window_text({"reason": "stale", "start_ms": 1000,
                                         "last_ms": 15000, "duration_ms": 16000,
                                         "sustained": False})
        self.assertIn("elapsed 16.0s", text)
        self.assertIn("observed 14.0s", text)
        self.assertIn("not sustained 15s", text)

    def test_missing_evidence_is_unavailable(self):
        text = ended_signal_window_text({"reason": "stale", "duration_ms": 16000})
        self.assertIn("observed unavailable", text)
        self.assertIn("sustained status unavailable", text)


class SignalLoaderWiringTest(unittest.IsolatedAsyncioTestCase):
    async def test_quote_reader_uses_default_shared_status_and_renders_six_horizons(self):
        now = int(time.time() * 1000)
        horizons = {str(h): {"scores": {"up": 0.6, "down": 0.3, "flat": 0.1},
                             "direction": "UP", "samples": 3}
                    for h in (60, 300, 600, 900, 1200, 3600)}
        snapshot = {"now_ms": now, "assets": {"ZEC": {"fresh": True,
                    "as_of_ms": now, "expires_at_ms": now + 60000,
                    "quote": {"price": 100}, "horizons": horizons}}}

        class FixtureFeed:
            def poll(self):
                return None

        with tempfile.TemporaryDirectory() as directory, patch(
            "oracle_leverage.signals.status", return_value=snapshot
        ) as status:
            app = OracleWinnersApp(
                settings_path=Path(directory) / "view.json",
                data_loader=DataSession(Client()),
                quote_loader=QuoteReader(feed=FixtureFeed()),
                stream=DisabledStream(),
            )
            async with app.run_test(size=(150, 52)) as pilot:
                deadline = time.monotonic() + 5
                while app.signal_result is None:
                    self.assertLess(time.monotonic(), deadline)
                    await pilot.pause(0.05)
                app.paint_shared_signals()
                rendered = app.query_one("#shared-signals", Static).render().plain
                status.assert_called()
                for horizon in horizons:
                    self.assertIn(f"{horizon}s", rendered)
                self.assertIn("● live", rendered)

    async def test_explicit_signal_loader_never_calls_default(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "oracle_leverage.signals.status", side_effect=AssertionError("unexpected default")
        ) as status:
            app = OracleWinnersApp(
                settings_path=Path(directory) / "view.json",
                data_loader=DataSession(Client()),
                quote_loader=QuoteReader(feed=type("Feed", (), {"poll": lambda self: None})()),
                stream=DisabledStream(),
                signal_loader=lambda request, cancelled: {"assets": {}},
            )
            async with app.run_test(size=(150, 52)) as pilot:
                deadline = time.monotonic() + 5
                while app.signal_result is None:
                    self.assertLess(time.monotonic(), deadline)
                    await pilot.pause(0.05)
                status.assert_not_called()

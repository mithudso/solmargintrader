"""Event identities, silent startup, optional preferences and real child cleanup."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from research.tests.test_zec_tui_alerts import START, context, snapshot
from research.tests.test_zec_tui_model import original
from research.zec_tui_alerts import bearish_alert
from research.zec_tui_model import WorkingSet
from research.zec_tui_notifications import (
    AFPLAY,
    SYSTEM_SOUND,
    NotificationEvents,
    SoundPlayer,
    sound_settings,
)

ENABLED = {"reversal": True, "two_up": True, "backend": "bell"}


def raw_context(now, *, uu=False):
    shift = int(now // 600) * 600 - START
    saved = context(now - shift, uu=uu)
    saved["rows"] = {
        t + shift: {**bar, "ts": t + shift} for t, bar in saved["rows"].items()
    }
    saved["end"] += shift
    saved["calculated_at"] += shift
    return saved


def frame(now, *, uu=False, price=101, trade=True):
    saved = raw_context(now, uu=uu)
    current = snapshot(now, price)
    current["connected"] = trade
    return bearish_alert(saved, current, now)


class EventIdentities(unittest.TestCase):
    def test_invalid_history_does_not_prime_then_existing_conditions_are_silent(self):
        tracker = NotificationEvents()
        self.assertEqual(
            tracker.observe({"error": "missing"}, ENABLED, START + 303), ()
        )
        self.assertIsNone(tracker.start_window)
        self.assertEqual(
            tracker.observe(
                frame(START + 303, uu=True, price=99), ENABLED, START + 303
            ),
            (),
        )
        for price in (101, 99, 99):
            self.assertEqual(
                tracker.observe(
                    frame(START + 304, uu=True, price=price), ENABLED, START + 304
                ),
                (),
            )
        self.assertEqual(
            tracker.observe(
                frame(START + 903, uu=True, price=99), ENABLED, START + 903
            ),
            ("two_up", "reversal"),
        )

    def test_startup_missing_quote_is_unknown_not_a_false_reversal_baseline(self):
        tracker = NotificationEvents()
        tracker.observe(frame(START + 303, trade=False), ENABLED, START + 303)
        self.assertFalse(tracker.reversal_ready)
        self.assertEqual(
            tracker.observe(frame(START + 304, price=99), ENABLED, START + 304), ()
        )
        self.assertTrue(tracker.reversal_ready)
        self.assertEqual(
            tracker.observe(frame(START + 305, price=101), ENABLED, START + 305), ()
        )
        self.assertEqual(
            tracker.observe(frame(START + 306, price=99), ENABLED, START + 306), ()
        )

    def test_before_midpoint_is_known_false_then_real_later_reversal_can_ring(self):
        tracker = NotificationEvents()
        tracker.observe(frame(START + 100, price=99, trade=False), ENABLED, START + 100)
        self.assertTrue(tracker.reversal_ready)
        self.assertEqual(
            tracker.observe(frame(START + 303, price=99), ENABLED, START + 303),
            ("reversal",),
        )
        for price, trade in ((101, True), (99, False), (99, True)):
            self.assertEqual(
                tracker.observe(
                    frame(START + 304, price=price, trade=trade), ENABLED, START + 304
                ),
                (),
            )

    def test_muted_events_and_quiet_configuration_changes_never_backfill(self):
        tracker = NotificationEvents()
        tracker.observe(frame(START + 100), sound_settings(), START + 100)
        self.assertEqual(
            tracker.observe(
                frame(START + 303, price=99), sound_settings(), START + 303
            ),
            (),
        )
        self.assertEqual(
            tracker.observe(
                frame(START + 304, price=99), ENABLED, START + 304, quiet=True
            ),
            (),
        )
        self.assertEqual(
            tracker.observe(frame(START + 305, price=99), ENABLED, START + 305), ()
        )
        tracker.observe(
            frame(START + 903, uu=True, price=99), ENABLED, START + 903, quiet=True
        )
        self.assertEqual(
            tracker.observe(
                frame(START + 904, uu=True, price=99), ENABLED, START + 904
            ),
            (),
        )
        tracker.observe(
            {"error": "history_unavailable"}, ENABLED, START + 1503, quiet=True
        )
        self.assertEqual(
            tracker.observe(
                frame(START + 1504, uu=True, price=99), ENABLED, START + 1504
            ),
            (),
        )
        self.assertEqual(
            tracker.observe(
                frame(START + 2103, uu=True, price=99), ENABLED, START + 2103
            ),
            ("two_up", "reversal"),
        )

    def test_two_up_uses_valid_closed_setup_without_a_fresh_trade(self):
        tracker = NotificationEvents()
        tracker.observe(frame(START + 303), ENABLED, START + 303)
        actual = frame(START + 603, uu=True, trade=False)
        self.assertEqual(actual["data_status"], "trade_unavailable")
        self.assertEqual(tracker.observe(actual, ENABLED, START + 603), ("two_up",))
        self.assertEqual(
            tracker.observe(frame(START + 604, uu=True), ENABLED, START + 604), ()
        )

    def test_cache_is_bounded_and_old_targets_or_clock_rollback_do_not_replay(self):
        tracker = NotificationEvents()
        tracker.observe(frame(START + 303), ENABLED, START + 303)
        for offset in range(1, 301):
            now = START + 303 + offset * 600
            self.assertEqual(
                tracker.observe(frame(now, uu=True, price=99), ENABLED, now),
                ("two_up", "reversal"),
            )
        self.assertLessEqual(len(tracker.seen), 256)
        self.assertEqual(
            tracker.observe(
                frame(START + 903, uu=True, price=99), ENABLED, START + 903
            ),
            (),
        )
        latest = START + 303 + 300 * 600
        self.assertEqual(
            tracker.observe(frame(latest - 600, uu=True, price=99), ENABLED, latest), ()
        )


class Preferences(unittest.TestCase):
    def test_old_preferences_remain_quiet_and_explicit_save_roundtrips_sounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            state = WorkingSet([original()])
            state.save(path)
            old = json.loads(path.read_text())
            old.pop("sounds")
            path.write_text(json.dumps(old))
            state.sounds = dict(ENABLED)
            state.load(path)
            self.assertEqual(state.sounds, sound_settings())
            state.sounds = {**ENABLED, "backend": "macos"}
            self.assertNotIn("sounds", json.loads(path.read_text()))
            state.save(path)
            restored = WorkingSet([original()])
            restored.load(path)
            self.assertEqual(restored.sounds, state.sounds)

    def test_invalid_sound_options_do_not_mutate_current_view(self):
        for bad in (
            {"reversal": 1},
            {"two_up": "yes"},
            {"backend": "shell"},
            {"command": "anything"},
            [],
            None,
        ):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "view.json"
                state = WorkingSet([original()])
                state.save(path)
                data = json.loads(path.read_text())
                data["sounds"] = bad
                data["refresh"] = 250
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    state.load(path)
                self.assertEqual(state.refresh, 10)
                self.assertEqual(state.sounds, sound_settings())


class Playback(unittest.TestCase):
    def setUp(self):
        self.preflight = patch(
            "research.zec_tui_notifications.Path.is_file", return_value=True
        )
        self.preflight.start()
        self.addCleanup(self.preflight.stop)
        self.children, self.arguments = [], []

    def player(self, code, timeout=2):
        def child(argv, **kwargs):
            self.arguments.append(argv)
            process = subprocess.Popen([sys.executable, "-c", code], **kwargs)
            self.children.append(process)
            return process

        player = SoundPlayer(popen=child, timeout=timeout)
        self.addCleanup(player.close)
        return player

    def finished(self, player):
        deadline = time.monotonic() + 4
        while player.alive:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        return player.poll()

    def test_success_is_off_thread_fixed_argv_and_no_overlap_or_backlog(self):
        player = self.player("import time; time.sleep(.15)")
        self.assertTrue(player.play())
        self.assertFalse(player.play())
        result = self.finished(player)
        self.assertIsNone(result["error"])
        self.assertEqual(self.arguments, [[AFPLAY, SYSTEM_SOUND]])
        self.assertEqual(len(self.children), 1)
        self.assertIsNone(player.poll())

    def test_nonzero_stderr_is_bounded_and_failure_never_retries_itself(self):
        player = self.player("import os, sys; os.write(2,b'x'*100000); sys.exit(7)")
        player.play()
        result = self.finished(player)
        self.assertIn("exit 7", result["error"])
        self.assertEqual(len(result["stderr"]), 4096)
        self.assertEqual(len(self.children), 1)
        self.assertIsNone(player.poll())
        self.assertTrue(player.play())  # Only an explicit new request retries.
        self.finished(player)
        self.assertEqual(len(self.children), 2)

    def test_timeout_and_exit_cancel_reap_real_owned_children(self):
        player = self.player("import time; time.sleep(30)", timeout=0.1)
        player.play()
        self.assertIn("timed out", self.finished(player)["error"])
        self.assertIsNotNone(self.children[-1].poll())
        player = self.player("import time; time.sleep(30)")
        player.play()
        deadline = time.monotonic() + 2
        while len(self.children) < 2:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.01)
        player.close()
        self.assertFalse(player.alive)
        self.assertIsNotNone(self.children[-1].poll())
        self.assertFalse(player.play())
        self.assertIsNone(player.poll())

    def test_missing_system_backend_reports_once_without_launch(self):
        player = self.player("pass")
        with patch("research.zec_tui_notifications.Path.is_file", return_value=False):
            player.play()
            self.assertIn("unavailable", self.finished(player)["error"])
        self.assertEqual(self.children, [])


if __name__ == "__main__":
    unittest.main()

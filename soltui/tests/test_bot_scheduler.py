from __future__ import annotations

import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
import subprocess

from soltui import bot_scheduler as sched


class BotSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_independent_coins_default_no_global_adoption_and_next_run(self):
        calls = []
        def optimize(bot, settings, **kw):
            calls.append((bot, kw["coins"], kw["adopt"]))
            kw["progress"](.5, "testing")
            return {"status": "completed", "verdict": {"adopted": False}}
        with patch.object(sched.bots, "PER_COIN_OPTIMIZE_ADOPTION_SAFE", False, create=True):
            result = sched.run_cycle(root=self.root, settings=object(), coins=["SOL", "BTC"], optimizer=optimize, now=lambda: 100.)
        self.assertEqual(result, {"pending": 0, "failed": 0})
        self.assertEqual(len(calls), 5)
        self.assertTrue(all(not call[2] for call in calls))
        self.assertEqual({tuple(c[1]) for c in calls if c[1]}, {("SOL",), ("BTC",)})
        st = sched.status(root=self.root)
        self.assertEqual(st["next_run"], 100 + sched.DEFAULT_INTERVAL)
        self.assertEqual(st["last_result"], "completed")
        self.assertEqual(st["progress"]["message"], "testing")

    def test_capability_limits_promotion_to_coin_bots(self):
        calls = []
        def optimize(bot, settings, **kw):
            calls.append((bot, kw["adopt"]))
            return {"status": "completed"}
        with patch.object(sched.bots, "PER_COIN_OPTIMIZE_ADOPTION_SAFE", True, create=True):
            sched.run_cycle(root=self.root, settings=object(), coins=["SOL"], optimizer=optimize)
        self.assertEqual(dict(calls), {"dca": True, "grid": True, "triangle": False})

    def test_failure_does_not_abort_other_items(self):
        def optimize(bot, settings, **kw):
            if bot == "grid":
                raise RuntimeError("missing bars")
            return {"status": "completed"}
        r = sched.run_cycle(root=self.root, settings=object(), coins=["SOL"], optimizer=optimize)
        self.assertEqual(r["failed"], 1)
        st = sched.status(root=self.root)
        self.assertEqual(st["last_result"], "partial")
        self.assertIn("missing bars", next(x["error"] for x in st["items"] if x["bot"] == "grid"))
        self.assertEqual(sum(x["state"] == "completed" for x in st["items"]), 2)

    def test_stop_at_boundary_and_resume_remaining(self):
        calls = []
        def stop_first(bot, settings, **kw):
            calls.append(bot)
            sched.stop(root=self.root)
            return {"status": "completed"}
        first = sched.run_cycle(root=self.root, settings=object(), coins=["SOL"], optimizer=stop_first)
        self.assertEqual(first["pending"], 2)
        with closing(sched._db(self.root)) as db, db:
            sched._set(db, stop_requested=False)
        def resume(bot, settings, **kw):
            calls.append(bot)
            return {"status": "completed"}
        second = sched.run_cycle(root=self.root, settings=object(), coins=["DIFFERENT"], optimizer=resume)
        self.assertEqual(second["pending"], 0)
        self.assertEqual(sorted(calls), ["dca", "grid", "triangle"])
        self.assertFalse(any(x["coin"] == "DIFFERENT" for x in sched.status(root=self.root)["items"]))

    def test_missing_coins_and_lock_liveness(self):
        sched.run_cycle(root=self.root, settings=object(), coins=[], optimizer=lambda *a, **k: {"status": "completed"})
        self.assertEqual(sched.status(root=self.root)["last_result"], "partial")
        fd = sched._lock(self.root)
        self.addCleanup(lambda: __import__("os").close(fd))
        self.assertTrue(sched.status(root=self.root)["running"])
        with self.assertRaises(RuntimeError):
            sched.start(root=self.root)

    def test_interrupted_and_invalid_interval(self):
        with closing(sched._db(self.root)) as db, db:
            sched._set(db, phase="running")
        self.assertEqual(sched.status(root=self.root)["phase"], "interrupted")
        with self.assertRaises(ValueError):
            sched.start(root=self.root, interval_seconds=0)

    def test_watchdog_resumes_enabled_and_never_restarts_after_stop(self):
        with closing(sched._db(self.root)) as db, db:
            sched._set(db, enabled=True, interval_seconds=3600, next_run=123)
        with patch.object(sched, "_start", return_value={}) as start:
            sched.watchdog(root=self.root)
            start.assert_called_once_with(3600, self.root)
            sched.stop(root=self.root)
            sched.watchdog(root=self.root)
            start.assert_called_once()
        self.assertFalse(sched.status(root=self.root)["enabled"])

    def test_watchdog_plist_is_dedicated_and_conflicts_are_refused(self):
        import plistlib
        with patch.object(sched.sys, "platform", "darwin"), patch.dict(sched.os.environ, {"SOLTUI_LAUNCHAGENTS_DIR": str(self.root)}), \
             patch.object(sched.subprocess, "run", side_effect=[subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]) as run:
            sched._install_watchdog(self.root)
            spec = plistlib.loads(sched._plist_path().read_bytes())
            self.assertEqual(spec["Label"], sched.LABEL)
            self.assertEqual(spec["StartInterval"], 300)
            self.assertEqual(run.call_count, 2)
            spec["Label"] = "someone.else"
            sched._plist_path().write_bytes(plistlib.dumps(spec))
            with self.assertRaisesRegex(RuntimeError, "differs"):
                sched._install_watchdog(self.root)

    def test_start_failure_disables_recovery(self):
        with patch.object(sched, "_install_watchdog"), patch.object(sched.subprocess, "Popen", side_effect=OSError("spawn failed")):
            with self.assertRaisesRegex(OSError, "spawn failed"):
                sched.start(root=self.root)
        self.assertFalse(sched.status(root=self.root)["enabled"])


if __name__ == "__main__":
    unittest.main()

"""Shared paper producer ownership, priority requests and detached lifetime."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from soltui import commands, config, forwardtest, prediction_recovery as recovery


class PredictionRecovery(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(patch.object(config, "CONFIG_DIR", self.root))
        self.ctx = commands.Context.from_settings(config.Settings(), commands.Runtime())
        self.plan = {"asset": "SOL", "assets": ["SOL", "ETH", "BTC"], "horizons": (1, 5, 10, 30),
                     "trials": [{"label": "hold", "mode": "all", "members": [forwardtest.member("buy_and_hold", {})]}],
                     "cost": 17.25, "code": "saved-evidence-revision", "tune": False, "execution": None}

    def lease(self):
        owner = recovery.acquire(self.plan, "test")
        self.assertIsNotNone(owner)
        self.addCleanup(owner.finish)
        return owner

    def test_health_is_read_only_for_missing_state(self):
        before = list(self.root.iterdir())
        result = commands.dispatch("forwardtest.health", {"asset": "SOL"}, ctx=self.ctx, quiet=True)
        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["state"], "stopped")
        self.assertTrue(result["result"]["can_start"])
        self.assertEqual(list(self.root.iterdir()), before)

    def test_existing_owner_is_reused_and_priority_requests_are_deduplicated(self):
        owner = self.lease()
        owner.update(state="running", current_asset="ETH", busy=True)
        with patch.object(recovery.subprocess, "Popen") as spawn:
            first = recovery.ensure("SOL", lambda: self.fail("Must reuse the existing owner"))
            second = recovery.ensure("SOL", lambda: self.fail("Must reuse the existing owner"))
        self.assertEqual(recovery.pending_assets(), ["SOL"])
        self.assertTrue(first["queued"])
        self.assertEqual(first["current_asset"], "ETH")
        self.assertTrue(second["running"])
        self.assertFalse(second["can_start"])
        self.assertGreater(second["cooldown_seconds"], 0)
        spawn.assert_not_called()
        recovery.ensure("ETH", lambda: self.fail("Must reuse the existing owner"))
        self.assertEqual(recovery.pending_assets(), ["SOL"], "The current asset must not queue itself again")

    def test_start_race_holds_one_lease_before_spawn_and_preserves_saved_plan(self):
        forwardtest.save_session(self.plan)
        inherited = []
        gate = threading.Barrier(8)

        class Child:
            def wait(self):
                return 0

        def spawn(*args, **kwargs):
            inherited.append(os.dup(kwargs["pass_fds"][0]))
            return Child()

        def ensure(_):
            gate.wait(5)
            return recovery.ensure("SOL", lambda: self.fail("The saved plan must be reused"))

        try:
            with patch.object(recovery.subprocess, "Popen", side_effect=spawn) as start:
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(ensure, range(8)))
            self.assertEqual(start.call_count, 1)
            self.assertTrue(all(result["running"] for result in results))
            actual = forwardtest.load_session()
            self.assertEqual(actual["assets"], self.plan["assets"])
            for key in ("trials", "horizons", "cost", "execution", "tune"):
                self.assertEqual(actual[key], self.plan[key])
            self.assertEqual(actual["code"], forwardtest.revision())
        finally:
            for descriptor in inherited:
                os.close(descriptor)

    def test_paused_marker_blocks_automatic_recovery_and_restore(self):
        forwardtest.save_session(self.plan)
        recovery.remember(self.plan)
        commands.forwardtest_stop(self.ctx, {})
        with patch.object(recovery.subprocess, "Popen") as spawn:
            for _ in range(3):
                result = commands.forwardtest_ensure(self.ctx, {"asset": "SOL"})
                self.assertEqual(result["state"], "paused")
                self.assertTrue(result["can_start"])
            self.assertEqual(commands.forwardtest_restore(self.ctx, {}), {"restored": False, "paused": True})
        spawn.assert_not_called()
        self.assertEqual(recovery.saved_plan()["cost"], self.plan["cost"])

    def test_launch_failure_is_visible_and_throttled_but_manual_start_can_retry(self):
        forwardtest.save_session(self.plan)
        recovery.pause(self.plan)
        with patch.object(recovery.subprocess, "Popen", side_effect=OSError("fixture launch failed")) as spawn:
            result = commands.forwardtest_ensure(self.ctx, {"asset": "SOL", "manual": True})
            self.assertEqual(result["state"], "failed")
            self.assertIn("fixture launch failed", result["last_error"])
            self.assertFalse(result["paused"])
            self.assertTrue(result["can_start"])
            self.assertGreater(result["cooldown_seconds"], 0)
            commands.forwardtest_ensure(self.ctx, {"asset": "SOL"})
            self.assertEqual(spawn.call_count, 1)
            commands.forwardtest_ensure(self.ctx, {"asset": "SOL", "manual": True})
            self.assertEqual(spawn.call_count, 2)

    def test_unlocked_stale_pid_does_not_count_as_a_running_owner(self):
        recovery._write("producer.json", {"pid": os.getpid(), "state": "running", "last": {}})
        result = recovery.health("SOL")
        self.assertEqual(result["state"], "failed")
        self.assertFalse(result["running"])
        self.assertTrue(result["can_start"])

    def test_legacy_console_prevents_a_second_producer(self):
        with patch.object(recovery, "_legacy_owner", return_value={"pid": 123, "kind": "legacy_console"}), patch.object(
                recovery.subprocess, "Popen") as spawn:
            result = recovery.ensure("SOL", lambda: self.plan, manual=True)
        self.assertEqual(result["state"], "failed")
        self.assertFalse(result["can_start"])
        self.assertIn("existing console", result["message"])
        spawn.assert_not_called()

    def test_registered_console_is_exempt_only_while_live_and_identity_matches(self):
        with patch.object(recovery, "_process_identity", return_value="fixture-start-identity"):
            handle = recovery.register_console()
            try:
                self.assertTrue(recovery._registered_console(os.getpid()))
                # An upgraded console is safe for another client to coexist
                # with even when the shared prediction producer is stopped.
                process_list = subprocess.CompletedProcess([], 0, stdout=f"{os.getpid()} python -m soltui.tui\n")
                with patch.object(recovery.config, "CONFIG_DIR", Path.home() / ".config" / "soltui"), patch.object(
                        recovery.subprocess, "run", return_value=process_list), patch.object(
                        recovery.os, "getpid", return_value=os.getpid() + 1), patch.object(
                        recovery, "_registered_console", return_value=True) as registered:
                    self.assertIsNone(recovery._legacy_owner())
                    registered.assert_called_once()
                with patch.object(recovery, "_process_identity", return_value="reused-pid-new-start"):
                    self.assertFalse(recovery._registered_console(os.getpid()))
            finally:
                handle.close()
            self.assertFalse(recovery._registered_console(os.getpid()), "A stale marker is not a live registration")

    def test_hung_held_owner_is_reported_without_starting_another_writer(self):
        owner = self.lease()
        with owner.lock:
            owner.metadata.update(heartbeat_at=time.time() - 120, state="running")
            recovery._write("producer.json", owner.metadata)
        with patch.object(recovery.subprocess, "Popen") as spawn:
            result = recovery.ensure("SOL", lambda: self.plan)
        self.assertEqual(result["state"], "failed")
        self.assertTrue(result["running"])
        self.assertFalse(result["can_start"])
        spawn.assert_not_called()

    def test_selected_coin_preempts_remaining_queue_without_parallel_ticks(self):
        owner = self.lease()
        runtime = self.ctx.runtime
        runtime.forward_owner = owner
        runtime.forward_plan = self.plan
        seen = []
        active = 0

        def tick(asset, *args, **kwargs):
            nonlocal active
            active += 1
            self.assertEqual(active, 1)
            seen.append(asset)
            if asset == "SOL":
                result = recovery.ensure("BTC", lambda: self.fail("Do not replace the owner"))
                self.assertTrue(result["queued"])
                self.assertEqual(result["current_asset"], "SOL")
            active -= 1
            return {"bar": 1, "recorded": 1, "message": "fixture"}

        with patch.object(forwardtest, "tick", side_effect=tick):
            commands._forward_check_all(runtime, self.plan)
        self.assertEqual(seen, ["SOL", "BTC", "ETH"])
        self.assertEqual(recovery.pending_assets(), [])
        self.assertEqual(set(recovery.health("SOL")["last"]), set(self.plan["assets"]))

    def test_remote_stop_cancels_current_work_and_releases_lease(self):
        forwardtest.save_session(self.plan)
        recovery.remember(self.plan)
        runtime = self.ctx.runtime
        runtime.forward_plan = self.plan
        runtime.forward_owner = recovery.acquire(self.plan, "test")
        entered = threading.Event()

        def tick(asset, *args, stop, **kwargs):
            entered.set()
            if not stop.wait(5):
                self.fail("The remote pause must reach the running job")
            raise RuntimeError("Forwardtest stopped")

        with patch.object(forwardtest, "tick", side_effect=tick), patch.object(commands, "FORWARD_GRACE_S", 0):
            worker = threading.Thread(target=commands._forward_owned_runner, args=(runtime,))
            runtime.forward_thread = worker
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                other = commands.Context.from_settings(config.Settings(), commands.Runtime())
                result = commands.forwardtest_stop(other, {})
                self.assertTrue(result["stopping"])
            finally:
                recovery.pause(self.plan)
                runtime.forward_stop.set()
                worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(recovery.health("SOL")["running"])
        self.assertEqual(recovery.health("SOL")["state"], "paused")
        self.assertIsNone(forwardtest.load_session())
        self.assertEqual(recovery.saved_plan()["trials"], self.plan["trials"])

    def test_new_coin_is_added_between_checks_without_replacing_plan(self):
        forwardtest.save_session(self.plan)
        owner = self.lease()
        runtime = self.ctx.runtime
        runtime.forward_owner, runtime.forward_plan = owner, self.plan
        queued = recovery.ensure("ADA", lambda: self.fail("Do not replace the current plan"))
        self.assertTrue(queued["queued"])
        self.assertNotIn("ADA", queued["assets"], "Coverage is not claimed before the owner applies the request")
        with patch.object(forwardtest, "tick", return_value={"bar": 1, "recorded": 1, "message": "fixture"}) as tick:
            commands._forward_check_all(runtime, self.plan)
        self.assertEqual(tick.call_args_list[0].args[0], "ADA")
        actual = forwardtest.load_session()
        self.assertEqual(actual["assets"], ["SOL", "ETH", "BTC", "ADA"])
        self.assertEqual(actual["trials"], self.plan["trials"])
        self.assertEqual(actual["cost"], 17.25)
        self.assertIn("ADA", recovery.health("ADA")["assets"])

    def test_pinned_snapshot_refuses_another_coin_with_or_without_owner(self):
        pinned = {**self.plan, "assets": ["SOL"], "source": {"backtest_context": "immutable-fixture"}}
        forwardtest.save_session(pinned)
        with patch.object(recovery.subprocess, "Popen") as spawn:
            refused = recovery.ensure("ETH", lambda: self.fail("Preserve the pinned plan"), manual=True)
            self.assertEqual(refused["state"], "failed")
            self.assertFalse(refused["can_start"])
            self.assertIn("pinned to SOL", refused["message"])
            owner = recovery.acquire(pinned, "test")
            try:
                self.assertIsNotNone(owner)
                refused = recovery.ensure("ETH", lambda: self.fail("Preserve the pinned plan"))
                self.assertFalse(refused["queued"])
                self.assertFalse(refused["can_start"])
                self.assertEqual(recovery.pending_assets(), [])
            finally:
                owner.finish()
        spawn.assert_not_called()
        self.assertEqual(forwardtest.load_session()["source"], pinned["source"])

    def test_worker_failure_releases_ownership_and_records_failure(self):
        runtime = self.ctx.runtime
        runtime.forward_plan = self.plan
        runtime.forward_owner = recovery.acquire(self.plan, "test")
        with patch.object(commands, "_forward_runner", side_effect=RuntimeError("fixture worker failed")):
            commands._forward_owned_runner(runtime)
        result = recovery.health("SOL")
        self.assertEqual(result["state"], "failed")
        self.assertTrue(result["can_start"])
        self.assertFalse(result["running"])
        self.assertIn("fixture worker failed", result["last_error"])

    def test_other_runtime_cannot_run_restore_or_manual_tick_over_a_held_owner(self):
        forwardtest.save_session(self.plan)
        self.lease()
        self.assertFalse(commands.forwardtest_restore(self.ctx, {})["restored"])
        self.ctx.runtime.forward_plan = self.plan
        with patch.object(forwardtest, "tick") as tick:
            for name in ("forwardtest.run", "forwardtest.tick"):
                result = commands.dispatch(name, {}, ctx=self.ctx, quiet=True)
                self.assertFalse(result["ok"], result)
        tick.assert_not_called()
        self.assertEqual(forwardtest.load_session()["cost"], self.plan["cost"])

    def test_fallback_plan_uses_current_roster_and_saved_simulation_settings(self):
        captured = []

        def inspect(asset, fallback, *, manual=False):
            captured.append(fallback())
            return {"state": "starting"}

        with patch.object(recovery, "ensure", side_effect=inspect):
            result = commands.forwardtest_ensure(self.ctx, {"asset": "ETH"})
        self.assertEqual(result["state"], "starting")
        self.assertEqual(captured[0]["assets"], ["ETH"])
        self.assertEqual(len(captured[0]["trials"]), len(self.ctx.roster))
        self.assertEqual(captured[0]["execution"]["leverage"], self.ctx.settings.leverage)

    def test_actual_detached_worker_survives_short_lived_caller_and_stops_cooperatively(self):
        forwardtest.save_session(self.plan)
        fixture = self.root / "python-fixture"
        fixture.mkdir()
        # Only the external market-data boundary is replaced. The spawned
        # service, scheduler, SQLite writes, inherited lease and stop are real.
        (fixture / "sitecustomize.py").write_text('''\
import numpy as np
from soltui import commands, compound
commands.FORWARD_GRACE_S = 0
def candles(asset, *, now, **kwargs):
    ts = (int(now) // 60 - 200 + np.arange(200)) * 60
    prices = np.full(200, 100.)
    return dict(ts=ts, open=prices, high=prices, low=prices, close=prices, volume=np.ones(200))
compound.fetch_closed_candles = candles
''', encoding="utf-8")
        environment = {**os.environ, "SOLTUI_CONFIG_DIR": str(self.root),
                       "PYTHONPATH": os.pathsep.join([str(fixture), str(recovery.REPO)])}
        caller = [sys.executable, "-c", "import json; from soltui import commands; "
                  "print(json.dumps(commands.dispatch('forwardtest.ensure', {'asset':'SOL'}, quiet=True)))"]
        try:
            result = subprocess.run(caller, env=environment, cwd=recovery.REPO, capture_output=True,
                                    text=True, timeout=10, check=True)
            self.assertTrue(json.loads(result.stdout)["ok"], result.stdout)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                status = recovery.health("SOL")
                if status["running"] and status["owner"]["pid"] != os.getpid() and status["last"].get("SOL"):
                    break
                time.sleep(.05)
            else:
                self.fail(f"Detached producer did not survive its caller: {recovery.health('SOL')}")
            self.assertEqual(status["owner"]["kind"], "detached")
            self.assertEqual(status["last"]["SOL"]["recorded"], 4)
            self.assertTrue(forwardtest.status("SOL"))
            # A second short-lived client reuses the existing process.
            second = subprocess.run(caller, env=environment, cwd=recovery.REPO, capture_output=True,
                                    text=True, timeout=10, check=True)
            shared = json.loads(second.stdout)["result"]
            self.assertEqual(shared["owner"]["pid"], status["owner"]["pid"])
        finally:
            recovery.pause(self.plan)
            deadline = time.monotonic() + 10
            while recovery.health("SOL")["running"] and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(recovery.health("SOL")["running"], "The isolated detached child must stop")


if __name__ == "__main__":
    unittest.main()

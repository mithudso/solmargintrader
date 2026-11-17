"""Run ownership and local triangle inventory use isolated evidence and no transport."""

from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from soltui import config, pricefeed
from soltui import experiment_jobs as jobs
from soltui import experiment_runner as runner
from soltui.experiments import ExperimentError, ExperimentStore


class ExperimentOwnershipResumeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.enterContext(patch.object(config, "CONFIG_DIR", self.root / "config"))
        self.store = ExperimentStore(self.root / "authority")
        self.run = self.store.create_run(
            {"source": "native", "bot": "grid", "candidates": [{}]}
        )
        self.store.update_run(self.run, status="running")

    def test_status_retains_native_exclusion_through_reconciliation(self):
        reading = threading.Event()
        release = threading.Event()
        original = self.store.get_run
        calls = []

        def read(run_id):
            if not calls:
                calls.append(True)
                reading.set()
                if not release.wait(3):
                    raise AssertionError("status barrier timed out")
            return original(run_id)

        with (
            patch.object(self.store, "get_run", side_effect=read),
            ThreadPoolExecutor(max_workers=1) as pool,
        ):
            status = pool.submit(jobs.status, self.store, self.run)
            try:
                self.assertTrue(reading.wait(3))
                with (
                    self.assertRaisesRegex(ExperimentError, "active worker"),
                    runner._lock(self.store, "run:" + self.run),
                ):
                    pass
            finally:
                release.set()
            self.assertEqual(status.result(timeout=3)["status"], "interrupted")

    def test_status_never_settles_a_live_direct_runner(self):
        with runner._lock(self.store, "run:" + self.run):
            value = jobs.status(self.store, self.run)
        self.assertTrue(value["worker_active"])
        self.assertEqual(value["status"], "running")

    def test_old_reaper_cannot_interrupt_a_live_direct_runner(self):
        old = Mock()
        old.wait.return_value = 1
        with runner._lock(self.store, "run:" + self.run):
            jobs._reap(old, self.store, self.run)
        self.assertEqual(self.store.get_run(self.run)["status"], "running")

    def test_triangle_preview_without_recorded_products_never_fetches_or_writes_cache(
        self,
    ):
        with (
            patch.object(pricefeed, "read_latest", return_value=None),
            patch.object(runner, "_recorded_hours", return_value=iter(())),
            patch.object(pricefeed, "_get_json", return_value=[]) as transport,
            patch.object(pricefeed, "_atomic_write") as write,
        ):
            result = runner.preview_experiment(
                "triangle", space={}, windows=2, store=self.store
            )
        transport.assert_not_called()
        write.assert_not_called()
        self.assertFalse(result["ready"])
        self.assertEqual(result["products"], [])
        self.assertIn("recorded", " ".join(result["skipped"].values()).lower())

    def test_triangle_products_are_bound_to_recorded_metadata(self):
        products = ["ETH-USD", "BTC-USD", "ETH-BTC"]
        chunks = [
            [
                (
                    3600 + index * 3600 + k,
                    {p: [1, 1, 1, 1, 1, 3600 + index * 3600 + k] for p in products},
                )
                for k in range(65)
            ]
            for index in range(2)
        ]
        with (
            patch.object(pricefeed, "read_latest", return_value={"products": products}),
            patch.object(runner, "_recorded_hours", side_effect=lambda: iter(chunks)),
            patch.object(
                pricefeed, "_get_json", side_effect=AssertionError("no transport")
            ),
            patch.object(
                pricefeed, "_atomic_write", side_effect=AssertionError("no cache write")
            ),
        ):
            first = runner._triangle_windows(2)
            second = runner._triangle_windows(2)
        self.assertEqual(first, second)
        self.assertEqual(set(first[3]), set(products))
        self.assertEqual(len(first[0]), 2)

    def test_status_observes_blocked_direct_runner_as_active(self):
        from contextlib import nullcontext

        run_id = self.store.create_run(
            {
                "source": "native",
                "bot": "grid",
                "candidates": [{}],
                "windows": [{"coin": "SOL", "split": "train", "start": 1, "end": 10}],
            }
        )
        evaluating = threading.Event()
        release = threading.Event()

        def evaluate(*_):
            evaluating.set()
            if not release.wait(3):
                raise AssertionError("direct evaluation barrier timed out")
            return False

        with (
            patch.object(runner, "optimizer_lease", return_value=nullcontext()),
            patch.object(runner, "_check_context", return_value=None),
            patch.object(runner, "_evaluate", side_effect=evaluate),
            patch.object(runner, "_report", return_value={}),
            patch.object(runner, "_publish", return_value={}),
            ThreadPoolExecutor(max_workers=1) as pool,
        ):
            direct = pool.submit(runner.run_experiment, run_id, store=self.store)
            try:
                self.assertTrue(evaluating.wait(3))
                status = jobs.status(self.store, run_id)
                self.assertTrue(status["worker_active"])
                self.assertEqual(status["status"], "running")
            finally:
                release.set()
            direct.result(timeout=3)

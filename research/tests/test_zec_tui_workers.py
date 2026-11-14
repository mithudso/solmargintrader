"""Event-coordinated cancellation, coalescing and teardown without live I/O."""

from __future__ import annotations

import threading
import time
import unittest

from research.zec_tui_workers import LatestWorker, WorkerResult


class LatestWorkerTests(unittest.TestCase):
    def make_worker(self, loader, release=None):
        worker = LatestWorker(loader, name="oracle-worker-test")

        def cleanup():
            if release is not None:
                release.set()
            worker.close(timeout=1)

        self.addCleanup(cleanup)
        return worker

    def wait_result(self, worker) -> WorkerResult:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            result = worker.poll()
            if result is not None:
                return result
            threading.Event().wait(0.001)
        self.fail("worker result did not arrive")

    def test_success_is_delivered_once_with_generation(self):
        worker = self.make_worker(lambda request, cancelled: request * 2)
        generation = worker.submit(7)
        result = self.wait_result(worker)
        self.assertEqual(result, WorkerResult(generation=generation, value=14))
        self.assertEqual(worker.generation, generation)
        self.assertIsNone(worker.poll())

    def test_pending_requests_coalesce_and_only_one_loader_runs(self):
        entered, release = threading.Event(), threading.Event()
        calls, cancelled_states, active, peak = [], [], 0, 0
        guard = threading.Lock()

        def loader(request, cancelled):
            nonlocal active, peak
            with guard:
                active += 1
                peak = max(peak, active)
                calls.append(request)
            try:
                if request == 1:
                    entered.set()
                    if not release.wait(2):
                        raise TimeoutError("test coordination timed out")
                    cancelled_states.append(cancelled())
                return request
            finally:
                with guard:
                    active -= 1

        worker = self.make_worker(loader, release)
        worker.submit(1)
        self.assertTrue(entered.wait(2))
        worker.submit(2)
        latest = worker.submit(3)
        release.set()
        result = self.wait_result(worker)
        self.assertEqual(result, WorkerResult(generation=latest, value=3))
        self.assertEqual(calls, [1, 3])
        self.assertEqual(peak, 1)
        self.assertEqual(cancelled_states, [True])

    def test_request_is_deepcopied_before_editor_can_mutate_it(self):
        entered, release = threading.Event(), threading.Event()

        def loader(request, cancelled):
            entered.set()
            if not release.wait(2):
                raise TimeoutError("test coordination timed out")
            return request

        worker = self.make_worker(loader, release)
        request = {"members": [{"period": 14}]}
        worker.submit(request)
        self.assertTrue(entered.wait(2))
        request["members"][0]["period"] = 45
        release.set()
        self.assertEqual(self.wait_result(worker).value, {"members": [{"period": 14}]})

    def test_superseded_error_cannot_override_a_newer_request(self):
        entered, release = threading.Event(), threading.Event()

        def loader(request, cancelled):
            if request == "old":
                entered.set()
                if not release.wait(2):
                    raise TimeoutError("test coordination timed out")
                raise RuntimeError("old provider secret and path")
            return request

        worker = self.make_worker(loader, release)
        worker.submit("old")
        self.assertTrue(entered.wait(2))
        generation = worker.submit("current")
        release.set()
        self.assertEqual(
            self.wait_result(worker),
            WorkerResult(generation=generation, value="current"),
        )
        self.assertIsNone(worker.poll())

    def test_failure_is_sanitized_and_worker_recovers(self):
        def loader(request, cancelled):
            if request == "fail":
                raise ValueError("private provider response")
            return "recovered"

        worker = self.make_worker(loader)
        generation = worker.submit("fail")
        result = self.wait_result(worker)
        self.assertEqual(
            result, WorkerResult(generation=generation, error="worker_failed")
        )
        worker.submit("okay")
        result = self.wait_result(worker)
        self.assertEqual(result.value, "recovered")
        self.assertIsNone(result.error)

    def test_saved_cancellation_predicate_keeps_its_original_generation(self):
        predicates = {}

        def loader(request, cancelled):
            predicates[request] = cancelled
            return request

        worker = self.make_worker(loader)
        worker.submit("first")
        self.wait_result(worker)
        self.assertFalse(predicates["first"]())
        worker.submit("second")
        self.wait_result(worker)
        self.assertTrue(predicates["first"]())
        self.assertFalse(predicates["second"]())

    def test_close_is_bounded_cancels_pending_and_drops_late_result(self):
        entered, release, finished = (
            threading.Event(),
            threading.Event(),
            threading.Event(),
        )
        calls, cancelled_states = [], []

        def loader(request, cancelled):
            calls.append(request)
            entered.set()
            try:
                if not release.wait(2):
                    raise TimeoutError("test coordination timed out")
                cancelled_states.append(cancelled())
                return "too late"
            finally:
                finished.set()

        worker = self.make_worker(loader, release)
        worker.submit("active")
        self.assertTrue(entered.wait(2))
        self.assertTrue(worker.busy)
        worker.submit("pending")
        started = time.monotonic()
        worker.close(timeout=0.01)
        self.assertLess(time.monotonic() - started, 0.5)
        self.assertTrue(worker.alive)  # Never claim a blocked Python call was killed.
        self.assertIsNone(worker.poll())
        release.set()
        self.assertTrue(finished.wait(2))
        worker.close(timeout=1)
        self.assertFalse(worker.alive)
        self.assertFalse(worker.busy)
        self.assertEqual(calls, ["active"])
        self.assertEqual(cancelled_states, [True])
        self.assertIsNone(worker.poll())
        with self.assertRaisesRegex(RuntimeError, "^worker_closed$"):
            worker.submit("after shutdown")

    def test_close_joins_idle_worker_and_is_idempotent(self):
        worker = self.make_worker(lambda request, cancelled: request)
        worker.close()
        self.assertFalse(worker.alive)
        worker.close()
        self.assertIsNone(worker.poll())

    def test_loader_can_close_itself_without_self_join(self):
        workers = {}
        returned = threading.Event()

        def loader(request, cancelled):
            workers["worker"].close()
            returned.set()
            return "discarded"

        worker = self.make_worker(loader)
        workers["worker"] = worker
        worker.submit(None)
        self.assertTrue(returned.wait(2))
        worker.close(timeout=1)
        self.assertFalse(worker.alive)
        self.assertIsNone(worker.poll())

    def test_unbounded_or_invalid_close_timeout_is_refused(self):
        worker = self.make_worker(lambda request, cancelled: request)
        for timeout in (float("inf"), float("nan"), -1, True, 10**400):
            with (
                self.subTest(timeout=timeout),
                self.assertRaisesRegex(ValueError, "invalid_close_timeout"),
            ):
                worker.close(timeout=timeout)
        worker.close()


if __name__ == "__main__":
    unittest.main()

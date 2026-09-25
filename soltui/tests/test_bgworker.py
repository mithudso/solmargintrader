"""Tests for the background worker's run loop.

`run()` takes its results path, state path, settings and stop flag as arguments
precisely so the loop can be driven without spawning a process or touching real
price data — the strategy evaluation itself is patched out, because what is under
test here is the *loop*: resume, stop, limit, and the failure paths.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from soltui import bgqueue as q
from soltui import bgworker
from soltui.config import default_settings


def _jobs(n: int, interval: str = "1d") -> list[q.Job]:
    """A deterministic queue of n distinct jobs."""
    return [
        q.Job("rsi", "medium", "SOL", interval, {"period": i + 2}, likelihood="low")
        for i in range(n)
    ]


def _ok(job: q.Job, arrays, cfg, settings) -> q.JobResult:  # noqa: ANN001, ARG001
    """A passing evaluation, standing in for a real CPCV run."""
    return q.JobResult(
        job_id=job.job_id, strategy=job.strategy, horizon=job.horizon,
        asset=job.asset, interval=job.interval, params=dict(job.params),
        tier=job.tier, variation=job.variation, family=job.family,
        median_sharpe=1.0, iqr=0.1, frac_positive=0.7, median_return=0.2,
        trades=50, evaluable=True,
    )


class _RunCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.results = self.dir / "results.jsonl"
        self.state = self.dir / "state.json"
        self.settings = default_settings()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_worker(self, jobs, evaluate=_ok, stop=None, limit=None, cache=None):
        """Drive `run()` with the queue and evaluator patched out."""
        patches = [
            mock.patch.object(bgworker, "build_queue", return_value=jobs),
            mock.patch.object(bgworker, "evaluate", side_effect=evaluate),
        ]
        if cache is not None:
            patches.append(mock.patch.object(bgworker, "ArrayCache", cache))
        else:
            patches.append(
                mock.patch.object(bgworker, "ArrayCache", lambda s: mock.MagicMock())
            )
        for p in patches:
            p.start()
        self.addCleanup(lambda: [p.stop() for p in patches])
        return bgworker.run(
            "SOL", settings=self.settings, results_path=self.results,
            state_path=self.state, stop=stop or bgworker._Stop(), limit=limit,
        )


class TestRunLoop(_RunCase):
    def test_completes_and_writes_every_result(self) -> None:
        state = self.run_worker(_jobs(4))
        self.assertEqual(state.phase, "done")
        self.assertEqual(state.done, 4)
        self.assertEqual(len(q.read_results(self.results)), 4)

    def test_empty_queue_is_done_not_error(self) -> None:
        state = self.run_worker([])
        self.assertEqual(state.phase, "done")
        self.assertEqual(state.total, 0)

    def test_limit_truncates_the_batch(self) -> None:
        state = self.run_worker(_jobs(10), limit=3)
        self.assertEqual(state.total, 3)
        self.assertEqual(len(q.read_results(self.results)), 3)

    def test_stop_halts_at_a_job_boundary(self) -> None:
        stop = bgworker._Stop()
        stop.requested = True
        state = self.run_worker(_jobs(4), stop=stop)
        self.assertEqual(state.phase, "stopped")
        self.assertEqual(len(q.read_results(self.results)), 0)

    def test_resume_skips_completed_work(self) -> None:
        """The point of flushing every result: an interrupted sweep restarts
        where it left off rather than recomputing."""
        jobs = _jobs(5)
        self.run_worker(jobs[:2])
        state = self.run_worker(jobs)
        self.assertEqual(state.total, 3)
        self.assertEqual(len(q.read_results(self.results)), 5)

    def test_final_state_is_persisted(self) -> None:
        self.run_worker(_jobs(2))
        self.assertEqual(q.read_state(self.state).phase, "done")


class TestFailurePaths(_RunCase):
    def test_one_bad_config_does_not_end_the_sweep(self) -> None:
        def flaky(job, arrays, cfg, settings):  # noqa: ANN001
            if job.params["period"] == 3:
                raise ValueError("bad parameter")
            return _ok(job, arrays, cfg, settings)

        state = self.run_worker(_jobs(4), evaluate=flaky)
        self.assertEqual(state.phase, "done")
        rows = q.read_results(self.results)
        self.assertEqual(len(rows), 4)
        failed = [r for r in rows if not r.evaluable]
        self.assertEqual(len(failed), 1)
        self.assertIn("bad parameter", failed[0].reason)

    def test_a_deterministic_failure_is_recorded_so_resume_skips_it(self) -> None:
        """Skipping instead of recording would block the queue on every restart."""
        def always_bad(job, arrays, cfg, settings):  # noqa: ANN001, ARG001
            raise ValueError("always")

        jobs = _jobs(2)
        self.run_worker(jobs, evaluate=always_bad)
        state = self.run_worker(jobs)
        self.assertEqual(state.total, 0)

    def test_failed_rows_can_never_reach_the_leaderboard(self) -> None:
        def always_bad(job, arrays, cfg, settings):  # noqa: ANN001, ARG001
            raise ValueError("always")

        self.run_worker(_jobs(3), evaluate=always_bad)
        ranked, floor = q.leaderboard(q.read_results(self.results))
        self.assertEqual(ranked, [])
        self.assertEqual(len(floor), 3)

    def test_a_missing_interval_skips_only_that_interval(self) -> None:
        """A missing SOL_1h.csv must not abandon the runnable daily jobs — the
        queue interleaves intervals, so aborting wholesale loses the sweep."""
        class Cache:
            def __init__(self, settings) -> None:  # noqa: ANN001, ARG002
                pass

            def get(self, asset, interval):  # noqa: ANN001
                if interval == "1h":
                    raise FileNotFoundError("no price cache at data/SOL_1h.csv")
                return {}

        jobs = _jobs(2, interval="1h") + _jobs(3, interval="1d")
        state = self.run_worker(jobs, cache=Cache)
        self.assertEqual(state.phase, "done")
        rows = q.read_results(self.results)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r.interval == "1d" for r in rows))
        self.assertIn("SOL_1h.csv", state.error)

    def test_every_interval_missing_is_an_error_not_a_clean_sweep(self) -> None:
        class Cache:
            def __init__(self, settings) -> None:  # noqa: ANN001, ARG002
                pass

            def get(self, asset, interval):  # noqa: ANN001, ARG002
                raise FileNotFoundError("no price cache")

        state = self.run_worker(_jobs(3), cache=Cache)
        self.assertEqual(state.phase, "error")
        self.assertEqual(len(q.read_results(self.results)), 0)


class TestFailedResult(unittest.TestCase):
    def test_carries_the_reason_and_is_never_evaluable(self) -> None:
        job = q.Job("rsi", "medium", "SOL", "1d", {"period": 14})
        row = bgworker.failed_result(job, ValueError("boom"))
        self.assertFalse(row.evaluable)
        self.assertFalse(row.ranked_ok)
        self.assertIn("boom", row.reason)
        self.assertEqual(row.job_id, job.job_id)

    def test_reason_is_bounded(self) -> None:
        """An exception carrying a whole dataframe repr must not blow up a line
        of the results file."""
        job = q.Job("rsi", "medium", "SOL", "1d", {})
        row = bgworker.failed_result(job, ValueError("x" * 5000))
        self.assertLessEqual(len(row.reason), 200)


class TestArrayCache(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.settings = default_settings()
        self.settings.data_dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_series_names_the_fetch_command(self) -> None:
        """The single most common first-run failure; a bare ENOENT would leave
        the user guessing which command repairs it."""
        cache = bgworker.ArrayCache(self.settings)
        with self.assertRaises(FileNotFoundError) as ctx:
            cache.get("SOL", "1h")
        self.assertIn("backtester.core.fetch", str(ctx.exception))
        self.assertIn("--interval 1h", str(ctx.exception))

    def test_series_is_loaded_once_per_key(self) -> None:
        Path(self.settings.data_dir, "SOL_1d.csv").write_text("x", encoding="utf-8")
        cache = bgworker.ArrayCache(self.settings)
        with mock.patch.object(bgworker, "CsvLoader") as loader, \
                mock.patch.object(bgworker, "frame_to_arrays", return_value={"a": 1}):
            cache.get("SOL", "1d")
            cache.get("SOL", "1d")
            cache.get("sol", "1d")  # case-insensitive key
        self.assertEqual(loader.call_count, 1)


class TestPriority(unittest.TestCase):
    def test_lower_priority_reports_a_readback_not_the_request(self) -> None:
        """Reporting the request would be reporting a wish; a sandbox may refuse."""
        level = bgworker.lower_priority(0)
        self.assertIsInstance(level, int)

    def test_a_refused_setpriority_is_not_fatal(self) -> None:
        with mock.patch("os.setpriority", side_effect=OSError("denied")):
            self.assertIsInstance(bgworker.lower_priority(), int)


class TestAssetValidation(unittest.TestCase):
    def test_a_path_escape_is_refused(self) -> None:
        """The symbol becomes a filename, and `Path('data') / '/tmp/x'` discards
        the left operand entirely."""
        for bad in ("../../etc/passwd", "/tmp/x", "SOL/../BTC", ""):
            with self.assertRaises(ValueError):
                q.validate_asset(bad)

    def test_a_plain_symbol_is_normalised(self) -> None:
        self.assertEqual(q.validate_asset(" sol "), "SOL")


if __name__ == "__main__":
    unittest.main()

"""Tests for the resumable 1-minute fetch.

Each class here guards a bug that was live on disk, not a hypothetical one. The fetch is
a multi-hour job against a rate-limited venue, so its failure modes are all of the same
shape: something is recorded as done that was not done, and no count reveals it.

  * **the trailing window.** Flooring the plan's end to the minute rather than to the
    window grid put the last window's request end in the future. It returned partial, was
    recorded done, and was an interior member of every later plan -- so it was never
    refetched. Found on disk holding 61 of 300 bars while the report said "full".
  * **the cached probe floor.** `first_available` early-exits at the oldest planned
    window, so its answer means "there was data at this search floor", not "the listing
    starts here". Cached from a short run it silently caps every longer one.
  * **the in-place rewrite.** `finalise` rewrote the only copy of a file that costs hours
    of requests. An interrupted write left a stump the sidecar still called complete.

Network paths are not exercised: `get_candles` is stubbed. What is tested is the plan
arithmetic and the ledger, which is where every one of those bugs lived.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backtester.core.fetch_minutes as fm  # noqa: E402


class PlanWindowsTests(unittest.TestCase):
    """The window grid. Every resume decision is keyed on these numbers."""

    NOW = 1785942061          # deliberately not on a window boundary

    def test_no_planned_window_ends_in_the_future(self) -> None:
        """The bug: a window whose end had not happened yet came back partial."""
        windows = fm.plan_windows(5.0, now=self.NOW)
        self.assertLessEqual(windows[-1] + fm.WINDOW_SECONDS, self.NOW)

    def test_every_start_is_on_the_window_grid(self) -> None:
        # Sidecar keys are window starts, so a start off the grid is a key that a later
        # plan can never match -- the window would be refetched for ever.
        for start in fm.plan_windows(5.0, now=self.NOW):
            self.assertEqual(start % fm.WINDOW_SECONDS, 0)

    def test_the_plan_is_unchanged_until_a_whole_window_has_passed(self) -> None:
        base = fm.plan_windows(5.0, now=self.NOW)
        still_inside = fm.WINDOW_SECONDS - (self.NOW % fm.WINDOW_SECONDS) - 1
        self.assertEqual(fm.plan_windows(5.0, now=self.NOW + still_inside), base)

    def test_the_plan_advances_by_exactly_one_window_at_the_boundary(self) -> None:
        base = fm.plan_windows(5.0, now=self.NOW)
        crossed = fm.plan_windows(
            5.0, now=self.NOW + fm.WINDOW_SECONDS - (self.NOW % fm.WINDOW_SECONDS))
        self.assertEqual(crossed[-1], base[-1] + fm.WINDOW_SECONDS)
        self.assertEqual(len(crossed), len(base))

    def test_windows_are_contiguous_and_ascending(self) -> None:
        windows = fm.plan_windows(1.0, now=self.NOW)
        deltas = {b - a for a, b in zip(windows, windows[1:])}
        self.assertEqual(deltas, {fm.WINDOW_SECONDS})


class SidecarTests(unittest.TestCase):
    """The ledger of attempted windows, and the probe floor that travels with it."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        self._data = mock.patch.object(fm, "DATA", self.tmp)
        self._data.start()
        self.addCleanup(self._data.stop)

    def test_progress_round_trips(self) -> None:
        fm.save_progress("BTC", {100, 200, 300})
        self.assertEqual(fm.load_progress("BTC"), {100, 200, 300})

    def test_saving_progress_preserves_the_probe(self) -> None:
        """Progress is written far more often than the probe; it must not erase it."""
        fm.save_listing_start("BTC", 5_000, 1_000)
        fm.save_progress("BTC", {100, 200})
        self.assertEqual(fm.load_probe("BTC"), (5_000, 1_000))
        self.assertEqual(fm.load_progress("BTC"), {100, 200})

    def test_an_unreadable_sidecar_does_not_abort_the_run(self) -> None:
        # Refetching is merely slower; crashing would strand a job that is otherwise fine.
        fm.progress_path("BTC").write_text("{ this is not json")
        self.assertEqual(fm.load_progress("BTC"), set())
        self.assertIsNone(fm.load_probe("BTC"))

    def test_a_probe_without_a_floor_is_refused(self) -> None:
        """A legacy sidecar has no floor, so its listing start cannot be trusted.

        Returning None forces a re-probe, which is the correct migration: the recorded
        value may be a search floor from a shorter run rather than a listing start.
        """
        fm.progress_path("BTC").write_text(json.dumps(
            {"windows_done": [1, 2], "listing_start": 1234}))
        self.assertIsNone(fm.load_probe("BTC"))
        self.assertIsNone(fm.load_listing_start("BTC"))


class EffectiveWindowsTests(unittest.TestCase):
    """Reuse of the probe, which is where a five-year request became a one-year one."""

    NOW = 1785942061

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        self._data = mock.patch.object(fm, "DATA", self.tmp)
        self._data.start()
        self.addCleanup(self._data.stop)

    def test_a_short_probe_does_not_cap_a_longer_run(self) -> None:
        """The bug: a --years 1 probe floor was reused to cap a --years 5 plan."""
        one_year_floor = fm.plan_windows(1.0, now=self.NOW)[0]
        fm.save_listing_start("BTC", one_year_floor, one_year_floor)
        with mock.patch.object(fm, "first_available", return_value=0) as probe:
            windows = fm.effective_windows("BTC", 5.0, now=self.NOW)
        probe.assert_called_once()          # must re-probe rather than reuse
        self.assertEqual(len(windows), len(fm.plan_windows(5.0, now=self.NOW)))

    def test_a_probe_from_the_same_floor_is_reused(self) -> None:
        five = fm.plan_windows(5.0, now=self.NOW)
        fm.save_listing_start("BTC", five[10], five[0])
        with mock.patch.object(fm, "first_available") as probe:
            windows = fm.effective_windows("BTC", 5.0, now=self.NOW)
        probe.assert_not_called()
        self.assertEqual(windows[0], five[10])

    def test_probing_can_be_switched_off(self) -> None:
        with mock.patch.object(fm, "first_available") as probe:
            windows = fm.effective_windows("BTC", 5.0, now=self.NOW, probe=False)
        probe.assert_not_called()
        self.assertEqual(windows, fm.plan_windows(5.0, now=self.NOW))


class FirstAvailableTests(unittest.TestCase):
    """The listing-start search, which persists its answer and so must not overshoot."""

    NOW = 1785942061

    def _search(self, has_data) -> int:
        with mock.patch.object(fm, "get_candles",
                              side_effect=lambda url, lim=None: [1] if has_data(url) else []):
            return fm.first_available("BTC", 5.0, None, self.NOW)

    @staticmethod
    def _start_of(url: str) -> str:
        return url.split("start=")[1].split("&")[0]

    def test_a_venue_with_full_history_returns_the_oldest_window(self) -> None:
        self.assertEqual(self._search(lambda url: True),
                         fm.plan_windows(5.0, now=self.NOW)[0])

    def test_a_single_hole_does_not_end_the_search(self) -> None:
        """One empty window is a halt, not a boundary -- and the answer is cached.

        Before the fix, a lone gap above the true start discarded everything behind it.
        """
        windows = fm.plan_windows(5.0, now=self.NOW)
        hole = {windows[3]}
        import pandas as pd
        holes = {str(pd.Timestamp(w, unit="s", tz="UTC").isoformat()) for w in hole}
        got = self._search(lambda url: self._start_of(url) not in holes)
        self.assertEqual(got, windows[0])

    def test_a_venue_with_no_data_at_all_is_refused_loudly(self) -> None:
        with self.assertRaises(fm.FetchError):
            self._search(lambda url: False)


class CoverageTests(unittest.TestCase):
    """Coverage separates missing calendar from missing minutes inside it."""

    def setUp(self) -> None:
        # Isolated from data/: coverage reads the real sidecar for windows_done, so
        # without this the assertions depend on whatever a live fetch has written.
        self.tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        patcher = mock.patch.object(fm, "DATA", self.tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _frame(timestamps: list[int]):
        import pandas as pd
        return pd.DataFrame({
            "timestamp": timestamps, "open": 1.0, "high": 1.0,
            "low": 1.0, "close": 1.0, "volume": 1.0,
        })

    def test_a_complete_series_reads_as_complete(self) -> None:
        ts = list(range(0, 600 * fm.MINUTE, fm.MINUTE))
        cov = fm.coverage("BTC", self._frame(ts), 5.0)
        self.assertEqual(cov.bars, 600)
        self.assertEqual(cov.missing_bars, 0)
        self.assertAlmostEqual(cov.completeness, 1.0, places=6)

    def test_a_hole_shows_up_as_missing_minutes_not_short_history(self) -> None:
        # The distinction the manifest exists to make: same span, fewer bars.
        ts = [t for t in range(0, 600 * fm.MINUTE, fm.MINUTE)
              if not 100 * fm.MINUTE <= t < 200 * fm.MINUTE]
        cov = fm.coverage("BTC", self._frame(ts), 5.0)
        self.assertEqual(cov.missing_bars, 100)
        self.assertEqual(cov.largest_gap_minutes, 101)
        self.assertEqual(cov.gaps_over_an_hour, 1)
        self.assertLess(cov.completeness, 1.0)

    def test_short_history_is_reported_as_a_calendar_shortfall(self) -> None:
        ts = list(range(0, 600 * fm.MINUTE, fm.MINUTE))
        cov = fm.coverage("BTC", self._frame(ts), 5.0)
        self.assertGreater(cov.short_of_request_days, 1800)
        self.assertEqual(cov.missing_bars, 0)      # nothing missing INSIDE the span

    def test_an_empty_series_is_not_called_complete(self) -> None:
        cov = fm.coverage("BTC", self._frame([]), 5.0)
        self.assertEqual(cov.bars, 0)
        self.assertFalse(cov.complete_fetch)


class CacheTests(unittest.TestCase):
    """Reading and rewriting the only copy of an expensive file."""

    def setUp(self) -> None:
        self.tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        self._data = mock.patch.object(fm, "DATA", self.tmp)
        self._data.start()
        self.addCleanup(self._data.stop)

    def _write(self, timestamps: list[int]) -> None:
        rows = ["timestamp,open,high,low,close,volume"]
        rows += [f"{t},1,1,1,1,1" for t in timestamps]
        fm.minute_path("BTC").write_text("\n".join(rows) + "\n")

    def test_a_zero_byte_cache_raises_fetch_error_not_a_pandas_error(self) -> None:
        """`path.open("a")` creates the file before any window lands.

        So "exists" is not "has rows", and pandas would raise EmptyDataError from deep
        inside instead of the actionable message this module owns.
        """
        fm.minute_path("BTC").touch()
        with self.assertRaises(fm.FetchError):
            fm.load_minutes("BTC")

    def test_a_missing_cache_raises_fetch_error(self) -> None:
        with self.assertRaises(fm.FetchError):
            fm.load_minutes("BTC")

    def test_out_of_order_appends_are_sorted_and_deduplicated_on_read(self) -> None:
        self._write([300, 60, 120, 60])
        df = fm.load_minutes("BTC")
        self.assertEqual(list(df["timestamp"]), [60, 120, 300])

    def test_finalise_writes_through_a_temporary_and_renames(self) -> None:
        """An interrupted in-place rewrite left a stump the sidecar called complete.

        Asserting the rename rather than the outcome, because the outcome of the safe
        and unsafe versions is identical whenever nothing goes wrong.
        """
        self._write([180, 60, 120])
        with mock.patch.object(Path, "replace", autospec=True) as replace:
            fm.finalise("BTC")
        self.assertEqual(replace.call_count, 1)
        source = replace.call_args.args[0]
        self.assertTrue(str(source).endswith(".csv.tmp"), source)

    def test_finalise_leaves_the_cache_sorted(self) -> None:
        self._write([180, 60, 120])
        fm.finalise("BTC")
        self.assertEqual(list(fm.load_minutes("BTC")["timestamp"]), [60, 120, 180])


class RateLimiterTests(unittest.TestCase):
    """The one place the venue's per-IP limit is enforced."""

    def test_it_spaces_successive_acquisitions(self) -> None:
        import time
        limiter = fm.RateLimiter(50.0)          # 20ms apart
        started = time.monotonic()
        for _ in range(5):
            limiter.acquire()
        # Four gaps of 20ms; the first acquire is free.
        self.assertGreaterEqual(time.monotonic() - started, 4 * 0.02 - 0.005)

    def test_an_idle_limiter_cannot_bank_credit(self) -> None:
        """max(now, self._next) is what stops a burst after a quiet period."""
        import time
        limiter = fm.RateLimiter(20.0)
        limiter.acquire()
        time.sleep(0.15)                        # far longer than the 50ms interval
        started = time.monotonic()
        limiter.acquire()
        limiter.acquire()
        self.assertGreaterEqual(time.monotonic() - started, 0.05 - 0.005)


class RetryAfterTests(unittest.TestCase):
    """Back-off for a 429, which must not be retried like a transport stall."""

    @staticmethod
    def _error(header: str | None) -> object:
        class Fake(Exception):
            code = 429
            headers = {} if header is None else {"Retry-After": header}
        return Fake()

    def test_the_venues_own_retry_after_is_honoured(self) -> None:
        self.assertEqual(fm._retry_after(self._error("7"), 0), 7.0)

    def test_an_absurd_retry_after_is_capped(self) -> None:
        self.assertEqual(fm._retry_after(self._error("9999"), 0), 30.0)

    def test_a_junk_retry_after_falls_back_to_geometric(self) -> None:
        self.assertEqual(fm._retry_after(self._error("soon"), 1), 1.0)

    def test_without_a_header_it_backs_off_geometrically_and_is_bounded(self) -> None:
        delays = [fm._retry_after(self._error(None), a) for a in range(6)]
        self.assertEqual(delays[:4], [0.5, 1.0, 2.0, 4.0])
        self.assertLessEqual(max(delays), 8.0)


if __name__ == "__main__":
    unittest.main()

"""Tests for the background sweep's queue, file contract and leaderboard.

The properties worth defending here are the ones a background process makes
hard to notice going wrong: an ordering that stops putting the published preset
first, a resume that re-runs finished work, a reader that dies on a torn line,
and — most importantly — a leaderboard that quietly ranks a Sharpe computed from
three trades.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.core.strategy_cards import load_all

from soltui import bgqueue as q


def _result(**kw) -> q.JobResult:
    """A JobResult with sane defaults, overridden per test."""
    base = dict(
        job_id="id", strategy="rsi", horizon="medium", asset="SOL", interval="1d",
        params={}, tier=0, variation="", family="mean-reversion",
        median_sharpe=1.0, iqr=0.1, frac_positive=0.6, median_return=0.1,
        trades=q.MIN_TRADES, evaluable=True,
    )
    base.update(kw)
    return q.JobResult(**base)


class TestJobIdentity(unittest.TestCase):
    def test_id_is_stable_across_dict_ordering(self) -> None:
        """The same configuration must hash the same however it was built."""
        a = q.Job("rsi", "medium", "SOL", "1d", {"period": 14, "oversold": 30.0})
        b = q.Job("rsi", "medium", "SOL", "1d", {"oversold": 30.0, "period": 14})
        self.assertEqual(a.job_id, b.job_id)

    def test_integral_float_and_int_are_one_job(self) -> None:
        """The engine cannot tell 20 from 20.0, so the queue must not either."""
        a = q.Job("bb_reversion", "medium", "SOL", "1d", {"window": 20})
        b = q.Job("bb_reversion", "medium", "SOL", "1d", {"window": 20.0})
        self.assertEqual(a.job_id, b.job_id)

    def test_commentary_does_not_change_the_id(self) -> None:
        """Editing a card's prose must not orphan finished work."""
        a = q.Job("rsi", "medium", "SOL", "1d", {"period": 14}, likelihood="low")
        b = q.Job("rsi", "medium", "SOL", "1d", {"period": 14}, likelihood="moderate")
        self.assertEqual(a.job_id, b.job_id)

    def test_different_params_are_different_jobs(self) -> None:
        a = q.Job("rsi", "medium", "SOL", "1d", {"period": 14})
        b = q.Job("rsi", "medium", "SOL", "1d", {"period": 7})
        self.assertNotEqual(a.job_id, b.job_id)


class TestPerturbation(unittest.TestCase):
    def test_bool_is_never_scaled(self) -> None:
        """bool subclasses int; scaling a flag would produce allow_short=2."""
        self.assertIsNone(q._perturb(True, 2.0))
        self.assertIsNone(q._perturb(False, 0.5))

    def test_string_is_never_scaled(self) -> None:
        self.assertIsNone(q._perturb("ema", 2.0))

    def test_int_below_one_is_dropped_not_clamped(self) -> None:
        """Clamping to 1 would duplicate another job under a different label."""
        self.assertIsNone(q._perturb(1, 0.5))

    def test_no_op_scaling_is_dropped(self) -> None:
        self.assertIsNone(q._perturb(10, 1.0))

    def test_int_stays_int(self) -> None:
        self.assertEqual(q._perturb(20, 0.5), 10)
        self.assertIsInstance(q._perturb(20, 0.5), int)


class TestOrdering(unittest.TestCase):
    def test_presets_come_before_every_variation(self) -> None:
        """Tier 0 first is the whole promise: an interrupted sweep should have
        covered every card's own configuration before guessing at any of them."""
        jobs = q.order_jobs([
            q.Job("a", "medium", "SOL", "1d", {"x": 2}, tier=2, likelihood="moderate"),
            q.Job("b", "medium", "SOL", "1d", {"x": 1}, tier=0, likelihood="very-low"),
            q.Job("c", "medium", "SOL", "1d", {"x": 3}, tier=1, likelihood="moderate"),
        ])
        self.assertEqual([j.tier for j in jobs], [0, 1, 2])

    def test_likelihood_orders_within_a_tier(self) -> None:
        jobs = q.order_jobs([
            q.Job("a", "medium", "SOL", "1d", {}, tier=0, likelihood="very-low"),
            q.Job("b", "medium", "SOL", "1d", {}, tier=0, likelihood="moderate"),
            q.Job("c", "medium", "SOL", "1d", {}, tier=0, likelihood="low"),
        ])
        self.assertEqual([j.likelihood for j in jobs],
                         ["moderate", "low", "very-low"])

    def test_unknown_likelihood_sorts_last_without_raising(self) -> None:
        """A new card value should degrade the ordering, not stop the sweep."""
        jobs = q.order_jobs([
            q.Job("a", "medium", "SOL", "1d", {}, tier=0, likelihood="speculative"),
            q.Job("b", "medium", "SOL", "1d", {}, tier=0, likelihood="low"),
        ])
        self.assertEqual([j.strategy for j in jobs], ["b", "a"])

    def test_ordering_is_deterministic(self) -> None:
        jobs = [
            q.Job(s, "medium", "SOL", "1d", {}, tier=0, likelihood="low")
            for s in ("rsi", "macd", "breakout")
        ]
        self.assertEqual(
            [j.strategy for j in q.order_jobs(jobs)],
            [j.strategy for j in q.order_jobs(list(reversed(jobs)))],
        )


class TestDedupe(unittest.TestCase):
    def test_identical_evaluations_collapse(self) -> None:
        """medium and long are both daily; a no-parameter strategy is then the
        same computation twice, and heat is the only thing that buys."""
        jobs = [
            q.Job("buy_and_hold", "medium", "SOL", "1d", {}),
            q.Job("buy_and_hold", "long", "SOL", "1d", {}),
        ]
        self.assertEqual(len(q.dedupe(jobs)), 1)

    def test_different_intervals_survive(self) -> None:
        jobs = [
            q.Job("buy_and_hold", "medium", "SOL", "1d", {}),
            q.Job("buy_and_hold", "short", "SOL", "1h", {}),
        ]
        self.assertEqual(len(q.dedupe(jobs)), 2)

    def test_keeps_the_first_occurrence(self) -> None:
        jobs = [
            q.Job("buy_and_hold", "medium", "SOL", "1d", {}, likelihood="moderate"),
            q.Job("buy_and_hold", "long", "SOL", "1d", {}, likelihood="very-low"),
        ]
        self.assertEqual(q.dedupe(jobs)[0].horizon, "medium")


class TestHorizonInterval(unittest.TestCase):
    def test_short_is_hourly_and_others_daily(self) -> None:
        """A horizon is a parameter scale, and a scale is meaningless without a
        bar size — running the short presets on daily bars mislabels them."""
        self.assertEqual(q.HORIZON_INTERVAL["short"], "1h")
        self.assertEqual(q.HORIZON_INTERVAL["medium"], "1d")
        self.assertEqual(q.HORIZON_INTERVAL["long"], "1d")

    def test_jobs_inherit_the_horizon_interval(self) -> None:
        cards = load_all()
        card = cards["rsi"]
        jobs = q.jobs_for_card(card, "short", "SOL", max_tier=0)
        self.assertTrue(jobs)
        self.assertEqual(jobs[0].interval, "1h")


class TestBuildQueue(unittest.TestCase):
    """These run against the real cards, which is the point: the defaults must
    come from the cards rather than a copy that can drift."""

    def test_queue_is_non_empty_and_starts_at_tier_zero(self) -> None:
        jobs = q.build_queue("SOL", max_tier=1)
        self.assertTrue(jobs)
        self.assertEqual(jobs[0].tier, 0)

    def test_every_job_names_a_buildable_strategy(self) -> None:
        from backtester.core.strategies import REGISTRY

        for job in q.build_queue("SOL", max_tier=0):
            self.assertIn(job.strategy, REGISTRY)

    def test_params_match_the_card_preset_at_tier_zero(self) -> None:
        cards = load_all()
        for job in q.build_queue("SOL", horizons=["medium"], max_tier=0):
            card = next(c for c in cards.values()
                        if (c.registry_key or c.id) == job.strategy)
            self.assertEqual(job.params, q._canonical(card.preset("medium")))

    def test_higher_tier_adds_jobs(self) -> None:
        self.assertGreater(
            len(q.build_queue("SOL", max_tier=2)),
            len(q.build_queue("SOL", max_tier=0)),
        )

    def test_ids_are_unique(self) -> None:
        jobs = q.build_queue("SOL", max_tier=2)
        self.assertEqual(len({j.job_id for j in jobs}), len(jobs))


class TestPending(unittest.TestCase):
    def test_completed_ids_are_skipped_and_order_is_kept(self) -> None:
        jobs = [
            q.Job("a", "medium", "SOL", "1d", {"x": 1}),
            q.Job("b", "medium", "SOL", "1d", {"x": 2}),
            q.Job("c", "medium", "SOL", "1d", {"x": 3}),
        ]
        todo = q.pending(jobs, {jobs[1].job_id})
        self.assertEqual([j.strategy for j in todo], ["a", "c"])


class TestFileContract(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.results = self.dir / "results.jsonl"
        self.state = self.dir / "state.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_append_then_read_round_trips(self) -> None:
        q.append_result(_result(job_id="one"), self.results)
        q.append_result(_result(job_id="two", strategy="macd"), self.results)
        rows = q.read_results(self.results)
        self.assertEqual([r.job_id for r in rows], ["one", "two"])
        self.assertEqual(rows[1].strategy, "macd")

    def test_torn_final_line_is_skipped_not_raised(self) -> None:
        """A read racing an in-flight append must lose a row, not the pane."""
        q.append_result(_result(job_id="one"), self.results)
        with self.results.open("a", encoding="utf-8") as fh:
            fh.write('{"job_id": "two", "strat')
        rows = q.read_results(self.results)
        self.assertEqual([r.job_id for r in rows], ["one"])

    def test_unknown_fields_are_ignored(self) -> None:
        """A results file written by a newer build must still be readable."""
        with self.results.open("a", encoding="utf-8") as fh:
            payload = json.loads(_result(job_id="one").to_json())
            payload["invented_later"] = 42
            fh.write(json.dumps(payload) + "\n")
        self.assertEqual(len(q.read_results(self.results)), 1)

    def test_missing_results_file_reads_empty(self) -> None:
        self.assertEqual(q.read_results(self.dir / "absent.jsonl"), [])

    def test_state_round_trips(self) -> None:
        q.write_state(q.QueueState(phase="running", done=3, total=10), self.state)
        state = q.read_state(self.state)
        self.assertEqual(state.phase, "running")
        self.assertEqual(state.remaining, 7)
        self.assertAlmostEqual(state.percent or 0, 0.3)

    def test_state_write_leaves_no_temp_files(self) -> None:
        """tmp+rename must clean up after itself, not litter the config dir."""
        q.write_state(q.QueueState(phase="running"), self.state)
        q.write_state(q.QueueState(phase="done"), self.state)
        self.assertEqual([p.name for p in self.dir.iterdir()], ["state.json"])

    def test_missing_state_reads_idle(self) -> None:
        self.assertEqual(q.read_state(self.dir / "absent.json").phase, "idle")

    def test_corrupt_state_reads_idle_rather_than_raising(self) -> None:
        self.state.write_text("{not json", encoding="utf-8")
        self.assertEqual(q.read_state(self.state).phase, "idle")

    def test_unknown_total_reports_no_percent(self) -> None:
        self.assertIsNone(q.QueueState(done=5, total=0).percent)
        self.assertEqual(q.QueueState(done=5, total=0).remaining, 0)


class TestLeaderboard(unittest.TestCase):
    """The liar's-leaderboard guard. These are the tests that matter most."""

    def test_thin_evidence_never_ranks_however_good_it_looks(self) -> None:
        lucky = _result(job_id="lucky", median_sharpe=9.9, trades=3)
        honest = _result(job_id="honest", median_sharpe=0.4, trades=50)
        ranked, floor = q.leaderboard([lucky, honest])
        self.assertEqual([r.job_id for r in ranked], ["honest"])
        self.assertEqual([r.job_id for r in floor], ["lucky"])

    def test_not_evaluable_never_ranks_even_above_the_floor(self) -> None:
        broken = _result(job_id="broken", median_sharpe=5.0, trades=500,
                         evaluable=False, reason="warm-up")
        ranked, floor = q.leaderboard([broken])
        self.assertEqual(ranked, [])
        self.assertEqual([r.job_id for r in floor], ["broken"])

    def test_the_floor_is_inclusive(self) -> None:
        """Exactly MIN_TRADES must qualify; an off-by-one here silently drops a
        whole band of otherwise-valid rows."""
        ranked, _ = q.leaderboard([_result(trades=q.MIN_TRADES)])
        self.assertEqual(len(ranked), 1)
        ranked, _ = q.leaderboard([_result(trades=q.MIN_TRADES - 1)])
        self.assertEqual(len(ranked), 0)

    def test_ranked_is_best_first(self) -> None:
        rows = [
            _result(job_id="mid", median_sharpe=0.5, trades=20),
            _result(job_id="top", median_sharpe=1.5, trades=20),
            _result(job_id="low", median_sharpe=-0.5, trades=20),
        ]
        ranked, _ = q.leaderboard(rows)
        self.assertEqual([r.job_id for r in ranked], ["top", "mid", "low"])

    def test_floor_rows_are_returned_not_hidden(self) -> None:
        """Hiding them would overstate how much of the space was usefully covered."""
        _, floor = q.leaderboard([_result(trades=1), _result(trades=2)])
        self.assertEqual(len(floor), 2)

    def test_summarise_counts_rankable_not_evaluated(self) -> None:
        rows = [_result(job_id="a", trades=50), _result(job_id="b", trades=2)]
        text = q.summarise(q.QueueState(phase="done"), rows)
        self.assertIn("1 rankable", text)
        self.assertIn("below the", text)

    def test_summarise_reports_progress_while_running(self) -> None:
        state = q.QueueState(phase="running", done=2, total=8)
        self.assertIn("2/8", q.summarise(state, []))

    def test_summarise_surfaces_an_error(self) -> None:
        state = q.QueueState(phase="error", error="no price cache")
        self.assertIn("no price cache", q.summarise(state, []))


class TestJobImmutability(unittest.TestCase):
    """`frozen=True` blocks rebinding, not in-place dict mutation — and job_id is
    recomputed from params on every access, so a mutable dict made the "stable
    content hash" claim false."""

    def test_params_cannot_be_mutated_in_place(self) -> None:
        job = q.Job("rsi", "medium", "SOL", "1d", {"period": 14})
        with self.assertRaises(TypeError):
            job.params["period"] = 7  # type: ignore[index]

    def test_mutating_the_source_dict_does_not_change_the_job(self) -> None:
        source = {"period": 14}
        job = q.Job("rsi", "medium", "SOL", "1d", source)
        before = job.job_id
        source["period"] = 7
        self.assertEqual(job.job_id, before)
        self.assertEqual(job.params["period"], 14)

    def test_jobs_are_hashable(self) -> None:
        """The generated __hash__ called hash() on the dict and raised, so the
        type advertised a hashability it did not have."""
        jobs = [
            q.Job("rsi", "medium", "SOL", "1d", {"period": 14}),
            q.Job("rsi", "medium", "SOL", "1d", {"period": 14}),
            q.Job("rsi", "medium", "SOL", "1d", {"period": 7}),
        ]
        self.assertEqual(len(set(jobs)), 2)


class TestTierOrdering(unittest.TestCase):
    def test_near_variations_are_reached_before_far_ones(self) -> None:
        """An earlier version had these reversed, so `--max-tier 1` swept only
        the half/double extremes while its help text sold it as the close-in
        option."""
        self.assertEqual(q.PERTURBATION_TIERS[1], (0.75, 1.5))
        self.assertEqual(q.PERTURBATION_TIERS[2], (0.5, 2.0))

    def test_max_tier_one_yields_the_near_variations(self) -> None:
        cards = load_all()
        jobs = q.jobs_for_card(cards["rsi"], "medium", "SOL", max_tier=1)
        variations = {j.variation for j in jobs if j.tier == 1}
        self.assertTrue(variations)
        self.assertTrue(all("x0.75" in v or "x1.5" in v for v in variations),
                        f"expected near variations, got {variations}")


class TestAssetScoping(unittest.TestCase):
    """One results file holds every sweep, so ranking must be scoped or a BTC
    config can take the top row of a table read as SOL."""

    def test_leaderboard_scopes_to_one_asset(self) -> None:
        rows = [
            _result(job_id="sol", asset="SOL", median_sharpe=0.5, trades=50),
            _result(job_id="btc", asset="BTC", median_sharpe=9.0, trades=50),
        ]
        ranked, _ = q.leaderboard(rows, "SOL")
        self.assertEqual([r.job_id for r in ranked], ["sol"])

    def test_no_asset_means_everything(self) -> None:
        rows = [
            _result(job_id="sol", asset="SOL", trades=50),
            _result(job_id="btc", asset="BTC", trades=50),
        ]
        ranked, _ = q.leaderboard(rows)
        self.assertEqual(len(ranked), 2)

    def test_scoping_is_case_insensitive(self) -> None:
        rows = [_result(job_id="sol", asset="SOL", trades=50)]
        self.assertEqual(len(q.for_asset(rows, "sol")), 1)

    def test_summarise_counts_only_the_scoped_asset(self) -> None:
        rows = [
            _result(job_id="sol", asset="SOL", trades=50),
            _result(job_id="btc", asset="BTC", trades=50),
        ]
        self.assertIn("1 rankable", q.summarise(q.QueueState(phase="done"), rows, "SOL"))


class TestStaleState(unittest.TestCase):
    def test_a_dead_worker_is_not_reported_as_running(self) -> None:
        """A SIGKILLed worker leaves state.json saying "running" forever; the
        pane would otherwise claim progress for a process that no longer exists."""
        state = q.QueueState(phase="running", done=4, total=10)
        text = q.summarise(state, [], worker_alive=False)
        self.assertIn("stopped unexpectedly", text)
        self.assertNotIn("running 4/10", text)

    def test_a_live_worker_still_reports_progress(self) -> None:
        state = q.QueueState(phase="running", done=4, total=10)
        self.assertIn("running 4/10", q.summarise(state, [], worker_alive=True))

    def test_unknown_liveness_keeps_the_old_behaviour(self) -> None:
        state = q.QueueState(phase="running", done=4, total=10)
        self.assertIn("running 4/10", q.summarise(state, []))


class TestCorruptRows(unittest.TestCase):
    """A results file is untrusted input once it can be corrupted: one bad row
    must cost one row, never the pane."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.results = Path(self._tmp.name) / "results.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, payload: dict) -> None:
        with self.results.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    def test_a_string_where_a_float_belongs_does_not_break_ranking(self) -> None:
        good = json.loads(_result(job_id="good", trades=50).to_json())
        bad = dict(good, job_id="bad", median_sharpe="not a number")
        self._write(good)
        self._write(bad)
        rows = q.read_results(self.results)
        self.assertEqual(len(rows), 2)
        ranked, _ = q.leaderboard(rows)  # must not raise comparing str to float
        self.assertEqual(ranked[0].job_id, "good")

    def test_nan_is_neutralised(self) -> None:
        """NaN poisons every comparison it touches, silently reordering a sort."""
        self.assertEqual(q._as_float(float("nan")), 0.0)

    def test_a_bad_trade_count_does_not_rank(self) -> None:
        bad = dict(json.loads(_result(job_id="bad").to_json()), trades="lots")
        self._write(bad)
        ranked, floor = q.leaderboard(q.read_results(self.results))
        self.assertEqual(ranked, [])
        self.assertEqual(len(floor), 1)

    def test_corrupt_state_numerics_do_not_break_percent(self) -> None:
        path = Path(self._tmp.name) / "state.json"
        path.write_text('{"phase": "running", "done": 2, "total": "many"}',
                        encoding="utf-8")
        state = q.read_state(path)
        self.assertEqual(state.total, 0)
        self.assertIsNone(state.percent)


class TestIncrementalRead(unittest.TestCase):
    """Re-reading the whole file per append makes watching a sweep cost O(N^2) in
    the number of jobs, and a long sweep is exactly where the file gets big."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.results = Path(self._tmp.name) / "results.jsonl"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_reads_only_what_was_appended(self) -> None:
        q.append_result(_result(job_id="one"), self.results)
        first, cursor, restarted = q.read_results_since(path=self.results)
        self.assertEqual([r.job_id for r in first], ["one"])
        self.assertTrue(restarted)  # first read of a file always starts at 0

        q.append_result(_result(job_id="two"), self.results)
        second, cursor2, restarted2 = q.read_results_since(cursor, self.results)
        self.assertEqual([r.job_id for r in second], ["two"])
        self.assertGreater(cursor2.offset, cursor.offset)
        self.assertFalse(restarted2)

    def test_nothing_new_reads_nothing(self) -> None:
        q.append_result(_result(job_id="one"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)
        again, cursor2, _ = q.read_results_since(cursor, self.results)
        self.assertEqual(again, [])
        self.assertEqual(cursor2.offset, cursor.offset)

    def test_a_partial_trailing_line_is_left_for_next_time(self) -> None:
        """The offset must not advance past an incomplete line, or the row is
        lost forever once the worker finishes writing it."""
        q.append_result(_result(job_id="one"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)
        with self.results.open("a", encoding="utf-8") as fh:
            fh.write('{"job_id": "two", "strat')
        rows, cursor2, _ = q.read_results_since(cursor, self.results)
        self.assertEqual(rows, [])
        self.assertEqual(cursor2.offset, cursor.offset)

    def test_a_truncated_file_resets_and_says_so(self) -> None:
        """Continuing from a stale offset after truncation would slice a line."""
        q.append_result(_result(job_id="one"), self.results)
        q.append_result(_result(job_id="two"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)
        self.results.unlink()
        q.append_result(_result(job_id="three"), self.results)
        rows, _, restarted = q.read_results_since(cursor, self.results)
        self.assertEqual([r.job_id for r in rows], ["three"])
        self.assertTrue(restarted)

    def test_matches_a_full_read(self) -> None:
        for i in range(5):
            q.append_result(_result(job_id=f"j{i}"), self.results)
        incremental: list[q.JobResult] = []
        cursor = q.ResultsCursor()
        for _ in range(5):
            rows, cursor, _ = q.read_results_since(cursor, self.results)
            incremental.extend(rows)
        self.assertEqual(
            [r.job_id for r in incremental],
            [r.job_id for r in q.read_results(self.results)],
        )

    def test_absent_file_reads_empty(self) -> None:
        rows, cursor, restarted = q.read_results_since(
            path=Path(self._tmp.name) / "absent.jsonl"
        )
        self.assertEqual(rows, [])
        self.assertEqual(cursor.offset, 0)
        self.assertTrue(restarted)

    def test_the_cursor_carries_the_mtime_of_what_it_read(self) -> None:
        """A poller comparing against an mtime sampled AFTER the read would
        record a row appended during that read as already-seen. If that was a
        sweep's last row, the leaderboard stays one short until a manual
        refresh — silently."""
        q.append_result(_result(job_id="one"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)
        self.assertEqual(cursor.mtime, self.results.stat().st_mtime)

    def test_a_row_appended_after_the_read_changes_the_observed_mtime(self) -> None:
        q.append_result(_result(job_id="one"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)
        os.utime(self.results, (cursor.mtime + 5, cursor.mtime + 5))
        self.assertNotEqual(self.results.stat().st_mtime, cursor.mtime)
        rows, cursor2, _ = q.read_results_since(cursor, self.results)
        self.assertEqual(rows, [])
        self.assertEqual(cursor2.mtime, self.results.stat().st_mtime)

    def test_an_absent_file_has_a_zero_mtime_cursor(self) -> None:
        _, cursor, _ = q.read_results_since(path=Path(self._tmp.name) / "gone.jsonl")
        self.assertEqual(cursor.mtime, 0.0)

    def test_a_file_replaced_and_regrown_past_the_offset_resets(self) -> None:
        """Size alone cannot detect this, and neither can a line-boundary check:
        result lines are near enough uniform in length that a stale offset lands
        on a boundary of the NEW file. Only the inode distinguishes them, and
        without it one sweep's tail gets spliced onto another's rows."""
        for i in range(2):
            q.append_result(_result(job_id=f"old{i}"), self.results)
        _, cursor, _ = q.read_results_since(path=self.results)

        self.results.unlink()
        for i in range(6):
            q.append_result(_result(job_id=f"new{i}"), self.results)
        self.assertGreater(self.results.stat().st_size, cursor.offset)

        rows, _, restarted = q.read_results_since(cursor, self.results)
        self.assertTrue(restarted)
        self.assertEqual([r.job_id for r in rows], [f"new{i}" for i in range(6)])


class TestIncompleteSweepIsDisclosed(unittest.TestCase):
    def test_a_done_sweep_still_reports_a_missing_price_file(self) -> None:
        """A sweep that skipped a whole interval for want of its CSV finishes
        "done". Showing the reason only in the error phase would render it as an
        unqualified success with every 1h row silently absent."""
        state = q.QueueState(phase="done", done=9, total=9,
                             error="no price cache at data/SOL_1h.csv")
        text = q.summarise(state, [])
        self.assertIn("incomplete", text)
        self.assertIn("SOL_1h.csv", text)

    def test_a_clean_sweep_says_nothing_extra(self) -> None:
        self.assertNotIn("incomplete", q.summarise(q.QueueState(phase="done"), []))


if __name__ == "__main__":
    unittest.main()

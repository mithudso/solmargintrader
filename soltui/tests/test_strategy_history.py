"""The Strategies tab's test history and its three Backtest buttons.

History is derived from the background sweep's results file, so what it can get wrong is
counting and choosing: a duplicate line counted as a second test, a best-of-many row shown as
"the" result, an untestable strategy shown as merely untested, a button that starts a sweep that
has nothing to do. Each test targets one of those.
"""

from __future__ import annotations

import time
import unittest
from unittest import mock

from soltui import bgcontrol, bgqueue as q, bgworker, commands
from soltui.commands import dispatch
from soltui.tests.bridge_support import World


def row(job_id="a", strategy="rsi", horizon="medium", tier=0, sharpe=0.5, trades=20,
        evaluable=True, finished_at=1_700_000_000.0, ret=0.1, reason="") -> q.JobResult:
    return q.JobResult(
        job_id=job_id, strategy=strategy, horizon=horizon, asset="SOL", interval="1d", params={},
        tier=tier, variation="", family="mean-reversion", median_sharpe=sharpe, iqr=0.1,
        frac_positive=0.6, median_return=ret, trades=trades, evaluable=evaluable, reason=reason,
        finished_at=finished_at,
    )


class TestHistory(unittest.TestCase):
    def test_a_strategy_with_no_rows_is_absent_and_reads_as_not_tested(self) -> None:
        self.assertNotIn("macd", q.strategy_history([row()], "SOL"))
        self.assertEqual(q.StrategyHistory("macd").result_text, "not tested")
        self.assertFalse(q.StrategyHistory("macd").tested)

    def test_a_duplicated_job_counts_once(self) -> None:
        h = q.strategy_history([row("a"), row("a"), row("b", horizon="long")], "SOL")["rsi"]
        self.assertEqual(h.runs, 2)

    def test_the_newest_duplicate_wins(self) -> None:
        h = q.strategy_history([row("a", sharpe=0.1, finished_at=10.0),
                                row("a", sharpe=0.9, finished_at=20.0)], "SOL")["rsi"]
        self.assertEqual(h.preset.median_sharpe, 0.9)
        self.assertEqual(h.last_at, 20.0)

    def test_the_headline_is_the_cards_own_parameters_not_the_best_variation(self) -> None:
        rows = [row("p", tier=0, sharpe=-0.3), row("v", tier=1, sharpe=3.0)]
        h = q.strategy_history(rows, "SOL")["rsi"]
        self.assertEqual(h.preset.median_sharpe, -0.3)
        self.assertIn("Sharpe -0.30", h.result_text)

    def test_medium_stands_in_for_the_preset_before_other_horizons(self) -> None:
        rows = [row("s", horizon="short", sharpe=1.0), row("m", horizon="medium", sharpe=2.0)]
        self.assertEqual(q.strategy_history(rows, "SOL")["rsi"].preset.horizon, "medium")

    def test_other_assets_do_not_count(self) -> None:
        other = row("x")
        other.asset = "BTC"
        self.assertEqual(q.strategy_history([other], "SOL"), {})

    def test_thin_evidence_is_labelled_not_hidden(self) -> None:
        h = q.strategy_history([row(trades=3)], "SOL")["rsi"]
        self.assertIn("trade floor", h.result_text)
        self.assertEqual(h.ranked, 0)

    def test_a_failed_run_still_counts_as_tested_and_says_why(self) -> None:
        h = q.strategy_history([row(evaluable=False, trades=0, reason="warm-up too long")], "SOL")["rsi"]
        self.assertTrue(h.tested)
        self.assertIn("warm-up too long", h.result_text)

    def test_positive_count_is_over_ranked_runs_only(self) -> None:
        rows = [row("a", sharpe=1.0), row("b", sharpe=-1.0, tier=1), row("c", sharpe=2.0, tier=1, trades=2)]
        h = q.strategy_history(rows, "SOL")["rsi"]
        self.assertEqual((h.ranked, h.positive), (2, 1))
        self.assertIn("1/2 ranked runs positive", h.result_text)

    def test_a_row_written_before_dates_were_kept_says_so(self) -> None:
        self.assertEqual(q.format_when(0.0), "date not recorded")
        self.assertRegex(q.format_when(1_700_000_000.0), r"^\d{4}-\d\d-\d\d \d\d:\d\d$")

    def test_finished_at_round_trips_and_old_lines_still_load(self) -> None:
        self.assertEqual(q.JobResult.from_dict(__import__("json").loads(row().to_json())).finished_at,
                         1_700_000_000.0)
        legacy = __import__("json").loads(row().to_json())
        del legacy["finished_at"]
        self.assertEqual(q.JobResult.from_dict(legacy).finished_at, 0.0)

    def test_the_worker_stamps_every_row_it_writes(self) -> None:
        job = q.build_queue("SOL", max_tier=0)[0]
        before = time.time()
        self.assertGreaterEqual(bgworker.failed_result(job, ValueError("x")).finished_at, before)


class TestQueueFilter(unittest.TestCase):
    def test_strategies_restricts_the_queue(self) -> None:
        jobs = q.build_queue("SOL", max_tier=0, strategies=["dca", "ppo"])
        self.assertEqual({j.strategy for j in jobs}, {"dca", "ppo"})

    def test_none_means_everything_and_empty_means_nothing(self) -> None:
        self.assertGreater(len(q.build_queue("SOL", max_tier=0)), len(q.build_queue("SOL", max_tier=0, strategies=["dca"])))
        self.assertEqual(q.build_queue("SOL", max_tier=0, strategies=[]), [])

    def test_the_worker_command_carries_the_strategy_list(self) -> None:
        cmd = bgcontrol.worker_command("SOL", max_tier=0, strategies=["dca", "ppo"])
        self.assertEqual(cmd[cmd.index("--strategies") + 1:], ["dca", "ppo"])
        self.assertNotIn("--strategies", bgcontrol.worker_command("SOL"))


class TestCommands(unittest.TestCase):
    def setUp(self) -> None:
        self.world = World().__enter__()
        self.addCleanup(self.world.__exit__, None, None, None)
        (self.world.root / "bg").mkdir(parents=True, exist_ok=True)

    def history(self) -> dict:
        env = dispatch("strategies.history", {})
        self.assertTrue(env["ok"], env)
        return {r["name"]: r for r in env["result"]["rows"]}

    def test_every_registered_strategy_has_a_row_and_none_start_tested(self) -> None:
        from backtester.core.strategy_cards import load_all

        rows = self.history()
        self.assertIn("dca", rows)
        self.assertTrue(all(not r["tested"] for r in rows.values()))
        self.assertEqual(rows["rsi"]["last_tested"], "never")
        self.assertEqual(rows["rsi"]["result"], "not tested")
        catalog = dispatch("strategies.cards", {})
        self.assertTrue(catalog["ok"], catalog)
        cards = {row["key"]: row for row in catalog["result"]["cards"]}
        self.assertEqual(len(cards), len(load_all()))
        self.assertEqual({key for key, card in cards.items() if card["registered"]}, set(rows))
        self.assertTrue(cards["rsi"]["testable"])
        self.assertNotIn("tv_builtin_average_price", cards)
        self.assertNotIn("tv_gbc8qoy8_a_quick_guide_to_multi_timeframe_scaling", cards)
        self.assertNotIn("tv_builtin_supertrend", cards)
        for key in ("jlp_vs_sol_relative_value", "pairs_cointegration", "ladder_grid", "dca_bot", "triangular_arbitrage"):
            self.assertNotIn(key, cards)

    def test_a_recorded_result_shows_count_date_and_numbers(self) -> None:
        q.append_result(row("a", strategy="rsi", sharpe=0.42), q.RESULTS_PATH)
        q.append_result(row("b", strategy="rsi", horizon="long", sharpe=0.1), q.RESULTS_PATH)
        r = self.history()["rsi"]
        self.assertTrue(r["tested"])
        self.assertEqual(r["runs"], 2)
        self.assertRegex(r["last_tested"], r"^\d{4}-")
        self.assertIn("Sharpe +0.42", r["result"])

    def test_untested_count_matches_the_rows(self) -> None:
        q.append_result(row("a", strategy="rsi"), q.RESULTS_PATH)
        result = dispatch("strategies.history", {})["result"]
        self.assertEqual(result["tested"], 1)
        self.assertEqual(result["untested"], sum(1 for r in result["rows"] if r["testable"]) - 1)

    def test_selected_starts_the_worker_for_that_strategy_only(self) -> None:
        with mock.patch.object(bgcontrol, "start") as start:
            env = dispatch("queue.backtest", {"scope": "selected", "names": ["dca"]})
        self.assertTrue(env["ok"], env)
        self.assertTrue(env["result"]["started"])
        start.assert_called_once()
        self.assertEqual(start.call_args.kwargs["strategies"], ["dca"])
        self.assertEqual(start.call_args.kwargs["max_tier"], 0)

    def test_untested_leaves_out_strategies_that_already_have_a_result(self) -> None:
        q.append_result(row("a", strategy="rsi"), q.RESULTS_PATH)
        with mock.patch.object(bgcontrol, "start") as start:
            env = dispatch("queue.backtest", {"scope": "untested"})
        names = start.call_args.kwargs["strategies"]
        self.assertTrue(env["result"]["started"])
        self.assertNotIn("rsi", names)
        self.assertIn("dca", names)

    def test_all_includes_strategies_that_already_have_a_result(self) -> None:
        q.append_result(row("a", strategy="rsi"), q.RESULTS_PATH)
        with mock.patch.object(bgcontrol, "start") as start:
            dispatch("queue.backtest", {"scope": "all"})
        self.assertIn("rsi", start.call_args.kwargs["strategies"])

    def test_nothing_new_to_run_does_not_start_a_worker(self) -> None:
        for job in q.build_queue("SOL", max_tier=0, strategies=["dca"]):
            q.append_result(row(job.job_id, strategy="dca", horizon=job.horizon), q.RESULTS_PATH)
        with mock.patch.object(bgcontrol, "start") as start:
            env = dispatch("queue.backtest", {"scope": "selected", "names": ["dca"]})
        self.assertTrue(env["ok"])
        self.assertFalse(env["result"]["started"])
        self.assertIn("already tested", env["result"]["message"])
        start.assert_not_called()

    def test_all_untested_when_everything_is_tested_says_so(self) -> None:
        for strategy in commands._testable_strategies():
            q.append_result(row(f"id-{strategy}", strategy=strategy), q.RESULTS_PATH)
        with mock.patch.object(bgcontrol, "start") as start:
            env = dispatch("queue.backtest", {"scope": "untested"})
        self.assertFalse(env["result"]["started"])
        start.assert_not_called()

    def test_a_running_sweep_is_refused_with_the_way_out(self) -> None:
        with mock.patch.object(bgcontrol, "start", side_effect=RuntimeError("a background sweep is already running")):
            env = dispatch("queue.backtest", {"scope": "all"})
        self.assertFalse(env["ok"])
        self.assertIn("Queue tab", env["error"]["message"])

    def test_undertested_takes_the_never_tested_and_the_thinly_tested_with_variations(self) -> None:
        # rsi: 3 runs (enough). macd: 1 run (little testing). dca: none.
        for i, horizon in enumerate(("short", "medium", "long")):
            q.append_result(row(f"r{i}", strategy="rsi", horizon=horizon), q.RESULTS_PATH)
        q.append_result(row("m0", strategy="macd"), q.RESULTS_PATH)
        with mock.patch.object(bgcontrol, "start") as start:
            env = dispatch("queue.backtest", {"scope": "undertested"})
        self.assertTrue(env["ok"], env)
        self.assertTrue(env["result"]["started"])
        names = start.call_args.kwargs["strategies"]
        self.assertIn("dca", names)
        self.assertIn("macd", names)
        self.assertNotIn("rsi", names)
        self.assertEqual(start.call_args.kwargs["max_tier"], 1)   # near variations too
        self.assertIn("with fewer than 3 runs", env["result"]["message"])
        with mock.patch.object(bgcontrol, "start") as start:
            dispatch("queue.backtest", {"scope": "undertested", "min_runs": 4})
        self.assertIn("rsi", start.call_args.kwargs["strategies"])
        self.assertEqual(dispatch("queue.backtest", {"scope": "undertested", "min_runs": 0})["error"]["code"],
                         "bad_params")

    def test_backtest_command_reports_exclusions_as_candidates_not_failed_jobs(self) -> None:
        with mock.patch.object(bgcontrol, "start"), \
                mock.patch.object(commands, "_testable_strategies", return_value={"hurst_switch"}):
            env = dispatch("queue.backtest", {"scope": "undertested"})
        self.assertTrue(env["ok"], env)
        census = env["result"]["candidates"]
        self.assertGreater(census["excluded"], 0)
        self.assertEqual(census["requested"], census["eligible"] + census["excluded"])
        self.assertEqual(env["result"]["jobs"], census["eligible"])
        self.assertTrue(all(e["reason"] == "invalid_parameters" for e in census["exclusions"]))
        self.assertIn("excluded before evaluation", env["result"]["message"])

    def test_bad_requests_are_refused(self) -> None:
        self.assertEqual(dispatch("queue.backtest", {"scope": "everything"})["error"]["code"], "bad_params")
        self.assertEqual(dispatch("queue.backtest", {"scope": "selected"})["error"]["code"], "bad_params")
        env = dispatch("queue.backtest", {"scope": "selected", "names": ["no_such_strategy"]})
        self.assertFalse(env["ok"])
        self.assertIn("no_such_strategy", env["error"]["message"])


if __name__ == "__main__":
    unittest.main()

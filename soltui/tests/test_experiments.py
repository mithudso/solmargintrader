"""Simulation evidence is durable, bounded and cannot reopen inspected holdout dates."""
from __future__ import annotations

import concurrent.futures
import copy
import tempfile
import unittest
from pathlib import Path

from soltui import bots
from soltui.experiments import (
    ExperimentError,
    ExperimentStore,
    candidate_summary,
    compare_runs,
    import_tradingview,
    preview_space,
    sparse_heatmap,
)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ExperimentStore(Path(self.tmp.name))
        self.spec = {"source": "native", "bot": "grid", "candidates": [{"x": 1, "y": 1}, {"x": 2, "y": 2}],
                     "data_fingerprint": "historical-v1", "costs": {"fee_bps": 6}}
        self.run = self.store.create_run(self.spec)

    def cell(self, **values):
        return {"coin": "SOL", "split": "train", "start": 0, "end": 10, "status": "completed",
                "metrics": {"total_return": 0.1, "max_drawdown": 0.03, "trades": 2, "costs_usd": 3}, **values}

    def expose(self, run=None, start=0, end=10, coin="SOL"):
        return self.store.reserve_exploration(run or self.run, [{"coin": coin, "start": start, "end": end}])

    def final(self, run=None, start=10, end=20, coin="SOL"):
        self.store.freeze_candidate(run or self.run, "1")
        return self.store.reserve_holdout(run or self.run, "1", [{"coin": coin, "start": start, "end": end}])

    def test_run_identity_persists_and_cannot_bind_changed_evidence(self):
        self.assertEqual(ExperimentStore(self.store.root).get_run(self.run)["spec"], self.spec)
        self.assertEqual(self.store.create_run(self.spec, self.run), self.run)
        with self.assertRaisesRegex(ExperimentError, "different evidence"):
            self.store.create_run({**self.spec, "data_fingerprint": "changed"}, self.run)
        fetched = self.store.get_run(self.run)
        fetched["spec"]["data_fingerprint"] = "mutated"
        self.assertEqual(self.store.get_run(self.run)["spec"], self.spec)

    def test_cells_require_reservation_and_completed_evidence_is_immutable(self):
        with self.assertRaisesRegex(ExperimentError, "reserved"):
            self.store.record_cell(self.run, "0", "window", self.cell())
        self.expose()
        saved = self.store.record_cell(self.run, "0", "window", self.cell())
        self.assertEqual(self.store.record_cell(self.run, "0", "window", self.cell()), saved)
        with self.assertRaisesRegex(ExperimentError, "immutable"):
            self.store.record_cell(self.run, "0", "window", self.cell(metrics={"total_return": 0.2}))
        self.assertEqual(len(self.store.cells(self.run)), 1)

    def test_nonfinite_and_unknown_candidates_are_refused(self):
        with self.assertRaisesRegex(ExperimentError, "finite JSON"):
            self.store.create_run({**self.spec, "cost": float("nan")})
        self.expose()
        with self.assertRaisesRegex(ExperimentError, "finite JSON"):
            self.store.record_cell(self.run, "0", "window", self.cell(metrics={"return": float("inf")}))
        with self.assertRaisesRegex(ExperimentError, "candidate"):
            self.store.record_cell(self.run, "unknown", "window", self.cell())

    def test_failure_requires_error_and_can_be_retried(self):
        self.expose()
        with self.assertRaisesRegex(ExperimentError, "explicit error"):
            self.store.record_cell(self.run, "0", "w", self.cell(status="failed"))
        self.store.record_cell(self.run, "0", "w", self.cell(status="failed", error="bad source", metrics={}))
        self.store.record_cell(self.run, "0", "w", self.cell())
        self.assertEqual(self.store.cells(self.run)[0]["status"], "completed")

    def test_reservations_are_half_open_and_exploration_never_includes_final(self):
        self.expose()
        self.final()  # [0,10) and [10,20) are adjacent, never overlapping.
        self.store.record_cell(self.run, "1", "final", self.cell(split="holdout", start=10, end=20))
        self.assertEqual(self.store.cells(self.run), [])
        self.assertEqual(len(self.store.cells(self.run, include_holdout=True)), 1)
        with self.assertRaisesRegex(ExperimentError, "overlaps reserved final"):
            self.expose(start=15, end=30)
        with self.assertRaisesRegex(ExperimentError, "after start"):
            self.expose(start=30, end=30)

    def test_final_candidate_is_frozen_and_reservations_are_exactly_resumable(self):
        self.final()
        self.final()  # safe retry after process death.
        with self.assertRaisesRegex(ExperimentError, "already frozen"):
            self.store.freeze_candidate(self.run, "0")
        with self.assertRaisesRegex(ExperimentError, "cannot change"):
            self.final(start=11, end=20)

    def test_changed_search_cost_data_and_coin_case_do_not_refresh_dates(self):
        self.final()
        for change in ({"costs": {"fee_bps": 10}}, {"data_fingerprint": "v2"},
                       {"candidates": [{"x": 3}, {"x": 4}]}):
            other = self.store.create_run({**self.spec, **change})
            with self.assertRaisesRegex(ExperimentError, "spent dates"):
                self.final(other, coin="sol")

    def test_final_cannot_be_shifted_onto_prior_exploration_even_within_same_run(self):
        self.expose(start=0, end=20)
        with self.assertRaisesRegex(ExperimentError, "already exposed"):
            self.final(start=10, end=20)
        other = self.store.create_run(self.spec)
        with self.assertRaisesRegex(ExperimentError, "already exposed"):
            self.final(other, start=10, end=30)

    def test_concurrent_exposure_and_final_reservations_allow_exactly_one(self):
        other = self.store.create_run(self.spec)
        self.store.freeze_candidate(other, "1")
        def attempt(final):
            try:
                fresh = ExperimentStore(self.store.root)
                if final:
                    fresh.reserve_holdout(other, "1", [{"coin": "SOL", "start": 0, "end": 10}])
                else:
                    fresh.reserve_exploration(self.run, [{"coin": "SOL", "start": 0, "end": 10}])
                return True
            except ExperimentError:
                return False
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(attempt, [False, True]))
        self.assertEqual(sum(results), 1)

    def test_holdout_record_requires_reservation_and_frozen_pick(self):
        with self.assertRaisesRegex(ExperimentError, "frozen"):
            self.store.record_cell(self.run, "1", "w", self.cell(split="holdout"))
        self.store.freeze_candidate(self.run, "1")
        with self.assertRaisesRegex(ExperimentError, "reserved"):
            self.store.record_cell(self.run, "1", "w", self.cell(split="holdout"))

    def test_pause_cancel_requests_do_not_reopen_terminal_run_or_lose_race(self):
        self.assertEqual(self.store.request_control(self.run, "pause")["status"], "pause_requested")
        skipped = self.store.transition_run(self.run, "running", expected=["created"])
        self.assertFalse(skipped["transition_applied"])
        self.assertEqual(skipped["status"], "pause_requested")
        self.assertEqual(self.store.request_control(self.run, "cancel")["status"], "cancel_requested")
        self.store.update_run(self.run, status="completed")
        result = self.store.request_control(self.run, "pause")
        self.assertFalse(result["control_applied"])
        self.assertEqual(result["status"], "completed")

    def test_summary_preserves_rich_cost_alias_and_excludes_holdout(self):
        self.expose()
        self.store.record_cell(self.run, "0", "window", self.cell())
        self.final()
        self.store.record_cell(self.run, "1", "final", self.cell(split="holdout", start=10, end=20,
                              metrics={"total_return": 99}))
        rows = candidate_summary(self.store, self.run)
        self.assertEqual(rows[0]["metrics"]["total_cost"]["median"], 3)
        self.assertEqual(rows[1]["metrics"], {})

    def test_finalize_is_idempotent_and_pending_control_prevents_adoption(self):
        calls = []
        self.store.update_run(self.run, status="running")
        self.store.request_control(self.run, "pause")
        result = self.store.finalize_run(self.run, {"reliable": True}, apply=lambda summary: calls.append(summary))
        self.assertEqual(result["status"], "paused")
        self.assertEqual(calls, [])
        self.store.update_run(self.run, status="finalizing", error="old failure")
        self.store.update_run(self.run, error=None)
        self.assertIsNone(self.store.get_run(self.run)["error"])
        def adopt(summary):
            calls.append(summary)
            return {**summary, "adopted": True}
        result = self.store.finalize_run(self.run, {"reliable": True}, apply=adopt)
        self.assertTrue(result["summary"]["adopted"])
        self.store.finalize_run(self.run, {"reliable": False}, apply=adopt)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.store.get_run(self.run)["summary"], result["summary"])

    def test_finalization_callback_failure_rolls_back_lifecycle(self):
        self.store.update_run(self.run, status="finalizing")
        def fail(summary):
            raise OSError("disk full")
        with self.assertRaisesRegex(OSError, "disk full"):
            self.store.finalize_run(self.run, {}, apply=fail)
        self.assertEqual(self.store.get_run(self.run)["status"], "finalizing")
        self.assertEqual(self.store.request_control(self.run, "cancel")["status"], "cancel_requested")

    def test_sparse_heatmap_preserves_missing_combinations_and_conditions(self):
        self.expose()
        self.store.record_cell(self.run, "0", "w", self.cell())
        self.store.record_cell(self.run, "1", "w", self.cell(metrics={"total_return": 0.2}))
        result = sparse_heatmap(self.store, self.run, "x", "y")
        group = result["groups"][0]
        self.assertEqual(group["observed_points"], 2)
        self.assertEqual(group["possible_points"], 4)
        self.assertEqual(len(group["missing"]), 2)
        self.assertFalse(result["interpolated"])
        with self.assertRaisesRegex(ExperimentError, "train/validation"):
            sparse_heatmap(self.store, self.run, "x", "y", split="holdout")
        third = self.store.create_run({**self.spec, "candidates": [{"x": 1, "y": 1, "z": 1},
                                                                 {"x": 2, "y": 2, "z": 2}]})
        self.assertEqual(len(sparse_heatmap(self.store, third, "x", "y")["groups"]), 2)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.base = copy.deepcopy(bots.DEFAULTS["grid"])

    def test_decimal_range_fixed_enum_and_baseline_deduplication(self):
        result = preview_space("grid", self.base, {"range_pct": {"kind": "range", "start": 2, "stop": 2.3, "step": 0.1},
                     "spacing": {"kind": "enum", "values": ["arith", "geom"]},
                     "rungs": {"kind": "fixed", "value": 5}}, coins=["SOL", "BTC", "SOL"], windows=3)
        self.assertEqual(result["dimensions"]["range_pct"], [2.0, 2.1, 2.2, 2.3])
        self.assertEqual(result["evaluations"], result["candidate_count"] * 2 * 3)
        self.assertEqual(result["candidates"][0], self.base)
        self.assertIsNone(result["estimated_seconds"])
        fixed = preview_space("grid", self.base, {"rungs": {"kind": "fixed", "value": self.base["rungs"]}})
        self.assertEqual(fixed["candidate_count"], 1)

    def test_log_scale_positive_and_integer_domain_validation(self):
        space = {"range_pct": {"kind": "range", "start": 2, "stop": 32, "count": 3, "scale": "log"}}
        result = preview_space("grid", self.base, space)
        self.assertAlmostEqual(result["dimensions"]["range_pct"][1], 8)
        for spec in ({"kind": "fixed", "value": True}, {"kind": "fixed", "value": 4.5},
                     {"kind": "range", "start": 3, "stop": 5, "step": -1}):
            with self.subTest(spec=spec), self.assertRaises(ExperimentError):
                preview_space("grid", self.base, {"rungs": spec})
        with self.assertRaises(ExperimentError):
            preview_space("grid", self.base, {"range_pct": {"kind": "range", "start": 0, "stop": 5, "count": 3, "scale": "log"}})

    def test_unknown_fields_outside_domains_and_hard_budgets(self):
        for space in ({"oops": {"kind": "fixed", "value": 2}},
                      {"rungs": {"kind": "fixed", "value": 100}},
                      {"rungs": {"kind": "fixed", "value": 5, "secret": 1}},
                      {"rungs": {"kind": "fixed", "type": "fixed", "value": 5}}):
            with self.subTest(space=space), self.assertRaises(ExperimentError):
                preview_space("grid", self.base, space)
        with self.assertRaisesRegex(ExperimentError, "candidate budget"):
            preview_space("grid", self.base, {"rungs": {"kind": "enum", "values": [3, 4, 5]}}, max_candidates=2)
        with self.assertRaisesRegex(ExperimentError, "workload"):
            preview_space("grid", self.base, {}, coins=10, windows=6, max_evaluations=50)
        with self.assertRaises(ExperimentError):
            preview_space("grid", self.base, {}, max_candidates=1000)


META = {"bot": "grid", "coin": "SOL", "start": "2024-01-01", "end": "2024-02-01", "interval": "1h",
        "return_unit": "percent", "drawdown_unit": "percent", "fee_bps": 6, "slippage_bps": 2,
        "borrow_bps_per_day": 0, "fill_delay": 1, "currency": "USD", "strategy": "grid simulator", "data_source": "fixture"}
CSV = "candidate_id,total_return,max_drawdown,trades,total_cost,param.rungs\n0,10,3,12,4,5\n1,12,5,10,5,7\n"


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = ExperimentStore(Path(self.tmp.name))

    def test_normalized_csv_keeps_reported_units_and_never_promotes(self):
        run = import_tradingview(self.store, CSV, META)
        rows = self.store.cells(run["id"])
        self.assertEqual(rows[0]["metrics"]["total_return"], 0.1)
        self.assertEqual(rows[0]["reported_metrics"]["total_return"], 10)
        self.assertEqual(rows[0]["raw"]["total_return"], "10")
        self.assertEqual(run["spec"]["provenance"]["return_unit"], "percent")
        self.assertFalse(run["summary"]["promotion_eligible"])
        with self.assertRaisesRegex(ExperimentError, "imported"):
            self.store.freeze_candidate(run["id"], "0")
        with self.assertRaisesRegex(ExperimentError, "native"):
            self.store.reserve_holdout(run["id"], "0", [{"coin": "SOL", "start": 0, "end": 10}])

    def test_actual_optimizer_export_aliases_and_both_drawdown_columns(self):
        text = ("Net profit_all,Net profit_all_percent,Max equity drawdown_all,Max equity drawdown_all_percent,"
                "Total trades_all,Commission paid_all,Profit factor_all,Sharpe ratio_all,rungs\n"
                "1200,12,900,9,30,42,1.5,0.8,7\n")
        run = import_tradingview(self.store, text, META)
        row = self.store.cells(run["id"])[0]
        self.assertEqual(row["metrics"]["total_return"], 0.12)
        self.assertEqual(row["metrics"]["max_drawdown"], 0.09)
        self.assertEqual(row["metrics"]["net_profit"], 1200)
        self.assertEqual(row["metrics"]["trades"], 30)
        self.assertEqual(row["metrics"]["total_cost"], 42)
        self.assertEqual(run["spec"]["candidates"][0]["config"], {"rungs": "7"})

    def test_mixed_dated_and_unbound_rows_cannot_compare_as_bound_evidence(self):
        metadata = {k: v for k, v in META.items() if k not in {"coin", "start", "end"}}
        header = "candidate_id,coin,start,end,total_return\n"
        dated = "0,SOL,2024-01-01,2024-02-01,10\n"
        left = import_tradingview(self.store, header + dated, metadata)
        for extra in ("1,SOL,,,900\n", "1,,2024-01-01,2024-02-01,900\n"):
            with self.subTest(extra=extra):
                right = import_tradingview(self.store, header + dated + extra, metadata)
                result = compare_runs(self.store, left["id"], right["id"])
                self.assertFalse(result["comparable"])
                self.assertTrue(any("lack explicit coin/date bounds" in reason for reason in result["reasons"]))
                candidate = next(row for row in result["right_candidates"] if row["candidate_id"] == "1")
                self.assertEqual(candidate["unbound"], 1)
                self.assertEqual(candidate["metrics"]["total_return"]["median"], 9.0)
                self.assertEqual(len(self.store.get_run(right["id"])["spec"]["reported_rows"]), 2)

    def test_missing_units_remain_unknown_and_undated_rows_are_inspectable(self):
        run = import_tradingview(self.store, CSV)
        self.assertEqual(self.store.cells(run["id"]), [])
        self.assertEqual(run["summary"]["undated_rows"], 2)
        rows = candidate_summary(self.store, run["id"])
        self.assertEqual(rows[0]["undated"], 1)
        self.assertEqual(rows[0]["metrics"]["total_return"]["median"], None)
        self.assertEqual(rows[0]["metrics"]["trades"]["median"], 12)
        self.assertFalse(compare_runs(self.store, run["id"], run["id"])["comparable"])

    def test_malformed_nonfinite_duplicate_or_ambiguous_rows_do_not_create_run(self):
        for text in ("trades,trades\n1,2\n", "trades\n1,2\n", "total_return\nNaN\n", "trades\n1.5\n",
                     "candidate_id,trades,param.rungs\n0,1,5\n0,2,7\n", "split,trades\nholdout,1\n", 'trades\n"1\n'):

            with self.subTest(text=text), self.assertRaises(ExperimentError):
                import_tradingview(self.store, text, META)
        self.assertEqual(self.store.list_runs(), [])

    def test_comparison_requires_explicit_equal_context_and_actual_cell_coverage(self):
        a = import_tradingview(self.store, CSV, META)
        b = import_tradingview(self.store, CSV, {**META, "return_unit": "fraction", "drawdown_unit": "fraction"})
        self.assertTrue(compare_runs(self.store, a["id"], b["id"])["comparable"])
        cost = import_tradingview(self.store, CSV, {**META, "fee_bps": 0})
        result = compare_runs(self.store, a["id"], cost["id"])
        self.assertFalse(result["comparable"])
        self.assertIn("fee_bps: differs", result["reasons"])
        different = import_tradingview(self.store, "coin,start,end,total_return\nBTC,2024-03-01,2024-04-01,10\n", META)
        result = compare_runs(self.store, a["id"], different["id"])
        self.assertFalse(result["comparable"])
        self.assertIn("coin/date window coverage differs", result["reasons"])
        self.assertIn("declared coin conflicts with actual cell coverage", result["reasons"])

    def test_percentage_markers_cannot_be_relabelled_as_fraction_or_currency(self):
        for text in ("total_return\n10%\n", "Net profit_all_percent\n10\n"):
            with self.subTest(text=text), self.assertRaisesRegex(ExperimentError, "percentage evidence conflicts"):
                import_tradingview(self.store, text, {**META, "return_unit": "fraction"})

    def test_real_negative_engine_drawdown_matches_positive_tradingview_loss(self):
        import numpy as np

        from backtester.core.metrics import max_drawdown

        native = self.store.create_run({"source": "native", "bot": "grid", "provenance": {
            **META, "return_unit": "fraction", "drawdown_unit": "fraction"}, "candidates": [{"rungs": 5}, {"rungs": 7}]})
        self.store.reserve_exploration(native, [{"coin": "SOL", "start": META["start"], "end": META["end"]}])
        for index, trough in enumerate((90., 50.)):
            actual = max_drawdown(np.array([100., trough]), np.array([0, 1])).max_drawdown
            self.assertLess(actual, 0)
            self.store.record_cell(native, str(index), "w", {"coin": "SOL", "split": "validation", "start": META["start"],
                "end": META["end"], "status": "completed", "metrics": {"total_return": .1, "max_drawdown": actual}})
        external = import_tradingview(self.store,
            "candidate_id,Net profit_all_percent,Max equity drawdown_all_percent\n0,10,10\n1,10,50\n", META)
        result = compare_runs(self.store, native, external["id"])
        self.assertTrue(result["comparable"], result["reasons"])
        self.assertEqual([r["metrics"]["max_drawdown"]["median"] for r in result["left_candidates"]], [.1, .5])
        self.assertEqual([r["metrics"]["max_drawdown"]["median"] for r in result["right_candidates"]], [.1, .5])
        self.assertEqual(self.store.cells(native)[0]["metrics"]["max_drawdown"], -.1)
        self.assertEqual(self.store.cells(external["id"])[0]["reported_metrics"]["max_drawdown"], 10)
        signed = import_tradingview(self.store, "total_return,max_drawdown\n10,-10\n", META)
        self.assertEqual(self.store.cells(signed["id"])[0]["metrics"]["max_drawdown"], .1)
        self.assertEqual(self.store.cells(signed["id"])[0]["reported_metrics"]["max_drawdown"], -10)
        unknown = import_tradingview(self.store, "total_return,max_drawdown\n10,-10\n")
        self.assertIsNone(candidate_summary(self.store, unknown["id"])[0]["metrics"]["max_drawdown"]["median"])

    def test_native_import_comparison_uses_common_metrics_and_bound_windows(self):
        spec = {"source": "native", "bot": "grid", "provenance": {**META, "return_unit": "fraction", "drawdown_unit": "fraction"},
                "candidates": [{"rungs": "5"}, {"rungs": "7"}]}
        native = self.store.create_run(spec)
        self.store.reserve_exploration(native, [{"coin": "SOL", "start": META["start"], "end": META["end"]}])
        for i in (0, 1):
            self.store.record_cell(native, str(i), "w", {"coin": "SOL", "split": "validation", "start": META["start"],
                "end": META["end"], "status": "completed", "metrics": {"total_return": 0.1, "costs_usd": 4}})
        external = import_tradingview(self.store, CSV, META)
        result = compare_runs(self.store, native, external["id"])
        self.assertTrue(result["comparable"], result["reasons"])
        self.assertEqual(result["left_candidates"][0]["metrics"]["total_cost"]["median"], 4)


if __name__ == "__main__":
    unittest.main()

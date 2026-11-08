"""Causal ranking, evidence boundaries and single/bulk parity."""

from __future__ import annotations

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from soltui import bots, coin_fit


class CoinFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.path = Path(cls.directory.name)
        coin_fit.demo_data(cls.path, 30)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def settings(self):
        return SimpleNamespace(
            data_dir=str(self.path),
            asset="RANGE",
            fee_bps=6,
            slippage_bps=2,
            capital=1000,
        )

    def run_fit(self, coins="RANGE", **kwargs):
        return coin_fit.rank_coins(
            "grid",
            coins,
            self.settings(),
            days=30,
            config=dict(bots.GRID_DEFAULTS),
            **kwargs,
        )

    def test_single_bulk_equal_metrics_and_deterministic_sort(self):
        single = self.run_fit()["rows"][0]
        bulk = self.run_fit(["FALL", "RANGE", "RALLY"])
        same = next(r for r in bulk["rows"] if r["coin"] == "RANGE")
        self.assertEqual(single["metrics"], same["metrics"])
        self.assertEqual(single["score"], same["score"])
        self.assertEqual(bulk["rows"][0]["coin"], "RANGE")
        self.assertEqual(
            [r["coin"] for r in bulk["rows"]],
            [r["coin"] for r in self.run_fit(["RALLY", "RANGE", "FALL"])["rows"]],
        )

    def test_quick_does_not_score_holdout_prices(self):
        original = coin_fit.load_coin("RANGE", self.settings())
        first = self.run_fit()
        row = first["rows"][0]
        changed = {
            k: v.copy() if isinstance(v, np.ndarray) else v for k, v in original.items()
        }
        hold = changed["ts"] >= row["holdout_start"]
        for k in ("open", "high", "low", "close"):
            changed[k][hold] *= 0.2
        with patch.object(coin_fit, "load_coin", return_value=changed):
            second = self.run_fit()
        self.assertEqual(first["rows"][0]["score"], second["rows"][0]["score"])
        self.assertEqual(first["rows"][0]["metrics"], second["rows"][0]["metrics"])
        self.assertNotEqual(
            first["rows"][0]["data_sha256"], second["rows"][0]["data_sha256"]
        )

    def test_audit_respects_frozen_policy_costs_and_data(self):
        quick = self.run_fit()
        row = quick["rows"][0]
        audit = coin_fit.rank_coins(
            "grid",
            ["RANGE"],
            self.settings(),
            mode="audit",
            start=quick["common_start"],
            reference_end=quick["common_end"],
            days=30,
            config=quick["config"],
            policy=quick["policy"],
            fee_bps=quick["fee_bps"],
            slippage_bps=quick["slippage_bps"],
            capital=quick["capital_usd"],
            expected_data_sha256=row["data_sha256"],
            selection_id=quick["selection_id"],
        )
        result = audit["rows"][0]
        self.assertEqual(audit["selection_id"], quick["selection_id"])
        self.assertEqual(audit["errors"], {})
        self.assertEqual(len(result["windows"]), 10)
        self.assertEqual(sum(w["stress"] for w in result["windows"]), 5)
        self.assertEqual(
            next(f["value"] for f in result["template"] if f["metric"] == "as_of"),
            audit["common_end"],
        )
        self.assertEqual(result["fit"], "GOOD_FIT")

    def test_changed_cache_refuses_a_bound_audit(self):
        quick = self.run_fit()
        audit = self.run_fit(mode="audit", expected_data_sha256="0" * 64)
        self.assertEqual(audit["rows"][0]["fit"], "INSUFFICIENT_DATA")
        self.assertIn("changed since quick", audit["errors"]["RANGE"])
        self.assertEqual(quick["errors"], {})

    def test_missing_candidate_kept_and_wrong_cache_never_falls_back(self):
        result = self.run_fit(["RANGE", "MISSING"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertIn("MISSING", result["errors"])
        wrong = self.settings()
        wrong.data_dir = str(self.path / "not-there")
        with (
            patch.object(
                bots, "data_dir", side_effect=AssertionError("fallback called")
            ),
            self.assertRaisesRegex(bots.BotError, "no fallback"),
        ):
            coin_fit.rank_coins("grid", ["RANGE"], wrong)

    def test_minute_row_count_cannot_fabricate_full_hours(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "BAD_1m.csv"
            with path.open("w", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
                writer.writerows(
                    [1735689600 + h * 3600 + sec, 100, 100, 100, 100, 1]
                    for h in range(24 * 8)
                    for sec in range(60)
                )
            s = self.settings()
            s.data_dir = tmp
            result = coin_fit.rank_coins("grid", ["BAD"], s, days=7)
            self.assertEqual(result["rows"][0]["fit"], "INSUFFICIENT_DATA")
            self.assertIn("whole UTC minutes", result["errors"]["BAD"])

    def test_gaps_not_bridged_and_input_not_mutated(self):
        original = coin_fit.load_coin("RANGE", self.settings())
        checksum = coin_fit._hash(original)
        bad = {
            k: np.delete(v, 300) if isinstance(v, np.ndarray) else v
            for k, v in original.items()
        }
        with patch.object(coin_fit, "load_coin", return_value=bad):
            result = self.run_fit(mode="audit")
        self.assertIn("incomplete common window", result["errors"]["RANGE"])
        self.assertEqual(coin_fit._hash(original), checksum)

    def test_all22fields_present_and_unknowns_stay_unknown(self):
        result = self.run_fit()["rows"][0]
        self.assertEqual(len(result["template"]), 22)
        self.assertEqual(
            {v["metric"] for v in result["template"]}, set(coin_fit.TEMPLATE_FIELDS)
        )
        venue = next(v for v in result["template"] if v["metric"] == "venue_pair")
        self.assertEqual(venue["state"], "unknown")
        self.assertTrue(result["missing_evidence"])

    def test_no_bot_configs_or_results_written(self):
        with (
            patch.object(bots, "save_config", side_effect=AssertionError("write")),
            patch.object(bots, "_record", side_effect=AssertionError("write")),
        ):
            self.run_fit(mode="audit")

    def test_context_input_and_version_validation(self):
        with self.assertRaisesRegex(bots.BotError, "object for each coin"):
            self.run_fit(context={"RANGE": []})
        for version in (2, True):
            with self.assertRaisesRegex(bots.BotError, "version"):
                self.run_fit(policy={"version": version})
        with self.assertRaises(bots.BotError):
            self.run_fit(policy={"max_drawdown": float("nan")})

    def test_context_changes_identity_and_thesis_is_not_price_inference(self):
        params = {
            "mode": "audit",
            "days": 30,
            "context": {
                "RALLY": {
                    "investment_thesis": {
                        "approved": True,
                        "reason": "Explicit test thesis",
                        "source": "fixture:test",
                    }
                }
            },
        }
        positive = coin_fit.rank_coins(
            "scheduled_dca", ["RALLY"], self.settings(), **params
        )
        params["context"]["RALLY"]["investment_thesis"]["approved"] = False
        negative = coin_fit.rank_coins(
            "scheduled_dca", ["RALLY"], self.settings(), **params
        )
        unknown = coin_fit.rank_coins(
            "scheduled_dca", ["RALLY"], self.settings(), mode="audit", days=30
        )
        self.assertEqual(positive["rows"][0]["fit"], "GOOD_FIT")
        self.assertEqual(negative["rows"][0]["fit"], "POOR_FIT")
        self.assertEqual(unknown["rows"][0]["fit"], "INSUFFICIENT_DATA")
        self.assertNotEqual(positive["context_sha256"], negative["context_sha256"])

    def test_cancel_keeps_requested_rows_and_checks_between_windows(self):
        state = {"cancel": False}

        def progress(fraction, message):
            if "development fold2" in message:
                state["cancel"] = True

        result = self.run_fit(
            ["RANGE", "RALLY"],
            mode="audit",
            progress=progress,
            cancelled=lambda: state["cancel"],
        )
        self.assertTrue(result["cancelled"])
        self.assertEqual({r["coin"] for r in result["rows"]}, {"RANGE", "RALLY"})
        self.assertTrue(all(r["fit"] == "CANCELLED" for r in result["rows"]))

    def test_native_source_bad_ohlc_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = pd.read_csv(self.path / "RANGE_1h.csv")
            frame.loc[20, "high"] = frame.loc[20, "low"] - 1
            frame.to_csv(Path(tmp) / "BAD_1h.csv", index=False)
            settings = self.settings()
            settings.data_dir = tmp
            result = coin_fit.rank_coins("grid", ["BAD"], settings, days=30)
            self.assertEqual(result["rows"][0]["fit"], "INSUFFICIENT_DATA")

    def test_markdown_csv_include_costs_inventory_and_period(self):
        report = self.run_fit(mode="audit")
        markdown = coin_fit.render_report([report])
        self.assertIn("Pre-exit coin quantity", markdown)
        self.assertIn("Fees + slippage USD", markdown)
        rows = list(
            csv.DictReader(io.StringIO(coin_fit.render_report([report], "csv")))
        )
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["metric_end"])
        self.assertTrue(rows[0]["data_sha256"])
        self.assertTrue(rows[0]["costs_usd"])

    def test_cli_offline_demo_script_outputs_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.json"
            result = coin_fit.cli_main(
                [
                    "--demo",
                    "--coin",
                    "RANGE",
                    "--days",
                    "7",
                    "--format",
                    "json",
                    "--output",
                    str(out),
                ]
            )
            self.assertEqual(result, 0)
            parsed = json.loads(out.read_text())
            self.assertTrue(parsed["runs"][0]["synthetic"])
            self.assertEqual(parsed["runs"][0]["rows"][0]["coin"], "RANGE")

    def test_cli_validation_uses_exit2_without_traceback(self):
        for args in (
            ["--coin", "BTC", "--data-dir", str(self.path / "none")],
            ["--demo", "--fee-bps", "nan"],
        ):
            with (
                redirect_stderr(io.StringIO()) as captured,
                redirect_stdout(io.StringIO()),
            ):
                with self.assertRaises(SystemExit) as exc:
                    coin_fit.cli_main(args)
                self.assertEqual(exc.exception.code, 2)
                self.assertNotIn("Traceback", captured.getvalue())


if __name__ == "__main__":
    unittest.main()

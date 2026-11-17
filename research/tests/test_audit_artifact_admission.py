from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from research import coinbase50_study, shape_study, strategy_aux_compare, strategy_config_sweep
from research import coinbase50_report


class ArtifactAdmissionTests(unittest.TestCase):
    def test_renderer_refuses_changed_artifact_before_creating_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run, data, output = root / "run", root / "data", root / "output"
            run.mkdir()
            data.mkdir()
            universe = data / "universe.json"
            universe.write_text('{"assets":[]}')
            protocol = data / "protocol.json"
            protocol.write_text('{}')
            for name in ("cycle_summary.json", "clock_tests.json", "portfolios.json", "baselines.json", "selection.json"):
                (run / name).write_text('[]')
            curve = run / "portfolio_curves.npz"
            curve.write_bytes(b"original fixture")
            manifest = {"status": "complete", "data": str(data), "grid_eligible": [], "grid_excluded": [],
                        "universe_sha256": hashlib.sha256(universe.read_bytes()).hexdigest(),
                        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
                        "artifacts": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()}}
            (run / "manifest.json").write_text(json.dumps(manifest))
            curve.write_bytes(b"changed finite-result fixture")
            with (patch.object(sys, "argv", ["report", "--run", str(run), "--report", str(root / "report.md"), "--results", str(output)]),
                  patch.object(coinbase50_report.plt, "subplots", side_effect=AssertionError("render must not begin")),
                  self.assertRaisesRegex(ValueError, "artifact")):
                coinbase50_report.main()
            self.assertFalse(output.exists())

    def test_missing_reservation_source_is_not_verified_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                shape_study.protected_intervals(Path(directory) / "missing.sqlite3", ("BTC",))

    def test_receipt_checks_the_consumed_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.csv"
            original.write_text("timestamp,close\n1,100\n")
            (root / "BTC_1h.csv").write_text("timestamp,close\n1,200\n")
            (root / "BTC_1h.json").write_text(json.dumps({"csv": str(original), "sha256": hashlib.sha256(original.read_bytes()).hexdigest()}))
            with patch.object(coinbase50_study, "protected_intervals", return_value=[]), self.assertRaisesRegex(ValueError, "checksum"):
                coinbase50_study.read(root, "BTC", "1h")

    def test_cached_diagnostics_cannot_change_replicate_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "BTC_diagnostics.json").write_text(json.dumps({"binding": {}, "replicates": 19}))
            with (patch.object(coinbase50_study, "binding", return_value={}),
                  patch.object(coinbase50_study, "read", return_value=pd.DataFrame()),
                  self.assertRaisesRegex(ValueError, "replicate")):
                coinbase50_study.diagnostics((root, root, {"symbol": "BTC"}, 9999))

    def test_cache_reuse_rechecks_current_reservations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "BTC_diagnostics.json").write_text(json.dumps({"binding": {}, "replicates": 9999}))
            with (patch.object(coinbase50_study, "binding", return_value={}),
                  patch.object(coinbase50_study, "read", side_effect=ValueError("protected unsealed holdout")),
                  self.assertRaisesRegex(ValueError, "protected")):
                coinbase50_study.diagnostics((root, root, {"symbol": "BTC"}, 9999))

    def test_unterminated_result_is_not_committed_for_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            path.write_text('{"configuration_id":"A"}\n{"configuration_id":"B"}')
            self.assertEqual(strategy_config_sweep._read_done(path), {"A"})
            strategy_config_sweep._record(path, {"configuration_id": "C"})
            self.assertEqual(strategy_config_sweep._read_done(path), {"A", "C"})

    def test_abstaining_scorecards_produce_both_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = {"correct_calls": 0, "active_calls": 0, "accuracy": None, "coverage": 0.0, "majority_baseline": None}
            result = {"disclaimer": "synthetic", "protocol": "synthetic", "limitations": [],
                      "rows": [{"mechanism": "scorecard", "dataset": "synthetic", "original": {"accuracy": panel}, "candidate": {"accuracy": panel}}]}
            with (patch.object(strategy_aux_compare, "run", return_value=result),
                  patch.object(strategy_aux_compare, "resolve_data_dir", return_value=root),
                  patch.object(sys, "argv", ["aux", "--experiment", str(root), "--data-dir", str(root), "--prices-dir", str(root)]),
                  redirect_stdout(StringIO())):
                self.assertEqual(strategy_aux_compare.main(), 0)
            self.assertTrue((root / "results/auxiliary.json").is_file())
            self.assertIn("n/a", (root / "results/auxiliary.md").read_text())

    def test_refused_daily_inputs_do_not_abort_unrelated_mechanisms(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("SOL_1d", "BTC_1d", "ETH_1d", "SOL_1h"):
                (root / (name + ".csv")).write_text("timestamp\n0\n")
            with (patch.object(strategy_aux_compare, "ensure_snapshots"),
                  patch.object(strategy_aux_compare, "source_hashes", return_value={}),
                  patch.object(strategy_aux_compare, "load_registry"),
                  patch.object(strategy_aux_compare, "load_sample", side_effect=ValueError("invalid fixture"))):
                result = strategy_aux_compare.run(root, root, root)
            self.assertTrue({"peer_spread", "triangle", "scorecard"} <= {row["mechanism"] for row in result["rows"]})
            self.assertTrue(all(row.get("status") == "failed" for row in result["rows"] if row["mechanism"] == "peer_spread"))

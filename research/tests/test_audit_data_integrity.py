from __future__ import annotations

import tempfile
import unittest
import warnings
from concurrent.futures import Future
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from research import dso_audit, minute_sweep, perturb


class AuditDataIntegrityTests(unittest.TestCase):
    def report(self, median=1.0, iqr=1.0, evaluable=True):
        baseline = perturb.Trial("b", "baseline", median, iqr, 1.0, 0.1, 100, evaluable)
        trial = perturb.Trial("p", "variant", median + 0.25, 1.0, 1.0, 0.1, 100, True)
        return perturb.Report("x", "long", baseline, trials=[trial])

    def test_undefined_or_insufficient_baseline_cannot_be_stable(self):
        for report in (self.report(iqr=0), self.report(evaluable=False), self.report(median=float("nan"))):
            with self.subTest(baseline=report.baseline):
                self.assertTrue(report.verdict().startswith("INCONCLUSIVE"))

    def test_constant_rank_inputs_cannot_claim_directional_stability(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            text = perturb.render_batch("long", [self.report(median=x) for x in (1.0, 2.0, 3.0)])
        self.assertNotIn("MORE stable", text)
        self.assertIn("undefined", text)

    def test_batch_threads_selected_asset_without_evaluating(self):
        with patch.object(perturb, "run") as run, redirect_stderr(StringIO()):
            perturb.run_all_singles("long", 0.1, 8, 2, asset="BTC")
        self.assertTrue(run.called)
        self.assertTrue(all(call.kwargs.get("asset") == "BTC" for call in run.call_args_list))

    def test_changed_csv_invalidates_the_slice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            source.write_text("timestamp\n0\n60\n120\n")
            with (patch.object(minute_sweep, "SLICES", root / "slices"),
                  patch.object(minute_sweep, "minute_path", return_value=source),
                  patch.object(minute_sweep, "load_minutes", side_effect=lambda _: pd.read_csv(source))):
                first = minute_sweep.build_slice("BTC", 2, None)
                source.write_text("timestamp\n0\n60\n120\n180\n")
                second = minute_sweep.build_slice("BTC", 2, None)
                with np.load(second) as data:
                    self.assertEqual(int(data["timestamp"][-1]), 180)
                self.assertNotEqual(first, second)

    def test_interrupted_slice_does_not_publish_partial_zip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            source.write_text("timestamp\n0\n60\n")

            def fail(target, **_):
                if hasattr(target, "write"):
                    target.write(b"partial zip")
                else:
                    Path(target).write_bytes(b"partial zip")
                raise OSError("synthetic disk failure")

            with (patch.object(minute_sweep, "SLICES", root / "slices"),
                  patch.object(minute_sweep, "minute_path", return_value=source),
                  patch.object(minute_sweep, "load_minutes", return_value=pd.DataFrame({"timestamp": [0, 60]})),
                  patch.object(minute_sweep.np, "savez", side_effect=fail), self.assertRaises(OSError)):
                minute_sweep.build_slice("BTC", 2, None)
            self.assertEqual(list((root / "slices").glob("*.npz")), [])

    def test_unknown_measurements_are_explicit(self):
        frame = pd.DataFrame([{"strategy": "x", "_file": "fixture.csv", "median_sharpe": 1.0,
                               "total_trades": np.nan, "q1_sharpe": np.nan}])
        self.assertTrue(dso_audit.s3_evidence_floor(frame, 30))

    def test_all_failed_cells_have_nonzero_exit_without_starting_workers(self):
        class SyntheticPool:
            def __init__(self, **_):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_):
                pass

            def submit(self, *_):
                future = Future()
                future.set_result({"asset": "BTC", "strategy": "ma_crossover", "error": "fixture-failed"})
                return future

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.csv"
            source.write_text("timestamp\n0\n60\n")
            with (patch.object(minute_sweep, "OUT", root),
                  patch.object(minute_sweep, "minute_path", return_value=source),
                  patch.object(minute_sweep, "build_slice", return_value=source),
                  patch.object(minute_sweep, "render", return_value="FAILED CELLS"),
                  patch.object(minute_sweep, "ProcessPoolExecutor", SyntheticPool),
                  redirect_stdout(StringIO()), redirect_stderr(StringIO())):
                self.assertEqual(minute_sweep.main(["--asset", "BTC", "--strategy", "ma_crossover", "--bars", "2", "--workers", "1"]), 1)

    def test_zero_sharpe_does_not_prove_no_trades(self):
        frame = pd.DataFrame([{"strategy": "x", "_file": "fixture.csv", "median_sharpe": 1.0,
                               "total_trades": 100, "q1_sharpe": 0.0}])
        self.assertNotIn("paths took no trade", " ".join(dso_audit.s3_evidence_floor(frame, 30)))

    def test_unrelated_two_row_audit_keeps_two_trials(self):
        frame = pd.DataFrame({"strategy": ["a", "b"], "median_sharpe": [0.1, 0.2]})
        with patch.object(dso_audit, "bars_for", return_value=(1875, "synthetic")):
            result = dso_audit.s2_burden({"fixture_1d.csv": frame}, 1875, 8, 2, 5)
        self.assertIn("2 after", " ".join(result))

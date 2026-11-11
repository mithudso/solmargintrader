from __future__ import annotations

import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from research.volty_predictive_checks import (
    block_interval,
    daily_log_growth,
    digest,
    main,
    passive_equity,
)


class PredictiveCheckTests(unittest.TestCase):
    def test_complete_days_include_first_fee_and_exclude_partial_edges(self):
        timestamps = np.arange(1440 * 2 + 60) * 60
        equity = np.full(len(timestamps), 90.)
        equity[1440:] = 99.
        result = daily_log_growth(timestamps, equity, 100)
        np.testing.assert_allclose(result, [np.log(.9), np.log(1.1)])
        self.assertIsNone(daily_log_growth([0], [0], 100))

    def test_paired_block_interval_preserves_constant_difference(self):
        result = block_interval(np.full(35, -.01))
        np.testing.assert_allclose(result["ci95_daily_log_excess"], [-.01, -.01])
        self.assertEqual(block_interval(np.ones(20))["status"], "insufficient_complete_days")
        with self.assertRaises(ValueError):
            block_interval([float("nan")])

    def test_passive_pays_both_sides_and_only_holds_evaluation_window(self):
        bars = {"open": np.array([999., 100., 105.]), "close": np.array([999., 105., 110.])}
        equity = passive_equity(bars, 1, 10, 20, 100)
        units = 100 / (100 * 1.002 * 1.001)
        np.testing.assert_allclose(equity, [units * 105, units * 110 * .998 * .999])

    def test_wrong_source_hash_cannot_create_a_result(self):
        with TemporaryDirectory() as temp:
            source, output = Path(temp) / "bars.csv", Path(temp) / "result.json"
            source.write_text("not the frozen source\n")
            with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                main(["--data", str(source), "--expected-sha256", "0" * 64,
                      "--output", str(output)])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())

    def test_existing_evidence_is_never_replaced(self):
        with TemporaryDirectory() as temp:
            source, output = Path(temp) / "bars.csv", Path(temp) / "result.json"
            source.write_text("timestamp,open,high,low,close,volume\n" + "".join(
                f"{i * 60},{100 + i},{102 + i},{99 + i},{101 + i},1\n" for i in range(20)))
            output.write_text("previous evidence\n")
            with self.assertRaises(FileExistsError):
                main(["--data", str(source), "--expected-sha256", digest(source),
                      "--output", str(output)])
            self.assertEqual(output.read_text(), "previous evidence\n")


if __name__ == "__main__":
    unittest.main()

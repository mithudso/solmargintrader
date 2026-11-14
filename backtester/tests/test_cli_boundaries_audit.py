"""CLI failures preserve safe errors, source selection and explicit seed values."""

from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester import botcli, cli, gridcli, paircli
from backtester.core.data import SyntheticLoader


class CliBoundariesTests(unittest.TestCase):
    def test_triangle_bad_boolean_is_usage_error_and_missing_recording_is_unavailable(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            botcli.main(["triangle", "--snapshots", "missing.jsonl", "--use-displayed-size", "tru"])
        self.assertEqual(error.exception.code, 2)
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            self.assertEqual(botcli.main(["triangle", "--snapshots", "missing.jsonl"]), 1)

    def _frame(self, *, flat=False):
        values = np.full(80, 100.0) if flat else 100 + np.arange(80) * .1 + np.sin(np.arange(80))
        return pd.DataFrame({"timestamp": 1_609_459_200 + np.arange(80) * 86400,
                             **{name: values.copy() for name in ("open", "high", "low", "close")},
                             "volume": np.ones(80)})

    def test_malformed_csv_cells_are_not_echoed_by_loading_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            frame = self._frame()
            frame["close"] = frame["close"].astype(object)
            frame.loc[0, "close"] = "PRIVATE_API_CANARY"
            path = directory / "SOL_1d.csv"
            frame.to_csv(path, index=False)
            calls = [(cli.main, ["--data", str(path)]),
                     (gridcli.main, ["--lower", "80", "--upper", "120", "--data", str(path)]),
                     (botcli.main, ["dca", "--data", str(path), "--interval", "1d"]),
                     (paircli.main, ["--data-dir", str(directory)])]
            for invoke, arguments in calls:
                output = io.StringIO()
                with self.subTest(cli=invoke.__module__), redirect_stderr(output), redirect_stdout(io.StringIO()):
                    self.assertEqual(invoke(arguments), 1)
                    self.assertNotIn("PRIVATE_API_CANARY", output.getvalue())

    def test_invalid_or_ambiguous_synthetic_source_refuses_before_loading(self):
        calls = [(cli.main, ["--synthetic", "0"]),
                 (cli.main, ["--synthetic", "100", "--data", "ignored.csv"]),
                 (botcli.main, ["dca", "--synthetic", "0"])]
        for invoke, arguments in calls:
            with self.subTest(cli=invoke.__module__, arguments=arguments), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(invoke(arguments), 2)

    def test_explicit_zero_seed_reaches_the_synthetic_loader(self):
        with patch.object(cli, "SyntheticLoader", wraps=SyntheticLoader) as loader, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = cli.main(["--synthetic", "100", "--seed", "0", "--strategy", "buy_and_hold", "--start", "2020-01-01", "--no-charts"])
        self.assertEqual(code, 0)
        self.assertEqual(loader.call_args.kwargs["seed"], 0)

    def test_pair_invalid_cost_and_unavailable_diagnostic_return_clear_status(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name in ("SOL", "BTC"):
                self._frame(flat=True).to_csv(directory / f"{name}_1d.csv", index=False)
            common = ["--data-dir", str(directory), "--fit-window", "30"]
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(paircli.main([*common, "--fee-bps", "-1"]), 2)
            output = io.StringIO()
            with redirect_stderr(output), redirect_stdout(io.StringIO()):
                self.assertEqual(paircli.main(common), 1)
            self.assertIn("diagnostic", output.getvalue())

    def test_pair_short_split_refuses_without_traceback(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for name in ("SOL", "BTC"):
                frame = self._frame()
                if name == "BTC":
                    for column in ("open", "high", "low", "close"):
                        frame[column] += np.cos(np.arange(80) * .7) * .2
                frame.to_csv(directory / f"{name}_1d.csv", index=False)
            output = io.StringIO()
            with redirect_stderr(output), redirect_stdout(io.StringIO()):
                code = paircli.main(["--data-dir", str(directory), "--fit-window", "30", "--split", ".1"])
            self.assertEqual(code, 1)
            self.assertIn("split", output.getvalue())


if __name__ == "__main__":
    unittest.main()

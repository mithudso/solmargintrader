"""The gap opt-in cannot authorize malformed bars or replace a good cache."""

from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from backtester.core import fetch
from backtester.core.data import CsvLoader


def _bars() -> pd.DataFrame:
    return pd.DataFrame({
        "timestamp": [1_609_459_200, 1_609_632_000],
        "open": [100.0, 100.0],
        "high": [101.0, 101.0],
        "low": [99.0, 99.0],
        "close": [100.0, 100.0],
        "volume": [1.0, 1.0],
    })


class FetchValidationTests(unittest.TestCase):
    def _run(self, frame: pd.DataFrame, destination: Path, *, allow: bool) -> int:
        args = ["--out", str(destination), "--start", "2021-01-01", "--end", "2021-01-04"]
        if allow:
            args.append("--allow-gaps")
        with patch.object(fetch, "fetch_coinbase", return_value=frame), redirect_stderr(io.StringIO()):
            return fetch.main(args)

    def test_gap_opt_in_preserves_good_cache_when_values_are_invalid(self):
        for column, value in [("open", -1.0), ("close", float("nan")), ("volume", -1.0), ("high", 1.0)]:
            with self.subTest(column=column, value=value), tempfile.TemporaryDirectory() as temp:
                destination = Path(temp) / "cache.csv"
                original = b"existing verified cache\n"
                destination.write_bytes(original)
                frame = _bars()
                frame.loc[0, column] = value
                self.assertEqual(self._run(frame, destination, allow=True), 1)
                self.assertEqual(destination.read_bytes(), original)

    def test_gap_opt_in_still_writes_valid_incomplete_series(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "cache.csv"
            self.assertEqual(self._run(_bars(), destination, allow=True), 0)
            pd.testing.assert_frame_equal(pd.read_csv(destination), _bars())

    def test_default_refuses_gap_without_creating_cache(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "cache.csv"
            self.assertEqual(self._run(_bars(), destination, allow=False), 1)
            self.assertFalse(destination.exists())

    def test_explicit_midnight_cutoff_does_not_expand_to_whole_day(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "cache.csv"
            frame = _bars()
            frame.loc[1, "timestamp"] = frame.loc[0, "timestamp"] + 60
            frame.to_csv(destination, index=False)
            loader = CsvLoader(destination)
            self.assertEqual(len(loader.load("SOL", None, "2021-01-01", "1m")), 2)
            selected = loader.load("SOL", None, "2021-01-01 00:00:00", "1m")
            self.assertEqual(selected["timestamp"].tolist(), [1_609_459_200])


if __name__ == "__main__":
    unittest.main()

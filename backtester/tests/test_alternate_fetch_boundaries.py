"""Malformed provider pages and worker crashes must remain visible failures."""

from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backtester.core import fetch_minutes as fm
from backtester.core import fetch_minutes_alt as alt


class AlternateBoundariesTests(unittest.TestCase):
    def test_malformed_success_payloads_raise_the_declared_fetch_error(self):
        cases = [(alt._okx_rows, "code", "0", "data"), (alt._kucoin_rows, "code", "200000", "data"),
                 (alt._bitget_rows, "code", "00000", "data"), (alt._whitebit_rows, "success", True, "result")]
        for parse, key, value, rows_key in cases:
            for malformed in [None, {}, "invalid", [[1]], [[0, "PRIVATE_CANARY"]]]:
                with self.subTest(provider=parse.__name__, data=malformed):
                    with self.assertRaises(alt.AltFetchError) as caught:
                        parse({key: value, rows_key: malformed})
                    self.assertNotIn("PRIVATE_CANARY", str(caught.exception))

    def test_sanity_refuses_nonfinite_or_nonintegral_minute_values(self):
        for row in [[60, 10, float("inf"), 9, 11, 1], [60, 10, 12, 9, 11, float("inf")],
                    [60.5, 10, 12, 9, 11, 1], [61, 10, 12, 9, 11, 1]]:
            with self.subTest(row=row):
                self.assertEqual(alt.sane([row]), ([], 1))

    def test_worker_failure_produces_nonzero_exit_instead_of_silent_success(self):
        for error in [ValueError("PRIVATE_CANARY"), OSError("PRIVATE_CANARY"), RuntimeError("PRIVATE_CANARY")]:
            with self.subTest(error=type(error).__name__), tempfile.TemporaryDirectory() as temp:
                output = io.StringIO()
                with patch.object(fm, "DATA", Path(temp)), patch.object(alt, "DATA", Path(temp)), \
                     patch.object(alt, "fetch_asset", side_effect=error), redirect_stdout(output), redirect_stderr(output):
                    status = alt.main(["--assets", "TRX"])
                self.assertEqual(status, 1)
                self.assertIn("FAILED TRX", output.getvalue())
                self.assertNotIn("PRIVATE_CANARY", output.getvalue())


if __name__ == "__main__":
    unittest.main()

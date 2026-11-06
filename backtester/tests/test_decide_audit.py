"""Readout trust boundaries over synthetic arrays; no cache/network dependency."""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest.mock import patch

import numpy as np

from backtester.tests.test_decide import make_arrays
from research import decide


class ReadoutAuditTests(unittest.TestCase):
    def arrays(self):
        return {k: v.copy() for k, v in make_arrays([100, 101, 102, 103]).items()}

    def report(self, arrays=None, **kwargs):
        return decide.build_report(self.arrays() if arrays is None else arrays, asset='X', interval='1d', source='synthetic', checksum='a' * 64, keys=['buy_and_hold'], **kwargs)

    def test_classify_refuses_nonfinite_or_boolean_numeric_values(self):
        for previous, target, tolerance in [(0, 1, np.inf), (np.nan, 1, .01), (0, np.nan, .01), (0, np.inf, .01), (True, 1, .01), (0, 1, True)]:
            with self.subTest(values=(previous, target, tolerance)), self.assertRaises(ValueError):
                decide.classify(previous, target, tolerance)

    def test_report_refuses_invalid_execution_configuration(self):
        for kwargs in [{'tolerance': np.inf}, {'tolerance': np.nan}, {'fill_delay': np.nan}, {'fill_delay': .5}, {'fill_delay': True}, {'mode': 'unsupported'}, {'allow_short': 1}, {'now': np.nan}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.report(**kwargs)
        with patch.object(decide, 'CsvLoader'), patch.object(decide, 'frame_to_arrays', return_value=self.arrays()), patch.object(decide, 'checksum_frame', return_value='fake'), contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(decide.main(['--data', 'X_1d.csv', '--tolerance', 'inf', '--json']), 2)

    def test_staleness_refuses_nonfinite_clock_or_timestamp(self):
        for last, now in [(np.nan, 100), (100, np.nan), (100, np.inf), (np.inf, 100)]:
            with self.subTest(values=(last, now)), self.assertRaises(ValueError):
                decide.staleness(last, '1d', now=now)
        self.assertEqual(decide.staleness(200, '1d', now=100)['age_bars'], 0)

    def test_report_refuses_invalid_public_array_values(self):
        for field, value in [('close', np.nan), ('high', np.inf), ('open', 0), ('volume', -1), ('ts', np.nan)]:
            arrays = self.arrays()
            arrays[field] = arrays[field].astype(float)
            arrays[field][-1] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.report(arrays)
        arrays = self.arrays()
        arrays['high'][-1] = arrays['low'][-1] - 1
        with self.assertRaises(ValueError):
            self.report(arrays)

    def test_report_refuses_mismatched_or_multidimensional_arrays(self):
        arrays = self.arrays()
        arrays['volume'] = arrays['volume'][:-1]
        with self.assertRaises(ValueError):
            self.report(arrays)
        arrays = self.arrays()
        arrays['close'] = arrays['close'][:, None]
        with self.assertRaises(ValueError):
            self.report(arrays)

    def test_valid_report_is_strict_json(self):
        json.dumps(self.report(), allow_nan=False)
        odd = self.arrays()
        odd['ts'] = 1600000000 + np.arange(4) * 777
        # Preserve the existing documented unknown-spacing passthrough.
        json.dumps(self.report(odd), allow_nan=False)

    def test_explicit_asset_even_when_equal_to_old_default_wins(self):
        for args, expected in [(['--asset', 'SOL'], 'SOL'), (['--asset', 'ETH'], 'ETH'), ([], 'BTC')]:
            output = io.StringIO()
            with self.subTest(args=args), patch.object(decide, 'CsvLoader'), patch.object(decide, 'frame_to_arrays', return_value=self.arrays()), patch.object(decide, 'checksum_frame', return_value='fake'), patch.object(decide, 'build_report', side_effect=lambda *a, **kw: {'asset': kw['asset']}), contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(decide.main(['--data', 'BTC_1d.csv', '--json', *args]), 0)
            self.assertEqual(json.loads(output.getvalue())['asset'], expected)

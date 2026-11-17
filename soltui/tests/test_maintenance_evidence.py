"""Adversarial synthetic measurements never become rankable strategy evidence."""
import dataclasses
import json
import math
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from soltui import bgqueue, bgworker, config, signals


def result_row():
    return dict(job_id='fixture', strategy='rsi', horizon='medium', asset='SOL', interval='1d', params={}, tier=0, variation='', family='mean-reversion', median_sharpe=1.0, iqr=0.1, frac_positive=0.7, median_return=0.2, trades=50, evaluable=True)


class MeasurementBoundaryTests(unittest.TestCase):
    def test_evaluator_nonfinite_measurements_are_explicitly_unevaluable(self):
        job = bgqueue.Job('rsi','medium','SOL','1d',{})
        for field in ('median_sharpe','spread','frac_positive','median_return','total_trades'):
            value = dict(median_sharpe=1.,spread=.1,frac_positive=.7,median_return=.1,total_trades=50,insufficient=False,reason='')
            value[field] = float('inf')
            with self.subTest(field=field), mock.patch.object(bgworker,'run_cpcv',return_value=SimpleNamespace(**value)):
                result=bgworker.evaluate(job,{},object(),config.Settings())
            self.assertFalse(result.evaluable)
            self.assertFalse(result.ranked_ok)
            self.assertIn('invalid',result.reason)

    def test_nonfinite_or_missing_metrics_and_false_strings_are_not_rankable(self):
        for field in ('median_sharpe', 'iqr', 'frac_positive', 'median_return'):
            for value in (None, 'bad', float('inf'), float('-inf'), float('nan')):
                with self.subTest(field=field, value=value):
                    row = result_row()
                    row[field] = value
                    result = bgqueue.JobResult.from_dict(row)
                    self.assertFalse(result.ranked_ok)
                    self.assertFalse(result.evaluable)
        row = result_row()
        row['evaluable'] = 'false'
        self.assertFalse(bgqueue.JobResult.from_dict(row).ranked_ok)

    def test_direct_results_with_invalid_financial_evidence_cannot_rank(self):
        for value in (float('inf'), float('nan')):
            row = result_row()
            row['median_sharpe'] = value
            self.assertFalse(bgqueue.JobResult(**row).ranked_ok)

    def test_invalid_identifiers_are_rejected_before_grouping(self):
        for field in ('job_id', 'strategy', 'asset', 'interval', 'horizon', 'family', 'variation'):
            for value in (None, [], {}):
                with self.subTest(field=field, value=value):
                    row = result_row()
                    row[field] = value
                    with self.assertRaises((ValueError, TypeError)):
                        bgqueue.JobResult.from_dict(row)

    def test_infinite_counts_degrade_without_overflow(self):
        row = result_row()
        row['trades'] = float('inf')
        result = bgqueue.JobResult.from_dict(row)
        self.assertFalse(result.ranked_ok)
        self.assertEqual(result.trades, 0)
        self.assertEqual(bgqueue._as_int(float('inf')), 0)

    def test_signal_types_finiteness_and_constructor_minimums(self):
        defaults = signals.SignalDefaults()
        for field, value in [('sma_fast', True), ('sma_fast', 2.5), ('sma_fast', '2'), ('dual_skip', 0.5), ('dual_formation', 1), ('adx_period', 1), ('ou_fit_window', 19), ('vol_window', 1)]:
            with self.subTest(field=field, value=value), self.assertRaises(signals.SignalError):
                signals.validate(dataclasses.replace(defaults, **{field: value}))
        for field in dataclasses.fields(defaults):
            if type(field.default) is float:
                for value in (float('nan'), float('inf'), float('-inf')):
                    with self.subTest(field=field.name, value=value), self.assertRaises(signals.SignalError):
                        signals.validate(dataclasses.replace(defaults, **{field.name: value}))

    def test_nonmapping_settings_fail_as_config_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            for value in ([], 'bad', 7, True):
                path.write_text(json.dumps(value))
                with self.subTest(value=value), self.assertRaises(config.ConfigError):
                    config.load_settings(path)

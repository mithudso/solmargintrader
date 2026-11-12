"""Synthetic provider and cache failures never acquire real data."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester.core import cointegration, fetch, funding, ticks, universe
from backtester.core import fetch_minutes as minutes
from backtester.core import fetch_minutes_alt as alternate
from backtester.core.types import BAR_COLUMNS


def bars(timestamp=0):
    return pd.DataFrame([[timestamp, 1., 1., 1., 1., 1.]], columns=BAR_COLUMNS)


class AcquisitionIntegrityTests(unittest.TestCase):
    def test_empty_intermediate_candle_page_does_not_hide_older_history(self):
        with patch.object(fetch, '_get_json', side_effect=[[], [[0, 1, 1, 1, 1, 1]]]), patch.object(fetch.time, 'sleep'):
            result = fetch.fetch_coinbase('FIXTURE-USD', '1970-01-01', '1970-01-01T10:00:00', '1m', verbose=False)
        self.assertEqual(result.timestamp.tolist(), [0])

    def test_allow_gaps_never_allows_invalid_financial_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'out.csv'
            invalid = bars()
            invalid.loc[0, 'close'] = -1
            with patch.object(fetch, 'fetch_coinbase', return_value=invalid), redirect_stderr(StringIO()):
                self.assertEqual(fetch.main(['--asset', 'SOL', '--start', '1970-01-01', '--end', '1970-01-02', '--allow-gaps', '--out', str(target)]), 1)
            self.assertFalse(target.exists())

    def test_stalled_tick_pagination_is_not_complete(self):
        page = pd.DataFrame({'trade_id': [11], 'timestamp': [100.], 'price': [1.], 'size': [1.]})
        with patch.object(ticks, 'seek_trade_id', return_value=10), patch.object(ticks, '_trade_page', return_value=page):
            result = ticks.fetch_trades('FIXTURE-USD', '1970-01-01', '1970-01-01T00:03:00', verbose=False)
        self.assertTrue(result.attrs['truncated'])

    def test_tick_aggregation_refuses_missing_or_nonfinite_observations(self):
        for field in ('price', 'size', 'timestamp'):
            frame = pd.DataFrame({'trade_id': [1, 2], 'timestamp': [0., 1.], 'price': [1., 2.], 'size': [1., 1.]})
            frame.loc[0, field] = np.nan
            with self.subTest(field=field), self.assertRaises(ValueError):
                ticks.trades_to_bars(frame, '1m')

    def test_quote_currencies_do_not_share_a_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = universe.FetchPlan(available=('SOL',), products={'SOL': 'SOL-USDT'})
            universe.fetch_universe(plan, '1970-01-01', '1970-01-02', '1d', fetcher=lambda *_args, **_kw: bars(), out_dir=Path(tmp), verbose=False)
            self.assertTrue((Path(tmp) / 'SOL_USDT_1d.csv').exists())
            self.assertFalse((Path(tmp) / 'SOL_1d.csv').exists())

    def test_failed_universe_publication_preserves_the_previous_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'SOL_1d.csv'
            target.write_text('previous accepted bytes\n')
            frame = bars()
            def failed(target, **_kwargs):
                if hasattr(target, 'write'): target.write('partial')
                else: Path(target).write_text('partial')
                raise OSError('synthetic ENOSPC')
            plan = universe.FetchPlan(available=('SOL',), products={'SOL': 'SOL-USD'})
            with patch.object(frame, 'to_csv', side_effect=failed):
                result = universe.fetch_universe(plan, '', '', '1d', fetcher=lambda *_a, **_kw: frame, out_dir=Path(tmp), skip_existing=False, verbose=False)
            self.assertTrue(result['SOL'].startswith('FAILED'))
            self.assertEqual(target.read_text(), 'previous accepted bytes\n')

    def test_malformed_funding_page_cannot_finalize_a_valid_prefix(self):
        valid = [{'time': 3600000, 'fundingRate': '0.001', 'premium': '0'}]
        with patch.object(funding, 'MAX_ROWS_PER_REQUEST', 1), patch.object(funding, '_post_json', side_effect=[valid, {'unexpected': 'object'}]), patch.object(funding.time, 'sleep'), self.assertRaises(funding.FundingFetchError):
            funding.fetch_hyperliquid_funding('SYNTHETIC')

    def test_conflicting_duplicate_funding_payments_are_refused(self):
        rows = [{'time': 3600000, 'fundingRate': '0.001', 'premium': '0'}, {'time': 3600000, 'fundingRate': '0.002', 'premium': '0'}]
        with patch.object(funding, '_post_json', return_value=rows), self.assertRaises(funding.FundingFetchError):
            funding.fetch_hyperliquid_funding('SYNTHETIC')

    def test_one_malformed_funding_asset_cannot_abort_other_assets(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(funding, 'hyperliquid_universe', return_value=['BTC', 'SOL']), patch.object(funding, 'fetch_hyperliquid_funding', side_effect=[TypeError('synthetic provider shape'), pd.DataFrame([[3600, .001, 0]], columns=funding.FUNDING_COLUMNS)]):
            result = funding.fetch_funding_universe(['BTC', 'SOL'], out_dir=Path(tmp), skip_existing=False)
        self.assertEqual(result['BTC'].rows, 0)
        self.assertEqual(result['SOL'].rows, 1)

    def test_a_nonempty_truncated_minute_cache_is_not_complete(self):
        with patch.object(minutes, 'plan_windows', return_value=[0, 18000]), patch.object(minutes, 'load_progress', return_value={0, 18000}), patch.object(minutes, 'load_probe', return_value=None), patch.object(minutes, 'load_window_receipts', return_value={}, create=True):
            self.assertFalse(minutes.coverage('BTC', pd.DataFrame({'timestamp': [60]}), 1, now=36000).complete_fetch)

    def test_alternate_sanity_rejects_nonfinite_values(self):
        for column in range(6):
            row = [0., 1., 1., 1., 1., 1.]
            row[column] = float('inf')
            good, bad = alternate.sane([row])
            with self.subTest(column=column):
                self.assertEqual(good, [])
                self.assertEqual(bad, 1)

    def test_explosive_deterministic_series_is_not_stationary(self):
        self.assertFalse(cointegration.adf_test(np.exp(np.arange(80) * .1), lags=0).stationary_at_5pct)

    def test_engle_granger_uses_the_two_series_residual_calibration(self):
        rng = np.random.default_rng(7)
        x, y = np.cumsum(rng.normal(size=250)), np.cumsum(rng.normal(size=250))
        result = cointegration.engle_granger(x, y, lags=0)
        self.assertAlmostEqual(result.adf.critical['5%'], -3.33613 - 6.1101 / 249 - 6.823 / 249**2, places=8)


class MinuteReceiptTests(unittest.TestCase):
    def test_truncated_legacy_receipt_refetches_and_sparse_observation_can_resume(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(minutes, 'DATA', Path(tmp)), patch.object(minutes, 'plan_windows', return_value=[0]), patch.object(minutes, 'effective_windows', return_value=[0]), patch.object(minutes, 'load_probe', return_value=None):
            bars().to_csv(minutes.minute_path('FIX'), index=False)
            minutes.save_progress('FIX', {0}, planned_end=18000)
            with patch.object(minutes, 'get_candles', return_value=[[0, 1, 1, 1, 1, 1]]) as get:
                first = minutes.fetch_minutes('FIX', 1, workers=1, verbose=False)
            self.assertEqual(get.call_count, 1)
            self.assertTrue(first.complete_fetch)
            with patch.object(minutes, 'get_candles', side_effect=AssertionError('durable sparse receipt should resume')):
                second = minutes.fetch_minutes('FIX', 1, workers=1, verbose=False)
            self.assertTrue(second.complete_fetch)

    def test_explicit_refetch_replaces_stale_values(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(minutes, 'DATA', Path(tmp)):
            frame = pd.concat([bars(), bars()], ignore_index=True)
            frame.loc[1, ['close', 'high']] = 2
            frame.to_csv(minutes.minute_path('FIX'), index=False)
            self.assertEqual(minutes.load_minutes('FIX').close.tolist(), [2])

    def test_all_empty_fetch_returns_explicit_incomplete_coverage(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(minutes, 'DATA', Path(tmp)), patch.object(minutes, 'plan_windows', return_value=[0]), patch.object(minutes, 'effective_windows', return_value=[0]), patch.object(minutes, 'load_probe', return_value=None), patch.object(minutes, 'get_candles', return_value=[]):
            result = minutes.fetch_minutes('FIX', 1, workers=1, resume=False, verbose=False)
            self.assertEqual(result.bars, 0)
            self.assertFalse(result.complete_fetch)

    def test_alternate_completion_uses_only_its_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(alternate, 'DATA', Path(tmp)), patch.object(alternate, 'minute_path', return_value=Path(tmp) / 'FIX_1m.csv'):
            source = alternate.minute_path('FIX')
            bars().to_csv(source, index=False)
            state = {'complete': True, 'cache_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
            alternate.progress_path('FIX').write_text(json.dumps(state))
            self.assertTrue(alternate.coverage('FIX', bars(), 1).complete_fetch)
            state['complete'] = False
            alternate.progress_path('FIX').write_text(json.dumps(state))
            self.assertFalse(alternate.coverage('FIX', bars(), 1).complete_fetch)

    def test_unexpected_alternate_worker_error_is_a_cli_failure(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(alternate, 'fetch_asset', side_effect=RuntimeError('synthetic worker failure')), patch.object(alternate, 'minute_path', return_value=Path(tmp) / 'absent.csv'), redirect_stderr(StringIO()):
            self.assertEqual(alternate.main(['--assets', 'TRX']), 1)

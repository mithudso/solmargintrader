"""Invalid market observations never become complete replay or funding evidence."""
from contextlib import contextmanager
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester.core import compound, funding, ticks


class EvidenceInputTests(unittest.TestCase):
    def _funding(self, times):
        return pd.DataFrame({'timestamp': times, 'funding_rate': [0.001] * len(times),
                             'premium': [float('nan')] * len(times)})

    def test_funding_epoch_and_rate_shape_refuse_without_truncating(self):
        for stamp in (-1, .5, float('inf'), True):
            with self.subTest(stamp=stamp), self.assertRaises(funding.FundingFetchError):
                funding.validate_funding(self._funding([stamp]))
        # Actual historical settlement spacing need not be a uniform hour.
        self.assertEqual(len(funding.validate_funding(self._funding([3600, 7199, 10800]))), 3)

    def test_funding_nonprogress_or_nonlist_page_is_not_successful_partial_history(self):
        first = [{'time': 3600000, 'fundingRate': '.001'},
                 {'time': 7200000, 'fundingRate': '.001'}]
        for second in (first, {'private': 'PRIVATE_CANARY'}):
            with self.subTest(second=type(second).__name__), patch.object(funding, 'MAX_ROWS_PER_REQUEST', 2), patch.object(funding, '_post_json', side_effect=[first, second]), patch.object(funding.time, 'sleep'):
                with self.assertRaises(funding.FundingFetchError):
                    funding.fetch_hyperliquid_funding('BTC')

    def test_funding_conflicting_duplicate_timestamp_is_not_silently_kept(self):
        page = [{'time': 3600000, 'fundingRate': '.001'},
                {'time': 3600000, 'fundingRate': '.002'}]
        with patch.object(funding, '_post_json', return_value=page), self.assertRaises(funding.FundingFetchError):
            funding.fetch_hyperliquid_funding('BTC')

    def test_provider_error_text_stays_out_of_public_funding_error_and_events(self):
        @contextmanager
        def response(*args, **kwargs):
            yield io.BytesIO(json.dumps({'error': 'PRIVATE_CANARY'}).encode())
        with patch.object(funding.urllib.request, 'urlopen', response):
            with self.assertLogs('backtester.market', level='INFO') as events:
                with self.assertRaises(funding.FundingFetchError) as error:
                    funding._post_json({'type': 'meta'}, retries=1)
            self.assertNotIn('PRIVATE_CANARY', str(error.exception) + str(events.output))
            self.assertEqual([e.outcome for e in events.records], ['attempt', 'failed'])

    def test_invalid_tick_fields_refuse_instead_of_becoming_an_ohlcv_bar(self):
        normal = {'trade_id': 2, 'price': '100', 'size': '1', 'side': 'buy',
                  'time': '2026-07-06T00:00:00Z'}
        for key, value in [('trade_id', 2.5), ('trade_id', True), ('price', 'nan'),
                           ('size', '-1'), ('side', 'PRIVATE_CANARY')]:
            with self.subTest(key=key, value=value), self.assertRaises(ticks.FetchError):
                ticks._parse_trades([{**normal, key: value}])

    def test_nonprogress_tick_walk_carries_truncation(self):
        page = pd.DataFrame({'timestamp': [pd.Timestamp('2026-07-06T00:00:10Z').timestamp()],
                             'trade_id': [10], 'price': [100.], 'size': [1.], 'side': ['buy']})
        with patch.object(ticks, 'seek_trade_id', return_value=10), patch.object(ticks, '_trade_page', return_value=page), patch.object(ticks.time, 'sleep'):
            out = ticks.fetch_trades('BTC-USD', '2026-07-06', '2026-07-07', verbose=False)
        self.assertTrue(out.attrs['truncated'])

    def _bars(self):
        return pd.DataFrame({'timestamp': np.arange(10) * 60,
                             **{key: np.full(10, 100.) for key in ('open', 'high', 'low', 'close')},
                             'volume': np.ones(10)})

    def test_compound_loader_does_not_repair_duplicate_or_fractional_observations(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bars.csv'
            for frame in (pd.concat([self._bars(), self._bars().iloc[:1]]),
                          self._bars().assign(timestamp=lambda d: d.timestamp + .5)):
                frame.to_csv(path, index=False)
                with self.subTest(rows=len(frame)), self.assertRaises(compound.CompoundDataError):
                    compound._read(path)

    def test_compound_resample_refuses_duplicate_or_offgrid_source_minutes(self):
        for frame in (pd.concat([self._bars(), self._bars().iloc[:1]]),
                      self._bars().assign(timestamp=lambda d: d.timestamp + 1)):
            with self.subTest(rows=len(frame)), self.assertRaises(compound.CompoundDataError):
                compound.resample_complete(frame)


class OfflineCacheTests(unittest.TestCase):
    def _frame(self):
        return pd.DataFrame({'timestamp': [3600, 7200], 'funding_rate': [.001, .002],
                             'premium': [float('nan')] * 2})

    def test_funding_summary_reads_selected_cache_without_requesting_the_network(self):
        from contextlib import redirect_stdout, redirect_stderr
        with tempfile.TemporaryDirectory() as temp:
            self._frame().to_csv(Path(temp) / 'BTC_funding_1h.csv', index=False)
            with patch.object(funding, 'hyperliquid_universe', side_effect=AssertionError('unexpected network')), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(funding.main(['--assets', 'BTC', '--summary', '--out-dir', temp]), 0)

    def test_cached_funding_is_validated_before_it_can_be_reported_as_success(self):
        with tempfile.TemporaryDirectory() as temp:
            self._frame().assign(timestamp=[3600, 3600]).to_csv(Path(temp) / 'BTC_funding_1h.csv', index=False)
            with patch.object(funding, 'hyperliquid_universe', return_value=['BTC']):
                result = funding.fetch_funding_universe(['BTC'], out_dir=Path(temp))
            self.assertEqual(result['BTC'].rows, 0)

    def test_malformed_product_catalogue_is_unavailable_instead_of_empty_listed_universe(self):
        from backtester.core import universe
        with self.assertRaises(universe.FetchError):
            universe.list_coinbase_products(lambda _url: {'error': 'PRIVATE_CANARY'})


if __name__ == '__main__':
    unittest.main()

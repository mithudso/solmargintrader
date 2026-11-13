"""Synthetic evidence and launch boundaries; no external data or strategy search."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from research import (
    candle_gap_audit,
    coinbase50_study,
    dso_audit,
    grid_holdout,
    meta_analysis,
    strategy_aux_compare,
    tick_backfill,
)
from research.candle_crosscheck import compare
from research.strategy_config_sweep import _derived_interval


def candles(timestamps):
    return pd.DataFrame({'timestamp': timestamps, 'open': 100., 'high': 101.,
                         'low': 99., 'close': 100., 'volume': 1.})


class AuditBoundaryTests(unittest.TestCase):
    def test_tick_failure_never_means_no_trades(self):
        with (patch.object(candle_gap_audit, 'fetch_trades', side_effect=OSError('private failure canary')),
              redirect_stderr(io.StringIO()), self.assertRaisesRegex(RuntimeError, 'tick_fetch_unavailable')):
            candle_gap_audit.classify_run('TEST-USD', (60, 60), 60)
        with patch.object(candle_gap_audit, 'fetch_trades', return_value=pd.DataFrame(columns=['timestamp', 'size'])):
            result = candle_gap_audit.classify_run('TEST-USD', (60, 60), 60)
        self.assertEqual(result['verdict'], 'quiet (no trades)')
        self.assertEqual(result['trades'], 0)

    def test_unavailable_repair_cannot_publish_a_successful_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candles([0, 120]).to_csv(root / 'TEST_1m.csv', index=False)
            report = root / 'report.md'
            with (patch.object(candle_gap_audit, 'fetch_trades', side_effect=TimeoutError('private failure canary')),
                  redirect_stderr(io.StringIO()) as error):
                code = candle_gap_audit.main(['--assets', 'TEST', '--data-dir', str(root),
                    '--suffix', '', '--repair', '--out-dir', str(root / 'repaired'), '--report', str(report)])
            self.assertFalse(report.exists(), 'Unavailable ticks produced a successful audit report')
            self.assertFalse((root / 'repaired').exists())
            self.assertEqual(code, 3)
            self.assertIn('tick_fetch_unavailable', error.getvalue())
            self.assertNotIn('private failure canary', error.getvalue())

    def test_consolidated_data_and_hash_share_one_source_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'evidence.json'
            original = b'{"figure":1}'
            source.write_bytes(original)
            read = Path.read_bytes

            def replace_after_read(path):
                raw = read(path)
                if path.resolve() == source.resolve():
                    path.write_bytes(b'{"figure":2}')
                return raw

            with patch.object(Path, 'read_bytes', replace_after_read):
                artifact = meta_analysis.consolidate([source])['artifacts'][0]
            self.assertEqual(artifact['data'], {'figure': 1})
            self.assertEqual(artifact['sha256'], hashlib.sha256(original).hexdigest())
            self.assertEqual(artifact['bytes'], len(original))

    def test_compressed_csv_still_binds_original_compressed_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'rows.csv.gz'
            original = gzip.compress(b'coin,value\nTEST,7\n')
            source.write_bytes(original)
            artifact = meta_analysis.consolidate([source])['artifacts'][0]
            self.assertEqual(artifact['data'], [{'coin': 'TEST', 'value': '7'}])
            self.assertEqual(artifact['sha256'], hashlib.sha256(original).hexdigest())

    def test_holdout_parse_and_digest_share_the_same_csv_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'bars.csv'
            candles(grid_holdout.HOLDOUT_START_TS + np.arange(3) * 86400).to_csv(source, index=False)
            original = source.read_bytes()
            reader = pd.read_csv

            def replace_after_parse(value, *args, **kwargs):
                frame = reader(value, *args, **kwargs)
                source.write_bytes(original.replace(b'100.0', b'200.0'))
                return frame

            with patch.object(grid_holdout.pd, 'read_csv', replace_after_parse):
                result = grid_holdout.run(source)
            self.assertEqual(result['first_close'], 100.)
            self.assertEqual(result['data_sha256'], hashlib.sha256(original).hexdigest())

    def test_sweep_help_and_invalid_input_do_not_start_strategy_work(self):
        script = Path(__file__).resolve().parents[1] / 'sweep_untested.py'
        program = '''
from pathlib import Path
import runpy, sys
from research import sweep
script, marker = sys.argv[1:3]
def blocked(*args, **kwargs):
    Path(marker).write_text('strategy work attempted')
    raise RuntimeError('test blocked strategy execution')
sweep.load_horizon = blocked
sys.argv = [script, *sys.argv[3:]]
runpy.run_path(script, run_name='__main__')
'''
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / 'attempted'
            for option, code in [('--help', 0), ('--unknown', 2)]:
                with self.subTest(option=option):
                    marker.unlink(missing_ok=True)
                    result = subprocess.run([sys.executable, '-B', '-c', program, str(script), str(marker), option],
                        check=False, capture_output=True, text=True, timeout=5)
                    self.assertFalse(marker.exists(), 'Argument handling started strategy work')
                    self.assertEqual(result.returncode, code, result.stderr)
                    self.assertIn('usage:', result.stdout + result.stderr)

    def test_incomplete_or_invalid_fine_bars_cannot_pass_row_count_check(self):
        fine = candles(np.arange(24) * 3600)
        coarse = candles([0])
        coarse.volume = 24.
        result = compare(fine, coarse, 86400, 3600)
        self.assertEqual(result['compared'], 1)
        self.assertTrue(all(count == 0 for count in result['fields'].values()))
        duplicate, nonfinite, unaligned = fine.copy(), fine.copy(), fine.copy()
        duplicate.loc[23, 'timestamp'] = duplicate.loc[22, 'timestamp']
        nonfinite.loc[4, 'high'] = float('nan')
        unaligned.timestamp += 1
        for frame in (duplicate, nonfinite, unaligned):
            with self.subTest(frame=frame.timestamp.iloc[-1]), self.assertRaises(ValueError):
                compare(frame, coarse, 86400, 3600)

    def test_sidecar_cannot_verify_a_different_csv_than_the_requested_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original, actual = root / 'original.csv', root / 'TEST_15m.csv'
            candles([0, 900, 1800]).to_csv(original, index=False)
            candles([0, 900, 1800]).assign(close=100.5).to_csv(actual, index=False)
            (root / 'TEST_15m.json').write_text(json.dumps({
                'csv': str(original), 'sha256': hashlib.sha256(original.read_bytes()).hexdigest()}))
            with (patch.object(coinbase50_study, 'protected_intervals', return_value=[]),
                  self.assertRaisesRegex(ValueError, 'source checksum changed')):
                coinbase50_study.read(root, 'TEST', '15m')

    def test_tampered_derived_cache_is_refused_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'TEST_1m.csv'
            candles(np.arange(60) * 60).to_csv(source, index=False)
            target = _derived_interval(source, 'TEST', '1h', root / 'output')
            changed = target.read_bytes().replace(b'100.0', b'100.5')
            target.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, 'derived.*(checksum|binding)'):
                _derived_interval(source, 'TEST', '1h', root / 'output')
            self.assertEqual(target.read_bytes(), changed)

    def test_derived_source_hash_and_candles_use_one_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'TEST_1m.csv'
            candles(np.arange(60) * 60).to_csv(source, index=False)
            original = source.read_bytes()
            reader = pd.read_csv

            def replace_before_parse(value, *args, **kwargs):
                source.write_bytes(original.replace(b'100.0', b'100.5'))
                return reader(value, *args, **kwargs)

            with patch('pandas.read_csv', replace_before_parse):
                target = _derived_interval(source, 'TEST', '1h', root / 'output')
            self.assertEqual(pd.read_csv(target).close.iloc[0], 100.)
            marker = json.loads(target.with_suffix(target.suffix + '.source.json').read_text())
            self.assertEqual(marker['sha256'], hashlib.sha256(original).hexdigest())

    def test_abstaining_auxiliary_accuracy_is_reported_as_undefined(self):
        panel = {'accuracy': None, 'correct_calls': 0, 'active_calls': 0,
                 'coverage': None, 'majority_baseline': None}
        result = {'rows': [{'mechanism': 'scorecard', 'dataset': 'fixture',
                           'original': {'status': 'ran', 'accuracy': panel},
                           'candidate': {'status': 'ran', 'accuracy': panel}}],
                  'disclaimer': 'synthetic fixture', 'protocol': 'no replay', 'limitations': []}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (patch.object(strategy_aux_compare, 'run', return_value=result),
                  patch.object(sys, 'argv', ['aux', '--experiment', str(root), '--data-dir', str(root), '--prices-dir', str(root)]),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(strategy_aux_compare.main(), 0)
            report = (root / 'results/auxiliary.md').read_text()
            self.assertIn('undefined', report)
            self.assertIn('0/0', report)

    def test_nonfinite_sharpe_never_receives_an_attribution_rank(self):
        frames = {
            'a': pd.DataFrame({'strategy': ['missing', 'control'], 'median_sharpe': [np.inf, 1.]}),
            'b': pd.DataFrame({'strategy': ['missing', 'control'], 'median_sharpe': [0., 1.]}),
        }
        self.assertEqual(dso_audit.s5_attribution(frames, swing=1), [])

    def test_nonadvancing_tick_page_cannot_complete_or_publish_backfill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / 'checkpoints/TEST_1m_2026-01-01_2026-01-02.json'
            checkpoint.parent.mkdir()
            binding = tick_backfill._checkpoint_binding('TEST-USD', '1m',
                pd.Timestamp('2026-01-01T00:00:00Z').timestamp(),
                pd.Timestamp('2026-01-02T00:00:00Z').timestamp())
            checkpoint.write_text(json.dumps({'binding': binding, 'cursor': 50, 'pages': 1, 'trades': 1, 'done': False, 'bars': {}}))
            prior = checkpoint.read_bytes()
            output = root / 'output/TEST_1m_2026-01-01_2026-01-02_from_ticks.csv'
            output.parent.mkdir()
            output.write_bytes(b'preserved earlier output\n')
            page = pd.DataFrame({'timestamp': [int(pd.Timestamp('2026-01-01T00:01:00Z').timestamp())],
                                 'trade_id': [50], 'price': [100.], 'size': [1.]})
            with (patch.object(tick_backfill, '_page', return_value=page),
                  patch.object(tick_backfill, 'seek_trade_id', side_effect=AssertionError('network boundary')),
                  patch.object(tick_backfill, '_stop', False), redirect_stderr(io.StringIO()),
                  self.assertRaisesRegex(tick_backfill.FetchError, 'nonprogress')):
                tick_backfill.backfill('TEST', 'USD', '2026-01-01', '2026-01-02', '1m',
                    checkpoint.parent, output.parent, pause=0, verbose=False)
            self.assertEqual(checkpoint.read_bytes(), prior)
            self.assertEqual(output.read_bytes(), b'preserved earlier output\n')

    def test_legacy_checkpoint_cannot_be_adopted_for_a_different_quote(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = root / 'checkpoints/TEST_1m_2026-01-01_2026-01-02.json'
            checkpoint.parent.mkdir()
            stamp = int(pd.Timestamp('2026-01-01T00:00:00Z').timestamp())
            aggregator = tick_backfill.MinuteAggregator(60)
            aggregator.add(pd.DataFrame({'timestamp': [stamp], 'trade_id': [1], 'price': [100.], 'size': [1.]}))
            checkpoint.write_text(json.dumps({'cursor': 1, 'pages': 1, 'trades': 1, 'done': True, 'bars': aggregator.state()}))
            prior = checkpoint.read_bytes()
            with (patch.object(tick_backfill, '_page', side_effect=AssertionError('network boundary')),
                  redirect_stderr(io.StringIO()),
                  self.assertRaisesRegex(tick_backfill.FetchError, 'checkpoint.*identity')):
                tick_backfill.backfill('TEST', 'USDT', '2026-01-01', '2026-01-02', '1m',
                    checkpoint.parent, root / 'output', pause=0, verbose=False)
            self.assertEqual(checkpoint.read_bytes(), prior)
            self.assertFalse((root / 'output').exists())


class RemainingAuditBoundaries(unittest.TestCase):
    def test_every_current_component_requires_documentation(self):
        from scripts import check_docs
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / check_docs.OVERVIEW_MD
            target.parent.mkdir(parents=True)
            target.write_text(' '.join(x + '/' for x in
                ('backtester', 'research', 'extension', 'soltui', 'mongo', 'liquidity', 'executor')))
            with patch.object(check_docs, 'REPO', root):
                errors = check_docs.check_components_covered()
            self.assertEqual(len(errors), 4)
            self.assertTrue(all(any(name + '/' in e for e in errors)
                                for name in ('botmanager', 'oracle', 'ecosystem', 'website')))

    def test_undefined_perturbation_cannot_claim_stability(self):
        from research.perturb import Report, Trial
        baseline = Trial('base', 'base', 1., 0., 1., .1, 10, True)
        trial = Trial('change', 'change', 1.5, 1., 1., .2, 10, True)
        self.assertIn('INCONCLUSIVE', Report('test', 'long', baseline, trials=[trial]).verdict())
        baseline.iqr = 1.
        self.assertIn('STABLE', Report('test', 'long', baseline, trials=[trial]).verdict())

    def test_ratio_cli_never_silently_ignores_execution_flags(self):
        from research import ratio_rotation
        with patch.object(ratio_rotation, 'load_panel', side_effect=AssertionError('data boundary')):
            for args in (['--sweep', '--leverage', '2'], ['--sweep', '--fill-delay', '1']):
                with self.subTest(args=args):
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
                        ratio_rotation.main(args)
                    self.assertEqual(result.exception.code, 2)
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(ratio_rotation.main([]), 0)
            self.assertIn('usage:', output.getvalue())

    def test_reserved_interval_reader_closes_connection(self):
        from research import shape_study
        class Connection:
            closed = False
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def execute(self, *args): return self
            def fetchall(self): return [('TEST-USD', 1, 2, 'fixture')]
            def close(self): self.closed = True
        db = Connection()
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / 'ledger.sqlite'; ledger.touch()
            with patch.object(shape_study.sqlite3, 'connect', return_value=db):
                self.assertEqual(shape_study.protected_intervals(ledger, ('TEST',))[0]['run_id'], 'fixture')
            self.assertTrue(db.closed)

    def test_empty_admitted_experiment_keeps_report_schema(self):
        from research import cpcv_sweep
        frame, metadata = cpcv_sweep.bind_experiment([], {'pbo': float('nan')}, {'run_id': 'fixture'})
        self.assertEqual(frame.insufficient.dtype, bool)
        ranked = frame[~frame.insufficient].sort_values('median_sharpe')
        self.assertTrue(ranked.empty)
        self.assertIn('horizon', ranked.columns)
        self.assertEqual(metadata['run_id'], 'fixture')

    def test_minute_cache_never_reuses_changed_source_or_legacy(self):
        from research import minute_sweep
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'TEST_1m.csv'
            candles([0, 60, 120]).to_csv(source, index=False)
            with (patch.object(minute_sweep, 'SLICES', root / 'slices'),
                  patch.object(minute_sweep, 'minute_path', return_value=source),
                  patch.object(minute_sweep, 'load_minutes', side_effect=lambda asset: pd.read_csv(source))):
                path = minute_sweep.build_slice('TEST', 2, None)
                self.assertEqual(minute_sweep.build_slice('TEST', 2, None), path)
                prior = path.read_bytes()
                source.write_bytes(source.read_bytes().replace(b'100.0', b'100.5'))
                with self.assertRaisesRegex(ValueError, 'cache.*binding'):
                    minute_sweep.build_slice('TEST', 2, None)
                self.assertEqual(path.read_bytes(), prior)

    def test_minute_cache_refuses_legacy_and_modified_array_bytes(self):
        from research import minute_sweep
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root / 'TEST_1m.csv'
            candles([0, 60, 120]).to_csv(source, index=False)
            with (patch.object(minute_sweep, 'SLICES', root / 'slices'),
                  patch.object(minute_sweep, 'minute_path', return_value=source),
                  patch.dict(minute_sweep._ARRAYS, {}, clear=True)):
                path = minute_sweep.build_slice('TEST', 2, None)
                arrays, first, last = minute_sweep._arrays_for('TEST', 2, None)
                self.assertEqual((first, last), (60, 120))
                self.assertEqual(arrays['close'].tolist(), [100., 100.])
                minute_sweep._ARRAYS.clear()
                with path.open('ab') as output: output.write(b'modified fixture')
                prior = path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'cache.*binding'):
                    minute_sweep._arrays_for('TEST', 2, None)
                self.assertEqual(path.read_bytes(), prior)
                path.with_suffix('.json').unlink()
                with self.assertRaisesRegex(ValueError, 'cache.*binding'):
                    minute_sweep.build_slice('TEST', 2, None)
                self.assertEqual(path.read_bytes(), prior)

    def test_funding_after_the_last_bar_cannot_leak_into_it(self):
        from research import triggers
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pd.DataFrame({'timestamp': [100, 172801], 'funding_rate': [.01, .9]}).to_csv(
                root / 'TEST_funding_1h.csv', index=False)
            result = triggers.load_funding('TEST', np.array([0, 86400]), '1d', root)
            np.testing.assert_allclose(result, [.01, .01])

    def test_batch_perturbation_preserves_requested_asset_and_output(self):
        from research import perturb
        fake = perturb.Report('test', 'long', perturb.Trial('base', 'base', 1., 1., 1., .1, 10, True))
        with (patch.object(perturb, 'run', return_value=fake) as run,
              patch.dict(perturb.HORIZONS, {'fixture': {'params': {'macd': {}}}}),
              redirect_stderr(io.StringIO())):
            perturb.run_all_singles('fixture', .2, 8, 2, asset='BTC')
        self.assertEqual(run.call_args.kwargs['asset'], 'BTC')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); requested = root / 'requested.txt'
            with (patch.object(perturb, 'OUT', root / 'results'),
                  patch.object(perturb, 'run_all_singles', return_value=[fake]) as batch,
                  redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
                self.assertEqual(perturb.main(['--all-singles', '--asset', 'BTC', '--pct', '.2', '--out', str(requested)]), 0)
            self.assertEqual(batch.call_args.kwargs['asset'], 'BTC')
            self.assertTrue(requested.is_file())
            self.assertIn('+/-20%', requested.read_text())
            self.assertTrue((root / 'results/perturb_all_singles_btc_long.txt').is_file())

    def test_help_never_builds_an_index_or_reads_private_research(self):
        from research import verify_numbers
        from scripts import build_doc_index
        for module, boundary in ((verify_numbers, 'load'), (build_doc_index, 'build')):
            for flag, expected in (('--help', 0), ('--unknown', 2)):
                with self.subTest(module=module.__name__, flag=flag):
                    with (patch.object(sys, 'argv', ['tool', flag]),
                          patch.object(module, boundary, side_effect=AssertionError('data/write boundary')) as work,
                          redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()),
                          self.assertRaises(SystemExit) as result):
                        module.main()
                    self.assertEqual(result.exception.code, expected)
                    work.assert_not_called()

    def test_replication_never_counts_the_target_as_an_independent_asset(self):
        from types import SimpleNamespace

        from research import triggers
        fixture = SimpleNamespace(ts=np.arange(200), cond={}, funding=None)
        with (patch.object(triggers, 'load_dataset', return_value=fixture) as load,
              patch.object(triggers, 'enumerate_conjunctions', return_value=([], {}))):
            _, metadata, _ = triggers.mine('ZEC', '1d')
        self.assertNotIn('ZEC', metadata['replication_assets'])
        self.assertEqual(sum(call.args[0] == 'ZEC' for call in load.call_args_list), 1)

    def test_bound_tick_checkpoint_has_positive_resume_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            page = pd.DataFrame({'trade_id': [4, 3], 'timestamp': [1767225601., 1767225599.],
                                 'price': [100., 99.], 'size': [1., 1.]})
            with (patch.object(tick_backfill, 'seek_trade_id', return_value=5),
                  patch.object(tick_backfill, '_page', return_value=page) as fetch,
                  patch.object(tick_backfill, '_stop', False), redirect_stderr(io.StringIO())):
                args = ('TEST', 'USD', '2026-01-01', '2026-01-02', '1m', root / 'checkpoints', root / 'output')
                output = tick_backfill.backfill(*args, pause=0, verbose=False)
                self.assertTrue(output.is_file())
                tick_backfill.backfill(*args, pause=0, verbose=False)
                self.assertEqual(fetch.call_count, 1)
            checkpoint = next((root / 'checkpoints').glob('*.json'))
            saved = json.loads(checkpoint.read_text())
            self.assertEqual(saved['binding']['product'], 'TEST-USD')
            self.assertTrue(saved['done'])


if __name__ == '__main__':
    unittest.main()

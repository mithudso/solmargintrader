"""Fixed synthetic boundaries; no studies, searches, models, or network calls."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester.core import compound
from backtester.core.cpcv import BlockResult
from backtester.core.types import CostConfig
from research import (
    candle_crosscheck,
    candle_gap_audit,
    coinbase50_stats,
    frontier_tune,
    full_suite,
    geometry,
    leverage_tiers,
    meta_analysis,
    ratio_rotation,
    shape_report,
    signal_redundancy,
    strategy_snapshots,
    tick_backfill,
    trigger_backtest,
    triggers,
    turnover_table,
    verify_numbers,
    zec_cycle_report,
)


def candles(count=4, step=60):
    return pd.DataFrame({'timestamp': np.arange(count) * step, 'open': np.ones(count), 'high': np.ones(count), 'low': np.ones(count), 'close': np.ones(count), 'volume': np.ones(count)})


class NumericalReceiptTests(unittest.TestCase):
    def test_candle_comparison_refuses_nonfinite_before_reduction(self):
        fine = candles()
        fine.loc[1, 'high'] = np.nan
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            candle_crosscheck.compare(fine, candles(1, 240), 240, 60)

    def test_clock_refuses_infinite_profile_before_null_generation(self):
        profiles = pd.DataFrame(np.ones((120, 24)), index=pd.date_range('2025-01-01', periods=120))
        profiles.iloc[1, 1] = np.inf
        with self.assertRaises(ValueError):
            coinbase50_stats.clock_test(profiles, 'direction', replicates=1)

    def test_frontier_requires_finite_distinct_coin_support(self):
        row = {'asset': 'A', 'label': 'frontier:rsi hold=12', 'is': {'pnl': {'sharpe': 2}}}
        self.assertEqual(frontier_tune.candidates([row] * 10, 2), [])
        row['is']['pnl']['sharpe'] = np.inf
        self.assertIsNone(frontier_tune.is_sharpe(row))
        self.assertGreater(frontier_tune.score_or_missing(0), frontier_tune.score_or_missing(-1))

    def test_frontier_baseline_uses_source_hold_even_outside_tuning_grid(self):
        row = {'asset': 'A', 'label': 'frontier:rsi hold=12', 'is': {'pnl': {'sharpe': 2}}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(frontier_tune, 'load_run', return_value=[row]), patch.object(frontier_tune, 'config_for', side_effect=lambda metric, hold, *a, **k: {'hold': hold}), patch.object(frontier_tune, 'run_all', return_value=[]) as runner, patch.object(frontier_tune, 'summarise', return_value={'is_median_sharpe': 0, 'oos_median_sharpe': 0, 'oos_positive_coins': 0, 'oos_beat_buy_hold_coins': 0, 'coins': 0}), patch.object(frontier_tune.sc, 'BY_ID', {'rsi': SimpleNamespace(id='rsi', params=[], family='x', style='x')}), patch.object(frontier_tune.sc, 'COMPONENTS', []):
            frontier_tune.main(['--run-id', 'fixture', '--min-coins', '1', '--top', '1', '--out', str(Path(tmp) / 'out.json')])
            baseline = runner.call_args_list[0].args[1]
            self.assertEqual(baseline, [('baseline:rsi hold=12', {'hold': 12})])

    def test_turnover_refuses_nonfinite_or_negative_financial_values(self):
        frame = pd.DataFrame({'symbol': list(turnover_table.SPOKES), 'volume_24h_usd': [1.] * 10, 'market_cap_usd': [10.] * 10})
        frame.loc[0, 'market_cap_usd'] = np.nan
        with patch.object(turnover_table.pd, 'read_csv', return_value=frame), self.assertRaises(ValueError):
            turnover_table.turnover_table()

    def test_integer_turnover_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'spoke.md'
            p.write_text('Turnover 9% and 1% turnover')
            frame = pd.DataFrame({'symbol': list(turnover_table.SPOKES), 'turnover_pct': [1.] * 10})
            with patch.object(turnover_table, 'find_spoke', return_value=p):
                self.assertEqual(turnover_table.check(frame), 1)

    def test_failed_or_truncated_ticks_are_unknown_and_never_repair(self):
        for value in (None, pd.DataFrame({'timestamp': [60], 'size': [1]})):
            if value is not None:
                value.attrs['truncated'] = True
            with patch.object(candle_gap_audit, '_fetch_window', return_value=value):
                self.assertTrue(candle_gap_audit.classify_run('A-USD', (60, 60), 60)['verdict'].startswith('UNKNOWN'))
                with self.assertRaises(ValueError):
                    candle_gap_audit.repair_window('A-USD', (60, 60), candles(), 60)

    def test_no_gap_sampling_is_valid_empty_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            candles().to_csv(Path(tmp) / 'A_1m_last30d.csv', index=False)
            self.assertEqual(candle_gap_audit.main(['--assets', 'A', '--data-dir', tmp, '--sample', '2']), 0)

    def test_consolidation_records_unreadable_and_binds_exact_retained_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'source.json'
            raw = b'{"value": 1}'
            p.write_bytes(raw)
            result = meta_analysis.consolidate([p, Path(tmp) / 'missing.json'])
            self.assertEqual(len(result['read_errors']), 1)
            self.assertEqual(result['artifacts'][0]['data'], {'value': 1})
            self.assertEqual(result['artifacts'][0]['sha256'], hashlib.sha256(raw).hexdigest())
            # One read supplies hash, size, and parser, even if later reads differ.
            with patch.object(Path, 'read_bytes', side_effect=[raw, b'{"value": 2}']):
                result = meta_analysis.consolidate([p])
                self.assertEqual(result['artifacts'][0]['data'], {'value': 1})

    def test_neutral_ties_retain_both_disjoint_legs(self):
        weights = ratio_rotation.target_weights(np.full((12, 4), 100.), 3, 1, book='neutral', margin=1)
        live = weights[3:]
        np.testing.assert_allclose(live.sum(axis=1), 0)
        np.testing.assert_allclose(np.abs(live).sum(axis=1), 1)

    def test_rotation_refuses_elapsed_gaps(self):
        panel = ratio_rotation.Panel(('A',), np.array([0, 86400, 86400 * 3]), np.full((3, 1), 100.), '1d')
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            ratio_rotation.simulate(panel, np.ones((3, 1)))

    def test_rotation_charges_directional_borrow(self):
        panel = ratio_rotation.Panel(('A',), np.arange(3) * 86400, np.full((3, 1), 100.), '1d')
        costs = CostConfig(fee_bps=0, slippage_bps=0, max_hourly_rate_bps_long=10, max_hourly_rate_bps_short=1, utilization=1)
        long = ratio_rotation.simulate(panel, np.ones((3, 1)), costs, accrue_borrow=True)
        short = ratio_rotation.simulate(panel, -np.ones((3, 1)), costs, accrue_borrow=True)
        self.assertAlmostEqual(long.borrow_cost_total / short.borrow_cost_total, 10.)

    def test_missing_exposure_is_not_time_in_market(self):
        result = signal_redundancy.per_strategy_table(pd.DataFrame({'rsi': [np.nan, np.nan, 0., 1.]}), {'rsi': 2}, [])
        self.assertEqual(result.iloc[0].time_in_market, .5)
        self.assertEqual(result.iloc[0].state_changes, 1)

    def test_empty_filtered_universe_never_becomes_default_assets(self):
        self.assertEqual(full_suite.sweep_steps([], Path('.'), SimpleNamespace(fetch_only=False)), [])

    def test_comparative_pbo_uses_identical_config_populations(self):
        blocks = {i: np.array([-.01, .02, .01]) for i in range(6)}
        a, b = geometry.GeometryRun(6, 2), geometry.GeometryRun(8, 2)
        a.block_returns = {'shared_a': blocks, 'shared_b': blocks, 'only_a': blocks}
        b.block_returns = {'shared_a': blocks, 'shared_b': blocks, 'only_b': blocks}
        geometry.align_pbo_populations([a, b])
        self.assertEqual(a.pbo_configs, ['shared_a', 'shared_b'])
        self.assertEqual(a.pbo_configs, b.pbo_configs)
        self.assertEqual(a.pbo, b.pbo)

    def test_row_verification_cannot_mix_horizons(self):
        frame = pd.DataFrame({'label': ['rsi', 'rsi'], 'oos_sharpe': [1., 2.], 'oos_return': [.1, .2]})
        self.assertFalse(verify_numbers.check_row(frame, 'rsi', [('oos_sharpe', 1, .01), ('oos_return', .2, .01)])[0])
        self.assertTrue(verify_numbers.check_row(frame, 'rsi', [('oos_sharpe', 2, .01), ('oos_return', .2, .01)])[0])

    def test_stitched_charges_follow_compounded_capital(self):
        first = compound._Slice(np.array([1.]), 1, 1., .01, .02, 0, 1)
        second = compound._Slice(np.array([0.]), 1, 1., .01, .02, 0, 1)
        result = compound._stitch([first, second])
        self.assertEqual(result['fees_pct'], 3.)
        self.assertEqual(result['borrow_pct'], 6.)

    def test_trigger_outcome_uses_next_open_exit(self):
        n = triggers.H_MAX + 5
        opens = np.ones(n) * 100
        opens[2] = 120
        close = np.ones(n) * 101
        outcome = triggers.forward_outcomes(np.arange(n) * 86400, opens, np.maximum(opens, close), np.minimum(opens, close), close, 86400)
        self.assertAlmostEqual(outcome.ret[1][0], .2)

    def test_missing_daily_funding_is_not_carried_forward(self):
        with tempfile.TemporaryDirectory() as tmp:
            pd.DataFrame({'timestamp': np.arange(24) * 3600, 'funding_rate': [.001] * 24}).to_csv(Path(tmp) / 'A_funding_1h.csv', index=False)
            actual = triggers.load_funding('A', np.array([0, 86400]), '1d', Path(tmp))
            self.assertAlmostEqual(actual[0], .024)
            self.assertTrue(np.isnan(actual[1]))

    def test_fixed_report_refuses_alternative_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'research/results'
            p.mkdir(parents=True)
            for module, filename in [(shape_report, 'shape_spot_20261111_manifest.json'), (zec_cycle_report, 'zec_cycles_20261111_manifest.json')]:
                (p / filename).write_text(json.dumps({'artifacts': {'data.csv': 'known'}}))
                module.verify_fixed_report_contract({'artifacts': {'data.csv': 'known'}}, Path(tmp))
                with self.assertRaises(ValueError):
                    module.verify_fixed_report_contract({'artifacts': {'data.csv': 'alternative'}}, Path(tmp))

    def test_trigger_missing_stop_is_refused_before_engine(self):
        chosen = pd.DataFrame([{'conditions': 'rsi_lt30', 'direction': 'long', 'horizon': 1, 'stop_frac': np.nan}])
        a = np.arange(30)
        dataset = SimpleNamespace(ts=a, o=a, h=a, l=a, c=a, v=a)
        with patch.object(trigger_backtest, 'select', return_value=(chosen, 'fixture')), patch.object(triggers, 'load_dataset', return_value=dataset), patch.object(triggers, 'split_index', return_value=0), patch('research.leverage_tiers.load_layers', return_value=[]), patch.object(trigger_backtest, 'evaluate_block', side_effect=AssertionError('must refuse first')), self.assertRaisesRegex(ValueError, 'discovery stop'):
            trigger_backtest.run('A', '1d', pd.DataFrame(), {})

class OrchestrationReceiptTests(unittest.TestCase):
    def test_snapshot_interruption_never_publishes_partial_source(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {}
            for variant in ('original', 'candidate'):
                members = {'core/strategies/__init__.py': b'', 'fail.txt': b'complete'}
                archive = root / f'{variant}.zip'
                with zipfile.ZipFile(archive, 'w') as zipped:
                    for name, content in members.items():
                        zipped.writestr(name, content)
                manifest[variant] = {'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': {k: hashlib.sha256(v).hexdigest() for k, v in members.items()}}
            (root / 'archives.json').write_text(json.dumps(manifest))
            original_write = Path.write_bytes
            def interrupted(path, content):
                if path.name == 'fail.txt':
                    raise OSError('synthetic interrupted extraction')
                return original_write(path, content)
            with patch.object(Path, 'write_bytes', interrupted), self.assertRaises(OSError):
                strategy_snapshots.ensure_snapshots(root)
            self.assertFalse((root / 'original').exists())
            self.assertFalse(list(root.glob('.original-*')))
            strategy_snapshots.ensure_snapshots(root)
            self.assertEqual((root / 'original/fail.txt').read_bytes(), b'complete')

    def test_coinbase_bad_raw_cache_is_retried_and_fractional_time_refused(self):
        from research import coinbase50_data
        with tempfile.TemporaryDirectory() as tmp, patch.object(coinbase50_data, 'PLAN', {'fixture': (3600, 1)}), patch.object(coinbase50_data, 'CUTOFF', '1970-01-02T00:00:00Z'):
            asset = {'symbol': 'A', 'product': {'product_id': 'A-USD'}}
            limiter = SimpleNamespace(wait=lambda: None)
            for response in ({'error': 'invalid'}, [[.5, 1, 1, 1, 1, 1]]):
                with patch.object(coinbase50_data, '_get_json', return_value=response):
                    result = coinbase50_data.collect_cell(Path(tmp), asset, 'fixture', limiter)
                self.assertEqual(len(result['errors']), 1)
                self.assertEqual(list((Path(tmp) / 'chunks/A_fixture').glob('*.json')), [])

    def test_invalid_cached_numeric_page_is_preserved_and_can_be_retried(self):
        from research import coinbase50_data as data
        with tempfile.TemporaryDirectory() as tmp, patch.object(data, 'PLAN', {'fixture': (3600, 1)}), patch.object(data, 'CUTOFF', '1970-01-02T00:00:00Z'):
            root = Path(tmp)
            asset = {'symbol': 'A', 'product': {'product_id': 'A-USD'}}
            limiter = SimpleNamespace(wait=lambda: None)
            with patch.object(data, '_get_json', return_value={'error': 'fixture'}):
                result = data.collect_cell(root, asset, 'fixture', limiter)
            path = root / 'chunks/A_fixture/0_86400.json'
            raw = json.dumps({'url': result['errors'][0]['url'], 'rows': [['bad', 1, 1, 1, 1, 1]]}).encode()
            path.write_bytes(raw)
            with patch.object(data, '_get_json', side_effect=AssertionError('cached page must be validated first')):
                result = data.collect_cell(root, asset, 'fixture', limiter)
            self.assertEqual(len(result['errors']), 1)
            quarantine = list(path.parent.glob('*.invalid-*'))
            self.assertEqual(len(quarantine), 1)
            self.assertEqual(quarantine[0].read_bytes(), raw)
            with patch.object(data, '_get_json', return_value=[]) as request:
                data.collect_cell(root, asset, 'fixture', limiter)
                request.assert_called_once()

    def test_infinite_gate_feature_never_authorizes_entry(self):
        from research import coinbase50_grid
        frame = candles(8, 900)
        features = pd.DataFrame({'available_at': [0], 'H1': [np.inf], 'cycle_allowed': [np.inf]})
        shape = pd.DataFrame({'shape': ['range'] * 8, 'range_position': [.5] * 8})
        with patch.object(coinbase50_grid, 'detect_shapes', return_value=shape):
            allowed, _ = coinbase50_grid.permissions(frame, features, 3600)
        self.assertFalse(allowed[:, -1].any())
        self.assertFalse(allowed[:, 0].any())

    def test_unusable_trigger_validation_is_not_zero_return(self):
        selected = pd.DataFrame([{'conditions': 'rsi_lt30', 'direction': 'long', 'horizon': 1, 'stop_frac': .02}])
        a = np.arange(100)
        dataset = SimpleNamespace(ts=a, o=a, h=a, l=a, c=a, v=a)
        unusable = BlockResult(0, 0, 10, np.array([]), 0, False, 'fixture insufficient')
        with patch.object(trigger_backtest, 'select', return_value=(selected, 'fixture')), patch.object(triggers, 'load_dataset', return_value=dataset), patch.object(triggers, 'split_index', return_value=0), patch('research.leverage_tiers.load_layers', return_value=[]), patch.object(trigger_backtest, 'evaluate_block', return_value=unusable), self.assertRaisesRegex(ValueError, 'unusable validation'):
            trigger_backtest.run('A', '1d', pd.DataFrame(), {})

    def test_empty_trigger_results_have_readable_schema_and_exclude_discovery_asset(self):
        stamps = np.arange(100) * 86400
        dataset = SimpleNamespace(ts=stamps, cond={}, funding=None)
        with tempfile.TemporaryDirectory() as tmp, patch.object(triggers, 'load_dataset', return_value=dataset) as loader, patch.object(triggers, 'split_index', return_value=50), patch.object(triggers, 'enumerate_conjunctions', return_value=([], {})), patch.object(triggers, 'REPLICATION_ASSETS', ['A', 'B']), patch.object(triggers, 'OUT', Path(tmp)):
            frame, metadata, _ = triggers.mine('A', '1d')
            result = triggers.write_results(frame, metadata)
            loaded = pd.read_csv(result)
            self.assertTrue(loaded.empty)
            self.assertIn('reliable', loaded.columns)
            self.assertEqual([call.args[0] for call in loader.call_args_list], ['A', 'B'])

    def test_stalled_tick_pager_remains_incomplete_and_does_not_double_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            page = pd.DataFrame({'timestamp': [100.], 'trade_id': [11], 'price': [1.], 'size': [1.]})
            with patch.object(tick_backfill, 'seek_trade_id', return_value=10), patch.object(tick_backfill, '_page', return_value=page), patch.object(tick_backfill, '_stop', False):
                result = tick_backfill.backfill('A', 'EUR', '1970-01-01', '1970-01-02', '1m', root / 'checkpoints', root / 'output', pause=0)
            self.assertIsNone(result)
            checkpoint = root / 'checkpoints/A_EUR_1m_1970-01-01_1970-01-02.json'
            state = json.loads(checkpoint.read_text())
            self.assertFalse(state['done'])
            self.assertEqual(state['trades'], 0)
            self.assertFalse((root / 'checkpoints/A_1m_1970-01-01_1970-01-02.json').exists())

    def test_decision_equality_ignores_provenance_but_compares_targets(self):
        import subprocess
        base = {'strategies': [{'strategy': 'rsi', 'target': 1, 'action': 'BUY'}], 'data_checksum': 'a'}
        revised = {**base, 'data_checksum': 'b'}
        with patch.object(tick_backfill.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, json.dumps(base)), subprocess.CompletedProcess([], 0, json.dumps(revised))]):
            self.assertIn('unchanged', tick_backfill.rerun_decision('A', Path('old'), Path('new'), '1d'))
        revised = {'strategies': [{'strategy': 'rsi', 'target': 0, 'action': 'SELL'}]}
        with patch.object(tick_backfill.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 0, json.dumps(base)), subprocess.CompletedProcess([], 0, json.dumps(revised))]):
            self.assertIn('DIFFERENT', tick_backfill.rerun_decision('A', Path('old'), Path('new'), '1d'))

    def test_tick_audit_counts_missing_measurements_and_omits_partial_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            truth = candles(3)
            truth.timestamp += 60
            truth.to_csv(root / 'truth.csv', index=False)
            incomplete = truth.copy()
            incomplete.loc[1, 'high'] = np.nan
            incomplete.to_csv(root / 'A_1m_last30d.csv', index=False)
            candles(1, 300).to_csv(root / 'A_5m.csv', index=False)
            result = tick_backfill.audit('A', root / 'truth.csv', root, '1m')
            self.assertEqual(len(result), 1)
            self.assertIn('1 wrong high', result[0])

    def test_empty_admitted_cpcv_search_returns_explicit_schema(self):
        from research import cpcv_sweep
        with patch.object(cpcv_sweep, 'load_horizon', return_value=({}, SimpleNamespace())), patch.object(cpcv_sweep, 'independent_combos', return_value=[]), patch.object(cpcv_sweep, 'experiment_metadata', return_value={'manifest': {}}):
            frame, pbo = cpcv_sweep.run_combos('medium', 2, 8, 2, ('all',), ('rsi',))
        self.assertTrue(frame.empty)
        self.assertEqual(frame.insufficient.dtype, bool)
        self.assertEqual(pbo['n_configs'], 0)

    def test_leverage_population_keeps_insufficient_and_pools_actual_paths(self):
        from research import leverage_tiers as lev
        block = BlockResult(0, 0, 3, np.array([0., .01, -.01]), 1, True)
        def result(sharpes, insufficient=False):
            return SimpleNamespace(insufficient=insufficient, reason='not enough', usable_blocks=1, blocks=[block], median_sharpe=np.median(sharpes), path_sharpes=np.array(sharpes), frac_positive=1, median_return=0, total_trades=1)
        values = [result([1, 2, 3]), result([100]), result([0], True)]
        with patch.object(lev, 'load_horizon', return_value=({'ts': np.arange(3)}, None)), patch.object(lev, 'load_layers', return_value=[]), patch.object(lev, 'HORIZONS', {'medium': {'params': {'a': {}, 'b': {}, 'c': {}}}}), patch.object(lev, 'cpcv_evaluate', side_effect=values):
            per, summary, _, _ = lev.run('A', '1d', [], 8, 1)
        self.assertEqual(len(per), 3)
        self.assertTrue(per.iloc[2].insufficient)
        self.assertEqual(summary.iloc[0].oos_median_sharpe, 2.5)
        self.assertEqual(summary.iloc[0].strategies, 2)

    def test_fine_coverage_requires_exact_cadence(self):
        fine = SimpleNamespace(ts=np.array([0, 900, 1800, 3599, 3600]), low=np.ones(5), seconds=900, interval='15m')
        arrays = {'ts': np.array([0, 3600]), 'low': np.ones(2)}
        result = leverage_tiers.coverage_audit(arrays, [fine])
        self.assertEqual(result['layers'][0]['bars_fully_covered'], 0)

    def test_active_worker_refuses_before_fetch(self):
        from soltui import bgcontrol
        with patch.object(bgcontrol, 'is_running', return_value=True), patch.object(full_suite.subprocess, 'run', side_effect=AssertionError('must refuse before fetch')), patch.object(full_suite, 'resolve_data_dir', return_value=Path('fixture')):
            self.assertEqual(full_suite.main(['--assets', 'BTC']), 1)

class RemainingOrchestrationTests(unittest.TestCase):
    def test_current_day_fetch_can_begin_with_api_when_archives_do_not_exist(self):
        from research import fetch_zec_history as fetch
        frame = candles(3)
        start = int(pd.Timestamp('2026-11-12T00:00:00Z').timestamp())
        frame.timestamp += start
        with tempfile.TemporaryDirectory() as tmp, patch('sys.argv', ['fixture', '--output', tmp, '--start', '2026-11-12', '--workers', '1']), patch.object(fetch, 'STEPS', {'1m': 60}), patch.object(fetch, 'request_bytes', return_value=json.dumps({'serverTime': (start + 4 * 3600) * 1000}).encode()), patch.object(fetch, 'api_tail', return_value=([frame], [])) as tail:
            self.assertEqual(fetch.main(), 0)
            self.assertEqual(tail.call_args.args[1], start)
            self.assertTrue((Path(tmp) / 'ZEC_1m.csv').exists())

    def test_failed_untested_candidates_report_failure(self):
        from research import sweep_untested
        with patch.object(sweep_untested, 'REGISTRY', {}), patch.object(sweep_untested, 'load_horizon', return_value=({}, None)), patch.object(sweep_untested, 'walk_forward', side_effect=ValueError('fixture unusable')):
            self.assertEqual(sweep_untested.main(), 1)

    def test_untested_recommendation_retains_exact_evaluated_parameters(self):
        from research import sweep_untested
        metric = SimpleNamespace(sharpe=1., total_return=.1, max_drawdown=.2, trade_count=20)
        with tempfile.TemporaryDirectory() as tmp, patch.object(sweep_untested, 'REPO', Path(tmp)), patch.object(sweep_untested, 'REGISTRY', {}), patch.object(sweep_untested, 'load_horizon', return_value=({}, None)), patch.object(sweep_untested, 'walk_forward', return_value=(metric, metric, metric)), patch.object(sweep_untested, 'fmt_table', return_value='fixture'):
            (Path(tmp) / 'research').mkdir()
            self.assertEqual(sweep_untested.main(), 0)
            recommendation = json.loads((Path(tmp) / 'research/TOP_UNTESTED_RECOMMENDATION.json').read_text())
            self.assertEqual(recommendation['strategy'], 'rsi')
            self.assertEqual(recommendation['params'], {'period': 5, 'oversold': 20., 'exit_level': 70.})

    def test_failed_attempt_remains_in_search_denominator(self):
        from research import sweep
        with patch.object(sweep, 'HORIZONS', {'fixture': {'params': {'rsi': {'period': 5}}}}), patch.object(sweep, 'load_horizon', return_value=({}, None)), patch.object(sweep, 'walk_forward', side_effect=ValueError('fixture failed')):
            sweep.FAILED_EVALUATIONS.clear()
            self.assertEqual(sweep.sweep_singles('fixture'), [])
            self.assertEqual(sweep.FAILED_EVALUATIONS, [{'horizon': 'fixture', 'kind': 'single', 'label': 'rsi', 'params': {'period': 5}, 'error': 'fixture failed'}])
            sweep.FAILED_EVALUATIONS.clear()

    def test_reference_duplicates_refuse_before_any_evaluation(self):
        from research import cross_asset_cpcv as cross
        frame = pd.DataFrame([dict.fromkeys(cross.COLUMNS, 0)] * 2)
        frame['asset'], frame['strategy'] = 'A', 'rsi'
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'reference.csv'
            frame.to_csv(source, index=False)
            with patch.object(cross, 'REFERENCE', source), patch.object(cross, 'run_asset', side_effect=AssertionError('must refuse duplicates')):
                self.assertEqual(cross.self_test(), 1)

    def test_holdout_signal_failure_preserves_usable_working_split(self):
        from research import strategy_compare as compare
        class Policy:
            def warmup_bars(self):
                return 0
        def targets(factory, arrays):
            if len(arrays['ts']) > 5:
                raise ValueError('synthetic holdout failure')
            return np.zeros(len(arrays['ts']))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'A_1d.csv').write_bytes(b'fixture')
            with patch.object(compare, 'ensure_snapshots'), patch.object(compare, 'source_hashes', return_value={}), patch.object(compare, 'load_registry', return_value={'fixture': Policy}), patch.object(compare, 'load_sample', return_value=(candles(10, 86400), {})), patch.object(compare, 'targets', side_effect=targets), patch.object(compare, 'evaluate', return_value={'status': 'ok'}), patch.object(compare, 'write_outputs') as output:
                compare.run(root, root, ['A_1d'], root / 'out', split=.5, names=['fixture'])
                rows = output.call_args.args[2]
                self.assertTrue(all(row['status'] == 'ok' for row in rows if row['split'] == 'working'))
                self.assertTrue(all(row['status'] == 'failed' for row in rows if row['split'] == 'holdout'))

    def test_concentration_refuses_calendar_mismatch_before_publication(self):
        from research import meta_followups as meta
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'selection.json').write_text(json.dumps([{'selected': ['A'], 'marketcap_ten': ['A']}] * 3))
            np.savez(root / 'portfolio_curves.npz', timestamp=np.arange(6), zero_2_m00=np.ones(6) * meta.CAPITAL)
            for fold in range(3):
                np.savez(root / f'A_f{fold}_zero_2.npz', timestamp=np.array([10, 11]), equity=np.ones((16, 2)), passive=np.ones(2))
            with self.assertRaisesRegex(ValueError, 'timestamps differ'):
                meta.concentration(root, root, {})
            self.assertFalse((root / 'concentration.json').exists())

    def test_empty_cycle_windows_are_recorded_ineligible_without_null_work(self):
        from research import zec_cycles as cycles
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'input'
            source.mkdir()
            candles(1).to_csv(source / 'ZEC_USD_1m.csv', index=False)
            with patch.object(cycles, 'INTERVALS', ('1m',)), patch.object(cycles, 'protected_intervals', return_value=[]), patch.object(cycles, 'refuse_reserved'), patch.object(cycles, 'null_test', side_effect=AssertionError('no eligible observations')):
                cycles.run(source, root / 'out', target_day='2026-11-10', replicates=1)
            coverage = pd.read_csv(root / 'out/coverage.csv')
            self.assertTrue((coverage.bars == 0).all())
            self.assertFalse(coverage.eligible.any())
            self.assertEqual(json.loads((root / 'out/manifest.json').read_text())['status'], 'insufficient')

    def test_disjoint_primary_calendars_refuse_before_model_work(self):
        from research import zec_ensembles as ensemble
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for interval, step, origin in [('1m', 60, 0), ('1h', 3600, 10000000)]:
                frame = candles(2000, step)
                frame.timestamp += origin
                frame.to_csv(root / f'ZEC_{interval}.csv', index=False)
            with patch.object(ensemble, 'catalog', return_value=[]), patch.object(ensemble, 'verify_batch_parity', side_effect=AssertionError('must refuse before model parity')), self.assertRaisesRegex(ValueError, 'holdout calendars do not overlap'):
                ensemble.main(['--data-dir', str(root), '--output', str(root / 'out'), '--minute-days', '0'])
            self.assertFalse((root / 'out/manifest.json').exists())

    def test_broken_pool_preserves_unstarted_configurations_for_retry(self):
        import concurrent.futures
        from concurrent.futures.process import BrokenProcessPool

        from research import strategy_config_sweep as sweep
        class BrokenPool:
            def __init__(self, **kwargs):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def submit(self, *args):
                future = concurrent.futures.Future()
                future.set_exception(BrokenProcessPool('fixture worker exited'))
                return future
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'A.csv'
            source.write_text('fixture')
            tasks = [{'configuration_id': 'a'}, {'configuration_id': 'b'}]
            with patch.object(sweep, 'discover_assets', return_value={'A': {'1d': source}}), patch.object(sweep, '_lock_output'), patch.object(sweep, '_source_fingerprint', return_value={}), patch.object(sweep, '_historical_base_settings', return_value={}), patch.object(sweep, 'build_jobs', return_value=(tasks, {})), patch.object(sweep.concurrent.futures, 'ProcessPoolExecutor', BrokenPool), patch.object(sweep, '_record', side_effect=AssertionError('infrastructure failures must remain pending')), self.assertRaisesRegex(RuntimeError, 'pending configurations were preserved'):
                sweep.main(['--data-dir', str(root), '--output-dir', str(root / 'out'), '--workers', '1'])

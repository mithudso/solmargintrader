"""Known-answer gates for the paired offline comparison, not performance assertions."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.strategies.ma_crossover import MaCrossover
from backtester.core.strategies.tiers import LevLow
from research.strategy_compare import (accuracy_panel, evaluate, pair_rows,
                                       source_hashes, targets, write_outputs, run, load_registry, load_sample)


def arrays(closes: list[float], opens: list[float] | None = None) -> dict:
    close = np.array(closes, dtype=float)
    op = np.array(opens, dtype=float) if opens is not None else close.copy()
    return {'ts': 1700000000 + np.arange(len(close)) * 86400,
            'open': op, 'high': np.maximum(op, close) + 1,
            'low': np.minimum(op, close) - 1, 'close': close,
            'volume': np.full(len(close), 1000.)}


class TestStrategyComparison(unittest.TestCase):
    def test_accuracy_uses_next_open_close_and_counts_flat_misses(self):
        market = arrays([100, 102, 99, 100, 100], [100] * 5)
        panel = accuracy_panel(np.array([1, 1, 0, 1, 0]), market, 1, 5)
        self.assertEqual(panel['active_calls'], 3)
        self.assertEqual(panel['correct_calls'], 1)
        self.assertEqual(panel['accuracy'], 1 / 3)
        self.assertEqual(panel['coverage'], 3 / 4)
        self.assertEqual(panel['majority_baseline'], 1 / 3)

    def test_all_flat_is_undefined_accuracy_not_perfect(self):
        market = arrays([100, 101, 102])
        panel = accuracy_panel(np.zeros(3), market, 1, 3)
        self.assertIsNone(panel['accuracy'])
        self.assertEqual(panel['active_calls'], 0)
        self.assertEqual(panel['coverage'], 0)

    def test_scoring_excludes_prefix_and_pays_nonzero_costs(self):
        market = arrays([100] * 20)
        result = evaluate(BuyAndHold, market, '1d', 10, 20)
        self.assertEqual(result['bars'], 10)
        self.assertEqual(result['scored_start_index'], 10)
        self.assertGreater(result['total_fees'], 0)
        self.assertLess(result['total_return'], 0)
        self.assertEqual(result['trade_count'], 1)

    def test_prefix_signal_replay_does_not_see_future(self):
        factory = lambda: MaCrossover(fast=2, slow=4)
        market = arrays([100 + i % 7 for i in range(30)])
        prefix = {k: v[:20] for k, v in market.items()}
        np.testing.assert_array_equal(targets(factory, market)[:20], targets(factory, prefix))
        changed = {k: v.copy() for k, v in market.items()}
        for key in ('open', 'high', 'low', 'close'):
            changed[key][20:] *= 3
        a = evaluate(factory, market, '1d', 10, 20)
        b = evaluate(factory, changed, '1d', 10, 20)
        self.assertEqual(a, b)

    def test_tiers_use_perp_and_borrow_not_spot(self):
        factory = lambda: LevLow(base='buy_and_hold')
        result = evaluate(factory, arrays([100] * 20), '1d', 10, 20)
        self.assertEqual(result['mode'], 'perp')
        self.assertEqual(result['leverage'], 2)
        self.assertGreater(result['total_borrow_fees'], 0)

    def test_hashes_track_code_changes_but_ignore_bytecode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a.py').write_text('one')
            before = source_hashes(root)
            (root / '__pycache__').mkdir()
            (root / '__pycache__/a.pyc').write_bytes(b'cache')
            self.assertEqual(before, source_hashes(root))
            (root / 'a.py').write_text('two')
            self.assertNotEqual(before, source_hashes(root))

    def test_cached_causal_replay_equals_direct_engine_signals(self):
        factory = lambda: MaCrossover(fast=2, slow=4)
        market = arrays([100 + (i % 7) * 3 for i in range(40)])
        direct = evaluate(factory, market, '1d', 20, 40)
        cached = evaluate(factory, market, '1d', 20, 40, targets(factory, market))
        self.assertEqual(direct, cached)

    def test_contiguous_suffix_selected_only_from_timestamps(self):
        market = arrays([100, 101, 102, 103, 104, 105])
        import pandas as pd
        frame = pd.DataFrame({('timestamp' if k == 'ts' else k): v for k, v in market.items()})
        frame.loc[3:, 'timestamp'] += 86400
        raw = frame.to_csv(index=False).encode()
        with self.assertRaises(ValueError):
            load_sample(raw, '1d')
        selected, meta = load_sample(raw, '1d', contiguous_tail=True)
        self.assertEqual(meta['selected_start_index'], 3)
        self.assertEqual(meta['timestamp_gaps'], 1)
        self.assertEqual(len(selected), 3)
        np.testing.assert_array_equal(selected['close'], [103, 104, 105])
        frame.loc[:, 'close'] = frame['open']
        _, changed = load_sample(frame.to_csv(index=False).encode(), '1d', True)
        self.assertEqual(changed['selected_start_index'], meta['selected_start_index'])

    def test_separate_packages_do_not_share_relative_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for variant, value in (('original', 1), ('candidate', 2)):
                package = root / variant
                (package / 'strategies').mkdir(parents=True)
                (package / '__init__.py').write_text('')
                (package / 'value.py').write_text(f'VALUE = {value}\n')
                (package / 'strategies/__init__.py').write_text(
                    'from ..value import VALUE\nREGISTRY = {"value": lambda: VALUE}\n')
            old = load_registry(root / 'original', 'original')
            new = load_registry(root / 'candidate', 'candidate')
            self.assertEqual(old['value'](), 1)
            self.assertEqual(new['value'](), 2)
            self.assertEqual(old['value'](), 1)

    def test_missing_data_keeps_every_variant_and_split_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = {'buy_and_hold': BuyAndHold}
            with patch('research.strategy_compare.load_registry', return_value=registry), \
                    patch('research.strategy_compare.ensure_snapshots'):
                manifest = run(root, root, ['SOL_1d'], root / 'out')
            rows = json.loads((root / 'out/results.json').read_text())
            self.assertEqual(manifest['failed_cells'], 4)
            self.assertEqual(len(rows), 4)
            self.assertEqual({r['variant'] for r in rows}, {'original', 'candidate'})
            self.assertEqual({r['split'] for r in rows}, {'working', 'holdout'})
            self.assertTrue(all(r['status'] == 'failed' for r in rows))

    def test_failed_pair_is_retained_and_undefined_json_is_null(self):
        rows = [{'dataset': 'SOL_1d', 'strategy': 'test', 'split': 'holdout',
                 'variant': 'original', 'status': 'ok', 'accuracy': float('nan')},
                {'dataset': 'SOL_1d', 'strategy': 'test', 'split': 'holdout',
                 'variant': 'candidate', 'status': 'failed', 'error': 'bad data'}]
        self.assertEqual(pair_rows(rows)[0]['status'], 'failed')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_outputs(root, {}, rows)
            text = (root / 'results.json').read_text()
            self.assertNotIn('NaN', text)
            self.assertIsNone(json.loads(text)[0]['accuracy'])
            self.assertIn('failed', (root / 'comparison.md').read_text())


if __name__ == '__main__':
    unittest.main()

"""Source byte and run-artifact identity, without a MongoDB connection."""
from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backtester.core.data import frame_to_arrays, validate_bars
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.report import write_outputs
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.tests.test_engine import make_frame
from mongo import load


class SnapshotAudit(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'research/results'
        self.results.mkdir(parents=True)
        self.repo_patch = patch.object(load, 'REPO', self.root)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)

    def test_experiment_digest_matches_parsed_bytes_even_if_source_changes_during_read(self):
        path = self.results / 'sweep_demo.csv'
        before = b'label,value\na,1\n'
        path.write_bytes(before)
        original_open = Path.open
        changed = False
        def replace_once(target, mode='r', *args, **kwargs):
            nonlocal changed
            if target == path and not changed:
                changed = True
                with original_open(path, 'wb') as handle:
                    handle.write(b'label,value\nb,99\n')
                return io.BytesIO(before) if 'b' in mode else io.StringIO(before.decode())
            return original_open(target, mode, *args, **kwargs)
        with patch.object(Path, 'open', replace_once):
            experiments, rows = load.load_experiments()
        self.assertEqual(rows[0]['label'], 'a')
        self.assertEqual(rows[0]['source_sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(experiments[0]['source_sha256'], rows[0]['source_sha256'])

    def write_current_run(self):
        out = self.root / 'results'
        out.mkdir(exist_ok=True)
        arrays = frame_to_arrays(validate_bars(make_frame([100, 101, 102, 103]), '1d'))
        full = run_backtest(BuyAndHold(), arrays, EngineConfig())
        manifest = SimpleNamespace(to_dict=lambda: {'asset': 'SOL', 'interval': '1d', 'mode': 'spot',
            'strategies': {full.strategy_name: {}}, 'data_checksum': 'unit'})
        write_outputs(out, [SimpleNamespace(full=full)], manifest, 'unit report')
        return out, full.strategy_name

    def test_run_inventory_excludes_leftovers_and_rejects_modified_selected_artifacts(self):
        out, name = self.write_current_run()
        (out / 'trades_old_strategy.csv').write_text('timestamp,price\n1600000000,1\n')
        (out / 'equity_old_strategy.csv').write_text('timestamp,equity\n1600000000,1\n')
        trades = load.load_trades()
        curves = load.load_equity_points()
        self.assertTrue(trades and curves)
        self.assertEqual({row['strategy'] for row in trades}, {name})
        self.assertEqual({row['curve']['strategy'] for row in curves}, {name})
        manifest = json.loads((out / 'run_manifest.json').read_text())
        self.assertEqual(set(manifest['artifact_sha256']),
                         {'comparison.csv', f'trades_{name}.csv', f'equity_{name}.csv', 'report.md'})
        (out / f'trades_{name}.csv').write_text('timestamp,price\n1600000000,999\n')
        with self.assertRaisesRegex(ValueError, 'artifact|hash|digest'):
            load.load_trades()

    def test_legacy_matching_artifacts_require_new_proof_without_rewriting_them(self):
        out = self.root / 'results'
        out.mkdir()
        (out / 'run_manifest.json').write_text(json.dumps({'strategies': {'buy_and_hold': {}}}))
        path = out / 'equity_buy_and_hold.csv'
        original = b'timestamp,equity\n1600000000,100\n'
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'artifact|manifest|proof'):
            load.load_equity_points()
        self.assertEqual(path.read_bytes(), original)

    def test_complete_publication_replaces_manifest_only_after_all_artifacts_are_written(self):
        out, name = self.write_current_run()
        manifest = json.loads((out / 'run_manifest.json').read_text())
        for relative, expected in manifest['artifact_sha256'].items():
            self.assertEqual(load.sha256(out / relative), expected)
        self.assertEqual(load.load_backtest_runs()[0]['comparison_provenance']['source_sha256'],
                         manifest['artifact_sha256']['comparison.csv'])

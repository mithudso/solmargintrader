"""Offline loader regressions: fixtures and fake databases only."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from mongo import load, schema


class FakeDatabase:
    def __init__(self):
        self.calls = []

    def drop_collection(self, name):
        self.calls.append(('drop', name))

    def create_collection(self, name, **kwargs):
        self.calls.append(('create', name))

    def command(self, command, name, **kwargs):
        self.calls.append((command, name))

    def __getitem__(self, name):
        outer = self
        class Collection:
            def create_index(self, keys, **options):
                outer.calls.append(('index', name))
            def insert_many(self, docs, **kwargs):
                outer.calls.append(('insert', name))
        return Collection()


class LoaderAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'data').mkdir()
        self.results = self.root / 'research' / 'results'
        self.results.mkdir(parents=True)
        self.patch_repo = patch.object(load, 'REPO', self.root)
        self.patch_repo.start()
        self.addCleanup(self.patch_repo.stop)

    def test_bar_census_excludes_non_ohlcv_caches_by_contract(self):
        (self.root / 'data' / 'SOL_1d.csv').write_text('timestamp,open,high,low,close,volume\n1,1,1,1,1,1\n')
        (self.root / 'data' / 'SOL_funding_1h.csv').write_text('timestamp,funding_rate,premium\n1,0.01,0\n')
        # Header contract, rather than the word "funding" in a filename, decides admission.
        (self.root / 'data' / 'OTHER_1h.csv').write_text('timestamp,funding_rate,premium\n1,0.01,0\n')
        self.assertEqual([(a, i) for _, a, i in load.bar_files()], [('SOL', '1d')])

    def test_ambiguous_broken_bar_cache_is_not_silently_discarded(self):
        (self.root / 'data' / 'SOL_1d.csv').write_text('timestamp,close\n1,1\n')
        with self.assertRaisesRegex(ValueError, 'OHLCV|bar.*column|column.*bar'):
            load.bar_files()

    def test_empty_or_unknown_selection_never_connects_or_builds(self):
        for value in ['', ' ', ',', 'bars,,signals', 'unknown']:
            with self.subTest(value=value), patch.object(load, 'connect') as connect, patch.object(load, 'build_all') as build, patch.object(load, 'create') as create, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(load.main(['--only', value]), 2)
                connect.assert_not_called()
                build.assert_not_called()
                create.assert_not_called()

    def test_selected_schema_creation_never_touches_other_collections(self):
        db = FakeDatabase()
        errors = ModuleType('pymongo.errors')
        errors.CollectionInvalid = type('CollectionInvalid', (Exception,), {})
        with patch.dict(sys.modules, {'pymongo': ModuleType('pymongo'), 'pymongo.errors': errors}):
            schema.create(db, only={'signals'})
        self.assertTrue(db.calls)
        self.assertEqual({name for _, name in db.calls}, {'signals'})
        for only in [set(), {'unknown'}]:
            db = FakeDatabase()
            with self.assertRaises(ValueError):
                schema.create(db, only=only)
            self.assertEqual(db.calls, [])

    def test_loader_passes_selection_to_schema(self):
        db = FakeDatabase()
        with patch.object(load, 'build_all', return_value={'signals': []}), patch.object(load, 'connect', return_value={schema.DB_NAME: db}), patch.object(load, 'create') as create, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(load.main(['--only', 'signals']), 0)
        create.assert_called_once_with(db, drop=True, only={'signals'})

    def test_sidecar_summary_has_its_own_source_identity(self):
        csv_path = self.results / 'cpcv_demo.csv'
        csv_path.write_text('horizon,pbo\nshort,0.5\n')
        sidecar = csv_path.with_suffix('.json')
        sidecar.write_text(json.dumps([{'horizon': 'short', 'pbo': 0.7}]))
        experiments, rows = load.load_experiments()
        result = next(r for r in rows if r['section'] == 'result')
        summary = next(r for r in rows if r['section'] == 'summary')
        self.assertEqual(result['source_sha256'], load.sha256(csv_path))
        self.assertEqual(summary['source_path'], 'research/results/cpcv_demo.json')
        self.assertEqual(summary['source_sha256'], load.sha256(sidecar))
        self.assertEqual(experiments[0]['summary_provenance']['source_sha256'], load.sha256(sidecar))
        sidecar.write_text(json.dumps([{'horizon': 'short', 'pbo': 0.9}]))
        _, rows2 = load.load_experiments()
        summary2 = next(r for r in rows2 if r['section'] == 'summary')
        self.assertNotEqual(summary['source_sha256'], summary2['source_sha256'])
        self.assertEqual(summary2['pbo'], 0.9)

    def test_object_sidecar_provenance_hashes_the_bytes_used(self):
        csv_path = self.results / 'sweep_demo.csv'
        csv_path.write_text('horizon,value\nshort,1\n')
        sidecar = csv_path.with_suffix('.json')
        sidecar.write_text('{"measured": 3}')
        experiments, _ = load.load_experiments()
        self.assertEqual(experiments[0]['summary'], {'measured': 3})
        self.assertEqual(experiments[0]['summary_provenance']['source_sha256'], load.sha256(sidecar))
        original_bytes = sidecar.read_bytes()
        read_bytes = Path.read_bytes
        def replace_after_read(path):
            data = read_bytes(path)
            if path == sidecar:
                path.write_text('{"measured": 999}')
            return data
        with patch.object(Path, 'read_bytes', replace_after_read):
            experiments, _ = load.load_experiments()
        self.assertEqual(experiments[0]['summary'], {'measured': 3})
        self.assertEqual(experiments[0]['summary_provenance']['source_sha256'], hashlib.sha256(original_bytes).hexdigest())
        self.assertNotEqual(experiments[0]['summary_provenance']['source_sha256'], load.sha256(sidecar))
        # Keep the existing standalone read_sidecar helper contract outside REPO.
        with tempfile.TemporaryDirectory() as outside:
            path = Path(outside) / 'summary.json'
            path.write_text('[{"pbo":0.7}]')
            self.assertEqual(load.read_sidecar(path), (None, [{'pbo': 0.7}]))

    def test_result_and_summary_values_cannot_overwrite_reserved_metadata(self):
        path = self.results / 'sweep_demo.csv'
        path.write_text('experiment_id,kind,section,row,value\nforged,single,forged,999,3\n')
        path.with_suffix('.json').write_text(json.dumps([{'kind': 'pair', 'section': 'forged', 'row': 999, 'pbo': 0.7}]))
        _, rows = load.load_experiments()
        self.assertEqual([r['section'] for r in rows], ['result', 'summary'])
        for row in rows:
            self.assertEqual(row['experiment_id'], 'sweep/sweep_demo')
            self.assertEqual(row['kind'], 'sweep')
            self.assertEqual(row['row'], 0)
            self.assertEqual(row['source_fields']['row'], 999)
        self.assertEqual(rows[0]['source_fields']['kind'], 'single')
        self.assertEqual(rows[1]['source_fields']['kind'], 'pair')

    def test_run_identity_includes_economic_configuration(self):
        manifest = {'asset': 'SOL', 'interval': '1d', 'mode': 'perp', 'data_checksum': 'a' * 64, 'leverage': 1, 'costs': {'fee_bps': 1}, 'fill_delay': 1}
        original = load.run_identifier(manifest)
        self.assertEqual(original, load.run_identifier(dict(reversed(list(manifest.items())))))
        for changed in [{'leverage': 5}, {'costs': {'fee_bps': 2}}, {'fill_delay': 2}, {'data_checksum': 'a' * 63 + 'b'}]:
            self.assertNotEqual(original, load.run_identifier({**manifest, **changed}))

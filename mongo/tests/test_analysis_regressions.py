"""Mongo contracts tested with byte snapshots and fake collections only."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from mongo import load, schema
from mongo.tests.test_load_audit import FakeDatabase


class AnalysisLoaderRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp=self.enterContext(tempfile.TemporaryDirectory())
        self.root=Path(self.tmp)
        (self.root/'data').mkdir()
        (self.root/'results').mkdir()
        self.enterContext(mock.patch.object(load,'REPO',self.root))

    def manifest(self):
        contents={'comparison.csv':'strategy,sharpe\ns,1\n','equity_s.csv':'timestamp,equity\n60,10000\n','trades_s.csv':'ts,side\n60,buy\n'}
        for name,body in contents.items(): (self.root/'results'/name).write_text(body)
        manifest=dict(asset='SOL',interval='1d',mode='spot',strategies=['s'],artifact_sha256={n:hashlib.sha256(b.encode()).hexdigest() for n,b in contents.items()})
        return manifest,dict(source_path='results/run_manifest.json',source_sha256='a'*64,loaded_at=load.LOADED_AT)

    def test_alt_venue_sidecar_identity_and_exact_bytes_follow_bars(self):
        (self.root/'data'/'TRX_1m.csv').write_text('timestamp,open,high,low,close,volume\n60,10,11,9,10,1\n')
        sidecar=self.root/'data'/'TRX_1m.source.json'
        body=json.dumps(dict(asset='TRX',venue='okx',pair='TRX-USDT',quote='USDT'))
        sidecar.write_text(body)
        row=load.load_bars()[0]
        self.assertEqual(row['series']['source'],'okx')
        self.assertEqual(row['series']['quote'],'USDT')
        self.assertEqual(row['series']['pair'],'TRX-USDT')
        self.assertEqual(row['series']['source_metadata_provenance']['source_sha256'],hashlib.sha256(body.encode()).hexdigest())
        sidecar.write_text('{"asset":"SOL","venue":"okx","pair":"TRX-USDT","quote":"USDT"}')
        with self.assertRaises(ValueError): load.load_bars()

    def test_strategy_card_fields_and_hash_use_one_snapshot(self):
        from backtester.core import strategy_cards
        original=Path(strategy_cards.CARD_DIR)/'buy_and_hold.md'
        raw=original.read_bytes()
        directory=self.root/'cards';directory.mkdir()
        path=directory/original.name;path.write_bytes(raw)
        read_bytes,read_text=Path.read_bytes,Path.read_text
        def mutate_after_read(p):
            result=read_bytes(p)
            if p==path: p.write_bytes(raw+b'\nchanged after snapshot\n')
            return result
        def mutate_after_text(p,*args,**kwargs):
            result=read_text(p,*args,**kwargs)
            if p==path: p.write_bytes(raw+b'\nchanged after snapshot\n')
            return result
        with mock.patch.object(strategy_cards,'CARD_DIR',directory), mock.patch.object(Path,'read_bytes',mutate_after_read), mock.patch.object(Path,'read_text',mutate_after_text):
            docs=load.load_strategies()
        self.assertEqual(len(docs),1)
        self.assertEqual(docs[0]['source_sha256'],hashlib.sha256(raw).hexdigest())
        self.assertNotIn('changed after snapshot',docs[0]['body'])
        self.assertNotEqual(docs[0]['source_sha256'],load.sha256(path))

    def test_missing_declared_selected_artifacts_refuse_instead_of_empty_results(self):
        for loader,filename in ((load.load_backtest_runs,'comparison.csv'),(load.load_equity_points,'equity_s.csv'),(load.load_trades,'trades_s.csv')):
            context=self.manifest()
            (self.root/'results'/filename).unlink()
            with self.subTest(filename=filename),self.assertRaises((ValueError,FileNotFoundError)): loader(run_snapshot=context)

    def test_backtest_identity_and_results_match_bundled_query_contract(self):
        row=load.load_backtest_runs(run_snapshot=self.manifest())[0]
        for key,value in [('asset','SOL'),('interval','1d'),('mode','spot')]: self.assertEqual(row[key],value)
        self.assertEqual(row['results'],[dict(strategy='s',sharpe=1)])
        self.assertEqual(row['comparison'],row['results'])
        self.assertIsNotNone(row['comparison_provenance'])

    def test_ordinary_reload_never_drops_historical_test_receipts(self):
        db=FakeDatabase()
        def create_fake(db,*,drop,only):
            if drop:
                for n in only if only is not None else schema.ALL_COLLECTIONS: db.drop_collection(n)
        with mock.patch.object(load,'build_all',return_value={'signals':[],'test_results':[]}),mock.patch.object(load,'connect',return_value={schema.DB_NAME:db}),mock.patch.object(load,'create',side_effect=create_fake),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(load.main([]),0)
        self.assertNotIn(('drop','test_results'),db.calls)
        self.assertIn(('drop','signals'),db.calls)

    def test_observed_test_receipts_upsert_by_commit_suite_and_preserve_skipped_suites(self):
        class Receipts:
            def __init__(self): self.rows={('old','backtester'):{'git_sha':'old','suite':'backtester'},('new','soltui'):{'git_sha':'new','suite':'soltui'}}
            def replace_one(self,key,row,*,upsert):
                self.assert_key=key
                assert upsert
                self.rows[(key['git_sha'],key['suite'])]=row
            def insert_many(self,rows,**kw): self.rows={('bad','bad'):rows}
        receipts=Receipts()
        db={'test_results':receipts}
        row={'git_sha':'new','suite':'backtester','ok':True,'count':2}
        with mock.patch.object(load,'build_all',return_value={'test_results':[row]}),mock.patch.object(load,'connect',return_value={schema.DB_NAME:db}),mock.patch.object(load,'create') as create,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(load.main(['--only','test_results','--run-tests','--skip-suite','soltui']),0)
        self.assertEqual(set(receipts.rows),{('old','backtester'),('new','soltui'),('new','backtester')})
        create.assert_called_once_with(db,drop=False,only={'test_results'})

    def test_keep_mode_validates_existing_timeseries_layout(self):
        from pymongo.errors import CollectionInvalid
        for options in ({},{'timeseries':{'timeField':'legacy','metaField':'series','granularity':'hours'}},{'timeseries':{'timeField':'ts','metaField':'series','granularity':'minutes'}},{'timeseries':{'timeField':'ts','metaField':'series','granularity':'hours'}},
                        {'timeseries':{'timeField':'ts','metaField':'series','granularity':'hours','bucketMaxSpanSeconds':2592000,'bucketRoundingSeconds':86400}},
                        {'timeseries':{'timeField':'ts','metaField':'series','bucketMaxSpanSeconds':3600,'bucketRoundingSeconds':3600}}):
            collection=mock.Mock();collection.options.return_value=options
            db=mock.MagicMock();db.create_collection.side_effect=CollectionInvalid('exists');db.__getitem__.return_value=collection
            compatible=all(options.get('timeseries',{}).get(k)==v for k,v in schema.TIME_SERIES['bars']['timeseries'].items())
            with self.subTest(options=options):
                if compatible: self.assertEqual(schema.create(db,drop=False,only={'bars'}),['bars'])
                else:
                    with self.assertRaisesRegex(ValueError,'schema|layout|timeseries'): schema.create(db,drop=False,only={'bars'})
                db.drop_collection.assert_not_called()
                collection.options.assert_called_once()


class AdditionalLoaderRegressions(unittest.TestCase):
    setUp = AnalysisLoaderRegressions.setUp
    manifest = AnalysisLoaderRegressions.manifest
    def test_missing_artifacts_refuse_before_any_database_operation(self):
        context=self.manifest()
        (self.root/'results'/'equity_s.csv').unlink()
        with mock.patch.object(load,'run_context',return_value=context),mock.patch.object(load,'connect') as connect,mock.patch.object(load,'create') as create:
            with self.assertRaises(ValueError): load.main(['--only','equity_points'])
        connect.assert_not_called()
        create.assert_not_called()

    def test_untouched_test_results_are_omitted_from_rebuild_batches(self):
        with mock.patch.object(load,'load_test_results') as receipts:
            self.assertEqual(load.build_all({'test_results'},run_suites=False),{})
        receipts.assert_not_called()

    def test_all_supported_venue_pair_formats_and_source_snapshot_races(self):
        from backtester.core.fetch_minutes_alt import VENUES
        path=self.root/'data'/'SOL_1m.csv'
        path.write_text('timestamp,open,high,low,close,volume\n60,10,11,9,10,1\n')
        source=path.with_suffix('.source.json')
        for venue,contract in VENUES.items():
            metadata=dict(asset='SOL',venue=venue,pair=contract.pair('SOL'),quote='USDT')
            raw=json.dumps(metadata).encode()
            source.write_bytes(raw)
            reader=Path.read_bytes
            def mutate(p):
                value=reader(p)
                if p==source: p.write_bytes(b'{"asset":"FORGED"}')
                return value
            with self.subTest(venue=venue),mock.patch.object(Path,'read_bytes',mutate):
                row=load.load_bars()[0]['series']
                self.assertEqual(row['source'],venue)
                self.assertEqual(row['pair'],contract.pair('SOL'))
                self.assertEqual(row['source_metadata_provenance']['source_sha256'],hashlib.sha256(raw).hexdigest())
            source.write_text(json.dumps({**metadata,'pair':'WRONG-USDT'}))
            with self.assertRaises(ValueError): load.load_bars()
        source.unlink()
        self.assertEqual(load.load_bars()[0]['series']['quote'],'USD')

    def test_proven_zero_row_artifacts_are_distinct_from_missing_files(self):
        manifest,prov=self.manifest()
        for name,header in [('comparison.csv','strategy,sharpe\n'),('equity_s.csv','timestamp,equity\n'),('trades_s.csv','ts,side\n')]:
            path=self.root/'results'/name
            path.write_text(header)
            manifest['artifact_sha256'][name]=hashlib.sha256(header.encode()).hexdigest()
        context=(manifest,prov)
        run=load.load_backtest_runs(run_snapshot=context)[0]
        self.assertEqual(run['results'],[])
        self.assertIsNotNone(run['comparison_provenance'])
        self.assertEqual(load.load_equity_points(run_snapshot=context),[])
        self.assertEqual(load.load_trades(run_snapshot=context),[])

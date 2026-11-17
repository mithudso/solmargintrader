"""Retained-candle and publication boundaries with disposable SQLite fixtures."""
from __future__ import annotations
import json
import sqlite3
import threading
import unittest
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
import numpy as np
from soltui import bots, config, forwardtest as ft, council
from . import test_forwardtest as fixtures
from . import test_council as council_fixtures

BASE=fixtures.BASE


class ForwardIntegrity(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root=Path(tmp.name)
        self.enterContext(mock.patch.object(config,'CONFIG_DIR',self.root))
        self.trial={'label':'fixture','mode':'all','members':[ft.member('buy_and_hold',{})]}

    def tick(self, minute, **kwargs):
        return ft.tick('SOL',[self.trial],(1,),16.,fetch=lambda *a,**k:fixtures.candles(minute),clock=lambda:BASE+minute*60+4, code='integrity-fixture', **kwargs)

    def test_retained_candle_controls_settlement_after_fetched_revision(self):
        # CDO-66591df3e8
        self.tick(0,tune=False)
        with closing(ft._db()) as db, db:
            db.execute('INSERT INTO candle VALUES (?,?,?,?,?,?,?)',('SOL',BASE+60,100.,100.,90.,90.,1.))
        self.tick(2,tune=False)
        with closing(ft._db()) as db:
            call=db.execute('SELECT outcome,bps FROM call WHERE bar=?',(BASE-60,)).fetchone()
            retained=db.execute('SELECT close FROM candle WHERE asset=? AND ts=?',('SOL',BASE+60)).fetchone()[0]
        self.assertEqual(retained,90.)
        self.assertEqual(call[0],-1)
        self.assertAlmostEqual(call[1],10000*np.log(.9))

    def test_rolled_back_adoption_cannot_publish_default(self):
        # CDO-862a03f2de
        stopped=threading.Event()
        def adopt_then_cancel(db,key,generation,active,moved,cost,candles,bar,minutes,tune,on_adopt,**_):
            on_adopt(active,active,.99,100)
            stopped.set()
            return active,generation
        with mock.patch.object(ft,'_resolve',side_effect=adopt_then_cancel):
            with self.assertRaisesRegex(RuntimeError,'stopped'):
                self.tick(0,stop=stopped)
        self.assertEqual(ft.load_defaults(),{})
        with closing(ft._db()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM trial').fetchone()[0],0)

    def test_bridged_candles_keep_an_observation_mask(self):
        # CDO-b818b9a083 / CDO-2ee26a74b8
        arrays=fixtures.candles(2)
        selected={k:v[-3:][[0,2]] for k,v in arrays.items()}
        result=bots.bridged(selected,step=60)
        np.testing.assert_array_equal(result['bars']['observed'],[True,False,True])
        malformed={**selected,'ts':np.array([BASE,BASE+59])}
        with self.assertRaisesRegex(ValueError,'cadence'):
            bots.bridged(malformed,step=60)
        minutes=bots.MinuteBars('fixture'); minutes.bars={BASE:[100.]*4,BASE+120:[200.]*4}
        actual,_,_=minutes.arrays(BASE+180)
        np.testing.assert_array_equal(actual['observed'],[True,False,True])

    def test_failed_default_export_remains_committed_and_retryable(self):
        def adopt(db,key,generation,active,moved,cost,candles,bar,minutes,tune,on_adopt,**_):
            on_adopt(active,active,.99,100)
            return active,generation
        with mock.patch.object(ft,'_resolve',side_effect=adopt), mock.patch.object(ft,'save_default',side_effect=OSError('fixture disk unavailable')):
            with self.assertRaises(OSError):
                self.tick(0)
        with closing(ft._db()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_export').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM trial').fetchone()[0],1)
        ft._export_committed_defaults(None)
        self.assertIn('SOL|fixture|1',ft.load_defaults())
        with closing(ft._db()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_export').fetchone()[0],0)

    def test_council_recovers_more_than_seven_days_in_bounded_pages(self):
        # CDO-012278d812
        council.config({'execution':{'min_confidence':0}})
        def step(minute):
            now=BASE+minute*60+5
            return council.step(now=now,snapshot={'rows':council_fixtures.rows(expires=now+60)},quote={'source':'jupiter','price':100.,'fetched_at':now},bars=council_fixtures.bars(now),recover=lambda _:None)
        step(0); before=step(2)
        self.assertIsNotNone(before['position'])
        requested=[]
        def fetch(asset,*,now,bars,seconds,**_):
            requested.append(bars)
            latest=int(now//60)*60-60
            ts=np.arange(latest-(bars-1)*60,latest+1,60)
            return {'ts':ts,**{k:np.full(len(ts),100.) for k in ('open','high','low','close','volume')}}
        now=BASE+10085*60+5
        with mock.patch.object(council.compound,'fetch_closed_candles',side_effect=fetch):
            middle=council.step(now=now,snapshot={'rows':[]},quote={},recover=lambda _:None)
            final=council.step(now=now,snapshot={'rows':[]},quote={},recover=lambda _:None)
        self.assertGreater(middle['last_bar'],before['last_bar'])
        self.assertEqual(final['last_bar'],BASE+10084*60)
        self.assertTrue(all(n<=10080 for n in requested))
        self.assertIsNotNone(final['position'])

"""Bounded synthetic/mocked guards for research selection and experiment identity."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from backtester.core.cpcv import CpcvResult, pbo_cscv
from backtester.core.engine import EngineConfig
from backtester.tests.test_engine_audit import bars
from research import cpcv_sweep as cpcv, decide, sweep


class WarmupParityRegressions(unittest.TestCase):
    def test_exposure_replay_helper_is_bound_by_evidence_identity(self):
        from research.evidence import source_hashes
        hashes = source_hashes()
        replay_source = Path(decide.__file__).read_bytes()
        self.assertEqual(hashes['research/decide.py'], hashlib.sha256(replay_source).hexdigest())

    def test_stateful_single_and_composite_exposures_match_engine_warmup(self):
        from research import signal_redundancy as producer
        from backtester.core.strategies import build, build_composite
        close = np.concatenate((100.-np.arange(15), np.full(305, 94.)))
        arrays = bars(close)
        arrays['high'] += 1
        arrays['low'] -= 1
        params = {'rsi':dict(period=14, oversold=30, exit_level=50),
                  'sma_regime':dict(window=100)}
        with mock.patch.object(producer, 'REGISTRY', {'rsi':None}):
            singles, warmups = producer.exposure_matrix(arrays, params, progress_every=0)
        expected = decide.replay_targets(build('rsi', **params['rsi']), arrays)
        np.testing.assert_array_equal(singles['rsi'], expected)
        self.assertTrue(np.isnan(singles['rsi'][:warmups['rsi']]).all())
        for mode in ('any', 'all'):
            with self.subTest(mode=mode):
                combined, warmup = producer.combination_exposures(arrays, params,
                            [('rsi', 'sma_regime')], mode, progress_every=0)
                expected = decide.replay_targets(build_composite(list(params.items()), mode=mode), arrays)
                np.testing.assert_array_equal(combined['rsi+sma_regime'], expected)
                self.assertTrue(np.isnan(combined['rsi+sma_regime'][:warmup]).all())
        self.assertEqual(singles['rsi'][250], 0.)


class ResearchRegressions(unittest.TestCase):
    def test_exact_equal_comparisons_and_zero_signs_are_neutral(self):
        w=decide.final_window(decide.validate_arrays(bars((100.,)*300)))
        signals={r.key:r for r in decide.signal_readings(w)}
        indicators={r.key:r for r in decide.indicator_readings(w)}
        for key in ('ts_momentum_60', 'macd_cross', 'sma_200_regime', 'sma_50_200_cross', 'vwap_20_reversion', 'obv_trend_20'):
            with self.subTest(key=key): self.assertEqual(signals[key].reading, decide.NEUTRAL)
        for key in ('roc', 'macd_12_26_9', 'ppo_12_26_9'):
            with self.subTest(key=key): self.assertEqual(indicators[key].reading, decide.NEUTRAL)

    def test_oos_fills_first_split_open_for_every_positive_delay(self):
        a=bars((100.,)*21+(200.,)*9, (100.,)*22+(200.,)*8)
        for delay in (1, 2, 3):
            cfg=EngineConfig(fill_delay=delay)
            with self.subTest(delay=delay):
                _, _, oos=sweep.walk_forward(lambda: sweep.build('buy_and_hold'), a, cfg)
                self.assertGreater(oos.total_return, .98)

    def test_legacy_full_history_gate_is_refused_before_selection(self):
        csv='a,b,corr,redundant\nma_crossover,rsi,0.1,False\n'
        with tempfile.TemporaryDirectory() as td, mock.patch.object(sweep, 'OUT_DIR', Path(td)), mock.patch.object(sweep, 'load_horizon', return_value=(bars((100.,)*100), EngineConfig())):
            (Path(td)/sweep.redundancy_filename('SOL','medium')).write_text(csv)
            with self.assertRaisesRegex(SystemExit, 'discovery|manifest|proof'):
                sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured')

    def test_triples_only_resolves_discovery_prerequisite(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(sweep, 'OUT_DIR', Path(td)), mock.patch.object(sweep, 'sweep_singles', return_value=[]) as singles, mock.patch.object(sweep, 'fmt_table', return_value=''), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sweep.main(['--stage','triples','--horizon','medium','--pair-gate','family']),0)
            singles.assert_called_once_with('medium')
            counts=json.loads((Path(td)/'configuration_counts.json').read_text())
            self.assertIn('medium/singles',counts)

    def test_low_positive_share_does_not_claim_profitable_winner_loses(self):
        noise=np.array([-.0003,.0003,-.0001,.0001])
        blocks={f'config{i}':[noise+mean for _ in range(4)] for i,mean in enumerate([-.009,-.008,-.007,-.006,-.005,-.004,-.003,-.002,-.001,.002])}
        p=pbo_cscv(blocks)
        self.assertEqual(p['pbo'],0)
        text=' '.join(cpcv.interpret(10,10,1,p['pbo']))
        self.assertNotIn('reliably as a loser',text)
        self.assertIn('winner',text.lower())

    def test_cpcv_results_bind_data_geometry_costs_parameters_and_candidate_gate(self):
        result=CpcvResult('fixture',8,2,1,np.array([1.]),np.array([.1]),np.array([1.]),12,4)
        for combo in (False,True):
            with mock.patch.object(cpcv, 'load_horizon', return_value=(bars((100.,)*100),EngineConfig())), mock.patch.object(cpcv,'cpcv_evaluate',return_value=result):
                rows,pbo=(cpcv.run_combos('medium',2,8,2,('all',),('ma_crossover','rsi'),gate='family') if combo else cpcv.run_horizon('medium',8,2))
            for key in ('run_id','data_checksum','engine_config','n_groups','k_test','parameters','pair_gate'):
                with self.subTest(combo=combo,key=key):
                    self.assertIn(key,rows.columns)
                    self.assertIn(key,pbo)
            self.assertIn('manifest',pbo)
            self.assertEqual(pbo['manifest']['pair_gate'], 'family' if combo else None)
            self.assertTrue((rows.run_id==pbo['run_id']).all())


class DiscoveryEvidenceRegressions(unittest.TestCase):
    def test_producer_and_gate_ignore_heldout_prices_and_exposures(self):
        import pandas as pd
        from research import signal_redundancy as producer
        from research.evidence import discovery_context, identity
        a=bars(tuple(100+np.tile([-1.,1.],50)))
        a['volume']=1+np.tile([0.,0.,1.,1.],25)
        outputs=[]
        for reverse in (False,True):
            data={k:v.copy() for k,v in a.items()}
            data['volume'][70:]=(data['close'][70:]>100) if not reverse else (data['close'][70:]<100)
            def exposures(arrays, params):
                return pd.DataFrame({'ma_crossover':(arrays['close']>100).astype(float),'rsi':(arrays['volume']>1).astype(float)}), {'ma_crossover':0,'rsi':0}
            with tempfile.TemporaryDirectory() as td, mock.patch.object(sweep,'OUT_DIR',Path(td)), mock.patch.object(producer,'OUT',Path(td)), mock.patch.object(producer,'load_series',return_value=(data,sweep.HORIZONS['medium']['params'],'fixture')), mock.patch.object(producer,'exposure_matrix',side_effect=exposures) as expose, mock.patch.object(sweep,'load_horizon',return_value=(data,EngineConfig())), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(producer.main(['--horizon','medium','--out','auto']),0)
                self.assertEqual(len(expose.call_args.args[0]['ts']),70)
                target=Path(td)/sweep.redundancy_filename('SOL','medium')
                proof=json.loads(target.with_suffix('.manifest.json').read_text())
                self.assertEqual(proof['scope'],'discovery')
                outputs.append((target.read_bytes(),proof,sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured')))
        self.assertEqual(outputs[0],outputs[1])

    def test_gate_rejects_changed_artifact_parameters_cutoff_and_full_scope(self):
        from research.evidence import discovery_context, write_gate_proof
        data=bars((100.,)*100)
        _,context=discovery_context(data,sweep.HORIZONS['medium']['params'],'SOL','medium',sweep.SPLIT)
        csv='a,b,corr,redundant\nma_crossover,rsi,0.1,False\n'
        with tempfile.TemporaryDirectory() as td,mock.patch.object(sweep,'OUT_DIR',Path(td)),mock.patch.object(sweep,'load_horizon',return_value=(data,EngineConfig())):
            target=Path(td)/sweep.redundancy_filename('SOL','medium')
            target.write_text(csv)
            write_gate_proof(target,context)
            self.assertEqual(sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured'),[('ma_crossover','rsi')])
            for change in (dict(scope='full'),dict(cutoff_ts=context['cutoff_ts']+86400),dict(parameters={}),dict(data_checksum='wrong')):
                write_gate_proof(target,{**context,**change})
                with self.subTest(change=change),self.assertRaisesRegex(SystemExit,'discovery manifest'):
                    sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured')
            write_gate_proof(target,context)
            target.write_text(csv.replace('False','True'))
            with self.assertRaisesRegex(SystemExit,'discovery manifest'):
                sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured')
            target.write_text(csv)
            write_gate_proof(target,context)
            combo=Path(td)/sweep.combination_redundancy_filename('SOL','medium')
            combo.write_text('a,b,redundant\nall(ma_crossover+rsi),all(ma_crossover+rsi),True\n')
            with self.assertRaisesRegex(SystemExit,'discovery manifest'):
                sweep.independent_combos(('ma_crossover','rsi'),2,'medium','measured')

    def test_cpcv_run_identity_changes_with_data_cost_geometry_and_exact_parameters(self):
        from research.evidence import identity
        data=bars((100.,)*100)
        cfg=EngineConfig()
        result=CpcvResult('fixture',8,2,1,np.array([1.]),np.array([.1]),np.array([1.]),12,4)
        def run(arrays=data,config=cfg,groups=8):
            with mock.patch.object(cpcv,'load_horizon',return_value=(arrays,config)),mock.patch.object(cpcv,'cpcv_evaluate',return_value=result):
                _,pbo=cpcv.run_horizon('medium',groups,2)
                self.assertEqual(pbo['run_id'],identity(pbo['manifest']))
                return pbo
        original=run()
        wick={k:v.copy() for k,v in data.items()};wick['low'][20]=90.
        expensive=EngineConfig();expensive.costs.fee_bps+=1
        for variant in (run(wick),run(config=expensive),run(groups=10)):
            self.assertNotEqual(original['run_id'],variant['run_id'])
        params={name:dict(values) for name,values in sweep.HORIZONS['medium']['params'].items()}
        params['ma_crossover']['fast']=21
        with mock.patch.dict(sweep.HORIZONS['medium'],{'params':params}):
            changed=run()
        self.assertNotEqual(original['run_id'],changed['run_id'])

    def test_combination_measurement_uses_the_same_discovery_prefix_as_members(self):
        import pandas as pd
        from research import signal_redundancy as producer
        data=bars((100.,)*100)
        group=[('ma_crossover','rsi'),('ma_crossover','bb_reversion')]
        def exposures(arrays, params, combos, mode):
            n=len(arrays['ts'])
            return pd.DataFrame({'ma_crossover+rsi':np.arange(n)%2,'ma_crossover+bb_reversion':np.arange(n)%2}),0
        with mock.patch.object(producer,'load_series',return_value=(data,sweep.HORIZONS['medium']['params'],'fixture')), mock.patch.object(sweep,'redundancy_classes',return_value=({},[])) as classes, mock.patch.object(producer,'twin_groups',return_value=[group]), mock.patch.object(producer,'combination_exposures',side_effect=exposures) as expose, contextlib.redirect_stderr(io.StringIO()):
            table=producer.combination_redundancy('SOL','medium',(2,),('all',))
        self.assertEqual(len(expose.call_args.args[0]['ts']),70)
        self.assertEqual(table.attrs['discovery_context']['bars'],70)
        self.assertEqual(classes.call_args.kwargs['discovery']['cutoff_ts'],int(data['ts'][70]))

    def test_explicit_family_gate_does_not_require_measured_artifacts_for_diagnostics(self):
        with mock.patch.object(sweep,'load_horizon',return_value=(bars((100.,)*100),EngineConfig())), mock.patch.object(sweep,'walk_forward',return_value=(None,None,None)), mock.patch.object(sweep,'gate_counts',side_effect=AssertionError('measured evidence must not gate explicit family selection')), contextlib.redirect_stderr(io.StringIO()):
            rows=sweep.sweep_combos('medium',2,modes=('all',),gate='family')
        self.assertGreater(len(rows),0)

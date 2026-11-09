"""Offline counterexamples for allocation, causal intrabar data and research economics."""
from __future__ import annotations

from collections import Counter
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd

from backtester.core import compound, fetch_minutes as fm, gridsim, scorecard as sc
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.types import CostConfig, IntrabarLayer, Mode
from backtester.tests.test_engine_audit import Always, bars, zero_cost


class SecondAuditRegressions(unittest.TestCase):
    @staticmethod
    def evaluation(closes, calls, *, hold=1, blocked=None):
        arrays = bars(closes)
        b = sc.Bars.from_mapping(arrays)
        cfg = sc.default_config()
        cfg['aggregate']['hold'] = hold
        return sc.Evaluation(b, cfg, {}, {}, np.full(len(b), 'neutral'),
                             np.asarray(calls, dtype=float), np.ones(len(b)),
                             np.asarray(blocked if blocked is not None else [False]*len(b)),
                             np.asarray(calls, dtype='int8'))

    def test_open_gap_liquidates_old_collateral_before_every_queued_target(self):
        from backtester.core.compound import PrecomputedTargets
        for side, gap in ((1., 84.), (-1., 116.)):
            for queued in (0., side, -side):
                a = bars((100., 100., gap))
                a['ts'] = 1_700_000_100 + np.arange(3)*300
                cfg = EngineConfig(mode=Mode.PERP, interval='5m', leverage=5,
                                   allow_short=True, fill_delay=1,
                                   costs=zero_cost(max_lev_constant=20,
                                                   liquidation_forfeits_collateral=True))
                with self.subTest(side=side, queued=queued):
                    result = run_backtest(PrecomputedTargets([side, queued, 0.]), a, cfg)
                    self.assertEqual(result.liquidation_count, 1)
                    self.assertEqual(result.metrics.final_equity, 0.)
                    gap_trades = [t for t in result.trades if t.bar_index == 2]
                    self.assertEqual(gap_trades[0].reason, 'liquidation')
                    self.assertFalse(any(t.reason == 'resize_down' for t in gap_trades))

    def test_minimum_hold_blocks_early_opposite_calls_but_gates_still_exit(self):
        for side in (1, -1):
            calls = [side, -side, -side, -side, -side]
            with self.subTest(side=side):
                ev = self.evaluation([100.]*5, calls, hold=4)
                np.testing.assert_array_equal(sc.target_path(ev), [side]*4+[-side])
                ev.blocked[2] = True
                np.testing.assert_array_equal(sc.target_path(ev), [side, side, 0., -side, -side])

    def test_forecast_statistics_cannot_use_outcomes_at_or_after_split(self):
        results = []
        for future in (200., 50.):
            close = [100.+i for i in range(30)] + [future]*300
            ev = self.evaluation(close, [1]*len(close))
            results.append(sc.forecast_stats([ev], None, ev.bars.ts[30]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]['bars'], 29)
        self.assertEqual({r['bars']:r['calls'] for r in results[0]['horizons']},
                         {1:29, 6:24, 12:18})

    def test_non_list_candle_json_refuses_and_leaves_fetch_window_retryable(self):
        for raw in (b'null', b'false', b'0', b'""', b'"candles"'):
            with self.subTest(raw=raw), mock.patch.object(fm.urllib.request, 'urlopen',
                    side_effect=lambda *a, **k: io.BytesIO(raw)):
                with self.assertRaises(fm.FetchError):
                    fm.get_candles('https://invalid.example/offline')
        with tempfile.TemporaryDirectory() as td, mock.patch.object(fm, 'DATA', Path(td)), \
                mock.patch.object(fm, 'effective_windows', return_value=[0]), \
                mock.patch.object(fm.urllib.request, 'urlopen', side_effect=lambda *a, **k: io.BytesIO(b'null')), \
                mock.patch.object(fm, 'save_progress') as save, \
                mock.patch.object(fm, 'finalise', return_value=pd.DataFrame()), \
                mock.patch.object(fm, 'coverage', return_value='offline'):
            self.assertEqual(fm.fetch_minutes('BTC', 1, workers=1, resume=False, verbose=False), 'offline')
            self.assertTrue(save.called)
            self.assertTrue(all(call.args[1] == set() for call in save.call_args_list))
        with mock.patch.object(fm.urllib.request, 'urlopen', return_value=io.BytesIO(b'[]')):
            self.assertEqual(fm.get_candles('https://invalid.example/offline'), [])


class AnalysisRegressions(unittest.TestCase):
    def test_partial_to_full_allocation_spends_cash_after_costs(self):
        class Increase(Always):
            def on_bar(self, h): return .5 if h.i == 0 else 1.
        for mode, leverage in ((Mode.SPOT, 1), (Mode.PERP, 10)):
            costs = CostConfig(fee_bps=10, perp_base_fee_bps=10, slippage_bps=2, max_hourly_rate_bps_long=0, max_hourly_rate_bps_short=0)
            cfg = EngineConfig(mode=mode, leverage=leverage, costs=costs, fill_delay=0)
            result = run_backtest(Increase(), bars((100., 100., 100.)), cfg)
            with self.subTest(mode=mode):
                self.assertGreater(result.exposure[1], .99 * leverage)
                self.assertTrue(any(t.reason == 'resize_up' for t in result.trades))
                self.assertAlmostEqual(sum(t.realized_pnl for t in result.trades), result.metrics.final_equity - 10000)
                self.assertGreater(result.metrics.total_fees, 0)

    def test_near_threshold_coarse_touch_is_honored_for_both_sides(self):
        for side in (1., -1.):
            class Hold(Always):
                def on_bar(self, h): return side
            d = bars((100., 100.))
            hts = d['ts'][0] + np.arange(48) * 3600
            fine = dict(ts=hts, open=np.full(48, 100.), close=np.full(48, 100.),
                        low=np.full(48, 90.21 if side > 0 else 100.),
                        high=np.full(48, 100. if side > 0 else 109.79))
            d['low'][1] = 90.19 if side > 0 else 100.
            d['high'][1] = 100. if side > 0 else 109.81
            cfg = dict(mode=Mode.PERP, leverage=10, fill_delay=0, allow_short=True, costs=zero_cost(liquidation_forfeits_collateral=True))
            coarse = run_backtest(Hold(), d, EngineConfig(**cfg))
            refined = run_backtest(Hold(), d, EngineConfig(**cfg, intrabar=(IntrabarLayer('1h', fine),)))
            with self.subTest(side=side):
                self.assertEqual(coarse.liquidation_count, 1)
                self.assertEqual(refined.liquidation_count, 1)
                self.assertEqual(refined.bars_range_mismatch, 0)
                self.assertEqual(coarse.metrics.final_equity, refined.metrics.final_equity)

    def test_shifted_and_clustered_count_complete_layers_cannot_refine_or_see_future(self):
        d = bars((100., 100.))
        cfg = dict(mode=Mode.PERP, leverage=10, fill_delay=0, costs=zero_cost())
        for clustered in (False, True):
            offsets = np.arange(24) * (60 if clustered else 3600) + (0 if clustered else 1800)
            ts = np.concatenate([t + offsets for t in d['ts']])
            fine = {key: np.full(48, 100.) for key in ('open', 'high', 'low', 'close')}
            fine['ts'] = ts
            clean = run_backtest(Always(), d, EngineConfig(**cfg, intrabar=(IntrabarLayer('1h', fine),)))
            fine = {k: v.copy() for k, v in fine.items()}
            fine['low'][-1] = 80.
            poison = run_backtest(Always(), d, EngineConfig(**cfg, intrabar=(IntrabarLayer('1h', fine),)))
            with self.subTest(clustered=clustered):
                self.assertEqual(clean.bars_refined, 0)
                self.assertEqual(poison.liquidation_count, 0)
                np.testing.assert_array_equal(clean.equity, poison.equity)

    def test_grid_full_plan_matches_extension_when_slippage_crosses_midpoint(self):
        cfg = gridsim.GridConfig(100, 102, 3, 12, spacing='arith')
        book = gridsim._GridBook(1000, CostConfig(fee_bps=0, slippage_bps=60))
        book.buy(100, .12, 0, 0)
        plan = gridsim._plan(cfg, [100., 101., 102.], 100.8, book.lots, Counter())
        script = """import { planGrid } from './extension/src/core/grid.js';
        const p=planGrid({config:{gridId:'x',lower:100,upper:102,rungs:3,spacing:'arith',notionalPerRungUsd:12},price:100.8,openLots:[{baseQty:.12,priceUsd:100.6}]});
        console.log(JSON.stringify(p.intents.map(x=>({side:x.side,level:x.level}))));"""
        js = subprocess.run(['node', '--input-type=module', '-e', script], cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, check=True)
        self.assertEqual([dict(side=x.side, level=x.level) for x in plan], json.loads(js.stdout))
        self.assertEqual(plan[0].closes, ((100., .12),))

    def test_bar_hash_identifies_every_ohlcv_and_quality_input(self):
        frame = pd.DataFrame(dict(timestamp=[0, 300], open=[100., 100.], high=[101., 101.], low=[99., 99.], close=[100., 100.], volume=[1., 1.], minutes=[5, 5]))
        original = compound._hash_frame(frame)
        for key in ('timestamp', 'open', 'high', 'low', 'close', 'volume', 'minutes'):
            changed = frame.copy()
            changed.loc[0, key] += 1
            with self.subTest(key=key): self.assertNotEqual(original, compound._hash_frame(changed))
        self.assertEqual(original, compound._hash_frame(frame[list(reversed(frame.columns))]))

    def test_public_compound_identity_binds_auxiliary_inputs_and_low_only_liquidations(self):
        n=600
        close=100+.05*np.arange(n)
        op=np.r_[close[0],close[:-1]]
        frame=pd.DataFrame(dict(timestamp=1700000100+300*np.arange(n),open=op,high=close+.1,low=op-.1,close=close,volume=np.ones(n)))
        cfg=sc.standalone_config(sc.default_config(),'ema_cross')
        cfg['execution']['leverage']=5.
        def report(df=frame, funding=None, btc=None, events=None):
            prep=dict(asset='SOL',bars=df,source='synthetic',funding=funding,btc=btc,data_hash=compound._hash_frame(df),incomplete_pct=None)
            return compound.run_compound('SOL',cfg,prepared=prep,events=events)
        original=report()
        wick=frame.copy();wick.loc[500,'low']=10.
        changed=report(wick)
        self.assertEqual(original['oos']['pnl']['liquidations'],0)
        self.assertEqual(changed['oos']['pnl']['liquidations'],1)
        self.assertNotEqual(original['data_hash'],changed['data_hash'])
        for kwargs in (dict(funding={'ts':np.array([frame.timestamp.iloc[0]]),'rate':np.array([.0001])}),
                       dict(btc=np.full(n,50000.)),dict(events=[{'ts':int(frame.timestamp.iloc[450]),'title':'fixture'}])):
            with self.subTest(kwargs=tuple(kwargs)):
                variant=report(**kwargs)
                self.assertNotEqual(original['input_hash'],variant['input_hash'])
                self.assertEqual(original['data_hash'],variant['data_hash'])

    def test_final_resolved_horizon_call_and_minimum_length_are_included(self):
        for closes in ((100., 110., 90.), (100., 110.)):
            n = len(closes)
            b = sc.Bars(np.arange(n)*300, np.full(n, 100.), np.maximum(closes, 100), np.minimum(closes, 100), np.array(closes), np.ones(n))
            ev = sc.Evaluation(b, sc.default_config(), {}, {}, np.zeros(n), np.ones(n), np.ones(n), np.zeros(n, dtype=bool), np.ones(n))
            h = sc.forecast_stats([ev])['horizons'][0]
            self.assertEqual(h['calls'], n-1)
            self.assertAlmostEqual(h['gross_bps'], round(float(np.log(np.array(closes[1:])/100).mean()*1e4), 3))

    def test_every_accepted_short_quantile_window_evaluates_causally(self):
        n=50
        b = sc.Bars(np.arange(n)*300, np.full(n, 100.), np.full(n, 101.), np.full(n, 99.), np.full(n, 100.), np.ones(n))
        for window in (12, 19, 20):
            for quantile in (0., .9):
                cfg=sc.default_config()
                cfg['aggregate'].update(adaptive_window=window, entry_quantile=quantile)
                with self.subTest(window=window, quantile=quantile):
                    full=sc.evaluate(b, sc.normalise_config(cfg))
                    prefix=sc.evaluate(b.slice(35), cfg)
                    np.testing.assert_array_equal(full.indication[:35], prefix.indication)


class FetchRegressions(unittest.TestCase):
    def test_internal_multi_window_outage_cannot_hide_earlier_served_history(self):
        windows=list(range(0, 12*fm.WINDOW_SECONDS, fm.WINDOW_SECONDS))
        def response(url, limiter):
            start=int(pd.Timestamp(url.split('start=')[1].split('&')[0]).timestamp())
            return [1] if windows.index(start) in (3, 4, 8, 9, 10, 11) else []
        with mock.patch.object(fm, 'plan_windows', return_value=windows), mock.patch.object(fm, 'get_candles', side_effect=response):
            self.assertEqual(fm.first_available('SOL', 1), windows[3])

    def test_invalid_ohlcv_or_timestamp_is_refused_before_cache(self):
        bad = ([[60, 12, 9, 10, 11, 1]], [[60, 9, 12, 10, float('nan'), 1]],
               [[60.5, 9, 12, 10, 11, 1]], [[61, 9, 12, 10, 11, 1]],
               [[60, 9, 12, 10, 11, -1]], [[60, 9, 12, 10, 11]])
        for rows in bad:
            with self.subTest(rows=rows), self.assertRaises(fm.FetchError): fm._window_frame(rows)

    def test_append_interruption_does_not_commit_unwritten_window(self):
        import tempfile
        for error in (KeyboardInterrupt, OSError):
            with tempfile.TemporaryDirectory() as td, mock.patch.object(fm, 'DATA', Path(td)), mock.patch.object(fm, 'effective_windows', return_value=[0]), mock.patch.object(fm, 'get_candles', return_value=[[60, 9, 12, 10, 11, 1]]), mock.patch.object(pd.DataFrame, 'to_csv', side_effect=error), mock.patch.object(fm, 'save_progress') as save:
                with self.assertRaises(error): fm.fetch_minutes('SOL', 1, verbose=False)
                self.assertTrue(save.called)
                self.assertNotIn(0, save.call_args.args[1])

    def test_shallow_probe_does_not_claim_deeper_coverage(self):
        windows=list(range(0, 12*fm.WINDOW_SECONDS, fm.WINDOW_SECONDS))
        frame=pd.DataFrame({'timestamp':np.arange(windows[6], windows[-1]+fm.WINDOW_SECONDS,60)})
        with mock.patch.object(fm, 'plan_windows', return_value=windows), mock.patch.object(fm, 'load_probe', return_value=(windows[6], windows[6])), mock.patch.object(fm, 'load_progress', return_value=set(windows[6:])):
            cov=fm.coverage('SOL', frame, 1, now=windows[-1]+fm.WINDOW_SECONDS)
            self.assertEqual(cov.windows_total, 12)
            self.assertFalse(cov.complete_fetch)


class FetchDurabilityRegressions(unittest.TestCase):
    def test_interrupted_partial_row_is_rolled_back_then_retried(self):
        import tempfile
        original=pd.DataFrame.to_csv
        for failure in (KeyboardInterrupt,OSError):
            with tempfile.TemporaryDirectory() as td,mock.patch.object(fm,'DATA',Path(td)),mock.patch.object(fm,'effective_windows',return_value=[0]),mock.patch.object(fm,'get_candles',return_value=[[60,9,12,10,11,1]]):
                path=fm.minute_path('SOL')
                def interrupted(frame,handle,**kwargs):
                    handle.write('timestamp,open,high,low,close,volume\n60,10')
                    raise failure()
                with mock.patch.object(pd.DataFrame,'to_csv',interrupted):
                    with self.assertRaises(failure): fm.fetch_minutes('SOL',1,verbose=False)
                self.assertEqual(path.read_bytes(),b'')
                self.assertNotIn(0,fm.load_progress('SOL'))
                fm.fetch_minutes('SOL',1,verbose=False)
                self.assertEqual(list(fm.load_minutes('SOL').timestamp),[60])
                self.assertIn(0,fm.load_progress('SOL'))

    def test_legacy_binary_probe_is_not_reused_as_a_proven_boundary(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td,mock.patch.object(fm,'DATA',Path(td)):
            path=fm.progress_path('SOL');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(dict(listing_start=1000,probe_floor=0,windows_done=[])))
            self.assertIsNone(fm.load_probe('SOL'))

    def test_genuine_missing_minutes_are_preserved_but_duplicates_are_refused(self):
        rows=[[60,9,12,10,11,1],[180,9,12,10,11,1]]
        self.assertEqual(list(fm._window_frame(rows).timestamp),[60,180])
        with self.assertRaises(fm.FetchError): fm._window_frame(rows+rows[:1])

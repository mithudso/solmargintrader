"""Source-bound maintenance counterexamples; fixtures never contact a provider."""
from __future__ import annotations
import json
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import mock
import numpy as np
from soltui import analyze, coin_fit, config, jupiter_tokens, liquidity, live_run, paper, roster, runner, utxo_scan, wallet_activity
from backtester.core.engine import EngineConfig


def bars(ts):
    return {'ts': np.array(ts, dtype='int64'), **{k: np.full(len(ts), 100.) for k in ('open','high','low','close','volume')}}


class BackendEvidenceTests(unittest.TestCase):
    def test_roster_malformed_entry_does_not_hide_valid_successor(self):
        # CDO-1ecc18c32d
        result = roster.Roster.from_list([{'name':'rsi','params':[1]}, None, {'name':[], 'params':{}}, {'name':'buy_and_hold'}])
        self.assertEqual(result.labels, ['buy_and_hold'])

    def test_liquidity_totals_require_every_position(self):
        # CDO-2f82768c8f
        for missing in (None, float('nan'), float('inf')):
            result = liquidity.summarise({'positions':[{'deposited_usd':100, 'pnl_usd':10}, {'deposited_usd':100, 'pnl_usd':missing}]})
            self.assertIsNone(result.total_pnl_usd)
            self.assertIsNone(result.net_pct)
        self.assertIsNone(liquidity.summarise({'positions':[{'pnl_usd':1e308}, {'pnl_usd':1e308}]}).total_pnl_usd)

    def test_token_resolution_checks_duplicates_beyond_display_limit(self):
        # CDO-95f98cea7c
        payload = [{'id':'1'*32, 'symbol':'SOL', 'name':'fixture', 'decimals':9, 'isVerified':True}]
        payload += [{'id':'2'*32, 'symbol':'OTHER', 'name':'fixture', 'decimals':9, 'isVerified':True} for _ in range(49)]
        payload += [{'id':'3'*32, 'symbol':'SOL', 'name':'fixture', 'decimals':9, 'isVerified':True}]
        with mock.patch.object(jupiter_tokens, 'get', return_value=payload):
            self.assertEqual(len(jupiter_tokens.search('SOL')), 50)
            with self.assertRaisesRegex(ValueError, 'ambiguous'):
                jupiter_tokens.resolve('SOL')

    def test_paper_return_includes_first_bar_cost(self):
        # CDO-c8fa2eb0ce
        arrays = bars([0,60])
        result = SimpleNamespace(equity=np.array([99.,99.]), timestamps=arrays['ts'], trades=[], exposure=np.zeros(2), metrics=SimpleNamespace(total_return=-.01))
        with mock.patch.object(paper, 'run_backtest', return_value=result):
            session = paper.start_session(object(), arrays, EngineConfig(initial_capital=100))
        session.seek_end()
        self.assertEqual(session.starting_equity, 100.)
        self.assertAlmostEqual(session.pnl, result.metrics.total_return)

    def test_off_cadence_dryrun_refuses_before_engine(self):
        # CDO-d05a4c0c88
        settings = config.Settings(interval='1d')
        with mock.patch.object(runner, 'load_arrays', return_value=bars([0,86400,129600,216000,302400])), mock.patch.object(paper, 'start_session') as start:
            with self.assertRaisesRegex(ValueError, 'cadence'):
                live_run.run_dryrun('buy_and_hold', settings)
        start.assert_not_called()

    def test_immediate_fill_replay_matches_real_engine_return(self):
        strategy=SimpleNamespace(name='fixture',params={},warmup_bars=lambda:0,on_bar=lambda _:1.)
        session=paper.start_session(strategy,bars([0,60]),EngineConfig(initial_capital=100,interval='1m',fill_delay=0))
        session.seek_end()
        self.assertLess(session.result.metrics.total_return,0)
        self.assertAlmostEqual(session.pnl,session.result.metrics.total_return)

    def test_report_cannot_overwrite_candle_source_or_hardlink(self):
        # CDO-bcba5e367b8
        with TemporaryDirectory() as tmp:
            root=Path(tmp); source=root/'RANGE_1h.csv'; source.write_text('retained input')
            alias=root/'report.md'; alias.hardlink_to(source)
            with mock.patch.object(coin_fit, 'rank_coins', return_value={'errors':[]}), mock.patch.object(coin_fit, 'render_report', return_value='report'):
                for output in (source, alias):
                    with self.subTest(output=output.name), self.assertRaises(SystemExit) as error:
                        coin_fit.cli_main(['--coin','RANGE','--data-dir',tmp,'--days','7','--output',str(output)])
                    self.assertEqual(error.exception.code, 2)
                    self.assertEqual(source.read_text(), 'retained input')

    def test_analysis_discloses_gaps_in_selected_history(self):
        # CDO-e9fc5d872e
        with TemporaryDirectory() as tmp:
            Path(tmp,'SOL_1h.csv').write_text('timestamp,open,high,low,close,volume\n0,100,100,100,100,1\n3600,100,100,100,100,1\n10800,100,100,100,100,1\n')
            result=analyze.analyse('SOL','1h',data_dir=Path(tmp), keys=[])
        self.assertEqual(result.missing_bars, 1)
        self.assertEqual(result.gap_count, 1)
        self.assertIn('missing', result.headline.lower())

    def test_explorer_numeric_fields_are_integral_and_finite(self):
        # CDO-f3740aefe0
        for value in (float('inf'),float('nan'),1.5):
            with self.subTest(value=value), self.assertRaises(utxo_scan.WalletHttpError):
                utxo_scan._int(value)

    def test_explorer_error_does_not_echo_derived_address(self):
        # CDO-a4ae28934a
        address='synthetic-derived-address'
        backend=utxo_scan.BlockCypherBackend(lambda _: {'error':'lookup failed for '+address})
        with self.assertRaises(utxo_scan.WalletHttpError) as error:
            backend.stats([address])
        self.assertNotIn(address, str(error.exception))

    def test_overflow_timestamp_is_unknown(self):
        # CDO-669c894ec1
        self.assertIsNone(wallet_activity._timestamp(10**400))

    def test_sweep_start_is_serialized_until_worker_is_started(self):
        # CDO-247a254384
        entered, release, second = threading.Event(), threading.Event(), threading.Event()
        workers=[]; outcomes=[]
        class Worker:
            def __init__(self, **_): self.alive=False; workers.append(self)
            def start(self):
                if len(workers)==1:
                    entered.set(); self.waited=release.wait(2)
                self.alive=True
            def is_alive(self): return self.alive
        sweep=runner.SweepRunner(SimpleNamespace())
        registered=roster.Roster(); registered.add('buy_and_hold')
        def call(signal=None):
            if signal: signal.set()
            try: sweep.start(registered,config.Settings()); outcomes.append('started')
            except RuntimeError: outcomes.append('refused')
        first=threading.Thread(target=call); other=threading.Thread(target=call,args=(second,))
        with mock.patch.object(runner.threading, 'Thread', Worker):
            try:
                first.start(); self.assertTrue(entered.wait(1)); other.start(); self.assertTrue(second.wait(1)); other.join(.1)
            finally:
                release.set(); first.join(2); other.join(2)
        self.assertFalse(first.is_alive()); self.assertFalse(other.is_alive())
        self.assertEqual(len(workers),1)
        self.assertCountEqual(outcomes,['started','refused'])

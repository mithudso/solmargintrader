"""Inert control/reconciliation seams retain identity and unresolved outcomes."""
import concurrent.futures
import json
import sys
import importlib.util
import os
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock
import numpy as np
from soltui import commands, compound, compound_agent, current_signal, forwardtest, jupiter_manual, coinbase_account, coinbase_manual
from soltui.tests.bridge_support import World
from soltui.tests import test_compound as compound_fixtures


class ControlEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(World())

    def test_requested_manual_signal_keeps_its_explicit_member_parameters(self):
        now = 6000
        ts = np.arange(0, now, 60)
        bars = {'ts': ts, **{key: np.ones(len(ts)) for key in ('open', 'high', 'low', 'close')}, 'volume': np.zeros(len(ts))}
        requested = [('rsi', {'period': 7})]
        with mock.patch.object(forwardtest, 'saved_default', return_value=[('macd', {})]), mock.patch.object(forwardtest, '_predict', return_value=1) as predict:
            current_signal.check('SOL', [{'label': 'requested', 'members': requested}], fetch=lambda *args, **kw: bars, clock=lambda: now)
        self.assertEqual(predict.call_args.args[0], requested)

    def test_structurally_damaged_jupiter_records_remain_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(jupiter_manual, '_storage_dir', return_value=Path(tmp)):
            for data in ({}, {'state': []}, {'state': 'mystery'}):
                (Path(tmp) / ('a' * 32 + '.json')).write_text(json.dumps(data))
                self.assertTrue(jupiter_manual._has_unresolved())

    def test_processed_transaction_error_does_not_clear_unresolved_gate(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(jupiter_manual, '_storage_dir', return_value=Path(tmp)):
            identity = 'a' * 32
            (Path(tmp) / (identity + '.json')).write_text(json.dumps({'preview_id': identity, 'state': 'pending', 'signature': 'synthetic-signature'}))
            client = SimpleNamespace(rpc=lambda *args: {'result': {'value': [{'err': {'InstructionError': [0, 'Custom']}, 'confirmationStatus': 'processed'}]}})
            result = jupiter_manual.order_reconcile(identity, http_client=client)
            self.assertTrue(result['unresolved'])
            self.assertNotEqual(result['state'], 'failed')

    def test_each_forward_call_uses_its_own_recorded_costs(self):
        calls = [{'type': 'call', 'id': str(i), 'bar_ts': 60 * i, 'call': 'UP', 'price': 100, 'round_trip_bps': cost, 'notional_usd': 10000, 'scores': {}} for i, cost in enumerate((2, 8), 1)]
        ledger = calls + [{'type': 'resolve', 'id': row['id'], 'ret_bps': 20} for row in calls]
        with mock.patch.object(compound, 'read_ledger', return_value=ledger):
            result = compound.forward_status('SOL')
        self.assertEqual(result['compound']['net_bps_per_call_if_one_bar'], 15)
        self.assertEqual(result['paper']['costs_usd'], 10)
        self.assertEqual(result['paper']['net_usd'], 30)

    def test_adoption_failure_preserves_mapping_notes(self):
        venue = compound_fixtures.Venue(now=compound_fixtures.T0 + 300 * 20 + 10)
        with mock.patch.object(compound, 'auto_adopt', side_effect=compound.CompoundError('synthetic refusal')):
            result = compound.forward_tick('SOL', now=venue.now, get=venue.get, post=venue.post)
        self.assertIsInstance(result['notes'], dict)
        self.assertIn('adoption_error', result['notes'])

    def test_agent_unload_failure_preserves_the_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.plist'
            path.write_text('synthetic registration')
            with mock.patch.object(compound_agent, 'plist_path', return_value=path), mock.patch.object(compound_agent, '_launchctl', return_value=SimpleNamespace(returncode=5, stderr='synthetic refusal')):
                result = compound_agent.uninstall()
            self.assertTrue(path.exists())
            self.assertFalse(result['removed'])

    def test_balance_rows_cannot_replace_validated_portfolio_identity(self):
        def call(args):
            if args[:2] == ['portfolios','list']:
                return {'portfolios':[{'uuid':'fixture','name':'Validated'}]}
            if args[:2] == ['portfolios','get']:
                return {'portfolio':{'uuid':'fixture'}}
            return {'portfolio_id':'fixture','has_next':False,'accounts':[{'currency':'USD','portfolio_id':'forged','portfolio_name':'Forged'}]}
        result=coinbase_account.sync_account(call)
        self.assertEqual(result['accounts'][0]['portfolio_id'],'fixture')
        self.assertEqual(result['accounts'][0]['portfolio_name'],'Validated')

    def test_immediate_terminal_lookup_cannot_change_client_identity(self):
        from . import test_coinbase_manual as fixtures
        venue=fixtures.Venue()
        def call(args):
            result=venue(args)
            if args[:2] == ['orders','get']:
                result['client_order_id']='conflicting-fixture'
            return result
        preview=coinbase_manual.preview('SOL-USDC','BUY','2','quote',call)
        result=coinbase_manual.submit(preview['preview_id'],call)
        self.assertEqual(result['status'],'PENDING')
        self.assertTrue(coinbase_manual.state()['unresolved'])
        self.assertEqual(sum(args[:2]==['orders','create'] for args in venue.calls),1)

    def test_search_module_is_not_returned_half_initialized(self):
        entered, release, attempted = threading.Event(), threading.Event(), threading.Event()
        module=SimpleNamespace(ready=False); results=[]
        def initialize(_):
            entered.set()
            if not release.wait(2): raise TimeoutError('fixture barrier')
            module.ready=True
        def call(signal=None):
            if signal: signal.set()
            results.append(commands._repo_search().ready)
        first=threading.Thread(target=call); second=threading.Thread(target=call,args=(attempted,))
        spec=SimpleNamespace(loader=SimpleNamespace(exec_module=initialize))
        with mock.patch.dict(sys.modules), mock.patch.object(importlib.util,'spec_from_file_location',return_value=spec), mock.patch.object(importlib.util,'module_from_spec',return_value=module):
            sys.modules.pop('repo_index_search',None)
            try:
                first.start(); self.assertTrue(entered.wait(1)); second.start(); self.assertTrue(attempted.wait(1)); second.join(.1)
            finally:
                release.set(); first.join(2); second.join(2)
        self.assertFalse(first.is_alive()); self.assertFalse(second.is_alive())
        self.assertEqual(results,[True,True])

    def test_parallel_materialization_publishes_complete_unique_staging_files(self):
        import pandas as pd
        frame=pd.DataFrame({key:[1.,2.] for key in ('timestamp','open','high','low','close','volume','minutes')})
        barrier=threading.Barrier(2); real_save=np.savez
        def save(*args,**kwargs):
            barrier.wait(2)
            return real_save(*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'bars.npz'
            with mock.patch.object(compound,'bars_cache_path',return_value=path), mock.patch.object(compound,'_data_signature',return_value=[]), mock.patch.object(compound.cbt,'load_bars_5m',return_value=(frame,'fixture')), mock.patch.object(np,'savez',side_effect=save):
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results=list(pool.map(compound.materialize_bars,['SOL','SOL']))
            self.assertEqual(len(results),2)
            with np.load(path,allow_pickle=False) as saved:
                np.testing.assert_array_equal(saved['close'],[1.,2.])
            self.assertEqual(list(Path(tmp).glob('*.tmp-*')),[])

    def test_agent_registration_preserves_venv_symlink_and_cli_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); target=root/'python-real'; target.touch(); link=root/'python'; link.symlink_to(target)
            registration=root/'fixture.plist'
            with mock.patch.object(compound_agent,'plist_path',return_value=registration), mock.patch.object(compound_agent,'log_path',return_value=root/'log'), mock.patch.object(compound_agent,'is_worktree',return_value=False):
                compound_agent.install(link,root,start=False)
            import plistlib
            document=plistlib.loads(registration.read_bytes())
            self.assertEqual(document['ProgramArguments'][0],str(link.absolute()))
            self.assertTrue(os.path.isabs(document['WorkingDirectory']))
        with mock.patch.object(compound_agent,'install',return_value={'bootstrap':5}), redirect_stdout(io.StringIO()):
            self.assertEqual(compound_agent.main(['install']),1)

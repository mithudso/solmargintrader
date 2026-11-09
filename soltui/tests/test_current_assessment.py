from __future__ import annotations
import unittest
from unittest import mock
import numpy as np
from soltui import current_signal, live_price
from soltui.commands import Context, dispatch
from soltui.config import Settings


class CurrentAssessment(unittest.TestCase):
    def bars(self):
        ts = np.arange(600) * 60
        return {'ts': ts, **{k: np.full(600, v) for k, v in [('open',100.),('high',101.),('low',99.),('close',100.),('volume',1.)]}}

    def test_current_check_has_no_history_gate_and_excludes_open_candle(self):
        trial = {'label': 'hold', 'members': [{'name': 'buy_and_hold', 'params': {}}], 'mode': 'all'}
        with mock.patch.object(current_signal.forwardtest, 'load_defaults', return_value={}), \
             mock.patch.object(current_signal.forwardtest, '_predict', return_value=1) as predict:
            result = current_signal.check('SOL', [trial], fetch=lambda *a, **k:self.bars(), clock=lambda:35970)
        self.assertEqual(result['score'],100)
        self.assertEqual(result['candle_closed_at'],35940)
        self.assertTrue(np.all(predict.call_args.args[2]['ts'] + 60 <= 35970))

    def test_old_candle_cannot_be_returned_as_a_current_assessment(self):
        with self.assertRaisesRegex(ValueError,'Latest closed minute'):
            current_signal.check('SOL', [], fetch=lambda *a, **k:self.bars(), clock=lambda:40000)

    def test_batch_start_all_does_not_duplicate_running_batch(self):
        ctx=Context.from_settings(Settings())
        with mock.patch('soltui.f5_batch.list_runs',return_value=[{'run_id':'abc','running':True}]), \
             mock.patch('soltui.f5_batch.create') as create:
            env=dispatch('batch.run_all',{},ctx=ctx,quiet=True)
        self.assertTrue(env['ok']); create.assert_not_called()

    def test_batch_start_all_creates_and_starts_all_default_dimensions(self):
        ctx=Context.from_settings(Settings())
        with mock.patch('soltui.f5_batch.list_runs',return_value=[]), \
             mock.patch('soltui.f5_batch.catalog_coins'), \
             mock.patch('soltui.f5_batch.create',return_value={'run_id':'abc'}) as create, \
             mock.patch('soltui.f5_batch.start',return_value={'running':True}) as start:
            env=dispatch('batch.run_all',{},ctx=ctx,quiet=True)
        self.assertTrue(env['ok']); create.assert_called_once_with(ctx.settings,longest_contiguous=True); start.assert_called_once_with('abc')

    def test_jupiter_price_uses_exact_mint_and_does_not_claim_market_timestamp(self):
        result=live_price.jupiter('SOL',get=lambda path,params:{live_price.SOL_MINT:{'usdPrice':86.5,'blockId':123}},clock=lambda:99)
        self.assertEqual(result['price'],86.5); self.assertEqual(result['source'],'jupiter')
        self.assertIsNone(result['source_timestamp']); self.assertEqual(result['fetched_at'],99)

    def test_jupiter_missing_price_and_ambiguous_symbols_refuse(self):
        for price in (None,0,float('nan'),True):
            with self.subTest(price=price),self.assertRaises(ValueError):
                live_price.jupiter('SOL',get=lambda *a:{live_price.SOL_MINT:{'usdPrice':price}})
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            live_price.jupiter('BTC',get=lambda *a:[])

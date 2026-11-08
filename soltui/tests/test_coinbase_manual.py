"""Manual orders use exact reviewed contracts and fail closed on ambiguity."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from soltui import coinbase_manual as cm, commands, config


class Venue:
    def __init__(self):
        self.calls = []
        self.create_error = False
        self.order_status = 'FILLED'
        self.price = '89.4'
        self.fee = '0.01'

    def __call__(self, args):
        self.calls.append(args)
        if args[:2] == ['portfolios','list']:
            return {'portfolios':[{'uuid':'portfolio','type':'DEFAULT','name':'Default'}]}
        if args[:2] == ['portfolios','get']:
            return {'portfolio':{'uuid':'portfolio'}}
        if args[0] == 'balance':
            return {'portfolio_id':'portfolio','has_next':False,'accounts':[
                {'currency':'USDC','available_balance':{'value':'1000'}},
                {'currency':'SOL','available_balance':{'value':'10'}}]}
        if args[:2] == ['products','get']:
            return {'product_id':'SOL-USDC','product_type':'SPOT','status':'online',
                    'base_currency_id':'SOL','quote_currency_id':'USDC',
                    'base_min_size':'0.00000001','base_max_size':'1000','base_increment':'0.00000001',
                    'quote_min_size':'1','quote_max_size':'100000','quote_increment':'0.01'}
        if args[:2] == ['orders','preview']:
            return {'est_average_filled_price':self.price,'commission_total':self.fee,
                    'quote_size':'1.99','base_size':'0.022','order_total':'2'}
        if args[:2] == ['orders','create']:
            if self.create_error:
                raise TimeoutError('ambiguous')
            return {'order_id':'order-1'}
        if args[:2] == ['orders','get']:
            side = next((x.split('=',1)[1] for c in self.calls if c[:2] == ['orders','create']
                         for x in c if x.startswith('side=')), 'BUY')
            return {'order_id':'order-1','product_id':'SOL-USDC','side':side,
                    'status':self.order_status,'filled_size':'0.022', 'private_field':'never show'}
        raise AssertionError(args)


class ManualOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(config, 'CONFIG_DIR', Path(self.tmp.name)); p.start(); self.addCleanup(p.stop)
        self.venue = Venue()

    def preview(self):
        return cm.preview('SOL-USDC','BUY','2.00','quote',self.venue)

    def test_preview_never_places_order_and_submit_is_single_use(self):
        p = self.preview()
        self.assertFalse(any(c[:2] == ['orders','create'] for c in self.venue.calls))
        result = cm.submit(p['preview_id'],self.venue)
        self.assertEqual((result['order_id'],result['status']),('order-1','FILLED'))
        self.assertNotIn('private_field',result['order'])
        creates = [c for c in self.venue.calls if c[:2] == ['orders','create']]
        self.assertEqual(len(creates),1)
        self.assertTrue(any(x.startswith('client_order_id=') for x in creates[0]))
        with self.assertRaisesRegex(ValueError,'already been used'):
            cm.submit(p['preview_id'],self.venue)
        self.assertEqual(len([c for c in self.venue.calls if c[:2] == ['orders','create']]),1)

    def test_timeout_blocks_retries_and_new_orders(self):
        p = self.preview(); self.venue.create_error = True
        with self.assertRaisesRegex(RuntimeError,'outcome is unknown'):
            cm.submit(p['preview_id'],self.venue)
        with self.assertRaisesRegex(ValueError,'already been used'):
            cm.submit(p['preview_id'],self.venue)
        with self.assertRaisesRegex(ValueError,'unresolved'):
            self.preview()
        self.assertTrue(cm.state()['unresolved'])
        self.assertTrue(cm.status('order-1',self.venue)['unresolved'])
        self.assertEqual(len([c for c in self.venue.calls if c[:2] == ['orders','create']]),1)

    def test_sell_uses_exact_base_quantity(self):
        p = cm.preview('SOL-USDC','SELL','0.012','base',self.venue)
        self.assertEqual(cm.submit(p['preview_id'],self.venue)['status'],'FILLED')
        create = next(c for c in self.venue.calls if c[:2] == ['orders','create'])
        self.assertIn('base_size=0.012',create)
        self.assertFalse(any(x.startswith('quote_size=') for x in create))

    def test_expired_or_changed_price_never_submits(self):
        p = self.preview()
        with mock.patch.object(cm.time,'time',return_value=p['expires_at']+1):
            with self.assertRaisesRegex(ValueError,'expired'):
                cm.submit(p['preview_id'],self.venue)
        p = self.preview(); self.venue.price = '100'
        with self.assertRaisesRegex(ValueError,'price changed'):
            cm.submit(p['preview_id'],self.venue)
        self.assertFalse(any(c[:2] == ['orders','create'] for c in self.venue.calls))

    def test_increments_modes_and_cap_fail_closed(self):
        for side,size,unit in [('BUY','2.001','quote'),('BUY','NaN','quote'),('BUY','101','quote'),
                               ('SELL','2','quote'),('BUY','2','base')]:
            with self.subTest(side=side,size=size,unit=unit):
                with self.assertRaises(ValueError): cm.preview('SOL-USDC',side,size,unit,self.venue)
        self.assertFalse(any(c[:2] == ['orders','create'] for c in self.venue.calls))

    def test_increased_fee_requires_new_review(self):
        p = self.preview(); self.venue.fee = '0.03'
        with self.assertRaisesRegex(ValueError,'fee increased'):
            cm.submit(p['preview_id'],self.venue)
        self.assertFalse(any(c[:2] == ['orders','create'] for c in self.venue.calls))

    def test_pending_order_blocks_new_preview_until_terminal_lookup(self):
        self.venue.order_status='OPEN'; p=self.preview(); result=cm.submit(p['preview_id'],self.venue)
        self.assertEqual(result['status'],'OPEN')
        with self.assertRaisesRegex(ValueError,'unresolved'): self.preview()
        self.venue.order_status='FILLED'; self.assertEqual(cm.status('order-1',self.venue)['status'],'FILLED')
        self.assertFalse(cm.state()['unresolved'])
        self.assertTrue(self.preview()['preview_id'])

    def test_registry_requires_explicit_confirmation(self):
        with mock.patch.object(cm,'submit') as submit:
            r=commands.dispatch('coinbase.order_submit',{'preview_id':'a'*32},quiet=True)
            self.assertFalse(r['ok']); submit.assert_not_called()
            self.assertTrue(commands.COMMANDS['coinbase.order_submit'].requires_confirm)

    def test_quick_order_requires_opt_in_and_preserves_single_submission_checks(self):
        params = {'product_id':'SOL-USDC', 'side':'BUY', 'size':'2.00', 'size_currency':'quote'}
        with mock.patch.object(cm.cb, '_cli', self.venue):
            result = commands.dispatch('coinbase.order_quick', params | {'skip_confirm':False}, quiet=True)
            self.assertFalse(result['ok'])
            self.assertFalse(self.venue.calls)
            result = commands.dispatch('coinbase.order_quick', params | {'skip_confirm':True}, quiet=True)
            self.assertTrue(result['ok'], result)
            self.assertEqual(len([c for c in self.venue.calls if c[:2] == ['orders','preview']]), 2)
            self.assertEqual(len([c for c in self.venue.calls if c[:2] == ['orders','create']]), 1)

    def test_quick_order_timeout_blocks_following_orders(self):
        params = {'product_id':'SOL-USDC', 'side':'BUY', 'size':'2.00', 'size_currency':'quote', 'skip_confirm':True}
        self.venue.create_error = True
        with mock.patch.object(cm.cb, '_cli', self.venue):
            self.assertFalse(commands.dispatch('coinbase.order_quick', params, quiet=True)['ok'])
            self.assertFalse(commands.dispatch('coinbase.order_quick', params, quiet=True)['ok'])
        self.assertEqual(len([c for c in self.venue.calls if c[:2] == ['orders','create']]), 1)


if __name__ == '__main__': unittest.main()

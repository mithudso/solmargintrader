"""Coinbase snapshots preserve existing data and expose incomplete catalog scopes."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlparse

from soltui.tests.test_tui import offline_console_reads
from soltui import coinbase_account as cb, config


class CoinbaseAccountTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(config, 'CONFIG_DIR', Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)

    def test_incomplete_catalog_is_separate_and_discloses_scope(self):
        cb._store(cb.markets_path(), {'complete': True, 'products': [{'product_id': 'old'}]})
        def fetch(url):
            args = parse_qs(urlparse(url).query)
            kind = args['product_type'][0]
            return {'products': [{'product_id': kind}], 'pagination': {
                'has_next': kind == 'EQUITY', 'next_cursor': 'stalled'}}
        r = cb.download_markets(fetch, lambda: {'result': [{'instrument_name': 'x'}]})
        self.assertFalse(r['complete'])
        self.assertFalse(r['scopes']['EQUITY']['complete'])
        self.assertEqual(r['scopes']['EQUITY']['count'], 1)
        self.assertEqual(cb.markets()['products'][0]['product_id'], 'old')
        self.assertTrue(Path(r['path']).exists())

    def test_spot_pairs_publish_only_after_all_pages(self):
        def fetch(url):
            query=parse_qs(urlparse(url).query)
            if 'cursor' not in query:
                return {'products':[{'product_id':'SOL-USDC','product_type':'SPOT'}],
                        'pagination':{'has_next':True,'next_cursor':'next'}}
            return {'products':[{'product_id':'BTC-USD','product_type':'SPOT'},{'product_id':'SOL-USDC','product_type':'SPOT'}],
                    'pagination':{'has_next':False}}
        result=cb.download_spot_pairs(fetch)
        self.assertTrue(result['complete']); self.assertEqual(result['count'],2)
        self.assertEqual(cb.spot_pairs('sol')['pairs'],['SOL-USDC'])
        self.assertEqual(cb.spot_pairs()['count'],2)

    def test_spot_pagination_failure_preserves_last_complete_catalog(self):
        cb._store(cb.spot_pairs_path(),{'complete':True,'count':1,'products':[{'product_id':'OLD-USD'}]})
        def fetch(url):
            return {'products':[{'product_id':'SOL-USDC','product_type':'SPOT'}],
                    'pagination':{'has_next':True,'next_cursor':'stalled'}}
        with self.assertRaisesRegex(ValueError,'pagination stalled'):
            cb.download_spot_pairs(fetch)
        self.assertEqual(cb.spot_pairs()['pairs'],['OLD-USD'])

    def test_balance_pages_are_validated_before_replacing_snapshot(self):
        cb._store(cb.storage_dir() / 'account.json', {'accounts': [{'currency': 'OLD'}]})
        def call(args):
            if args[0] == 'portfolios':
                return {'portfolios': [{'uuid': 'one'}]} if args[1] == 'list' else {'portfolio': {'uuid': 'one'}}
            return {'portfolio_id': 'wrong', 'accounts': [], 'has_next': False}
        with self.assertRaises(ValueError):
            cb.sync_account(call)
        self.assertEqual(cb.last_account()['accounts'][0]['currency'], 'OLD')

    def test_balance_pages_are_merged(self):
        def call(args):
            if args[0] == 'portfolios':
                return {'portfolios': [{'uuid': 'one', 'name': 'Default'}]} if args[1] == 'list' else {'portfolio': {'uuid': 'one'}}
            second = any(x.startswith('cursor==') for x in args)
            return {'portfolio_id': 'one', 'accounts': [{'currency': 'SOL' if second else 'USD'}],
                    'has_next': not second, 'cursor': 'next'}
        result = cb.sync_account(call)
        self.assertEqual([r['currency'] for r in result['accounts']], ['USD', 'SOL'])

    def test_cli_terminal_page_may_omit_false_pagination_fields(self):
        def call(args):
            if args[0] == 'portfolios':
                return {'portfolios': [{'uuid': 'one'}]} if args[1] == 'list' else {'portfolio': {'uuid': 'one'}}
            if not any(x.startswith('cursor==') for x in args):
                return {'portfolio_id': 'one', 'accounts': [{'currency': 'USD'}], 'has_next': True, 'cursor': 'next'}
            return {'portfolio_id': 'one', 'accounts': [{'currency': 'SOL'}], 'size': 1}
        result = cb.sync_account(call)
        self.assertEqual([r['currency'] for r in result['accounts']], ['USD', 'SOL'])

    def test_omitted_pagination_does_not_hide_incomplete_page(self):
        cb._store(cb.storage_dir() / 'account.json', {'accounts': [{'currency': 'OLD'}]})
        def call(args):
            if args[0] == 'portfolios':
                return {'portfolios': [{'uuid': 'one'}]} if args[1] == 'list' else {'portfolio': {'uuid': 'one'}}
            return {'portfolio_id': 'one', 'accounts': [{'currency': 'SOL'}], 'size': 2}
        with self.assertRaisesRegex(ValueError, 'incomplete balance page'):
            cb.sync_account(call)
        self.assertEqual(cb.last_account()['accounts'][0]['currency'], 'OLD')

    def test_snapshot_writers_are_not_registered_as_read_only(self):
        from soltui import commands
        self.assertTrue(commands.COMMANDS['coinbase.account'].read_only)
        self.assertFalse(commands.COMMANDS['coinbase.sync'].read_only)
        self.assertFalse(commands.COMMANDS['coinbase.markets'].read_only)


class CoinbasePaneTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(offline_console_reads())

    async def test_wallet_displays_trading_and_staked_positions_separately(self):
        from textual.widgets import DataTable, TabbedContent
        from soltui.tests.test_tui import TEST_SIZE, make_settings
        from soltui.tui import SolTuiApp
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, 'CONFIG_DIR', Path(tmp)):
            cb._store(cb.storage_dir() / 'account.json', {
                'accounts': [{'portfolio_name': 'Default', 'currency': 'SOL',
                              'available_balance': {'value': '1'}, 'hold': {'value': '0'}}],
                'breakdowns': [{'portfolio': {'name': 'Default'}, 'spot_positions': [
                    {'asset': 'SOL', 'account_type': 'ACCOUNT_TYPE_STAKED_FUNDS',
                     'total_balance_crypto': 2, 'total_balance_fiat': 180}]}]})
            app = SolTuiApp(make_settings())
            async with app.run_test(size=TEST_SIZE) as pilot:
                app.query_one('#main-tabs', TabbedContent).active = 'tab-wallet'
                await pilot.pause()
                self.assertEqual(app.query_one('#coinbase-holdings', DataTable).row_count, 1)
                self.assertEqual(app.query_one('#coinbase-positions', DataTable).row_count, 1)


if __name__ == '__main__':
    unittest.main()

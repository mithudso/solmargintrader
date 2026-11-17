"""Synthetic edge cases preserve unavailable measurements and token identity."""
import concurrent.futures
from datetime import date
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

from soltui import cumulative, eth_scan, pnl, portfolio, pricefeed, top5, wallet


class FinancialEvidenceTests(unittest.TestCase):
    def test_nonfinite_csv_measurements_are_unavailable(self):
        for value in ('inf', '-inf', 'nan', None):
            with self.subTest(value=value):
                self.assertIsNone(cumulative._as_float(value))
                self.assertIsNone(cumulative._as_int(value))
                self.assertIsNone(top5._f({'value': value}, 'value'))
                self.assertIsNone(top5._i({'value': value}, 'value'))

    def test_nonresult_files_do_not_inflate_evidence_and_read_errors_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.csv'
            path.write_text('label,total_trades,n_paths\nnot-a-result,50,20\n')
            self.assertEqual(cumulative.load_result_file(path).rows, [])
            with mock.patch.object(Path, 'open', side_effect=PermissionError('synthetic')):
                with self.assertRaises(ValueError):
                    cumulative.load_result_file(path)

    def test_truncated_and_conflicting_recommendations_are_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'top.csv'
            header = 'asset,rank,label,horizon,median_sharpe,total_trades,n_paths\n'
            for body in ('SOL,1,rsi,medium,1\n', 'SOL,1,rsi,medium,1,50,10\nDOGE,1,macd,long,2,60,10\n'):
                path.write_text(header + body)
                with self.subTest(body=body), self.assertRaises(top5.EvidenceUnavailable):
                    top5.load_top5(path)

    def test_equity_preserves_observation_order_at_equal_timestamps(self):
        curve = pnl.Curve('paper', 'fixture', 'SOL', 100, [(1, 100), (1, 90)])
        self.assertEqual(curve.points[-1], (1, 90))

    def test_percentage_and_dollar_drawdown_have_independent_maxima(self):
        days = [pnl.Day(date(2026, 1, i), equity, 0, 0, None) for i, equity in enumerate((50, 1000, 700), 1)]
        report = pnl.drawdown_report(100, days)
        self.assertAlmostEqual(report['max_drawdown_pct'], -0.5)
        self.assertEqual(report['max_drawdown_usd'], -300)

    def test_lp_missing_measurements_do_not_become_zero_profit(self):
        position = dict(pnl_usd=1, deposited_usd=10, gas_usd=0.1, rewards_usd=0.2)
        for field in position:
            bad = {**position, field: None}
            with self.subTest(field=field), self.assertRaises(ValueError):
                pnl.curve_from_lp_status({'generated_at': 100, 'mode': 'dry-run', 'positions': [bad]})

    def test_ticker_without_exchange_timestamp_is_not_fresh_evidence(self):
        state = {}
        self.assertFalse(pricefeed.apply_ticker(state, {'type': 'ticker', 'product_id': 'SOL-USD', 'best_bid': '10', 'best_ask': '11'}, 100))
        self.assertEqual(state, {})

    def test_nonfinite_book_sizes_cannot_become_executable_quotes(self):
        book = pricefeed.Book()
        with self.assertRaises(ValueError):
            book.load([['10', 'inf']], [['11', '1']], 100)
        self.assertIsNone(book.top())

    def test_invalidated_book_removes_the_previous_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = pricefeed.Recorder(['SOL-USD'], root=Path(tmp))
            recorder.last_received_at = 100
            recorder.state['SOL-USD'] = [10, 11, 10.5, 1, 1, 100]
            recorder.books['SOL-USD'] = pricefeed.Book()
            recorder.refresh_from_books(101)
            self.assertNotIn('SOL-USD', recorder.state)

    def test_fragmented_message_has_one_cumulative_memory_bound(self):
        ws = pricefeed.WebSocket('ws://fixture.invalid')
        ws.sock = mock.Mock()
        ws._buf = bytearray(b'\x01\x14' + b'a' * 20 + b'\x80\x14' + b'b' * 20)
        with mock.patch.object(pricefeed, 'MAX_FRAME_BYTES', 32), self.assertRaises(pricefeed.PriceFeedError):
            ws.recv_text()

    def test_unvalued_position_nfts_make_wallet_total_incomplete(self):
        scan = wallet.ChainScan('base', 'synthetic-public-owner')
        scan.positions = [{'symbol': 'LP', 'kind': 'position-nft', 'value_usd': None}]
        self.assertFalse(scan.to_dict()['total_complete'])

    def test_missing_solana_balance_and_malformed_account_envelopes_are_partial(self):
        for accounts in ([], {'value': [3]}, {'value': []},
                         {'value': [{'account': {'data': {'parsed': {'info': {'mint': [], 'tokenAmount': []}}}}}]}):
            def fetch(url, body=None):
                if body:
                    method = body['method']
                    value = None if method == 'getBalance' else accounts if method == 'getTokenAccountsByOwner' else []
                    return {'result': value}
                return {}
            with self.subTest(accounts=accounts):
                result = wallet.scan_solana('synthetic-public-owner', fetch).to_dict()
                self.assertIsNone(result['native'])
                self.assertFalse(result['total_complete'])

    def test_failed_eth_token_measurements_make_totals_incomplete(self):
        answers = ['0x0'] * len(eth_scan.TOKENS)
        answers[0] = None
        with mock.patch.object(eth_scan, '_rpc', return_value='0x0'), mock.patch.object(eth_scan, '_batch', return_value=answers), mock.patch.object(eth_scan, 'spot_prices', return_value=({}, [])):
            result = eth_scan.scan_ethereum('0x' + '11' * 20, mock.Mock()).to_dict()
        self.assertFalse(result['total_complete'])

    def test_distinct_same_symbol_tokens_preserve_separate_balance_changes(self):
        def snapshot(ts, amounts):
            holdings = [{'symbol': 'SAME', 'address': f'0x{i:040x}', 'amount': value, 'price_usd': 1, 'included': True, 'kind': 'erc20'} for i, value in enumerate(amounts, 1)]
            chain = dict(status='ok', total_usd=3, total_complete=True, native=None, holdings=holdings, stakes=[], positions=[])
            return portfolio.build_snapshot(dict(ts=ts, scanned_at=str(ts), partial=False, total_usd=3, chains={'base': chain}))
        before, after = snapshot(1, [1, 2]), snapshot(2, [2, 1])
        self.assertEqual(len(portfolio.diff_snapshots(before, after)['changes']), 2)
        self.assertNotIn('0x000000', json.dumps(before))

    def test_invalid_history_rows_do_not_reach_report_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'history.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in ({'ts': float('inf'), 'chains': {}}, {'ts': 1, 'chains': {'base': []}}, {'ts': 2, 'chains': {'base': {'status': 'ok'}}})))
            self.assertEqual(portfolio.load_snapshots(path), [])

    def test_concurrent_scan_publications_use_distinct_temporary_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'last.json'
            barrier = threading.Barrier(2)
            replace = portfolio.os.replace
            def publish(source, destination):
                barrier.wait(3)
                return replace(source, destination)
            with mock.patch.object(portfolio, 'last_scan_path', return_value=target), mock.patch.object(portfolio.os, 'replace', side_effect=publish), concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(portfolio.save_last_scan, {'fixture': i}, 'base') for i in range(2)]
                for future in futures:
                    self.assertEqual(future.result(timeout=5), target)
            self.assertIn(json.loads(target.read_text())['result']['fixture'], (0, 1))

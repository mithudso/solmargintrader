import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from oracle_leverage import signals


def packet(now=100000, seq=1, publisher='one', asset='BTC', scores=None):
    if scores is None:
        scores = {'up': .8, 'down': .1, 'flat': .1}
    m = max(scores.values())
    winners = [k.upper() for k, v in scores.items() if v == m]
    direction = winners[0] if len(winners) == 1 else 'FLAT'
    metric = {'brier': 0, 'hits': 0}
    h = {'scores': scores, 'direction': direction, 'samples': 0, 'issued': 0,
         'resolved': 0, 'expired': 0, 'capacityDrops': 0, 'pending': 0,
         'candidate': metric, 'uniform': metric, 'frequency': metric}
    source = signals.SOURCES[asset]
    return {'schema_version': 1, 'publisher_id': publisher, 'sequence': seq, 'asset': asset,
            'quote': {'price': 100, 'exchangeMs': now, 'receivedMs': now},
            'snapshot': {'key': json.dumps([1, signals.MODEL, signals.TARGET, asset, source], separators=(',', ':')),
                         'market': asset, 'source': source, 'model': signals.MODEL, 'target': signals.TARGET,
                         'asOfMs': now, 'status': 'learning', 'horizons': {k: dict(h) for k in signals.HORIZONS}}}


class RelayTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name) / 'private'
        self.env = patch.dict(os.environ, {'ORACLE_AUTOTRADE_HOME': str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def publish(self, t, seq, **kw):
        return signals.publish(packet(t, seq, **kw), t)

    def test_absent_read_does_not_create_owner(self):
        self.assertFalse(signals.status(100000)['available'])
        self.assertFalse(self.home.exists())
        self.publish(100000, 1)
        self.assertFalse((self.home / 'journal.sqlite3').exists())
        self.assertFalse((self.home / 'owner.sock').exists())

    def test_open_sustain_flip_and_stale_virtual_end(self):
        for i in range(16):
            result = self.publish(100000 + 1000 * i, i + 1)
        w = result['asset']['horizons']['60']['window']
        self.assertTrue(w['sustained'])
        self.assertEqual(w['duration_ms'], 15000)
        result = self.publish(116000, 17, scores={'up': .05, 'down': .9, 'flat': .05})
        h = result['asset']['horizons']['60']
        self.assertEqual(h['history'][-1]['reason'], 'side_flip')
        self.assertEqual(h['window']['direction'], 'DOWN')
        before = (self.home / 'signals.sqlite3').read_bytes()
        h = signals.status(118001)['assets']['BTC']['horizons']['60']
        self.assertIsNone(h['window'])
        self.assertEqual(h['history'][-1]['reason'], 'stale')
        self.assertEqual(before, (self.home / 'signals.sqlite3').read_bytes())
        result = self.publish(119000, 18)
        self.assertEqual(len(result['asset']['horizons']['60']['history']), 2)

    def test_lease_idempotence_and_assets(self):
        p = packet()
        self.assertFalse(signals.publish(p, 100000)['duplicate'])
        self.assertTrue(signals.publish(p, 102500)['duplicate'])
        with self.assertRaisesRegex(ValueError, 'publisher_busy'):
            self.publish(102500, 1, publisher='two')
        with self.assertRaisesRegex(ValueError, 'sequence_conflict'):
            self.publish(101000, 1)
        self.publish(101000, 1, asset='ZEC')
        self.publish(104000, 1, publisher='two')
        self.assertEqual(set(signals.status(104000)['assets']), {'BTC', 'ZEC'})

    def test_validation_and_private_files(self):
        p = packet()
        p['snapshot']['weights'] = []
        with self.assertRaises(ValueError): signals.publish(p, 100000)
        self.publish(100000, 1)
        os.chmod(self.home / 'signals.sqlite3', 0o644)
        with self.assertRaises(ValueError): signals.status(100000)

    def test_warming_ties_and_timestamp_validation(self):
        p = packet()
        p['snapshot']['status'] = 'warming'
        for h in p['snapshot']['horizons'].values():
            h['scores'] = None
            h['direction'] = 'FLAT'
        self.assertIsNone(signals.publish(p, 100000)['asset']['horizons']['60']['window'])
        p = packet(101000, 2, scores={'up': .45, 'down': .45, 'flat': .1})
        self.assertEqual(signals.publish(p, 101000)['asset']['horizons']['60']['direction'], 'FLAT')
        p = packet(102000, 3)
        p['quote']['exchangeMs'] += 251
        with self.assertRaisesRegex(ValueError, 'quote_not_fresh'):
            signals.publish(p, 102000)

    def test_reject_hardlink_and_symlink(self):
        self.publish(100000, 1)
        db = self.home / 'signals.sqlite3'
        alias = self.home / 'alias'
        os.link(db, alias)
        with self.assertRaisesRegex(ValueError, 'signal_file_not_private'):
            signals.status(100000)
        alias.unlink()
        db.unlink()
        db.symlink_to('/dev/null')
        with self.assertRaisesRegex(ValueError, 'signal_file_not_private'):
            signals.status(100000)

    def test_exchange_time_must_advance_even_if_receipt_advances(self):
        original = packet()
        signals.publish(original, 100000)
        self.assertTrue(signals.publish(original, 100500)['duplicate'])
        for exchange in (100000, 99999):
            p = packet(100500, 2)
            p['quote']['exchangeMs'] = exchange
            with self.assertRaisesRegex(ValueError, 'quote_out_of_order'):
                signals.publish(p, 100500)
        self.assertTrue(signals.publish(packet(100500, 2), 100500)['accepted'])

    def test_invalidation_fences_delayed_publish_and_keeps_history(self):
        self.publish(100000, 1)
        late = packet(100500, 2)
        event = {'asset': 'BTC', 'publisher_id': 'one', 'sequence': 3, 'reason': 'feed_unavailable'}
        result = signals.invalidate(event, 100600)
        row = result['asset']['horizons']['60']
        self.assertFalse(result['asset']['fresh'])
        self.assertIsNone(row['window'])
        self.assertEqual(row['history'][-1]['reason'], 'feed_unavailable')
        self.assertEqual(row['history'][-1]['end_ms'], 100600)
        self.assertTrue(signals.invalidate(event, 100700)['duplicate'])
        with self.assertRaisesRegex(ValueError, 'sequence_conflict'):
            signals.publish(late, 100700)
        conflicting = {**event, 'reason': 'stale'}
        with self.assertRaisesRegex(ValueError, 'sequence_conflict'):
            signals.invalidate(conflicting, 100700)
        self.assertEqual(len(signals.status(100700)['assets']['BTC']['horizons']['60']['history']), 1)
        resumed = signals.publish(packet(100800, 4), 100800)
        self.assertTrue(resumed['asset']['fresh'])
        self.assertEqual(len(resumed['asset']['horizons']['60']['history']), 1)

    def test_invalidation_before_first_publish_and_other_publisher(self):
        event = {'asset': 'BTC', 'publisher_id': 'one', 'sequence': 2, 'reason': 'page_closed'}
        self.assertTrue(signals.invalidate(event, 100500)['accepted'])
        self.assertEqual(signals.status(100500)['assets'], {})
        self.assertTrue(signals.invalidate(event, 100600)['duplicate'])
        with self.assertRaisesRegex(ValueError, 'sequence_conflict'):
            signals.publish(packet(100000, 1), 100600)
        self.assertTrue(signals.publish(packet(100700, 1, publisher='two'), 100700)['accepted'])
        self.assertFalse(signals.invalidate({**event, 'sequence': 3}, 100800)['accepted'])
        self.assertIsNotNone(signals.status(100800)['assets']['BTC']['horizons']['60']['window'])
        with self.assertRaisesRegex(ValueError, 'publisher_busy'):
            signals.publish(packet(100800, 1), 100800)

    def test_invalidation_validation_and_stale_deduplication(self):
        self.publish(100000, 1)
        event = {'asset': 'BTC', 'publisher_id': 'one', 'sequence': 2, 'reason': 'stale'}
        with self.assertRaisesRegex(ValueError, 'invalid_invalidation'):
            signals.invalidate({**event, 'reason': 'secret'}, 102100)
        result = signals.invalidate(event, 102100)
        history = result['asset']['horizons']['60']['history']
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['end_ms'], 102000)
        self.assertEqual(history[0]['reason'], 'stale')
        self.assertEqual(len(signals.invalidate(event, 102200)['asset']['horizons']['60']['history']), 1)

    def test_history_bound(self):
        for i in range(55):
            scores = {'up': .9, 'down': .05, 'flat': .05} if i % 2 == 0 else {'up': .05, 'down': .9, 'flat': .05}
            result = self.publish(100000 + i * 1000, i + 1, scores=scores)
        self.assertEqual(len(result['asset']['horizons']['60']['history']), 24)


if __name__ == '__main__': unittest.main()

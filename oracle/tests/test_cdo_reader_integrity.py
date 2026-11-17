from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from oracle.engine import OracleEngine
from oracle.reader import ReadOnlyOracle
from oracle.store import canonical


class ReaderIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'archive.sqlite3'
        self.writer = OracleEngine(self.path, instrument='SOL/USD', minimum_resolved=1)

    def test_replaced_archive_is_rejected_before_exposing_other_instrument(self):
        reader = ReadOnlyOracle(self.path, instrument='SOL/USD')
        replacement = Path(self.temp.name) / 'replacement.sqlite3'
        OracleEngine(replacement, instrument='BTC/USD', minimum_resolved=1)
        os.replace(replacement, self.path)
        with self.assertRaisesRegex(ValueError, 'oracle_archive_changed'):
            reader.status()

    def test_early_resolution_is_rejected_before_it_can_vote(self):
        reader = ReadOnlyOracle(self.path, instrument='SOL/USD')
        card = self.writer.strategies()[0]
        with self.writer.store.connection() as db:
            db.execute('INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?)',
                       ('prior', card['strategy_id'], card['version'], 900, 960, 1, 100, canonical({'direction': 1, 'issued_at': 900, 'expires_at': 960})))
            db.execute('INSERT INTO resolutions VALUES(?,?,?,?,?)', ('prior', 1, 1, 901, '{}'))
        with self.assertRaisesRegex(ValueError, 'oracle_resolution_before_target'):
            reader.predictions(930)

    def test_in_place_policy_change_is_rejected(self):
        reader = ReadOnlyOracle(self.path, instrument='SOL/USD')
        with self.writer.store.connection() as db:
            db.execute("UPDATE metadata SET body='{}' WHERE key='policy'")
        with self.assertRaisesRegex(ValueError, 'oracle_archive_changed'):
            reader.status()


if __name__ == '__main__':
    unittest.main()

"""Crash and conflict recovery for forward-test saved defaults."""
import json
import os
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from soltui import config
from soltui import forwardtest as ft


class ForwardOutboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.enterContext(patch.object(config, 'CONFIG_DIR', Path(self.tmp.name)))
        self.dbpath = Path(self.tmp.name) / 'batch-a' / 'forward.sqlite3'
        self.key = 'SOL|fixture|1'
        self.desired = {'members': [{'name': 'one', 'params': {}}], 'saved_at': 1}

    def stage(self, *, commit):
        with ft._defaults_lock(), closing(ft._db(self.dbpath)) as db:
            db.execute('BEGIN IMMEDIATE')
            ft._stage_default(db, self.key, {}, self.desired)
            db.commit() if commit else db.rollback()

    def recover(self):
        with ft._defaults_lock():
            ft._recover_defaults_locked()

    def test_rollback_never_changes_defaults_and_removes_orphan_marker(self):
        self.stage(commit=False)
        self.assertFalse(ft.defaults_path().exists())
        self.recover()
        self.assertFalse(ft.defaults_path().exists())
        self.assertEqual(list((ft.defaults_path().parent / 'defaults-pending').iterdir()), [])

    def test_committed_intent_replays_after_file_write_before_ack(self):
        self.stage(commit=True)
        write = ft._write_durable
        def interrupted(path, value):
            write(path, value)
            if path == ft.defaults_path():
                raise OSError('simulated power interruption')
        with (patch.object(ft, '_write_durable', side_effect=interrupted),
              self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable')):
            self.recover()
        self.assertEqual(ft.load_defaults()[self.key], self.desired)
        self.recover()
        self.recover()
        self.assertEqual(ft.load_defaults()[self.key], self.desired)
        with closing(ft._db(self.dbpath)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_outbox').fetchone()[0], 0)

    def test_changed_key_blocks_recovery_without_overwriting_newer_value(self):
        self.stage(commit=True)
        other = {'members': [{'name': 'newer', 'params': {}}]}
        ft.defaults_path().write_text(json.dumps({self.key: other}))
        with self.assertRaisesRegex(RuntimeError, 'forward_default_conflict'):
            self.recover()
        self.assertEqual(ft.load_defaults()[self.key], other)
        with closing(ft._db(self.dbpath)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_outbox').fetchone()[0], 1)

    def test_missing_database_blocks_other_batch_before_default_write(self):
        self.stage(commit=True)
        self.dbpath.unlink()
        with self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable'):
            self.recover()
        self.assertFalse(ft.defaults_path().exists())
        with (patch.object(ft, 'admit_read') as admit,
              self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable')):
            ft.tick('SOL', [], (1,), 16, db_path=Path(self.tmp.name) / 'batch-b.sqlite3',
                    fetch=lambda *args, **kwargs: self.fail('must not fetch'), code='fixture')
        admit.assert_not_called()

    def test_replaced_database_cannot_hide_committed_intent(self):
        self.stage(commit=True)
        original = self.dbpath.with_name('committed-original.sqlite3')
        self.dbpath.rename(original)
        with closing(ft._db(self.dbpath)):
            pass
        with self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable'):
            self.recover()
        self.assertFalse(ft.defaults_path().exists())
        self.assertEqual(len(list((ft.defaults_path().parent / 'defaults-pending').iterdir())), 1)
        with closing(ft._db(original)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_outbox').fetchone()[0], 1)

    def test_changed_database_generation_blocks_recovery(self):
        self.stage(commit=True)
        with closing(ft._db(self.dbpath)) as db, db:
            db.execute("UPDATE default_outbox_identity SET generation='new-generation' WHERE id=1")
        with self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable'):
            self.recover()
        self.assertFalse(ft.defaults_path().exists())
        self.assertEqual(len(list((ft.defaults_path().parent / 'defaults-pending').iterdir())), 1)

    def test_abandoned_owned_marker_temp_is_quarantined_and_committed_intent_replays(self):
        self.stage(commit=True)
        pending = ft.defaults_path().parent / 'defaults-pending'
        fd, name = tempfile.mkstemp(prefix='.pending-', dir=pending)
        with os.fdopen(fd, 'w') as stream:
            stream.write('partial marker')
        self.recover()
        self.assertEqual(ft.load_defaults()[self.key], self.desired)
        quarantine = pending / 'quarantine'
        saved = list(quarantine.iterdir())
        self.assertEqual(len(saved), 1)
        self.assertTrue(saved[0].name.startswith(Path(name).name + '-'))
        self.assertEqual(saved[0].read_text(), 'partial marker')
        self.recover()

    def test_unverified_temporary_or_malformed_final_marker_stays_blocked(self):
        pending = ft.defaults_path().parent / 'defaults-pending'
        pending.mkdir(parents=True)
        target = Path(self.tmp.name) / 'other-file'
        target.write_text('do not move')
        suspect = pending / '.pending-aaaaaaaa'
        suspect.symlink_to(target)
        with self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable'):
            self.recover()
        self.assertTrue(suspect.is_symlink())
        suspect.unlink()
        malformed = pending / ('0000000000000000-' + 'a' * 32 + '.json')
        malformed.write_text('{')
        with self.assertRaisesRegex(RuntimeError, 'forward_default_recovery_unavailable'):
            self.recover()
        self.assertEqual(malformed.read_text(), '{')

    def test_pending_intents_for_same_key_replay_in_transaction_order(self):
        later = {'members': [{'name': 'two', 'params': {}}], 'saved_at': 2}
        with ft._defaults_lock(), closing(ft._db(self.dbpath)) as db:
            db.execute('BEGIN IMMEDIATE')
            expected = {}
            ft._stage_default(db, self.key, expected, self.desired)
            ft._stage_default(db, self.key, expected, later)
            db.commit()
        self.recover()
        self.assertEqual(ft.load_defaults()[self.key], later)

    def test_tick_rollback_after_adoption_never_writes_default(self):
        from soltui.tests.test_forwardtest import BASE, candles

        trial = {'label': 'fixture', 'mode': 'all',
                 'members': [ft.member('buy_and_hold', {})]}
        def interrupted(*args, **kwargs):
            on_adopt = args[10]
            on_adopt(self.desired['members'], trial['members'], 0.99, 100)
            raise RuntimeError('fixture stop after adoption')

        with (patch.object(ft, '_resolve', side_effect=interrupted), patch.object(ft, 'admit_read'),
              self.assertRaisesRegex(RuntimeError, 'fixture stop after adoption')):
            ft.tick('SOL', [trial], (1,), 16, db_path=self.dbpath,
                    fetch=lambda *args, **kwargs: candles(0),
                    clock=lambda: BASE + 4, code='fixture')
        self.assertFalse(ft.defaults_path().exists())
        self.recover()
        self.assertFalse(ft.defaults_path().exists())
        with closing(ft._db(self.dbpath)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM default_outbox').fetchone()[0], 0)

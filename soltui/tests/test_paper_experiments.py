"""Prospective paper experiments stay isolated, causal and fee-aware."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from soltui import config, forwardtest, paper_experiments as pe


class PaperExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.object(config, 'CONFIG_DIR', Path(self.tmp.name))
        patch.start()
        self.addCleanup(patch.stop)

    def test_start_validates_and_persists_unique_forecast_contract(self):
        with mock.patch.object(forwardtest, 'revision', return_value='revision'), \
             mock.patch.object(pe.subprocess, 'Popen') as launch:
            launch.return_value.pid = 2345
            r = pe.start('rsi', 'SOL', 5, 1000, 13)
        plan = pe._read(pe._path(r['id'], 'json'))
        self.assertEqual((plan['asset'], plan['minutes'], plan['capital'], plan['cost_bps']), ('SOL', 5, 1000, 13))
        self.assertEqual(plan['label'], 'paper-experiment:' + r['id'])
        self.assertEqual(plan['spec']['name'], 'rsi')
        self.assertIn('soltui.paper_experiments', launch.call_args.args[0])
        with self.assertRaises(ValueError):
            pe.start('missing', 'SOL', 5, 1000, 13)
        with self.assertRaises(ValueError):
            pe.start('rsi', 'SOL', 5, float('nan'), 13)
        from soltui import commands
        from soltui.tests.test_tui import make_settings
        ctx = commands.Context.from_settings(make_settings())
        with mock.patch.object(pe, 'start', return_value={'id': 'ok'}) as called:
            env = commands.dispatch('paper_experiment.start',
                                    {'strategy': 'rsi', 'asset': 'SOL', 'minutes': 5,
                                     'capital': 1000.0, 'params': {}}, ctx=ctx, quiet=True)
        self.assertTrue(env['ok'], env)
        self.assertEqual(called.call_args.args[:4], ('rsi', 'SOL', 5, 1000.0))

    def test_status_reports_only_its_own_settled_calls_and_paper_equity(self):
        eid = 'a' * 24
        plan = {'id': eid, 'asset': 'SOL', 'strategy': 'rsi', 'minutes': 5, 'capital': 1000,
                'cost_bps': 10, 'label': 'paper-experiment:' + eid, 'created_at': 1,
                'phase': 'stopped', 'message': 'Stopped'}
        pe._write(pe._path(eid, 'json'), plan)
        with forwardtest._db() as db:
            for key, label in [('mine', plan['label']), ('other', 'another-run')]:
                db.execute('INSERT INTO trial(id,asset,label,mode,minutes,cost,active) VALUES (?,?,?,?,?,?,?)',
                           (key, 'SOL', label, 'all', 5, 10, '[]'))
            db.execute('INSERT INTO call(trial,bar,issued,start,finish,generation,guesses,prediction,outcome,bps) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       ('mine', 100, 110, 120, 420, 0, '[]', 1, 1, 100.0))
            db.execute('INSERT INTO call(trial,bar,issued,start,finish,generation,guesses,prediction) VALUES (?,?,?,?,?,?,?,?)',
                       ('mine', 500, 510, 520, 820, 0, '[]', -1))
            db.execute('INSERT INTO call(trial,bar,issued,start,finish,generation,guesses,prediction,outcome,bps) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       ('other', 100, 110, 120, 420, 0, '[]', 1, 1, 1000.0))
        s = pe.status(eid)
        self.assertEqual(s['calls_recorded'], 2)
        self.assertEqual(s['trades'], 1)
        self.assertAlmostEqual(s['equity'], 1000 * (1 + __import__('math').expm1(.01) - .001))
        self.assertIsNone(s['calls'][1]['paper_pnl'])
        self.assertLess(s['calls'][0]['issued'], s['calls'][0]['start'])

    def test_resume_keeps_contract_and_rejects_changed_code(self):
        with mock.patch.object(pe, '_revision', return_value='v1'), mock.patch.object(pe.subprocess, 'Popen') as launch:
            launch.return_value.pid = 77
            eid = pe.start('rsi', 'SOL', 5, 1000, 13)['id']
            plan = pe._read(pe._path(eid, 'json'))
            plan['phase'] = 'stopped'
            pe._write(pe._path(eid, 'json'), plan)
            pe.resume(eid)
            resumed = pe._read(pe._path(eid, 'json'))
            self.assertEqual(resumed['label'], plan['label'])
            self.assertEqual(resumed['spec'], plan['spec'])
            resumed['phase'] = 'stopped'
            pe._write(pe._path(eid, 'json'), resumed)
        with mock.patch.object(pe, '_revision', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'code changed'):
                pe.resume(eid)

    def test_worker_records_then_stops_cooperatively(self):
        eid = 'c' * 24
        plan = {'id': eid, 'asset': 'SOL', 'strategy': 'rsi', 'minutes': 5, 'capital': 1000,
                'cost_bps': 13, 'spec': {'name': 'rsi', 'params': {}}, 'code': 'v1',
                'label': 'paper-experiment:' + eid, 'created_at': 1, 'phase': 'starting'}
        pe._write(pe._path(eid, 'json'), plan)
        def tick(*args, **kwargs):
            pe._path(eid, 'stop').touch()
            return {'message': 'Checked'}
        with mock.patch.object(pe, '_revision', return_value='v1'), \
             mock.patch.object(pe.time, 'time', return_value=125), \
             mock.patch.object(pe.time, 'sleep'), \
             mock.patch.object(pe.forwardtest, 'tick', side_effect=tick) as tick_mock:
            self.assertEqual(pe.run(eid), 0)
        self.assertEqual(tick_mock.call_args.kwargs['tune'], False)
        self.assertEqual(pe._read(pe._path(eid, 'json'))['phase'], 'stopped')
        self.assertFalse(pe._locked(eid))

    def test_rejects_untrusted_ids_and_signals_interruption(self):
        with self.assertRaises(ValueError):
            pe.status('../other')
        eid = 'b' * 24
        pe._write(pe._path(eid, 'json'), {'id': eid, 'asset': 'SOL', 'capital': 1000,
                                          'phase': 'running', 'label': 'x', 'created_at': 1})
        self.assertEqual(pe.status(eid)['phase'], 'interrupted')
        self.assertFalse(pe.stop(eid)['stopping'])


class ExperimentPaneTests(unittest.IsolatedAsyncioTestCase):
    async def test_tab_shows_strategy_selection_and_paper_run_controls(self):
        from textual.widgets import Button, Select, TabbedContent
        from soltui.tests.test_tui import TEST_SIZE, make_settings
        from soltui.tui import SolTuiApp
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(config, 'CONFIG_DIR', Path(tmp)):
            app = SolTuiApp(make_settings())
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                app.query_one('#main-tabs', TabbedContent).active = 'tab-paper-experiments'
                await pilot.pause()
                self.assertIsNotNone(app.query_one('#paper-exp-strategy', Select).value)
                self.assertEqual(str(app.query_one('#paper-exp-start', Button).label), 'Start experiment')
                self.assertTrue(app.query_one('#paper-exp-table'))

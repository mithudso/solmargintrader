"""Real mounted controls with isolated command transport; no detached producers."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Button, Checkbox, Input, TabbedContent
from soltui import council
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp


class PredictionControls(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patch = mock.patch('soltui.config.CONFIG_DIR', Path(temporary.name))
        patch.start(); self.addCleanup(patch.stop)

    async def drain(self, app, pilot, field):
        deadline = time.monotonic() + 5
        while getattr(app, field) and time.monotonic() < deadline:
            await pilot.pause(.01)
        self.assertFalse(getattr(app, field))

    async def test_expired_auto_recovery_is_single_and_pause_has_manual_start(self):
        app = SolTuiApp(settings=make_settings(), start='tab-compound', classic=False, auto_recover=True)
        original = app._call
        paused = False
        calls = []
        def call(name, params=None, **kw):
            if name in ('forwardtest.health', 'forwardtest.ensure'):
                calls.append((name, params))
                return {'ok': True, 'result': {'running': False, 'paused': paused,
                    'can_start': True, 'message': 'Paused' if paused else 'Stopped'}}
            return original(name, params, **kw)
        with mock.patch.object(app, '_call', side_effect=call), mock.patch('soltui.tui.time.time', return_value=1_800_000_000.):
            async with app.run_test(size=TEST_SIZE) as pilot:
                await self.drain(app, pilot, '_signal_recovery_busy')
                self.assertEqual(sum(n == 'forwardtest.ensure' for n, _ in calls), 1)
                app._signal_live_request_recovery(startup=True)
                await self.drain(app, pilot, '_signal_recovery_busy')
                self.assertEqual(sum(n == 'forwardtest.ensure' for n, _ in calls), 1)
                paused = True
                # CDO-db61e4dcb9: expire the independent cooldown so only the
                # explicit owner pause can prevent automatic recovery.
                app._signal_recovery_at.clear()
                before_pause = sum(n == 'forwardtest.ensure' for n, _ in calls)
                app._signal_live_request_recovery(startup=True)
                await self.drain(app, pilot, '_signal_recovery_busy')
                self.assertEqual(sum(n == 'forwardtest.ensure' for n, _ in calls), before_pause)
                app._signal_live_prediction_rows = []
                app._signal_live_update_score(time.time())
                self.assertTrue(app.query_one('#signal-live-predictions-start', Button).display)
                app._signal_live_start_predictions()
                await self.drain(app, pilot, '_signal_recovery_busy')
                ensures=[params for name,params in calls if name=='forwardtest.ensure']
                self.assertEqual(len(ensures),before_pause+1)
                self.assertEqual(ensures[-1],{'asset':'SOL','manual':True})
                app._signal_live_open_forward()
                self.assertEqual(app.query_one('#main-tabs', TabbedContent).active, 'tab-forwardtest')

    async def test_headless_default_never_starts_a_real_producer(self):
        app = SolTuiApp(settings=make_settings(), start='tab-compound')
        original = app._call
        calls = []
        def call(name, params=None, **kw):
            calls.append(name)
            if name == 'forwardtest.ensure':
                self.fail('Headless startup must not spawn a producer')
            return original(name, params, **kw)
        with mock.patch.object(app, '_call', side_effect=call):
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause(.05)
                self.assertNotIn('forwardtest.ensure', calls)

    async def test_council_settings_controls_and_poll_preserve_draft(self):
        app = SolTuiApp(settings=make_settings(), start='tab-bots', classic=True)
        state = {'mode': 'paper', 'running': False, 'config': council.config(), 'position': None,
                 'message': 'Waiting for confidence', 'equity': 10000, 'confidence': None,
                 'confidence_samples': 0, 'fills': []}
        calls = []
        original = app._call
        def call(name, params=None, **kw):
            if name.startswith('council.'):
                calls.append((name, params))
                return {'ok': True, 'result': state['config'] if name == 'council.config' else state}
            return original(name, params, **kw)
        with mock.patch.object(app, '_call', side_effect=call):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app._council_request()
                await self.drain(app, pilot, '_council_busy')
                app.query_one('#council-asset', Input).value = 'ETH'
                app.query_one('#council-shorts', Checkbox).value = True
                app.query_one('#council-leveraged', Checkbox).value = True
                app._council_request()
                await self.drain(app, pilot, '_council_busy')
                self.assertEqual(app.query_one('#council-asset', Input).value, 'ETH')
                app._council_action(Button.Pressed(app.query_one('#council-save', Button)))
                await self.drain(app, pilot, '_council_busy')
                config = next(p['config'] for n, p in calls if n == 'council.config')
                self.assertEqual(config['asset'], 'ETH')
                self.assertTrue(config['execution']['allow_short'])
                self.assertTrue(config['execution']['use_leverage'])
                state.update(running=True, position={'direction': -1, 'entry_price': 100})
                app._council_done({'ok': True, 'result': state})
                self.assertTrue(app.query_one('#council-save', Button).disabled)
                self.assertTrue(app.query_one('#council-start', Button).disabled)
                self.assertFalse(app.query_one('#council-stop', Button).disabled)
                self.assertIn('Short @ $100', text_of(app, '#council-status'))

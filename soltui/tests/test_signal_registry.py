import unittest

from soltui.commands import COMMANDS


class SignalRegistryTest(unittest.TestCase):
    def test_registry_contract(self):
        read = COMMANDS['oracle.signals.status']
        write = COMMANDS['oracle.signals.publish']
        invalidate = COMMANDS['oracle.signals.invalidate']
        self.assertTrue(read.read_only)
        self.assertFalse(write.read_only)
        self.assertFalse(write.requires_confirm)
        self.assertFalse(invalidate.read_only)
        self.assertFalse(invalidate.requires_confirm)
        self.assertEqual([(p.name, p.type, p.required) for p in invalidate.params], [('event', 'json', True)])
        self.assertEqual([(p.name, p.type, p.required) for p in write.params], [('packet', 'json', True)])


class SignalTuiTest(unittest.IsolatedAsyncioTestCase):
    async def test_relay_rows_and_worker_shutdown(self):
        import time

        from textual.widgets import Static

        from oracle_leverage.tests.test_signals import packet
        from research.zec_tui import OracleWinnersApp

        now = int(time.time() * 1000)
        p = packet(now, asset='ZEC', scores={'up': .05, 'down': .9, 'flat': .05})
        rows = {k: {**v, 'window': None, 'history': []} for k, v in p['snapshot']['horizons'].items()}
        state = {'fresh': True, 'expires_at_ms': now + 10000, 'as_of_ms': now,
                 'status': 'learning', 'source': p['snapshot']['source'], 'quote': p['quote'], 'horizons': rows}
        # Bypass market feeds; the shared signal loader is the only data used by this assertion.
        app = OracleWinnersApp(data_loader=lambda *_: {}, quote_loader=lambda *_: {},
                               alert_loader=lambda *_: {}, signal_loader=lambda *_: {'now_ms': now, 'assets': {'ZEC': state}})
        async with app.run_test(size=(160, 60)) as pilot:
            await pilot.pause(0.5)
            widget = app.query_one('#shared-signals', Static)
            text = widget.render()
            self.assertIn('Jupiter relay', text.plain)
            self.assertIn('↓ DOWN', text.plain)
            self.assertIn('90.0%', text.plain)
            self.assertEqual(len([s for s in app._signal_rendered[1] if "'red'" in s]), 6)
        self.assertFalse(app.signal_worker.alive)

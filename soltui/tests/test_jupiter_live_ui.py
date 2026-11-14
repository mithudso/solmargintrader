"""The optional Jupiter reader must never block or publish across UI contexts."""
from __future__ import annotations

import asyncio
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from textual.widgets import Select, Sparkline
from soltui.tests.test_tui import offline_console_reads
from soltui.tests.test_tui import TEST_SIZE, make_settings, text_of
from soltui.tui import SolTuiApp


class JupiterLiveUI(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.enterContext(offline_console_reads())
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        patch = mock.patch('soltui.config.CONFIG_DIR', Path(temporary.name))
        patch.start(); self.addCleanup(patch.stop)

    def app(self):
        settings = make_settings()
        settings.forwardtest_autostart = False
        return SolTuiApp(settings=settings, start='tab-compound', classic=False)

    async def drained(self, app, pilot):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            await pilot.pause(0.01)
            # Select.Changed is queued; initial idle is not a completed read.
            if (app._signal_live_jupiter_state != 'idle' and not app._jupiter_price_busy
                    and app._signal_live_jupiter_drained.is_set()):
                return
        self.fail('Jupiter reader did not drain')

    async def test_failure_recovers_and_price_histories_stay_separate(self):
        app = self.app()
        original = app._call
        attempts = []
        fail = {'value': True}
        def call(name, params=None, **kwargs):
            if name != 'prices.quote':
                return original(name, params, **kwargs)
            attempts.append(params)
            if fail['value']:
                raise RuntimeError('fixture failure')
            return {'ok': True, 'result': {'price': 88., 'fetched_at': time.time(), 'block_id': 12}}
        with mock.patch('soltui.live_score.prediction_snapshot', return_value={'rows': []}), \
             mock.patch.object(app, '_call', side_effect=call):
            async with app.run_test(size=TEST_SIZE) as pilot:
                app._signal_live_price_history['SOL'] = [(1., 100.)]
                app.query_one('#signal-live-price-source', Select).value = 'jupiter'
                await self.drained(app, pilot)
                self.assertEqual(app._signal_live_jupiter_state, 'failed')
                self.assertIn('RuntimeError', text_of(app, '#signal-live-stream'))
                fail['value'] = False
                app._signal_live_jupiter_at = 0
                app._signal_live_tick()
                await self.drained(app, pilot)
                self.assertEqual(app._signal_live_jupiter_state, 'completed')
                self.assertIn('Jupiter SOL/USD', text_of(app, '#signal-live-chart-context'))
                self.assertEqual(app._signal_live_price_history['SOL'], [(1., 100.)])
                jupiter_prices = [p for _, p in app._signal_live_price_history['jupiter:SOL']]
                self.assertTrue(jupiter_prices)
                self.assertEqual(set(jupiter_prices), {88.})
                self.assertEqual(list(app.query_one('#signal-live-chart', Sparkline).data), jupiter_prices)

    async def test_held_read_is_single_responsive_and_discards_coin_and_feed_switches(self):
        app = self.app()
        original = app._call
        started, release = threading.Event(), threading.Event()
        calls = []
        active = peak = 0
        def call(name, params=None, **kwargs):
            nonlocal active, peak
            if name != 'prices.quote':
                return original(name, params, **kwargs)
            calls.append(params['asset']); active += 1; peak = max(peak, active)
            try:
                if len(calls) == 1:
                    started.set()
                    if not release.wait(30):
                        raise RuntimeError('test did not release held quote')
                return {'ok': True, 'result': {'price': 11. if len(calls) == 1 else 22., 'fetched_at': time.time()}}
            finally:
                active -= 1
        with mock.patch('soltui.live_score.prediction_snapshot', return_value={'rows': []}), \
             mock.patch.object(app, '_call', side_effect=call):
            try:
                async with app.run_test(size=TEST_SIZE) as pilot:
                    source = app.query_one('#signal-live-price-source', Select)
                    source.value = 'jupiter'
                    self.assertTrue(await asyncio.to_thread(started.wait, 5))
                    # A queued UI message completes while the network reader is held.
                    responsive = asyncio.Event()
                    app.set_timer(0.01, responsive.set)
                    await asyncio.wait_for(responsive.wait(), 2)
                    for _ in range(3): app._signal_live_tick()
                    self.assertEqual(calls, ['SOL'])
                    source.value = 'coinbase'
                    await pilot.pause(0.05)
                    source.value = 'jupiter'
                    app._compound_coin = 'ETH'
                    app._signal_live_tick()
                    await pilot.pause(0.05)
                    release.set()
                    await self.drained(app, pilot)
                    self.assertEqual(peak, 1)
                    self.assertEqual(calls[0], 'SOL')
                    self.assertTrue(calls[1:])
                    self.assertEqual(set(calls[1:]), {'ETH'})
                    self.assertNotIn('jupiter:SOL', app._signal_live_price_history)
                    self.assertTrue(app._signal_live_price_history['jupiter:ETH'])
                    self.assertEqual({p for _, p in app._signal_live_price_history['jupiter:ETH']}, {22.})
                    self.assertIn('Jupiter ETH/USD', text_of(app, '#signal-live-chart-context'))
            finally:
                release.set()

    async def test_shutdown_drains_held_reader_without_publication(self):
        app = self.app()
        original = app._call
        started, release = threading.Event(), threading.Event()
        unmounting = threading.Event()
        release_after_unmount = threading.Event()
        shutdown_finished_before_release = threading.Event()
        original_unmount = app.on_unmount
        async def unmount(_app):
            unmounting.set()
            try:
                await original_unmount()
            finally:
                if not release.is_set():
                    shutdown_finished_before_release.set()
        def release_during_shutdown():
            # Observe the actual drain wait, not a timer-driven early release.
            if unmounting.wait(60) and waiting.wait(2):
                release_after_unmount.set()
            release.set()
        waiting = threading.Event()
        original_wait = None
        wait_patch = None
        def drain_wait(timeout=None):
            if unmounting.is_set(): waiting.set()
            return original_wait(timeout)
        def call(name, params=None, **kwargs):
            if name != 'prices.quote': return original(name, params, **kwargs)
            started.set()
            if not release.wait(120): raise RuntimeError('held fixture timed out')
            return {'ok': True, 'result': {'price': 88., 'fetched_at': time.time()}}
        with mock.patch('soltui.live_score.prediction_snapshot', return_value={'rows': []}), \
             mock.patch.object(app, '_call', side_effect=call), \
             mock.patch.object(type(app), 'on_unmount', new=unmount), \
             mock.patch.object(app, '_signal_live_jupiter_done', wraps=app._signal_live_jupiter_done) as publish:
            try:
                helper = None
                async with app.run_test(size=TEST_SIZE):
                    app.query_one('#signal-live-price-source', Select).value = 'jupiter'
                    self.assertTrue(await asyncio.to_thread(started.wait, 5))
                    self.assertTrue(app._jupiter_price_busy)
                    self.assertFalse(app._signal_live_jupiter_drained.is_set())
                    # Each read installs a new drain Event; observe that current
                    # event only after the fake reader has actually entered.
                    original_wait = app._signal_live_jupiter_drained.wait
                    wait_patch = mock.patch.object(app._signal_live_jupiter_drained, 'wait', side_effect=drain_wait)
                    wait_patch.start()
                    helper = threading.Thread(target=release_during_shutdown, daemon=True)
                    helper.start()
                # CDO-c890bc1a53: context exit itself must wait for held IO.
                helper.join(3)
                self.assertTrue(release_after_unmount.is_set())
                self.assertFalse(shutdown_finished_before_release.is_set())
                self.assertTrue(app._jupiter_price_shutdown_drained)
                publish.assert_not_called()
                self.assertFalse(app._jupiter_price_busy)
                self.assertTrue(app._signal_live_jupiter_drained.is_set())
            finally:
                release.set()
                unmounting.set()
                waiting.set()
                if helper is not None:
                    helper.join(3)
                if wait_patch is not None:
                    wait_patch.stop()

"""Editor ownership and progress routing for interactive backtests."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from soltui.backtest_log import BacktestLog
from soltui.commands import Context, Runtime, bots_backtest, compound_backtest
from soltui.tests.test_tui import make_settings, TEST_SIZE
from soltui.tui import SolTuiApp
from textual.widgets import TextArea


class EditorBacktestTests(unittest.IsolatedAsyncioTestCase):
    async def test_log_follows_new_bytes_and_does_not_steal_preview(self) -> None:
        app = SolTuiApp(make_settings())
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'worker.log'
            path.write_text('old run\n')
            async with app.run_test(size=TEST_SIZE) as pilot:
                await pilot.pause()
                app._start_log('Strategy backtest', 'starting', BacktestLog(path))
                with path.open('a') as f:
                    f.write('running rsi\n')
                app._poll_backtest_log()
                view = app.query_one('#docs-view', TextArea)
                self.assertIn('running rsi', view.text)
                self.assertNotIn('old run', view.text)
                app._show_preview('coin', 'SOL details')
                with path.open('a') as f:
                    f.write('finished\n')
                app._poll_backtest_log()
                self.assertEqual(view.text, 'SOL details')
                self.assertIn('finished', app._backtest_log_text)


class ProgressRoutingTests(unittest.TestCase):
    def test_commands_forward_engine_progress(self) -> None:
        ctx = Context.from_settings(make_settings(), Runtime())
        lines = []
        ctx.progress = lines.append
        def compound(*args, **kwargs):
            kwargs['progress']('1/2 SOL metric')
            return {}
        def bots(*args, **kwargs):
            kwargs['progress'](.5, 'BTC (1/2)')
            return {}
        with patch('soltui.commands.compound_mod.backtest', side_effect=compound):
            compound_backtest(ctx, {'asset': 'SOL'})
        with patch('soltui.bots.backtest_many', side_effect=bots):
            bots_backtest(ctx, {'bot': 'grid', 'coins': ['BTC']})
        self.assertEqual(lines, ['1/2 SOL metric', 'BTC (1/2)'])

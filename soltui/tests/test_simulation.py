"""Jupiter notional costs, confidence gates, and immutable prospective economics."""
from __future__ import annotations

import json
import sqlite3
import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np

from backtester.core.types import BarWindow, Mode
from soltui import config, forwardtest as ft, simulation as sim
from soltui.runner import engine_config
from soltui.tests.test_forwardtest import BASE, candles


class Signal:
    name = "constant"
    params = {}
    def __init__(self, target=1.0):
        self.target = target
    def warmup_bars(self):
        return 0
    def on_bar(self, history):
        return self.target


def history(closes, i):
    n = len(closes)
    return BarWindow(np.arange(n) * 60, np.full(n, 100.), np.maximum(closes, 100),
                     np.minimum(closes, 100), np.array(closes), np.ones(n), i)


class JupiterSimulation(unittest.TestCase):
    def test_settings_migrate_legacy_fees_and_preserve_explicit_scenarios(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"fee_bps": 80}))
            migrated = config.load_settings(path)
            self.assertEqual(migrated.fee_bps, 6)
            self.assertFalse(migrated.armed)
            path.write_text(json.dumps({"fee_schedule": "jupiter-perps", "fee_bps": 7}))
            self.assertEqual(config.load_settings(path).fee_bps, 7)
        for changes in ({"leverage": float("nan")}, {"leverage": 251}, {"min_confidence": 1.01},
                        {"min_confidence": float("inf")}, {"allow_short": 1}, {"use_leverage": "false"}):
            with self.subTest(changes=changes), self.assertRaises(config.ConfigError):
                config.validate(config.Settings(**changes))

    def test_shared_engine_uses_jupiter_fees_and_only_selected_leverage(self):
        settings = config.Settings(leverage=5, allow_short=True, fee_bps=7)
        cfg = engine_config(settings)
        self.assertIs(cfg.mode, Mode.PERP)
        self.assertEqual(cfg.leverage, 1)
        self.assertTrue(cfg.allow_short)
        self.assertEqual(cfg.costs.perp_base_fee_bps, 7)
        self.assertEqual(cfg.costs.utilization, 1)
        self.assertEqual(engine_config(replace(settings, use_leverage=True)).leverage, 5)

    def test_confidence_is_prior_success_not_exposure_and_blocks_065(self):
        execution = sim.Execution(min_confidence=.8)
        gate = sim.ConfidenceGate(Signal(), execution, "1m")
        closes = [102.] * 65 + [98.] * 35 + [102.]
        for i in range(len(closes)):
            target = gate.on_bar(history(closes, i))
        self.assertLess(gate.confidence, .66)
        self.assertGreater(gate.confidence, .63)
        self.assertEqual(target, 0)
        self.assertFalse(execution.permits(1, .65))
        self.assertTrue(execution.permits(1, .8))
        self.assertFalse(execution.permits(1, None))

    def test_confidence_does_not_see_future_bars_and_waits_for_fill_delay(self):
        def replay(closes, end):
            gate = sim.ConfidenceGate(Signal(), sim.Execution(), "1m", fill_delay=2)
            return [(gate.on_bar(history(closes, i)), gate.confidence) for i in range(end)]
        prefix = [102.] * 35
        self.assertEqual(replay(prefix + [500.] * 5, 35), replay(prefix + [1.] * 5, 35))
        self.assertEqual(replay(prefix, 35), replay(prefix + [500.], 35))
        values = replay(prefix, 25)
        self.assertTrue(all(score is None for _, score in values[:21]))
        self.assertGreater(values[-1][0], 0)

    def test_shorts_require_opt_in_and_flat_stays_flat(self):
        for short in (False, True):
            ex = sim.Execution(allow_short=short, min_confidence=0)
            gate = sim.ConfidenceGate(Signal(-1), ex, "1m")
            self.assertEqual(gate.on_bar(history([100.], 0)), -1 if short else 0)
            self.assertFalse(ex.permits(0, 1))

    def test_short_option_enables_only_an_explicit_bearish_branch(self):
        from backtester.core.strategies import build
        strategy = sim.gate(build("ma_crossover", fast=2, slow=3),
                            config.Settings(allow_short=True, min_confidence=0), "1m")
        self.assertEqual(strategy.on_bar(history([103., 102., 101.], 2)), -1)
        self.assertEqual(sim.ConfidenceGate(Signal(0), sim.Execution(allow_short=True,
                         min_confidence=0)).on_bar(history([100.], 0)), 0)

    def test_costs_scale_with_notional_and_charge_both_sides_and_borrow(self):
        ex = sim.Execution(use_leverage=True, leverage=5, slippage_bps=2)
        result = sim.settle(ex, 1, [(100, 100, 100, 100)] * 60)
        notional = 1 / (.2 + .0008)
        expected_fee = notional * .0012
        expected_slip = notional * .0004
        expected_borrow = notional * .8 / 10000
        self.assertAlmostEqual(result['net_return'], -expected_fee - expected_slip - expected_borrow)
        self.assertAlmostEqual(result['fees_bps'], expected_fee * 10000)
        self.assertAlmostEqual(result['borrow_bps'], expected_borrow * 10000)
        short = sim.settle(ex, -1, [(100, 100, 100, 100)] * 60)
        self.assertAlmostEqual(short['borrow_bps'], notional * .15)
        self.assertGreater(short['net_return'], result['net_return'])

    def test_down_short_profits_and_intraminute_liquidation_cannot_recover(self):
        ex = sim.Execution(use_leverage=True, leverage=5, allow_short=True)
        prices = [(100, 100, 98, 98)]
        self.assertGreater(sim.settle(ex, -1, prices)['net_return'], 0)
        self.assertLess(sim.settle(ex, 1, prices)['net_return'], 0)
        result = sim.settle(ex, 1, [(100, 110, 70, 110)])
        self.assertEqual((result['net_return'], result['liquidated']), (-1, 1))
        short = sim.settle(ex, -1, [(100, 130, 90, 90)])
        self.assertEqual((short['net_return'], short['liquidated']), (-1, 1))

    def test_forward_settlement_matches_historical_engine_for_each_side(self):
        from backtester.core.engine import run_backtest
        for direction in (-1, 1):
            for low, high, close in ((98., 103., 102.), (70., 130., 102.)):
                with self.subTest(direction=direction, low=low):
                    ex = sim.Execution(use_leverage=True, leverage=5, allow_short=True, min_confidence=0)
                    arrays = dict(ts=np.array([0, 60]), open=np.array([100., 100.]),
                                  high=np.array([100., high]), low=np.array([100., low]),
                                  close=np.array([100., close]), volume=np.ones(2))
                    result = run_backtest(Signal(direction), arrays, ex.engine(interval='1m'))
                    net = sim.settle(ex, direction, [(100., high, low, close)])
                    self.assertAlmostEqual(net['net_return'], result.equity[-1] / 10000 - 1)
                    self.assertEqual(net['liquidated'], result.liquidation_count)

    def test_forward_gate_persists_settings_and_skips_trade_until_prior_evidence(self):
        with TemporaryDirectory() as tmp, patch.object(config, 'CONFIG_DIR', Path(tmp)):
            trial = {"label": "hold", "mode": "all", "members": [ft.member("buy_and_hold", {})]}
            profile = sim.Execution(use_leverage=True, leverage=3).to_dict()
            def advance(minute, execution=profile):
                return ft.tick("SOL", [trial], (1,), 16., execution=execution,
                    fetch=lambda *a, **k: candles(minute),
                    clock=lambda: BASE + minute * 60 + 4, code="fixture", tune=False)
            for minute in range(26):
                result = advance(minute)
            row = result['rows'][0]
            self.assertGreater(row['paper_trades'], 0)
            self.assertGreater(row['net_pct'], 0)
            self.assertEqual(row['execution'], profile)
            self.assertGreater(row['cost_bps'], 16)
            with ft._db() as db:
                first = db.execute('SELECT confidence,traded,net_return FROM call ORDER BY bar LIMIT 1').fetchone()
                self.assertEqual(first, (None, 0, 0.))
                before = db.execute('SELECT bar,prediction,traded,net_return FROM call WHERE trial=? ORDER BY bar', (row['id'],)).fetchall()
            changed = advance(26, {**profile, 'leverage': 5, 'min_confidence': .9})
            self.assertEqual(len(changed['rows']), 2)
            with ft._db() as db:
                after = db.execute('SELECT bar,prediction,traded,net_return FROM call WHERE trial=? ORDER BY bar', (row['id'],)).fetchall()
            self.assertEqual([r for r in before if r[-1] is not None],
                             [r for r in after if r[0] <= before[-3][0]])

    def test_confidence_gate_fills_only_after_the_prior_samples_and_next_open(self):
        from backtester.core.engine import run_backtest
        from soltui.runner import engine_config
        prices = np.full(35, 102.)
        arrays = dict(ts=np.arange(35) * 60, open=np.full(35, 100.),
                      high=prices, low=np.full(35, 100.), close=prices, volume=np.ones(35))
        settings = config.Settings(interval="1m", min_confidence=.8)
        result = run_backtest(sim.gate(Signal(), settings), arrays, engine_config(settings))
        self.assertTrue(result.trades)
        self.assertGreaterEqual(result.trades[0].bar_index, 21)
        blocked = run_backtest(sim.gate(Signal(), replace(settings, min_confidence=1)), arrays,
                               engine_config(settings))
        self.assertEqual(blocked.trades, [])

    def test_legacy_database_migration_preserves_original_rows(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'legacy.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE trial(id TEXT PRIMARY KEY,asset TEXT,label TEXT,mode TEXT,minutes INTEGER,cost REAL,active TEXT,generation INTEGER DEFAULT 0,moved INTEGER DEFAULT 0,note TEXT DEFAULT '')")
                db.execute("CREATE TABLE call(trial TEXT,bar INTEGER,issued REAL,start INTEGER,finish INTEGER,generation INTEGER,guesses TEXT,prediction INTEGER,outcome INTEGER,bps REAL,expired INTEGER DEFAULT 0,PRIMARY KEY(trial,bar))")
                db.execute("INSERT INTO trial(id,asset,label,mode,minutes,cost,active) VALUES('old','SOL','old','all',1,160,'[]')")
                db.execute("INSERT INTO call(trial,bar,prediction,outcome,bps) VALUES('old',1,1,1,200)")
            with ft._db(path) as db:
                self.assertEqual(db.execute("SELECT cost,execution FROM trial").fetchone(), (160, ''))
                self.assertEqual(db.execute("SELECT bps,traded,net_return FROM call").fetchone(), (200., None, None))
            row = ft.status('SOL', db_path=path)[0]
            self.assertIsNone(row['net_pct'])


class SimulationControlLayout(unittest.IsolatedAsyncioTestCase):
    async def test_both_forms_keep_controls_visible_and_clickable_at_100_columns(self):
        from textual.app import App, ComposeResult
        from textual.containers import Vertical
        from textual.widgets import Checkbox, Input
        from soltui.tui import SolTuiApp

        class Form(App):
            CSS = SolTuiApp.CSS
            settings = config.Settings()
            def compose(self) -> ComposeResult:
                with Vertical():
                    yield from SolTuiApp._simulation_controls(self, 'forward')
                    yield from SolTuiApp._simulation_controls(self, 'backtest')

        app = Form()
        async with app.run_test(size=(100, 55)) as pilot:
            for prefix in ('forward', 'backtest'):
                for suffix in ('use-leverage', 'allow-short', 'leverage', 'min-confidence'):
                    widget = app.query_one(f'#{prefix}-{suffix}')
                    self.assertGreater(widget.region.width, 0)
                    self.assertLessEqual(widget.region.right, 100)
                await pilot.click(f'#{prefix}-use-leverage')
                await pilot.click(f'#{prefix}-allow-short')
                app.query_one(f'#{prefix}-leverage', Input).value = '5'
                values = SolTuiApp._simulation_form(app, prefix)
                self.assertEqual(values, dict(use_leverage=True, allow_short=True, leverage=5., min_confidence=.8))

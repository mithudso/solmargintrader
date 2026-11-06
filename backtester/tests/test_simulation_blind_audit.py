"""Independent held-out selection and raw-bar refusal regressions."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.gridsim import GridConfig, run_grid_backtest
from backtester.core.types import CostConfig, Mode
from research import sweep


class Always:
    name = 'blind-always'
    params = {}
    def warmup_bars(self): return 0
    def on_bar(self, history): return 1.


def arrays():
    return dict(ts=np.array([1_700_000_000, 1_700_086_400]),
                open=np.array([100., 100.]), high=np.array([100., 100.]),
                low=np.array([100., 100.]), close=np.array([100., 100.]), volume=np.ones(2))


def zero(**patch):
    return CostConfig(fee_bps=0, slippage_bps=0, perp_base_fee_bps=0,
                      max_hourly_rate_bps_long=patch.pop('max_hourly_rate_bps_long', 0),
                      max_hourly_rate_bps_short=0, **patch)


class RawMarketBoundary(unittest.TestCase):
    def test_nan_intrabar_extreme_cannot_disable_liquidation(self):
        for field in ('high', 'low'):
            a = arrays()
            a[field][-1] = np.nan
            with self.subTest(field=field), self.assertRaises(ValueError):
                run_backtest(Always(), a, EngineConfig(mode=Mode.PERP, leverage=10, fill_delay=0, costs=zero()))
        valid = arrays()
        valid['low'][-1] = 50
        result = run_backtest(Always(), valid, EngineConfig(mode=Mode.PERP, leverage=10, fill_delay=0, costs=zero()))
        self.assertEqual(result.liquidation_count, 1)

    def test_shape_numeric_ohlc_volume_and_timestamp_contract_is_checked_before_strategy(self):
        mutations = [
            ('open', [100.]), ('low', [[100., 100.]]), ('high', [100., np.inf]),
            ('close', [100., 0.]), ('volume', [1., -1.]), ('volume', [1., np.nan]),
            ('open', [100., 101.]), ('high', [100., 99.]), ('low', [100., 101.]),
            ('ts', [1_700_000_000, 1_700_000_000]), ('ts', [1_700_086_400, 1_700_000_000]),
            ('ts', [1_700_000_000, 1_700_086_400.5]), ('ts', [1_700_000_000_000, 1_700_000_086_400]),
        ]
        strategy = mock.Mock(wraps=Always())
        for field, values in mutations:
            a = arrays(); a[field] = np.asarray(values)
            with self.subTest(field=field, values=values), self.assertRaises(ValueError):
                run_backtest(strategy, a, EngineConfig())
        strategy.on_bar.assert_not_called()

    def test_gap_or_wrong_cadence_refuses_instead_of_undercharging_time_costs(self):
        cfg = EngineConfig(mode=Mode.PERP, fill_delay=0, costs=zero(max_hourly_rate_bps_long=1, utilization=1))
        good = run_backtest(Always(), arrays(), cfg)
        self.assertAlmostEqual(good.metrics.total_borrow_fees, 24)
        for seconds in (30 * 86400, 3600, 0):
            a = arrays(); a['ts'][1] = a['ts'][0] + seconds
            with self.subTest(seconds=seconds), self.assertRaises(ValueError): run_backtest(Always(), a, cfg)
            with self.subTest(grid_seconds=seconds), self.assertRaises(ValueError):
                run_grid_backtest(GridConfig(80, 120, 3, 25), a, carry_bps_per_hour=1)
        hourly = arrays(); hourly['ts'][1] = hourly['ts'][0] + 3600
        result = run_backtest(Always(), hourly, EngineConfig(mode=Mode.PERP, interval='1h', fill_delay=0,
                                                           costs=zero(max_hourly_rate_bps_long=1, utilization=1)))
        self.assertAlmostEqual(result.metrics.total_borrow_fees, 1)

    def test_cli_allow_gaps_does_not_bypass_simulation_cadence_refusal(self):
        import pandas as pd
        from backtester import cli
        a = arrays()
        a['ts'][1] = a['ts'][0] + 30 * 86400
        frame = pd.DataFrame({'timestamp': a['ts'], **{k: a[k] for k in ('open', 'high', 'low', 'close', 'volume')}})
        errors = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'gapped.csv'
            frame.to_csv(path, index=False)
            with contextlib.redirect_stderr(errors):
                code = cli.main(['--data', str(path), '--allow-gaps', '--strategy', 'buy_and_hold'])
        self.assertEqual(code, 1)
        self.assertIn('cadence', errors.getvalue())

    def test_cli_invalid_cost_still_returns_usage_error_instead_of_traceback(self):
        from backtester import cli
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['--synthetic', '4', '--fee-bps', '-1', '--strategy', 'buy_and_hold']), 2)


class HeldOutSelection(unittest.TestCase):
    def test_test_only_scores_and_trade_counts_never_change_triple_construction(self):
        names = ['ma_crossover', 'macd', 'ts_momentum', 'rsi']
        def metric(score, trades):
            return SimpleNamespace(sharpe=score, trade_count=trades, total_return=0., max_drawdown=0., exposure_fraction=0.)
        captures = []
        for scores, counts in [([100, 10, 1, -100], [100, 100, 100, 0]),
                               ([-100, 1, 10, 100], [0, 100, 100, 100])]:
            rows = [sweep.Row(name, 'single', 'medium', sweep.FAMILY[name], '-',
                              metric(0, 100), metric(i + 1, 100), metric(scores[i], counts[i]), [name])
                    for i, name in enumerate(names)]
            def capture(top, *_args): captures.append(list(top)); return []
            with tempfile.TemporaryDirectory() as directory, \
                 mock.patch.object(sweep, 'OUT_DIR', Path(directory)), \
                 mock.patch.object(sweep, 'sweep_singles', return_value=rows), \
                 mock.patch.object(sweep, 'load_horizon', return_value=({}, EngineConfig())), \
                 mock.patch.object(sweep, 'independent_combos', side_effect=capture), \
                 mock.patch.object(sweep, 'fmt_table', return_value=''), \
                 mock.patch.object(sweep, 'data_dir', return_value=Path('/synthetic')), \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(sweep.main(['--stage', 'singles', '--stage', 'triples', '--horizon', 'medium', '--triple-top', '3']), 0)
        self.assertEqual(captures, [['rsi', 'ts_momentum', 'macd']] * 2)

"""Streaming prefixes retain economics instead of undoing a terminal trade."""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.types import CostConfig


def bars(n=4):
    p = np.array([100.0, 101.0, 104.0, 102.0][:n])
    return {
        "ts": np.arange(n) * 60 + 1700000040,
        "open": p,
        "high": p,
        "low": p,
        "close": p,
        "volume": np.ones(n),
    }


class OpenPrefixTests(unittest.TestCase):
    def test_open_account_and_pending_target(self):
        cfg = EngineConfig(interval="1m", costs=CostConfig(fee_bps=10, slippage_bps=5))
        result = run_backtest(BuyAndHold(), bars(), cfg, close_at_end=False)
        self.assertGreater(result.account.position.units, 0)
        self.assertGreater(result.account.position.entry_costs, 0)
        self.assertAlmostEqual(
            result.equity[-1], result.account.cash + result.account.position.units * 102
        )
        self.assertNotIn("final", [t.reason for t in result.trades])
        self.assertIn(4, result.account.pending_targets)
        closed = run_backtest(BuyAndHold(), bars(), cfg)
        self.assertEqual(closed.account.position.units, 0)
        self.assertEqual(closed.trades[-1].reason, "final")
        for n in range(1, 5):
            prefix = run_backtest(BuyAndHold(), bars(n), cfg, close_at_end=False)
            self.assertEqual(
                prefix.trades, [t for t in result.trades if t.bar_index < n]
            )

    def test_missing_volume_is_unavailable(self):
        a = bars()
        del a["volume"]
        run_backtest(
            BuyAndHold(),
            a,
            EngineConfig(interval="1m"),
            close_at_end=False,
            price_only=True,
        )

        class VolumeUser(BuyAndHold):
            def on_bar(self, history):
                return float(history.volumes[-1])

        with self.assertRaisesRegex(ValueError, "volume_unavailable"):
            run_backtest(
                VolumeUser(),
                a,
                EngineConfig(interval="1m"),
                close_at_end=False,
                price_only=True,
            )

    def test_deliberate_future_access_refuses(self):
        from backtester.core.types import LookAheadError

        class Leaky(BuyAndHold):
            def on_bar(self, history):
                return history.bar(-1).close

        with self.assertRaises(LookAheadError):
            run_backtest(
                Leaky(), bars(), EngineConfig(interval="1m"), close_at_end=False
            )

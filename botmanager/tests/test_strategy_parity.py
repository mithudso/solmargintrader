from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.config import resolve_config
from botmanager.data import load_recording
from botmanager.domain import BotSpec
from botmanager.strategies import evaluate

from tests.test_paper import recording


class FamilyParityTests(unittest.TestCase):
    def test_prefixes_keep_open_inventory_and_restart(self):
        from uuid import uuid4

        from botmanager.ledger import RuntimeLedger

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for family, overrides in [
                ("grid", {}),
                ("dca", {}),
                ("trend", {"fast_period": 2, "slow_period": 3}),
                ("momentum", {"window": 2}),
            ]:
                spec = BotSpec.create(
                    family, family, resolve_config(family, {}, overrides, None)
                )
                data = load_recording(recording(root, 12), strategy_id=family)
                with patch(
                    "socket.socket", side_effect=AssertionError("engine network")
                ):
                    final = evaluate(spec, data, 12)
                    for n in range(1, 13):
                        prefix = evaluate(spec, data, n)
                        self.assertEqual(
                            prefix["fills"],
                            [f for f in final["fills"] if f["bar_index"] < n],
                        )
                        self.assertAlmostEqual(
                            prefix["equity_quote"],
                            prefix["cash_quote"] + prefix["exposure_quote"],
                        )
                ledger = RuntimeLedger(root / family)
                ledger.register(spec, data)
                ledger.control(spec, "start", str(uuid4()))
                generation = ledger.claim(spec.bot_id, "test")
                ledger.commit_tick(spec.bot_id, generation, 0, evaluate(spec, data, 5))
                ledger.recover("restart")
                generation = ledger.claim(spec.bot_id, "restart")
                ledger.commit_tick(spec.bot_id, generation, 5, final)
                self.assertEqual(ledger.get(spec.bot_id)["checkpoint"], final)

    def test_canonical_batch_results_and_future_tail_invariance(self):
        import copy
        from dataclasses import asdict

        import numpy as np
        from botmanager.config import DEFAULTS
        from botmanager.domain import fingerprint

        from backtester.core.dcasim import DcaConfig, run_dca_backtest
        from backtester.core.engine import EngineConfig, run_backtest
        from backtester.core.strategies.signals import TsMomentum
        from backtester.core.types import CostConfig
        from soltui.trend import TrendConfig, TrendFollowing

        with tempfile.TemporaryDirectory() as tmp:
            for family, changes in [
                ("dca", {}),
                ("trend", {"fast_period": 2, "slow_period": 3}),
                ("momentum", {"window": 2}),
            ]:
                spec = BotSpec.create(
                    family, family, resolve_config(family, {}, changes, None)
                )
                data = load_recording(recording(Path(tmp), 12), strategy_id=family)
                a = {
                    k: np.array([b[k] for b in data["bars"]])
                    for k in ("ts", "open", "high", "low", "close")
                }
                costs = CostConfig(fee_bps=6, slippage_bps=2)
                if family == "dca":
                    result = run_dca_backtest(
                        DcaConfig(
                            **{k: spec.resolved_values[k] for k in DEFAULTS["dca"]}
                        ),
                        a,
                        initial_capital=1000,
                        interval="1m",
                        costs=costs,
                        close_at_end=False,
                    )
                else:
                    strategy = (
                        TrendFollowing(TrendConfig(fast_period=2, slow_period=3))
                        if family == "trend"
                        else TsMomentum(window=2)
                    )
                    result = run_backtest(
                        strategy,
                        a,
                        EngineConfig(initial_capital=1000, interval="1m", costs=costs),
                        close_at_end=False,
                        price_only=True,
                    )
                actual = evaluate(spec, data, 12)
                self.assertEqual(actual["fills"], [asdict(t) for t in result.trades])
                self.assertAlmostEqual(actual["equity_quote"], result.equity[-1])
                changed = copy.deepcopy(data)
                for bar in changed["bars"][6:]:
                    for key in ("open", "high", "low", "close"):
                        bar[key] *= 100
                changed["snapshot_hash"] = fingerprint(
                    {k: v for k, v in changed.items() if k != "snapshot_hash"}
                )
                before = evaluate(spec, data, 6)
                after = evaluate(spec, changed, 6)
                for key in (
                    "fills",
                    "lots",
                    "equity_quote",
                    "cash_quote",
                    "fees_quote",
                ):
                    self.assertEqual(before[key], after[key])

    def test_warmup_costs_and_distinct_signal_rules(self):
        import numpy as np

        from backtester.core.engine import EngineConfig, run_backtest
        from backtester.core.strategies.buy_and_hold import BuyAndHold
        from backtester.core.strategies.signals import TsMomentum
        from backtester.core.types import BarWindow, CostConfig
        from soltui.trend import TrendConfig, TrendFollowing

        p = np.array([100.0, 100.0, 104.0, 101.0])
        a = {
            "ts": np.arange(4) * 60 + 1700000040,
            **{k: p for k in ("open", "high", "low", "close")},
        }
        trend = TrendFollowing(
            TrendConfig(fast_period=1, slow_period=3, entry_buffer_bps=100)
        )
        h = lambda i: BarWindow(a["ts"], p, p, p, p, None, i)
        self.assertEqual(trend.on_bar(h(2)), 1)
        # At the next bar fast<=slow exits. Momentum's trailing return remains positive.
        self.assertEqual(trend.on_bar(h(3)), 0)
        self.assertEqual(TsMomentum(window=3).on_bar(h(3)), 1)
        flat = {**a, **{k: np.ones(4) * 100 for k in ("open", "high", "low", "close")}}
        result = run_backtest(
            BuyAndHold(),
            flat,
            EngineConfig(interval="1m", costs=CostConfig(fee_bps=50, slippage_bps=20)),
            close_at_end=False,
            price_only=True,
        )
        self.assertLess(result.equity[-1], 10000)
        warm = run_backtest(
            TsMomentum(window=60),
            a,
            EngineConfig(interval="1m"),
            close_at_end=False,
            price_only=True,
        )
        self.assertEqual(warm.trades, [])
        self.assertEqual(warm.account.cash, 10000)

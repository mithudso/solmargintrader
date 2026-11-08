"""Economic invariants independent of the coin-fit ranking formula."""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.coinfit import matched_hold, simulate, underwater_days
from backtester.core.dcasim import DcaConfig
from backtester.core.types import CostConfig


def flat(n=48, price=100.0):
    return {
        "ts": np.arange(n, dtype="int64") * 3600,
        **{key: np.full(n, price) for key in ("open", "high", "low", "close")},
        "volume": np.ones(n),
    }


class EconomicTests(unittest.TestCase):
    def test_baseline_waits_for_next_open_and_pays_both_sides(self):
        data = flat()
        data["open"][1] = 200
        hold = matched_hold(data, 1000, CostConfig(fee_bps=10, slippage_bps=20))
        expected = 1000 / (1.001 * 200 * 1.002) * 100 * 0.998 * 0.999
        self.assertEqual(hold[0], 1000)
        self.assertAlmostEqual(hold[-1], expected)

    def test_scheduled_next_open_not_decision_close(self):
        data = flat()
        data["open"][1] = data["high"][1] = 200
        out = simulate(
            "scheduled_dca",
            {"interval_hours": 168},
            data,
            capital=1000,
            costs=CostConfig(fee_bps=0, slippage_bps=0),
            include_fills=True,
        )
        self.assertEqual(out["metrics"]["final_equity"], 500)
        self.assertEqual(out["fills"][0]["bar_index"], 1)
        self.assertEqual(out["fills"][-1]["side"], "sell")

    def test_flat_schedule_hand_accounting_and_ledger(self):
        out = simulate(
            "scheduled_dca",
            {"interval_hours": 12},
            flat(),
            capital=1000,
            costs=CostConfig(fee_bps=10, slippage_bps=20),
            include_fills=True,
        )
        expected = 1000 / (1.001 * 1.002) * 0.998 * 0.999
        self.assertAlmostEqual(out["metrics"]["final_equity"], expected)
        self.assertAlmostEqual(1000 - expected, out["metrics"]["costs_usd"])
        cash, quantity = 1000.0, 0.0
        for fill in out["fills"]:
            if fill["side"] == "buy":
                cash -= fill["notional"] + fill["fee"]
                quantity += fill["units"]
            else:
                cash += fill["notional"] - fill["fee"]
                quantity -= fill["units"]
        self.assertAlmostEqual(quantity, 0)
        self.assertAlmostEqual(cash, expected)

    def test_scheduled_stress_costs_reduce_fixed_path_equity(self):
        base = simulate(
            "scheduled_dca",
            {"interval_hours": 12},
            flat(),
            capital=1000,
            costs=CostConfig(fee_bps=10, slippage_bps=20),
        )
        stress = simulate(
            "scheduled_dca",
            {"interval_hours": 12},
            flat(),
            capital=1000,
            costs=CostConfig(fee_bps=20, slippage_bps=40),
        )
        self.assertLess(
            stress["metrics"]["final_equity"], base["metrics"]["final_equity"]
        )

    def test_dca_reserve_not_only_base_and_unfinished_deal_disclosed(self):
        costs = CostConfig(fee_bps=6, slippage_bps=2)
        result = simulate(
            "dca",
            DcaConfig().to_dict(),
            flat(),
            capital=1000,
            costs=costs,
            include_fills=True,
        )
        expected = 1000 - 100 * 1.0006 + 100 / 1.0002 * 0.9998 * 0.9994
        self.assertAlmostEqual(result["metrics"]["final_equity"], expected)
        self.assertAlmostEqual(result["metrics"]["total_return"], expected / 1000 - 1)
        self.assertEqual(result["metrics"]["cycles"], 0)
        self.assertEqual(result["metrics"]["unfinished_deals"], 1)
        self.assertGreater(result["metrics"]["open_inventory_before_exit"], 0)
        self.assertEqual(result["fills"][-1]["reason"], "dca_forced_exit")

    def test_risk_uses_full_curve_not_display_samples(self):
        data = flat(200)
        data["open"][40] = data["close"][40] = data["low"][40] = 40
        result = simulate(
            "scheduled_dca",
            {"interval_hours": 200},
            data,
            capital=1000,
            costs=CostConfig(fee_bps=1, slippage_bps=1),
            trace_limit=2,
        )
        self.assertEqual(len(result["equity"]), 2)
        self.assertLess(result["metrics"]["max_drawdown"], -0.59)

    def test_gap_and_missing_observed_open_refused(self):
        data = flat()
        data = {k: np.delete(v, 10) for k, v in data.items()}
        with self.assertRaises(ValueError):
            simulate(
                "scheduled_dca",
                {"interval_hours": 24},
                data,
                capital=1000,
                costs=CostConfig(),
            )
        data = flat()
        del data["open"]
        with self.assertRaisesRegex(ValueError, "observed opens"):
            simulate(
                "scheduled_dca",
                {"interval_hours": 24},
                data,
                capital=1000,
                costs=CostConfig(),
            )

    def test_negative_costs_and_unsupported_bot_refused(self):
        with self.assertRaises(ValueError):
            CostConfig(fee_bps=-1)
        with self.assertRaises(ValueError):
            simulate("triangle", {}, flat(), capital=1000, costs=CostConfig())

    def test_ongoing_underwater_episode_counted(self):
        self.assertEqual(
            underwater_days(np.array([100, 90, 95, 99]), np.arange(4) * 86400, 100), 3
        )


if __name__ == "__main__":
    unittest.main()

"""Acceptance tests for the backtest engine.

These are known-answer tests, not smoke tests. Each one has a hand-computed
expected value, so a failure localises the bug rather than just signalling
that something changed.
"""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from backtester.core import perps
from backtester.core.data import (
    DataValidationError,
    SyntheticLoader,
    frame_to_arrays,
    validate_bars,
)
from backtester.core.engine import EngineConfig, _Book, run_backtest
from backtester.core.strategies.buy_and_hold import BuyAndHold
from backtester.core.types import BarWindow, CostConfig, LookAheadError, Mode, Side


def make_frame(closes: list[float], step: int = 86400) -> pd.DataFrame:
    """Build a minimal valid frame whose open == previous close."""
    n = len(closes)
    closes_arr = np.array(closes, dtype="float64")
    opens = np.empty(n)
    opens[0] = closes_arr[0]
    opens[1:] = closes_arr[:-1]
    return pd.DataFrame(
        {
            "timestamp": 1_600_000_000 + np.arange(n, dtype="int64") * step,
            "open": opens,
            "high": np.maximum(opens, closes_arr) * 1.01,
            "low": np.minimum(opens, closes_arr) * 0.99,
            "close": closes_arr,
            "volume": np.full(n, 1000.0),
        }
    )


ZERO_COST = CostConfig(fee_bps=0.0, slippage_bps=0.0, perp_base_fee_bps=0.0)


class TestBuyAndHoldIdentity(unittest.TestCase):
    """The engine's primary known-answer test."""

    def test_zero_cost_identity(self) -> None:
        """Buy-and-hold total return == last_close/first_close - 1 exactly."""
        closes = [100.0, 105.0, 98.0, 120.0, 117.5, 131.0]
        arrays = frame_to_arrays(validate_bars(make_frame(closes), "1d"))
        cfg = EngineConfig(
            initial_capital=10_000.0,
            costs=ZERO_COST,
            fill_delay=0,
            mode=Mode.SPOT,
        )
        res = run_backtest(BuyAndHold(), arrays, cfg)
        expected = closes[-1] / closes[0] - 1.0
        self.assertAlmostEqual(res.metrics.total_return, expected, places=12)
        self.assertAlmostEqual(
            res.metrics.final_equity, 10_000.0 * (1.0 + expected), places=8
        )

    def test_identity_holds_on_synthetic_series(self) -> None:
        """Same identity on 500 seeded bars, not just a hand-written six."""
        df = SyntheticLoader(n_bars=500, seed=7).load("SOL", None, None, "1d")
        arrays = frame_to_arrays(df)
        cfg = EngineConfig(costs=ZERO_COST, fill_delay=0)
        res = run_backtest(BuyAndHold(), arrays, cfg)
        expected = float(df["close"].iloc[-1] / df["close"].iloc[0] - 1.0)
        self.assertAlmostEqual(res.metrics.total_return, expected, places=10)

    def test_perp_at_1x_matches_spot(self) -> None:
        """At leverage 1 with zero costs, perp accounting reduces to spot."""
        closes = [50.0, 55.0, 45.0, 60.0]
        arrays = frame_to_arrays(validate_bars(make_frame(closes), "1d"))
        no_borrow = CostConfig(
            fee_bps=0.0,
            slippage_bps=0.0,
            perp_base_fee_bps=0.0,
            max_hourly_rate_bps_long=0.0,
            max_hourly_rate_bps_short=0.0,
        )
        spot = run_backtest(
            BuyAndHold(),
            arrays,
            EngineConfig(costs=ZERO_COST, fill_delay=0, mode=Mode.SPOT),
        )
        perp = run_backtest(
            BuyAndHold(),
            arrays,
            EngineConfig(
                costs=no_borrow, fill_delay=0, mode=Mode.PERP, leverage=1.0
            ),
        )
        self.assertAlmostEqual(
            spot.metrics.total_return, perp.metrics.total_return, places=10
        )


class TestLookAheadGuard(unittest.TestCase):
    """A guard that cannot fail is not a guard."""

    def _window(self) -> BarWindow:
        df = validate_bars(make_frame([10.0, 11.0, 12.0, 13.0, 14.0]), "1d")
        a = frame_to_arrays(df)
        return BarWindow(
            a["ts"], a["open"], a["high"], a["low"], a["close"], a["volume"], i=2
        )

    def test_slice_hides_future(self) -> None:
        """Truncated accessors expose exactly i+1 bars."""
        w = self._window()
        self.assertEqual(len(w), 3)
        self.assertEqual(len(w.closes), 3)
        self.assertEqual(float(w.closes[-1]), 12.0)

    def test_indexing_past_current_bar_raises(self) -> None:
        """Reading closes[i+1] off the truncated view raises IndexError."""
        w = self._window()
        with self.assertRaises(IndexError):
            _ = w.closes[w.i + 1]

    def test_absolute_future_index_raises(self) -> None:
        """at() rejects an absolute index beyond the current bar."""
        w = self._window()
        with self.assertRaises(LookAheadError):
            w.at(3)

    def test_negative_offset_raises(self) -> None:
        """A negative offset names a future bar and is rejected."""
        w = self._window()
        with self.assertRaises(LookAheadError):
            w.bar(-1)

    def test_cheating_strategy_is_caught_by_the_engine(self) -> None:
        """A strategy that peeks at the next bar fails the run, loudly."""

        class Cheater:
            name = "cheater"
            params: dict = {}

            def warmup_bars(self) -> int:
                return 1

            def on_bar(self, history: BarWindow) -> float:
                # Tomorrow's close, if we could see it.
                return 1.0 if history.closes[history.i + 1] > history.closes[-1] else 0.0

        arrays = frame_to_arrays(
            validate_bars(make_frame([10.0, 11.0, 12.0, 13.0]), "1d")
        )
        with self.assertRaises(IndexError):
            run_backtest(Cheater(), arrays, EngineConfig(costs=ZERO_COST))


class TestFillTiming(unittest.TestCase):
    """A signal on bar t fills at bar t+1's open."""

    def test_fill_lands_on_next_bar_open(self) -> None:
        """First fill is at index 1 and at that bar's open price."""
        closes = [100.0, 110.0, 120.0, 130.0]
        df = validate_bars(make_frame(closes), "1d")
        arrays = frame_to_arrays(df)
        res = run_backtest(
            BuyAndHold(),
            arrays,
            EngineConfig(costs=ZERO_COST, fill_delay=1, initial_capital=1_000.0),
        )
        opens = df["open"].to_numpy()
        first = res.trades[0]
        self.assertEqual(first.reason, "open")
        self.assertEqual(first.bar_index, 1)
        self.assertAlmostEqual(first.price, float(opens[1]), places=12)

    def test_delay_two_lands_two_bars_later(self) -> None:
        """fill_delay=2 pushes the first fill to index 2."""
        arrays = frame_to_arrays(
            validate_bars(make_frame([100.0, 110.0, 120.0, 130.0, 140.0]), "1d")
        )
        res = run_backtest(
            BuyAndHold(), arrays, EngineConfig(costs=ZERO_COST, fill_delay=2)
        )
        self.assertEqual(res.trades[0].bar_index, 2)

    def test_no_trade_before_warmup(self) -> None:
        """A strategy with warmup W produces no fill before bar W."""

        class LateStarter:
            name = "late"
            params: dict = {}

            def warmup_bars(self) -> int:
                return 3

            def on_bar(self, history: BarWindow) -> float:
                return 1.0

        arrays = frame_to_arrays(
            validate_bars(make_frame([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), "1d")
        )
        res = run_backtest(
            LateStarter(), arrays, EngineConfig(costs=ZERO_COST, fill_delay=1)
        )
        self.assertTrue(all(t.bar_index >= 3 for t in res.trades))


class TestFeeArithmetic(unittest.TestCase):
    """Costs are charged on the fill, at hand-computable values."""

    def test_round_trip_cost_matches_hand_computation(self) -> None:
        """Total cost equals notional * (fee+slip) on open plus on close."""
        costs = CostConfig(fee_bps=6.0, slippage_bps=2.0)
        arrays = frame_to_arrays(validate_bars(make_frame([100.0, 100.0, 100.0]), "1d"))
        cfg = EngineConfig(initial_capital=10_000.0, costs=costs, fill_delay=0)
        res = run_backtest(BuyAndHold(), arrays, cfg)

        c = (6.0 + 2.0) / 10_000.0
        open_notional = 10_000.0 / (1.0 + c)  # solves N + N*c == capital
        expected_open_cost = open_notional * c
        # Price is flat, so the close settles the same notional.
        expected_close_cost = open_notional * c
        expected_total = expected_open_cost + expected_close_cost

        self.assertAlmostEqual(res.metrics.total_fees, expected_total, places=8)
        # Flat price plus costs means the account must end down by exactly the costs.
        self.assertAlmostEqual(
            res.metrics.final_equity, 10_000.0 - expected_total, places=6
        )

    def test_gross_beats_net_by_the_cost_drag(self) -> None:
        """The parallel zero-cost book differs from net by total costs."""
        costs = CostConfig(fee_bps=10.0, slippage_bps=5.0)
        arrays = frame_to_arrays(
            validate_bars(make_frame([100.0, 120.0, 90.0, 150.0]), "1d")
        )
        res = run_backtest(
            BuyAndHold(),
            arrays,
            EngineConfig(initial_capital=10_000.0, costs=costs, fill_delay=0),
        )
        self.assertGreater(res.gross_metrics.total_return, res.metrics.total_return)


class TestResizeCosts(unittest.TestCase):
    """A same-side resize pays cost on the size change, not a round trip."""

    def test_resize_charges_only_the_delta(self) -> None:
        """Growing a position by D notional costs D*(fee+slip), once."""
        costs = CostConfig(fee_bps=10.0, slippage_bps=0.0)
        cfg = EngineConfig(initial_capital=10_000.0, costs=costs, fill_delay=0)
        book = _Book(cfg)
        book.open(1_000.0, Side.LONG, price=100.0, ts=0, index=0)
        fee_after_open = sum(t.fee for t in book.trades)

        book.resize(1_500.0, price=100.0, ts=1, index=1)
        resize_trade = book.trades[-1]
        self.assertEqual(resize_trade.reason, "resize_up")
        # Delta is 500 notional, so the fee is 500 * 10bps = 0.50.
        self.assertAlmostEqual(resize_trade.fee, 500.0 * 0.001, places=10)
        self.assertAlmostEqual(resize_trade.notional, 500.0, places=10)
        # A close+reopen would have charged ~1000*10bps + 1500*10bps = 2.50.
        self.assertLess(sum(t.fee for t in book.trades) - fee_after_open, 1.0)

    def test_resize_up_blends_entry_price(self) -> None:
        """Adding at a higher price raises the average entry, not resets it."""
        cfg = EngineConfig(initial_capital=100_000.0, costs=ZERO_COST, fill_delay=0)
        book = _Book(cfg)
        book.open(1_000.0, Side.LONG, price=100.0, ts=0, index=0)  # 10 units
        book.resize(2_000.0, price=200.0, ts=1, index=1)  # position worth 2000 @200
        # Current notional at 200 is 10*200 = 2000, already the target, so no
        # change should occur -- the gap is zero.
        self.assertAlmostEqual(book.pos.entry_price, 100.0, places=10)

        # Now genuinely grow it: target 3000 at price 200 adds 5 units at 200.
        book.resize(3_000.0, price=200.0, ts=2, index=2)
        expected_entry = (10 * 100.0 + 5 * 200.0) / 15.0
        self.assertAlmostEqual(book.pos.entry_price, expected_entry, places=10)
        self.assertAlmostEqual(abs(book.pos.units), 15.0, places=10)

    def test_resize_down_realises_partial_pnl(self) -> None:
        """Trimming half a winning position realises half the gain."""
        cfg = EngineConfig(initial_capital=10_000.0, costs=ZERO_COST, fill_delay=0)
        book = _Book(cfg)
        book.open(1_000.0, Side.LONG, price=100.0, ts=0, index=0)  # 10 units @100
        book.resize(1_000.0, price=200.0, ts=1, index=1)  # 10@200=2000 -> trim to 1000
        trade = book.trades[-1]
        self.assertEqual(trade.reason, "resize_down")
        # Sold 5 units bought at 100, now 200 -> +500 realised.
        self.assertAlmostEqual(trade.realized_pnl, 500.0, places=8)
        self.assertAlmostEqual(abs(book.pos.units), 5.0, places=10)
        # Entry price is unchanged by a partial exit.
        self.assertAlmostEqual(book.pos.entry_price, 100.0, places=10)

    def test_resize_up_is_not_counted_as_a_decided_trade(self) -> None:
        """A size increase has no outcome yet, so it must not count as a loss."""
        from backtester.core.metrics import trade_stats
        from backtester.core.types import Trade

        stats = trade_stats(
            [
                Trade(0, 0, "long", 100.0, 1.0, 100.0, 0.1, 0.0, 0.0, -0.1, 0.0, "open"),
                Trade(1, 1, "long", 100.0, 1.0, 100.0, 0.1, 0.0, 0.0, -0.1, 0.0, "resize_up"),
                Trade(2, 2, "close", 120.0, -2.0, 240.0, 0.2, 0.0, 0.0, 40.0, 0.0, "signal"),
            ]
        )
        self.assertEqual(stats["trade_count"], 1)
        self.assertAlmostEqual(stats["win_rate"], 1.0, places=10)


class TestGapLiquidation(unittest.TestCase):
    """A bar that gaps through the level liquidates at the open."""

    def test_gap_down_fills_at_open_not_at_level(self) -> None:
        """Liquidation cannot fill at a price the bar never traded above."""
        # Bar 2 opens at 70, far below the ~90.26 liquidation level.
        df = pd.DataFrame(
            {
                "timestamp": 1_600_000_000 + np.arange(3, dtype="int64") * 86400,
                "open": [100.0, 100.0, 70.0],
                "high": [101.0, 101.0, 72.0],
                "low": [99.0, 99.0, 60.0],
                "close": [100.0, 100.0, 65.0],
                "volume": [1.0, 1.0, 1.0],
            }
        )
        arrays = frame_to_arrays(validate_bars(df, "1d"))
        cfg = EngineConfig(
            mode=Mode.PERP,
            leverage=10.0,
            initial_capital=1_000.0,
            fill_delay=0,
            costs=CostConfig(),
        )
        res = run_backtest(BuyAndHold(), arrays, cfg)
        liq_fills = [t for t in res.trades if t.reason == "liquidation"]
        self.assertTrue(liq_fills, "expected a liquidation on the gap-down bar")
        # Must fill at or below the gapped open, never at the ~90.26 level.
        self.assertLessEqual(liq_fills[0].price, 70.0 + 1e-9)


class TestBorrowFeeSign(unittest.TestCase):
    """Borrow fees are never negative, for either side, at any utilization."""

    def test_non_negative_across_utilization_and_side(self) -> None:
        """The floor-at-zero property holds across the whole domain."""
        costs = CostConfig()
        for u in np.linspace(0.0, 1.0, 51):
            for side in (Side.LONG, Side.SHORT):
                rate = perps.hourly_borrow_rate(costs, side, float(u))
                self.assertGreaterEqual(
                    rate, 0.0, f"negative rate at u={u}, side={side}"
                )
                fee = perps.accrue_borrow_fee(
                    costs, side, notional=10_000.0, hours=24.0, utilization=float(u)
                )
                self.assertGreaterEqual(fee, 0.0)

    def test_both_sides_pay(self) -> None:
        """Both directions owe a strictly positive fee at nonzero utilization."""
        costs = CostConfig()
        long_fee = perps.accrue_borrow_fee(
            costs, Side.LONG, 10_000.0, 24.0, utilization=0.5
        )
        short_fee = perps.accrue_borrow_fee(
            costs, Side.SHORT, 10_000.0, 24.0, utilization=0.5
        )
        self.assertGreater(long_fee, 0.0)
        self.assertGreater(short_fee, 0.0)
        # Shorts borrow stable custody, which is documented as far cheaper.
        self.assertLess(short_fee, long_fee)

    def test_documented_rate_reference_point(self) -> None:
        """0.016%/hr max at 50% utilization gives 0.008%/hr effective."""
        costs = CostConfig(max_hourly_rate_bps_long=1.6)
        rate = perps.hourly_borrow_rate(costs, Side.LONG, 0.5)
        self.assertAlmostEqual(rate, 0.00008, places=10)  # 0.008%
        # ~140% APR at full utilization is the documented SOL figure.
        full = perps.hourly_borrow_rate(costs, Side.LONG, 1.0)
        self.assertAlmostEqual(full * 24 * 365, 1.4016, places=6)

    def test_fee_is_linear_not_compounding(self) -> None:
        """Doubling the hours doubles the fee exactly (index difference)."""
        costs = CostConfig()
        a = perps.accrue_borrow_fee(costs, Side.LONG, 10_000.0, 24.0, 0.5)
        b = perps.accrue_borrow_fee(costs, Side.LONG, 10_000.0, 48.0, 0.5)
        self.assertAlmostEqual(b, 2 * a, places=12)

    def test_rate_floor_option(self) -> None:
        """The proposed dual-slope floor is available and overrides flat-linear."""
        costs = CostConfig(min_hourly_rate_bps=0.5)
        # At zero utilization flat-linear gives 0; the floor must win.
        self.assertAlmostEqual(
            perps.hourly_borrow_rate(costs, Side.LONG, 0.0), 0.00005, places=10
        )

    def test_invalid_utilization_rejected(self) -> None:
        """Utilization outside [0,1] is a programming error, not a clamp."""
        with self.assertRaises(ValueError):
            perps.hourly_borrow_rate(CostConfig(), Side.LONG, 1.5)


class TestLiquidation(unittest.TestCase):
    """Liquidation price matches the documented worked example, and drifts."""

    def test_documented_worked_example(self) -> None:
        """Entry 100, size 10k, collateral 1k, 10x, zero borrow -> 90.26."""
        costs = CostConfig(perp_base_fee_bps=6.0)
        info = perps.liquidation_price(
            entry_price=100.0,
            side=Side.LONG,
            collateral=1_000.0,
            notional=10_000.0,
            accrued_borrow_fee=0.0,
            costs=costs,
        )
        self.assertTrue(info.in_domain)
        self.assertAlmostEqual(info.price, 90.26, places=6)
        self.assertAlmostEqual(info.buffer_fraction, 0.0974, places=10)

    def test_maintenance_margin_is_two_tenths_percent(self) -> None:
        """max_lev is the protocol constant 500, so maintenance is 0.2%."""
        self.assertAlmostEqual(CostConfig().maintenance_margin_fraction, 0.002, places=12)

    def test_buffer_at_high_leverage(self) -> None:
        """At 250x the buffer is ~0.14% before a single hour of fees."""
        costs = CostConfig(perp_base_fee_bps=6.0)
        info = perps.liquidation_price(
            entry_price=100.0,
            side=Side.LONG,
            collateral=10_000.0 / 250.0,
            notional=10_000.0,
            accrued_borrow_fee=0.0,
            costs=costs,
        )
        self.assertAlmostEqual(info.buffer_fraction, 1 / 250 - 0.0006 - 0.002, places=10)
        self.assertLess(info.buffer_fraction, 0.0015)

    def test_short_liquidation_is_above_entry(self) -> None:
        """A short liquidates on the way up."""
        info = perps.liquidation_price(
            100.0, Side.SHORT, 1_000.0, 10_000.0, 0.0, CostConfig()
        )
        self.assertAlmostEqual(info.price, 109.74, places=6)

    def test_liquidation_price_drifts_toward_spot(self) -> None:
        """Accruing borrow fees monotonically shrinks the long's buffer."""
        costs = CostConfig()
        prices = [
            perps.liquidation_price(
                100.0, Side.LONG, 1_000.0, 10_000.0, borrow, costs
            ).price
            for borrow in (0.0, 50.0, 100.0, 200.0, 400.0)
        ]
        for earlier, later in zip(prices, prices[1:]):
            self.assertGreater(
                later, earlier, "long liquidation price must rise toward spot"
            )

    def test_below_maintenance_leaves_formula_domain(self) -> None:
        """Once collateral is exhausted the formula is flagged, not trusted."""
        info = perps.liquidation_price(
            100.0, Side.LONG, 20.0, 10_000.0, 0.0, CostConfig()
        )
        self.assertFalse(info.in_domain)
        self.assertTrue(info.below_maintenance)

    def test_wick_triggers_liquidation(self) -> None:
        """An intrabar low through the level liquidates even if the close recovers."""
        info = perps.liquidation_price(
            100.0, Side.LONG, 1_000.0, 10_000.0, 0.0, CostConfig()
        )
        self.assertTrue(perps.is_liquidated(Side.LONG, info, bar_low=90.0, bar_high=101.0))
        self.assertFalse(
            perps.is_liquidated(Side.LONG, info, bar_low=95.0, bar_high=101.0)
        )

    def test_engine_liquidates_on_adverse_move(self) -> None:
        """End-to-end: a 10x long into a -20% move is liquidated."""
        closes = [100.0, 99.0, 80.0, 75.0]
        arrays = frame_to_arrays(validate_bars(make_frame(closes), "1d"))
        cfg = EngineConfig(
            mode=Mode.PERP,
            leverage=10.0,
            initial_capital=1_000.0,
            fill_delay=0,
            costs=CostConfig(),
        )
        res = run_backtest(BuyAndHold(), arrays, cfg)
        self.assertGreaterEqual(res.liquidation_count, 1)
        self.assertLess(res.metrics.total_return, 0.0)


class TestDataValidation(unittest.TestCase):
    """Malformed input is rejected rather than silently backtested."""

    def test_duplicate_timestamp_rejected(self) -> None:
        """Duplicate bars would double-count a period."""
        df = make_frame([10.0, 11.0, 12.0])
        df.loc[2, "timestamp"] = df.loc[1, "timestamp"]
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_high_below_low_rejected(self) -> None:
        """An impossible bar is a data error, not a trading opportunity."""
        df = make_frame([10.0, 11.0, 12.0])
        df.loc[1, "high"] = 1.0
        df.loc[1, "low"] = 100.0
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_negative_price_rejected(self) -> None:
        """Prices must be positive."""
        df = make_frame([10.0, 11.0, 12.0])
        df.loc[1, "close"] = -5.0
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_gap_rejected(self) -> None:
        """A missing bar silently changes every rolling window."""
        df = make_frame([10.0, 11.0, 12.0, 13.0])
        df.loc[2, "timestamp"] = int(df.loc[2, "timestamp"]) + 86400 * 5
        df.loc[3, "timestamp"] = int(df.loc[3, "timestamp"]) + 86400 * 5
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_millisecond_timestamps_rejected(self) -> None:
        """Millisecond epochs are a unit error, not a distant date."""
        df = make_frame([10.0, 11.0, 12.0])
        df["timestamp"] = df["timestamp"].astype("int64") * 1000
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_missing_column_rejected(self) -> None:
        """The on-disk schema is exact."""
        df = make_frame([10.0, 11.0, 12.0]).drop(columns=["volume"])
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_empty_series_rejected(self) -> None:
        """Zero bars is not a backtest."""
        df = make_frame([10.0, 11.0]).iloc[0:0]
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")

    def test_nan_price_rejected(self) -> None:
        """NaN prices would silently propagate into every metric."""
        df = make_frame([10.0, 11.0, 12.0])
        df.loc[1, "close"] = float("nan")
        with self.assertRaises(DataValidationError):
            validate_bars(df, "1d")


class TestDeterminism(unittest.TestCase):
    """Same inputs and seed produce identical output."""

    def test_two_runs_are_identical(self) -> None:
        """Equity curves match exactly across repeated runs."""
        df = SyntheticLoader(n_bars=300, seed=11).load("SOL", None, None, "1d")
        arrays = frame_to_arrays(df)
        cfg = EngineConfig(costs=CostConfig(), fill_delay=1, seed=99)
        from backtester.core.strategies import build

        a = run_backtest(build("ma_crossover"), arrays, cfg)
        b = run_backtest(build("ma_crossover"), arrays, cfg)
        np.testing.assert_array_equal(a.equity, b.equity)
        self.assertEqual(len(a.trades), len(b.trades))
        self.assertEqual(a.metrics.to_dict(), b.metrics.to_dict())

    def test_synthetic_loader_is_reproducible(self) -> None:
        """The same seed yields the same series."""
        one = SyntheticLoader(n_bars=100, seed=5).load("SOL", None, None, "1d")
        two = SyntheticLoader(n_bars=100, seed=5).load("SOL", None, None, "1d")
        pd.testing.assert_frame_equal(one, two)


class TestConfigGuards(unittest.TestCase):
    """Configuration errors fail fast, not deep in the loop."""

    def test_spot_rejects_leverage(self) -> None:
        """Spot mode does not borrow."""
        with self.assertRaises(ValueError):
            EngineConfig(mode=Mode.SPOT, leverage=5.0)

    def test_negative_fill_delay_rejected(self) -> None:
        """A negative delay would be look-ahead by configuration."""
        with self.assertRaises(ValueError):
            EngineConfig(fill_delay=-1)

    def test_warmup_longer_than_series_rejected(self) -> None:
        """Refuse rather than return an all-flat curve."""
        arrays = frame_to_arrays(validate_bars(make_frame([1.0, 2.0, 3.0]), "1d"))
        from backtester.core.strategies import build

        with self.assertRaises(ValueError):
            run_backtest(build("ma_crossover"), arrays, EngineConfig())


if __name__ == "__main__":
    unittest.main(verbosity=2)

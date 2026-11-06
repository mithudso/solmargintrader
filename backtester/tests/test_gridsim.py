"""Tests for the resting-ladder grid simulator.

The load-bearing test in this file is `test_round_trip_captures_exactly_one_rung`.
The extension shipped a bug once where the exit rested at the level it had just
bought at, capturing zero and paying two fees; `expectedRoundTripUsd` and its JS
test exist to keep that fixed. This suite is the Python half of that guard — if
the two implementations disagree about what a round trip earns, the backtest is
lying about the strategy that runs live.
"""

from __future__ import annotations

import unittest

import numpy as np

from backtester.core.gridsim import (
    SIDE_BUY,
    SIDE_SELL,
    SPACING_ARITH,
    GridConfig,
    _GridBook,
    capital_requirement,
    expected_round_trip_usd,
    grid_levels,
    nearest_level_index,
    paired_exit_level,
    run_grid_backtest,
    rung_width_bps,
    side_for_level,
)
from backtester.core.types import CostConfig

FREE = CostConfig(fee_bps=0.0, slippage_bps=0.0)


def bars(rows: list[tuple[float, float, float, float]], start_ts: int = 1_600_000_000):
    """Build an arrays dict from (open, high, low, close) rows, one day apart."""
    n = len(rows)
    return {
        "ts": np.array([start_ts + i * 86400 for i in range(n)], dtype="int64"),
        "open": np.array([r[0] for r in rows], dtype="float64"),
        "high": np.array([r[1] for r in rows], dtype="float64"),
        "low": np.array([r[2] for r in rows], dtype="float64"),
        "close": np.array([r[3] for r in rows], dtype="float64"),
        "volume": np.ones(n, dtype="float64"),
    }


def flat(price: float, count: int):
    """`count` bars that neither rise nor fall, for priming the ladder."""
    return [(price, price, price, price)] * count


class TestLadderGeometry(unittest.TestCase):
    """Geometry ported from extension/src/core/grid.js."""

    def test_geometric_levels_pin_both_endpoints(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        levels = grid_levels(cfg)
        self.assertEqual(len(levels), 7)
        self.assertEqual(levels[0], 60.0)
        self.assertEqual(levels[-1], 90.0)
        self.assertTrue(all(b > a for a, b in zip(levels, levels[1:])))

    def test_geometric_spacing_is_constant_in_percent(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        levels = grid_levels(cfg)
        ratios = [levels[i] / levels[i - 1] for i in range(1, len(levels))]
        for r in ratios[1:]:
            self.assertAlmostEqual(r, ratios[0], places=12)

    def test_arithmetic_spacing_is_constant_in_dollars(self) -> None:
        cfg = GridConfig(
            lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0,
            spacing=SPACING_ARITH,
        )
        levels = grid_levels(cfg)
        steps = [levels[i] - levels[i - 1] for i in range(1, len(levels))]
        for s in steps:
            self.assertAlmostEqual(s, 5.0, places=12)

    def test_rung_width_matches_the_javascript_implementation(self) -> None:
        # Cross-implementation parity. Both figures were read off
        # extension/src/core/grid.js `rungWidthBps` rather than derived here, so a
        # divergence means the two engines price a round trip differently.
        # 0.85x-1.15x with 7 rungs is the ladder tools/dryrun.js builds, and 516.7
        # bps is the number extension/README.md reports for it.
        self.assertAlmostEqual(
            rung_width_bps(
                GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
            ),
            699.1319,
            places=3,
        )
        self.assertAlmostEqual(
            rung_width_bps(
                GridConfig(lower=85.0, upper=115.0, rungs=7, notional_per_rung_usd=12.0)
            ),
            516.7,
            places=1,
        )

    def test_paired_exit_is_one_rung_up_never_flat(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        levels = grid_levels(cfg)
        for i, level in enumerate(levels[:-1]):
            self.assertEqual(paired_exit_level(levels, level), levels[i + 1])
            self.assertGreater(paired_exit_level(levels, level), level)

    def test_top_rung_exit_extrapolates_one_more_step(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        levels = grid_levels(cfg)
        exit_level = paired_exit_level(levels, levels[-1])
        ratio = levels[-1] / levels[-2]
        self.assertAlmostEqual(exit_level, levels[-1] * ratio, places=12)
        self.assertGreater(exit_level, cfg.upper)

    def test_deadband_suppresses_levels_at_the_market(self) -> None:
        self.assertEqual(side_for_level(70.0, 75.0, 25.0), SIDE_BUY)
        self.assertEqual(side_for_level(80.0, 75.0, 25.0), SIDE_SELL)
        self.assertIsNone(side_for_level(75.05, 75.0, 25.0))

    def test_nearest_level_index_picks_the_closest(self) -> None:
        levels = [60.0, 70.0, 80.0]
        self.assertEqual(nearest_level_index(levels, 59.0), 0)
        self.assertEqual(nearest_level_index(levels, 71.0), 1)
        self.assertEqual(nearest_level_index(levels, 100.0), 2)

    def test_rejects_a_ladder_that_cannot_be_built(self) -> None:
        for kwargs in (
            {"lower": 0.0, "upper": 90.0, "rungs": 5},
            {"lower": 90.0, "upper": 60.0, "rungs": 5},
            {"lower": 60.0, "upper": 90.0, "rungs": 1},
        ):
            with self.assertRaises(ValueError):
                GridConfig(notional_per_rung_usd=12.0, **kwargs)
        with self.assertRaises(ValueError):
            GridConfig(lower=60.0, upper=90.0, rungs=5, notional_per_rung_usd=0.0)
        with self.assertRaises(ValueError):
            GridConfig(
                lower=60.0, upper=90.0, rungs=5, notional_per_rung_usd=12.0,
                spacing="linear",
            )

    def test_capital_requirement_counts_only_the_bids(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        need = capital_requirement(cfg, 90.0)
        # Every level sits below the market at price == upper except the top one,
        # which is inside the deadband, so six bids need funding.
        self.assertAlmostEqual(need["total_usd"], 6 * 12.0, places=9)
        self.assertGreater(need["base_qty"], 0.0)


class TestRoundTripEconomics(unittest.TestCase):
    """The paired-exit invariant, which is why this module exists."""

    def setUp(self) -> None:
        self.cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        self.levels = grid_levels(self.cfg)

    def test_round_trip_captures_exactly_one_rung(self) -> None:
        # A two-rung ladder is the only shape that isolates a single round trip:
        # on a wider ladder a dip to rung 3 also fills every bid above it on the
        # way down, so several lots exist and FIFO decides which one the exit is
        # matched against (see test_pairing_and_fifo_disagree_per_trip).
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=2, notional_per_rung_usd=12.0)
        rows = flat(90.0, 2) + [
            (90.0, 90.0, 60.0, 60.0),
            (60.0, 90.0, 60.0, 90.0),
        ]
        res = run_grid_backtest(cfg, bars(rows), initial_capital=1_000.0, costs=FREE)

        self.assertEqual(res.round_trips, 1, res.skipped)
        expected = expected_round_trip_usd(cfg, 60.0)
        self.assertAlmostEqual(res.gross_captured_usd, expected, places=9)
        self.assertAlmostEqual(res.realized_pnl_usd, expected, places=9)
        # The same figure stated the other way round: notional x rung width. This
        # is the economic contract extension/src/core/grid.js is tested against.
        qty = cfg.notional_per_rung_usd / 60.0
        self.assertAlmostEqual(expected, qty * (90.0 - 60.0), places=12)
        self.assertAlmostEqual(
            expected,
            cfg.notional_per_rung_usd * (rung_width_bps(cfg) / 10_000.0),
            places=9,
        )

    def test_exit_never_rests_at_the_entry_level(self) -> None:
        # The regression guard for the zero-spread bug: a round trip must never
        # realize zero gross while paying two fees.
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=2, notional_per_rung_usd=12.0)
        rows = flat(90.0, 2) + [
            (90.0, 90.0, 60.0, 60.0),
            (60.0, 90.0, 60.0, 90.0),
        ]
        res = run_grid_backtest(cfg, bars(rows), initial_capital=1_000.0, costs=FREE)
        self.assertEqual(res.round_trips, 1)
        self.assertGreater(res.gross_captured_usd, 0.0)
        sells = [t for t in res.trades if t.side == SIDE_SELL and t.reason == "grid_exit"]
        buys = [t for t in res.trades if t.side == SIDE_BUY]
        self.assertEqual(len(sells), 1)
        self.assertGreater(sells[0].price, buys[0].price)

    def test_an_exit_closes_the_lot_it_was_paired_with(self) -> None:
        # A dip sweeps several bids, so several lots are open when the lowest
        # lot's exit fills. That exit must realize the lot it was paired with: one
        # full rung. Strict FIFO matched it to the oldest lot instead, which was
        # bought a rung ABOVE the exit and booked a loss on a trip that earned its
        # spread (the extension had the identical defect; TASK-348).
        rows = flat(90.0, 2) + [
            (90.0, 90.0, self.levels[3], self.levels[3]),
            (self.levels[3], self.levels[4] + 0.5, self.levels[3], self.levels[4] + 0.5),
        ]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertGreater(res.buys_filled, 1, "a dip should sweep several bids")
        self.assertEqual(res.round_trips, 1)
        first_exit = next(t for t in res.trades if t.reason == "grid_exit")
        self.assertAlmostEqual(
            first_exit.realized_pnl, expected_round_trip_usd(self.cfg, self.levels[3]), places=9
        )
        # Totals still tie out: zero costs means final equity is capital plus
        # realized P&L once everything is closed.
        self.assertAlmostEqual(
            res.metrics.final_equity, 1_000.0 + res.realized_pnl_usd, places=6
        )

    def test_the_residual_after_an_exit_is_the_inventory_actually_held(self) -> None:
        # The misdirection itself. Lots are bought at rungs 5, 4 and 3; rung 3's
        # exit (at rung 4) fills first. The inventory still held is rungs 5 and 4.
        # FIFO would close rung 5 and leave rungs 4 and 3, so the next plan would
        # rest the "rung 4" lot's exit at rung 5... and the true rung-4 lot's exit
        # at rung 5 as well, while rung 3's phantom lot kept an exit at rung 4: a
        # sell at the level the real rung-4 inventory was bought at, zero spread.
        rows = flat(90.0, 2) + [
            (90.0, 90.0, self.levels[3], self.levels[3]),
            (self.levels[3], self.levels[4] + 0.5, self.levels[3], self.levels[4] + 0.5),
        ]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE, close_at_end=False
        )
        held = sorted(lot.level for lot in res.open_lots_at_end)
        self.assertEqual(held, sorted([self.levels[4], self.levels[5]]))

    def test_costs_reduce_realized_below_gross(self) -> None:
        entry = self.levels[3]
        rows = flat(90.0, 2) + [
            (90.0, 90.0, entry, entry),
            (entry, self.levels[4] + 0.5, entry, self.levels[4] + 0.5),
        ]
        costed = run_grid_backtest(
            self.cfg,
            bars(rows),
            initial_capital=1_000.0,
            costs=CostConfig(fee_bps=6.0, slippage_bps=2.0),
        )
        self.assertEqual(costed.round_trips, 1)
        self.assertGreater(costed.fees_paid_usd, 0.0)
        self.assertGreater(costed.slippage_paid_usd, 0.0)
        self.assertLess(costed.realized_pnl_usd, costed.gross_captured_usd)

    def test_the_book_reconciles_at_non_zero_cost(self) -> None:
        # The regression guard for a double-counted slippage leg. Every other
        # reconciliation test runs at zero cost, where a double count is
        # invisible; this one fails if either leg's slippage is netted inside
        # gross AND subtracted again as an explicit cost.
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=2, notional_per_rung_usd=12.0)
        rows = flat(90.0, 2) + [
            (90.0, 90.0, 60.0, 60.0),
            (60.0, 90.0, 60.0, 90.0),
        ]
        for slippage_bps in (2.0, 50.0, 300.0):
            res = run_grid_backtest(
                cfg,
                bars(rows),
                initial_capital=1_000.0,
                costs=CostConfig(fee_bps=6.0, slippage_bps=slippage_bps),
            )
            self.assertEqual(res.round_trips, 1)
            self.assertAlmostEqual(
                res.metrics.final_equity,
                1_000.0 + res.realized_pnl_usd,
                places=9,
                msg=f"book must reconcile at {slippage_bps} bps slippage",
            )
            # Gross is the rung spread and must not move with slippage at all;
            # only realized should shrink as costs rise.
            self.assertAlmostEqual(
                res.gross_captured_usd,
                expected_round_trip_usd(cfg, 60.0),
                places=9,
                msg="gross is measured level-to-level, before costs",
            )
            self.assertLess(res.realized_pnl_usd, res.gross_captured_usd)

    def test_carry_is_charged_on_held_inventory(self) -> None:
        entry = self.levels[3]
        rows = flat(90.0, 2) + [(90.0, 90.0, entry, entry)] + flat(entry, 5)
        held = run_grid_backtest(
            self.cfg,
            bars(rows),
            initial_capital=1_000.0,
            costs=FREE,
            carry_bps_per_hour=1.6,
        )
        free = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertGreater(held.carry_paid_usd, 0.0)
        self.assertEqual(free.carry_paid_usd, 0.0)
        self.assertLess(held.metrics.final_equity, free.metrics.final_equity)


class TestNoLookahead(unittest.TestCase):
    """A grid backtest's easiest lie is the same-bar round trip."""

    def setUp(self) -> None:
        self.cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        self.levels = grid_levels(self.cfg)

    def test_no_fill_on_the_very_first_bar(self) -> None:
        # Nothing is resting before the first close, so a bar that sweeps the
        # whole ladder on bar 0 must fill nothing at all.
        res = run_grid_backtest(
            self.cfg,
            bars([(90.0, 95.0, 55.0, 60.0)]),
            initial_capital=1_000.0,
            costs=FREE,
        )
        self.assertEqual(res.buys_filled, 0)
        self.assertEqual(res.round_trips, 0)

    def test_one_bar_cannot_hold_both_legs_of_a_round_trip(self) -> None:
        entry = self.levels[3]
        # Bar 2 spans from below the entry to above its paired exit. A path-blind
        # simulator would book a free round trip here; this one must book only
        # the entry, because the exit does not exist until that bar's close.
        # The close stays inside [low, high] — a bar that closes outside its own
        # range is malformed data and is refused up front.
        rows = flat(90.0, 2) + [(90.0, 90.0, entry - 1.0, self.levels[5])]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertGreater(res.buys_filled, 0)
        self.assertEqual(res.round_trips, 0)

    def test_a_touch_one_bar_before_the_plan_does_not_fill(self) -> None:
        # Bar 1 touches a level while the ladder was planned from bar 0's close,
        # so that IS fillable; bar 0's own touch is not. Assert the boundary by
        # confirming the first fill's bar index is never 0.
        rows = [(90.0, 90.0, 60.0, 90.0)] + flat(90.0, 1) + [(90.0, 90.0, 60.0, 90.0)]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        fills = [t for t in res.trades if t.side == SIDE_BUY]
        self.assertTrue(fills)
        self.assertTrue(all(t.bar_index > 0 for t in fills))


class TestFailureModes(unittest.TestCase):
    """A grid is short volatility; the losing cases have to be visible."""

    def setUp(self) -> None:
        self.cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        self.levels = grid_levels(self.cfg)

    def test_one_way_downtrend_fills_every_bid_and_loses(self) -> None:
        # The characteristic grid failure: maximum exposure at the worst moment.
        rows = flat(90.0, 2)
        for level in reversed(self.levels):
            rows.append((level, level, level, level))
        rows.append((50.0, 50.0, 50.0, 50.0))
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertGreater(res.buys_filled, 0)
        self.assertEqual(res.round_trips, 0)
        self.assertLess(res.metrics.final_equity, 1_000.0)
        self.assertGreater(res.bars_below_grid, 0)

    def test_forced_exit_is_not_counted_as_a_round_trip(self) -> None:
        rows = flat(90.0, 2) + [(90.0, 90.0, self.levels[0], self.levels[0])]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertGreater(res.forced_exit_qty, 0.0)
        self.assertEqual(res.round_trips, 0)
        self.assertTrue(
            any(t.reason == "grid_forced_exit" for t in res.trades),
            "leftover inventory must be closed explicitly, not dropped",
        )

    def test_oscillation_beats_the_same_move_one_way(self) -> None:
        entry = self.levels[3]
        exit_level = self.levels[4]
        down = flat(90.0, 2) + [(90.0, 90.0, entry, entry)]
        osc = down + [(entry, exit_level + 0.5, entry, exit_level + 0.5)]
        one_way = down + [(entry, entry, entry, entry)]
        a = run_grid_backtest(self.cfg, bars(osc), initial_capital=1_000.0, costs=FREE)
        b = run_grid_backtest(
            self.cfg, bars(one_way), initial_capital=1_000.0, costs=FREE
        )
        self.assertEqual(a.round_trips, 1)
        self.assertEqual(b.round_trips, 0)
        self.assertGreater(a.realized_pnl_usd, b.realized_pnl_usd)

    def test_insufficient_cash_skips_a_rung_rather_than_overdrawing(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=100.0)
        rows = flat(90.0, 2) + [(90.0, 90.0, 60.0, 60.0)] + flat(60.0, 1)
        res = run_grid_backtest(cfg, bars(rows), initial_capital=150.0, costs=FREE)
        self.assertGreater(res.skipped.get("insufficient-cash", 0), 0)
        self.assertTrue(np.all(res.equity >= 0.0))
        self.assertLessEqual(res.buys_filled, 2)

    def test_a_rung_below_the_venue_minimum_is_never_placed(self) -> None:
        cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=5.0)
        rows = flat(90.0, 2) + [(90.0, 90.0, 60.0, 60.0)]
        res = run_grid_backtest(cfg, bars(rows), initial_capital=1_000.0, costs=FREE)
        self.assertEqual(res.orders_placed, 0)
        self.assertEqual(res.buys_filled, 0)
        self.assertGreater(res.skipped.get("entry-below-venue-minimum", 0), 0)

    def test_price_above_the_ladder_rests_no_bids(self) -> None:
        rows = flat(200.0, 3)
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        self.assertEqual(res.buys_filled, 0)
        self.assertEqual(res.bars_above_grid, 3)


class TestAccounting(unittest.TestCase):
    """FIFO realization and the book identity."""

    def setUp(self) -> None:
        self.cfg = GridConfig(lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0)
        self.levels = grid_levels(self.cfg)

    def test_an_unpaired_sell_matches_the_oldest_lot_first(self) -> None:
        # No `closes` (the end-of-run forced exit, or a link whose lot is gone)
        # falls back to FIFO. A falling bar fills the highest bid first, so the
        # oldest lot is the most expensive; picking a cheaper one would inflate
        # the realized figure.
        book = _GridBook(1_000.0, FREE)
        book.buy(self.levels[4], 0.1, 1, 1)
        book.buy(self.levels[2], 0.1, 2, 2)
        realized, matched = book.sell(self.levels[5], 0.1, 3, 3, reason="grid_exit")
        self.assertAlmostEqual(matched, 0.1)
        self.assertAlmostEqual(realized, (self.levels[5] - self.levels[4]) * 0.1, places=12)
        self.assertEqual([lot.level for lot in book.lots], [self.levels[2]])

    def test_a_paired_sell_closes_its_own_lots_before_falling_back_to_fifo(self) -> None:
        book = _GridBook(1_000.0, FREE)
        book.buy(self.levels[4], 0.1, 1, 1)  # oldest
        book.buy(self.levels[2], 0.1, 2, 2)
        book.buy(self.levels[3], 0.1, 3, 3)
        # Linked to rung 2 (0.1) and rung 3 (0.05); fill is 0.2, so 0.05 is left
        # for FIFO, which takes the oldest (rung 4).
        realized, matched = book.sell(
            self.levels[5], 0.2, 4, 4, reason="grid_exit",
            closes=((self.levels[2], 0.1), (self.levels[3], 0.05)),
        )
        self.assertAlmostEqual(matched, 0.2)
        expected = (
            (self.levels[5] - self.levels[2]) * 0.1
            + (self.levels[5] - self.levels[3]) * 0.05
            + (self.levels[5] - self.levels[4]) * 0.05
        )
        self.assertAlmostEqual(realized, expected, places=12)
        left = {lot.level: round(lot.qty, 12) for lot in book.lots}
        self.assertEqual(left, {self.levels[4]: 0.05, self.levels[3]: 0.05})

    def test_equity_equals_cash_plus_inventory_at_every_bar(self) -> None:
        rows = flat(90.0, 2) + [
            (90.0, 90.0, self.levels[2], self.levels[2]),
            (self.levels[2], self.levels[4], self.levels[2], self.levels[3]),
            (self.levels[3], self.levels[5], self.levels[3], self.levels[5]),
        ]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        # With zero costs, no money is created or destroyed beyond price P&L:
        # final equity must equal initial capital plus realized P&L once all
        # inventory is closed out at the end.
        self.assertAlmostEqual(
            res.metrics.final_equity, 1_000.0 + res.realized_pnl_usd, places=6
        )
        self.assertTrue(np.all(np.isfinite(res.equity)))

    def test_an_entry_is_not_recorded_as_a_losing_trade(self) -> None:
        rows = flat(90.0, 2) + [(90.0, 90.0, self.levels[3], self.levels[3])]
        res = run_grid_backtest(
            self.cfg,
            bars(rows),
            initial_capital=1_000.0,
            costs=CostConfig(fee_bps=6.0, slippage_bps=2.0),
        )
        entries = [t for t in res.trades if t.reason == "grid_entry"]
        self.assertTrue(entries)
        for t in entries:
            self.assertEqual(t.realized_pnl, 0.0)
            self.assertGreater(t.fee, 0.0)

    def test_baseline_is_reported_alongside_the_grid(self) -> None:
        rows = flat(90.0, 2) + [(90.0, 90.0, 60.0, 60.0)] + flat(60.0, 2)
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        # Holding through a 33% fall must lose; the comparison is only meaningful
        # if the baseline actually tracks the asset.
        self.assertLess(res.baseline_metrics.total_return, 0.0)
        self.assertEqual(len(res.baseline_equity), len(res.equity))

    def test_empty_series_is_refused(self) -> None:
        with self.assertRaises(ValueError):
            run_grid_backtest(self.cfg, bars([]), initial_capital=1_000.0)

    def test_summary_lines_render(self) -> None:
        rows = flat(90.0, 2) + [(90.0, 90.0, 60.0, 60.0)]
        res = run_grid_backtest(
            self.cfg, bars(rows), initial_capital=1_000.0, costs=FREE
        )
        lines = res.summary_lines()
        self.assertTrue(any("rung width" in ln for ln in lines))
        self.assertTrue(any("hold" in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()

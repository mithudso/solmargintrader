from __future__ import annotations

import unittest

from research.rs_zigzag import Bar, _patterns, pivot_events, signals


def bars_for_hours(hour_specs: list[tuple[float, float, float, float]]) -> list[Bar]:
    """Four consistent 15-minute bars per supplied hourly OHLC tuple."""
    bars = []
    for hour, (op, high, low, close) in enumerate(hour_specs):
        bars.extend([
            Bar(hour*3600, op, max(op, (op+close)/2), min(op, (op+close)/2), (op+close)/2),
            Bar(hour*3600+900, (op+close)/2, high, min((op+close)/2, close), close),
            Bar(hour*3600+1800, close, max(close, op), low, close),
            Bar(hour*3600+2700, close, max(close, op), min(close, op), close),
        ])
    return bars


class ZigZagResearchTests(unittest.TestCase):
    def test_confirmed_pivots_and_signals_are_prefix_invariant(self):
        bars = bars_for_hours([(10, 12, 8, 9), (9, 13, 8, 12),
                               (12, 15, 9, 10), (10, 14, 8, 13),
                               (13, 16, 10, 11), (11, 15, 9, 14)])
        full_pivots = pivot_events(bars, 900, 'confirmed')
        full_signals = signals(bars, 900, 'confirmed')
        for end in range(1, len(bars)+1):
            self.assertEqual(pivot_events(bars[:end], 900, 'confirmed'), full_pivots[:end])
            self.assertEqual(signals(bars[:end], 900, 'confirmed'), full_signals[:end])

    def test_legacy_reveals_future_hour_at_first_child(self):
        bars = bars_for_hours([(10, 12, 8, 9), (9, 13, 8, 12),
                               (12, 15, 9, 10), (10, 14, 8, 13)])
        first_child = 8
        full = pivot_events(bars, 900, 'legacy')
        prefix = pivot_events(bars[:first_child+1], 900, 'legacy')
        self.assertEqual(full[first_child], 15)
        self.assertIsNone(prefix[first_child])
        self.assertNotEqual(full[first_child], prefix[first_child])

    def test_confirmed_moves_event_one_hour_later(self):
        bars = bars_for_hours([(10, 12, 8, 9), (9, 13, 8, 12),
                               (12, 15, 9, 10), (10, 14, 8, 13)])
        legacy, confirmed = pivot_events(bars, 900, 'legacy'), pivot_events(bars, 900, 'confirmed')
        self.assertEqual(legacy[8], 15)
        self.assertEqual(confirmed[12], 15)
        self.assertNotEqual(confirmed[8], legacy[8])

    def test_zero_xa_does_not_hide_abcd_that_does_not_use_xa(self):
        self.assertTrue(_patterns(10, 10, 14, 12, 15))
        self.assertFalse(_patterns(10, 10, 10, 10, 10))

    def test_ten_minute_projection_is_prefix_invariant(self):
        specs = [(10, 12, 8, 9), (9, 13, 8, 12), (12, 15, 9, 10), (10, 14, 8, 13)]
        bars = []
        for hour, (op, high, low, close) in enumerate(specs):
            for j in range(6):
                bars.append(Bar(hour*3600+j*600, op if j == 0 else close,
                                high if j == 1 else max(op, close),
                                low if j == 2 else min(op, close), close))
        full = pivot_events(bars, 600, 'confirmed')
        for end in range(1, len(bars)+1):
            self.assertEqual(pivot_events(bars[:end], 600, 'confirmed'), full[:end])
        self.assertEqual(pivot_events(bars, 600, 'legacy')[12], 15)
        self.assertEqual(full[18], 15)

    def test_missing_or_invalid_bars_fail_closed(self):
        bars = bars_for_hours([(10, 12, 8, 9), (9, 13, 8, 12)])
        with self.assertRaisesRegex(ValueError, 'contiguous'):
            signals(bars[:2]+bars[3:], 900)
        with self.assertRaisesRegex(ValueError, 'invalid'):
            pivot_events([Bar(0, 10, 9, 8, 10)], 900)
        with self.assertRaisesRegex(ValueError, 'step'):
            pivot_events(bars, 300)


class ExecutionSensitivityTests(unittest.TestCase):
    def test_next_open_sizing_costs_and_initial_margin_rejection(self):
        from research.rs_zigzag import ExecutionAssumptions, simulate_decisions
        bars = [Bar(0, 10, 11, 9, 10), Bar(900, 11, 12, 10, 11),
                Bar(1800, 12, 13, 11, 12)]
        blank = {"buy_entry": False, "buy_close": False, "sell_entry": False, "sell_close": False}
        actions = [{**blank, "buy_entry": True}, {**blank, "buy_close": True}, blank]
        free = simulate_decisions(bars, 900, actions, ExecutionAssumptions(quantity=2))
        self.assertEqual(free['final_equity'], 100_002)
        self.assertEqual(free['closed_trades'], 1)
        costed = simulate_decisions(bars, 900, actions, ExecutionAssumptions(quantity=2, fee_bps=100))
        self.assertAlmostEqual(costed['fees'], .46)
        self.assertAlmostEqual(costed['final_equity'], 100_001.54)
        denied = simulate_decisions(bars, 900, actions, ExecutionAssumptions(quantity=10_000, margin_fraction=1))
        self.assertEqual(denied['rejected_entries'], 1)
        self.assertEqual(denied['final_equity'], 100_000)

    def test_same_side_does_not_pyramid_and_open_position_is_marked(self):
        from research.rs_zigzag import ExecutionAssumptions, simulate_decisions
        bars = [Bar(i*900, 10, 11, 9, 10) for i in range(3)]
        flags = {"buy_entry": True, "buy_close": False, "sell_entry": False, "sell_close": False}
        result = simulate_decisions(bars, 900, [flags]*3, ExecutionAssumptions(quantity=3))
        self.assertEqual(result['open_quantity'], 3)
        self.assertEqual(result['closed_trades'], 0)

    def test_close_signal_without_open_position_does_not_close_new_entry(self):
        from research.rs_zigzag import ExecutionAssumptions, simulate_decisions
        bars = [Bar(i*900, 10, 11, 9, 10) for i in range(2)]
        flags = {"buy_entry": True, "buy_close": True, "sell_entry": False, "sell_close": False}
        result = simulate_decisions(bars, 900, [flags, flags], ExecutionAssumptions(quantity=3))
        self.assertEqual(result['open_quantity'], 3)
        self.assertEqual(result['closed_trades'], 0)


if __name__ == '__main__':
    unittest.main()

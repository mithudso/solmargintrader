"""Unknown scorecard inputs stay unavailable and enabled gates fail closed."""
import unittest
import numpy as np
from backtester.core import scorecard as sc
from backtester.tests.test_scorecard import synthetic, only


class ScorecardInputTests(unittest.TestCase):
    def test_invalid_live_values_cannot_become_finite_saturated_votes(self):
        bars = synthetic(60)
        for cid, key in [('book_imbalance', 'book_imbalance'), ('premium', 'premium')]:
            for value in (float('nan'), float('inf'), -float('inf'), True):
                with self.subTest(component=cid, value=value):
                    result = sc.BY_ID[cid].fn(bars, sc.BY_ID[cid].defaults(), {'live': {key: value}})
                    self.assertTrue(np.isnan(result).all())

    def test_funding_invalid_or_conflicting_alignment_cannot_saturate_into_vote(self):
        bars = synthetic(60)
        cfg = only(funding=1)
        for times, rates in [([bars.ts[0]], [float('inf')]),
                             ([bars.ts[0], bars.ts[0]], [.001, .002]),
                             ([float('nan')], [.001])]:
            with self.subTest(times=times, rates=rates):
                result = sc.evaluate(bars, cfg, {'funding': {'ts': times, 'rate': rates}})
                self.assertFalse(result.indication.any())
                self.assertIn('funding', result.errors)

    def test_missing_news_read_is_blocking_but_successful_empty_read_is_known(self):
        bars = synthetic(60)
        gate = sc.BY_ID['gate_news']
        self.assertTrue(gate.fn(bars, gate.defaults(), {})[-1])
        self.assertFalse(gate.fn(bars, gate.defaults(), {'live': {'news_hits': []}})[-1])

    def test_invalid_event_timestamp_blocks_instead_of_silently_disabling_gate(self):
        result = sc.evaluate(synthetic(60), only(ema_cross=1, gate_events=1), {'events': [{'ts': float('nan')}]})
        self.assertTrue(result.blocked.all())
        self.assertIn('gate_events', result.errors)

    def test_false_string_and_nonobject_sections_are_not_coerced_into_active_defaults(self):
        for value in ({'components': {'rsi': {'enabled': 'false'}}}, {'components': []},
                      {'aggregate': []}, {'execution': []}, {'components': {'rsi': {'params': []}}}):
            with self.subTest(config=value), self.assertRaises(sc.ScorecardError):
                sc.normalise_config(value)

    def test_empty_valid_bars_produce_an_empty_unavailable_evaluation(self):
        bars = sc.Bars(*[np.array([]) for _ in range(6)])
        result = sc.evaluate(bars)
        self.assertEqual(result.indication.size, 0)
        self.assertEqual(sc.forecast_stats([result]), {'bars': 0, 'calls': 0})

    def test_invalid_ohlcv_never_becomes_a_directional_evaluation(self):
        bars = synthetic(10)
        for field, value in [('close', 0), ('volume', -1), ('high', 0)]:
            parts = {name: getattr(bars, name).copy() for name in ('ts', 'open', 'high', 'low', 'close', 'volume')}
            parts[field][3] = value
            with self.subTest(field=field), self.assertRaises(sc.ScorecardError):
                sc.Bars(**parts)


if __name__ == '__main__':
    unittest.main()

"""Continuation must retain causal policy state and actual intrabar data identity."""
import copy
import unittest
from typing import ClassVar

import numpy as np

from backtester.core.engine import EngineConfig, rebind_signal_state, run_backtest
from backtester.core.types import BarWindow, IntrabarLayer
from backtester.core.zec_ensemble import ZecEnsemble


def bars(count, step=3600):
    price = 100 + np.sin(np.arange(count) * .7)
    return {"ts": 1_800_000_000 + np.arange(count) * step,
            **{name: price.copy() for name in ("open", "high", "low", "close")},
            "volume": np.ones(count)}


def cut(arrays, start, end):
    return {key: value[start:end] for key, value in arrays.items()}


class Holding:
    name = "intrabar-checkpoint-control"
    params: ClassVar[dict] = {}

    def warmup_bars(self):
        return 0

    def on_bar(self, history):
        return 1.0

    def checkpoint_state(self):
        return {}

    def restore_state(self, state):
        pass


class ContinuationIdentityTests(unittest.TestCase):
    def test_flat_policy_adoption_emits_a_resumable_current_binding(self):
        class Flat(Holding):
            def on_bar(self, history):
                return 0.0

        arrays = bars(6)
        config = EngineConfig(interval="1h")
        prefix = run_backtest(Flat(), cut(arrays, 0, 3), config, close_at_end=False)
        rebound = rebind_signal_state(prefix.continuation, Holding(), config)
        rest = run_backtest(Holding(), cut(arrays, 3, 6), config,
                            continuation=rebound, close_at_end=False)
        self.assertEqual(rest.continuation["binding"], rebound["binding"])
        self.assertTrue(rest.trades)

    def test_equivalent_reconstructed_intrabar_config_continues(self):
        arrays, fine = bars(6), bars(360, 60)
        config = EngineConfig(interval="1h", intrabar=(IntrabarLayer("1m", fine),))
        whole = run_backtest(Holding(), arrays, config, close_at_end=False)
        prefix = run_backtest(Holding(), cut(arrays, 0, 3), config, close_at_end=False)
        equivalent = EngineConfig(interval="1h", intrabar=(IntrabarLayer("1m", copy.deepcopy(fine)),))
        rest = run_backtest(Holding(), cut(arrays, 3, 6), equivalent,
                            continuation=prefix.continuation, close_at_end=False)
        np.testing.assert_array_equal(np.r_[prefix.equity, rest.equity], whole.equity)
        self.assertEqual(rest.continuation, whole.continuation)

    def test_changed_intrabar_bytes_refuse_even_outside_current_segment(self):
        arrays, fine = bars(6), bars(360, 60)
        config = EngineConfig(interval="1h", intrabar=(IntrabarLayer("1m", fine),))
        prefix = run_backtest(Holding(), cut(arrays, 0, 3), config, close_at_end=False)
        changed = copy.deepcopy(fine)
        for name in ("open", "high", "low", "close"):
            changed[name][-1] += 1
        config.intrabar = (IntrabarLayer("1m", changed),)
        with self.assertRaisesRegex(ValueError, "configuration changed"):
            run_backtest(Holding(), cut(arrays, 3, 6), config,
                         continuation=prefix.continuation, close_at_end=False)

    def test_ensemble_resume_matches_whole_for_recursive_and_stateful_members(self):
        arrays = bars(150)
        for name in ("buy_and_hold", "rsi", "macd", "obv_trend"):
            with self.subTest(strategy=name):
                policy = {"interval": "1h", "mode": "single", "members": [{"strategy": name}]}
                config = EngineConfig(interval="1h")
                whole = run_backtest(ZecEnsemble(policy), arrays, config, close_at_end=False)
                state, pieces = None, []
                for start, end in ((0, 4), (4, 45), (45, 90), (90, 150)):
                    part = run_backtest(ZecEnsemble(policy), cut(arrays, start, end), config,
                                        continuation=state, close_at_end=False)
                    state = part.continuation
                    pieces.append(part.equity)
                np.testing.assert_array_equal(np.concatenate(pieces), whole.equity)
                self.assertEqual(state, whole.continuation)

    def test_direct_policy_changed_history_origin_still_refuses(self):
        arrays = bars(8)
        policy = ZecEnsemble({"interval": "1h", "mode": "single",
                              "members": [{"strategy": "buy_and_hold"}]})
        policy.on_bar(BarWindow(*(arrays[k] for k in ("ts", "open", "high", "low", "close", "volume")), 3))
        with self.assertRaisesRegex(ValueError, "history origin changed"):
            other = cut(arrays, 1, 8)
            policy.on_bar(BarWindow(*(other[k] for k in ("ts", "open", "high", "low", "close", "volume")), 3))

    def test_long_ensemble_resume_keeps_bounded_history_and_original_origin(self):
        policy = {"interval": "1h", "mode": "single", "members": [{"strategy": "buy_and_hold"}]}
        limit = ZecEnsemble(policy).continuation_history_bars()
        arrays = bars(limit + 10)
        config = EngineConfig(interval="1h")
        whole = run_backtest(ZecEnsemble(policy), arrays, config, close_at_end=False)
        prefix = run_backtest(ZecEnsemble(policy), cut(arrays, 0, limit + 2), config, close_at_end=False)
        self.assertEqual(len(prefix.continuation["tail"]["ts"]), limit)
        self.assertGreater(prefix.continuation["tail"]["ts"][0], int(arrays["ts"][0]))
        rest = run_backtest(ZecEnsemble(policy), cut(arrays, limit + 2, len(arrays["ts"])), config,
                            continuation=prefix.continuation, close_at_end=False)
        np.testing.assert_array_equal(np.r_[prefix.equity, rest.equity], whole.equity)
        self.assertEqual(rest.continuation, whole.continuation)
        changed = copy.deepcopy(prefix.continuation)
        changed["tail"]["close"][-1] += .1
        with self.assertRaisesRegex(ValueError, "restored history changed"):
            run_backtest(ZecEnsemble(policy), cut(arrays, limit + 2, len(arrays["ts"])), config,
                         continuation=changed, close_at_end=False)

    def test_binding_is_order_independent_and_refuses_unsupported_values(self):
        from backtester.core.continuation import configuration_binding

        self.assertEqual(configuration_binding({"a": 1, "b": [2]}),
                         configuration_binding({"b": [2], "a": 1}))
        self.assertEqual(configuration_binding(np.array([1., 2.], dtype=">f8")),
                         configuration_binding(np.array([1., 2.], dtype="<f8")))
        for value in (float("nan"), object(), np.array([float("inf")]), {1: "unsafe"}):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                configuration_binding(value)


if __name__ == "__main__":
    unittest.main()

"""Policy normalization and rejected checkpoint restore preserve exposure meaning."""
import copy
import unittest
from backtester.core.zec_ensemble import ZecEnsemble, canonical_config


def config():
    return {'interval': '1h', 'mode': 'weighted',
            'members': [{'strategy': 'buy_and_hold'}, {'strategy': 'rsi'}],
            'weights': [1e308, 1e308]}


class EnsembleStateTests(unittest.TestCase):
    def test_large_finite_weights_keep_their_proportions(self):
        normalized = canonical_config(config())
        self.assertEqual(normalized['weights'], [.5, .5])

    def test_normalized_policy_identity_is_idempotent(self):
        from backtester.core.zec_ensemble import candidate_id
        for weights in ([1.0794672386852124e133, 2.653250141551182e-173, 7.897321782975387e124],
                        [7.992085110996004e87, 3.471643597278483e231, 1.6220396285417145e229],
                        [3.1114508607663943e81, 481524520444.7745, 4.972296787917932e77]):
            value = config()
            value['members'].append({'strategy': 'macd'})
            value['weights'] = weights
            with self.subTest(weights=weights):
                normalized = canonical_config(value)
                self.assertEqual(candidate_id(value), candidate_id(normalized))
                self.assertEqual(canonical_config(normalized), normalized)

    def test_rejected_restore_leaves_all_current_policy_state_unchanged(self):
        value = config()
        value['weights'] = [1, 1]
        policy = ZecEnsemble(value)
        before = policy.checkpoint_state()
        invalid = copy.deepcopy(before)
        invalid['last_ts'] = 123
        invalid['origin_ts'] = 100
        invalid['persistence']['last'] = 1.
        invalid['members'] = {}
        with self.assertRaises(ValueError):
            policy.restore_state(invalid)
        self.assertEqual(policy.checkpoint_state(), before)


if __name__ == '__main__':
    unittest.main()

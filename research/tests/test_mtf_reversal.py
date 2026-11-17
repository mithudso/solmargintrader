import copy
import unittest

from research.mtf_reversal import (
    classify,
    context_at,
    frame_index,
    hypothesis,
    live_context,
    metrics,
    score_context,
    select,
)


def rows(n=1200):
    return [
        [
            i * 60,
            100 + i * 0.01,
            100.02 + i * 0.01,
            99.99 + i * 0.01,
            100.01 + i * 0.01,
            0,
        ]
        for i in range(n)
    ]


def model():
    return {
        "alpha": 20,
        "min_cell_n": 20,
        "min_components": 2,
        "base_models": {
            "5": {
                "n": 100,
                "down": 50,
                "contexts": {
                    str(m): {
                        "cap": {"n": 20, "down": 0},
                        "bowl": {"n": 20, "down": 20},
                        "tiny": {"n": 2, "down": 2},
                    }
                    for m in (5, 10, 15, 20)
                },
            }
        },
    }


def context(shape):
    return {
        "at": 0,
        "frames": {
            str(m): {"shape": shape, "pair": "UU", "closed_at": 0}
            for m in (5, 10, 15, 20)
        },
    }


class MTFTests(unittest.TestCase):
    def test_asof_and_prefix_causality(self):
        full = rows()
        at = 1195 * 60
        a = live_context(full, at)
        b = live_context(full[:1195], at)
        self.assertEqual(a, b)
        self.assertEqual(a["frames"]["20"]["closed_at"], 1180 * 60)
        self.assertLessEqual(a["frames"]["20"]["closed_at"], at)

    def test_gap_resets_and_stale(self):
        full = rows()
        index = frame_index(full[:1000] + full[1020:])
        self.assertEqual(
            context_at(index, 1010 * 60)["frames"]["5"]["shape"], "unknown"
        )
        self.assertEqual(
            context_at(index, 1040 * 60)["frames"]["5"]["shape"], "unknown"
        )

    def test_support_and_correlated_average(self):
        self.assertEqual(
            score_context(model(), 5, context("tiny"))["status"], "insufficient"
        )
        cap = score_context(model(), 5, context("cap"))
        bowl = score_context(model(), 5, context("bowl"))
        self.assertGreater(cap["score_down"], 0)
        self.assertLess(bowl["score_down"], 1)
        self.assertAlmostEqual(cap["score_down"], 1 / 3)
        self.assertEqual(classify(cap["score_down"], 0.55), "UP")
        self.assertEqual(classify(bowl["score_down"], 0.55), "DOWN")
        self.assertIsNone(classify(0.51, 0.525))
        self.assertIsNone(classify(0.5, 0.5))

    def test_literal_hints_and_conflicts(self):
        ctx = context("range")
        ctx["frames"]["20"]["shape"] = "bowl"
        self.assertEqual(hypothesis(ctx), "DOWN")
        ctx["frames"]["5"]["shape"] = "cap"
        self.assertIsNone(hypothesis(ctx))
        ctx["frames"]["20"]["shape"] = "range"
        self.assertEqual(hypothesis(ctx), "UP")

    def test_correct_but_liquidated(self):
        es = [{"target_color": "DOWN", "target": [0, 100, 100.098, 99, 99.5, 0]}]
        report = metrics(es, ["DOWN"])
        self.assertEqual(report["hits"], 1)
        self.assertEqual(report["joint_by_bps"]["9.8"], 0)
        self.assertEqual(report["crossed_by_bps"]["9.8"], 1)

    def test_selection_ignores_test_split(self):
        def variant(name, lower):
            return {
                "id": name,
                "mode": "all",
                "minutes": 5,
                "threshold": 0.5,
                "splits": {
                    "train": {"strategy": {"n": 40}},
                    "validation": {
                        "strategy": {"n": 20, "joint_wilson_9.8": [lower, 1]}
                    },
                    "test": {"strategy": {"n": 10, "hits": 10}},
                },
            }

        variants = [variant("a", 0.1), variant("b", 0.2)]
        altered = copy.deepcopy(variants)
        altered[0]["splits"]["test"]["strategy"]["hits"] = 0
        altered[1]["splits"]["test"]["strategy"]["hits"] = 0
        self.assertEqual(select(variants), select(altered))


if __name__ == "__main__":
    unittest.main()

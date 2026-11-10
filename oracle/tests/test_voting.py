import unittest

from oracle.voting import Vote, aggregate


class VotingTests(unittest.TestCase):
    def vote(self, name="a", direction=1, hits=60, resolved=100, issued=1, expires=10):
        return Vote(name, direction, hits, resolved, issued, expires)

    def result(self, votes):
        return aggregate(votes, now=5, minimum_resolved=10)

    def test_threshold_exclusion_and_recovery(self):
        self.assertEqual(self.result([self.vote(hits=59)])["status"], "unavailable")
        self.assertEqual(self.result([self.vote(hits=60)])["signal"], "Strong Buy")

    def test_bonus_uses_hits_not_resolutions(self):
        first = self.result([self.vote(hits=100, resolved=110)])["included"][0]["weight"]
        second = self.result([self.vote(hits=101, resolved=110)])["included"][0]["weight"]
        self.assertAlmostEqual(first, 100 / 110)
        self.assertAlmostEqual(second, 202 / 110)

    def test_flat_and_opposing_votes(self):
        result = self.result([self.vote(), self.vote("b", -1), self.vote("c", 0)])
        self.assertEqual(result["signal"], "Flat")
        self.assertEqual(result["balance_percent"], 0)

    def test_future_expired_and_insufficient_abstain(self):
        votes = [self.vote(issued=6, expires=7), self.vote("b", expires=5),
                 self.vote("c", hits=1, resolved=1)]
        self.assertEqual(self.result(votes)["status"], "unavailable")

    def test_duplicate_and_invalid_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            self.result([self.vote(), self.vote()])
        with self.assertRaises(ValueError):
            self.result([self.vote(hits=101, resolved=100)])

    def test_signal_boundaries(self):
        for direction, opposing, expected in ((1, 2, "Buy"), (1, 1, "Strong Buy"),
                                              (-1, 2, "Sell"), (-1, 1, "Strong Sell")):
            with self.subTest(expected=expected):
                votes = [self.vote(str(i), -direction if i < opposing else direction,
                                   100, 100) for i in range(5)]
                self.assertEqual(self.result(votes)["signal"], expected)

    def test_nonfinite_clock_and_oversized_roster_refused(self):
        with self.assertRaises(ValueError):
            aggregate([], now=float("nan"), minimum_resolved=1)
        with self.assertRaises(ValueError):
            self.result([self.vote(str(i)) for i in range(15)])


if __name__ == "__main__":
    unittest.main()

import unittest

from research.exit50_report import render_report


def summary():
    return {
        "n": 30,
        "unscored": 0,
        "target_touched": 10,
        "target_filled": 8,
        "liquidated": 4,
        "mean_roe": 0.1,
        "net_micro_sum": 30_000_000,
    }


def result(asset):
    strategy = {
        "id": "confirmed_uu/shape/target_momentum/10",
        "family": "confirmed_uu",
        "filter": "shape",
        "exit": "target_momentum",
        "delay_seconds": 10,
        "overlap_skips": 1,
        "train": summary(),
        "validation": summary(),
        "test": summary(),
    }
    baseline = {
        "id": "confirmed_uu/none/fixed/10",
        "family": "confirmed_uu",
        "filter": "none",
        "exit": "fixed",
        "delay_seconds": 10,
        "overlap_skips": 2,
        "train": summary(),
        "validation": summary(),
        "test": summary(),
    }
    sensitivity = [
        {
            **strategy,
            "id": f"confirmed_uu/shape/{exit_name}/{delay}",
            "exit": exit_name,
            "delay_seconds": delay,
        }
        for exit_name in ("fixed", "second_turn", "target", "target_momentum")
        for delay in (0, 5, 10)
        if (exit_name, delay) != ("target_momentum", 10)
    ]
    pairs = {
        s: {"strategy": summary(), "baseline": summary()}
        for s in ("train", "validation", "test")
    }
    return {
        "asset": asset,
        "model_sha256": "a" * 64,
        "selected": {"id": strategy["id"], "family": "confirmed_uu", "filter": "shape"},
        "candidates": [
            {
                "family": "confirmed_uu",
                "split": split,
                "signal": {"shape_filter": True, "bop_filter": True},
            }
            for split in ("train", "validation", "test")
        ],
        "variants": [strategy, baseline, *sensitivity],
        "selected_paired_comparisons": pairs,
    }


class ReportTests(unittest.TestCase):
    def test_reports_fixed_comparisons_and_sampled_limit(self):
        report, policies = render_report(
            {"BTC": result("BTC"), "ZEC": result("ZEC")},
            "a" * 64,
            {"BTC": "art:btc", "ZEC": "art:zec"},
        )
        self.assertIn("not prove a continuous keeper path", report)
        self.assertIn("same-entry fixed, common proof", report)
        self.assertIn("not a test of an extended second reversal", report)
        self.assertEqual(
            policies["assets"]["BTC"]["selection_status"], "validation-selected"
        )
        self.assertEqual(policies["assets"]["ZEC"]["validation_n"], 30)


if __name__ == "__main__":
    unittest.main()

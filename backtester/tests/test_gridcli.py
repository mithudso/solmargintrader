"""Tests for the ladder-grid CLI.

The CLI is a thin adapter over a tested core, so these tests cover only what
lives in the adapter itself: exit-code mapping, argument rejection, JSON
validity, and the disclaimer. Each one exists because that logic cannot fail
anywhere else.
"""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from backtester.gridcli import DISCLAIMER, main

LADDER = ["--lower", "60", "--upper", "90", "--rungs", "7", "--notional-per-rung", "12"]


def run(argv: list[str]) -> tuple[int, str, str]:
    """Invoke the CLI in-process, capturing streams. Returns (code, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _reject_constant(value: str) -> None:
    """json.loads hook that refuses the non-standard NaN/Infinity tokens."""
    raise AssertionError(f"output is not strict JSON: bare {value} token")


class TestJsonOutput(unittest.TestCase):
    def test_json_is_strictly_parseable(self) -> None:
        # profit_factor is +inf on a run with no losing trade, and json.dumps
        # writes that as a bare `Infinity` token, which no strict parser accepts.
        # A wide ladder on synthetic data is exactly such a run.
        code, out, err = run([*LADDER, "--synthetic", "400", "--capital", "500", "--json"])
        self.assertEqual(code, 0, err)
        payload = json.loads(out, parse_constant=_reject_constant)
        self.assertIn("grid_metrics", payload)
        self.assertIn("buy_and_hold_metrics", payload)
        self.assertEqual(payload["config"]["rungs"], 7)

    def test_levels_json_is_parseable_and_carries_the_ladder(self) -> None:
        code, out, err = run([*LADDER, "--levels", "--json"])
        self.assertEqual(code, 0, err)
        payload = json.loads(out, parse_constant=_reject_constant)
        self.assertEqual(len(payload["levels"]), 7)
        self.assertAlmostEqual(payload["levels"][0], 60.0)
        self.assertAlmostEqual(payload["levels"][-1], 90.0)
        self.assertGreater(payload["capital_requirement_at_upper"]["total_usd"], 0.0)


class TestDisclaimer(unittest.TestCase):
    """A number that leaves this tool without the disclaimer can be pasted anywhere."""

    def test_every_output_shape_carries_it(self) -> None:
        shapes = [
            [*LADDER, "--synthetic", "200", "--capital", "500"],
            [*LADDER, "--synthetic", "200", "--capital", "500", "--json"],
            [*LADDER, "--levels"],
            [*LADDER, "--levels", "--json"],
        ]
        for argv in shapes:
            code, out, err = run(argv)
            self.assertEqual(code, 0, err)
            self.assertIn(
                "NOT investment advice",
                out,
                msg=f"missing disclaimer: {' '.join(argv)}",
            )
        # And the constant is the single source, so no path can drift from it.
        self.assertIn("NOT investment advice", DISCLAIMER)


class TestExitCodes(unittest.TestCase):
    """Usage errors exit 2, runtime failures exit 1. A script cannot tell the
    difference between "you typed it wrong" and "the run failed" otherwise."""

    def test_bad_ladder_geometry_is_a_usage_error(self) -> None:
        for bad in (
            ["--lower", "60", "--upper", "90", "--rungs", "1", "--notional-per-rung", "12"],
            ["--lower", "90", "--upper", "90", "--rungs", "7", "--notional-per-rung", "12"],
            ["--lower", "0", "--upper", "90", "--rungs", "7", "--notional-per-rung", "12"],
            ["--lower", "60", "--upper", "90", "--rungs", "7", "--notional-per-rung", "0"],
        ):
            code, _, err = run(bad)
            self.assertEqual(code, 2, f"{bad} should be a usage error")
            self.assertIn("error:", err)

    def test_out_of_range_run_arguments_are_usage_errors(self) -> None:
        for flag, value in (
            ("--capital", "0"),
            ("--capital", "-5"),
            ("--carry-bps-per-hour", "-1"),
            ("--fee-bps", "-1"),
            ("--slippage-bps", "10000"),
            ("--min-order-usd", "-1"),
            ("--synthetic", "0"),
        ):
            argv = (
                [*LADDER, flag, value]
                if flag == "--synthetic"
                else [*LADDER, flag, value, "--synthetic", "200"]
            )
            code, _, err = run(argv)
            self.assertEqual(code, 2, f"{flag} {value} should be a usage error")
            # Either the flag or its underlying field must be named — some are
            # rejected by GridConfig, which speaks in field names.
            field = flag.lstrip("-").replace("-", "_")
            self.assertTrue(
                flag in err or field in err,
                msg=f"{flag} {value} error must name the offending argument: {err!r}",
            )

    def test_two_data_sources_is_refused_rather_than_one_silently_winning(self) -> None:
        code, _, err = run([*LADDER, "--data", "nonexistent.csv", "--synthetic", "200"])
        self.assertEqual(code, 2)
        self.assertIn("--data", err)

    def test_synthetic_zero_does_not_silently_fall_back_to_a_csv(self) -> None:
        # `if args.synthetic:` treated 0 as absent and loaded data/SOL_1d.csv,
        # turning "no synthetic bars" into a real-data run or a confusing
        # FileNotFoundError.
        code, _, err = run([*LADDER, "--synthetic", "0"])
        self.assertEqual(code, 2)
        self.assertIn("--synthetic", err)
        self.assertNotIn("SOL_1d.csv", err)

    def test_a_missing_data_file_is_a_runtime_error_not_a_usage_error(self) -> None:
        code, _, err = run([*LADDER, "--data", "definitely-not-here.csv"])
        self.assertEqual(code, 1)
        self.assertIn("error:", err)

    def test_no_arguments_prints_help_and_succeeds(self) -> None:
        code, out, _ = run([])
        self.assertEqual(code, 0)
        self.assertIn("--lower", out)

    def test_an_unknown_flag_is_rejected_not_ignored(self) -> None:
        # A silently dropped flag that changes position size is a money bug.
        with self.assertRaises(SystemExit) as ctx:
            run([*LADDER, "--notional-per-rungs", "999"])
        self.assertEqual(ctx.exception.code, 2)


class TestReportedConfigMatchesTheRun(unittest.TestCase):
    def test_json_config_echoes_what_was_asked_for(self) -> None:
        argv = [
            "--lower", "70", "--upper", "110", "--rungs", "5",
            "--notional-per-rung", "20", "--spacing", "arith",
            "--synthetic", "200", "--capital", "800", "--json",
        ]
        code, out, err = run(argv)
        self.assertEqual(code, 0, err)
        payload = json.loads(out, parse_constant=_reject_constant)
        self.assertEqual(payload["config"]["lower"], 70.0)
        self.assertEqual(payload["config"]["upper"], 110.0)
        self.assertEqual(payload["config"]["rungs"], 5)
        self.assertEqual(payload["config"]["spacing"], "arith")
        self.assertEqual(payload["initial_capital"], 800.0)
        self.assertGreater(payload["bar_count"], 0)
        # Arithmetic spacing on 70-110 in 5 rungs is a $10 step, so the first
        # rung's width is 1000 bps; the reported figure must describe the ladder
        # that actually ran, not a default.
        self.assertGreater(payload["rung_width_bps"], 1000.0)


if __name__ == "__main__":
    unittest.main()

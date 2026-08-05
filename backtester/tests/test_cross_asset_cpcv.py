"""The cross-asset CPCV script's pure parts.

No test here loads a price file, runs the engine, or writes anywhere under
`research/results/`. That is not tidiness -- it is what makes these tests
runnable at all, and safe to run:

  * `data/` is gitignored, so a test that opened `data/BTC_1d.csv` would pass on a
    development machine and fail in CI for a reason unrelated to the code. Worse,
    a test that merely *tolerates* a missing price file can go green in CI for the
    wrong reason -- the refusal it asserts arriving from the data check rather than
    from the guard it names. Every test that calls `main` therefore stubs
    `missing_data_files` and asserts the specific refusal text.
  * `research/results/` holds the published evidence, including the one file the
    self-test compares against. A test that drives `main` at the real `OUT` is one
    guard-regression away from having the *test suite* overwrite that evidence, so
    every test that can reach a write redirects `OUT` and `REFERENCE` into a
    temporary directory first. The guards themselves are asserted against the real
    constants through `resolve_output_path`, which never writes.

The expensive halves (`self_test`'s 50-configuration sweep, `run_asset`,
`run_top5`'s real evaluation) stay integration-only and are exercised by the
script's own two gates.

What is worth pinning here is a set of *silent* failures. The script's job is to
re-derive a published number, so its characteristic defect is not a crash but a
verdict printed over a check that did not happen:

  * **The output guard.** `research/results/cpcv_all25_btc_eth_1d.csv` is the only
    independent record of the numbers the self-test compares against. Overwriting
    it from this script would leave the gate comparing the script to itself, and
    `--assets BTC,ETH` derives exactly that filename without anyone typing
    `--out`. The refusal must also fire *before* the sweep, or a refused run still
    costs the whole compute.
  * **The self-test's NaN blindness.** A NaN difference compares False against
    every threshold, and insufficient configurations are written as NaN on
    purpose, so a number-that-became-NaN was the one divergence the gate was
    least able to see while printing PASSED.
  * **The control gate.** `--top5` certifies the composite wiring by reproducing
    SOL's published medians. Its verdict has to survive a partial control (a
    skipna'd aggregate agreed on one row out of five) and has to reach the exit
    code, or no script can check it.
  * **`TOP5_COLUMNS` versus the row dict.** `pd.DataFrame(rows, columns=...)`
    silently emits an all-NaN column for a key that was renamed and silently drops
    one that was never declared. Neither raises, and neither is visible in the
    column *set* -- only in the values, and in a frame built without the column
    list.
  * **Which configuration each labelled row was actually evaluated from.** Label,
    rank and horizon come from the spec while the metrics come from the engine, so
    a row can carry rank 5's label and rank 1's strategy. That produces a
    plausible Sharpe, not an error.
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core.cpcv import CpcvResult  # noqa: E402
from backtester.core.strategies.composite import COMBINE_MODES, Composite  # noqa: E402
from research import cross_asset_cpcv as cac  # noqa: E402
from research.sweep import HORIZONS  # noqa: E402

# Deliberately eight mutually distinct metrics. A fake whose median, quartiles and
# counts collide cannot tell a correct row dict from one that wrote q3 into q1 or
# usable_blocks into n_paths, and those swaps are silent in both the CSV and the
# column set.
SHARPES = (-1.0, 0.5, 2.0, 3.0)     # median 1.25, q1 0.125, q3 2.25, positive 0.75
RETURNS = (0.05, 0.1, 0.2, 0.4)     # median 0.15
TRADES = 37
USABLE = 6
N_PATHS = 15


def cpcv_result(
    sharpes: tuple[float, ...] = SHARPES,
    returns: tuple[float, ...] = RETURNS,
    trades: int = TRADES,
    usable: int = USABLE,
    n_paths: int = N_PATHS,
) -> CpcvResult:
    """A CpcvResult with real derived properties rather than a stub.

    The metrics the row dict reads (`median_sharpe`, `q1_sharpe`, ...) are
    computed properties over `path_sharpes`, so a hand-rolled fake with those as
    plain attributes would test the fake instead of the wiring.
    """
    return CpcvResult(
        label="fake",
        n_groups=8,
        k_test=2,
        n_paths=n_paths,
        path_sharpes=np.array(sharpes, dtype="float64"),
        path_returns=np.array(returns, dtype="float64"),
        block_sharpes=np.array(sharpes, dtype="float64"),
        total_trades=trades,
        usable_blocks=usable,
    )


class PatchMixin(unittest.TestCase):
    """Module-attribute substitution with restoration, matching house style.

    The repo uses no mocking library anywhere, so the pattern is the one in
    `test_universe.py`: replace the module global, put it back afterwards. Doing
    it through `addCleanup` rather than `finally` means a failing assertion still
    restores the module for every later test in the file.
    """

    def patch(self, name: str, value: object) -> None:
        original = getattr(cac, name)
        setattr(cac, name, value)
        self.addCleanup(setattr, cac, name, original)

    def sandbox_results_dir(self) -> Path:
        """Redirect OUT and REFERENCE into a tempdir before driving `main`.

        Without this, the only thing standing between the test suite and the
        published evidence in `research/results/` is the guard the test is trying
        to break. REPO moves with them because the final report line renders the
        destination relative to it.
        """
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # Resolved, because the module's own REPO is resolved and it renders the
        # destination relative to it. On macOS a temp dir is /var/... while its
        # resolved form is /private/var/..., so an unresolved stand-in would make
        # the final report line raise where production never can.
        root = Path(tmp.name).resolve()
        out = root / "results"
        out.mkdir()
        self.patch("REPO", root)
        self.patch("OUT", out)
        self.patch("REFERENCE", out / cac.REFERENCE.name)
        return out

    def run_main(self, argv: list[str]) -> tuple[int, str]:
        """Run `main` with stdout captured.

        Two reasons, both about signal: a captured refusal can be *attributed* to
        the guard that emitted it, and a green suite does not bury a real failure
        under fifty lines of REFUSED chatter.
        """
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cac.main(argv)
        return code, buffer.getvalue()

    def run_self_test(self) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cac.self_test(groups=8, k=2)
        return code, buffer.getvalue()

    def resolve_quietly(self, name: str) -> Path | None:
        """`resolve_output_path` prints its own refusal, which is the operator's
        only signal and therefore not silenced in production -- only here, so a
        green suite stays readable.
        """
        with redirect_stdout(io.StringIO()):
            return cac.resolve_output_path(name)


class Top5SpecTests(unittest.TestCase):
    def test_every_spec_carries_exactly_the_keys_its_readers_use(self):
        """`run_top5` and `make_top5_strategy` index these by name. A missing key
        is a KeyError mid-sweep; an extra one is a value nothing ever reads, which
        is the more dangerous of the two because it looks configured.
        """
        expected = {"rank", "label", "horizon", "members", "mode", "sol_median"}
        for spec in cac.TOP5:
            self.assertEqual(set(spec), expected, spec.get("label"))

    def test_the_ranks_are_one_through_five_in_order(self):
        """The rank is written into the CSV and quoted as "#1".."#5" in
        TOP5-RECOMMENDATION.md, so a duplicated or reordered rank silently
        renames a published row.
        """
        self.assertEqual([s["rank"] for s in cac.TOP5], [1, 2, 3, 4, 5])

    def test_the_labels_are_unique(self):
        """The label is the CSV's human key and `cpcv_evaluate`'s label. Two rows
        sharing one would make the transfer table ambiguous about which
        configuration a delta belongs to.
        """
        self.assertEqual(len({s["label"] for s in cac.TOP5}), len(cac.TOP5))

    def test_the_advertised_shape_of_the_set_holds(self):
        """Three composites and four long-horizon entries is the module
        docstring's stated reason this block exists rather than reusing the
        singles sweep. If it drifts, the docstring's justification is stale.
        """
        composites = [s for s in cac.TOP5 if len(s["members"]) > 1]
        long_horizon = [s for s in cac.TOP5 if s["horizon"] == "long"]
        self.assertEqual(len(composites), 3)
        self.assertEqual(len(long_horizon), 4)

    def test_every_member_has_parameters_at_its_own_horizon(self):
        """The parameters are looked up as `HORIZONS[horizon]["params"][member]`.
        A member absent at its horizon is a KeyError only once the sweep reaches
        that configuration, i.e. after minutes of unrelated compute.
        """
        for spec in cac.TOP5:
            self.assertIn(spec["horizon"], HORIZONS, spec["label"])
            params = HORIZONS[spec["horizon"]]["params"]
            self.assertTrue(spec["members"], spec["label"])
            for member in spec["members"]:
                self.assertIn(member, params, f"{spec['label']} / {member}")

    def test_every_mode_is_one_the_composite_builder_accepts(self):
        """`Composite` raises on an unknown mode, but only for multi-member
        specs -- a single-member spec never reaches it, so a typo'd mode there
        would sit unnoticed until someone added a second member.
        """
        for spec in cac.TOP5:
            self.assertIn(spec["mode"], COMBINE_MODES, spec["label"])

    def test_the_control_medians_are_real_numbers(self):
        """`delta_vs_sol` subtracts these and the control gate thresholds the
        result. A string raises a TypeError deep inside the row build rather than
        at the constant, and an int would silently change the printed precision.
        """
        for spec in cac.TOP5:
            self.assertIsInstance(spec["sol_median"], float, spec["label"])


class MakeTop5StrategyTests(unittest.TestCase):
    def test_a_single_member_spec_is_not_wrapped_in_a_composite(self):
        """A one-element `all(...)` is the same signal, but it warms up and names
        itself differently, so wrapping it would stop the singles in this table
        being comparable to the singles table -- the reason the branch exists.
        """
        spec = next(s for s in cac.TOP5 if len(s["members"]) == 1)
        built = cac.make_top5_strategy(spec)()
        self.assertNotIsInstance(built, Composite)
        self.assertEqual(built.name, spec["label"])

    def test_a_multi_member_spec_becomes_a_composite_in_the_declared_mode(self):
        """`all` and `any` are different strategies, not different labels: `any`
        holds when either member holds. Building the wrong one still produces a
        full distribution of paths and a plausible Sharpe.
        """
        for spec in (s for s in cac.TOP5 if len(s["members"]) > 1):
            built = cac.make_top5_strategy(spec)()
            self.assertIsInstance(built, Composite, spec["label"])
            self.assertEqual(built.mode, spec["mode"], spec["label"])
            self.assertEqual(len(built.members), len(spec["members"]), spec["label"])

    def test_the_horizon_comes_from_the_spec_not_from_the_caller(self):
        """This is what makes the one-argument signature safe. `obv_trend` is
        ma_window=20 at medium and 60 at long, and rank 4's label says 60 -- so a
        caller that passed its own horizon could build `obv_trend_60` out of the
        medium parameters and neither the label nor the CSV would show it.
        """
        long_single = next(s for s in cac.TOP5 if s["label"] == "obv_trend_60")
        self.assertEqual(long_single["horizon"], "long")
        self.assertEqual(cac.make_top5_strategy(long_single)().params["ma_window"], 60)
        self.assertEqual(HORIZONS["medium"]["params"]["obv_trend"]["ma_window"], 20)

    def test_a_medium_horizon_composite_uses_the_medium_parameters(self):
        """Rank 2 is the only medium entry in a mostly-long table, so it is the
        one a horizon mix-up would hit. `hurst_switch` is lag=5/trend_window=100
        at medium against 10/200 at long.
        """
        medium = next(s for s in cac.TOP5 if s["horizon"] == "medium")
        members = cac.make_top5_strategy(medium)().params["members"]
        hurst = next(v for k, v in members.items() if k.startswith("hurst_switch"))
        self.assertEqual(hurst["lag"], 5)
        self.assertEqual(hurst["trend_window"], 100)

    def test_each_spec_builds_its_own_configuration(self):
        """Five distinct configurations must produce five distinct strategies. A
        factory that closed over the wrong spec -- or a caller that reused one --
        still returns a working strategy for every rank, which is why the
        assertion is on the built names rather than on any exception.
        """
        built = [cac.make_top5_strategy(spec)() for spec in cac.TOP5]
        self.assertEqual(len({s.name for s in built}), len(cac.TOP5))

    def test_a_factory_returns_a_fresh_instance_each_call(self):
        """`cpcv_evaluate` builds one instance per block precisely so position
        state cannot leak across blocks. A factory that returned a cached object
        would defeat that without any test of the engine noticing.
        """
        factory = cac.make_top5_strategy(cac.TOP5[0])
        self.assertIsNot(factory(), factory())


class Top5RowTests(PatchMixin):
    """`run_top5`'s row dict, its column declaration, and its wiring."""

    def setUp(self):
        self.loads: list[tuple[str, str]] = []
        self.evaluated: list[tuple[str, str]] = []
        self.kwargs: list[dict] = []

        def fake_load(asset: str, horizon: str):
            self.loads.append((asset, horizon))
            return {"close": np.zeros(3)}, object(), "9 bars, 2021-01-01..2021-01-09"

        def fake_evaluate(label, make_strategy, arrays, cfg, n_groups=8, k_test=2):
            # The strategy is *built* here so the label a row carries can be
            # checked against the configuration that row was evaluated from.
            self.evaluated.append((label, make_strategy().name))
            self.kwargs.append({"n_groups": n_groups, "k_test": k_test})
            return cpcv_result()

        self.patch("load_asset", fake_load)
        self.patch("cpcv_evaluate", fake_evaluate)

    def run_top5(self, assets: list[str] = ["DOGE"], groups: int = 8, k: int = 2):
        return cac.run_top5(assets, groups=groups, k=k, verbose=False)

    def test_the_declared_columns_are_exactly_the_row_keys(self):
        """Both directions, and the duplicated key list is the point. Comparing
        the built frame's columns to `TOP5_COLUMNS` is tautological -- the frame is
        built *with* that list -- so the row dict's own keys are read by building
        the frame without it.
        """
        expected = {
            "asset", "rank", "label", "horizon", "sol_median_sharpe", "median_sharpe",
            "delta_vs_sol", "q1_sharpe", "q3_sharpe", "frac_paths_positive",
            "median_return", "total_trades", "n_paths", "usable_blocks",
        }
        self.assertEqual(set(cac.TOP5_COLUMNS), expected)
        self.assertEqual(len(cac.TOP5_COLUMNS), len(expected))

        declared = list(cac.TOP5_COLUMNS)
        self.patch("TOP5_COLUMNS", None)  # frame takes its columns from the dict
        df, _windows = self.run_top5()
        self.assertEqual(set(df.columns), set(declared))

    def test_every_metric_column_carries_the_result_field_it_names(self):
        """A renamed or swapped key is invisible in the column set and in an
        is-it-all-NaN check: writing q3 into q1_sharpe, or usable_blocks into
        n_paths, produces a full and plausible CSV. The fake's eight metrics are
        mutually distinct so that each swap changes a value.
        """
        expected = cpcv_result()
        df, _windows = self.run_top5()
        self.assertEqual(len(df), len(cac.TOP5))
        for _i, row in df.iterrows():
            self.assertAlmostEqual(row["median_sharpe"], expected.median_sharpe)
            self.assertAlmostEqual(row["q1_sharpe"], expected.q1_sharpe)
            self.assertAlmostEqual(row["q3_sharpe"], expected.q3_sharpe)
            self.assertAlmostEqual(row["frac_paths_positive"], expected.frac_positive)
            self.assertAlmostEqual(row["median_return"], expected.median_return)
            self.assertEqual(row["total_trades"], expected.total_trades)
            self.assertEqual(row["n_paths"], expected.n_paths)
            self.assertEqual(row["usable_blocks"], expected.usable_blocks)

    def test_every_spec_column_carries_that_spec_s_value(self):
        """The other half of the row: rank, label and horizon are copied from the
        spec, and a row that mixed one spec's label with another's rank would
        rename a published row.
        """
        df, _windows = self.run_top5()
        for spec, (_i, row) in zip(cac.TOP5, df.iterrows(), strict=True):
            self.assertEqual(row["rank"], spec["rank"])
            self.assertEqual(row["label"], spec["label"])
            self.assertEqual(row["horizon"], spec["horizon"])
            self.assertAlmostEqual(row["sol_median_sharpe"], spec["sol_median"])

    def test_each_labelled_row_was_evaluated_from_its_own_configuration(self):
        """The regression a column-shape test cannot see. Label, rank and horizon
        come from the spec while the metrics come from the engine, so every row
        could be evaluated from rank 1's strategy and still read as ranks 1..5 --
        a plausible number, not an error.
        """
        self.run_top5()
        expected = [
            (spec["label"], cac.make_top5_strategy(spec)().name) for spec in cac.TOP5
        ]
        self.assertEqual(self.evaluated, expected)

    def test_the_block_geometry_reaches_the_evaluator(self):
        """`--groups` and `--k` are the CPCV geometry. Hardcoding either inside
        `run_top5` would silently ignore the flags and report a distribution from
        a different geometry than the one the header prints.
        """
        self.run_top5(groups=6, k=3)
        self.assertEqual(self.kwargs, [{"n_groups": 6, "k_test": 3}] * len(cac.TOP5))

    def test_delta_is_the_difference_its_name_claims(self):
        """The control gate thresholds this column, so a sign flip or a swapped
        operand order would move the verdict rather than the report.
        """
        df, _windows = self.run_top5()
        for _i, row in df.iterrows():
            self.assertAlmostEqual(
                row["delta_vs_sol"],
                row["median_sharpe"] - row["sol_median_sharpe"],
                places=12,
            )

    def test_the_series_is_read_once_per_asset(self):
        """A documented past regression: the cache was keyed on the horizon, so
        the medium entry and the long entries re-read the identical 1d file while
        the docstring claimed one read per asset.
        """
        self.run_top5(["DOGE", "ZEC"])
        self.assertEqual([asset for asset, _h in self.loads], ["DOGE", "ZEC"])

    def test_each_asset_reports_its_own_date_window(self):
        """The windows are the script's disclosure of confound #1 -- block *i* is
        not the same period across assets. A dropped or overwritten entry turns
        that disclosure into a claim about one asset.
        """
        _df, windows = self.run_top5(["DOGE", "ZEC"])
        self.assertEqual(set(windows), {"DOGE", "ZEC"})
        self.assertIn("2021-01-01", windows["DOGE"])

    def test_the_singles_columns_match_the_reference_header(self):
        """`COLUMNS` is compared positionally against the reference file's header
        in `self_test`; the docstring calls matching it exactly what makes the
        self-test a comparison rather than an interpretation.
        """
        header = pd.read_csv(cac.REFERENCE, nrows=0).columns.tolist()
        self.assertEqual(header, cac.COLUMNS)


class OutputPathTests(PatchMixin):
    """The write guard, asserted against the real constants where it cannot write."""

    def test_the_reference_file_is_refused(self):
        """The one file this script must never write. `resolve_output_path` is
        pure, so this is the safe place to assert against the real REFERENCE.
        """
        self.assertIsNone(self.resolve_quietly(cac.REFERENCE.name))

    def test_the_default_singles_filename_for_btc_eth_is_the_reference(self):
        """No `--out` is needed to aim at the reference: the singles branch derives
        this slug from the asset list. If the two ever stop matching, the guard
        stops covering the path that actually reaches it.
        """
        interval = HORIZONS[cac.REFERENCE_HORIZON]["interval"]
        self.assertEqual(f"cpcv_all25_btc_eth_{interval}.csv", cac.REFERENCE.name)

    def test_a_bare_filename_lands_in_the_results_directory(self):
        """The permitted case, asserted so the guard cannot be "fixed" by
        refusing everything.
        """
        dest = self.resolve_quietly("scratch_not_written.csv")
        self.assertIsNotNone(dest)
        self.assertEqual(dest.parent, cac.OUT.resolve())
        self.assertFalse(dest.exists(), "resolving a path must not create the file")

    def test_a_name_that_is_not_a_bare_filename_is_refused(self):
        """`OUT / name` confines nothing: an absolute operand replaces the left
        side outright and `..` walks out of it. `data/` is gitignored, so landing
        there is an unrecoverable overwrite of an input every published number
        depends on. Refusing anything with a path separator is what makes the
        containment check below unreachable rather than merely untested.
        """
        for name in ("/tmp/escaped.csv", "../../data/SOL_1d.csv", "sub/dir.csv", ""):
            self.assertIsNone(self.resolve_quietly(name), name)

    def test_a_dot_segment_is_refused(self):
        """`.` and `..` name a directory, not a file, and `Path("..").name` is the
        empty string -- so they are refused by the bare-filename rule rather than
        by the containment check that follows it. That check is therefore
        defence-in-depth with no input of its own today; it is kept because it is
        the invariant (`dest.parent == OUT`) the write actually depends on, and the
        bare-filename rule is the easier of the two to relax by accident.
        """
        self.assertIsNone(self.resolve_quietly(".."))
        self.assertIsNone(self.resolve_quietly("."))

    def test_the_singles_branch_refuses_before_evaluating_anything(self):
        """`--assets BTC,ETH` derives the reference filename with no `--out` at
        all. The guard used to sit after the sweep, so the run paid for 50
        configurations and then discarded them -- and a refusal that expensive is
        one an operator learns to route around.
        """
        self.sandbox_results_dir()
        self.patch("missing_data_files", lambda *a, **k: [])
        calls: list[str] = []
        self.patch("run_asset", lambda *a, **k: (calls.append("ran"), ([], "w"))[1])
        code, out = self.run_main(["--assets", "BTC,ETH", "--skip-self-test"])
        self.assertEqual(code, 1)
        self.assertIn("is the reference file", out)
        self.assertEqual(calls, [])

    def test_the_top5_branch_refuses_the_reference_too(self):
        """The branch that had no guard at all. Its rows carry no `strategy`
        column, so overwriting the reference with them does not merely corrupt the
        comparison -- it makes `self_test`'s merge key absent and the gate
        unrunnable.
        """
        out_dir = self.sandbox_results_dir()
        self.patch("missing_data_files", lambda *a, **k: [])
        calls: list[str] = []
        self.patch("run_top5", lambda *a, **k: calls.append("ran"))
        code, out = self.run_main(
            ["--top5", "--out", cac.REFERENCE.name, "--skip-self-test"]
        )
        self.assertEqual(code, 1)
        self.assertIn("is the reference file", out)
        self.assertEqual(calls, [])
        self.assertEqual(list(out_dir.iterdir()), [])

    def test_a_missing_price_file_is_refused_by_name(self):
        """The check exists so a typo does not surface as a FileNotFoundError
        partway through the loop, discarding every asset already computed.
        """
        self.sandbox_results_dir()
        code, out = self.run_main(["--assets", "NOSUCHCOIN", "--skip-self-test"])
        self.assertEqual(code, 1)
        self.assertIn("NOSUCHCOIN", out)
        self.assertIn("missing price data", out)

    def test_a_degenerate_block_geometry_is_refused_by_name(self):
        """`--groups 1` makes `make_groups` raise, which `cpcv_evaluate` converts
        into zero-path rows -- so the run wrote a CSV full of zeros and announced
        success. `--k 0` reached `np.concatenate` with no arrays instead. The
        refusal text is asserted because `rc == 1` alone cannot tell these apart
        from each other, or from the data check.
        """
        self.sandbox_results_dir()
        self.patch("missing_data_files", lambda *a, **k: [])
        calls: list[str] = []
        self.patch("run_asset", lambda *a, **k: (calls.append("ran"), ([], "w"))[1])
        cases = {
            "--groups": (["--groups", "1"], "--groups must be >= 2"),
            "k too low": (["--k", "0"], "--k must be >= 1"),
            "k too high": (["--k", "8"], "--k must be >= 1"),
            "k negative": (["--k", "-1"], "--k must be >= 1"),
        }
        for name, (argv, expected) in cases.items():
            code, out = self.run_main(argv + ["--skip-self-test"])
            self.assertEqual(code, 1, name)
            self.assertIn(expected, out, name)
        self.assertEqual(calls, [])

    def test_an_empty_asset_list_is_refused(self):
        """`--assets ","` produced a header-only CSV named `cpcv_all25__1d.csv`
        and reported "Wrote 0 rows" -- a file that looks like a result.
        """
        out_dir = self.sandbox_results_dir()
        self.patch("missing_data_files", lambda *a, **k: [])
        code, out = self.run_main(["--assets", ",", "--skip-self-test"])
        self.assertEqual(code, 1)
        self.assertIn("named no assets", out)
        code, out = self.run_main(
            ["--top5", "--no-control", "--assets", "SOL", "--skip-self-test"]
        )
        self.assertEqual(code, 1)
        self.assertIn("nothing to evaluate", out)
        self.assertEqual(list(out_dir.iterdir()), [])


class ControlGateTests(PatchMixin):
    """The `--top5` control gate: SOL must reproduce its own published medians."""

    def frame(self, deltas: dict[int, float] | None = None, drop_ranks=()) -> pd.DataFrame:
        """A SOL control block plus one transfer asset.

        `deltas` shifts a rank's median away from its published value; a NaN shift
        stands for an insufficient configuration, which is how a real partial
        control arrives.
        """
        deltas = deltas or {}
        rows = []
        for asset in ("SOL", "DOGE"):
            for spec in cac.TOP5:
                if asset == "SOL" and spec["rank"] in drop_ranks:
                    continue
                shift = deltas.get(spec["rank"], 0.0) if asset == "SOL" else -0.5
                median = spec["sol_median"] + shift
                rows.append({
                    "asset": asset, "rank": spec["rank"], "label": spec["label"],
                    "horizon": spec["horizon"], "sol_median_sharpe": spec["sol_median"],
                    "median_sharpe": median, "delta_vs_sol": median - spec["sol_median"],
                    "q1_sharpe": 0.1, "q3_sharpe": 0.9, "frac_paths_positive": 0.6,
                    "median_return": 0.2, "total_trades": 40,
                    "n_paths": N_PATHS, "usable_blocks": USABLE,
                })
        return pd.DataFrame(rows, columns=cac.TOP5_COLUMNS)

    def run_top5_main(self, df: pd.DataFrame, extra: list[str] = []) -> tuple[int, str]:
        self.sandbox_results_dir()
        self.patch("missing_data_files", lambda *a, **k: [])
        self.patch("run_top5", lambda *a, **k: (df, {"SOL": "w", "DOGE": "w"}))
        return self.run_main(["--top5", "--assets", "DOGE", "--skip-self-test"] + extra)

    def test_an_agreeing_control_passes_and_exits_zero(self):
        """The baseline the other cases are read against."""
        code, out = self.run_top5_main(self.frame())
        self.assertEqual(code, 0)
        self.assertIn("CONTROL PASSED", out)

    def test_a_control_beyond_tolerance_diverges_and_exits_non_zero(self):
        """CROSS-ASSET-TRANSFER.md treats this as one of two gates, and the branch
        returned 0 unconditionally -- so no script could check it, and a divergence
        was a line of prose in a passing run.
        """
        code, out = self.run_top5_main(self.frame({1: cac.CONTROL_TOLERANCE * 10}))
        self.assertEqual(code, 1)
        self.assertIn("CONTROL DIVERGED", out)
        self.assertIn("unverified", out)

    def test_a_control_inside_tolerance_still_passes(self):
        """The published medians are quoted to three decimals, so rounding alone
        can contribute 5e-4. A gate that failed on that would be unusable.
        """
        code, out = self.run_top5_main(self.frame({1: cac.CONTROL_TOLERANCE / 10}))
        self.assertEqual(code, 0)
        self.assertIn("CONTROL PASSED", out)

    def test_a_partial_control_does_not_pass_on_the_rows_that_survived(self):
        """`.abs().max()` skips NaN, so four insufficient configurations and one
        agreeing one printed PASSED on a fifth of the evidence -- the worst
        available outcome, because the verdict reads as authoritative.
        """
        nans = {rank: float("nan") for rank in (1, 2, 3, 4)}
        code, out = self.run_top5_main(self.frame(nans))
        self.assertEqual(code, 1)
        self.assertIn("CONTROL DIVERGED", out)
        self.assertIn("1 of 5 control configurations", out)

    def test_a_missing_control_row_does_not_pass(self):
        """Same failure in its other form: a configuration that produced no row at
        all cannot be distinguished from one that agreed, if only the rows present
        are aggregated.
        """
        code, out = self.run_top5_main(self.frame(drop_ranks=(5,)))
        self.assertEqual(code, 1)
        self.assertIn("CONTROL DIVERGED", out)

    def test_the_control_can_be_waived_but_then_certifies_nothing(self):
        """`--no-control` is a documented option, so it must not fail; it must also
        not print a verdict it did not earn.
        """
        code, out = self.run_top5_main(self.frame(), extra=["--no-control"])
        self.assertEqual(code, 0)
        self.assertNotIn("CONTROL", out)

    def test_the_transfer_summary_excludes_untestable_configurations(self):
        """A drifted copy of `summarise()` hardcoded "/5" and skipped the
        `n_paths > 0` filter, so a dropped configuration was counted in the
        denominator but never the numerator -- reported as "tested and failed"
        rather than "never testable".
        """
        df = self.frame()
        df.loc[(df["asset"] == "DOGE") & (df["rank"] == 5), "n_paths"] = 0
        code, out = self.run_top5_main(df)
        self.assertEqual(code, 0)
        self.assertIn("DOGE", out)
        self.assertIn("/4 still positive", out)
        self.assertIn("1 insufficient", out)


class SelfTestGateTests(PatchMixin):
    """The gate's own comparison logic, without the 50-configuration sweep."""

    ROWS = (
        {"asset": "BTC", "strategy": "obv_trend", "n_paths": 28, "usable_blocks": 8,
         "median_sharpe": 0.5, "q1_sharpe": 0.1, "q3_sharpe": 0.9,
         "frac_paths_positive": 0.6, "median_return": 0.2, "total_trades": 40},
        {"asset": "ETH", "strategy": "obv_trend", "n_paths": 0, "usable_blocks": 3,
         "median_sharpe": float("nan"), "q1_sharpe": float("nan"),
         "q3_sharpe": float("nan"), "frac_paths_positive": float("nan"),
         "median_return": float("nan"), "total_trades": 7},
    )

    def use_reference(self, frame: pd.DataFrame) -> Path:
        """Redirect REFERENCE to a temp two-row stand-in.

        A temp reference rather than the real 50-row file for two reasons: the
        real one needs `data/`, which is gitignored, and a failing comparison
        against it prints fifty rows of merge output per test.
        """
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        reference = Path(tmp.name) / "reference.csv"
        frame.to_csv(reference, index=False)
        self.patch("REFERENCE", reference)
        self.patch("missing_data_files", lambda *a, **k: [])
        return reference

    def gate_over(self, produced: tuple[dict, ...]) -> tuple[int, str]:
        """Have the sweep yield `produced` against a temp copy of ROWS.

        Nothing is read from `data/` and nothing is written to
        `research/results/`.
        """
        self.use_reference(pd.DataFrame(list(self.ROWS), columns=cac.COLUMNS))
        self.patch("REFERENCE_ASSETS", ("BTC", "ETH"))
        by_asset = {r["asset"]: r for r in produced}
        self.patch(
            "run_asset",
            lambda asset, *a, **k: ([by_asset[asset]], "9 bars, a..b"),
        )
        return self.run_self_test()

    def test_an_exact_reproduction_passes(self):
        """The baseline the other cases are read against, including the NaN row:
        NaN equal to NaN must not itself be a divergence.
        """
        code, out = self.gate_over(self.ROWS)
        self.assertEqual(code, 0)
        self.assertIn("SELF-TEST PASSED", out)

    def test_a_number_that_became_nan_fails(self):
        """The divergence the gate could not see. `NaN > TOLERANCE` is False, so
        subtracting through left `worst` at zero and printed PASSED -- and
        insufficient configurations are written as NaN deliberately, so this is
        the shape a real regression would most likely take.
        """
        broken = ({**self.ROWS[0], "median_sharpe": float("nan")}, self.ROWS[1])
        code, out = self.gate_over(broken)
        self.assertEqual(code, 1)
        self.assertIn("between a value and NaN", out)

    def test_a_nan_that_became_a_number_fails(self):
        """The same hole in the other direction: a configuration that used to be
        refused for want of usable blocks now reporting a Sharpe is a change in
        what was measured, not an improvement.
        """
        broken = (self.ROWS[0], {**self.ROWS[1], "median_sharpe": 0.4})
        code, out = self.gate_over(broken)
        self.assertEqual(code, 1)
        self.assertIn("between a value and NaN", out)

    def test_a_difference_above_tolerance_fails(self):
        """Named in the output so a divergence points at the column and row that
        moved rather than at the file as a whole.
        """
        broken = ({**self.ROWS[0], "median_sharpe": 0.5 + cac.TOLERANCE * 10}, self.ROWS[1])
        code, out = self.gate_over(broken)
        self.assertEqual(code, 1)
        self.assertIn("median_sharpe on BTC/obv_trend", out)

    def test_a_difference_below_tolerance_passes(self):
        """Re-derivation through pandas and numpy is not bit-identical across
        versions, which is the whole reason TOLERANCE is not zero.
        """
        ok = ({**self.ROWS[0], "median_sharpe": 0.5 + cac.TOLERANCE / 10}, self.ROWS[1])
        code, _out = self.gate_over(ok)
        self.assertEqual(code, 0)

    def test_a_changed_row_set_fails_as_a_row_set_difference(self):
        """Renaming a strategy makes the merge produce left-only and right-only
        rows. The diagnostic matters as much as the exit code: the NaN check fires
        on the same input, so a gate that reported "value became NaN" would send
        the reader looking for a numerical problem instead of a renamed row.
        """
        broken = ({**self.ROWS[0], "strategy": "renamed"}, self.ROWS[1])
        code, out = self.gate_over(broken)
        self.assertEqual(code, 1)
        self.assertIn("row sets differ", out)

    def test_a_missing_reference_does_not_read_as_a_pass(self):
        """The caller's test is `!= 0`. Returning 0 for "there was nothing to
        compare against" made a gate that never ran indistinguishable from one
        that agreed, and the run went on to write new asset rows.
        """
        self.patch("REFERENCE", Path("/nonexistent/reference.csv"))
        code, out = self.run_self_test()
        self.assertNotEqual(code, 0)
        self.assertIn("SELF-TEST SKIPPED", out)

    def test_absent_price_data_does_not_read_as_a_pass(self):
        """`data/` is gitignored, so "the reference exists but its inputs do not"
        is the normal state of a fresh clone -- exactly where a silent pass would
        be most expensive.
        """
        self.use_reference(pd.DataFrame(list(self.ROWS), columns=cac.COLUMNS))
        self.patch("missing_data_files", lambda *a, **k: ["data/BTC_1d.csv"])
        code, out = self.run_self_test()
        self.assertNotEqual(code, 0)
        self.assertIn("SELF-TEST SKIPPED", out)

    def test_a_reference_missing_a_column_fails_instead_of_raising(self):
        """The gate exists to turn "cannot reproduce" into a sentence. A drifted
        schema used to surface as a bare KeyError from the suffixed lookup, which
        is the same information delivered as a crash.
        """
        frame = pd.DataFrame(list(self.ROWS), columns=cac.COLUMNS).drop(columns=["q3_sharpe"])
        self.use_reference(frame)
        code, out = self.run_self_test()
        self.assertEqual(code, 1)
        self.assertIn("missing columns", out)

    def test_an_unreproducible_gate_stops_the_new_asset_run(self):
        """The gate's purpose expressed end to end: new rows must not be written
        on a harness that cannot reproduce the old ones.
        """
        self.sandbox_results_dir()
        self.patch("self_test", lambda *a, **k: 1)
        calls: list[str] = []
        self.patch("run_asset", lambda *a, **k: (calls.append("ran"), ([], "w"))[1])
        code, out = self.run_main(["--assets", "DOGE"])
        self.assertEqual(code, 1)
        self.assertIn("Refusing to report new assets", out)
        self.assertEqual(calls, [])

    def test_the_gate_is_pinned_to_the_horizon_its_reference_came_from(self):
        """The reference is one fixed file. Running the comparison at whatever
        `--horizon` the operator asked for made every non-default horizon a
        refusal, which teaches the operator to pass --skip-self-test.
        """
        seen: list[str] = []
        self.use_reference(pd.DataFrame(list(self.ROWS), columns=cac.COLUMNS))
        self.patch(
            "run_asset",
            lambda asset, horizon, *a, **k: (seen.append(horizon), ([], "w"))[1],
        )
        self.run_self_test()
        self.assertEqual(set(seen), {cac.REFERENCE_HORIZON})


class SummariseTests(unittest.TestCase):
    FRAME = pd.DataFrame(
        [
            {"asset": "DOGE", "strategy": "a", "n_paths": 28, "usable_blocks": 8,
             "median_sharpe": 0.5, "q1_sharpe": 0.0, "q3_sharpe": 1.0,
             "frac_paths_positive": 0.6, "median_return": 0.2, "total_trades": 10},
            {"asset": "DOGE", "strategy": "b", "n_paths": 21, "usable_blocks": 7,
             "median_sharpe": -0.5, "q1_sharpe": -1.0, "q3_sharpe": 0.0,
             "frac_paths_positive": 0.3, "median_return": -0.1, "total_trades": 20},
            {"asset": "DOGE", "strategy": "c", "n_paths": 0, "usable_blocks": 3,
             "median_sharpe": float("nan"), "q1_sharpe": float("nan"),
             "q3_sharpe": float("nan"), "frac_paths_positive": float("nan"),
             "median_return": float("nan"), "total_trades": 4},
        ],
        columns=cac.COLUMNS,
    )

    def test_a_configuration_with_no_paths_leaves_both_halves_of_the_ratio(self):
        """"1/2 positive", not "1/3". A configuration that could not be tested is
        a different fact from one that was tested and failed to clear zero, and
        putting it in the denominator states the second -- the distinction
        `run_asset`'s own comment turns on when it writes the zero-path row.
        """
        line = cac.summarise(self.FRAME)
        self.assertIn("1/2 positive median Sharpe", line)
        self.assertIn("1 made money", line)

    def test_the_median_return_is_taken_over_the_ranked_rows_only(self):
        """The dropped row's NaN would be skipped by `.median()` anyway, but the
        headline is the number a reader quotes, so it is pinned rather than
        inferred: +0.2 and -0.1 give +5.00%.
        """
        self.assertIn("+5.00%", cac.summarise(self.FRAME))

    def test_the_path_and_block_ranges_describe_the_ranked_rows_only(self):
        """The ranges are the evidence floor a reader checks the medians against.
        Including the dropped row would report `paths 0-28` and understate the
        floor for every configuration that did run.
        """
        line = cac.summarise(self.FRAME)
        self.assertIn("paths 21-28", line)
        self.assertIn("blocks 7-8", line)

    def test_each_asset_gets_its_own_line_in_input_order(self):
        """Grouped with sort=False on purpose: `--top5` puts the SOL control
        first so a reader meets the control before the assets it certifies.
        """
        frame = pd.concat([self.FRAME.assign(asset="ZEC"), self.FRAME])
        lines = cac.summarise(frame).splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("ZEC", lines[0])
        self.assertIn("DOGE", lines[1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

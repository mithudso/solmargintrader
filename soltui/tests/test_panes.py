"""The four modules behind the new console tabs.

No test here drives a terminal, opens a socket, or reads `data/`. That is the same
split the rest of this package keeps: `tui.py` is presentation, and the logic lives
in modules that can be tested without an event loop.

The two worth reading first are `test_a_below_floor_row_is_never_rankable` and
`test_slicing_happens_before_the_replay`. Each pins a property that, if it broke,
would produce a confident wrong answer rather than an error.
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from soltui import analyze, cumulative, docs_browser, serve


def write_index(root: Path, files: list[dict]) -> Path:
    p = root / "INDEX.json"
    p.write_text(json.dumps({"files": files}))
    return p


class DocsBrowserTests(unittest.TestCase):
    ENTRIES = [
        {"path": "docs/SCRIPTS.md", "name": "SCRIPTS.md", "dir": "docs",
         "kind": "doc", "summary": "Every runnable entry point.",
         "summarySource": "opening-prose", "lines": 400, "bytes": 20_000},
        {"path": "backtester/core/cpcv.py", "name": "cpcv.py",
         "dir": "backtester/core", "kind": "code-python",
         "summary": "Combinatorial purged cross-validation and the evidence floor.",
         "summarySource": "docstring", "lines": 331, "bytes": 12_907},
    ]

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.index = write_index(Path(self.tmp.name), self.ENTRIES)
        self.catalog = docs_browser.load_catalog(self.index)

    def test_a_missing_index_names_the_command_that_builds_it(self):
        """An empty Docs tab reads as "this repo has no files", which is a much
        worse diagnostic than one sentence saying the index was never built.
        """
        with self.assertRaises(docs_browser.CatalogUnavailable) as ctx:
            docs_browser.load_catalog(Path(self.tmp.name) / "absent.json")
        self.assertIn("index/build.py all", str(ctx.exception))

    def test_the_filter_matches_summaries_not_only_paths(self):
        """"evidence floor" is what someone types; it appears in a summary, not in
        any filename. A path-only filter would return nothing and look broken.
        """
        hits = docs_browser.filter_entries(self.catalog, "evidence floor")
        self.assertEqual([e.path for e in hits], ["backtester/core/cpcv.py"])

    def test_filtering_by_kind_narrows_without_a_query(self):
        self.assertEqual(
            [e.path for e in docs_browser.filter_entries(self.catalog, kind="doc")],
            ["docs/SCRIPTS.md"])

    def test_the_catalogue_is_the_allowlist(self):
        """The viewer must not read a path merely because a caller supplied it.

        This process also serves over HTTP, so a viewer that opens arbitrary paths
        is a file-disclosure surface rather than a convenience.
        """
        with self.assertRaises(FileNotFoundError):
            docs_browser.resolve("../../etc/passwd", self.catalog)
        with self.assertRaises(FileNotFoundError):
            docs_browser.resolve("backtester/core/engine.py", self.catalog)

    def test_language_is_derived_from_the_extension(self):
        by_path = {e.path: e for e in self.catalog}
        self.assertEqual(by_path["backtester/core/cpcv.py"].language, "python")
        self.assertEqual(by_path["docs/SCRIPTS.md"].language, "markdown")

    def test_results_tree_has_no_write_path(self):
        """The evidence tree staying unwritable is the feature, so it is pinned.

        `docs_browser` now has a guarded `write_document()` (see
        `test_docs_browser.py` for the full guard suite) — the Docs tab is no
        longer read-only end to end. What must never change is this: writing
        under `research/results/` is refused regardless of kind or caller,
        because `verify_numbers.py` and friends assume that tree changes only
        through committed scripts that can be re-run.
        """
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "research" / "results").mkdir(parents=True)
        index = write_index(root, [
            {"path": "research/results/sweep.csv", "name": "sweep.csv",
             "dir": "research/results", "kind": "code-python", "summary": "",
             "summarySource": "none", "lines": 1, "bytes": 10},
        ])
        catalog = docs_browser.load_catalog(index)
        with self.assertRaises(PermissionError):
            docs_browser.write_document(
                "research/results/sweep.csv", "tampered", catalog)


class CumulativeTests(unittest.TestCase):
    HEADER = ("asset,strategy,n_paths,usable_blocks,median_sharpe,q1_sharpe,"
              "q3_sharpe,frac_paths_positive,median_return,total_trades\n")

    def make_results(self, rows: str) -> Path:
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "cpcv_all25_demo_1d.csv").write_text(self.HEADER + rows)
        return root

    def test_a_below_floor_row_is_never_rankable(self):
        """The defect this module exists to prevent, using the real example.

        BTC's top-ranked `ou_reversion` medians +1.657 on **six** trades. The
        engine printed it DROPPED but still returned a full path count, so a
        filter on `n_paths > 0` ranks it first. It must never be `best`.
        """
        root = self.make_results(
            "BTC,ou_reversion,15,6,1.657,0.5,2.0,0.8,0.4,6\n"
            "BTC,macd,21,7,0.496,0.1,0.9,0.76,0.03,134\n"
        )
        s = cumulative.load_all(root)[0]
        self.assertEqual(len(s.rankable), 1)
        self.assertEqual(len(s.below_floor), 1)
        self.assertIsNotNone(s.best)
        self.assertEqual(s.best.label, "macd",
                         "the 6-trade row must not be the headline result")

    def test_a_row_with_no_paths_is_also_refused(self):
        root = self.make_results("BTC,never_ran,0,0,,,,,,0\n")
        s = cumulative.load_all(root)[0]
        self.assertEqual(s.rankable, [])
        self.assertIsNone(s.best)

    def test_nan_sharpe_does_not_become_a_number(self):
        """Insufficient configurations are written as NaN. Parsed naively they
        compare as floats and can win a max().
        """
        root = self.make_results("BTC,dropped,15,6,NaN,NaN,NaN,NaN,NaN,40\n")
        row = cumulative.load_all(root)[0].rows[0]
        self.assertIsNone(row.median_sharpe)

    def test_totals_count_evidence_and_never_pool_a_sharpe(self):
        """Files span different assets, horizons and CPCV geometries, so a median
        across them would describe nothing. Counting is the honest aggregate.
        """
        root = self.make_results(
            "BTC,a,21,7,1.0,0,0,0.9,0.5,50\nBTC,b,21,7,-0.5,0,0,0.2,-0.3,50\n")
        t = cumulative.totals(cumulative.load_all(root))
        self.assertEqual(t["rankable"], 2)
        self.assertEqual(t["positive"], 1)
        self.assertEqual(t["made_money"], 1)
        self.assertNotIn("median_sharpe", t)

    def test_floor_casualties_surface_the_highest_claims_first(self):
        """These are the rows a naive aggregate would show first, which is exactly
        why the tab lists them explicitly.
        """
        root = self.make_results(
            "BTC,small_but_loud,15,6,1.9,0,0,1.0,0.9,4\n"
            "BTC,small_and_quiet,15,6,0.1,0,0,0.5,0.0,4\n")
        worst = cumulative.floor_casualties(cumulative.load_all(root))
        self.assertEqual(worst[0].label, "small_but_loud")

    def test_the_headline_states_the_floor(self):
        root = self.make_results("BTC,a,21,7,1.0,0,0,0.9,0.5,50\n")
        self.assertIn("rankable", cumulative.headline(cumulative.load_all(root)))


class AnalyzeTests(unittest.TestCase):
    def test_timestamps_are_read_as_utc(self):
        """A naive local timestamp selects a different bar than the user meant —
        on a daily series, a different day's decision.
        """
        for text in ("2024-06-01", "2024-06-01 12:30", "2024-06-01T12:30",
                     "2024-06-01T12:30:00Z"):
            with self.subTest(text=text):
                self.assertEqual(analyze.parse_as_of(text).tzinfo, timezone.utc)

    def test_an_unreadable_timestamp_is_refused_not_guessed(self):
        for bad in ("", "yesterday", "01/06/2024"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                analyze.parse_as_of(bad)

    def test_slicing_happens_before_the_replay(self):
        """The correctness condition of the whole tab.

        Stateful strategies decide today's exposure from the bar that opened the
        position, so the series must be truncated at `as_of` and replayed from the
        start. Reading a row out of a full-history replay would report a number
        that depended on bars after the chosen moment.
        """
        import numpy as np

        ts = np.array(["2024-01-01", "2024-01-02", "2024-01-03"],
                      dtype="datetime64[s]")
        arrays = {"close": np.array([1.0, 2.0, 3.0]),
                  "timestamp": np.array([0, 1, 2])}
        sliced, idx = analyze.slice_to(
            arrays, ts, datetime(2024, 1, 2, tzinfo=timezone.utc))
        self.assertEqual(idx, 1)
        self.assertEqual(len(sliced["close"]), 2,
                         "bars after as_of must not reach the replay")
        self.assertEqual(sliced["close"][-1], 2.0)

    def test_a_cutoff_before_all_history_is_an_error(self):
        import numpy as np

        ts = np.array(["2024-01-02"], dtype="datetime64[s]")
        with self.assertRaises(ValueError):
            analyze.slice_to({"close": np.array([1.0])}, ts,
                             datetime(2020, 1, 1, tzinfo=timezone.utc))

    def test_available_assets_reports_the_cache_not_a_fixed_universe(self):
        """`data/` is gitignored and per-machine, so a hardcoded picker would
        offer symbols that fail on selection.
        """
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "SOL_1d.csv").write_text("timestamp\n")
        (root / "BTC_1h.csv").write_text("timestamp\n")
        (root / "notes.txt").write_text("ignored")
        self.assertEqual(analyze.available_assets(root),
                         [("BTC", "1h"), ("SOL", "1d")])

    def test_a_missing_series_names_the_fetch_command(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        with self.assertRaises(FileNotFoundError) as ctx:
            analyze.load_series("NOPE", "1d", Path(tmp.name))
        self.assertIn("backtester.core.fetch", str(ctx.exception))


class ServeTests(unittest.TestCase):
    def test_it_binds_loopback_only(self):
        """The served console can drive the Execute tab. That tab is dry-run only,
        but loopback is still the right default and there is no flag to widen it.
        """
        self.assertEqual(serve.HOST, "127.0.0.1")
        self.assertIn("127.0.0.1", serve.url_for(1234))

    def test_the_app_command_uses_an_absolute_interpreter(self):
        """A menu-bar process inherits neither cwd nor PATH reliably."""
        self.assertTrue(serve.app_command().startswith("/"))
        self.assertIn("-m soltui.tui", serve.app_command())

    def test_find_port_returns_something_free(self):
        port = serve.find_port()
        self.assertIsNotNone(port)
        self.assertTrue(serve.port_is_free(port))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

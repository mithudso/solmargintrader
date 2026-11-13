"""Protect timestamp alignment, selection independence and missing-data behavior."""

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research import news_event_report, news_event_study
from research.news_event_report import _paired_latency
from research.news_event_study import (
    canonical_url,
    cluster_interval,
    entry_minute,
    epoch,
    event_returns,
    measure,
    reviewed_events,
    select_events,
)

CLI_BLOCKER = '''import builtins, importlib, json, runpy, sys
module, blocked, arguments = sys.argv[1:]
original_import = builtins.__import__
original_module = importlib.import_module
def refuse(name):
    if name == blocked or name.startswith(blocked + "."):
        raise ModuleNotFoundError("PRIVATE_DEPENDENCY_CANARY", name=blocked)
def guarded_import(name, *args, **kwargs):
    refuse(name)
    return original_import(name, *args, **kwargs)
def guarded_module(name, *args, **kwargs):
    refuse(name)
    return original_module(name, *args, **kwargs)
builtins.__import__ = guarded_import
importlib.import_module = guarded_module
sys.argv = [module, *json.loads(arguments)]
runpy.run_module(module, run_name="__main__")
'''


class NewsEvents(unittest.TestCase):
    def test_utc_week_uses_instant_across_offset_boundary(self):
        same_instant = [
            {"published_at": "1970-01-08T00:30:00+01:00", "x": 1},
            {"published_at": "1970-01-07T23:30:00Z", "x": 2},
        ]
        self.assertEqual(cluster_interval(same_instant, "x"), (None, None, 1))
        different_weeks = [
            {"published_at": "1970-01-08T00:30:00+01:00", "x": 1},
            {"published_at": "1970-01-08T00:30:00Z", "x": 2},
        ]
        self.assertEqual(cluster_interval(different_weeks, "x")[2], 2)

    def test_entry_is_strictly_after_publication(self):
        self.assertEqual(entry_minute(120), 180)
        self.assertEqual(entry_minute(121), 180)
        self.assertEqual(entry_minute(179), 180)

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            epoch("2026-01-01T00:00:00")
        self.assertEqual(
            epoch("2026-01-01T01:00:00+01:00"), epoch("2026-01-01T00:00:00Z")
        )

    def test_missing_minute_is_not_next_observed_row(self):
        self.assertIsNone(event_returns({60: 10, 180: 12}, 60, 1))
        self.assertAlmostEqual(event_returns({60: 10, 180: 12}, 60, 2), 20)

    def test_nonpositive_price_refused(self):
        with self.assertRaises(ValueError):
            event_returns({60: 0, 120: 1}, 60, 1)

    def test_tracking_query_is_not_an_independent_story(self):
        self.assertEqual(
            canonical_url("https://example.com/news/?utm_source=feed"),
            "https://example.com/news",
        )

    @staticmethod
    def article(
        title="Solana launches protocol upgrade",
        date="2026-08-20T01:00:01Z",
        url="https://example.com/a",
    ):
        return {
            "title": title,
            "published_at": date,
            "url": url,
            "source": "fixture",
            "timestamp_source": "publisher_api",
        }

    def test_conflicting_rolling_publication_is_excluded(self):
        a = self.article()
        b = self.article(date="2026-08-21T01:00:01Z")
        selected, rejected = select_events([a, b], [], 0, 9999999999)
        self.assertFalse(selected)
        self.assertEqual(rejected[0]["reason"], "conflicting_publication_times_for_url")

    def test_market_control_holdout_protects_other_asset_event(self):
        a = self.article()
        start = entry_minute(epoch(a["published_at"]))
        reservations = [
            {"coin": "USD-ETH-BTC", "start": start + 60, "end": start + 120}
        ]
        selected, rejected = select_events([a], reservations, 0, 9999999999)
        self.assertFalse(selected)
        self.assertEqual(rejected[0]["reason"], "protected_event_or_prior_week_window")

    def test_price_reaction_headline_is_not_catalyst(self):
        selected, rejected = select_events(
            [self.article(title="Solana price surges after ETF launch")],
            [],
            0,
            9999999999,
        )
        self.assertFalse(selected)
        self.assertEqual(
            rejected[0]["reason"], "price_commentary_evergreen_or_promotion"
        )

    def test_spaced_selection_is_deterministic_without_outcomes(self):
        rows = [
            self.article(
                date=f"2026-08-{day:02}T01:00:01Z", url=f"https://example.com/{day}"
            )
            for day in range(1, 25)
        ]
        a, _ = select_events(rows, [], 0, 9999999999, limit=5)
        b, _ = select_events(list(reversed(rows)), [], 0, 9999999999, limit=5)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 5)

    def test_returns_use_correct_market_control_and_paired_clock(self):
        entry = 800000
        e = {
            **self.article(),
            "coin": "SOL",
            "entry": entry,
            "published": entry - 20,
            "event_type": "protocol_adoption",
        }
        prices = {
            c: {
                entry: 100,
                entry + 60: p,
                entry - 3600: 100,
                entry - 604800: 100,
                entry - 604800 + 60: 100,
            }
            for c, p in (("SOL", 110), ("BTC", 102), ("ETH", 104))
        }
        row = measure([e], prices)[0]
        self.assertAlmostEqual(row["return_pct"], 10)
        self.assertAlmostEqual(row["benchmark_pct"], 3)
        self.assertAlmostEqual(row["excess_pp"], 7)
        self.assertAlmostEqual(row["paired_excess_delta_pp"], 7)

    def test_uncertainty_needs_multiple_dates(self):
        self.assertEqual(
            cluster_interval([{"published_at": "2026-01-01", "x": 1}], "x"),
            (None, None, 1),
        )

    def test_prepublication_window_does_not_include_post_news_entry(self):
        published = epoch("2026-08-20T01:00:20Z")
        entry = entry_minute(published)
        pre_end = (published // 60 - 1) * 60
        event = {
            **self.article(),
            "coin": "SOL",
            "published": published,
            "entry": entry,
            "event_type": "protocol_adoption",
        }
        prices = {
            coin: {pre_end - 3600: 100, pre_end: 100, entry: 200, entry + 60: 200}
            for coin in ("SOL", "BTC", "ETH")
        }
        row = measure([event], prices)[0]
        self.assertEqual(row["pre60_return_pct"], 0)
        self.assertLess(epoch(row["pre60_end_utc"]), published)

    def test_replacing_frozen_cohort_needs_independent_review_too(self):
        event = {
            **self.article(),
            "coin": "SOL",
            "event_type": "protocol_adoption",
            "published": epoch(self.article()["published_at"]),
        }
        event["entry"] = entry_minute(event["published"])
        decision = {
            **event,
            "include": True,
            "corrected_event_type": event["event_type"],
        }
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            events = home / "events-frozen.json"
            review = home / "eligibility-review-v2.json"
            manifest = home / "selection-v2-manifest.json"
            events.write_text(json.dumps([event]))
            review.write_text(
                json.dumps(
                    {
                        "price_data_accessed": False,
                        "new_articles_added": 0,
                        "rejected_rows_replaced": 0,
                        "decisions": [decision],
                    }
                )
            )

            def bind():
                manifest.write_text(
                    json.dumps(
                        {
                            "files": {
                                str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in (events, review)
                            }
                        }
                    )
                )

            bind()
            self.assertEqual(reviewed_events(home), [event])
            events.write_text(
                json.dumps([event, {**event, "url": "https://example.com/extra"}])
            )
            with self.assertRaisesRegex(ValueError, "checksum"):
                reviewed_events(home)
            bind()
            with self.assertRaisesRegex(ValueError, "identities"):
                reviewed_events(home)

    def test_delay_comparison_uses_same_available_event_rows(self):
        base = [
            {"coin": "SOL", "url": url, "horizon_minutes": "1", "return_pct": value}
            for url, value in (("a", "10"), ("b", "-10"))
        ]
        delayed = [
            {"coin": "SOL", "url": url, "horizon_minutes": "1", "return_pct": value}
            for url, value in (("a", "1"), ("b", ""))
        ]
        pair = _paired_latency(base, delayed)[("SOL", 1)]
        self.assertEqual(pair["n"], 1)
        self.assertEqual(pair["immediate_mean"], 10)
        self.assertEqual(pair["delayed_mean"], 1)


class NewsPrerequisites(unittest.TestCase):
    def cli(self, module, blocked, arguments):
        return subprocess.run(
            [sys.executable, "-c", CLI_BLOCKER, module, blocked, json.dumps(arguments)],
            cwd=Path(__file__).resolve().parents[2],
            env={**os.environ, "TOOL_NO_VENV": "1"},
            capture_output=True, text=True, timeout=20, check=False,
        )

    def test_stdlib_help_and_argument_errors_before_dependencies(self):
        for module in ("research.news_event_study", "research.news_event_report"):
            for arguments, expected in ((["--help"], 0), (["--unknown"], 2), ([], 2)):
                with self.subTest(module=module, arguments=arguments):
                    result = self.cli(module, "numpy", arguments)
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn("PRIVATE_DEPENDENCY_CANARY", result.stderr)

    def test_report_only_dependency_failure_precedes_input_and_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for module, blocked in (
                ("research.news_event_study", "numpy"),
                ("research.news_event_report", "numpy"),
                ("research.news_event_report", "matplotlib"),
                ("research.news_event_report", "matplotlib.pyplot"),
            ):
                arguments = ["--home", str(root / "absent-home")]
                arguments += (
                    ["--output", str(root / "absent-output")]
                    if module.endswith("study") else
                    ["--analyzed", str(root / "absent-analysis"), "--repo", str(root / "absent-repo")]
                )
                with self.subTest(module=module, blocked=blocked):
                    result = self.cli(module, blocked, arguments)
                    self.assertEqual(result.returncode, 3, result.stderr)
                    self.assertIn(blocked, result.stderr)
                    self.assertIn("uv run --no-project", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertNotIn("PRIVATE_DEPENDENCY_CANARY", result.stderr)
                    self.assertEqual(list(root.iterdir()), [])

    def test_missing_plotting_dependency_preserves_existing_report_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home, analyzed, repo = (root / name for name in ("home", "analyzed", "repo"))
            home.mkdir()
            analyzed.mkdir()
            output = repo / "research" / "results"
            output.mkdir(parents=True)
            for name, value in (
                ("selection-v2-manifest.json", {}), ("timestamp-audit.json", {}),
                ("eligibility-review-v2.json", {"decisions": []}), ("price-acquisition.json", {}),
            ):
                (home / name).write_text(json.dumps(value))
            (analyzed / "results.json").write_text('{"results": []}')
            for name in ("summary.csv", "event-returns.csv", "latency5-summary.csv", "latency5-event-returns.csv"):
                (analyzed / name).write_text("coin,horizon_minutes,return_pct\n")
            (output / f"{news_event_report.PREFIX}_summary.csv").write_text("original summary")
            (repo / "research/NEWS-EVENT-STUDY.md").write_text("original report")
            before = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            with patch.dict(sys.modules, {"matplotlib": None}), self.assertRaises((ImportError, RuntimeError)):
                news_event_report.render(home, analyzed, repo)
            after = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            self.assertEqual(after, before)

    def test_bootstrap_owns_environment_and_reexecs_only_validated_arguments(self):
        class Reexec(BaseException):
            pass

        script = Path(news_event_report.__file__).resolve()
        arguments = ["--home", "/tmp/news-home", "--analyzed", "/tmp/news-analysis", "--repo", "/tmp/news-repo"]
        with (
            patch("backtester.run.ensure_environment", return_value=Path("/tmp/private-news-python")) as ensure,
            patch.dict(os.environ, {}, clear=True),
            patch("os.execve", side_effect=Reexec) as execute,
            self.assertRaises(Reexec),
        ):
            news_event_study._bootstrap_and_reexec(script, arguments)
        self.assertEqual(ensure.call_args.args, (script.parent,))
        self.assertEqual(ensure.call_args.kwargs["required_modules"], ("numpy", "matplotlib"))
        self.assertEqual(ensure.call_args.kwargs["owner"], "oraclebot-news-event-tools/v1")
        self.assertEqual(ensure.call_args.kwargs["entrypoint"], script)
        self.assertEqual(set(ensure.call_args.kwargs["requirements"]), {"numpy>=2.5.4", "matplotlib>=3.11.2"})
        self.assertEqual(execute.call_args.args[:2], ("/tmp/private-news-python", ["/tmp/private-news-python", str(script), *arguments]))
        self.assertEqual(execute.call_args.args[2]["ORACLEBOT_NEWS_REEXEC"], str(script))

    def test_report_only_and_reexec_failure_never_install_or_write(self):
        arguments = ["--home", "/tmp/absent-news-home", "--output", "/tmp/absent-news-output"]
        for environment in ({"TOOL_NO_VENV": "1"}, {"ORACLEBOT_NEWS_REEXEC": str(Path(news_event_study.__file__).resolve())}):
            with self.subTest(environment=environment), patch.dict(os.environ, environment, clear=True):
                with (
                    patch.dict(sys.modules, {"numpy": None}),
                    patch("backtester.run.ensure_environment") as ensure,
                    patch("os.execve") as execute,
                    patch("sys.stderr"),
                ):
                    self.assertEqual(news_event_study.main(arguments), 3)
                ensure.assert_not_called()
                execute.assert_not_called()

    def test_cli_missing_dependency_enters_owned_bootstrap_and_sanitizes_failure(self):
        arguments = ["--home", "/tmp/absent-news-home", "--output", "/tmp/absent-news-output"]
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(sys.modules, {"numpy": None}),
            patch("backtester.run.ensure_environment", side_effect=RuntimeError("PRIVATE_DEPENDENCY_CANARY")) as ensure,
            patch("os.execve") as execute,
            patch("sys.stderr") as stderr,
        ):
            self.assertEqual(news_event_study.main(arguments), 3)
        ensure.assert_called_once()
        execute.assert_not_called()
        messages = "".join(str(call.args[0]) for call in stderr.write.call_args_list)
        self.assertIn("numpy", messages)
        self.assertIn("RuntimeError", messages)
        self.assertNotIn("PRIVATE_DEPENDENCY_CANARY", messages)

    def test_preflight_names_every_unavailable_dependency(self):
        with (
            patch("importlib.import_module", side_effect=ImportError("PRIVATE_DEPENDENCY_CANARY")),
            self.assertRaisesRegex(RuntimeError, "numpy, matplotlib, matplotlib.pyplot") as raised,
        ):
            news_event_study._preflight(plotting=True)
        self.assertNotIn("PRIVATE_DEPENDENCY_CANARY", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

"""Tests for the pure soltui layer: indicator title, settings, roster, replay.

The load-bearing assertion in this file is that **no money figure in the
menu-bar title is ever unlabelled**. A naked '+9.4%' in a status bar reads as a
live account balance, and there is no live account. That property is asserted
directly rather than left to code review.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from backtester.core.data import SyntheticLoader, frame_to_arrays
from soltui.config import (
    ConfigError,
    Settings,
    default_settings,
    load_settings,
    save_settings,
    validate,
)
from soltui.paper import MODE_LABEL, PaperSession, start_session
from soltui.roster import Roster, RosterError, available_strategies
from soltui.runner import engine_config
from soltui.status import (
    ICONS,
    MAX_TITLE_CHARS,
    AppState,
    Phase,
    build_menu_summary,
    build_title,
    format_pct,
)


class TestIndicatorTitle(unittest.TestCase):
    """The menu-bar string."""

    def test_idle(self) -> None:
        """Idle says idle."""
        self.assertIn("idle", build_title(AppState()))

    def test_running_shows_work_remaining(self) -> None:
        """While sweeping, the count is the point."""
        s = AppState(phase=Phase.RUNNING, done=340, total=630, activity="backtest")
        title = build_title(s)
        self.assertIn("340/630", title)
        self.assertIn("backtest", title)

    def test_running_without_total_does_not_show_a_fake_denominator(self) -> None:
        """Unknown total must not render as '/0'."""
        title = build_title(AppState(phase=Phase.RUNNING, done=5, total=0))
        self.assertNotIn("/0", title)
        self.assertIn("running", title)

    def test_remaining_and_percent(self) -> None:
        """Derived progress figures."""
        s = AppState(phase=Phase.RUNNING, done=100, total=400)
        self.assertEqual(s.remaining, 100 + 200)  # 400-100 == 300
        self.assertAlmostEqual(s.percent, 0.25, places=6)

    def test_percent_is_none_when_total_unknown(self) -> None:
        """No total means no percentage, not a division by zero."""
        self.assertIsNone(AppState(total=0).percent)

    def test_running_outranks_a_stale_result(self) -> None:
        """A live sweep matters more than the previous number."""
        s = AppState(phase=Phase.RUNNING, done=1, total=10, last_backtest_return=0.5)
        self.assertNotIn("50.0%", build_title(s))

    # -- the load-bearing property -------------------------------------

    def test_backtest_pnl_is_always_labelled(self) -> None:
        """A money figure must never appear without its source."""
        s = AppState(phase=Phase.DONE, last_backtest_return=0.094)
        title = build_title(s)
        self.assertIn("+9.4%", title)
        self.assertIn("last backtest", title)

    def test_paper_pnl_is_always_labelled(self) -> None:
        """Same rule for the paper simulator."""
        s = AppState(phase=Phase.PAPER, paper_return=0.021, paper_fills=12)
        title = build_title(s)
        self.assertIn("+2.1%", title)
        self.assertIn("paper", title)

    def test_no_phase_produces_a_bare_percentage(self) -> None:
        """Exhaustive check across phases: any % is accompanied by a source word."""
        sources = ("last backtest", "paper")
        for phase in Phase:
            s = AppState(
                phase=phase, done=1, total=2, last_backtest_return=0.05,
                paper_return=0.05, paper_fills=1, error="boom", activity="x",
            )
            title = build_title(s)
            if "%" in title:
                self.assertTrue(
                    any(src in title for src in sources),
                    f"{phase}: title {title!r} shows a percentage with no source label",
                )

    def test_negative_return_is_signed(self) -> None:
        """Losses must read as losses."""
        s = AppState(phase=Phase.DONE, last_backtest_return=-0.708)
        self.assertIn("-70.8%", build_title(s))

    def test_format_pct_always_signs(self) -> None:
        """Unsigned percentages are ambiguous in a status bar."""
        self.assertEqual(format_pct(0.094), "+9.4%")
        self.assertEqual(format_pct(-0.094), "-9.4%")
        self.assertEqual(format_pct(0.0), "+0.0%")

    def test_error_phase_shows_the_error(self) -> None:
        """Failures must be visible, not silent.

        Asserts the failure GLYPH plus the message, not the literal word "error":
        the word is redundant next to ✕ and costs 8 characters that the actual
        message needs in a 40-char status item.
        """
        title = build_title(AppState(phase=Phase.ERROR, error="no data"))
        self.assertIn(ICONS["error"], title)
        self.assertIn("no data", title)

    def test_long_error_stays_readable(self) -> None:
        """A long message is truncated cleanly, not elided into fragments.

        An earlier version let _clip() handle it and produced unreadable output
        like "✕: …or — no data — run the fetch…".
        """
        title = build_title(
            AppState(phase=Phase.ERROR, error="no data — run the fetch command")
        )
        self.assertLessEqual(len(title), MAX_TITLE_CHARS)
        self.assertTrue(title.startswith(f"{ICONS['error']} SOL: no data"))
        self.assertNotIn("…or", title)

    def test_full_error_text_survives_in_the_menu(self) -> None:
        """Truncating the title must not lose the detail entirely."""
        long_err = "no data — run the fetch command"
        summary = " ".join(
            build_menu_summary(AppState(phase=Phase.ERROR, error=long_err))
        )
        self.assertIn(long_err, summary)

    def test_titles_stay_within_the_bar(self) -> None:
        """Long content is clipped, and clipping keeps the number."""
        s = AppState(
            phase=Phase.PAPER, paper_return=-0.7081234, paper_fills=999999,
        )
        title = build_title(s)
        self.assertLessEqual(len(title), MAX_TITLE_CHARS)

    def test_clip_preserves_the_number_not_the_label(self) -> None:
        """When something must go, the label goes first."""
        s = AppState(phase=Phase.RUNNING, activity="a" * 60, done=7, total=9)
        self.assertIn("7/9", build_title(s))


class TestMenuSummary(unittest.TestCase):
    """The dropdown has room for the caveat the title cannot fit."""

    def test_always_states_there_is_no_live_account(self) -> None:
        """This line is the whole point of the summary."""
        for state in (
            AppState(),
            AppState(phase=Phase.DONE, last_backtest_return=0.1),
            AppState(phase=Phase.PAPER, paper_return=0.1, paper_fills=3),
        ):
            joined = " ".join(build_menu_summary(state)).lower()
            self.assertIn("no live account", joined)

    def test_reports_remaining_while_running(self) -> None:
        """Progress detail belongs here too."""
        s = AppState(phase=Phase.RUNNING, done=10, total=40, activity="pairs")
        joined = " ".join(build_menu_summary(s))
        self.assertIn("30 left", joined)

    def test_labels_backtest_as_historical(self) -> None:
        """Even in the menu, a figure carries its nature."""
        s = AppState(phase=Phase.DONE, last_backtest_return=0.1)
        self.assertIn("historical", " ".join(build_menu_summary(s)).lower())


class TestSettings(unittest.TestCase):
    """Config validation, especially the safety defaults."""

    def test_defaults_are_dry_run_and_disarmed(self) -> None:
        """A fresh install must not be able to place an order."""
        s = default_settings()
        self.assertEqual(s.mode, "dry-run")
        self.assertFalse(s.armed)
        self.assertFalse(s.i_understand_this_is_simulated_only)

    def test_live_mode_is_rejected(self) -> None:
        """There is no live order path, so no config may select one."""
        with self.assertRaises(ConfigError):
            validate(Settings(mode="live"))

    def test_armed_requires_explicit_acknowledgement(self) -> None:
        """Arming cannot be inherited from an old config file."""
        with self.assertRaises(ConfigError):
            validate(Settings(armed=True))
        # With the acknowledgement it validates -- but mode is still dry-run.
        ok = validate(
            Settings(armed=True, i_understand_this_is_simulated_only=True)
        )
        self.assertEqual(ok.mode, "dry-run")

    def test_negative_fill_delay_rejected_as_look_ahead(self) -> None:
        """A negative delay would be look-ahead by configuration."""
        with self.assertRaises(ConfigError):
            validate(Settings(fill_delay=-1))

    def test_bad_interval_rejected_with_the_valid_list(self) -> None:
        """Fail at the form, not at data load."""
        with self.assertRaises(ConfigError):
            validate(Settings(interval="3d"))

    def test_cpcv_k_must_be_under_groups(self) -> None:
        """k >= groups leaves no training blocks."""
        with self.assertRaises(ConfigError):
            validate(Settings(cpcv_groups=4, cpcv_k=4))

    def test_round_trip(self) -> None:
        """Save then load reproduces the settings."""
        with TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            s = Settings(asset="SOL", capital=25_000.0, cpcv_groups=6, cpcv_k=2)
            save_settings(s, p)
            back = load_settings(p)
            self.assertEqual(back.capital, 25_000.0)
            self.assertEqual(back.cpcv_groups, 6)

    def test_unknown_keys_are_ignored_not_fatal(self) -> None:
        """A config from a newer build still opens."""
        import json

        with TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text(json.dumps({"asset": "SOL", "from_the_future": 1}))
            self.assertEqual(load_settings(p).asset, "SOL")

    def test_missing_file_yields_defaults(self) -> None:
        """First run must work with no config present."""
        with TemporaryDirectory() as d:
            self.assertEqual(
                load_settings(Path(d) / "absent.json").mode, "dry-run"
            )


class TestRoster(unittest.TestCase):
    """Strategy add/remove."""

    def test_default_roster_is_the_backtester_default_set(self) -> None:
        """Four strategies, buy_and_hold included as the baseline."""
        r = Roster.default()
        self.assertEqual(len(r), 4)
        self.assertTrue(any(e.name == "buy_and_hold" for e in r))

    def test_add_unknown_strategy_lists_the_valid_names(self) -> None:
        """A typo must fail here with help, not deep inside a sweep."""
        r = Roster()
        with self.assertRaises(RosterError) as ctx:
            r.add("mvoing_average")
        self.assertIn("Available:", str(ctx.exception))

    def test_add_validates_parameters_immediately(self) -> None:
        """An inverted fast/slow pair fails at the form."""
        r = Roster()
        with self.assertRaises(RosterError):
            r.add("ma_crossover", fast=50, slow=20)

    def test_add_rejects_unknown_parameter_names(self) -> None:
        """A misspelled kwarg is caught, not silently dropped."""
        r = Roster()
        with self.assertRaises(RosterError):
            r.add("ma_crossover", quick=5)

    def test_duplicates_rejected_by_generated_label(self) -> None:
        """Same strategy with same params is the same entry."""
        r = Roster()
        r.add("ma_crossover", fast=20, slow=50)
        with self.assertRaises(RosterError):
            r.add("ma_crossover", fast=20, slow=50)
        # Different params are a different entry, and allowed.
        r.add("ma_crossover", fast=10, slow=40)
        self.assertEqual(len(r), 2)

    def test_remove_by_label(self) -> None:
        """Removal uses the label the UI shows."""
        r = Roster.default()
        label = r.labels[1]
        r.remove(label)
        self.assertNotIn(label, r.labels)

    def test_remove_missing_lists_what_is_present(self) -> None:
        """The error should help, not just refuse."""
        r = Roster.default()
        with self.assertRaises(RosterError) as ctx:
            r.remove("nope")
        self.assertIn("Present:", str(ctx.exception))

    def test_entries_copy_is_not_a_backdoor(self) -> None:
        """Mutating the returned list must not change the roster."""
        r = Roster.default()
        r.entries.clear()
        self.assertEqual(len(r), 4)

    def test_families_and_max_warmup(self) -> None:
        """Derived fields the UI groups and gates on."""
        r = Roster.default()
        self.assertIn("trend", r.families)
        self.assertGreater(r.max_warmup(), 0)

    def test_serialisation_round_trip(self) -> None:
        """to_list/from_list preserves the roster."""
        r = Roster.default()
        back = Roster.from_list(r.to_list())
        self.assertEqual(r.labels, back.labels)

    def test_from_list_skips_entries_that_no_longer_load(self) -> None:
        """An old saved roster still opens."""
        back = Roster.from_list(
            [{"name": "buy_and_hold"}, {"name": "deleted_strategy"}]
        )
        self.assertEqual(len(back), 1)

    def test_available_strategies_covers_the_registry(self) -> None:
        """The Strategies tab list is complete."""
        from backtester.core.strategies import REGISTRY

        self.assertEqual(len(available_strategies()), len(REGISTRY))


class TestPaperSession(unittest.TestCase):
    """The dry-run replay."""

    @classmethod
    def setUpClass(cls) -> None:
        """One synthetic series and one session for the read-only assertions."""
        df = SyntheticLoader(n_bars=400, seed=9).load("SOL", None, None, "1d")
        cls.arrays = frame_to_arrays(df)
        from backtester.core.strategies import build

        cls.session = start_session(
            build("ma_crossover"), cls.arrays, engine_config(default_settings())
        )

    def test_mode_label_states_no_orders_are_placed(self) -> None:
        """The mode must be unambiguous in the UI."""
        self.assertIn("DRY RUN", MODE_LABEL)
        self.assertIn("no orders", MODE_LABEL.lower())

    def test_summary_reports_zero_live_orders(self) -> None:
        """Structurally always zero; asserted so a regression is loud."""
        self.assertEqual(self.session.summary()["live_orders_placed"], 0)

    def test_starts_at_the_first_bar(self) -> None:
        """A new session has not advanced."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        self.assertEqual(s.cursor, 0)
        self.assertAlmostEqual(s.pnl, 0.0, places=12)

    def test_advance_moves_and_clamps(self) -> None:
        """The cursor never runs past the final bar."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        s.advance(10)
        self.assertEqual(s.cursor, 10)
        s.advance(10**6)
        self.assertEqual(s.cursor, len(s) - 1)
        self.assertTrue(s.at_end)

    def test_advance_refuses_to_go_backwards(self) -> None:
        """Rewinding is reset()'s job, so a negative step is a bug."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        with self.assertRaises(ValueError):
            s.advance(-1)

    def test_reset_and_seek_end(self) -> None:
        """Navigation helpers."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        s.seek_end()
        self.assertTrue(s.at_end)
        s.reset()
        self.assertEqual(s.cursor, 0)

    def test_fills_are_never_ahead_of_the_cursor(self) -> None:
        """The replay must not reveal future activity."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        for stop in (10, 100, 250, len(s) - 1):
            s.reset()
            s.advance(stop)
            for fill in s.intended_fills():
                self.assertLessEqual(fill.bar_index, s.cursor)

    def test_fill_count_matches_intended_fills(self) -> None:
        """The two accessors must agree."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        s.advance(200)
        self.assertEqual(s.fill_count, len(s.intended_fills()))

    def test_pnl_matches_the_engine_at_the_end(self) -> None:
        """A replay of a backtest must reproduce that backtest's return."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        s.seek_end()
        expected = (
            self.session.result.equity[-1] / self.session.result.equity[0] - 1.0
        )
        self.assertAlmostEqual(s.pnl, float(expected), places=10)

    def test_fills_carry_a_readable_timestamp(self) -> None:
        """The Execute tab shows when, not just which bar."""
        s = PaperSession(self.session.result, self.arrays["ts"])
        s.seek_end()
        fills = s.intended_fills()
        if fills:
            self.assertRegex(fills[0].when, r"^\d{4}-\d{2}-\d{2}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

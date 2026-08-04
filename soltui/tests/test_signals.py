"""Tests for editable signal parameters.

The load-bearing property: **an explicit per-entry parameter always beats a signal
default.** Getting that direction backwards would mean the Signals tab silently
overwrites a value the user deliberately pinned in the Strategies tab, and the
symptom would be a strategy quietly not doing what its own label says.
"""

from __future__ import annotations

import unittest

from backtester.core.strategies import REGISTRY, build
from soltui.config import ConfigError, Settings, validate as validate_settings
from soltui.signals import (
    SIGNAL_GROUPS,
    STRATEGY_PARAM_MAP,
    SignalDefaults,
    SignalError,
    coerce,
    field_names,
    from_dict,
    mapped_strategies,
    merged_params,
    params_for,
    validate,
)


class TestPrecedence(unittest.TestCase):
    """Explicit params win over signal defaults."""

    def test_explicit_beats_default(self) -> None:
        """A pinned RSI period survives a different signal default."""
        d = SignalDefaults(rsi_period=14)
        merged = merged_params("rsi", d, {"period": 7})
        self.assertEqual(merged["period"], 7)

    def test_default_fills_what_was_not_pinned(self) -> None:
        """Unpinned fields still come from the defaults."""
        d = SignalDefaults(rsi_period=14, rsi_oversold=25.0)
        merged = merged_params("rsi", d, {"period": 7})
        self.assertEqual(merged["period"], 7)
        self.assertEqual(merged["oversold"], 25.0)

    def test_no_explicit_params_uses_all_defaults(self) -> None:
        """With nothing pinned the defaults apply wholesale."""
        d = SignalDefaults(sma_fast=5, sma_slow=99)
        merged = merged_params("ma_crossover", d, None)
        self.assertEqual(merged, {"fast": 5, "slow": 99})

    def test_merged_params_are_accepted_by_the_real_constructor(self) -> None:
        """Every mapped strategy must actually build from its merged params.

        This is what catches a rename on either side of STRATEGY_PARAM_MAP.
        """
        d = SignalDefaults()
        for name in mapped_strategies():
            with self.subTest(strategy=name):
                build(name, **merged_params(name, d))


class TestMapping(unittest.TestCase):
    """The map between signal fields and constructor kwargs."""

    def test_every_registered_strategy_is_mapped(self) -> None:
        """An unmapped strategy would silently ignore the Signals tab."""
        missing = set(REGISTRY) - set(STRATEGY_PARAM_MAP)
        self.assertEqual(missing, set(), f"unmapped strategies: {missing}")

    def test_every_mapped_field_exists(self) -> None:
        """A typo in the map would read a non-existent attribute."""
        names = set(field_names())
        for strategy, mapping in STRATEGY_PARAM_MAP.items():
            for kwarg, field in mapping.items():
                with self.subTest(strategy=strategy, kwarg=kwarg):
                    self.assertIn(field, names)

    def test_buy_and_hold_has_no_tunables(self) -> None:
        """It takes no parameters, so it must map to nothing."""
        self.assertEqual(params_for("buy_and_hold", SignalDefaults()), {})

    def test_unknown_strategy_returns_empty_rather_than_raising(self) -> None:
        """An unmapped name must still construct with its own defaults."""
        self.assertEqual(params_for("not_a_strategy", SignalDefaults()), {})

    def test_every_field_appears_in_a_ui_group(self) -> None:
        """A field absent from SIGNAL_GROUPS would be uneditable and invisible."""
        grouped = {n for _, names in SIGNAL_GROUPS for n in names}
        missing = set(field_names()) - grouped
        self.assertEqual(missing, set(), f"fields not in any group: {missing}")

    def test_no_field_is_listed_in_two_groups(self) -> None:
        """A duplicated field would render two inputs writing the same value."""
        seen: list[str] = [n for _, names in SIGNAL_GROUPS for n in names]
        self.assertEqual(len(seen), len(set(seen)))


class TestValidation(unittest.TestCase):
    """Bad values must fail in the form, not at sweep time."""

    def test_shipped_defaults_are_valid(self) -> None:
        """The values we ship must pass our own checks."""
        validate(SignalDefaults())

    def test_fast_must_be_shorter_than_slow(self) -> None:
        """Both for SMA and MACD."""
        with self.assertRaises(SignalError):
            validate(SignalDefaults(sma_fast=50, sma_slow=20))
        with self.assertRaises(SignalError):
            validate(SignalDefaults(macd_fast=26, macd_slow=12))

    def test_oversold_must_be_below_exit(self) -> None:
        """An inverted band would enter and exit on the same bar."""
        with self.assertRaises(SignalError):
            validate(SignalDefaults(rsi_oversold=60.0, rsi_exit=40.0))
        with self.assertRaises(SignalError):
            validate(SignalDefaults(stoch_oversold=90.0, stoch_exit=20.0))

    def test_zscore_entry_must_be_negative(self) -> None:
        """It is the oversold threshold a long reversion enters at."""
        with self.assertRaises(SignalError) as ctx:
            validate(SignalDefaults(zscore_entry=2.0))
        self.assertIn("negative", str(ctx.exception))

    def test_fractions_must_be_fractions(self) -> None:
        """A '5%' typed as 5 would be 500%."""
        for kwargs in ({"vwap_discount": 5.0}, {"grid_step": 1.5}):
            with self.subTest(**kwargs):
                with self.assertRaises(SignalError):
                    validate(SignalDefaults(**kwargs))

    def test_windows_must_be_at_least_one(self) -> None:
        """A zero-length window is not a window."""
        with self.assertRaises(SignalError):
            validate(SignalDefaults(bollinger_window=0))

    def test_positive_multipliers(self) -> None:
        """A non-positive band width collapses the channel."""
        with self.assertRaises(SignalError):
            validate(SignalDefaults(bollinger_std=0.0))
        with self.assertRaises(SignalError):
            validate(SignalDefaults(keltner_mult=-1.0))


class TestCoercion(unittest.TestCase):
    """Form strings become the declared type."""

    def test_int_field_stays_int(self) -> None:
        """A window must not silently become 20.0."""
        v = coerce("bollinger_window", "20", SignalDefaults())
        self.assertIsInstance(v, int)

    def test_float_field_becomes_float(self) -> None:
        """A threshold keeps its decimal."""
        v = coerce("bollinger_std", "2.5", SignalDefaults())
        self.assertIsInstance(v, float)
        self.assertAlmostEqual(v, 2.5)

    def test_blank_keeps_the_current_value(self) -> None:
        """Clearing a field should not zero it."""
        d = SignalDefaults(rsi_period=9)
        self.assertEqual(coerce("rsi_period", "   ", d), 9)

    def test_non_numeric_is_rejected_with_the_field_name(self) -> None:
        """The message must say which field."""
        with self.assertRaises(SignalError) as ctx:
            coerce("rsi_period", "fourteen", SignalDefaults())
        self.assertIn("rsi_period", str(ctx.exception))


class TestPersistence(unittest.TestCase):
    """Round-trip through config."""

    def test_from_dict_round_trip(self) -> None:
        """to_dict/from_dict preserves values."""
        d = SignalDefaults(rsi_period=9, bollinger_std=2.5)
        back = from_dict(d.to_dict())
        self.assertEqual(back.rsi_period, 9)
        self.assertAlmostEqual(back.bollinger_std, 2.5)

    def test_from_dict_ignores_unknown_keys(self) -> None:
        """A config from a newer build still loads."""
        self.assertEqual(from_dict({"rsi_period": 8, "invented": 1}).rsi_period, 8)

    def test_from_dict_validates(self) -> None:
        """An invalid stored value is caught on load, not on use."""
        with self.assertRaises(SignalError):
            from_dict({"sma_fast": 99, "sma_slow": 10})

    def test_empty_dict_yields_shipped_defaults(self) -> None:
        """First run has no stored signals."""
        self.assertEqual(from_dict({}).rsi_period, SignalDefaults().rsi_period)

    def test_settings_validation_surfaces_signal_errors(self) -> None:
        """A bad stored signal must fail as a ConfigError, one error type."""
        with self.assertRaises(ConfigError) as ctx:
            validate_settings(
                Settings(signal_defaults={"sma_fast": 99, "sma_slow": 10})
            )
        self.assertIn("signal_defaults", str(ctx.exception))

    def test_valid_signal_defaults_pass_settings_validation(self) -> None:
        """The happy path still works."""
        validate_settings(Settings(signal_defaults=SignalDefaults().to_dict()))


if __name__ == "__main__":
    unittest.main(verbosity=2)

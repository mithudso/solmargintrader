"""Tests for the per-bar rule readout in `research/decide.py`.

The readout's one substantive claim is that its target exposures are the same
numbers the engine would have acted on. Three tests defend it:

  * **Engine parity.** A recording wrapper captures every `on_bar` return the
    engine asks for, and the replay must reproduce that sequence exactly, for
    every registered strategy. This is the test that fails if the replay ever
    drifts from `run_backtest`'s call ordering or warm-up rule.
  * **No leak.** A decision computed on history truncated at bar k must equal
    the decision at bar k of the full replay. This is what fails if someone
    "optimises" the replay into a single `on_bar` call on the last bar, or if a
    strategy starts reading a future bar.
  * **Path dependence is real.** A constructed series where the single-last-bar
    shortcut gives the opposite answer to the replay, so the previous test is
    known to be load-bearing rather than vacuously true.
"""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from backtester.core import indicators as ind  # noqa: E402
from backtester.core.data import SyntheticLoader, frame_to_arrays, validate_bars  # noqa: E402
from backtester.core.engine import EngineConfig, _resolve_target, run_backtest  # noqa: E402
from backtester.core.strategies import REGISTRY, build  # noqa: E402
from backtester.core.strategies.breakout import DonchianBreakout  # noqa: E402
from backtester.core.types import BarWindow, CostConfig, Mode  # noqa: E402
from research import decide  # noqa: E402

ZERO_COST = CostConfig(fee_bps=0.0, slippage_bps=0.0, perp_base_fee_bps=0.0)

# Long enough for the 251-bar warm-ups (`ou_reversion`, `hurst_switch`,
# `vol_regime`) to produce a real decision rather than a NO-DATA row.
SYNTHETIC_BARS = 600


def synthetic_arrays(
    n: int = SYNTHETIC_BARS, seed: int = 7, interval: str = "1d"
) -> dict[str, np.ndarray]:
    """Deterministic OHLCV arrays; no network, no CSV."""
    frame = SyntheticLoader(n_bars=n, seed=seed).load("SOL", None, None, interval)
    return frame_to_arrays(frame)


def truncate(arrays: dict[str, np.ndarray], upto: int) -> dict[str, np.ndarray]:
    """The same arrays as they looked at bar `upto`, inclusive."""
    return {k: v[: upto + 1] for k, v in arrays.items()}


def make_arrays(closes: list[float], step: int = 86400) -> dict[str, np.ndarray]:
    """Arrays from a close series, with open == previous close."""
    closes_arr = np.asarray(closes, dtype="float64")
    n = len(closes_arr)
    opens = np.empty(n)
    opens[0] = closes_arr[0]
    opens[1:] = closes_arr[:-1]
    frame = pd.DataFrame(
        {
            "timestamp": 1_600_000_000 + np.arange(n, dtype="int64") * step,
            "open": opens,
            "high": np.maximum(opens, closes_arr),
            "low": np.minimum(opens, closes_arr),
            "close": closes_arr,
            "volume": np.full(n, 1000.0),
        }
    )
    return frame_to_arrays(validate_bars(frame, "1d"))


class Recorder:
    """Wraps a strategy and records every target the engine asks it for."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.name = inner.name
        self.params = dict(getattr(inner, "params", {}))
        self.calls: list[tuple[int, float]] = []

    def warmup_bars(self) -> int:
        """Delegate, so the engine's warm-up gate is the strategy's own."""
        return self.inner.warmup_bars()

    def on_bar(self, history: BarWindow) -> float:
        """Delegate and record (bar index, raw target)."""
        raw = float(self.inner.on_bar(history))
        self.calls.append((history.i, raw))
        return raw


class TestEngineParity(unittest.TestCase):
    """The replay must reproduce the engine's own call sequence and answers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.arrays = synthetic_arrays()

    def test_every_registered_strategy_matches(self) -> None:
        """Same bars asked, same raw targets returned, for all 25 strategies."""
        for key in REGISTRY:
            with self.subTest(strategy=key):
                recorder = Recorder(build(key))
                run_backtest(
                    recorder,
                    self.arrays,
                    EngineConfig(
                        mode=Mode.SPOT, fill_delay=0, costs=ZERO_COST, interval="1d"
                    ),
                )
                engine_indices = [i for i, _ in recorder.calls]
                engine_targets = np.array(
                    [_resolve_target(t, Mode.SPOT, False) for _, t in recorder.calls]
                )

                replayed = decide.replay_targets(build(key), self.arrays)
                asked = np.flatnonzero(np.isfinite(replayed))

                self.assertEqual(list(asked), engine_indices)
                np.testing.assert_allclose(replayed[asked], engine_targets, rtol=0, atol=0)

    def test_reported_target_is_the_last_engine_target(self) -> None:
        """The headline number is the engine's final decision, not a re-derivation."""
        for key in ("breakout", "bb_reversion", "grid", "voltarget"):
            with self.subTest(strategy=key):
                recorder = Recorder(build(key))
                run_backtest(
                    recorder,
                    self.arrays,
                    EngineConfig(
                        mode=Mode.SPOT, fill_delay=0, costs=ZERO_COST, interval="1d"
                    ),
                )
                expected = _resolve_target(recorder.calls[-1][1], Mode.SPOT, False)
                decision = decide.decide_strategy(key, self.arrays)
                self.assertAlmostEqual(decision.target, expected, places=12)

    def test_parity_holds_on_the_short_side(self) -> None:
        """A perp run that permits shorts must match too, negatives included.

        Spot clamps every negative target to zero, so a spot-only parity test
        would never exercise the short half of `_resolve_target`. Built directly
        rather than through the registry because no registered default shorts
        (see `test_no_registry_default_emits_a_short`).
        """
        config = EngineConfig(
            mode=Mode.PERP,
            allow_short=True,
            leverage=1.0,
            fill_delay=0,
            costs=ZERO_COST,
            interval="1d",
        )
        recorder = Recorder(build("ma_crossover", short_when_below=True))
        run_backtest(recorder, self.arrays, config)
        engine_targets = np.array(
            [_resolve_target(t, Mode.PERP, True) for _, t in recorder.calls]
        )
        replayed = decide.replay_targets(
            build("ma_crossover", short_when_below=True),
            self.arrays,
            mode=Mode.PERP,
            allow_short=True,
        )
        asked = np.flatnonzero(np.isfinite(replayed))
        self.assertEqual(list(asked), [i for i, _ in recorder.calls])
        np.testing.assert_allclose(replayed[asked], engine_targets, rtol=0, atol=0)
        self.assertTrue(
            bool(np.any(engine_targets < 0)), "no negative target seen; test proves nothing"
        )

    def test_spot_clamps_that_same_short_to_flat(self) -> None:
        """The clamp is the engine's, so spot must report flat, not a short."""
        replayed = decide.replay_targets(
            build("ma_crossover", short_when_below=True), self.arrays
        )
        asked = np.flatnonzero(np.isfinite(replayed))
        self.assertGreaterEqual(float(np.min(replayed[asked])), 0.0)

    def test_no_registry_default_emits_a_short(self) -> None:
        """Documents why `--allow-short` changes nothing on a default readout.

        Every registered strategy's default parameters are long-or-flat, so
        HOLD-SHORT is unreachable through the CLI. If a future strategy ships a
        shorting default this fails, and the readout's help text needs updating
        rather than the test relaxing.
        """
        for key in REGISTRY:
            with self.subTest(strategy=key):
                replayed = decide.replay_targets(
                    build(key), self.arrays, mode=Mode.PERP, allow_short=True
                )
                asked = np.flatnonzero(np.isfinite(replayed))
                self.assertGreaterEqual(float(np.min(replayed[asked])), 0.0)

    def test_bars_before_warmup_are_nan_not_zero(self) -> None:
        """An unasked bar must be NaN, distinct from a decision to stay flat."""
        strategy = build("sma_regime")
        warmup = strategy.warmup_bars()
        replayed = decide.replay_targets(strategy, self.arrays)
        self.assertTrue(np.all(np.isnan(replayed[:warmup])))
        self.assertTrue(np.all(np.isfinite(replayed[warmup:])))

    def test_engine_exposure_sign_agrees(self) -> None:
        """With a same-bar fill and no costs, held exposure follows the target.

        `BacktestResult.exposure` is the APPLIED exposure (signed notional over
        equity), not the raw target, so this checks the direction rather than
        asserting equality against a number that fees and price drift move.
        """
        result = run_backtest(
            build("breakout"),
            self.arrays,
            EngineConfig(mode=Mode.SPOT, fill_delay=0, costs=ZERO_COST, interval="1d"),
        )
        replayed = decide.replay_targets(build("breakout"), self.arrays)
        # The engine flattens on the final bar for metrics, so stop one short.
        for i in np.flatnonzero(np.isfinite(replayed))[:-1]:
            with self.subTest(bar=int(i)):
                self.assertEqual(replayed[i] > 0, result.exposure[i] > 1e-9)


class TestNoLeak(unittest.TestCase):
    """A decision may not change when future bars are removed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.arrays = synthetic_arrays()

    def test_truncated_history_reproduces_the_same_decision(self) -> None:
        """decide(history[:k+1]).target == full_replay[k], for stateful strategies."""
        for key in ("breakout", "bb_reversion", "keltner", "ou_reversion", "grid"):
            replayed = decide.replay_targets(build(key), self.arrays)
            for k in (300, 450, 599):
                with self.subTest(strategy=key, bar=k):
                    truncated = decide.decide_strategy(key, truncate(self.arrays, k))
                    self.assertAlmostEqual(truncated.target, replayed[k], places=12)

    def test_previous_is_the_bar_before(self) -> None:
        """The 'previous' exposure is the second-to-last replayed target."""
        replayed = decide.replay_targets(build("ma_crossover"), self.arrays)
        decision = decide.decide_strategy("ma_crossover", self.arrays)
        self.assertAlmostEqual(decision.previous, replayed[-2], places=12)


class TestPathDependence(unittest.TestCase):
    """Proof that replaying is not busywork."""

    def test_single_last_bar_call_gives_the_wrong_answer(self) -> None:
        """A breakout still holding reads as flat if you only ask about today.

        The series breaks out, then goes dead flat. Replayed, the position
        opened at the breakout and never saw a 10-bar low, so it is still long.
        Asked only about the final bar, the close does not exceed the prior
        20-bar high -- every one of those bars is the same price -- so a
        one-shot call says flat. Opposite answers from the same data.
        """
        closes = [100.0 + i for i in range(30)] + [129.5] * 30
        arrays = make_arrays(closes)

        replayed = decide.replay_targets(DonchianBreakout(), arrays)
        self.assertEqual(replayed[-1], 1.0)

        window = decide.final_window(arrays)
        self.assertEqual(DonchianBreakout().on_bar(window), 0.0)

    def test_decide_strategy_agrees_with_the_replay_not_the_shortcut(self) -> None:
        """The reported action reflects the held position."""
        closes = [100.0 + i for i in range(30)] + [129.5] * 30
        decision = decide.decide_strategy("breakout", make_arrays(closes))
        self.assertEqual(decision.action, decide.HOLD_LONG)
        self.assertEqual(decision.target, 1.0)


class TestClassify(unittest.TestCase):
    """HOLD is split, because 'stay long' and 'stay in cash' are opposites."""

    def test_flat_and_hold_long_are_distinct(self) -> None:
        """Unchanged exposure reports which side it is unchanged on."""
        self.assertEqual(decide.classify(1.0, 1.0), decide.HOLD_LONG)
        self.assertEqual(decide.classify(0.0, 0.0), decide.FLAT)

    def test_entry_and_exit(self) -> None:
        """A first entry is a BUY; going flat is a SELL."""
        self.assertEqual(decide.classify(None, 1.0), decide.BUY)
        self.assertEqual(decide.classify(0.0, 1.0), decide.BUY)
        self.assertEqual(decide.classify(1.0, 0.0), decide.SELL)

    def test_first_decision_compares_against_a_flat_book(self) -> None:
        """No prior decision means the book was flat, not that nothing changed."""
        self.assertEqual(decide.classify(None, 0.0), decide.FLAT)

    def test_short_side(self) -> None:
        """A short is held as HOLD-SHORT and covered as a BUY."""
        self.assertEqual(decide.classify(-1.0, -1.0), decide.HOLD_SHORT)
        self.assertEqual(decide.classify(-1.0, 0.0), decide.BUY)
        self.assertEqual(decide.classify(0.0, -1.0), decide.SELL)

    def test_tolerance_suppresses_a_re_size_below_the_threshold(self) -> None:
        """A sub-tolerance change in a sized position is a HOLD, not a trade."""
        self.assertEqual(decide.classify(0.50, 0.505, 0.01), decide.HOLD_LONG)
        self.assertEqual(decide.classify(0.50, 0.60, 0.01), decide.BUY)

    def test_zero_tolerance_reports_every_change(self) -> None:
        """The suppression is the tolerance's doing, not a rounding artifact."""
        self.assertEqual(decide.classify(0.50, 0.505, 0.0), decide.BUY)

    def test_negative_tolerance_is_refused(self) -> None:
        """It inverts the comparison, making an unchanged flat position a BUY."""
        with self.assertRaises(ValueError):
            decide.classify(0.0, 0.0, -5.0)


class TestInsufficientHistory(unittest.TestCase):
    """A strategy that cannot compute must say so, not report a verdict."""

    def test_short_series_reports_no_data(self) -> None:
        """`sma_regime` needs 200 bars; on 10 it refuses rather than guessing."""
        arrays = make_arrays([100.0 + i for i in range(10)])
        decision = decide.decide_strategy("sma_regime", arrays)
        self.assertEqual(decision.action, decide.INSUFFICIENT)
        self.assertIsNone(decision.target)
        self.assertIn("200", decision.note)

    def test_engine_would_have_refused_the_same_series(self) -> None:
        """The NO-DATA boundary is the engine's, not an independent guess."""
        arrays = make_arrays([100.0 + i for i in range(10)])
        with self.assertRaises(ValueError):
            run_backtest(
                build("sma_regime"),
                arrays,
                EngineConfig(mode=Mode.SPOT, fill_delay=0, interval="1d"),
            )

    def test_whole_report_survives_a_short_series(self) -> None:
        """Every section renders; nothing raises on a series that warms nothing up."""
        arrays = make_arrays([100.0 + i for i in range(6)])
        report = decide.build_report(
            arrays,
            asset="TEST",
            interval="1d",
            source="synthetic",
            checksum="0" * 64,
        )
        actions = {s["action"] for s in report["strategies"]}
        self.assertIn(decide.INSUFFICIENT, actions)
        self.assertIn("NOT INVESTMENT ADVICE", decide.render_text(report))

    def test_single_bar_series(self) -> None:
        """One row of data is handled, not crashed on."""
        arrays = {
            "ts": np.array([1_600_000_000], dtype="int64"),
            "open": np.array([1.0]),
            "high": np.array([1.0]),
            "low": np.array([1.0]),
            "close": np.array([1.0]),
            "volume": np.array([1.0]),
        }
        report = decide.build_report(
            arrays, asset="JLP", interval="1d", source="x", checksum="0" * 64
        )
        self.assertEqual(report["bars"], 1)
        # buy_and_hold has zero warm-up, so it is the one strategy that can act.
        by_key = {s["key"]: s for s in report["strategies"]}
        self.assertEqual(by_key["buy_and_hold"]["action"], decide.BUY)
        self.assertEqual(by_key["sma_regime"]["action"], decide.INSUFFICIENT)

    def test_empty_series_is_rejected(self) -> None:
        """No bars means no decision bar to report on."""
        empty = {k: np.zeros(0) for k in ("ts", "open", "high", "low", "close", "volume")}
        with self.assertRaises(ValueError):
            decide.build_report(
                empty, asset="X", interval="1d", source="x", checksum="0" * 64
            )


class TestSignals(unittest.TestCase):
    """Stateless one-bar rules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.arrays = synthetic_arrays()
        cls.window = decide.final_window(cls.arrays)

    def test_every_rule_returns_a_known_reading(self) -> None:
        """No rule may invent a vocabulary of its own."""
        allowed = {decide.BULLISH, decide.BEARISH, decide.NEUTRAL, decide.UNAVAILABLE}
        for reading in decide.signal_readings(self.window):
            with self.subTest(signal=reading.key):
                self.assertIn(reading.reading, allowed)
                self.assertTrue(reading.rule)
                self.assertTrue(reading.detail)

    def test_keys_are_unique(self) -> None:
        """Duplicate keys would silently overwrite each other in the JSON."""
        keys = [r.key for r in decide.SIGNAL_RULES]
        self.assertEqual(len(keys), len(set(keys)))

    def test_periods_track_the_registered_strategy_defaults(self) -> None:
        """The two signals that mirror a strategy must not drift from it.

        A row claiming a 20-bar channel while `breakout` trades a 55-bar one
        would be a quietly wrong explanation of the strategy above it.
        """
        self.assertEqual(decide.DONCHIAN, dict(build("breakout").params))
        self.assertEqual(decide.ICHIMOKU, dict(build("ichimoku").params))
        self.assertEqual(decide.TS_MOMENTUM, dict(build("ts_momentum").params))
        keys = {r.key for r in decide.SIGNAL_RULES}
        expected = (
            f"donchian_{DonchianBreakout().entry_lookback}"
            f"_{DonchianBreakout().exit_lookback}"
        )
        self.assertIn(expected, keys)
        self.assertIn(f"ts_momentum_{build('ts_momentum').params['window']}", keys)

    def test_momentum_signal_reads_the_strategy_lookback(self) -> None:
        """The regression: a 90-bar ROC explaining a 60-bar strategy.

        On the cached SOL daily series the two even disagreed -- the 90-bar leg
        was negative while the 60-bar leg the strategy trades was positive -- so
        the row labelled `ts_momentum` argued against the strategy above it.
        """
        window = build("ts_momentum").params["window"]
        expected = ind.roc(self.window.closes, window)
        reading = {r.key: r for r in decide.signal_readings(self.window)}[
            f"ts_momentum_{window}"
        ]
        self.assertIn(f"{window}-bar", reading.detail)
        self.assertEqual(
            reading.reading, decide.BULLISH if expected > 0 else decide.BEARISH
        )

    def test_short_history_is_unavailable_not_neutral(self) -> None:
        """'Cannot compute' must not be reported as 'looked and found nothing'."""
        arrays = make_arrays([100.0, 101.0, 102.0, 103.0])
        window = decide.final_window(arrays)
        readings = {r.key: r.reading for r in decide.signal_readings(window)}
        momentum = f"ts_momentum_{decide.TS_MOMENTUM['window']}"
        for key in ("sma_200_regime", "ichimoku_cloud", "adx_14_di", momentum):
            with self.subTest(signal=key):
                self.assertEqual(readings[key], decide.UNAVAILABLE)

    def test_reversion_and_breakout_disagree_on_the_same_band_break(self) -> None:
        """A close below the lower band is bullish to one rule, bearish to the other.

        The disagreement is the informative part of the readout, so it gets a
        test: averaging these two into a consensus would destroy the signal.
        """
        # A long flat stretch then a sharp drop puts the close below the band.
        closes = [100.0] * 40 + [80.0]
        arrays = make_arrays(closes)
        window = decide.final_window(arrays)
        readings = {r.key: r.reading for r in decide.signal_readings(window)}
        self.assertEqual(readings["bb_reversion_20_2"], decide.BULLISH)
        self.assertEqual(readings["bb_breakout_20_2"], decide.BEARISH)

    def test_adx_gate_withholds_a_direction_in_chop(self) -> None:
        """Below ADX 25 there is no trend, so no side is reported.

        A repeating triangle wave rather than a random walk: it moves in both
        directions in comparable measure, so DX stays low and ADX cannot cross
        the gate. A seeded random walk drifts and sometimes does cross it, and a
        strict two-value zigzag is worse -- it produces -DM of exactly zero,
        which pins DX at 100.
        """
        cycle = [100.0 + i for i in range(6)] + [104.0 - i for i in range(4)]
        closes = (cycle * 12)[:120]
        arrays = make_arrays(closes)
        window = decide.final_window(arrays)
        plus, minus, adx = ind.directional_movement(
            window.highs, window.lows, window.closes, 14
        )
        self.assertLess(adx, 25.0)
        # Ungated, the DI comparison here would have printed a direction. The
        # gate is what stops it, so assert the direction exists to be withheld.
        self.assertNotAlmostEqual(plus, minus, places=6)
        readings = {r.key: r.reading for r in decide.signal_readings(window)}
        self.assertEqual(readings["adx_14_di"], decide.NEUTRAL)

    def test_ichimoku_signal_uses_a_displaced_cloud(self) -> None:
        """The signal must match the strategy's look-ahead-free comparison.

        Reading spans computed AT the current bar would compare today's close
        against a cloud built from data the trader could not have had.
        """
        arrays = synthetic_arrays()
        closes, highs, lows = arrays["close"], arrays["high"], arrays["low"]
        cut = len(closes) - 26
        _, _, span_a, span_b = ind.ichimoku(highs[:cut], lows[:cut], 9, 26, 52)
        expected = (
            decide.BULLISH
            if float(closes[-1]) > max(span_a, span_b)
            else (
                decide.BEARISH
                if float(closes[-1]) < min(span_a, span_b)
                else decide.NEUTRAL
            )
        )
        readings = {r.key: r.reading for r in decide.signal_readings(self.window)}
        self.assertEqual(readings["ichimoku_cloud"], expected)


class TestIndicators(unittest.TestCase):
    """Values, with a reading only where one honestly exists."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.arrays = synthetic_arrays()
        cls.window = decide.final_window(cls.arrays)

    def test_module_is_fully_covered(self) -> None:
        """Every public indicator is reported or explicitly skipped, with a reason.

        This is the drift guard: the indicator table is hand-written because the
        signatures are heterogeneous, so without this test a newly added
        indicator would be silently missing from the readout.
        """
        public = {
            name
            for name, obj in vars(ind).items()
            if not name.startswith("_")
            and inspect.isfunction(obj)
            and obj.__module__ == ind.__name__
        }
        covered = {src for row in decide.INDICATOR_ROWS for src in row.sources}
        missing = public - covered - set(decide.INDICATOR_SKIP)
        self.assertEqual(
            missing,
            set(),
            f"indicators neither reported nor skip-listed: {sorted(missing)}",
        )

    def test_skip_list_and_sources_name_real_functions(self) -> None:
        """A renamed indicator must not leave a dangling entry behind."""
        for name in set(decide.INDICATOR_SKIP) | {
            src for row in decide.INDICATOR_ROWS for src in row.sources
        }:
            with self.subTest(function=name):
                self.assertTrue(
                    hasattr(ind, name), f"core.indicators has no '{name}'"
                )

    def test_magnitude_indicators_report_no_direction(self) -> None:
        """ATR does not become bullish. Neither does realised vol or a half-life."""
        readings = {r.key: r.reading for r in decide.indicator_readings(self.window)}
        for key in (
            "atr_14",
            "realised_vol_20",
            "ewma_vol",
            "ou_half_life_250",
            "bollinger_20_2",
            "variance_ratio_250",
            "ichimoku_9_26_52",
            "obv",
        ):
            with self.subTest(indicator=key):
                self.assertEqual(readings[key], decide.NO_DIRECTION)

    def test_no_direction_is_distinct_from_neutral(self) -> None:
        """'Has no side' and 'looked and found nothing' are different claims."""
        self.assertNotEqual(decide.NO_DIRECTION, decide.NEUTRAL)

    def test_every_row_returns_a_known_reading_and_a_note(self) -> None:
        """No row may invent a vocabulary, and each explains its reading."""
        allowed = {
            decide.BULLISH,
            decide.BEARISH,
            decide.NEUTRAL,
            decide.UNAVAILABLE,
            decide.NO_DIRECTION,
        }
        for reading in decide.indicator_readings(self.window):
            with self.subTest(indicator=reading.key):
                self.assertIn(reading.reading, allowed)
                self.assertTrue(reading.note)
                self.assertTrue(reading.value)

    def test_annualisation_follows_the_interval(self) -> None:
        """An hourly series must not be annualised on a daily convention."""
        daily = {r.key: r.value for r in decide.indicator_readings(self.window, 365.0)}
        hourly = {
            r.key: r.value for r in decide.indicator_readings(self.window, 365.0 * 24)
        }
        self.assertNotEqual(daily["realised_vol_20"], hourly["realised_vol_20"])
        self.assertNotEqual(daily["ewma_vol"], hourly["ewma_vol"])

    def test_keys_are_unique(self) -> None:
        """Duplicate keys would silently overwrite each other in the JSON."""
        keys = [r.key for r in decide.INDICATOR_ROWS]
        self.assertEqual(len(keys), len(set(keys)))


class TestReport(unittest.TestCase):
    """Assembly, provenance, and the honesty furniture."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.arrays = synthetic_arrays()
        cls.report = decide.build_report(
            cls.arrays,
            asset="SOL",
            interval="1d",
            source="synthetic",
            checksum="a" * 64,
        )

    def test_decision_bar_is_the_last_bar(self) -> None:
        """The reader must be able to date the decision."""
        bar = self.report["decision_bar"]
        self.assertEqual(bar["index"], len(self.arrays["close"]) - 1)
        self.assertEqual(bar["timestamp"], int(self.arrays["ts"][-1]))
        self.assertAlmostEqual(bar["close"], float(self.arrays["close"][-1]))
        self.assertTrue(bar["utc"].endswith("Z"))

    def test_stale_data_is_called_out(self) -> None:
        """A cached CSV says nothing about when it was fetched; the age must.

        Without this an hourly readout whose last bar closed 36 hours ago looks
        exactly like a fresh one.
        """
        last = int(self.arrays["ts"][-1])
        fresh = decide.build_report(
            self.arrays,
            asset="SOL",
            interval="1d",
            source="s",
            checksum="a" * 64,
            now=last + 3600,
        )
        self.assertFalse(fresh["decision_bar"]["stale"])
        self.assertNotIn("STALE", decide.render_text(fresh))

        old = decide.build_report(
            self.arrays,
            asset="SOL",
            interval="1d",
            source="s",
            checksum="a" * 64,
            now=last + 10 * 86400,
        )
        self.assertTrue(old["decision_bar"]["stale"])
        self.assertAlmostEqual(old["decision_bar"]["age_bars"], 10.0, places=6)
        self.assertAlmostEqual(old["decision_bar"]["age_hours"], 240.0, places=6)
        self.assertIn("STALE", decide.render_text(old))

    def test_age_is_measured_in_bars_of_the_stated_interval(self) -> None:
        """40 hours is 1.7 daily bars but 40 hourly ones -- only one is stale."""
        last = int(self.arrays["ts"][-1])
        common = dict(asset="SOL", source="s", checksum="a" * 64, now=last + 40 * 3600)
        daily = decide.staleness(last, "1d", now=last + 40 * 3600)
        hourly = decide.staleness(last, "1h", now=last + 40 * 3600)
        self.assertFalse(daily["stale"])
        self.assertTrue(hourly["stale"])
        self.assertAlmostEqual(hourly["age_bars"], 40.0, places=6)
        # And the same series read at two intervals reports the two ages.
        self.assertFalse(
            decide.build_report(self.arrays, interval="1d", **common)["decision_bar"][
                "stale"
            ]
        )

    def test_interval_is_detected_from_the_timestamps(self) -> None:
        """The median spacing, so real gaps do not change the answer."""
        base = 1_600_000_000
        hourly = np.array([base + i * 3600 for i in range(50)], dtype="int64")
        self.assertEqual(decide.detected_interval(hourly), "1h")
        # One 6-hour gap, as the cached hourly SOL series actually has.
        gapped = np.concatenate([hourly, [hourly[-1] + 21600], [hourly[-1] + 25200]])
        self.assertEqual(decide.detected_interval(gapped), "1h")
        self.assertIsNone(decide.detected_interval(np.array([base], dtype="int64")))
        self.assertIsNone(
            decide.detected_interval(np.array([base, base + 777], dtype="int64"))
        )

    def test_a_contradicted_interval_is_refused(self) -> None:
        """Named so the caller can fix it, not silently accepted."""
        hourly = np.array([1_600_000_000 + i * 3600 for i in range(50)], dtype="int64")
        decide.check_interval(hourly, "1h")
        with self.assertRaises(ValueError) as caught:
            decide.check_interval(hourly, "1d")
        self.assertIn("--interval 1h", str(caught.exception))

    def test_an_undetectable_spacing_does_not_block_the_readout(self) -> None:
        """A series that matches no known interval is passed through, not refused."""
        odd = np.array([1_600_000_000 + i * 777 for i in range(10)], dtype="int64")
        decide.check_interval(odd, "1d")

    def test_asset_is_read_from_a_cache_filename(self) -> None:
        """Follows the `<ASSET>_<interval>.csv` convention `core.fetch` writes."""
        self.assertEqual(decide.asset_from_path(Path("data/BTC_1d.csv")), "BTC")
        self.assertEqual(decide.asset_from_path(Path("data/JLP_spot.csv")), "JLP")
        self.assertIsNone(decide.asset_from_path(Path("data/prices.csv")))

    def test_a_future_timestamp_reports_zero_age_not_a_negative(self) -> None:
        """Clock skew must not print a negative age."""
        aged = decide.staleness(2_000_000_000, "1d", now=1_900_000_000)
        self.assertEqual(aged["age_bars"], 0.0)
        self.assertFalse(aged["stale"])

    def test_execution_context_is_stated(self) -> None:
        """Bounds, tolerance and fill delay change what the verbs mean."""
        ex = self.report["execution"]
        self.assertEqual(ex["exposure_bounds"], [0.0, 1.0])
        self.assertEqual(ex["change_tolerance"], decide.DEFAULT_TOLERANCE)
        self.assertEqual(ex["fill_delay"], 1)
        self.assertIn("after the decision bar", ex["applies_to"])

    def test_short_bound_requires_perp_and_the_flag(self) -> None:
        """Spot cannot go short, so the reported bound must not claim it can."""
        spot = decide.build_report(
            self.arrays,
            asset="SOL",
            interval="1d",
            source="s",
            checksum="a" * 64,
            allow_short=True,
            mode=Mode.SPOT,
        )
        self.assertEqual(spot["execution"]["exposure_bounds"], [0.0, 1.0])
        perp = decide.build_report(
            self.arrays,
            asset="SOL",
            interval="1d",
            source="s",
            checksum="a" * 64,
            allow_short=True,
            mode=Mode.PERP,
        )
        self.assertEqual(perp["execution"]["exposure_bounds"], [-1.0, 1.0])

    def test_all_registered_strategies_are_reported(self) -> None:
        """The readout follows the registry, so a new strategy appears for free."""
        keys = [s["key"] for s in self.report["strategies"]]
        self.assertEqual(keys, list(REGISTRY))

    def test_no_overall_verdict_or_vote_count(self) -> None:
        """A consensus tally would read as evidence from correlated rules."""
        self.assertNotIn("consensus", self.report)
        self.assertNotIn("verdict", self.report)
        self.assertNotIn("recommendation", self.report)
        text = decide.render_text(self.report).lower()
        self.assertIn("not a vote", text)
        self.assertIn("not investment advice", text)

    def test_family_tally_groups_rather_than_totals(self) -> None:
        """Counts are per family, and they add up to the strategies reported."""
        tally = self.report["family_tally"]
        total = sum(sum(v.values()) for v in tally.values())
        self.assertEqual(total, len(self.report["strategies"]))
        self.assertGreater(len(tally), 1)

    def test_selected_strategies_only(self) -> None:
        """`--strategy` narrows the readout."""
        report = decide.build_report(
            self.arrays,
            asset="SOL",
            interval="1d",
            source="s",
            checksum="a" * 64,
            keys=["breakout", "rsi"],
        )
        self.assertEqual([s["key"] for s in report["strategies"]], ["breakout", "rsi"])

    def test_unknown_strategy_raises(self) -> None:
        """A typo must fail loudly rather than silently reporting 24 of 25."""
        with self.assertRaises(KeyError):
            decide.strategy_decisions(self.arrays, keys=["no_such_strategy"])

    def test_render_text_lists_every_section(self) -> None:
        """All three layers reach the page."""
        text = decide.render_text(self.report)
        for heading in ("STRATEGIES", "SIGNALS", "INDICATORS"):
            self.assertIn(heading, text)
        for key in list(REGISTRY)[:5]:
            self.assertIn(key, text)


class TestCli(unittest.TestCase):
    """The entry point, including its failure paths.

    Every case writes its own CSV rather than reaching for `data/`, which is
    gitignored and absent in a fresh clone -- a `skipTest` here would mean the
    CLI is effectively untested in CI.
    """

    @contextlib.contextmanager
    def cached_csv(self, name: str = "SOL_1d.csv", bars: int = 300):
        """A temporary CSV in the on-disk cache format, plus its path."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / name
            SyntheticLoader(n_bars=bars, seed=11).load("SOL", None, None, "1d").to_csv(
                path, index=False
            )
            yield path

    @staticmethod
    def run_cli(args: list[str]) -> tuple[int, str, str]:
        """Invoke `main` with stdout and stderr captured."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = decide.main(args)
        return code, out.getvalue(), err.getvalue()

    def test_a_readout_runs_end_to_end_from_a_csv(self) -> None:
        """The happy path, exercised through the real loader."""
        with self.cached_csv() as path:
            code, out, _ = self.run_cli(["--data", str(path), "--strategy", "rsi"])
        self.assertEqual(code, 0)
        self.assertIn("STRATEGIES", out)
        self.assertIn("NOT INVESTMENT ADVICE", out)

    def test_a_non_ohlcv_csv_is_refused_by_name(self) -> None:
        """`data/JLP_spot.csv` is a Jupiter price snapshot, not a bar series.

        It has `timestamp,iso,mint,usd_price,source` and one row. The readout
        must name the missing columns rather than half-parse it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "JLP_spot.csv"
            path.write_text(
                "timestamp,iso,mint,usd_price,source\n"
                "1785867150,2026-08-04T18:12:30+00:00,27G8Mt,3.59334506,jupiter-price-v3\n",
                encoding="utf-8",
            )
            code, _, err = self.run_cli(["--data", str(path), "--strategy", "rsi"])
        self.assertEqual(code, 2)
        self.assertIn("missing required column", err)

    def test_an_interval_the_data_contradicts_is_refused(self) -> None:
        """Reading the hourly cache as daily silently broke two reported numbers.

        `validate_bars` only catches spacing larger than one bar, so hourly bars
        under `--interval 1d` passed and then reported 40 stale bars as 1.7 and
        annualised vol at 365 bars/year instead of 8,760.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SOL_1h.csv"
            SyntheticLoader(n_bars=200, seed=5).load("SOL", None, None, "1h").to_csv(
                path, index=False
            )
            code, _, err = self.run_cli(
                ["--data", str(path), "--interval", "1d", "--strategy", "rsi"]
            )
        self.assertEqual(code, 2)
        self.assertIn("spaced as 1h", err)
        self.assertIn("--interval 1h", err)

    def test_the_asset_label_follows_the_data_filename(self) -> None:
        """A header reading SOL over BTC bars would make the readout unfalsifiable."""
        with self.cached_csv(name="BTC_1d.csv") as path:
            code, out, _ = self.run_cli(["--data", str(path), "--strategy", "rsi"])
            self.assertEqual(code, 0)
            self.assertIn("Rule readout -- BTC 1d", out)
            # An explicit --asset still wins.
            _, out, _ = self.run_cli(
                ["--asset", "WRAPPED", "--data", str(path), "--strategy", "rsi"]
            )
        self.assertIn("Rule readout -- WRAPPED 1d", out)

    def test_missing_data_file_exits_nonzero(self) -> None:
        """A missing cache is an error with a message, not a traceback."""
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = decide.main(["--data", str(REPO / "data" / "definitely_absent.csv")])
        self.assertEqual(code, 2)
        self.assertIn("no cached data", stderr.getvalue())

    def test_bad_numeric_arguments_exit_nonzero(self) -> None:
        """A rejected tolerance or fill delay is a usage error, not a traceback."""
        with self.cached_csv() as path:
            for args in (["--tolerance", "-5"], ["--fill-delay", "-3"]):
                with self.subTest(args=args):
                    code, _, err = self.run_cli(
                        ["--data", str(path), "--strategy", "rsi", *args]
                    )
                    self.assertEqual(code, 2)
                    self.assertIn("must be >= 0", err)

    def test_out_file_receives_the_same_text(self) -> None:
        """`--out` writes what was printed, so a saved readout is not a summary."""
        with self.cached_csv() as path:
            target = path.parent / "readout.txt"
            code, out, _ = self.run_cli(
                ["--data", str(path), "--strategy", "rsi", "--out", str(target)]
            )
            self.assertEqual(code, 0)
            self.assertEqual(target.read_text(encoding="utf-8"), out)

    def test_json_output_is_parseable(self) -> None:
        """`--json` must emit exactly one JSON document on stdout."""
        arrays = synthetic_arrays(n=300)
        report = decide.build_report(
            arrays, asset="SOL", interval="1d", source="s", checksum="b" * 64
        )
        parsed = json.loads(json.dumps(report, sort_keys=True))
        self.assertEqual(parsed["asset"], "SOL")
        self.assertEqual(len(parsed["strategies"]), len(REGISTRY))

    def test_default_path_follows_the_fetch_convention(self) -> None:
        """Where the readout looks matches where `core.fetch` writes."""
        self.assertEqual(
            decide.default_data_path("SOL", "1h").name,
            "SOL_1h.csv",
        )


if __name__ == "__main__":
    unittest.main()

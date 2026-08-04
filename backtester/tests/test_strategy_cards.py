"""Tests for strategy cards.

These are the tests that make a card a contract rather than a claim. Prose in a
card can be wrong and no test will catch it; a *number* in a card is checked
against the code that would use it.

Drift is checked in both directions, because both failures are silent:

* a card declares a default the constructor no longer has, or
* a registry entry has no card at all / a card names a registry key that is gone.

A third check ties in `research/sweep.py`: where both declare per-horizon
parameters for the same strategy, they must agree. Otherwise the card documents
one experiment and the sweep runs another.
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
import unittest
from pathlib import Path

import numpy as np

from backtester.core import strategy_cards as sc
from backtester.core.engine import EngineConfig, run_backtest
from backtester.core.strategies import FAMILY, REGISTRY
from backtester.core.types import CostConfig

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def constructor_defaults(factory) -> dict:
    """Declared defaults of a strategy class's __init__, excluding self."""
    sig = inspect.signature(factory.__init__)
    return {
        p.name: p.default
        for p in list(sig.parameters.values())[1:]
        if p.default is not inspect.Parameter.empty
    }


def synthetic_bars(n: int = 400, seed: int = 7) -> dict[str, np.ndarray]:
    """A deterministic OHLCV series long enough for a 200-bar warmup."""
    rng = np.random.default_rng(seed)
    close = 100.0 * np.exp(np.cumsum(rng.normal(0.0, 0.02, n)))
    high = close * 1.01
    low = close * 0.99
    return {
        "ts": np.arange(n, dtype="int64") * 86400 + 1_600_000_000,
        "open": close,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.full(n, 1_000.0),
    }


class TestFrontmatterParser(unittest.TestCase):
    """The parser accepts a documented subset and refuses everything else."""

    def test_parses_every_supported_form(self) -> None:
        data, body = sc.parse_frontmatter(
            "\n".join(
                [
                    "---",
                    "id: demo",
                    "count: 12",
                    "ratio: 2.5",
                    "flag: true",
                    "missing: null",
                    'quoted: "a: b"',
                    "bare: some words here",
                    "seq: [ohlcv, funding]",
                    "flow: {a: 1, b: two}",
                    "block:",
                    "  first: 1",
                    "  second: {x: 2.0}",
                    "---",
                    "",
                    "# Body",
                ]
            )
        )
        self.assertEqual(data["id"], "demo")
        self.assertEqual(data["count"], 12)
        self.assertEqual(data["ratio"], 2.5)
        self.assertIs(data["flag"], True)
        self.assertIsNone(data["missing"])
        self.assertEqual(data["quoted"], "a: b")
        self.assertEqual(data["bare"], "some words here")
        self.assertEqual(data["seq"], ["ohlcv", "funding"])
        self.assertEqual(data["flow"], {"a": 1, "b": "two"})
        self.assertEqual(data["block"], {"first": 1, "second": {"x": 2.0}})
        self.assertIn("# Body", body)

    def test_refuses_what_it_does_not_support(self) -> None:
        cases = {
            "no fence": "id: demo\n",
            "unclosed": "---\nid: demo\n",
            "tab": "---\nid:\tdemo\n---\n",
            "block sequence": "---\nseq:\n  - one\n---\n",
            "deep nesting": "---\na:\n  b:\n      c: 1\n---\n",
            "no colon": "---\njust a line\n---\n",
            "unterminated flow": "---\nseq: [a, b\n---\n",
            "nest under scalar": "---\na: 1\n  b: 2\n---\n",
        }
        for label, text in cases.items():
            with self.subTest(label), self.assertRaises(sc.CardError):
                sc.parse_frontmatter(text, where=label)


class TestCardsLoad(unittest.TestCase):
    def setUp(self) -> None:
        self.cards = sc.load_all()

    def test_every_card_loads_and_is_named_after_its_id(self) -> None:
        self.assertGreater(len(self.cards), 0, "no cards found")
        for card_id, card in self.cards.items():
            self.assertEqual(card_id, card.path.stem)
            self.assertTrue(card.summary, f"{card_id}: summary must not be empty")
            self.assertTrue(card.body, f"{card_id}: body must not be empty")

    def test_every_card_states_its_data_requirements(self) -> None:
        for card_id, card in self.cards.items():
            self.assertTrue(
                card.data_required,
                f"{card_id}: data_required must list at least one input",
            )

    def test_measured_cards_carry_evaluation_provenance(self) -> None:
        # A number with no stated evaluation method is a number nobody can weigh.
        for card_id, card in self.cards.items():
            if card.status == "measured":
                self.assertTrue(
                    card.evaluation,
                    f"{card_id}: a measured card must state how it was evaluated",
                )


class TestRegistryDrift(unittest.TestCase):
    """Both directions. Either one failing silently is how cards rot."""

    def setUp(self) -> None:
        self.cards = sc.load_all()
        self.by_key = {c.registry_key: c for c in self.cards.values() if c.registry_key}

    def test_every_registry_strategy_has_a_card(self) -> None:
        missing = sorted(set(REGISTRY) - set(self.by_key))
        self.assertEqual(
            missing, [], f"registry strategies with no card: {missing}"
        )

    def test_every_card_registry_key_exists(self) -> None:
        unknown = sorted(set(self.by_key) - set(REGISTRY))
        self.assertEqual(
            unknown, [], f"cards naming a strategy that no longer exists: {unknown}"
        )

    def test_declared_defaults_match_the_constructors(self) -> None:
        for key, card in self.by_key.items():
            actual = constructor_defaults(REGISTRY[key])
            declared = card.defaults()
            self.assertEqual(
                declared,
                actual,
                f"{card.id}: card defaults drifted from {REGISTRY[key].__name__}",
            )

    def test_declared_warmup_matches_the_instance(self) -> None:
        for key, card in self.by_key.items():
            if card.warmup_bars is None:
                continue
            self.assertEqual(
                card.warmup_bars,
                REGISTRY[key]().warmup_bars(),
                f"{card.id}: warmup_bars drifted",
            )

    def test_declared_family_matches_the_registry(self) -> None:
        for key, card in self.by_key.items():
            self.assertEqual(card.family, FAMILY[key], f"{card.id}: family drifted")


class TestSweepDrift(unittest.TestCase):
    """Card presets and research/sweep.py must describe the same experiment."""

    def setUp(self) -> None:
        self.cards = sc.load_all()
        path = REPO_ROOT / "research" / "sweep.py"
        if not path.exists():
            self.skipTest("research/sweep.py not present")
        # research/ is not a package, so load the module by path rather than
        # importing it.
        name = "_sweep_for_tests"
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        # Registered before exec because `@dataclass` resolves its own module out
        # of sys.modules; without this the decorator raises on an unregistered
        # dynamically-loaded module.
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        self.horizons = module.HORIZONS

    def test_presets_agree_with_the_sweep_grid(self) -> None:
        for horizon, spec in self.horizons.items():
            for key, params in spec["params"].items():
                card = next(
                    (c for c in self.cards.values() if c.registry_key == key), None
                )
                self.assertIsNotNone(card, f"sweep runs {key!r} but no card describes it")
                if not params:
                    continue
                declared = card.presets.get(horizon)
                self.assertIsNotNone(
                    declared, f"{card.id}: no {horizon} preset, but the sweep has one"
                )
                self.assertEqual(
                    {k: declared[k] for k in params if k in declared},
                    params,
                    f"{card.id}: {horizon} preset disagrees with research/sweep.py",
                )


class TestCardsAreRunnable(unittest.TestCase):
    """The point of the schema: a card is enough to construct and run a strategy."""

    def setUp(self) -> None:
        self.cards = sc.load_all()
        self.arrays = synthetic_bars()
        self.config = EngineConfig(
            initial_capital=10_000.0,
            interval="1d",
            costs=CostConfig(fee_bps=6.0, slippage_bps=2.0),
        )

    def test_every_buildable_card_constructs_and_backtests(self) -> None:
        for card in self.cards.values():
            if not card.buildable:
                continue
            with self.subTest(card.id):
                strategy = sc.build_from_card(card)
                result = run_backtest(strategy, self.arrays, self.config)
                self.assertEqual(len(result.equity), len(self.arrays["close"]))
                self.assertTrue(np.all(np.isfinite(result.equity)))

    def test_every_horizon_preset_constructs(self) -> None:
        for card in self.cards.values():
            if not card.buildable:
                continue
            for horizon in card.presets:
                with self.subTest(f"{card.id}:{horizon}"):
                    sc.build_from_card(card, horizon=horizon)

    def test_overrides_beat_the_preset(self) -> None:
        card = next(c for c in self.cards.values() if "window" in c.params)
        built = sc.build_from_card(card, window=33)
        self.assertEqual(built.params["window"], 33)

    def test_a_spec_only_card_refuses_to_build_and_says_what_it_needs(self) -> None:
        spec_only = [c for c in self.cards.values() if c.status == "spec-only"]
        self.assertTrue(spec_only, "expected at least one spec-only card")
        for card in spec_only:
            self.assertIsNone(card.registry_key)
            self.assertIsNone(card.runner)
            self.assertFalse(card.implemented)
            with self.assertRaises(sc.CardError) as ctx:
                sc.build_from_card(card)
            self.assertIn(card.data_required[0], str(ctx.exception))

    def test_the_ladder_card_is_implemented_but_not_registry_buildable(self) -> None:
        # The ladder grid is not a Strategy: it has no on_bar and no registry
        # key, and runs through gridcli against core/gridsim.py.
        ladders = [c for c in self.cards.values() if c.kind == "ladder"]
        self.assertEqual(len(ladders), 1, "expected exactly one ladder card")
        ladder = ladders[0]
        self.assertTrue(ladder.implemented)
        self.assertFalse(ladder.buildable)
        self.assertEqual(ladder.runner, "backtester.gridcli")
        with self.assertRaises(sc.CardError):
            sc.build_from_card(ladder)


class TestAgentAffordances(unittest.TestCase):
    """Fields that exist so an agent can filter without parsing prose."""

    def setUp(self) -> None:
        self.cards = sc.load_all()

    def test_implementable_today_selects_spec_cards_with_data_on_hand(self) -> None:
        selected = sc.implementable_today(self.cards)
        for card in selected:
            self.assertEqual(card.status, "spec-only")
            self.assertTrue(card.data_available)
        # And it must exclude anything needing data this repo does not have.
        excluded = [
            c for c in self.cards.values() if c.status == "spec-only" and not c.data_available
        ]
        for card in excluded:
            self.assertNotIn(card, selected)

    def test_preset_falls_back_to_defaults_when_a_horizon_is_absent(self) -> None:
        card = next(c for c in self.cards.values() if c.buildable and c.params)
        self.assertEqual(
            card.preset("medium") if "medium" in card.presets else card.defaults(),
            card.preset("medium"),
        )

    def test_an_unknown_horizon_is_refused(self) -> None:
        card = next(iter(self.cards.values()))
        with self.assertRaises(KeyError):
            card.preset("decade")


if __name__ == "__main__":
    unittest.main()

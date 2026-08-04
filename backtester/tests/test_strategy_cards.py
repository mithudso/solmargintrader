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
            # This case raises at the "indented line has no parent key" check, not at
            # a nest-under-scalar check; named for what it actually exercises.
            "indent with no parent": "---\na: 1\n  b: 2\n---\n",
            "nested flow sequence": "---\na: {b: [1, 2]}\n---\n",
            "nested flow mapping": "---\na: [x, {b: 1}]\n---\n",
            "duplicate top-level key": "---\na: 1\nb: 2\na: 3\n---\n",
            "duplicate flow key": "---\na: {x: 1, x: 2}\n---\n",
            "duplicate block child": "---\na:\n  x: 1\n  x: 2\n---\n",
            "nan": "---\na: nan\n---\n",
            "inf": "---\na: inf\n---\n",
            "negative infinity": "---\na: -Infinity\n---\n",
        }
        for label, text in cases.items():
            with self.subTest(label), self.assertRaises(sc.CardError):
                sc.parse_frontmatter(text, where=label)


class TestCardValidation(unittest.TestCase):
    """What a malformed card is refused for. Every rule here protects a number."""

    BASE = {
        "id": "demo", "name": "Demo", "kind": "exposure-strategy",
        "status": "spec-only", "family": "test", "summary": "one line",
        "data_required": "[ohlcv]", "data_available": "true",
        "success_likelihood": "low", "success_basis": "a-priori",
    }

    def write_card(self, extra_lines: list[str] = (), **overrides) -> Path:
        fields = {**self.BASE, **overrides}
        lines = ["---"] + [f"{k}: {v}" for k, v in fields.items()]
        lines += list(extra_lines) + ["---", "", "# Body"]
        path = Path(self.tmp) / "demo.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def setUp(self) -> None:
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_a_valid_minimal_card_loads(self) -> None:
        card = sc.load_card(self.write_card())
        self.assertEqual(card.id, "demo")
        self.assertFalse(card.implemented)

    def test_an_unknown_frontmatter_field_is_refused(self) -> None:
        # A `warmpu_bars` typo used to be dropped in silence, and the warmup drift
        # check then skipped the card entirely.
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(self.write_card(warmpu_bars="53"))
        self.assertIn("warmpu_bars", str(ctx.exception))

    def test_a_param_needs_either_a_default_or_required(self) -> None:
        with self.assertRaises(sc.CardError):
            sc.load_card(self.write_card(["params:", "  a: {type: int}"]))
        with self.assertRaises(sc.CardError):
            sc.load_card(
                self.write_card(["params:", "  a: {default: 1, required: true}"])
            )
        ok = sc.load_card(self.write_card(["params:", "  a: {required: true}"]))
        self.assertEqual(ok.required_params(), ["a"])
        self.assertEqual(ok.defaults(), {})

    def test_a_declared_param_type_is_enforced_against_its_default(self) -> None:
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(
                self.write_card(["params:", "  a: {default: two, type: int}"])
            )
        self.assertIn("type int", str(ctx.exception))
        # A bool is not an int here, despite Python's inheritance.
        with self.assertRaises(sc.CardError):
            sc.load_card(
                self.write_card(["params:", "  a: {default: true, type: int}"])
            )

    def test_an_unknown_param_key_is_refused(self) -> None:
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(
                self.write_card(["params:", "  a: {default: 1, dsec: typo}"])
            )
        self.assertIn("dsec", str(ctx.exception))

    def test_string_fields_must_be_strings(self) -> None:
        # `family: 007` parsed to int 7 and then crashed the inventory printer.
        with self.assertRaises(sc.CardError):
            sc.load_card(self.write_card(family="007"))

    def test_data_required_entries_must_be_strings(self) -> None:
        with self.assertRaises(sc.CardError):
            sc.load_card(self.write_card(data_required="[1, 2]"))

    def test_a_falsy_wrong_type_still_reaches_the_type_check(self) -> None:
        # `params: []` was coerced to {} by an `or`, skipping the isinstance guard.
        with self.assertRaises(sc.CardError):
            sc.load_card(self.write_card(params="[]"))

    def test_an_implemented_card_may_not_claim_a_measurement(self) -> None:
        # 'implemented' exists precisely to describe code with no data to run on —
        # the JLP case. Letting it carry an evaluation or cite measured-oos would
        # collapse it back into 'measured' and invent a result.
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(
                self.write_card(
                    status="implemented", runner="backtester.paircli",
                    evaluation="single-split-70-30",
                )
            )
        self.assertIn("evaluation must be null", str(ctx.exception))

        with self.assertRaises(sc.CardError):
            sc.load_card(
                self.write_card(
                    status="implemented", runner="backtester.paircli",
                    success_basis="measured-oos",
                )
            )

    def test_an_implemented_card_must_still_name_a_runner(self) -> None:
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(self.write_card(status="implemented"))
        self.assertIn("must name its runner", str(ctx.exception))

    def test_a_valid_implemented_card_loads(self) -> None:
        card = sc.load_card(
            self.write_card(status="implemented", runner="backtester.paircli")
        )
        self.assertTrue(card.implemented, "runner set means something runs it")
        self.assertFalse(card.buildable, "but not from the strategy registry")
        self.assertIsNone(card.evaluation)

    def test_a_card_on_backtester_cli_must_name_a_registry_key(self) -> None:
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_card(
                self.write_card(status="measured", runner="backtester.cli",
                                evaluation="single-split-70-30",
                                success_basis="measured-oos")
            )
        self.assertIn("registry_key", str(ctx.exception))

    def test_a_spec_only_card_cannot_claim_a_runner_or_registry_key(self) -> None:
        for override in ({"registry_key": "macd"}, {"runner": "backtester.cli"}):
            with self.assertRaises(sc.CardError):
                sc.load_card(self.write_card(**override))

    def test_two_cards_cannot_claim_one_registry_key(self) -> None:
        for name in ("a.md", "b.md"):
            Path(self.tmp, name).write_text(
                "\n".join(
                    [
                        "---",
                        f"id: {name[0]}",
                        "name: Demo",
                        "kind: exposure-strategy",
                        "status: measured",
                        "family: trend",
                        "summary: s",
                        "registry_key: macd",
                        "runner: backtester.cli",
                        "evaluation: single-split-70-30",
                        "data_required: [ohlcv]",
                        "data_available: true",
                        "success_likelihood: low",
                        "success_basis: measured-oos",
                        "---",
                        "",
                        "body",
                    ]
                ),
                encoding="utf-8",
            )
        with self.assertRaises(sc.CardError) as ctx:
            sc.load_all(self.tmp)
        self.assertIn("already", str(ctx.exception))


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


class TestSuccessRatings(unittest.TestCase):
    """The ratings must stay honest, and honesty here is checkable in three ways."""

    def setUp(self) -> None:
        self.cards = sc.load_all()

    def test_no_card_claims_a_rating_outside_the_scale(self) -> None:
        for card in self.cards.values():
            self.assertIn(card.success_likelihood, sc.SUCCESS_LIKELIHOODS)
            self.assertIn(card.success_basis, sc.SUCCESS_BASES)

    def test_there_is_no_high_rating_available_at_all(self) -> None:
        # Across 311 rankable configurations, 14% had a positive out-of-sample
        # Sharpe and 9% made money. A 'high' rating would be a claim the evidence
        # base cannot support for anything, so the vocabulary omits it.
        self.assertNotIn("high", sc.SUCCESS_LIKELIHOODS)
        for card in self.cards.values():
            self.assertNotEqual(card.success_likelihood, "high")

    def test_only_a_measured_card_may_cite_a_measured_result(self) -> None:
        for card in self.cards.values():
            if card.success_basis == "measured-oos":
                self.assertEqual(
                    card.status,
                    "measured",
                    f"{card.id}: cites an out-of-sample result it never produced",
                )
            if card.status == "spec-only":
                self.assertNotEqual(card.success_basis, "measured-oos", card.id)

    def test_every_card_explains_its_rating_in_the_body(self) -> None:
        # A rating with no stated reason is an opinion wearing a field name.
        for card in self.cards.values():
            self.assertIn(
                f"Likelihood of success: {card.success_likelihood}",
                card.body,
                f"{card.id}: frontmatter rating has no matching body section",
            )
            self.assertIn(
                f"Basis: {card.success_basis}",
                card.body,
                f"{card.id}: body does not state the basis its frontmatter claims",
            )

    def test_the_distribution_is_not_flattering(self) -> None:
        # A directory where most cards looked promising would be the tell that the
        # ratings had drifted into marketing. The measured base rate is 9% profitable.
        counts = {k: 0 for k in sc.SUCCESS_LIKELIHOODS}
        for card in self.cards.values():
            counts[card.success_likelihood] += 1
        self.assertLessEqual(
            counts["moderate"],
            max(2, len(self.cards) // 10),
            f"too many cards rated moderate: {counts}",
        )


class TestRegistryDrift(unittest.TestCase):
    """Both directions. Either one failing silently is how cards rot."""

    def setUp(self) -> None:
        self.cards = sc.load_all()
        # Built with a collision check rather than a comprehension: a dict
        # comprehension is last-wins, so a second card claiming the same key would
        # shadow the first and its defaults would never be compared to anything.
        self.by_key: dict[str, sc.StrategyCard] = {}
        for card in self.cards.values():
            if not card.registry_key:
                continue
            self.assertNotIn(
                card.registry_key,
                self.by_key,
                f"{card.id}: registry_key already claimed",
            )
            self.by_key[card.registry_key] = card

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


class TestLadderDrift(unittest.TestCase):
    """The ladder has no registry key, so the registry drift test cannot see it.

    Without this class its declared parameters are verified against nothing — and it is
    the card sitting under the strategy the extension actually trades.
    """

    def setUp(self) -> None:
        self.cards = sc.load_all()
        ladders = [c for c in self.cards.values() if c.kind == "ladder"]
        self.assertEqual(len(ladders), 1, "expected exactly one ladder card")
        self.card = ladders[0]

    def test_declared_params_match_gridconfig(self) -> None:
        from backtester.core.gridsim import GridConfig

        sig = inspect.signature(GridConfig)
        self.assertEqual(
            set(self.card.params),
            set(sig.parameters),
            "ladder card parameters drifted from GridConfig",
        )
        for name, param in sig.parameters.items():
            spec = self.card.params[name]
            if param.default is inspect.Parameter.empty:
                self.assertIs(
                    spec.get("required"),
                    True,
                    f"{name} has no default in GridConfig, so the card must mark it "
                    "required rather than invent one",
                )
                self.assertNotIn("default", spec, f"{name} must not declare a default")
            else:
                self.assertEqual(
                    spec.get("default"),
                    param.default,
                    f"{name}: card default drifted from GridConfig",
                )

    def test_declared_defaults_are_constructible(self) -> None:
        # The declared defaults plus a plausible required set must build a real config,
        # so the card cannot declare a combination GridConfig would reject.
        from backtester.core.gridsim import GridConfig

        cfg = GridConfig(
            lower=60.0, upper=90.0, rungs=7, notional_per_rung_usd=12.0,
            **self.card.defaults(),
        )
        self.assertEqual(cfg.spacing, self.card.defaults()["spacing"])


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
                # Exact, not an intersection: an extra preset key at a value the
                # sweep never ran is the same "card documents one experiment, sweep
                # runs another" failure this class exists to catch.
                self.assertEqual(
                    declared,
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

    def test_preset_layers_over_defaults_and_falls_back_when_absent(self) -> None:
        # Hand-built rather than selected from the corpus, so the assertion is against
        # literals. The previous version of this test picked a card that HAD a medium
        # preset and compared preset("medium") to itself, which passed against a
        # stubbed-out implementation.
        card = sc.StrategyCard(
            id="demo", name="demo", kind="exposure-strategy", status="spec-only",
            family="test", summary="s", data_required=["ohlcv"], data_available=True,
            success_likelihood="low", success_basis="a-priori",
            path=Path("demo.md"), body="b",
            params={"a": {"default": 1}, "b": {"default": 2}},
            presets={"short": {"a": 9}},
        )
        # A partial preset layers over the defaults rather than replacing them.
        self.assertEqual(card.preset("short"), {"a": 9, "b": 2})
        # An absent horizon falls back to the defaults entirely.
        self.assertEqual(card.preset("long"), {"a": 1, "b": 2})

    def test_an_unknown_horizon_is_refused(self) -> None:
        card = next(iter(self.cards.values()))
        with self.assertRaises(KeyError):
            card.preset("decade")


if __name__ == "__main__":
    unittest.main()

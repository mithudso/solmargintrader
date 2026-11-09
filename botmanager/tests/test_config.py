from __future__ import annotations

import ast
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from botmanager.config import DEFAULT_CONTEXT, STRATEGY_VERSIONS, resolve_config
from botmanager.domain import BotSpec, ManagerError, ResolvedConfig, fingerprint


def learned(**changes):
    return {
        "schema_version": 1,
        "strategy_id": "grid",
        "strategy_version": STRATEGY_VERSIONS["grid"],
        "context": dict(DEFAULT_CONTEXT, execution_model="trigger_ladder"),
        "revision": "learned-7",
        "values": {"range_pct": 22.0},
        **changes,
    }


class ConfigTests(unittest.TestCase):
    def test_direct_resolved_overrides_and_provenance_must_match_effective_values(self):
        base = resolve_config("grid", {}, {"range_pct": 19.0}, None)
        for overrides in (
            {"range_pct": "credential-canary-for-review"},
            {"range_pct": 20.0},
            {},
            {"range_pct": True},
        ):
            forged = ResolvedConfig(
                base.values, base.provenance, overrides, base.shared_compatibility
            )
            with self.subTest(case=type(overrides.get("range_pct")).__name__):
                with self.assertRaises(ManagerError) as raised:
                    BotSpec.create("forged", "grid", forged)
                self.assertNotIn("credential-canary-for-review", str(raised.exception))
        provenance = {key: dict(value) for key, value in base.provenance.items()}
        provenance["range_pct"]["source"] = "packaged"
        with self.assertRaises(ManagerError):
            BotSpec.create(
                "forged",
                "grid",
                ResolvedConfig(
                    base.values,
                    provenance,
                    base.user_overrides,
                    base.shared_compatibility,
                ),
            )

    def test_reconstruction_checks_metadata_types_and_shared_compatibility(self):
        valid = BotSpec.create("valid", "grid", resolve_config("grid", {}, {}, None))
        malformed = (
            {"bar_seconds": 60.0},
            {
                "shared_compatibility": {
                    "accepted": "false",
                    "reason": "no_shared_snapshot",
                }
            },
            {
                "shared_compatibility": {
                    "accepted": False,
                    "reason": "exact_semantics_match",
                }
            },
            {
                "shared_compatibility": {
                    "accepted": True,
                    "reason": "incompatible_shared_context",
                }
            },
            {
                "shared_compatibility": {
                    "accepted": True,
                    "reason": "exact_semantics_match",
                }
            },
            {
                "shared_compatibility": {
                    "accepted": False,
                    "reason": "no_shared_snapshot",
                    "extra": 1,
                }
            },
        )
        for change in malformed:
            raw = {**valid.to_dict(), **change}
            raw["config_hash"] = fingerprint(
                {key: raw[key] for key in valid._config_body()}
            )
            with (
                self.subTest(field=next(iter(change))),
                self.assertRaises(ManagerError),
            ):
                BotSpec.from_dict(raw)

    def test_complete_defaults_and_sources(self):
        for family in ("grid", "dca", "trend", "momentum"):
            result = resolve_config(family, {}, {}, None)
            self.assertEqual(result.values["mode"], "paper")
            self.assertIs(result.values["armed"], False)
            self.assertEqual(set(result.values), set(result.provenance))
            self.assertTrue(
                all(
                    p["source_revision"] and p["reason"]
                    for p in result.provenance.values()
                )
            )
        self.assertEqual(
            resolve_config("dca", {}, {}, None).values["min_order_usd"], 10.0
        )

    def test_learned_defaults_only_with_exact_semantics(self):
        good = resolve_config("grid", {}, {}, learned())
        self.assertEqual(good.values["range_pct"], 22.0)
        self.assertEqual(good.provenance["range_pct"]["source"], "shared")
        for changes in (
            {"strategy_version": "old"},
            {"schema_version": 2},
            {
                "context": dict(
                    DEFAULT_CONTEXT, venue="coinbase", execution_model="trigger_ladder"
                )
            },
            {
                "context": dict(
                    DEFAULT_CONTEXT, bar_seconds=3600, execution_model="trigger_ladder"
                )
            },
            {
                "context": dict(
                    DEFAULT_CONTEXT, bar_seconds=60.0, execution_model="trigger_ladder"
                )
            },
            {"context": {}},
        ):
            rejected = resolve_config("grid", {}, {}, learned(**changes))
            self.assertEqual(rejected.values["range_pct"], 15.0)
            self.assertEqual(rejected.shared_compatibility["accepted"], False)
            self.assertIn("incompatible", rejected.provenance["range_pct"]["reason"])

    def test_override_wins_zero_false_and_immutable_snapshot(self):
        overrides = {"deadband_bps": 0, "armed": False, "range_pct": 19.0}
        result = resolve_config("grid", {}, overrides, learned())
        overrides["range_pct"] = 88
        self.assertEqual(result.values["deadband_bps"], 0)
        self.assertIs(result.values["armed"], False)
        self.assertEqual(result.values["range_pct"], 19)
        self.assertEqual(result.user_overrides["range_pct"], 19)
        self.assertEqual(result.provenance["range_pct"]["source"], "override")
        with self.assertRaises(TypeError):
            result.values["range_pct"] = 1
        with self.assertRaises(TypeError):
            result.provenance["range_pct"]["source"] = "changed"

    def test_nonfinite_unknown_wrong_types_and_cross_constraints_refuse(self):
        for values in (
            {"range_pct": math.nan},
            {"range_pct": math.inf},
            {"range_pct": True},
            {"rungs": 7.0},
            {"rungs": "7"},
            {"range_pct": 100},
            {"rungs": 1},
            {"api_key": "canary-secret"},
            {"armed": True},
            {"mode": "live"},
        ):
            with self.subTest(values=values), self.assertRaises(ManagerError):
                resolve_config("grid", {}, values, None)
        with self.assertRaises(ManagerError):
            resolve_config("grid", {}, {"capital_usd": 10**1000}, None)
        for family, values in (
            ("trend", {"fast_period": 30}),
            ("dca", {"price_deviation_pct": 50}),
            ("dca", {"base_order_usd": 1}),
            ("momentum", {"window": False}),
        ):
            with self.assertRaises(ManagerError):
                resolve_config(family, {}, values, None)

    def test_no_learned_risk_or_arming_and_invalid_learned_settings_refuse(self):
        for values in (
            {"armed": True},
            {"capital_usd": 9000},
            {"range_pct": math.nan},
            {"rungs": False},
            {"unknown": 3},
        ):
            with self.assertRaises(ManagerError):
                resolve_config("grid", {}, {}, learned(values=values))

    def test_unsupported_families_are_explicit(self):
        for family, code in (
            ("arbitrage", "solana_adapter_unavailable"),
            ("council", "external_only"),
        ):
            with self.assertRaises(ManagerError) as raised:
                resolve_config(family, {}, {}, None)
            self.assertEqual(raised.exception.code, code)

    def test_shared_dca_settings_cannot_reduce_stop_or_venue_constraints(self):
        for protected in (
            "base_order_usd",
            "safety_order_usd",
            "min_order_usd",
            "stop_loss_pct",
        ):
            snapshot = learned(
                strategy_id="dca",
                strategy_version=STRATEGY_VERSIONS["dca"],
                context=dict(DEFAULT_CONTEXT, execution_model="safety_order_ladder"),
                values={protected: 0},
            )
            with self.assertRaises(ManagerError):
                resolve_config("dca", {}, {}, snapshot)

    def test_defaults_match_constructor_source_without_importing_numeric_adapters(self):
        root = Path(__file__).resolve().parents[2]
        tree = ast.parse((root / "soltui/bots.py").read_text())
        grid = next(
            node
            for node in tree.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "GRID_DEFAULTS"
        )
        for key, value in ast.literal_eval(grid.value).items():
            self.assertEqual(resolve_config("grid", {}, {}, None).values[key], value)
        for family, path, class_name in (
            ("dca", "backtester/core/dcasim.py", "DcaConfig"),
            ("trend", "soltui/trend.py", "TrendConfig"),
        ):
            tree = ast.parse((root / path).read_text())
            cls = next(
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef) and node.name == class_name
            )
            values = resolve_config(family, {}, {}, None).values
            for field in (node for node in cls.body if isinstance(node, ast.AnnAssign)):
                value = (
                    10.0
                    if isinstance(field.value, ast.Name)
                    else ast.literal_eval(field.value)
                )
                self.assertEqual(values[field.target.id], value)
        tree = ast.parse((root / "backtester/core/strategies/signals.py").read_text())
        cls = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "TsMomentum"
        )
        constructor = next(
            node
            for node in cls.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        for key, node in zip(("window", "threshold"), constructor.args.defaults):
            self.assertEqual(
                resolve_config("momentum", {}, {}, None).values[key],
                ast.literal_eval(node),
            )

    def test_changed_packaged_default_does_not_change_saved_spec(self):
        from botmanager.domain import BotSpec

        from botmanager import config

        spec = BotSpec.create("pinned", "grid", resolve_config("grid", {}, {}, None))
        with patch.object(config, "SOURCE_REVISION", "new-code-revision"):
            loaded = BotSpec.from_dict(spec.to_dict())
        self.assertEqual(loaded.to_dict(), spec.to_dict())

"""Candidate economic corrections remain separate from the frozen baseline."""
from __future__ import annotations

import importlib
import unittest
import tempfile
import shutil
from pathlib import Path
from research.strategy_compare import load_registry

import numpy as np

from backtester.core.types import BarWindow

from research.strategy_snapshots import ensure_snapshots

_scratch = tempfile.TemporaryDirectory(prefix='candidate-strategies-')
EXPERIMENT = Path(_scratch.name)
_SOURCE = Path(__file__).resolve().parents[2] / 'research/strategy_experiment'
for _name in ('archives.json', 'snapshot.json', 'original.zip', 'candidate.zip'):
    shutil.copyfile(_SOURCE / _name, EXPERIMENT / _name)
ensure_snapshots(EXPERIMENT)
for _variant in ('original', 'candidate'):
    load_registry(EXPERIMENT / _variant / 'core', 'candidate_test_' + _variant)

def tearDownModule():
    _scratch.cleanup()


def window(step: int, n: int = 180, extra: int = 0) -> BarWindow:
    i = np.arange(n + extra)
    close = 100 * np.exp(i * .003 + .02 * np.sin(i))
    return BarWindow(i * step, close, close * 1.01, close * .99, close,
                     np.ones(n + extra), n - 1)


class CandidateAnnualizationTests(unittest.TestCase):
    def test_hourly_risk_scaling_and_daily_parity(self):
        for module, name in [('signals', 'VolTargetTrend'), ('advanced', 'GarchVolTarget')]:
            with self.subTest(strategy=name):
                old = getattr(importlib.import_module(f'_strategy_compare_candidate_test_original.strategies.{module}'), name)
                new = getattr(importlib.import_module(f'_strategy_compare_candidate_test_candidate.strategies.{module}'), name)
                daily = new(target_vol=.01).on_bar(window(86400))
                hourly = new(target_vol=.01).on_bar(window(3600))
                self.assertAlmostEqual(daily, old(target_vol=.01).on_bar(window(86400)))
                self.assertGreater(hourly, 0)
                self.assertLess(daily, 1)
                self.assertAlmostEqual(daily / hourly, np.sqrt(24))

    def test_candidate_prefix_invariance(self):
        for module, name in [('signals', 'VolTargetTrend'), ('advanced', 'GarchVolTarget')]:
            factory = getattr(importlib.import_module(f'_strategy_compare_candidate_test_candidate.strategies.{module}'), name)
            self.assertEqual(factory().on_bar(window(3600)), factory().on_bar(window(3600, extra=30)))

    def test_invalid_cadence_refuses_risk_sizing(self):
        cadence = importlib.import_module('_strategy_compare_candidate_test_candidate.strategies._cadence').observed_periods_per_year
        for w in [window(0), window(3600, n=1)]:
            with self.assertRaises(ValueError):
                cadence(w)

    def test_original_files_still_match_snapshot(self):
        import hashlib
        import json
        experiment = EXPERIMENT
        manifest = json.loads((experiment / 'snapshot.json').read_text())
        for relative, expected in manifest['original_files'].items():
            with self.subTest(path=relative):
                self.assertEqual(hashlib.sha256((experiment / 'original' / relative).read_bytes()).hexdigest(), expected)

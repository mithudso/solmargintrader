"""Consolidation keeps unavailable, diagnostic and incompatible records visible."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.meta_analysis import clean, consolidate, family, role


class MetaAnalysisTests(unittest.TestCase):
    def test_preserves_fraction_percent_bps_strings_and_insufficient_records(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "sweep.csv"
            p.write_text('id,return,return_pct,fee_bps,insufficient\n001,0.25,25,90,False\n002,,,,True\n')
            result = consolidate([p])
            rows = result["artifacts"][0]["data"]
            self.assertEqual(rows[0], {"id": "001", "return": "0.25", "return_pct": "25", "fee_bps": "90", "insufficient": "False"})
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["insufficient"], "True")

    def test_byte_duplicates_are_aliases_not_extra_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory) / "a.json", Path(directory) / "b.json"
            a.write_text('[{"return": -1}]')
            b.write_bytes(a.read_bytes())
            result = consolidate([a, b])
            self.assertEqual(len(result["artifacts"]), 1)
            self.assertEqual(result["byte_identical_aliases"][0]["same_bytes_as"], str(a.resolve()))

    def test_nonfinite_is_visible_and_strict_json_remains_valid(self):
        value = clean({"sharpe": float("inf"), "failed": float("nan")})
        self.assertEqual(value["sharpe"], {"nonfinite_original": "inf"})
        json.dumps(value, allow_nan=False)

    def test_report_only_and_diagnostic_sources_are_not_profit_replications(self):
        self.assertIn("not_an_independent", role("SWEEP-9COIN.md"))
        self.assertIn("diagnostic", role("signal_redundancy.csv"))
        self.assertEqual(family("strategy-config-sweep-validated-20261110/results.jsonl"), "validated_configuration_sweep")
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "SWEEP-9COIN.md"
            p.write_text('Historical report; raw source missing.')
            result = consolidate([p], [{"path": "/missing", "reason": "unavailable"}])
            self.assertEqual(result["artifacts"][0]["data"], p.read_text())
            self.assertEqual(len(result["excluded_or_missing"]), 1)

    def test_read_error_is_not_an_empty_successful_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bad.json"
            p.write_text('{broken')
            result = consolidate([p])
            self.assertEqual(result["artifacts"], [])
            self.assertEqual(len(result["read_errors"]), 1)


if __name__ == "__main__":
    unittest.main()

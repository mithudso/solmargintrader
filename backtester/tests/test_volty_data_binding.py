"""Preparation binds exact source bytes without executing the strategy study."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from backtester import voltycli


class VoltyInputTests(unittest.TestCase):
    def _inputs(self, root):
        source, output = root / "source", root / "output"
        source.mkdir()
        output.mkdir()
        frame = pd.DataFrame({"timestamp": np.arange(160) * 60,
                              **{name: np.full(160, 100.0) for name in ("open", "high", "low", "close")},
                              "volume": np.ones(160)})
        manifest = {}
        for interval in ("1m", "1h"):
            path = source / f"ZEC_{interval}.csv"
            frame.to_csv(path, index=False)
            manifest[interval] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        (source / "manifest.json").write_text(json.dumps(manifest))
        return source, output, frame, manifest

    def test_replacement_before_parse_cannot_change_the_hashed_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output, frame, manifest = self._inputs(Path(temp))
            parse = pd.read_csv
            changed = False
            def replace_before_parse(data, *args, **kwargs):
                nonlocal changed
                if not changed:
                    changed = True
                    replacement = frame.copy()
                    replacement.loc[:, ["open", "high", "low", "close"]] = 110.0
                    replacement.to_csv(source / "ZEC_1m.csv", index=False)
                return parse(data, *args, **kwargs)
            with patch.object(voltycli, "STEPS", {name: 60 for name in voltycli.STEPS}), patch.object(voltycli.pd, "read_csv", replace_before_parse):
                frames, provenance = voltycli.prepare(source, output, 90)
            self.assertTrue(changed)
            self.assertTrue(np.all(frames["1m"]["close"] == 100.0))
            self.assertEqual(provenance["1m"]["source_sha256"], manifest["1m"]["sha256"])

    def test_off_grid_source_is_refused_before_any_derived_file_is_written(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output, frame, manifest = self._inputs(Path(temp))
            frame["timestamp"] += 1
            path = source / "ZEC_1m.csv"
            frame.to_csv(path, index=False)
            manifest["1m"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            (source / "manifest.json").write_text(json.dumps(manifest))
            with patch.object(voltycli, "STEPS", {name: 60 for name in voltycli.STEPS}), self.assertRaises(ValueError):
                voltycli.prepare(source, output, 90)
            self.assertEqual(list(output.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

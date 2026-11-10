from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from research.strategy_snapshots import ensure_snapshots


class SnapshotMetadataTests(unittest.TestCase):
    def test_finder_metadata_does_not_change_frozen_source_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = {}
            for variant in ("original", "candidate"):
                path = root / variant
                path.mkdir()
                (path / "engine.py").write_bytes(b"original source")
                (path / ".DS_Store").write_bytes(b"finder metadata")
                manifest[variant] = {
                    "files": {
                        "engine.py": hashlib.sha256(b"original source").hexdigest()
                    }
                }
            (root / "archives.json").write_text(json.dumps(manifest))
            ensure_snapshots(root)
            (root / "original" / "extra.py").write_text("unexpected code")
            with self.assertRaisesRegex(ValueError, "expanded sources differ"):
                ensure_snapshots(root)

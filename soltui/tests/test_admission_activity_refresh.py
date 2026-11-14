"""Observed process liveness can refresh without clearing explicit owner fences."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from soltui.experiments import ExperimentError, ExperimentStore


class ActivityRefreshTests(unittest.TestCase):
    def refresh(self, declared, *, legacy=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = ExperimentStore(root / "canonical")
            descriptor = {"root": str(root / "client"), "kind": "f5", "active": declared}
            observed = {**descriptor, "coverage": "verified", "absence_checked": False,
                        "records": [], "active": True}
            with patch("soltui.research_admission.inspect_history", return_value=observed):
                store.manager_register_client(descriptor)
            if legacy:
                with store._connect() as db:
                    old = json.loads(db.execute("SELECT identity FROM manager_clients").fetchone()[0])
                    old.pop("declared_active", None)
                    db.execute("UPDATE manager_clients SET identity=?", (json.dumps(old),))
            run = {"status": "created", "spec": {"geometry": {"holdout": [{"coin": "SOL", "start": 100., "end": 200.}]}}}
            with patch("soltui.research_admission.inspect_history", return_value={**observed, "active": False}), \
                    patch.object(store, "get_run", return_value=run), \
                    self.assertRaisesRegex(ExperimentError, "persisted verdict"):
                # The real refresh executes before the unchanged final-verdict
                # gate refuses this deliberately unprepared temporary run.
                store.manager_unseal("inert-unprepared-run")
            with store._connect() as db:
                return db.execute("SELECT active,identity FROM manager_clients").fetchone()

    def test_observed_liveness_clears_after_a_later_inactive_observation(self):
        active, identity = self.refresh(False)
        self.assertEqual(active, 0)
        self.assertIs(json.loads(identity)["declared_active"], False)

    def test_explicit_manual_active_fence_remains_blocked(self):
        self.assertEqual(self.refresh(True)[0], 1)

    def test_legacy_ambiguous_activity_remains_conservatively_blocked(self):
        self.assertEqual(self.refresh(False, legacy=True)[0], 1)


if __name__ == "__main__":
    unittest.main()

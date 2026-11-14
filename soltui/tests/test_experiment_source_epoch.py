"""Changed source refuses a fresh experiment before admission or publication."""
from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from soltui import experiment_runner
from soltui.source_epoch import SourceEpochChanged


class ExperimentEpochTests(unittest.TestCase):
    def test_prepare_refuses_before_creating_an_experiment_store(self):
        epoch = Mock()
        epoch.verify.side_effect = SourceEpochChanged("restart required")
        with patch.object(experiment_runner, "_SOURCE_EPOCH", epoch, create=True), \
                patch.object(experiment_runner, "ExperimentStore") as store, \
                self.assertRaises(SourceEpochChanged):
            experiment_runner.prepare_experiment("grid")
        store.assert_not_called()

    def test_run_refuses_before_creating_an_experiment_store(self):
        epoch = Mock()
        epoch.verify.side_effect = SourceEpochChanged("restart required")
        with patch.object(experiment_runner, "_SOURCE_EPOCH", epoch, create=True), \
                patch.object(experiment_runner, "ExperimentStore") as store, \
                self.assertRaises(SourceEpochChanged):
            experiment_runner.run_experiment("inert")
        store.assert_not_called()

    def test_source_change_during_computation_cannot_publish_a_cell(self):
        epoch = Mock()
        epoch.verify.side_effect = [None, None, None, SourceEpochChanged("restart required")]
        store = Mock()
        store.cells.return_value = []
        window = {"coin": "SOL", "split": "train", "start": 0, "end": 3600,
                  "key": "inert", "data_source": "temporary", "data_fingerprint": "synthetic"}
        spec = {"bot": "grid", "candidates": [{}], "products": [],
                "code_fingerprint": "source-only", "costs": {}}
        with patch.object(experiment_runner, "_SOURCE_EPOCH", epoch, create=True), \
                patch.object(experiment_runner, "_halt", return_value=False), \
                patch.object(experiment_runner, "_reload_bar", return_value={}), \
                patch.object(experiment_runner, "_metrics", return_value={"total_return": 0.}), \
                self.assertRaises(SourceEpochChanged):
            experiment_runner._evaluate(store, "inert", spec, None, [window], [0], None)
        store.record_cell.assert_not_called()


if __name__ == "__main__":
    unittest.main()

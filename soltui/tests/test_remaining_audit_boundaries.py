"""Known-answer final production boundaries; no live work or image rendering."""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from soltui import config, f5_batch, liquidity
from soltui.experiment_screens import ExperimentScreen
from soltui.source_epoch import SourceEpochChanged


class RemainingBoundaryTests(unittest.TestCase):
    def test_liquidity_huge_number_and_future_age_stay_unknown(self):
        self.assertIsNone(liquidity.num(10 ** 400))
        summary = liquidity.summarise({"generated_at": 200.}, now=100.)
        self.assertTrue(summary.stale)
        self.assertIsNone(summary.age)

    def test_liquidity_incomplete_position_sum_is_not_a_complete_total(self):
        summary = liquidity.summarise({"positions": [{"pnl_usd": 10., "deposited_usd": 100.},
                                                     {"deposited_usd": 100.}]})
        self.assertIsNone(summary.total_pnl_usd)
        self.assertIsNone(summary.net_pct)
        self.assertEqual(summary.total_deposited_usd, 200.)

    def test_workbench_unexpected_exception_cannot_echo_private_input(self):
        canary = "PRIVATE-WORKBENCH-CREDENTIAL-CANARY"
        envelopes = []
        screen = SimpleNamespace(call=Mock(side_effect=OSError(canary)),
            query_one=lambda *_: SimpleNamespace(update=lambda _text: None),
            _received=lambda name, env, callback, quiet, accept: envelopes.append(env),
            app=SimpleNamespace(call_from_thread=lambda callback, *args: callback(*args)),
            run_worker=lambda function, **kwargs: function())
        ExperimentScreen._command(screen, "experiments.get", {})
        self.assertNotIn(canary, str(envelopes))
        self.assertIn("OSError", envelopes[0]["error"]["message"])

    def test_icon_conversion_preserves_an_existing_sibling_iconset(self):
        source = Path(__file__).resolve().parents[1] / "make_icon.py"
        tree = ast.parse(source.read_text())
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "build_icns"]
        class ImageFixture:
            def resize(self, *_args):
                return self
            def save(self, path):
                Path(path).write_bytes(b"inert fixture")
        namespace = {"Path": Path, "shutil": shutil, "subprocess": subprocess, "tempfile": tempfile,
                     "render": lambda _size: ImageFixture(), "BASE": 1024, "ICONSET": [(16, "icon.png")],
                     "Image": SimpleNamespace(LANCZOS=0)}
        # Execute only the audited filesystem converter with an inert renderer.
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)  # noqa: S102
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "custom.icns"
            sibling = target.with_suffix(".iconset")
            sibling.mkdir()
            sentinel = sibling / "unrelated-user-file"
            sentinel.write_text("preserve")
            with patch.object(shutil, "which", return_value="/inert/iconutil"), \
                    patch.object(subprocess, "run", return_value=SimpleNamespace(returncode=0)) as convert:
                namespace["build_icns"](target)
            self.assertEqual(sentinel.read_text(), "preserve")
            self.assertEqual(convert.call_args.kwargs["timeout"], 60)

    def test_changed_epoch_refuses_f5_create_before_plan_directory(self):
        epoch = Mock()
        epoch.verify.side_effect = SourceEpochChanged("restart required")
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(f5_batch, "_SOURCE_EPOCH", epoch, create=True), \
                self.assertRaises(SourceEpochChanged):
            f5_batch.create(config.Settings(), ["SOL"], root=Path(directory),
                            intervals=("1h",), strategies=("buy_and_hold",), horizons=("medium",))

    def test_changed_epoch_refuses_f5_run_before_accessing_a_batch(self):
        epoch = Mock()
        epoch.verify.side_effect = SourceEpochChanged("restart required")
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {"SOLTUI_RESEARCH_AUTHORITY": ""}), \
                patch.object(f5_batch, "_SOURCE_EPOCH", epoch, create=True), \
                self.assertRaises(SourceEpochChanged):
            f5_batch.run("0" * 32, root=Path(directory))

    def test_changed_epoch_refuses_f5_cell_before_any_ledger_write(self):
        epoch = Mock()
        epoch.verify.side_effect = SourceEpochChanged("restart required")
        ledger = Mock()
        row = {"id": 1, "asset": "SOL", "interval": "1h", "strategy": "unknown", "horizon": "medium"}
        with patch.object(f5_batch, "_SOURCE_EPOCH", epoch, create=True), self.assertRaises(SourceEpochChanged):
            f5_batch._run_cell(ledger, row, None, {}, lambda: False)
        ledger.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()

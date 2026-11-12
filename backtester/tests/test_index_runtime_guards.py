"""Offline index regressions. All model, HTTP and subprocess work is mocked."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "index"))
import build
import idle
import make_files_doc
import ollama_ensure as oe
import search


class IndexRuntimeGuards(unittest.TestCase):
    def test_model_list_helper_refuses_remote_hosts_before_io(self):
        with mock.patch.object(oe, "_get_json", return_value={"models": []}) as fetch:
            self.assertIsNone(oe.installed_models("https://example.invalid"))
        fetch.assert_not_called()

    def test_model_pull_helper_refuses_remote_hosts_before_io(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"status":"success"}'
        with mock.patch("urllib.request.urlopen", return_value=response) as fetch:
            self.assertFalse(oe.pull_model("fixture", "https://example.invalid"))
        fetch.assert_not_called()

    def test_malformed_model_lists_do_not_raise_or_claim_readiness(self):
        for payload in ([], None, {"models": None}, {"models": ["bad"]}):
            with self.subTest(payload=payload), mock.patch.object(oe, "_get_json", return_value=payload):
                self.assertIsNone(oe.installed_models())

    def test_server_launch_failure_returns_unavailable_without_exception_details(self):
        with mock.patch.object(oe, "installed_models", return_value=None), \
                mock.patch.object(oe, "start_server", side_effect=PermissionError("private-canary")):
            status = oe.ensure()
        self.assertFalse(status.ok)
        self.assertFalse(status.started)
        self.assertNotIn("private-canary", status.message)

    def test_finished_rebuild_preserves_the_hourly_throttle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.multiple(idle, OUT=root, STATE_FILE=root / "state.json", LOCK_FILE=root / "lock"), \
                    mock.patch.object(build, "build_meta", return_value={}), \
                    mock.patch.object(build, "build_semantic", return_value=0), \
                    mock.patch.object(idle.time, "time", return_value=1000), redirect_stdout(io.StringIO()):
                idle._write_state({"last_build_at": 900})
                self.assertEqual(idle.run_build(), 0)
                state = idle._read_state()
                self.assertEqual(state["last_build_at"], 900)
                with mock.patch.dict(idle.os.environ, {"INDEX_FORCE_INTERVAL": "3600"}):
                    self.assertFalse(idle.sweep_due(state, 1600))

    def test_scalar_idle_state_and_manifest_are_unavailable_not_exceptions(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text("[]")
            with mock.patch.object(idle, "STATE_FILE", state):
                self.assertEqual(idle._read_state(), {})
            with mock.patch.object(idle, "active_manifest", return_value=(state, state)):
                self.assertEqual(idle.semantic_status()[0], "stale")

    def test_corrupt_semantic_artifacts_degrade_without_raw_exception_details(self):
        for broken in ("not-json", "[]", json.dumps({"model": oe.EMBED_MODEL})):
            with self.subTest(manifest=broken), tempfile.TemporaryDirectory() as directory:
                manifest = Path(directory) / "manifest.json"
                manifest.write_text(broken)
                notes = []
                ready = oe.Status(True, True, False, True, "ready")
                response = mock.MagicMock()
                response.__enter__.return_value.read.return_value = b'{"embeddings":[[1,0]]}'
                with mock.patch.object(search, "semantic_pair", return_value=(manifest, manifest)), \
                        mock.patch.object(oe, "ensure", return_value=ready), \
                        mock.patch("urllib.request.urlopen", return_value=response), \
                        mock.patch.object(search, "_semantic_matrix", side_effect=ValueError("private-canary")):
                    self.assertIsNone(search.semantic("fixture", notes=notes, start_ollama=False))
                self.assertTrue(notes)
                self.assertNotIn("private-canary", " ".join(notes))

    def test_dimension_mismatch_degrades_to_keyword(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps({"model": oe.EMBED_MODEL}))
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = b'{"embeddings":[[1,0]]}'
            notes = []
            with mock.patch.object(search, "semantic_pair", return_value=(manifest, manifest)), \
                    mock.patch.object(oe, "ensure", return_value=oe.Status(True, True, False, True, "ready")), \
                    mock.patch("urllib.request.urlopen", return_value=response), \
                    mock.patch.object(search, "_semantic_matrix", return_value=({}, np.ones((1, 3)), ["fixture.py"])):
                self.assertIsNone(search.semantic("fixture", notes=notes, start_ollama=False))
            self.assertTrue(notes)

    def test_non_http_semantic_endpoint_is_refused_before_any_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(json.dumps({"endpoint": "file:///private-canary"}))
            with mock.patch.object(search, "semantic_pair", return_value=(manifest, manifest)), \
                    mock.patch.object(oe, "ensure") as ensure, \
                    mock.patch("urllib.request.urlopen") as fetch:
                self.assertIsNone(search.semantic("fixture", notes=[], start_ollama=False))
            ensure.assert_not_called()
            fetch.assert_not_called()

    def test_partial_embedding_response_never_publishes_an_invalid_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            array = root / "semantic.npz"
            manifest = root / "semantic.json"
            with mock.patch.multiple(build, REPO=root, SEMANTIC_NPZ=array, SEMANTIC_MANIFEST=manifest), \
                    mock.patch.object(build, "semantic_corpus", return_value=(["one", "two"], ["a.py", "b.py"])), \
                    mock.patch.object(oe, "ensure", return_value=oe.Status(True, True, False, True, "ready")), \
                    mock.patch.object(build, "embed", return_value=[[1, 0]]), redirect_stdout(io.StringIO()):
                result = build.build_semantic({"files": []})
            self.assertEqual(result, 1)
            self.assertFalse(array.exists())
            self.assertFalse(manifest.exists())

    def test_website_tests_and_modules_have_their_actual_runner(self):
        self.assertEqual(build.classify("website/test/api.test.js"), "test")
        entry = {"path": "website/test/api.test.js", "kind": "test", "ext": ".js"}
        self.assertEqual(make_files_doc.derived_use(entry), "`node --test website/test/api.test.js`")
        entry = {"path": "website/public/app.js", "kind": "code-js", "ext": ".js"}
        self.assertNotIn("extension", make_files_doc.derived_use(entry))


if __name__ == "__main__":
    unittest.main()
